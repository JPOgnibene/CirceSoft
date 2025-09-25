#!/usr/bin/env python3
"""
grid_astar_dynamic.py
A* shortest path on an N×M grid with obstacles loaded from a static text file.

INPUT FILE FORMAT (one point per line):
- "x,y" or "x y" (0-based), e.g. "3,5" or "3 5"
- Blank lines allowed
- Lines starting with '#' are comments

USAGE:
  # Auto-infer grid size from obstacles + start/goal (default behavior)
  python grid_astar_dynamic.py obstacles.txt --start 0,0 --goal 19,19

  # Explicitly set grid size
  python grid_astar_dynamic.py obstacles.txt --width 50 --height 50 --start 0,0 --goal 49,49 --diagonal

OUTPUT:
- Path length (Manhattan with 4-way; octile with 8-way)
- List of path coordinates
- ASCII map of the grid showing obstacles and the path (may be wide on large grids)

NOTES:
- If --width/--height are given, points outside the grid are ignored with warnings.
- If size is auto-inferred, the grid will be (max_x_seen+1) by (max_y_seen+1),
  considering all obstacles and the start/goal coordinates.
"""

from __future__ import annotations
from typing import List, Tuple, Optional, Set, Dict, Iterable
from heapq import heappush, heappop
import argparse
import sys
import math

Coord = Tuple[int, int]

# ------------------------- Parsing & Utilities -------------------------

def parse_point(token: str) -> Coord:
    """
    Parse a coordinate from 'x,y' or 'x y' into (x, y).
    Raises ValueError on malformed input.
    """
    token = token.strip().replace(",", " ")
    parts = [p for p in token.split() if p]
    if len(parts) != 2:
        raise ValueError(f"Could not parse point from: {token!r}")
    x, y = int(parts[0]), int(parts[1])
    return (x, y)

def load_points_from_file(path: str) -> List[Coord]:
    """
    Load raw points from file without bounds checks.
    Each line: 'x,y' or 'x y'. Lines starting with '#' are comments.
    """
    pts: List[Coord] = []
    with open(path, "r", encoding="utf-8") as f:
        for ln, line in enumerate(f, start=1):
            s = line.strip()
            if not s or s.startswith("#"):
                continue
            try:
                pt = parse_point(s)
            except ValueError:
                print(f"[warn] {path}:{ln}: ignoring malformed line: {s!r}", file=sys.stderr)
                continue
            pts.append(pt)
    return pts

def infer_grid_size(
    obstacles: Iterable[Coord],
    start: Coord,
    goal: Coord
) -> Tuple[int, int]:
    """
    Infer grid width/height as (max_x + 1, max_y + 1) from obstacles + start + goal.
    Ensures minimum size of 1x1.
    """
    max_x = max([start[0], goal[0]] + [p[0] for p in obstacles]) if obstacles else max(start[0], goal[0])
    max_y = max([start[1], goal[1]] + [p[1] for p in obstacles]) if obstacles else max(start[1], goal[1])
    return (max(1, max_x + 1), max(1, max_y + 1))

def clamp_blocked_to_grid(
    raw_points: Iterable[Coord],
    width: int,
    height: int,
    *,
    warn_prefix: str = "obstacles"
) -> Set[Coord]:
    """
    Keep only points within [0,width)×[0,height]. Warn on out-of-bounds.
    """
    blocked: Set[Coord] = set()
    for pt in raw_points:
        x, y = pt
        if 0 <= x < width and 0 <= y < height:
            blocked.add(pt)
        else:
            print(f"[warn] {warn_prefix}: out-of-bounds point {pt} ignored (grid is {width}x{height})", file=sys.stderr)
    return blocked

# ------------------------- A* Implementation -------------------------

def astar(
    width: int,
    height: int,
    start: Coord,
    goal: Coord,
    blocked: Set[Coord],
    diagonal: bool = False
) -> Optional[List[Coord]]:
    """
    Run A* on a width×height grid with given blocked cells.
    Returns the shortest path (list of coords from start to goal), or None if no path exists.

    - diagonal=False: 4-way movement, Manhattan heuristic.
    - diagonal=True : 8-way movement, octile heuristic (diagonal step cost = sqrt(2)).
    """
    if start == goal:
        return [start]
    if not in_bounds(start, width, height) or not in_bounds(goal, width, height):
        return None
    if start in blocked or goal in blocked:
        return None

    if diagonal:
        neighbors = [(-1,0),(1,0),(0,-1),(0,1),(-1,-1),(-1,1),(1,-1),(1,1)]
        def h(a: Coord, b: Coord) -> float:
            dx, dy = abs(a[0]-b[0]), abs(a[1]-b[1])
            # Octile distance
            D = 1.0
            D2 = math.sqrt(2.0)
            return D * (dx + dy) + (D2 - 2*D) * min(dx, dy)
        def step_cost(a: Coord, b: Coord) -> float:
            ax, ay = a; bx, by = b
            return math.sqrt(2.0) if (ax != bx and ay != by) else 1.0
    else:
        neighbors = [(-1,0),(1,0),(0,-1),(0,1)]
        def h(a: Coord, b: Coord) -> float:
            return abs(a[0]-b[0]) + abs(a[1]-b[1])  # Manhattan
        def step_cost(a: Coord, b: Coord) -> float:
            return 1.0

    open_heap: List[Tuple[float, Coord]] = []
    heappush(open_heap, (h(start, goal), start))

    g: Dict[Coord, float] = {start: 0.0}
    came_from: Dict[Coord, Coord] = {}
    closed: Set[Coord] = set()

    while open_heap:
        _, current = heappop(open_heap)
        if current in closed:
            continue
        if current == goal:
            return reconstruct(came_from, current)

        closed.add(current)

        for dx, dy in neighbors:
            nx, ny = current[0] + dx, current[1] + dy
            nxt = (nx, ny)
            if not in_bounds(nxt, width, height) or nxt in blocked:
                continue
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

def in_bounds(p: Coord, width: int, height: int) -> bool:
    x, y = p
    return 0 <= x < width and 0 <= y < height

def path_length(path: Optional[List[Coord]]) -> float:
    """Compute path length with 1 for orthogonal steps and sqrt(2) for diagonal steps."""
    if not path or len(path) < 2:
        return 0.0 if path else float("inf")
    total = 0.0
    for a, b in zip(path, path[1:]):
        ax, ay = a; bx, by = b
        dx, dy = abs(ax - bx), abs(ay - by)
        total += (math.sqrt(2.0) if (dx == 1 and dy == 1) else 1.0)
    return total

# ------------------------- Rendering -------------------------

def render_ascii(
    width: int,
    height: int,
    start: Coord,
    goal: Coord,
    blocked: Set[Coord],
    path: Optional[List[Coord]] = None
) -> str:
    """
    Render a text map of the grid.
      '.' empty
      '#' blocked
      '•' path cells (if any)
      'S' start
      'G' goal
    Note: Start/Goal symbols override path dot at their cells.
    """
    pathset = set(path or [])
    rows: List[str] = []
    for y in range(height):
        line = []
        for x in range(width):
            p = (x, y)
            ch = '.'
            if p in blocked:
                ch = '#'
            elif p in pathset:
                ch = '•'
            if p == start:
                ch = 'S'
            if p == goal:
                ch = 'G'
            line.append(ch)
        rows.append("".join(line))
    legend = f"Legend: S=start  G=goal  #=blocked  •=path  .=free   (grid {width}x{height})"
    return "\n".join(rows + [legend])

# ------------------------- CLI -------------------------

def main(argv: List[str]) -> int:
    ap = argparse.ArgumentParser(description="A* on an N×M grid with obstacles from file.")
    ap.add_argument("file", help="Text file listing blocked points (one per line: 'x,y' or 'x y').")
    ap.add_argument("--start", default=None, help="Start coordinate, e.g. '0,0'. Default: (0,0).")
    ap.add_argument("--goal",  default=None, help="Goal coordinate, e.g. '49,49'. Default: (W-1,H-1).")
    ap.add_argument("--width", type=int, default=None, help="Grid width. If omitted, auto-infer from data.")
    ap.add_argument("--height", type=int, default=None, help="Grid height. If omitted, auto-infer from data.")
    ap.add_argument("--diagonal", action="store_true", help="Allow 8-way movement (diagonals).")
    ap.add_argument("--no-map", action="store_true", help="Suppress ASCII map output.")
    args = ap.parse_args(argv)

    # Load raw obstacles (no bounds checks yet)
    raw_obstacles = load_points_from_file(args.file)

    # Parse start/goal (defaults depend on grid size; parse now, set defaults later)
    start = parse_point(args.start) if args.start else None
    goal  = parse_point(args.goal)  if args.goal  else None

    # Decide grid size
    if args.width is not None and args.height is not None:
        width, height = args.width, args.height
        if width <= 0 or height <= 0:
            print("Width and height must be positive integers.", file=sys.stderr)
            return 2
        # Now set start/goal defaults based on explicit size
        if start is None:
            start = (0, 0)
        if goal is None:
            goal = (width - 1, height - 1)
    else:
        # Auto-infer: need provisional start/goal for inference
        provisional_start = start if start is not None else (0, 0)
        # If goal is missing, guess a generous provisional goal (max of obstacles or default 1,1)
        if goal is None:
            if raw_obstacles:
                max_x = max(pt[0] for pt in raw_obstacles + [provisional_start])
                max_y = max(pt[1] for pt in raw_obstacles + [provisional_start])
                provisional_goal = (max_x, max_y)
            else:
                provisional_goal = (1, 1)
        else:
            provisional_goal = goal

        width, height = infer_grid_size(raw_obstacles, provisional_start, provisional_goal)
        # Finalize defaults for start/goal after we know size
        if start is None:
            start = (0, 0)
        if goal is None:
            goal = (width - 1, height - 1)

    # Validate start/goal now that we have size
    if not in_bounds(start, width, height):
        print(f"Start {start} out of bounds for grid {width}x{height}.", file=sys.stderr)
        return 2
    if not in_bounds(goal, width, height):
        print(f"Goal {goal} out of bounds for grid {width}x{height}.", file=sys.stderr)
        return 2

    # Clamp obstacles to grid
    blocked = clamp_blocked_to_grid(raw_obstacles, width, height, warn_prefix="obstacles")

    if start in blocked:
        print(f"[warn] start {start} is in blocked set; no path possible.", file=sys.stderr)
    if goal in blocked:
        print(f"[warn] goal  {goal} is in blocked set; no path possible.", file=sys.stderr)

    path = astar(width, height, start, goal, blocked, diagonal=args.diagonal)
    if path is None:
        print(f"No path found on grid {width}x{height}.")
        if not args.no_map:
            print(render_ascii(width, height, start, goal, blocked, path=None))
        return 1

    length = path_length(path)
    print(f"Grid: {width}x{height}  |  Movement: {'8-way' if args.diagonal else '4-way'}")
    print(f"Shortest path length: {length:.3f}")
    print(f"Path ({len(path)} nodes): {path}\n")
    if not args.no_map:
        print(render_ascii(width, height, start, goal, blocked, path))
    return 0

if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
