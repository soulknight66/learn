# Sealed validation harness

The scripts in this directory have distinct deterministic roles:

- `check_pack.py` verifies required/forbidden paths, exact top-level content, regular entry types, nonempty directories, immutable JSON, provenance hash semantics, disclosure policy, credential-like patterns, and a content-tree digest.
- `learner_view.py` builds or verifies a view using the fixed policy in `environment/learner-view.json` and refuses to overwrite a destination.
- `test_learner_view.py` uses only synthetic temporary fixtures to cover allowlist copying, destination preservation, and special-entry rejection.
- `validate_student_view.py` builds a controller-selected destination and runs a bounded bubblewrap probe that must be unable to read both view-relative and production-source sealed paths.
- `run_learner_validation.py` locks the starter/public/sealed test inputs, creates candidate replacements only in scratch modules, disables module/toolchain downloads, accepts the known-good reference, and rejects seeded parser-coordinate, slot-range, and arithmetic defects.

Representative commands from the pack root are:

```bash
python3 sealed/validation/check_pack.py
python3 -m unittest discover -s sealed/validation -p 'test_*.py' -v
python3 sealed/validation/validate_student_view.py --source . --destination /controller/scratch/pebble-view
python3 sealed/validation/run_learner_validation.py --self-check
python3 sealed/validation/run_learner_validation.py --candidate /controller/submission/starter
```

The view destination and candidate path must be controller-owned locations outside this source pack. A successful builder run does not promote any validation label; a fresh independent harness must preserve its commands, exits, and output.
