#!/usr/bin/env python3
import asyncio, json, math, signal
from typing import List, Tuple
import websockets

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy


# --- Helper to convert quaternion to yaw ---
def yaw_from_quat(q):
    siny_cosp = 2.0*(q.w*q.z + q.x*q.y)
    cosy_cosp = 1.0 - 2.0*(q.y*q.y + q.z*q.z)
    return math.atan2(siny_cosp, cosy_cosp)


class PathFollower(Node):
    """
    Connects to a backend WebSocket server (hardcoded: ws://localhost:8765/ws),
    receives 'path' or 'stop' JSON messages, and drives a differential robot in Gazebo.
    Sends status back to the backend at ~5Hz.
    """

    def __init__(self):
        super().__init__('brain_ws_follower')

        # --- Hardcoded backend address ---
        self.backend_ws = "ws://localhost:8765/ws"

        # --- Control tuning ---
        self.lookahead = 1.0
        self.max_lin = 0.6
        self.max_ang = 1.5

        # --- ROS pub/sub ---
        qos = QoSProfile(depth=10)
        qos.reliability = ReliabilityPolicy.RELIABLE
        qos.history = HistoryPolicy.KEEP_LAST

        self.pub_cmd = self.create_publisher(Twist, '/cmd_vel', 10)
        self.sub_odom = self.create_subscription(Odometry, '/odom', self.on_odom, qos)

        # --- State ---
        self.pose_xy: Tuple[float, float] = (0.0, 0.0)
        self.yaw = 0.0
        self.path: List[Tuple[float, float]] = []
        self.active = False
        self.hard_stop = False
        self.stop_at_end = True

        # --- Control timer (50Hz) ---
        self.timer = self.create_timer(0.02, self.control_step)

        # --- Start WebSocket client ---
        self.loop = asyncio.get_event_loop()
        self.loop.create_task(self.client_loop())
        self.get_logger().info(f"Attempting WS connection to {self.backend_ws} ...")

    # ---------------------------------------------------------
    #   WebSocket Client Loop
    # ---------------------------------------------------------
    async def client_loop(self):
        """Maintain connection to backend and exchange messages."""
        while rclpy.ok():
            try:
                async with websockets.connect(self.backend_ws, ping_interval=20, ping_timeout=10) as ws:
                    self.get_logger().info("✅ WebSocket connection established with backend")
                    await ws.send(json.dumps({"type": "hello", "role": "brain"}))

                    last_status = 0.0
                    while rclpy.ok():
                        # --- Receive commands (non-blocking) ---
                        try:
                            raw = await asyncio.wait_for(ws.recv(), timeout=0.05)
                            await self.handle_incoming(raw, ws)
                        except asyncio.TimeoutError:
                            pass

                        # --- Send robot status every 0.2s (5Hz) ---
                        now = self.get_clock().now().nanoseconds / 1e9
                        if now - last_status > 0.2:
                            await self.send_status(ws)
                            last_status = now

                        await asyncio.sleep(0.01)
            except Exception as e:
                self.get_logger().warn(f"⚠️  WS connection lost: {e}. Retrying in 2s...")
                await asyncio.sleep(2.0)

    async def handle_incoming(self, raw, ws):
        try:
            data = json.loads(raw if isinstance(raw, str) else raw.decode('utf-8'))
        except Exception as e:
            self.get_logger().warn(f"Bad JSON from backend: {e}")
            return

        msg_type = data.get("type", "")
        if msg_type == "path":
            pts = data.get("points", [])
            if not isinstance(pts, list) or not pts:
                await ws.send(json.dumps({"ok": False, "err": "empty points"}))
                return
            try:
                self.path = [(float(p["x"]), float(p["y"])) for p in pts]
            except Exception as e:
                await ws.send(json.dumps({"ok": False, "err": f"bad points: {e}"}))
                return
            self.stop_at_end = bool(data.get("stop_at_end", True))
            self.active = True
            self.hard_stop = False
            self.get_logger().info(f"📍 New path received with {len(self.path)} points")
            await ws.send(json.dumps({"ok": True, "status": "path accepted"}))

        elif msg_type == "stop":
            self.hard_stop = True
            self.active = False
            self.path = []
            self.pub_stop()
            self.get_logger().warn("⛔ STOP command received")
            await ws.send(json.dumps({"ok": True, "status": "stopped"}))

    async def send_status(self, ws):
        x, y = self.pose_xy
        msg = {"type": "status", "x": x, "y": y, "yaw": self.yaw,
               "isMoving": self.active and not self.hard_stop}
        try:
            await ws.send(json.dumps(msg))
        except Exception as e:
            self.get_logger().warn(f"Status send failed: {e}")

    # ---------------------------------------------------------
    #   ROS Callbacks & Controller
    # ---------------------------------------------------------
    def on_odom(self, msg: Odometry):
        self.pose_xy = (msg.pose.pose.position.x, msg.pose.pose.position.y)
        self.yaw = yaw_from_quat(msg.pose.pose.orientation)

    def control_step(self):
        if self.hard_stop:
            self.pub_stop()
            return
        if not self.active or not self.path:
            self.pub_stop()
            return

        x, y = self.pose_xy
        th = self.yaw

        # Drop waypoints already passed
        while self.path:
            dx, dy = self.path[0][0] - x, self.path[0][1] - y
            if (dx*dx + dy*dy) < (self.lookahead*0.5)**2 and len(self.path) > 1:
                self.path.pop(0)
            else:
                break

        # Pick target at lookahead distance
        target = None
        for px, py in self.path:
            if (px - x)**2 + (py - y)**2 >= self.lookahead**2:
                target = (px, py)
                break
        if target is None:
            target = self.path[-1]

        tx, ty = target
        dx, dy = tx - x, ty - y
        ct, st = math.cos(-th), math.sin(-th)
        rx = dx*ct - dy*st
        ry = dx*st + dy*ct

        Ld = max(self.lookahead, 1e-3)
        kappa = 2.0 * ry / (Ld*Ld)
        v = self.max_lin
        w = max(-self.max_ang, min(self.max_ang, kappa * v))

        # Stop if close to goal
        fdx, fdy = self.path[-1][0] - x, self.path[-1][1] - y
        if (fdx*fdx + fdy*fdy) < (0.25**2) and self.stop_at_end:
            self.active = False
            self.path = []
            self.pub_stop()
            self.get_logger().info("🏁 Reached end of path")
            return

        cmd = Twist()
        cmd.linear.x = v
        cmd.angular.z = w
        self.pub_cmd.publish(cmd)

    def pub_stop(self):
        self.pub_cmd.publish(Twist())


# ---------------------------------------------------------
#   Main entry point
# ---------------------------------------------------------
def main():
    rclpy.init()
    node = PathFollower()
    loop = asyncio.get_event_loop()

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, loop.stop)

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
