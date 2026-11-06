// issue617_seam_pcurve: #617's pad on its revolution -- the pcurve of the pad's
// bottom edge on the revolution (ProjLib_ProjectedCurve, what the pave filler
// builds it with), and the general fuse of the two. See ../README.md, "#617:
// the pad's bottom edge projected across the revolution's seam".
//
// The revolution's profile is a closed B-spline, not periodic: the surface is
// closed in v, its two v bounds one circle. The pad's bottom edge is the
// revolution's cut by z = 0 and starts and ends on that circle. Its projection
// walked to v's upper bound, and the guard against traps on a revolution's v
// bounds (UpdateTripleByTrapCriteria, OCCT bug 25892) searched the last point
// afresh, found the lower bound and took it: the pcurve ran back across the
// whole range on its last step, 36.5 off. And the approximation of the walk
// was held to 16 segments, which cannot follow a degree 8 B-spline of 29
// spans, its knots bunched where the cut turns: 0.8 off at any tolerance.
// Every general fuse of the two carried an edge of tolerance 36 to 39 (the
// plain one took 184 s).
//
// Build (OCCT install prefix O; on Linux add -Wl,--enable-new-dtags so that
// LD_LIBRARY_PATH can put another library first):
//   c++ -std=c++17 -w -I$O/include/opencascade issue617_seam_pcurve.cpp \
//     -L$O/lib -Wl,-rpath,$O/lib -lTKBO -lTKTopAlgo -lTKBRep -lTKGeomAlgo \
//     -lTKGeomBase -lTKG3d -lTKG2d -lTKMath -lTKernel -o issue617_seam_pcurve
// Run: ./issue617_seam_pcurve <revolution.brep> <prisms.brep> [--write <dir>]
//   (exit 0 when every run passes)
//   --write: the pcurve at each tolerance as an edge on the revolution,
//   <dir>/pcurve_<tol>.brep, and the bottom edge, <dir>/edge.brep
#include <BOPAlgo_Builder.hxx>
#include <BRepAdaptor_Surface.hxx>
#include <BRepBuilderAPI_MakeEdge.hxx>
#include <BRepTools.hxx>
#include <BRep_Builder.hxx>
#include <BRep_Tool.hxx>
#include <Geom2d_Curve.hxx>
#include <GeomAdaptor_Curve.hxx>
#include <Geom_Curve.hxx>
#include <Geom_Surface.hxx>
#include <ProjLib.hxx>
#include <ProjLib_ProjectedCurve.hxx>
#include <TopExp.hxx>
#include <TopExp_Explorer.hxx>
#include <TopTools_IndexedMapOfShape.hxx>
#include <TopoDS.hxx>
#include <TopoDS_Edge.hxx>
#include <TopoDS_Face.hxx>
#include <algorithm>
#include <chrono>
#include <cstdio>
#include <cstring>
#include <string>

int main(int argc, char** argv)
{
  if (argc < 3)
  {
    fprintf(stderr, "usage: %s revolution.brep prisms.brep [--write dir]\n", argv[0]);
    return 2;
  }
  const char* aDir = (argc > 4 && !strcmp(argv[3], "--write")) ? argv[4] : nullptr;
  BRep_Builder aBB;
  TopoDS_Shape aRev, aPrisms;
  if (!BRepTools::Read(aRev, argv[1], aBB) || !BRepTools::Read(aPrisms, argv[2], aBB))
  {
    fprintf(stderr, "cannot read the models\n");
    return 2;
  }
  TopTools_IndexedMapOfShape aMF, aME;
  TopExp::MapShapes(aRev, TopAbs_FACE, aMF);
  TopExp::MapShapes(aPrisms, TopAbs_EDGE, aME);
  const TopoDS_Face aF = TopoDS::Face(aMF(1));
  const TopoDS_Edge aE = TopoDS::Edge(aME(2)); // the first prism's bottom edge
  double            f, l;
  const occ::handle<Geom_Curve>   aC = BRep_Tool::Curve(aE, f, l);
  const occ::handle<Geom_Surface> aS = BRep_Tool::Surface(aF);
  if (aDir)
  {
    BRepTools::Write(aE, (std::string(aDir) + "/edge.brep").c_str());
  }
  bool bOK = true;

  // 1. The pcurve, at the edge's tolerance and at a fuzzy value's: within the
  // tolerance of the edge (or 4e-7, the edge being 3.5e-7 off the revolution),
  // and ending at v's upper bound, where the edge comes back to the circle.
  occ::handle<BRepAdaptor_Surface> aHS = new BRepAdaptor_Surface(aF, true);
  occ::handle<GeomAdaptor_Curve>   aHC = new GeomAdaptor_Curve(aC, f, l);
  for (double aTol : {1.e-7, 1.e-5})
  {
    ProjLib_ProjectedCurve aProj(aHS, aHC, aTol);
    occ::handle<Geom2d_Curve> aC2;
    ProjLib::MakePCurveOfType(aProj, aC2);
    if (aC2.IsNull())
    {
      printf("pcurve tol %g: none  FAIL\n", aTol);
      bOK = false;
      continue;
    }
    double aDMax = 0.;
    for (int i = 0; i <= 2000; ++i)
    {
      const double t  = f + (l - f) * i / 2000.;
      gp_Pnt2d     uv = aC2->Value(t);
      aDMax           = std::max(aDMax, aS->Value(uv.X(), uv.Y()).Distance(aC->Value(t)));
    }
    const gp_Pnt2d aUV1 = aC2->Value(l);
    const bool     bEnd = std::abs(aUV1.Y() - aHS->LastVParameter()) < 1.e-6;
    const bool     bRun = aDMax <= std::max(aTol, 4.e-7) && bEnd;
    printf("pcurve tol %g: %.3g off the edge, ends at v %.6f (bounds %.6f, %.6f)  %s\n",
           aTol,
           aDMax,
           aUV1.Y(),
           aHS->FirstVParameter(),
           aHS->LastVParameter(),
           bRun ? "PASS" : "FAIL");
    bOK = bOK && bRun;
    if (aDir)
    {
      char aName[64];
      snprintf(aName, sizeof(aName), "/pcurve_%g.brep", aTol);
      BRepTools::Write(BRepBuilderAPI_MakeEdge(aC2, aS, f, l).Edge(),
                       (std::string(aDir) + aName).c_str());
    }
  }

  // 2. The general fuse of the two, plain and under fuzzy values: done, and no
  // edge of its result with a tolerance above 1e-3. Each from the models as
  // read: the fuse updates its arguments' tolerances and pcurves.
  for (double aFuzzy : {0., 1.e-6, 1.e-5, 1.e-4})
  {
    TopoDS_Shape aRevG, aPrismsG;
    BRepTools::Read(aRevG, argv[1], aBB);
    BRepTools::Read(aPrismsG, argv[2], aBB);
    BOPAlgo_Builder aGF;
    aGF.AddArgument(aRevG);
    aGF.AddArgument(aPrismsG);
    if (aFuzzy > 0.)
    {
      aGF.SetFuzzyValue(aFuzzy);
    }
    const auto aT0 = std::chrono::steady_clock::now();
    aGF.Perform();
    const double aSec =
      std::chrono::duration<double>(std::chrono::steady_clock::now() - aT0).count();
    double aTolMax = 0.;
    for (TopExp_Explorer aX(aGF.Shape(), TopAbs_EDGE); aX.More(); aX.Next())
    {
      aTolMax = std::max(aTolMax, BRep_Tool::Tolerance(TopoDS::Edge(aX.Current())));
    }
    const bool bRun = !aGF.HasErrors() && aTolMax <= 1.e-3;
    printf("general fuse, fuzzy %g: %s, largest edge tolerance %.3g, %.1f s  %s\n",
           aFuzzy,
           aGF.HasErrors() ? "errors" : "done",
           aTolMax,
           aSec,
           bRun ? "PASS" : "FAIL");
    bOK = bOK && bRun;
  }
  return bOK ? 0 : 1;
}
