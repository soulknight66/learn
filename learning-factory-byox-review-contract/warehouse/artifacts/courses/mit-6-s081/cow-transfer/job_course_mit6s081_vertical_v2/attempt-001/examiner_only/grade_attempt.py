from __future__ import annotations

import io
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SUBMISSION = ROOT / "attempts/target-learner/attempt-001/submission"


def main() -> int:
    sys.path.insert(0, str(SUBMISSION))
    suite = unittest.TestSuite(
        [
            unittest.TestLoader().discover("student_safe/public_tests", pattern="test_*.py"),
            unittest.TestLoader().discover("examiner_only/hidden_tests", pattern="test_*.py"),
        ]
    )
    stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
    report = {
        "attempt_id": "target-learner-attempt-001",
        "evaluator": "independent deterministic examiner",
        "result": "PASS" if result.wasSuccessful() else "FAIL",
        "tests_run": result.testsRun,
        "failures": len(result.failures),
        "errors": len(result.errors),
        "skipped": len(result.skipped),
        "evidence": stream.getvalue().splitlines(),
    }
    destination = ROOT / "evaluations/attempt-001.json"
    destination.parent.mkdir(exist_ok=True)
    destination.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(stream.getvalue(), end="")
    print(json.dumps({key: report[key] for key in ("result", "tests_run", "failures", "errors")}))
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
