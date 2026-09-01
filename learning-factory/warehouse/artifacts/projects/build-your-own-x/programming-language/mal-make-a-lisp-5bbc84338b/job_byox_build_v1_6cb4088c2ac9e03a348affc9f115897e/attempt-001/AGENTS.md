# Learner agent guide

Work only in `starter/` unless a human explicitly asks for another location. The public API and
observable behavior are specified in `REQUIREMENTS.md`; prose output from an agent is not evidence
that it works.

Use the standard-library test runner from the repository root:

```bash
PYTHONPATH=starter python3 -m unittest discover -s public_tests -p 'test_*.py' -v
```

Implementation rules:

- Keep the project compatible with Python 3.6+ and add no runtime dependencies.
- Do not use Python `eval`, `exec`, `ast.literal_eval`, or a host-language parser as the Lisp reader.
- Keep parsing, evaluation, compilation, and VM execution as separate phases.
- Never treat a host exception or traceback as a language-level diagnostic.
- Enforce step and call-depth limits in deterministic code.
- Preserve the public module names and callable interfaces supplied in `starter/sprig`.
- Do not inspect or copy any `sealed/` content.

When changing semantics, first reconcile the change with `REQUIREMENTS.md` and add a deterministic
test. Run focused tests during development, then the full public suite.
