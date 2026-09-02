# Productionization plan

The reference is not productionized. Before accepting untrusted programs, place evaluation in a
separate constrained process; cap source bytes, token count, AST depth, constants, scopes, stack depth,
output bytes, and string size; add deadline/cancellation checks; and avoid exposing arbitrary file paths.

Add property-based and coverage-guided fuzzing for scanner/parser/VM validation, mutation tests for the
semantic suite, structured diagnostic codes, bytecode format versioning, and telemetry that excludes
source contents by default. Benchmark only after defining representative workloads and record hardware,
JVM flags, warm-up, distributions, and input hashes. Perform security review of any serialization or
embedding API. None of those claims are made by this artifact.
