# FreeCADCmd triage.py: results of a sweep tried again on the shape refined
# (removeSplitter), to tell what is invalid for the body being in pieces from
# what is invalid on any body.
#
# env: SHAPE  a name of shapes.lst
#      LIST   a file of "shape case result" lines (grep " BAD" of a baseline,
#             say); the cases of SHAPE in it are run
#
# One line per case: T <shape> <case> split:<status> ref:<status>, a status
# being ok:<volume>, ok(bop):<volume> (valid, but Part's check(True) reports
# something), BAD:<volume> or EXC. The refined shape's edges are found by the
# middles of the case's; "ref:noedge" when one is gone -- an edge that was a
# split itself. A fresh copy of the input for each fillet.
import os, sys, Part, FreeCAD as App
def w(*a): os.write(1,(" ".join(str(x) for x in a)+"\n").encode())
HERE=os.path.dirname(os.path.abspath(__file__))
paths={}
for l in open(os.path.join(HERE,"shapes.lst")):
    l=l.split()
    if len(l)==2 and not l[0].startswith("#"): paths[l[0]]=os.path.normpath(os.path.join(HERE,l[1]))
name=os.environ["SHAPE"]
cases=[l.split()[1] for l in open(os.environ["LIST"]) if l.split() and l.split()[0]==name]
def stat(x):
    if x.isValid():
        try: x.check(True); b=""
        except Exception: b="(bop)"
        return "ok%s:%.6g"%(b,x.Volume)
    return "BAD:%.6g"%x.Volume
for c in cases:
    spec,r=c.split("@"); r=float(r)
    eis=[int(v) for v in (spec.split(":")[1] if ":" in spec else spec[1:]).split(",")]
    out=[]
    s=Part.read(paths[name])
    mids=[]
    for i in eis:
        e=s.Edges[i-1]; mids.append(e.valueAt((e.FirstParameter+e.LastParameter)/2))
    try: out.append("split:"+stat(s.makeFillet(r,[s.Edges[i-1] for i in eis])))
    except Exception: out.append("split:EXC")
    ref=Part.read(paths[name]).removeSplitter()
    red=[]; note=""
    for m in mids:
        c2=[k for k,x in enumerate(ref.Edges) if x.distToShape(Part.Vertex(m))[0]<1e-6]
        if not c2: note="noedge"; break
        if c2[0] not in red: red.append(c2[0])
    if note: out.append("ref:"+note)
    else:
        try: out.append("ref:"+stat(ref.makeFillet(r,[ref.Edges[k] for k in red]))+("" if len(red)==len(eis) else "(%d edges)"%len(red)))
        except Exception: out.append("ref:EXC")
    w("T",name,c," ".join(out))
w("DONE")
