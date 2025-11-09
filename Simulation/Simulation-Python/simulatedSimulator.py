#!/usr/bin/env python3
"""
CirceBot Simulator — waits for explicit START, reports cable in feet,
handles STOP/idle properly, and logs all PUT payloads.

Hard-coded endpoints:
  GET  /directions
  GET  /grid/path
  PUT  /current-values
"""

import asyncio
import math
import json
import hashlib
from datetime import datetime, timezone
import aiohttp

# ------------------------- ENDPOINTS -------------------------
HTTP_DIR_URL    = "http://localhost:8765/directions"
HTTP_PATH_URL   = "http://localhost:8765/grid/path"
HTTP_STATUS_URL = "http://localhost:8765/current-values"

# ------------------------- CONSTANTS -------------------------
SPEED_FTPS   = 2.0
POLL_DT      = 0.5
X_SCALE      = 7.5
Y_SCALE      = 5.16129
DIAG_SCALE   = 9.104334
CABLE_MAX_FT = 300.0

# -------------------------------------------------------------
def iso_now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")

def step_length_feet(a, b):
    """Feet distance from grid point a->{r,c} to b->{r,c} using axis scales."""
    dr = abs(b["r"] - a["r"])
    dc = abs(b["c"] - a["c"])
    if dr == 0.0 and dc == 0.0:
        return 0.0
    diag = min(dr, dc)
    rem_r = dr - diag
    rem_c = dc - diag
    return diag * DIAG_SCALE + rem_r * Y_SCALE + rem_c * X_SCALE

def grid_to_xy_feet(r, c):
    """Convert grid (r,c) to world coordinates (feet)."""
    return {"x": c * X_SCALE, "y": r * Y_SCALE}

# -------------------------------------------------------------
class Simulator:
    def __init__(self):
        self.path = []
        self.curr = {"r": 0.0, "c": 0.0}
        self.next_idx = 0
        self.running = False
        self.prev_running = False
        self.percent_batt = 100
        self.cable_remaining_ft = CABLE_MAX_FT
        self.distance_traveled_ft = 0.0
        self._last_path_hash = None

    # ---------- HTTP ----------
    async def get_directions(self, session) -> str:
        try:
            async with session.get(HTTP_DIR_URL) as r:
                r.raise_for_status()
                text = await r.text()
                if text.strip().startswith("{"):
                    data = await r.json()
                    return str(data.get("directions", "STOP")).strip().upper()
                return text.strip().upper()
        except Exception as e:
            print(f"[{iso_now()}] directions fetch failed: {e}")
            return "STOP"

    async def load_path_if_changed(self, session):
        """Reload path only if JSON content changed."""
        try:
            async with session.get(HTTP_PATH_URL) as r:
                r.raise_for_status()
                raw = await r.text()
        except Exception as e:
            print(f"[{iso_now()}] path fetch failed: {e}")
            return

        new_hash = hashlib.sha256(raw.encode("utf-8")).hexdigest()
        if new_hash == self._last_path_hash:
            return  # unchanged

        try:
            obj = json.loads(raw)
            pts = obj.get("data", [])
            new_path = [{"r": float(p["r"]), "c": float(p["c"])} for p in pts if "r" in p and "c" in p]
        except Exception as e:
            print(f"[{iso_now()}] path parse failed: {e}")
            return

        self.path = new_path
        self._last_path_hash = new_hash
        self.next_idx = 0
        print(f"[{iso_now()}] Loaded path with {len(self.path)} waypoints (changed).")

    # ---------- Distance ----------
    def distance_remaining_ft(self) -> float:
        """Feet from current position to the end of path."""
        if not self.path or self.next_idx >= len(self.path):
            return 0.0
        total = step_length_feet(self.curr, self.path[self.next_idx])
        for i in range(self.next_idx, len(self.path) - 1):
            total += step_length_feet(self.path[i], self.path[i + 1])
        return total

    # ---------- Status PUT ----------
    async def put_status(self, session, *, waypoint_number_1based: int | None, is_moving: bool):
        if not is_moving:
            heading = "stopped" if self.next_idx < len(self.path) else "idle"
        else:
            nxt = self.path[self.next_idx] if self.next_idx < len(self.path) else None
            heading = f"to r={int(round(nxt['r']))}, c={int(round(nxt['c']))}" if nxt else "idle"

        xy = grid_to_xy_feet(self.curr["r"], self.curr["c"])

        payload = {
            "X_ECI": xy["x"],
            "Y_ECI": xy["y"],
            "Z_ECI": 0.0,
            "Vx_ECI": SPEED_FTPS,
            "Vy_ECI": SPEED_FTPS,
            "Vz_ECI": 0.0,
            "Heading": heading,
            "cableRemaining_ft": round(max(self.cable_remaining_ft, 0.0), 4),
            "percentBatteryRemaining": max(self.percent_batt, 0),
            "errorCode": 0,
            "cableDispenseStatus": True,
            "cableDispenseCommand": True,
            "SequenceNum": "" if waypoint_number_1based is None else str(waypoint_number_1based),
            "isMoving": bool(is_moving),
            "distanceTraveled_ft": round(self.distance_traveled_ft, 4),
            "distanceRemaining_ft": round(self.distance_remaining_ft(), 4),
        }

        print(f"[{iso_now()}] PUT /current-values payload:\n{json.dumps(payload, indent=2, sort_keys=True)}")
        async with session.put(HTTP_STATUS_URL, json=payload) as r:
            if not (200 <= r.status < 300):
                txt = await r.text()
                print(f"[{iso_now()}] PUT /current-values failed {r.status}: {txt}")

    # ---------- Main loop ----------
    async def run(self):
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
            await self.load_path_if_changed(session)

            # Wait for explicit START before doing anything
            print(f"[{iso_now()}] Waiting for START command...")
            while True:
                state = (await self.get_directions(session)).upper()
                if state == "START":
                    self.running = True
                    self.prev_running = True
                    print(f"[{iso_now()}] START command received — beginning movement.")
                    break
                await asyncio.sleep(1)

            # Emit initial status
            await self.put_status(session, waypoint_number_1based=None, is_moving=self.running)

            while True:
                self.running = (await self.get_directions(session)) == "START"

                # Handle STOP events
                if self.prev_running and not self.running:
                    print(f"[{iso_now()}] STOP received — pausing movement.")
                    await self.put_status(session, waypoint_number_1based=None, is_moving=False)

                self.prev_running = self.running
                await self.load_path_if_changed(session)

                if not self.running or not self.path or self.next_idx >= len(self.path):
                    await asyncio.sleep(POLL_DT)
                    continue

                target = self.path[self.next_idx]
                prev = dict(self.curr)
                remaining_ft = step_length_feet(prev, target)
                step_ft = SPEED_FTPS * POLL_DT

                if remaining_ft <= 1e-9 or step_ft >= remaining_ft:
                    # Arrive at waypoint
                    moved_ft = remaining_ft
                    self.curr = {"r": target["r"], "c": target["c"]}
                    self.distance_traveled_ft += moved_ft
                    self.cable_remaining_ft = max(self.cable_remaining_ft - moved_ft, 0.0)
                    self.percent_batt = max(self.percent_batt - 1, 0)
                    seq_num = self.next_idx + 1
                    self.next_idx += 1
                    still_has_next = self.next_idx < len(self.path)
                    is_moving_now = self.running and still_has_next
                    await self.put_status(session, waypoint_number_1based=seq_num, is_moving=is_moving_now)
                    if not still_has_next:
                        print(f"[{iso_now()}] Route complete — no more waypoints.")
                else:
                    # Partial progress
                    ratio = step_ft / remaining_ft
                    self.curr = {
                        "r": prev["r"] + (target["r"] - prev["r"]) * ratio,
                        "c": prev["c"] + (target["c"] - prev["c"]) * ratio,
                    }
                    moved_ft = step_ft
                    self.distance_traveled_ft += moved_ft
                    self.cable_remaining_ft = max(self.cable_remaining_ft - moved_ft, 0.0)
                    # (Optional) mid-move PUT could go here

                await asyncio.sleep(POLL_DT)

# -------------------------------------------------------------
if __name__ == "__main__":
    try:
        asyncio.run(Simulator().run())
    except KeyboardInterrupt:
        print("\n[shutdown] bye!")
