# FreeCADCmd prep_fixes.py -- the panels of the pictures of
# make_fix_pictures.sh: the drivers' results (models/*.cpp --write) in
# $W/<fix>/before and after, laid out as panels; $W/jobs.json for
# ../../fillet/pictures/render.py and $W/pictures.json for
# ../../boolean/pictures/compose.py.
import json
import os

import FreeCAD as App
import Part

V = App.Vector
W = os.environ["W"]
MAGENTA = (0.85, 0.2, 0.85)


def emit(s):
    os.write(1, (s + "\n").encode())


jobs, pictures = [], []


def panel(pic, shape, title, note, eye, center, height, colors=None, mark=False, bad=False):
    i = len(jobs)
    out = os.path.join(W, "panel%d.brep" % i)
    shape.exportBrep(out)
    png = os.path.join(W, "panel%d.png" % i)
    jobs.append(dict(brep=out, png=png, eye=eye, center=center, height=height,
                     facecolors=colors or {}, mark=mark))
    pic["panels"].append(dict(png=png, title=title, note=note, bad=bad))
    emit("PANEL %d %s / %s" % (i, pic["name"], title))


def result(stage, run):
    path = os.path.join(W, "363", stage, run + ".brep")
    return Part.read(path) if os.path.exists(path) else None


def describe(shape):
    if shape is None:
        return "refused"
    return "%s, %.4f" % ("valid" if shape.isValid() else "invalid", shape.Volume)


# #363: the issue's shape, a cylinder with a groove across its bottom under a
# chamfered top, 1 inward (Arc join, no intersection); once with the top
# removed, once with both bottoms (the issue's Thickness001).
given = Part.read(os.path.join(W, "363", "after", "groove10_chamfer_in.brep"))
flat = [i for i, f in enumerate(given.Faces) if f.Surface.TypeId == "Part::GeomPlane"]
top = max(flat, key=lambda i: given.Faces[i].CenterOfMass.z)
bottoms = [i for i in flat if abs(given.Faces[i].CenterOfMass.z) < 1e-6]
CENTER, HEIGHT = [0, 0, 7], 68
ABOVE, BELOW, SIDE = [0.9, -1.3, 1.1], [0.9, -1.3, -0.8], [0.25, -1.5, 0.35]
CAPTION = ("BRepOffsetAPI_MakeThickSolid::MakeThickSolidByJoin, -1, the Arc join and no "
           "intersection (FreeCAD's Thickness as it comes); the removed faces in magenta, faces "
           "failing their check in red. The groove is a half cylinder of radius 10.06 along y, "
           "its axis on the bottom's plane; the side meets each of its faces at both ends.")
for run, removed, what, eye, cause in (
        ("groove10_chamfer_top", [top], "the top", ABOVE,
         "the inside's side cut off at its top, the inside dropped"),
        ("groove10_chamfer_bottoms", bottoms, "both bottoms", BELOW,
         "the side lost whole, the solid inside out")):
    pic = dict(name="issue363_" + run, title="#363: a cylinder with a groove across its bottom, "
               "%s removed, 1 inward" % what, caption=CAPTION, panels=[])
    panel(pic, given, "the input", "%s (magenta) removed" % what, eye, CENTER, HEIGHT,
          {str(i): MAGENTA for i in removed})
    before, after = result("before", run), result("after", run)
    if before is not None:
        panel(pic, before, "before", describe(before) + ": " + cause, eye, CENTER, HEIGHT,
              mark=True, bad=True)
    panel(pic, after, "after", describe(after) + ", the volume booleans give", eye, CENTER,
          HEIGHT, mark=True)
    half = after.common(Part.makeBox(80, 40, 40, V(-40, 0, -5)))
    panel(pic, half, "after, cut open", "beyond y = 0: the wall 1 thick, the groove's arch "
          "inside", SIDE, CENTER, HEIGHT)
    pictures.append(pic)

# A filleted dome outward: the crease between two fillets fades out at the
# dome's corner, and its tube (the Arc join) closes to a point there. The
# tubes in orange: the faces with a degenerated edge.
ORANGE = (0.95, 0.55, 0.1)
dome = Part.read(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "boolean",
                              "models", "dome_fillet_r3.brep"))
out2 = Part.read(os.path.join(W, "dome", "after", "out2.brep"))
tubes = {str(i): ORANGE for i, f in enumerate(out2.Faces) if any(e.Degenerated for e in f.Edges)}
pic = dict(name="dome_crease_fades",
           title="A box under a B-spline dome, its edges filleted, 2 outward with the bottom removed",
           caption="BRepOffsetAPI_MakeThickSolid::MakeThickSolidByJoin, the Arc join. At each corner "
                   "of the dome two fillets meet in a mitre, a crease that fades out where both "
                   "meet the dome tangentially; the crease's tube (orange) closes to a point there. "
                   "Before, 1, 2 and 3 outward were refused.",
           panels=[])
panel(pic, dome, "the input", "the bottom (magenta) removed, 2 outward", [-0.7, -1.0, -0.6],
      [40, 25, 18], 110, {"3": MAGENTA})
panel(pic, out2, "after", "valid, %.4f, the volume booleans give; the four tubes orange"
      % out2.Volume, [-0.5, -0.9, 0.8], [40, 25, 18], 115, tubes)
panel(pic, out2, "after, at a corner", "the tube on the mitre narrows to the dome's corner and "
      "ends in a point", [-0.6, -1.0, 0.7], [0.6, 0.8, 25.0], 10, tubes, mark=True)
half = out2.common(Part.makeBox(100, 30, 60, V(-10, -5, -5)))
panel(pic, half, "after, cut open", "beyond y = 25 cut away: the wall 2 thick", [0.5, 1.2, 0.6],
      [40, 12, 15], 105)
pictures.append(pic)

# The same dome with the dome itself removed, 2 inward: tubes (orange) round
# the dome's edges, where it meets the fillets tangentially, close the wall;
# the rim left of the dome (magenta) runs round the opening.
cap = dome.Faces[8]
in2 = Part.read(os.path.join(W, "domecap", "after", "in2.brep"))


def on_tube(f):
    u0, u1, v0, v1 = f.ParameterRange
    p = f.valueAt((u0 + u1) / 2, (v0 + v1) / 2)
    return abs(Part.Vertex(p).distToShape(cap.OuterWire)[0] - 2.0) < 1e-3


def on_cap(f):
    u0, u1, v0, v1 = f.ParameterRange
    return Part.Vertex(f.valueAt((u0 + u1) / 2, (v0 + v1) / 2)).distToShape(cap)[0] < 1e-4


colors = {}
for i, f in enumerate(in2.Faces):
    if on_tube(f):
        colors[str(i)] = ORANGE
    elif on_cap(f):
        colors[str(i)] = MAGENTA
pic = dict(name="dome_cap_removed",
           title="A box under a B-spline dome, its edges filleted, 2 inward with the dome removed",
           caption="BRepOffsetAPI_MakeThickSolid::MakeThickSolidByJoin, the Arc join. The dome meets "
                   "each fillet tangentially; a tube (orange) round each of its edges closes the wall, "
                   "from the fillet's offset to the rim left of the dome (magenta). Before, 1, 2 and "
                   "2.5 inward were refused.",
           panels=[])
panel(pic, dome, "the input", "the dome (magenta) removed, 2 inward", [-0.5, -0.9, 0.8],
      [40, 25, 18], 110, {"8": MAGENTA})
panel(pic, in2, "after", "valid, %.4f, as worked numerically; the tubes orange, the rim magenta"
      % in2.Volume, [-0.5, -0.9, 0.8], [40, 25, 18], 115, colors)
panel(pic, in2, "after, at a corner", "two tubes meet in a mitre down to the fillets' offsets",
      [-0.4, -0.6, 0.9], [76.3, 46.2, 24.2], 7, colors, mark=True)
half = in2.common(Part.makeBox(100, 30, 60, V(-10, -5, -5)))
panel(pic, half, "after, cut open", "beyond y = 25 cut away: the wall 2 thick, rounded into the "
      "rim", [0.5, 1.2, 0.6], [40, 12, 15], 105)
pictures.append(pic)

# The same, outward: the tubes (orange) now stand above the dome's edges, and
# two of them touch at each corner of the dome.
out2 = Part.read(os.path.join(W, "domecapout", "after", "out2.brep"))
colors = {}
for i, f in enumerate(out2.Faces):
    if on_tube(f):
        colors[str(i)] = ORANGE
    elif on_cap(f):
        colors[str(i)] = MAGENTA
pic = dict(name="dome_cap_removed_out",
           title="A box under a B-spline dome, its edges filleted, 2 outward with the dome removed",
           caption="BRepOffsetAPI_MakeThickSolid::MakeThickSolidByJoin, the Arc join. A tube (orange) "
                   "round each of the dome's edges closes the wall, from the fillet's offset over to "
                   "the dome's edge; at each corner of the dome two tubes touch, and their section "
                   "is tangent at its end to the one's end and the other's edge. Before, 0.5 to 4 "
                   "outward were refused.",
           panels=[])
panel(pic, dome, "the input", "the dome (magenta) removed, 2 outward", [-0.5, -0.9, 0.8],
      [40, 25, 18], 110, {"8": MAGENTA})
panel(pic, out2, "after", "valid, %.4f, as worked numerically; the tubes orange"
      % out2.Volume, [-0.5, -0.9, 0.8], [40, 25, 20], 120, colors)
panel(pic, out2, "after, at a corner", "two tubes meet on a curved section, from the walls "
      "up to where the tubes touch", [-0.3, -0.7, 0.9], [76.9, 46.35, 26.1], 9, colors,
      mark=True)
half = out2.common(Part.makeBox(110, 35, 70, V(-15, -10, -5)))
panel(pic, half, "after, cut open", "beyond y = 25 cut away: the wall 2 thick, rounded over the "
      "dome's edge", [0.5, 1.2, 0.6], [40, 12, 15], 115)
pictures.append(pic)

json.dump(dict(size=[420, 420], panels=jobs), open(os.path.join(W, "jobs.json"), "w"))
json.dump(pictures, open(os.path.join(W, "pictures.json"), "w"))
emit("DONE")
os._exit(0)
