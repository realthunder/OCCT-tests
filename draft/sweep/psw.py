# One shape's cases through PartDesign: SHAPE, CASES (face neutral angle per
# line), METHOD (New/Classic/Auto), STOP (1/0), PROP (TangentPropagation, 1/0).
# One line per case: the case,
# ok:vol:faces:bopclean | LOOSE:vol:faces:bopclean:gap | BAD:... | FAIL(..),
# the time of the second recompute. LOOSE is valid, but an edge's curve ends
# farther from its vertex than ten times the edge's tolerance, 1e-4 and any
# gap of the input's own (../../loose_ends.py).
import os, sys, time
import FreeCAD as App
import Part

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
from loose_ends import loose, widest  # noqa: E402


def emit(s):
    os.write(1, ("\n" + s + "\n").encode())


S0 = Part.read(os.environ["SHAPE"])
inloose = widest(S0)  # a result may be as loose as its input
method = os.environ.get("METHOD", "New")
stop = os.environ.get("STOP", "1") == "1"
prop = os.environ.get("PROP", "1") == "1"
doc = App.newDocument("sweep")
base = doc.addObject("Part::Feature", "Base")
base.Shape = S0
body = doc.addObject("PartDesign::Body", "Body")
body.BaseFeature = base
doc.recompute()
for line in open(os.environ["CASES"]):
    w = line.split()
    if len(w) < 3:
        continue
    f, n, a = int(w[0]), int(w[1]), float(w[2])
    d = body.newObject("PartDesign::Draft", "Draft")
    try:
        d.Base = (base, ["Face%d" % f])
        d.NeutralPlane = (base, ["Face%d" % n])
        d.Angle = a
        d.Method = method
        d.StopAtBody = stop
        d.TangentPropagation = prop
        doc.recompute()
        d.touch()
        t = time.time()
        doc.recompute()
        dt = time.time() - t
        st = [str(s) for s in d.State]
        r = d.Shape
        if "Invalid" in st or "Error" in st or r.isNull():
            res = "FAIL(%s)" % d.getStatusString().replace(" ", "_")[:160]
        else:
            clean = 1
            try:
                r.check(True)
            except Exception:
                clean = 0
            gap = loose(r, inloose)[0] if r.isValid() else 0.0
            res = "%s:%.6f:%d:%d" % ("BAD" if not r.isValid() else "LOOSE" if gap else "ok",
                                     r.Volume, len(r.Faces), clean)
            if gap:
                res += ":%.3g" % gap
    except Exception as e:
        dt = 0
        res = "FAIL(exc_%s)" % str(e).replace(" ", "_")[:60]
    body.removeObject(d)
    doc.removeObject(d.Name)
    emit("%d %d %s %s %.2fs" % (f, n, w[2], res, dt))
emit("END")
