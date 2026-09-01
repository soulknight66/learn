# Kickoff Unit Notes

Scope: finite real-valued discrete-time signals, integer shifts, and linear
convolution only. This is a manager-authored kickoff unit, not an official
EE120 lab, and completing it cannot complete the course.

## Mathematical model

- A nonempty representation `(start, samples)` maps tuple position `i` to
  absolute index `start + i`; values outside the tuple are zero.
- `shift(k)[n] = original[n-k]`, so shifting changes `start` to `start+k` and
  does not reorder samples.
- For starts `sx, sh` and tuple positions `i, j`, convolution starts at
  `sx+sh`, accumulates at tuple position `i+j`, and has length `N+M-1`.
- Empty and represented-all-zero signals are observably different. Boundary
  zeros carry support metadata and must not be trimmed.

## Engineering lessons practiced

- Validate types at the API edge, remembering that Python booleans are integer
  subclasses; distinguish wrong types from invalid numeric values.
- Copy mutable inputs and expose tuples/read-only properties so validation
  remains true after construction.
- Use several evidence types: constants derived by hand, boundary cases,
  fixed-seed generated agreement, and mathematical properties. Agreement
  between implementations alone can preserve a correlated defect.
- Complexity for sparse convolution includes input scans and the required full
  output: Θ(`N+M+Kx*Kh`) time, not only the multiplication count.
- A benchmark observation is conditional on its inputs and environment. Raw
  repetitions, provenance, output agreement, and an explicit validation label
  are part of the result.

## Working hypotheses and outcomes

1. Tuple copying plus blocked attribute writes is sufficient for the observable
   immutability contract. Construction and mutation tests passed.
2. Sparse traversal should have its clearest benefit when `Kx*Kh` is far below
   `N*M`. The zero-heavy measurement supported this for the selected case.
3. Dense performance is implementation- and environment-dependent. This run
   unexpectedly showed a small sparse advantage, so no dense crossover claim
   is justified.

Next practice target: measure multiple sizes and densities with randomized
case order and retained dispersion, without expanding into later course topics.
