#!/usr/bin/env python3
"""
Grid A* pathfinder with labeled waypoints + obstacle watching + cable limit + robust length.

Reads:
  GET http://localhost:8765/waypoints        -> {"data":[{"r":..,"c":..,"label":"START|WAYPOINT|END"}, ...]}
  GET http://localhost:8765/grid/obstacles   -> list OR {"data":[{r,c}|{x,y}, ...]}

Writes:
  PUT http://localhost:8765/grid/path        -> bare JSON list: [{"r":int,"c":int}, ...]

Rules:
  - Exactly one START and one END are required.
  - WAYPOINTs (if any) are visited in the order provided.
  - 8-directional movement (diagonals allowed).
  - Costs are in feet with custom scales (X/Y/Diag).
  - If total path length > MAX_CABLE_FT, print "NO VIABLE PATH" and do not publish.

Watcher:
  - Polls endpoints, hashes responses, and recomputes on any change (debounce + cooldown).
"""

from __future__ import annotations
import asyncio
import json
import math
import hashlib
import time
from typing import Dict, Iterable, List, Optional, Tuple

import aiohttp

# ----------------- Endpoints -----------------
WAYPOINTS_URL = "http://localhost:8765/waypoints"
OBSTACLES_URL = "http://localhost:8765/grid/obstacles"
PATH_PUT_URL  = "http://localhost:8765/grid/path"

# ----------------- Movement scales (feet) -----------------
X_SCALE      = 7.5         # horizontal (Δc) per cell
Y_SCALE      = 5.16129     # vertical (Δr) per cell
DIAG_SCALE   = 9.104334    # diagonal (±1,±1) per cell
MAX_CABLE_FT = 300.0

# ----------------- Watcher tunables -----------------
POLL_INTERVAL_SEC = 2.0
DEBOUNCE_MS       = 150
COOLDOWN_SEC      = 2.0

# ----------------- Helpers -----------------
def _unwrap_data(obj):
    return obj["data"] if isinstance(obj, dict) and "data" in obj else obj

def _pt_from_rc_or_xy(p) -> Tuple[int, int]:
    if not isinstance(p, dict):
        raise ValueError(f"Point not a dict: {p}")
    if "r" in p and "c" in p:
        return int(p["r"]), int(p["c"])
    if "x" in p and "y" in p:
        return int(p["y"]), int(p["x"])
    raise ValueError(f"Point missing row/col (or x/y): {p}")

def _hash_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

# ----------------- Feet-aware distance & validation -----------------
def step_feet_adjacent(a: Tuple[int,int], b: Tuple[int,int]) -> float:
    """Feet between adjacent grid cells a->b (|Δr|,|Δc| ≤ 1)."""
    ar, ac = a; br, bc = b
    dr = br - ar; dc = bc - ac
    if dr == 0 and dc == 0:
        return 0.0
    if dr != 0 and dc != 0:
        return DIAG_SCALE
    if dr != 0:
        return Y_SCALE
    return X_SCALE

def segment_length_feet(a: Tuple[int,int], b: Tuple[int,int]) -> float:
    """Feet between any two grid cells a->b (adjacent or not)."""
    ar, ac = a; br, bc = b
    dr = abs(br - ar)
    dc = abs(bc - ac)
    if dr == 0 and dc == 0:
        return 0.0
    d = min(dr, dc)                 # number of diagonal steps
    rem_r = dr - d                  # remaining vertical steps
    rem_c = dc - d                  # remaining horizontal steps
    return d * DIAG_SCALE + rem_r * Y_SCALE + rem_c * X_SCALE

def polyline_feet(path: List[Tuple[int,int]]) -> float:
    """Sum segment lengths (in feet) across the whole polyline."""
    total = 0.0
    for i in range(len(path) - 1):
        total += segment_length_feet(path[i], path[i+1])
    return total

def validate_adjacency(path: List[Tuple[int,int]]) -> None:
    """Warn if any consecutive points are not 8-connected (Δr>1 or Δc>1)."""
    bad = []
    for i in range(len(path) - 1):
        r0, c0 = path[i]
        r1, c1 = path[i+1]
        if abs(r1 - r0) > 1 or abs(c1 - c0) > 1:
            bad.append((i, (r0, c0), (r1, c1)))
    if bad:
        print(f"[warn] path contains {len(bad)} non-adjacent step(s):")
        for i, a, b in bad[:10]:
            print(f"       step {i}: {a} -> {b} (Δr={abs(b[0]-a[0])}, Δc={abs(b[1]-a[1])})")

# ----------------- Heuristic (admissible lower bound in feet) -----------------
def h_feet(a: Tuple[int,int], b: Tuple[int,int]) -> float:
    """Lower-bound heuristic in feet for 8-dir grid with these asymmetric costs."""
    dx = abs(a[1]-b[1])
    dy = abs(a[0]-b[0])
    d  = min(dx, dy)
    rem = max(dx, dy) - d
    # cheapest diagonal cannot exceed DIAG or X+Y combo
    diag_cost = min(DIAG_SCALE, X_SCALE + Y_SCALE)
    straight_cost = min(X_SCALE, Y_SCALE)
    return d * diag_cost + rem * straight_cost

# ----------------- A* (feet costs) -----------------
def neighbors_8(r: int, c: int):
    for dr, dc in [(-1,0),(1,0),(0,-1),(0,1),(-1,-1),(-1,1),(1,-1),(1,1)]:
        yield r+dr, c+dc

def astar_feet(bounds: Tuple[int,int,int,int],
               start: Tuple[int,int],
               goal: Tuple[int,int],
               obstacles: set[Tuple[int,int]]) -> Optional[List[Tuple[int,int]]]:
    """A* where g-costs are in feet using scales above; heuristic h_feet is admissible."""
    rmin, rmax, cmin, cmax = bounds
    def inb(r,c): return rmin <= r <= rmax and cmin <= c <= cmax

    import heapq
    openh = []
    heapq.heappush(openh, (0.0, start))
    g: Dict[Tuple[int,int], float] = {start: 0.0}
    came: Dict[Tuple[int,int], Tuple[int,int]] = {}

    while openh:
        _, cur = heapq.heappop(openh)
        if cur == goal:
            path = [cur]
            while cur in came:
                cur = came[cur]
                path.append(cur)
            path.reverse()
            return path

        cr, cc = cur
        for nr, nc in neighbors_8(cr, cc):
            if not inb(nr, nc): continue
            if (nr, nc) in obstacles: continue
            cost = step_feet_adjacent((cr,cc), (nr,nc))
            tentative = g[cur] + cost
            if tentative < g.get((nr,nc), float("inf")):
                g[(nr,nc)] = tentative
                came[(nr,nc)] = cur
                f = tentative + h_feet((nr,nc), goal)
                heapq.heappush(openh, (f, (nr,nc)))
    return None

# ----------------- Parsing inputs -----------------
def classify_waypoints(items: List[dict]) -> Tuple[Tuple[int,int], List[Tuple[int,int]], Tuple[int,int]]:
    start = None
    end = None
    mids: List[Tuple[int,int]] = []
    for p in items:
        r, c = _pt_from_rc_or_xy(p)
        label = str(p.get("label","")).strip().upper()
        if label == "START":
            if start is not None:
                raise ValueError("Multiple START labels found.")
            start = (r, c)
        elif label == "END":
            if end is not None:
                raise ValueError("Multiple END labels found.")
            end = (r, c)
        elif label == "WAYPOINT" or label == "":
            mids.append((r, c))
        else:
            # Unknown label -> treat like a required waypoint (back-compat).
            mids.append((r, c))
    if start is None:
        raise ValueError("Missing START labeled waypoint.")
    if end is None:
        raise ValueError("Missing END labeled waypoint.")
    return start, mids, end

def infer_bounds(points: Iterable[Tuple[int,int]], pad: int = 5) -> Tuple[int,int,int,int]:
    rs = [r for r,_ in points]
    cs = [c for _,c in points]
    return min(rs)-pad, max(rs)+pad, min(cs)-pad, max(cs)+pad

# ----------------- Composite path through waypoints -----------------
def compute_path_through_waypoints(start: Tuple[int,int],
                                   mids: List[Tuple[int,int]],
                                   end: Tuple[int,int],
                                   obstacles: set[Tuple[int,int]]) -> List[Tuple[int,int]]:
    all_pts = [start] + mids + [end]
    bounds = infer_bounds(list(obstacles) + all_pts, pad=5)
    full: List[Tuple[int,int]] = []
    cur = start
    for idx, nxt in enumerate(mids + [end], 1):
        seg = astar_feet(bounds, cur, nxt, obstacles)
        if seg is None:
            raise RuntimeError(f"No segment path between {cur} and {nxt} (leg {idx}).")
        # concatenate (avoid duplicating junction)
        if full:
            full.extend(seg[1:])
        else:
            full.extend(seg)
        cur = nxt
    return full

# ----------------- IO -----------------
async def fetch_json(session: aiohttp.ClientSession, url: str):
    async with session.get(url) as r:
        r.raise_for_status()
        try:
            return await r.json()
        except Exception:
            return json.loads(await r.text())

async def put_path(session: aiohttp.ClientSession, path_rc: List[Tuple[int,int]]):
    # Backend expects a bare list of points
    points = [{"r": int(r), "c": int(c)} for (r,c) in path_rc]
    async with session.put(PATH_PUT_URL, json=points) as r:
        body = await r.text()
        ok = 200 <= r.status < 300
        stamp = time.strftime("%Y-%m-%d %H:%M:%S")
        if ok:
            print(f"[{stamp}] [ok] PUT /grid/path with {len(points)} points.")
        else:
            print(f"[{stamp}] [err] PUT /grid/path -> {r.status}; {body[:300]}")

# ----------------- Watcher loop -----------------
class WatchState:
    def __init__(self):
        self.hw = None   # hash of waypoints JSON
        self.ho = None   # hash of obstacles JSON
        self.cool_until = 0.0

async def load_inputs(session: aiohttp.ClientSession):
    # Waypoints (labeled)
    w_raw = await fetch_json(session, WAYPOINTS_URL)
    w_list = _unwrap_data(w_raw)
    if not isinstance(w_list, list):
        raise ValueError("Waypoints endpoint must return a list (or {data:[...]}).")
    start, mids, end = classify_waypoints(w_list)

    # Obstacles
    o_raw = await fetch_json(session, OBSTACLES_URL)
    o_list = _unwrap_data(o_raw)
    if not isinstance(o_list, list):
        raise ValueError("Obstacles endpoint must return a list (or {data:[...]}).")
    obstacles = set(_pt_from_rc_or_xy(p) for p in o_list)

    # Hashes for change detection
    w_json = json.dumps(w_list, sort_keys=True)
    o_json = json.dumps(o_list, sort_keys=True)
    return start, mids, end, obstacles, _hash_text(w_json), _hash_text(o_json)

async def recompute_once(session: aiohttp.ClientSession):
    start, mids, end, obstacles, _, _ = await load_inputs(session)
    path = compute_path_through_waypoints(start, mids, end, obstacles)
    validate_adjacency(path)
    total_ft = polyline_feet(path)
    print(f"[info] path length: {total_ft:.3f} ft")
    if total_ft > MAX_CABLE_FT:
        print("NO VIABLE PATH")
        return
    await put_path(session, path)

async def watch_loop():
    st = WatchState()
    print(f"[watch] Start: poll={POLL_INTERVAL_SEC:.3f}s, debounce={DEBOUNCE_MS}ms, cooldown={COOLDOWN_SEC:.3f}s")
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
        # Initial compute
        try:
            await recompute_once(session)
            _, _, _, _, st.hw, st.ho = await load_inputs(session)
        except Exception as e:
            print(f"[error] Initial compute failed: {e}")

        while True:
            await asyncio.sleep(POLL_INTERVAL_SEC)
            try:
                # Debounce
                await asyncio.sleep(DEBOUNCE_MS / 1000.0)

                start, mids, end, obstacles, hw, ho = await load_inputs(session)
                changed = (hw != st.hw) or (ho != st.ho)
                if not changed:
                    continue

                print("[watch] Change detected.")
                now = time.time()
                if now < st.cool_until:
                    print(f"[watch] Cooling down until {st.cool_until:.3f} (now={now:.3f})")
                    continue

                try:
                    path = compute_path_through_waypoints(start, mids, end, obstacles)
                    validate_adjacency(path)
                    total_ft = polyline_feet(path)
                    print(f"[info] path length: {total_ft:.3f} ft")
                    if total_ft > MAX_CABLE_FT:
                        print("NO VIABLE PATH")
                    else:
                        await put_path(session, path)
                        st.hw, st.ho = hw, ho
                        st.cool_until = time.time() + COOLDOWN_SEC
                except Exception as e:
                    print(f"[error] Recompute failed: {e}")

            except Exception as e:
                print(f"[error] Watch iteration: {e}")

def main():
    try:
        asyncio.run(watch_loop())
    except KeyboardInterrupt:
        print("\n[shutdown] bye!")

if __name__ == "__main__":
    main()
