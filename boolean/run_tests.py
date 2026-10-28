# Regression tests for the fork's fixes met through the general fuse and the
# booleans (BOPAlgo and what it calls).
#
# Run with any FreeCAD build linked against this OCCT:
#
#     FreeCADCmd tests/fork/boolean/run_tests.py
#
# Exit code is 0 when no case fails. See README.md for what each case covers;
# models/ has a C++ driver of each fix, run against an install.

import math
import os
import sys
import traceback

import FreeCAD as App
import Part

V = App.Vector
HERE = os.path.dirname(os.path.abspath(__file__))


def emit(line):
    # FreeCAD redirects sys.stdout into its own console, which swallows
    # script output under FreeCADCmd - write straight to fd 1.
    os.write(1, (line + "\n").encode())


# Every case here pins what the fork does. On another OCCT -- upstream's, as
# FreeCAD can load it -- they fail for want of the fork, so the suite says so
# and runs nothing. The fork is found as FreeCAD finds it, by a C function of
# its TKBRep; a FreeCAD from before Part.hasOCCTFunction runs the suite.
if hasattr(Part, "hasOCCTFunction") and not Part.hasOCCTFunction("TKBRep", "SetFuncShowTopoShape"):
    emit("SKIP: not the OCCT fork (TKBRep has no SetFuncShowTopoShape)")
    emit("summary: SKIP=1")
    sys.stdout.flush()
    os._exit(0)

results = []


def report(name, ok, what):
    results.append(ok)
    emit("%-44s %s  %s" % (name, "PASS" if ok else "FAIL", what))


def guarded(fix):
    # a fix's cases; an exception among them is a FAIL, not the end of the
    # suite (FreeCADCmd ends a script that raises with exit code 0)
    try:
        fix()
    except Exception:
        report(fix.__name__, False, "raised: " + traceback.format_exc().splitlines()[-1])


# #64: a cylinder (r 25, h 35) split by the plane y = k (z - 34.36), tilted
# off its axis, with a fuzzy value; the cylinder's seam at the cut (x = 25,
# y = 0) or turned 90 deg away. Two valid solids each time; with the seam
# away, each within 1% of its volume at no fuzzy value. (With the seam at
# the cut a fuzzy value merges the plane's crossing of the top rim into the
# seam's vertex there, valid within tolerances but read short by the volume
# integrals: only the two valid solids are asked. README.md, #64.)
def split(k, fuzzy, angle):
    cyl = Part.makeCylinder(25, 35)
    cyl.rotate(V(), V(0, 0, 1), angle)
    zc = 34.36
    pts = [V(-40, k * (-5 - zc), -5), V(-40, k * (40 - zc), 40), V(40, k * (40 - zc), 40),
           V(40, k * (-5 - zc), -5)]
    plane = Part.Face(Part.makePolygon(pts + pts[:1]))
    res = cyl.generalFuse([plane], fuzzy)[0]
    return res if res.isValid() else None, sorted(s.Volume for s in res.Solids)


def issue064():
    for k in (0.1, 0.35, 1.0):
        for angle in (0, 90):
            ref = split(k, 0.0, angle)[1]
            for fuzzy in (0.0, 0.1, 0.5, 1.0):
                res, vols = split(k, fuzzy, angle)
                ok = res is not None and len(vols) == 2 and len(ref) == 2
                if ok and not (angle == 0 and fuzzy > 0):
                    ok = all(abs(v - r) <= 1e-2 * r for v, r in zip(vols, ref))
                report("issue064_k%g_seam%d_fuzzy%g" % (k, angle, fuzzy), ok,
                       ("invalid " if res is None else "") + " ".join("%.4f" % v for v in vols))


guarded(issue064)


# #580: #580's Pad003, whose planar face 19 holds a degenerated edge with no
# 3D curve, mirrored and moved with a copy, and fused with its mirror: each
# valid, the copies of its volume, the fuse twice it less the common. The
# copy used to drop that edge's pcurve (README.md, #580).
def solid_case(name, shape, want):
    ok = shape.isValid() and abs(shape.Volume - want) <= 1e-6 * want
    invalid = "" if shape.isValid() else "invalid "
    report(name, ok, "%svol %.4f (want %.4f)" % (invalid, shape.Volume, want))


def issue580():
    pad = Part.read(os.path.join(HERE, "models", "issue580_pad003.brep"))
    v0 = pad.Volume
    mirrored = pad.mirror(V(0, 0, 0), V(0, 1, 0))
    solid_case("issue580_mirror", mirrored, v0)
    moved = pad.copy()
    move = App.Placement(V(1, 2, 3), App.Rotation(V(1, 0, 0), math.degrees(0.7))).toMatrix()
    moved.transformShape(move, True)
    solid_case("issue580_moved_copy", moved, v0)
    solid_case("issue580_fuse_mirror", pad.fuse(mirrored), 2 * v0 - pad.common(mirrored).Volume)


guarded(issue580)

# #613: a cylinder's or a cone's face, a whole turn with its seam d off
# u = 0, cut by the plane z = 0: the section is the whole circle. With the
# seam's vertex within tolerance of the circle's end (d 1e-8, 2e-8) the
# section was empty (README.md, #613).
def seam_surface(kind):
    if kind == "cylinder":
        s = Part.Cylinder()
        s.Radius = 21.2
    else:
        s = Part.Cone()
        s.SemiAngle = 0.2
        s.Radius = 21.2
    s.Center = V(0, 0, -5)
    s.Axis = V(0, 0, 1)
    return s


def issue613():
    for kind, want in (("cylinder", 2 * math.pi * 21.2),
                       ("cone", 2 * math.pi * (21.2 + 5 * math.tan(0.2)))):
        surf = seam_surface(kind)
        for d in (0.0, 1e-9, 1e-8, 2e-8, 5e-8, 1e-6):
            face = surf.toShape(d, d + 2 * math.pi, 0.0, 10.0)
            plane = Part.makePlane(100, 100, V(-50, -50, 0))
            sec = face.section(plane)
            length = sum(e.Length for e in sec.Edges)
            ok = sec.Edges and abs(length - want) <= 1e-6 * want
            report("issue613_%s_seam_%g" % (kind, d), bool(ok),
                   "%d edge(s), length %.6f (want %.6f)" % (len(sec.Edges), length, want))


guarded(issue613)

failed = results.count(False)
emit("---")
emit("summary: PASS=%d%s" % (results.count(True), "  FAIL=%d" % failed if failed else ""))
sys.stdout.flush()
os._exit(1 if failed else 0)
