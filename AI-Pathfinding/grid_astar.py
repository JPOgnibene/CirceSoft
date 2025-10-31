#!/usr/bin/env python3
"""
grid_astar.py
A* shortest path with:
- JSON inputs from API endpoints (no CSVs):
    GET http://localhost:8000/obstacles  -> [{"row": r, "col": c}, ...]
    GET http://localhost:8000/waypoints  -> [{"row": r, "col": c, "type": "start|waypoint|end"}, ...]
- Required waypoint chain: start -> waypoint1 -> ... -> end (order preserved for 'waypoint' items)
- One-cell safety buffer (inflation) around obstacles (not persisted)
- Cable-length limit, anisotropic step costs (ft): X=7.5, Y=5.16129, Diag=9.104334
- ASCII/PNG rendering
- POST computed path back to: POST http://localhost:8000/path
- NEW: Periodic watcher (--watch) polls endpoints and auto-recomputes when data changes
"""

import argparse, math, sys, os, time, hashlib, json
from typing import Dict, List, Optional, Set, Tuple
import requests

# -------------------------
# API endpoints
# -------------------------
OBSTACLES_URL = "http://localhost:8000/obstacles"
WAYPOINTS_URL = "http://localhost:8000/waypoints"
POST_PATH_URL  = "http://localhost:8000/path"

# -------------------------
# Cable + per-step distances (feet)
# -------------------------
CABLE_MAX_FT = 300.0
COST_X = 7.5
COST_Y = 5.16129
COST_DIAG = 9.104334  # (±1,±1) steps

# -------------------------
# Optional PNG rendering
# -------------------------
try:
    import matplotlib.pyplot as plt
    import numpy as np
    from matplotlib.colors import ListedColormap
    import matplotlib.patches as mpatches
    _MATPLOTLIB_AVAILABLE = True
except Exception:
    _MATPLOTLIB_AVAILABLE = False

Coord = Tuple[int, int]  # (x=col, y=row)

# ------------------------- Logging -------------------------

def log(msg: str) -> None:
    print(msg, flush=True)

# ------------------------- Endpoint I/O -------------------------

def _xy_from_any(d: dict) -> Coord:
    if "col" in d and "row" in d:
        return (int(d["col"]), int(d["row"]))
    if "x" in d and "y" in d:
        return (int(d["x"]), int(d["y"]))
    raise ValueError(f"Point missing row/col (or x/y): {d}")

def get_obstacles() -> List[Coord]:
    r = requests.get(OBSTACLES_URL, timeout=5)
    r.raise_for_status()
    arr = r.json()
    return [_xy_from_any(d) for d in arr]

def get_waypoints() -> List[Tuple[Coord, str]]:
    r = requests.get(WAYPOINTS_URL, timeout=5)
    r.raise_for_status()
    arr = r.json()
    out: List[Tuple[Coord,str]] = []
    for d in arr:
        xy = _xy_from_any(d)
        t  = str(d.get("type","waypoint")).lower()
        if t not in {"start","waypoint","end"}:
            t = "waypoint"
        out.append((xy, t))
    return out

def post_path_json(path: List[Coord], total_feet: float) -> None:
    payload = [{"col": x, "row": y, "x": x, "y": y} for (x, y) in path]
    # Add cumulative feet convenience field
    cum = 0.0
    if len(path) > 1:
        payload[0]["cum_ft"] = 0.0
        for i in range(1, len(path)):
            cum += step_cost(path[i-1], path[i])
            payload[i]["cum_ft"] = round(cum, 6)
    else:
        for p in payload:
            p["cum_ft"] = 0.0
    body = {"path": payload, "total_feet": round(total_feet, 6)}
    r = requests.post(POST_PATH_URL, json=body, timeout=5)
    r.raise_for_status()

# ------------------------- Geometry / Costs -------------------------

def in_bounds(p: Coord, width: int, height: int) -> bool:
    x, y = p
    return 0 <= x < width and 0 <= y < height

def neighbors_4(x: int, y: int):
    return [(x-1,y), (x+1,y), (x,y-1), (x,y+1)]

def neighbors_8(x: int, y: int):
    return [(x-1,y), (x+1,y), (x,y-1), (x,y+1),
            (x-1,y-1), (x-1,y+1), (x+1,y-1), (x+1,y+1)]

def weighted_manhattan(a: Coord, b: Coord) -> float:
    dx = abs(a[0] - b[0]); dy = abs(a[1] - b[1])
    return COST_X * dx + COST_Y * dy

def weighted_octile(a: Coord, b: Coord) -> float:
    dx = abs(a[0] - b[0]); dy = abs(a[1] - b[1])
    dmin = min(dx, dy); dmax = max(dx, dy)
    return COST_DIAG * dmin + (dmax - dmin) * (COST_X if dx > dy else COST_Y)

def step_cost(a: Coord, b: Coord) -> float:
    ax, ay = a; bx, by = b
    if ax != bx and ay != by: return COST_DIAG
    if ax != bx: return COST_X
    return COST_Y

def path_length_feet(path: Optional[List[Coord]]) -> float:
    if not path or len(path) < 2: return 0.0 if path else float("inf")
    total = 0.0
    for u, v in zip(path, path[1:]): total += step_cost(u, v)
    return total

# ------------------------- A* -------------------------

def reconstruct(came_from: Dict[Coord, Coord], current: Coord) -> List[Coord]:
    path = [current]
    while current in came_from:
        current = came_from[current]
        path.append(current)
    path.reverse()
    return path

def astar(width: int, height: int, start: Coord, goal: Coord,
          blocked: Set[Coord], valid: Set[Coord],
          *, diagonal: bool=False, cable_limit_ft: float = CABLE_MAX_FT,
          g_offset: float = 0.0) -> Optional[List[Coord]]:
    if start not in valid or goal not in valid: return None
    if start in blocked or goal in blocked: return None

    from heapq import heappush, heappop
    neigh = neighbors_8 if diagonal else neighbors_4
    h = weighted_octile if diagonal else weighted_manhattan

    open_heap: List[Tuple[float, Coord]] = []
    heappush(open_heap, (g_offset + h(start, goal), start))
    g: Dict[Coord, float] = {start: g_offset}
    came_from: Dict[Coord, Coord] = {}
    closed: Set[Coord] = set()

    while open_heap:
        _, current = heappop(open_heap)
        if current in closed: continue
        if g[current] > cable_limit_ft: continue

        if current == goal:
            if g[current] <= cable_limit_ft:
                return reconstruct(came_from, current)
        closed.add(current)

        cx, cy = current
        for nxt in neigh(cx, cy):
            if not in_bounds(nxt, width, height): continue
            if nxt not in valid: continue
            if nxt in blocked: continue
            tentative = g[current] + step_cost(current, nxt)
            if tentative > cable_limit_ft: continue
            if tentative < g.get(nxt, float("inf")):
                g[nxt] = tentative
                came_from[nxt] = current
                f = tentative + h(nxt, goal)
                heappush(open_heap, (f, nxt))
    return None

# ------------------------- Safety buffer -------------------------

def inflate_obstacles(blocked: Set[Coord], valid: Set[Coord], width: int, height: int, radius: int = 1) -> Set[Coord]:
    if radius <= 0: return set(blocked)
    inflated = set(blocked)
    deltas = [(dx, dy) for dx in range(-radius, radius+1) for dy in range(-radius, radius+1)]
    for (ox, oy) in list(blocked):
        for dx, dy in deltas:
            nx, ny = ox + dx, oy + dy
            p = (nx, ny)
            if 0 <= nx < width and 0 <= ny < height and p in valid:
                inflated.add(p)
    return inflated

# ------------------------- Rendering -------------------------

def render_ascii(width: int, height: int, start: Coord, goal: Coord,
                 base_blocked: Set[Coord], valid: Set[Coord], path: Optional[List[Coord]],
                 *, ascii_safe: bool=False, outside_space: bool=False,
                 buffer: Optional[Set[Coord]] = None) -> str:
    buffer = buffer or set()
    dot_outside = ' ' if outside_space else '.'
    path_char = '*' if ascii_safe else '•'
    pathset = set(path or [])
    rows: List[str] = []
    for y in range(height):
        line = []
        for x in range(width):
            p = (x, y)
            if p not in valid:
                ch = dot_outside
            else:
                ch = '.'
                if p in base_blocked: ch = '#'
                elif p in buffer:     ch = '+'
                elif p in pathset:    ch = path_char
                if p == start: ch = 'S'
                if p == goal:  ch = 'G'
            line.append(ch)
        rows.append("".join(line))
    legend = f"Legend: S=start  G=end  #=obstacle  +=buffer  {path_char}=path  .=free   (grid {width}x{height})"
    return "\n".join(rows + [legend])

def render_png(outfile: str,
               width: int, height: int,
               start: Coord, goal: Coord,
               base_blocked: Set[Coord], valid: Set[Coord],
               path: Optional[List[Coord]],
               *, dpi: int=140, cell_size: int=16,
               show_grid: bool=False, show_legend: bool=True,
               buffer: Optional[Set[Coord]] = None) -> None:
    if not _MATPLOTLIB_AVAILABLE:
        raise RuntimeError("matplotlib not available. Install it to use --png-out.")
    buffer = buffer or set()

    img = np.zeros((height, width), dtype=np.uint8)
    for y in range(height):
        for x in range(width):
            img[y, x] = 1
    for (x, y) in base_blocked:
        if 0 <= x < width and 0 <= y < height: img[y, x] = 2
    for (x, y) in buffer:
        if 0 <= x < width and 0 <= y < height and img[y, x] != 2: img[y, x] = 3

    cmap = ListedColormap(["#d9d9d9", "#ffffff", "#000000", "#7f7f7f"])

    px_w, px_h = max(1, width*cell_size), max(1, height*cell_size)
    fig_w, fig_h = px_w/dpi, px_h/dpi
    fig, ax = plt.subplots(figsize=(fig_w, fig_h), dpi=dpi)
    ax.imshow(img, cmap=cmap, interpolation="nearest", origin="upper")
    ax.set_xlim(-0.5, width-0.5); ax.set_ylim(height-0.5, -0.5)

    if path and len(path) > 1:
        xs = [x for (x, _) in path]; ys = [y for (_, y) in path]
        ax.plot(xs, ys, linewidth=max(2, cell_size//5))

    ax.scatter([start[0]], [start[1]], marker='o', s=max(36, cell_size**2//4))
    ax.scatter([goal[0]],  [goal[1]],  marker='X', s=max(44, cell_size**2//3))

    if show_grid:
        for x in range(width+1): ax.axvline(x-0.5, linewidth=0.5)
        for y in range(height+1): ax.axhline(y-0.5, linewidth=0.5)

    if show_legend:
        bg   = mpatches.Patch(color="#d9d9d9", label="Outside Mask")
        free = mpatches.Patch(color="#ffffff", label="Free")
        obs  = mpatches.Patch(color="#000000", label="Obstacle")
        buf  = mpatches.Patch(color="#7f7f7f", label="Buffer")
        line = plt.Line2D([0], [0], lw=max(2, cell_size//5), label='Path')
        spt  = plt.Line2D([0], [0], marker='o', linestyle='None', label='Start', markersize=8)
        gpt  = plt.Line2D([0], [0], marker='X', linestyle='None', label='End', markersize=8)
        ax.legend(handles=[bg, free, obs, buf, line, spt, gpt], loc='lower right', framealpha=0.7)

    ax.set_aspect('equal'); ax.set_xticks([]); ax.set_yticks([])
    fig.tight_layout(pad=0); fig.savefig(outfile, bbox_inches="tight"); plt.close(fig)

# ------------------------- Planner core -------------------------

def compute_and_post(args) -> int:
    try:
        obstacles_list = get_obstacles()
        waypoints_raw  = get_waypoints()
    except Exception as e:
        log(f"[error] Failed to load JSON from endpoints: {e}")
        return 2

    starts   = [xy for (xy,t) in waypoints_raw if t == "start"]
    ends     = [xy for (xy,t) in waypoints_raw if t == "end"]
    mids     = [xy for (xy,t) in waypoints_raw if t == "waypoint"]

    if not starts or not ends:
        log("[error] Waypoints must include at least one 'start' and one 'end'.")
        return 2
    if len(starts) > 1 or len(ends) > 1:
        log("[warn] Multiple starts/ends provided; using the first of each.")

    start = starts[0]; goal = ends[0]
    ordered_pts: List[Coord] = [start] + mids + [goal]

    xs = [x for (x,y) in obstacles_list] + [x for (x,y) in ordered_pts]
    ys = [y for (x,y) in obstacles_list] + [y for (x,y) in ordered_pts]
    if not xs or not ys:
        log("[error] No points to define grid extents.")
        return 2
    width, height = max(xs) + 1, max(ys) + 1
    valid: Set[Coord] = {(x, y) for y in range(height) for x in range(width)}

    base_blocked: Set[Coord] = set(obstacles_list) & valid
    inflated_blocked: Set[Coord] = inflate_obstacles(base_blocked, valid, width, height, radius=1)
    buffer_only: Set[Coord] = inflated_blocked - base_blocked

    total_path: List[Coord] = []
    used_feet = 0.0
    ok = True

    for i in range(len(ordered_pts)-1):
        a = ordered_pts[i]; b = ordered_pts[i+1]
        splice = len(total_path) > 0
        seg = astar(width, height, a, b, inflated_blocked, valid,
                    diagonal=args.diagonal, cable_limit_ft=args.cable_ft, g_offset=used_feet)
        if seg is None:
            log(f"No path found between {a} -> {b} within cable limit {args.cable_ft:.3f} ft.")
            ok = False
            break
        seg_len = path_length_feet(seg)
        used_feet = seg_len
        total_path.extend(seg[1:] if splice else seg)

    # Render
    if not args.no_map:
        print(render_ascii(width, height, start, goal, base_blocked, valid,
                           total_path if ok else None,
                           ascii_safe=args.ascii_safe, outside_space=args.outside_space,
                           buffer=buffer_only))
    if args.png_out:
        try:
            render_png(args.png_out, width, height, start, goal, base_blocked, valid,
                       total_path if ok else None,
                       dpi=args.dpi, cell_size=args.cell_size,
                       show_grid=args.grid_lines, show_legend=not args.no_legend,
                       buffer=buffer_only)
            log(f"[info] PNG saved: {args.png_out}")
        except Exception as e:
            log(f"[warn] PNG render failed: {e}")

    if not ok:
        return 1

    total_feet = path_length_feet(total_path)
    log(f"Path length: {total_feet:.3f} ft (limit {args.cable_ft:.3f} ft)")
    log(f"Waypoints (incl. endpoints): {len(ordered_pts)} | Path nodes: {len(total_path)}")

    try:
        post_path_json(total_path, total_feet)
        log("[info] Path posted to /path")
    except Exception as e:
        log(f"[warn] Failed to POST path to {POST_PATH_URL}: {e}")
        return 1

    return 0

# ------------------------- Watcher -------------------------

def _stable_hash_json(obj) -> str:
    """Stable hash for change detection (handles lists/dicts recursively)."""
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
    """Fetch raw JSON (without mapping to Coord) to hash exactly what server returns."""
    obstacles_raw = requests.get(OBSTACLES_URL, timeout=5).json()
    waypoints_raw = requests.get(WAYPOINTS_URL, timeout=5).json()
    return obstacles_raw, waypoints_raw

def run_watcher(args) -> None:
    log(f"[watch] Starting watcher: interval={args.interval:.3f}s, debounce={args.debounce_ms}ms")
    last_obs_hash = None
    last_wp_hash  = None
    last_rc = None
    debounce_deadline = 0.0

    while True:
        t0 = time.time()
        try:
            obs_raw, wp_raw = _fetch_raw()
            h_obs = _stable_hash_json(obs_raw)
            h_wp  = _stable_hash_json(wp_raw)
            changed = (h_obs != last_obs_hash) or (h_wp != last_wp_hash)

            # Debounce: if changes keep happening inside debounce window, extend window
            if changed:
                debounce_deadline = max(debounce_deadline, t0) + (args.debounce_ms / 1000.0)
                last_obs_hash = h_obs
                last_wp_hash  = h_wp
                log("[watch] Change detected. Debouncing...")

            # If debounce window expired AND we have at least one known state, recompute
            if last_obs_hash is not None and last_wp_hash is not None and time.time() >= debounce_deadline:
                rc = compute_and_post(args)
                if rc != last_rc:
                    # Only log on status change to reduce noise
                    status = "OK" if rc == 0 else f"ERR({rc})"
                    log(f"[watch] Recompute status: {status}")
                last_rc = rc
                # Move deadline forward to prevent immediate retrigger on same hashes
                debounce_deadline = float("inf")  # wait for next change to reset
        except KeyboardInterrupt:
            log("[watch] Stopped by user.")
            break
        except Exception as e:
            log(f"[watch] Poll error: {e}")

        # Sleep to next poll
        dt = time.time() - t0
        time.sleep(max(0.0, args.interval - dt))

# ------------------------- CLI -------------------------

def main(argv: List[str]) -> int:
    ap = argparse.ArgumentParser(description="A* with JSON endpoints + waypoints + cable limit + watcher.")
    ap.add_argument("--diagonal", action="store_true", help="Allow 8-way movement.")
    ap.add_argument("--cable-ft", type=float, default=CABLE_MAX_FT, help="Cable length budget in feet.")
    ap.add_argument("--no-map", action="store_true", help="Suppress ASCII output.")
    ap.add_argument("--ascii-safe", action="store_true", help="ASCII map uses '*' instead of '•' for path.")
    ap.add_argument("--outside-space", action="store_true", help="Use spaces for cells outside the rectangle.")
    ap.add_argument("--png-out", default=None, help="Output PNG file.")
    ap.add_argument("--dpi", type=int, default=140)
    ap.add_argument("--cell-size", type=int, default=16)
    ap.add_argument("--grid-lines", action="store_true")
    ap.add_argument("--no-legend", action="store_true")
    # Watcher options
    ap.add_argument("--watch", action="store_true", help="Continuously poll endpoints and auto-recompute on changes.")
    ap.add_argument("--interval", type=float, default=2.0, help="Polling interval in seconds (default 2.0).")
    ap.add_argument("--debounce-ms", type=int, default=150, help="Debounce window in milliseconds (default 150).")
    args = ap.parse_args(argv)

    if args.watch:
        run_watcher(args)
        return 0
    else:
        return compute_and_post(args)

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
