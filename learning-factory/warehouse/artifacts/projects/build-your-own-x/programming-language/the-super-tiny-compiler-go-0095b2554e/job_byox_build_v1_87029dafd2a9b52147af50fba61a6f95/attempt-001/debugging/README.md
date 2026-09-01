# Debugging exercises

These prompts are evaluator material. Their answers are isolated per exercise under `sealed/debugging/`.

## Scanner-position exercise

A candidate scanner reports the `(` in `# c\r\n(print 1)` at line 2, column 2, even though it should be column 1. Locate the smallest state-transition error, explain why tests containing only `\n` do not catch it, and propose a regression table including byte offsets.

## Compiler-stack exercise

A candidate compiler emits binary operands left-to-right but emits `OpPrint` before the expression's arithmetic opcode. Simple literal print tests pass; nested arithmetic fails bytecode validation with stack residue. Trace the abstract stack, identify the violated stage invariant, and propose the smallest structural test that catches it without running the VM.
