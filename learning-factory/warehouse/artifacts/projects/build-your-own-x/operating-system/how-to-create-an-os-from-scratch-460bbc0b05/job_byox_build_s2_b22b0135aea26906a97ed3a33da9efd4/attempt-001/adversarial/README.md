# Adversarial test stage

After the public suite passes, add tests that combine ordinary operations in inconvenient orders:
all tables full, every process blocked, duplicate virtual pages with busy frames, EOF at exact file
capacity, exit with mappings and descriptors, invalid booleans, unterminated names, and output
sentinels on every error.

Also mutate a copy of public state and call `cairn_validate`. Start with out-of-range descriptor and
frame indices because an invariant checker that follows them before checking bounds can itself become
the memory-safety bug.

The deterministic sealed driver uses a fixed seed and checks invariants after every operation. Do not
interpret its operation count as fuzzing coverage or a `FUZZED` validation label.
