# Working agreement for Ember-C

Work only in this repository.  Treat `sealed/` as validator-owned: do not read,
copy, or modify it while solving the challenge.  Learner implementation work
belongs under `starter/`; learner tests may be added beside `public_tests/`.

Preserve these behavioral constraints:

- Use C17 and compile with strict warnings.
- Do not execute source text through a shell or through the host C compiler.
- Keep lexer, compiler, and VM limits deterministic.
- Report source locations for lexical, syntax, and runtime errors; retain
  source metadata through bytecode execution.
- Enforce the normative syntax-depth limit before recursive descent.
- Check division, remainder, stack bounds, memory bounds, jumps, and signed
  arithmetic before performing them.
- Keep subprocess invocations as argument arrays in any added harness code.
- Do not add secrets, credentials, external repositories, or generated binary
  artifacts to the challenge pack.

Suggested checks from the repository root:

```sh
make -C starter clean all
MICROC_BIN="$PWD/starter/build/emberc" public_tests/run.sh
```

The public suite is incomplete by design.  Passing it is not proof of overall
correctness or self-interpretation.
