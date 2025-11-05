#!/usr/bin/env python3
"""
CirceBot Simulator — path-change detection + verbose status logging.

- Reads /grid/path once; only reloads if endpoint content changes (hash-checked)
- START/STOP from /directions
- Moves 2 ft/s using custom axis/diagonal scales
- PUTs to /current-values on waypoint arrival
- Prints the full JSON payload on every PUT
- Tracks cable (max 300 ft), distanceTraveled_ft, distanceRemaining_ft, battery (-1% per waypoint)
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
SPEED_FTPS   = 2.0        # ft/s
POLL_DT      = 0.5        # s
# feet-per-step scales
X_SCALE      = 7.5
Y_SCALE      = 5.16129
DIAG_SCALE   = 9.104334

# Cable
CABLE_MAX_FT = 300.0
FT_TO_M      = 0.3048
CABLE_MAX_M  = CABLE_MAX_FT * FT_TO_M

def iso_now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")

def step_length_feet(a, b):
    """
    Feet distance from grid point a->{r,c} to b->{r,c}.
    Supports fractional r,c: decomposes into diagonal + straight components
    under provided scales.
    """
    dr = abs(b["r"] - a["r"])
    dc = abs(b["c"] - a["c"])
    if dr == 0.0 and dc == 0.0:
        return 0.0
    diag = min(dr, dc)
    rem_r = dr - diag
    rem_c = dc - diag
    return diag * DIAG_SCALE + rem_r * Y_SCALE + rem_c * X_SCALE

def grid_to_xy_feet(r, c):
    """Map report coordinates in feet for status JSON."""
    return {"x": c * X_SCALE, "y": r * Y_SCALE}

class Simulator:
    def __init__(self):
        self.path: list[dict] = []        # [{"r":float,"c":float}, ...]
        self.curr = {"r": 0.0, "c": 0.0}  # fractional between waypoints is ok
        self.next_idx = 0
        self.running = False
        self.percent_batt = 100
        self.cable_remaining_m = CABLE_MAX_M
        self.distance_traveled_ft = 0.0

        # Path change detection
        self._last_path_hash: str | None = None

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
        """
        Fetch /grid/path and only update self.path if the raw response changed.
        Uses SHA-256 of the response text for quick comparison.
        """
        try:
            async with session.get(HTTP_PATH_URL) as r:
                r.raise_for_status()
                raw = await r.text()
        except Exception as e:
            print(f"[{iso_now()}] path fetch failed: {e}")
            return  # keep existing path

        new_hash = hashlib.sha256(raw.encode("utf-8")).hexdigest()
        if new_hash == self._last_path_hash:
            # No change — do nothing
            return

        # Changed: parse and load
        try:
            obj = json.loads(raw)
            pts = obj.get("data", [])
            new_path = [{"r": float(p["r"]), "c": float(p["c"])} for p in pts if "r" in p and "c" in p]
            if not isinstance(new_path, list):
                raise ValueError("parsed path not a list")
        except Exception as e:
            print(f"[{iso_now()}] path parse failed: {e}")
            return

        self.path = new_path
        self._last_path_hash = new_hash
        if self.next_idx >= len(self.path):
            self.next_idx = 0
        print(f"[{iso_now()}] Loaded path with {len(self.path)} waypoints (changed).")

    # ---------- Distances ----------
    def distance_remaining_ft(self) -> float:
        """Feet from current position to end of path along our scaled metric."""
        if not self.path or self.next_idx >= len(self.path):
            return 0.0
        total = step_length_feet(self.curr, self.path[self.next_idx])
        for i in range(self.next_idx, len(self.path) - 1):
            total += step_length_feet(self.path[i], self.path[i + 1])
        return total

    # ---------- Status PUT ----------
    async def put_status(self, session, waypoint_number_1based: int | None, is_moving: bool):
        xy = grid_to_xy_feet(self.curr["r"], self.curr["c"])
        heading = "idle"
        if self.next_idx < len(self.path):
            nxt = self.path[self.next_idx]
            heading = f"to r={int(round(nxt['r']))}, c={int(round(nxt['c']))}"

        payload = {
            # Positions
            "X_ECI": xy["x"],                # X coordinate on the map (feet)
            "Y_ECI": xy["y"],                # Y coordinate on the map (feet)
            "Z_ECI": 0.0,                    # assume always 0
            # Velocities (always 2 ft/s per spec)
            "Vx_ECI": SPEED_FTPS,
            "Vy_ECI": SPEED_FTPS,
            "Vz_ECI": 0.0,
            # Heading: string naming the next point
            "Heading": heading,
            # Cable remaining (meters)
            "cableRemaining_m": max(self.cable_remaining_m, 0.0),
            # Battery
            "percentBatteryRemaining": max(self.percent_batt, 0),
            # Errors / flags
            "errorCode": 0,
            "cableDispenseStatus": True,
            "cableDispenseCommand": True,
            # Sequence as STRING (waypoint check-in number)
            "SequenceNum": "" if waypoint_number_1based is None else str(waypoint_number_1based),
            # Movement flag: True unless STOP read
            "isMoving": bool(is_moving),
            # Distance tracking (feet)
            "distanceTraveled_ft": round(self.distance_traveled_ft, 4),
            "distanceRemaining_ft": round(self.distance_remaining_ft(), 4),
        }

        # Print full status JSON every PUT
        print(f"[{iso_now()}] PUT /current-values payload:\n{json.dumps(payload, indent=2, sort_keys=True)}")

        async with session.put(HTTP_STATUS_URL, json=payload) as r:
            if not (200 <= r.status < 300):
                txt = await r.text()
                print(f"[{iso_now()}] PUT /current-values failed {r.status}: {txt}")

    # ---------- Core loop ----------
    async def run(self):
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
            # Initial path load (once)
            await self.load_path_if_changed(session)
            self.running = (await self.get_directions(session)) == "START"
            print(f"[{iso_now()}] Initial: {'START' if self.running else 'STOP'}")

            # Initial status (no waypoint number)
            await self.put_status(session, waypoint_number_1based=None, is_moving=self.running)

            while True:
                # Controls
                self.running = (await self.get_directions(session)) == "START"

                # Only update path if endpoint content changed
                await self.load_path_if_changed(session)

                if (not self.running) or (not self.path) or (self.next_idx >= len(self.path)):
                    await asyncio.sleep(POLL_DT)
                    continue

                target = self.path[self.next_idx]
                prev = dict(self.curr)

                # Feet to target, and feet we move this tick
                remaining_ft = step_length_feet(prev, target)
                step_ft = SPEED_FTPS * POLL_DT

                if remaining_ft <= 1e-9 or step_ft >= remaining_ft:
                    # arrive this tick
                    moved_ft = remaining_ft
                    self.curr = {"r": target["r"], "c": target["c"]}
                    self.distance_traveled_ft += moved_ft
                    self.cable_remaining_m = max(self.cable_remaining_m - moved_ft * FT_TO_M, 0.0)
                    # battery -1% per waypoint check-in
                    self.percent_batt = max(self.percent_batt - 1, 0)
                    # 1-based sequence number for this check-in
                    seq_num = self.next_idx + 1
                    self.next_idx += 1
                    await self.put_status(session, waypoint_number_1based=seq_num, is_moving=self.running)
                else:
                    # partial progress (proportional along r/c)
                    ratio = step_ft / remaining_ft
                    self.curr = {
                        "r": prev["r"] + (target["r"] - prev["r"]) * ratio,
                        "c": prev["c"] + (target["c"] - prev["c"]) * ratio,
                    }
                    moved_ft = step_ft
                    self.distance_traveled_ft += moved_ft
                    self.cable_remaining_m = max(self.cable_remaining_m - moved_ft * FT_TO_M, 0.0)
                    # (No mid-move PUT; enable if desired)

                await asyncio.sleep(POLL_DT)

# ------------------------- MAIN ----------------------------
if __name__ == "__main__":
    try:
        asyncio.run(Simulator().run())
    except KeyboardInterrupt:
        print("\n[shutdown] bye!")
