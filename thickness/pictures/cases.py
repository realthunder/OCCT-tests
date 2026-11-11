# The cases pictured in models/pictures: the suite's (run_tests.py) that a fix
# turned from failing to passing, each with the stage of the fix -- the fork
# commit just before it (STAGES) is the "before" column.
import math
import os

try:
    import FreeCAD as App, Part
except ImportError:  # plain Python reads the tables only
    App = Part = None


def V(*a):
    return App.Vector(*a)


# stage -> (the fork commit just before the fix, the section of models/Thickness.md)
STAGES = {
    "s2": ("050c66d58e", "2"),
    "s3": ("2a15bbb52b", "3"),
    "s4": ("cbc47c91a7", "4"),
    "s5": ("51a0cc9b38", "5"),
    "s6": ("e5e6d02f70", "6"),
    "s8": ("9a14fb9db5", "8"),
    "s9": ("c4be5548f9", "9"),
    "s10": ("457b652f42", "10"),
    "s11": ("b21dabe1c4", "11"),
    "s12": ("d4d2fe0719", "12"),
    "s13": ("d8d480ef65", "13"),
    "s14": ("839a3e4606", "14"),
    "s15": ("f723999a15", "15"),
    "s16": ("dc3a7b85d1", "16"),
    "s17": ("b6404e079a", "17"),
    "s18": ("705644654e", "18"),
    "s19": ("e63b3f86cc", "19"),
    "s20": ("ffc01775a7", "20"),
    "s21a": ("76691d6f87", "21"),
    "s21b": ("b45cff22c5", "21"),
    "s21c": ("20372de2b3", "21"),
    "s22a": ("1e6f5a464c", "22"),
    "s22b": ("631700cbf8", "22"),
    "s22c": ("c747dd8371", "22"),
    "s23": ("80fa234b05", "23"),
    "s24": ("42475a8cca", "24"),
    "s25": ("8d5aa88952", "25"),
    "s26a": ("99971a1dc8", "26"),
    "s26b": ("54d2c02774", "26"),
    "s28": ("047a9e432d", "28"),
    "s29": ("efe6683cd7", "29"),
    "s30": ("193f97a680", "30"),
    "s31": ("92cc9effb6", "31"),
    "s34": ("047a9e432d", "34"),
    "s35": ("eebc4a98b5", "35"),
    "s36": ("c1f874898c", "36"),
    "s37": ("ddac69429e", "37"),
    "s38": ("fd833a6672", "38"),
    "s39": ("2ad983305c", "39"),
    "s40": ("1fbb9fe781", "40"),
    "s41": ("ec1bf4cdc8", "41"),
    "s42": ("1fcefd3de8", "42"),
    "s43": ("ef5ab58d9e", "43"),
    "s44": ("4c8778375c", "44"),
    "s45": ("336f3d38c9", "45"),
    "s46": ("8d4483af45", "46"),
    "s47": ("9cd33c4b68", "47"),
    "s48": ("7f0d86814c", "48"),
    "s49": ("a0f53eb60e", "49"),
    "s50": ("34ec30cbe6", "50"),
    "s51": ("a4c29a9c89", "51"),
    "s52": ("81dab158bb", "52"),
    "s53": ("848b935668", "53"),
    "s54": ("4e2ce9cbbf", "54"),
    "s55": ("79041b6478", "55"),
    "s56": ("fa92a21610", "56"),
    "s57": ("92c4617170", "57"),
    "s58": ("e1d0c13102", "58"),
    "s59": ("ede496a1f2", "59"),
    "s60": ("10a2414c33", "60"),
    "s61": ("03d799f0c5", "61"),
    "s62": ("d82a097786", "62"),
}
# Upstream: every file the fork has changed in the two packages the fix chain
# works in, at the fork's base. The packages are named, not the files: it was
# eleven files once, the chain went on into six more, and a library built
# again with those six left as the fork has them showed its fixes as upstream's.
UPSTREAM = ("91be8c4c71", [
    "src/ModelingAlgorithms/TKBool/BRepAlgo",
    "src/ModelingAlgorithms/TKOffset/BRepOffset"])
def _blindpot():
    # The blind hole's wall and floor and the top beside them, an open shell:
    # Face3 is the top.
    b = SHAPES["blindhole"]()
    return Part.Shell([b.Faces[i - 1] for i in (7, 8, 3)])


def _sector(past):
    # A ring sector straddling angle 0, padded 27, its arcs' parameters
    # running from past - a to past + a: Face3 is the outer arc's.
    o = Part.ArcOfCircle(Part.Circle(V(0, 0, 0), V(0, 0, 1), 59.3), past - 0.29, past + 0.29).toShape()
    i = Part.ArcOfCircle(Part.Circle(V(0, 0, 0), V(0, 0, 1), 46.85), past - 0.23, past + 0.23).toShape()
    sides = [Part.makeLine(i.Vertexes[k].Point, o.Vertexes[k].Point) for k in (0, 1)]
    return Part.Face(Part.Wire(Part.__sortEdges__([o, sides[0], i, sides[1]]))).extrude(V(0, 0, 27))


def _fillet(r):
    b = Part.makeBox(10, 8, 6)
    return b.makeFillet(r, [b.Edges[i] for i in (0, 2, 4, 6)])
def _placement():
    return App.Placement(V(3, 4, 5), App.Rotation(V(1, 2, 3), 40))


def _placed(shape):
    # Under a location: an object's placement.
    shape.Placement = _placement()
    return shape


def _turned(shape):
    # The geometry itself turned and moved, no location on it.
    shape.transformShape(_placement().Matrix, True)
    return shape


def _halfball(cut=None):
    # Half a ball cut through both its poles; with cut, its sphere in two
    # faces already, by a general fuse with a meridian or the equator.
    b = Part.makeSphere(5, V(), V(0, 0, 1), -90, 90, 180)
    if cut == "meridian":
        e = Part.Arc(V(0, 0, -5), V(0, 5, 0), V(0, 0, 5)).toShape()
    elif cut == "equator":
        e = Part.ArcOfCircle(Part.Circle(V(), V(0, 0, 1), 5), 0, math.pi).toShape()
    else:
        return b
    return b.generalFuse([e])[0].Solids[0]


def _split_at(shape, i):
    # The shape with a vertex at the middle of its edge i (0-based).
    e = shape.Edges[i]
    return shape.generalFuse([Part.Vertex(e.valueAt((e.FirstParameter + e.LastParameter) / 2))])[0].Solids[0]


def _reordered(shape, order):
    # The solid with its faces in another order (1-based).
    return Part.Solid(Part.Shell([shape.Faces[i - 1] for i in order]))


def _axis_wedge(ang):
    # A ball made on an axis through the middle of the wedge it is cut to: its
    # face has a seam and a pole inside. Face1 is the sphere.
    mid = math.radians(ang / 2.0)
    m = V(math.cos(mid), math.sin(mid), 0)
    gap = Part.makeCylinder(10, 20, V(0, 0, -10), V(0, 0, 1), 360 - ang)
    gap.rotate(V(), V(0, 0, 1), ang)
    w = Part.makeSphere(5, V(), m).cut(gap).Solids[0]
    assert w.Faces[0].Surface.__class__.__name__ == "Sphere"
    return w


def _mitrebox(xmax, ymax):
    # A box with two adjacent top edges filleted, r2: the edge at x = 0 or 10
    # and the one at y = 0 or 8. Its bottom is Face4 or Face6 (run_tests.py
    # finds it by place).
    b = Part.makeBox(10, 8, 6)
    top = [e for e in b.Edges if abs(e.BoundBox.ZMin - 6) < 1e-9 and abs(e.BoundBox.ZMax - 6) < 1e-9]
    ex = [e for e in top if abs(e.BoundBox.XMin - xmax) < 1e-9 and abs(e.BoundBox.XMax - xmax) < 1e-9]
    ey = [e for e in top if abs(e.BoundBox.YMin - ymax) < 1e-9 and abs(e.BoundBox.YMax - ymax) < 1e-9]
    return b.makeFillet(2, ex + ey)


def _roundtop():
    # The box of _mitrebox with all four top edges filleted, r2: its bottom
    # is Face4.
    b = Part.makeBox(10, 8, 6)
    return b.makeFillet(2, [e for e in b.Edges
                            if abs(e.BoundBox.ZMin - 6) < 1e-9 and abs(e.BoundBox.ZMax - 6) < 1e-9])


def _filleteddome():
    # A box under a B-spline dome, the dome's four edges filleted r3 (the
    # suite's _dome): its bottom is Face4.
    s = Part.Shape()
    s.importBrep(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "boolean",
                              "models", "dome_fillet_r3.brep"))
    return s


def _groove5seam():
    # #363's grooved cylinder, the groove one face whose own seam lies on its
    # edge with the right bottom (run_tests.py's _gs): the left bottom is Face4.
    return Part.makeCylinder(25.807914, 14.0).cut(
        Part.makeCylinder(5.0, 120, V(0, -60, 0), V(0, 1, 0)).rotated(V(), V(0, 1, 0), 90))


def _step():
    # #363's cylinder with a square step cut off its side (run_tests.py's
    # _step): Face2 the bottom, Face3 the step's wall, Face4 its ceiling,
    # Face5 the top.
    return Part.makeCylinder(25.807914, 14.0).cut(
        Part.makeBox(60 - 10.062591, 120, 10.062591 + 1, V(-60, -60, -1)))


def _groove10():
    # #363's grooved cylinder as run_tests.py's grooved_cylinder(10.062591)
    # makes it: the groove two quarter cylinders.
    return Part.makeCylinder(25.807914, 14.0).cut(
        Part.makeCylinder(10.062591, 120, V(0, -60, 0), V(0, 1, 0)))


def _boxgroove10():
    # The box with #363's groove across its bottom, as run_tests.py's
    # grooved_box(10.062591): Face6 the left quarter, Face7 the right.
    R = 25.807914
    return Part.makeBox(2 * R, 2 * R, 14.0, V(-R, -R, 0)).cut(
        Part.makeCylinder(10.062591, 120, V(0, -60, 0), V(0, 1, 0)))


def _slot():
    # The same cylinder with a square slot across its end (run_tests.py's
    # _slot).
    return Part.makeCylinder(25.807914, 14.0).cut(
        Part.makeBox(2 * 10.062591, 120, 10.062591 + 1, V(-10.062591, -60, -1)))


def _issue363base():
    # Thickness001's base (realthunder/OCCT#363): its left bottom is Face5.
    s = Part.Shape()
    s.importBrep(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "models",
                              "issue363_thickness001_base.brep"))
    return s


def _issue521():
    # #521's Connect: a box 10 fused with a cylinder r 2 at its corner edge,
    # left-handed, refined: 1 x = 10, 2 y = 10, 3 y = 0, 4 the cylinder,
    # 5 x = 0, 6 the top, 7 the bottom.
    s = Part.Shape()
    s.importBrep(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "models",
                              "issue521_connect.brep"))
    return s


def _issue613():
    # #613's part: the issue file's stored Fillet, a cylinder under a cone
    # with a ridge across its top, filleted. Face7 is the top of the ridge,
    # Face16 the bottom.
    s = Part.Shape()
    s.importBrep(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "models",
                              "issue613_fillet.brep"))
    return s


def _issue360():
    # #360's plate, the base of its Thickness: 10 thick, square holes 4.3
    # apart and 2.5 from the outline. Face5 is the top, Face4 the bottom.
    s = Part.Shape()
    s.importBrep(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "models",
                              "issue360_plate.brep"))
    return s


def _holed_plate(holes, lx=80, ly=30):
    # run_tests.py's _holed_plate: 80 x 30 x 10 (or as given) with square
    # holes through it, the top Face3.
    s = Part.makeBox(lx, ly, 10)
    for x0, y0 in holes:
        s = s.cut(Part.makeBox(12.4, 12.4, 12, V(x0, y0, -1)))
    return s.removeSplitter()


def _round_plate(holes):
    # run_tests.py's _round_plate: 80 x 30 x 10 with round holes through it,
    # the top Face3.
    s = Part.makeBox(80, 30, 10)
    for x, y, r in holes:
        s = s.cut(Part.makeCylinder(r, 12, V(x, y, -1)))
    return s.removeSplitter()


def _revolve346():
    # #346's Revolve as the issue has it, a shell: Face1 the cone, Face2 the
    # dome, its top a dimple.
    s = Part.Shape()
    s.importBrep(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "models",
                              "issue346_revolve.brep"))
    return s


def _issue346(cx):
    # #346's profile -- a line from (37.71, 51.19) to (30, 42), an arc
    # centred (cx, -20.08) on to the axis -- closed by the axis and a disc at
    # the top, turned about y: the dome's top a dimple (cx > 0) or a peak
    # (cx < 0). Face3 is the disc.
    cy = -20.083431642721106
    a, b = V(37.713451316238469, 51.192533317427738, 0), V(30, 42, 0)
    r = math.hypot(30 - cx, 42 - cy)
    t = V(0, cy + math.sqrt(r * r - cx * cx), 0)
    am = 0.5 * (math.atan2(42 - cy, 30 - cx) + math.atan2(t.y - cy, -cx))
    m = V(cx + r * math.cos(am), cy + r * math.sin(am), 0)
    c = V(0, a.y, 0)
    w = Part.Wire([Part.LineSegment(a, b).toShape(), Part.Arc(b, m, t).toShape(),
                   Part.LineSegment(t, c).toShape(), Part.LineSegment(c, a).toShape()])
    return Part.Face(w).revolve(V(), V(0, 1, 0), 360)


def _issue346_shell(cx):
    # The same profile not closed: the cone and the dome alone, a shell, as
    # run_tests.py's issue346_profile(cx) makes it. Face1 is the cone.
    cy = -20.083431642721106
    a, b = V(37.713451316238469, 51.192533317427738, 0), V(30, 42, 0)
    r = math.hypot(30 - cx, 42 - cy)
    t = V(0, cy + math.sqrt(r * r - cx * cx), 0)
    am = 0.5 * (math.atan2(42 - cy, 30 - cx) + math.atan2(t.y - cy, -cx))
    m = V(cx + r * math.cos(am), cy + r * math.sin(am), 0)
    w = Part.Wire([Part.LineSegment(a, b).toShape(), Part.Arc(b, m, t).toShape()])
    return w.revolve(V(), V(0, 1, 0), 360)


def _dome2(line=False):
    # A dome on the y axis, its rim in two arcs: fused with the vertex across
    # from its seam's end, or -- line -- with the line between them, which
    # cuts its flat in two halves as well.
    d = Part.makeSphere(5, V(), V(0, 1, 0), 0, 90, 360)
    rim = [e for e in d.Edges if not e.Degenerated and abs(e.Length - 10 * math.pi) < 1e-6][0]
    p = rim.Vertexes[0].Point
    tool = Part.makeLine(p, p * -1) if line else Part.Vertex(p * -1)
    return d.generalFuse([tool])[0].Solids[0]


SHAPES = {
    "cyl": lambda: Part.makeCylinder(4, 20),
    "ann": lambda: Part.makeCylinder(5, 10).cut(Part.makeCylinder(2, 10)),
    "ell": lambda: Part.Face(Part.Wire(Part.Ellipse(V(0, 0, 0), 10, 5).toShape())).extrude(V(0, 0, 8)),
    "cylpocket": lambda: Part.makeCylinder(6, 6).cut(Part.makeCylinder(3, 3, V(0, 0, 3))),
    "boxhole": lambda: Part.makeBox(10, 10, 5).cut(Part.makeCylinder(2, 5, V(5, 5, 0))),
    "lbox": lambda: Part.makeBox(10, 10, 5).cut(Part.makeBox(5, 5, 5, V(5, 5, 0))),
    "tshape": lambda: Part.makeBox(12, 4, 4).fuse(Part.makeBox(4, 4, 10, V(4, 0, 0))).removeSplitter(),
    "pocketbox": lambda: Part.makeBox(10, 10, 6).cut(Part.makeBox(6, 6, 3, V(2, 2, 3))),
    "conehole": lambda: Part.makeCone(6, 3, 8).cut(Part.makeCylinder(1.5, 8)),
    "pocket5": lambda: Part.makeBox(10, 10, 6).cut(Part.makeBox(5, 5, 3, V(2.5, 2.5, 3))),
    "blindhole": lambda: Part.makeBox(10, 10, 5).cut(Part.makeCylinder(2, 3, V(5, 5, 2))),
    "filletbox": lambda: _fillet(2),
    "filletbox25": lambda: _fillet(2.5),
    "shortcyl": lambda: Part.makeCylinder(4, 1.5),
    "shortbox": lambda: Part.makeBox(10, 10, 1.5),
    "box6": lambda: Part.makeBox(10, 10, 6),
    "blindpot": lambda: _blindpot(),
    "cylboss": lambda: Part.makeCylinder(6, 4).fuse(Part.makeCylinder(3, 4, V(0, 0, 4))),
    "sector": lambda: _sector(2 * math.pi),
    "sphere": lambda: Part.makeSphere(5),
    "dome": lambda: Part.makeSphere(5, V(), V(0, 0, 1), 0, 90, 360),
    "cap": lambda: Part.makeSphere(5, V(), V(0, 0, 1), 30, 90, 360),
    "cone": lambda: Part.makeCone(0, 4, 6),
    "halfdome": lambda: Part.makeSphere(5, V(), V(0, 0, 1), 0, 90, 180),
    "splitbox": lambda: Part.makeBox(4, 8, 6).fuse(Part.makeBox(6, 8, 6, V(4, 0, 0))),
    "eighth": lambda: Part.makeSphere(5, V(), V(0, 0, 1), 0, 90, 90),
    "dome120": lambda: Part.makeSphere(5, V(), V(0, 0, 1), 0, 90, 120),
    "dome270": lambda: Part.makeSphere(5, V(), V(0, 0, 1), 0, 90, 270),
    "lune": lambda: Part.makeSphere(5, V(), V(0, 0, 1), -90, 90, 90),
    "placed_dome": lambda: _placed(Part.makeSphere(5, V(), V(0, 0, 1), 0, 90, 360)),
    "placed_cone": lambda: _placed(Part.makeCone(0, 4, 6)),
    "placed_coneup": lambda: _placed(Part.makeCone(4, 0, 6)),
    "placed_halfdome": lambda: _placed(Part.makeSphere(5, V(), V(0, 0, 1), 0, 90, 180)),
    "turned_filletbox": lambda: _turned(_fillet(2)),
    "turned_halfcap": lambda: _turned(Part.makeSphere(5, V(), V(0, 0, 1), 30, 90, 180)),
    "turned_bullet": lambda: _turned(Part.makeCylinder(5, 4, V(0, 0, -4)).fuse(
        Part.makeSphere(5, V(), V(0, 0, 1), 0, 90, 360)).removeSplitter()),
    "halfball": lambda: _halfball(),
    "luneball": lambda: _halfball("meridian"),
    "eqball": lambda: _halfball("equator"),
    "dome2": lambda: _dome2(),
    "dome2f": lambda: _dome2(True),
    "halfball1": lambda: _halfball().removeSplitter(),
    "cutball": lambda: Part.makeSphere(5).cut(Part.makeBox(20, 20, 20, V(-10, -20, -10))),
    "ball270": lambda: Part.makeSphere(5, V(), V(0, 0, 1), -90, 90, 270),
    "ball240": lambda: Part.makeSphere(5, V(), V(0, 0, 1), -90, 90, 240),
    "ball150": lambda: Part.makeSphere(5, V(), V(0, 0, 1), -90, 90, 150),
    "boxsplit": lambda: _split_at(Part.makeBox(10, 8, 6), 0),
    "cylseam": lambda: _split_at(Part.makeCylinder(4, 6), 1),
    "ball270split": lambda: Part.makeSphere(5, V(), V(0, 0, 1), -90, 90, 270).generalFuse(
        [Part.Vertex(V(5, 0, 0))])[0].Solids[0],
    "axiswedge270": lambda: _axis_wedge(270),
    "turned_eqball": lambda: _turned(_halfball("equator")),
    "placed_luneball": lambda: _placed(_halfball("meridian")),
    "capsplit": lambda: _split_at(Part.makeSphere(5, V(), V(0, 0, 1), 30, 90, 360), 1),
    "bulletsplit": lambda: _split_at(Part.makeCylinder(5, 4, V(0, 0, -4)).fuse(
        Part.makeSphere(5, V(), V(0, 0, 1), 0, 90, 360)).removeSplitter(), 1),
    "dome270split": lambda: _split_at(Part.makeSphere(5, V(), V(0, 0, 1), 0, 90, 270), 3),
    "cutballsplit": lambda: _split_at(Part.makeSphere(5).cut(Part.makeBox(20, 20, 20, V(-10, -20, -10))), 2),
    "luneballsplit": lambda: _split_at(_halfball("meridian"), 0),
    "luneball_flatsfirst": lambda: _reordered(_halfball("meridian"), (3, 4, 1, 2)),
    "mitrebox_x0y8": lambda: _mitrebox(0, 8),
    "mitrebox_x10y0": lambda: _mitrebox(10, 0),
    "mitrebox_x10y8": lambda: _mitrebox(10, 8),
    "roundtop": lambda: _roundtop(),
    "filleteddome": lambda: _filleteddome(),
    "groove5seam": lambda: _groove5seam(),
    "issue363base": lambda: _issue363base(),
    "step": lambda: _step(),
    "slot": lambda: _slot(),
    "groove10": lambda: _groove10(),
    "boxgroove10": lambda: _boxgroove10(),
    "issue521": lambda: _issue521(),
    "dimple346": lambda: _issue346(1.0500384390052573),
    "peak346": lambda: _issue346(-1.0500384390052573),
    "peakshell346": lambda: _issue346_shell(-1.05),
    "steepdimpleshell346": lambda: _issue346_shell(3.0),
    "issue613": lambda: _issue613(),
    "revolve346": lambda: _revolve346(),
    "issue360": lambda: _issue360(),
    "platerow2": lambda: _holed_plate([(10, 8.8), (26.7, 8.8)]),
    "platestaggered": lambda: _holed_plate([(10, 6), (26.7, 10)]),
    "plateedge6": lambda: _holed_plate([(10, 6)]),
    "plategrid": lambda: _holed_plate([(10, 10), (26.7, 10), (10, 30), (26.7, 30)], 60, 55),
    "plateround2": lambda: _round_plate([(16.2, 15, 6.2), (32.9, 15, 6.2)]),
    "plateroundedge3": lambda: _round_plate([(16.2, 9.2, 6.2)]),
}
# name: (stage, shape, face or list of faces removed, value, inter, join, reference volume)
CASES = {
    "cyl_bottom_in": ("s2", "cyl", 2, -1, False, 0, 468.0973),
    "hole_bottom_in": ("s2", "ann", 2, -1, False, 0, 461.8141),
    "hole_outer_out": ("s2", "ann", 1, +1, False, 0, 241.7451),
    "hole_outer_in": ("s2", "ann", 1, -1, False, 0, 257.6106),
    "hole_inner_out": ("s2", "ann", 4, +1, False, 0, 531.0589),
    "hole_inner_in": ("s2", "ann", 4, -1, False, 0, 358.1416),
    "ellipse_bottom_out": ("s2", "ell", 2, +1, False, 0, 609.8911),
    "ellipse_bottom_in": ("s2", "ell", 2, -1, False, 0, 474.1842),
    "ellipse_top_out": ("s2", "ell", 3, +1, False, 0, 609.8911),
    "ellipse_top_in": ("s2", "ell", 3, -1, False, 0, 474.1842),
    "pocket_bottom_out": ("s2", "cylpocket", 3, +1, False, 0, 433.9707),
    "pocket_bottom_in": ("s2", "cylpocket", 3, -1, False, 0, 346.7660),
    "boxhole_hole_out": ("s2", "boxhole", 7, +1, False, 0, 457.5959),
    "boxhole_hole_in": ("s2", "boxhole", 7, -1, False, 0, 282.8673),
    "lbox_arm_end_out": ("s3", "lbox", 4, +1, False, 0, 388.5671),
    "tshape_arm_end_out": ("s3", "tshape", 1, +1, False, 0, 372.9204),
    "pocketbox_wall_out": ("s3", "pocketbox", 7, +1, False, 0, None),
    "tshape_bar_top_out": ("s3", "tshape", 2, +1, False, 0, 382.4425),
    "tshape_bar_top_in": ("s4", "tshape", 2, -1, False, 0, 215.5708),
    "lbox_top_inter_join_out": ("s4", "lbox", 3, +1, True, 2, 339.0),
    "lbox_top_inter_join_in": ("s4", "lbox", 3, -1, True, 2, 219.0),
    "tshape_back_inter_join_out": ("s4", "tshape", 8, +1, True, 2, 312.0),
    "tshape_back_inter_join_in": ("s4", "tshape", 8, -1, True, 2, 192.0),
    "conehole_bottom_inter_in": ("s4", "conehole", 3, -1, True, 0, 307.1946),
    "tshape_bar_top_right_join_in": ("s5", "tshape", 7, -1, False, 2, 216.0),
    "pocket_floor_join_out": ("s5", "pocket5", 11, +1, False, 2, 591.0),
    "pocket_floor_join_in": ("s5", "pocket5", 11, -1, False, 2, 367.0),
    "blindhole_floor_join_out": ("s5", "blindhole", 8, +1, False, 2, 533.1327),
    "blindhole_floor_join_in": ("s5", "blindhole", 8, -1, False, 2, 326.8496),
    "lbox_notch_wall_inter_join_out": ("s5", "lbox", 7, +1, True, 2, 423.0),
    "tshape_post_wall_inter_join_in": ("s5", "tshape", 3, -1, True, 2, 212.0),
    "pocket_wall_inter_join_in": ("s5", "pocket5", 7, -1, True, 2, 395.0),
    "filletbox_end_in": ("s6", "filletbox", 1, -1, False, 0, 261.1150),
    "filletbox_side_in": ("s6", "filletbox", 6, -1, False, 0, 253.1150),
    "filletbox_end_out": ("s6", "filletbox", 1, +1, False, 0, 403.9604),
    "filletbox_side_out": ("s6", "filletbox", 6, +1, False, 0, 388.8188),
    "filletbox_fillet_in": ("s8", "filletbox", 3, -1, False, 0, 267.0193),
    "filletbox_fillet_out": ("s8", "filletbox", 3, +1, False, 0, 405.9034),
    "filletbox_end_join_in": ("s9", "filletbox", 1, -1, False, 2, 262.8319),
    "filletbox_end_join_out": ("s9", "filletbox", 1, +1, False, 2, 422.7964),
    "filletbox_side_join_in": ("s9", "filletbox", 6, -1, False, 2, 254.8319),
    "filletbox_side_join_out": ("s9", "filletbox", 6, +1, False, 2, 406.7964),
    "filletbox_fillet_join_in": ("s9", "filletbox", 3, -1, False, 2, 268.7129),
    "filletbox_fillet_join_out": ("s9", "filletbox", 3, +1, False, 2, 424.7690),
    "filletbox25_fillet_join_in": ("s9", "filletbox25", 3, -1, False, 2, 258.4221),
    "filletbox25_fillet_join_out": ("s9", "filletbox25", 3, +1, False, 2, 407.4611),
    "conehole_top_in": ("s10", "conehole", 2, -1, False, 0, 358.3146),
    "conehole_top_inter_in": ("s10", "conehole", 2, -1, True, 0, 358.3146),
    "conehole_bottom_in": ("s10", "conehole", 3, -1, False, 0, 307.1946),
    "cyl_side_out": ("s11", "cyl", 1, +1, False, 0, 100.5310),
    "cyl_side_in": ("s11", "cyl", 1, -1, False, 0, 100.5310),
    "short_cyl_side_in": ("s11", "shortcyl", 1, -1, False, 0, 75.3982),
    "short_box_bottom_in": ("s11", "shortbox", [1, 2, 3, 4, 6], -1, False, 0, 100.0),
    "cyl_cap_alone_join_out": ("s12", "cyl", [1, 3], +1, False, 2, 50.2655),
    "box_bottom_alone_join_in": ("s12", "box6", [1, 2, 3, 4, 6], -1, False, 2, 100.0),
    "cyl_side_join_out": ("s12", "cyl", 1, +1, False, 2, 100.5310),
    "blind_top_out": ("s13", "blindhole", 3, +1, False, 0, 380.6342),
    "blind_top_in": ("s13", "blindhole", 3, -1, False, 0, 315.6543),
    "pocket_top_in": ("s13", "pocket5", 3, -1, False, 0, 392.2271),
    "cylpocket_top_join_out": ("s13", "cylpocket", 2, +1, False, 2, 458.6725),
    "blind_top_in_inter_join": ("s13", "blindhole", 3, -1, True, 2, 319.3982),
    "blind_wall_out_join": ("s13", "blindhole", 7, +1, False, 2, 508.0),
    "blind_pot_shell_out": ("s13", "blindpot", 3, +1, False, 0, 31.4159),
    "blind_pot_shell_in": ("s13", "blindpot", 3, -1, False, 0, 71.6543),
    "pocket_top_out_inter_join": ("s13", "pocket5", 3, +1, True, 2, 465.0),
    "cylboss_shoulder_in": ("s13", "cylboss", 2, -1, False, 0, 292.1681),
    "sector_outer_arc_input": ("s14", "sector", [3, 5, 6], +1, False, 0, 9405.6558),
    "sphere_face_refused_in": ("s15", "sphere", 1, -1, False, 0, None),
    "box_all_faces_refused_in": ("s15", "box6", [1, 2, 3, 4, 5, 6], -1, False, 0, None),
    "dome_flat_out": ("s16", "dome", 2, +0.5, False, 0, 86.6556),
    "dome_flat_in": ("s16", "dome", 2, -0.5, False, 0, 70.9476),
    "cap_flat_in": ("s16", "cap", 2, -0.5, False, 0, 33.6412),
    "cone_base_out": ("s16", "cone", 2, +0.5, False, 0, 52.4095),
    "cone_base_in": ("s17", "cone", 2, -0.5, False, 0, 38.8428),
    "cone_base_join_in": ("s17", "cone", 2, -0.5, False, 2, 38.8428),
    "halfdome_bottom_out": ("s17", "halfdome", 2, +0.5, False, 0, 66.1779),
    "halfdome_side_out": ("s17", "halfdome", 3, +0.5, False, 0, 79.7628),
    "halfdome_side_in": ("s17", "halfdome", 3, -0.5, False, 0, 58.8944),
    "halfdome_other_side_in": ("s18", "halfdome", 4, -0.5, False, 0, 58.8944),
    "splitbox_top_piece_join_out": ("s18", "splitbox", 3, +1, False, 2, 440.0),
    "splitbox_top_piece_join_in": ("s18", "splitbox", 3, -1, False, 2, 276.0),
    "splitbox_end_join_in": ("s18", "splitbox", 1, -1, False, 2, 264.0),
    "halfdome_side_join_in": ("s18", "halfdome", 3, -0.5, False, 2, 59.1071),
    "halfdome_bottom_join_out": ("s18", "halfdome", 2, +0.5, False, 2, 67.0206),
    "halfdome_side_join_out": ("s18", "halfdome", 3, +0.5, False, 2, 81.7345),
    "eighth_ball_bottom_join_out": ("s18", "eighth", 2, +0.5, False, 2, 46.7279),
    "dome270_bottom_join_out": ("s19", "dome270", 2, +0.5, False, 2, 87.3133),
    "dome270_side_join_out": ("s19", "dome270", 3, +0.5, False, 2, 113.7486),
    "dome270_side_join_in": ("s19", "dome270", 3, -0.5, False, 2, 83.7681),
    "dome270_side_in": ("s19", "dome270", 3, -0.5, False, 0, 83.7681),
    "dome270_side_join_out_thick": ("s19", "dome270", 3, +1.0, False, 2, 260.9367),
    "eighth_ball_bottom_out": ("s19", "eighth", 2, +0.5, False, 0, 45.5612),
    "dome120_bottom_out": ("s19", "dome120", 2, +0.5, False, 0, 52.4334),
    "dome120_side_in": ("s19", "dome120", 3, -0.5, False, 0, 41.2951),
    "eighth_ball_sphere_out": ("s19", "eighth", 1, +0.5, False, 0, 32.3576),
    "eighth_ball_sphere_join_out": ("s19", "eighth", 1, +0.5, False, 2, 33.2167),
    "dome120_sphere_join_out": ("s19", "dome120", 1, +0.5, False, 2, 35.8993),
    "halfdome_sphere_out": ("s19", "halfdome", 1, +0.5, False, 0, 41.0976),
    "halfdome_sphere_join_out": ("s19", "halfdome", 1, +0.5, False, 2, 41.6307),
    "lune_sphere_out": ("s19", "lune", 1, +0.5, False, 0, 41.0976),
    "lune_sphere_in": ("s19", "lune", 1, -0.5, False, 0, 36.6474),
    "dome270_sphere_join_out": ("s19", "dome270", 1, +0.5, False, 2, 50.0446),
    "dome270_sphere_out_thick": ("s19", "dome270", 1, +1.0, False, 0, 99.0413),
    "placed_dome_flat_out": ("s20", "placed_dome", 2, +0.5, False, 0, 86.6556),
    "placed_cone_base_join_out": ("s20", "placed_cone", 2, +0.5, False, 2, 52.4563),
    "placed_coneup_base_out": ("s20", "placed_coneup", 2, +0.5, False, 0, 52.4095),
    "placed_halfdome_bottom_join_out": ("s20", "placed_halfdome", 2, +0.5, False, 2, 67.0206),
    "turned_filletbox_out": ("s20", "turned_filletbox", 4, +1, False, 0, 405.9034),
    "turned_halfcap_sphere_in": ("s20", "turned_halfcap", 1, -0.5, False, 0, 19.2316),
    "turned_halfcap_sphere_join_in": ("s20", "turned_halfcap", 1, -0.5, False, 2, 19.2316),
    "turned_bullet_side_join_out": ("s20", "turned_bullet", 1, +0.5, False, 2, 100.7315),
    "halfball_flat_join_out": ("s20", "halfball", 2, +0.5, False, 2, 113.0909),
    "halfball_flat_join_in": ("s20", "halfball", 2, -0.5, False, 2, 89.0272),
    "halfball_sphere_out": ("s20", "halfball", 1, +0.5, False, 0, 39.1390),
    "halfball_sphere_join_out": ("s20", "halfball", 1, +0.5, False, 2, 39.1390),
    "luneball_spheres_out": ("s20", "luneball", [1, 2], +0.5, False, 0, 39.1390),
    "eqball_flat_join_out": ("s20", "eqball", 3, +0.5, False, 2, 113.0909),
    "eqball_flat_join_in": ("s20", "eqball", 3, -0.5, False, 2, 89.0272),
    "dome2_flat_out": ("s21a", "dome2", 2, +0.5, False, 0, 86.6556),
    "dome2_flat_in": ("s21a", "dome2", 2, -0.5, False, 0, 70.9476),
    "dome2_sphere_out": ("s21a", "dome2", 1, +0.5, False, 0, 39.1390),
    "dome2_sphere_join_in": ("s21a", "dome2", 1, -0.5, False, 2, 39.1390),
    "dome2f_sphere_out": ("s21a", "dome2f", 1, +0.5, False, 0, 39.1390),
    "halfball1_sphere_out": ("s21a", "halfball1", 1, +0.5, False, 0, 39.1390),
    "halfball1_sphere_in": ("s21a", "halfball1", 1, -0.5, False, 0, 39.1390),
    "halfball1_disc_join_out": ("s21b", "halfball1", 2, +0.5, False, 2, 86.6556),
    "halfball1_disc_join_in": ("s21b", "halfball1", 2, -0.5, False, 2, 70.9476),
    "halfball1_sphere_join_out": ("s21b", "halfball1", 1, +0.5, False, 2, 39.1390),
    "cutball_disc_join_out": ("s21b", "cutball", 2, +0.5, False, 2, 86.6556),
    "cutball_sphere_out": ("s21b", "cutball", 1, +0.5, False, 0, 39.1390),
    "luneball_flat_join_out": ("s21c", "luneball", 3, +0.5, False, 2, 113.0909),
    "luneball_flat_join_in": ("s21c", "luneball", 3, -0.5, False, 2, 89.0272),
    "eqball_spheres_out": ("s21c", "eqball", [1, 2], +0.5, False, 0, 39.1390),
    "eqball_spheres_join_out": ("s21c", "eqball", [1, 2], +0.5, False, 2, 39.1390),
    "ball270_sphere_out": ("s22a", "ball270", 1, +0.5, False, 0, 36.6474),
    "ball270_sphere_join_out": ("s22a", "ball270", 1, +0.5, False, 2, 36.6474),
    "ball240_sphere_join_out": ("s22a", "ball240", 1, +0.5, False, 2, 37.6996),
    "ball150_sphere_out": ("s22a", "ball150", 1, +0.5, False, 0, 39.7919),
    "dome2f_flat_join_out": ("s22b", "dome2f", 2, +0.5, False, 2, 113.0909),
    "dome2f_flat_join_in": ("s22b", "dome2f", 2, -0.5, False, 2, 89.0272),
    "boxsplit_side_out": ("s22c", "boxsplit", 1, +0.5, False, 0, 177.6136),
    "boxsplit_side_in": ("s22c", "boxsplit", 1, -0.5, False, 0, 147.5),
    "cylseam_top_out": ("s22c", "cylseam", 2, +0.5, False, 0, 110.4400),
    "ball270split_sphere_join_in": ("s22c", "ball270split", 1, -0.5, False, 2, 41.6307),
    "axiswedge270_sphere_join_in": ("s22c", "axiswedge270", 1, -0.5, False, 2, 41.6307),
    "axiswedge270_sphere_out": ("s22c", "axiswedge270", 1, +0.5, False, 0, 36.6474),
    "eqball_sphere1_join_out": ("s23", "eqball", 1, +0.5, False, 2, 91.1786),
    "eqball_sphere1_join_in": ("s23", "eqball", 1, -0.5, False, 2, 74.1857),
    "luneball_sphere1_join_out": ("s23", "luneball", 1, +0.5, False, 2, 91.1786),
    "luneball_sphere1_join_in": ("s23", "luneball", 1, -0.5, False, 2, 74.1857),
    "turned_eqball_sphere2_join_in": ("s23", "turned_eqball", 2, -0.5, False, 2, 74.1857),
    "placed_luneball_sphere2_join_out": ("s23", "placed_luneball", 2, +0.5, False, 2, 91.1786),
    "capsplit_sphere_out": ("s24", "capsplit", 1, +0.5, False, 0, 31.285),
    "bulletsplit_flat_out": ("s24", "bulletsplit", 3, +0.5, False, 0, 152.629),
    "bulletsplit_sphere_in": ("s24", "bulletsplit", 2, -0.5, False, 0, 97.2749),
    "dome270split_side_out": ("s24", "dome270split", 3, +0.5, False, 0, 111.7391),
    "eqball_sphere1_out": ("s25", "eqball", 1, +0.5, False, 0, 89.1638),
    "eqball_sphere1_in": ("s25", "eqball", 1, -0.5, False, 0, 73.5777),
    "luneball_sphere1_out": ("s25", "luneball", 1, +0.5, False, 0, 89.1638),
    "luneball_sphere1_in": ("s25", "luneball", 1, -0.5, False, 0, 73.5777),
    "turned_eqball_sphere2_in": ("s25", "turned_eqball", 2, -0.5, False, 0, 73.5777),
    "placed_luneball_sphere2_in": ("s25", "placed_luneball", 2, -0.5, False, 0, 73.5777),
    "cutballsplit_sphere_out": ("s26a", "cutballsplit", 1, +0.5, False, 0, 39.1390),
    "cutballsplit_disc_join_out": ("s26a", "cutballsplit", 2, +0.5, False, 2, 86.6556),
    "cutballsplit_disc_join_in": ("s26a", "cutballsplit", 2, -0.5, False, 2, 70.9476),
    "luneball_flatsfirst_sphere1_join_out": ("s26b", "luneball_flatsfirst", 3, +0.5, False, 2, 91.1786),
    "luneball_flatsfirst_sphere2_join_in": ("s26b", "luneball_flatsfirst", 4, -0.5, False, 2, 74.1857),
    "luneballsplit_sphere1_join_out": ("s26b", "luneballsplit", 1, +0.5, False, 2, 91.1786),
    "luneballsplit_sphere1_join_in": ("s26b", "luneballsplit", 1, -0.5, False, 2, 74.1857),
    "mitrebox_x0y8_join_in": ("s28", "mitrebox_x0y8", 4, -1, False, 2, 228.2242),
    "mitrebox_x0y8_join_out": ("s28", "mitrebox_x0y8", 4, +1, False, 2, 334.7817),
    "mitrebox_x10y0_join_in": ("s28", "mitrebox_x10y0", 4, -1, False, 2, 228.2242),
    "mitrebox_x10y0_join_out": ("s28", "mitrebox_x10y0", 4, +1, False, 2, 334.7817),
    "mitrebox_x10y8_join_in": ("s28", "mitrebox_x10y8", 6, -1, False, 2, 228.2242),
    "mitrebox_x10y8_join_out": ("s28", "mitrebox_x10y8", 6, +1, False, 2, 334.7817),
    "roundtop_join_in": ("s29", "roundtop", 4, -1, False, 2, 217.7906),
    "roundtop_join_out": ("s29", "roundtop", 4, +1, False, 2, 313.2065),
    "dome_join_in": ("s30", "filleteddome", 4, -1, False, 2, 10416.5477),
    "dome_join_in_2": ("s30", "filleteddome", 4, -2, False, 2, 20254.4292),
    "dome_join_out": ("s31", "filleteddome", 4, 1, False, 2, 11010.6637),
    "dome_join_out_2": ("s31", "filleteddome", 4, 2, False, 2, 22629.5034),
    # The same dome with the dome itself (Face9) removed, the Arc join: tubes
    # round its tangent edges, inward (sec 34) and outward (sec 35).
    "dome_cap_removed_in_0_5": ("s34", "filleteddome", 9, -0.5, False, 0, 5536.4205),
    "dome_cap_removed_in_1": ("s34", "filleteddome", 9, -1, False, 0, 10903.5721),
    "dome_cap_removed_in": ("s34", "filleteddome", 9, -2, False, 0, 21141.2680),
    "dome_cap_removed_in_2_5": ("s34", "filleteddome", 9, -2.5, False, 0, 26016.1606),
    "dome_cap_removed_out_0_5": ("s35", "filleteddome", 9, 0.5, False, 0, 5783.3829),
    "dome_cap_removed_out_1": ("s35", "filleteddome", 9, 1, False, 0, 11891.1235),
    "dome_cap_removed_out_1_5": ("s35", "filleteddome", 9, 1.5, False, 0, 18325.2355),
    "dome_cap_removed_out": ("s35", "filleteddome", 9, 2, False, 0, 25087.2990),
    "dome_cap_removed_out_2_5": ("s35", "filleteddome", 9, 2.5, False, 0, 32178.6711),
    "dome_cap_removed_out_3": ("s35", "filleteddome", 9, 3, False, 0, 39601.1422),
    "dome_cap_removed_out_4": ("s35", "filleteddome", 9, 4, False, 0, 55446.4475),
    # A grooved cylinder, the groove one face with its seam on one bottom's
    # edge, the other bottom removed (sec 36).
    "issue363_groove5_groove_seam_left_bottom_in": ("s36", "groove5seam", 4, -1, False, 0, 5600.5842),
    "issue363_thickness001_left_bottom_in": ("s36", "issue363base", 5, -1, False, 0, 5933.2710),
    # The cylinder with a step cut off its side, each face but the side
    # removed, the Intersection join (sec 37).
    "step_top_in_join": ("s37", "step", 5, -1, False, 2, 4028.4994),
    "step_wall_in_join": ("s37", "step", 3, -1, False, 2, 5501.2992),
    "step_ceiling_in_join": ("s37", "step", 4, -1, False, 2, 5434.6552),
    "step_bottom_in_join": ("s37", "step", 2, -1, False, 2, 4555.7822),
    "step_top_out_join": ("s37", "step", 5, 1, False, 2, 4443.8934),
    "step_wall_out_join": ("s37", "step", 3, 1, False, 2, 6205.8133),
    "step_ceiling_out_join": ("s37", "step", 4, 1, False, 2, 6148.6061),
    "step_bottom_out_join": ("s37", "step", 2, 1, False, 2, 4996.9311),
    # #521's Connect, -0.5, intersection on (sec 38).
    "issue521_connect_top_in_join": ("s38", "issue521", 6, -0.5, True, 2, 262.7776),
    "issue521_connect_wall_x0_in_join": ("s38", "issue521", 5, -0.5, True, 2, 270.4120),
    "issue521_connect_wall_y0_in_join": ("s38", "issue521", 3, -0.5, True, 2, 270.4120),
    "issue521_connect_wall_y0_in": ("s38", "issue521", 3, -0.5, False, 0, 269.8020),
    # The step with its ceiling removed, the Arc join (sec 39).
    "step_ceiling_in": ("s39", "step", 4, -1, False, 0, 5434.6552),
    "step_ceiling_out": ("s39", "step", 4, 1, False, 0, 6078.0044),
    "issue346_dimple_solid_thick": ("s40", "dimple346", 3, -1, False, 0, 5287.5411),
    "issue346_peak_solid_thick": ("s40", "peak346", 3, -0.5, False, 0, 2712.9873),
    "issue613_fillet_top_bottom_out": ("s41", "issue613", [7, 16], 2, False, 0, 11247.7097),
    "issue613_fillet_top_out": ("s41", "issue613", 7, 2, False, 0, 14889.3719),
    "issue363_thickness001_in_join": ("s42", "issue363base", [3, 5], -1, False, 2, 5495.9827),
    "issue363_thickness001_out_join": ("s42", "issue363base", [3, 5], 1, False, 2, 5843.3934),
    "issue346_revolve_thick_out_join": ("s43", "revolve346", 1, 2, False, 2, 6198.1628),
    "issue346_revolve_thick_in_join": ("s43", "revolve346", 1, -1, False, 2, 2896.5118),
    "issue346_dimple_solid_thick_out_join": ("s44", "dimple346", 3, 1, False, 2, 5749.7112),
    "issue521_connect_cylinder_in": ("s45", "issue521", 4, -0.5, False, 0, 264.8641),
    "issue521_connect_cylinder_in_join": ("s45", "issue521", 4, -0.5, True, 2, 264.8641),
    "issue363_thickness001_groove_out_join": ("s46", "issue363base", 4, 1, False, 2, 5491.6348),
    "issue363_thickness001_top_out_join": ("s46", "issue363base", 6, 1, False, 2, 5071.2208),
    "slot_ceiling_in_join": ("s46", "slot", 4, -1, False, 2, 5519.7372),
    "issue363_groove10_top_out_join": ("s47", "groove10", 6, 1, False, 2, 4854.5817),
    "issue363_groove10_bottom_out_join": ("s47", "groove10", 2, 1, False, 2, 6459.0048),
    "slot_left_wall_in_join": ("s48", "slot", 5, -1, False, 2, 6128.2407),
    "issue363_groove10_both_bottoms_out_half_join": ("s49", "groove10", [2, 5], 0.5, False, 2, 2853.0372),
    "issue521_connect_cylinder_out_join": ("s50", "issue521", 4, 1, True, 2, 688.9322),
    "issue363_box_groove10_left_out_join": ("s51", "boxgroove10", 6, 1, False, 2, 8212.2444),
    "issue363_groove10_left_in_join": ("s52", "groove10", 4, -1, False, 2, 5589.2394),
    "issue363_groove10_left_out": ("s53", "groove10", 4, 1, False, 0, 6238.2052),
    "step_side_out_join": ("s54", "step", 1, 1, False, 2, 4658.7586),
    "issue363_groove10_side_out_join": ("s55", "groove10", 1, 1, False, 2, 4766.5338),
    "issue346_revolve_thick_in": ("s56", "revolve346", 1, -1, False, 0, 2896.5118),
    "issue346_revolve_thick_out_join_level2": ("s57", "revolve346", 1, 2, False, 2, 6198.0920),
    "issue346_peak_shell_thick_in_join": ("s58", "peakshell346", 1, -1, False, 2, 2922.2257),
    "issue346_dome_removed_in_refused": ("s59", "revolve346", 2, -1, False, 0, None),
    "issue346_steep_dimple_shell_apex_thick_out_level3": ("s59", "steepdimpleshell346", 1, 1, False,
                                                          0, 3008.6805),
    "issue360_plate_top_in4_inter": ("s60", "issue360", 5, -4, True, 0, 38747.1395),
    "plate_row2_top_in4_inter": ("s60", "platerow2", 3, -4, True, 0, 15869.0119),
    "plate_staggered_top_in4_inter": ("s60", "platestaggered", 3, -4, True, 0, 15683.8564),
    "plate_edge6_top_in4_inter": ("s60", "plateedge6", 3, -4, True, 0, 15165.1911),
    "plate_grid_top_in4_inter": ("s61", "plategrid", 3, -4, True, 0, 21014.4693),
    "issue360_plate_top_in2_inter": ("s61", "issue360", 5, -2, True, 0, 33213.1056),
    "plate_round2_top_in4_inter": ("s62", "plateround2", 3, -4, True, 0, 15826.1480),
    "plate_roundedge3_top_in4_inter": ("s62", "plateroundedge3", 3, -4, True, 0, 14876.6460),
}
# Cases whose right result is more than one shell: the holed cone's top, its
# cavity sealed below the removed face (a skin and a void).
SHELLS = {
    "conehole_top_in": 2,
    "conehole_top_inter_in": 2,
}
# Cases whose right result is several solids, a compound: the faces that
# stay fall apart into pieces once the removed ones are gone (sec 11).
SOLIDS = {
    "cyl_side_out": 2,
    "cyl_side_in": 2,
    "cyl_side_join_out": 2,
    "blind_top_out": 2,
    "pocket_top_in": 2,
    "cylpocket_top_join_out": 2,
    "blind_wall_out_join": 2,
    "pocket_top_out_inter_join": 2,
    "cylboss_shoulder_in": 2,
    "turned_bullet_side_join_out": 2,
    "step_side_out_join": 2,
    "issue363_groove10_side_out_join": 2,
}
# Cases pictured for what the thickness leaves of its input: the panels show
# the input after the call, and the reference volume is the input's own
# (sec 14: the thickness was right and left its input inside out).
INPUT = {
    "sector_outer_arc_input",
}
# Cases whose right outcome is a refusal: every face is removed, no face
# stays to be thickened (sec 15). The panels show the input.
REFUSED = {
    "sphere_face_refused_in",
    "box_all_faces_refused_in",
    "issue346_dome_removed_in_refused",
}
# Cases made at a fix level of the fork's (BRepOffset_SetFixLevel, 0 unless
# set): the fix comes at that level only, so that a document saved before
# recomputes as it did (sec 31). Libraries without the level run them as
# they are. None now: sec 31's fixes are made at every level (sec 32).
FIX_LEVEL = {
    "issue346_revolve_thick_out_join_level2": 2,
    "issue346_steep_dimple_shell_apex_thick_out_level3": 3,
}
# The captured user models; upstream 8.0.1 passes them all, so not pictured.
DOCS = {
    "issue1_ellipse_thickness": ("issue1_ellipse_thickness.FCStd", "Thickness", 3598.2930),
    "issue3_pad_thickness": ("issue3_pad_thickness.FCStd", "Thickness", 1241.0718),
    "issue4_revolution_thickness": ("issue4_revolution_thickness.FCStd", "Thickness", 431.4454),
}
