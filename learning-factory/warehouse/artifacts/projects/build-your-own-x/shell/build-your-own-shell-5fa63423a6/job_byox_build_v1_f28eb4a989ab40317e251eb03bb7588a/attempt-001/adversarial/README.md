# Adversarial test plan

This is a set of hostile boundary scenarios, not a record of executed tests.
No outcome or validation label is claimed here. Run cases in a fresh temporary
directory with a wall-clock deadline and process-group cleanup so a shell bug
cannot wedge the test runner or leave children behind.

## Harness rules

- Invoke batch cases as an argv array such as `./byosh -c "$case"`; do not ask a
  host shell to reinterpret the case under test.
- Capture stdout, stderr, and the numeric exit status separately.
- For interactive cases, allocate a pseudo-terminal and make the shell the
  session leader with that terminal as its controlling terminal.
- On timeout, terminate and reap the complete test process group, not only the
  shell leader.
- Give each case a new working directory and known environment. Use only
  disposable paths inside that directory.
- Assert both positive output and negative side effects (files not created,
  shell descriptors restored, and no unreaped descendants).

## Lexing and parsing attacks

| Input shape | Required oracle |
| --- | --- |
| `printf '<%s>\n' '' ""` | Two present empty arguments survive; neither is dropped. |
| `printf '%s\n' ab" cd"'ef'` | Adjacent fragments become one argument containing the space. |
| `printf '%s\n' a\|b "c>d"` | Protected operator bytes remain data. |
| `printf x|cat>/dev/null` | Operators tokenize without surrounding whitespace. |
| unclosed single/double quote | Parse failure, no child launch. |
| final unpaired backslash | Parse failure, no child launch. |
| leading, adjacent, or trailing `|` | Parse failure, no prefix execution. |
| `&` followed by another token | Parse failure rather than partial background execution. |
| redirection with no WORD operand | Parse failure and no file side effect. |
| two `<` or two output redirects | Parse failure; no redirect target is created/truncated. |

For the fixed-capacity learner scaffold, generate boundary cases from the
constants in `starter/include/byosh.h`: exact limit minus one, exact limit, and
limit plus one for argv and command count. Over-limit inputs must fail
deterministically without truncating a word into a different executable or
launching a valid prefix. For a growable implementation, impose harness safety
ceilings and fault-inject allocation failure rather than assuming a constant.

## Redirection and descriptor attacks

- Combine one input and one output redirect on every pipeline position.
- Verify explicit redirection overrides that stage's implicit pipe endpoint.
- Try an unreadable input, a nonexistent parent directory, a directory as an
  output path, and a descriptor-limit failure. The command must not run after
  its setup fails.
- Run a parent builtin with successful redirection, then print another value;
  the later value must use the original shell stdout.
- Repeat with an input redirect installed before an output open fails; all shell
  descriptors must still be restored.
- Feed enough data to exceed pipe capacity through two and many stages. This
  exposes sequential waiting and retained write endpoints.
- Pipe a long producer into a consumer that exits immediately. The shell must
  handle the resulting broken pipe without dying or waiting forever.
- Inspect child descriptors when the platform permits it and assert that
  unrelated pipe, saved, and harness descriptors do not survive `exec`.

## Process and status attacks

- Make the first stage exit immediately while the last stage sleeps, then swap
  those roles. Completion must account for every pipeline member.
- Exercise exits 0, 1, 126/127 paths promised by the implementation, and signal
  termination. Assert decoded command status rather than raw wait bits.
- Rapidly launch immediate-exit background jobs. Every child must become
  attributable and reapable even if it exits before the parent next reads
  input.
- Run enough waves to encourage PID reuse; never let a status for a new process
  complete an old job-table entry.
- Inject failure after some, but not all, pipes/children have been created.
  Assert bounded cleanup, terminal recovery, and no healthy partial job entry.
- Interrupt blocking waits and input operations repeatedly. `EINTR` must not be
  mistaken for EOF or successful completion.

## Interactive terminal attacks

These require a pseudo-terminal; a pipe is not a substitute.

1. Start a foreground multi-stage pipeline, send the terminal's interrupt
   character, and require the whole foreground group—not the shell—to react.
2. Send the suspend character, require one stopped job, run `bg`, then `fg`, and
   verify terminal ownership at each transition.
3. Start a background process that reads the terminal. Observe and record the
   platform's `SIGTTIN` stop behavior without allowing it to steal input.
4. Stop or terminate a job during the narrow handoff window and require the
   shell to regain the terminal and print/read normally.
5. Send EOF on an empty prompt and while partial input exists, according to the
   documented line-input policy.
6. Resize the pseudo-terminal and deliver unrelated signals while jobs change
   state; notifications must not corrupt a command line or table entry.

## Metamorphic properties

Useful oracles do not require a second shell implementation:

- adding unquoted whitespace between tokens does not change argv or operators;
- quoting an ordinary non-operator byte does not change that byte's argv value;
- inserting a `cat` stage preserves a finite byte stream and termination;
- redirecting a command's stdout to a file preserves its bytes while removing
  them from captured stdout;
- changing only foreground to background changes waiting/notification behavior,
  not the command's parsed argv;
- a rejected suffix prevents all effects of an otherwise valid prefix.

Record seeds, exact argv/environment, deadlines, and cleanup observations for
any failure. Timing alone is not a correctness oracle; the harness must identify
the unfinished process or state transition.
