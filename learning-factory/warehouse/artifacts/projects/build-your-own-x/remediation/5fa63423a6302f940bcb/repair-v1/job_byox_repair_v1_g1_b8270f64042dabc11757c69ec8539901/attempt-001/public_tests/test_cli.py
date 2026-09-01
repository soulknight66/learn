#!/usr/bin/env python3
"""Black-box public checks for a completed byosh executable.

The harness intentionally remains compatible with Python 3.6, the interpreter
available in the recorded build environment.
"""

import argparse
import errno
import os
import pathlib
import shutil
import signal
import subprocess
import sys
import tempfile


COMMAND_TIMEOUT_SECONDS = 5.0
PS_TIMEOUT_SECONDS = 0.5
REAP_TIMEOUT_SECONDS = 1.0
SESSION_CLEANUP_PASSES = 4
LOG_TAIL_CHARACTERS = 4000


def require_tool(name):
    path = shutil.which(name)
    if path is None:
        raise RuntimeError("required utility is not available on PATH: {0}".format(name))
    return os.path.abspath(path)


def shell_quote(value):
    """Quote one word for the deliberately small byosh grammar."""
    return "'" + value.replace("'", "'\\''") + "'"


def kill_helper(process):
    """Kill a helper's private group without ever waiting indefinitely."""
    errors = []
    if process.poll() is not None:
        return errors
    try:
        if os.getsid(process.pid) == process.pid:
            os.killpg(process.pid, signal.SIGKILL)
        else:
            process.kill()
    except OSError as error:
        if error.errno != errno.ESRCH:
            errors.append("killpg: {0}".format(error))
    try:
        process.kill()
    except OSError as error:
        if error.errno != errno.ESRCH:
            errors.append("kill: {0}".format(error))
    return errors


def session_members(ps_path, session_id):
    """Return (pid, state) rows for one session using a bounded helper."""
    process = subprocess.Popen(
        [
            ps_path,
            "-o",
            "pid=",
            "-o",
            "sid=",
            "-o",
            "stat=",
            "--sid",
            str(session_id),
        ],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
        start_new_session=True,
    )
    try:
        output, standard_error = process.communicate(timeout=PS_TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired:
        errors = kill_helper(process)
        try:
            process.communicate(timeout=REAP_TIMEOUT_SECONDS)
        except subprocess.TimeoutExpired:
            errors.append("helper could not be reaped within the cleanup timeout")
        detail = "; ".join(errors)
        if detail:
            detail = ": " + detail
        raise RuntimeError("ps timed out while enumerating the test session{0}".format(detail))

    # procps returns 1, with no diagnostic, when the selected session has no
    # remaining processes. No unrelated process-table rows were requested.
    if process.returncode == 1 and not output.strip() and not standard_error.strip():
        return []
    if process.returncode != 0:
        raise RuntimeError(
            "ps exited {0} while enumerating the test session: {1}".format(
                process.returncode, standard_error.strip()
            )
        )

    members = []
    for line in output.splitlines():
        fields = line.split()
        if len(fields) < 3:
            continue
        try:
            pid = int(fields[0])
            row_session_id = int(fields[1])
        except ValueError:
            continue
        if row_session_id == session_id:
            members.append((pid, fields[2]))
    return members


def signal_session_process(pid, session_id):
    """Signal only a PID that still belongs to the session we created."""
    try:
        current_session_id = os.getsid(pid)
    except OSError as error:
        if error.errno == errno.ESRCH:
            return None
        return "getsid({0}): {1}".format(pid, error)
    if current_session_id != session_id:
        return "refused to signal reused pid {0}".format(pid)
    try:
        os.kill(pid, signal.SIGKILL)
    except OSError as error:
        if error.errno != errno.ESRCH:
            return "kill({0}): {1}".format(pid, error)
    return None


def fallback_kill(process, session_id):
    errors = [
        "scoped session enumeration failed; descendant cleanup is unverified"
    ]
    # A live, unreaped Popen child cannot have had its PID reused. Signal only
    # that known child; never infer that its numeric SID is still a safe PGID.
    if process.poll() is None:
        error = signal_session_process(process.pid, session_id)
        if error:
            errors.append(error)
    return errors


def terminate_session(process, session_id, ps_path):
    """Boundedly kill every live process still in the target's session."""
    notes = []
    for unused_pass in range(SESSION_CLEANUP_PASSES):
        try:
            rows = session_members(ps_path, session_id)
        except RuntimeError as error:
            notes.append(str(error))
            notes.extend(fallback_kill(process, session_id))
            return notes

        live_pids = [pid for pid, state in rows if not state.startswith("Z")]
        if process.poll() is None and process.pid not in live_pids:
            live_pids.append(process.pid)
        if not live_pids:
            return notes

        # Stop the shell/session leader first so it cannot create more children
        # while the remaining process groups are being dismantled.
        live_pids.sort(key=lambda pid: 0 if pid == session_id else 1)
        for pid in live_pids:
            error = signal_session_process(pid, session_id)
            if error:
                notes.append(error)

    try:
        rows = session_members(ps_path, session_id)
    except RuntimeError as error:
        notes.append(str(error))
        notes.extend(fallback_kill(process, session_id))
        return notes
    survivors = [pid for pid, state in rows if not state.startswith("Z")]
    for pid in survivors:
        error = signal_session_process(pid, session_id)
        if error:
            notes.append(error)
    if survivors:
        notes.append("session still listed live pids after cleanup: {0}".format(survivors))
    return notes


def reap_target(process, session_id):
    """Collect a killed target and its pipe data with bounded retries."""
    try:
        return process.communicate(timeout=REAP_TIMEOUT_SECONDS), []
    except subprocess.TimeoutExpired as error:
        notes = ["target did not reap within the first cleanup timeout"]
        if process.poll() is None:
            target_error = signal_session_process(process.pid, session_id)
            if target_error:
                notes.append(target_error)
        try:
            return process.communicate(timeout=REAP_TIMEOUT_SECONDS), notes
        except subprocess.TimeoutExpired:
            notes.append("target could not be reaped within the final cleanup timeout")
            return (getattr(error, "output", None), getattr(error, "stderr", None)), notes


def log_tail(value):
    if value is None:
        return "<not captured>"
    if isinstance(value, bytes):
        value = value.decode("utf-8", "replace")
    return value[-LOG_TAIL_CHARACTERS:]


def invoke(shell, arguments, cwd, ps_path, script=None):
    argv = [str(shell)] + arguments
    process = subprocess.Popen(
        argv,
        cwd=str(cwd),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
        start_new_session=True,
    )
    session_id = process.pid
    try:
        output, standard_error = process.communicate(
            input=script, timeout=COMMAND_TIMEOUT_SECONDS
        )
    except subprocess.TimeoutExpired as error:
        notes = terminate_session(process, session_id, ps_path)
        (output, standard_error), reap_notes = reap_target(process, session_id)
        notes.extend(reap_notes)
        if output is None:
            output = getattr(error, "output", None)
        if standard_error is None:
            standard_error = getattr(error, "stderr", None)
        raise RuntimeError(
            "tested shell timed out after {0:.1f}s: {1!r}\n"
            "stdout tail:\n{2}\nstderr tail:\n{3}\ncleanup: {4}".format(
                COMMAND_TIMEOUT_SECONDS,
                argv,
                log_tail(output),
                log_tail(standard_error),
                "; ".join(notes) if notes else "complete",
            )
        )
    except Exception:
        terminate_session(process, session_id, ps_path)
        reap_target(process, session_id)
        raise

    try:
        rows = session_members(ps_path, session_id)
    except RuntimeError:
        terminate_session(process, session_id, ps_path)
        raise
    live_pids = [pid for pid, state in rows if not state.startswith("Z")]
    if live_pids:
        notes = terminate_session(process, session_id, ps_path)
        raise RuntimeError(
            "tested shell returned but left live session processes {0}: {1}".format(
                live_pids, "; ".join(notes) if notes else "cleanup complete"
            )
        )
    return subprocess.CompletedProcess(
        argv, process.returncode, stdout=output, stderr=standard_error
    )


def run(shell, command, cwd, ps_path):
    return invoke(shell, ["-c", command], cwd, ps_path)


def run_script(shell, script, cwd, ps_path):
    return invoke(shell, [], cwd, ps_path, script=script)


def require(condition, message, details=""):
    if not condition:
        suffix = f"\n{details}" if details else ""
        raise AssertionError(f"{message}{suffix}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("shell", type=pathlib.Path)
    args = parser.parse_args()
    shell = args.shell.resolve()
    tools = dict(
        (name, require_tool(name)) for name in ("false", "printf", "ps", "tr")
    )
    quoted_printf = shell_quote(tools["printf"])
    quoted_tr = shell_quote(tools["tr"])

    with tempfile.TemporaryDirectory(prefix="byosh-public-") as directory:
        work = pathlib.Path(directory)

        result = run(shell, "{0} 'hello world'".format(quoted_printf), work, tools["ps"])
        require(result.returncode == 0, "simple command failed", result.stderr)
        require(result.stdout == "hello world", "quoting changed output", repr(result.stdout))

        result = run(
            shell,
            "{0} abc | {1} a-z A-Z".format(quoted_printf, quoted_tr),
            work,
            tools["ps"],
        )
        require(result.returncode == 0, "pipeline failed", result.stderr)
        require(result.stdout == "ABC", "pipeline output differs", repr(result.stdout))

        output = work / "result.txt"
        result = run(
            shell, "{0} first > result.txt".format(quoted_printf), work, tools["ps"]
        )
        require(result.returncode == 0, "output redirection failed", result.stderr)
        result = run(
            shell, "{0} second >> result.txt".format(quoted_printf), work, tools["ps"]
        )
        require(result.returncode == 0, "append redirection failed", result.stderr)
        require(output.read_text() == "firstsecond", "redirection content differs")

        source = work / "source.txt"
        source.write_text("mixed Case")
        result = run(
            shell, "{0} a-z A-Z < source.txt".format(quoted_tr), work, tools["ps"]
        )
        require(result.returncode == 0, "input redirection failed", result.stderr)
        require(result.stdout == "MIXED CASE", "input content differs")

        result = run(shell, "pwd", work, tools["ps"])
        require(result.returncode == 0, "pwd builtin failed", result.stderr)
        require(pathlib.Path(result.stdout.strip()) == work, "pwd reported another directory")

        child = work / "child"
        child.mkdir()
        result = run_script(shell, "cd child\npwd\n", work, tools["ps"])
        require(result.returncode == 0, "cd script failed", result.stderr)
        require(pathlib.Path(result.stdout.strip()) == child, "cd did not persist")

        result = run(shell, "exit 7", work, tools["ps"])
        require(result.returncode == 7, "exit did not preserve requested status")

        result = run(shell, "printf 'unterminated", work, tools["ps"])
        require(result.returncode == 2, "syntax error did not return status 2")

        result = run(shell, "definitely_not_a_byosh_command", work, tools["ps"])
        require(result.returncode != 0, "missing command unexpectedly succeeded")

        result = run_script(
            shell, "{0}\n\n".format(shell_quote(tools["false"])), work, tools["ps"]
        )
        require(
            result.returncode == 1,
            "a trailing blank line reset the preceding nonzero status",
            result.stderr,
        )

    print("completed-shell public smoke tests: PASS")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError) as error:
        print("public test harness error: {0}".format(error), file=sys.stderr)
        raise SystemExit(2)
