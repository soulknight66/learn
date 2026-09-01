# Sealed design rationale and question responses

This is solution-bearing evaluator material.

## Architecture

The reference uses a conventional four-stage flow:

```text
source bytes -> token array -> bytecode + slot count -> VM side effects
```

Tokens and instructions both carry one source point. Parsing emits bytecode
directly. Each precedence routine leaves exactly one expression result on the
conceptual stack. Each statement restores the prior stack height. Variable names
are resolved to stable integer slots at compile time.

The compiler's central invariants are:

- `FCurrent` names the next unconsumed token and never advances beyond EOF.
- expression compilation has stack effect `+1`;
- `print`, `let`, and assignment have net stack effect `0`;
- both paths of an `if` begin and end at the same stack height;
- a loop back-edge returns to the condition with its original stack height;
- every placeholder jump is patched exactly once to the current code length.

The VM increments and checks its step counter before dispatch, so instructions 1
through 100000 execute and instruction 100001 does not. Binary operations pop the
right operand first and the left operand second.

## Responses to the public design questions

1. An AST retains spans, syntactic grouping, names before resolution, and a shape
   that can be revisited. That enables type checking, constant folding, multiple
   backends, source formatting, and diagnostics covering whole expressions.
   Direct emission avoids AST allocation but commits early to one evaluation
   order and makes transformations awkward.

2. Lexical scope needs a stack of scope markers plus bindings annotated with
   depth. Entering `{` pushes a marker; declarations append bindings; leaving the
   block removes them (and possibly emits slot cleanup). Lookup searches from the
   newest binding backward, making shadowing natural. Mica deliberately uses a
   single name array instead.

3. Visibility during initialization permits self-reference syntactically but
   requires a rule for the value before assignment. It is useful for recursive
   functions only if functions and predeclared bindings exist. Delayed visibility
   catches accidental `let x = x` and is simpler for integer slots.

4. A condition is a temporary expression value. If `JUMP_IF_FALSE` only peeks,
   each loop iteration leaves another condition on the stack. Long-running loops
   then consume unbounded memory and break later stack-effect assumptions.

5. Store jumps as references to labels or basic blocks during transformation,
   then linearize and resolve labels after instruction insertion/removal. Numeric
   indices should be a final encoding, not the optimizer's identity model.

6. Distinct Booleans require value tags or a static type system, Boolean results
   for comparisons, and condition checks that reject integers. Arithmetic and
   equality rules must state whether coercions exist. The current Int64-only VM
   intentionally uses normalized results plus general truthiness.

7. Literal magnitude is known during lexing. Constant-expression overflow can be
   diagnosed during an optional fold, but nonconstant overflow belongs in VM
   execution. Pascal overflow flags are defense in depth, not language semantics,
   because build profiles vary. The reference computes within safe Int64 bounds
   and explicitly enforces Mica's narrower range.

8. Assign each opcode a required input height and stack delta, construct the
   control-flow graph, and propagate abstract heights from entry. Reject an edge
   that lacks operands or reaches a program point with a height different from an
   earlier edge. The direct compiler also supports a structural proof from parser
   routines, but validating bytecode independently protects the VM boundary.

9. Attach start and end byte offsets (or line/column pairs) to AST nodes and carry
   a source-map entry per instruction. An operator point is compact; a span can
   underline the complete failing expression and still retain operator precision.

10. A function activation record needs arguments, locals, a return address, and
    usually a link to the caller frame; closures add an environment link. `CALL`
    pushes or creates a frame, and `RETURN` restores the caller and transfers one
    result. Both are ordinary executed instructions and count toward the same
    global budget unless the language specifies per-call accounting.

11. Deterministic bytecode is a tooling contract here, not a condition for two
    programs to have the same language behavior. It makes golden tests,
    reproducible builds, diffs, and cache keys useful. A future optimizer could
    change bytecode while preserving source semantics, so the layers should be
    versioned separately.

12. Fuzz lexing/compilation in a mode that never invokes the VM, with a harness
    wall-clock timeout and bounded source size. Parser completion is distinct from
    runtime step exhaustion. Generated valid programs can then run separately and
    treat exit 70 with `instruction limit exceeded` as a defined result.
