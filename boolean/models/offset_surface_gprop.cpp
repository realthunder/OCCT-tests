// offset_surface_gprop: the volume and area integrals (BRepGProp, without a
// precision) of a solid whose wall is an offset surface. See ../README.md,
// "An offset surface integrated at 18 points".
//
// A prism on an ellipse (semi-axes a, b, height 8), offset by d (+1 and -1)
// with the Intersection join: the wall becomes the offset (Geom_OffsetSurface)
// of the prism's, the caps stay planes, cut by the wall in the offset curve.
// Held against Steiner: the offset ellipse's region has the area
// pi a b + L d + pi d^2 (L the ellipse's length, GCPnts_AbscissaPoint), its
// curve the length L + 2 pi d; the solid is that region times the height
// 8 + 2 d. Before the fix: 0.2% short on the 10 x 5 ellipse.
//
// Build (macOS, OCCT install prefix O):
//   clang++ -std=c++17 -w -I$O/include/opencascade offset_surface_gprop.cpp \
//     -L$O/lib -Wl,-rpath,$O/lib -lTKOffset -lTKPrim -lTKTopAlgo -lTKBRep \
//     -lTKGeomAlgo -lTKGeomBase -lTKG3d -lTKG2d -lTKMath -lTKernel -o offset_surface_gprop
// Run: ./offset_surface_gprop [--write <dir>]
//   (exit 0 when every integral agrees to 1e-7)
//   --write: <dir>/<a>x<b>_<d>.brep, the offset solid of each case
#include <BRepAdaptor_Surface.hxx>
#include <BRepBuilderAPI_MakeEdge.hxx>
#include <BRepBuilderAPI_MakeFace.hxx>
#include <BRepBuilderAPI_MakeWire.hxx>
#include <BRepGProp.hxx>
#include <BRepOffsetAPI_MakeOffsetShape.hxx>
#include <BRepPrimAPI_MakePrism.hxx>
#include <BRepTools.hxx>
#include <GCPnts_AbscissaPoint.hxx>
#include <GProp_GProps.hxx>
#include <GeomAdaptor_Curve.hxx>
#include <Geom_Ellipse.hxx>
#include <TopExp_Explorer.hxx>
#include <TopoDS.hxx>
#include <cmath>
#include <cstdio>
#include <cstring>
#include <string>

int main(int argc, char** argv)
{
  const std::string aDir   = argc > 2 && !strcmp(argv[1], "--write") ? argv[2] : "";
  const double      aH     = 8.;
  const double      aCases[][3] = {{10., 5., 1.},
                                   {10., 5., -1.},
                                   {10., 2., 1.},
                                   {6., 5., 1.},
                                   {10., 1., 1.},
                                   {30., 1., 1.}};
  bool              isOk   = true;
  for (const auto& aCase : aCases)
  {
    const double a = aCase[0], b = aCase[1], d = aCase[2];
    occ::handle<Geom_Ellipse> anEll = new Geom_Ellipse(gp_Ax2(gp_Pnt(0, 0, 0), gp::DZ()), a, b);
    const TopoDS_Edge  anEdge = BRepBuilderAPI_MakeEdge(anEll).Edge();
    const TopoDS_Face  aBase  = BRepBuilderAPI_MakeFace(BRepBuilderAPI_MakeWire(anEdge).Wire()).Face();
    const TopoDS_Shape aPrism = BRepPrimAPI_MakePrism(aBase, gp_Vec(0, 0, aH)).Shape();
    BRepOffsetAPI_MakeOffsetShape anOff;
    anOff.PerformByJoin(aPrism, d, 1.e-7, BRepOffset_Skin, false, false, GeomAbs_Intersection);
    if (!anOff.IsDone())
    {
      printf("%gx%g d %g: the offset failed\n", a, b, d);
      isOk = false;
      continue;
    }
    const TopoDS_Shape& aSolid = anOff.Shape();
    int                 aNbOffset = 0;
    for (TopExp_Explorer anE(aSolid, TopAbs_FACE); anE.More(); anE.Next())
    {
      aNbOffset +=
        BRepAdaptor_Surface(TopoDS::Face(anE.Current())).GetType() == GeomAbs_OffsetSurface;
    }
    GeomAdaptor_Curve aC(anEll);
    const double      aL      = GCPnts_AbscissaPoint::Length(aC, 1.e-12);
    const double      aRegion = M_PI * a * b + aL * d + M_PI * d * d;
    const double      aVolRef = aRegion * (aH + 2. * d);
    const double      anAreaRef = 2. * aRegion + (aL + 2. * M_PI * d) * (aH + 2. * d);
    GProp_GProps      aV, aS;
    BRepGProp::VolumeProperties(aSolid, aV);
    BRepGProp::SurfaceProperties(aSolid, aS);
    const double aVErr = std::abs(aV.Mass() - aVolRef) / aVolRef;
    const double aSErr = std::abs(aS.Mass() - anAreaRef) / anAreaRef;
    const bool   isCase = aNbOffset == 1 && aVErr < 1.e-7 && aSErr < 1.e-7;
    printf("%gx%g d %+g: %d offset wall; volume %.6f (want %.6f, off %.2g), area %.6f (want %.6f, "
           "off %.2g): %s\n",
           a,
           b,
           d,
           aNbOffset,
           aV.Mass(),
           aVolRef,
           aVErr,
           aS.Mass(),
           anAreaRef,
           aSErr,
           isCase ? "PASS" : "FAIL");
    isOk = isOk && isCase;
    if (!aDir.empty())
    {
      char aName[64];
      snprintf(aName, sizeof(aName), "/%gx%g_%g.brep", a, b, d);
      BRepTools::Write(aSolid, (aDir + aName).c_str());
    }
  }
  return isOk ? 0 : 1;
}
