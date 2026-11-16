# scan.py -- the probe's shapes, every face removed in turn over a run of
# thicknesses (README.md sec 84): a fault that shows at one thickness and not
# at its neighbours is not met at 0.5 and 1. One shape a run:
#   SHAPE  its name in shapes.py      OUT    the file the lines go to
#   SET    2: the shapes of shapes2.py; 3: of shapes3.py
#   STEP, COUNT  the thicknesses are STEP, 2 STEP ... COUNT STEP, either way
#                (0.05 and 30)
#   JOIN   0 (Arc) or 2 (Intersection)    TOL    the thickness' tolerance, 1e-7
# A line a run: "<shape> f<face> <thickness>: made <volume>", "invalid
# <volume>" or "refused". The shape is made anew for every run. islands.py
# reads the files.
import FreeCAD, Part, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from shapes import SHAPES

if os.environ.get("SET", "") == "2":
    from shapes2 import SHAPES
if os.environ.get("SET", "") == "3":
    from shapes3 import SHAPES

name = os.environ["SHAPE"]
step = float(os.environ.get("STEP", "0.05"))
count = int(os.environ.get("COUNT", "30"))
join = int(os.environ.get("JOIN", "0"))
tol = float(os.environ.get("TOL", "1e-7"))
out = open(os.environ["OUT"], "w")
for fi in range(len(SHAPES[name]().Faces)):
    for sign in (1, -1):
        for i in range(1, count + 1):
            t = sign * i * step
            s = SHAPES[name]()
            try:
                r = s.makeThickness([s.Faces[fi]], t, tol, False, False, 0, join)
                line = "%s %.4f" % ("made" if r.isValid() else "invalid", r.Volume)
            except Exception:
                line = "refused"
            out.write("%s f%d %+.2f: %s\n" % (name, fi + 1, t, line))
            out.flush()
out.write("# done\n")
out.close()
