// extrusion_area_gprop: the area and volume integrals (BRepGProp, without a
// precision) of an extrusion and a revolution of an ellipse. See
// ../README.md, "An ellipse's extrusion: its area integrated at 18 points".
//
// The area element of an extrusion or a revolution of a curve carries the
// curve's speed under a square root. Held against closed forms:
//   a prism on an ellipse a x b, height 8: area 2 pi a b + 8 L (L the
//     ellipse's length, GCPnts_AbscissaPoint), volume 8 pi a b;
//   a spheroid, half an ellipse revolved about its axis, a across and c
//     along the axis: area 2 pi a^2 + pi c^2 / e ln((1 + e) / (1 - e)),
//     e^2 = 1 - c^2 / a^2 (oblate, a > c), or 2 pi a^2 (1 + c / (a e)
//     asin e), e^2 = 1 - a^2 / c^2 (prolate); volume 4/3 pi a^2 c.
// Before the fix: 1.8e-5 short on the 10 x 5 prism, 0.45% on 30 x 1.
//
// Build (macOS, OCCT install prefix O):
//   clang++ -std=c++17 -w -I$O/include/opencascade extrusion_area_gprop.cpp \
//     -L$O/lib -Wl,-rpath,$O/lib -lTKPrim -lTKTopAlgo -lTKBRep \
//     -lTKGeomAlgo -lTKGeomBase -lTKG3d -lTKG2d -lTKMath -lTKernel -o extrusion_area_gprop
// Run: ./extrusion_area_gprop [--write <dir>]
//   (exit 0 when every integral agrees to 1e-9)
//   --write: <dir>/<name>.brep, the solid of each case
#include <BRepBuilderAPI_MakeEdge.hxx>
#include <BRepBuilderAPI_MakeFace.hxx>
#include <BRepBuilderAPI_MakeWire.hxx>
#include <BRepGProp.hxx>
#include <BRepPrimAPI_MakePrism.hxx>
#include <BRepPrimAPI_MakeRevol.hxx>
#include <BRepTools.hxx>
#include <GCPnts_AbscissaPoint.hxx>
#include <GProp_GProps.hxx>
#include <GeomAdaptor_Curve.hxx>
#include <Geom_Ellipse.hxx>
#include <Geom_TrimmedCurve.hxx>
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
  const double aVErr = std::abs(aV.Mass() - theVolRef) / theVolRef;
  const double aSErr = std::abs(aS.Mass() - theAreaRef) / theAreaRef;
  const bool   isOk  = aVErr < 1.e-9 && aSErr < 1.e-9;
  printf("%s: area %.6f (want %.6f, off %.2g), volume %.6f (want %.6f, off %.2g): %s\n",
         theName,
         aS.Mass(),
         theAreaRef,
         aSErr,
         aV.Mass(),
         theVolRef,
         aVErr,
         isOk ? "PASS" : "FAIL");
  if (!theDir.empty())
  {
    BRepTools::Write(theSolid, (theDir + "/" + theName + ".brep").c_str());
  }
  return isOk;
}

int main(int argc, char** argv)
{
  const std::string aDir = argc > 2 && !strcmp(argv[1], "--write") ? argv[2] : "";
  const double      aH   = 8.;
  bool              isOk = true;
  const double aPrisms[][2] = {{10., 5.}, {10., 2.}, {6., 5.}, {10., 1.}, {30., 1.}};
  for (const auto& aCase : aPrisms)
  {
    const double a = aCase[0], b = aCase[1];
    occ::handle<Geom_Ellipse> anEll = new Geom_Ellipse(gp_Ax2(gp_Pnt(0, 0, 0), gp::DZ()), a, b);
    const TopoDS_Edge  anEdge = BRepBuilderAPI_MakeEdge(anEll).Edge();
    const TopoDS_Face  aBase  = BRepBuilderAPI_MakeFace(BRepBuilderAPI_MakeWire(anEdge).Wire()).Face();
    const TopoDS_Shape aPrism = BRepPrimAPI_MakePrism(aBase, gp_Vec(0, 0, aH)).Shape();
    GeomAdaptor_Curve  aC(anEll);
    const double       aL = GCPnts_AbscissaPoint::Length(aC, 1.e-12);
    char               aName[64];
    snprintf(aName, sizeof(aName), "prism_%gx%g", a, b);
    isOk = check(aName, aPrism, aH * M_PI * a * b, 2. * M_PI * a * b + aH * aL, aDir) && isOk;
  }
  // spheroids: a across the axis, c along it
  const double aSpheroids[][2] = {{10., 2.}, {10., 5.}, {2., 10.}, {5., 10.}};
  for (const auto& aCase : aSpheroids)
  {
    const double a = aCase[0], c = aCase[1];
    // half the ellipse in the xz plane, x >= 0: its major axis along x
    // (oblate) or along z (prolate), the minor one with the other
    occ::handle<Geom_TrimmedCurve> aHalf =
      a > c ? new Geom_TrimmedCurve(
                new Geom_Ellipse(gp_Ax2(gp_Pnt(0, 0, 0), -gp::DY(), gp::DX()), a, c),
                -M_PI / 2.,
                M_PI / 2.)
            : new Geom_TrimmedCurve(
                new Geom_Ellipse(gp_Ax2(gp_Pnt(0, 0, 0), gp::DY(), gp::DZ()), c, a),
                0.,
                M_PI);
    const gp_Pnt       aP1 = aHalf->StartPoint(), aP2 = aHalf->EndPoint();
    const TopoDS_Wire  aWire = BRepBuilderAPI_MakeWire(BRepBuilderAPI_MakeEdge(aHalf).Edge(),
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
    char aName[64];
    snprintf(aName, sizeof(aName), "spheroid_%gx%g", a, c);
    isOk = check(aName, aSolid, 4. / 3. * M_PI * a * a * c, anArea, aDir) && isOk;
  }
  return isOk ? 0 : 1;
}
