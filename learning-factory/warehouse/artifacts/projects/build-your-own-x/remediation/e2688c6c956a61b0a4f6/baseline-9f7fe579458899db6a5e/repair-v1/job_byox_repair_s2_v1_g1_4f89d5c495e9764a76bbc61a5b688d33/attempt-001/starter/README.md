# Starter workspace

The header is the immutable exercise ABI. The three source files initialize
their fixed-size objects but leave behavior-changing operations as explicit
TODO stubs. The stubs are safe and warning-clean; they are not a solution.

Use `make compile` for a compile-only checkpoint and `make test` to build and
run the public suite. Do not change constants or structure layouts, since
additional validators compile against this header. Keep implementation helpers
`static` inside their owning source file.

Suggested implementation order is lookup/validation helpers, process
transitions, virtual mappings, then filesystem namespace and I/O. Re-run the
whole test suite after each phase because failure atomicity crosses helper
boundaries.
