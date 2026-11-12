// issue617_torus_pad: #617's Pad on a torus (the model's _simple variant) --
// the torus fused with the pad's prism, and their cut and common. See
// ../README.md, "#617: a pad standing on a torus along its own cut".
//
// The torus (R 27.58, r 11.97, its axis in the plane z = 0, tilted) is cut by
// the plane x = 0 in two closed curves; the pad's profile is one of them as
// the sketch keeps it, a B-spline of degree 5 that is 6.1e-5 off the torus
// and crosses it 44 times, and the prism runs from it to x = -100. The
// profile says so, a tolerance of 7.3e-5 (FreeCAD since `SimplifiedWithin`;
// at the default 1e-7 the edge is neither on the torus nor off it, and no
// result is to be asked for): its edge and the vertices alone in
// issue617_torus_pad_edge.brep, the prism's wall as well, as FreeCAD makes
// the pad, in issue617_torus_pad.brep. The
// wall stands on the torus along the profile and is tangent to it at
// (0, 29.2128, -28.3025) and (0, 6.3525, -21.1993); there the second branch
// of their section leaves the edge, to the wall's seam at x = -26.01 and
// back. The walking lines lose their way at both points: one turns 0.07
// short, runs beside the edge and stops 0.17 past the point on nothing, the
// other comes along the edge, crosses it 0.007 the wrong side of the point
// and hooks back over it 0.12 further on. With the edge alone saying it
// the fuse came back two solids, unfused, the common nothing and the cut
// the torus, with no error; with the wall as well one solid, 3.4 short,
// with a vertex of 0.041 and an edge going nowhere.
//
// The right volumes, from the prism moved 0.01 along x either way, halved
// (nothing tangent there, and the three add up): cut 70020.56, common
// 7959.79, fuse 122396.04. No vertex of a result may be looser than the
// profile says (1e-4 asked), and no edge has a face missing.
//
// Build (OCCT install prefix O; on Linux add -Wl,--enable-new-dtags so that
// LD_LIBRARY_PATH can put another library first):
//   c++ -std=c++17 -w -I$O/include/opencascade issue617_torus_pad.cpp \
//     -L$O/lib -Wl,-rpath,$O/lib -lTKBO -lTKTopAlgo -lTKBRep -lTKGeomAlgo \
//     -lTKGeomBase -lTKG3d -lTKG2d -lTKMath -lTKernel -o issue617_torus_pad
// Run: ./issue617_torus_pad <torus.brep> <pad.brep> [--write <dir>]
//   (exit 0 when every run passes)
//   --write: each result, <dir>/cut.brep, common.brep, fuse.brep
#include <BRepAlgoAPI_Common.hxx>
#include <BRepAlgoAPI_Cut.hxx>
#include <BRepAlgoAPI_Fuse.hxx>
#include <BRepCheck_Analyzer.hxx>
#include <BRepGProp.hxx>
#include <BRepTools.hxx>
#include <BRep_Builder.hxx>
#include <BRep_Tool.hxx>
#include <GProp_GProps.hxx>
#include <TopExp.hxx>
#include <TopExp_Explorer.hxx>
#include <TopTools_IndexedDataMapOfShapeListOfShape.hxx>
#include <TopTools_ListOfShape.hxx>
#include <TopoDS.hxx>
#include <TopoDS_Vertex.hxx>
#include <algorithm>
#include <cmath>
#include <cstdio>
#include <cstring>
#include <string>

template <class Op>
static bool run(const char*         theName,
                const TopoDS_Shape& thePart,
                const TopoDS_Shape& theTool,
                const double        theRef,
                const char*         theDir)
{
  TopTools_ListOfShape aLA, aLT;
  aLA.Append(thePart);
  aLT.Append(theTool);
  Op anOp;
  anOp.SetArguments(aLA);
  anOp.SetTools(aLT);
  anOp.Build();
  if (!anOp.IsDone() || anOp.HasErrors())
  {
    printf("%s: failed  FAIL\n", theName);
    return false;
  }
  const TopoDS_Shape& aRes   = anOp.Shape();
  const bool          bValid = BRepCheck_Analyzer(aRes).IsValid();
  GProp_GProps        aGP;
  BRepGProp::VolumeProperties(aRes, aGP);
  int    aNbSo = 0, aNbF = 0;
  double aTolV = 0.;
  for (TopExp_Explorer aX(aRes, TopAbs_SOLID); aX.More(); aX.Next())
  {
    ++aNbSo;
  }
  for (TopExp_Explorer aX(aRes, TopAbs_FACE); aX.More(); aX.Next())
  {
    ++aNbF;
  }
  for (TopExp_Explorer aX(aRes, TopAbs_VERTEX); aX.More(); aX.Next())
  {
    aTolV = std::max(aTolV, BRep_Tool::Tolerance(TopoDS::Vertex(aX.Current())));
  }
  // the edges a face is missing at
  TopTools_IndexedDataMapOfShapeListOfShape aMEF;
  TopExp::MapShapesAndAncestors(aRes, TopAbs_EDGE, TopAbs_FACE, aMEF);
  int aNbLoose = 0;
  for (int i = 1; i <= aMEF.Extent(); ++i)
  {
    const TopoDS_Edge& aE = TopoDS::Edge(aMEF.FindKey(i));
    // a seam is on its one face twice; in the cut the profile is on four,
    // where the hole reaches the torus' skin along it
    if (!BRep_Tool::Degenerated(aE) && aMEF(i).Extent() % 2 != 0
        && !(aMEF(i).Extent() == 1 && BRep_Tool::IsClosed(aE, TopoDS::Face(aMEF(i).First()))))
    {
      ++aNbLoose;
    }
  }
  const double aRefTol = 1.e-5 * theRef;
  const bool   bRun    = bValid && aNbSo == 1 && std::abs(aGP.Mass() - theRef) <= aRefTol
                         && aTolV <= 1.e-4 && aNbLoose == 0;
  printf("%s: %s, %d solid(s), %d faces, volume %.4f (want %.2f +- %.2f), largest vertex "
         "tolerance %.2g (want <= 1e-4), %d edge(s) with a face missing  %s\n",
         theName,
         bValid ? "valid" : "invalid",
         aNbSo,
         aNbF,
         aGP.Mass(),
         theRef,
         aRefTol,
         aTolV,
         aNbLoose,
         bRun ? "PASS" : "FAIL");
  if (theDir)
  {
    BRepTools::Write(aRes, (std::string(theDir) + "/" + theName + ".brep").c_str());
  }
  return bRun;
}

int main(int argc, char** argv)
{
  if (argc < 3)
  {
    fprintf(stderr, "usage: %s torus.brep pad.brep [--write dir]\n", argv[0]);
    return 2;
  }
  const char*  aDir = (argc > 4 && !strcmp(argv[3], "--write")) ? argv[4] : nullptr;
  BRep_Builder aBB;
  TopoDS_Shape aPart, aTool;
  if (!BRepTools::Read(aPart, argv[1], aBB) || !BRepTools::Read(aTool, argv[2], aBB))
  {
    fprintf(stderr, "cannot read the models\n");
    return 2;
  }
  bool bOK = run<BRepAlgoAPI_Cut>("cut", aPart, aTool, 70020.56, aDir);
  bOK      = run<BRepAlgoAPI_Common>("common", aPart, aTool, 7959.79, aDir) && bOK;
  bOK      = run<BRepAlgoAPI_Fuse>("fuse", aPart, aTool, 122396.04, aDir) && bOK;
  return bOK ? 0 : 1;
}
