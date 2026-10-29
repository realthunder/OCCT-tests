# The fork's offset fix level (BRepOffset_SetFixLevel, BRepOffset.hxx) for a
# suite run by FreeCADCmd: env THICK_FIX_LEVEL=<n> sets it on the calling
# thread, which is the one the suite's offsets run on. Found through ctypes in
# the TKOffset FreeCAD has loaded, so a FreeCAD that knows nothing of the
# level runs the suite at any level.
import ctypes
import os


def _tkoffset():
    try:
        with open("/proc/self/maps") as f:
            for line in f:
                if "libTKOffset" in line:
                    return ctypes.CDLL(line.split()[-1])
    except OSError:
        pass
    # macOS has no /proc: walk the images dyld has loaded. A bare name would be
    # looked up on the library path and can find another OCCT's (Homebrew's
    # 7.6 in /usr/local), which has no level.
    try:
        dyld = ctypes.CDLL("/usr/lib/libSystem.B.dylib")
        dyld._dyld_get_image_name.restype = ctypes.c_char_p
        for i in range(dyld._dyld_image_count()):
            path = dyld._dyld_get_image_name(i).decode()
            if "libTKOffset" in path:
                lib = ctypes.CDLL(path)
                if hasattr(lib, "BRepOffset_SetFixLevel"):
                    return lib
    except (OSError, AttributeError):
        pass
    for name in ("libTKOffset.dylib", "TKOffset.dll", "libTKOffset.so"):
        try:
            return ctypes.CDLL(name)
        except OSError:
            pass
    return None


def set_offset_fix_level(level):
    """Sets the level, returns the one before; None where the libraries lack it."""
    lib = _tkoffset()
    if lib is None or not hasattr(lib, "BRepOffset_SetFixLevel"):
        return None
    return lib.BRepOffset_SetFixLevel(ctypes.c_int(level))


def from_env():
    """THICK_FIX_LEVEL, if set: sets it and returns it, else None."""
    level = os.environ.get("THICK_FIX_LEVEL")
    if level is None:
        return None
    if set_offset_fix_level(int(level)) is None:
        raise RuntimeError("THICK_FIX_LEVEL set, but TKOffset has no BRepOffset_SetFixLevel")
    return int(level)
