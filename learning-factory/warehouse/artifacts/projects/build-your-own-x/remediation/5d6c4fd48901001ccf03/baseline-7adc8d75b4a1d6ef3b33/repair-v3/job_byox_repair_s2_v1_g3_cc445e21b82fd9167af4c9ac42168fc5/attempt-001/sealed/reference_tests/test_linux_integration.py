"""Opt-in Linux smoke test. Default discovery skips host-dependent execution."""

import json
import os
from pathlib import Path
import platform
import shutil
import tempfile
import unittest

from minictr.planner import build_launch_plan, build_preflight_plan
from minictr.runner import Runner
from minictr.spec import ContainerSpec


@unittest.skipUnless(os.environ.get("MINICTR_LINUX_INTEGRATION") == "1", "set MINICTR_LINUX_INTEGRATION=1")
class LinuxIntegrationTest(unittest.TestCase):
    def _fixture(self):
        if platform.system() != "Linux":
            self.skipTest("Linux is required")
        unshare = shutil.which("unshare")
        if unshare is None:
            self.skipTest("util-linux unshare is unavailable")
        dependencies = [Path("/bin/true"), Path("/lib64/libc.so.6"), Path("/lib64/ld-linux-x86-64.so.2")]
        if any(not item.is_file() for item in dependencies):
            self.skipTest("expected x86-64 /bin/true runtime dependencies are unavailable")
        return unshare, dependencies

    def test_true_in_disposable_writable_rootfs(self):
        unshare, dependencies = self._fixture()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "root"
            (root / "bin").mkdir(parents=True)
            (root / "lib64").mkdir()
            (root / "proc").mkdir()
            shutil.copy2(dependencies[0], root / "bin" / "true")
            shutil.copy2(dependencies[1], root / "lib64" / "libc.so.6")
            shutil.copy2(dependencies[2], root / "lib64" / "ld-linux-x86-64.so.2")
            spec = ContainerSpec.from_mapping(
                {
                    "id": "integration",
                    "rootfs": str(root),
                    "command": ["/bin/true"],
                    "timeout_seconds": 10,
                    "readonly_root": False,
                    "network": False,
                }
            )
            plan = build_launch_plan(spec, unshare)
            payload = json.dumps(spec.to_mapping(), sort_keys=True, separators=(",", ":")).encode()
            support = Runner().run(build_preflight_plan(spec, unshare), payload)
            self.assertFalse(support.timed_out, support.stderr.decode(errors="replace"))
            self.assertEqual(support.exit_code, 0, support.stderr.decode(errors="replace"))
            result = Runner().run(plan, payload)
            self.assertFalse(result.timed_out, result.stderr.decode(errors="replace"))
            self.assertEqual(result.exit_code, 0, result.stderr.decode(errors="replace"))

    def test_default_readonly_root_is_preflighted_before_workload(self):
        unshare, dependencies = self._fixture()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "root"
            (root / "bin").mkdir(parents=True)
            (root / "lib64").mkdir()
            (root / "proc").mkdir()
            shutil.copy2(dependencies[0], root / "bin" / "true")
            shutil.copy2(dependencies[1], root / "lib64" / "libc.so.6")
            shutil.copy2(dependencies[2], root / "lib64" / "ld-linux-x86-64.so.2")
            spec = ContainerSpec.from_mapping(
                {
                    "id": "readonly",
                    "rootfs": str(root),
                    "command": ["/bin/true"],
                    "timeout_seconds": 10,
                    "network": False,
                }
            )
            payload = json.dumps(spec.to_mapping(), sort_keys=True, separators=(",", ":")).encode()
            support = Runner().run(build_preflight_plan(spec, unshare), payload)
            if support.exit_code != 0 or support.timed_out:
                message = support.stderr.decode(errors="replace")
                self.assertFalse(support.timed_out, message)
                self.assertEqual(support.exit_code, 69, message)
                self.assertIn("UNSUPPORTED read-only root setup", message)
                self.assertIn("workload was not started", message)
                return
            result = Runner().run(build_launch_plan(spec, unshare), payload)
            self.assertFalse(result.timed_out, result.stderr.decode(errors="replace"))
            self.assertEqual(result.exit_code, 0, result.stderr.decode(errors="replace"))


if __name__ == "__main__":
    unittest.main()
