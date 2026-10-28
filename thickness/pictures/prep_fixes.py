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

json.dump(dict(size=[420, 420], panels=jobs), open(os.path.join(W, "jobs.json"), "w"))
json.dump(pictures, open(os.path.join(W, "pictures.json"), "w"))
emit("DONE")
os._exit(0)
