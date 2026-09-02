# Sealed implementation review

The reference is designed to satisfy the written educational contract under its sealed test suite. Its
strongest properties are separated parsing/evaluation, exact boolean/integer boundaries, lexical closure
parenting, left-to-right effects, controlled CLI errors, and loop-based tail calls verified at 6,000
iterations.

It is not production ready. Important residual risks are:

- no total source-size, token-count, allocation, output, or instruction budget beyond the documented
  10,000-digit integer-token and 256-level syntax limits;
- host callers can construct cyclic lists outside the language; the iterative formatter and equality
  walker do not detect every such embedding violation and may fail to terminate;
- returned and quoted host lists can be mutated by an embedding application;
- the CLI reads an entire file before parsing and the interactive prompt accepts only one physical line;
- error messages contain source positions but not filenames, spans, or escaped excerpts;
- malformed hand-built bytecode can form an infinite jump loop because the VM has no execution budget;
- no packaging metadata, compatibility matrix, concurrency contract, observability hooks, or long-running
  process tests are supplied; and
- performance and security properties have not been independently benchmarked, fuzzed, or audited.

The optional VM is an equivalence exercise for a stated subset, not an optimization claim or sandbox. The
artifact should remain `GENERATED` + `PARTIAL` until independent validators rerun commands and examine the
learner/reference boundary.
