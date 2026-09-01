# Adversarial testing exercise

Design black-box tests that challenge Minibox's trust boundaries without relying on implementation
details. Run privileged cases only in a disposable VM.

Your test matrix should cover:

- container identifiers that could affect state-file selection;
- absolute, relative, empty, and `PATH`-resolved commands;
- traversal and symbolic links at each rootfs path component;
- malformed specifications, environment entries, hostnames, timeouts, and network modes;
- malformed or oversized helper messages;
- illegal and concurrent lifecycle updates;
- backend setup failure, nonzero target exit, timeout, signal, and controller interruption; and
- rootfs mutation between validation and execution.

For every case, record the input, the observable result, the state before and after, and which
invariant the test is intended to probe. Distinguish a rejected request, a launcher failure, and a
target program's nonzero exit. Do not treat output text as evidence of isolation.

Submit a table of cases plus automated tests. Label any case that requires privileges or a particular
kernel feature, and include safe cleanup instructions. A private discussion of expected findings is
available to instructors under the global `sealed/` tree.

