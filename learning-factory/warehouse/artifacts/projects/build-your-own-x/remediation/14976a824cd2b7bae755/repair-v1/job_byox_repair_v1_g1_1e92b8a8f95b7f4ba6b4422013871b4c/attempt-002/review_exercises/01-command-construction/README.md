# Review 1: command construction and state paths

Review `candidate.sh`, a proposed implementation of create, run, and delete.
It is a static review artifact, not a runnable starter. Assume all CLI values
are attacker-controlled and `MINICTR_HOME` itself is a trusted absolute path.

Produce a prioritized review. Look for distinct root causes rather than merely
listing every line on which one bug appears. At minimum, reason about exact
argv preservation, path containment, concurrent creators, rootfs metadata,
option-like values, and error propagation.

