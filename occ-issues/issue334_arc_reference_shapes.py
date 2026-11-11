# FreeCADCmd issue334_arc_reference_shapes.py -- the two shapes of the
# picture of README.md's "A face not found again for its arc": #334's body
# as the file holds it and as it recomputes. Writes
# $OUT/issue334_{stored,recomputed}.brep and prints what each is.
import os, json
import FreeCAD as App, Part
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.environ.get("OUT", HERE)
d = App.openDocument(os.path.join(HERE, "models", "issue334_draft_artifact.FCStd"))
stored = d.Body.Shape.copy()
d.recompute()
made = d.Body.Shape
info = {"stored": [round(stored.Volume, 4), stored.isValid()],
        "recomputed": [round(made.Volume, 4), made.isValid()],
        "not up to date": [o.Name for o in d.Objects if "Up-to-date" not in o.State]}
stored.exportBrep(os.path.join(OUT, "issue334_stored.brep"))
made.exportBrep(os.path.join(OUT, "issue334_recomputed.brep"))
os.write(1, ("\nPIC " + json.dumps(info) + "\n").encode())
