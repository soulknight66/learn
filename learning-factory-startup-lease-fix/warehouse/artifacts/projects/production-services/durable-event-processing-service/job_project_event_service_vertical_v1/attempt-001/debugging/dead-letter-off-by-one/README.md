# Debugging challenge: poison message never dies on schedule

With `max_attempts=2`, the second failed delivery should enter the DLQ. The buggy service grants
another retry. Reproduce with `PYTHONPATH=buggy python3 regression.py`. Find one root cause,
explain the operational harm, write a regression, and propose safe handling of messages already
over budget. Reveal `sealed/` only afterward.
