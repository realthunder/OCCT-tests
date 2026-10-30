# Compile TKBool and TKOffset again from the build tree's own compile
# commands, with the sources under $U/src and the headers under $U/inc taking
# the place of the tree's, and link them into $U/lib. Called by mkold.sh.
import os
import re
import shlex
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

U = os.environ["U"]
SRC = os.environ["OCCT"].rstrip("/") + "/"
MAC = sys.platform == "darwin"
B = os.environ.get("OCCT_BUILD", SRC + ("build_conda_rwdi_801" if MAC else "build_conda_relwithdebinfo_801"))
RUN = os.environ.get("RUN", os.path.expanduser("~/works/sw/fcad/.conda/run.sh"))
# On macOS the system ninja: conda's takes the tree for out of date.
NINJA = ["/usr/local/bin/ninja"] if MAC else [RUN, "ninja"]
out = subprocess.run(NINJA + ["-C", B, "-t", "commands", "TKOffset"],
                     capture_output=True, text=True).stdout.splitlines()
comp = []
links = []
for l in out:
    if ("TKBool.dir" in l or "TKOffset.dir" in l) and " -c " in l:
        comp.append(l)
    elif re.search(r"-o \S*libTK(Bool|Offset)(\.so(\.[0-9.]+)?|\.8\.0\.1\.dylib)( |$)", l):
        links.append(l)
print(len(comp), "objects,", len(links), "libraries")


def fix(l):
    a = shlex.split(l)
    r = []
    i = 0
    while i < len(a):
        x = a[i]
        if x == "-MD":
            i += 1
            continue
        if x in ("-MT", "-MF"):
            i += 2
            continue
        if x == "-o":
            o = U + "/obj/" + a[i + 1]
            os.makedirs(os.path.dirname(o), exist_ok=True)
            r += ["-o", o]
            i += 2
            continue
        if x.startswith(SRC + "src/") and os.path.exists(U + "/" + x[len(SRC):]):
            x = U + "/" + x[len(SRC):]
        r.append(x)
        i += 1
    r.insert(1, "-I" + U + "/inc")
    return r


def run(l):
    p = subprocess.run(fix(l), cwd=B, capture_output=True, text=True)
    if p.returncode:
        print(p.stderr[-3000:])
        return 1
    return 0


with ThreadPoolExecutor(min(os.cpu_count(), 4) if MAC else os.cpu_count()) as ex:
    bad = sum(ex.map(run, comp))
print("compile failures", bad)
if bad:
    sys.exit(1)
for l in links:
    seg = [s for s in l.split("&&") if " -o " in s][0]
    a = shlex.split(seg)
    r = [U + "/obj/" + x if x.endswith(".o") and ("TKBool.dir" in x or "TKOffset.dir" in x) else x
         for x in a]
    j = r.index("-o")
    # macOS: named as the clients' install name has it (libTKOffset.8.0.dylib),
    # which is what dyld looks up in DYLD_LIBRARY_PATH.
    r[j + 1] = U + "/lib/" + re.sub(r"\.8\.0\.1\.dylib$", ".8.0.dylib", os.path.basename(r[j + 1]))
    p = subprocess.run(r, cwd=B, capture_output=True, text=True)
    print("link", os.path.basename(r[j + 1]), p.returncode, p.stderr[-2000:])
    if p.returncode:
        sys.exit(1)
