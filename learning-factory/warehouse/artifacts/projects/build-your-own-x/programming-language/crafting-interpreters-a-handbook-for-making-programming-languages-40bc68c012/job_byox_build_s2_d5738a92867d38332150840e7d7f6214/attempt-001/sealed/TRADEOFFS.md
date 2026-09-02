# Tradeoffs

- The VM stores variable names and performs scope-chain lookup at runtime. Slot allocation would be
  faster and catch some errors earlier, but would obscure the first compiler milestone.
- The AST uses Java records and `instanceof` dispatch. A visitor would make adding operations easier;
  records keep the learner-facing representation compact.
- Only ASCII identifiers are accepted. Unicode identifier policy is valuable but requires normalization
  and security decisions outside this challenge.
- Mica reports the first lexical or parse error. Error recovery would improve editor use but complicate
  deterministic expected diagnostics.
- A fixed execution budget is deterministic and portable. It is not a substitute for memory limits or
  process isolation in an untrusted production service.
- Bytecode constants contain ordinary Java values and variable names. A serialized format would need
  explicit versioning, bounds, checksums, and a decoder with allocation limits.
