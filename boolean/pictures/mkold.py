#!/usr/bin/env python3
# mkold.py <build dir> <out dir> <commit> <source>... -- a private copy of a
# library of the fork's build, linked from the build's own objects with the
# given sources as they were at <commit> (compiled with the build's flags).
# Loaded first (DYLD_LIBRARY_PATH / LD_LIBRARY_PATH), it gives the "before"
# of a fix without touching the install or the build tree.
#
# The library is the one that owns the first source; all must be in it.
# Example (make_pictures.sh):
#   mkold.py ~/works/sw/occt/build_conda_rwdi_801 /tmp/old 51e4faf111^ \
#       src/ModelingData/TKGeomBase/IntAna/IntAna_QuadQuadGeo.cxx
import os
import re
import subprocess
import sys

build, out, commit, sources = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4:]
ninja = os.environ.get("NINJA", "/usr/local/bin/ninja" if sys.platform == "darwin" else "ninja")
occt = subprocess.check_output(["git", "-C", build, "rev-parse", "--show-toplevel"],
                               text=True).strip()
lib = re.search(r"/(TK\w+)/", sources[0]).group(1)
os.makedirs(out, exist_ok=True)

# The library's real file (libTKx.8.0.1.dylib or libTKx.so.8.0.1) and the
# commands that make it.
targets = subprocess.check_output([ninja, "-C", build, "-t", "targets", "all"], text=True)
target = [t.split(":")[0] for t in targets.splitlines()
          if re.search(r"/lib%s\.(8\.0\.1\.dylib|so\.8\.0\.1):" % lib, t)][0]
cmds = subprocess.check_output([ninja, "-C", build, "-t", "commands", target],
                               text=True).splitlines()
link = [c for c in cmds if " -o " + target in c][-1]
link = link.split(" && ", 1)[1] if link.startswith(":") else link
link = re.sub(r"\s*&&\s*:\s*$", "", link)
soname = os.path.basename(target)
soname = re.sub(r"\.8\.0\.1\.dylib$", ".8.0.dylib", soname)
soname = re.sub(r"\.so\.8\.0\.1$", ".so.8.0", soname)

for src in sources:
    comp = [c for c in cmds if src in c and " -c " in c][0]
    obj = re.search(r" -o (\S+) -c ", comp).group(1)
    old = os.path.join(out, os.path.basename(src))
    with open(old, "w") as f:
        f.write(subprocess.check_output(["git", "-C", occt, "show", "%s:%s" % (commit, src)],
                                        text=True))
    oldobj = os.path.join(out, os.path.basename(src) + ".o")
    comp = comp.replace(" -o " + obj, " -o " + oldobj)
    comp = comp.replace(" -c " + os.path.join(occt, src), " -c " + old)
    comp = comp.replace(" -c " + src, " -c " + old)
    subprocess.check_call(comp, shell=True, cwd=build)
    link = link.replace(" " + obj + " ", " " + oldobj + " ")
link = link.replace(" -o " + target, " -o " + os.path.join(out, soname))
subprocess.check_call(link, shell=True, cwd=build)
print(os.path.join(out, soname))
