# Working agreement for Mica learners

Work only in `starter/`. Treat `public_tests/` and the written requirements as
the public interface; do not weaken tests or change expected language behavior.

Use C11 and keep the project buildable with:

```bash
make -C starter clean all
python3 public_tests/test_public.py
```

Implementation order:

1. Preserve the existing tokenizer behavior.
2. Add recursive-descent parsing with the precedence stated in
   `REQUIREMENTS.md`.
3. Add validation for declarations and the documented resource limits.
4. Implement `run` before `compile`; use differential checks between them.
5. Make diagnostics deterministic and keep normal output on stdout, errors on
   stderr.

Do not introduce shell-command subprocesses, unbounded input reads, undefined
signed overflow, or machine-dependent output. Do not inspect sealed material.
Your implementation should reject malformed programs rather than recover and
continue.
