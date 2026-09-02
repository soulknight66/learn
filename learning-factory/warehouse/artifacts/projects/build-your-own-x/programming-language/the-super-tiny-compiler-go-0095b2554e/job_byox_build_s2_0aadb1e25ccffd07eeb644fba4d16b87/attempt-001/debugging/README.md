# Debugging exercises

These exercises contain minimal failing components, not the reference compiler.
Each answer is isolated inside that exercise's own `sealed/` directory.

- `lexer_position/`: a cursor reports column zero after a newline, shifting every
  subsequent token diagnostic.
- `jump_patch/`: a forward conditional skips the first else instruction and can
  reach a join with no value.

Run an exercise from its directory with `go test ./...` when Go is available.
First add or preserve a failing regression test, then repair the smallest
invariant. Do not move answer material into learner-facing directories.
