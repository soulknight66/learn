# Learner and agent rules

- Implement the TODOs under `starter/`; do not import code or prose from `sealed/`.
- Treat `REQUIREMENTS.md` as the behavioral contract. Public tests are examples, not the full spec.
- Keep the Java package `org.learningfactory.mica` and avoid third-party dependencies.
- Preserve deterministic behavior: source order, diagnostic location, and output are observable.
- Do not weaken, delete, or special-case tests.
- Do not add network access, filesystem access from Mica programs, reflection, or host process launch.
- Use bounded resources in any extensions and document newly chosen limits.
- Before handing off, compile from a clean temporary directory and run `public_tests/run.sh`.

Reference implementations, reference tests, design answers, and solution-bearing reviews belong only
under `sealed/`. Never move them into the learner-visible tree.
