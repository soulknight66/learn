# Exercise 01 answer: inconsistent work budgets

The patch does not define a shared unit. The tree backend charges one unit only
after a loop condition succeeds, while the VM charges every dispatched opcode.
A finite loop body with several expressions consumes one tree step per
iteration but many VM steps. Conversely, a large straight-line expression or a
chain of conditionals is unmetered by the tree backend. Even repeatedly
evaluating a final false condition is counted differently.

This is a high correctness issue if backend parity includes resource errors and
an availability issue wherever source is untrusted. It is not a secure process
isolation mechanism: one tree visit can still perform expensive host work, and
a bug outside the counter can hang.

Recommended design:

1. Document budgets as backend-specific implementation work, not as an exact
   language-level execution count, unless both engines consume a deliberately
   specified abstract fuel model.
2. For strict parity, call a shared `consumeFuel()` at defined semantic points
   such as expression evaluation, statement execution, condition checks, and
   assignments, and compile equivalent fuel-check instructions or metadata.
3. Reject non-integer, non-positive, or unreasonably large budget options at the
   API boundary and use one stable Pebble error code for exhaustion.
4. Test the exact boundary immediately below, at, and above the required fuel;
   include straight-line expressions, false conditions, empty bodies, and
   nested loops through both backends.
5. Retain an outer deadline or worker/process termination boundary for hostile
   input. Fuel improves determinism but cannot contain runtime or implementation
   defects.
