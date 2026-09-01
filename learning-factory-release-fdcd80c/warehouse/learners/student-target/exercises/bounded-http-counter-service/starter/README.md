# Starter

Fill in `http_service.py` without changing its exported contract. Begin with parser unit
tests, then the application state machine, then one bounded server architecture. Run:

```sh
PYTHONPATH=starter python3 -m unittest discover -s public_tests -v
```

Public tests are necessary but intentionally incomplete. Write tests for fragmented bodies,
overload, shutdown, concurrent increments, malformed framing, and injected handler failure.
