# onedome.py [thickness] [cells]  -- hand values, Thickness.md sec 23
#
# The half ball y >= 0 of radius R = 5, its sphere in two faces that meet
# along a tangent edge: two domes (z > 0, z < 0, the edge half the equator)
# or two lunes (x > 0, x < 0, the edge a meridian). One of them removed. The
# half ball turned a quarter about y takes the domes onto the lunes; the
# flat's split along the z axis changes nothing, so both give these values.
#
# The removed face lies on the kept face's own sphere, and the kept face's
# offset never meets it. The gap is closed as at a tangent edge between
# coplanar faces (sec 9, sec 18):
#  - j2 (Intersection): the kept face runs on round the sphere a thickness
#    (an arc of t) into the removed one, to a wall square to the sphere
#    there -- the cone from its centre at latitude t / R;
#  - j0 (Arc): a tube round the edge, its ends where it meets the flat's
#    offset and, outward, a ball round each end of the edge.
#    Outward this solid has a sliver face at each end of the edge, in the
#    plane z = 0 between the flat's offset, the sphere and the ball (0.025 by
#    0.0006, pictures/sliver); the fork does not build it (sec 25), and the
#    volume is the same to the last figure given.
# Elsewhere the rules of polehand.py: the skin is closed in the removed
# face's own surface, extended (the flat's slab beside the removed dome is cut
# by the sphere), j2 meets in sharp corners, j0 rounds the convex edges
# outward.
#
# Columns along z over the (x, y) plane, each one's extent in z worked
# exactly; a midpoint rule over (x, y). Domes, the dome z > 0 removed.
import math
import sys

import numpy as np

R = 5.0
t = float(sys.argv[1]) if len(sys.argv) > 1 else 0.5
N = int(sys.argv[2]) if len(sys.argv) > 2 else 4800
SPAN = 6.0
h = 2 * SPAN / N
c = -SPAN + (np.arange(N) + .5) * h
X, Y = np.meshgrid(c, c, indexing='ij')
RHO = np.hypot(X, Y)


def cap(r, rho2=None):
    rho2 = RHO * RHO if rho2 is None else rho2
    return np.sqrt(np.clip(r * r - rho2, 0, None))


def L(a, b):
    return np.clip(b - a, 0, None)


def U(a1, b1, a2, b2):
    """the length of the union of [a1, b1] and [a2, b2]"""
    return L(a1, b1) + L(a2, b2) - L(np.maximum(a1, a2), np.minimum(b1, b2))


def vol(length):
    return length.sum() * h * h


yin = Y >= 0
slab = (Y < 0) & (Y >= -t)
V0 = vol(np.where(yin, 2 * cap(R), 0))
cone = RHO * math.tan(t / R)      # the wall: z = rho tan(t / R)
tube = np.sqrt(np.clip(t * t - (RHO - R) ** 2, 0, None))   # round the equator
res = {}

# j2 outward: off the half ball, y >= -t, r <= R + t below the wall, r <= R above
a = np.where(yin, L(-cap(R + t), -cap(R)) + L(cap(R), np.minimum(cap(R + t), cone)), 0)
b = np.where(slab, U(-cap(R + t), np.minimum(cap(R + t), cone), -cap(R), cap(R)), 0)
res['out', 2] = vol(a + b)
# j2 inward: the cavity y > t, r < R - t, and r < R above the wall
res['in', 2] = V0 - vol(np.where(Y > t, U(-cap(R - t), cap(R - t), np.maximum(cone, -cap(R)), cap(R)), 0))
# j0 inward: the cavity y > t, below the equator r < R - t, above it r < R
# off the tube
res['in', 0] = V0 - vol(np.where(Y > t, L(-cap(R - t), 0) + L(tube, cap(R)), 0))
# j0 outward: below the equator, within t of the kept dome and the flat (a
# quarter tube round the flat's rim); above it the flat's slab cut by the
# sphere, the tube round the equator off the ball, and a ball round each end
tau = np.sqrt(np.clip(t * t - Y * Y, 0, None))
low = np.where(slab, L(-cap(R + tau, X * X), 0), 0) + np.where(yin, L(-cap(R + t), -cap(R)), 0)
balls = np.maximum(np.sqrt(np.clip(t * t - (X - R) ** 2 - Y * Y, 0, None)),
                   np.sqrt(np.clip(t * t - (X + R) ** 2 - Y * Y, 0, None)))
high = np.where(Y < 0, U(0, np.where(slab, cap(R), 0), 0, balls), 0) + np.where(yin, L(cap(R), tube), 0)
res['out', 0] = vol(low + high)

if __name__ == "__main__":
    print("V0 %.4f" % V0)
    for d in ("out", "in"):
        for j in (2, 0):
            print("onedome_%s_j%d %.4f" % (d, j, res[d, j]))
