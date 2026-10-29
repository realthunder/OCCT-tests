# FreeCAD's ImmutableShapeValues (Part's preferences) for a script run by
# FreeCADCmd. The preference is the user's own, in the user's user.cfg: a run
# that set it and left it set ran the user's next FreeCAD -- and its test
# suites -- frozen or unfrozen behind their back. set_for_run() puts the
# user's value back before FreeCAD can save it.
#
# When it can: a script that ends in os._exit saves no parameters at all, so
# nothing reaches user.cfg. One that ends any other way -- an exception, a
# Ctrl-C, falling off its end -- has FreeCADCmd exit normally, close every
# document and then save the user parameters, and Python's atexit runs after
# that save, too late. So the value is put back as a temporary document of
# this module's own closes, which is before the save. A crash still leaves the
# run's value.
import FreeCAD as App

_GROUP = "User parameter:BaseApp/Preferences/Mod/Part"
_NAME = "ImmutableShapeValues"
_DOC = "FreezeRestore"
_observer = None


class _Restore:
    def __init__(self, grp, had, old):
        self.grp, self.had, self.old = grp, had, old

    def restore(self):
        if self.had:
            self.grp.SetBool(_NAME, self.old)
        else:
            self.grp.RemBool(_NAME)

    def slotDeletedDocument(self, doc):
        if doc.Name == _DOC:
            self.restore()


def set_for_run(frozen):
    """Sets ImmutableShapeValues to frozen until FreeCAD exits."""
    global _observer
    grp = App.ParamGet(_GROUP)
    if _observer is None:
        _observer = _Restore(grp, _NAME in grp.GetBools(), grp.GetBool(_NAME))
        App.addDocumentObserver(_observer)
        App.newDocument(_DOC, hidden=True, temp=True)
    grp.SetBool(_NAME, bool(frozen))
