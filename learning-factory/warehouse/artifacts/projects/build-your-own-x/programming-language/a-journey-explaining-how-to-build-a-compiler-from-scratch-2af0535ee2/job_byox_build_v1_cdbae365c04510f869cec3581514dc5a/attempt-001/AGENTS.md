# Worker guide

This is a progressively revealable compiler exercise. Learner work belongs in `starter/`. Do not move
or quote material from `sealed/` into learner-visible paths. Treat `sealed/`, `adversarial/`,
`debugging/`, `review_exercises/`, and `benchmarks/` as evaluator-owned material unless a harness
explicitly reveals one exercise.

Keep the public API in `starter/include/pebble.h` stable. Build using argv-based tools as shown in the
Makefiles. Diagnostics and output are part of the contract, so tests must not depend on locale or
wall-clock time. Add public tests only for behavior documented in `REQUIREMENTS.md`; do not encode a
particular parser or bytecode layout. Never place a completed implementation or exercise answer in
`starter/`, `public_tests/`, or `environment/`.
