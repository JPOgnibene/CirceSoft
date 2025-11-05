#!/usr/bin/env python3
"""
HTTP-only simulator for your FastAPI backend.

• Reads path from /grid/path ({"data":[{"r":int,"c":int},...]}) or fallback /path ([{"x":float,"y":float},...])
• Waits for START from /directions (either {"directions":"START"} or plain "START")
• Moves at 2 ft/s and PUTs /current-values with the same shape your backend writes:
  {
    "X_ECI": float, "Y_ECI": float, "Z_ECI": 0,
    "Vx_ECI": 0, "Vy_ECI": 0, "Vz_ECI": 0,
    "Heading": 0,
    "cableRemaining_m": float,
    "percentBatteryRemaining": 100,
    "errorCode": 0,
    "cableDispenseStatus": 0,
    "cableDispenseCommand": 0,
    "SequenceNum": int,
    "isMoving": bool
  }

Quickstart:
  pip install aiohttp
  python sim_runner.py --base http://localhost:8765
"""

import argparse
import asyncio
import math
from datetime import datetime, timezone

import aiohttp

def iso_now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")

def hypot(a, b):
    return math.hypot(b["x"] - a["x"], b["y"] - a["y"])

def step_towards(curr, target, max_step):
    dx = target["x"] - curr["x"]
    dy = target["y"] - curr["y"]
    d = math.hypot(dx, dy)
    if d == 0 or d <= max_step:
      return {"x": target["x"], "y": target["y"]}
    s = max_step / d
    return {"x": curr["x"] + dx * s, "y": curr["y"] + dy * s}

class Sim:
    def __init__(self, base, speed_ftps=2.0, poll=0.5, reach_tol=0.5,
                 path_ep_grid="/grid/path", path_ep_legacy="/path",
                 directions_ep="/directions", current_values_ep="/current-values",
                 heartbeat=None, cells_to_feet=1.0):
        self.base = base.rstrip("/")
        self.urls = {
            "path_grid": self.base + path_ep_grid,
            "path_legacy": self.base + path_ep_legacy,
            "directions": self.base + directions_ep,
            "current_values": self.base + current_values_ep,
        }
        self.speed = float(speed_ftps)
        self.poll = float(poll)
        self.reach_tol = float(reach_tol)
        self.cells_to_feet = float(cells_to_feet)
        self.heartbeat = heartbeat

        self.path = []         # list of {"x":float,"y":float} in feet
        self.curr = {"x": 0.0, "y": 0.0}
        self.next_idx = 0
        self.running = False
        self.seq = 0
        self.cable_remaining_m = 50.0  # default from models.py INITIAL_LENGTH, meters-ish
        self._last_hb = 0.0

    # ---------- HTTP helpers ----------
    async def _get_json(self, session, url):
        async with session.get(url) as r:
            r.raise_for_status()
            return await r.json()

    async def _get_text(self, session, url):
        async with session.get(url) as r:
            r.raise_for_status()
            return await r.text()

    async def _put_json(self, session, url, payload):
        async with session.put(url, json=payload) as r:
            if 200 <= r.status < 300:
                return True
            else:
                txt = await r.text()
                raise RuntimeError(f"PUT {url} failed {r.status}: {txt}")

    # ---------- Endpoint consumers ----------
    async def fetch_directions(self, session) -> str:
        """
        Accepts either:
          {"directions":"START"} or {"directions":"STOP"}
        or plain "START"/"STOP" (as a raw file string).
        Defaults to STOP on any parse error.
        """
        try:
            # Try JSON first
            data = await self._get_json(session, self.urls["directions"])
            if isinstance(data, dict) and "directions" in data:
                s = str(data["directions"]).strip().upper()
                return "START" if s == "START" else "STOP"
        except Exception:
            pass

        try:
            txt = (await self._get_text(session, self.urls["directions"])).strip().upper()
            return "START" if txt == "START" else "STOP"
        except Exception:
            return "STOP"

    def _coerce_path_grid(self, obj):
        """{"data":[{"r":int,"c":int},...]} -> [{"x":float,"y":float},...] in feet"""
        if not isinstance(obj, dict) or "data" not in obj or not isinstance(obj["data"], list):
            return None
        out = []
        for p in obj["data"]:
            if not isinstance(p, dict): continue
            if ("r" in p and "c" in p) or ("row" in p and "col" in p):
                r = float(p.get("r", p.get("row")))
                c = float(p.get("c", p.get("col")))
                # map grid (c,r) to (x,y). scale cells to feet by cells_to_feet.
                out.append({"x": c * self.cells_to_feet, "y": r * self.cells_to_feet})
        return out if out else None

    def _coerce_path_legacy(self, obj):
        """[{"x":float,"y":float},...] (feet) -> same"""
        if isinstance(obj, list) and obj and isinstance(obj[0], dict) and "x" in obj[0] and "y" in obj[0]:
            return [{"x": float(p["x"]), "y": float(p["y"])} for p in obj]
        return None

    async def fetch_path(self, session):
        """
        Prefer /grid/path format. Fallback to legacy /path.
        """
        # try grid path
        try:
            obj = await self._get_json(session, self.urls["path_grid"])
            pts = self._coerce_path_grid(obj)
            if pts:
                self.path = pts
                if self.next_idx >= len(self.path):
                    self.next_idx = 0
                return True
        except Exception:
            pass

        # try legacy path
        try:
            obj = await self._get_json(session, self.urls["path_legacy"])
            pts = self._coerce_path_legacy(obj)
            if pts:
                self.path = pts
                if self.next_idx >= len(self.path):
                    self.next_idx = 0
                return True
        except Exception:
            pass

        return False

    async def put_current_values(self, session, isMoving: bool):
        """
        Matches write_status_to_file(...) shape so your frontend sees familiar keys.
        We'll set X_ECI/Y_ECI from our feet position; everything else is stubbed.
        """
        self.seq += 1

        # crude cable usage: convert feet moved in this cycle to meters and decrement
        payload = {
            "X_ECI": self.curr["x"],
            "Y_ECI": self.curr["y"],
            "Z_ECI": 0.0,
            "Vx_ECI": 0.0,
            "Vy_ECI": 0.0,
            "Vz_ECI": 0.0,
            "Heading": 0.0,
            "cableRemaining_m": max(self.cable_remaining_m, 0.0),
            "percentBatteryRemaining": 100,
            "errorCode": 0,
            "cableDispenseStatus": 0,
            "cableDispenseCommand": 0,
            "SequenceNum": self.seq,
            "isMoving": bool(isMoving),
        }
        await self._put_json(session, self.urls["current_values"], payload)

    async def heartbeat(self, session):
        if not self.heartbeat:
            return
        await self.put_current_values(session, isMoving=self.running)

    # ---------- Main loop ----------
    async def run(self):
        dt = self.poll
        max_step = self.speed * dt

        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
            await self.fetch_path(session)  # initial try
            self.running = (await self.fetch_directions(session)) == "START"
            print(f"[{iso_now()}] Initial state: {'START' if self.running else 'STOP'}. Waypoints: {len(self.path)}")

            hb_accum = 0.0

            while True:
                # refresh directions & path
                self.running = (await self.fetch_directions(session)) == "START"
                await self.fetch_path(session)

                # heartbeat if enabled
                if self.heartbeat:
                    hb_accum += self.poll
                    if hb_accum >= self.heartbeat:
                        await self.heartbeat(session)
                        hb_accum = 0.0

                # nothing to do without a path
                if not self.path or self.next_idx >= len(self.path) or not self.running:
                    await asyncio.sleep(self.poll)
                    continue

                # move
                target = self.path[self.next_idx]
                before = dict(self.curr)
                self.curr = step_towards(self.curr, target, max_step)

                # cable remaining estimate (feet->meters)
                moved_ft = math.hypot(self.curr["x"] - before["x"], self.curr["y"] - before["y"])
                self.cable_remaining_m -= (moved_ft * 0.3048)

                # reached?
                if hypot(self.curr, target) <= self.reach_tol:
                    # snap & advance
                    self.curr = {"x": target["x"], "y": target["y"]}
                    idx = self.next_idx
                    self.next_idx += 1

                    # report waypoint-reached via current-values PUT
                    try:
                        await self.put_current_values(session, isMoving=False)
                        print(f"[{iso_now()}] Reached waypoint {idx} at {self.curr}. PUT /current-values OK.")
                    except Exception as e:
                        print(f"[{iso_now()}] PUT /current-values failed at wp {idx}: {e}")
                else:
                    # mid-leg heartbeat as “moving” (optional)
                    pass

                await asyncio.sleep(self.poll)

def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://localhost:8765", help="Server base URL")
    ap.add_argument("--speed", type=float, default=2.0, help="Speed ft/s")
    ap.add_argument("--poll", type=float, default=0.5, help="Poll dt in seconds")
    ap.add_argument("--tol",  type=float, default=0.5, help="Waypoint reach tolerance (ft)")
    ap.add_argument("--heartbeat", type=float, default=None, help="Optional PUT heartbeat interval (s)")
    ap.add_argument("--cells-to-feet", type=float, default=1.0, help="Scale grid cell to feet for /grid/path")
    return ap.parse_args()

async def amain():
    a = parse_args()
    sim = Sim(
        base=a.base,
        speed_ftps=a.speed,
        poll=a.poll,
        reach_tol=a.tol,
        heartbeat=a.heartbeat,
        cells_to_feet=a.cells_to_feet,
    )
    await sim.run()

if __name__ == "__main__":
    try:
        asyncio.run(amain())
    except KeyboardInterrupt:
        print("\n[shutdown] bye!")