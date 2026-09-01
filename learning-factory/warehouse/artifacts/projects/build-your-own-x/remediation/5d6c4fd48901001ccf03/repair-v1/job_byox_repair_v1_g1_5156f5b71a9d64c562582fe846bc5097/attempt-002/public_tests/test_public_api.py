import unittest

import minibox


class PublicPackageSurfaceTests(unittest.TestCase):
    def test_documented_values_are_exported_from_package_root(self):
        expected = {
            "BackendError",
            "BackendTimeout",
            "BackendUnavailable",
            "ContainerSpec",
            "ContainerState",
            "ExecutionResult",
            "IsolationPlan",
            "LinuxSubprocessBackend",
            "MiniboxError",
            "RootfsError",
            "Runtime",
            "SpecError",
            "StateCommitUncertain",
            "StateError",
            "StateStore",
            "build_plan",
            "from_dict",
            "load_spec",
            "resolve_executable",
        }

        self.assertTrue(expected.issubset(set(minibox.__all__)))
        for name in expected:
            self.assertTrue(hasattr(minibox, name), name)


if __name__ == "__main__":
    unittest.main()
