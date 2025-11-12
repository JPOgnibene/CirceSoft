#!/usr/bin/env python3
"""
CirceBot Simulator (HTTP polling, aligned with planner; continuous distance math)

Endpoints:
  GET  http://localhost:8765/directions      -> "START"/"STOP" or {"directions"|"command": "..."}
  GET  http://localhost:8765/grid/path       -> bare list OR {"data":[{"r","c"}, ...]}
  PUT  http://localhost:8765/current-values  -> status JSON

Behavior:
  - Waits until it reads "START" from /directions AND a non-empty /grid/path is available.
  - Loads /grid/path only when the response changes (hash-checked).
  - On every new path: the bot is positioned ON path[0] and heads to path[1].
  - Moves 2 ft/s using custom scales: X=7.5 ft, Y=5.16129 ft, Diagonal=9.104334 ft.
  - Continuous feet math (no rounding current position) to avoid premature arrivals.
  - Tracks:
        cableRemaining_ft (starts 300 ft; decremented by actual feet moved),
        distanceTraveled_ft (cumulative),
        distanceRemaining_ft (same metric as planner, from current fractional position).
  - Battery drops 1% on each waypoint arrival.
  - Sends a full status JSON (PUT /current-values) on:
        • START heartbeat,
        • each waypoint arrival,
        • STOP command,
        • route completion.
"""

import asyncio
import json
import hashlib
from datetime import datetime, timezone
import aiohttp

# ------------------------- ENDPOINTS -------------------------
HTTP_DIR_URL    = "http://localhost:8765/directions"
HTTP_PATH_URL   = "http://localhost:8765/grid/path"
HTTP_STATUS_URL = "http://localhost:8765/current-values"

# ------------------------- CONSTANTS -------------------------
SPEED_FTPS   = 2.0              # movement speed (ft/s)
POLL_DT      = 0.5              # simulation tick (s)
X_SCALE      = 7.5              # ft per Δc
Y_SCALE      = 5.16129          # ft per Δr
DIAG_SCALE   = 9.104334         # ft per diagonal cell
CABLE_MAX_FT = 300.0
EPS_FT       = 1e-6             # small tolerance for arrival tests

# -------------------------------------------------------------
def iso_now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")

# ===== Shared distance math (continuous; no rounding) =====
def segment_length_feet(a: dict, b: dict) -> float:
    """
    Feet between ANY two points a->{r,c}, b->{r,c}.
    Works for fractional positions (continuous version of the diagonal+axis metric).
    """
    ar, ac = float(a["r"]), float(a["c"])
    br, bc = float(b["r"]), float(b["c"])
    dr = abs(br - ar)
    dc = abs(bc - ac)
    if dr == 0.0 and dc == 0.0:
        return 0.0
    d = min(dr, dc)                 # diagonal portion (can be fractional)
    rem_r = dr - d                  # remaining vertical portion
    rem_c = dc - d                  # remaining horizontal portion
    return d * DIAG_SCALE + rem_r * Y_SCALE + rem_c * X_SCALE

def polyline_feet(points: list[dict]) -> float:
    total = 0.0
    for i in range(len(points) - 1):
        total += segment_length_feet(points[i], points[i+1])
    return total

def grid_to_xy_feet(r, c):
    # (0,0) bottom-left; X along columns, Y along rows
    return {"x": c * X_SCALE, "y": r * Y_SCALE}

# -------------------------------------------------------------
class Simulator:
    def __init__(self):
        self.path: list[dict] = []           # [{"r":float,"c":float}, ...]
        self.curr = {"r": 0.0, "c": 0.0}     # fractional position between waypoints
        self.next_idx = 0                    # next waypoint index into self.path
        self.running = False                 # true iff /directions == "START"
        self.prev_running = False
        self.percent_batt = 100
        self.cable_remaining_ft = CABLE_MAX_FT
        self.distance_traveled_ft = 0.0
        self._last_path_hash: str | None = None

    # ---------- /directions ----------
    @staticmethod
    def _normalize_dir_value(val) -> str:
        if isinstance(val, str):
            return val.strip().upper()
        if isinstance(val, dict):
            if "directions" in val:
                return str(val["directions"]).strip().upper()
            if "command" in val:
                return str(val["command"]).strip().upper()
        return "STOP"

    async def get_directions(self, session) -> str:
        try:
            async with session.get(HTTP_DIR_URL) as r:
                r.raise_for_status()
                raw = await r.text()
                raw_s = raw.strip()
                if raw_s.startswith("{"):
                    try:
                        obj = json.loads(raw_s)
                        return self._normalize_dir_value(obj)
                    except Exception:
                        pass
                return self._normalize_dir_value(raw_s)
        except Exception as e:
            print(f"[{iso_now()}] directions fetch failed: {e}")
            return "STOP"

    # ---------- /grid/path ----------
    def _warn_non_adjacent(self):
        bad = []
        for i in range(len(self.path) - 1):
            r0, c0 = self.path[i]["r"], self.path[i]["c"]
            r1, c1 = self.path[i+1]["r"], self.path[i+1]["c"]
            if abs(r1 - r0) > 1 or abs(c1 - c0) > 1:
                bad.append((i, (r0, c0), (r1, c1)))
        if bad:
            print(f"[warn] path contains {len(bad)} non-adjacent step(s); sample: {bad[:3]}")

    async def load_path_if_changed(self, session):
        """Fetch /grid/path and, if changed, set path and place bot ON first point."""
        try:
            async with session.get(HTTP_PATH_URL) as r:
                r.raise_for_status()
                raw = await r.text()
        except Exception as e:
            print(f"[{iso_now()}] path fetch failed: {e}")
            return

        new_hash = hashlib.sha256(raw.encode("utf-8")).hexdigest()
        if new_hash == self._last_path_hash:
            return

        try:
            obj = json.loads(raw)
            pts = obj.get("data") if isinstance(obj, dict) else obj   # accept bare list or {"data":[...]}
            if not isinstance(pts, list):
                raise ValueError("grid/path must be a list of points or {data:[...]}")
            new_path = [{"r": float(p["r"]), "c": float(p["c"])} for p in pts if "r" in p and "c" in p]
        except Exception as e:
            print(f"[{iso_now()}] path parse failed: {e}")
            return

        self.path = new_path
        self._last_path_hash = new_hash

        if len(self.path) >= 1:
            # Start ON the first waypoint; head to the second (if any)
            self.curr = {"r": float(self.path[0]["r"]), "c": float(self.path[0]["c"])}
            self.next_idx = 1 if len(self.path) > 1 else 0
        else:
            self.curr = {"r": 0.0, "c": 0.0}
            self.next_idx = 0

        total_ft = polyline_feet(self.path) if len(self.path) >= 2 else 0.0
        print(f"[{iso_now()}] Loaded path with {len(self.path)} points; total length ≈ {total_ft:.3f} ft (sim).")
        self._warn_non_adjacent()

    # ---------- Distances ----------
    def distance_remaining_ft(self) -> float:
        """Feet from current position to end, using continuous metric."""
        if not self.path or self.next_idx >= len(self.path):
            return 0.0
        total = segment_length_feet(self.curr, self.path[self.next_idx])
        for i in range(self.next_idx, len(self.path) - 1):
            total += segment_length_feet(self.path[i], self.path[i+1])
        return total

    # ---------- Status PUT ----------
    async def put_status(self, session, *, waypoint_number_1based=None, is_moving=False, note=None):
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
            "cableRemaining": round(max(self.cable_remaining_ft, 0.0), 4),
            "percentBatteryRemaining": max(self.percent_batt, 0),
            "errorCode": 0,
            "cableDispenseStatus": True,
            "cableDispenseCommand": True,
            "SequenceNum": "" if waypoint_number_1based is None else str(waypoint_number_1based),
            "isMoving": bool(is_moving),
            "distanceTraveled": round(self.distance_traveled_ft, 4),
            "distanceRemaining": round(self.distance_remaining_ft(), 4),
        }
        if note:
            payload["debug_note"] = note

        print(f"[{iso_now()}] PUT /current-values payload:\n{json.dumps(payload, indent=2, sort_keys=True)}")
        async with session.put(HTTP_STATUS_URL, json=payload) as r:
            if not (200 <= r.status < 300):
                txt = await r.text()
                print(f"[{iso_now()}] PUT /current-values failed {r.status}: {txt}")

    # ---------- Main loop ----------
    async def run(self):
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
            # Preload path if present (sets curr to path[0] and next_idx accordingly)
            await self.load_path_if_changed(session)

            # Wait for explicit START and non-empty path
            print(f"[{iso_now()}] Waiting for START and a non-empty /grid/path...")
            while True:
                dir_value = (await self.get_directions(session)).upper()
                await self.load_path_if_changed(session)
                has_path = bool(self.path)
                if dir_value == "START" and has_path:
                    self.running = True
                    self.prev_running = True
                    first_target = self.path[self.next_idx] if self.next_idx < len(self.path) else None
                    if first_target:
                        print(f"[{iso_now()}] START received. First target: r={int(first_target['r'])}, c={int(first_target['c'])}")
                    else:
                        print(f"[{iso_now()}] START received but path has a single point.")
                    await self.put_status(session, waypoint_number_1based=None, is_moving=True, note="START received; beginning movement")
                    break
                elif dir_value == "START" and not has_path:
                    print(f"[{iso_now()}] START received, but path is empty — waiting for /grid/path ...")
                await asyncio.sleep(1.0)

            # Movement loop
            while True:
                # Controls
                self.running = (await self.get_directions(session)) == "START"

                # STOP edge -> immediate PUT with isMoving:false
                if self.prev_running and not self.running:
                    print(f"[{iso_now()}] STOP received — pausing movement.")
                    await self.put_status(session, waypoint_number_1based=None, is_moving=False, note="STOP received")

                self.prev_running = self.running

                # Only reload path if changed (won't teleport; starts on new path[0])
                await self.load_path_if_changed(session)

                # Idle if not running / no path / finished
                if not self.running or not self.path or self.next_idx >= len(self.path):
                    await asyncio.sleep(POLL_DT)
                    continue

                # Move toward next waypoint
                target = self.path[self.next_idx]
                prev = dict(self.curr)
                remaining_ft = segment_length_feet(prev, target)
                step_ft = SPEED_FTPS * POLL_DT

                if remaining_ft <= EPS_FT or step_ft >= remaining_ft - EPS_FT:
                    # Arrive at waypoint
                    moved_ft = max(0.0, remaining_ft)
                    self.curr = {"r": target["r"], "c": target["c"]}
                    self.distance_traveled_ft += moved_ft
                    self.cable_remaining_ft = max(self.cable_remaining_ft - moved_ft, 0.0)
                    self.percent_batt = max(self.percent_batt - 1, 0)

                    seq_num = self.next_idx + 1  # 1-based
                    self.next_idx += 1

                    still_has_next = self.next_idx < len(self.path)
                    is_moving_now = self.running and still_has_next

                    await self.put_status(
                        session,
                        waypoint_number_1based=seq_num,
                        is_moving=is_moving_now,
                        note=f"Reached waypoint {seq_num}"
                    )

                    if not still_has_next:
                        print(f"[{iso_now()}] Route complete — no more waypoints.")
                else:
                    # Partial progress along the metric-geodesic
                    ratio = step_ft / remaining_ft
                    self.curr = {
                        "r": prev["r"] + (target["r"] - prev["r"]) * ratio,
                        "c": prev["c"] + (target["c"] - prev["c"]) * ratio,
                    }
                    moved_ft = step_ft
                    self.distance_traveled_ft += moved_ft
                    self.cable_remaining_ft = max(self.cable_remaining_ft - moved_ft, 0.0)

                await asyncio.sleep(POLL_DT)

# -------------------------------------------------------------
if __name__ == "__main__":
    try:
        asyncio.run(Simulator().run())
    except KeyboardInterrupt:
        print("\n[shutdown] bye!")
