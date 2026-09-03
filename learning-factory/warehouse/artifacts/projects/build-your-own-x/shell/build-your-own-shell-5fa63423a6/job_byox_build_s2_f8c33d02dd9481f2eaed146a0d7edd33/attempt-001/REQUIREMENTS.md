# Behavioral requirements

Implement the public interface in `starter/include/minish.h`. Input is one logical line of at most 4096 bytes, including its optional trailing newline. The implementation must never call `system`, `popen`, or `/bin/sh -c`.

## 1. Lexing

Split the line into `WORD`, `|`, `<`, `>`, `>>`, `&`, and terminal `END` tokens.

- Unquoted spaces, tabs, carriage returns, and newlines separate words.
- Single quotes preserve every enclosed byte literally except NUL, which cannot occur in the C string input.
- Double quotes remove the quotes. A backslash inside double quotes quotes the following byte.
- Outside quotes, backslash quotes the following byte.
- Adjacent quoted and unquoted fragments form one word; `ab"cd"''` is the word `abcd`.
- Empty quotes produce an empty `WORD`.
- Operators need not be surrounded by whitespace: `a|b>>out&` is valid tokenization.
- An unquoted `#` starts a comment only where a new word could begin. Inside or in the middle of a word it is literal.
- Unclosed quotes and a trailing backslash are lexical errors.
- On failure, return `-1`, produce a useful nonempty diagnostic when an error buffer is supplied, and leave the output safe to free.

## 2. Parsing

Parse this grammar, where redirections may appear anywhere within a command:

```text
pipeline := command ( "|" command )* ( "&" )? END
command  := ( WORD | "<" WORD | ">" WORD | ">>" WORD )+
```

Each command must contain at least one `WORD`. Preserve argument order. A command may have at most one input redirection and one output redirection. `>` means truncate and `>>` means append. `&` is allowed only once and only after the complete pipeline.

Reject empty commands, missing redirection targets, duplicate/conflicting redirections, misplaced `&`, unexpected tokens, and an empty/comment-only line. Parser output owns deep copies of all strings and remains safe to free after failure.

## 3. Execution

- Use `execvp` so ordinary `PATH` lookup applies.
- A pipeline of *N* commands uses *N − 1* pipes and *N* children.
- Apply a command's explicit input/output redirection after connecting its pipeline descriptors, so explicit redirection wins for that stream.
- Open input read-only. Open output with mode `0666`, subject to the process umask; truncate for `>` and append for `>>`.
- Put every child in one new process group whose ID is the first child's PID. Call `setpgid` in both parent and child to close the race.
- Reset `SIGINT`, `SIGQUIT`, `SIGTSTP`, `SIGTTIN`, and `SIGTTOU` to defaults in children before `execvp`.
- In interactive foreground mode, transfer the controlling terminal to the job before waiting and restore it to the shell afterward.
- Wait for every foreground child, retrying interrupted waits. Return the last pipeline command's exit status, or `128 + signal` if it died from a signal.
- For a background pipeline, print one stable launch notification containing its process-group ID, do not block, return zero after successful launch, and allow later nonblocking reaping.
- A failed setup or `execvp` in a child must diagnose to standard error and exit with `_exit(126)` or `_exit(127)` respectively.
- On partial launch failure, close descriptors, terminate/reap children already launched, and return nonzero.

## 4. Shell loop and built-ins

Read with `getline`. Show `minish$ ` only when standard input is a terminal. Continue after lexical, syntax, or command errors. End cleanly on EOF.

Implement these built-ins only for a single foreground command with no redirections:

- `cd [directory]`: change the shell process's working directory; use `HOME` when omitted; reject more than one argument.
- `exit [0..255]`: end the shell; with no operand, use the most recently completed command status; reject nonnumeric or extra operands without exiting.

Built-ins used in pipelines or background jobs may be rejected with a diagnostic. This pack does not require expansion, globbing, script files, semicolons, logical operators, or job-selection commands such as `fg`/`bg`.

## 5. Resource and quality constraints

- No invalid reads/writes/frees on any accepted or rejected line.
- No file-descriptor growth across 200 sequential foreground pipelines.
- No zombies after the reap function is called until it reports no more completions.
- Diagnostics go to standard error; command output remains unpolluted on standard output.
- Source must compile with the flags supplied by the starter Makefile.
