# Behavioral contract

Keywords **MUST**, **SHOULD**, and **MAY** are normative. Public tests cover only a subset; sealed tests may exercise every numbered requirement.

## R1 — Build and invocation

- **R1.1:** `make -C starter clean all` MUST create the executable `starter/msh` using C11 and POSIX.1-2008 interfaces.
- **R1.2:** With no arguments, `msh` MUST read newline-delimited commands from standard input until EOF.
- **R1.3:** `msh -c STRING` MUST parse and execute exactly one command line and return its status.
- **R1.4:** Any other arguments MUST print a diagnostic to standard error and return status 2.
- **R1.5:** A prompt containing `msh$ ` MUST be printed only when standard input is a terminal. Batch output MUST contain no prompt.

## R2 — Grammar and parsing

The entire line MUST be parsed before any process is launched.

```text
line      := [ pipeline [ "&" ] ]
pipeline  := command { "|" command }
command   := word { word }
```

- **R2.1:** Unquoted spaces, tabs, and newlines separate words.
- **R2.2:** `|` and `&` are operators without requiring surrounding spaces.
- **R2.3:** Single quotes preserve every enclosed byte except the terminating single quote. Double quotes preserve enclosed bytes; a backslash inside double quotes quotes the next byte.
- **R2.4:** Outside quotes, a backslash quotes the next byte. Quote delimiters and quoting backslashes are not included in the resulting argument.
- **R2.5:** Empty quoted strings produce empty arguments. There is no variable expansion, globbing, or field splitting.
- **R2.6:** An unmatched quote, trailing backslash, empty pipeline segment, non-final `&`, or line containing only `&` is a syntax error.
- **R2.7:** A syntax error MUST launch nothing, write a diagnostic prefixed with `msh:` to standard error, set status 2, and allow a batch or interactive session to read the next line.
- **R2.8:** An empty or whitespace-only line is successful and launches nothing.

## R3 — external commands and pipelines

- **R3.1:** Resolve external commands with `execvp`, preserving the parsed argument vector exactly.
- **R3.2:** A command-not-found failure MUST return 127; another execution failure MUST return 126. The child MUST write an informative `msh:` diagnostic to standard error.
- **R3.3:** A pipeline MUST create all pipes and launch all commands before waiting. Standard output of command *i* connects to standard input of command *i + 1*.
- **R3.4:** Every process MUST close every pipe descriptor it does not use. The parent MUST close its copies once forking is complete. EOF must therefore be observable by readers.
- **R3.5:** The pipeline status is the normalized status of its last command: normal exit code, or `128 + signal_number` for a signal.
- **R3.6:** A partial setup failure MUST close descriptors and reap or terminate already-created children; it MUST NOT leave zombies.

## R4 — parent built-ins

Built-ins MUST run in the shell process and are valid only as a single foreground command. Using a built-in in a pipeline or with `&` is an error with status 2.

- **R4.1:** `cd [DIR]` changes the shell's directory. With no operand it uses `HOME`; more than one operand or a missing `HOME` is an error.
- **R4.2:** `exit [N]` requests shell exit. With no operand it uses the previous status. One decimal operand in the range 0–255 is accepted. Invalid input MUST diagnose and keep the shell running.
- **R4.3:** `jobs` takes no operands, first performs nonblocking child collection, then prints every retained background job as `[ID] STATE PGID COMMAND`. `STATE` is `Running`, `Stopped`, or `Done`.
- **R4.4:** `wait` takes no operands and waits for all running background jobs. It returns the normalized status of the last command in the highest-numbered completed retained job, or zero when no jobs remain. It MUST not busy-spin.

## R5 — process groups and interactive control

- **R5.1:** All children in one pipeline MUST share a process group whose ID is the first child's PID. Separate pipelines MUST use separate groups.
- **R5.2:** The shell MUST remain outside child process groups.
- **R5.3:** In interactive mode, the shell SHOULD own the controlling terminal while reading. It MUST give the terminal to a foreground pipeline and reclaim it after that pipeline exits or stops.
- **R5.4:** The interactive shell MUST ignore `SIGINT`, `SIGQUIT`, `SIGTSTP`, `SIGTTIN`, and `SIGTTOU`; children MUST restore their default dispositions before `execvp`.
- **R5.5:** Foreground waiting MUST target the foreground process group, not an arbitrary child. A stopped foreground group MUST be retained as a stopped job.

## R6 — job lifetime and robustness

- **R6.1:** A command followed by `&` starts without a foreground wait, is retained in a job table, and prints `[ID] PGID`.
- **R6.2:** The shell MUST periodically call `waitpid` with `WNOHANG`, `WUNTRACED`, and (where available) `WCONTINUED` so background state changes do not accumulate as zombies.
- **R6.3:** Job IDs are positive, monotonically increasing within a shell process, and are not reused.
- **R6.4:** All heap allocations and owned descriptors MUST be released on normal shutdown. System-call failures MUST be handled without undefined behavior.

## Explicit non-goals

Redirection, here-documents, semicolons, `&&`, `||`, wildcard expansion, variables, command substitution, aliases, shell functions, startup files, and a `fg`/`bg` interface are outside this contract. Bytes such as `<`, `>`, `$`, `*`, and `;` are ordinary word bytes for this grammar.
