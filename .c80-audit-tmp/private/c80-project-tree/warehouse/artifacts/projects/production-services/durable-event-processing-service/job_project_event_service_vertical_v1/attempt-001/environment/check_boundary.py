import subprocess
import sys
import tempfile
from pathlib import Path


root = Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory(prefix="event-student-boundary-") as temporary:
    view = Path(temporary) / "student"
    completed = subprocess.run(
        [sys.executable, str(root / "environment/materialize_student_view.py"), str(view)],
        check=False,
        text=True,
        capture_output=True,
    )
    if completed.returncode != 0:
        raise SystemExit(completed.stderr)
    forbidden = [
        view / "sealed",
        view / "benchmarks",
        view / "debugging",
        view / "review_exercises",
        view / "production",
    ]
    if any(path.exists() for path in forbidden):
        raise SystemExit("student view leaked a reveal-only path")
    names = {path.name for path in view.rglob("*")}
    if "reference_tests" in names or "EXPECTED_REVIEW.md" in names:
        raise SystemExit("student view leaked withheld filenames")
    print("materialized student view contains only explicit learner-safe inputs")
