import tempfile
import unittest
from pathlib import Path

from minibox.config import from_dict
from minibox.runtime import ExecutionResult, Runtime
from minibox.state import StateStore


class RecordingBackend:
    def __init__(self, result=None, error=None):
        self.result = result
        self.error = error
        self.calls = []

    def run(self, spec):
        self.calls.append(spec)
        if self.error is not None:
            raise self.error
        return self.result


class RuntimePublicTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        base = Path(self.temporary_directory.name)
        rootfs = base / "rootfs"
        rootfs.mkdir()
        self.spec = from_dict(
            {
                "schema_version": 1,
                "rootfs": str(rootfs),
                "argv": ["/bin/program"],
            }
        )
        self.store = StateStore(base / "states", clock=lambda: 50.0)

    def test_success_returns_output_and_records_exited_state(self):
        expected = ExecutionResult(exit_code=0, stdout=b"hello\n", stderr=b"")
        backend = RecordingBackend(result=expected)

        actual = Runtime(self.store, backend).run(self.spec, "success")

        self.assertEqual(actual, expected)
        self.assertEqual(backend.calls, [self.spec])
        state = self.store.get("success")
        self.assertEqual(state.status, "EXITED")
        self.assertEqual(state.exit_code, 0)
        self.assertIsNone(state.error)
        self.assertEqual(state.revision, 2)

    def test_nonzero_exit_is_a_completed_execution_not_runtime_failure(self):
        result = ExecutionResult(exit_code=23, stdout=b"", stderr=b"bad input")

        returned = Runtime(self.store, RecordingBackend(result=result)).run(
            self.spec, "nonzero"
        )

        self.assertEqual(returned.exit_code, 23)
        state = self.store.get("nonzero")
        self.assertEqual(state.status, "EXITED")
        self.assertEqual(state.exit_code, 23)

    def test_backend_exception_is_recorded_as_failed_and_reraised(self):
        failure = RuntimeError("backend exploded")
        backend = RecordingBackend(error=failure)

        with self.assertRaises(RuntimeError) as caught:
            Runtime(self.store, backend).run(self.spec, "failed")

        self.assertIs(caught.exception, failure)
        state = self.store.get("failed")
        self.assertEqual(state.status, "FAILED")
        self.assertIsNone(state.exit_code)
        self.assertIn("backend exploded", state.error)
        self.assertEqual(state.revision, 2)


if __name__ == "__main__":
    unittest.main()
