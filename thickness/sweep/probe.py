# probe.py -- one thickness run of a survey shape, with what the fork shows of
# its way there. The first thing to run on a fault survey.py or the suite
# reports.
#
#   W=<key>[:<edge>]  a shape of survey.py; with <edge>, a vertex at the
#                     middle of that edge (1-based)
#   ORDER=3412        the solid with its faces in that order
#   PLACE=placed|turned
#   F=<face> OFF=<offset> JOIN=0|2 INTER=0|1 FREEZE=0|1
#                     the face removed (1-based, counted on the shape as
#                     made, before the vertex and the order), the offset,
#                     the join (0 Arc, 2 Intersection), intersection mode,
#                     ImmutableShapeValues; defaults 1, 0.5, 0, 0, 1
#   DESC=1            list the shape's faces and edges, each edge with its
#                     pcurve's ends and whether it is closed on the face
#   FACES=1           list the result's faces
#   KEYS="BRepOffset_MakeOffset.cxx BRepAlgo_Loop.cxx"  (or "*")
#                     the source files whose SHOW_TOPO_SHAPE dumps are
#                     taken (Part.showShapeOCCT); each dump is listed in
#                     the order it was made, with its name
#   ONLY=<regex>      of the dumps, those whose name matches
#   SAVE=<dir>        an absolute directory: the result and every dump
#                     listed, as BREP files
#
#   W=luneball ORDER=3412 F=1 JOIN=2 KEYS="*" ONLY=CellBeyond FreeCADCmd probe.py
import os
import re
import sys

import FreeCAD
import Part

os.environ["SURVEY_AS_MODULE"] = "1"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import survey  # noqa: E402

out = survey.out


def desc(sh):
    bb = sh.BoundBox
    d = "%s f%d e%d v%d (%.3f %.3f %.3f)-(%.3f %.3f %.3f)" % (
        sh.ShapeType, len(sh.Faces), len(sh.Edges), len(sh.Vertexes),
        bb.XMin, bb.YMin, bb.ZMin, bb.XMax, bb.YMax, bb.ZMax)
    if sh.ShapeType == "Edge":
        try:
            c = sh.Curve
            d += " %s [%.4f %.4f]" % (c.__class__.__name__, sh.FirstParameter, sh.LastParameter)
            if len(sh.Vertexes) > 1:
                d += " ends %s %s" % tuple("(%.4f %.4f %.4f)" % tuple(v.Point) for v in sh.Vertexes[:2])
            if hasattr(c, "Radius"):
                d += " r=%.4f" % c.Radius
        except Exception as e:
            d += " (no curve: %s)" % e
    elif sh.ShapeType == "Face":
        d += " %s area %.5f wires %d" % (sh.Surface.__class__.__name__, sh.Area, len(sh.Wires))
    elif sh.ShapeType == "Vertex":
        d += " at (%.4f %.4f %.4f) tol %.1e" % (sh.Point.x, sh.Point.y, sh.Point.z, sh.Tolerance)
    return d


def describe(s):
    for fi, f in enumerate(s.Faces):
        out("F%d %s area %.4f, uv %s" % (fi + 1, f.Surface.__class__.__name__, f.Area,
                                         " ".join("%.4f" % x for x in f.ParameterRange)))
        for e in f.Edges:
            idx = [i for i, g in enumerate(s.Edges) if g.isSame(e)][0] + 1
            try:
                c, a, b = f.curveOnSurface(e)
                pc = "(%.4f %.4f)->(%.4f %.4f)" % (c.value(a).x, c.value(a).y, c.value(b).x, c.value(b).y)
            except Exception as ex:
                pc = "no pcurve: %s" % ex
            out("  E%d %s closed=%s degenerated=%s %s" % (idx, e.Orientation, e.isSeam(f), e.Degenerated, pc))


# before any shape is made: a value is frozen, or not, as it is made
FreeCAD.ParamGet("User parameter:BaseApp/Preferences/Mod/Part").SetBool(
    "ImmutableShapeValues", os.environ.get("FREEZE", "1") == "1")
key, _, edge = os.environ.get("W", "box").partition(":")
fi = int(os.environ.get("F", "1")) - 1
s = survey.place(survey.SHAPES[key](), os.environ.get("PLACE"))
if edge:
    label, s, order = [v for v in survey.variants_split(s) if v[0] == "E" + edge][0]
    fi = order[fi]
if os.environ.get("ORDER"):
    o = [int(c) - 1 for c in os.environ["ORDER"]]
    s = Part.Solid(Part.Shell([s.Faces[i] for i in o]))
    fi = o.index(fi)
if os.environ.get("DESC"):
    describe(s)
off = float(os.environ.get("OFF", "0.5"))
join = int(os.environ.get("JOIN", "0"))
doc = FreeCAD.newDocument("Probe")
for k in os.environ.get("KEYS", "").split():
    Part.showShapeOCCT(k)
save = os.environ.get("SAVE")
try:
    r = s.makeThickness([s.Faces[fi]], off, 1e-7, os.environ.get("INTER", "0") == "1", False, 0, join)
    out("RESULT valid=%s %s shells=%d faces=%d volume=%.4f" % (
        r.isValid(), r.ShapeType, len(r.Shells), len(r.Faces), r.Volume))
    if os.environ.get("FACES"):
        for i, f in enumerate(r.Faces):
            out("  R%d %s valid=%s" % (i + 1, desc(f), f.isValid()))
    if save:
        r.exportBrep(save + "/result.brep")
except Exception as e:
    out("THREW " + str(e).strip().splitlines()[-1])
only = re.compile(os.environ.get("ONLY", "."))
for n, o in enumerate(doc.Objects):
    name = o.Label.rsplit("_", 2)[0]
    if only.search(name):
        out("%4d %-28s %s" % (n + 1, name, desc(o.Shape)))
        if save:
            o.Shape.exportBrep("%s/%04d_%s.brep" % (save, n + 1, name))
os._exit(0)
