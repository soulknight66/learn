# Sealed adversarial plan

Independent validators may derive cases from these risk classes rather than trusting the generated
suite:

- every token prefix and suffix around built-in spellings;
- embedded bytes 0x00 through 0x20 and bytes above ASCII;
- signed-decimal extrema, very long zero strings, and overflow near each digit update;
- all operations at stack depths zero, one, 255, and 256;
- compile errors after many output instructions to verify zero output;
- runtime errors after output to verify non-rollback;
- pipe delivery in single-byte reads and source lengths 4095, 4096, and larger;
- closed or faulting standard streams;
- mutation of compiled opcodes under a dedicated harness.

This is a plan, not evidence that fuzzing or adversarial validation occurred.

