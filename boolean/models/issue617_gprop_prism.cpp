// issue617: the volume and area integrals (BRepGProp, without a precision)
// of two prisms on the cut of #617's revolution -- degree 8 B-splines of 29
// spans, their knots bunched where the cut turns. See ../README.md, "#617:
// a volume integrated a point or two a span".
//
// The revolution's face is cut by the plane z = 0 as FreeCAD's sketch cuts
// it (BRepAlgoAPI_Section, built after Approximation is set), each closed
// cut made a face and extruded 100. The integrals are held against what
// does not come from them: a lobe's area by the shoelace over 400001 points
// of its curve, the curve's length by GCPnts_AbscissaPoint; the prisms'
// volume is the areas times 100, their area the lobes twice and the lengths
// times 100. Before the fix: 92341 for 71191.
//
// Build (macOS, OCCT install prefix O):
//   clang++ -std=c++17 -w -I$O/include/opencascade issue617_gprop_prism.cpp \
//     -L$O/lib -Wl,-rpath,$O/lib -lTKBO -lTKPrim -lTKTopAlgo -lTKBRep -lTKGeomAlgo \
//     -lTKGeomBase -lTKG3d -lTKG2d -lTKMath -lTKernel -o issue617_gprop_prism
// Run: ./issue617_gprop_prism issue617_revolution.brep [--write <dir>]
//   (exit 0 when the integrals agree to 1e-7)
//   --write: <dir>/revolution.brep, prisms.brep and section.brep
#include <BRepAdaptor_Curve.hxx>
#include <BRepAlgoAPI_Section.hxx>
#include <BRepBuilderAPI_MakeFace.hxx>
#include <BRepBuilderAPI_MakeWire.hxx>
#include <BRepGProp.hxx>
#include <BRepPrimAPI_MakePrism.hxx>
#include <BRepTools.hxx>
#include <BRep_Builder.hxx>
#include <GCPnts_AbscissaPoint.hxx>
#include <GProp_GProps.hxx>
#include <TopExp_Explorer.hxx>
#include <TopoDS.hxx>
#include <gp_Pln.hxx>

#include <cmath>
#include <cstdio>
#include <cstring>
#include <string>

int main(int argc, char** argv)
{
  if (argc < 2)
  {
    printf("usage: %s issue617_revolution.brep [--write <dir>]\n", argv[0]);
    return 2;
  }
  std::string aDir = argc > 3 && !strcmp(argv[2], "--write") ? argv[3] : "";
  BRep_Builder aBB;
  TopoDS_Shape aRev;
  if (!BRepTools::Read(aRev, argv[1], aBB))
  {
    printf("cannot read %s\n", argv[1]);
    return 2;
  }
  TopoDS_Face aFace = TopoDS::Face(TopExp_Explorer(aRev, TopAbs_FACE).Current());
  const gp_Pln aPln(gp_Pnt(0, 0, 0), gp_Dir(0, 0, 1));
  BRepAlgoAPI_Section aSec(aFace, aPln, false);
  aSec.Approximation(true);
  aSec.Build();
  if (!aSec.IsDone())
  {
    printf("no section\n");
    return 1;
  }
  const double    aH = 100.;
  TopoDS_Compound aPrisms;
  aBB.MakeCompound(aPrisms);
  double aVolRef = 0., anAreaRef = 0.;
  int    aNb = 0;
  for (TopExp_Explorer anE(aSec.Shape(), TopAbs_EDGE); anE.More(); anE.Next())
  {
    const TopoDS_Edge& anEdge = TopoDS::Edge(anE.Current());
    BRepAdaptor_Curve  aC(anEdge);
    // the lobe's area: the shoelace over a dense polygon of its curve
    const int    aN  = 400000;
    const double aT0 = aC.FirstParameter(), aT1 = aC.LastParameter();
    double       aShoe = 0.;
    gp_Pnt       aP0   = aC.Value(aT0), aPrev = aP0;
    for (int i = 1; i <= aN; ++i)
    {
      const gp_Pnt aP = i == aN ? aP0 : aC.Value(aT0 + (aT1 - aT0) * i / aN);
      aShoe += aPrev.X() * aP.Y() - aP.X() * aPrev.Y();
      aPrev = aP;
    }
    const double aLobe = 0.5 * std::abs(aShoe);
    const double aLen  = GCPnts_AbscissaPoint::Length(aC, 1.e-10);
    TopoDS_Wire  aW    = BRepBuilderAPI_MakeWire(anEdge).Wire();
    TopoDS_Face  aF    = BRepBuilderAPI_MakeFace(aPln, aW).Face();
    GProp_GProps aG;
    BRepGProp::SurfaceProperties(aF, aG);
    printf("lobe %d: degree %d, %d knots; area %.6f (shoelace %.6f), length %.6f\n",
           ++aNb,
           aC.GetType() == GeomAbs_BSplineCurve ? aC.Degree() : 0,
           aC.GetType() == GeomAbs_BSplineCurve ? aC.NbKnots() : 0,
           aG.Mass(),
           aLobe,
           aLen);
    aBB.Add(aPrisms, BRepPrimAPI_MakePrism(aF, gp_Vec(0, 0, aH)).Shape());
    aVolRef += aLobe * aH;
    anAreaRef += 2. * aLobe + aLen * aH;
  }
  GProp_GProps aV, aS;
  BRepGProp::VolumeProperties(aPrisms, aV);
  BRepGProp::SurfaceProperties(aPrisms, aS);
  const double aVErr = std::abs(aV.Mass() - aVolRef) / aVolRef;
  const double aSErr = std::abs(aS.Mass() - anAreaRef) / anAreaRef;
  const bool   isOk  = aNb == 2 && aVErr < 1.e-7 && aSErr < 1.e-7;
  printf("prisms: volume %.4f (want %.4f, off %.2g), area %.4f (want %.4f, off %.2g): %s\n",
         aV.Mass(),
         aVolRef,
         aVErr,
         aS.Mass(),
         anAreaRef,
         aSErr,
         isOk ? "PASS" : "FAIL");
  if (!aDir.empty())
  {
    BRepTools::Write(aRev, (aDir + "/revolution.brep").c_str());
    BRepTools::Write(aPrisms, (aDir + "/prisms.brep").c_str());
    BRepTools::Write(aSec.Shape(), (aDir + "/section.brep").c_str());
  }
  return isOk ? 0 : 1;
}
