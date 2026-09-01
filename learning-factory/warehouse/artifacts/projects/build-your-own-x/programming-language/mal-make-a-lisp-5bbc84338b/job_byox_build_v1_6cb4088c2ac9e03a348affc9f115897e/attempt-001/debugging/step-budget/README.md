# Exercise: the final permitted step fails

Run:

```bash
python3 -m unittest discover -s debugging/step-budget -p 'test_*.py' -v
```

The counter should allow exactly `limit` calls to `consume()` and reject the next one. Diagnose why a
limit of three currently permits only two successful calls. Propose the smallest fix and add boundary
coverage for limits zero and one. Do not change the required error code.
