"""The figure of sec 67: #360's plate, its top removed 4 inward (Arc join,
intersection on), seen from above -- the result's edges, and the vertices
that lie between just two of them, before sec 67 and after it. Run with
FreeCADCmd, given the two results as BRep files (corpus/tools/thk writes one
with OUT=<file>: `thk models/issue360_plate.brep -4 0 1 5`, on the fork
before `JoinEdgePieces` and on the fork now):

    BEFORE=before.brep AFTER=after.brep PNG=models/pictures/issue360_plate_edge_pieces.png \\
        FreeCADCmd pictures/edge_pieces.py
"""
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

import Part


def load(path):
    shape = Part.Shape()
    shape.read(path)
    lines = [[(p.x, p.y) for p in e.discretize(12)] for e in shape.Edges]
    between = [v.Point for v in shape.Vertexes if len(shape.ancestorsOfType(v, Part.Edge)) == 2]
    return shape, lines, between


fig, axes = plt.subplots(1, 2, figsize=(11.0, 5.4), dpi=150)
for ax, key, title in ((axes[0], "BEFORE", "fork before sec 67"), (axes[1], "AFTER", "fork after")):
    shape, lines, between = load(os.environ[key])
    for line in lines:
        ax.plot([p[0] for p in line], [p[1] for p in line], color="#5b6b82", linewidth=0.5)
    if between:
        ax.plot([p.x for p in between], [p.y for p in between], linestyle="none", marker="o",
                markersize=2.6, color="#c0504d", label="a vertex between two pieces of one edge")
        ax.legend(frameon=False, fontsize=8, loc="upper center", bbox_to_anchor=(0.5, -0.02))
    ax.set_title("%s: %d edges, %d vertices, %d between two edges"
                 % (title, len(shape.Edges), len(shape.Vertexes), len(between)), fontsize=9,
                 loc="left")
    ax.set_aspect("equal")
    ax.axis("off")
fig.suptitle("#360's plate, its top removed, 4 inward: the edges of the result, from above",
             fontsize=11, x=0.01, ha="left")
fig.tight_layout()
fig.savefig(os.environ["PNG"])
os._exit(0)
