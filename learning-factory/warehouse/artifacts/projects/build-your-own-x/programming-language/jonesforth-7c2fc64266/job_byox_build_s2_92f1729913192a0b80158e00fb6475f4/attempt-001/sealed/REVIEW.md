# Implementation review

## What was checked

- Every externally supplied token comparison uses an explicit byte length.
- Dictionary publication happens after a successfully emitted RET.
- Data, code, control, return, name, and input capacities are checked before writes.
- Signed conversion accepts both int64 endpoints and distinguishes overflow from lookup failure.
- Signed division handles zero and the one hardware-overflow pair before `idiv`.
- VM calls use a separate bounded return stack and an instruction counter.
- System-call writes account for partial completion and `EINTR`.
- Public and sealed tests launch the executable without a shell and with timeouts.

## Known limitations

The executable assumes Linux x86-64 and an ET_EXEC load address. Absolute compiled branch pointers
are not serializable. Diagnostics identify error classes but omit source positions and offending
tokens. The read-all model is batch-only. There is no signal policy, sandbox, memory protection
between VM structures, dictionary deletion, persistence, optimizer, or interactive recovery.

The million-instruction fuel check is defense in depth; under the current instruction set, recursive
nontermination reaches the smaller 256-continuation limit first and a nonrecursive body cannot fill a
million operations in the 8,192-cell arena. Keeping fuel still prevents a future backward-branch
feature from silently creating unbounded execution.

## Review disposition

The locally generated reference and tests are suitable as an educational oracle for the stated
contract. They are not independently validated, fuzzed, benchmarked, transfer-verified, or reviewed
for production deployment. `MANIFEST.yaml` therefore remains `GENERATED` + `PARTIAL` and
`productionized` remains false.
