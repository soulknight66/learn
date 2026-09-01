# Reference tests

The deterministic suite replaces the isolation boundary with regular-file fake
executables. It checks lifecycle transitions, exact argv preservation,
injection resistance, child output/status propagation, verified running PIDs,
stale metadata recovery, safe deletion, and the complete namespace/mount/chroot
argv without requiring root:

```bash
bash sealed/reference_tests/run.sh
```

`real_integration.sh` is an opt-in host capability probe. It compiles a tiny
static binary locally into a temporary rootfs; it performs no download and does
not copy an image. Unsupported compilers or kernel namespace policy produce an
explicit `SKIP`:

```bash
bash sealed/reference_tests/real_integration.sh
MINICTR_RUN_REAL_TESTS=1 bash sealed/reference_tests/real_integration.sh
```

The real probe is environmental evidence only. It does not make this
educational runtime production-ready or replace independent validation.
