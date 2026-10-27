# Surface checks

Checks of the surfaces built through curve networks (`GeomFill_Gordon`,
`GeomFill_NetworkSurface`), which FreeCAD's Surface workbench builds on
(FreeCAD's `docs/Surface.md`). A C++ driver each, built against an
install, as `../math/`'s are.

`network_degree.cpp` -- a network of polynomial curves gives a polynomial
surface of their degree, through `GeomFill_NetworkSurface` and through
`GeomFill_Gordon`; a network of rational arcs keeps its rational surface.
Build and run as its header says; it exits 1 on a failure.

## A polynomial network came back rational, and of degree 9

FreeCAD's survey for the Surface workbench (`docs/Surface.md` sec 3.4,
`scripts/occt-gordon-probe.cpp`) measured `GeomFill_Gordon` on networks of
cubic B-splines, all weights 1:

- 5 x 4 curves crossing at uneven parameters: degree 9, 217 x 212 poles,
  flagged rational;
- 12 x 12 curves: degree 9, 2004 x 2004 poles, 14 to 20 s.

It was taken for the price of an exact reparametrization. It was not:
`GeomFill_NetworkSurface` alone does the same to a network that is already
compatible -- 4 x 5 cubics sharing their knots came back degree 9, 45 x 59
poles, interior knots of multiplicity 7.

The network surface is a profile skin plus a guide skin minus a reference
surface through the crossings. A rational one goes through the exact product
of the three denominators, which makes the degree 3 x 3. Two things sent a
polynomial network there:

- **The reference surface.** It was taken as polynomial when
  `hasRationalCurve(profiles) != hasRationalCurve(guides)` -- false when
  neither family has a rational curve. A network with no rational curve at
  all had its reference surface interpolated in homogeneous form.
- **Weights of 1 that came back 1 only to rounding.** The skins, and that
  reference surface, interpolate the weights with the poles
  (`BSplCLib::Interpolate`, `BSplSLib::Interpolate` with weights). For a
  polynomial family the weights are all 1, and they came back as
  0.9999999999999998 and the like. `Geom_BSplineSurface` compares weights at
  `Epsilon` of the weight, so the surface was rational.

The fix (occt 09c2509936, `GeomFill_NetworkSurface.cxx`, internal
functions only, no ABI change):

- the reference surface is polynomial unless both families are rational;
- a family whose weights are all 1 is interpolated without them, with
  `BSplCLib::Interpolate` and `BSplSLib::Interpolate` without weights, so
  they stay exactly 1.

| Network | Before | After |
|---|---|---|
| NetworkSurface, wave 4 x 5, compatible cubics | degree 9, rational, 45 x 59, mult 7 | degree 3, polynomial, 9 x 11, mult 1 |
| Gordon, wave 5 x 4, uneven | degree 9, rational, 217 x 212, mult 9 | degree 3, polynomial, 37 x 38, mult 3 |
| Gordon, wave 12 x 12 (the probe) | degree 9, 2004 x 2004, 14-20 s | degree 3, 306 x 306, 119 ms |
| Gordon, duct of rational arcs | degree 9, rational, 33 x 45 | the same |

Every result is still exact: after the fix the probe measures the input
curves on the surface within 2e-12 wherever it measures (it skips the 12 x
12: 306 x 306 is still over its limit of 40000 poles).

Gordon's exact reparametrization still puts a knot of multiplicity 3 at each
crossing, which leaves the surface C0 inside in its parametrization.
FreeCAD's Surface workbench refits each curve family instead (degree 3, C2,
within a tolerance) and hands `GeomFill_NetworkSurface` a compatible network:
the 12 x 12 network is 67 x 26 poles in 78 ms there.
