# Reference design

## Data and ownership

The lexer owns a growable `TokenList`. Operator tokens have null text; word tokens own `strdup` allocations, including an allocation for the empty word. Its failure path releases the partially built word and calls the same idempotent list destructor used on success.

The parser never steals token memory. It builds a local `Command`, deep-copies each argument and path, then moves the completed command into the pipeline array. Every error either frees the local command or the accumulated pipeline. Consequently the caller may always free tokens immediately after parsing and may call either destructor on a zeroed or already-freed object.

This answers the first four design questions with one invariant: an object owns all pointers reachable from it, and moving an object zeroes the source.

## Lexical state

The lexer tracks `word_started` separately from buffer length. That is the distinction needed for `''`: a word exists even though it has zero bytes. Single-quoted, double-quoted, escaped, and ordinary fragments all append to the same buffer, so adjacent fragments concatenate without a second pass.

Operators flush the current word before producing an operator token. A comment begins only when no word is in progress. This makes `x#y` a word but `x #y` a word followed by a comment.

## Parsing

Parsing is a single forward pass over typed tokens. `parse_command` owns the policy for duplicate redirections because it has exactly the command-local context needed to distinguish legal redirections in different pipeline stages. The outer parser consumes `|`, optional final `&`, and the unique end marker.

Execution never sees malformed structure: each `Command` has a non-null, null-terminated argument vector with at least one element, and each stream has at most one explicit redirection.

## Descriptor topology

The executor creates only the next pipe while iterating. Immediately before a child applies explicit redirections, its inherited pipeline topology is:

```text
previous pipe read -> standard input (unless first stage)
standard output -> next pipe write (unless last stage)
all original pipe descriptors closed
```

Explicit file redirection is applied afterward, so it replaces the relevant pipeline connection. The parent closes the old read end and new write end immediately after each fork. If it retained a write reference while waiting, the downstream reader could never observe EOF.

## Processes, groups, and status

The first child's PID becomes the process-group ID. Each child calls `setpgid` before descriptor setup, and the parent repeats it to cover either side of the fork/exec scheduling race. Children restore interactive signals to default dispositions before `execvp`; the shell ignores those signals while supervising jobs.

For an interactive foreground pipeline, the parent gives the terminal to the job group, waits for every known PID, derives the returned status from the last pipeline stage, and restores the terminal to its own group. Waiting by recorded PID makes the last-stage identity independent of completion order.

A background launch returns after creation and is reaped by later nonblocking `waitpid` calls. A stopped foreground pipeline is noticed and the terminal is restored, but no `fg`/`bg` selection layer is provided. This is a deliberate educational boundary and one reason the pack remains `PARTIAL`.

## Failure containment

Every `pipe` and `fork` failure closes locally held descriptors. If some children have already launched, the parent signals the entire group and waits for recorded children. Child-side setup failures use `perror` followed by `_exit(126)`; lookup failure uses `_exit(127)`, avoiding copied stdio buffers and parent cleanup handlers.

Built-ins that mutate shell state are dispatched in the parent only for one foreground command with no redirection. Other placements are rejected, making the policy explicit instead of silently running a state-changing command in an ineffective child.
