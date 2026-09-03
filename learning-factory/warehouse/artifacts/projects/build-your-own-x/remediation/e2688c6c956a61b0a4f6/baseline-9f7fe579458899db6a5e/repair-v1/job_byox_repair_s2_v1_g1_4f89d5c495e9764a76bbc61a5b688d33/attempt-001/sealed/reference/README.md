# Sealed reference implementation

This directory contains the complete fixed-capacity C implementation and a
freestanding AArch64 integration kernel. It is evaluator material and must not
be copied into a learner view.

`make all` compiles and runs hosted contract tests, deterministic adversarial
state sequences, then an AArch64 QEMU boot. The freestanding image uses the
PL011 device exposed by QEMU's `virt` machine and semihosting only to return an
exit status to the harness. It does not configure a Raspberry Pi peripheral,
hardware MMU, exception level, or persistent storage.

All compiler and emulator paths come from `environment/toolchain.mk`; no
network access or source checkout is used.
