#!/usr/bin/env python3
"""Deterministic black-box tests for the sealed minish reference."""

from __future__ import print_function

import os
import pathlib
import pty
import select
import signal
import subprocess
import tempfile
import termios
import time
import unittest


HERE = pathlib.Path(__file__).resolve().parent
REFERENCE = HERE.parent / "reference"
BINARY = REFERENCE / "minish"


def session_groups(session_id):
    try:
        listing = subprocess.run(
            ["ps", "-e", "-o", "sid=", "-o", "pgid="],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            timeout=2,
            check=True,
        )
    except (OSError, subprocess.SubprocessError):
        return {session_id}
    groups = set()
    for row in listing.stdout.splitlines():
        fields = row.split()
        if len(fields) == 2 and fields[0].isdigit() and fields[1].isdigit():
            if int(fields[0]) == session_id and int(fields[1]) > 0:
                groups.add(int(fields[1]))
    return groups


def signal_session(session_id, signal_number):
    for unused_round in range(3):
        groups = session_groups(session_id)
        if not groups:
            return
        for group in groups:
            try:
                os.killpg(group, signal_number)
            except ProcessLookupError:
                pass
        time.sleep(0.01)


class MiniShellTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        completed = subprocess.run(
            ["make", "-C", str(REFERENCE), "clean", "all"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
        )
        if completed.returncode != 0:
            raise RuntimeError(
                "reference build failed\nstdout:\n{}\nstderr:\n{}".format(
                    completed.stdout, completed.stderr
                )
            )

    def run_shell(self, command=None, input_data=None, cwd=None, env_updates=None,
                  timeout=5):
        argv = [str(BINARY)]
        if command is not None:
            argv.extend(["-c", command])
        environment = os.environ.copy()
        environment["LC_ALL"] = "C"
        if env_updates:
            environment.update(env_updates)
        process = subprocess.Popen(
            argv,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=cwd,
            env=environment,
            universal_newlines=True,
            start_new_session=True,
        )
        try:
            stdout, stderr = process.communicate(input_data, timeout=timeout)
        except subprocess.TimeoutExpired:
            signal_session(process.pid, signal.SIGKILL)
            process.communicate(timeout=2)
            raise
        return subprocess.CompletedProcess(argv, process.returncode,
                                           stdout, stderr)

    @staticmethod
    def read_until(fd, marker, timeout):
        data = b""
        deadline = time.monotonic() + timeout
        while marker not in data:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise AssertionError(
                    "timed out waiting for {!r}; transcript={!r}".format(
                        marker, data
                    )
                )
            readable, unused_writable, unused_exceptional = select.select(
                [fd], [], [], remaining
            )
            if not readable:
                continue
            try:
                chunk = os.read(fd, 4096)
            except OSError:
                chunk = b""
            if not chunk:
                raise AssertionError(
                    "terminal closed before {!r}; transcript={!r}".format(
                        marker, data
                    )
                )
            data += chunk
        return data

    @staticmethod
    def wait_for_child(pid, timeout):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            waited, status = os.waitpid(pid, os.WNOHANG)
            if waited == pid:
                return status
            time.sleep(0.01)
        raise AssertionError("child {} did not exit".format(pid))

    def test_cli_rejects_unsupported_forms(self):
        result = subprocess.run(
            [str(BINARY), "script.minish"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
        )
        self.assertEqual(2, result.returncode)
        self.assertEqual("", result.stdout)
        self.assertEqual("Usage: minish [-c COMMAND]\n", result.stderr)

    def test_help_describes_both_input_modes(self):
        result = subprocess.run(
            [str(BINARY), "--help"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
        )
        self.assertEqual(0, result.returncode)
        self.assertIn("Usage:", result.stdout)
        self.assertIn("-c COMMAND", result.stdout)
        self.assertIn("standard input", result.stdout)
        self.assertEqual("", result.stderr)

    def test_quotes_escapes_empty_word_and_concatenation(self):
        command = (
            "printf '<%s>\\n' plain 'two words' \"three words\" "
            "escaped\\ space \"\" a\"b\"'c'"
        )
        result = self.run_shell(command)
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual(
            "<plain>\n<two words>\n<three words>\n<escaped space>\n<>\n<abc>\n",
            result.stdout,
        )
        self.assertEqual("", result.stderr)

    def test_quoted_and_escaped_operators_are_words(self):
        result = self.run_shell(
            "printf '%s\\n' a\\|b \"c;d\" 'e&f' g\\>h i\\<j"
        )
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual("a|b\nc;d\ne&f\ng>h\ni<j\n", result.stdout)

    def test_pipeline_and_sequence_precedence(self):
        result = self.run_shell(
            "printf 'a\\nb\\n' | grep b ; printf tail"
        )
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual("b\ntail", result.stdout)

    def test_pipeline_is_launched_concurrently(self):
        result = self.run_shell("seq 1 20000 | wc -l")
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual("20000", result.stdout.strip())

    def test_pipeline_status_comes_from_last_process(self):
        result = self.run_shell("definitely_missing_minish_command | true")
        self.assertEqual(0, result.returncode)
        self.assertIn("definitely_missing_minish_command", result.stderr)

        result = self.run_shell("true | definitely_missing_minish_command")
        self.assertEqual(127, result.returncode)

    def test_redirection_create_append_and_input(self):
        with tempfile.TemporaryDirectory() as directory:
            result = self.run_shell(
                "printf first > 'data file' ; "
                "printf second >> 'data file' ; cat < 'data file'",
                cwd=directory,
            )
            self.assertEqual(0, result.returncode, result.stderr)
            self.assertEqual("firstsecond", result.stdout)
            with open(os.path.join(directory, "data file"), "r") as stream:
                self.assertEqual("firstsecond", stream.read())

    def test_redirections_are_applied_left_to_right(self):
        with tempfile.TemporaryDirectory() as directory:
            result = self.run_shell(
                "printf payload > first > second", cwd=directory
            )
            self.assertEqual(0, result.returncode, result.stderr)
            with open(os.path.join(directory, "first"), "r") as stream:
                self.assertEqual("", stream.read())
            with open(os.path.join(directory, "second"), "r") as stream:
                self.assertEqual("payload", stream.read())

    def test_command_redirection_overrides_pipe_endpoint(self):
        with tempfile.TemporaryDirectory() as directory:
            result = self.run_shell(
                "printf pipe | printf file > result ; cat result", cwd=directory
            )
            self.assertEqual(0, result.returncode, result.stderr)
            self.assertEqual("file", result.stdout)

    def test_builtin_redirection_is_restored(self):
        with tempfile.TemporaryDirectory() as directory:
            result = self.run_shell(
                "pwd > where ; printf marker ; cat where", cwd=directory
            )
            self.assertEqual(0, result.returncode, result.stderr)
            self.assertEqual("marker{}\n".format(directory), result.stdout)

    def test_redirection_failure_does_not_poison_later_output(self):
        with tempfile.TemporaryDirectory() as directory:
            result = self.run_shell(
                "pwd > absent/output ; printf ok", cwd=directory
            )
            self.assertEqual(0, result.returncode)
            self.assertEqual("ok", result.stdout)
            self.assertIn("absent/output", result.stderr)

    def test_failed_redirection_prevents_parent_builtin_state_change(self):
        with tempfile.TemporaryDirectory() as directory:
            os.mkdir(os.path.join(directory, "sub"))
            result = self.run_shell(
                "cd sub > absent/output ; pwd", cwd=directory
            )
            self.assertEqual(0, result.returncode)
            self.assertEqual(directory + "\n", result.stdout)
            self.assertIn("absent/output", result.stderr)

    def test_cd_persists_and_uses_home(self):
        with tempfile.TemporaryDirectory() as directory:
            subdirectory = os.path.join(directory, "sub")
            home = os.path.join(directory, "home")
            os.mkdir(subdirectory)
            os.mkdir(home)
            result = self.run_shell(
                "pwd ; cd sub ; pwd ; cd ; pwd",
                cwd=directory,
                env_updates={"HOME": home},
            )
            self.assertEqual(0, result.returncode, result.stderr)
            self.assertEqual(
                "{}\n{}\n{}\n".format(directory, subdirectory, home),
                result.stdout,
            )

    def test_builtin_in_pipeline_cannot_change_parent(self):
        with tempfile.TemporaryDirectory() as directory:
            os.mkdir(os.path.join(directory, "sub"))
            result = self.run_shell("cd sub | cat ; pwd", cwd=directory)
            self.assertEqual(0, result.returncode, result.stderr)
            self.assertEqual(directory + "\n", result.stdout)

    def test_exit_status_and_short_circuit_of_remaining_list(self):
        result = self.run_shell("printf before ; exit 23 ; printf after")
        self.assertEqual(23, result.returncode)
        self.assertEqual("before", result.stdout)
        self.assertEqual("", result.stderr)

    def test_exit_status_is_reduced_modulo_256(self):
        self.assertEqual(231, self.run_shell("exit 999").returncode)
        self.assertEqual(255, self.run_shell("exit -1").returncode)
        self.assertEqual(
            1,
            self.run_shell("exit +1000000000000000000000000000000001").returncode,
        )

    def test_invalid_exit_does_not_terminate_the_command_list(self):
        result = self.run_shell("exit nope ; printf alive")
        self.assertEqual(0, result.returncode)
        self.assertEqual("alive", result.stdout)
        self.assertIn("decimal integer", result.stderr)

    def test_exit_without_operand_uses_last_foreground_status(self):
        result = self.run_shell("false ; sleep 30 & exit")
        self.assertEqual(1, result.returncode, result.stderr)

    def test_natural_end_uses_current_list_status_not_foreground_memory(self):
        result = self.run_shell("false ; true &")
        self.assertEqual(0, result.returncode, result.stderr)

    def test_syntax_status_and_later_operand_free_exit_are_distinct(self):
        result = self.run_shell(input_data="false\nprintf 'open\n")
        self.assertEqual(2, result.returncode)
        self.assertIn("syntax error", result.stderr)

        result = self.run_shell(input_data="false\nprintf 'open\nexit\n")
        self.assertEqual(1, result.returncode)
        self.assertIn("syntax error", result.stderr)

    def test_nul_byte_rejects_the_entire_input_line(self):
        result = self.run_shell(input_data="printf BAD\x00ignored\n")
        self.assertEqual(2, result.returncode)
        self.assertEqual("", result.stdout)
        self.assertIn("NUL byte", result.stderr)

    def test_command_not_found_has_status_127(self):
        result = self.run_shell("definitely_missing_minish_command")
        self.assertEqual(127, result.returncode)
        self.assertEqual("", result.stdout)
        self.assertIn("definitely_missing_minish_command", result.stderr)

    def test_empty_command_name_is_not_mistaken_for_a_path_directory(self):
        result = self.run_shell("''")
        self.assertEqual(127, result.returncode)
        self.assertEqual("", result.stdout)

    def test_existing_script_with_missing_interpreter_has_status_126(self):
        with tempfile.TemporaryDirectory() as directory:
            program = os.path.join(directory, "missing-interpreter")
            with open(program, "w") as stream:
                stream.write("#!/definitely/not/a/real/interpreter\n")
            os.chmod(program, 0o700)
            result = self.run_shell("./missing-interpreter", cwd=directory)
            self.assertEqual(126, result.returncode)
            self.assertEqual("", result.stdout)
            self.assertIn("missing-interpreter", result.stderr)

    def test_execvp_text_file_fallback_is_external_program_behavior(self):
        with tempfile.TemporaryDirectory() as directory:
            program = os.path.join(directory, "plain-text-program")
            with open(program, "w") as stream:
                stream.write("printf fallback")
            os.chmod(program, 0o700)
            result = self.run_shell("./plain-text-program", cwd=directory)
            self.assertEqual(0, result.returncode, result.stderr)
            self.assertEqual("fallback", result.stdout)

    def test_not_a_directory_exec_failure_maps_to_not_found(self):
        with tempfile.TemporaryDirectory() as directory:
            with open(os.path.join(directory, "ordinary-file"), "w") as stream:
                stream.write("not a directory")
            result = self.run_shell("./ordinary-file/child", cwd=directory)
            self.assertEqual(127, result.returncode)

    def test_syntax_error_prevents_whole_line_from_running(self):
        result = self.run_shell("printf SHOULD_NOT_RUN ; | cat")
        self.assertEqual(2, result.returncode)
        self.assertEqual("", result.stdout)
        self.assertIn("syntax error", result.stderr)

    def test_lexical_and_redirection_errors(self):
        for command in ["printf 'unterminated", "printf trailing\\", "cat >"]:
            result = self.run_shell(command)
            self.assertEqual(2, result.returncode, command)
            self.assertEqual("", result.stdout, command)
            self.assertIn("syntax error", result.stderr, command)

    def test_batch_newline_does_not_satisfy_a_trailing_escape(self):
        result = self.run_shell(input_data="printf x\\\n")
        self.assertEqual(2, result.returncode)
        self.assertEqual("", result.stdout)
        self.assertIn("syntax error", result.stderr)

    def test_stdin_mode_has_no_prompt_and_reads_each_line(self):
        result = self.run_shell(input_data="printf one\nprintf two\n")
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual("onetwo", result.stdout)
        self.assertNotIn("minish$", result.stdout)

    def test_c_command_can_read_its_standard_input(self):
        result = self.run_shell("cat", input_data="child input\n")
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual("child input\n", result.stdout)

    def test_batch_background_job_gets_dev_null_by_default(self):
        command = (
            "sh -c 'if IFS= read -r line; then printf BAD; else printf EOF; fi' "
            "& fg %1"
        )
        result = self.run_shell(command, input_data="must not be consumed\n")
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual("EOF", result.stdout)

    def test_background_input_redirection_overrides_dev_null(self):
        with tempfile.TemporaryDirectory() as directory:
            with open(os.path.join(directory, "source"), "w") as stream:
                stream.write("redirected\n")
            result = self.run_shell("cat < source & fg %1", cwd=directory)
            self.assertEqual(0, result.returncode, result.stderr)
            self.assertEqual("redirected\n", result.stdout)

    def test_c_option_treats_newline_as_command_separator(self):
        result = self.run_shell("printf one\nprintf two")
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual("onetwo", result.stdout)

    def test_c_option_stops_later_physical_lines_after_exit(self):
        result = self.run_shell("printf before\nexit 9\nprintf after")
        self.assertEqual(9, result.returncode)
        self.assertEqual("before", result.stdout)

    def test_jobs_and_fg_have_stable_noninteractive_output(self):
        result = self.run_shell("sleep 0.25 & jobs ; fg %1 ; jobs ; printf done")
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual("[1] Running sleep 0.25\ndone", result.stdout)
        self.assertEqual("", result.stderr)

    def test_jobs_preserves_internal_source_spacing_but_trims_edges(self):
        result = self.run_shell("  sleep   0.20   & jobs ; fg %1")
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual("[1] Running sleep   0.20\n", result.stdout)

    def test_done_job_is_reaped_and_not_listed(self):
        result = self.run_shell("true & sleep 0.05 ; jobs ; jobs")
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual("", result.stdout)

    def test_job_operand_requires_percent_prefix(self):
        result = self.run_shell("sleep 0.20 & fg 1 ; fg %1")
        self.assertEqual(0, result.returncode)
        self.assertIn("invalid job", result.stderr)

    def test_job_operand_rejects_a_signed_identifier(self):
        result = self.run_shell("sleep 0.20 & fg %+1 ; fg %1")
        self.assertEqual(0, result.returncode)
        self.assertIn("invalid job: %+1", result.stderr)

    def test_bg_rejects_a_job_that_is_already_running(self):
        result = self.run_shell("sleep 0.20 & bg %1 ; fg %1")
        self.assertEqual(0, result.returncode)
        self.assertIn("job is not stopped", result.stderr)

    def test_stopped_job_can_be_resumed_with_bg_then_fg(self):
        job_text = "true | sh -c 'kill -STOP $$; sleep 0.20'"
        result = self.run_shell(
            job_text + " & fg %1 ; jobs ; bg %1 ; fg %1 ; printf done"
        )
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual(
            "[1] Stopped {}\n[1] {}\ndone".format(job_text, job_text),
            result.stdout,
        )

    def test_stopped_foreground_command_sets_signal_status(self):
        result = self.run_shell("sh -c 'kill -STOP $$' ; exit")
        self.assertEqual(128 + signal.SIGSTOP, result.returncode)

    def test_stopped_pipeline_uses_rightmost_stopped_member_status(self):
        result = self.run_shell("sh -c 'kill -STOP $$' | true")
        self.assertEqual(128 + signal.SIGSTOP, result.returncode, result.stderr)

    def test_external_pipeline_has_its_own_process_group(self):
        command = "sh -c 'test \"$$\" -eq \"$(ps -o pgid= -p $$)\"'"
        result = self.run_shell(command)
        self.assertEqual(0, result.returncode, result.stderr)

    def test_terminal_interrupt_reaches_foreground_job_and_prompt_recovers(self):
        pid, master = pty.fork()
        if pid == 0:
            environment = os.environ.copy()
            environment["LC_ALL"] = "C"
            os.execve(str(BINARY), [str(BINARY)], environment)

        reaped = False
        try:
            transcript = self.read_until(master, b"minish$ ", 2.0)
            attributes = termios.tcgetattr(master)
            attributes[3] &= ~termios.ECHO
            termios.tcsetattr(master, termios.TCSANOW, attributes)
            os.write(
                master,
                b"python3 -c 'import os,signal,time; [time.sleep(.001) for _ in "
                b"iter(lambda: os.tcgetpgrp(0) != os.getpgrp(), False)]; "
                b"signal.signal(signal.SIGINT,lambda s,f: os._exit(130)); "
                b"os.write(1,b\"READY\"); signal.pause()'\n",
            )
            transcript += self.read_until(master, b"READY", 2.0)
            self.assertNotEqual(pid, os.tcgetpgrp(master))
            interrupted_at = time.monotonic()
            os.write(master, b"\x03")
            transcript += self.read_until(master, b"minish$ ", 2.0)
            self.assertLess(time.monotonic() - interrupted_at, 1.0)
            os.write(master, b"exit 0\n")
            status = self.wait_for_child(pid, 2.0)
            reaped = True
            self.assertTrue(os.WIFEXITED(status), transcript)
            self.assertEqual(0, os.WEXITSTATUS(status), transcript)
        finally:
            if not reaped:
                try:
                    os.write(master, b"\x03exit 0\n")
                except OSError:
                    pass
                try:
                    signal_session(pid, signal.SIGKILL)
                except OSError:
                    pass
                try:
                    os.waitpid(pid, 0)
                except ChildProcessError:
                    pass
            os.close(master)

    def test_terminal_handoff_does_not_require_terminal_stdout(self):
        output_read, output_write = os.pipe()
        pid, master = pty.fork()
        if pid == 0:
            os.close(output_read)
            os.dup2(output_write, 1)
            os.close(output_write)
            environment = os.environ.copy()
            environment["LC_ALL"] = "C"
            os.execve(str(BINARY), [str(BINARY)], environment)

        os.close(output_write)
        reaped = False
        try:
            os.write(
                master,
                b"sleep 0.05 &\n"
                b"python3 -c 'import os,time; [time.sleep(.001) for _ in "
                b"iter(lambda: os.tcgetpgrp(0) != os.getpgrp(), False)]; "
                b"value=os.read(0,100).strip(); "
                b"os.write(1,b\"GOT:\"+value+b\"\\n\")'\n"
                b"payload\nexit 0\n",
            )
            output = b""
            deadline = time.monotonic() + 3.0
            while time.monotonic() < deadline:
                readable, unused_writable, unused_exceptional = select.select(
                    [output_read], [], [], deadline - time.monotonic()
                )
                if not readable:
                    continue
                chunk = os.read(output_read, 4096)
                if not chunk:
                    break
                output += chunk
            status = self.wait_for_child(pid, 2.0)
            reaped = True
            self.assertTrue(os.WIFEXITED(status), output)
            self.assertEqual(0, os.WEXITSTATUS(status), output)
            self.assertEqual(b"GOT:payload\n", output)
        finally:
            os.close(output_read)
            if not reaped:
                try:
                    os.write(master, b"\x03exit 0\n")
                except OSError:
                    pass
                try:
                    signal_session(pid, signal.SIGKILL)
                except OSError:
                    pass
                try:
                    os.waitpid(pid, 0)
                except ChildProcessError:
                    pass
            os.close(master)

    def test_immediate_foreground_reader_cannot_race_terminal_handoff(self):
        output_read, output_write = os.pipe()
        pid, master = pty.fork()
        if pid == 0:
            os.close(output_read)
            os.dup2(output_write, 1)
            os.close(output_write)
            environment = os.environ.copy()
            environment["LC_ALL"] = "C"
            os.execve(str(BINARY), [str(BINARY)], environment)

        os.close(output_write)
        reaped = False
        try:
            os.write(
                master,
                b"python3 -c 'import os; value=os.read(0,8); "
                b"os.write(1,b\"GOT:\"+value)'\n"
                b"payload\n"
                b"exit 0\n",
            )
            status = self.wait_for_child(pid, 3.0)
            reaped = True
            output = b""
            while True:
                chunk = os.read(output_read, 4096)
                if not chunk:
                    break
                output += chunk
            self.assertTrue(os.WIFEXITED(status), output)
            self.assertEqual(0, os.WEXITSTATUS(status), output)
            self.assertEqual(b"GOT:payload\n", output)
        finally:
            os.close(output_read)
            if not reaped:
                try:
                    os.write(master, b"\x03exit 0\n")
                except OSError:
                    pass
                try:
                    signal_session(pid, signal.SIGKILL)
                except OSError:
                    pass
                try:
                    os.waitpid(pid, 0)
                except ChildProcessError:
                    pass
            os.close(master)

    def test_c_mode_on_a_terminal_emits_no_interactive_job_notice(self):
        pid, master = pty.fork()
        if pid == 0:
            environment = os.environ.copy()
            environment["LC_ALL"] = "C"
            os.execve(
                str(BINARY),
                [str(BINARY), "-c", "sleep 30 &"],
                environment,
            )

        reaped = False
        try:
            status = self.wait_for_child(pid, 2.0)
            reaped = True
            transcript = b""
            while True:
                readable, unused_writable, unused_exceptional = select.select(
                    [master], [], [], 0
                )
                if not readable:
                    break
                try:
                    chunk = os.read(master, 4096)
                except OSError:
                    break
                if not chunk:
                    break
                transcript += chunk
            self.assertTrue(os.WIFEXITED(status), transcript)
            self.assertEqual(0, os.WEXITSTATUS(status), transcript)
            self.assertEqual(b"", transcript)
        finally:
            if not reaped:
                try:
                    signal_session(pid, signal.SIGKILL)
                except OSError:
                    pass
                try:
                    os.waitpid(pid, 0)
                except ChildProcessError:
                    pass
            os.close(master)

    def test_background_children_are_cleaned_up_at_eof(self):
        started = time.monotonic()
        result = self.run_shell("sleep 30 &", timeout=2)
        elapsed = time.monotonic() - started
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertLess(elapsed, 1.5)


if __name__ == "__main__":
    unittest.main(verbosity=2)
