# Agent guide for the Mica challenge

Work only in `starter/` and learner-authored test files unless an instructor explicitly changes the
scope. A valid learner checkout is the allowlisted projection defined by
`environment/learner-view-policy.json`; it contains no `sealed` path. If such a path or instructor
reference material is present, stop and report a packaging-boundary failure without inspecting it.

Preserve the public module interfaces in `REQUIREMENTS.md`. Prefer small, deterministic functions,
ES modules, and Node built-ins; this project has no third-party dependencies. Diagnostics are part
of the public contract: retain stable codes and source spans rather than matching prose messages.

Run `node --test public_tests/*.test.mjs` after each stage. Public tests are deliberately incomplete,
so add your own boundary cases for malformed tokens, precedence, scope, jumps, and backend parity.
Do not weaken tests, special-case their source strings, or expose implementation answers in
learner-visible files.

Keep generated build products out of the repository. Do not add credentials, network calls,
subprocesses, symlinks, or package-manager dependencies.
