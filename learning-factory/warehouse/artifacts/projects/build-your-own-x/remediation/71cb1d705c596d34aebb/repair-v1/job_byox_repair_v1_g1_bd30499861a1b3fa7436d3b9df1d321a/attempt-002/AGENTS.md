# Working agreement for learner coding agents

This file governs agents implementing the learner submission. A reference
builder or harness-controlled independent validator with an explicit sealed
task follows that task's authority instead; it must not expose sealed content
into the learner view.

The learner view is the exact default-deny allowlist in
`environment/VIEW_POLICY.json`, not this validator-pack root. Do not broaden
that list or copy files into it as a way to reach instructor material.

Implement the learner solution only inside `starter/`, and treat
`REQUIREMENTS.md` as the public behavioral contract. Do not inspect or copy any
sealed or instructor-only material. Public tests are examples, not the complete
specification.

## Safe iteration

1. Run `make -C starter clean all` before changing behavior.
2. Keep lexer, parser, execution, and job tracking ownership boundaries clear.
3. Add deterministic tests for every newly supported grammar or process-state
   transition.
4. Run `python3 -m unittest discover -s public_tests -v` after each stage.
5. Test interactive behavior through a pseudo-terminal, never by assuming that
   piped stdin behaves like a terminal.

Compile with the existing strict warning flags. Use argv-based process APIs;
never route user input through `system(3)` or `/bin/sh -c`. Put each pipeline in
one process group, close unused file descriptors in parent and children, retry
appropriate interrupted calls, and reap all children. Builtins that modify
shell state must execute in the shell process when they are standalone
foreground commands.

Do not add credentials, network dependencies, generated binaries, core dumps,
or machine-specific absolute paths. Do not weaken tests or warning flags to hide
a defect. Keep error messages on stderr and do not let diagnostics become the
only source of state correctness.
