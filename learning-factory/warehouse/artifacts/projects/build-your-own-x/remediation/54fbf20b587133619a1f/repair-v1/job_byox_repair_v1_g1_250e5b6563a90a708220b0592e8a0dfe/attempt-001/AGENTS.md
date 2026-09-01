# Agent guide for the Pebble challenge

Work on the learner implementation in `starter/`. Read `REQUIREMENTS.md` before changing an exported
API. The visible tests are examples, not the whole specification.

## Rules

- Work only in the projected stage view supplied by the challenge administrator. If `sealed/` or an
  unrevealed prompt directory is present, stop and report an isolation failure rather than opening it.
- Do not inspect `debugging/`, `review_exercises/`, `adversarial/`, or `benchmarks/` unless that
  directory is present in the named stage projection.
- Keep the implementation dependency-free and compatible with Node.js 20+ ESM.
- Preserve the exports documented by `starter/README.md`.
- Never implement language execution with JavaScript `eval`, `Function`, `vm`, or child processes.
- Token locations and thrown Pebble errors are observable behavior.
- Reject malformed source and malformed bytecode deterministically; do not silently repair it.
- Keep parser and VM work iterative where practical, and enforce configured work limits.
- Add learner tests beside the public suite only if the administrator allows new visible files.

Run from the repository root:

```bash
node --test public_tests/*.test.mjs
```

When reporting completion, state exactly which command ran and whether every test passed. A prose
claim without command output is not validation.
