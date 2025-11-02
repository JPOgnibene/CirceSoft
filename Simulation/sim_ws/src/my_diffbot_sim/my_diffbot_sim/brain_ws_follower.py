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
STEP_X_M = 7.5 * FT_TO_M         # grid step in X (ft) -> meters
STEP_Y_M = 5.16129 * FT_TO_M     # grid step in Y (ft) -> meters
TARGET_SPEED_MPS = 2.0 * FT_TO_M # 2 ft/s

# -------------------- Backend endpoints (updated to match your app) --------------------
HTTP_DIR_URL    = "http://localhost:8765/directions"   # GET returns "START"/"STOP" or {"directions": "..."}
HTTP_PATH_URL   = "http://localhost:8765/grid/path"    # GET returns {"data":[{r,c},...]} (or other shapes)
HTTP_STATUS_URL = "http://localhost:8765/current-values"  # PUT status JSON

# -------------------- Model params --------------------
INITIAL_CABLE_M = 50.0
BATTERY_DROP_PER_WAYPOINT = 1  # percent per waypoint
REACH_EPS_M = 0.05             # how close is "reached"

def yaw_from_quat(q):
    siny_cosp = 2.0*(q.w*q.z + q.x*q.y)
    cosy_cosp = 1.0 - 2.0*(q.y*q.y + q.z*q.z)
    return math.atan2(siny_cosp, cosy_cosp)

def dist_m(a: Tuple[float,float], b: Tuple[float,float]) -> float:
    dx, dy = b[0]-a[0], b[1]-a[1]
    return math.hypot(dx, dy)

class PathFollower(Node):
    """
    - Polls /grid/path for waypoints (grid r,c to meters via STEP_X/Y)
    - Polls /directions for START/STOP (text or JSON)
    - Drives at 2 ft/s; emits PUT /current-values on each waypoint and on STOP
    """
    def __init__(self):
        super().__init__('brain_ws_follower')

        # controller params
        self.lookahead = 1.0
        self.max_lin   = TARGET_SPEED_MPS
        self.max_ang   = 1.5

        # ROS wiring
        qos = QoSProfile(depth=10)
        qos.reliability = ReliabilityPolicy.RELIABLE
        qos.history = HistoryPolicy.KEEP_LAST
        self.pub_cmd = self.create_publisher(Twist, '/cmd_vel', 10)
        self.sub_odom = self.create_subscription(Odometry, '/odom', self.on_odom, qos)

        # state
        self.pose_xy: Tuple[float,float] = (0.0, 0.0)
        self.yaw = 0.0
        self.path: List[Tuple[float,float]] = []
        self.segment_lengths_m: List[float] = []
        self.seg_idx = 0
        self.seg_remaining_m = 0.0
        self.last_pose_for_seg = (0.0, 0.0)

        self.active = False
        self.hard_stop = False
        self.cable_remaining_m = INITIAL_CABLE_M
        self.percent_batt = 100
        self.seq_num = 0

        # async infra
        self.loop = asyncio.get_event_loop()
        self.session = aiohttp.ClientSession()
        self.loop.create_task(self.http_path_poller())
        self.loop.create_task(self.http_directions_poller())

        # control loop
        self.timer = self.create_timer(0.02, self.control_step)  # 50 Hz

        self.get_logger().info(
            f"Brain ready | DIR={HTTP_DIR_URL} PATH={HTTP_PATH_URL} STATUS={HTTP_STATUS_URL} "
            f"| speed={self.max_lin:.3f} m/s (2 ft/s)"
        )

    # -------------------- HTTP pollers --------------------
    async def http_directions_poller(self):
        """Accept plain text or JSON {directions:'START'|'STOP'}."""
        last_val = None
        while rclpy.ok():
            try:
                async with self.session.get(HTTP_DIR_URL, timeout=2.0) as resp:
                    if resp.status != 200:
                        await asyncio.sleep(0.5); continue
                    # Try JSON first
                    try:
                        j = await resp.json()
                        txt = str(j.get("directions", "")).strip().upper()
                    except Exception:
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
                    await self.put_status(is_moving_override=False)

                elif txt == "START":
                    self.hard_stop = False
                    self.active = bool(self.path)
                    self.last_pose_for_seg = self.pose_xy
                    self.get_logger().info("START received")

                else:
                    # Ignore unknown values but keep polling
                    self.get_logger().warn(f"/directions unrecognized: '{txt}'")
            await asyncio.sleep(0.5)

    async def http_path_poller(self):
        """
        Accepts:
          - {"data":[...]}  (your backend)
          - {"points":[...]}
          - [...]           (raw list)
        Points may be {r,c} (grid) or {x,y} meters/feet (feet not used here).
        """
        last_raw = None
        while rclpy.ok():
            try:
                async with self.session.get(HTTP_PATH_URL, timeout=2.0) as resp:
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
                    self.get_logger().warn(f"/grid/path parse error: {e}")
                    await asyncio.sleep(0.5); continue

                # Normalize possible shapes
                points = None
                if isinstance(decoded, dict):
                    points = decoded.get("data") or decoded.get("points")
                if points is None:
                    points = decoded

                new_path: List[Tuple[float,float]] = []
                if isinstance(points, list) and points:
                    for p in points:
                        if isinstance(p, dict) and "r" in p and "c" in p:
                            x_m = float(p["c"]) * STEP_X_M
                            y_m = float(p["r"]) * STEP_Y_M
                            new_path.append((x_m, y_m))
                        elif isinstance(p, dict) and "x" in p and "y" in p:
                            # Assume meters if provided (feet not used in your backend right now)
                            new_path.append((float(p["x"]), float(p["y"])))

                if new_path:
                    self.install_new_path(new_path)
                    self.get_logger().info(f"/grid/path loaded: {len(new_path)} waypoints")
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

    # -------------------- Status --------------------
    async def put_status(self, is_moving_override: Optional[bool] = None):
        payload = self.build_status_payload(is_moving_override)
        try:
            async with self.session.put(HTTP_STATUS_URL, json=payload, timeout=3.0) as resp:
                if resp.status != 200:
                    self.get_logger().warn(f"PUT /current-values failed ({resp.status})")
        except Exception as e:
            self.get_logger().warn(f"PUT /current-values error: {e}")

    def build_status_payload(self, is_moving_override: Optional[bool] = None) -> dict:
        x, y = self.pose_xy
        heading = f"{self.path[0][0]:.3f},{self.path[0][1]:.3f}" if self.path else ""
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
            "Heading": heading,
            "cableRemaining_m": self.cable_remaining_m,
            "percentBatteryRemaining": self.percent_batt,
            "errorCode": 0,
            "cableDispenseStatus": True,
            "cableDispenseCommand": True,
            "SequenceNum": str(self.seq_num),
            "isMoving": is_moving,
        }

    # -------------------- ROS callbacks & control --------------------
    def on_odom(self, msg: Odometry):
        self.pose_xy = (msg.pose.pose.position.x, msg.pose.pose.position.y)
        self.yaw = yaw_from_quat(msg.pose.pose.orientation)
        # cable usage approximated by motion since last anchor
        x, y = self.pose_xy
        lx, ly = self.last_pose_for_seg
        self.cable_remaining_m = max(0.0, self.cable_remaining_m - math.hypot(x-lx, y-ly))

    def control_step(self):
        if self.hard_stop:
            self.pub_stop(); return
        if not self.active or len(self.path) <= 1:
            self.pub_stop(); return

        x, y = self.pose_xy
        th = self.yaw

        # segment progress by distance traveled
        dx = x - self.last_pose_for_seg[0]
        dy = y - self.last_pose_for_seg[1]
        dstep = math.hypot(dx, dy)
        if dstep > 0.0:
            self.seg_remaining_m = max(0.0, self.seg_remaining_m - dstep)
            self.last_pose_for_seg = (x, y)

        # reached waypoint?
        while self.seg_idx < len(self.segment_lengths_m) and self.seg_remaining_m <= REACH_EPS_M:
            if len(self.path) > 1:
                self.path.pop(0)
            self.seq_num += 1
            self.percent_batt = max(0, self.percent_batt - BATTERY_DROP_PER_WAYPOINT)
            asyncio.ensure_future(self.put_status())  # fire-and-forget

            self.seg_idx += 1
            if self.seg_idx < len(self.segment_lengths_m):
                self.seg_remaining_m = self.segment_lengths_m[self.seg_idx]
                self.last_pose_for_seg = (x, y)
            else:
                self.active = False
                self.pub_stop()
                return

        # pure pursuit to current target
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

# -------------------- entry --------------------
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
