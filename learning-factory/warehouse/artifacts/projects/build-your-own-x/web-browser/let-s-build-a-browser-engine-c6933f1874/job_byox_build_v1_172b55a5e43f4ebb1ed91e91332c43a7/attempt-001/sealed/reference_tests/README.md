# Sealed conformance tests

`conformance.rs` exercises limit boundaries, malformed protocol input, parser structure, cascade ordering, box flow, paint order, and end-to-end policy. A small integration-test wrapper includes it in the reference crate.

These tests supplement rather than weaken the normative requirements. Independent validators should add their own cases and must not expose this directory to learners.
