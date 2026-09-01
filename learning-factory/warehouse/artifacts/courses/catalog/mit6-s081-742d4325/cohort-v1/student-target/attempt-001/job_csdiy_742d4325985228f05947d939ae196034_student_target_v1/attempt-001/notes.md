# Unit 0 Learner Notes

## Scope

These notes cover only `unit_kickoff_vmwalk_v1`, a small teaching model. It is not an xv6 or Sv39 implementation, an MIT lab submission, or evidence of completing MIT 6.S081.

## Contract extracted before implementation

- Address split: `L1 = (va >> 12) & 0xf`, `L2 = (va >> 8) & 0xf`, `offset = va & 0xff`.
- Successful translation: `physical = (PPN << 8) | offset`.
- Parsing has two phases: zero or more maps, then zero or more accesses.
- A valid access can yield `OK`, `UNMAPPED`, or `PERMISSION`; all three keep exit status 0.
- Trace errors are atomic: validate everything and emit no access lines if any line is invalid.
- Hard bounds are 128 bytes per logical line, 2,048 lines, 256 unique mappings, and 1,024 accesses.

## Concrete hypotheses and experiments

1. **Hypothesis:** fixed arrays are a better representation than dynamic allocation because every capacity is part of the contract. **Experiment:** fill all 256 table slots and translate both endpoint addresses. **Observation:** the full table is accepted and produces `0x0000` and `0xffff` as expected.
2. **Hypothesis:** storing accesses until end-of-file validation prevents partial standard output. **Experiment:** place a valid access before an illegal later map, and separately submit 1,025 accesses. **Observation:** both inputs return 2 with empty standard output.
3. **Hypothesis:** byte-wise input handling makes CRLF, an unterminated final line, non-ASCII input, and the exact 128-byte boundary unambiguous. **Experiment:** exercise each form in the black-box suite. **Observation:** permitted forms pass; overlong and malformed forms receive line diagnostics.
4. **Hypothesis:** presence and permission must be represented separately. **Experiment:** compare an absent entry with a read-only entry receiving a write request. **Observation:** the outputs distinguish `UNMAPPED` from `PERMISSION`.

## Production-engineering lessons

- Validation order is externally observable when output must be all-or-nothing.
- Limits should shape data structures and tests, not remain prose-only checks.
- Numeric parsing needs a pre-operation bound check; a wider accumulator alone is not a complete defense.
- Finding a compiler driver does not guarantee that its backend, headers, linker, or runtime libraries are discoverable in a sealed environment.
- Learner test success is reproducibility evidence, not controlled validation.
