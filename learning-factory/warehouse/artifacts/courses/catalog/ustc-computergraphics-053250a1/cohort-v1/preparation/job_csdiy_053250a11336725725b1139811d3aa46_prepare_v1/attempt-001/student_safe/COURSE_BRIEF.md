# USTC Computer Graphics — Engineering Kickoff

## What this packet is

This packet contains one bounded, manager-authored bridge unit: **Build a Testable 2D Transform Pipeline**. It uses a core computer-graphics idea to practice production-minded C++ design. Plan for 6–8 hours.

The unit is not presented as USTC's official first lesson. The catalog identifies a USTC Computer Graphics course, a course-site link, a recording link, a reference textbook, and an assignment collection. Their detailed contents and official order are not available in this workspace. You do not need any of those external resources for this unit.

Completing this unit starts the course; it does not complete a roughly 100-hour course. Further units require separately retrieved, classified, prepared, and validated material.

## Why this unit

An algorithms background gives you useful habits: define a representation, state an invariant, reason about operation order, and analyze cost. Software engineering adds another obligation: make those choices visible in interfaces, validate inputs, isolate failure, build reproducibly, and collect evidence that another person can rerun.

By the end of this unit, you should be able to:

- express 2D translation, scaling, and rotation as homogeneous matrices;
- compose transformations in a stated order and explain noncommutativity;
- isolate a small mathematical core from input/output code;
- give a command-line program deterministic success and failure behavior;
- test examples, invariants, compositions, and malformed inputs; and
- document a design so that another engineer can build and challenge it.

## Mathematical convention for the unit

Use column vectors and homogeneous coordinates:

\[
p = \begin{bmatrix}x\\y\\1\end{bmatrix}.
\]

The elementary transforms are

\[
T(t_x,t_y)=
\begin{bmatrix}
1&0&t_x\\
0&1&t_y\\
0&0&1
\end{bmatrix},\quad
S(s_x,s_y)=
\begin{bmatrix}
s_x&0&0\\
0&s_y&0\\
0&0&1
\end{bmatrix},
\]

and, for a counterclockwise angle \(\theta\) measured in radians,

\[
R(\theta)=
\begin{bmatrix}
\cos\theta&-\sin\theta&0\\
\sin\theta&\cos\theta&0\\
0&0&1
\end{bmatrix}.
\]

If operation \(A\) appears before operation \(B\), the point experiences \(A\) and then \(B\):

\[
p' = B A p.
\]

Consequently, a running composite starts at the identity and is updated as \(M \leftarrow O M\) for each operation \(O\) in file order. State this convention in your own documentation; do not leave readers to infer it from code.

## Engineering ideas to carry into the task

### Make invalid states visible at the boundary

Parsing a token and validating it are different acts. A syntactically numeric value can still be non-finite. A structurally valid file can still repeat an identifier or place an operation after the point section begins. Reject the complete input before emitting any result so that failure cannot look like partial success.

### Keep the mathematical core pure

Matrix construction, multiplication, and point application should not read files, print diagnostics, or inspect process arguments. Pure operations are easier to test, reuse, and reason about. Keep parsing and command-line presentation at the boundary.

### Treat floating-point checks as claims with domains

Exact comparison is appropriate for some structural facts, but computed real-number results usually need a documented absolute/relative tolerance. An inverse round trip also has preconditions: zero scaling is not invertible, and very ill-conditioned inputs weaken useful guarantees. Choose ordinary, finite test values and say what your tolerance means.

### Make evidence reproducible

A green test report is meaningful only when another person can reproduce the build and see what was exercised. Use a fresh build directory, CTest integration, fixed cases or fixed seeds, and a short test inventory. Do not claim properties that the tests do not check.

## Suggested timebox

| Work | Time |
|---|---:|
| Read, restate conventions, sketch modules | 45–60 min |
| Implement and unit-test the matrix core | 90–120 min |
| Implement parser and deterministic CLI | 90–120 min |
| Add composition, property, and failure tests | 75–105 min |
| Fresh-build check, documentation, comprehension | 60–90 min |

Stop at the specified boundary. Rendering, OpenGL, 3D projection, a GUI, a scene graph, arbitrary matrix inversion, benchmarking, packaging, and continuous-integration setup are possible later work, not requirements for this kickoff.

## Evidence you will produce

Your submission is a small C++ source tree, its automated tests, build instructions, a design note, and your own comprehension responses. Completion is determined by independent validation of those artifacts, not by a statement that the work is finished.
