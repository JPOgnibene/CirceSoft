#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
field_grid_tool.py

Detect a football-field-like quadrilateral (or any trapezoid), interactively
adjust the 4 corners, set rows/cols, and export all grid node coordinates.

New:
  • On exit, automatically saves:
      - grid node coordinates -> grid_coordinates.csv
      - obstacle node coordinates -> obstacles.csv
  • Right-click any grid node to toggle it as an obstacle (highlighted).

Requirements:
  pip install opencv-python numpy

Usage (GUI editor):
  python field_grid_tool.py path/to/image.jpg --rows 12 --cols 24

Headless export (no GUI; just detect, generate, and save CSV):
  python field_grid_tool.py path/to/image.jpg --rows 12 --cols 24 --no-gui --save

Keys in GUI:
  - Drag green points to move corners (TL, TR, BR, BL)
  - r / R : rows +1 / -1
  - c / C : cols +1 / -1
  - p     : print all coordinates to console
  - s     : save annotated image + CSV (also writes grid_coordinates.csv & obstacles.csv)
  - o     : re-order corners to TL, TR, BR, BL
  - x     : clear all obstacles
  - Right-click: toggle obstacle at nearest grid node
  - q/ESC : quit (auto-saves CSVs on exit)
"""

import argparse
from typing import Optional, Tuple, Dict, List, Tuple as Tup, Set

import cv2
import numpy as np


# ============================ Geometry / Helpers ============================

def _is_convex_quad(pts: np.ndarray) -> bool:
    pts = pts.reshape(4, 2).astype(np.float32)
    cross = []
    for i in range(4):
        a = pts[(i + 1) % 4] - pts[i]
        b = pts[(i + 2) % 4] - pts[(i + 1) % 4]
        cross.append(np.cross(a, b))
    return np.all(np.array(cross) > 0) or np.all(np.array(cross) < 0)


def _order_corners_clockwise(pts: np.ndarray) -> np.ndarray:
    """Return TL, TR, BR, BL order, robust to rotation."""
    pts = pts.reshape(4, 2).astype(np.float32)
    ys = pts[:, 1]
    top_idx = np.argsort(ys)[:2]
    bot_idx = np.argsort(ys)[2:]

    top = pts[top_idx]
    bot = pts[bot_idx]

    tl, tr = top[np.argsort(top[:, 0])]
    bl, br = bot[np.argsort(bot[:, 0])]

    ordered = np.array([tl, tr, br, bl], dtype=np.float32)
    if not _is_convex_quad(ordered):
        ordered = np.array([tl, bl, br, tr], dtype=np.float32)
    return ordered


def order_corners(corners: np.ndarray) -> np.ndarray:
    """Public API: order corners TL, TR, BR, BL."""
    return _order_corners_clockwise(corners)


def _quad_area(pts: np.ndarray) -> float:
    pts = pts.reshape(-1, 2).astype(np.float32)
    return cv2.contourArea(pts)


def _validate_quad(pts: np.ndarray, w: int, h: int, min_frac=0.05, max_frac=0.95) -> bool:
    area = _quad_area(pts)
    img_area = float(w * h)
    if area < min_frac * img_area or area > max_frac * img_area:
        return False
    eps = 2.0
    if np.any(pts[:, 0] < -eps) or np.any(pts[:, 0] > w + eps):
        return False
    if np.any(pts[:, 1] < -eps) or np.any(pts[:, 1] > h + eps):
        return False
    return _is_convex_quad(pts)


def _approx_largest_quad(contours, eps_factor=0.02) -> Optional[np.ndarray]:
    for cnt in sorted(contours, key=cv2.contourArea, reverse=True):
        peri = cv2.arcLength(cnt, True)
        approx = cv2.approxPolyDP(cnt, eps_factor * peri, True)
        if len(approx) == 4:
            return approx.reshape(-1, 2)
    return None


def _min_area_rect_quad(cnt) -> np.ndarray:
    rect = cv2.minAreaRect(cnt)  # ((cx,cy),(w,h),angle)
    box = cv2.boxPoints(rect)
    return box.astype(np.float32)


# ============================ Detection Methods ============================

def find_trapezoid_corners(
    image_path: str,
    min_area_frac: float = 0.02,
    epsilon_factor: float = 0.02
) -> Optional[np.ndarray]:
    """Generic quad detection from edges."""
    image = cv2.imread(image_path)
    if image is None:
        print(f"Error: Could not load image from {image_path}")
        return None

    h, w = image.shape[:2]
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blurred, 50, 150)

    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    contours = [c for c in contours if cv2.contourArea(c) >= min_area_frac * w * h]
    if not contours:
        return None

    quad = _approx_largest_quad(contours, epsilon_factor)
    if quad is None:
        largest = max(contours, key=cv2.contourArea)
        quad = _min_area_rect_quad(largest)

    quad = _order_corners_clockwise(quad)
    if _validate_quad(quad, w, h):
        return quad
    return None


def find_football_field_corners(image_path: str) -> Optional[np.ndarray]:
    """Color + shape driven; good for grassy fields with white lines."""
    image = cv2.imread(image_path)
    if image is None:
        print(f"Error: Could not load image from {image_path}")
        return None
    h, w = image.shape[:2]

    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    lower_green = np.array([35, 30, 30], dtype=np.uint8)
    upper_green = np.array([90, 255, 255], dtype=np.uint8)
    green = cv2.inRange(hsv, lower_green, upper_green)

    k = max(3, int(round(min(w, h) * 0.006)))
    kernel = np.ones((k, k), np.uint8)
    green = cv2.morphologyEx(green, cv2.MORPH_CLOSE, kernel)
    green = cv2.morphologyEx(green, cv2.MORPH_OPEN, kernel)

    cnts, _ = cv2.findContours(green, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not cnts:
        print("No green areas found")
        return None

    largest = max(cnts, key=cv2.contourArea)
    peri = cv2.arcLength(largest, True)

    for eps in (0.01, 0.015, 0.02, 0.03, 0.05):
        approx = cv2.approxPolyDP(largest, eps * peri, True)
        if len(approx) == 4:
            quad = _order_corners_clockwise(approx.reshape(-1, 2))
            if _validate_quad(quad, w, h, min_frac=0.08):
                return quad

    # Fallback: min-area rectangle
    quad = _min_area_rect_quad(largest)
    quad = _order_corners_clockwise(quad)
    if _validate_quad(quad, w, h, min_frac=0.08):
        return quad

    # Bonus: refine with white line cue
    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
    L = lab[:, :, 0]
    _, white = cv2.threshold(L, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    white = cv2.morphologyEx(white, cv2.MORPH_OPEN, np.ones((k, k), np.uint8))

    edges = cv2.Canny(white, 50, 150)
    lines = cv2.HoughLinesP(
        edges, 1, np.pi / 180, threshold=150,
        minLineLength=int(0.25 * min(w, h)),
        maxLineGap=int(0.02 * min(w, h))
    )
    if lines is not None and len(lines) >= 2:
        ys, xs = np.where(white > 0)
        pts = np.column_stack([xs, ys]).astype(np.int32)
        hull = cv2.convexHull(pts)
        peri = cv2.arcLength(hull, True)
        approx = cv2.approxPolyDP(hull, 0.02 * peri, True)
        if len(approx) >= 4:
            if len(approx) == 4:
                quad = approx.reshape(-1, 2).astype(np.float32)
            else:
                quad = _min_area_rect_quad(hull)
            quad = _order_corners_clockwise(quad)
            if _validate_quad(quad, w, h, min_frac=0.08):
                return quad

    print("Could not approximate field to a valid quadrilateral.")
    return None


def find_field_with_edge_enhancement(image_path: str) -> Optional[np.ndarray]:
    """Edge-enhanced alternative."""
    image = cv2.imread(image_path)
    if image is None:
        return None
    h, w = image.shape[:2]

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    filtered = cv2.bilateralFilter(gray, 9, 75, 75)
    adaptive = cv2.adaptiveThreshold(
        filtered, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY, 11, 2
    )

    k = max(3, int(round(min(w, h) * 0.004)))
    kernel = np.ones((k, k), np.uint8)
    cleaned = cv2.morphologyEx(adaptive, cv2.MORPH_CLOSE, kernel)
    cleaned = cv2.morphologyEx(cleaned, cv2.MORPH_OPEN, kernel)

    cnts, _ = cv2.findContours(cleaned, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not cnts:
        return None

    candidates: List[Tup[float, np.ndarray]] = []
    for c in cnts:
        area = cv2.contourArea(c)
        if area < 0.05 * w * h:
            continue
        x, y, ww, hh = cv2.boundingRect(c)
        ar = ww / max(1, hh)
        if 1.1 < ar < 3.8:
            for eps in (0.015, 0.02, 0.03):
                approx = cv2.approxPolyDP(c, eps * cv2.arcLength(c, True), True)
                if len(approx) == 4:
                    quad = _order_corners_clockwise(approx.reshape(-1, 2))
                    if _validate_quad(quad, w, h, min_frac=0.06):
                        candidates.append((cv2.contourArea(approx), quad))
                        break
    if candidates:
        candidates.sort(key=lambda t: t[0], reverse=True)
        return candidates[0][1]

    best = max(cnts, key=cv2.contourArea)
    quad = _min_area_rect_quad(best)
    quad = _order_corners_clockwise(quad)
    return quad if _validate_quad(quad, w, h, min_frac=0.06) else None


def find_field_corners(image_path: str) -> Tuple[Optional[np.ndarray], Dict]:
    """Try multiple strategies; return (corners, info)."""
    image = cv2.imread(image_path)
    if image is None:
        return None, {"method": "error:load", "score": 0.0}
    h, w = image.shape[:2]

    quad = find_football_field_corners(image_path)
    if quad is not None:
        return quad, {"method": "color+shape", "score": _quad_area(quad) / (w * h)}

    quad = find_field_with_edge_enhancement(image_path)
    if quad is not None:
        return quad, {"method": "edge_enhanced", "score": _quad_area(quad) / (w * h)}

    quad = find_trapezoid_corners(image_path, min_area_frac=0.03, epsilon_factor=0.02)
    if quad is not None:
        return quad, {"method": "generic", "score": _quad_area(quad) / (w * h)}

    return None, {"method": "none", "score": 0.0}


# ============================ Grid & Export ============================

def interpolate_quad_grid(corners: np.ndarray, rows: int, cols: int) -> np.ndarray:
    """
    Given corners TL, TR, BR, BL, return (rows+1, cols+1, 2) nodes via bilinear interpolation.
    """
    c = corners.astype(np.float32)
    TL, TR, BR, BL = c[0], c[1], c[2], c[3]

    grid = np.zeros((rows + 1, cols + 1, 2), dtype=np.float32)
    for r in range(rows + 1):
        t = r / rows if rows > 0 else 0.0
        left = (1 - t) * TL + t * BL
        right = (1 - t) * TR + t * BR
        for q in range(cols + 1):
            s = q / cols if cols > 0 else 0.0
            grid[r, q] = (1 - s) * left + s * right
    return grid


def grid_to_list(grid: np.ndarray) -> List[Tuple[float, float, int, int]]:
    pts = []
    R, C = grid.shape[:2]
    for r in range(R):
        for c in range(C):
            x, y = grid[r, c]
            pts.append((float(x), float(y), r, c))
    return pts


def save_grid_csv(grid: np.ndarray, csv_path: str):
    import csv
    with open(csv_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["row", "col", "x", "y"])
        for r in range(grid.shape[0]):
            for c in range(grid.shape[1]):
                x, y = grid[r, c]
                w.writerow([r, c, f"{x:.3f}", f"{y:.3f}"])
    print(f"Saved coordinates to {csv_path}")


def save_obstacles_csv(obstacles: Set[Tuple[int, int]], grid: np.ndarray, csv_path: str):
    import csv
    with open(csv_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["row", "col", "x", "y"])
        for (r, c) in sorted(list(obstacles)):
            x, y = grid[r, c]
            w.writerow([r, c, f"{x:.3f}", f"{y:.3f}"])
    print(f"Saved obstacles to {csv_path}")


def visualize_corners(image_path: str, corners: np.ndarray,
                      output_path: Optional[str] = None, show: bool = False):
    image = cv2.imread(image_path)
    if image is None:
        return
    pts = corners.astype(int)
    for i, (x, y) in enumerate(pts):
        cv2.circle(image, (x, y), 8, (0, 255, 0), -1)
        cv2.putText(image, f"P{i+1}", (x + 10, y - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    cv2.polylines(image, [pts], True, (0, 0, 255), 3)

    if output_path:
        cv2.imwrite(output_path, image)
        print(f"Result saved to {output_path}")
    if show:
        cv2.imshow("Corners", image)
        cv2.waitKey(0)
        cv2.destroyAllWindows()


# ============================ Interactive Editor ============================

class CornerGridEditor:
    """
    Mouse-driven editor:
      - Drag corners to adjust (P1..P4 labels are TL, TR, BR, BL).
      - Right-click a grid node to toggle it as an obstacle.
      - Keys:
         r / R : rows +1 / -1
         c / C : cols +1 / -1
         p     : print all coordinates to console
         s     : save snapshot (image + CSV)
         o     : reorder corners to TL,TR,BR,BL
         x     : clear all obstacles
         q/ESC : quit (auto-saves grid_coordinates.csv & obstacles.csv)
    """
    def __init__(self, image_path: str,
                 corners: Optional[np.ndarray] = None,
                 rows: int = 10, cols: int = 20):
        self.image_path = image_path
        self.base = cv2.imread(image_path)
        if self.base is None:
            raise FileNotFoundError(f"Could not load image: {image_path}")
        self.h, self.w = self.base.shape[:2]

        if corners is None:
            self.corners = np.array([[0, 0],
                                     [self.w - 1, 0],
                                     [self.w - 1, self.h - 1],
                                     [0, self.h - 1]], dtype=np.float32)
        else:
            self.corners = order_corners(corners).astype(np.float32)

        self.rows = max(1, rows)
        self.cols = max(1, cols)

        # Obstacles: set of (row, col) indices of grid nodes
        self.obstacles: Set[Tuple[int, int]] = set()

        self.active_idx = None
        self.dragging = False
        self.radius = max(8, int(0.01 * min(self.w, self.h)))

        self.grid: Optional[np.ndarray] = None  # updated on each draw

        self.win = "CornerGridEditor"
        cv2.namedWindow(self.win)
        cv2.setMouseCallback(self.win, self._on_mouse)

    # --- obstacle toggling helper ---
    def _toggle_obstacle_at_pixel(self, x: int, y: int):
        if self.grid is None:
            return
        # find nearest grid node
        diff = self.grid - np.array([x, y], dtype=np.float32)
        dist2 = (diff[..., 0] ** 2 + diff[..., 1] ** 2)
        r, c = np.unravel_index(np.argmin(dist2), dist2.shape)
        # threshold: within ~3*radius pixels
        if dist2[r, c] <= (3 * self.radius) ** 2:
            key = (int(r), int(c))
            if key in self.obstacles:
                self.obstacles.remove(key)
            else:
                self.obstacles.add(key)

    def _on_mouse(self, event, x, y, flags, param):
        pt = np.array([x, y], dtype=np.float32)
        if event == cv2.EVENT_LBUTTONDOWN:
            dists = np.linalg.norm(self.corners - pt, axis=1)
            idx = int(np.argmin(dists))
            if dists[idx] < 3 * self.radius:
                self.active_idx = idx
                self.dragging = True
        elif event == cv2.EVENT_MOUSEMOVE and self.dragging and self.active_idx is not None:
            x = int(np.clip(x, 0, self.w - 1))
            y = int(np.clip(y, 0, self.h - 1))
            self.corners[self.active_idx] = (x, y)
        elif event == cv2.EVENT_LBUTTONUP:
            self.dragging = False
            self.active_idx = None
        elif event == cv2.EVENT_RBUTTONDOWN:
            self._toggle_obstacle_at_pixel(x, y)

    def _draw(self):
        vis = self.base.copy()
        pts = self.corners.astype(np.int32)
        cv2.polylines(vis, [pts], True, (0, 0, 255), 3)

        labels = ["P1 (TL)", "P2 (TR)", "P3 (BR)", "P4 (BL)"]
        for i, (x, y) in enumerate(pts):
            cv2.circle(vis, (x, y), self.radius, (0, 255, 0), -1)
            cv2.putText(vis, labels[i], (x + 10, y - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

        self.grid = interpolate_quad_grid(self.corners, self.rows, self.cols)

        # grid lines
        for r in range(self.rows + 1):
            row = self.grid[r].astype(np.int32)
            cv2.polylines(vis, [row], False, (255, 0, 0), 1)
        for c in range(self.cols + 1):
            col = self.grid[:, c].astype(np.int32)
            cv2.polylines(vis, [col], False, (255, 0, 0), 1)

        # grid nodes
        for r in range(self.rows + 1):
            for c in range(self.cols + 1):
                x, y = self.grid[r, c].astype(int)
                cv2.circle(vis, (x, y), max(2, self.radius // 2), (0, 255, 255), -1)

        # obstacles overlay (magenta filled circles with white outline)
        for (r, c) in self.obstacles:
            x, y = self.grid[r, c].astype(int)
            cv2.circle(vis, (x, y), max(4, self.radius // 2 + 2), (255, 255, 255), -1)
            cv2.circle(vis, (x, y), max(4, self.radius // 2 + 1), (255, 0, 255), -1)

        hud = ("rows={rows}  cols={cols}   [drag corners]  r/R +/-row  c/C +/-col  "
               "p print  s save  o order  x clear-obstacles  RMB toggle obstacle  q quit").format(
                   rows=self.rows, cols=self.cols)
        cv2.rectangle(vis, (0, 0), (self.w, 30), (32, 32, 32), -1)
        cv2.putText(vis, hud, (10, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (240, 240, 240), 1)

        return vis, self.grid

    def _print_coords(self, grid: np.ndarray):
        print("row,col,x,y")
        for r in range(grid.shape[0]):
            for c in range(grid.shape[1]):
                x, y = grid[r, c]
                print(f"{r},{c},{x:.3f},{y:.3f}")

    def _save_all_csvs(self, vis: Optional[np.ndarray], grid: np.ndarray, msg_prefix: str = "Saved"):
        # Annotated image
        if vis is not None:
            out_img = self.image_path.rsplit(".", 1)[0] + "_grid.jpg"
            cv2.imwrite(out_img, vis)
        # Required CSV filenames
        grid_csv = "grid_coordinates.csv"
        obs_csv = "obstacles.csv"
        save_grid_csv(grid, grid_csv)
        save_obstacles_csv(self.obstacles, grid, obs_csv)
        print(f"{msg_prefix}: grid -> {grid_csv}, obstacles -> {obs_csv}")

    def run(self):
        last_vis, last_grid = None, None
        while True:
            vis, grid = self._draw()
            last_vis, last_grid = vis, grid
            cv2.imshow(self.win, vis)
            key = cv2.waitKey(16) & 0xFF

            if key in (ord('q'), 27):
                break
            elif key == ord('r'):
                self.rows += 1
            elif key == ord('R'):
                self.rows = max(1, self.rows - 1)
            elif key == ord('c'):
                self.cols += 1
            elif key == ord('C'):
                self.cols = max(1, self.cols - 1)
            elif key == ord('o'):
                self.corners = order_corners(self.corners)
            elif key == ord('x'):
                self.obstacles.clear()
            elif key == ord('p'):
                self._print_coords(grid)
            elif key == ord('s'):
                self._save_all_csvs(vis, grid, msg_prefix="Saved (manual)")

        cv2.destroyWindow(self.win)
        # Auto-save on exit
        if last_grid is not None:
            self._save_all_csvs(last_vis, last_grid, msg_prefix="Auto-saved on exit")


# ============================ CLI / Main ============================

def main():
    ap = argparse.ArgumentParser(description="Detect/edit field corners and export grid coordinates.")
    ap.add_argument("image", help="Path to input image (e.g., field.jpg)")
    ap.add_argument("--rows", type=int, default=12, help="Number of grid rows (default: 12)")
    ap.add_argument("--cols", type=int, default=24, help="Number of grid cols (default: 24)")
    ap.add_argument("--no-gui", action="store_true", help="Disable GUI; just detect and export if --save")
    ap.add_argument("--save", action="store_true", help="Save annotated image and CSV")
    ap.add_argument("--print", dest="do_print", action="store_true", help="Print all coordinates to console")
    args = ap.parse_args()

    img_path = args.image
    rows = max(1, args.rows)
    cols = max(1, args.cols)

    print("Detecting field/trapezoid corners...")
    corners, info = find_field_corners(img_path)
    if corners is not None:
        corners = order_corners(corners)
        print(f"✓ Found corners via {info['method']} (coverage ~{info['score']:.3f})")
    else:
        print("✗ Detection failed; starting with full-image rectangle.")
        image = cv2.imread(img_path)
        if image is None:
            raise FileNotFoundError(f"Could not load image: {img_path}")
        h, w = image.shape[:2]
        corners = np.array([[0, 0], [w - 1, 0], [w - 1, h - 1], [0, h - 1]], dtype=np.float32)

    if args.no_gui:
        # Headless path: save grid to grid_coordinates.csv (and empty obstacles.csv)
        grid = interpolate_quad_grid(corners, rows, cols)
        if args.do_print:
            print("row,col,x,y")
            for r in range(grid.shape[0]):
                for c in range(grid.shape[1]):
                    x, y = grid[r, c]
                    print(f"{r},{c},{x:.3f},{y:.3f}")
        if args.save:
            # draw overlay to save image
            tmp_editor = CornerGridEditor(img_path, corners=corners, rows=rows, cols=cols)
            vis, grid = tmp_editor._draw()
            out_img = img_path.rsplit(".", 1)[0] + "_grid.jpg"
            cv2.imwrite(out_img, vis)
            save_grid_csv(grid, "grid_coordinates.csv")
            save_obstacles_csv(set(), grid, "obstacles.csv")
            print(f"Saved headless: {out_img}, grid_coordinates.csv, obstacles.csv")
        return

    # GUI path
    editor = CornerGridEditor(img_path, corners=corners, rows=rows, cols=cols)
    editor.run()


if __name__ == "__main__":
    main()
