# TKMath checks

`trig_roots.cpp` -- `math_TrigonometricFunctionRoots`, the solver of
a cos^2 + 2b cos sin + c cos + d sin + e = 0 between two bounds, which the
extrema of a point on an ellipse use (and through them BOP's projection of
a point on an edge). 200000 random equations of every form the solver has
a branch for, against the changes of sign of a dense sampling, and a point
projected on an arc of ellipse running from -PI/2 to 0. Build and run as
its header says; it exits 1 on a failure.

Upstream's solver, and the fork's before `5c531f4938`, brought the roots to
a lower bound below zero by no period at all and dropped every root
between the bound and zero: 72891 of the 196622 changes of sign have no
root, and the point on the arc does not project on it. The fork's finds
them all. The case that showed it, and the fix: `../fillet/README.md`,
"The roots of a trigonometric equation below zero".
