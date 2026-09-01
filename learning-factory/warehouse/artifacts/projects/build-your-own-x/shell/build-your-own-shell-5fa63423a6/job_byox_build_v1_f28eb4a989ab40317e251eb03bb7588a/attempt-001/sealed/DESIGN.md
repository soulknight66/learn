# Reference design

This is the sealed rationale for the reference implementation. It describes the
intended contracts, including the parts that are easy to miss when merely
making simple commands work.

## Scope

`byosh` implements one deliberately small shell language:

- words made from unquoted, single-quoted, double-quoted, and backslash-escaped
  text;
- pipelines separated by `|`;
- `<`, `>`, and `>>` redirections;
- a single optional trailing `&`;
- the builtins `cd`, `pwd`, `exit`, `jobs`, `fg`, and `bg`;
- interactive input, script input on standard input, and `-c COMMAND`.

It does not implement expansions, globbing, assignments, command substitution,
here-documents, logical operators, command lists, or shell functions. Keeping
those features out is an architectural boundary: adding expansion later should
be a distinct phase between parsing and execution, not an accidental side
effect of tokenization.

## Component boundaries

The implementation is split into five responsibilities:

1. `lexer.c` turns bytes into WORD and operator tokens. It removes syntactic
   quote and escape characters while preserving the resulting word, including
   an explicitly empty quoted word.
2. `parser.c` validates token order and fills the growable, owning command and
   pipeline structures declared by the sealed reference's `shell.h`.
3. `main.c` selects interactive, standard-input, or `-c` mode and coordinates
   execution.
4. `jobs.c` owns process-group lifecycle and the job table.
5. `builtins.c` implements builtin behavior without giving it ownership of the
   parser or job-launch loop.

No parsed reference object points into a line-reading scratch buffer. A complete
pipeline owns allocated bytes for its arguments, redirection paths, and source,
so it remains valid until execution and bookkeeping finish. Every growable-list
operation checks allocation before publishing a new element, and one destructor
accepts partially built pipelines. Allocation failure is a reported parse
error, never truncation or partial launch.

This differs intentionally from the learner scaffold's fixed-capacity public
API, whose documented pointers borrow its writable input line. Both are valid
ownership models as long as the relevant lifetime contract is preserved.

## Lexical contract

Operators are recognized even without surrounding whitespace, so `a|b>out` is
the same token sequence as `a | b > out`. Operators inside quotes or protected
by a backslash are ordinary word bytes.

The quoting rules are intentionally compact:

- inside either quote style, every byte except the matching closing quote is
  literal, including backslash;
- outside quotes, backslash protects the next byte;
- quote delimiters and protective backslashes do not appear in the resulting
  word;
- adjacent fragments concatenate into one word (`ab"cd"'ef'` becomes
  `abcdef`);
- `''` and `""` each produce a present argument whose value is the empty
  string;
- an unclosed quote or a final unpaired backslash is an error.

The lexer does not classify a word as a builtin and does not perform expansion.
That prevents quoted spelling and parser storage details from changing command
selection.

## Grammar and parser validation

In compact notation, the accepted shape is:

```text
pipeline := command ("|" command)* ["&"] end
command  := element+
element  := WORD | ("<" | ">" | ">>") WORD
```

A command must contain at least one WORD. Thus a leading pipe, adjacent pipes,
a trailing pipe, a redirection-only command, an operator without a following
WORD, and tokens after `&` are errors. Parsing completes before any pipe, file,
or process is created, so syntax errors have no execution side effects.

Each command may have at most one input redirection and at most one output
redirection. `>` and `>>` occupy the same output slot. A second redirection for
the same standard descriptor is a syntax error, so it is detected before any
file is opened or command is launched. One input and one output redirection may
appear together.

## Execution model

A parsed pipeline that launches children maps to one process group. A pipeline
with N child-context stages creates N children and N-1 pipes. Each child
performs only the setup needed for its stage:

1. join or create the pipeline's process group;
2. restore the normal signal dispositions inherited from an interactive shell;
3. connect the previous pipe to standard input and the next pipe to standard
   output;
4. apply the stage's explicit input/output redirections;
5. close every inherited pipe and temporary redirection descriptor;
6. run a child-context builtin or call `execvp`.

Applying explicit redirections after the implicit pipeline endpoints gives an
explicit file redirection on a stage the final say. Every process closes all
pipe descriptors it does not actively use. In particular, the parent closes
its copies promptly; otherwise a downstream reader cannot observe end of file.

The parent calls `setpgid` as well as each child. This apparent duplication is a
race-closing protocol: whichever side runs first establishes the same group,
and expected race outcomes are checked rather than treated as proof that job
setup succeeded.

If any pipe or fork fails partway through a launch, the parent closes all open
descriptors, terminates or reaps already-created children as appropriate, and
does not publish a healthy job-table entry for a pipeline that was never fully
started.

## Builtin contexts and redirection

A builtin in a single, foreground command runs in the shell process. That is
required for `cd`, `exit`, `fg`, and `bg` to affect the shell, and gives
consistent behavior for `pwd` and `jobs`. The same builtin in a pipeline or a
background command runs in a child context; its state changes disappear when
that child exits, just as external-command state changes do.

Parent-run builtin redirection is a transaction:

1. record whether each affected standard descriptor is open and, when it is,
   duplicate it to a descriptor above the standard range;
2. apply the parsed input/output redirections;
3. invoke the builtin;
4. flush buffered output;
5. restore every saved descriptor on all success and failure paths;
6. close saved descriptors and preserve the builtin's logical status.

The shell must not leave its own standard streams redirected after a builtin
error. Redirection setup failure prevents the builtin from running.

`exit` validates its argument before asking the main loop to terminate. `fg`
and `bg` resolve an existing job-table entry rather than guessing from a raw
PID. `fg` resumes a stopped group when needed, gives it the terminal, waits,
and always reclaims the terminal. `bg` resumes the entire group without a
terminal handoff.

## Interactive job control

Interactive mode is enabled only when the relevant descriptors are terminals.
The shell establishes its own process group, takes terminal ownership, and
ignores terminal-generated stop signals that would otherwise suspend the shell
while it manages a foreground job. Children reset those dispositions before
running user code.

Launching a job follows a signal-mask protocol:

1. block `SIGCHLD` in the shell;
2. create every child and establish the common process group; interactive
   foreground children wait on a private launch gate;
3. insert the complete job in the table while `SIGCHLD` is still blocked;
4. for a foreground job, transfer the terminal with `tcsetpgrp`;
5. release the launch gate only after successful terminal handoff;
6. restore the prior signal mask;
7. wait for foreground state changes, or return immediately for a background
   job;
8. reclaim the terminal for the shell on every foreground exit path.

Blocking closes the fast-child race in which a child exits before its table
entry exists. The child restores the inherited mask before running a builtin or
calling `execvp`.

The `SIGCHLD` handler performs no table traversal, allocation, formatted I/O,
or complex state transition. It preserves `errno`, sets a
`volatile sig_atomic_t` flag, and writes a byte to a nonblocking self-pipe.
Outside foreground waits, `SIGCHLD` remains blocked; `pselect` atomically
unblocks it while waiting for either input or the self-pipe. This closes the
lost-wakeup window without doing job-table work in the handler. Ordinary
control flow drains both the pipe and `waitpid` with `WNOHANG`, `WUNTRACED`,
and `WCONTINUED`, maps each PID back to its process group/job, and derives
aggregate job state.

A job is stopped when every noncompleted member is stopped, remains running if
any noncompleted member is running, and becomes done only after all of its
members have terminated. Completed jobs can be reported and then removed;
stopped jobs remain addressable by `jobs`, `fg`, and `bg`.

## Modes and diagnostics

Interactive mode may print prompts and asynchronous job notifications. `-c`
and non-interactive standard-input mode do not print prompts, which makes them
suitable for deterministic tests. End of file exits the main loop after
performing normal cleanup.

Diagnostics go to standard error and include enough context to distinguish a
syntax error, redirection failure, launch failure, builtin misuse, and command
lookup failure. User-controlled strings are data arguments to formatting
functions, never format strings. Child failures use `_exit` after fork so they
do not flush a copied parent `stdio` buffer.

## Core invariants

- Parsing is complete and successful before execution has side effects.
- Parsed argument and path storage is owned and NUL-terminated.
- Each child-launched pipeline has exactly one process group.
- A foreground pipeline, and only that pipeline, owns the terminal while it
  runs.
- The shell eventually closes every pipe endpoint and reaps every child.
- The job table changes only in normal control flow; `SIGCHLD` is masked across
  launch and membership publication.
- Parent-run builtin redirections are always restored.
- Batch behavior never depends on a prompt, controlling terminal, or timing
  accident.
