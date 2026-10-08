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


def classic(draft):
    """The kernel's own draft: a FreeCAD whose Draft has a Method retries a
    failed draft on the refined base by default, which is not this suite's
    subject (FreeCAD's TestDraft covers it)."""
    if "Method" in draft.PropertiesList:
        draft.Method = "Classic"


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


def judge(name, got, expect, ref_volume=None, feature=None):
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
    if expect.startswith("refused:"):
        # refused, the message naming why
        why = expect.split(":", 1)[1]
        msg = feature.getStatusString() if feature is not None else ""
        report(name, kind == "error" and why in msg, False,
               detail if why in msg else detail + " (" + msg + ")")
        return
    ok = kind == "valid"
    if ok and ref_volume is not None and abs(value - ref_volume) > RELTOL * abs(ref_volume):
        ok = False
        detail += " != %.4f" % ref_volume
    report(name, ok, expect == "xfail", detail)


# ---------------------------------------------------------------------------
# Shape cases: a Draft feature on a built shape.
# ---------------------------------------------------------------------------

def draft_case(name, shape, face, neutral, angle, expect, ref_volume=None, method=None,
               stop=True, reversed=False, neutral_shape=None):
    """Draft <face> of <shape> by <angle> degrees, the neutral plane that of
    the face <neutral> (faces picked by predicate), the pull direction its
    normal, as PartDesign's Draft takes it with no pull direction given.
    <face> with an attribute `many` is a function of the shape giving the
    indices of several faces. <method>: the Draft's Method (the classic
    draft when None), <stop> its StopAtBody. <neutral_shape>: a shape whose
    first face is the neutral plane, instead of a face of <shape>."""
    doc = App.newDocument("draft_" + name.replace(".", "_"))
    try:
        base = doc.addObject("Part::Feature", "Base")
        base.Shape = shape
        body = doc.addObject("PartDesign::Body", "Body")
        body.BaseFeature = base
        doc.recompute()
        many = getattr(face, "many", False)
        fi = face(shape) if many else [i for i, f in enumerate(shape.Faces, 1) if face(f)]
        if neutral_shape is None:
            ni = [i for i, f in enumerate(shape.Faces, 1) if neutral(f)]
        else:
            ni = [1]
        if not fi or (len(fi) != 1 and not many) or len(ni) != 1:
            report(name, False, False, "picked %d faces, %d neutral" % (len(fi), len(ni)))
            return
        d = body.newObject("PartDesign::Draft", "Draft")
        d.Base = (body.BaseFeature, ["Face%d" % i for i in fi])
        if neutral_shape is None:
            d.NeutralPlane = (body.BaseFeature, ["Face%d" % ni[0]])
        else:
            plane = doc.addObject("Part::Feature", "NeutralPlane")
            plane.Shape = neutral_shape
            d.NeutralPlane = (plane, ["Face1"])
        d.Angle = angle
        d.Reversed = reversed
        if method is None:
            classic(d)
        else:
            d.Method = method
            d.StopAtBody = stop
        doc.recompute()
        judge(name, outcome(d), expect, ref_volume, d)
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
# At 45 deg the front edge reaches the block's top and the notch's front
# edge shrinks to nothing: the result held a zero-length edge (invalid once
# written and read back), refused now. Past 45 it was refused already.
plain = notch(False)
for a in (5, 20, 44):
    draft_case("notch_ledge_a%d" % a, plain, plane_at("z", 5), plane_at("y", 5), a, "valid",
               plain.Volume + 125 * math.tan(math.radians(a)))
draft_case("notch_ledge_a45", plain, plane_at("z", 5), plane_at("y", 5), 45, "refused")

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
                classic(o)
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

def ramp_ledge_drafts(angles, method=None):
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
        if method is None:
            classic(d)
        else:
            d.Method = method
        doc.recompute()
        for a in angles:
            d.Angle = a
            doc.recompute()
            if method is None:
                judge("issue474_ramp_ledge_a%d" % a, outcome(d), "refused")
            else:
                # the ramp extended meets the lifted ledge again: the wedge
                # under the 8 x 4 ledge hinged at its end, 128 tan(a)
                judge("new_issue474_ramp_ledge_a%d" % a, outcome(d), "valid",
                      shape.Volume + 128 * math.tan(math.radians(a)))
    except Exception:
        report("issue474_ramp_ledge", False, False, traceback.format_exc().splitlines()[-1])
    finally:
        App.closeDocument(doc.Name)


ramp_ledge_drafts((11, 15, 17))

# ---------------------------------------------------------------------------
# The sweep's invalid drafts (2026-10-04): a draft that needs a change of
# topology is refused, and a vertex its edges pass by a hair is given the
# tolerance to cover it. See README.md.
# ---------------------------------------------------------------------------

def brep_case(name, path, face, neutral, angle, expect, ref_volume=None):
    """draft_case on a stored shape, its faces given by index."""
    shape = Part.read(path)
    draft_case(name, shape, lambda f, i=face: f.isSame(shape.Faces[i - 1]),
               lambda f, i=neutral: f.isSame(shape.Faces[i - 1]), angle, expect, ref_volume)


def slot(depth):
    """A 20 cube, a 4x6 slot 2 off its front wall y=0, <depth> deep from the top."""
    return Part.makeBox(20, 20, 20).cut(
        Part.makeBox(4, 6, depth, V(8, 2, 20 - depth))).removeSplitter()


# The slot's front wall y=2 drafted about the slot's floor: its top swings
# toward the block's front by 18 tan(a), a wedge of 4 * 18^2 tan(a) / 2 out of
# the 2 thick wall. Past 2/18 (6.3 deg) it would break through the front;
# the result was invalid (the top face's wires crossing), refused now.
deep = slot(18)
draft_case("slot_wall_a5", deep, plane_at("y", 2), plane_at("z", 2), 5, "valid",
           deep.Volume - 2 * 18 * 18 * math.tan(math.radians(5)))
for a in (15, 30):
    draft_case("slot_wall_a%d" % a, deep, plane_at("y", 2), plane_at("z", 2), a, "refused")


def split_floor():
    """A prism whose front wall y=0 (x in [10,20]) meets a slanted wall at
    (10,0), the floor and top split in coplanar pieces along x=10 from that
    corner: two solids fused, not refined."""
    p = Part.Face(Part.makePolygon([V(0, -5, 0), V(10, 0, 0), V(10, 10, 0), V(0, 10, 0),
                                    V(0, -5, 0)])).extrude(V(0, 0, 5))
    return p.fuse(Part.makeBox(10, 10, 5, V(10, 0, 0)))


# The front wall drafted about the end wall x=20: the corner at (10,0)
# slides along the slanted wall, off the split edge x=10, which the draft
# leaves alone. The result needs the slanted wall's edges to cross the
# split; it was invalid, refused now.
split = split_floor()
draft_case("split_floor_corner_a5", split, plane_at("y", 0), plane_at("x", 20), 5, "refused")

# A slot's wall in two coplanar pieces (split at x=9.3), the long piece
# drafted about the side x=0: the split edge becomes the piece's hinge line,
# the piece's top and bottom edges shrink to points, the face to nothing.
# The result was "invalid" at the input's own volume, refused now.
for a in (5, 15):
    brep_case("slot_wall_split_piece_a%d" % a, os.path.join(HERE, "models", "slot_wall_split.brep"),
              3, 1, a, "refused")

# #962's Pocket002: a wall drafted about a 45 deg chamfer's plane. A vertex
# of a split edge the draft leaves alone is placed by another edge's curve
# and misses the split edge by 3.4e-7, three times its tolerance: the
# result was invalid. The vertex's tolerance now covers it.
P962 = os.path.join(HERE, "..", "fillet", "models", "issue962_pocket002.brep")
for face, neutral, a, vol in ((41, 24, 5, 11432.6957), (44, 30, 5, 11738.5401),
                              (51, 30, 15, 12057.0173)):
    brep_case("issue962_f%d_n%d_a%d" % (face, neutral, a), P962, face, neutral, a, "valid", vol)

# ---------------------------------------------------------------------------
# The new draft (FreeCAD's Part::CellDraft, docs/NewDraft.md in
# realthunder/FreeCAD): a draft that can change topology. Through the Draft's
# Method = New; a FreeCAD without it (no StopAtBody property) skips these.
# The cases the classic draft refuses above come out valid at closed-form
# volumes; StopAtBody (default on) keeps a drafted face from growing the body
# past a plane that bounds the whole body.
# ---------------------------------------------------------------------------

def has_cell_draft():
    doc = App.newDocument("probe")
    try:
        return "StopAtBody" in doc.addObject("PartDesign::Draft", "Draft").PropertiesList
    finally:
        App.closeDocument(doc.Name)


def t(a):
    return math.tan(math.radians(a))


if has_cell_draft():
    for a in (5, 20, 44):
        draft_case("new_notch_ledge_a%d" % a, plain, plane_at("z", 5), plane_at("y", 5), a,
                   "valid", 1750 + 125 * t(a), method="New")
    # the ledge's front reaches the block's top: the notch's front edge goes
    draft_case("new_notch_ledge_a45", plain, plane_at("z", 5), plane_at("y", 5), 45, "valid",
               1875, method="New")
    # past the top at 60 deg (8.66 over 5): stopped at the top's plane, which
    # closes over the notch's front; unstopped, a fin stands 3.66 over the top
    draft_case("new_notch_ledge_a60", plain, plane_at("z", 5), plane_at("y", 5), 60, "valid",
               1750 + 125 * t(60) - 10 * (5 * t(60) - 5) ** 2 / (2 * t(60)), method="New")
    draft_case("new_notch_ledge_a60_unstopped", plain, plane_at("z", 5), plane_at("y", 5), 60,
               "valid", 1750 + 125 * t(60), method="New", stop=False)
    # the bevel's corner gets the new edge the classic draft cannot make;
    # stopped, the ledge rises only to the bevel's plane
    for a, stopped in ((5, 1660.2207), (20, 1685.2363), (45, 1719.4444)):
        draft_case("new_notch_bevel_ledge_a%d" % a, bevelled, plane_at("z", 5), plane_at("y", 5),
                   a, "valid", stopped, method="New")
        draft_case("new_notch_bevel_ledge_a%d_unstopped" % a, bevelled, plane_at("z", 5),
                   plane_at("y", 5), a, "valid", 1650 + 125 * t(a), method="New", stop=False)
    # the slot's wall breaks through the block's front at 2 / tan(a) above
    # the floor
    draft_case("new_slot_wall_a5", deep, plane_at("y", 2), plane_at("z", 2), 5, "valid",
               deep.Volume - 2 * 18 * 18 * t(5), method="New")
    for a in (15, 30):
        h = 2 / t(a)
        draft_case("new_slot_wall_a%d" % a, deep, plane_at("y", 2), plane_at("z", 2), a, "valid",
                   8000 - 4 * 6 * 18 - 4 * (h * 2 / 2 + 2 * (18 - h)), method="New")
    # the corner slides along the slanted wall to (x, (x - 10) / 2), where
    # the drafted wall y = -(20 - x) tan(5 deg) meets it: the outline
    # extruded 5
    tx = (5 - 20 * t(5)) / (0.5 - t(5))
    outline = [(0, -5), (tx, (tx - 10) / 2), (20, 0), (20, 10), (0, 10)]
    area = abs(sum(outline[i][0] * outline[i - 1][1] - outline[i - 1][0] * outline[i][1]
                   for i in range(len(outline)))) / 2
    draft_case("new_split_floor_corner_a5", split, plane_at("y", 0), plane_at("x", 20), 5,
               "valid", 5 * area, method="New")
    # an L-shaped face (a notch through the block's whole depth): the wedge
    # under it, 625 tan(a), either way
    lblock = Part.makeBox(20, 10, 10).cut(Part.makeBox(10, 10, 5, V(0, 0, 5))).removeSplitter()
    for a in (5, 20):
        draft_case("new_l_face_a%d" % a, lblock, plane_at("y", 0), plane_at("z", 0), a, "valid",
                   1500 - 625 * t(a), method="New")
        draft_case("new_l_face_a%d_reversed" % a, lblock, plane_at("y", 0), plane_at("z", 0), a,
                   "valid", 1500 + 625 * t(a), method="New", reversed=True)
    # two adjacent walls of a boss, in both orders: the same solid as the
    # classic draft's
    boss = Part.makeBox(30, 30, 5).fuse(Part.makeBox(10, 10, 5, V(10, 10, 5))).removeSplitter()

    def walls(order):
        def pick(shape):
            x10 = [i for i, f in enumerate(shape.Faces, 1) if plane_at("x", 10)(f)]
            y10 = [i for i, f in enumerate(shape.Faces, 1) if plane_at("y", 10)(f)
                   and f.BoundBox.ZMin > 5 - 1e-9]
            return (x10 + y10) if order else (y10 + x10)
        pick.many = True
        return pick
    for a, vol in ((5, 4978.4468), (30, 4869.5513)):
        for order in (True, False):
            draft_case("new_boss_walls_a%d_%s" % (a, "xy" if order else "yx"), boss, walls(order),
                       lambda f: plane_at("z", 5)(f) and f.Area > 100, a, "valid", vol,
                       method="New")
    # a 0.2 wide face whose walls meet 0.2 past it, drafted outward about a
    # plane 50 below: its new plane lies past the walls' meeting line, the
    # face would vanish; drafted inward, it shrinks the wedge
    wedge = Part.Face(Part.makePolygon([V(0, -5, 0), V(10, -0.1, 0), V(10, 0.1, 0),
                                        V(0, 5, 0), V(0, -5, 0)])).extrude(V(0, 0, 10))
    below = Part.makePlane(200, 200, V(-100, -100, -50))
    draft_case("new_face_vanishes", wedge, plane_at("x", 10), None, 5,
               "refused:FaceVanishes", method="New", reversed=True, neutral_shape=below)
    ramp_ledge_drafts((5, 11, 15, 17), method="New")
    draft_case("new_face_shrinks", wedge, plane_at("x", 10), None, 5, "valid", 386.6083,
               method="New", neutral_shape=below)
    # Tangent chains (phase 2): a block 20 x 10 x 10 with its vertical edges
    # filleted 2. Drafting one wall drafts the whole chain, the walls turned
    # and the fillets turned into cones: at height z the section is a
    # rounded rectangle with its walls moved in by z tan(a).
    rbox = Part.makeBox(20, 10, 10)
    rbox = rbox.makeFillet(2, [e for e in rbox.Edges
                               if abs(e.Vertexes[0].Z - e.Vertexes[1].Z) > 1])

    def rbox_volume(a, w=20, d=10, r=2, h=10, corners=4):
        # past the cones' apex (r / tan(a), drafted inward) the walls meet
        # in a sharp edge: no fillet to take off there
        k = t(a)
        z = min(h, r / k) if k > 0 else h
        return (w * d * h - (w + d) * k * h ** 2 + 4 * k ** 2 * h ** 3 / 3
                - corners * (1 - math.pi / 4) * (r ** 2 * z - r * k * z ** 2 + k ** 2 * z ** 3 / 3))

    def first_fillet(shape):
        return [[i for i, f in enumerate(shape.Faces, 1)
                 if f.Surface.__class__.__name__ == "Cylinder"][0]]
    first_fillet.many = True

    for a in (5, -5, -15):
        draft_case("new_chain_rbox_a%d" % a, rbox, plane_at("y", 0), plane_at("z", 0), a,
                   "valid", rbox_volume(a), method="New")
    # a fillet drafted itself drafts the same chain
    draft_case("new_chain_rbox_fillet_a5", rbox, first_fillet, plane_at("z", 0), 5, "valid",
               rbox_volume(5), method="New")
    # Inward at 15 and 20 deg the fillets' cones reach their apex at 2 /
    # tan(a) = 7.46 and 5.49, under the block's top: above it the walls meet
    # in a sharp edge. At 30 deg the short walls narrow to nothing at 5 /
    # tan(30) = 8.66, under the top too: refused.
    for a in (15, 20):
        draft_case("new_chain_rbox_a%d" % a, rbox, plane_at("y", 0), plane_at("z", 0), a,
                   "valid", rbox_volume(a), method="New")
    draft_case("new_chain_rbox_a30", rbox, plane_at("y", 0), plane_at("z", 0), 30,
               "refused:FaceVanishes", method="New")
    # One vertical edge filleted: the chain is a wall, the fillet and the
    # wall beyond, open at both ends; drafted from the wall and from the
    # fillet, past the apex at 15 deg.
    obox = Part.makeBox(20, 10, 10)
    obox = obox.makeFillet(2, [e for e in obox.Edges
                               if abs(e.Vertexes[0].Z - e.Vertexes[1].Z) > 1
                               and abs(e.Vertexes[0].X - 20) < 1e-9
                               and abs(e.Vertexes[0].Y - 10) < 1e-9])

    def obox_volume(a, h=10, r=2):
        k = t(a)
        z = min(h, r / k)
        return (200 * h - 30 * k * h ** 2 / 2 + k ** 2 * h ** 3 / 3
                - (1 - math.pi / 4) * (r ** 2 * z - r * k * z ** 2 + k ** 2 * z ** 3 / 3))

    draft_case("new_chain_open_apex_a15", obox, plane_at("y", 10), plane_at("z", 0), 15,
               "valid", obox_volume(15), method="New")
    draft_case("new_chain_open_apex_fillet_a15", obox, first_fillet, plane_at("z", 0), 15,
               "valid", obox_volume(15), method="New")
    # #631's S-shaped ramp (its Fillet002 input): the wall face 7 drafted
    # about face 9 drafts the chain, whose fillet ends where a cylinder and
    # the plane tangent to it meet; the new cone crosses their line of
    # contact, which only the coarse fuzzy fuse puts in one place. The
    # classic draft's volumes (to 1e-7: the recorded 4 decimals).
    p631 = Part.read(os.path.join(HERE, "..", "fillet", "models", "issue631_fillet002_base.brep"))
    for a, vol in ((5, 39164.1931), (15, 34327.1140)):
        draft_case("new_chain_issue631_f7_n9_a%d" % a, p631,
                   lambda f: f.isSame(p631.Faces[6]), lambda f: f.isSame(p631.Faces[8]), a,
                   "valid", vol, method="New")
    # Three vertical edges filleted, the one at the origin sharp: the chain
    # closes on itself there, and the two new planes meet in a new edge.
    # From the far wall and from a wall at the sharp corner; at 15 deg past
    # the cones' apex too (the classic draft refuses).
    sbox = Part.makeBox(20, 10, 10)
    sbox = sbox.makeFillet(2, [e for e in sbox.Edges
                               if abs(e.Vertexes[0].Z - e.Vertexes[1].Z) > 1
                               and abs(e.Vertexes[0].X) + abs(e.Vertexes[0].Y) > 1e-9])
    for a in (5, -5, 15):
        draft_case("new_chain_sharp_a%d" % a, sbox, plane_at("y", 10), plane_at("z", 0), a,
                   "valid", rbox_volume(a, corners=3), method="New")
    draft_case("new_chain_sharp_corner_wall_a15", sbox, plane_at("x", 0), plane_at("z", 0), 15,
               "valid", rbox_volume(15, corners=3), method="New")

    # A 40 x 30 x 20 block, a 20 x 10 pocket 16 deep with its corners
    # rounded 2, 2 behind the front: the pocket's walls drafted outward about
    # its floor move 16 tan(a) at the top, through the front wall from 7.3
    # deg. The solid: the block less the drafted pocket, a ruled loft
    # between the floor's outline and the top's.
    def rounded_rect(x0, y0, w, d, r, z):
        c = [(x0 + w - r, y0 + r), (x0 + w - r, y0 + d - r), (x0 + r, y0 + d - r),
             (x0 + r, y0 + r)]
        edges = []
        for i, (cx, cy) in enumerate(c):
            a = (i - 1) * math.pi / 2
            edges.append(Part.ArcOfCircle(Part.Circle(V(cx, cy, z), V(0, 0, 1), r),
                                          a, a + math.pi / 2).toShape())
            nx, ny = c[(i + 1) % 4]
            b = a + math.pi / 2
            edges.append(Part.LineSegment(V(cx + r * math.cos(b), cy + r * math.sin(b), z),
                                          V(nx + r * math.cos(b), ny + r * math.sin(b),
                                            z)).toShape())
        return Part.Wire(edges)

    block = Part.makeBox(40, 30, 20)
    pocketed = block.cut(Part.Face(rounded_rect(10, 2, 20, 10, 2, 4)).extrude(V(0, 0, 16)))
    pocketed = pocketed.removeSplitter()
    for a in (5, 10, 20):
        g = 16 * t(a)
        loft = Part.makeLoft([rounded_rect(10, 2, 20, 10, 2, 4),
                              rounded_rect(10 - g, 2 - g, 20 + 2 * g, 10 + 2 * g, 2 + g, 20)],
                             True, True)
        draft_case("new_chain_pocket_break_a%d" % a, pocketed, plane_at("y", 2),
                   plane_at("z", 4), a, "valid", block.cut(loft).Volume, method="New")
    # The pocket's walls drafted the other way, inward: at 15 deg its
    # concave corners close to a sharp edge 2 / tan(15) = 7.46 above the
    # floor, and the walls meet there. The pocket at height z over the floor
    # is a rectangle in by z tan(a), less its rounded corners below that.
    k = t(15)
    za = 2 / k
    pocket_volume = (200 * 16 - 30 * k * 16 ** 2 + 4 * k ** 2 * 16 ** 3 / 3
                     - (4 - math.pi) * (4 * za - 2 * k * za ** 2 + k ** 2 * za ** 3 / 3))
    draft_case("new_chain_pocket_apex_a15", pocketed, plane_at("y", 2), plane_at("z", 4), -15,
               "valid", block.Volume - pocket_volume, method="New")
    # the pocket with its corner at (10, 2) sharp: a concave sharp corner
    prof = Part.makeBox(20, 10, 16, V(10, 2, 4))
    prof = prof.makeFillet(2, [e for e in prof.Edges
                               if abs(e.Vertexes[0].Z - e.Vertexes[1].Z) > 1
                               and abs(e.Vertexes[0].X - 10) + abs(e.Vertexes[0].Y - 2) > 1e-9])
    pocketed3 = block.cut(prof).removeSplitter()
    pocket_volume3 = pocket_volume + (4 - math.pi) / 4 * (4 * za - 2 * k * za ** 2
                                                         + k ** 2 * za ** 3 / 3)
    draft_case("new_chain_pocket_sharp_a15", pocketed3, plane_at("y", 2), plane_at("z", 4), -15,
               "valid", block.Volume - pocket_volume3, method="New")
else:
    emit("new draft cases skipped: this FreeCAD's Draft has no cell draft")

# ---------------------------------------------------------------------------
counts = {}
for _, verdict, _ in results:
    counts[verdict] = counts.get(verdict, 0) + 1
if counts.get("UNEXPECTED-PASS"):
    emit("NOTE: xfail case(s) now pass - promote them to 'valid' with their volume.")
emit("summary: " + "  ".join("%s=%d" % kv for kv in sorted(counts.items())))
sys.exit(1 if counts.get("FAIL") else 0)
