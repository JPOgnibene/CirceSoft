#!/usr/bin/env python3
"""
grid_astar_from_csv_hardcoded.py
A* shortest path on a grid defined by two CSVs (grid + obstacles).

The file paths for the CSVs are hardcoded in this script:
- GRID_CSV_PATH
- OBSTACLES_CSV_PATH

CSV REQUIREMENTS
- Each CSV has headers: row,col,(other columns ok).
- Only the first two columns (row,col) are used.
- "row" = y, "col" = x.

OPTIONS
- --start-rc "row,col"   or --start "x,y"
- --goal-rc "row,col"    or --goal "x,y"
- --diagonal             allow 8-way moves
- --png-out FILE         export PNG
- --grid-lines           draw cell borders
- --no-map               suppress ASCII output
"""

import argparse, math, sys
from typing import Dict, List, Optional, Set, Tuple
import pandas as pd

# -------------------------
# Hardcoded CSV file paths
# -------------------------
GRID_CSV_PATH = "C:\\Users\\JP\\Desktop\\CSC Work\\Classes\\CSC4610\\grid_coordinates.csv"
OBSTACLES_CSV_PATH = "C:\\Users\\JP\\Desktop\\CSC Work\\Classes\\CSC4610\\obstacles.csv"

# Optional matplotlib
try:
    import matplotlib.pyplot as plt
    import numpy as np
    from matplotlib.colors import ListedColormap
    _MATPLOTLIB_AVAILABLE = True
except Exception:
    _MATPLOTLIB_AVAILABLE = False

Coord = Tuple[int, int]  # (x=col, y=row)

# ------------------------- Parsing -------------------------

def parse_xy(token: str) -> Coord:
    token = token.strip().replace(",", " ")
    parts = [p for p in token.split() if p]
    if len(parts) != 2:
        raise ValueError(f"Could not parse coordinate from: {token!r}")
    x, y = int(parts[0]), int(parts[1])
    return (x, y)

def parse_rc(token: str) -> Coord:
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
                 blocked: Set[Coord], valid: Set[Coord], path: Optional[List[Coord]]) -> str:
    pathset = set(path or [])
    rows: List[str] = []
    for y in range(height):
        line = []
        for x in range(width):
            p = (x, y)
            if p not in valid: ch = ' '
            else:
                ch = '.'
                if p in blocked: ch = '#'
                elif p in pathset: ch = '•'
                if p == start: ch = 'S'
                if p == goal:  ch = 'G'
            line.append(ch)
        rows.append("".join(line))
    legend = f"Legend: S=start  G=goal  #=blocked  •=path  .=free   (grid {width}x{height}, masked)"
    return "\n".join(rows + [legend])

def render_png(outfile: str,
               width: int, height: int,
               start: Coord, goal: Coord,
               blocked: Set[Coord], valid: Set[Coord],
               path: Optional[List[Coord]],
               *, dpi: int=140, cell_size: int=16,
               show_grid: bool=False, show_legend: bool=True) -> None:
    if not _MATPLOTLIB_AVAILABLE:
        raise RuntimeError("matplotlib not available. Install it to use --png-out.")
    import matplotlib.pyplot as plt
    import numpy as np
    from matplotlib.colors import ListedColormap
    import matplotlib.patches as mpatches

    img = np.zeros((height, width), dtype=np.uint8)
    for (x, y) in valid: img[y, x] = 1
    for (x, y) in blocked:
        if 0 <= x < width and 0 <= y < height: img[y, x] = 2

    cmap = ListedColormap(["#d9d9d9", "#ffffff", "#000000"])
    px_w, px_h = max(1, width*cell_size), max(1, height*cell_size)
    fig_w, fig_h = px_w/dpi, px_h/dpi
    fig, ax = plt.subplots(figsize=(fig_w, fig_h), dpi=dpi)
    ax.imshow(img, cmap=cmap, interpolation="nearest", origin="upper")
    ax.set_xlim(-0.5, width-0.5)
    ax.set_ylim(height-0.5, -0.5)

    if path and len(path)>1:
        xs = [x for (x, _) in path]
        ys = [y for (_, y) in path]
        ax.plot(xs, ys, linewidth=max(2, cell_size//5))

    ax.scatter([start[0]], [start[1]], marker='o', s=max(36, cell_size**2//4))
    ax.scatter([goal[0]], [goal[1]], marker='X', s=max(44, cell_size**2//3))

    if show_grid:
        for x in range(width+1): ax.axvline(x-0.5, linewidth=0.5)
        for y in range(height+1): ax.axhline(y-0.5, linewidth=0.5)

    if show_legend:
        bg = mpatches.Patch(color="#d9d9d9", label="Outside Mask")
        free = mpatches.Patch(color="#ffffff", label="Free")
        obs  = mpatches.Patch(color="#000000", label="Blocked")
        line = plt.Line2D([0], [0], lw=max(2, cell_size//5), label='Path')
        spt  = plt.Line2D([0], [0], marker='o', linestyle='None', label='Start', markersize=8)
        gpt  = plt.Line2D([0], [0], marker='X', linestyle='None', label='Goal', markersize=8)
        ax.legend(handles=[bg, free, obs, line, spt, gpt], loc='lower right', framealpha=0.7)

    ax.set_aspect('equal'); ax.set_xticks([]); ax.set_yticks([])
    fig.tight_layout(pad=0); fig.savefig(outfile, bbox_inches="tight"); plt.close(fig)

# ------------------------- CLI -------------------------

def main(argv: List[str]) -> int:
    ap = argparse.ArgumentParser(description="A* with hardcoded CSVs.")
    ap.add_argument("--start-rc", default=None, help="Start in 'row,col'.")
    ap.add_argument("--goal-rc",  default=None, help="Goal in 'row,col'.")
    ap.add_argument("--start", default=None, help="Start in 'x,y'.")
    ap.add_argument("--goal",  default=None, help="Goal in 'x,y'.")
    ap.add_argument("--diagonal", action="store_true", help="Allow 8-way movement.")
    ap.add_argument("--no-map", action="store_true", help="Suppress ASCII output.")
    ap.add_argument("--png-out", default=None, help="Output PNG file.")
    ap.add_argument("--dpi", type=int, default=140)
    ap.add_argument("--cell-size", type=int, default=16)
    ap.add_argument("--grid-lines", action="store_true")
    ap.add_argument("--no-legend", action="store_true")
    args = ap.parse_args(argv)

    # Load CSVs
    grid_df = pd.read_csv(GRID_CSV_PATH)
    grid_rc = grid_df.iloc[:, :2]
    obs_df = pd.read_csv(OBSTACLES_CSV_PATH)
    obs_rc = obs_df.iloc[:, :2]

    valid: Set[Coord] = set((int(c), int(r)) for r, c in zip(grid_rc.iloc[:,0], grid_rc.iloc[:,1]))
    blocked_raw: Set[Coord] = set((int(c), int(r)) for r, c in zip(obs_rc.iloc[:,0], obs_rc.iloc[:,1]))
    blocked = set(pt for pt in blocked_raw if pt in valid)

    min_x, min_y = min(x for x,_ in valid), min(y for _,y in valid)
    max_x, max_y = max(x for x,_ in valid), max(y for _,y in valid)
    width, height = max_x+1, max_y+1

    if args.start_rc: start = parse_rc(args.start_rc)
    elif args.start: start = parse_xy(args.start)
    else: start = (min_x, min_y)

    if args.goal_rc: goal = parse_rc(args.goal_rc)
    elif args.goal: goal = parse_xy(args.goal)
    else: goal = (max_x, max_y)

    path = astar(width, height, start, goal, blocked, valid, diagonal=args.diagonal)
    if path is None:
        print("No path found.")
        if not args.no_map:
            print(render_ascii(width, height, start, goal, blocked, valid, None))
        if args.png_out:
            render_png(args.png_out, width, height, start, goal, blocked, valid, None,
                       dpi=args.dpi, cell_size=args.cell_size,
                       show_grid=args.grid_lines, show_legend=not args.no_legend)
            print(f"[info] PNG saved: {args.png_out}")
        return 1

    length = path_length(path)
    print(f"Path length: {length:.3f}")
    print(f"Start: {start}  Goal: {goal}")
    print(f"Path nodes ({len(path)}): {path}\n")
    if not args.no_map:
        print(render_ascii(width, height, start, goal, blocked, valid, path))
    if args.png_out:
        render_png(args.png_out, width, height, start, goal, blocked, valid, path,
                   dpi=args.dpi, cell_size=args.cell_size,
                   show_grid=args.grid_lines, show_legend=not args.no_legend)
        print(f"[info] PNG saved: {args.png_out}")
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
