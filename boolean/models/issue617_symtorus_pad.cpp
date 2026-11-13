// issue617_symtorus_pad: a pad standing on a torus along the torus' own cut
// through a plane of symmetry -- the torus fused with the pad's prism, and
// their cut and common. See ../README.md, "#617: the same line more than once
// past a tangent point".
//
// The torus (R 30, r 12, about the y axis) is cut by the plane x = 10 in two
// closed curves, one at z < 0 and one at z > 0, each the other's mirror image
// and its own in y = 0; the pad's profile is the two as a sketch keeps them,
// B-splines of degree 5 that are 6e-5 off the torus and say so (8.1e-5), and
// the prism runs from them along x: to x = 70 (issue617_symtorus_pad.brep),
// to x = -50 (issue617_symtorus_pad_back.brep), and to x = 70 with each
// curve cut in two at (10, -0.0053, +-14.9666), as FreeCAD's face maker had
// them until 2026-11-13 (issue617_symtorus_pad_split.brep). The walls stand
// on the torus along the profile and are tangent to it at (10, +-12,
// +-28.2843), where the second branch of their section leaves the edge.
//
// Towards +x three walking lines of one wall go by one such point: one
// stops 0.016 short of it, two come round it 0.022 off and run on along the
// profile. The first was cut and joined to the point, the other two took
// the point as it was and it grew to reach them: valid, a vertex of 0.028,
// the fuse 11.4 short, the cut 5.9 and the common 1.2. With the curves cut
// in two a line runs past the end of its wall, and one comes by the point,
// runs on along the edge for 0.44, turns round and comes by again: the fuse
// and the cut invalid, a vertex of 11, the common one solid of the two.
// Towards -x the results were right and took more than 100 s each: one
// line's length was integrated down to 5e-24.
//
// The right volumes, from the prism moved 0.01 along x either way, halved:
// towards +x cut 68644.34 (two solids: what is left of the torus beyond the
// plane touches the rest along the profile only), common 16629.04 (two),
// fuse 126823.24; towards -x cut 50970.12 (four), common 34303.27 (two),
// fuse 109149.01. No vertex of a result may be looser than 1e-4 (3e-4 with
// the curves cut in two, where a section curve is given as 2.2e-4), no edge
// has a face missing, and no run takes a minute.
//
// And a torus about a tilted axis (issue617_tilttorus.brep: the circle of
// radius 12 at (39, 12, 0) about the line from (15, 40, 0) to (9, 0, 0)), cut
// by x = 0 in two curves that are each other's mirror image only, with the
// prism on both towards +x (issue617_tilttorus_pad.brep, "tilt") and towards
// -x (issue617_tilttorus_pad_back.brep, "tiltback"). Towards -x two lines of
// one wall go by one tangent point, one of them given as 1.1e-3 by the
// intersector and swinging 0.018 out of its wall past the point: both took
// the point grown to 0.0135 and the fuse was 4.6 short (valid). Wanted: cut
// 46379.70, common 32890.45, fuse 108216.35 towards +x, and 63229.37,
// 16040.78, 125066.03 towards -x, where a vertex may be 1e-3 (that line is
// given as 5.4e-4 once cut).
//
// And the prism of cut curves moved 0.01 into the symmetric torus ("sunk",
// with issue617_symtorus_pad_split.brep; the move is made here). Its bottom
// edge crosses the torus at a grazing angle near each tangent point, and the
// vertex made there had its tolerance stretched to 0.3 and was put on a
// section line that only passes it, 0.046 off: five edges in one vertex of
// 0.046, a face of the torus not made, the common nothing and the cut the
// torus less 31, valid and with no error. Wanted, the prism of whole curves'
// own at that place: cut 68634.65, common 16638.73, fuse 126813.55.
//
// Build (OCCT install prefix O; on Linux add -Wl,--enable-new-dtags so that
// LD_LIBRARY_PATH can put another library first):
//   c++ -std=c++17 -w -I$O/include/opencascade issue617_symtorus_pad.cpp \
//     -L$O/lib -Wl,-rpath,$O/lib -lTKBO -lTKTopAlgo -lTKBRep -lTKGeomAlgo \
//     -lTKGeomBase -lTKG3d -lTKG2d -lTKMath -lTKernel -o issue617_symtorus_pad
// Run: ./issue617_symtorus_pad <torus.brep> <pad.brep> forward|back|split|tilt|tiltback|sunk
//        [--write <dir>]
//   (exit 0 when every run passes)
//   --write: each result, <dir>/cut.brep, common.brep, fuse.brep
#include <BRepAlgoAPI_Common.hxx>
#include <BRepAlgoAPI_Cut.hxx>
#include <BRepAlgoAPI_Fuse.hxx>
#include <BRepBuilderAPI_Transform.hxx>
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
#include <chrono>
#include <cmath>
#include <cstdio>
#include <cstring>
#include <string>

template <class Op>
static bool run(const char*         theName,
                const TopoDS_Shape& thePart,
                const TopoDS_Shape& theTool,
                const double        theRef,
                const int           theNbSolids,
                const double        theTolMax,
                const char*         theDir)
{
  const auto aStart = std::chrono::steady_clock::now();
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
  const double aTime =
    std::chrono::duration<double>(std::chrono::steady_clock::now() - aStart).count();
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
    // a seam is on its one face twice; where two solids touch along the
    // profile it is on four faces
    if (!BRep_Tool::Degenerated(aE) && aMEF(i).Extent() % 2 != 0
        && !(aMEF(i).Extent() == 1 && BRep_Tool::IsClosed(aE, TopoDS::Face(aMEF(i).First()))))
    {
      ++aNbLoose;
    }
  }
  const double aRefTol = 1.e-5 * theRef;
  const bool   bRun    = bValid && aNbSo == theNbSolids
                         && std::abs(aGP.Mass() - theRef) <= aRefTol && aTolV <= theTolMax
                         && aNbLoose == 0 && aTime < 60.;
  printf("%s: %s, %d solid(s) (want %d), %d faces, volume %.4f (want %.2f +- %.2f), largest "
         "vertex tolerance %.2g (want <= %.0e), %d edge(s) with a face missing, %.1f s (want "
         "< 60)  %s\n",
         theName,
         bValid ? "valid" : "invalid",
         aNbSo,
         theNbSolids,
         aNbF,
         aGP.Mass(),
         theRef,
         aRefTol,
         aTolV,
         theTolMax,
         aNbLoose,
         aTime,
         bRun ? "PASS" : "FAIL");
  if (theDir)
  {
    BRepTools::Write(aRes, (std::string(theDir) + "/" + theName + ".brep").c_str());
  }
  return bRun;
}

int main(int argc, char** argv)
{
  // the volumes wanted and the solids of the cut, the common and the fuse,
  // and the loosest vertex allowed
  struct Kind
  {
    const char* Name;
    double      Vol[3];
    int         Solids[3];
    double      Tol;
  };
  static const Kind aKinds[] = {
    {"forward", {68644.34, 16629.04, 126823.24}, {2, 2, 1}, 1.e-4},
    {"back", {50970.12, 34303.27, 109149.01}, {4, 2, 1}, 1.e-4},
    {"split", {68644.34, 16629.04, 126823.24}, {2, 2, 1}, 3.e-4},
    {"tilt", {46379.70, 32890.45, 108216.35}, {2, 2, 1}, 1.e-4},
    {"tiltback", {63229.37, 16040.78, 125066.03}, {2, 2, 1}, 1.e-3},
    {"sunk", {68634.65, 16638.73, 126813.55}, {2, 2, 1}, 1.e-4}};
  const Kind* aKind = nullptr;
  for (const Kind& aK : aKinds)
  {
    if (argc > 3 && !strcmp(argv[3], aK.Name))
    {
      aKind = &aK;
    }
  }
  if (!aKind)
  {
    fprintf(stderr,
            "usage: %s torus.brep pad.brep forward|back|split|tilt|tiltback|sunk [--write dir]\n",
            argv[0]);
    return 2;
  }
  const char*  aDir = (argc > 5 && !strcmp(argv[4], "--write")) ? argv[5] : nullptr;
  BRep_Builder aBB;
  TopoDS_Shape aPart, aTool;
  if (!BRepTools::Read(aPart, argv[1], aBB) || !BRepTools::Read(aTool, argv[2], aBB))
  {
    fprintf(stderr, "cannot read the models\n");
    return 2;
  }
  if (!strcmp(aKind->Name, "sunk"))
  {
    gp_Trsf aMove;
    aMove.SetTranslation(gp_Vec(-0.01, 0., 0.));
    aTool = BRepBuilderAPI_Transform(aTool, aMove, true).Shape();
  }
  bool bOK = run<BRepAlgoAPI_Cut>("cut", aPart, aTool, aKind->Vol[0], aKind->Solids[0],
                                  aKind->Tol, aDir);
  bOK = run<BRepAlgoAPI_Common>("common", aPart, aTool, aKind->Vol[1], aKind->Solids[1],
                                aKind->Tol, aDir)
        && bOK;
  bOK = run<BRepAlgoAPI_Fuse>("fuse", aPart, aTool, aKind->Vol[2], aKind->Solids[2], aKind->Tol,
                              aDir)
        && bOK;
  return bOK ? 0 : 1;
}
