# Build Mica: one language, two execution engines

Mica is a deliberately small, independently designed programming language. Your task is to complete
its front end and two execution engines in Java: a tree-walk interpreter and a compiler targeting a
stack-based virtual machine. Both engines must implement the same observable semantics.

This repository is progressively revealable. Start with this file, then read `REQUIREMENTS.md` and
`CONCEPTS.md`. Work only in `starter/`. Run `public_tests/run.sh` whenever you want feedback. The
`sealed/` tree contains reference and review material for an instructor or validator and is not part
of the learner view.

## Suggested milestones

1. Scan tokens with accurate line and column locations.
2. Parse expressions and statements with precedence and useful syntax errors.
3. Execute programs in the tree-walk engine with lexical scope.
4. Emit bytecode, patch jumps, and execute it on the VM.
5. Compare both engines on success output and failure category/location.

The project has no third-party dependencies. It targets Java 21 and uses a small Java test harness so
it can be built with `javac` alone. See `environment/README.md` for exact commands.

## Boundaries

The catalog link is provenance only. No linked tutorial text or code was copied. This challenge uses
its own name, grammar, API, code, tests, and explanations. `MANIFEST.yaml` deliberately remains
`GENERATED` + `PARTIAL`: only an independent validator may award stronger labels.
