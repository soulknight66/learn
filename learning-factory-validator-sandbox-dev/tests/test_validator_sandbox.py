from __future__ import annotations

import json
import os
import signal
import shutil
import subprocess
import tempfile
import threading
import time
import tracemalloc
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

import learnfactory.validator_sandbox as sandbox_module
from learnfactory.validator_sandbox import (
    SandboxContractError,
    SandboxLimits,
    SandboxRequest,
    ToolchainRoot,
    probe_capabilities,
    run_sandbox,
    tree_sha256,
)


MIB = 1024 * 1024


def limits(**overrides: object) -> SandboxLimits:
    values: dict[str, object] = {
        "wall_seconds": 5,
        "output_bytes": 256 * 1024,
        "retained_output_bytes": 16 * 1024,
        "writable_bytes": 32 * MIB,
        "writable_inodes": 4096,
        "input_bytes": 16 * MIB,
        "input_entries": 2048,
        "input_path_bytes": 512 * 1024,
        "input_depth": 32,
        "file_bytes": 16 * MIB,
        "open_files": 64,
        "cpu_seconds": 2,
        "address_space_bytes": 256 * MIB,
        "aggregate_memory_bytes": 512 * MIB,
        "launcher_memory_bytes": 256 * MIB,
        "max_tasks": 4,
    }
    values.update(overrides)
    return SandboxLimits(**values)  # type: ignore[arg-type]


class SandboxContractTests(unittest.TestCase):
    def test_argv_is_an_exact_nonempty_tuple_with_absolute_executable(self) -> None:
        invalid = (
            SandboxRequest(argv=()),
            SandboxRequest(argv=("python3", "-c", "pass")),
            SandboxRequest(argv=("/etc/passwd",)),
            SandboxRequest(argv=("/usr/local/bin/arm-realm-join",)),
            SandboxRequest(argv=("/usr/bin/python3\0bad",)),
        )
        for request in invalid:
            with self.subTest(request=request), self.assertRaises(SandboxContractError):
                run_sandbox(request)

    def test_cwd_and_environment_are_strict_and_secret_free(self) -> None:
        invalid = (
            SandboxRequest(argv=("/usr/bin/true",), cwd="../escape"),
            SandboxRequest(argv=("/usr/bin/true",), cwd="/absolute"),
            SandboxRequest(argv=("/usr/bin/true",), env={"PATH": "/evil"}),
            SandboxRequest(argv=("/usr/bin/true",), env={"API_TOKEN": "secret"}),
            SandboxRequest(argv=("/usr/bin/true",), env={"GOOD": "bad\0value"}),
            SandboxRequest(argv=("/usr/bin/true",), env={"APIKEY": "x"}),
            SandboxRequest(argv=("/usr/bin/true",), env={"MYTOKEN": "x"}),
            SandboxRequest(argv=("/usr/bin/true",), env={"PASSWORD123": "x"}),
            SandboxRequest(argv=("/usr/bin/true",), env={"AWSACCESSKEYID": "x"}),
            SandboxRequest(argv=("/usr/bin/true",), env={"LD_PRELOAD": "/tmp/x"}),
            SandboxRequest(argv=("/usr/bin/true",), env={"PYTHONPATH": "/tmp/x"}),
            SandboxRequest(argv=("/usr/bin/true",), env={"GLIBC_TUNABLES": "x=y"}),
            SandboxRequest(argv=("/usr/bin/true",), env={"OPAQUE": "sk-abcdefghijklmnop"}),
            SandboxRequest(argv=("/usr/bin/true", "Bearer abcdefghijklmnop")),
            SandboxRequest(argv=("/usr/bin/true", "ghp_abcdefghijklmnopqrstuvwxyz")),
            SandboxRequest(argv=("/usr/bin/true", "xoxb-1234567890-abcdefghij")),
            SandboxRequest(
                argv=("/usr/bin/true", "eyJabcdefghij.abcdefghij.abcdefghij")
            ),
            SandboxRequest(
                argv=("/usr/bin/true", "https://student:private@example.invalid/x")
            ),
            SandboxRequest(argv=("/usr/bin/true", 'password="two secret words"')),
            SandboxRequest(
                argv=(
                    "/usr/bin/true",
                    "-----BEGIN PRIVATE KEY-----\nsecret\n-----END PRIVATE KEY-----",
                )
            ),
        )
        for request in invalid:
            with self.subTest(request=request), self.assertRaises(SandboxContractError):
                run_sandbox(request)

    def test_limits_reject_unbounded_or_incoherent_values(self) -> None:
        malformed = (
            SandboxLimits(wall_seconds=float("inf")),
            SandboxLimits(max_tasks=0),
            SandboxLimits(retained_output_bytes=2, output_bytes=1),
            SandboxLimits(input_bytes=20, writable_bytes=10, file_bytes=5),
            SandboxLimits(address_space_bytes=31 * MIB),
            SandboxLimits(address_space_bytes=512 * MIB, launcher_memory_bytes=256 * MIB),
        )
        for value in malformed:
            with self.subTest(value=value), self.assertRaises(SandboxContractError):
                value.validated()

    def test_input_requires_an_exact_checksum(self) -> None:
        with tempfile.TemporaryDirectory(prefix="sandbox-contract-") as raw:
            root = Path(raw)
            with self.assertRaisesRegex(SandboxContractError, "requires.*SHA-256"):
                run_sandbox(SandboxRequest(argv=("/usr/bin/true",), input_root=root))

    def test_broad_or_non_toolchain_read_roots_are_rejected(self) -> None:
        for root in (Path("/arm/tools"), Path("/projects"), Path("/home"), Path("/etc")):
            with self.subTest(root=root), self.assertRaises(SandboxContractError):
                run_sandbox(SandboxRequest(argv=("/usr/bin/true",), toolchain_roots=(root,)))

    def test_toolchain_roots_require_a_recursive_checksum_contract(self) -> None:
        with tempfile.TemporaryDirectory(prefix="sandbox-toolchain-") as raw:
            root = Path(raw)
            with self.assertRaisesRegex(SandboxContractError, "ToolchainRoot"):
                run_sandbox(
                    SandboxRequest(
                        argv=("/usr/bin/true",),
                        toolchain_roots=(root,),  # type: ignore[arg-type]
                    )
                )
            with self.assertRaisesRegex(SandboxContractError, "outside /arm/tools"):
                run_sandbox(
                    SandboxRequest(
                        argv=("/usr/bin/true",),
                        toolchain_roots=(ToolchainRoot(root, tree_sha256(root)),),
                    )
                )

    def test_missing_sandbox_tool_blocks_without_spawning_or_fallback(self) -> None:
        with patch("learnfactory.validator_sandbox.shutil.which", return_value=None), patch(
            "learnfactory.validator_sandbox.subprocess.Popen"
        ) as popen:
            result = run_sandbox(SandboxRequest(argv=("/usr/bin/true",)))
        self.assertEqual("BLOCKED", result.status)
        self.assertEqual("prerequisite-unavailable", result.reason)
        self.assertFalse(result.evidence["unsafe_fallback_used"])
        popen.assert_not_called()

    def test_expected_exit_is_execution_only_and_never_promotion(self) -> None:
        result = run_sandbox(SandboxRequest(argv=("/usr/bin/true",), limits=limits()))
        if result.status == "BLOCKED":
            self.skipTest(result.reason)
        self.assertEqual("EXECUTED", result.status)
        self.assertTrue(result.execution_succeeded)
        self.assertFalse(result.passed)
        self.assertFalse(result.promotion_eligible)
        self.assertFalse(result.evidence["promotion_eligible"])
        self.assertTrue(result.evidence["external_grader_required"])

    def test_default_request_and_capability_probe_use_the_same_coherent_limits(self) -> None:
        defaults = SandboxLimits().validated()
        self.assertGreaterEqual(defaults.launcher_memory_bytes, defaults.address_space_bytes)
        capability = probe_capabilities()
        self.assertEqual(defaults.as_dict(), capability.evidence["limits"])

    def test_extended_secret_redaction_never_persists_known_formats(self) -> None:
        samples = {
            "ghp_abcdefghijklmnopqrstuvwxyz": "github",
            "xoxb-1234567890-abcdefghij": "slack",
            "eyJabcdefghij.abcdefghij.abcdefghij": "jwt",
            "dXNlcjpwYXNzd29yZA==": "basic",
            "student:private": "userinfo",
            "two secret words": "quoted",
            "PRIVATE-MATERIAL": "pem",
        }
        raw = "\n".join(
            (
                "ghp_abcdefghijklmnopqrstuvwxyz",
                "xoxb-1234567890-abcdefghij",
                "eyJabcdefghij.abcdefghij.abcdefghij",
                "Authorization: Basic dXNlcjpwYXNzd29yZA==",
                "https://student:private@example.invalid/x",
                'password="two secret words"',
                "-----BEGIN PRIVATE KEY-----\nPRIVATE-MATERIAL\n-----END PRIVATE KEY-----",
            )
        )
        redacted = sandbox_module._redact(raw)
        for secret, label in samples.items():
            self.assertNotIn(secret, redacted, label)
        self.assertEqual(
            "prefix\n<redacted-private-key>",
            sandbox_module._redact(
                "prefix\n-----BEGIN PRIVATE KEY-----\nTRUNCATED-PRIVATE-MATERIAL"
            ),
        )
        self.assertEqual(
            "<redacted-private-key>\nsuffix",
            sandbox_module._redact(
                "TRUNCATED-PRIVATE-MATERIAL\n-----END PRIVATE KEY-----\nsuffix"
            ),
        )

    def test_kernel_resource_scope_rejects_nominal_systemd_only_scope(self) -> None:
        limits_value = limits()
        payload = {
            "resource_scope_unit": "learnfactory-validator-123-0123456789abcdef.scope"
        }
        membership = (
            "5:memory:/user.slice/unlimited.scope\n"
            "4:pids:/user.slice/unlimited.scope\n"
            "1:name=systemd:/user.slice/learnfactory-validator-123-0123456789abcdef.scope\n"
        )
        original = Path.read_text

        def fake_read(path: Path, *args, **kwargs):
            if str(path) == "/proc/self/cgroup":
                return membership
            return original(path, *args, **kwargs)

        with patch.object(Path, "read_text", fake_read), self.assertRaisesRegex(
            RuntimeError, "outside real memory/pids"
        ):
            sandbox_module._verify_kernel_resource_scope(payload, limits_value)

    def test_kernel_resource_scope_accepts_only_exact_v1_controller_ceilings(self) -> None:
        limits_value = limits(max_tasks=4, aggregate_memory_bytes=512 * MIB)
        unit = "learnfactory-validator-123-0123456789abcdef.scope"
        payload = {"resource_scope_unit": unit}
        membership = f"5:memory:/user.slice/{unit}\n4:pids:/user.slice/{unit}\n"
        values = {
            "/proc/self/cgroup": membership,
            f"/sys/fs/cgroup/memory/user.slice/{unit}/memory.limit_in_bytes": str(
                limits_value.aggregate_memory_bytes
            ),
            f"/sys/fs/cgroup/memory/user.slice/{unit}/memory.memsw.limit_in_bytes": str(
                limits_value.aggregate_memory_bytes
            ),
            f"/sys/fs/cgroup/pids/user.slice/{unit}/pids.max": str(
                limits_value.max_tasks + sandbox_module._CGROUP_TRUSTED_TASK_OVERHEAD
            ),
        }

        def fake_read(path: Path, *args, **kwargs):
            try:
                return values[str(path)]
            except KeyError as error:
                raise AssertionError(f"unexpected cgroup read: {path}") from error

        with patch.object(Path, "read_text", fake_read):
            evidence = sandbox_module._verify_kernel_resource_scope(payload, limits_value)
        self.assertEqual(1, evidence["version"])
        self.assertTrue(evidence["verified"])
        self.assertEqual(0, evidence["swap_max"])

    def test_kernel_resource_scope_accepts_only_exact_v2_controller_ceilings(self) -> None:
        limits_value = limits(max_tasks=4, aggregate_memory_bytes=512 * MIB)
        unit = "learnfactory-validator-123-0123456789abcdef.scope"
        payload = {"resource_scope_unit": unit}
        root = f"/sys/fs/cgroup/user.slice/{unit}"
        values = {
            "/proc/self/cgroup": f"0::/user.slice/{unit}\n",
            f"{root}/memory.max": str(limits_value.aggregate_memory_bytes),
            f"{root}/memory.swap.max": "0",
            f"{root}/pids.max": str(
                limits_value.max_tasks + sandbox_module._CGROUP_TRUSTED_TASK_OVERHEAD
            ),
        }

        def fake_read(path: Path, *args, **kwargs):
            try:
                return values[str(path)]
            except KeyError as error:
                raise AssertionError(f"unexpected cgroup read: {path}") from error

        with patch.object(Path, "read_text", fake_read):
            evidence = sandbox_module._verify_kernel_resource_scope(payload, limits_value)
        self.assertEqual(2, evidence["version"])
        self.assertTrue(evidence["verified"])


class BoundedTreeTests(unittest.TestCase):
    def test_hash_binds_root_and_nested_directory_modes(self) -> None:
        with tempfile.TemporaryDirectory(prefix="sandbox-tree-modes-") as raw:
            root = Path(raw)
            nested = root / "nested"
            nested.mkdir(mode=0o700)
            baseline = tree_sha256(root)
            nested.chmod(0o755)
            self.assertNotEqual(baseline, tree_sha256(root))
            nested.chmod(0o700)
            baseline = tree_sha256(root)
            root.chmod(0o755 if root.stat().st_mode & 0o777 != 0o755 else 0o700)
            self.assertNotEqual(baseline, tree_sha256(root))

    def test_hash_rejects_a_distinct_mount_id_even_when_device_matches(self) -> None:
        with tempfile.TemporaryDirectory(prefix="sandbox-tree-mount-id-") as raw:
            root = Path(raw)
            (root / "nested").mkdir()
            real_mount_id = sandbox_module._fd_mount_id
            calls = 0

            def changed_mount_id(descriptor: int) -> int:
                nonlocal calls
                calls += 1
                observed = real_mount_id(descriptor)
                return observed if calls == 1 else observed + 1

            with patch(
                "learnfactory.validator_sandbox._fd_mount_id",
                side_effect=changed_mount_id,
            ), self.assertRaisesRegex(SandboxContractError, "mount boundary"):
                tree_sha256(root)

    @unittest.skipUnless(
        shutil.which("unshare") and shutil.which("mount"),
        "mount namespace tools are unavailable",
    )
    def test_hash_rejects_an_actual_same_filesystem_bind_mount(self) -> None:
        with tempfile.TemporaryDirectory(prefix="sandbox-tree-bind-") as raw:
            base = Path(raw)
            source = base / "source"
            root = base / "root"
            target = root / "bound"
            source.mkdir()
            root.mkdir()
            target.mkdir()
            (source / "canary").write_text("outside traversal", encoding="utf-8")
            probe = base / "probe.py"
            probe.write_text(
                "import os, subprocess, sys\n"
                "from pathlib import Path\n"
                "sys.path.insert(0, sys.argv[1])\n"
                "from learnfactory.validator_sandbox import SandboxContractError, tree_sha256\n"
                "source, root, target = map(Path, sys.argv[2:])\n"
                "subprocess.run(['/usr/bin/mount', '--bind', str(source), "
                "str(target)], check=True)\n"
                "assert source.stat().st_dev == root.stat().st_dev == target.stat().st_dev\n"
                "try:\n"
                "    tree_sha256(root)\n"
                "except SandboxContractError as error:\n"
                "    assert 'mount boundary' in str(error), error\n"
                "else:\n"
                "    raise SystemExit('same-filesystem bind mount escaped detection')\n",
                encoding="utf-8",
            )
            completed = subprocess.run(
                (
                    shutil.which("unshare") or "/usr/bin/unshare",
                    "--map-root-user",
                    "--mount",
                    "--propagation",
                    "private",
                    "--fork",
                    os.sys.executable,
                    "-I",
                    str(probe),
                    str(Path(__file__).parents[1] / "src"),
                    str(source),
                    str(root),
                    str(target),
                ),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
                timeout=10,
            )
            self.assertEqual(
                0, completed.returncode, completed.stderr.decode("utf-8", "replace")
            )

    def test_seccomp_policy_denies_anonymous_memory_and_restricts_socket_families(self) -> None:
        descriptor, _, rules = sandbox_module._create_seccomp_filter()
        try:
            for name in ("memfd_create", "shmget", "shmat", "shmdt", "shmctl"):
                self.assertIn(name, rules)
            self.assertIn("socket(allow=AF_UNIX,AF_INET,AF_INET6)", rules)
            self.assertIn("socketpair(allow=AF_UNIX)", rules)
        finally:
            os.close(descriptor)

    @unittest.skipUnless(shutil.which("bwrap"), "bubblewrap is unavailable")
    def test_seccomp_filter_actually_blocks_vsock_memfd_and_sysv_shm(self) -> None:
        descriptor, _, _ = sandbox_module._create_seccomp_filter()
        probe = r"""
import ctypes, errno, json, os, socket
observed = {}
for name, call in (
    ('vsock', lambda: socket.socket(40, socket.SOCK_STREAM)),
):
    try:
        value = call()
    except OSError as error:
        observed[name] = error.errno
    else:
        observed[name] = 0
        value.close() if hasattr(value, 'close') else os.close(value)
libc = ctypes.CDLL(None, use_errno=True)
ctypes.set_errno(0)
value = libc.syscall(319, b'escape', 0)  # memfd_create on x86_64
observed['memfd'] = ctypes.get_errno() if value == -1 else 0
if value != -1:
    os.close(value)
ctypes.set_errno(0)
value = libc.shmget(0, 4096, 0o1000 | 0o600)
observed['shmget'] = ctypes.get_errno() if value == -1 else 0
if value != -1:
    libc.shmctl(value, 0, 0)
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
observed['inet'] = 0
s.close()
print(json.dumps(observed, sort_keys=True))
"""
        try:
            completed = subprocess.run(
                (
                    shutil.which("bwrap") or "/usr/bin/bwrap",
                    "--unshare-net",
                    "--ro-bind",
                    "/",
                    "/",
                    "--seccomp",
                    str(descriptor),
                    "--",
                    "/usr/bin/python3",
                    "-c",
                    probe,
                ),
                pass_fds=(descriptor,),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
                timeout=10,
            )
        finally:
            os.close(descriptor)
        self.assertEqual(0, completed.returncode, completed.stderr.decode("utf-8", "replace"))
        observed = json.loads(completed.stdout)
        self.assertEqual({"inet": 0, "memfd": 1, "shmget": 1, "vsock": 1}, observed)

    def test_minimal_runtime_excludes_usr_local_and_blanket_usr_mount(self) -> None:
        bindings = sandbox_module._minimal_runtime_sources()
        self.assertTrue(bindings)
        for source, target, _ in bindings:
            self.assertFalse(source.startswith("/usr/local"), source)
            self.assertFalse(target.startswith("/usr/local"), target)
            self.assertNotEqual("/usr", target)
        root = Path("/isolated-root")
        command = sandbox_module._build_bwrap_argv(
            {
                "tools": {"bwrap": "/usr/bin/bwrap"},
                "cwd": ".",
                "fixed_path": "/usr/bin",
                "env": {},
                "argv": ["/usr/bin/true"],
            },
            root,
            root / "work",
            [],
            [{"source": "/usr/bin/true", "target": "/usr/bin/true"}],
            16,
            (10, 11),
            12,
            13,
            14,
        )
        rendered = "\0".join(command)
        self.assertNotIn("--ro-bind\0/usr\0/usr", rendered)
        self.assertIn("--ro-bind\0/isolated-root/.learnfactory/masked-proc-1\0/proc/1", rendered)
        self.assertIn("/.learnfactory/command_supervisor.py", command)
        with tempfile.TemporaryDirectory(prefix="sandbox-runtime-root-") as raw:
            prepared_root, _, _, prepared_bindings, _ = (
                sandbox_module._prepare_sandbox_root(
                    {"input_root": None, "toolchain_roots": []},
                    Path(raw),
                    SandboxLimits().validated(),
                )
            )
            self.assertEqual(
                0o555,
                (prepared_root / ".learnfactory").stat().st_mode & 0o777,
            )
            self.assertEqual(
                0o555,
                (prepared_root / ".learnfactory/command_supervisor.py").stat().st_mode
                & 0o777,
            )
            self.assertTrue(prepared_bindings)

    def test_trusted_command_supervisor_distinguishes_exit_twins_from_signals(self) -> None:
        with tempfile.TemporaryDirectory(prefix="sandbox-supervisor-") as raw:
            supervisor = Path(raw) / "supervisor.py"
            supervisor.write_text(sandbox_module._COMMAND_SUPERVISOR_SOURCE, encoding="ascii")
            cases = (
                ("import sys;sys.exit(137)", {"kind": "exit", "exit_code": 137}),
                (
                    "import os,signal;os.kill(os.getpid(),signal.SIGKILL)",
                    {"kind": "signal", "signal": 9},
                ),
                (
                    "import os,signal;os.kill(os.getpid(),signal.SIGTERM)",
                    {"kind": "signal", "signal": 15},
                ),
                (
                    "import os,signal;signal.signal(signal.SIGXFSZ,signal.SIG_DFL);"
                    "os.kill(os.getpid(),signal.SIGXFSZ)",
                    {"kind": "signal", "signal": 25},
                ),
            )
            for command, expected in cases:
                with self.subTest(expected=expected):
                    read_fd, write_fd = os.pipe()
                    process = subprocess.Popen(
                        (
                            "/usr/bin/python3",
                            "-I",
                            str(supervisor),
                            str(write_fd),
                            "/usr/bin/python3",
                            "-c",
                            command,
                        ),
                        pass_fds=(write_fd,),
                        close_fds=True,
                    )
                    os.close(write_fd)
                    observed = json.loads(os.read(read_fd, 1024))
                    os.close(read_fd)
                    process.wait(timeout=5)
                    self.assertEqual(expected, observed)

    def test_trusted_command_supervisor_closes_fds_and_is_not_proc_readable(self) -> None:
        with tempfile.TemporaryDirectory(prefix="sandbox-supervisor-fds-") as raw:
            supervisor = Path(raw) / "supervisor.py"
            supervisor.write_text(sandbox_module._COMMAND_SUPERVISOR_SOURCE, encoding="ascii")
            read_fd, write_fd = os.pipe()
            extra_read, extra_write = os.pipe()
            os.dup2(extra_read, 100, inheritable=True)
            command = r"""
import json, os
parent = os.getppid()
try:
    os.fstat(100)
    leaked = True
except OSError:
    leaked = False
try:
    open('/proc/%d/mem' % parent, 'rb').read(1)
    parent_mem = True
except OSError:
    parent_mem = False
try:
    os.listdir('/proc/%d/fd' % parent)
    parent_fds = True
except OSError:
    parent_fds = False
print(json.dumps({'leaked': leaked, 'parent_mem': parent_mem, 'parent_fds': parent_fds}))
"""
            try:
                process = subprocess.Popen(
                    (
                        "/usr/bin/python3",
                        "-I",
                        str(supervisor),
                        str(write_fd),
                        "/usr/bin/python3",
                        "-c",
                        command,
                    ),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    pass_fds=(write_fd, 100),
                    close_fds=True,
                )
                os.close(write_fd)
                status = json.loads(os.read(read_fd, 1024))
                stdout, stderr = process.communicate(timeout=5)
            finally:
                os.close(read_fd)
                os.close(extra_read)
                os.close(extra_write)
                os.close(100)
            self.assertEqual({"kind": "exit", "exit_code": 0}, status)
            self.assertEqual(b"", stderr)
            self.assertEqual(
                {"leaked": False, "parent_fds": False, "parent_mem": False},
                json.loads(stdout),
            )
    def test_hash_rejects_a_file_replaced_by_an_outside_symlink(self) -> None:
        with tempfile.TemporaryDirectory(prefix="sandbox-tree-race-") as raw:
            base = Path(raw)
            root = base / "root"
            root.mkdir()
            victim = root / "victim"
            victim.write_text("safe", encoding="utf-8")
            outside = base / "outside"
            outside.write_text("outside-content", encoding="utf-8")
            real_open = os.open
            swapped = False

            def racing_open(path, flags, *args, **kwargs):
                nonlocal swapped
                if path == "victim" and kwargs.get("dir_fd") is not None and not swapped:
                    swapped = True
                    victim.unlink()
                    victim.symlink_to(outside)
                return real_open(path, flags, *args, **kwargs)

            with patch("learnfactory.validator_sandbox.os.open", side_effect=racing_open):
                with self.assertRaises((SandboxContractError, OSError)):
                    tree_sha256(root)
            self.assertTrue(swapped)

    def test_hash_enforces_byte_limit_before_reading_unbounded_content(self) -> None:
        with tempfile.TemporaryDirectory(prefix="sandbox-tree-bytes-") as raw:
            root = Path(raw)
            (root / "large").write_bytes(b"x" * (2 * MIB))
            with self.assertRaisesRegex(SandboxContractError, "byte limit"):
                tree_sha256(root, maximum_bytes=MIB)

    def test_sixty_thousand_entries_stop_at_hard_cap_with_bounded_memory(self) -> None:
        with tempfile.TemporaryDirectory(prefix="sandbox-tree-entries-") as raw:
            root = Path(raw)
            for index in range(60_000):
                descriptor = os.open(
                    root / f"f-{index:05d}",
                    os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                    0o600,
                )
                os.close(descriptor)
            tracemalloc.start()
            try:
                with self.assertRaisesRegex(SandboxContractError, "too many entries"):
                    tree_sha256(root)
                _, peak = tracemalloc.get_traced_memory()
            finally:
                tracemalloc.stop()
            self.assertLess(peak, 8 * MIB)


class SandboxRuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.capability = probe_capabilities()
        if not cls.capability.available:
            raise unittest.SkipTest(
                "validator sandbox unavailable: "
                + json.dumps(
                    {"reason": cls.capability.reason, "evidence": cls.capability.evidence},
                    sort_keys=True,
                    default=str,
                )[:2000]
            )

    def _script(
        self,
        source: str,
        *,
        arguments: tuple[str, ...] = (),
        env: dict[str, str] | None = None,
        selected_limits: SandboxLimits | None = None,
        expected_exit: int = 0,
        cwd: str = ".",
        extra_files: dict[str, str] | None = None,
    ):
        temporary = tempfile.TemporaryDirectory(prefix="sandbox-input-")
        root = Path(temporary.name)
        script = root / "runner.py"
        script.write_text(source, encoding="utf-8")
        for relative, content in (extra_files or {}).items():
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
        request = SandboxRequest(
            argv=("/usr/bin/python3", "/work/runner.py", *arguments),
            input_root=root,
            expected_input_sha256=tree_sha256(root),
            env=env or {},
            limits=selected_limits or limits(),
            cwd=cwd,
            expected_exit=expected_exit,
        )
        result = run_sandbox(request)
        return temporary, root, result

    def test_filesystem_environment_and_network_are_isolated(self) -> None:
        with tempfile.TemporaryDirectory(prefix="sandbox-host-sentinel-") as raw:
            sentinel = Path(raw) / "outside.txt"
            sentinel.write_text("host secret\n", encoding="utf-8")
            with patch.dict(os.environ, {"SHOULD_NOT_EXIST": "operator-value"}):
                temporary, source, result = self._script(
                    """
import json, os, socket, sys
paths = ['/projects', '/home', '/etc/passwd', '/arm/ref', '/proc/1/root/projects', sys.argv[1]]
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
network = s.connect_ex(('1.1.1.1', 53))
open('/work/generated.txt', 'w').write('disposable\\n')
print(json.dumps({
    'visible': [os.path.exists(path) for path in paths],
    'network': network,
    'explicit': os.environ.get('EXPLICIT_VALUE'),
    'inherited': os.environ.get('SHOULD_NOT_EXIST'),
    'home': os.environ.get('HOME'),
    'path': os.environ.get('PATH'),
}, sort_keys=True))
""",
                    arguments=(str(sentinel),),
                    env={"EXPLICIT_VALUE": "present"},
                )
            try:
                self.assertTrue(result.execution_succeeded, (result.reason, result.stderr))
                observed = json.loads(result.stdout)
                self.assertEqual([False] * 6, observed["visible"])
                self.assertNotEqual(0, observed["network"])
                self.assertEqual("present", observed["explicit"])
                self.assertIsNone(observed["inherited"])
                self.assertEqual("/tmp", observed["home"])
                self.assertEqual("/usr/bin", observed["path"])
                self.assertFalse((source / "generated.txt").exists())
                self.assertEqual("host secret\n", sentinel.read_text(encoding="utf-8"))
                self.assertFalse(result.evidence["input_root_exposed_to_command"])
                self.assertEqual("unshared", result.evidence["network"])
                self.assertEqual(65534, result.evidence["launcher"]["command_uid"])
                self.assertNotEqual(
                    result.evidence["launcher"]["initial_work_sha256"],
                    result.evidence["launcher"]["final_work_sha256"],
                )
            finally:
                temporary.cleanup()

    def test_one_byte_and_inode_cap_covers_every_writable_location(self) -> None:
        selected = limits(
            writable_bytes=16 * MIB,
            writable_inodes=256,
            input_bytes=4 * MIB,
            input_entries=128,
            file_bytes=2 * MIB,
        )
        temporary, _, result = self._script(
            r"""
import json, os
paths = ['/', '/work', '/tmp', '/etc', '/dev', '/dev/shm']
stats = {p: [os.stat(p).st_dev,
             os.statvfs(p).f_blocks * os.statvfs(p).f_frsize,
             os.statvfs(p).f_files,
             os.access(p, os.W_OK)] for p in paths}
forbidden = {}
for p in ['/', '/etc', '/dev']:
    try:
        open(p + '/escape', 'wb').write(b'x')
        forbidden[p] = 'wrote'
    except OSError as error:
        forbidden[p] = error.errno
written = 0
for i in range(64):
    root = ['/work', '/tmp', '/dev/shm'][i % 3]
    try:
        open('%s/blob-%03d' % (root, i), 'wb').write(b'x' * (1024 * 1024))
        written += 1024 * 1024
    except OSError:
        break
created = 0
for i in range(1000):
    try:
        open('/tmp/inode-%04d' % i, 'wb').close()
        created += 1
    except OSError:
        break
print(json.dumps({'stats': stats, 'forbidden': forbidden,
                  'written': written, 'created': created}, sort_keys=True))
""",
            selected_limits=selected,
        )
        try:
            self.assertTrue(result.execution_succeeded, (result.reason, result.stderr))
            observed = json.loads(result.stdout)
            stats = observed["stats"]
            self.assertEqual(1, len({values[0] for values in stats.values()}))
            self.assertTrue(
                all(values[1] <= selected.writable_bytes for values in stats.values()), stats
            )
            self.assertTrue(
                all(values[2] <= selected.writable_inodes for values in stats.values()), stats
            )
            self.assertEqual({"/": False, "/etc": False, "/dev": False}, {
                path: values[3] for path, values in stats.items() if path in {"/", "/etc", "/dev"}
            })
            self.assertNotIn("wrote", observed["forbidden"].values())
            self.assertLess(observed["written"], 40 * MIB)
            self.assertLess(observed["created"], 1000)
            launcher = result.evidence["launcher"]
            self.assertTrue(launcher["single_writable_filesystem"])
            self.assertLessEqual(launcher["tmpfs_capacity_bytes"], selected.writable_bytes)
            self.assertLessEqual(launcher["tmpfs_inode_capacity"], selected.writable_inodes)
        finally:
            temporary.cleanup()

    def test_command_is_non_owner_and_cannot_change_root_permissions(self) -> None:
        owner_only_candidates = [
            path
            for path in Path("/usr/lib/modules").glob("*/System.map")
            if path.is_file() and path.stat().st_uid == 0 and path.stat().st_mode & 0o777 == 0o600
        ]
        if not owner_only_candidates:
            self.skipTest("host has no safe root-owned mode-0600 runtime probe")
        temporary, _, result = self._script(
            r"""
import json, os, sys
try:
    os.chmod('/', 0o777)
    changed = True
except OSError:
    changed = False
try:
    open(sys.argv[1], 'rb').read(1)
    owner_only_readable = True
except PermissionError:
    owner_only_readable = False
cap_eff = next(line.split()[1] for line in open('/proc/self/status') if line.startswith('CapEff:'))
print(json.dumps({'uid': os.getuid(), 'writable': os.access('/', os.W_OK),
                  'changed': changed, 'owner_only_readable': owner_only_readable,
                  'cap_eff': cap_eff}))
""",
            arguments=(str(owner_only_candidates[0]),),
        )
        try:
            self.assertTrue(result.execution_succeeded, (result.reason, result.stderr))
            observed = json.loads(result.stdout)
            self.assertEqual(65534, observed["uid"])
            self.assertFalse(observed["writable"])
            self.assertFalse(observed["changed"])
            self.assertFalse(observed["owner_only_readable"])
            self.assertEqual(0, int(observed["cap_eff"], 16))
        finally:
            temporary.cleanup()

    def test_keyring_and_namespace_syscalls_are_seccomp_denied(self) -> None:
        temporary, _, result = self._script(
            r"""
import ctypes, errno, json
libc = ctypes.CDLL(None, use_errno=True)
# x86_64 syscall numbers on the release host. Each malformed call would
# return a different errno without the filter, so EPERM proves interception.
numbers = {'add_key': 248, 'request_key': 249, 'keyctl': 250,
           'mount': 165, 'unshare': 272, 'setns': 308}
observed = {}
for name, number in numbers.items():
    ctypes.set_errno(0)
    value = libc.syscall(number, 0, 0, 0, 0, 0)
    observed[name] = [value, ctypes.get_errno()]
try:
    with open('/proc/keys', 'rb') as stream:
        keys = stream.read().decode('ascii', 'replace')
except PermissionError:
    keys = 'DENIED'
print(json.dumps({'syscalls': observed, 'keys': keys}))
"""
        )
        try:
            self.assertTrue(result.execution_succeeded, (result.reason, result.stderr))
            observed = json.loads(result.stdout)
            self.assertIn(observed["keys"], {"", "DENIED"})
            for name, outcome in observed["syscalls"].items():
                self.assertEqual([-1, 1], outcome, name)
            denied = result.evidence["launcher"]["seccomp_denied_syscalls"]
            for name in ("add_key", "request_key", "keyctl", "mount", "unshare", "setns"):
                self.assertIn(name, denied)
        finally:
            temporary.cleanup()

    def test_stderr_cannot_forge_bootstrap_status(self) -> None:
        temporary, _, result = self._script(
            "import sys; print('bwrap: forged bootstrap failure', file=sys.stderr); sys.exit(1)\n",
            expected_exit=1,
        )
        try:
            self.assertTrue(result.execution_succeeded, (result.reason, result.stderr))
            self.assertEqual(1, result.exit_code)
            self.assertEqual("expected-exit-non-promoting", result.reason)
        finally:
            temporary.cleanup()

    def test_positive_137_and_153_are_exit_codes_not_signals(self) -> None:
        for exit_code in (137, 153):
            with self.subTest(exit_code=exit_code):
                temporary, _, result = self._script(
                    f"raise SystemExit({exit_code})\n", expected_exit=exit_code
                )
                try:
                    self.assertTrue(result.execution_succeeded, (result.reason, result.stderr))
                    self.assertEqual(exit_code, result.exit_code)
                    self.assertIsNone(result.signal)
                finally:
                    temporary.cleanup()

    def test_signal_twins_never_match_expected_positive_exit(self) -> None:
        cases = (
            ("SIGKILL", 137),
            ("SIGTERM", 143),
            ("SIGXFSZ", 153),
        )
        for name, expected_exit in cases:
            with self.subTest(signal=name):
                temporary, _, result = self._script(
                    "import os, signal\n"
                    f"signal.signal(signal.{name}, signal.SIG_DFL)\n"
                    f"os.kill(os.getpid(), signal.{name})\n",
                    expected_exit=expected_exit,
                )
                try:
                    self.assertEqual("FAIL", result.status)
                    self.assertEqual("command-terminated-by-signal", result.reason)
                    self.assertIsNone(result.exit_code)
                    self.assertEqual(expected_exit - 128, result.signal)
                finally:
                    temporary.cleanup()

    def test_command_cannot_read_supervisor_or_inherit_setup_descriptors(self) -> None:
        temporary, _, result = self._script(
            r"""
import json, os
parent = os.getppid()
try:
    parent_entries = os.listdir('/proc/%d/fd' % parent)
except OSError:
    parent_entries = None
try:
    open('/proc/%d/mem' % parent, 'rb').read(1)
    parent_mem = True
except OSError:
    parent_mem = False
opened = []
for descriptor in range(3, 64):
    try:
        os.fstat(descriptor)
        opened.append(descriptor)
    except OSError:
        pass
print(json.dumps({'pid1': os.listdir('/proc/1'), 'parent_entries': parent_entries,
                  'parent_mem': parent_mem, 'opened': opened}))
"""
        )
        try:
            self.assertTrue(result.execution_succeeded, (result.reason, result.stderr))
            observed = json.loads(result.stdout)
            self.assertEqual([], observed["pid1"])
            self.assertIsNone(observed["parent_entries"])
            self.assertFalse(observed["parent_mem"])
            self.assertEqual([], observed["opened"])
        finally:
            temporary.cleanup()

    def test_unsafe_address_and_anonymous_memory_syscalls_are_denied(self) -> None:
        temporary, _, result = self._script(
            r"""
import ctypes, json, os, socket
observed = {}
try:
    socket.socket(40, socket.SOCK_STREAM)
except OSError as error:
    observed['vsock'] = error.errno
libc = ctypes.CDLL(None, use_errno=True)
ctypes.set_errno(0)
value = libc.syscall(319, b'escape', 0)
observed['memfd'] = ctypes.get_errno() if value == -1 else 0
ctypes.set_errno(0)
value = libc.shmget(0, 4096, 0o1000 | 0o600)
observed['shmget'] = ctypes.get_errno() if value == -1 else 0
print(json.dumps(observed, sort_keys=True))
"""
        )
        try:
            self.assertTrue(result.execution_succeeded, (result.reason, result.stderr))
            self.assertEqual({"memfd": 1, "shmget": 1, "vsock": 1}, json.loads(result.stdout))
            scope = result.evidence["launcher"]["kernel_resource_scope"]
            self.assertTrue(scope["verified"])
            self.assertEqual(0, scope["swap_max"])
        finally:
            temporary.cleanup()

    def test_usr_local_and_vendor_site_packages_are_not_visible(self) -> None:
        temporary, _, result = self._script(
            "import json, os, site\n"
            "print(json.dumps({'local': os.path.exists('/usr/local'), "
            "'site': [p for p in site.getsitepackages() if os.listdir(p)]}))\n"
        )
        try:
            self.assertTrue(result.execution_succeeded, (result.reason, result.stderr))
            self.assertEqual({"local": False, "site": []}, json.loads(result.stdout))
        finally:
            temporary.cleanup()

    def test_argv_is_literal_and_never_shell_interpreted(self) -> None:
        with tempfile.TemporaryDirectory(prefix="sandbox-shell-marker-") as raw:
            marker = Path(raw) / "created"
            literal = f"; touch {marker}"
            temporary, _, result = self._script(
                "import sys; print(sys.argv[1])\n", arguments=(literal,)
            )
            try:
                self.assertTrue(result.execution_succeeded, result.stderr)
                self.assertEqual(literal, result.stdout.strip())
                self.assertFalse(marker.exists())
                self.assertNotIn(literal, json.dumps(result.evidence, sort_keys=True))
                self.assertEqual(3, result.evidence["argv_count"])
            finally:
                temporary.cleanup()

    def test_relative_cwd_is_confined_to_disposable_work_tree(self) -> None:
        temporary, _, result = self._script(
            "import os; print(os.getcwd())\n",
            cwd="sub",
            extra_files={"sub/keep.txt": "present\n"},
        )
        try:
            self.assertTrue(result.execution_succeeded, result.stderr)
            self.assertEqual("/work/sub", result.stdout.strip())
        finally:
            temporary.cleanup()

    def test_input_checksum_mismatch_and_symlink_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory(prefix="sandbox-bad-input-") as raw:
            root = Path(raw)
            (root / "regular").write_text("value", encoding="utf-8")
            mismatch = run_sandbox(
                SandboxRequest(
                    argv=("/usr/bin/true",),
                    input_root=root,
                    expected_input_sha256="0" * 64,
                    limits=limits(),
                )
            )
            self.assertEqual("BLOCKED", mismatch.status)
            self.assertEqual("input-checksum-mismatch", mismatch.reason)

            (root / "link").symlink_to(root / "regular")
            linked = run_sandbox(
                SandboxRequest(
                    argv=("/usr/bin/true",),
                    input_root=root,
                    expected_input_sha256="0" * 64,
                    limits=limits(),
                )
            )
            self.assertEqual("BLOCKED", linked.status)
            self.assertNotEqual("PASS", linked.status)

    def test_missing_executable_is_blocked_not_run_on_host(self) -> None:
        result = run_sandbox(
            SandboxRequest(
                argv=("/usr/bin/learnfactory-tool-that-does-not-exist",),
                limits=limits(),
            )
        )
        self.assertEqual("BLOCKED", result.status)
        self.assertEqual("sandbox-executable-unavailable", result.reason)
        self.assertTrue(result.evidence["cleanup_succeeded"])

    def test_output_flood_is_stopped_and_retention_is_bounded(self) -> None:
        maximum = 64 * 1024
        selected = limits(output_bytes=maximum, retained_output_bytes=4096)
        temporary, _, result = self._script(
            "import os\nwhile True: os.write(1, b'x' * 65536)\n",
            selected_limits=selected,
        )
        try:
            self.assertEqual("LIMIT", result.status)
            self.assertEqual("output-limit", result.reason)
            self.assertLessEqual(result.evidence["combined_output_bytes"], maximum + 2 * 65536)
            self.assertLessEqual(len(result.stdout.encode("utf-8")), 4600)
            self.assertTrue(result.evidence["cleanup_succeeded"])
        finally:
            temporary.cleanup()

    def test_wall_timeout_stops_sleeping_command(self) -> None:
        selected = limits(wall_seconds=0.3, cpu_seconds=5)
        started = time.monotonic()
        result = run_sandbox(
            SandboxRequest(argv=("/usr/bin/sleep", "30"), limits=selected)
        )
        elapsed = time.monotonic() - started
        self.assertEqual("LIMIT", result.status)
        self.assertEqual("wall-time-limit", result.reason)
        self.assertLess(elapsed, 2)

    def test_cpu_address_space_file_and_disk_limits_are_effective(self) -> None:
        cases = (
            (
                "cpu",
                "while True: pass\n",
                # On a heavily shared host, one CPU second can take several
                # wall seconds.  Leave enough headroom to observe RLIMIT_CPU.
                limits(wall_seconds=15, cpu_seconds=1),
            ),
            (
                "address-space",
                "x = bytearray(512 * 1024 * 1024)\n",
                limits(address_space_bytes=128 * MIB, aggregate_memory_bytes=256 * MIB),
            ),
            (
                "file-size",
                "open('/work/large', 'wb').write(b'x' * (16 * 1024 * 1024))\n",
                limits(file_bytes=1 * MIB),
            ),
            (
                "tmpfs",
                "\n".join(
                    [
                        "for i in range(64):",
                        "    open('/work/f-%03d' % i, 'wb').write(b'x' * (1024 * 1024))",
                    ]
                ),
                limits(writable_bytes=16 * MIB, input_bytes=4 * MIB, file_bytes=4 * MIB),
            ),
        )
        for name, source, selected in cases:
            with self.subTest(name=name):
                temporary, _, result = self._script(source, selected_limits=selected)
                try:
                    self.assertIn(result.status, {"FAIL", "LIMIT"}, (result.reason, result.stderr))
                    self.assertTrue(result.evidence["cleanup_succeeded"])
                    launcher = result.evidence["launcher"]
                    if launcher is not None:
                        self.assertLessEqual(
                            launcher["tmpfs_capacity_bytes"],
                            selected.writable_bytes,
                        )
                finally:
                    temporary.cleanup()

    def test_task_bomb_cannot_escape_configured_bound(self) -> None:
        temporary, _, result = self._script(
            """
import os, time
children = []
for _ in range(100):
    pid = os.fork()
    if pid == 0:
        time.sleep(10)
        os._exit(0)
    children.append(pid)
""",
            selected_limits=limits(max_tasks=8, wall_seconds=3),
        )
        try:
            self.assertIn(result.status, {"FAIL", "LIMIT"})
            self.assertTrue(result.evidence["cleanup_succeeded"])
            observed = result.evidence["launcher"]["peak_tasks_observed"]
            self.assertLessEqual(observed, 20)
        finally:
            temporary.cleanup()

    def test_setsid_double_fork_descendant_is_reaped(self) -> None:
        token = "lf-sandbox-" + uuid.uuid4().hex
        temporary, _, result = self._script(
            """
import os, sys, time
token = sys.argv[1]
pid = os.fork()
if pid == 0:
    os.setsid()
    second = os.fork()
    if second > 0:
        os._exit(0)
    time.sleep(10)
    os._exit(0)
os.waitpid(pid, 0)
""",
            arguments=(token,),
            selected_limits=limits(wall_seconds=2, max_tasks=8),
        )
        try:
            self.assertIn(result.status, {"EXECUTED", "LIMIT"}, (result.reason, result.stderr))
            time.sleep(0.1)
            survivors = []
            for entry in Path("/proc").iterdir():
                if not entry.name.isdigit():
                    continue
                try:
                    command = (entry / "cmdline").read_bytes()
                except (FileNotFoundError, PermissionError, ProcessLookupError):
                    continue
                if token.encode() in command:
                    survivors.append(entry.name)
            self.assertEqual([], survivors)
        finally:
            temporary.cleanup()

    def test_background_process_cannot_poll_or_mutate_host_artifact(self) -> None:
        with tempfile.TemporaryDirectory(prefix="sandbox-host-artifact-") as raw:
            artifact = Path(raw) / "published.bin"
            artifact.write_bytes(b"authoritative")
            token = "lf-artifact-poller-" + uuid.uuid4().hex
            temporary, _, result = self._script(
                r"""
import os, sys, time
target, token = sys.argv[1:]
pid = os.fork()
if pid == 0:
    os.setsid()
    child = os.fork()
    if child > 0:
        os._exit(0)
    time.sleep(0.1)
    if os.path.exists(target):
        with open(target, 'wb') as stream:
            stream.write(b'corrupted')
    os._exit(0)
os.waitpid(pid, 0)
""",
                arguments=(str(artifact), token),
                selected_limits=limits(wall_seconds=2, max_tasks=8),
            )
            try:
                self.assertIn(result.status, {"EXECUTED", "LIMIT"})
                self.assertEqual(b"authoritative", artifact.read_bytes())
                time.sleep(0.1)
                survivors = []
                for entry in Path("/proc").iterdir():
                    if not entry.name.isdigit():
                        continue
                    try:
                        command = (entry / "cmdline").read_bytes()
                    except (FileNotFoundError, PermissionError, ProcessLookupError):
                        continue
                    if token.encode() in command:
                        survivors.append(entry.name)
                self.assertEqual([], survivors)
            finally:
                temporary.cleanup()

    def test_special_file_output_is_not_accepted_as_a_regular_final_tree(self) -> None:
        temporary, _, result = self._script("import os; os.mkfifo('/work/fifo')\n")
        try:
            self.assertEqual("FAIL", result.status)
            self.assertEqual("unsafe-final-work-tree", result.reason)
        finally:
            temporary.cleanup()

    def test_logs_are_redacted(self) -> None:
        temporary, _, result = self._script(
            """import sys
print('token=visible-secret')
print('{\"token\":\"json-secret\"}')
print("{'password': 'quoted-secret'}")
print('Authorization: Bearer abcdefghijklmnop')
print('sk-abcdefghijklmnop')
print('password=stderr-secret', file=sys.stderr)
"""
        )
        try:
            self.assertTrue(result.execution_succeeded)
            for secret in (
                "visible-secret",
                "json-secret",
                "quoted-secret",
                "abcdefghijklmnop",
                "stderr-secret",
            ):
                self.assertNotIn(secret, result.stdout + result.stderr)
            self.assertIn("<redacted>", result.stdout)
            self.assertIn("<redacted>", result.stderr)
        finally:
            temporary.cleanup()

    def test_argv_and_environment_values_are_not_persisted_in_evidence(self) -> None:
        canary_argument = "argument-canary-4dbdf56d"
        canary_environment = "environment-canary-a7a991e3"
        temporary, _, result = self._script(
            "pass\n",
            arguments=(canary_argument,),
            env={"OPAQUE": canary_environment},
        )
        try:
            self.assertTrue(result.execution_succeeded, (result.reason, result.stderr))
            rendered = json.dumps(result.evidence, sort_keys=True)
            self.assertNotIn(canary_argument, rendered)
            self.assertNotIn(canary_environment, rendered)
            self.assertFalse(result.evidence["env_values_recorded"])
        finally:
            temporary.cleanup()

    def test_cancellation_terminates_namespace(self) -> None:
        cancelled = threading.Event()
        timer = threading.Timer(0.2, cancelled.set)
        timer.start()
        try:
            result = run_sandbox(
                SandboxRequest(argv=("/usr/bin/sleep", "30"), limits=limits(wall_seconds=5)),
                cancel_event=cancelled,
            )
        finally:
            timer.cancel()
        self.assertEqual("CANCELLED", result.status)
        self.assertEqual("cancelled", result.reason)
        self.assertTrue(result.evidence["cleanup_succeeded"])


if __name__ == "__main__":
    unittest.main()
