# Durable Event Processing Service

Build and operate a deliberately boring service: accept idempotent events, claim work with
durable leases, retry transient failures, quarantine poison messages, and expose enough
state to debug an incident. Python 3.11 and SQLite keep every transaction boundary visible.
There are no packages to install and no network dependency.

This challenge is **agent-generated cross-source synthesis**. It was synthesized from the
learning factory's CSDIY and Build Your Own X topic catalogs; it does not copy a tutorial or
claim to be an upstream project. See `PROVENANCE.json`.

## Progressive path

1. Read `REQUIREMENTS.md`, `CONCEPTS.md`, and `DESIGN_QUESTIONS.md`.
2. Work only in `starter/`; run `PYTHONPATH=starter python3 -m unittest discover -s public_tests -v`.
3. Use `environment/materialize_student_view.py` to create an actual view with no sealed,
   hidden-test, production-candidate, debugging-answer, or review-answer files.
4. After implementing, reveal `sealed/reference_tests/`, then `sealed/reference/` and its design.
5. Reproduce the lost-ack crash, concurrency stress, model fuzz, bug hunt, and review PR.
6. Run the benchmark and interpret its raw samples before reading production gaps.

```sh
# Full controller-owned bounded validation (includes a fresh benchmark)
python3 scripts/run_all.py

# Keyset-paginated local administration example
PYTHONPATH=sealed/reference python3 sealed/reference/event_service.py           --db /tmp/event-learning.db ingest demo-1 '{"kind":"email"}'
PYTHONPATH=sealed/reference python3 sealed/reference/event_service.py           --db /tmp/event-learning.db list --limit 20 --after 0
```

Passing the included checks supports `BUILDS`, `TESTED`, `FUZZED`, `BENCHMARKED`, and
`REVIEWED`, always alongside `PARTIAL`. This is explicitly **not production-ready** and no
validator may claim `PRODUCTIONIZED`. The local effect table demonstrates duplicate
suppression; it cannot make an arbitrary remote side effect atomic with SQLite.
