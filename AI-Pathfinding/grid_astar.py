#!/usr/bin/env python3
"""
grid_astar.py
A* shortest path on a grid defined by two CSVs (grid + obstacles).

This version includes:
- Hardcoded CSV paths
- PNG rendering
- ASCII rendering with safety toggles
- Writes unreachable cells (w.r.t. start and movement model) back to obstacles.csv
- Exports the computed path to a hardcoded path.csv
- NEW: Keeps one-cell clearance from obstacles by inflating obstacles by 1 cell (8-neighborhood)
"""

import argparse, math, sys, os
from typing import Dict, List, Optional, Set, Tuple
import pandas as pd

# -------------------------
# Hardcoded file paths
# -------------------------
GRID_CSV_PATH = "C:\\Users\\johno\\Desktop\\CSC Work\\Classes\\CSC4610\\grid_coordinates2.csv"
OBSTACLES_CSV_PATH = "C:\\Users\\johno\\Desktop\\CSC Work\\Classes\\CSC4610\\obstacles2.csv"
OUTPUT_PATH_CSV = "C:\\Users\\johno\\Desktop\\CSC Work\\Classes\\CSC4610\\path2.csv"

# Optional matplotlib (for PNG rendering)
try:
    import matplotlib.pyplot as plt
    import numpy as np
    from matplotlib.colors import ListedColormap
    import matplotlib.patches as mpatches
    _MATPLOTLIB_AVAILABLE = True
except Exception:
    _MATPLOTLIB_AVAILABLE = False

Coord = Tuple[int, int]  # (x, y) == (col, row)

# ------------------------- Parsing -------------------------

def parse_xy(token: str) -> Coord:
    token = token.strip().replace(",", " ")
    parts = [p for p in token.split() if p]
    if len(parts) != 2:
        raise ValueError(f"Could not parse coordinate from: {token!r}")
    x, y = int(parts[0]), int(parts[1])
    return (x, y)

def parse_rc(token: str) -> Coord:
    # (row,col) -> (x=col, y=row)
    token = token.strip().replace(",", " ")
    parts = [p for p in token.split() if p]
    if len(parts) != 2:
        raise ValueError(f"Could not parse RC coordinate from: {token!r}")
    row, col = int(parts[0]), int(parts[1])
    return (col, row)

# ------------------------- A* helpers -------------------------

def in_bounds(p: Coord, width: int, height: int) -> bool:
    x, y = p
    return 0 <= x < width and 0 <= y < height

def neighbors_4(x: int, y: int):
    return [(x-1,y), (x+1,y), (x,y-1), (x,y+1)]

def neighbors_8(x: int, y: int):
    return [(x-1,y), (x+1,y), (x,y-1), (x,y+1),
            (x-1,y-1), (x-1,y+1), (x+1,y-1), (x+1,y+1)]

def manhattan(a: Coord, b: Coord) -> float:
    return abs(a[0]-b[0]) + abs(a[1]-b[1])

def octile(a: Coord, b: Coord) -> float:
    dx, dy = abs(a[0]-b[0]), abs(a[1]-b[1])
    D, D2 = 1.0, math.sqrt(2.0)
    return D*(dx+dy) + (D2-2*D)*min(dx, dy)

def astar(width: int, height: int, start: Coord, goal: Coord,
          blocked: Set[Coord], valid: Set[Coord], diagonal: bool=False) -> Optional[List[Coord]]:
    if start not in valid or goal not in valid: return None
    if start in blocked or goal in blocked: return None

    from heapq import heappush, heappop
    neigh = neighbors_8 if diagonal else neighbors_4
    h = octile if diagonal else manhattan
    step_cost = (lambda a,b: math.sqrt(2.0) if (a[0]!=b[0] and a[1]!=b[1]) else 1.0) if diagonal else (lambda a,b: 1.0)

    open_heap: List[Tuple[float, Coord]] = []
    heappush(open_heap, (h(start, goal), start))
    g: Dict[Coord, float] = {start: 0.0}
    came_from: Dict[Coord, Coord] = {}
    closed: Set[Coord] = set()

    while open_heap:
        _, current = heappop(open_heap)
        if current in closed: continue
        if current == goal: return reconstruct(came_from, current)
        closed.add(current)
        cx, cy = current
        for nxt in neigh(cx, cy):
            if not in_bounds(nxt, width, height): continue
            if nxt not in valid: continue
            if nxt in blocked: continue
            tentative = g[current] + step_cost(current, nxt)
            if tentative < g.get(nxt, float("inf")):
                g[nxt] = tentative
                came_from[nxt] = current
                f = tentative + h(nxt, goal)
                heappush(open_heap, (f, nxt))
    return None

def reconstruct(came_from: Dict[Coord, Coord], current: Coord) -> List[Coord]:
    path = [current]
    while current in came_from:
        current = came_from[current]
        path.append(current)
    path.reverse()
    return path

def path_length(path: Optional[List[Coord]]) -> float:
    if not path or len(path) < 2: return 0.0 if path else float("inf")
    total = 0.0
    for a, b in zip(path, path[1:]):
        diag = (a[0]!=b[0] and a[1]!=b[1])
        total += math.sqrt(2.0) if diag else 1.0
    return total

# ------------------------- Rendering -------------------------

def render_ascii(width: int, height: int, start: Coord, goal: Coord,
                 blocked: Set[Coord], valid: Set[Coord], path: Optional[List[Coord]],
                 *, ascii_safe: bool=False, outside_space: bool=False,
                 buffer: Optional[Set[Coord]] = None) -> str:
    """
    outside_space=False (default): prints '.' for cells outside the grid mask (solid rectangle).
    ascii_safe=True: uses '*' instead of '•' for path.
    '#' = actual obstacles (persisted)
    '+' = safety buffer (inflated, not persisted)
    """
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
                if p in blocked:
                    ch = '#'
                elif p in buffer:
                    ch = '+'
                elif p in pathset:
                    ch = path_char
                if p == start: ch = 'S'
                if p == goal:  ch = 'G'
            line.append(ch)
        rows.append("".join(line))
    legend = (
        f"Legend: S=start  G=goal  #=obstacle  +=buffer  {path_char}=path  .=free   "
        f"(grid {width}x{height}, masked)"
    )
    return "\n".join(rows + [legend])

def render_png(outfile: str,
               width: int, height: int,
               start: Coord, goal: Coord,
               blocked: Set[Coord], valid: Set[Coord],
               path: Optional[List[Coord]],
               *, dpi: int=140, cell_size: int=16,
               show_grid: bool=False, show_legend: bool=True,
               buffer: Optional[Set[Coord]] = None) -> None:
    if not _MATPLOTLIB_AVAILABLE:
        raise RuntimeError("matplotlib not available. Install it to use --png-out.")

    buffer = buffer or set()
    # 0 background, 1 free, 2 obstacle, 3 buffer
    img = np.zeros((height, width), dtype=np.uint8)
    for (x, y) in valid: img[y, x] = 1
    for (x, y) in blocked:
        if 0 <= x < width and 0 <= y < height: img[y, x] = 2
    for (x, y) in buffer:
        if 0 <= x < width and 0 <= y < height and img[y, x] != 2:
            img[y, x] = 3

    from matplotlib.colors import ListedColormap
    cmap = ListedColormap(["#d9d9d9", "#ffffff", "#000000", "#7f7f7f"])  # bg, free, obstacle, buffer

    px_w, px_h = max(1, width*cell_size), max(1, height*cell_size)
    fig_w, fig_h = px_w/dpi, px_h/dpi
    fig, ax = plt.subplots(figsize=(fig_w, fig_h), dpi=dpi)
    ax.imshow(img, cmap=cmap, interpolation="nearest", origin="upper")
    ax.set_xlim(-0.5, width-0.5)
    ax.set_ylim(height-0.5, -0.5)

    if path and len(path) > 1:
        xs = [x for (x, _) in path]
        ys = [y for (_, y) in path]
        ax.plot(xs, ys, linewidth=max(2, cell_size//5))

    ax.scatter([start[0]], [start[1]], marker='o', s=max(36, cell_size**2//4))
    ax.scatter([goal[0]],  [goal[1]],  marker='X', s=max(44, cell_size**2//3))

    if show_grid:
        for x in range(width+1): ax.axvline(x-0.5, linewidth=0.5)
        for y in range(height+1): ax.axhline(y-0.5, linewidth=0.5)

    if show_legend:
        import matplotlib.patches as mpatches
        bg   = mpatches.Patch(color="#d9d9d9", label="Outside Mask")
        free = mpatches.Patch(color="#ffffff", label="Free")
        obs  = mpatches.Patch(color="#000000", label="Obstacle")
        buf  = mpatches.Patch(color="#7f7f7f", label="Buffer")
        line = plt.Line2D([0], [0], lw=max(2, cell_size//5), label='Path')
        spt  = plt.Line2D([0], [0], marker='o', linestyle='None', label='Start', markersize=8)
        gpt  = plt.Line2D([0], [0], marker='X', linestyle='None', label='Goal', markersize=8)
        ax.legend(handles=[bg, free, obs, buf, line, spt, gpt], loc='lower right', framealpha=0.7)

    ax.set_aspect('equal'); ax.set_xticks([]); ax.set_yticks([])
    fig.tight_layout(pad=0); fig.savefig(outfile, bbox_inches="tight"); plt.close(fig)


# ------------------------- New: reachability / inflation / I/O helpers -------------------------

def _compute_reachable(width: int, height: int, start: Coord,
                       blocked: Set[Coord], valid: Set[Coord],
                       diagonal: bool) -> Set[Coord]:
    """Return set of cells reachable from start (respecting valid mask, obstacles, movement model)."""
    if start not in valid or start in blocked:
        return set()
    neigh = neighbors_8 if diagonal else neighbors_4
    seen: Set[Coord] = set([start])
    stack = [start]
    while stack:
        cx, cy = stack.pop()
        for nx, ny in neigh(cx, cy):
            p = (nx, ny)
            if not in_bounds(p, width, height): 
                continue
            if p in seen: 
                continue
            if p not in valid or p in blocked: 
                continue
            seen.add(p)
            stack.append(p)
    return seen

def inflate_obstacles(blocked: Set[Coord], valid: Set[Coord], width: int, height: int, radius: int = 1) -> Set[Coord]:
    """
    Inflate obstacles by Chebyshev radius (default 1). This ensures the path keeps at least
    one cell away in all directions. Only inflates into valid cells and within bounds.
    """
    if radius <= 0:
        return set(blocked)
    inflated = set(blocked)
    # All displacements with Chebyshev distance <= radius
    deltas = [(dx, dy) for dx in range(-radius, radius+1)
                       for dy in range(-radius, radius+1)]
    for (ox, oy) in list(blocked):
        for dx, dy in deltas:
            nx, ny = ox + dx, oy + dy
            p = (nx, ny)
            if 0 <= nx < width and 0 <= ny < height and p in valid:
                inflated.add(p)
    return inflated

def _update_obstacles_csv(obstacles_df: pd.DataFrame, new_obstacles: Set[Coord]) -> None:
    """
    Merge new (x,y) obstacles into obstacles_df (using only first two columns as row,col) and write back
    to OBSTACLES_CSV_PATH. Duplicates are removed.
    """
    core = obstacles_df.iloc[:, :2].rename(columns={obstacles_df.columns[0]: "row",
                                                    obstacles_df.columns[1]: "col"})
    add_rows = pd.DataFrame(
        [{"row": y, "col": x} for (x, y) in sorted(new_obstacles)],
        columns=["row", "col"]
    )
    merged = pd.concat([core, add_rows], ignore_index=True).drop_duplicates(subset=["row", "col"])
    merged = merged[["row", "col"]]
    merged.to_csv(OBSTACLES_CSV_PATH, index=False)

def write_path_csv(path: List[Coord]) -> None:
    """Write the computed path to OUTPUT_PATH_CSV with headers col,row."""
    try:
        os.makedirs(os.path.dirname(OUTPUT_PATH_CSV), exist_ok=True)
        import csv
        with open(OUTPUT_PATH_CSV, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["col", "row"])
            for x, y in path:
                w.writerow([x, y])
        print(f"[info] Path saved to {OUTPUT_PATH_CSV} ({len(path)} points)")
    except Exception as e:
        print(f"[warn] Could not write path CSV: {e}")

# ------------------------- CLI -------------------------

def main(argv: List[str]) -> int:
    ap = argparse.ArgumentParser(description="A* with hardcoded CSVs.")
    ap.add_argument("--start-rc", default=None, help="Start in 'row,col'.")
    ap.add_argument("--goal-rc",  default=None, help="Goal in 'row,col'.")
    ap.add_argument("--start", default=None, help="Start in 'x,y'.")
    ap.add_argument("--goal",  default=None, help="Goal in 'x,y'.")
    ap.add_argument("--diagonal", action="store_true", help="Allow 8-way movement.")
    ap.add_argument("--no-map", action="store_true", help="Suppress ASCII output.")
    ap.add_argument("--ascii-safe", action="store_true", help="ASCII map uses '*' instead of '•' for path.")
    ap.add_argument("--outside-space", action="store_true", help="Use spaces for cells outside mask (default prints '.').")
    ap.add_argument("--png-out", default=None, help="Output PNG file.")
    ap.add_argument("--dpi", type=int, default=140)
    ap.add_argument("--cell-size", type=int, default=16)
    ap.add_argument("--grid-lines", action="store_true")
    ap.add_argument("--no-legend", action="store_true")
    args = ap.parse_args(argv)

    # Load CSVs (use first two columns as row,col)
    grid_df = pd.read_csv(GRID_CSV_PATH)
    grid_rc = grid_df.iloc[:, :2]
    obs_df = pd.read_csv(OBSTACLES_CSV_PATH)
    obs_rc = obs_df.iloc[:, :2]

    # Valid mask and original obstacles
    valid: Set[Coord] = set((int(c), int(r)) for r, c in zip(grid_rc.iloc[:, 0], grid_rc.iloc[:, 1]))
    blocked_raw: Set[Coord] = set((int(c), int(r)) for r, c in zip(obs_rc.iloc[:, 0], obs_rc.iloc[:, 1]))
    base_blocked: Set[Coord] = set(pt for pt in blocked_raw if pt in valid)  # persisted obstacles only

    if not valid:
        print("Grid CSV produced an empty set of valid cells.", file=sys.stderr)
        return 2

    # Bounds from valid set (image space is 0..max)
    min_x, min_y = min(x for x, _ in valid), min(y for _, y in valid)
    max_x, max_y = max(x for x, _ in valid), max(y for _, y in valid)
    width, height = max_x + 1, max_y + 1

    # Start / Goal defaults
    if args.start_rc:
        start = parse_rc(args.start_rc)
    elif args.start:
        start = parse_xy(args.start)
    else:
        start = (min_x, min_y)

    if args.goal_rc:
        goal = parse_rc(args.goal_rc)
    elif args.goal:
        goal = parse_xy(args.goal)
    else:
        goal = (max_x, max_y)

    # 1) Mark unreachable cells (w.r.t. start, movement model) as obstacles and persist
    reachable = _compute_reachable(width, height, start, base_blocked, valid, diagonal=args.diagonal)
    newly_unreachable: Set[Coord] = {p for p in valid if (p not in base_blocked) and (p not in reachable)}
    if newly_unreachable:
        base_blocked |= newly_unreachable
        _update_obstacles_csv(obs_df, newly_unreachable)
        print(f"[info] Marked {len(newly_unreachable)} unreachable cells as obstacles and updated obstacles.csv")

    # 2) Inflate obstacles by 1 cell for safety buffer (NOT persisted)
    inflated_blocked: Set[Coord] = inflate_obstacles(base_blocked, valid, width, height, radius=1)
    buffer_only: Set[Coord] = inflated_blocked - base_blocked  # show as '+' in ASCII / gray in PNG

    # 3) Run A* using the inflated obstacle set
    path = astar(width, height, start, goal, inflated_blocked, valid, diagonal=args.diagonal)

    # 4) ASCII (render even if no path found)
    if not args.no_map:
        print(
            render_ascii(
                width, height, start, goal,
                base_blocked,         # real (persisted) obstacles
                valid,
                path,
                ascii_safe=args.ascii_safe,
                outside_space=args.outside_space,
                buffer=buffer_only     # safety buffer overlay
            )
        )

    # 5) PNG (render even if no path found)
    if args.png_out:
        render_png(
            args.png_out, width, height, start, goal,
            base_blocked,            # real obstacles
            valid,
            path,
            dpi=args.dpi, cell_size=args.cell_size,
            show_grid=args.grid_lines, show_legend=not args.no_legend,
            buffer=buffer_only
        )
        print(f"[info] PNG saved: {args.png_out}")

    # 6) Path reporting / CSV
    if path is None:
        # Helpful hints if start/goal fell inside the safety buffer
        if start in buffer_only and start not in base_blocked:
            print("[hint] Start is inside the 1-cell safety buffer. Move it at least 1 cell away from obstacles.")
        if goal in buffer_only and goal not in base_blocked:
            print("[hint] Goal is inside the 1-cell safety buffer. Move it at least 1 cell away from obstacles.")
        print("No path found.")
        return 1

    length = path_length(path)
    print(f"Path length: {length:.3f}")
    print(f"Start: {start}  Goal: {goal}")
    print(f"Path nodes ({len(path)}): {path}")
    write_path_csv(path)

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
