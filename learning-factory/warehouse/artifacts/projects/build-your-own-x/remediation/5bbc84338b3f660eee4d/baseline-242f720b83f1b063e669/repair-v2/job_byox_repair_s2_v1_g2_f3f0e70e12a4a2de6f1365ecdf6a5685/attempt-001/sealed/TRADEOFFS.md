# Sealed tradeoffs and alternatives

## Shared syntax/value lists

Sharing representations makes quote, equality, and printing compact. Separate immutable syntax nodes
would preserve locations after parsing and prevent host mutation, at the cost of a conversion step for
quoted data. A diagnostic-focused implementation should favor explicit nodes.

## Exceptions versus result values

Language-specific exceptions keep the straight-line evaluator readable and give the CLI one boundary to
handle. Explicit result values would make all error flow visible and can be easier to port to languages
without exceptions, but they add propagation code around every recursive call.

## Environment chains versus resolved slots

Dictionary chains explain lexical scope directly and make a REPL flexible. A compiler could resolve locals
to numbered slots, detect some absent names earlier, and reduce lookup cost. That would require separate
handling for globals and closed-over cells.

## Loop-based tail calls versus a trampoline

Updating `(form, environment)` inside the evaluator minimizes allocations and naturally handles required
tail positions. A trampoline that returns explicit continuation records can separate control decisions
more cleanly and support instrumentation, but allocates a record per bounce. Neither addresses deeply
nested non-tail syntax without a broader explicit control stack.

## Narrow bytecode subset versus whole-language compilation

The supplied compiler is intentionally honest: it rejects lexical bindings and functions. Extending it
requires local slots, closure capture descriptors, call frames, and tail-call instructions. Falling back
silently to the interpreter would obscure which execution model a test exercised, so the reference does
not do that.
