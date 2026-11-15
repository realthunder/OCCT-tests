// issue617_grazing_classify: points outside the prisms of #617's tilted torus
// said inside them.
// See ../README.md, "A line that grazes a face".
//
// The shape is the two prisms padded from the cut of a tilted torus
// (issue617_tilttorus_pad_back.brep: two solids, valid), their walls
// extrusions of closed B-spline curves. BRepClass3d_SolidClassifier casts a
// line from the point to a point of a face and takes the first crossing;
// IntCurvesFace_Intersector finds the crossings on a polyhedron of the face
// and then exactly. A line that passes through a bulge of a curved wall
// crosses it twice, close by -- at 6.356 and 6.588 for a point at
// (24.190, 31.107, -26.782) of the other prism's file, 0.4 degrees off the
// wall's tangent plane; at 4.695 and 6.310 for another, 2.9 degrees off --
// and the intersector, whose polyhedron the line may cross once or not at
// all there, returned the second crossing alone, going out: the point was
// said inside. The classifier does not believe alone a line whose first
// crossing is within 0.1 of the face's tangent plane (the cosine with the
// normal): the next line that does not graze has to agree with it, or a
// third decides between the two.
//
// Checked here: eight such points are outside; of 30000 points sampled in
// the shape's box, none is said on the side that eight of nine lines from
// it deny (6 before).
//
// Build (OCCT install prefix O; on Linux add -Wl,--enable-new-dtags so that
// LD_LIBRARY_PATH can put another library first):
//   c++ -std=c++17 -w -I$O/include/opencascade issue617_grazing_classify.cpp \
//     -L$O/lib -Wl,-rpath,$O/lib -lTKBO -lTKPrim -lTKTopAlgo -lTKBRep \
//     -lTKGeomAlgo -lTKGeomBase -lTKG3d -lTKG2d -lTKMath -lTKernel \
//     -o issue617_grazing_classify
// Run: ./issue617_grazing_classify <issue617_tilttorus_pad_back.brep> [--write <dir>]
//   (exit 0 when every check passes)
//   --write: <dir>/said_wrong.brep, the shape with a ball at each of the
//   eight points and each sampled point said on the wrong side
#include <BRepBndLib.hxx>
#include <Bnd_Box.hxx>
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
    fprintf(stderr, "usage: %s issue617_tilttorus_pad_back.brep [--write dir]\n", argv[0]);
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

  // the points found, all outside
  const double aPnts[8][3] = {{-64.417922, 5.393937, -38.464740},
                              {-56.791860, 30.220370, -23.466659},
                              {-18.876547, 31.332908, -27.669281},
                              {-16.536926, 31.875933, -29.833540},
                              {-16.616102, 31.442742, -28.171500},
                              {1.275644, 5.484870, -35.884340},
                              {-19.710294, 29.986907, -22.564094},
                              {-35.809750, 31.107302, -26.782223}};
  TopoDS_Compound aSaid;
  aBB.MakeCompound(aSaid);
  aBB.Add(aSaid, aSolid);
  int aNbWrong = 0;
  for (const double* aP : aPnts)
  {
    BRepClass3d_SolidClassifier aCl(aSolid, gp_Pnt(aP[0], aP[1], aP[2]), 1.e-7);
    if (aCl.State() != TopAbs_OUT)
    {
      ++aNbWrong;
      aBB.Add(aSaid, BRepPrimAPI_MakeSphere(gp_Pnt(aP[0], aP[1], aP[2]), 0.9).Shape());
    }
  }
  printf("points: %d of 8 outside the solids said inside (want 0)  %s\n",
         aNbWrong,
         aNbWrong == 0 ? "PASS" : "FAIL");
  bOK = bOK && aNbWrong == 0;

  // a sample in the shape's box, grown by a tenth; each point's side counted
  // along nine lines as well
  NCollection_IndexedMap<TopoDS_Shape, TopTools_ShapeMapHasher> aFaces;
  TopExp::MapShapes(aSolid, TopAbs_FACE, aFaces);
  std::vector<std::unique_ptr<IntCurvesFace_Intersector>> anInter;
  for (int i = 1; i <= aFaces.Extent(); i++)
  {
    anInter.emplace_back(new IntCurvesFace_Intersector(TopoDS::Face(aFaces(i)), 1.e-7));
  }
  Bnd_Box aBox;
  BRepBndLib::Add(aSolid, aBox);
  double aX0, aY0, aZ0, aX1, aY1, aZ1;
  aBox.Get(aX0, aY0, aZ0, aX1, aY1, aZ1);
  const double                           aGX = 0.1 * (aX1 - aX0), aGY = 0.1 * (aY1 - aY0),
                                         aGZ = 0.1 * (aZ1 - aZ0);
  std::mt19937                           aGen(5);
  std::uniform_real_distribution<double> aUX(aX0 - aGX, aX1 + aGX), aUY(aY0 - aGY, aY1 + aGY),
    aUZ(aZ0 - aGZ, aZ1 + aGZ);
  std::normal_distribution<double> aN(0., 1.);
  const int                        aNb     = 30000;
  int                              aNbSaid = 0;
  BRepClass3d_SolidClassifier      aCl(aSolid);
  for (int i = 0; i < aNb; i++)
  {
    const gp_Pnt aP(aUX(aGen), aUY(aGen), aUZ(aGen));
    aCl.Perform(aP, 1.e-7);
    if (aCl.State() != TopAbs_OUT && aCl.State() != TopAbs_IN)
    {
      continue;
    }
    int aNbIn = 0;
    for (int k = 0; k < 9; k++)
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
    if (aCl.State() == TopAbs_OUT ? aNbIn >= 8 : aNbIn <= 1)
    {
      ++aNbSaid;
      aBB.Add(aSaid, BRepPrimAPI_MakeSphere(aP, 0.9).Shape());
    }
  }
  printf("sample: %d of %d points in the box said on the wrong side (want 0)  %s\n",
         aNbSaid,
         aNb,
         aNbSaid == 0 ? "PASS" : "FAIL");
  bOK = bOK && aNbSaid == 0;

  if (aDir)
  {
    BRepTools::Write(aSaid, (std::string(aDir) + "/said_wrong.brep").c_str());
  }
  return bOK ? 0 : 1;
}
