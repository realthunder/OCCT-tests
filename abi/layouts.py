#!/usr/bin/env python3
"""layouts.py <upstream include dir> <fork include dir>

Record layouts of the classes in the headers the fork changed, upstream's
against the fork's: a class whose size changed, or a member of upstream's
that moved, is an ABI break no symbol shows (README.md).

The headers are the ones `git diff --name-only $BASE HEAD` names (BASE
defaults to upstream 8.0.1, b8f597c677) that both include directories have.
Each side is compiled once with clang's -fdump-record-layouts (CXX names
the compiler, default clang++; CXXFLAGS is added). Exit status 1 when a
record differs.
"""
import os
import re
import subprocess
import sys
import tempfile

BASE = os.environ.get("BASE", "b8f597c677")
CXX = os.environ.get("CXX", "clang++")
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, "..", "..", ".."))


def headers(up_inc, fork_inc):
    out = subprocess.run(["git", "-C", REPO, "diff", "--name-only", BASE, "HEAD", "--", "*.hxx"],
                         capture_output=True, text=True, check=True).stdout
    names = sorted({os.path.basename(p) for p in out.split()})
    return [n for n in names if os.path.exists(os.path.join(up_inc, n))
            and os.path.exists(os.path.join(fork_inc, n))]


def dump(inc, names):
    with tempfile.NamedTemporaryFile("w", suffix=".cpp", delete=False) as f:
        for n in names:
            f.write("#include <%s>\n" % n)
        # a record is laid out, and dumped, only when its size is asked for
        f.write("template <class T> struct Probe { char c[sizeof(T)]; };\n")
        src = f.name
    try:
        cmd = [CXX, "-std=c++17", "-fsyntax-only", "-DNDEBUG", "-w", "-Xclang",
               "-fdump-record-layouts-complete", "-I" + inc] + os.environ.get("CXXFLAGS", "").split()
        r = subprocess.run(cmd + [src], capture_output=True, text=True)
        if r.returncode:
            sys.exit("%s failed on %s:\n%s" % (CXX, inc, r.stderr[-2000:]))
        return r.stdout
    finally:
        os.unlink(src)


def parse(text):
    """record name -> (sizeof, [(offset, member)] of its own members and bases)"""
    recs = {}
    for blk in text.split("*** Dumping AST Record Layout")[1:]:
        lines = [l.rstrip() for l in blk.strip("\n").split("\n") if l.strip()]
        m = re.match(r"\s*0 \| (class|struct|union) (.+)$", lines[0])
        size = re.search(r"\[sizeof=(\d+)", blk)
        if not m or not size:
            continue
        own = []
        for l in lines[1:]:
            f = re.match(r"\s*(\d+)(:[\d-]+)? \|(\s+)(.*)$", l)
            if f and len(f.group(3)) <= 3:
                own.append((f.group(1) + (f.group(2) or ""), f.group(4).strip()))
        recs[m.group(2).strip()] = (int(size.group(1)), own)
    return recs


def main():
    up_inc, fork_inc = sys.argv[1], sys.argv[2]
    names = headers(up_inc, fork_inc)
    up, fork = parse(dump(up_inc, names)), parse(dump(fork_inc, names))
    broken, grown = [], []
    for name in sorted(set(up) & set(fork)):
        (us, um), (fs, fm) = up[name], fork[name]
        if um == fm and us == fs:
            continue
        # A member is its offset and its name: one given another type of the
        # same size (a double made atomic) is where it was. An empty member
        # has no storage, and where it is put is no one's concern.
        def key(x):
            return (x[0], x[1].split()[-1])
        fkeys = {key(x) for x in fm}
        ukeys = {key(x) for x in um}
        moved = [x for x in um if key(x) not in fkeys and not x[1].endswith("(empty)")]
        if us != fs or moved:
            broken.append((name, us, fs, moved))
        else:
            grown.append((name, [x for x in fm
                                 if key(x) not in ukeys and not x[1].endswith("(empty)")]))
    print("%d headers, %d records in both" % (len(names), len(set(up) & set(fork))))
    for name, added in grown:
        if added:
            print("fits   %s: %s" % (name, ", ".join("%s at %s" % (m, o) for o, m in added)))
    for name, us, fs, moved in broken:
        print("BREAK  %s: sizeof %d -> %d%s" % (
            name, us, fs, "".join("\n         upstream's %s at %s" % (m, o) for o, m in moved)))
    print("%d record(s) differ in size or in where upstream's members are" % len(broken))
    return 1 if broken else 0


if __name__ == "__main__":
    sys.exit(main())
