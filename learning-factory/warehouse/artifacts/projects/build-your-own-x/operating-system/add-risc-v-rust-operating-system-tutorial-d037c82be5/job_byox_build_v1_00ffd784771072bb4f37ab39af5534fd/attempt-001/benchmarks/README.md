# Benchmark design (no results recorded)

No benchmark was executed on the generation host. If performance work is
required, first keep correctness tests separate, use release builds, record
Rust version/target/CPU, warm-up policy, sample count, input construction, and
raw observations, and do not infer RISC-V kernel performance from host timing.

Suggested deterministic workloads:

- schedule 1, 16, and 1024 always-ready processes for a fixed transition count;
- map/translate/unmap pages that share two, one, or zero table prefixes;
- create and list directories at several widths, and write sequential versus
  hole-extending file ranges;
- measure successful paths separately from typed failure/rollback paths.

Use `std::hint::black_box` and report distributions rather than a single best
time. Allocation counts and page-table-frame counts are useful deterministic
metrics even when elapsed time is too noisy. Any future numbers must be written
as observed evidence with the exact command and must not upgrade validation
labels automatically.
