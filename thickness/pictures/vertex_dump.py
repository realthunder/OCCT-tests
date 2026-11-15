# vertex_dump.py: sec 72's picture, its numbers. The offset of #474's coil
# with its fillet by 0.2: its edges as polylines, the vertex near AT with its
# tolerance, and the 0.03 of each of its edges next to it, as JSON.
#   OUT=<file.json> FreeCADCmd vertex_dump.py
# Before the fix (6a0d5260bf) the vertex is at one of two places by the run:
# preload a TKOffset built from the commit before it (LD_PRELOAD) and run
# until both have come. vertex_draw.py draws three such files.
import os, sys, json
import FreeCAD as App
import Part
HERE = os.path.dirname(os.path.abspath(__file__))
T = os.path.join(HERE, "..", "..")
shape = Part.read(os.path.join(T, "draft", "sweep", "shapes", "issue474_Fillet.brep"))
r = shape.makeOffsetShape(0.2, 1e-3)
at = App.Vector(-13.0, -0.2, 10.811873)
out = {"valid": r.isValid(), "edges": [], "near": [], "input": []}
for v in r.Vertexes:
    if v.Point.distanceToPoint(at) < 0.05:
        out["vertex"] = [v.Point.x, v.Point.y, v.Point.z, v.Tolerance]
        for e in r.Edges:
            if any(w.isSame(v) for w in e.Vertexes):
                f, l = e.FirstParameter, e.LastParameter
                pf, pl = e.valueAt(f), e.valueAt(l)
                # 400 points on the 0.03 of length next to the vertex
                near_first = pf.distanceToPoint(v.Point) < pl.distanceToPoint(v.Point)
                pts = []
                for i in range(401):
                    t = i / 400.0 * min(1.0, 0.03 / e.Length)
                    u = f + (l - f) * t if near_first else l - (l - f) * t
                    p = e.valueAt(u)
                    pts.append([p.x, p.y, p.z])
                out["near"].append({"type": e.Curve.__class__.__name__, "tol": e.Tolerance,
                                    "len": e.Length, "pts": pts})
for e in r.Edges:
    out["edges"].append([[p.x, p.y, p.z] for p in e.discretize(Deflection=0.02)])
for e in shape.Edges:
    out["input"].append([[p.x, p.y, p.z] for p in e.discretize(Deflection=0.02)])
json.dump(out, open(os.environ["OUT"], "w"))
print("vertex", out.get("vertex"), "edges on it", len(out["near"]))
sys.stdout.flush(); os._exit(0)
