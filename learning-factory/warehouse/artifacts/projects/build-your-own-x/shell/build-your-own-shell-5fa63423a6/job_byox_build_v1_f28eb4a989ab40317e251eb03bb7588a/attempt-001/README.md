# Build Your Own Shell in C

Build a small Unix shell that turns text into running process pipelines. The project starts with a
compilable scaffold and grows through parsing, process creation, pipes, redirections, and interactive
job control. The goal is not to imitate every feature of an established shell. It is to understand the
OS interfaces behind a deliberately small, testable language.

Your finished program is named `byosh` and supports these entry points:

```text
./byosh
./byosh -c COMMAND
```

Without `-c`, it reads commands from standard input. When standard input is a terminal, it also
provides the interactive behavior described in [REQUIREMENTS.md](REQUIREMENTS.md).

> This is an educational shell, not a security boundary or a production command interpreter. Work in
> a disposable directory, avoid privileged accounts, and use harmless commands while testing.

## Start here

Read only as far ahead as you need:

1. Read the overview on this page, then build the scaffold using
   [starter/README.md](starter/README.md).
2. For each milestone, reveal the matching section of
   [REQUIREMENTS.md](REQUIREMENTS.md). Write a focused test before moving on.
3. Use [CONCEPTS.md](CONCEPTS.md) as a reference when an OS behavior is unfamiliar. It explains the
   mental models, not an implementation recipe.
4. At the end of a milestone, answer the corresponding questions in
   [DESIGN_QUESTIONS.md](DESIGN_QUESTIONS.md). If an answer is unclear, the milestone is probably not
   complete yet.

The initial scaffold check is:

```sh
cd starter
make
make check
```

Once command execution is implemented in Milestone 2, add these smoke checks:

```sh
./byosh -c 'pwd'
printf 'pwd\nexit\n' | ./byosh
```

Exact test commands supplied with the repository are described by the starter and test READMEs.

## Milestones

### 0. Establish the loop

Build with strict warnings, accept `-c` and standard-input modes, read complete input lines, and
handle blank input and end-of-file. Keep input, parsing, execution, and cleanup separate even before
all four stages do useful work.

Checkpoint: repeated blank lines and an immediate end-of-file terminate cleanly without a busy loop.

### 1. Parse words into commands

Recognize words, quotes, escapes, and the operators in the project grammar. Produce a structured
representation rather than executing while tokenizing. Reject malformed input without leaving state
behind.

Checkpoint: a parser-focused test can inspect multiple commands and redirections without launching a
process.

### 2. Run one command

Implement the stateful built-ins and launch external programs found through `PATH`. Propagate useful
exit status and diagnostics. Make a clear distinction between shell state and child-process state.

Checkpoint: a failed command does not terminate the shell, and a later valid command still runs.

### 3. Add redirections and pipelines

Connect file descriptors for `<`, `>`, `>>`, and `|`. Start every member of a pipeline before waiting
for the pipeline. Close every unused descriptor in every process.

Checkpoint: a pipeline that writes more than a pipe buffer completes, and a reader waiting for
end-of-file does not hang.

### 4. Add background work

Recognize a trailing `&`, return control without waiting for that pipeline to finish, reap completed
children, and expose useful job state through `jobs`.

Checkpoint: background jobs do not become zombies, including while the shell is otherwise idle.

### 5. Add interactive job control

In terminal mode, organize each pipeline as a process group, give foreground jobs temporary control
of the terminal, and implement `fg` and `bg`. Keep terminal-generated signals from accidentally
stopping or killing the shell itself.

Checkpoint: stop a foreground job, inspect it, resume it in the background, then bring it back to the
foreground. The shell must regain the terminal after every transition.

### 6. Harden and explain

Exercise syntax errors, failed system calls, unusual descriptor layouts, rapid child exits, long
pipelines, and repeated jobs. Run available memory and undefined-behavior checks. Document deliberate
limits instead of silently accepting ambiguous input.

Checkpoint: the complete public test suite and your own focused tests pass from a clean build.

## Scope boundaries

The required language is intentionally compact: one pipeline per input line, quoted or escaped words,
three file-redirection operators, and an optional trailing background marker. Variables, wildcard
expansion, command substitution, conditionals, and scripting constructs are extensions. Implement
them only after the required behavior is stable; an extension must not change the required grammar.

## What completion means

A plausible transcript is not enough. Keep reproducible evidence:

- the exact clean-build and test commands you ran;
- focused cases for parser errors, descriptor closure, and process-state changes;
- at least one non-interactive test and one pseudo-terminal test;
- a short record of unsupported behavior and known limitations.

The detailed contract is in [REQUIREMENTS.md](REQUIREMENTS.md). Environment assumptions and optional
diagnostic tools are listed in [environment/README.md](environment/README.md).
