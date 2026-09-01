# Sprig: a tiny language that runs on the JVM

Sprig is a build-your-own-language challenge in Java. You will turn a small,
statically typed source language into a valid JVM class file without parser
generators or bytecode libraries. The finished compiler must lex and parse the
input, reject ill-typed programs, lay out local variables, emit branch-safe JVM
bytecode, and write a loadable class exposing `public static int run()`.

This is an independent educational artifact inspired only by the catalog topic
“Creating JVM Language.” It does not reproduce the linked article. See
`PROVENANCE.json` and `LICENSE_BOUNDARY.md` for the source boundary.

## Start here

1. Read `REQUIREMENTS.md` for the normative language and compiler contract.
2. Read `CONCEPTS.md`, then answer `DESIGN_QUESTIONS.md` before coding.
3. Work only in `starter/`; it contains intentional `TODO` implementations.
4. Run `./environment/run-public-tests.sh` after each milestone.
5. Try the optional debugging, review, adversarial, and benchmark exercises only
   after the core public tests pass. Their answer material is sealed.

The challenge is progressively revealable: the root documents define behavior,
`starter/` supplies interfaces, and `public_tests/` supplies only black-box
checks. Reference code, reference tests, and design answers are under `sealed/`
and must not be exposed to learners.

## Milestones

- **M1 — Front end:** tokens, source locations, comments, and precedence parsing.
- **M2 — Static semantics:** scoped locals, definite declaration, and `Int` versus
  `Bool` checking.
- **M3 — Straight-line code:** constants, locals, arithmetic, return, and print.
- **M4 — Control flow:** comparisons, short-circuit operators, `if`, and `while`.
- **M5 — Artifact quality:** deterministic class bytes, diagnostics, limits, and
  verifier-safe output.

## Language taste

```sprig
fn main() -> Int {
  let n = 6;
  let acc = 1;
  while (n > 1) {
    acc = acc * n;
    n = n - 1;
  }
  print acc;
  return acc;
}
```

The generated class name is supplied separately, so source text contains no
package or class declaration. The example prints `720` and `run()` returns
`720`.

## Local validation status

This host does not provide a Java toolchain. The repository therefore remains
`GENERATED` + `PARTIAL`; consult `VALIDATION.md` for exact commands and observed
results. Independent validation is mandatory even on a host with Java 17+.

