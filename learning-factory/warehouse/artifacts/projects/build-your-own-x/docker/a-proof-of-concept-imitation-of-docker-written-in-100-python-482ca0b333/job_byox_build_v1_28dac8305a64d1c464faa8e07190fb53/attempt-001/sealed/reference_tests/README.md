# Sealed reference tests

These tests exercise lifecycle races, archive attack shapes, output limits, timeouts, launch failure, environment isolation, workspace provenance, and CLI serialization beyond the public examples.

Run from the repository root with Python 3.11+:

```bash
PYTHONPATH=sealed/reference python3.11 -m unittest discover -s sealed/reference_tests -v
```

They use a direct host-process test backend for `Runner`; they do not claim that Linux namespace creation works on the host.
