# The fork's ChFi3d_SetFlatEndAtVertex (ChFi3d_Builder::SetFlatEndAtVertex)
# from Python: a fillet's end at a vertex that would cut into the body past
# the vertex ends flat instead. Looked up at run time in what is loaded, as
# FreeCAD looks it up, so it reaches the TKFillet FreeCAD itself runs. The
# setting is the calling thread's.
import ctypes
import sys

_func = None


def _lookup():
    global _func
    if _func is None:
        if sys.platform == "darwin":
            # dlsym(RTLD_DEFAULT, ...): every image loaded
            lib = ctypes.CDLL("RTLD_DEFAULT", handle=ctypes.c_void_p(-2).value)
        elif sys.platform == "win32":
            lib = ctypes.CDLL("TKFillet.dll")
        else:
            lib = ctypes.CDLL(None)
        try:
            _func = lib.ChFi3d_SetFlatEndAtVertex
        except AttributeError:
            raise RuntimeError("this TKFillet has no ChFi3d_SetFlatEndAtVertex")
        _func.argtypes = [ctypes.c_int]
        _func.restype = ctypes.c_int
    return _func


def available():
    """Whether the TKFillet loaded has it."""
    try:
        _lookup()
        return True
    except (RuntimeError, OSError):
        return False


def set_flat_end(on):
    """Sets the flat end on or off; returns the setting before."""
    return bool(_lookup()(1 if on else 0))


class FlatEnd:
    """with FlatEnd(): ... -- the flat end on inside, as before after.
    FlatEnd(False) does nothing: it runs where the function is missing."""

    def __init__(self, on=True):
        self.on = on

    def __enter__(self):
        if self.on:
            self.before = set_flat_end(True)
        return self

    def __exit__(self, *exc):
        if self.on:
            set_flat_end(self.before)
        return False
