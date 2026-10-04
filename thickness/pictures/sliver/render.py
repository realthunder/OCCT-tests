# FreeCAD (GUI, under xvfb-run) render.py -- four views of $OUT/arc_out.brep,
# its sliver faces red, and meta.json with the cameras for compose.py.
import os, json
import FreeCAD as App, FreeCADGui as Gui, Part
V = App.Vector
def emit(s): os.write(1, (s + "\n").encode())
OUT = os.environ["OUT"]
App.ParamGet("User parameter:BaseApp/Preferences/Document").SetInt("TransactionLog", 0)
Gui.showMainWindow() if not Gui.getMainWindow() else None
def camera(eye, up, center, height):
    z = V(eye); z.normalize()
    y = up - z * up.dot(z); y.normalize()
    x = y.cross(z)
    r = App.Rotation(App.Matrix(x.x, y.x, z.x, 0, x.y, y.y, z.y, 0, x.z, y.z, z.z, 0))
    pos = center + z * 1000
    return ("#Inventor V2.1 ascii\nOrthographicCamera {\n viewportMapping ADJUST_CAMERA\n"
            " position %.9g %.9g %.9g\n orientation %.9g %.9g %.9g %.9g\n nearDistance 1\n farDistance 3000\n"
            " aspectRatio 1\n focalDistance 1000\n height %.9g\n}\n"
            % (pos.x, pos.y, pos.z, r.Axis.x, r.Axis.y, r.Axis.z, r.Angle, height)), (x, y)
shape = Part.Shape(); shape.read(OUT + "/arc_out.brep")
doc = App.newDocument("S")
obj = doc.addObject("Part::Feature", "S"); obj.Shape = shape
doc.recompute()
vo = obj.ViewObject
base = (0.62, 0.70, 0.80, 1.0)
cols = []
for f in shape.Faces:
    cols.append((0.90, 0.10, 0.10, 1.0) if f.Area < 1e-4 else base)
vo.LineColor = (0.12, 0.12, 0.18); vo.LineWidth = 1.5
vo.Deviation = 0.01; vo.AngularDeflection = 1.0
vo.DiffuseColor = cols
sl = [f for f in shape.Faces if f.Area < 1e-4 and f.CenterOfMass.x > 0][0]
c = sl.CenterOfMass
view = Gui.ActiveDocument.ActiveView
W, H = 900, 640
shots = [
    ("whole", V(0.45, -0.75, 0.95), V(0, 0, 1), V(0, 2.2, 0.1), 12.5),
    ("end", V(0.45, -0.75, 0.95), V(0, 0, 1), V(5.0, -0.2, 0.15), 1.9),
    ("corner", V(0.45, -0.75, 0.95), V(0, 0, 1), V(c.x, c.y, 0.0), 0.16),
    ("top", V(0, 0, 1), V(0, 1, 0), V(c.x - 0.002, c.y + 0.004, 0), 0.022),
]
meta = {"sliver": [c.x, c.y, c.z], "area": sl.Area, "size": [sl.BoundBox.XLength, sl.BoundBox.YLength], "W": W, "H": H, "shots": {}}
for name, eye, up, center, height in shots:
    cam, (x, y) = camera(eye, up, center, height)
    view.setCamera(cam)
    for _ in range(4): Gui.updateGui()
    view.redraw()
    view.saveImage("%s/%s.png" % (OUT, name), W, H, "#FFFFFF")
    meta["shots"][name] = dict(center=list(center), height=height, x=list(x), y=list(y))
    emit("PNG " + name)
json.dump(meta, open(OUT + "/meta.json", "w"))
emit("DONE"); os._exit(0)
