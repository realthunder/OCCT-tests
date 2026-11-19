# nurbs.py -- the probe's shapes turned to B-splines (Shape.toNurbs), every
# face removed in turn, 0.5 either way with the Arc join, each held against
# the same run on the shape as it is (README.md sec 89). The B-spline twin is
# the same solid: its thick solid is the analytic one's. One shape a run:
#   SHAPE  its name      MOD  shapes, shapes2 or shapes3      OUT  the file
#   TS     the thicknesses, "0.5 -0.5"
#   THICK_FIX_LEVEL  the fork's offset fix level the runs are made at (0)
# A line a run: "same" where both are valid and of one volume (to 1e-4 of it),
# "DIFFERENT" where both are valid and not, "refused" or "INVALID" for the
# twin's where the analytic run is valid, "noref" where that one is not.
import FreeCAD, Part, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
from fix_level import from_env as _fix_level_from_env

_fix_level_from_env()
mod = __import__(os.environ.get("MOD", "shapes"))
name = os.environ["SHAPE"]
out = open(os.environ["OUT"], "w")


def one(s, fi, t):
    try:
        r = s.makeThickness([s.Faces[fi]], t, 1e-7, False, False, 0, 0)
        return ("valid" if r.isValid() else "INVALID", r.Volume)
    except Exception:
        return ("refused", 0.0)


a = mod.SHAPES[name]()
n = a.toNurbs()
if len(n.Faces) != len(a.Faces):
    out.write("%s faces differ: %d analytic, %d nurbs\n" % (name, len(a.Faces), len(n.Faces)))
    out.close()
    sys.exit()
for fi in range(len(a.Faces)):
    for t in [float(x) for x in os.environ.get("TS", "0.5 -0.5").split()]:
        ra = one(mod.SHAPES[name](), fi, t)
        rn = one(mod.SHAPES[name]().toNurbs(), fi, t)
        if ra[0] != "valid":
            verdict = "noref"
        elif rn[0] == "valid" and abs(rn[1] - ra[1]) <= 1e-4 * max(1.0, abs(ra[1])):
            verdict = "same"
        elif rn[0] == "valid":
            verdict = "DIFFERENT"
        else:
            verdict = rn[0]
        out.write("%s f%d %s %g: %s | analytic %s %.4f | nurbs %s %.4f\n" % (
            name, fi + 1, a.Faces[fi].Surface.__class__.__name__, t, verdict,
            ra[0], ra[1], rn[0], rn[1]))
        out.flush()
out.write("# done\n")
out.close()
