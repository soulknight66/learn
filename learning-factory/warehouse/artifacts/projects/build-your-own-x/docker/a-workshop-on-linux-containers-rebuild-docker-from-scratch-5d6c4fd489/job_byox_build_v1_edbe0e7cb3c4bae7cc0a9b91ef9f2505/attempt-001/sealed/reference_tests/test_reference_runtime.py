import tempfile
import unittest
from dataclasses import fields, is_dataclass
from pathlib import Path
from unittest import mock

from minibox.config import from_dict
from minibox.errors import BackendError, BackendUnavailable, StateError
from minibox.runtime import ExecutionResult, LinuxSubprocessBackend, Runtime
from minibox.state import StateStore


class StaticBackend:
    def __init__(self, result=None, exception=None, observer=None):
        self.result = result
        self.exception = exception
        self.observer = observer
        self.calls = []

    def run(self, spec):
        self.calls.append(spec)
        if self.observer is not None:
            self.observer()
        if self.exception is not None:
            raise self.exception
        return self.result


class RuntimeReferenceTests(unittest.TestCase):
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
                "argv": ["/bin/tool", "arg"],
            }
        )
        self.store = StateStore(base / "states", clock=lambda: 123.0)

    def test_execution_result_is_the_three_field_dataclass(self):
        result = ExecutionResult(exit_code=9, stdout=b"out", stderr=b"err")

        self.assertTrue(is_dataclass(result))
        self.assertEqual(
            tuple(field.name for field in fields(result)),
            ("exit_code", "stdout", "stderr"),
        )
        self.assertEqual(result.exit_code, 9)
        self.assertEqual(result.stdout, b"out")
        self.assertEqual(result.stderr, b"err")

    def test_state_is_running_before_backend_is_called(self):
        observed_statuses = []
        result = ExecutionResult(0, b"output", b"")
        backend = StaticBackend(
            result=result,
            observer=lambda: observed_statuses.append(
                self.store.get("observed").status
            ),
        )

        returned = Runtime(self.store, backend).run(self.spec, "observed")

        self.assertIs(returned, result)
        self.assertEqual(observed_statuses, ["RUNNING"])
        self.assertEqual(backend.calls, [self.spec])
        final = self.store.get("observed")
        self.assertEqual(final.status, "EXITED")
        self.assertEqual(final.exit_code, 0)
        self.assertEqual(final.revision, 2)

    def test_all_integer_exit_codes_including_nonzero_finish_as_exited(self):
        for index, exit_code in enumerate((-9, 1, 255)):
            with self.subTest(exit_code=exit_code):
                container_id = "exit-{}".format(index)
                result = ExecutionResult(exit_code, b"stdout", b"stderr")
                returned = Runtime(
                    self.store, StaticBackend(result=result)
                ).run(self.spec, container_id)
                self.assertEqual(returned, result)
                state = self.store.get(container_id)
                self.assertEqual(state.status, "EXITED")
                self.assertEqual(state.exit_code, exit_code)
                self.assertIsNone(state.error)

    def test_backend_unavailable_is_recorded_then_same_exception_is_reraised(self):
        error = BackendUnavailable("unshare is unavailable")
        backend = StaticBackend(exception=error)

        with self.assertRaises(BackendUnavailable) as caught:
            Runtime(self.store, backend).run(self.spec, "unavailable")

        self.assertIs(caught.exception, error)
        state = self.store.get("unavailable")
        self.assertEqual(state.status, "FAILED")
        self.assertIn("unshare is unavailable", state.error)
        self.assertIsNone(state.exit_code)
        self.assertEqual(state.revision, 2)

    def test_arbitrary_backend_exception_is_durable_after_reraise(self):
        error = ValueError("bad backend response")

        with self.assertRaises(ValueError):
            Runtime(self.store, StaticBackend(exception=error)).run(
                self.spec, "backend-error"
            )

        reopened = StateStore(
            Path(self.temporary_directory.name) / "states", clock=lambda: 999.0
        )
        state = reopened.get("backend-error")
        self.assertEqual(state.status, "FAILED")
        self.assertIn("bad backend response", state.error)

    def test_invalid_execution_result_fields_are_backend_failures(self):
        invalid_results = (
            ExecutionResult(True, b"", b""),
            ExecutionResult("0", b"", b""),
            ExecutionResult(0, "text", b""),
            ExecutionResult(0, b"", bytearray()),
        )
        for index, result in enumerate(invalid_results):
            container_id = f"invalid-result-{index}"
            with self.subTest(result=result):
                with self.assertRaises(BackendError):
                    Runtime(self.store, StaticBackend(result=result)).run(
                        self.spec, container_id
                    )
                self.assertEqual(self.store.get(container_id).status, "FAILED")

    def test_backend_exception_survives_failed_failure_recording(self):
        class BrokenFailureStore:
            def create(self, container_id):
                return None

            def transition(self, container_id, expected, target, **kwargs):
                if target == "FAILED":
                    raise StateError("state disk unavailable")
                return None

        original = RuntimeError("original backend failure")
        runtime = Runtime(BrokenFailureStore(), StaticBackend(exception=original))

        with self.assertRaises(RuntimeError) as caught:
            runtime.run(self.spec, "recording-fails")

        self.assertIs(caught.exception, original)
        if hasattr(original, "__notes__"):
            self.assertTrue(
                any("state disk unavailable" in note for note in original.__notes__)
            )

    def test_existing_container_prevents_backend_invocation(self):
        self.store.create("duplicate")
        backend = StaticBackend(result=ExecutionResult(0, b"", b""))

        with self.assertRaises(StateError):
            Runtime(self.store, backend).run(self.spec, "duplicate")

        self.assertEqual(backend.calls, [])
        self.assertEqual(self.store.get("duplicate").status, "CREATED")

    def test_linux_backend_is_available_as_a_concrete_api_without_running_it(self):
        self.assertIsInstance(LinuxSubprocessBackend, type)
        self.assertTrue(callable(getattr(LinuxSubprocessBackend, "run", None)))

    def test_linux_backend_unavailable_program_fails_before_process_start(self):
        missing_unshare = str(
            Path(self.temporary_directory.name) / "missing-unshare"
        )
        backend = LinuxSubprocessBackend(
            unshare_path=missing_unshare,
            python_path="/also/not/used/python",
        )

        with mock.patch("minibox.runtime.subprocess.Popen") as popen:
            with self.assertRaises(BackendUnavailable):
                Runtime(self.store, backend).run(self.spec, "missing-program")

        popen.assert_not_called()
        state = self.store.get("missing-program")
        self.assertEqual(state.status, "FAILED")
        self.assertIn("BackendUnavailable", state.error)
        self.assertIn("unshare", state.error)
        self.assertEqual(state.revision, 2)

    def test_linux_backend_validates_output_limit_at_construction(self):
        for limit in (1, 16_777_216):
            with self.subTest(accepted=limit):
                backend = LinuxSubprocessBackend(
                    unshare_path="/not-run/unshare",
                    python_path="/not-run/python",
                    max_output_bytes=limit,
                )
                self.assertEqual(backend.max_output_bytes, limit)

        for limit in (0, -1, 16_777_217, True, False, 1.5, "1024", None):
            with self.subTest(rejected=limit):
                with self.assertRaises(ValueError):
                    LinuxSubprocessBackend(
                        unshare_path="/not-run/unshare",
                        python_path="/not-run/python",
                        max_output_bytes=limit,
                    )


if __name__ == "__main__":
    unittest.main()
