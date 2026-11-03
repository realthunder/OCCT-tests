// bspline_knots_gprop: the area and volume integrals (BRepGProp, without a
// precision) of shapes on an ellipse's exact rational B-spline, a curve of
// C0 or C1 knots. See ../README.md, "A B-spline integrated across its
// knots".
//
// A Gauss rule over a range a knot cuts converges only algebraically; over
// each span alone, as fast as over a smooth curve. Held against closed
// forms (L the ellipse's length, GCPnts_AbscissaPoint on the Geom_Ellipse):
//   a prism on the B-spline ellipse a x b, height 8: area 2 pi a b + 8 L,
//     volume 8 pi a b; the same made periodic;
//   a plate 30 x 20 x 8 with the ellipse 10 x 5 cut through it (its edge
//     reversed on the plate's faces): area 2 (600 - 50 pi) + 8 (100 + L),
//     volume 8 (600 - 50 pi);
//   a spheroid, half the B-spline ellipse revolved about its axis, a across
//     and c along it: area and volume as in extrusion_area_gprop.cpp. Its
//     seam runs pi in the curve's parameter, its knot at the middle: the
//     sample the crossing was looked for at landed on it, and the knot was
//     missed.
// Before the fix: the 10 x 2 prism 1.2e-3 off in area (its caps, the edge
// integral 18 points across the whole curve), the volumes 1.4e-3; the
// oblate spheroid 6.9e-6 in area.
//
// Build (macOS, OCCT install prefix O):
//   clang++ -std=c++17 -w -I$O/include/opencascade bspline_knots_gprop.cpp \
//     -L$O/lib -Wl,-rpath,$O/lib -lTKPrim -lTKTopAlgo -lTKBRep \
//     -lTKGeomAlgo -lTKGeomBase -lTKG3d -lTKG2d -lTKMath -lTKernel -o bspline_knots_gprop
// Run: ./bspline_knots_gprop [--write <dir>]
//   (exit 0 when every integral agrees to 1e-9)
//   --write: <dir>/<name>.brep, the solid of each case
#include <BRepBuilderAPI_MakeEdge.hxx>
#include <BRepBuilderAPI_MakeFace.hxx>
#include <BRepBuilderAPI_MakePolygon.hxx>
#include <BRepBuilderAPI_MakeWire.hxx>
#include <BRepGProp.hxx>
#include <BRepPrimAPI_MakePrism.hxx>
#include <BRepPrimAPI_MakeRevol.hxx>
#include <BRepTools.hxx>
#include <GCPnts_AbscissaPoint.hxx>
#include <GProp_GProps.hxx>
#include <GeomAdaptor_Curve.hxx>
#include <GeomConvert.hxx>
#include <Geom_BSplineCurve.hxx>
#include <Geom_Ellipse.hxx>
#include <Geom_TrimmedCurve.hxx>
#include <TopoDS.hxx>
#include <cmath>
#include <cstdio>
#include <cstring>
#include <string>

static bool check(const char*         theName,
                  const TopoDS_Shape& theSolid,
                  const double        theVolRef,
                  const double        theAreaRef,
                  const std::string&  theDir)
{
  GProp_GProps aV, aS;
  BRepGProp::VolumeProperties(theSolid, aV);
  BRepGProp::SurfaceProperties(theSolid, aS);
  const double aVErr = std::abs(std::abs(aV.Mass()) - theVolRef) / theVolRef;
  const double aSErr = std::abs(aS.Mass() - theAreaRef) / theAreaRef;
  const bool   isOk  = aVErr < 1.e-9 && aSErr < 1.e-9;
  printf("%s: area %.6f (want %.6f, off %.2g), volume %.6f (want %.6f, off %.2g): %s\n",
         theName,
         aS.Mass(),
         theAreaRef,
         aSErr,
         std::abs(aV.Mass()),
         theVolRef,
         aVErr,
         isOk ? "PASS" : "FAIL");
  if (!theDir.empty())
  {
    BRepTools::Write(theSolid, (theDir + "/" + theName + ".brep").c_str());
  }
  return isOk;
}

static double ellipseLength(const double a, const double b)
{
  GeomAdaptor_Curve aC(new Geom_Ellipse(gp_Ax2(gp_Pnt(0, 0, 0), gp::DZ()), a, b));
  return GCPnts_AbscissaPoint::Length(aC, 1.e-12);
}

// the ellipse a x b about the origin in the xy plane, as GeomConvert's rational B-spline
static occ::handle<Geom_BSplineCurve> bsplineEllipse(const double a, const double b)
{
  return GeomConvert::CurveToBSplineCurve(
    new Geom_Ellipse(gp_Ax2(gp_Pnt(0, 0, 0), gp::DZ()), a, b));
}

int main(int argc, char** argv)
{
  const std::string aDir = argc > 2 && !strcmp(argv[1], "--write") ? argv[2] : "";
  const double      aH   = 8.;
  bool              isOk = true;
  char              aName[64];
  const double      aPrisms[][3] = {{10., 5., 0.}, {10., 2., 0.}, {10., 1., 0.}, {10., 2., 1.}};
  for (const auto& aCase : aPrisms)
  {
    const double                   a = aCase[0], b = aCase[1];
    occ::handle<Geom_BSplineCurve> aCurve = bsplineEllipse(a, b);
    if (aCase[2] != 0.)
    {
      aCurve->SetPeriodic();
    }
    const TopoDS_Face aBase =
      BRepBuilderAPI_MakeFace(BRepBuilderAPI_MakeWire(BRepBuilderAPI_MakeEdge(aCurve).Edge()).Wire())
        .Face();
    const TopoDS_Shape aPrism = BRepPrimAPI_MakePrism(aBase, gp_Vec(0, 0, aH)).Shape();
    snprintf(aName, sizeof(aName), "prism_%gx%g%s", a, b, aCase[2] != 0. ? "_periodic" : "");
    isOk = check(aName,
                 aPrism,
                 aH * M_PI * a * b,
                 2. * M_PI * a * b + aH * ellipseLength(a, b),
                 aDir)
           && isOk;
  }
  // a plate with the ellipse cut through it: the B-spline edge reversed on its faces
  {
    BRepBuilderAPI_MakePolygon aRect(gp_Pnt(-15, -10, 0),
                                     gp_Pnt(15, -10, 0),
                                     gp_Pnt(15, 10, 0),
                                     gp_Pnt(-15, 10, 0),
                                     true);
    BRepBuilderAPI_MakeFace    aMaker(aRect.Wire(), true);
    const TopoDS_Wire          aHole =
      BRepBuilderAPI_MakeWire(BRepBuilderAPI_MakeEdge(bsplineEllipse(10., 5.)).Edge()).Wire();
    aMaker.Add(TopoDS::Wire(aHole.Reversed()));
    const TopoDS_Shape aPlate = BRepPrimAPI_MakePrism(aMaker.Face(), gp_Vec(0, 0, aH)).Shape();
    const double       aCap   = 600. - 50. * M_PI;
    isOk =
      check("plate_hole_10x5", aPlate, aH * aCap, 2. * aCap + aH * (100. + ellipseLength(10., 5.)), aDir)
      && isOk;
  }
  // spheroids: a across the axis, c along it, half the ellipse's B-spline
  const double aSpheroids[][2] = {{10., 2.}, {2., 10.}};
  for (const auto& aCase : aSpheroids)
  {
    const double a = aCase[0], c = aCase[1];
    // the half at x >= 0 in the xz plane, its axis along z
    occ::handle<Geom_Ellipse> anEll =
      a > c ? new Geom_Ellipse(gp_Ax2(gp_Pnt(0, 0, 0), -gp::DY(), gp::DX()), a, c)
            : new Geom_Ellipse(gp_Ax2(gp_Pnt(0, 0, 0), gp::DY(), gp::DZ()), c, a);
    occ::handle<Geom_TrimmedCurve> aHalf =
      a > c ? new Geom_TrimmedCurve(anEll, -M_PI / 2., M_PI / 2.)
            : new Geom_TrimmedCurve(anEll, 0., M_PI);
    occ::handle<Geom_BSplineCurve> aCurve = GeomConvert::CurveToBSplineCurve(aHalf);
    const gp_Pnt                   aP1 = aCurve->StartPoint(), aP2 = aCurve->EndPoint();
    const TopoDS_Wire              aWire =
      BRepBuilderAPI_MakeWire(BRepBuilderAPI_MakeEdge(aCurve).Edge(),
                              BRepBuilderAPI_MakeEdge(aP2, aP1).Edge())
        .Wire();
    const TopoDS_Face  aFace  = BRepBuilderAPI_MakeFace(aWire, true).Face();
    const TopoDS_Shape aSolid = BRepPrimAPI_MakeRevol(aFace, gp::OZ()).Shape();
    double             anArea;
    if (a > c)
    {
      const double e = std::sqrt(1. - c * c / (a * a));
      anArea         = 2. * M_PI * a * a + M_PI * c * c / e * std::log((1. + e) / (1. - e));
    }
    else
    {
      const double e = std::sqrt(1. - a * a / (c * c));
      anArea         = 2. * M_PI * a * a * (1. + c / (a * e) * std::asin(e));
    }
    snprintf(aName, sizeof(aName), "spheroid_%gx%g", a, c);
    isOk = check(aName, aSolid, 4. / 3. * M_PI * a * a * c, anArea, aDir) && isOk;
  }
  return isOk ? 0 : 1;
}
