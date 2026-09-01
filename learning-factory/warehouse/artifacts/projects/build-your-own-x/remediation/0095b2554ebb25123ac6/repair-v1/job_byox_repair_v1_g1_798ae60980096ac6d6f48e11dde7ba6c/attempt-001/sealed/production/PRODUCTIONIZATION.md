# Productionization assessment

`MANIFEST.yaml` correctly sets `productionized` to `false`. This is an educational compiler and no production claim is made.

Before production use, at minimum:

- compile and test on pinned supported Go versions and operating systems;
- run race tests, sustained fuzzing with persisted corpora, static analysis, and dependency/license scans;
- impose configurable limits on bytes, tokens, nesting, locals, instructions, execution steps, and output;
- replace recursive hostile-input paths or enforce safe depth bounds;
- add cancellation and context propagation for library and CLI use;
- define bytecode ownership or expose an immutable validated representation;
- version any serialized source/AST/bytecode formats and document compatibility;
- define structured diagnostics, localization policy, and safe source excerpt handling;
- add telemetry hooks that do not leak source or identifiers;
- test I/O failures and large-stream behavior in the CLI;
- establish release signing, reproducible builds, vulnerability response, ownership, and an operational support policy;
- conduct an independent security and correctness review with evidence captured outside this generated pack.

No production implementation, service integration, benchmark threshold, availability target, or threat-model signoff was attempted. The benchmark functions are measurement scaffolding only.
