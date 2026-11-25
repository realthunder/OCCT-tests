# frozen_run.py: runs a test suite with every input frozen, as a FreeCAD document's value is.
#
#   SUITE=<suite script> FreeCADCmd tests/fork/frozen_run.py
#
# FreeCAD freezes a shape stored in a document (Part's ImmutableShapeValues, on with the
# fork; the TKBRep Immutable flag): what would change it changes a copy. A suite builds its
# shapes in Python and never stores them, so it runs unfrozen. Here a profile hook stores
# each shape in a Part::Feature of a scratch document just before a modelling method of it
# is called -- the property shares the shape's TShapes and marks them -- so the call runs on
# the shape frozen in place. The preference is set on for the run; the suite's own switch
# must agree (THICK_FREEZE=1, FILLET_FREEZE=1, DRAFT_FREEZE=1 for those suites; the boolean
# suite has none), and freeze.py puts the user's value back. Compare the suite's case lines
# with its plain run: they should be the same (thickness README sec 109).
import os
import runpy
import sys

import FreeCAD as App

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from freeze import set_for_run  # noqa: E402

METHODS = {"makeThickness", "makeFillet", "makeChamfer", "fuse", "cut", "common",
           "generalFuse", "makeOffsetShape", "makeOffset2D", "removeSplitter", "makeDraft"}
_doc = [None]


def _hook(frame, event, arg):
    if event == "c_call" and getattr(arg, "__name__", "") in METHODS:
        shape = getattr(arg, "__self__", None)
        if shape is not None:
            if _doc[0] is None:
                _doc[0] = App.newDocument("FrozenRun", hidden=True, temp=True)
            _doc[0].addObject("Part::Feature", "F").Shape = shape


script = os.environ["SUITE"]
set_for_run(True)
sys.argv = [script]
sys.path.insert(0, os.path.dirname(os.path.abspath(script)))
sys.setprofile(_hook)
runpy.run_path(script, run_name="__main__")
