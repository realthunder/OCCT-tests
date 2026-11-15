# vertex_draw.py <one run> <another run> <now> <out.png>: sec 72's picture from
# three files of vertex_dump.py -- the offset's four edges at the vertex, and
# the vertex. Needs matplotlib (the FreeCAD conda env has it).
import json, sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle

runs = [json.load(open(p)) for p in sys.argv[1:4]]
titles = ["before, one run", "before, another run of the same program", "now, every run"]
fig = plt.figure(figsize=(17, 5.2), dpi=110)
ax = fig.add_subplot(1, 4, 1, projection="3d")
d = runs[2]
for pts in d["edges"]:
    ax.plot([p[0] for p in pts], [p[1] for p in pts], [p[2] for p in pts], color="#555555", lw=0.6)
v = d["vertex"]
ax.scatter([v[0]], [v[1]], [v[2]], color="#d81b60", s=60, depthshade=False)
ax.set_title("the coil with its fillet, offset by 0.2\n(the vertex in magenta)", fontsize=10)
ax.view_init(elev=18, azim=-118)
ax.set_box_aspect((1, 1, 1))
ax.set_axis_off()
cols = {"Line": "#1565c0", "BSplineCurve": "#2e7d32"}
for k, (d, t) in enumerate(zip(runs, titles)):
    ax = fig.add_subplot(1, 4, k + 2)
    v = d["vertex"]
    for n in d["near"]:
        pts = n["pts"]
        # the edges all run in the plane y = -0.2 here or leave it; shown in x and z
        ax.plot([p[0] for p in pts], [p[2] for p in pts], color=cols.get(n["type"], "#2e7d32"),
                lw=1.6, label="%s, length %.2f" % ("line" if n["type"] == "Line" else "spline",
                                                   n["len"]))
        ax.plot([pts[0][0]], [pts[0][2]], marker="s", ms=5, color=cols.get(n["type"], "#2e7d32"))
    ax.add_patch(Circle((v[0], v[2]), v[3], fill=False, ec="#d81b60", lw=1.0, ls="--"))
    ax.plot([v[0]], [v[2]], marker="o", ms=9, color="#d81b60")
    ax.set_xlim(-13.004, -12.9945)
    ax.set_ylim(10.8119 - 0.00475, 10.8119 + 0.00475)
    ax.set_aspect("equal")
    ax.set_title("%s\nvertex at x = %.4f, tolerance %.5f" % (t, v[0], v[3]), fontsize=10)
    ax.set_xlabel("x")
    ax.set_ylabel("z")
    ax.ticklabel_format(useOffset=False, style="plain")
    ax.tick_params(labelsize=7)
    ax.grid(True, lw=0.3, color="#cccccc")
    if k == 0:
        ax.legend(fontsize=7, loc="lower right")
fig.suptitle("makeOffsetShape(0.2, 1e-3) of issue474_Fillet: four edges end here, two at x = -13 "
             "and two at x = -12.9985; squares are the edges' ends, the dot the vertex, dashed its "
             "tolerance",
             fontsize=10)
fig.tight_layout(rect=(0, 0, 1, 0.94))
fig.savefig(sys.argv[4])
