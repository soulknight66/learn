# Sealed design answers

1. A successful expression compilation increases abstract stack height by
   exactly one.  Each binary operator consumes two expression results and
   leaves one; a unary operator consumes and replaces one.

2. A patch handle names the reserved operand word.  The opcode remains fixed;
   the operand changes from a sentinel to the absolute offset of the first
   instruction after the relevant region.

3. Store a scope depth on every active symbol.  Lookup searches backward for
   shadowing, while duplicate detection searches only entries at the current
   depth.  Truncate entries when leaving a block.

4. Ember-C explicitly keeps the new name out of scope through its initializer.
   Compile the initializer before inserting the symbol.  An outer declaration
   with the same spelling is therefore visible.

5. For `a && b`, emit `a; JZ false; b; NOT; NOT; JMP end; false: PUSH 0`.
   For `a || b`, emit `a; JZ rhs; PUSH 1; JMP end; rhs: b; NOT; NOT`.  Both
   normalize their results and skip the right operand when required.

6. Signed addition, subtraction, and multiplication can overflow; negating
   `INT64_MIN` overflows; division and remainder by zero are invalid; and
   `INT64_MIN / -1` is unrepresentable.  The analogous remainder expression is
   also undefined in C even though its mathematical remainder would be zero.

7. The VM checks every slot.  Emitted code is not the only possible future
   input: a bytecode loader, cache corruption, or fuzzer can bypass the
   compiler.  Defense at the execution boundary prevents memory unsafety.

8. Increment the budget once immediately before dispatching each opcode.
   Operand words are data, not instructions.  A taken and non-taken conditional
   each charge the `JZ` once.

9. The tower supplies compiled words, and the guest dispatches those words; it
   never tokenizes source text or recognizes declarations.  Full source-level
   self-hosting would require the implementation, written inside the accepted
   source subset, to consume its own source and reproduce equivalent behavior.

10. Source, identifier, code, stack, local, and heap bounds are part of this
    challenge's observable contract.  A production design might negotiate or
    configure them, while retaining hard allocation ceilings.  The instruction
    budget naturally belongs to per-execution deployment policy, with a stable
    documented default.
