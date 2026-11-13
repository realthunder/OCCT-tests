// issue613_roof_flat: #613's part (issue613_fillet.brep) with one flat of its
// roof removed, a thickness of it inward and outward (the Arc join). See
// ../README.md, "#613: a flat of the roof removed" (sec 70).
//
// Every edge of a flat is tangent to the face beside it -- the blend down to
// the cone, a B-spline, and the blend up to the ridge, a cylinder -- so the
// wall is closed by a tube round each edge, from the neighbour's offset to
// the rim left of the flat (BRepOffset_MakeOffset::ToContext).
//
// Face 15: its blend to the cone is in two halves (faces 2 and 6), so the
// flat's edge along it is two edges, one going on from the other in the same
// direction. Their tubes end in the same quarter circle there, and each had
// one of its own: tangent to each other, nothing cut one by the other, the
// shell stayed open along the two arcs, every face of the offset hung from
// there and was dropped, and the thickness was refused -- at any value,
// either way. The second tube now takes the first one's arc
// (ShareTubeEnds in BRepOffset_MakeOffset.cxx).
//
// Face 21, the mirror image, its blend (face 12) in one: outward at 1 it was
// made; inward, and at 0.5 either way, refused. The two tubes of the flat
// touch at each corner, and their section, on one of them, runs straight to
// its end while its derivative at the end parameter itself points 48 deg
// off, to the other side of the tube's own edge. The loop takes each edge's
// direction at a vertex from that derivative; it now takes the chord to a
// point a thousandth of the way along where the two differ by more than
// 0.05 rad (DartAngle in BRepAlgo_Loop.cxx).
//
// The two flats give the same volume to 2e-6 (the blend is modelled twice).
// Away from the removed flat each result is the points outside (inside) the
// part within the thickness of it: 1500 points at random, none wrong.
//
// Build (OCCT install prefix O):
//   c++ -std=c++17 -w -I$O/include/opencascade issue613_roof_flat.cpp \
//     -L$O/lib -Wl,-rpath,$O/lib -lTKOffset -lTKBO -lTKPrim -lTKTopAlgo -lTKBRep \
//     -lTKGeomAlgo -lTKGeomBase -lTKG3d -lTKG2d -lTKMath -lTKernel -o issue613_roof_flat
// Run: ./issue613_roof_flat issue613_fillet.brep 15|21 [--write <dir>]
//   (exit 0 when every run passes)
//   --write: each result, <dir>/f<face>_in<d>.brep or _out<d>.brep (none
//   when it is refused)
#include <BRepCheck_Analyzer.hxx>
#include <BRepGProp.hxx>
#include <BRepOffsetAPI_MakeThickSolid.hxx>
#include <BRepTools.hxx>
#include <BRep_Builder.hxx>
#include <GProp_GProps.hxx>
#include <Standard_Failure.hxx>
#include <TopExp.hxx>
#include <TopExp_Explorer.hxx>
#include <TopTools_IndexedMapOfShape.hxx>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>

int main(int argc, char** argv)
{
    if (argc < 3) {
        printf("usage: %s issue613_fillet.brep 15|21 [--write <dir>]\n", argv[0]);
        return 2;
    }
    const int    face = atoi(argv[2]);
    const char*  dir  = argc > 4 && !strcmp(argv[3], "--write") ? argv[4] : nullptr;
    TopoDS_Shape s;
    BRep_Builder b;
    if (!BRepTools::Read(s, argv[1], b) || (face != 15 && face != 21)) {
        printf("cannot read %s, or the face is neither 15 nor 21\n", argv[1]);
        return 2;
    }
    TopTools_IndexedMapOfShape faces;
    TopExp::MapShapes(s, TopAbs_FACE, faces);
    int bad = 0;
    // the volumes: face 15's, face 21's
    struct Run {
        double offset, want15, want21;
    } runs[] = {{0.25, 1617.8851, 1617.8873},   {0.5, 3286.0136, 3286.0189},
                {1., 6773.6378, 6773.6496},     {2., 14358.7727, 14358.8004},
                {-0.25, 1575.4511, 1575.4539},  {-0.5, 3116.4126, 3116.4171},
                {-1., 6096.2692, 6096.2767},    {-2., 11657.5021, 11657.5105}};
    for (const Run& r : runs) {
        const double want = face == 15 ? r.want15 : r.want21;
        std::string  what;
        bool         ok = false;
        TopoDS_Shape result;
        try {
            NCollection_List<TopoDS_Shape> removed;
            removed.Append(faces(face));
            BRepOffsetAPI_MakeThickSolid m;
            m.MakeThickSolidByJoin(s, removed, r.offset, 1e-7, BRepOffset_Skin, false, false,
                                   GeomAbs_Arc);
            if (!m.IsDone()) {
                what = "refused";
            } else {
                result = m.Shape();
                GProp_GProps g;
                BRepGProp::VolumeProperties(result, g);
                const bool valid  = BRepCheck_Analyzer(result).IsValid();
                int        solids = 0;
                for (TopExp_Explorer x(result, TopAbs_SOLID); x.More(); x.Next()) {
                    solids++;
                }
                char buf[160];
                snprintf(buf, sizeof(buf), "%s, %d solid(s), volume %.4f (want %.4f)",
                         valid ? "valid" : "invalid", solids, g.Mass(), want);
                what = buf;
                ok   = valid && solids == 1 && std::abs(g.Mass() - want) <= 1e-5 * want;
            }
        } catch (Standard_Failure& e) {
            what = std::string("threw ") + e.what();
        }
        printf("face %d %g %s %s\n", face, r.offset, ok ? "ok " : "BAD", what.c_str());
        bad += !ok;
        if (dir && !result.IsNull()) {
            char name[64];
            snprintf(name, sizeof(name), r.offset < 0 ? "/f%d_in%g.brep" : "/f%d_out%g.brep", face,
                     std::abs(r.offset));
            BRepTools::Write(result, (std::string(dir) + name).c_str());
        }
    }
    printf("%d bad\n", bad);
    return bad != 0;
}
