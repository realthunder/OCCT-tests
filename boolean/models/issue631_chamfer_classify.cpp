// issue631_chamfer_classify: points inside a chamfered solid said outside it.
// See ../README.md, "A line that passes an edge within its tolerance".
//
// The solid is #631's Fillet001 with two edges at a vertex chamfered at 1,
// the corner of the two set back and closed by a patch (the fork's fillet
// builder, d2c2d39f9d; issue631_chamfer_corner.brep: one solid, valid,
// 42166.9504). The patch is a B-spline face with edges of tolerance 0.011.
// BRepClass3d_SolidClassifier casts a line from the point to a point of a
// face. Where the line passes an edge within the edge's tolerance it took
// the pass for a crossing of the solid's skin there, which way told by the
// normals of the edge's two faces -- as of a line through the edge. The line
// of (47.056, 38.163, 95.37), a point 0.56 inside the solid, passes such an
// edge 0.008 from its curve at 5.9, where it clips a notch of the patch: out
// of the solid and in again within the edge's tolerance, neither crossing
// found on a face. It was taken to enter the solid there, and the point was
// OUT.
//
// Checked here: thirteen such points (found by a sample of 60000 in the cube
// of 8 about the vertex) are inside; of 24000 points sampled there, none
// said outside is inside by the crossings of seven lines from it, each face
// intersected on its own (IntCurvesFace_Intersector), counted.
//
// Build (OCCT install prefix O; on Linux add -Wl,--enable-new-dtags so that
// LD_LIBRARY_PATH can put another library first):
//   c++ -std=c++17 -w -I$O/include/opencascade issue631_chamfer_classify.cpp \
//     -L$O/lib -Wl,-rpath,$O/lib -lTKBO -lTKPrim -lTKTopAlgo -lTKBRep \
//     -lTKGeomAlgo -lTKGeomBase -lTKG3d -lTKG2d -lTKMath -lTKernel \
//     -o issue631_chamfer_classify
// Run: ./issue631_chamfer_classify <issue631_chamfer_corner.brep> [--write <dir>]
//   (exit 0 when every check passes)
//   --write: <dir>/said_out.brep, the solid with a ball at each sampled point
//   inside it that was said outside
#include <BRepClass3d_SolidClassifier.hxx>
#include <BRepPrimAPI_MakeSphere.hxx>
#include <BRepTools.hxx>
#include <BRep_Builder.hxx>
#include <IntCurvesFace_Intersector.hxx>
#include <NCollection_IndexedMap.hxx>
#include <TopExp.hxx>
#include <TopTools_ShapeMapHasher.hxx>
#include <TopoDS.hxx>
#include <TopoDS_Compound.hxx>
#include <gp_Lin.hxx>
#include <cmath>
#include <cstdio>
#include <cstring>
#include <memory>
#include <random>
#include <string>
#include <vector>

int main(int argc, char** argv)
{
  if (argc < 2)
  {
    fprintf(stderr, "usage: %s issue631_chamfer_corner.brep [--write dir]\n", argv[0]);
    return 2;
  }
  const char*  aDir = (argc > 3 && !strcmp(argv[2], "--write")) ? argv[3] : nullptr;
  BRep_Builder aBB;
  TopoDS_Shape aSolid;
  if (!BRepTools::Read(aSolid, argv[1], aBB))
  {
    fprintf(stderr, "cannot read the model\n");
    return 2;
  }
  bool bOK = true;

  // the points found
  const double aPnts[13][3] = {
    {46.955725, 37.499967, 94.849289}, {45.004238, 36.470048, 92.334427},
    {46.088384, 37.300863, 93.738921}, {47.028547, 38.460188, 95.627670},
    {45.918066, 38.248505, 94.513218}, {46.490766, 38.643030, 95.362799},
    {47.462874, 37.663013, 95.246202}, {46.673168, 37.377404, 94.545603},
    {46.843711, 37.733031, 94.788969}, {47.461501, 37.914552, 95.870643},
    {45.799292, 37.038818, 93.248019}, {45.665392, 38.194349, 94.241543},
    {46.968651, 38.873260, 95.988404}};
  int aNbOut = 0;
  for (const double* aP : aPnts)
  {
    BRepClass3d_SolidClassifier aCl(aSolid, gp_Pnt(aP[0], aP[1], aP[2]), 1.e-7);
    aNbOut += aCl.State() == TopAbs_IN ? 0 : 1;
  }
  printf("points: %d of 13 inside the solid said outside (want 0)  %s\n",
         aNbOut,
         aNbOut == 0 ? "PASS" : "FAIL");
  bOK = bOK && aNbOut == 0;

  // a sample about the vertex; what is said outside counted along seven lines
  NCollection_IndexedMap<TopoDS_Shape, TopTools_ShapeMapHasher> aFaces;
  TopExp::MapShapes(aSolid, TopAbs_FACE, aFaces);
  std::vector<std::unique_ptr<IntCurvesFace_Intersector>> anInter;
  for (int i = 1; i <= aFaces.Extent(); i++)
  {
    anInter.emplace_back(new IntCurvesFace_Intersector(TopoDS::Face(aFaces(i)), 1.e-7));
  }
  const gp_Pnt                           aC(44., 36.332, 92.);
  const double                           aH = 4.;
  std::mt19937                           aGen(3);
  std::uniform_real_distribution<double> aU(-aH, aH);
  std::normal_distribution<double>       aN(0., 1.);
  TopoDS_Compound                        aSaid;
  aBB.MakeCompound(aSaid);
  aBB.Add(aSaid, aSolid);
  const int                   aNb = 24000;
  int                         aNbSaid = 0;
  BRepClass3d_SolidClassifier aCl(aSolid);
  for (int i = 0; i < aNb; i++)
  {
    const gp_Pnt aP(aC.X() + aU(aGen), aC.Y() + aU(aGen), aC.Z() + aU(aGen));
    aCl.Perform(aP, 1.e-7);
    if (aCl.State() != TopAbs_OUT)
    {
      continue;
    }
    int aNbIn = 0;
    for (int k = 0; k < 7; k++)
    {
      const gp_Lin aL(aP, gp_Dir(aN(aGen), aN(aGen), aN(aGen)));
      int          aNbCross = 0;
      for (auto& anI : anInter)
      {
        anI->Perform(aL, 0., 1.e7);
        aNbCross += anI->IsDone() ? anI->NbPnt() : 0;
      }
      aNbIn += aNbCross % 2;
    }
    if (aNbIn >= 5)
    {
      ++aNbSaid;
      aBB.Add(aSaid, BRepPrimAPI_MakeSphere(aP, 0.12).Shape());
    }
  }
  printf("sample: %d of %d points about the vertex inside and said outside (want 0)  %s\n",
         aNbSaid,
         aNb,
         aNbSaid == 0 ? "PASS" : "FAIL");
  bOK = bOK && aNbSaid == 0;

  if (aDir)
  {
    BRepTools::Write(aSaid, (std::string(aDir) + "/said_out.brep").c_str());
  }
  return bOK ? 0 : 1;
}
