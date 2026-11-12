// issue474_helix_classify: points outside #474's Helix002 said inside it.
// See ../README.md, "#474: a point outside a helix said inside it".
//
// The solid is a helical thread, 2.6 turns of a square profile between the
// radii 9.28 and 13 (issue474_helix.brep: one solid, valid, 1850.69), its
// flanks B-spline faces of four C2 intervals each. BRepClass3d_SolidClassifier
// casts a line from the point to a point of a face and takes the first
// crossing; IntCurvesFace_Intersector finds the crossings on a polyhedron of
// the face and then exactly. The polyhedron of a face of several intervals is
// built on parameters that are denser in one interval than in another, and
// how far its border chords are from the face's border was measured on as
// many even steps: 0.121 for the 0.160 of the longest chords of the rim. A
// line that crosses a flank just inside the rim (0.0008) where a chord is
// long passes the border triangle 0.144 out, more than the 0.121 allowed,
// and the crossing was lost: the next one, going out of the solid, was the
// first, and the point was said inside. BOPAlgo classifies with the same
// classifier: the common of a line through the solid with it kept the part
// outside.
//
// Checked here: seven such points (found by a sample of 20000 in the corners
// of the solid's box, beyond the cylinder it is in: 28 said inside) are
// outside; of 6000 points sampled there none is inside; the common of the
// line from (10.875, -12.661, 17.151) along (-0.047987, 0.971357, -0.232727)
// with the solid is 6.7904 long, one edge (12.1082 with the part outside).
//
// Build (OCCT install prefix O; on Linux add -Wl,--enable-new-dtags so that
// LD_LIBRARY_PATH can put another library first):
//   c++ -std=c++17 -w -I$O/include/opencascade issue474_helix_classify.cpp \
//     -L$O/lib -Wl,-rpath,$O/lib -lTKBO -lTKPrim -lTKTopAlgo -lTKBRep \
//     -lTKGeomAlgo -lTKGeomBase -lTKG3d -lTKG2d -lTKMath -lTKernel \
//     -o issue474_helix_classify
// Run: ./issue474_helix_classify <helix.brep> [--write <dir>]
//   (exit 0 when every check passes)
//   --write: <dir>/said_in.brep, the solid with a ball at each sampled point
//   said inside
#include <BRepAlgoAPI_Common.hxx>
#include <BRepBndLib.hxx>
#include <BRepBuilderAPI_MakeEdge.hxx>
#include <BRepClass3d_SolidClassifier.hxx>
#include <BRepGProp.hxx>
#include <BRepPrimAPI_MakeSphere.hxx>
#include <BRepTools.hxx>
#include <BRep_Builder.hxx>
#include <Bnd_Box.hxx>
#include <GProp_GProps.hxx>
#include <TopExp_Explorer.hxx>
#include <TopoDS.hxx>
#include <TopoDS_Compound.hxx>
#include <cmath>
#include <cstdio>
#include <cstring>
#include <random>
#include <string>

int main(int argc, char** argv)
{
  if (argc < 2)
  {
    fprintf(stderr, "usage: %s helix.brep [--write dir]\n", argv[0]);
    return 2;
  }
  const char*  aDir = (argc > 3 && !strcmp(argv[2], "--write")) ? argv[3] : nullptr;
  BRep_Builder aBB;
  TopoDS_Shape aHelix;
  if (!BRepTools::Read(aHelix, argv[1], aBB))
  {
    fprintf(stderr, "cannot read the model\n");
    return 2;
  }
  bool bOK = true;

  // the points found
  const double aPnts[7][3] = {{10.875, -12.661, 17.151},    {12.7236, -7.6476, 12.1118},
                              {12.5155, -12.1097, 29.2421}, {13.2945, -8.6270, 28.0298},
                              {12.7915, -7.0546, 25.2969},  {12.5694, 7.2925, 24.5869},
                              {13.1348, -10.5992, 29.5003}};
  int          aNbIn      = 0;
  for (const double* aP : aPnts)
  {
    BRepClass3d_SolidClassifier aCl(aHelix, gp_Pnt(aP[0], aP[1], aP[2]), 1.e-7);
    aNbIn += aCl.State() == TopAbs_IN ? 1 : 0;
  }
  printf("points: %d of 7 outside the solid said inside (want 0)  %s\n",
         aNbIn,
         aNbIn == 0 ? "PASS" : "FAIL");
  bOK = bOK && aNbIn == 0;

  // a sample in the corners of the box, beyond the cylinder the solid is in
  Bnd_Box aBox;
  BRepBndLib::Add(aHelix, aBox);
  double aX0, aY0, aZ0, aX1, aY1, aZ1;
  aBox.Get(aX0, aY0, aZ0, aX1, aY1, aZ1);
  std::mt19937                           aGen(1);
  std::uniform_real_distribution<double> aUX(aX0, aX1), aUY(aY0, aY1), aUZ(aZ0, aZ1);
  TopoDS_Compound                        aSaid;
  aBB.MakeCompound(aSaid);
  aBB.Add(aSaid, aHelix);
  int       aNb = 0, aNbSaid = 0;
  const int aNbWanted = 6000;
  while (aNb < aNbWanted)
  {
    const gp_Pnt aP(aUX(aGen), aUY(aGen), aUZ(aGen));
    if (aP.X() * aP.X() + aP.Y() * aP.Y() < 14.45 * 14.45)
    {
      continue;
    }
    ++aNb;
    BRepClass3d_SolidClassifier aCl(aHelix, aP, 1.e-7);
    if (aCl.State() == TopAbs_IN)
    {
      ++aNbSaid;
      aBB.Add(aSaid, BRepPrimAPI_MakeSphere(aP, 0.6).Shape());
    }
  }
  printf("sample: %d of %d points beyond r 14.45 said inside (want 0)  %s\n",
         aNbSaid,
         aNb,
         aNbSaid == 0 ? "PASS" : "FAIL");
  bOK = bOK && aNbSaid == 0;

  // the common of a line through the solid with it
  const gp_Pnt       aPL(10.875, -12.661, 17.151);
  const gp_Dir       aDL(-0.047987, 0.971357, -0.232727);
  const TopoDS_Edge  aLine = BRepBuilderAPI_MakeEdge(aPL.Translated(gp_Vec(aDL) * -0.001),
                                                    aPL.Translated(gp_Vec(aDL) * 60.));
  BRepAlgoAPI_Common aCommon(aLine, aHelix);
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
  const bool bLine = aNbEdges == 1 && std::abs(aLen - 6.7904) <= 1.e-3;
  printf("line: its common with the solid %d edge(s), length %.4f (want 1, 6.7904)  %s\n",
         aNbEdges,
         aLen,
         bLine ? "PASS" : "FAIL");
  bOK = bOK && bLine;

  if (aDir)
  {
    BRepTools::Write(aSaid, (std::string(aDir) + "/said_in.brep").c_str());
  }
  return bOK ? 0 : 1;
}
