# Adversarial validation material

The executable adversarial suite is sealed at
`sealed/reference_tests/test_adversarial.c`. It uses a fixed PRNG seed and
4,000 operations per subsystem, checks state-machine invariants after every
step, and confirms that rejected mutations leave byte-identical state.

This directory contains no learner solution and no claimed fuzzing evidence.
The sequence test is deterministic robustness coverage; it was not generated
or controlled by an independent fuzzer, so the artifact does not carry a
`FUZZED` label.
