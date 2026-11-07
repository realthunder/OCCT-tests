# TKG3d checks

`osculating_threads.cpp` -- one `Geom_OffsetSurface` evaluated by several
threads at once where its normal degenerates. Build and run as its header
says; it exits 0, or crashes.

## An offset surface evaluated by several threads at its pole (2026-11-07)

**What was broken.** FreeCAD segfaulted cutting #346's shells, offset by the
fork (`../thickness/README.md`, sec 56), by their boolean references:
`Geom_OsculatingSurface::UOsculatingSurface`, under `IntCurveSurface` on the
threads of `OSD_ThreadPool` -- a parallel boolean, which FreeCAD's Part
booleans are. Not on every run: the box under load, twice in a row; idle,
none in twenty.

An offset surface whose basis degenerates along a row (a B-spline with a pole
there, as the fork's stretched dome is) evaluates its normal there from
osculating surfaces, kept in `NCollection_Sequence`s. They were fetched with
`Value(i)`, which is const but moves the sequence's own cursor
(`myCurrentItem`, `myCurrentIndex`) and walks from where it was. The threads
of a boolean share the surface and evaluate it at once: their cursors
crossed, one walked from a node another had just moved it off, and read
past the list.

**The fix** (`Geom_OsculatingSurface.cxx`): the surfaces, and the degrees
beside them, are found by walking the sequence with its iterator, which keeps
its own place and leaves the sequence as it is. The same item as before, so
no value changes; the class keeps its layout. `NCollection_Sequence::Value`
itself is left as it is: every loop over a const sequence leans on its cursor.

**The check.** `osculating_threads.cpp` makes a spherical cap a B-spline
(`GeomConvert`), its pole a row of equal poles, offsets it by 1, and has 8
threads evaluate D1 200000 times each, every other time on the pole row.
Before: a segfault on every run (3 of 3; one thread, none). After: none (3
of 3, and 5 of 5 on the fork's own stretched dome from #346). There is no
picture: the shapes are the same, only the process lives.

**Regression** (`51a27b908d`, on Linux): nothing changes. The thickness
corpus (1072 runs) line for line; Part 390, PartDesign 486 and ShapeStorage
63 OK, plain and frozen; thickness PASS=610 at fix levels 0, 1 and 2, plain
and frozen; the thickness sweep right in all 928 runs at all three; fillet
PASS=815 XFAIL=1, draft 104 + 1 FAIL (Linux's standing `new_roof_L_a-30`),
boolean 67 -- every line as it was, fillet and draft frozen too.
