# Learner and agent guide

Work only in `starter/` for the implementation. Treat `REQUIREMENTS.md` as the behavioral contract
and `public_tests/` as examples rather than as the whole specification.

- Keep the entry point `_start`; the build helper links without libc.
- Use Linux system calls directly and preserve output-channel separation.
- Check every fixed-capacity structure before writing to it.
- Make malformed source fail deterministically with exit status 2.
- Use argv-based subprocess calls with timeouts, captured logs, and isolated process groups in any
  new test tooling.
- Do not place implementation answers, copied upstream material, or credentials in learner-visible
  paths.

Run the exact build and test commands in `README.md`. Do not claim success from prose or an exit from
an editing agent; retain command output as evidence. The `sealed/` tree belongs to the evaluator and
is outside the exercise surface.
