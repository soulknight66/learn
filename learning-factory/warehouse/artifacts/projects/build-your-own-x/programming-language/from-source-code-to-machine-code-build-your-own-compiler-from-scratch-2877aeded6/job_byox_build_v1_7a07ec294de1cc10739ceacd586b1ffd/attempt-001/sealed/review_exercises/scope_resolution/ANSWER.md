# Review findings: scope resolution

An inner `declare("x", inner_slot)` overwrites the outer slot. Leaving the block deletes `x`, so the
outer binding is lost and a later read or assignment fails. The overwrite also silently accepts a
duplicate declaration in the same scope, and lists of names become fragile when error paths leave a
block partially processed.

Use a stack of scope dictionaries. Reject a declaration already in the final dictionary, allow the
same name in earlier dictionaries, search from final to first on resolve, and pop exactly one complete
dictionary on block exit. Emit an initializer before inserting its declaration to preserve the stated
self-initializer rule.
