# Review: trusted operands

A patch removes constant-index, jump-target, opcode, and stack checks from `run` because `compile`
normally emits valid chunks. Review the change under the documented public `run(chunk)` API. Which
failures could become nondeterministic host behavior, and what trust-boundary alternative could
justify a faster execution loop?
