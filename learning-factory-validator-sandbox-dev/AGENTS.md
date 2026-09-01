# Learning Factory agent guide

This repository is a deterministic control plane around probabilistic workers. Keep job state,
ownership, leases, retries, timestamps, validation, and artifact locations in SQLite or deterministic
code. An agent's prose claim is never evidence of completion.

## Commands

Run commands from the repository root with `PYTHONPATH=src`:

```bash
python3 -m learnfactory init
python3 -m unittest discover -s tests -v
python3 -m learnfactory status
python3 -m learnfactory run --until-idle
```

## Invariants

- Apply schema changes only through a numbered migration in `migrations/`.
- Use parameterized SQL and explicit transactions; atomic claims use `BEGIN IMMEDIATE`.
- State changes must follow the database-enforced transition table.
- Never place secrets, hidden graders, sealed references, or another student's files in a student view.
- Source repositories are read-only inputs. Workers operate only in per-attempt workspaces.
- Only validators controlled by the worker harness can promote a job to `SUCCEEDED`.
- Preserve durable failed attempts and evidence; scratch build products may be removed explicitly.
- Subprocesses use argv arrays, bounded timeouts, process groups, and captured logs—never shell strings.

## Quality bar

Add deterministic `unittest` coverage for changes to scheduling, persistence, isolation, validation,
or ingestion. Generated artifacts must record provenance and explicit validation labels.
