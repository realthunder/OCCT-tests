// adaptive_gprop: the area and volume integrals of BRepGProp given a
// precision (the adaptive ones, eps 1e-6) on extrusions and revolutions.
// See ../README.md, "The adaptive integral refined along the edges only".
//
// The adaptive integral refines its rule along the face's edges; across
// u it took one rule over the surface's spans, never refined -- an
// extrusion's or a revolution's whole range, whatever its curve. Held
// against closed forms and what does not come from the integrals:
//   a prism on an ellipse a x b, height 8: area 2 pi a b + 8 L (L the
//     ellipse's length, GCPnts_AbscissaPoint), volume 8 pi a b;
//   the same on the ellipse made a B-spline (GeomConvert: rational, three
//     spans), 10 x 2;
//   a spheroid, half an ellipse revolved about its axis, a across and c
//     along the axis (the closed forms of extrusion_area_gprop.cpp);
//   #617's prisms (issue617_prisms.brep, degree 8 B-splines of 29 spans,
//     extruded 100): the caps' area by the shoelace over 400001 points of
//     their curves, their length by GCPnts_AbscissaPoint.
// Before the fix: the prisms on the ellipse 0.2% to 11% short in area,
// 2.1e-5 over in volume, the B-spline one 6% over, #617's prisms 80% short
// in volume (14258 for 71191) -- each with an error of 2e-9 or less
// reported. The spheroids were right (a revolution's u is the turn about
// the axis, its rule exact).
//
// Build (macOS, OCCT install prefix O):
//   clang++ -std=c++17 -w -I$O/include/opencascade adaptive_gprop.cpp \
//     -L$O/lib -Wl,-rpath,$O/lib -lTKPrim -lTKTopAlgo -lTKBRep \
//     -lTKGeomAlgo -lTKGeomBase -lTKG3d -lTKG2d -lTKMath -lTKernel -o adaptive_gprop
// Run: ./adaptive_gprop issue617_prisms.brep [--write <dir>]
//   (exit 0 when every integral agrees to 1e-7, a tenth of the precision asked)
//   --write: <dir>/<name>.brep, the solid of each case
#include <BRepAdaptor_Curve.hxx>
#include <BRepBuilderAPI_MakeEdge.hxx>
#include <BRepBuilderAPI_MakeFace.hxx>
#include <BRepBuilderAPI_MakeWire.hxx>
#include <BRepGProp.hxx>
#include <BRepPrimAPI_MakePrism.hxx>
#include <BRepPrimAPI_MakeRevol.hxx>
#include <BRepTools.hxx>
#include <BRep_Builder.hxx>
#include <GCPnts_AbscissaPoint.hxx>
#include <GProp_GProps.hxx>
#include <GeomAdaptor_Curve.hxx>
#include <GeomConvert.hxx>
#include <Geom_BSplineCurve.hxx>
#include <Geom_Ellipse.hxx>
#include <Geom_TrimmedCurve.hxx>
#include <TopExp.hxx>
#include <TopExp_Explorer.hxx>
#include <TopTools_IndexedMapOfShape.hxx>
#include <TopoDS.hxx>
#include <cmath>
#include <cstdio>
#include <cstring>
#include <string>

static const double EPS = 1.e-6;

static bool check(const char*         theName,
                  const TopoDS_Shape& theSolid,
                  const double        theVolRef,
                  const double        theAreaRef,
                  const double        theTol,
                  const std::string&  theDir)
{
  GProp_GProps aV, aS;
  const double aVEps = BRepGProp::VolumeProperties(theSolid, aV, EPS);
  const double aSEps = BRepGProp::SurfaceProperties(theSolid, aS, EPS);
  const double aVErr = std::abs(aV.Mass() - theVolRef) / theVolRef;
  const double aSErr = std::abs(aS.Mass() - theAreaRef) / theAreaRef;
  const bool   isOk  = aVErr < theTol && aSErr < theTol;
  printf("%s: area %.6f (want %.6f, off %.2g, error given %.2g), volume %.6f (want %.6f, off "
         "%.2g, error given %.2g): %s\n",
         theName,
         aS.Mass(),
         theAreaRef,
         aSErr,
         aSEps,
         aV.Mass(),
         theVolRef,
         aVErr,
         aVEps,
         isOk ? "PASS" : "FAIL");
  if (!theDir.empty())
  {
    BRepTools::Write(theSolid, (theDir + "/" + theName + ".brep").c_str());
  }
  return isOk;
}

static TopoDS_Shape prism(const occ::handle<Geom_Curve>& theC, const double theH)
{
  const TopoDS_Edge anEdge = BRepBuilderAPI_MakeEdge(theC).Edge();
  const TopoDS_Face aBase = BRepBuilderAPI_MakeFace(BRepBuilderAPI_MakeWire(anEdge).Wire()).Face();
  return BRepPrimAPI_MakePrism(aBase, gp_Vec(0, 0, theH)).Shape();
}

int main(int argc, char** argv)
{
  if (argc < 2)
  {
    printf("usage: %s issue617_prisms.brep [--write <dir>]\n", argv[0]);
    return 2;
  }
  const std::string aDir = argc > 3 && !strcmp(argv[2], "--write") ? argv[3] : "";
  const double      aH   = 8.;
  bool              isOk = true;
  const double      aPrisms[][2] = {{10., 5.}, {10., 2.}, {6., 5.}, {10., 1.}, {30., 1.}};
  for (const auto& aCase : aPrisms)
  {
    const double a = aCase[0], b = aCase[1];
    occ::handle<Geom_Ellipse> anEll = new Geom_Ellipse(gp_Ax2(gp_Pnt(0, 0, 0), gp::DZ()), a, b);
    GeomAdaptor_Curve         aC(anEll);
    const double              aL = GCPnts_AbscissaPoint::Length(aC, 1.e-12);
    char                      aName[64];
    snprintf(aName, sizeof(aName), "prism_%gx%g", a, b);
    isOk = check(aName,
                 prism(anEll, aH),
                 aH * M_PI * a * b,
                 2. * M_PI * a * b + aH * aL,
                 1.e-7,
                 aDir)
           && isOk;
  }
  {
    occ::handle<Geom_Ellipse> anEll = new Geom_Ellipse(gp_Ax2(gp_Pnt(0, 0, 0), gp::DZ()), 10., 2.);
    occ::handle<Geom_BSplineCurve> aBS = GeomConvert::CurveToBSplineCurve(anEll);
    GeomAdaptor_Curve              aC(anEll);
    const double                   aL = GCPnts_AbscissaPoint::Length(aC, 1.e-12);
    isOk = check("bspline_prism_10x2",
                 prism(aBS, aH),
                 aH * M_PI * 20.,
                 2. * M_PI * 20. + aH * aL,
                 1.e-7,
                 aDir)
           && isOk;
  }
  // spheroids: a across the axis, c along it
  const double aSpheroids[][2] = {{10., 2.}, {10., 5.}, {2., 10.}, {5., 10.}};
  for (const auto& aCase : aSpheroids)
  {
    const double a = aCase[0], c = aCase[1];
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
    isOk = check(aName, aSolid, 4. / 3. * M_PI * a * a * c, anArea, 1.e-7, aDir) && isOk;
  }
  // #617's prisms: their caps' curves at z = 0, the prisms 100 high
  BRep_Builder aBB;
  TopoDS_Shape aPrisms617;
  if (!BRepTools::Read(aPrisms617, argv[1], aBB))
  {
    printf("cannot read %s\n", argv[1]);
    return 2;
  }
  double aVolRef = 0., anAreaRef = 0.;
  TopTools_IndexedMapOfShape anEdges;
  TopExp::MapShapes(aPrisms617, TopAbs_EDGE, anEdges);
  for (int k = 1; k <= anEdges.Extent(); ++k)
  {
    BRepAdaptor_Curve aC(TopoDS::Edge(anEdges(k)));
    const double      aT0 = aC.FirstParameter(), aT1 = aC.LastParameter();
    if (aC.GetType() != GeomAbs_BSplineCurve
        || std::abs(aC.Value(0.5 * (aT0 + aT1)).Z()) > 1.e-7)
    {
      continue;
    }
    const int aN    = 400000;
    double    aShoe = 0.;
    gp_Pnt    aP0 = aC.Value(aT0), aPrev = aP0;
    for (int i = 1; i <= aN; ++i)
    {
      const gp_Pnt aP = i == aN ? aP0 : aC.Value(aT0 + (aT1 - aT0) * i / aN);
      aShoe += aPrev.X() * aP.Y() - aP.X() * aPrev.Y();
      aPrev = aP;
    }
    const double aLobe = 0.5 * std::abs(aShoe);
    aVolRef += aLobe * 100.;
    anAreaRef += 2. * aLobe + GCPnts_AbscissaPoint::Length(aC, 1.e-10) * 100.;
  }
  isOk = check("issue617_prisms", aPrisms617, aVolRef, anAreaRef, 1.e-7, aDir) && isOk;
  return isOk ? 0 : 1;
}
