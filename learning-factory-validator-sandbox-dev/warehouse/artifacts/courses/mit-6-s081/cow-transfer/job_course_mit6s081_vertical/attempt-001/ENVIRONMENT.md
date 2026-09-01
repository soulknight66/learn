# Environment

The exercise uses Python 3.11+ and only the standard library so its state transitions are
easy to inspect. It models page-table behavior; it does not emulate RISC-V or replace xv6.

From this archive root, an operator can grade the preserved attempt with:

```sh
python3 examiner_only/grade_attempt.py
```

The grader imports only the submitted implementation, adds examiner tests from a separate
directory, writes `evaluations/attempt-001.json`, and exits nonzero on failure. A student view
should be made by copying `student_safe/` only. Network access is unnecessary.
