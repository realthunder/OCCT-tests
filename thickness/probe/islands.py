# islands.py <dir> [<dir before>]  -- what scan.py's files hold: the runs by
# outcome, the islands (a thickness refused or invalid between two that are
# made, alone or in a band), the volumes out of line with their neighbours',
# and the files not finished. With a second directory, what changed from it.
import collections
import glob
import os
import sys


def load(d):
    runs, unfinished = {}, []
    for f in sorted(glob.glob(os.path.join(d, "*.txt"))):
        text = open(f).read()
        if "# done" not in text:
            unfinished.append(os.path.basename(f))
        for line in text.splitlines():
            if line.startswith("#") or ": " not in line:
                continue
            tag, res = line.split(": ", 1)
            shape, face, t = tag.split()
            word = res.split()
            volume = float(word[1]) if len(word) > 1 else None
            runs[(shape, face, float(t))] = (word[0], volume)
    return runs, unfinished


runs, unfinished = load(sys.argv[1])
print("runs: %d  %s" % (len(runs), dict(collections.Counter(r[0] for r in runs.values()))))
if unfinished:
    print("NOT FINISHED:", " ".join(unfinished))
rows = collections.defaultdict(list)
for (shape, face, t), r in runs.items():
    rows[(shape, face, t > 0)].append((abs(t), r))
islands, kinks = [], []
for key in sorted(rows):
    row = sorted(rows[key])
    i = 0
    while i < len(row):
        if row[i][1][0] == "made":
            i += 1
            continue
        j = i
        while j < len(row) and row[j][1][0] != "made":
            j += 1
        if i > 0 and j < len(row):
            kinds = sorted(set(r[1][0] for r in row[i:j]))
            islands.append((key, row[i][0], row[j - 1][0], "/".join(kinds)))
        i = j
    for a, b, c in zip(row, row[1:], row[2:]):
        if a[1][0] == b[1][0] == c[1][0] == "made":
            bend = a[1][1] - 2 * b[1][1] + c[1][1]
            rise = (c[1][1] - a[1][1]) / 2
            if abs(bend) > 0.5 and abs(bend) > 0.05 * abs(rise):
                kinks.append((key, b[0], a[1][1], b[1][1], c[1][1]))
print("islands: %d" % len(islands))
for (shape, face, out), lo, hi, kinds in islands:
    span = "%g" % lo if lo == hi else "%g to %g" % (lo, hi)
    print("  %s %s %s %s: %s" % (shape, face, "outward" if out else "inward", span, kinds))
print("volumes out of line: %d" % len(kinks))
for (shape, face, out), t, a, b, c in kinks:
    print(
        "  %s %s %s %g: %.4f, %.4f, %.4f"
        % (shape, face, "outward" if out else "inward", t, a, b, c)
    )
if len(sys.argv) > 2:
    before, _ = load(sys.argv[2])
    moved = collections.Counter()
    for key in runs:
        if key in before and before[key] != runs[key]:
            was, now = before[key], runs[key]
            what = "%s -> %s" % (was[0], now[0])
            if was[0] == now[0] == "made":
                what = "made, another volume"
            moved[(key[0], what)] += 1
    print("changed from %s: %d" % (sys.argv[2], sum(moved.values())))
    for (shape, what), n in sorted(moved.items()):
        print("  %-22s %-28s %d" % (shape, what, n))
