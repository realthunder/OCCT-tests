# The fork against upstream's ABI

The fork's libraries stand in for upstream OCCT 8.0.1's: a library built
against upstream's -- conda-forge's ifcopenshell, a mesher, a Python
binding -- is loaded beside FreeCAD and finds the fork's `libTK*` under
upstream's names. It works only while the fork keeps what such a client
was compiled against:

- every symbol upstream exports (`symbols.py`), and
- the size of every class of an installed header, and the place of each
  of upstream's members in it (`layouts.py`).

The second is the one that bites, and no symbol shows it. A client holds
objects of OCCT's classes itself, on its stack or in its own classes, at
the size upstream's header gave them, and reads members through
upstream's inline functions. A member the fork adds makes the library's
constructor write past the client's object, or moves what the inline
function reads.

## What was found (2026-10-13)

`ifcopenshell.geom.serialise` and `tesselate` -- what FreeCAD's IFC
export calls -- crashed with the fork's libraries and ran with upstream's
(`ifc_serialise.py`). ifcopenshell holds a `BRepTools_ShapeSet` on its
stack, 528 bytes with upstream's header; the fork's constructor wrote 704.

Upstream at `b8f597c677` (8.0.1), built with the fork's flags, against
the fork:

| | found | fixed in |
|---|---|---|
| symbols | 3 of upstream's 77673 missing, each a function that had gained parameters: `ChFi3d_Builder::PerformOneCorner(int, bool)`, `BRepOffset_Tool::ExtentFace` with six, `BRepOffset_MakeOffset::ToContext` with one | `4988e007e1` -- upstream's signatures back as overloads that forward |
| `BRepTools_ShapeSet` 528 -> 704, `BinTools_ShapeSet` 528 -> 608, `TopTools_ShapeSet` (every member 8 on), `GeomTools_Curve2dSet` 56 -> 144 | the crash above | `e38b0e262d` |
| `ChFiDS_FilSpine` 1168 -> 1296 | | `c602dc457e` |
| `BRepAlgo_Loop` 512 -> 624, one map changed for another kind | | `d929c938a9` |
| `BRep_CurveRepresentation`, `BRep_PointRepresentation` and the 14 classes derived from them, 8 larger each | | `15bcce7c88`, then `a23e0824af` for MSVC as well; the query is `BRep_Builder_IsCache`, a C function (`102e86e44e`) |

Now: no symbol missing (the fork adds 217), no record differing, on
macOS (clang, libc++). On Linux (gcc 16, libstdc++; 2026-10-13, the same
commits): upstream exports 83784 there, none strong missing and one weak,
a piece of `std::sort` instantiated for a comparison; no record
differing, where the headers before these fixes give the same eight
breaks at libstdc++'s sizes (`BRepTools_ShapeSet` 528 -> 760). The libraries of the development environment that import OCCT
(SMESH's, netgen's, ifcopenshell's) lack none of the symbols they import.

## The checks

An upstream build first, of the commit the fork stands on, configured as
the fork's tree is (the FreeCAD repository's `docs/DevEnvironment.md` has
the command) into a directory of its own; debug information is not
needed (`-DCMAKE_CXX_FLAGS_RELWITHDEBINFO="-O2 -DNDEBUG"`), and it takes
310 MB and 50 minutes on four cores. Take the sources with `git archive
b8f597c677 | tar -x -C <dir>`. With libc++ upstream needs the two
`#include <mutex>` of the fork's `d58f0d2fa5` to compile.

```
./symbols.py <upstream build>/mac64/clang/libi <fork install>/lib [user binary ...]
CXX=clang++ ./layouts.py <upstream build>/include/opencascade <fork build>/include/opencascade
python ifc_serialise.py <any .brep>      # the fork's lib dir on DYLD_LIBRARY_PATH
```

`layouts.py` needs a clang that knows `-fdump-record-layouts-complete`
(the conda environment's; Apple's clang 12 does not). `iscache.cpp`,
`stable_add.cpp` and `thaw.cpp` are small programs against the fork's
library, each with its compile line at its head; they print `ok` or what
failed.

`symbols.py` lists, for each toolkit, what upstream's library exports and
the fork's does not (`missing.txt`), and for each user binary named the
OCCT symbols it imports that the fork lacks. `layouts.py` compiles the
headers the fork changed since `BASE` (default `b8f597c677`) once with
each include directory, with clang's `-fdump-record-layouts`, and reports
each record whose size differs or where a member of upstream's is not
where it was (`BREAK`), and each member the fork added without that
(`fits`). Both exit 1 on a finding; `symbols.py` not for a weak symbol
alone, an inline function or a template's instance the client has its
own of.

Neither sees a virtual function added to an upstream class, or put in
another place among its virtual functions, which moves every entry of
the table after it: do not. Neither sees what an inline function of a
header does: a client built against upstream runs upstream's.

## Adding to a class of upstream's

A function with more parameters: add it beside upstream's, do not change
upstream's. Where the new one had default arguments that made a call
ambiguous, it loses them and upstream's signature forwards to it.

A member: first see whether the class ends in unused bytes (`layouts.py`
prints `sizeof` and `dsize` apart in clang's dump; the difference is
free). A flag put there, after upstream's members, moves nothing:
`TopTools_ShapeSet::myCanonicalFlags`, the two flags of
`BRepTools_ShapeSet`.

Anything larger goes behind an allocator. The class has a collection of
NCollection's among upstream's members; the constructor, which is in the
library, gives that collection an allocator of a class derived from
`NCollection_BaseAllocator` that holds the fork's state, and the code
finds it again with `dynamic_cast` on the collection's `Allocator()`:

```cpp
class Curve2dSetState : public NCollection_BaseAllocator { public: ...the state... };

GeomTools_Curve2dSet::GeomTools_Curve2dSet() : myMap(1, new Curve2dSetState) {}

Curve2dSetState* aState = dynamic_cast<Curve2dSetState*>(myMap.Allocator().get());
```

The collection holds the state for as long as the object lives and lets
go of it with itself, whoever compiled the object's destructor -- upstream
leaves most of them inline, so the library is not told when a client's
object dies, and a table kept beside the objects would go stale. An
object the library's constructor did not make (a copy made by a client)
has no state or shares its original's: the code takes a null for "the
option is off". Accessors of such state are functions of the library,
not inline.

The same for what one object has to remember of another. A thawed copy
of a frozen shape's `TopoDS_TShape` knows its original
(`TopoDS_TShape::ThawedFrom`). That was a table beside the TShapes, and
a destructor declared for `TopoDS_TShape` to take a dying copy out of
it. `Thaw()` gives the copy's list of children an allocator that holds
the original instead (`ThawedOriginal` in `TopoDS_TShape.cxx`), putting
the children the copy already has back under it, and `ThawedFrom()`
asks the list's `Allocator()`: no table, no mutex, no destructor
(`a03dfbb393`). `thaw.cpp` does it 300000 times, children added before
the thaw and after: the copy holds its original once while it lives, and
the original's reference count is back where it was when the copies are
gone.

No destructor, and no other member function declared where upstream has
none or has it inline, in a class that classes in headers derive from.
OCCT's headers say `dllexport` to a client too, so with MSVC whatever
makes an object of a derived class that is all in its header -- a wire, a
shell, a solid, a compound -- imports the base's declared destructor by
name: eleven of FreeCAD's modules imported `TopoDS_TShape`'s, and
upstream's `TKBRep.dll` exports none. With the Itanium ABI upstream's
library has that symbol anyway, with the virtual table, so `symbols.py`
on Linux or macOS does not see this; only a build with MSVC does.

`BRep_CurveRepresentation` and `BRep_PointRepresentation` have no
collection and no unused bytes of their own, and what the fork wanted of
them was one flag: this representation is a cache, given to a frozen edge
or vertex after it was frozen. A flag declared before upstream's members
lands in the four bytes their base, `Standard_Transient`, ends with
unused -- with the Itanium C++ ABI (Linux, macOS); MSVC does not give a
base's unused bytes to a derived class. So there is no flag: a cache is
of a class of its own, the representation's class and a mark beside it
(`Cache<BRep_CurveOnSurface>` in `BRep_Builder.cxx`), made where the
representation is made and asked for with `dynamic_cast`. Its dynamic
type is the representation's, so nothing else needs to know;
`BRep_Builder_IsCache`, a C function, answers for a caller outside
(`iscache.cpp` is the smallest use: a frozen edge given a pcurve on a new
surface). Where the state is one bit about an object the library makes
itself, this moves nothing on any compiler.

The checks here run with clang. What MSVC lays out differently is a
base's unused bytes, as above: the flags in the unused bytes of
`TopTools_ShapeSet` and `BRepTools_ShapeSet` are in the class's own, after
its own last member, and are there with MSVC too.

## The other direction: a client of the fork with upstream's library

FreeCAD is built against the fork and should still load where the
libraries are upstream's. A function of the fork it calls by its C++
name is a symbol upstream's library does not have: the loader refuses
the whole library. So what FreeCAD needs of the fork is a C function,
declared `extern "C" Standard_EXPORT` beside the class it belongs to,
and FreeCAD looks it up by name at run time (`dlsym`, `GetProcAddress`;
`Part::lookUpTKFillet`, `Part::lookUpTKBRep`) and does without where it
is not there: `ChFi3d_SetPlateG0FallbackRatio`, `BRepFilletAPI_SetSetback`,
`BRep_Builder_IsCache`. Not a static member function, which is as much a
C++ symbol as any.

`symbols.py`, given FreeCAD's libraries for users, counts what each
imports that only the fork exports (`fork_only.txt`). On 2026-10-13
there were 7, in `Part.so`, `PartGui.so` and `Import.so`. Six have a
C function now (`fece1a32c7`): four of `STEPCAFControl_Reader` for the
streamed STEP read, `BinTools_ShapeSet_SetOmitPCurvesOnPlane` and
`GeomTools_Curve2dSet_SetMerging`. The seventh, the fork's own
`BRepTools_ShapeSet::Add`, is gone: `AddGeometry` names the shape's own
geometry for `SetStableBytes`, and a client calls upstream's `Add`
(`stable_add.cpp` writes a box and one face of it both ways, the same
bytes). FreeCAD's modules import none now.

Five more families, of FreeCAD's line that freezes shapes (branches
Transaction, LinkVibe and SolidBody; OcctFix calls none of them), have
their C functions since `a03dfbb393`: `TopoDS_TShape_ThawedFrom` (the
original in an argument), `TopoDS_LockedShape_Raised`,
`BRep_RepresentationLock_Acquire` and `BRep_RepresentationLock_Release`
(the lock as a pointer to give back), `BinTools_ShapeSet_SetStableBytes`
and `BRepTools_ShapeSet_AddOwnSurfaces`. The members and the lock class
stay for the library's own use. That commit was made and measured with
MSVC, on the Windows box -- the fork's layouts and virtual tables
upstream's, none of conda-forge's 50073 exported symbols missing,
FreeCAD's modules importing nothing only the fork has, FreeCADCmd running
on upstream's DLLs -- and built here with clang afterwards: `layouts.py`
42 headers, 2762 records, none differing; `symbols.py` none of upstream's
77673 missing, 225 added (219 before: the six names); `thaw.cpp` finds
the six by name.

An inline function of a header is the third way in, and the one no list
of FreeCAD's calls shows: it is compiled into the client, and a function
of the fork's it calls by name is the client's import, whether or not the
client ever gets there. `TopoDS_LockedShape`'s constructor was one. It
counted the refusals (`Raised()`, what FreeCAD reads to tell that an
algorithm was refused a frozen input and made an error message of it)
through `raisedCounter()`, exported; and the tolerance setters of
`BRep_TVertex`, `BRep_TEdge` and `BRep_TFace`, inline as upstream's are,
raise one. A client that set a tolerance on a TShape imported the
counter: FreeCAD's `Part_tests_run` did, the last of its binaries to
import anything of the fork's alone.

Since `9671c1f4a2` the count is behind the common allocator.
`NCollection_ForkState`, an abstract class in a header, is what the
fork's TKernel makes `NCollection_BaseAllocator::CommonBaseAllocator()`
of; an inline function asks that function, which upstream's library has
too, for it with `dynamic_cast` -- null with upstream's -- and goes on by
virtual calls, which are no symbols of the client's. It is the rule for a
class's state ("behind an allocator", above) for state that belongs to
no object. Not two bodies for the constructor, one counting in the
library and one not in a client: which copy of an inline function runs
is the loader's to say wherever the copies are shared, and a count that
held in one build would be lost in another. Here every copy does the
same, and the library answers.

So: an inline function of a header the fork changes calls nothing the
fork exports by name. The installed headers were read for it on
2026-10-13, and only the `SHOW_TOPO_SHAPE` debugging macro of
`TopTools.hxx` does. A member upstream has inline and the fork has out
of line is another matter and still an import of the client that calls
it (`BRepAlgo_Loop::CutEdges`, `BinTools_ShapeSet::IsOmitPCurvesOnPlane`
and `IsStableBytes`); FreeCAD calls none.

Measured with MSVC on the Windows box: `TopoDS_LockedShape` and
`NCollection_BaseAllocator` laid out as upstream's, none of conda-forge's
50073 exported symbols missing, no binary of FreeCAD's -- the test
binaries with them, 34 that import OCCT -- importing a symbol only the
fork exports, and FreeCAD's test of it
(`ImmutableShapeTest.aRefusalRaisedByAnInlineSetterIsCounted`: a refusal
raised by the test binary's own copy of the setter and one raised inside
the library both counted, a write that changes nothing not, another
thread's count its own) passing on the fork's DLLs and skipped on
upstream's, where the binary now loads. Not yet run with clang or gcc:
whether `dynamic_cast` finds the class across libraries there is the
thing to see.

What this does not make of a FreeCAD built against the fork is one that
behaves with upstream's library as one built against upstream would: it
still runs the fork's inline functions (a flag written where upstream
has unused bytes, a bit of a shape's state upstream ignores). It loads,
and what it asks of the fork it does without.

## After a change here

A change to an installed header's class is a change to everything
compiled against it: FreeCAD is built again after the fork is installed
(`Part`'s shape writer derives from `BRepTools_ShapeSet`), and so is any
package built against the fork's headers.
