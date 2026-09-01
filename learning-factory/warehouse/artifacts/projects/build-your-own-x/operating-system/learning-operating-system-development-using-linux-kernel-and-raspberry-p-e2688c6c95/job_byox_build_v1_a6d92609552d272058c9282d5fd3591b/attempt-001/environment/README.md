# Build environment

The portable core requires a C11 compiler, `make`, and a POSIX-like command environment. Run:

```sh
sh environment/check.sh
```

The check is observational: it does not install packages or access the network. GCC 8 or newer is sufficient for the host model.

A Raspberry Pi 3/4 bare-metal experiment normally also needs an AArch64 bare-metal cross-compiler and either hardware with a serial connection or an AArch64 system emulator. Tool presence alone is not evidence that an image boots, and absence does not affect the host milestones. This generated artifact is marked `PARTIAL` because no target toolchain or hardware execution is available in the recorded environment.
