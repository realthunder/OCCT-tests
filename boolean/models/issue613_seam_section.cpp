// issue613: a cylinder's or a cone's face, a whole turn with its seam a
// little off u = 0, cut by a plane square to its axis: BRepAlgoAPI_Section
// and the pave filler (BOPAlgo_PaveFiller) must give the circle. See
// ../README.md, #613.
//
// The circle the plane cuts starts at u = 0, and the seam's vertex lies on
// it at u = d. For d of 1e-8 and 2e-8 (2 to 4e-7 in space on a radius of
// 21.2, within the vertices' tolerance of the circle's end) no vertex was
// made at the circle's bounds -- the seam's stood for it, at d -- and
// PutClosingPaveOnCurve, which looks for a pave at a bound by its
// parameter, found none: the circle had one pave and no block, and the
// section was empty. In a thick solid of #613's filleted part the top's
// offset cone, its seam 2.1e-8 off, gave the cap no section and the cap was
// kept whole.
//
// Build (macOS, OCCT install prefix O):
//   clang++ -std=c++17 -w -I$O/include/opencascade issue613_seam_section.cpp \
//     -L$O/lib -Wl,-rpath,$O/lib -lTKBO -lTKBool -lTKTopAlgo -lTKBRep -lTKGeomAlgo \
//     -lTKGeomBase -lTKG3d -lTKG2d -lTKMath -lTKernel -o issue613_seam_section
// Run: ./issue613_seam_section [--write <dir>]   (exit 0 when every run passes)
//   --write: each run's face and section, <dir>/<surface>_<d>.brep, a compound
#include <BRepAlgoAPI_Section.hxx>
#include <BRepBuilderAPI_MakeFace.hxx>
#include <BRepTools.hxx>
#include <BRep_Builder.hxx>
#include <GCPnts_AbscissaPoint.hxx>
#include <BRepAdaptor_Curve.hxx>
#include <Geom_ConicalSurface.hxx>
#include <Geom_CylindricalSurface.hxx>
#include <TopExp_Explorer.hxx>
#include <TopoDS.hxx>
#include <TopoDS_Compound.hxx>
#include <TopoDS_Face.hxx>
#include <gp_Pln.hxx>
#include <cmath>
#include <cstdio>
#include <cstring>
#include <string>

int main(int argc, char** argv)
{
    const char* dir = argc > 2 && !strcmp(argv[1], "--write") ? argv[2] : nullptr;
    const double r  = 21.2;
    occ::handle<Geom_Surface> surfaces[2] = {
        new Geom_CylindricalSurface(gp_Ax3(gp_Pnt(0, 0, -5), gp::DZ()), r),
        new Geom_ConicalSurface(gp_Ax3(gp_Pnt(0, 0, -5), gp::DZ()), 0.2, r)};
    const char* names[2] = {"cylinder", "cone"};
    int         bad      = 0;
    for (int k = 0; k < 2; k++) {
        for (double d : {0., 1e-9, 1e-8, 2e-8, 5e-8, 1e-6}) {
            const TopoDS_Face face =
                BRepBuilderAPI_MakeFace(surfaces[k], d, d + 2 * M_PI, 0., 10., 1e-7);
            const TopoDS_Face plane =
                BRepBuilderAPI_MakeFace(gp_Pln(gp::Origin(), gp::DZ()), -50, 50, -50, 50);
            BRepAlgoAPI_Section section(face, plane);
            // the circle the plane cuts, whole: the length of the section's edges
            double length = 0.;
            int    edges  = 0;
            for (TopExp_Explorer x(section.Shape(), TopAbs_EDGE); x.More(); x.Next(), edges++)
                length += GCPnts_AbscissaPoint::Length(BRepAdaptor_Curve(TopoDS::Edge(x.Current())));
            const double expect = k == 0 ? 2 * M_PI * r : 2 * M_PI * (r + 5 * std::tan(0.2));
            const bool   ok     = edges > 0 && std::abs(length - expect) <= 1e-6 * expect;
            printf("%-8s seam at %-6g: %s %d edge(s), length %.6f (want %.6f)\n", names[k], d,
                   ok ? "ok " : "BAD", edges, length, expect);
            bad += !ok;
            if (dir) {
                TopoDS_Compound c;
                BRep_Builder    b;
                b.MakeCompound(c);
                b.Add(c, face);
                b.Add(c, section.Shape());
                char name[64];
                snprintf(name, sizeof(name), "/%s_%g.brep", names[k], d);
                BRepTools::Write(c, (std::string(dir) + name).c_str());
            }
        }
    }
    printf("%d bad\n", bad);
    return bad != 0;
}
