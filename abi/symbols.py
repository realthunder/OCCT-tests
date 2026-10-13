#!/usr/bin/env python3
"""symbols.py <upstream lib dir> <fork lib dir> [user binary ...]

The symbols each libTK* of upstream exports, against the fork's library of
the same name: one that is missing is a client of upstream's library that no
longer loads (README.md). Then, for each user binary named -- a library or a
Python extension built against upstream -- the OCCT symbols it imports that
the fork does not export.

The missing ones are written, demangled, to missing.txt in the current
directory. Exit status 1 when a strong symbol is missing or a user imports
one the fork lacks. A weak one alone does not fail: it is an inline function
or a template's instance that this build of upstream happened to keep and
this build of the fork did not (with gcc, a piece of std::sort for a
comparison the fork no longer makes), and a client that uses it has its own.
"""
import glob
import os
import platform
import subprocess
import sys

MAC = platform.system() == "Darwin"
EXT = ".dylib" if MAC else ".so"


def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True).stdout


def defined(lib):
    """(strong, weak) exported symbols"""
    strong, weak = set(), set()
    if MAC:
        for l in run(["nm", "-gUm", lib]).splitlines():
            if l.strip() and "private external" not in l:
                (weak if "weak" in l.split(")")[-1] else strong).add(l.split()[-1])
    else:
        for l in run(["nm", "-D", "--defined-only", lib]).splitlines():
            f = l.split()
            if len(f) >= 3:
                (weak if f[-2] in "WVwv" else strong).add(f[-1])
    return strong, weak


def undefined(lib):
    out = run(["nm", "-gu", lib] if MAC else ["nm", "-D", "--undefined-only", lib])
    return {l.split()[-1] for l in out.splitlines() if l.strip()}


def demangle(names):
    names = sorted(names)
    return run(["c++filt"] + names).splitlines() if names else []


def libs(d):
    """toolkit -> its library (the real file, not a link to it)"""
    r = {}
    for p in glob.glob(os.path.join(d, "libTK*" + EXT + "*")):
        if not os.path.islink(p):
            r[os.path.basename(p).split(".")[0][3:]] = p
    return r


def main():
    up, fork = libs(sys.argv[1]), libs(sys.argv[2])
    print("libraries: upstream %d, fork %d; only upstream's: %s" % (
        len(up), len(fork), " ".join(sorted(set(up) - set(fork))) or "none"))
    ud = {tk: defined(up[tk]) for tk in sorted(set(up) & set(fork))}
    fd = {tk: defined(fork[tk]) for tk in ud}
    uall = set().union(*[s | w for s, w in ud.values()])
    fall = set().union(*[s | w for s, w in fd.values()])
    nup = nadd = bad = 0
    missing = []
    for tk in ud:
        (us, uw), (fs, fw) = ud[tk], fd[tk]
        f = fs | fw
        gone_s, gone_w, added = us - f, uw - f, f - us - uw
        nup += len(us | uw)
        nadd += len(added)
        bad += len(gone_s)
        if gone_s or gone_w:
            print("%-14s missing: %d strong, %d weak" % (tk, len(gone_s), len(gone_w)))
        missing += ["%s strong %s" % (tk, n) for n in demangle(gone_s)]
        missing += ["%s weak   %s" % (tk, n) for n in demangle(gone_w)]
    print("upstream exports %d symbols; the fork lacks %d (%d strong) and adds %d" % (
        nup, len(missing), bad, nadd))
    for user in sys.argv[3:]:
        und = undefined(user)
        lost = {n for n in und if n in uall and n not in fall}
        print("%-50s imports %4d of OCCT's, %d not in the fork" % (
            os.path.basename(user)[:50], len({n for n in und if n in uall or n in fall}),
            len(lost)))
        missing += ["%s imports %s" % (os.path.basename(user), n) for n in demangle(lost)]
        bad += len(lost)
    with open("missing.txt", "w") as out:
        out.write("".join(m + "\n" for m in missing))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
