// issue280_pocket_cut: #280's Pocket -- the part cut by the pocket's tool,
// and their common and fuse. See ../README.md, "#280: a section that stops
// short of the corner it runs into".
//
// The part is a slab with a rounded edge, extruded 80 along y, its ends
// revolved a quarter turn about x and the whole mirrored about z = 0: the
// revolved ends meet the mirror plane in arcs. The tool is a prism along y
// under z = 0, its profile a quarter disc; its cylinder's rim lies in z = 0
// on the line x = 25 -- along the part's edge there for |y| <= 45, and for
// |y| > 45 outside the part, tangent at (25, +-45, 0) to the arc a revolved
// end meets the mirror plane in. The section of the cylinder with that end
// runs into the corner along both, the arc within 1e-7 of the cylinder for
// 0.25 before it, and the walking line stopped 0.0051 short. Its end took a
// vertex of its own, the pieces of the rim and of the arc from there to the
// corner (2e-7 apart) were not found the same, and no solid was split: the
// cut came back the part unchanged with 29 faces, the common and the fuse
// empty, with no error and no warning.
//
// The right volumes, from the tool moved 0.001 up and down along z (where
// nothing is tangent and the three add up): cut 70554.63, common 28084.41,
// fuse 156253.74. At the corner the two edges of the thin piece of the
// revolved face stay within tolerance of each other for 0.2, and the vertex
// there has that tolerance, before the fix as after; the volumes read
// across it are short by up to 0.12.
//
// Build (OCCT install prefix O; on Linux add -Wl,--enable-new-dtags so that
// LD_LIBRARY_PATH can put another library first):
//   c++ -std=c++17 -w -I$O/include/opencascade issue280_pocket_cut.cpp \
//     -L$O/lib -Wl,-rpath,$O/lib -lTKBO -lTKTopAlgo -lTKBRep -lTKGeomAlgo \
//     -lTKGeomBase -lTKG3d -lTKG2d -lTKMath -lTKernel -o issue280_pocket_cut
// Run: ./issue280_pocket_cut <part.brep> <tool.brep> [--write <dir>]
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
#include <TopExp_Explorer.hxx>
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
  const double aRefTol = 1.e-5 * theRef;
  const bool   bRun    = bValid && aNbSo == 1 && std::abs(aGP.Mass() - theRef) <= aRefTol;
  printf("%s: %s, %d solid(s), %d faces, volume %.4f (want %.2f +- %.2f), largest vertex "
         "tolerance %.2g  %s\n",
         theName,
         bValid ? "valid" : "invalid",
         aNbSo,
         aNbF,
         aGP.Mass(),
         theRef,
         aRefTol,
         aTolV,
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
    fprintf(stderr, "usage: %s part.brep tool.brep [--write dir]\n", argv[0]);
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
  bool bOK = run<BRepAlgoAPI_Cut>("cut", aPart, aTool, 70554.63, aDir);
  bOK      = run<BRepAlgoAPI_Common>("common", aPart, aTool, 28084.41, aDir) && bOK;
  bOK      = run<BRepAlgoAPI_Fuse>("fuse", aPart, aTool, 156253.74, aDir) && bOK;
  return bOK ? 0 : 1;
}
