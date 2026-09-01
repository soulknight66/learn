# Debugging exercises

Each exercise provides an isolated defective snippet, a symptom, and questions. Diagnose without
looking at the companion material under the root `sealed/debugging/` tree.

- `lexer_cursor/`: EOF and CRLF position corruption.
- `jump_patch/`: branch destinations that look plausible in a disassembly but fail validation.

The snippets are intentionally not imported by either implementation or test suite.
