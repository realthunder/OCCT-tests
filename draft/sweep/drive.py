#!/usr/bin/env python3
# drive.py <list> <outdir> [METHOD] [STOP]: draft every case of <list> (lines
# "shape face neutral angle") through PartDesign, one FreeCADCmd per shape
# (psw.py), one result line per case in <outdir>/<shape>.txt. A case with no
# output for 120 s is killed, marked TIMEOUT/CRASH, and the rest of its
# shape run in a new process. One process at a time: on an 8 GB box four at
# once drove it into swap.
#
# env: FCBUILD  a FreeCAD build (default: the mac or conda RelWithDebInfo
#               build of ~/works/sw/fcad)
#      RUN      the wrapper that runs a command in the build's environment
#      PROP     TangentPropagation, 1 (default) or 0
#      TKF      a directory of OCCT libraries to load first (DYLD_LIBRARY_PATH /
#               LD_LIBRARY_PATH): a rebuilt TKFillet, say, without installing it.
#               Set inside RUN: macOS strips DYLD_* from a bash script's children.
import os, platform, select, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
SHAPES = os.path.join(HERE, "shapes")
FCAD = os.path.expanduser("~/works/sw/fcad")
MAC = platform.system() == "Darwin"
FCBUILD = os.environ.get("FCBUILD", os.path.join(
    FCAD, "build", "mac-relwithdebinfo-801" if MAC else "conda-relwithdebinfo-801"))
RUN = os.environ.get("RUN", os.path.join(FCAD, ".conda", "run.sh"))
FC = os.path.join(FCBUILD, "bin", "FreeCADCmd")

lst, out = sys.argv[1], sys.argv[2]
method = sys.argv[3] if len(sys.argv) > 3 else "New"
stop = sys.argv[4] if len(sys.argv) > 4 else "1"
os.makedirs(out, exist_ok=True)
cases = {}
for l in open(lst):
    w = l.split()
    if len(w) >= 4:
        cases.setdefault(w[0], []).append(" ".join(w[1:4]))
pre = []
if os.environ.get("TKF"):
    pre = ["env", ("DYLD_LIBRARY_PATH=" if MAC else "LD_LIBRARY_PATH=") + os.environ["TKF"]]
for name, cs in cases.items():
    path = os.path.join(SHAPES, name + ".brep")
    done = []
    while len(done) < len(cs):
        cf = os.path.join(out, name + ".rest")
        open(cf, "w").write("\n".join(cs[len(done):]) + "\n")
        env = dict(os.environ, SHAPE=path, CASES=cf, METHOD=method, STOP=stop)
        p = subprocess.Popen([RUN] + pre + [FC, os.path.join(HERE, "psw.py")], env=env,
                             stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                             stdin=subprocess.DEVNULL)
        last = time.time()
        buf = b""
        got = 0
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
                    if len(w) >= 4 and w[0].isdigit() and w[1].isdigit():
                        done.append(" ".join(w))
                        got += 1
                        last = time.time()
            if time.time() - last > 120:
                p.kill()
                break
        p.wait()
        if len(done) < len(cs) and (got == 0 or p.returncode != 0):
            done.append(cs[len(done)] + " TIMEOUT/CRASH")
    os.remove(os.path.join(out, name + ".rest"))
    open(os.path.join(out, name + ".txt"), "w").write("\n".join(done) + "\n")
    print(name, len(done), flush=True)
print("FINISHED", out, flush=True)
