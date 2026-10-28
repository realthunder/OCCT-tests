// issue064: a cylinder (r 25, h 35) split by a plane tilted off its axis,
// with a fuzzy value -- the general fuse (BOPAlgo_Builder, what FreeCAD's
// Split and Fragments run) through OCCT. See ../README.md, #64.
//
// The plane is y = k (z - 34.36): it crosses the cylinder's seam (x = 25,
// y = 0) at z = 34.36, under the top rim, as #64's cut does; the cylinder
// is also turned 90 deg about z, its seam away from the cut. Each run must
// give two solids, valid, and, with the seam away, each within 1% of its
// volume at no fuzzy value. With the seam at the cut, the point where the
// plane crosses the top rim (k 0.64 from the seam's vertex there) is merged
// into that vertex once the fuzzy value nears it (the short section edge
// between them collapsed too): the top's chord starts that far from where
// its arc ends, the gap closed by the vertex's tolerance, and the volume
// integrals read the loop short (up to 1.8% here) -- a valid shape within
// its tolerances, which is what a fuzzy value asks for, so only the two
// valid solids are asked of a fuzzy run with the seam at the cut.
//
// Until OCCT 8.0.1's IntAna_QuadQuadGeo was fixed here, a fuzzy value over
// half the sine of the plane's tilt from the axis (0.05 at k 0.1, 0.17 at
// 0.35, 0.35 at 1) lost the plane/cylinder section: the plane was taken for
// parallel to the axis, the lines given for it missed the cylinder, and the
// fuse came back one solid, uncut.
//
// Build (macOS, OCCT install prefix O):
//   clang++ -std=c++17 -w -I$O/include/opencascade issue064_fuzzy_plane_cylinder.cpp \
//     -L$O/lib -Wl,-rpath,$O/lib -lTKBO -lTKPrim -lTKTopAlgo -lTKBRep -lTKGeomAlgo \
//     -lTKGeomBase -lTKG3d -lTKG2d -lTKMath -lTKernel -o issue064_fuzzy_plane_cylinder
// Run: ./issue064_fuzzy_plane_cylinder [--write <dir>]   (exit 0 when every run passes)
//   --write: each run's solids, a compound, to <dir>/k<k>_seam<deg>_fuzzy<f>.brep
//   (../pictures/make_pictures.sh)
#include <BOPAlgo_Builder.hxx>
#include <BRepTools.hxx>
#include <BRep_Builder.hxx>
#include <TopoDS_Compound.hxx>
#include <cstring>
#include <string>
#include <BRepBuilderAPI_MakeFace.hxx>
#include <BRepBuilderAPI_MakePolygon.hxx>
#include <BRepBuilderAPI_Transform.hxx>
#include <BRepCheck_Analyzer.hxx>
#include <BRepGProp.hxx>
#include <BRepPrimAPI_MakeCylinder.hxx>
#include <GProp_GProps.hxx>
#include <TopExp_Explorer.hxx>
#include <algorithm>
#include <cmath>
#include <cstdio>
#include <vector>

// the solids' volumes, smallest first; empty when the result is invalid.
// With <out>, the solids are written there, a compound
static std::vector<double> split(double k, double fuzzy, double angle, const char* out = nullptr)
{
    gp_Trsf turn;
    turn.SetRotation(gp::OZ(), angle * M_PI / 180.);
    TopoDS_Shape cyl =
        BRepBuilderAPI_Transform(BRepPrimAPI_MakeCylinder(25, 35).Shape(), turn).Shape();
    const double zc = 34.36;
    BRepBuilderAPI_MakePolygon p(gp_Pnt(-40, k * (-5 - zc), -5), gp_Pnt(-40, k * (40 - zc), 40),
                                 gp_Pnt(40, k * (40 - zc), 40), gp_Pnt(40, k * (-5 - zc), -5),
                                 true);
    TopoDS_Shape plane = BRepBuilderAPI_MakeFace(p.Wire(), true).Shape();

    BOPAlgo_Builder b;
    b.AddArgument(cyl);
    b.AddArgument(plane);
    b.SetFuzzyValue(fuzzy);
    b.SetNonDestructive(true);
    b.Perform();
    std::vector<double> v;
    if (b.HasErrors())
        return v;
    if (out) {
        BRep_Builder bb;
        TopoDS_Compound c;
        bb.MakeCompound(c);
        for (TopExp_Explorer x(b.Shape(), TopAbs_SOLID); x.More(); x.Next())
            bb.Add(c, x.Current());
        BRepTools::Write(c, out);
    }
    if (!BRepCheck_Analyzer(b.Shape()).IsValid())
        return v;
    for (TopExp_Explorer x(b.Shape(), TopAbs_SOLID); x.More(); x.Next()) {
        GProp_GProps g;
        BRepGProp::VolumeProperties(x.Current(), g, 1.e-9);
        v.push_back(g.Mass());
    }
    std::sort(v.begin(), v.end());
    return v;
}

int main(int argc, char** argv)
{
    const char* dir = argc > 2 && !strcmp(argv[1], "--write") ? argv[2] : nullptr;
    int bad = 0;
    for (double k : {0.1, 0.35, 1.}) {
        for (double angle : {0., 90.}) {
            const std::vector<double> ref = split(k, 0., angle);
            for (double fuzzy : {0., 0.1, 0.5, 1.}) {
                char name[64];
                snprintf(name, sizeof(name), "/k%g_seam%g_fuzzy%g.brep", k, angle, fuzzy);
                const std::vector<double> v =
                    split(k, fuzzy, angle, dir ? (std::string(dir) + name).c_str() : nullptr);
                bool ok = v.size() == 2 && ref.size() == 2;
                const bool isSnapped = angle == 0. && fuzzy > 0.;
                for (size_t i = 0; ok && !isSnapped && i < 2; i++)
                    ok = std::abs(v[i] - ref[i]) <= 1.e-2 * ref[i];
                printf("k %-4g seam %2g deg  fuzzy %-3g: %s", k, angle, fuzzy,
                       !ok ? "BAD " : isSnapped ? "ok (seam)" : "ok  ");
                if (v.empty())
                    printf(" invalid\n");
                else {
                    for (double x : v)
                        printf(" %.4f", x);
                    printf("\n");
                }
                bad += !ok;
            }
        }
    }
    printf("%d bad\n", bad);
    return bad != 0;
}
