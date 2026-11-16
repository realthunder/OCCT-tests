# shapes.py: plain shapes with blends, as a FreeCAD user makes them
import FreeCAD, Part, math
V = FreeCAD.Vector


def _edges(s, test):
    return [e for e in s.Edges if test(e)]


def _flat_at(z):
    return lambda e: abs(e.BoundBox.ZMin - z) < 1e-9 and abs(e.BoundBox.ZMax - z) < 1e-9


def _upright(e):
    return e.BoundBox.ZLength > 1e-6 and e.BoundBox.XLength < 1e-9 and e.BoundBox.YLength < 1e-9


def box_top4():
    b = Part.makeBox(20, 30, 10)
    return b.makeFillet(2, _edges(b, _flat_at(10)))


def box_top2():
    b = Part.makeBox(20, 30, 10)
    return b.makeFillet(2, [e for e in _edges(b, _flat_at(10)) if e.BoundBox.YLength > 1])


def box_top1():
    b = Part.makeBox(20, 30, 10)
    return b.makeFillet(2, [e for e in _edges(b, _flat_at(10)) if e.BoundBox.YLength > 1][:1])


def box_all12():
    b = Part.makeBox(20, 30, 10)
    return b.makeFillet(2, b.Edges)


def box_round():
    b = Part.makeBox(20, 30, 10)
    b2 = b.makeFillet(4, _edges(b, _upright))
    return b2.makeFillet(2, _edges(b2, _flat_at(10)))


def box_upright4():
    b = Part.makeBox(20, 30, 10)
    return b.makeFillet(4, _edges(b, _upright))


def cyl_top():
    c = Part.makeCylinder(10, 10)
    return c.makeFillet(2, [e for e in c.Edges if _flat_at(10)(e)])


def cyl_both():
    c = Part.makeCylinder(10, 10)
    return c.makeFillet(2, [e for e in c.Edges if _flat_at(10)(e) or _flat_at(0)(e)])


def stadium():
    w = Part.Wire([Part.makeLine(V(-10, -5, 0), V(10, -5, 0)),
                   Part.ArcOfCircle(V(10, -5, 0), V(15, 0, 0), V(10, 5, 0)).toShape(),
                   Part.makeLine(V(10, 5, 0), V(-10, 5, 0)),
                   Part.ArcOfCircle(V(-10, 5, 0), V(-15, 0, 0), V(-10, -5, 0)).toShape()])
    st = Part.Face(w).extrude(V(0, 0, 8))
    return st.makeFillet(1.5, _edges(st, _flat_at(8)))


def box_chamfer_top4():
    b = Part.makeBox(20, 30, 10)
    return b.makeChamfer(2, _edges(b, _flat_at(10)))


def box_chamfer_all():
    b = Part.makeBox(20, 30, 10)
    return b.makeChamfer(2, b.Edges)


def cyl_chamfer_top():
    c = Part.makeCylinder(10, 10)
    return c.makeChamfer(2, [e for e in c.Edges if _flat_at(10)(e)])


def boss_fillet():
    s = Part.makeBox(30, 30, 5).fuse(Part.makeCylinder(6, 8, V(15, 15, 5))).removeSplitter()
    foot = [e for e in s.Edges if _flat_at(5)(e) and e.Curve.__class__.__name__ == "Circle"]
    return s.makeFillet(2, foot)


def boss_fillet_both():
    s = boss_fillet()
    top = [e for e in s.Edges if _flat_at(13)(e)]
    return s.makeFillet(1.5, top)


def pocket_fillet():
    s = Part.makeBox(30, 30, 10).cut(Part.makeBox(16, 16, 6, V(7, 7, 4)))
    floor = [e for e in s.Edges if _flat_at(4)(e)]
    return s.makeFillet(2, floor)


def lbracket():
    w = Part.makePolygon([V(0, 0, 0), V(30, 0, 0), V(30, 5, 0), V(5, 5, 0), V(5, 25, 0),
                          V(0, 25, 0), V(0, 0, 0)])
    s = Part.Face(w).extrude(V(0, 0, 12))
    inner = [e for e in s.Edges if _upright(e) and abs(e.BoundBox.XMin - 5) < 1e-9
             and abs(e.BoundBox.YMin - 5) < 1e-9]
    outer = [e for e in s.Edges if _upright(e) and abs(e.BoundBox.XMin) < 1e-9
             and abs(e.BoundBox.YMin) < 1e-9]
    return s.makeFillet(3, inner + outer)


def tube_fillet():
    s = Part.makeCylinder(10, 12).cut(Part.makeCylinder(6, 12))
    top = [e for e in s.Edges if _flat_at(12)(e)]
    return s.makeFillet(1, top)


def countersink():
    s = Part.makeBox(30, 20, 8).cut(Part.makeCylinder(3, 8, V(15, 10, 0)))
    rim = [e for e in s.Edges if _flat_at(8)(e) and e.Curve.__class__.__name__ == "Circle"]
    return s.makeChamfer(2, rim)


def hex_top():
    pts = [V(10 * math.cos(math.radians(60 * i)), 10 * math.sin(math.radians(60 * i)), 0)
           for i in range(7)]
    s = Part.Face(Part.makePolygon(pts)).extrude(V(0, 0, 8))
    return s.makeFillet(1.5, _edges(s, _flat_at(8)))


def capsule():
    c = Part.makeCylinder(5, 12)
    return c.fuse(Part.makeSphere(5, V(0, 0, 12))).removeSplitter()


def cone_fillet():
    c = Part.makeCone(10, 6, 10)
    return c.makeFillet(1.5, [e for e in c.Edges if _flat_at(10)(e)])


def wedge_fillet():
    w = Part.makePolygon([V(0, 0, 0), V(30, 0, 0), V(30, 4, 0), V(0, 14, 0), V(0, 0, 0)])
    s = Part.Face(w).extrude(V(0, 0, 15))
    slope = [e for e in s.Edges if _upright(e) and abs(e.BoundBox.XMin) < 1e-9
             and abs(e.BoundBox.YMin - 14) < 1e-9]
    return s.makeFillet(3, slope)


SHAPES = {
    "box_top4": box_top4, "box_top2": box_top2, "box_top1": box_top1, "box_all12": box_all12,
    "box_round": box_round, "box_upright4": box_upright4, "cyl_top": cyl_top, "cyl_both": cyl_both,
    "stadium": stadium, "box_chamfer_top4": box_chamfer_top4, "box_chamfer_all": box_chamfer_all,
    "cyl_chamfer_top": cyl_chamfer_top, "boss_fillet": boss_fillet,
    "boss_fillet_both": boss_fillet_both, "pocket_fillet": pocket_fillet, "lbracket": lbracket,
    "tube_fillet": tube_fillet, "countersink": countersink, "hex_top": hex_top, "capsule": capsule,
    "cone_fillet": cone_fillet, "wedge_fillet": wedge_fillet,
}
