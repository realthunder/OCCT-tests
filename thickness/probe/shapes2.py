# shapes2.py: a second set, parts as PartDesign makes them
import FreeCAD, Part, math

V = FreeCAD.Vector


def _flat_at(z):
    return lambda e: abs(e.BoundBox.ZMin - z) < 1e-9 and abs(e.BoundBox.ZMax - z) < 1e-9


def _upright(e):
    return e.BoundBox.ZLength > 1e-6 and e.BoundBox.XLength < 1e-9 and e.BoundBox.YLength < 1e-9


def _poly(pts, h):
    return Part.Face(Part.makePolygon([V(*p) for p in pts] + [V(*pts[0])])).extrude(V(0, 0, h))


def enclosure():
    # a box with its upright edges and its bottom edges rounded
    b = Part.makeBox(40, 30, 15)
    b = b.makeFillet(5, [e for e in b.Edges if _upright(e)])
    return b.makeFillet(2, [e for e in b.Edges if _flat_at(0)(e)])


def plate_holes():
    p = Part.makeBox(40, 30, 6)
    for x, y in ((8, 8), (32, 8), (8, 22), (32, 22)):
        p = p.cut(Part.makeCylinder(2.5, 6, V(x, y, 0)))
    return p.removeSplitter()


def plate_slot():
    p = Part.makeBox(40, 20, 6)
    s = (
        Part.makeBox(16, 6, 6, V(12, 7, 0))
        .fuse(Part.makeCylinder(3, 6, V(12, 10, 0)))
        .fuse(Part.makeCylinder(3, 6, V(28, 10, 0)))
    )
    return p.cut(s).removeSplitter()


def step_block():
    return _poly([(0, 0, 0), (40, 0, 0), (40, 10, 0), (20, 10, 0), (20, 20, 0), (0, 20, 0)], 12)


def step_block_fillet():
    s = step_block()
    inner = [
        e
        for e in s.Edges
        if _upright(e) and abs(e.BoundBox.XMin - 20) < 1e-9 and abs(e.BoundBox.YMin - 10) < 1e-9
    ]
    return s.makeFillet(3, inner)


def stepped_shaft():
    return Part.makeCylinder(10, 8).fuse(Part.makeCylinder(6, 14, V(0, 0, 8))).removeSplitter()


def stepped_shaft_fillet():
    s = stepped_shaft()
    foot = [e for e in s.Edges if _flat_at(8)(e) and e.BoundBox.XLength < 13]
    return s.makeFillet(2, foot)


def rib():
    b = Part.makeBox(40, 20, 4)
    r = _poly([(18, 0, 4), (22, 0, 4), (22, 20, 4), (18, 20, 4)], 10)
    return b.fuse(r).removeSplitter()


def boss_hole():
    s = Part.makeBox(30, 30, 5).fuse(Part.makeCylinder(8, 10, V(15, 15, 5)))
    return s.cut(Part.makeCylinder(4, 15, V(15, 15, 0))).removeSplitter()


def u_channel():
    return _poly(
        [
            (0, 0, 0),
            (30, 0, 0),
            (30, 20, 0),
            (24, 20, 0),
            (24, 6, 0),
            (6, 6, 0),
            (6, 20, 0),
            (0, 20, 0),
        ],
        15,
    )


def u_channel_fillet():
    s = u_channel()
    inner = [e for e in s.Edges if _upright(e) and abs(e.BoundBox.YMin - 6) < 1e-9]
    return s.makeFillet(2, inner)


def t_slot():
    return _poly(
        [
            (0, 0, 0),
            (30, 0, 0),
            (30, 12, 0),
            (20, 12, 0),
            (20, 8, 0),
            (24, 8, 0),
            (24, 4, 0),
            (6, 4, 0),
            (6, 8, 0),
            (10, 8, 0),
            (10, 12, 0),
            (0, 12, 0),
        ],
        20,
    )


def hex_nut():
    pts = [
        (10 * math.cos(math.radians(60 * i)), 10 * math.sin(math.radians(60 * i)), 0)
        for i in range(6)
    ]
    return _poly(pts, 8).cut(Part.makeCylinder(4, 8)).removeSplitter()


def cone_frustum():
    return Part.makeCone(12, 8, 12)


def cyl_chamfer_both():
    c = Part.makeCylinder(10, 12)
    return c.makeChamfer(1.5, [e for e in c.Edges if _flat_at(12)(e) or _flat_at(0)(e)])


def box_fillet_bottom_chamfer_top():
    b = Part.makeBox(30, 20, 10)
    b = b.makeFillet(2, [e for e in b.Edges if _flat_at(0)(e)])
    return b.makeChamfer(1.5, [e for e in b.Edges if _flat_at(10)(e)])


def pocket_round():
    s = Part.makeBox(40, 30, 10)
    p = Part.makeBox(24, 14, 6, V(8, 8, 4))
    p = p.makeFillet(3, [e for e in p.Edges if _upright(e)])
    return s.cut(p).removeSplitter()


def revolve_cup():
    w = Part.makePolygon(
        [V(0, 0, 0), V(12, 0, 0), V(15, 0, 14), V(13, 0, 14), V(10.5, 0, 2), V(0, 0, 2), V(0, 0, 0)]
    )
    return Part.Face(w).revolve(V(0, 0, 0), V(0, 0, 1), 360)


def wedge_block():
    return _poly([(0, 0, 0), (30, 0, 0), (30, 5, 0), (0, 15, 0)], 12)


def cross():
    a = Part.makeBox(30, 8, 6, V(-15, -4, 0))
    b = Part.makeBox(8, 30, 6, V(-4, -15, 0))
    return a.fuse(b).removeSplitter()


def dome_cyl():
    c = Part.makeCylinder(8, 10)
    return c.fuse(Part.makeSphere(8, V(0, 0, 10), V(0, 0, 1), 0, 90, 360)).removeSplitter()


SHAPES = {
    "enclosure": enclosure,
    "plate_holes": plate_holes,
    "plate_slot": plate_slot,
    "step_block": step_block,
    "step_block_fillet": step_block_fillet,
    "stepped_shaft": stepped_shaft,
    "stepped_shaft_fillet": stepped_shaft_fillet,
    "rib": rib,
    "boss_hole": boss_hole,
    "u_channel": u_channel,
    "u_channel_fillet": u_channel_fillet,
    "t_slot": t_slot,
    "hex_nut": hex_nut,
    "cone_frustum": cone_frustum,
    "cyl_chamfer_both": cyl_chamfer_both,
    "box_fillet_bottom_chamfer_top": box_fillet_bottom_chamfer_top,
    "pocket_round": pocket_round,
    "revolve_cup": revolve_cup,
    "wedge_block": wedge_block,
    "cross": cross,
    "dome_cyl": dome_cyl,
}
