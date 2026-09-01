# Bounded kickoff submission

The collision-risk kickoff/first unit is implemented and locally validated.
This is not a claim of completing UCB CS126 or any unverified official
assignment or lab.

Primary artifacts:

- `submission/README.md` — offline commands and API/output contract
- `submission/report.md` — derivation, numerical method, complete experiment
  summary, interpretation, provenance, and limitations
- `submission/comprehension.md` — responses to all ten questions
- `submission/src/collision_lab/` — importable model, simulation, interval,
  and CLI implementation
- `submission/tests/test_collision_lab.py` — deterministic `unittest` suite
- `submission/results/` — six versioned JSON experiment records
- `notes.md` and `debugging-log.md` — hypotheses, observations, failures, and
  production-engineering lessons

Validation from `submission/`:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

Local result on Python 3.6.8: 12 tests passed. The required experiment matrix
used 20,000 trials per row and one preselected seed, `1262020`; all six exact
probabilities were inside their recorded Wilson intervals. That outcome is
reported as stochastic consistency evidence, while the test result is local
deterministic validation evidence.
