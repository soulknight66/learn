# Sealed reference tests

These instructor-controlled tests cover strict parsing, path containment, namespace argv
construction, database transitions, competing claims, subprocess timeout behavior, and child setup
order. They use only temporary files and fakes; none launches `unshare` or calls `chroot`.

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=sealed/reference \
  python3 -m unittest discover -s sealed/reference_tests -v
```

The optional kernel probe is separate in `environment/check_host.py`. Unit success is not evidence
that the optional privileged path works or is secure against an adversarial process.

On a disposable Linux builder with compatible `/bin/true` runtime libraries, the explicit opt-in
smoke test is:

```bash
MINICTR_LINUX_INTEGRATION=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=sealed/reference \
  python3 -m unittest sealed/reference_tests/test_linux_integration.py -v
```

It copies three host runtime files into a temporary, writable rootfs and removes that rootfs on exit.
A pass is only a single benign-workload smoke test; read-only-remount behavior is separately
host/filesystem-dependent.
