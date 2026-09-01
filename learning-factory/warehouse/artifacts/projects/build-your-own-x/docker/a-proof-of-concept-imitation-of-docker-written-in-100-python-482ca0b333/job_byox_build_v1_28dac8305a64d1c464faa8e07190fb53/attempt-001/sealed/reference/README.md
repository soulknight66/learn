# Reference implementation (sealed)

This directory contains an independent, standard-library Python implementation of the MiniBox contract. It is intentionally conservative: archive entries are validated before writes, lifecycle state is guarded in Python and SQLite, image publication is serialized per identifier, and runtime execution uses argv arrays with bounded in-memory capture.

Use it only for instructor evaluation:

```bash
PYTHONPATH=sealed/reference python3.11 -m unittest discover -s sealed/reference_tests -v
PYTHONPATH=sealed/reference python3.11 -m minibox --help
```

The runtime command planner is implemented, but a real namespace launch additionally needs host support and a populated rootfs. The reference is not production-ready; see `sealed/production/PRODUCTIONIZATION.md`.
