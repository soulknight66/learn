# Agent instructions

This is a progressively revealable operating-systems challenge.

- Learner work belongs in `starter/`; do not inspect `sealed/` while solving.
- Treat `REQUIREMENTS.md` as the behavioral contract and `public_tests/` as examples, not a complete
  specification.
- Keep the kernel core freestanding: no allocation, libc calls, ambient state, or undefined behavior.
- Do not weaken tests, alter API constants, or expose sealed material in learner-visible paths.
- Use argv-based build commands and the pinned absolute tool paths documented in `environment/`.
- A host test pass is not proof of hardware correctness. Preserve error output and report blockers.
- Do not claim validation labels; `MANIFEST.yaml` intentionally remains `GENERATED` + `PARTIAL` until
  an independent harness decides otherwise.
