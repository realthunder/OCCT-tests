"""The figure of "Two events at one level" (README): an L with its vertical
edges filleted 1, its walls drafted inward at 30 deg about its bottom, seen
from above -- the outline at the bottom and at levels up to where the arms
close over, and the events that fall at that one level. Drawn with shapely
and matplotlib from the FreeCAD conda env:

    python pictures/roof_tie.py models/pictures/new_roof_L_a-30.png
"""
import math
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from shapely.geometry import Polygon

L = Polygon([(0, 0), (30, 0), (30, 10), (10, 10), (10, 25), (0, 25)])
# every corner rounded 1, the concave one too
base = L.buffer(1, 64).buffer(-2, 64).buffer(1, 64)
TAN = math.tan(math.radians(30))

fig, ax = plt.subplots(figsize=(8.4, 6.6), dpi=150)
for z, color in ((0.0, "#30363d"), (2.0, "#6e7781"), (4.0, "#8c959f"), (6.0, "#afb8c1"),
                 (8.0, "#d0d7de")):
    shape = base.buffer(-z * TAN, 64)
    for poly in getattr(shape, "geoms", [shape]):
        xs, ys = poly.exterior.xy
        ax.plot(xs, ys, color=color, lw=1.6 if z == 0 else 1.0)
    ax.text(30.6 - z * TAN, 0.4 + z * TAN, "z = %g" % z, fontsize=7, color="#57606a")
# at z = 8.66 the arms, 10 wide, have closed over: two level ridges
ax.plot([5, 25], [5, 5], color="#cf222e", lw=2.2)
ax.plot([5, 5], [5, 20], color="#cf222e", lw=2.2)
planes = [(5, 20), (5, 5), (25, 5)]
ax.scatter([p[0] for p in planes], [p[1] for p in planes], s=46, color="#cf222e", zorder=5,
           label="two walls meet (z = 8.66)")
ax.scatter([11], [5], s=70, marker="X", color="#0969da", zorder=6,
           label="a wall narrows to nothing beside the concave fillet (z = 8.66)")
ax.annotate("which of these is first was\nthe last bit of a level", xy=(11, 5), xytext=(14.5, 13.5),
            fontsize=9, arrowprops=dict(arrowstyle="->", color="#57606a"), color="#24292f")
ax.annotate("", xy=(5, 5), xytext=(14.4, 13.2), arrowprops=dict(arrowstyle="->", color="#57606a"))
ax.set_aspect("equal")
ax.set_xlim(-2, 36)
ax.set_ylim(-2, 27)
ax.set_title("new_roof_L_a-30: an L drafted inward at 30 deg about its bottom, from above",
             fontsize=10, loc="left")
ax.legend(frameon=False, fontsize=8, loc="upper right")
for side in ("top", "right"):
    ax.spines[side].set_visible(False)
fig.tight_layout()
fig.savefig(sys.argv[1])
