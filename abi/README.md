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
| `BRep_CurveRepresentation`, `BRep_PointRepresentation` and the 14 classes derived from them, 8 larger each | | `15bcce7c88`, then `a23e0824af` for MSVC as well |

Now: no symbol missing (the fork adds 217), no record differing, on
macOS. The libraries of the development environment that import OCCT
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

`symbols.py` lists, for each toolkit, what upstream's library exports and
the fork's does not (`missing.txt`), and for each user binary named the
OCCT symbols it imports that the fork lacks. `layouts.py` compiles the
headers the fork changed since `BASE` (default `b8f597c677`) once with
each include directory, with clang's `-fdump-record-layouts`, and reports
each record whose size differs or where a member of upstream's is not
where it was (`BREAK`), and each member the fork added without that
(`fits`). Both exit 1 on a finding.

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
type is the representation's, so nothing else needs to know. Where the
state is one bit about an object the library makes itself, this moves
nothing on any compiler.

The checks here run with clang. What MSVC lays out differently is a
base's unused bytes, as above: the flags in the unused bytes of
`TopTools_ShapeSet` and `BRepTools_ShapeSet` are in the class's own, after
its own last member, and are there with MSVC too.

## After a change here

A change to an installed header's class is a change to everything
compiled against it: FreeCAD is built again after the fork is installed
(`Part`'s shape writer derives from `BRepTools_ShapeSet`), and so is any
package built against the fork's headers.
