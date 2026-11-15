// issue474_coil_classify: points of #474's coil with one edge filleted said
// on the wrong side of it.
// See ../README.md, "A face that ends a hair past a knot of its surface".
//
// The solid is the coil of realthunder/FreeCAD#474 standing on its block,
// the block's upright edge at the coil's foot filleted at 0.3
// (issue474_coil_edge_filleted.brep: one solid, valid). The fillet ends on
// the coil's first helical face, a B-spline surface with a knot at u = 4,
// and the face's bounds, taken from its pcurves, end at u = 4.0000000172.
// BRepClass3d_SolidClassifier casts a line from the point to a point of a
// face and takes the first crossing; IntCurvesFace_Intersector finds the
// crossings on a polyhedron of the face and then exactly. The polyhedron of
// a face of several C2 intervals is built interval by interval, and the
// interval from 4 to 4.0000000172 gave it a last row of triangles 1.7e-8
// wide. That row was its border; the row before it, 0.2 wide, was not, and
// a line that crosses the face near its edge, where the edge bulges out of
// the row's chords, was not tried against it. The crossing was lost, the
// next one was the first, and the point was said on the other side.
// BOPAlgo classifies with the same classifier: the common of a line with
// the solid kept the part outside it.
//
// Checked here: two points outside said inside and two inside said outside
// are on their sides; of 24000 points sampled about the coil's foot none is
// said on the side that six of seven lines from it deny; the common of the
// line from (-12.958, -0.347, 9.870) along (-0.001308, 0.061261, 0.998121),
// 0.3 back to 2 on, with the solid is the 0.8509 inside it (1.4491 with the
// part outside).
//
// Build (OCCT install prefix O; on Linux add -Wl,--enable-new-dtags so that
// LD_LIBRARY_PATH can put another library first):
//   c++ -std=c++17 -w -I$O/include/opencascade issue474_coil_classify.cpp \
//     -L$O/lib -Wl,-rpath,$O/lib -lTKBO -lTKPrim -lTKTopAlgo -lTKBRep \
//     -lTKGeomAlgo -lTKGeomBase -lTKG3d -lTKG2d -lTKMath -lTKernel \
//     -o issue474_coil_classify
// Run: ./issue474_coil_classify <issue474_coil_edge_filleted.brep> [--write <dir>]
//   (exit 0 when every check passes)
//   --write: <dir>/said_wrong.brep, the solid with a ball at each sampled
//   point said on the wrong side
#include <BRepAlgoAPI_Common.hxx>
#include <BRepBuilderAPI_MakeEdge.hxx>
#include <BRepClass3d_SolidClassifier.hxx>
#include <BRepGProp.hxx>
#include <BRepPrimAPI_MakeSphere.hxx>
#include <BRepTools.hxx>
#include <BRep_Builder.hxx>
#include <GProp_GProps.hxx>
#include <IntCurvesFace_Intersector.hxx>
#include <NCollection_IndexedMap.hxx>
#include <TopExp.hxx>
#include <TopExp_Explorer.hxx>
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
    fprintf(stderr, "usage: %s issue474_coil_edge_filleted.brep [--write dir]\n", argv[0]);
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

  // the points found: two outside, two inside
  const double aPnts[4][3] = {{-12.958, -0.347, 9.870},
                              {-12.883, -0.886, 9.834},
                              {-12.896, -0.814, 11.676},
                              {-12.885, -0.931, 11.869}};
  int          aNbWrong   = 0;
  for (int i = 0; i < 4; i++)
  {
    BRepClass3d_SolidClassifier aCl(aSolid, gp_Pnt(aPnts[i][0], aPnts[i][1], aPnts[i][2]), 1.e-7);
    aNbWrong += aCl.State() == (i < 2 ? TopAbs_OUT : TopAbs_IN) ? 0 : 1;
  }
  printf("points: %d of 4 said on the wrong side of the solid (want 0)  %s\n",
         aNbWrong,
         aNbWrong == 0 ? "PASS" : "FAIL");
  bOK = bOK && aNbWrong == 0;

  // a sample about the coil's foot; each point's side counted along seven
  // lines as well
  NCollection_IndexedMap<TopoDS_Shape, TopTools_ShapeMapHasher> aFaces;
  TopExp::MapShapes(aSolid, TopAbs_FACE, aFaces);
  std::vector<std::unique_ptr<IntCurvesFace_Intersector>> anInter;
  for (int i = 1; i <= aFaces.Extent(); i++)
  {
    anInter.emplace_back(new IntCurvesFace_Intersector(TopoDS::Face(aFaces(i)), 1.e-7));
  }
  const gp_Pnt                           aC(-13., 0., 11.);
  const double                           aH = 1.2;
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
    if (aCl.State() != TopAbs_OUT && aCl.State() != TopAbs_IN)
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
    if (aCl.State() == TopAbs_OUT ? aNbIn >= 6 : aNbIn <= 1)
    {
      ++aNbSaid;
      aBB.Add(aSaid, BRepPrimAPI_MakeSphere(aP, 0.03).Shape());
    }
  }
  printf("sample: %d of %d points about the foot said on the wrong side (want 0)  %s\n",
         aNbSaid,
         aNb,
         aNbSaid == 0 ? "PASS" : "FAIL");
  bOK = bOK && aNbSaid == 0;

  // the common of a line through the face's corner with the solid
  const gp_Pnt       aPL(-12.958, -0.347, 9.870);
  const gp_Dir       aDL(-0.001308, 0.061261, 0.998121);
  const TopoDS_Edge  aLine = BRepBuilderAPI_MakeEdge(aPL.Translated(gp_Vec(aDL) * -0.3),
                                                    aPL.Translated(gp_Vec(aDL) * 2.));
  BRepAlgoAPI_Common aCommon(aLine, aSolid);
  double             aLen     = 0.;
  int                aNbEdges = 0;
  if (aCommon.IsDone() && !aCommon.HasErrors())
  {
    GProp_GProps aGP;
    BRepGProp::LinearProperties(aCommon.Shape(), aGP);
    aLen = aGP.Mass();
    for (TopExp_Explorer aX(aCommon.Shape(), TopAbs_EDGE); aX.More(); aX.Next())
    {
      ++aNbEdges;
    }
  }
  const bool bLine = aNbEdges == 1 && std::abs(aLen - 0.8509) <= 1.e-3;
  printf("line: its common with the solid %d edge(s), length %.4f (want 1, 0.8509)  %s\n",
         aNbEdges,
         aLen,
         bLine ? "PASS" : "FAIL");
  bOK = bOK && bLine;

  if (aDir)
  {
    BRepTools::Write(aSaid, (std::string(aDir) + "/said_wrong.brep").c_str());
  }
  return bOK ? 0 : 1;
}
