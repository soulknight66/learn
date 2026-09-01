# Agent instructions

Work only in `starter/`, `public_tests/`, and the learner-facing Markdown files. Treat `sealed/` and all evaluator-only directories as unavailable.

Preserve these rules:

- Use Python 3.11+ and the standard library only.
- Apply database schema changes through numbered files in `starter/migrations/`.
- Parameterize SQL. Lifecycle compare-and-transition operations must use `BEGIN IMMEDIATE`.
- Keep lifecycle changes within the transition graph enforced by the database trigger.
- Parse archives member by member; never call `extractall()`.
- Launch subprocesses with argv arrays, `shell=False`, captured output, a bounded timeout, and their own process group.
- Never weaken a test to make it pass. Add deterministic tests for every safety fix.
- Do not claim real container isolation when only an argv plan or host subprocess has been tested.

Run checks from the repository root:

```bash
PYTHONPATH=starter python3 -m unittest discover -s public_tests -v
python3 environment/probe_namespaces.py
```
