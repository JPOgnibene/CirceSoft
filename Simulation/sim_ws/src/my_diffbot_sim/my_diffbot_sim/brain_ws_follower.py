#!/usr/bin/env python3
import asyncio, json, math, signal
from typing import List, Tuple, Optional

import aiohttp
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry

# -------------------- Units / constants --------------------
FT_TO_M = 0.3048
M_TO_FT = 1.0 / FT_TO_M

STEP_X_M = 7.5 * FT_TO_M        # 2.286 m per grid step in +X
STEP_Y_M = 5.16129 * FT_TO_M    # 1.573 m per grid step in +Y
TARGET_SPEED_MPS = 2.0 * FT_TO_M  # 2 ft/s = 0.6096 m/s

# Endpoints
HTTP_PATH_URL     = "http://localhost:8000/path"           # Waypoints
HTTP_DIR_URL      = "http://localhost:8765/directions"     # "START"/"STOP"
HTTP_STATUS_URL   = "http://localhost:8765/current-values" # JSON status PUT

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
    - PUTs JSON status to /current-values when:
        • waypoint reached
        • STOP received
    """

    def __init__(self):
        super().__init__('brain_ws_follower')

        self.lookahead = 1.0
        self.max_lin   = TARGET_SPEED_MPS
        self.max_ang   = 1.5

        qos = QoSProfile(depth=10)
        qos.reliability = ReliabilityPolicy.RELIABLE
        qos.history = HistoryPolicy.KEEP_LAST

        self.pub_cmd = self.create_publisher(Twist, '/cmd_vel', 10)
        self.sub_odom = self.create_subscription(Odometry, '/odom', self.on_odom, qos)

        self.pose_xy: Tuple[float,float] = (0.0, 0.0)
        self.yaw = 0.0
        self.path: List[Tuple[float,float]] = []
        self.segment_lengths_m: List[float] = []
        self.seg_idx = 0
        self.seg_remaining_m = 0.0
        self.last_pose_for_seg = (0.0, 0.0)

        self.active = False
        self.hard_stop = False
        self.stop_at_end = True

        self.cable_remaining_m = INITIAL_CABLE_M
        self.percent_batt = 100
        self.seq_num = 0

        self.loop = asyncio.get_event_loop()
        self.loop.create_task(self.http_path_poller())
        self.loop.create_task(self.http_directions_poller())

        self.session = aiohttp.ClientSession()

        self.timer = self.create_timer(0.02, self.control_step)  # 50 Hz

        self.get_logger().info(
            f"Brain initialized. speed={self.max_lin:.3f} m/s (2 ft/s)"
        )

    # -------------------- HTTP Pollers --------------------
    async def http_directions_poller(self):
        """Poll /directions for START/STOP commands."""
        last_val = None
        while rclpy.ok():
            try:
                async with self.session.get(HTTP_DIR_URL, timeout=2.0) as resp:
                    if resp.status != 200:
                        await asyncio.sleep(0.5)
                        continue
                    txt = (await resp.text()).strip().upper()
            except Exception:
                await asyncio.sleep(0.5)
                continue

            if txt != last_val:
                last_val = txt
                if txt == "STOP":
                    self.hard_stop = True
                    self.active = False
                    self.pub_stop()
                    self.get_logger().warn("STOP received")
                    # PUT status immediately on STOP
                    await self.put_status(is_moving_override=False)

                elif txt == "START":
                    self.hard_stop = False
                    self.active = bool(self.path)
                    self.last_pose_for_seg = self.pose_xy
                    self.get_logger().info("START received")

                else:
                    self.get_logger().warn(f"Unknown /directions value: '{txt}'")

            await asyncio.sleep(0.5)

    async def http_path_poller(self):
        """Poll /path for waypoint list."""
        last_raw = None
        while rclpy.ok():
            try:
                async with self.session.get(HTTP_PATH_URL, timeout=2.0) as resp:
                    if resp.status != 200:
                        await asyncio.sleep(0.5)
                        continue
                    raw = await resp.text()
            except Exception:
                await asyncio.sleep(0.5)
                continue

            if raw and raw != last_raw:
                last_raw = raw
                try:
                    decoded = json.loads(raw)
                except Exception as e:
                    self.get_logger().warn(f"/path parse error: {e}")
                    await asyncio.sleep(0.5)
                    continue

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
                        f"/path loaded: {len(new_path)} waypoints."
                    )

            await asyncio.sleep(0.5)

    def install_new_path(self, pts_m: List[Tuple[float,float]]):
        self.path = pts_m[:]
        self.segment_lengths_m = [dist_m(pts_m[i], pts_m[i+1]) for i in range(len(pts_m)-1)]
        self.seg_idx = 0
        self.seg_remaining_m = self.segment_lengths_m[0] if self.segment_lengths_m else 0.0
        self.last_pose_for_seg = self.pose_xy
        self.seq_num = 0
        if not self.hard_stop:
            self.active = True

    # -------------------- Status Reporting --------------------
    async def put_status(self, is_moving_override: Optional[bool] = None):
        """HTTP PUT to /current-values."""
        payload = self.build_status_payload(is_moving_override)
        try:
            async with self.session.put(HTTP_STATUS_URL, json=payload, timeout=3.0) as resp:
                if resp.status != 200:
                    self.get_logger().warn(f"PUT /current-values failed ({resp.status})")
        except Exception as e:
            self.get_logger().warn(f"PUT /current-values error: {e}")

    def build_status_payload(self, is_moving_override: Optional[bool] = None) -> dict:
        x, y = self.pose_xy
        heading_str = ""
        if self.path:
            heading_str = f"{self.path[0][0]:.3f},{self.path[0][1]:.3f}"

        is_moving = bool(self.active and not self.hard_stop)
        if is_moving_override is not None:
            is_moving = bool(is_moving_override)

        return {
            "X_ECI": x,
            "Y_ECI": y,
            "Z_ECI": 0.0,
            "Vx_ECI": 2.0,
            "Vy_ECI": 2.0,
            "Vz_ECI": 0.0,
            "Heading": heading_str,
            "cableRemaining_m": self.cable_remaining_m,
            "percentBatteryRemaining": self.percent_batt,
            "errorCode": 0,
            "cableDispenseStatus": True,
            "cableDispenseCommand": True,
            "SequenceNum": str(self.seq_num),
            "isMoving": is_moving,
        }

    # -------------------- ROS Callbacks & Control --------------------
    def on_odom(self, msg: Odometry):
        self.pose_xy = (msg.pose.pose.position.x, msg.pose.pose.position.y)
        self.yaw = yaw_from_quat(msg.pose.pose.orientation)

        x, y = self.pose_xy
        lx, ly = self.last_pose_for_seg
        self.cable_remaining_m = max(0.0, self.cable_remaining_m - math.hypot(x-lx, y-ly))

    def control_step(self):
        if self.hard_stop:
            self.pub_stop()
            return
        if not self.active or len(self.path) <= 1:
            self.pub_stop()
            return

        x, y = self.pose_xy
        th = self.yaw
        dx = x - self.last_pose_for_seg[0]
        dy = y - self.last_pose_for_seg[1]
        dstep = math.hypot(dx, dy)
        if dstep > 0.0:
            self.seg_remaining_m = max(0.0, self.seg_remaining_m - dstep)
            self.last_pose_for_seg = (x, y)

        # Waypoint reached check
        while self.seg_idx < len(self.segment_lengths_m) and self.seg_remaining_m <= REACH_EPS_M:
            if len(self.path) > 1:
                self.path.pop(0)
            self.seq_num += 1
            self.percent_batt = max(0, self.percent_batt - BATTERY_DROP_PER_WAYPOINT)
            asyncio.ensure_future(self.put_status())  # async fire-and-forget

            self.seg_idx += 1
            if self.seg_idx < len(self.segment_lengths_m):
                self.seg_remaining_m = self.segment_lengths_m[self.seg_idx]
                self.last_pose_for_seg = (x, y)
            else:
                self.active = False
                self.pub_stop()
                return

        # Pure pursuit
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

# -------------------- Entry point --------------------
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
        def spin_once(): executor.spin_once(timeout_sec=0.01)
        loop.call_soon(spin_once)
        while True:
            loop.run_until_complete(asyncio.sleep(0.01))
            spin_once()
    finally:
        loop.run_until_complete(node.session.close())
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
