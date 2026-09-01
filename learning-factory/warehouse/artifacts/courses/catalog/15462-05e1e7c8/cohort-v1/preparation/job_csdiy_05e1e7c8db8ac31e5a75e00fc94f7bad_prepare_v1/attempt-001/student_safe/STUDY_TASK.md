# Unit 01 Study Task: Deterministic Triangle Rasterizer

## Goal

Build a small C++17 program named `rasterize` that reads a versioned text scene, rasterizes colored 2D triangles at pixel centers, and writes a byte-for-byte deterministic binary PPM image. Package the geometry as a library, validate hostile inputs, and demonstrate behavior with automated tests.

The supplied local packet is the complete source material for this unit. Do not depend on the remote catalog links.

## Required repository shape

Use this minimum layout (you may add supporting files):

```text
CMakeLists.txt
README.md
ENGINEERING_NOTES.md
include/
src/
tests/
evidence/build-and-test.txt
COMPREHENSION_RESPONSES.md
```

The CMake build must produce a reusable core library, a `rasterize` executable, and at least one test executable registered with CTest. Keep scene parsing, PPM/file I/O, and command-line handling outside the coverage/interpolation core. The submission must build without network access and without third-party runtime dependencies.

## Command-line contract

The interface is:

```text
rasterize INPUT.scene OUTPUT.ppm
```

Return `0` only after a complete output has been written. Use a nonzero status for bad arguments, malformed or out-of-range input, read failure, or write failure. Diagnostics go to standard error and must identify the category of failure without relying on timestamps. A failed run must not leave a newly created file that looks like a successful output.

On success, print one deterministic summary line containing width, height, triangle-record count, and skipped-degenerate count. Do not include elapsed time or other volatile values.

## Scene format: `RSCENE1`

The file is ASCII. Tokens are separated by whitespace. A `#` begins a comment that continues through the end of that line. After comments are removed, records have this order:

```text
RSCENE1
size WIDTH HEIGHT
background R G B
triangle X0 Y0 R0 G0 B0 X1 Y1 R1 G1 B1 X2 Y2 R2 G2 B2
triangle ...
```

Requirements:

- `WIDTH` and `HEIGHT` are decimal integers in `[1, 4096]`.
- Background components are decimal integers in `[0, 255]`.
- Each position and vertex-color component is a finite decimal number parsed as `double`.
- Vertex-color components are in `[0, 1]`.
- There may be zero or more `triangle` records after the background.
- Reject missing values, extra values within a record, unknown records, duplicate/misordered header records, non-finite values, out-of-range values, integer overflow, and trailing non-comment tokens that do not form a record.
- Bound resource use: reject a scene with more than 100,000 triangles before rendering it.

## Image and rasterization contract

Use a framebuffer whose origin is the upper-left corner, with positive `x` to the right and positive `y` downward. Pixel `(x, y)` is sampled once at `(x + 0.5, y + 0.5)`.

For every triangle:

1. Work only over its integer pixel bounding box clipped to the framebuffer.
2. Determine coverage with oriented edge/half-space tests.
3. Accept clockwise and counterclockwise vertex input. Reversing winding without changing vertex attributes must not change the image.
4. Apply one documented top-left shared-edge convention. Two triangles that partition a rectangle along a common edge must assign every on-edge sample exactly once: no crack and no double ownership.
5. Treat a triangle whose signed double-precision area is exactly zero as degenerate: draw no samples, increment the skipped count, and continue. A finite, nonzero but very small area is not automatically malformed.
6. For a covered sample, compute affine barycentric weights and interpolate RGB from the three vertex colors.
7. Clamp each interpolated channel to `[0, 1]`, then convert it to a byte with `floor(255 * channel + 0.5)`.

Initialize the image to the declared background. Process triangles in file order; a later triangle overwrites a sample owned by an earlier triangle. There is no depth buffer. A wholly off-screen, nondegenerate triangle changes no pixels but still counts as a triangle record.

Write binary PPM (`P6`) with exactly this ASCII header, where values are rendered in ordinary decimal:

```text
P6
WIDTH HEIGHT
255
```

Immediately follow the final newline with `WIDTH * HEIGHT * 3` bytes in row-major order from top to bottom, RGB within each pixel. Repeated clean runs on identical input must produce identical bytes and an identical success summary.

## Engineering constraints

- Compile as C++17 with warnings enabled.
- Check dimension, pixel-count, byte-count, and allocation arithmetic before allocating.
- Avoid global mutable state and undefined behavior.
- Do not scan the full framebuffer when a clipped triangle bounding box is smaller.
- Make the core callable directly from tests without spawning the CLI.
- Keep generated build products out of source directories.
- Document your public data model, coverage convention, error strategy, and any remaining limitations.

## Required automated evidence

Write deterministic tests that cover at least:

- an empty scene and background serialization;
- a triangle with samples strictly inside, strictly outside, and exactly on boundaries;
- both windings of the same attributed triangle;
- two triangles forming a rectangle, including shared-edge ownership;
- barycentric color interpolation at selected covered sample centers;
- overlapping triangles and file-order overwrite behavior;
- partially and wholly off-screen triangles;
- zero-area and finite skinny triangles;
- malformed, non-finite, out-of-range, oversized, truncated, and unknown input;
- write failure or an equivalent injectable output-failure path;
- repeat-render byte equality; and
- fixed-seed property checks for winding invariance and bounded writes.

Use assertions that inspect coverage, pixel bytes, statuses, and output structure—not merely that the process ran. If you use randomized cases, commit a fixed seed and print it on failure.

From a clean checkout, capture the output of commands equivalent to:

```text
cmake -S . -B build
cmake --build build
ctest --test-dir build --output-on-failure
```

Store that unedited command output in `evidence/build-and-test.txt`, along with the submitted revision identifier if one exists. Evidence is useful for review but does not replace independent validation.

## Engineering notes

In `ENGINEERING_NOTES.md`, record:

- the invariants maintained by coverage and interpolation;
- your shared-edge and winding strategy;
- worst-case time in terms of triangle bounding boxes and framebuffer dimensions;
- memory complexity;
- overflow and floating-point decisions, including why a blanket epsilon is or is not appropriate;
- how parser and I/O failures avoid success-looking artifacts;
- one alternative design you rejected and the tradeoff; and
- which features are intentionally deferred beyond this unit.

## Comprehension response

Answer every prompt in `COMPREHENSION.md` in a new root-level file named `COMPREHENSION_RESPONSES.md`. Refer to concrete source files and tests where requested. Do not edit the prompt sheet.

## Scope guard

Do not add a GPU API, 3D camera pipeline, depth buffer, textures, perspective correction, multisampling, lighting, or parallel renderer. A small correct component with strong evidence is the intended result.

**Preparation label:** `PREPARED_UNVALIDATED` — the task specification is locally available, but no learner implementation has been validated.

