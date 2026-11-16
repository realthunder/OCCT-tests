# crease_dump.py: sec 74's picture, its numbers. #613's part with its top and
# bottom removed, 2 inward and 2 outward, at the fork's offset fix levels 3
# and 4: each face's section with the plane y = 0 (x > 0) as a polyline with
# the face's surface, and the widest gap between an edge's end and its vertex
# (../../loose_ends.py), as JSON.
#   OUT=<file.json> FreeCADCmd crease_dump.py
# crease_draw.py draws the file.
import os, sys, json
import FreeCAD as App
import Part
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", ".."))
from fix_level import set_offset_fix_level
from loose_ends import widest
shape = Part.read(os.path.join(HERE, "..", "models", "issue613_fillet.brep"))
out = {"input": [], "runs": []}


PLANE = Part.Plane(App.Vector(), App.Vector(0, 1, 0)).toShape(-100, 100, -100, 100)


def section(s):
    """[[surface, [[x, z], ...]], ...]: each face's section with y = 0, x > 0"""
    lines = []
    for f in s.Faces:
        for e in f.section(PLANE).Edges:
            pts = [[p.x, p.z] for p in e.discretize(Deflection=1e-5)]
            if max(p[0] for p in pts) > 0:
                lines.append([f.Surface.__class__.__name__, pts])
    return lines


out["input"] = section(shape)
for value in (-2.0, 2.0):
    for level in (3, 4):
        previous = set_offset_fix_level(level)
        r = shape.makeThickness([shape.Faces[6], shape.Faces[15]], value, 1e-7, False, False, 0, 0)
        set_offset_fix_level(previous)
        gap = widest(r)
        out["runs"].append({"value": value, "level": level, "valid": r.isValid(),
                            "volume": r.Volume, "gap": gap, "section": section(r)})
        print("value %g level %d: valid %s volume %.4f widest gap %.4g" % (
            value, level, r.isValid(), r.Volume, gap))
json.dump(out, open(os.environ["OUT"], "w"))
sys.stdout.flush(); os._exit(0)
