"""Generate an original explanatory visual of Nan Ma's 4D edge lift.

Uses the real Tile(1,1) prototile from the generator. Each directed edge is
assigned to one of two R² coordinate planes by its 30-degree direction class.
The closed R⁴ path is then shown through three projections: Hat, Tile(1,1),
and Turtle, plus an oblique R⁴→R³ projection.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from mpl_toolkits.mplot3d.art3d import Line3DCollection

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from spectre_patch.core.spectre_t11 import PROTOTILE_RING  # noqa: E402

OUT = ROOT / "site" / "assets" / "research" / "wiki" / "four-dimensional-lift.png"
BG = "#090b13"
RED = "#ff6a4a"
GREEN = "#4ecdc4"
TEXT = "#f7efe8"
MUTED = "#aeb7c8"


def edge_class(vector: np.ndarray) -> int:
    """0 for directions at multiples of 60°, 1 for odd multiples of 30°."""
    angle = math.degrees(math.atan2(float(vector[1]), float(vector[0]))) % 180
    step = int(round(angle / 30.0)) % 6
    return step % 2


def lifted_path() -> tuple[np.ndarray, list[int]]:
    ring = np.asarray(PROTOTILE_RING)
    path = [np.zeros(4)]
    classes: list[int] = []
    for i in range(len(ring)):
        edge = ring[(i + 1) % len(ring)] - ring[i]
        cls = edge_class(edge)
        classes.append(cls)
        lifted = np.array([edge[0], edge[1], 0.0, 0.0]) if cls == 0 else np.array(
            [0.0, 0.0, edge[0], edge[1]]
        )
        path.append(path[-1] + lifted)
    return np.asarray(path), classes


def project_2d(path: np.ndarray, a: float, b: float) -> np.ndarray:
    return a * path[:, :2] + b * path[:, 2:]


def project_3d(path: np.ndarray, t: float) -> np.ndarray:
    c, s = math.cos(t), math.sin(t)
    matrix = np.array(
        [
            [c, 0.0, s, 0.0],
            [0.0, c, 0.0, s],
            [-s, -s, c, c],
        ]
    )
    return path @ matrix.T


def draw_colored_outline(ax, points: np.ndarray, classes: list[int]) -> None:
    for i, cls in enumerate(classes):
        p, q = points[i], points[i + 1]
        ax.plot([p[0], q[0]], [p[1], q[1]], color=RED if cls == 0 else GREEN, lw=3.2)
    ax.fill(points[:, 0], points[:, 1], color="#171d31", alpha=0.8)
    ax.set_aspect("equal")
    ax.axis("off")


def main() -> None:
    path, classes = lifted_path()
    assert np.linalg.norm(path[-1]) < 1e-8, "lifted path must close"

    fig = plt.figure(figsize=(15, 9), facecolor=BG)
    gs = fig.add_gridspec(2, 3, height_ratios=[1.0, 1.25], hspace=0.2, wspace=0.08)
    projections = [
        ("Hat · Tile(1,√3)", 1.0, math.sqrt(3.0)),
        ("Tile(1,1)", 1.0, 1.0),
        ("Turtle · Tile(√3,1)", math.sqrt(3.0), 1.0),
    ]
    for col, (title, a, b) in enumerate(projections):
        ax = fig.add_subplot(gs[0, col], facecolor=BG)
        draw_colored_outline(ax, project_2d(path, a, b), classes)
        ax.set_title(title, color=TEXT, fontsize=14, fontweight="bold", pad=8)

    ax3 = fig.add_subplot(gs[1, :], projection="3d", facecolor=BG)
    p3 = project_3d(path, math.radians(33))
    segments = [[p3[i], p3[i + 1]] for i in range(len(classes))]
    colors = [RED if cls == 0 else GREEN for cls in classes]
    ax3.add_collection3d(Line3DCollection(segments, colors=colors, linewidths=5))
    ax3.scatter(p3[:, 0], p3[:, 1], p3[:, 2], c=TEXT, s=10, alpha=0.65)
    mins, maxs = p3.min(axis=0), p3.max(axis=0)
    center = (mins + maxs) / 2
    radius = max(maxs - mins) / 2 * 1.2
    ax3.set_xlim(center[0] - radius, center[0] + radius)
    ax3.set_ylim(center[1] - radius, center[1] + radius)
    ax3.set_zlim(center[2] - radius, center[2] + radius)
    ax3.set_box_aspect((1.6, 1.0, 0.8), zoom=2.25)
    ax3.view_init(elev=24, azim=-58)
    ax3.set_axis_off()
    ax3.set_title(
        "One closed path in ℝ⁴ · different projections produce the whole Tile(a,b) family",
        color=TEXT,
        fontsize=16,
        fontweight="bold",
        pad=0,
    )

    fig.text(
        0.5,
        0.025,
        "coral edges → first coordinate plane   ·   teal edges → second coordinate plane",
        ha="center",
        color=MUTED,
        fontsize=12,
    )
    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT, dpi=180, bbox_inches="tight", facecolor=BG)
    plt.close(fig)
    print(f"wrote {OUT} ({OUT.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
