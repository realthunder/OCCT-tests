#!/usr/bin/env python3
"""mkpage.py OUTDIR -- the "Thickness Before and After" page from the pictures.

Writes OUTDIR/index.html and copies every picture of models/pictures that
cases.py names into OUTDIR/img/. One section per fix of models/Thickness.md
that has pictures, oldest first, its title taken from the "### Sec N: ..."
heading and its summary from SUMMARY below. With THICK_WORK set (the
make_pictures.sh work directory) the counts of what upstream gets right come
from its results; otherwise they are left out.

Run it after every picture run, then publish OUTDIR (index.html plus img/).

env: SUITE  the suite's standing, e.g. "277 passing, 8 marked known broken"
     SWEEP  the sweep's, e.g. "928 of 928"
"""
import html, json, os, re, shutil, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import cases  # noqa: E402

DOC = os.path.join(HERE, "..", "models", "Thickness.md")
PICS = os.path.join(HERE, "..", "models", "pictures")

# One or two sentences per section: what was wrong and what the fix does.
SUMMARY = {
    2: "Upstream gets every case here right; the fork had broken all of them. Four causes in the loop and the context extension: a closed edge found twice on a periodic face (the floor went missing), one seam wire allowed per face (the second wall built from two bare circles), a const edge losing its orientation, and the offset of an ellipse stretched 100 lengths past its ends.",
    3: "Outward with the Arc join past a concave corner, the corner piece of an arc face came out as a face of its own. Plus a neighbour skipped before its edge was renewed, and a stretched edge lying on another (the T's bar top).",
    4: "The stretched removed face's crossing taken for an edge's own end (T bar top inward); an edge two faces share trimmed twice (the fork threw where upstream is right); a wire running once round a periodic face (a face of no area on the holed cone).",
    5: "Upstream fails all of these. Thick solids that came back inside out (drawn black) are now oriented by classification; a blind floor's section was the wrong way round; concave removed faces with intersection on are built as with it off.",
    6: "A box with filleted vertical edges, an end or side face removed: the fillets' offsets never meet the removed face (unhollowed) or meet it far round (a lip). A tube round the tangent edge closes the gap, with sphere eighths at the corners outward.",
    8: "The removed face is curved. Outward it threw, inward it came back valid but larger than the input. The tubes are built on the fillet's cylinder, the loop walks its angles as on a chart, and a hanging piece of the floor's offset is dropped. The cut is in plan.",
    9: "That join builds no tubes. The gap is closed by their sharp counterpart: a strip of the neighbour's tangent plane a thickness into the removed face, and a wall square to it; cubes at the corners.",
    10: "The holed cone's top removed inward: the cavity closes below the removed face, and the right result is a skin and a sealed void, two shells.",
    11: "Removing a face can leave the kept faces in separate pieces: each piece is thickened on its own and the result is a compound. A short box or cylinder taken down to one face is answered too.",
    12: "The same pieces with the Intersection join: a seam edge given once to the loop left the whole cap; one face left beside the removed ones threw.",
    13: "A top face with a pocket or blind hole removed leaves the pocket's wall and floor as a piece of its own; the fork built it wrong even as an open shell, where upstream is right.",
    14: "The thickness was right and left its input inside out: a test face was healed on the input's own edges. The panels show the input after the call.",
    15: "With every face removed no face stays to be thickened: refused. A sphere used to come back as itself, valid and unhollowed. The panels show the input.",
    16: "A dome, a bowl, a cap, a cone with its apex: the seam band's far edge can be the pole's degenerated edge. Upstream is right on these; the fork had been wrong since the chain was ported.",
    17: "An edge re-trimmed at an offset cone's apex had an infinite range; half a dome threw rebinding a border vertex. A result that is the input itself is refused.",
    18: "Half a dome's mirror side; the Intersection join on faces in coplanar pieces (a box fused of two); the closing wall on a sphere; and the offset sphere grown round its pole by turning the sphere's axis off the face.",
    19: "Three quarters of a dome (the axis turn stopped at half a turn; the old pole's edge kept two meridians apart; a meridian's piece past the pole kept a pcurve off the sphere); the piece of sphere where three tubes meet at a pole; a face extended to the far crossing; and the sphere itself removed, its wall built on a turned twin of the removed face. At twice the thickness one case had been a valid solid on the wrong side.",
    20: "Half a ball cut through both its poles: its sphere is cut in two first, along the equator where it stays and along a meridian where it is removed. And shapes under a location or turned in space, which gave other results than plain: a seam checked without its location, a cone's apex left where it was, a corner arc taken from the wrong section, a whole circle of section that lost the piece its own vertex lies in.",
    21: "A dome whose rim is in two arcs was broken since the chain was ported, upstream right: the face is now walked in (u, v) with its seam, and its flat's two arcs no longer both become one half circle. The half ball with one disc, as a refine or a cut leaves it, is put on a sphere turned onto its middle, which makes it that dome; and a half ball with its sphere in two faces has them joined first.",
    22: "A ball wedge's sphere removed outward is the rest of the ball's thick solid inward. A sphere face whose outline lies on the meridians of another axis is put on that axis: the dome with its flat in two halves, a ball wedge made on an axis through its face. And an edge cut in two by a vertex nothing else meets is joined first: since the chain was ported it broke the faces beside it, 361 runs of 824, a box among them where upstream is right.",
    23: "The half ball with its sphere in two domes or two lunes, one removed: the removed face lies on the kept face's own sphere, whose offset never meets it. With the Intersection join the kept face runs on round the sphere a thickness into the removed one, to a wall square to the sphere: a cone from its centre. On the way, a cone with its apex at a sphere's centre met it in B-splines, or not at all, as the sphere happened to be turned or placed. The Arc join is still refused.",
    24: "A seam in pieces, joined, came back with a parameter from 0, and stretched below its start its crossings fell at negative parameters, where the loop's periodic wrap never looked: a trimmed circle says it is not periodic. The wrap takes its basis's period, and a joined seam is put back on its surface's iso line. That is the root of sec 21's seam from 2 pi. And sec 23's crossings on a sphere no longer cross edges stretched over a pole.",
    25: "The Arc join for the same half ball: a tube round the tangent edge and, outward, a ball round each of its ends. The flat's offset is cut by the removed face's sphere on one side and bounded by its own rim's offset on the other, two circles about one centre a hair apart that never meet, and the face was left without a wire. A step joins them, an edge of the ball. The exact answer has a sliver face beside the step, 0.025 by 0.0006; it is not built.",
    26: "The two the vertex survey left. Half a ball cut from a ball by a box keeps the ball's seam for half its rim, both pcurves still on it: with a vertex there the pieces were taken for a seam's, not joined, and the sphere not turned onto its middle. And the half ball in two lunes, one removed, was right or wrong by the order its faces came in: the flat's half beside the removed lune closed the arc that bounds the other half with the line between them, the other half's face a second time. An offset face does not reach across its tangent edge.",
    28: "Two adjacent top fillets of a box, the bottom removed, the Intersection join: the fillets' offsets meet on an ellipse that the filler cut at its origin, and at three corners of the four that origin is where the section crosses the fillet's tangent line with the wall. The run-on beyond it was an edge of its own outside the faces, walked out and back by the loops. Two pieces of one periodic section curve that meet only at its origin are one edge again.",
    29: "The same box with all four top edges filleted: the top's offset, every edge of it tangent, met no section and was never extended, so it kept the edges it was made with while its neighbours were rebuilt with new ones along the same lines, and the shell held each of its edges once. A face beside an extended one across a tangent edge is extended and rebuilt with it.",
    30: "A box under a B-spline dome, its four edges filleted, the bottom removed, inward with the Intersection join: refused. The offsets of the tangent edges between its walls and fillets, B-splines, were given a range past the ends of their curves, where a B-spline does not go, and came out under a tolerance of 1.87; and at each corner of the top the end of one offset edge was stored on the next without a parameter on it, and the loops threw. Such an edge goes no further than its curve now, and the vertex keeps the parameter it was projected to.",
    31: "The same dome outward with the Intersection join, 1 and 2: refused. Its wall-to-fillet edges have to go on past their B-spline curves to meet the next wall, and a vertex where two prolonged edges cross took their whole tolerance, where their surfaces part; at the top corners three faces share one normal and the offset edges miss each other by 1.5e-3. The edges are made again from their pcurves, the vertices get their tolerance where they lie, the corners a vertex of their own. They first came at the fork's fix level 1 only, since they move a shape the suite had in its last place; measured, that move lies within the shape's tolerance, so they are made at every level (sec 32). The edges' other pcurves are made again from the new curves since, and they reach their corners: the widest tolerance at 2 is 0.0024, from 0.0116 (sec 33).",
    34: "The same dome with the dome itself removed, inward, the Arc join: refused, the input itself. The dome meets its fillets tangentially, so tubes round its edges close the wall, and none was built: the edges, 2e-6 rad off tangent, were tested to 1e-12; a tube's edge on the dome got no pcurve and ended short of the dome's corner; and where two tubes meet at a corner their section missed both the edge and the vertex it should end on, by 7e-6 and up to 1e-3. Each is answered, the section's ends taken within the edges' tolerances.",
    35: "The same outward, 0.5 to 4: refused. Two tubes touch at each corner, their section tangent at its end to the one's end and the other's edge. A corner sphere built where the tubes meet each other, a section line of no length, a cut edge's first vertex put after one at its own parameter, a pcurve's end tangent 4 to 6 deg the wrong side of the tube's (the loop walked two faces as one), and a vertex replaced on some faces only: five faults, each mended. An offset with none of the faces built round the removed ones that does not close is now refused, so 3 inward stays refused rather than coming back invalid.",
    36: "#363's grooved cylinder with the groove one face whose own seam lies on its edge with one bottom, the other bottom removed: valid and wrong (the issue's own base inside out). The side's offset, walked in (u, v), kept a wire under the groove's offset and the kept bottom's because it ran through the seam, and a wire through the seam was spared the rule that drops a wire running past an edge's span. On a face walked in (u, v) the seam is a border like any other, and the wire goes; the solid is the one the groove in two faces gives.",
    37: "The Intersection join on a cylinder with a step cut off its side, any face but the side removed, in or out: refused, or valid and wrong, upstream too. The side meets the step's wall at both ends of the step, and their offsets were intersected once, for the first edge, both edges then taking that one line; a removed wall had no section at the second edge at all. And the side's section with the bottom, a whole circle, closed a piece of the side's offset and of the bottom's under the step besides their own. Each shared edge now takes the pieces nearest it, and pieces off their face (a removed face's: away from the thickness) are dropped. All eight come out at the exact volumes.",
    38: "#521: a box with a three-quarter cylinder on its corner edge, -0.5, the Intersection join, the top removed: refused (upstream: valid and wrong). The cylinder's offset was extended a tenth of the quarter it leaves free and did not reach the walls' offsets, 19.5 degrees past its ends; a face of more than half a turn is now taken 0.45 round. And the wall at the end of the cylinder's seam removed was invalid with either join: the cylinder is left-handed, its face reversed, and rebuilt with its seam edge cut, the edge took its other pcurve and the face became the quarter inside the box. The Intersection join's results come out at the exact volumes.",
    39: "The Arc join on the cylinder with a step cut off its side, the step's ceiling removed: refused inward, inside out outward; upstream invalid inward and unhollowed outward. The ceiling's edge with the side is an arc of 137 degrees; its offset was stretched into a whole circle before the ceiling was cut by its neighbours' offsets, and the circle cut the side's offset all the way round. An arc of less than half a turn is now stretched short of closing.",
    40: "#346: an offset inward of a shell of revolution whose dome comes down to its axis, a dimple: the offset's meridians fall short of the axis inward, and a trim looked for their crossing past the end of the surface, a throw. The gap is left open for the sphere round the apex now, as it is outward, the sphere reversed inward. Where the apex is crossed instead -- a peak inward, the dimple on a solid -- the seam trimmed at the apex had no range on the face, and the result was invalid; it has the trim's range now.",
    41: "#613 outward: the ridge's top cap is cut by its neighbours' offsets enlarged, and the cone's, enlarged to a whole turn, started 2.1e-8 off its seam, where the circle the cap's plane cuts from it starts. No section edge came of it, the cone's offset top stayed above the plane and a face collapsed: inside out. Such a turn starts at its seam now. An outward result back at the input's own bounds is refused as unhollowed, not passed as a thick solid.",
    42: "#363's groove across a cylinder's end, both bottoms removed, with the Intersection join: each bottom's cut by the side's offset was the whole circle, the two lay on each other on the side and the thickness was refused. The circle is shared out between the bottoms, as the Arc join already did.",
    43: "#346 with the Intersection join: at the dome's dimple the offset was trimmed inward and extended outward, the wrong way round -- a throw, and a dome folded over its axis. The apex is left open for the sphere with either join now, as the Arc join does, its circle bounding the face as a closed edge. The enlarged dome's offset is unstable at its pole, and the result went invalid written and read back: BRep text keeps 17 digits of the topology now, not 15.",
    44: "The same apex made otherwise, the Intersection join: the dome's offset is a B-spline closed and not periodic, and the loop builder walked its face by angle, a seam's two sides taken for one -- the face open in (u, v), or nowhere. A seam across a face now gets the periodic search. And where a peak's offset is carried on to the axis, the approximation ended round a loop 1.3e-3 across, taken for an open apex: its end poles are the apex now.",
    45: "#521 with the cylinder removed, inward: the removed three-quarter cylinder, the stop of its neighbours' offsets, went too little of the way round and met them on the far side; its edge at 2 pi, closed on it, made its lips a periodic search; the Intersection join's 2D intersection read that edge a period off. Both joins now give the hand value.",
    46: "#363's Thickness001 and the slotted cylinder with the Intersection join, offset whole or one face removed: the side's loop with the groove, split at the groove's seam, was cut on neither piece; the right bottom's section with the side, the whole circle, was kept whole; with the top removed the chamfer's piece, only in part on its offset, was dropped; the slot's ceiling removed, its section with the side shared out to no arc. Every volume made is the hand value.",
    47: "The groove of two faces, as FreeCAD makes it, with the Intersection join: each quarter's loop with the side split where the quarters meet, its own piece crossed once and never trimmed, the other run on over the other quarter. The own piece is trimmed to the end they share and the other dropped; every volume made is the hand value.",
    48: "The slotted cylinder's left wall removed inward, the Intersection join: the side's offset came in two pieces, the second holding the lip's edges, and only the first took the lip's cuts -- refused, its mirror made. Every piece is rebuilt now; the volume is the hand value.",
    49: "The groove of two faces with both bottoms removed, the Intersection join: each bottom's section with the side's offset is the circle split at the side's seam, the halves on one curve, and the seam's vertex carried the first half's parameter, 2 pi -- the second half was trimmed the long way round, over the first. A parameter a period outside an edge's range is brought into it now; every volume is the hand value.",
    50: "#521 with the cylinder removed, outward: the cylinder's edge at 2 pi, closed on it and the input's own, is used by it once, reaching one pcurve; taken for a seam of the lips, they came out inside out with both joins. An edge of the face itself that the face reaches by one pcurve only is no seam of it now; both joins give the hand value.",
    51: "The box with #363's groove of two quarter cylinders, the left quarter removed, outward: invalid, both joins (the right one made in sec 50). The edge where the quarters meet is closed on the cylinder, each quarter reaching one of its pcurves; the left offset face is reversed, and the walk by angle took the edge's pcurve at 0 where the face lies by 2 pi. The strip the kept quarter's offset carries into the removed one came out of negative area and the face beyond it took it in, one face. The walk takes the pcurve the face reaches now; both quarters give the tangent caps' value by hand. A face built further round a period than its wires is dropped, so the same quarter on the grooved cylinder, still open, stays refused.",
    52: "The grooved cylinder with a quarter of its groove removed, the Intersection join: refused both ways. The tangent caps' strip ends on the cylinder's side, and its end edges, lines, have no pcurve there: they were given no type, and nothing intersected the strip with the side. Typed, the strip grown across the shape met the side's offset in one circle, all of it the first end's. The ends are typed as the wall's are now, and the strip is held in its band; every volume is the tangent caps' hand value, both quarters, inward and outward.",
    53: "The grooved cylinder with a quarter of its groove removed, outward, the Arc join: refused. The side's offset rebuilt beside the removed quarter and the tube round its edge with the kept quarter held that edge in two copies; and the tube round the crown, square-ended at the crown's ends with an eighth of a ball, has its edge on the removed quarter crossing the quarter's curved edge with the side 0.019 short of its end, where the cap's loop had no vertex and closed the opening over. The tube takes the face's pieces, and the crossing is cut; every volume is the boolean value of sec 6's design.",
    54: "The step (and the slot) cut off the cylinder's end, its side removed, the Intersection join: refused, in and out. The bottom's offset meets the side in a whole circle, given to the bottom's two arcs as one compound and looked for on the side's enlarged copy, where it is not: its corner with the wall's section was never intersected. Found on the side now; and outward the circle, which starts at the seam, is trimmed to the arc its edges lie on, not the one under the step.",
    55: "#363's grooved cylinders, their side removed, the Intersection join: refused. Each groove quarter's offset is the other's surface; its section with the side, split where the quarters meet, runs on over the other's, and was never trimmed: that was done only for an edge between two kept faces. Trimmed now where the quarter runs on, tangent, into the other; and ordering a section found nowhere on the side no longer throws.",
    56: "#346's shell, its cone removed, the Arc join: refused, the sphere's dome valid and wrong. The dome's rim, a whole circle, takes its section with the cone by orientation alone, and the section came the wrong way round: the rim ran the same way as the apex's edge, the face could not be oriented, and healing it gave edges of tolerance 1.5e3. The section runs as the rim it replaces now; inwards every volume is the boolean value to the digit.",
    57: "From the fork's offset fix level 2: a surface of revolution is stretched past its outline on its own meridian, not by a B-spline continuation that left the circle. #346's rim corner moved 5.4e-4 to its exact place, and every run it touches is now the exact value (6198.0920 here, from 6198.1628; offset areas up to 2.58 off before). The change is in the last digits, so both columns look alike at this scale.",
    58: "#346's peaked shells, the cone removed, inward with the Intersection join: refused, or inside out. The dome's offset is cut where its meridian crosses the axis, short of its basis's apex, and was stretched past the apex: the meridian turned back up across the axis and the face was never trimmed. A revolution is not stretched past an end on its axis now; every volume is the boolean one.",
    59: "#346's shell with its dome removed, inward: the cone's offset never met the dome and was dropped, and the shell itself came back as an invalid solid; it is refused now, as outward and as any open shell whose free edge no removed face covers. And from the fork's offset fix level 3, outward at a dimple the dome's offset is trimmed where its meridians cross the axis, not cut short and capped by a small sphere that crossed it (a face BOP's own check refuses); level 2's stretch reaches below a circle's origin; a peak's offset is carried to the axis on its own circle with the Intersection join. Every volume and area is the boolean one to the digit. The apex change is 1e-3 across, so both columns of the dimple look alike at this scale.",
    60: "#360's plate, square holes 4.3 apart and 2.5 from its outline, the top removed 4 inward: refused, as every plate whose holes are nearer each other or the outline than twice the thickness. There the offsets of a wall's two sides pass each other and the strip between is no pocket, which the edges' orientations say and the loops never read. A thick solid with no valid answer is made once more with the wires of planar faces taken by the way their edges run; that answer is kept only where it is valid and crosses itself nowhere.",
    61: "Four square holes in a square, the walls between them thinner than twice the thickness both ways, and #360's plate 2 inward: both refused, by two faults in sec 60's second way. The rounded corners between walls are cylinders, which it left to the search, and a corner handed its wall the wrong piece of the edge they share; and the point that tells whether a region lies within the removed face was taken off a chord, which beside a rounded corner lies on the arc's other side. Cylinders taken less than a turn round are read by regions too, and the point is taken off the edge itself.",
    62: "Round holes nearer each other, or the outline, than twice the thickness: invalid, where upstream is right. A round hole's wall is a whole cylinder with its seam, which sec 60's second way did not read. It does now: a region runs on across the seam, and where the face lies along the seam it is parted there. And a cut point given a whole turn off its edge's range, on a circle two sections share, is brought onto the edge. Ten plates with round holes, each to upstream's volume to the digit.",
    63: "#360's plate 5 inward, half its thickness: refused. Where a hole corner's offset meets the removed top it leaves an arc, which the corner's own face took whole and the top's rim cut in two. The record of what the arc became then held the arc and both pieces, the corner took all three, and with its top edge twice over the whole offset came apart. The pieces now take the place of the edge whole. Mended, that let through a result it had held back by accident: a cylinder with a slot, the slot's ceiling removed outward, a closed shell of negative volume (upstream gives the input back, invalid). A thick solid of negative volume, with a face removed, is now refused, and the second way makes the right one. Upstream makes the plate, to the same volume. The figure is sec 64's: the search that gave up on this plate after two minutes and 5 GB is no longer begun where it will run out of steps, and edges far apart are no longer measured against each other; the plate takes 5 s, not 146, and no result changes. The second figure is sec 65's: #613's model with its side removed, refused as upstream refuses it, took 20 to 80 s to be; it takes 3 to 7 now (a check of walls that measured faces far apart, and a projection that sought its start before its curve's own and was then fitted again and again to no gain). The third is sec 67's: the plate's thickness had the right faces and volume but 204 edges too many, each left in the pieces a discarded wall's offset had cut it in; they are joined now, and the result has upstream's 438 edges.",
    66: "A groove cut in the bottom of a cylinder by another cylinder, the groove's wall removed, outward (#363's Thickness002): invalid, where the same solid as the issue's file stores it is made. The wall is half the cutting cylinder and one of its straight edges lies on that cylinder's seam, kept with both of a seam's pcurves. The rim outward is a ring round the wall with the wall's outline as its hole; the hole runs that edge the other way round, which is its other pcurve, a period away from the rest, so the ring was taken for a face running round the cylinder and dropped, and the whole wall's surface stayed in the offset. The ring is now cut in two along the seam's line. Upstream throws, or gives the input back.",
}

# Pictures of a section made by make_fix_pictures.sh (a C++ driver of the fix,
# before and after) rather than from cases of the suite: shown after the
# section's cases.
FIXPICS = {
    40: ["issue346_revolve", "issue346_crossed"],
    63: ["issue360_plate_search_time", "issue613_side_refusal_time",
         "issue360_plate_edge_pieces"],
}

TAGLINE = "Every pictured case of the OCCT fork's thickness suite, each run three ways"


def sections():
    """{number: title} from the write-up's headings."""
    out = {}
    for line in open(DOC, encoding="utf-8"):
        m = re.match(r"### Sec (\d+): (.*)", line)
        if m:
            t = m.group(2).strip()
            out[int(m.group(1))] = t[:1].upper() + t[1:]
    return out


def png_size(path):
    with open(path, "rb") as f:
        head = f.read(24)
    return struct.unpack(">II", head[16:24])


def main(out):
    titles = sections()
    work = os.environ.get("THICK_WORK")
    up = None
    if work and os.path.exists(os.path.join(work, "r", "up", "results.json")):
        up = json.load(open(os.path.join(work, "r", "up", "results.json")))
    # section -> [(stage, [case, ...]), ...] in the order the stages are listed
    by_sec = {}
    for st, (commit, sec) in cases.STAGES.items():
        names = [n for n, c in cases.CASES.items() if c[0] == st]
        if names:
            by_sec.setdefault(int(sec), []).append((st, commit, names))
    order = sorted(by_sec)
    os.makedirs(os.path.join(out, "img"), exist_ok=True)

    total = len(cases.CASES)
    up_right = sum(1 for n in cases.CASES if up and up.get(n, {}).get("ok"))
    newest = order[-1]
    intro = "%s: %d cases across %d fixes, the newest last (sec %d)." % (TAGLINE, total, len(order), newest)
    if up:
        intro += " Upstream gets %d of them right (the fix chain's own regressions) and fails %d." % (
            up_right, total - up_right)
    if os.environ.get("SUITE"):
        intro += " The suite stands at %s." % os.environ["SUITE"]
    if os.environ.get("SWEEP"):
        intro += " The sweep: %s." % os.environ["SWEEP"]
    intro += (" Section numbers are those of the write-up, which lives in the fork with the pictures:"
              " <code>tests/fork/thickness/models/Thickness.md</code> and <code>models/pictures/</code>.")

    e = html.escape
    parts = []
    for sec in order:
        figs, metas = [], []
        for st, commit, names in by_sec[sec]:
            ok = sum(1 for n in names if up and up.get(n, {}).get("ok"))
            meta = "Before = fork at <code>%s</code> &middot; %d case%s" % (
                e(commit), len(names), "" if len(names) == 1 else "s")
            if up:
                meta += ", upstream right on %d" % ok
            meta += ": " + " ".join('<a href="#%s">%s</a>' % (e(n), e(n)) for n in names)
            metas.append('<p class="meta">%s</p>' % meta)
            for n in names:
                src = os.path.join(PICS, n + ".png")
                shutil.copyfile(src, os.path.join(out, "img", n + ".png"))
                w, h = png_size(src)
                figs.append(
                    '<figure id="%s"><img src="img/%s.png" alt="%s: the shape given, upstream, fork before, fork after"'
                    ' loading="lazy" width="%d" height="%d"><figcaption><code>%s</code></figcaption></figure>'
                    % (e(n), e(n), e(n), w, h, e(n)))
        for n in FIXPICS.get(sec, []):
            src = os.path.join(PICS, n + ".png")
            shutil.copyfile(src, os.path.join(out, "img", n + ".png"))
            w, h = png_size(src)
            figs.append(
                '<figure id="%s"><img src="img/%s.png" alt="%s: the fix\'s driver, before and after"'
                ' loading="lazy" width="%d" height="%d"><figcaption><code>%s</code></figcaption></figure>'
                % (e(n), e(n), e(n), w, h, e(n)))
        parts.append(
            '<section id="sec%d"><header class="sh"><span class="tag">sec %d</span><h2>%s</h2></header>\n'
            '<p>%s</p>%s\n%s</section>'
            % (sec, sec, e(titles.get(sec, "")), e(SUMMARY.get(sec, "")), "".join(metas), "\n".join(figs)))
    nav = " ".join('<a href="#sec%d">%d</a>' % (s, s) for s in order)
    page = TEMPLATE.replace("@INTRO@", intro).replace("@NAV@", nav).replace("@SECTIONS@", "\n".join(parts))
    with open(os.path.join(out, "index.html"), "w", encoding="utf-8") as f:
        f.write(page)
    print("%d sections, %d cases -> %s" % (len(order), total, out))


TEMPLATE = """<title>Thickness Before and After</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;600&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>
/* A long scroll of figure plates under one sticky index of fixes. */
:root{--bg:#f3f5f8;--panel:#ffffff;--ink:#1d2430;--muted:#5a6575;--line:#d8dee7;--accent:#3d5f8f;--good:#1f7a3a;--bad:#b3261e;--cut:#c66a2a;--plate:#ffffff;--plate-line:#e3e7ee;--plate-cap:#fafbfc;--plate-ink:#5a6575;color-scheme:light}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#141922;--panel:#1c2330;--ink:#e3e8ef;--muted:#9aa6b6;--line:#2d3746;--accent:#8fb0dd;--good:#6cc58a;--bad:#ef8a80;--cut:#e39a62;--plate:#ffffff;--plate-line:#e3e7ee;--plate-cap:#fafbfc;--plate-ink:#5a6575;color-scheme:dark}}
:root[data-theme="dark"]{--bg:#141922;--panel:#1c2330;--ink:#e3e8ef;--muted:#9aa6b6;--line:#2d3746;--accent:#8fb0dd;--good:#6cc58a;--bad:#ef8a80;--cut:#e39a62;--plate:#ffffff;--plate-line:#e3e7ee;--plate-cap:#fafbfc;--plate-ink:#5a6575;color-scheme:dark}
body{background:var(--bg);color:var(--ink);font:15px/1.55 "IBM Plex Sans",system-ui,sans-serif;padding-inline:16px;padding-block:24px 64px}
main{max-width:1120px;margin:0 auto;display:grid;gap:40px}
h1{font-size:28px;line-height:1.2;margin:0 0 8px;text-wrap:balance}
h2{font-size:20px;margin:0;text-wrap:balance}
p{max-width:68ch;margin:0}
code{font-family:"IBM Plex Mono",ui-monospace,monospace;font-size:.88em}
a{color:var(--accent)}
a:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
.intro{display:grid;gap:12px}
.key{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:8px 24px;padding:14px 16px;border:1px solid var(--line);border-radius:6px;background:var(--panel);font-size:14px}
.key b{font-weight:600}
.sw{display:inline-block;width:.8em;height:.8em;border-radius:2px;vertical-align:-1px;margin-right:6px}
nav{display:flex;flex-wrap:wrap;gap:6px 14px;font-family:"IBM Plex Mono",monospace;font-size:14px;position:sticky;top:env(safe-area-inset-top,0px);background:var(--bg);padding-block:8px;z-index:1;border-bottom:1px solid var(--line)}
section{display:grid;gap:14px;min-width:0}
.sh{display:flex;align-items:baseline;gap:12px;flex-wrap:wrap}
.tag{font-family:"IBM Plex Mono",monospace;font-size:13px;letter-spacing:.04em;color:var(--accent);text-transform:uppercase}
.meta{color:var(--muted);font-size:13.5px;max-width:none}
.meta a{font-family:"IBM Plex Mono",monospace;font-size:12.5px;margin-right:4px}
figure{margin:0;background:var(--plate);border:1px solid var(--line);border-radius:6px;overflow:hidden}
figure img{display:block;width:100%;height:auto}
figcaption{padding:6px 12px;font-size:13px;color:var(--plate-ink);border-top:1px solid var(--plate-line);background:var(--plate-cap)}
@media (prefers-reduced-motion:no-preference){html{scroll-behavior:smooth}}
</style>
<main>
<div class="intro">
<h1>Thickness, before and after</h1>
<p>@INTRO@</p>
<div class="key">
<div><b>Columns</b> &mdash; the shape given, its removed faces magenta &middot; upstream OCCT 8.0.1 chain files at <code>91be8c4c71</code> &middot; the fork just before the fix &middot; the fork now</div>
<div><b>Rows</b> &mdash; the result from the removed face's side &middot; cut open, <span class="sw" style="background:var(--cut)"></span>cut faces orange</div>
<div><b>Labels</b> &mdash; <span style="color:var(--good)">green</span> valid at the expected volume, <span style="color:var(--bad)">red</span> what went wrong; <i>unhollowed</i> = the input's volume</div>
<div><b>Marks</b> &mdash; red edges not used once each way round, red faces fail <code>isValid()</code>, black = inside out, grey = it threw (input shown)</div>
</div>
</div>
<nav aria-label="Fixes">@NAV@</nav>
@SECTIONS@
</main>
"""

if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.environ.get("THICK_WORK", "/tmp/thickness-pictures"), "page"))
