#!/usr/bin/env python3
import asyncio, json, math, signal
from typing import List, Tuple, Optional

import aiohttp
import websockets

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry

# -------------------- Units / constants --------------------
FT_TO_M = 0.3048
M_TO_FT = 1.0 / FT_TO_M

STEP_X_M = 7.5 * FT_TO_M        # 2.286 m per grid step in +X
STEP_Y_M = 5.16129 * FT_TO_M    # ~1.573161 m per grid step in +Y
TARGET_SPEED_MPS = 2.0 * FT_TO_M  # 2 ft/s = 0.6096 m/s

# Endpoints
BACKEND_WS_URI   = "ws://localhost:8765/ws"
HTTP_PATH_URL    = "http://localhost:8000/path"        # returns waypoints
HTTP_DIR_URL     = "http://localhost:8765/directions"  # "START" / "STOP"

# Cable / battery model
INITIAL_CABLE_M = 50.0
BATTERY_DROP_PER_WAYPOINT = 1  # percent drop per waypoint

# Distance tolerance for “segment reached”
REACH_EPS_M = 0.05  # 5 cm slack

# -------------------- Helpers --------------------
def yaw_from_quat(q):
    siny_cosp = 2.0*(q.w*q.z + q.x*q.y)
    cosy_cosp = 1.0 - 2.0*(q.y*q.y + q.z*q.z)
    return math.atan2(siny_cosp, cosy_cosp)

def dist_m(a: Tuple[float,float], b: Tuple[float,float]) -> float:
    dx, dy = b[0]-a[0], b[1]-a[1]
    return math.hypot(dx, dy)

# -------------------- Node --------------------
class PathFollower(Node):
    """
    - Polls HTTP /path for waypoints (grid or {x,y})
    - Polls HTTP /directions for "START"/"STOP"
    - Drives at 2 ft/s with pure-pursuit
    - Sends status JSON ONLY when a waypoint is reached
    - NEW: Immediately sends a status when STOP is received (isMoving=False)
    """

    def __init__(self):
        super().__init__('brain_ws_follower')

        # --- controller params ---
        self.lookahead = 1.0
        self.max_lin   = TARGET_SPEED_MPS
        self.max_ang   = 1.5

        # --- ROS I/O ---
        qos = QoSProfile(depth=10)
        qos.reliability = ReliabilityPolicy.RELIABLE
        qos.history = HistoryPolicy.KEEP_LAST

        self.pub_cmd = self.create_publisher(Twist, '/cmd_vel', 10)
        self.sub_odom = self.create_subscription(Odometry, '/odom', self.on_odom, qos)

        # --- state ---
        self.pose_xy: Tuple[float, float] = (0.0, 0.0)
        self.yaw: float = 0.0

        self.path: List[Tuple[float,float]] = []
        self.segment_lengths_m: List[float] = []   # per segment
        self.segment_lengths_ft: List[float] = []  # per segment (for visibility)
        self.seg_idx: int = 0                      # current segment index
        self.seg_remaining_m: float = 0.0          # remaining distance in current segment
        self.last_pose_for_seg: Tuple[float,float] = (0.0, 0.0)

        self.active = False
        self.hard_stop = False
        self.stop_at_end = True

        # accounting
        self.cable_remaining_m = INITIAL_CABLE_M
        self.percent_batt = 100
        self.seq_num = 0  # waypoints reached count

        # WS send queue: only push when a waypoint is reached or STOP hook
        self.status_queue: asyncio.Queue = asyncio.Queue(maxsize=128)

        # timers / tasks
        self.timer = self.create_timer(0.02, self.control_step)  # 50 Hz
        self.loop = asyncio.get_event_loop()
        self.loop.create_task(self.ws_sender_loop())        # sends from queue only
        self.loop.create_task(self.http_path_poller())
        self.loop.create_task(self.http_directions_poller())

        self.get_logger().info(
            f"Brain up. WS={BACKEND_WS_URI} PATH={HTTP_PATH_URL} DIR={HTTP_DIR_URL} "
            f"speed={self.max_lin:.3f} m/s (2 ft/s)"
        )

    # -------------------- HTTP pollers --------------------
    async def http_directions_poller(self):
        last_val = None
        async with aiohttp.ClientSession() as session:
            while rclpy.ok():
                try:
                    async with session.get(HTTP_DIR_URL, timeout=2.0) as resp:
                        if resp.status != 200:
                            await asyncio.sleep(0.5); continue
                        txt = (await resp.text()).strip().upper()
                except Exception:
                    await asyncio.sleep(0.5); continue

                if txt != last_val:
                    last_val = txt
                    if txt == "STOP":
                        self.hard_stop = True
                        self.active = False
                        self.pub_stop()
                        self.get_logger().warn("STOP received")

                        # 👉 NEW: emit one status immediately on STOP (isMoving=False)
                        payload = self.build_status_payload(is_moving_override=False)
                        try:
                            self.status_queue.put_nowait(payload)
                        except asyncio.QueueFull:
                            pass

                    elif txt == "START":
                        self.hard_stop = False
                        self.active = bool(self.path)
                        # When (re)starting a segment, reset seg progress anchor
                        self.last_pose_for_seg = self.pose_xy
                        self.get_logger().info("START received")
                    else:
                        self.get_logger().warn(f"Unknown /directions value: '{txt}'")
                await asyncio.sleep(0.5)

    async def http_path_poller(self):
        last_raw = None
        async with aiohttp.ClientSession() as session:
            while rclpy.ok():
                try:
                    async with session.get(HTTP_PATH_URL, timeout=2.0) as resp:
                        if resp.status != 200:
                            await asyncio.sleep(0.5); continue
                        raw = await resp.text()
                except Exception:
                    await asyncio.sleep(0.5); continue

                if raw and raw != last_raw:
                    last_raw = raw
                    try:
                        decoded = json.loads(raw)
                    except Exception as e:
                        self.get_logger().warn(f"/path parse error: {e}")
                        await asyncio.sleep(0.5); continue

                    points = decoded.get("points") if isinstance(decoded, dict) and "points" in decoded else decoded
                    units  = (decoded.get("units") if isinstance(decoded, dict) else None) or "m"

                    new_path: List[Tuple[float,float]] = []
                    if isinstance(points, list) and points:
                        for p in points:
                            if "r" in p and "c" in p:
                                x_m = float(p["c"]) * STEP_X_M
                                y_m = float(p["r"]) * STEP_Y_M
                                new_path.append((x_m, y_m))
                            elif "x" in p and "y" in p:
                                xv = float(p["x"]); yv = float(p["y"])
                                if str(units).lower().startswith("ft"):
                                    xv *= FT_TO_M; yv *= FT_TO_M
                                new_path.append((xv, yv))

                    if new_path and len(new_path) >= 1:
                        self.install_new_path(new_path)
                        self.get_logger().info(
                            f"/path loaded: {len(new_path)} waypoints, "
                            f"{len(self.segment_lengths_ft)} segments"
                        )
                await asyncio.sleep(0.5)

    def install_new_path(self, pts_m: List[Tuple[float,float]]):
        self.path = pts_m[:]  # copy
        # compute per-segment distances
        self.segment_lengths_m = []
        self.segment_lengths_ft = []
        for i in range(len(self.path)-1):
            Lm = dist_m(self.path[i], self.path[i+1])
            self.segment_lengths_m.append(Lm)
            self.segment_lengths_ft.append(Lm * M_TO_FT)
        self.seg_idx = 0
        self.seg_remaining_m = self.segment_lengths_m[0] if self.segment_lengths_m else 0.0
        self.last_pose_for_seg = self.pose_xy
        self.seq_num = 0
        if not self.hard_stop:
            self.active = True

    # -------------------- WS sender (only on waypoint reached or STOP hook) --------------------
    async def ws_sender_loop(self):
        while rclpy.ok():
            try:
                async with websockets.connect(
                    BACKEND_WS_URI, ping_interval=20, ping_timeout=10, max_size=2**22
                ) as ws:
                    self.get_logger().info("✅ WS connected (status-on-waypoint / STOP)")
                    await ws.send(json.dumps({"type":"hello","role":"brain"}))
                    while rclpy.ok():
                        payload = await self.status_queue.get()  # waits for event
                        try:
                            await ws.send(json.dumps(payload))
                        except Exception:
                            break
            except Exception as e:
                self.get_logger().warn(f"WS disconnected: {e}. Retrying in 2s...")
                await asyncio.sleep(2.0)

    def build_status_payload(self, is_moving_override: Optional[bool] = None) -> dict:
        x, y = self.pose_xy
        # Next heading target (next point) if available
        heading_str = ""
        if self.path:
            heading_str = f"{self.path[0][0]:.3f},{self.path[0][1]:.3f}"

        is_moving = bool(self.active and not self.hard_stop)
        if is_moving_override is not None:
            is_moving = bool(is_moving_override)

        return {
            "X_ECI": x,                       # meters
            "Y_ECI": y,                       # meters
            "Z_ECI": 0.0,                     # always 0
            "Vx_ECI": 2.0,                    # ft/s (per spec)
            "Vy_ECI": 2.0,                    # ft/s
            "Vz_ECI": 0.0,                    # ft/s
            "Heading": heading_str,           # "x,y" of next point
            "cableRemaining_m": self.cable_remaining_m,
            "percentBatteryRemaining": self.percent_batt,
            "errorCode": 0,
            "cableDispenseStatus": True,
            "cableDispenseCommand": True,
            "SequenceNum": str(self.seq_num), # waypoint index reached (string)
            "isMoving": is_moving,
        }

    # -------------------- ROS callbacks & control --------------------
    def on_odom(self, msg: Odometry):
        self.pose_xy = (msg.pose.pose.position.x, msg.pose.pose.position.y)
        self.yaw = yaw_from_quat(msg.pose.pose.orientation)

        # cable usage ~ distance moved since last segment anchor
        x, y = self.pose_xy
        lx, ly = self.last_pose_for_seg
        self.cable_remaining_m = max(0.0, self.cable_remaining_m - math.hypot(x-lx, y-ly))

    def control_step(self):
        # Honor STOP
        if self.hard_stop:
            self.pub_stop()
            return

        if not self.active or len(self.path) <= 1:
            # No movement if <2 points
            self.pub_stop()
            return

        x, y = self.pose_xy
        th = self.yaw

        # --- Segment progress accounting (distance-traveled based) ---
        dx = x - self.last_pose_for_seg[0]
        dy = y - self.last_pose_for_seg[1]
        dstep = math.hypot(dx, dy)
        if dstep > 0.0:
            self.seg_remaining_m = max(0.0, self.seg_remaining_m - dstep)
            self.last_pose_for_seg = (x, y)

        # If current segment is done -> "waypoint reached"
        while self.seg_idx < len(self.segment_lengths_m) and self.seg_remaining_m <= REACH_EPS_M:
            # reached next waypoint (path[1] at this moment)
            if len(self.path) > 1:
                self.path.pop(0)
            self.seq_num += 1
            self.percent_batt = max(0, self.percent_batt - BATTERY_DROP_PER_WAYPOINT)

            # enqueue status NOW (only on waypoint reached)
            try:
                self.status_queue.put_nowait(self.build_status_payload())
            except asyncio.QueueFull:
                pass

            self.seg_idx += 1
            if self.seg_idx < len(self.segment_lengths_m):
                self.seg_remaining_m = self.segment_lengths_m[self.seg_idx]
                self.last_pose_for_seg = (x, y)
            else:
                # Arrived at final waypoint
                self.active = False
                self.pub_stop()
                return

        # --- Pure-pursuit control toward current target ---
        # choose a target at >= lookahead along remaining path
        target = None
        for px, py in self.path:
            if (px - x)**2 + (py - y)**2 >= self.lookahead**2:
                target = (px, py); break
        if target is None:
            target = self.path[-1]

        tx, ty = target
        dx = tx - x; dy = ty - y
        ct, st = math.cos(-th), math.sin(-th)
        rx = dx*ct - dy*st
        ry = dx*st + dy*ct

        Ld = max(self.lookahead, 1e-3)
        kappa = 2.0 * ry / (Ld * Ld)
        v = self.max_lin
        w = max(-self.max_ang, min(self.max_ang, kappa * v))

        cmd = Twist()
        cmd.linear.x = v
        cmd.angular.z = w
        self.pub_cmd.publish(cmd)

    def pub_stop(self):
        self.pub_cmd.publish(Twist())

# -------------------- entry point --------------------
def main():
    rclpy.init()
    node = PathFollower()
    loop = asyncio.get_event_loop()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, loop.stop)
        except NotImplementedError:
            pass

    try:
        executor = rclpy.executors.SingleThreadedExecutor()
        def spin_once():
            executor.spin_once(timeout_sec=0.01)
        loop.call_soon(spin_once)
        while True:
            loop.run_until_complete(asyncio.sleep(0.01))
            spin_once()
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
