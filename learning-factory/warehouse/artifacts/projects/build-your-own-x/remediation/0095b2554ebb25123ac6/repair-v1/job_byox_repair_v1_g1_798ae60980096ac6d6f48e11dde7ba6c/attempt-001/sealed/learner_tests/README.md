# Sealed learner-targeted tests

These tests import `example.com/pebble`, not the sealed reference module. They intentionally have no committed `go.mod`: `sealed/validation/run_learner_validation.py` copies the immutable test source into scratch space and creates the only `replace` directive there, pointing at the candidate selected by the harness.

The runner executes three layers: candidate-local tests as diagnostic information, a pristine copy of the public black-box suite, and this sealed suite. Its `--self-check` mode creates a temporary `example.com/pebble` module from the sealed reference, requires all layers to accept it, then applies three deterministic seeded defects and requires the harness to reject each one.

Intended commands with Go 1.21+ are:

```bash
python3 sealed/validation/run_learner_validation.py --candidate starter
python3 sealed/validation/run_learner_validation.py --self-check
```

The generated module replacement, offline Go environment, captured output, process-group timeout, expected exit classification, and suite-content lock are controlled by the runner. These tests remain sealed evaluator input; their presence is not a validation label.
