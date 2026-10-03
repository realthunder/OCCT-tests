# Regression tests for the fork's draft (BRepOffsetAPI_DraftAngle, the
# Draft package in TKOffset) fixes.
#
# Run with any FreeCAD build linked against this OCCT:
#
#     FreeCADCmd tests/fork/draft/run_tests.py
#
# Exit code is 0 when no expected-pass case fails.  Known-broken cases are
# declared XFAIL below; when one starts passing the suite prints
# UNEXPECTED-PASS so its expectation (and README.md) can be updated.
#
# The drafts go through PartDesign's Draft feature, as a user's do: FreeCAD's
# Part module has no draft of its own.
#
# See README.md for what each case covers and the history of each problem.

import math
import os
import sys
import traceback

import FreeCAD as App
import Part

HERE = os.path.dirname(os.path.abspath(__file__))
ISSUES = os.path.join(HERE, "..", "occ-issues", "models")
RELTOL = 1e-6

V = App.Vector


def emit(line):
    # FreeCAD redirects sys.stdout into its own console, which swallows
    # script output under FreeCADCmd - write straight to fd 1.
    os.write(1, (line + "\n").encode())


# Unfrozen, as any other build of FreeCAD runs (see ../fillet/run_tests.py).
App.ParamGet("User parameter:BaseApp/Preferences/Mod/Part").SetBool(
    "ImmutableShapeValues", os.environ.get("DRAFT_FREEZE", "0") != "0")

results = []  # (name, verdict, detail)


def report(name, ok, expect_fail, detail):
    if ok and not expect_fail:
        verdict = "PASS"
    elif ok and expect_fail:
        verdict = "UNEXPECTED-PASS"
    elif not ok and expect_fail:
        verdict = "XFAIL"
    else:
        verdict = "FAIL"
    results.append((name, verdict, detail))
    emit("%-32s %-16s %s" % (name, verdict, detail))


def outcome(feature):
    """What a recomputed Draft feature gave: ('error', message),
    ('invalid', volume) or ('valid', volume)."""
    states = [str(s) for s in feature.State]
    if "Invalid" in states or "Error" in states:
        return "error", "; ".join(states)
    s = feature.getPropertyByName("Shape")
    if s.isNull():
        return "error", "null shape"
    return ("valid" if s.isValid() else "invalid"), s.Volume


def judge(name, got, expect, ref_volume=None):
    """expect='valid': a valid solid, ref_volume when given.
    expect='refused': the draft fails with an error -- the geometry cannot
    be drafted by moving it alone -- and never hands back an invalid shape.
    expect='xfail': known broken (README.md)."""
    kind, value = got
    detail = ("vol=%.4f" % value) if kind != "error" else ("error: " + value)
    if kind != "error":
        detail = kind + " " + detail
    if expect == "refused":
        report(name, kind == "error", False, detail)
        return
    ok = kind == "valid"
    if ok and ref_volume is not None and abs(value - ref_volume) > RELTOL * abs(ref_volume):
        ok = False
        detail += " != %.4f" % ref_volume
    report(name, ok, expect == "xfail", detail)


# ---------------------------------------------------------------------------
# Shape cases: a Draft feature on a built shape.
# ---------------------------------------------------------------------------

def draft_case(name, shape, face, neutral, angle, expect, ref_volume=None):
    """Draft <face> of <shape> by <angle> degrees, the neutral plane that of
    the face <neutral> (faces picked by predicate), the pull direction its
    normal, as PartDesign's Draft takes it with no pull direction given."""
    doc = App.newDocument("draft_" + name.replace(".", "_"))
    try:
        base = doc.addObject("Part::Feature", "Base")
        base.Shape = shape
        body = doc.addObject("PartDesign::Body", "Body")
        body.BaseFeature = base
        doc.recompute()
        fi = [i for i, f in enumerate(shape.Faces, 1) if face(f)]
        ni = [i for i, f in enumerate(shape.Faces, 1) if neutral(f)]
        if len(fi) != 1 or len(ni) != 1:
            report(name, False, False, "picked %d faces, %d neutral" % (len(fi), len(ni)))
            return
        d = body.newObject("PartDesign::Draft", "Draft")
        d.Base = (body.BaseFeature, ["Face%d" % fi[0]])
        d.NeutralPlane = (body.BaseFeature, ["Face%d" % ni[0]])
        d.Angle = angle
        doc.recompute()
        judge(name, outcome(d), expect, ref_volume)
    except Exception:
        report(name, False, False, traceback.format_exc().splitlines()[-1])
    finally:
        App.closeDocument(doc.Name)


def plane_at(axis, value):
    def pick(f):
        if f.Surface.__class__.__name__ != "Plane":
            return False
        b = f.BoundBox
        return (abs(getattr(b, axis.upper() + "Min") - value) < 1e-9
                and abs(getattr(b, axis.upper() + "Max") - value) < 1e-9)
    return pick


def notch(bevel):
    """A 20x10x10 block, a notch [0,10]x[0,5]x[5,10] off its front top: the
    ledge z=5, hinged on the notch's back wall y=5. With <bevel>, the block's
    front top edge right of the notch is bevelled from (y=0, z=5) back to
    the top: the bevel touches the ledge at its corner (10, 0, 5) only."""
    s = Part.makeBox(20, 10, 10).cut(Part.makeBox(10, 5, 5, V(0, 0, 5)))
    if bevel:
        w = Part.Face(Part.makePolygon([V(10, 0, 5), V(10, -1, 5), V(10, -1, 11),
                                        V(10, 4.8, 11), V(10, 0, 5)])).extrude(V(11, 0, 0))
        s = s.cut(w)
    return s.removeSplitter()


# The ledge drafted about the notch's back wall: its front edge rises by
# 5 tan(a) over the notch's 10, so the draft adds a wedge of 125 tan(a).
plain = notch(False)
for a in (5, 20, 45):
    draft_case("notch_ledge_a%d" % a, plain, plane_at("z", 5), plane_at("y", 5), a, "valid",
               plain.Volume + 125 * math.tan(math.radians(a)))

# With the bevel the ledge's front corner is a vertex of four faces, the
# bevel one that the draft does not reach. The corner moves with the ledge,
# off the bevel's plane, and the bevel's edges with it: the result was
# invalid (a self-intersecting wire) at every angle. The draft would need a
# new edge there; it is refused now.
bevelled = notch(True)
for a in (5, 20, 45):
    draft_case("notch_bevel_ledge_a%d" % a, bevelled, plane_at("z", 5), plane_at("y", 5), a,
               "refused")


# ---------------------------------------------------------------------------
# realthunder/FreeCAD#334: each Draft of the document recomputed alone, from
# its base feature's stored shape (the document's recompute stops earlier,
# at Sketch006, a FreeCAD element-map problem).
# ---------------------------------------------------------------------------

def document_drafts(filename, cases):
    try:
        doc = App.openDocument(os.path.join(ISSUES, filename))
    except Exception:
        report(filename, False, False, traceback.format_exc().splitlines()[-1])
        return
    try:
        for name, obj, expect, vol in cases:
            try:
                o = doc.getObject(obj)
                o.touch()
                o.recompute()
                judge(name, outcome(o), expect, vol)
            except Exception:
                report(name, False, False, traceback.format_exc().splitlines()[-1])
    finally:
        App.closeDocument(doc.Name)


# Draft001 and Draft003 draft a ledge whose front corner a bevel touches,
# the case above. The stored Draft001 is "valid" only by a vertex tolerance
# of 27.8 (the build that saved it widened it); recomputed it was invalid.
document_drafts("issue334_draft_artifact.FCStd", [
    ("issue334_draft", "Draft", "valid", 58330.5413),
    ("issue334_draft001", "Draft001", "refused", None),
    ("issue334_draft002", "Draft002", "valid", 48090.8618),
    ("issue334_draft003", "Draft003", "refused", None),
])

# ---------------------------------------------------------------------------
# #474 Fillet003's input: a ledge top that meets a helical ramp. Drafted
# about the ledge's end wall it lifts off the ramp, which it no longer meets
# near the edge they shared: the edge's new curve is a far branch of the
# plane-ramp intersection, and the vertex's new point lies past its end.
# Extending the curve to the point failed, left the edge with a null curve,
# and FreeCAD died (a segmentation fault) at 11 to 17 deg. Refused now.
#
# The brep's shape carries a location, a quarter turn about X, which the
# Part::Feature takes as its placement. A Draft's first recompute works in
# the global frame and its later ones in the base's own: the same problem
# turned, rounded differently, and only there does the extension fail. So
# the Draft is recomputed once first, as the task panel does before an
# angle is typed. A build without the fix takes this suite down here.
# ---------------------------------------------------------------------------

def ramp_ledge_drafts(angles):
    doc = App.newDocument("draft_issue474")
    try:
        shape = Part.read(os.path.join(HERE, "..", "fillet", "models",
                                       "issue474_fillet003_base.brep"))
        base = doc.addObject("Part::Feature", "Base")
        base.Shape = shape
        body = doc.addObject("PartDesign::Body", "Body")
        body.BaseFeature = base
        doc.recompute()
        d = body.newObject("PartDesign::Draft", "Draft")
        # Face3 the ledge top (z=13, x in [-17,-9]), Face10 its end wall x=-17
        d.Base = (body.BaseFeature, ["Face3"])
        d.NeutralPlane = (body.BaseFeature, ["Face10"])
        d.Angle = 1
        doc.recompute()
        for a in angles:
            d.Angle = a
            doc.recompute()
            judge("issue474_ramp_ledge_a%d" % a, outcome(d), "refused")
    except Exception:
        report("issue474_ramp_ledge", False, False, traceback.format_exc().splitlines()[-1])
    finally:
        App.closeDocument(doc.Name)


ramp_ledge_drafts((11, 15, 17))

# ---------------------------------------------------------------------------
counts = {}
for _, verdict, _ in results:
    counts[verdict] = counts.get(verdict, 0) + 1
if counts.get("UNEXPECTED-PASS"):
    emit("NOTE: xfail case(s) now pass - promote them to 'valid' with their volume.")
emit("summary: " + "  ".join("%s=%d" % kv for kv in sorted(counts.items())))
sys.exit(1 if counts.get("FAIL") else 0)
