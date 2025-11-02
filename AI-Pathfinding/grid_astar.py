#!/usr/bin/env python3
"""
grid_astar.py (headless, diagonals always enabled, watcher by default)

A* shortest path with:
- JSON inputs from API endpoints (no CSVs, no rendering):
    GET http://localhost:8000/obstacles  -> [{"row": r, "col": c}, ...]
    GET http://localhost:8000/waypoints  -> [{"row": r, "col": c, "type": "start|waypoint|end"}, ...]
- Required waypoint chain: start -> waypoint1 -> ... -> end
- Always uses 8-way (diagonal) movement for efficient routing
- One-cell safety buffer (inflation) around obstacles (not persisted)
- Cable-length limit, anisotropic step costs (ft): X=7.5, Y=5.16129, Diag=9.104334
- Posts computed path JSON to: POST http://localhost:8000/path
- Periodic watcher (default) polls endpoints and auto-recomputes on changes
- Cooldown after compute (default 2s) to avoid rapid re-runs
"""

import argparse, sys, time, hashlib, json
from typing import Dict, List, Optional, Set, Tuple
import requests

# -------------------------
# API endpoints
# -------------------------
OBSTACLES_URL = "http://localhost:8000/obstacles"
WAYPOINTS_URL = "http://localhost:8000/waypoints"
POST_PATH_URL = "http://localhost:8000/path"

# -------------------------
# Cable + per-step distances (feet)
# -------------------------
CABLE_MAX_FT = 300.0
COST_X = 7.5
COST_Y = 5.16129
COST_DIAG = 9.104334  # (±1,±1) steps

Coord = Tuple[int, int]  # (x=col, y=row)


# -------------------------
# Logging
# -------------------------
def log(msg: str) -> None:
    print(msg, flush=True)


# -------------------------
# Endpoint I/O
# -------------------------
def _xy_from_any(d: dict) -> Coord:
    if "col" in d and "row" in d:
        return (int(d["col"]), int(d["row"]))
    if "x" in d and "y" in d:
        return (int(d["x"]), int(d["y"]))
    raise ValueError(f"Point missing row/col (or x/y): {d}")


def get_obstacles() -> List[Coord]:
    r = requests.get(OBSTACLES_URL, timeout=5)
    r.raise_for_status()
    return [_xy_from_any(d) for d in r.json()]


def get_waypoints() -> List[Tuple[Coord, str]]:
    r = requests.get(WAYPOINTS_URL, timeout=5)
    r.raise_for_status()
    arr = r.json()
    out: List[Tuple[Coord, str]] = []
    for d in arr:
        xy = _xy_from_any(d)
        t = str(d.get("type", "waypoint")).lower()
        if t not in {"start", "waypoint", "end"}:
            t = "waypoint"
        out.append((xy, t))
    return out


def post_path_json(path: List[Coord], total_feet: float) -> None:
    payload = [{"col": x, "row": y, "x": x, "y": y} for (x, y) in path]
    cum = 0.0
    if len(path) > 1:
        payload[0]["cum_ft"] = 0.0
        for i in range(1, len(path)):
            cum += step_cost(path[i - 1], path[i])
            payload[i]["cum_ft"] = round(cum, 6)
    else:
        for p in payload:
            p["cum_ft"] = 0.0
    body = {"path": payload, "total_feet": round(total_feet, 6)}
    requests.post(POST_PATH_URL, json=body, timeout=5).raise_for_status()


# -------------------------
# Geometry / Costs
# -------------------------
def in_bounds(p: Coord, width: int, height: int) -> bool:
    x, y = p
    return 0 <= x < width and 0 <= y < height


def neighbors_8(x: int, y: int):
    return [
        (x - 1, y),
        (x + 1, y),
        (x, y - 1),
        (x, y + 1),
        (x - 1, y - 1),
        (x - 1, y + 1),
        (x + 1, y - 1),
        (x + 1, y + 1),
    ]


def weighted_octile(a: Coord, b: Coord) -> float:
    dx = abs(a[0] - b[0])
    dy = abs(a[1] - b[1])
    dmin, dmax = min(dx, dy), max(dx, dy)
    return COST_DIAG * dmin + (dmax - dmin) * (COST_X if dx > dy else COST_Y)


def step_cost(a: Coord, b: Coord) -> float:
    ax, ay = a
    bx, by = b
    if ax != bx and ay != by:
        return COST_DIAG
    if ax != bx:
        return COST_X
    return COST_Y


def path_length_feet(path: Optional[List[Coord]]) -> float:
    if not path or len(path) < 2:
        return 0.0 if path else float("inf")
    total = 0.0
    for u, v in zip(path, path[1:]):
        total += step_cost(u, v)
    return total


# -------------------------
# A*
# -------------------------
def reconstruct(came_from: Dict[Coord, Coord], current: Coord) -> List[Coord]:
    path = [current]
    while current in came_from:
        current = came_from[current]
        path.append(current)
    path.reverse()
    return path


def astar(
    width: int,
    height: int,
    start: Coord,
    goal: Coord,
    blocked: Set[Coord],
    valid: Set[Coord],
    *,
    cable_limit_ft: float = CABLE_MAX_FT,
    g_offset: float = 0.0,
) -> Optional[List[Coord]]:
    """A* pathfinding with diagonal moves and cable budget constraint."""
    if start not in valid or goal not in valid:
        return None
    if start in blocked or goal in blocked:
        return None

    from heapq import heappush, heappop

    h = weighted_octile
    neigh = neighbors_8

    open_heap: List[Tuple[float, Coord]] = []
    heappush(open_heap, (g_offset + h(start, goal), start))
    g: Dict[Coord, float] = {start: g_offset}
    came_from: Dict[Coord, Coord] = {}
    closed: Set[Coord] = set()

    while open_heap:
        _, current = heappop(open_heap)
        if current in closed:
            continue
        if g[current] > cable_limit_ft:
            continue

        if current == goal and g[current] <= cable_limit_ft:
            return reconstruct(came_from, current)

        closed.add(current)

        cx, cy = current
        for nxt in neigh(cx, cy):
            if not in_bounds(nxt, width, height):
                continue
            if nxt not in valid or nxt in blocked:
                continue

            tentative = g[current] + step_cost(current, nxt)
            if tentative > cable_limit_ft:
                continue
            if tentative < g.get(nxt, float("inf")):
                g[nxt] = tentative
                came_from[nxt] = current
                f = tentative + h(nxt, goal)
                heappush(open_heap, (f, nxt))
    return None


# -------------------------
# Safety buffer
# -------------------------
def inflate_obstacles(blocked: Set[Coord], valid: Set[Coord], width: int, height: int, radius: int = 1) -> Set[Coord]:
    if radius <= 0:
        return set(blocked)
    inflated = set(blocked)
    for (ox, oy) in list(blocked):
        for dx in range(-radius, radius + 1):
            for dy in range(-radius, radius + 1):
                nx, ny = ox + dx, oy + dy
                if 0 <= nx < width and 0 <= ny < height and (nx, ny) in valid:
                    inflated.add((nx, ny))
    return inflated


# -------------------------
# Core compute logic
# -------------------------
def compute_and_post(args) -> int:
    try:
        obstacles_list = get_obstacles()
        waypoints_raw = get_waypoints()
    except Exception as e:
        log(f"[error] Failed to load JSON from endpoints: {e}")
        return 2

    starts = [xy for (xy, t) in waypoints_raw if t == "start"]
    ends = [xy for (xy, t) in waypoints_raw if t == "end"]
    mids = [xy for (xy, t) in waypoints_raw if t == "waypoint"]

    if not starts or not ends:
        log("[error] Waypoints must include at least one 'start' and one 'end'.")
        return 2
    if len(starts) > 1 or len(ends) > 1:
        log("[warn] Multiple starts/ends provided; using the first of each.")

    start = starts[0]
    goal = ends[0]
    ordered_pts: List[Coord] = [start] + mids + [goal]

    xs = [x for (x, y) in obstacles_list] + [x for (x, y) in ordered_pts]
    ys = [y for (x, y) in obstacles_list] + [y for (x, y) in ordered_pts]
    if not xs or not ys:
        log("[error] No points to define grid extents.")
        return 2
    width, height = max(xs) + 1, max(ys) + 1
    valid: Set[Coord] = {(x, y) for y in range(height) for x in range(width)}

    base_blocked = set(obstacles_list) & valid
    inflated_blocked = inflate_obstacles(base_blocked, valid, width, height, radius=1)

    total_path: List[Coord] = []
    used_feet = 0.0
    ok = True

    for i in range(len(ordered_pts) - 1):
        a = ordered_pts[i]
        b = ordered_pts[i + 1]
        splice = len(total_path) > 0
        seg = astar(width, height, a, b, inflated_blocked, valid, cable_limit_ft=args.cable_ft, g_offset=used_feet)
        if seg is None:
            log(f"No path found between {a} -> {b} within cable limit {args.cable_ft:.3f} ft.")
            ok = False
            break
        seg_len = path_length_feet(seg)
        used_feet = seg_len
        total_path.extend(seg[1:] if splice else seg)

    if not ok:
        return 1

    total_feet = path_length_feet(total_path)
    log(f"[ok] Path length: {total_feet:.3f} ft (limit {args.cable_ft:.3f} ft) | nodes: {len(total_path)} | waypoints: {len(ordered_pts)}")
    try:
        post_path_json(total_path, total_feet)
        log("[info] Path posted to /path")
    except Exception as e:
        log(f"[warn] Failed to POST path to {POST_PATH_URL}: {e}")
        return 1

    return 0


# -------------------------
# Watcher (with debounce + cooldown)
# -------------------------
def _stable_hash_json(obj) -> str:
    def _normalize(o):
        if isinstance(o, dict):
            return {k: _normalize(o[k]) for k in sorted(o.keys())}
        if isinstance(o, list):
            return [_normalize(x) for x in o]
        return o

    norm = _normalize(obj)
    s = json.dumps(norm, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def _fetch_raw():
    return (
        requests.get(OBSTACLES_URL, timeout=5).json(),
        requests.get(WAYPOINTS_URL, timeout=5).json(),
    )


def run_watcher(args) -> None:
    log(f"[watch] Starting watcher: interval={args.interval:.3f}s, debounce={args.debounce_ms}ms, cooldown={args.cooldown:.3f}s")
    last_obs_hash = last_wp_hash = None
    last_rc = None
    debounce_deadline = 0.0
    last_compute_end_ts = 0.0

    while True:
        t0 = time.time()
        try:
            obs_raw, wp_raw = _fetch_raw()
            h_obs = _stable_hash_json(obs_raw)
            h_wp = _stable_hash_json(wp_raw)
            changed = (h_obs != last_obs_hash) or (h_wp != last_wp_hash)

            if changed:
                debounce_deadline = max(debounce_deadline, t0) + (args.debounce_ms / 1000.0)
                last_obs_hash, last_wp_hash = h_obs, h_wp
                log("[watch] Change detected. Debouncing...")

            now = time.time()
            cooldown_ok = (now - last_compute_end_ts) >= args.cooldown
            if last_obs_hash and last_wp_hash and now >= debounce_deadline and cooldown_ok:
                rc = compute_and_post(args)
                last_compute_end_ts = time.time()
                if rc != last_rc:
                    status = "OK" if rc == 0 else f"ERR({rc})"
                    log(f"[watch] Recompute status: {status}")
                last_rc = rc
                debounce_deadline = float("inf")

        except KeyboardInterrupt:
            log("[watch] Stopped by user.")
            break
        except Exception as e:
            log(f"[watch] Poll error: {e}")

        dt = time.time() - t0
        time.sleep(max(0.0, args.interval - dt))


# -------------------------
# CLI
# -------------------------
def main(argv: List[str]) -> int:
    ap = argparse.ArgumentParser(description="A* with JSON endpoints + waypoints + cable limit + watcher (headless, diagonals always enabled).")
    ap.add_argument("--cable-ft", type=float, default=CABLE_MAX_FT, help="Cable length budget in feet.")
    ap.add_argument("--once", action="store_true", help="Run a single compute and exit (disables watcher).")
    ap.add_argument("--interval", type=float, default=2.0, help="Polling interval in seconds (default 2.0).")
    ap.add_argument("--debounce-ms", type=int, default=150, help="Debounce window in milliseconds (default 150).")
    ap.add_argument("--cooldown", type=float, default=2.0, help="Cooldown after compute in seconds (default 2.0).")
    args = ap.parse_args(argv)

    if args.once:
        return compute_and_post(args)
    run_watcher(args)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
