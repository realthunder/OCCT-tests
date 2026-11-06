// issue617_pad_fuse: #617's Pad -- the fuse of the two prisms padded from the
// revolution's cut by z = 0 with the revolution. See ../README.md, "#617: a
// pad's wall standing on a revolution along its bottom edge".
//
// Each prism's bottom edge is the revolution's cut and lies on it; the
// prism's wall stands on the revolution along it and is tangent to it at the
// two points where the revolution turns vertical. There a second branch of
// the wall's section leaves the edge, climbs to z 7.64 and comes back:
// between it and the edge the wall is inside the revolution. No edge/face
// intersection marks the two points (the edge is on the face all along), and
// the walking lines of the section lose their way a few 1e-3 off them,
// running on along the edge or stopping short. The fuse was invalid (93428,
// 69 s), or under a fuzzy value valid and wrong (119660, a prism wall kept
// whole). The right volume is 127114: the revolution's 62081.90 and the
// prisms' 71190.80 less their common part, 6164 by vertical rays through the
// prisms' base; the prisms 0.01 above or below give 127121 and 127107.
//
// Build (OCCT install prefix O; on Linux add -Wl,--enable-new-dtags so that
// LD_LIBRARY_PATH can put another library first):
//   c++ -std=c++17 -w -I$O/include/opencascade issue617_pad_fuse.cpp \
//     -L$O/lib -Wl,-rpath,$O/lib -lTKBO -lTKTopAlgo -lTKBRep -lTKGeomAlgo \
//     -lTKGeomBase -lTKG3d -lTKG2d -lTKMath -lTKernel -o issue617_pad_fuse
// Run: ./issue617_pad_fuse <revolution.brep> <prisms.brep> [--write <dir>]
//   (exit 0 when every run passes)
//   --write: each fuse, <dir>/fuse_<fuzzy>.brep
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
#include <chrono>
#include <cmath>
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
  const char*  aDir = (argc > 4 && !strcmp(argv[3], "--write")) ? argv[4] : nullptr;
  const double aRef = 127114., aRefTol = 20.;
  bool         bOK  = true;
  for (double aFuzzy : {0., 1.e-6, 1.e-5, 1.e-4})
  {
    BRep_Builder aBB;
    TopoDS_Shape aRev, aPrisms;
    if (!BRepTools::Read(aRev, argv[1], aBB) || !BRepTools::Read(aPrisms, argv[2], aBB))
    {
      fprintf(stderr, "cannot read the models\n");
      return 2;
    }
    TopTools_ListOfShape aLA, aLT;
    aLA.Append(aRev);
    aLT.Append(aPrisms);
    BRepAlgoAPI_Fuse aFuse;
    aFuse.SetArguments(aLA);
    aFuse.SetTools(aLT);
    if (aFuzzy > 0.)
    {
      aFuse.SetFuzzyValue(aFuzzy);
    }
    const auto aT0 = std::chrono::steady_clock::now();
    aFuse.Build();
    const double aSec =
      std::chrono::duration<double>(std::chrono::steady_clock::now() - aT0).count();
    if (!aFuse.IsDone() || aFuse.HasErrors())
    {
      printf("fuse, fuzzy %g: failed, %.1f s  FAIL\n", aFuzzy, aSec);
      bOK = false;
      continue;
    }
    const TopoDS_Shape& aRes   = aFuse.Shape();
    const bool          bValid = BRepCheck_Analyzer(aRes).IsValid();
    GProp_GProps        aGP;
    BRepGProp::VolumeProperties(aRes, aGP);
    int    aNbSo = 0;
    double aTolV = 0.;
    for (TopExp_Explorer aX(aRes, TopAbs_SOLID); aX.More(); aX.Next())
    {
      ++aNbSo;
    }
    for (TopExp_Explorer aX(aRes, TopAbs_VERTEX); aX.More(); aX.Next())
    {
      aTolV = std::max(aTolV, BRep_Tool::Tolerance(TopoDS::Vertex(aX.Current())));
    }
    const bool bRun = bValid && aNbSo == 1 && std::abs(aGP.Mass() - aRef) <= aRefTol;
    printf("fuse, fuzzy %g: %s, %d solid(s), volume %.4f (want %.0f +- %.0f), largest vertex "
           "tolerance %.2g, %.1f s  %s\n",
           aFuzzy,
           bValid ? "valid" : "invalid",
           aNbSo,
           aGP.Mass(),
           aRef,
           aRefTol,
           aTolV,
           aSec,
           bRun ? "PASS" : "FAIL");
    bOK = bOK && bRun;
    if (aDir)
    {
      char aName[64];
      snprintf(aName, sizeof(aName), "/fuse_%g.brep", aFuzzy);
      BRepTools::Write(aRes, (std::string(aDir) + aName).c_str());
    }
  }
  return bOK ? 0 : 1;
}
