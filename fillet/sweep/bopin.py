# The sweep's inputs put to BOP's argument check (Part's check(True)), run
# inside FreeCADCmd: writes OUT (default baseline/inputs_bop.txt), a line
# "<name> clean" or "<name> b:<what it reports>" per shape of shapes.lst.
# fsw_bop.py does not run the cases of an input that fails the check itself:
# its results inherit the fault (and the check of a loose one takes minutes).
import os
import Part

HERE = os.path.expanduser(os.environ.get("SWEEP", "~/works/sw/occt/tests/fork/fillet/sweep"))


def bop(s):
    try:
        s.check(True)
        return "clean"
    except Exception as e:
        n = {}
        for l in str(e).split("\n"):
            if l.strip().startswith("Error in "):
                t, k = l.strip()[9:].split(":", 1)
                k = t.strip() + "/" + k.replace("BOPAlgo", "").replace("_", "").replace(" ", "")
                n[k] = n.get(k, 0) + 1
        return "b:" + ",".join("%s*%d" % x for x in sorted(n.items()))


out = open(os.environ.get("OUT", os.path.join(HERE, "baseline", "inputs_bop.txt")), "w")
for l in open(os.path.join(HERE, "shapes.lst")):
    w = l.split()
    if len(w) >= 2 and not w[0].startswith("#"):
        out.write("%s %s\n" % (w[0], bop(Part.read(os.path.normpath(os.path.join(HERE, w[1]))))))
        out.flush()
