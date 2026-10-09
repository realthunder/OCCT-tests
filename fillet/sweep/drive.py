#!/usr/bin/env python3
# drive.py <edge|vertex> <outdir> [shape ...]: the fillet sweep (fsw.py) over
# every shape of shapes.lst (or the ones named), one FreeCADCmd per shape, one
# result line per case in <outdir>/<shape>.txt. A case with no output for
# 120 s is killed, marked TIMEOUT, and the rest of its shape run in a new
# process; a process that dies marks the case it was on CRASH and goes on the
# same way. One process at a time: an 8 GB box swaps with four.
#
# env: FCBUILD  a FreeCAD build (default: the mac or conda RelWithDebInfo
#               build of ~/works/sw/fcad)
#      RUN      the wrapper that runs a command in the build's environment
#      RADII    passed to fsw.py
#      TKF      a directory of OCCT libraries to load first (DYLD_LIBRARY_PATH /
#               LD_LIBRARY_PATH): a rebuilt TKFillet, say, without installing it.
#               Set inside RUN: macOS strips DYLD_* from a bash script's children.
import os, platform, select, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
FCAD = os.path.expanduser("~/works/sw/fcad")
MAC = platform.system() == "Darwin"
FCBUILD = os.environ.get("FCBUILD", os.path.join(
    FCAD, "build", "mac-relwithdebinfo-801" if MAC else "conda-relwithdebinfo-801"))
RUN = os.environ.get("RUN", os.path.join(FCAD, ".conda", "run.sh"))
FC = os.path.join(FCBUILD, "bin", "FreeCADCmd")

mode, out = sys.argv[1], sys.argv[2]
only = set(sys.argv[3:])
os.makedirs(out, exist_ok=True)
shapes = []
for l in open(os.path.join(HERE, "shapes.lst")):
    w = l.split()
    if len(w) >= 2 and not w[0].startswith("#") and (not only or w[0] in only):
        shapes.append((w[0], os.path.normpath(os.path.join(HERE, w[1]))))
pre = []
if os.environ.get("TKF"):
    pre = ["env", ("DYLD_LIBRARY_PATH=" if MAC else "LD_LIBRARY_PATH=") + os.environ["TKF"]]
for name, path in shapes:
    if not os.path.exists(path):
        print(name, "MISSING", path, flush=True)
        continue
    done, total, finished = [], None, False
    while not finished and (total is None or len(done) < total):
        env = dict(os.environ, SHAPE=path, MODE=mode, START=str(len(done)))
        p = subprocess.Popen([RUN] + pre + [FC, os.path.join(HERE, "fsw.py")], env=env,
                             stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                             stdin=subprocess.DEVNULL)
        last, buf, why, trying = time.time(), b"", "CRASH", "?"
        while True:
            r, _, _ = select.select([p.stdout], [], [], 5)
            if r:
                chunk = os.read(p.stdout.fileno(), 65536)
                if not chunk:
                    break
                buf += chunk
                while b"\n" in buf:
                    line, buf = buf.split(b"\n", 1)
                    w = line.decode(errors="replace").split()
                    if len(w) == 2 and w[0] == "N" and w[1].isdigit():
                        total = int(w[1])
                    elif len(w) == 3 and w[0] == "T":
                        trying = w[2]
                    elif len(w) == 3 and w[0].isdigit() and int(w[0]) == len(done):
                        done.append(w[1] + " " + w[2])
                    elif w == ["DONE"]:
                        finished = True
                    else:
                        continue
                    last = time.time()
            if time.time() - last > 120:
                p.kill()
                why = "TIMEOUT"
                break
        p.wait()
        if total is None:
            print(name, "NO OUTPUT", flush=True)
            break
        if not finished and len(done) < total:
            done.append("%s %s" % (trying, why))
    open(os.path.join(out, name + ".txt"), "w").write("".join(x + "\n" for x in done))
    print(name, len(done), flush=True)
print("FINISHED", out, flush=True)
