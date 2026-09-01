import errno
import ctypes
import fcntl
import os
import pty
import select
import shutil
import signal
import subprocess
import sys
import tempfile
import termios
import time
import unittest


HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_SHELL = os.path.abspath(os.path.join(HERE, "..", "reference", "byosh"))
SHELL = os.environ.get("SHELL_UNDER_TEST", DEFAULT_SHELL)
REQUIRED_TOOLS = (
    "cat", "head", "printf", "ps", "python3", "sh", "sleep", "tr",
    "true", "wc", "yes",
)
TOOLS = dict((name, shutil.which(name)) for name in REQUIRED_TOOLS)
MISSING_TOOLS = sorted(name for name, path in TOOLS.items() if path is None)
PYTHON = os.path.abspath(TOOLS["python3"]) if TOOLS["python3"] else ""


class CleanupError(RuntimeError):
    pass


def _enable_child_subreaper():
    if not sys.platform.startswith("linux"):
        return False
    try:
        library = ctypes.CDLL(None, use_errno=True)
        return library.prctl(36, 1, 0, 0, 0) == 0
    except (AttributeError, OSError):
        return False


IS_CHILD_SUBREAPER = _enable_child_subreaper()


def shell_quote(value):
    return "'" + value.replace("'", "'\"'\"'") + "'"


def tool(name):
    path = TOOLS.get(name)
    if path is None:
        raise unittest.SkipTest("required utility not found: {}".format(name))
    return shell_quote(os.path.abspath(path))


def _session_members(session_id):
    ps_path = TOOLS.get("ps")
    if ps_path is None:
        raise CleanupError("SID-scoped ps helper is unavailable")
    try:
        process = subprocess.Popen(
            [ps_path, "-o", "pid=", "-o", "sid=", "-o", "stat=", "--sid", str(session_id)],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
        )
    except OSError as error:
        raise CleanupError("could not start SID-scoped ps helper: {}".format(error))

    try:
        stdout, stderr = process.communicate(timeout=0.5)
    except subprocess.TimeoutExpired:
        kill_error = None
        try:
            process.kill()
        except OSError as error:
            if error.errno != errno.ESRCH:
                kill_error = error
        try:
            process.communicate(timeout=0.5)
        except subprocess.TimeoutExpired:
            if process.stdout is not None:
                process.stdout.close()
            if process.stderr is not None:
                process.stderr.close()
            try:
                process.wait(timeout=0.5)
            except subprocess.TimeoutExpired:
                raise CleanupError(
                    "SID-scoped ps helper timed out and could not be reaped"
                )
        if kill_error is not None:
            raise CleanupError(
                "SID-scoped ps helper timed out and could not be killed: {}".format(
                    kill_error
                )
            )
        raise CleanupError("SID-scoped ps helper timed out")
    except OSError as error:
        raise CleanupError("SID-scoped ps helper failed: {}".format(error))

    if process.returncode == 1 and stdout == "" and stderr == "":
        return []
    if process.returncode != 0:
        raise CleanupError(
            "SID-scoped ps helper exited with status {}: {!r}".format(
                process.returncode, stderr
            )
        )
    if stderr:
        raise CleanupError(
            "SID-scoped ps helper produced error output: {!r}".format(stderr)
        )

    members = []
    seen_pids = set()
    for line_number, line in enumerate(stdout.splitlines(), 1):
        fields = line.split()
        if len(fields) != 3:
            raise CleanupError(
                "malformed SID-scoped ps output on line {}: {!r}".format(
                    line_number, line
                )
            )
        try:
            pid = int(fields[0])
            sid = int(fields[1])
        except ValueError:
            raise CleanupError(
                "malformed SID-scoped ps output on line {}: {!r}".format(
                    line_number, line
                )
            )
        if pid <= 0 or sid != session_id or pid in seen_pids:
            raise CleanupError(
                "unexpected SID-scoped ps output on line {}: {!r}".format(
                    line_number, line
                )
            )
        seen_pids.add(pid)
        members.append((pid, fields[2]))
    return members


def _signal_if_same_session(pid, session_id, chosen_signal):
    """Signal pid only after an immediate, matching SID check."""
    try:
        actual_session_id = os.getsid(pid)
    except OSError as error:
        if error.errno == errno.ESRCH:
            return True
        raise CleanupError("could not verify session for pid {}: {}".format(pid, error))
    if actual_session_id != session_id:
        raise CleanupError(
            "refusing to signal pid {}: expected SID {}, found {}".format(
                pid, session_id, actual_session_id
            )
        )
    try:
        os.kill(pid, chosen_signal)
    except OSError as error:
        if error.errno == errno.ESRCH:
            return True
        raise CleanupError("could not signal pid {}: {}".format(pid, error))
    return False


def _terminate_direct_child_after_enumeration_failure(process, session_id, grace):
    """Boundedly kill only the known direct child after scoped ps fails."""
    if process.poll() is not None:
        return

    signal_error = None
    try:
        _signal_if_same_session(process.pid, session_id, signal.SIGKILL)
    except CleanupError as error:
        signal_error = error

    wait_error = None
    try:
        process.wait(timeout=grace)
    except subprocess.TimeoutExpired:
        wait_error = CleanupError(
            "direct child {} did not exit after bounded SIGKILL fallback".format(
                process.pid
            )
        )

    if signal_error is not None and wait_error is not None:
        raise CleanupError("{}; {}".format(signal_error, wait_error))
    if signal_error is not None:
        raise signal_error
    if wait_error is not None:
        raise wait_error


def _session_members_for_cleanup(process, session_id, grace):
    try:
        return _session_members(session_id)
    except Exception as enumeration_error:
        fallback_error = None
        try:
            _terminate_direct_child_after_enumeration_failure(
                process, session_id, grace
            )
        except Exception as error:
            fallback_error = error

        message = "session cleanup incomplete: scoped enumeration failed: {}".format(
            enumeration_error
        )
        if fallback_error is not None:
            message += "; direct-child fallback failed: {}".format(fallback_error)
        raise CleanupError(message) from enumeration_error


def _bounded_pause(deadline, maximum=0.02):
    remaining = deadline - time.monotonic()
    if remaining > 0:
        select.select([], [], [], min(maximum, remaining))


def _reap_scoped_children(pids):
    if not IS_CHILD_SUBREAPER:
        return
    for pid in pids:
        try:
            os.waitpid(pid, os.WNOHANG)
        except OSError as error:
            if error.errno not in (errno.ECHILD, errno.ESRCH):
                raise


def terminate_session(process, grace=0.5):
    """Boundedly terminate only members of the process's dedicated session."""
    session_id = process.pid
    observed = set()
    for chosen_signal in (signal.SIGTERM, signal.SIGKILL):
        deadline = time.monotonic() + grace
        while True:
            members = _session_members_for_cleanup(process, session_id, grace)
            observed.update(pid for pid, _ in members)
            live = [pid for pid, state in members if not state.startswith("Z")]
            for pid in live:
                _signal_if_same_session(pid, session_id, chosen_signal)
            if not live or time.monotonic() >= deadline:
                break
            _bounded_pause(deadline)

    if process.poll() is None:
        try:
            process.wait(timeout=grace)
        except subprocess.TimeoutExpired:
            _signal_if_same_session(process.pid, session_id, signal.SIGKILL)
            try:
                process.wait(timeout=grace)
            except subprocess.TimeoutExpired:
                raise CleanupError(
                    "direct child {} did not exit after SIGKILL".format(process.pid)
                )
    observed.discard(process.pid)

    deadline = time.monotonic() + grace
    while time.monotonic() < deadline:
        members = _session_members_for_cleanup(process, session_id, grace)
        observed.update(pid for pid, _ in members)
        _reap_scoped_children(observed)
        if not members:
            break
        for pid, state in members:
            if not state.startswith("Z"):
                _signal_if_same_session(pid, session_id, signal.SIGKILL)
        _bounded_pause(deadline)
    _reap_scoped_children(observed)

    remaining = _session_members_for_cleanup(process, session_id, grace)
    observed.update(pid for pid, _ in remaining)
    _reap_scoped_children(observed)
    live_remaining = [
        pid for pid, state in remaining if not state.startswith("Z")
    ]
    for pid in live_remaining:
        _signal_if_same_session(pid, session_id, signal.SIGKILL)
    if live_remaining:
        raise CleanupError(
            "session cleanup incomplete: live members remain after bounded cleanup: {}".format(
                ", ".join(str(pid) for pid in live_remaining)
            )
        )


def communicate_bounded(process, input_text, timeout, description):
    try:
        stdout, stderr = process.communicate(input_text, timeout=timeout)
    except subprocess.TimeoutExpired:
        terminate_session(process)
        try:
            stdout, stderr = process.communicate(timeout=0.5)
        except subprocess.TimeoutExpired as final_timeout:
            stdout = final_timeout.output or ""
            stderr = final_timeout.stderr or ""
            if process.stdout is not None:
                process.stdout.close()
            if process.stderr is not None:
                process.stderr.close()
        raise AssertionError(
            "process timed out: {!r}\nstdout={!r}\nstderr={!r}".format(
                description, stdout, stderr
            )
        )
    terminate_session(process)
    return process.returncode, stdout, stderr


def run_process(arguments, input_text=None, cwd=None, env=None, timeout=5.0):
    process = subprocess.Popen(
        arguments,
        stdin=subprocess.PIPE if input_text is not None else subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=cwd,
        env=env,
        universal_newlines=True,
        start_new_session=True,
    )
    return communicate_bounded(process, input_text, timeout, arguments)


def run_command_with_closed_fds(command, closed_fds, timeout=5.0):
    def close_requested_fds():
        for descriptor in closed_fds:
            try:
                os.close(descriptor)
            except OSError as error:
                if error.errno != errno.EBADF:
                    raise

    process = subprocess.Popen(
        [SHELL, "-c", command],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        preexec_fn=close_requested_fds,
        universal_newlines=True,
        start_new_session=True,
    )
    return communicate_bounded(process, None, timeout, [SHELL, "-c", command])


def run_command(command, cwd=None, env=None, timeout=5.0):
    return run_process([SHELL, "-c", command], cwd=cwd, env=env, timeout=timeout)


def run_script(script, cwd=None, env=None, timeout=5.0):
    return run_process([SHELL], input_text=script, cwd=cwd, env=env, timeout=timeout)


class ShellTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not os.path.isfile(SHELL) or not os.access(SHELL, os.X_OK):
            raise unittest.SkipTest("shell executable not found: {}".format(SHELL))
        if MISSING_TOOLS:
            raise unittest.SkipTest(
                "required standard utilities not found: {}".format(
                    ", ".join(MISSING_TOOLS)
                )
            )


class ParsingTests(ShellTestCase):
    def test_only_documented_invocation_shapes_are_accepted(self):
        for arguments in ([SHELL, "--help"], [SHELL, "-c"], [SHELL, "x", "y"]):
            with self.subTest(arguments=arguments):
                status, stdout, stderr = run_process(arguments)
                self.assertNotEqual(status, 0)
                self.assertEqual(stdout, "")
                self.assertIn("usage: byosh [-c COMMAND]", stderr)

    def test_quotes_escapes_empty_words_and_concatenation(self):
        command = tool("printf") + r''' '<%s>\n' plain 'two words' "three words" escaped\ space "" ab"cd"'ef' 'single\slash' "double\slash" '''
        status, stdout, stderr = run_command(command)
        self.assertEqual(status, 0, stderr)
        self.assertEqual(
            stdout,
            "<plain>\n<two words>\n<three words>\n<escaped space>\n<>\n"
            "<abcdef>\n<single\\slash>\n<double\\slash>\n",
        )
        self.assertEqual(stderr, "")

    def test_operators_need_no_surrounding_whitespace(self):
        status, stdout, stderr = run_command(
            "{} abc|{} a-z A-Z".format(tool("printf"), tool("tr"))
        )
        self.assertEqual((status, stdout, stderr), (0, "ABC", ""))

    def test_parse_errors_are_status_two_and_descriptive(self):
        cases = [
            (tool("printf") + " 'unterminated", "unclosed single quote"),
            (tool("printf") + " trailing\\", "trailing escape"),
            ("| " + tool("cat"), "missing command before pipe"),
            (tool("printf") + " ok |", "missing command after pipe"),
            (tool("cat") + " <", "redirection requires a path"),
            (
                "{} ok & {}".format(tool("printf"), tool("cat")),
                "background marker must be last",
            ),
        ]
        for command, fragment in cases:
            with self.subTest(command=command):
                status, stdout, stderr = run_command(command)
                self.assertEqual(status, 2)
                self.assertEqual(stdout, "")
                self.assertIn("byosh: parse error:", stderr)
                self.assertIn(fragment, stderr)

    def test_duplicate_same_stream_redirections_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            first = os.path.join(directory, "first")
            second = os.path.join(directory, "second")
            command = "{} data > {} >> {}".format(
                tool("printf"), shell_quote(first), shell_quote(second)
            )
            status, stdout, stderr = run_command(command)
            self.assertEqual(status, 2)
            self.assertEqual(stdout, "")
            self.assertIn("duplicate output redirection", stderr)
            self.assertFalse(os.path.exists(first))
            self.assertFalse(os.path.exists(second))

    def test_semicolon_and_hash_have_no_special_meaning(self):
        status, stdout, stderr = run_command(
            "{} '%s|%s' 'a;b' '#literal'".format(tool("printf"))
        )
        self.assertEqual((status, stdout, stderr), (0, "a;b|#literal", ""))


class RedirectionAndPipelineTests(ShellTestCase):
    def test_redirection_preserves_open_result_equal_to_standard_fd(self):
        with tempfile.TemporaryDirectory() as directory:
            source = os.path.join(directory, "source")
            copied = os.path.join(directory, "copied")
            generated = os.path.join(directory, "generated")
            with open(source, "w") as stream:
                stream.write("input-survived")

            status, stdout, stderr = run_command_with_closed_fds(
                "{} < {} > {}".format(
                    tool("cat"), shell_quote(source), shell_quote(copied)
                ),
                [0],
            )
            self.assertEqual((status, stdout, stderr), (0, "", ""))
            with open(copied, "r") as stream:
                self.assertEqual(stream.read(), "input-survived")

            status, stdout, stderr = run_command_with_closed_fds(
                "{} output-survived > {}".format(
                    tool("printf"), shell_quote(generated)
                ),
                [1],
            )
            self.assertEqual((status, stdout, stderr), (0, "", ""))
            with open(generated, "r") as stream:
                self.assertEqual(stream.read(), "output-survived")

    def test_pipeline_descriptors_avoid_closed_stdin_and_stdout(self):
        with tempfile.TemporaryDirectory() as directory:
            output = os.path.join(directory, "pipeline output")
            status, stdout, stderr = run_command_with_closed_fds(
                "{} pipeline-data | {} | {} > {}".format(
                    tool("printf"),
                    tool("cat"),
                    tool("cat"),
                    shell_quote(output),
                ),
                [0, 1],
            )
            self.assertEqual((status, stdout, stderr), (0, "", ""))
            with open(output, "r") as stream:
                self.assertEqual(stream.read(), "pipeline-data")

            status, stdout, stderr = run_command_with_closed_fds(
                "{} visible-through-pipe | {}".format(
                    tool("printf"), tool("cat")
                ),
                [0],
            )
            self.assertEqual((status, stdout, stderr), (0, "visible-through-pipe", ""))

    def test_truncate_append_input_and_paths_with_spaces(self):
        with tempfile.TemporaryDirectory() as directory:
            source = os.path.join(directory, "source file")
            output = os.path.join(directory, "output file")

            status, stdout, stderr = run_command(
                "{} first > {}".format(tool("printf"), shell_quote(source))
            )
            self.assertEqual((status, stdout, stderr), (0, "", ""))
            status, stdout, stderr = run_command(
                "{} second >> {}".format(tool("printf"), shell_quote(source))
            )
            self.assertEqual((status, stdout, stderr), (0, "", ""))
            with open(source, "r") as stream:
                self.assertEqual(stream.read(), "firstsecond")

            status, stdout, stderr = run_command(
                "{} < {} | {} a-z A-Z > {}".format(
                    tool("cat"),
                    shell_quote(source),
                    tool("tr"),
                    shell_quote(output),
                )
            )
            self.assertEqual((status, stdout, stderr), (0, "", ""))
            with open(output, "r") as stream:
                self.assertEqual(stream.read(), "FIRSTSECOND")

    def test_explicit_output_redirection_overrides_pipe_endpoint(self):
        with tempfile.TemporaryDirectory() as directory:
            destination = os.path.join(directory, "diverted")
            status, stdout, stderr = run_command(
                "{} diverted > {} | {} -c".format(
                    tool("printf"), shell_quote(destination), tool("wc")
                )
            )
            self.assertEqual(status, 0, stderr)
            self.assertEqual(stdout.strip(), "0")
            with open(destination, "r") as stream:
                self.assertEqual(stream.read(), "diverted")

    def test_explicit_input_redirection_overrides_pipe_endpoint(self):
        with tempfile.TemporaryDirectory() as directory:
            source = os.path.join(directory, "input")
            with open(source, "w") as stream:
                stream.write("from-file")
            status, stdout, stderr = run_command(
                "{} from-pipe | {} < {}".format(
                    tool("printf"), tool("cat"), shell_quote(source)
                )
            )
            self.assertEqual(status, 0, stderr)
            self.assertEqual(stdout, "from-file")

    def test_three_stage_pipeline_runs_concurrently(self):
        status, stdout, stderr = run_command(
            "{} x | {} -n 50000 | {} -l".format(
                tool("yes"), tool("head"), tool("wc")
            ),
            timeout=8.0,
        )
        self.assertEqual(status, 0, stderr)
        self.assertEqual(stdout.strip(), "50000")

    def test_pipeline_status_comes_from_last_command(self):
        status, stdout, stderr = run_command(
            "{} -c 'exit 3' | {} -c 'exit 9'".format(tool("sh"), tool("sh"))
        )
        self.assertEqual(status, 9, stderr)
        self.assertEqual(stdout, "")

    def test_missing_command_is_status_127(self):
        status, stdout, stderr = run_command("byosh_command_that_does_not_exist")
        self.assertEqual(status, 127)
        self.assertEqual(stdout, "")
        self.assertIn("command not found", stderr)


class BuiltinTests(ShellTestCase):
    def test_cd_changes_parent_for_later_input_lines(self):
        with tempfile.TemporaryDirectory() as directory:
            child = os.path.join(directory, "directory with spaces")
            os.mkdir(child)
            script = "pwd\ncd {}\npwd\n".format(shell_quote(child))
            status, stdout, stderr = run_script(script, cwd=directory)
            self.assertEqual(status, 0, stderr)
            self.assertEqual(stdout.splitlines(), [directory, child])

    def test_cd_without_argument_uses_home(self):
        with tempfile.TemporaryDirectory() as directory:
            env = os.environ.copy()
            env["HOME"] = directory
            status, stdout, stderr = run_script("cd\npwd\n", env=env)
            self.assertEqual(status, 0, stderr)
            self.assertEqual(stdout, directory + "\n")

    def test_cd_in_pipeline_does_not_change_parent(self):
        with tempfile.TemporaryDirectory() as directory:
            status, stdout, stderr = run_script(
                "cd / | {}\npwd\n".format(tool("cat")), cwd=directory
            )
            self.assertEqual(status, 0, stderr)
            self.assertEqual(stdout, directory + "\n")

    def test_parent_builtin_honors_and_restores_redirection(self):
        with tempfile.TemporaryDirectory() as directory:
            output = os.path.join(directory, "pwd output")
            script = "pwd > {}\n{} visible\n".format(
                shell_quote(output), tool("printf")
            )
            status, stdout, stderr = run_script(script, cwd=directory)
            self.assertEqual(status, 0, stderr)
            self.assertEqual(stdout, "visible")
            with open(output, "r") as stream:
                self.assertEqual(stream.read(), directory + "\n")

    def test_parent_builtins_restore_initially_closed_standard_fds(self):
        with tempfile.TemporaryDirectory() as directory:
            output = os.path.join(directory, "closed stdout pwd")
            status, stdout, stderr = run_command_with_closed_fds(
                "pwd > {}".format(shell_quote(output)), [1]
            )
            self.assertEqual((status, stdout, stderr), (0, "", ""))
            with open(output, "r") as stream:
                self.assertTrue(stream.read().endswith("\n"))

        status, stdout, stderr = run_command_with_closed_fds("cd /", [0])
        self.assertEqual((status, stdout, stderr), (0, "", ""))

    def test_output_builtins_report_closed_stdout(self):
        for command in ("pwd", "jobs"):
            with self.subTest(command=command):
                status, stdout, stderr = run_command_with_closed_fds(command, [1])
                self.assertEqual(status, 1)
                self.assertEqual(stdout, "")
                self.assertIn("byosh: {}:".format(command), stderr)

    def test_builtin_argument_errors_use_status_two(self):
        for command in ("pwd extra", "jobs extra", "cd one two"):
            with self.subTest(command=command):
                status, stdout, stderr = run_command(command)
                self.assertEqual(status, 2)
                self.assertEqual(stdout, "")
                self.assertIn("byosh:", stderr)

    def test_exit_stops_input_and_uses_requested_status(self):
        status, stdout, stderr = run_script(
            "{} before\nexit 300\n{} after\n".format(
                tool("printf"), tool("printf")
            )
        )
        self.assertEqual(status, 44, stderr)
        self.assertEqual(stdout, "before")

    def test_exit_without_argument_uses_previous_status(self):
        status, stdout, stderr = run_script(
            "{} -c 'exit 6'\nexit\n".format(tool("sh"))
        )
        self.assertEqual(status, 6, stderr)
        self.assertEqual(stdout, "")

    def test_bad_numeric_exit_stops_with_status_two(self):
        status, stdout, stderr = run_script(
            "exit nope\n{} after\n".format(tool("printf"))
        )
        self.assertEqual(status, 2)
        self.assertEqual(stdout, "")
        self.assertIn("numeric argument required", stderr)


class NonInteractiveJobTests(ShellTestCase):
    def test_background_job_is_visible_to_jobs(self):
        sleeper = "{} 30".format(tool("sleep"))
        status, stdout, stderr = run_script(
            "{} &\njobs\nexit 0\n".format(sleeper)
        )
        self.assertEqual(status, 0, stderr)
        self.assertIn("[1] Running {} &".format(sleeper), stdout)
        self.assertRegex(stderr, r"\[1\] [0-9]+")

    def test_fg_accepts_percent_job_id_and_waits(self):
        status, stdout, stderr = run_script(
            "{} 1 &\nfg %1\n{} foreground-complete\n".format(
                tool("sleep"), tool("printf")
            ),
            timeout=5.0,
        )
        self.assertEqual(status, 0, stderr)
        self.assertEqual(stdout, "foreground-complete")
        self.assertRegex(stderr, r"\[1\] [0-9]+")

    def test_fg_and_bg_report_missing_jobs(self):
        for command in ("fg", "bg 99", "fg %bad"):
            with self.subTest(command=command):
                status, stdout, stderr = run_command(command)
                self.assertEqual(status, 1)
                self.assertEqual(stdout, "")
                self.assertIn("byosh:", stderr)

    def test_jobs_in_pipeline_does_not_list_its_own_pipeline(self):
        sleeper = "{} 30".format(tool("sleep"))
        status, stdout, stderr = run_script(
            "{} &\njobs | {}\nexit 0\n".format(sleeper, tool("cat"))
        )
        self.assertEqual(status, 0, stderr)
        self.assertIn("[1] Running {} &".format(sleeper), stdout)
        self.assertNotIn("[2]", stdout)

    def test_bg_rejects_running_job_without_changing_its_state(self):
        sleeper = "{} 30".format(tool("sleep"))
        status, stdout, stderr = run_script(
            "{} &\nbg %1\njobs\nexit 0\n".format(sleeper)
        )
        self.assertEqual(status, 0, stderr)
        self.assertEqual(stdout.count("[1] Running {} &".format(sleeper)), 1)
        self.assertIn("bg: job is not stopped", stderr)


def _make_controlling_terminal():
    os.setsid()
    fcntl.ioctl(0, termios.TIOCSCTTY, 0)


class PtyShell(object):
    def __init__(self):
        self.master, slave = pty.openpty()
        self.process = subprocess.Popen(
            [SHELL],
            stdin=slave,
            stdout=slave,
            stderr=slave,
            preexec_fn=_make_controlling_terminal,
            close_fds=True,
        )
        os.close(slave)
        self.buffer = b""

    def send(self, data):
        os.write(self.master, data)

    def wait_for_foreground_owner(self, shell_owns_terminal, timeout=3.0):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            foreground = os.tcgetpgrp(self.master)
            owns_terminal = foreground == self.process.pid
            if owns_terminal == shell_owns_terminal:
                return foreground
            if self.process.poll() is not None:
                raise AssertionError("shell exited while waiting for terminal owner")
            _bounded_pause(deadline, maximum=0.01)
        raise AssertionError(
            "terminal owner did not become {} (last pgrp {})".format(
                "shell" if shell_owns_terminal else "foreground job",
                os.tcgetpgrp(self.master),
            )
        )

    def read_until(self, marker, timeout=5.0):
        deadline = time.monotonic() + timeout
        while marker not in self.buffer:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise AssertionError(
                    "timed out waiting for {!r}; received {!r}".format(
                        marker, self.buffer
                    )
                )
            readable, _, _ = select.select([self.master], [], [], remaining)
            if not readable:
                continue
            try:
                chunk = os.read(self.master, 4096)
            except OSError as error:
                if error.errno == errno.EIO and self.process.poll() is not None:
                    chunk = b""
                else:
                    raise
            if not chunk:
                raise AssertionError(
                    "pty closed waiting for {!r}; received {!r}".format(
                        marker, self.buffer
                    )
                )
            self.buffer += chunk
        end = self.buffer.index(marker) + len(marker)
        result = self.buffer[:end]
        self.buffer = self.buffer[end:]
        return result.decode("utf-8", "replace").replace("\r\n", "\n")

    def close(self):
        if self.process.poll() is None:
            try:
                self.send(b"exit\n")
                self.process.wait(timeout=1.0)
            except (OSError, subprocess.TimeoutExpired):
                pass
        terminate_session(self.process)
        os.close(self.master)


@unittest.skipUnless(hasattr(termios, "TIOCSCTTY"), "controlling pty unavailable")
class InteractiveJobControlTests(ShellTestCase):
    def test_idle_shell_reaps_completed_background_job_without_input(self):
        session = PtyShell()
        try:
            session.read_until(b"byosh$ ")
            quick_command = "{} &".format(tool("true"))
            for job_id in range(1, 31):
                encoded = quick_command.encode("utf-8")
                session.send(encoded + b"\n")
                session.read_until(encoded + b"\r\n")
                done_marker = "[{}] Done {}".format(job_id, quick_command).encode(
                    "utf-8"
                )
                completed = session.read_until(done_marker, timeout=3.0)
                self.assertIn(done_marker.decode("utf-8"), completed)
                session.read_until(b"byosh$ ")
            session.send(b"exit 0\n")
            self.assertEqual(session.process.wait(timeout=2.0), 0)
        finally:
            session.close()

    def test_foreground_child_observes_terminal_handoff_before_execution(self):
        session = PtyShell()
        try:
            session.read_until(b"byosh$ ")
            probe = (
                'import os; os.write(1, b"HANDOFF_OK\\n" if '
                'os.tcgetpgrp(0) == os.getpgrp() else b"HANDOFF_BAD\\n")'
            )
            command = "{} -c {}".format(shell_quote(PYTHON), shell_quote(probe))
            encoded = command.encode("utf-8")
            for _ in range(30):
                session.send(encoded + b"\n")
                session.read_until(encoded + b"\r\n")
                output = session.read_until(b"byosh$ ")
                self.assertIn("HANDOFF_OK", output)
                self.assertNotIn("HANDOFF_BAD", output)
            session.send(b"exit 0\n")
            self.assertEqual(session.process.wait(timeout=2.0), 0)
        finally:
            session.close()

    def test_stop_jobs_bg_fg_interrupt_and_shell_survival(self):
        session = PtyShell()
        try:
            opening = session.read_until(b"byosh$ ")
            self.assertEqual(opening, "byosh$ ")

            sleeper = "{} 30".format(tool("sleep"))
            sleeper_bytes = sleeper.encode("utf-8")
            session.send(sleeper_bytes + b"\n")
            session.read_until(sleeper_bytes + b"\r\n")
            session.wait_for_foreground_owner(False)
            session.send(b"\x1a")
            stopped_marker = "Stopped {}".format(sleeper).encode("utf-8")
            stopped = session.read_until(stopped_marker)
            self.assertIn(stopped_marker.decode("utf-8"), stopped)
            session.read_until(b"byosh$ ")
            session.wait_for_foreground_owner(True)

            session.send(b"jobs\n")
            session.read_until(b"jobs\r\n")
            jobs_marker = "[1] Stopped {}".format(sleeper).encode("utf-8")
            jobs_output = session.read_until(jobs_marker)
            self.assertIn(jobs_marker.decode("utf-8"), jobs_output)
            session.read_until(b"byosh$ ")

            session.send(b"bg %1\n")
            session.read_until(b"bg %1\r\n")
            running_marker = "[1] Running {}".format(sleeper).encode("utf-8")
            backgrounded = session.read_until(running_marker)
            self.assertIn(running_marker.decode("utf-8"), backgrounded)
            session.read_until(b"byosh$ ")

            session.send(b"fg %1\n")
            session.read_until(b"fg %1\r\n")
            session.wait_for_foreground_owner(False)
            session.send(b"\x03")
            session.read_until(b"^C")
            session.read_until(b"byosh$ ")
            session.wait_for_foreground_owner(True)

            visible = "{} alive".format(tool("printf")).encode("utf-8")
            session.send(visible + b"\n")
            session.read_until(visible + b"\r\n")
            alive = session.read_until(b"alive")
            self.assertIn("alive", alive)
            session.read_until(b"byosh$ ")

            session.send(b"exit 0\n")
            self.assertEqual(session.process.wait(timeout=2.0), 0)
        finally:
            session.close()


if __name__ == "__main__":
    unittest.main()
