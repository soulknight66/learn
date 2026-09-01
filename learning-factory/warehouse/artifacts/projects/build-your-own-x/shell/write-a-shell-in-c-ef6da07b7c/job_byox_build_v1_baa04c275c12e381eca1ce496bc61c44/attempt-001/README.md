# Build a small shell in C

This challenge asks you to build `msh`, a deliberately small POSIX shell. The goal is not shell-language compatibility. The goal is to understand the boundary between parsing a command line and arranging processes, pipes, process groups, and terminal ownership.

The repository is progressively revealable:

1. Read this page and build the starter.
2. Use `REQUIREMENTS.md` as the behavioral contract.
3. Use `CONCEPTS.md` when a process or terminal concept is unfamiliar.
4. Answer `DESIGN_QUESTIONS.md` before choosing data structures.
5. Run the public tests one stage at a time.

Reference material and evaluator-only artifacts are sealed. They are not part of the learner view and should not be inspected while solving the challenge.

## Quick start

```sh
make -C starter clean all
python3 public_tests/test_shell.py --shell starter/msh --stage parsing
python3 public_tests/test_shell.py --shell starter/msh --stage execution
python3 public_tests/test_shell.py --shell starter/msh --stage builtins
python3 public_tests/test_shell.py --shell starter/msh --stage jobs
```

The starter is intentionally incomplete. A clean compile is the first checkpoint; behavioral tests are expected to fail until you implement the corresponding stages.

## Suggested milestones

- **Milestone 0 — lifecycle:** preserve the supplied ownership and cleanup rules; make an empty batch input exit successfully.
- **Milestone 1 — parsing:** produce an argument vector for words, quotes, escapes, `|`, and a final `&`; reject malformed input without crashing.
- **Milestone 2 — processes and pipes:** fork one child per command, wire every pipeline concurrently, close unused descriptors, and return the last command's status.
- **Milestone 3 — parent built-ins:** implement `cd`, `exit`, `jobs`, and `wait` in the shell process.
- **Milestone 4 — job control:** place each pipeline in one process group, keep background jobs, reap children, and hand the controlling terminal to foreground groups in interactive mode.

## Scope

The required language is C11 plus POSIX.1-2008 interfaces. There are no third-party runtime dependencies. Parameter expansion, globbing, redirections, command substitution, logical operators, and scripting syntax are explicit non-goals. Treat their metacharacters as ordinary word characters unless `REQUIREMENTS.md` says otherwise.

Use only disposable directories for experiments. The implementation must not create files as part of normal command execution unless the launched program itself does so.

## Validation status

This pack is generated and intentionally labeled `PARTIAL`: local builds and tests are useful evidence, but only the learning-factory's independent validators can award validation labels. See `VALIDATION.md` for the exact local observations.
