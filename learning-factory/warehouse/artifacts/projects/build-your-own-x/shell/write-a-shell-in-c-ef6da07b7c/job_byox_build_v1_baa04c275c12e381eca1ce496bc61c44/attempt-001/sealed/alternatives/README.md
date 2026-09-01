# Alternative designs

These are evaluator notes, not additional reference implementations.

## Arena-backed parser

Allocate one growable arena for decoded word bytes and one vector of spans. After grammar validation, materialize `argv` pointers into the stable arena. Cleanup becomes one arena free plus vector frees. The hard part is preserving pointer validity whenever the arena grows; offsets are safer than pointers until growth ends.

## Rolling pipeline descriptors

Keep only the previous read end and one newly created pipe while forking left to right. Each child still closes inherited endpoints and the parent still defers all waits. This changes peak descriptor use from proportional to pipeline length to constant, at the cost of a more stateful failure path.

## SIGCHLD self-pipe event loop

Install a minimal handler that writes one byte to a nonblocking close-on-exec pipe. The main loop waits on terminal input and the pipe together, then performs all `waitpid` calls in normal code. The handler must tolerate a full pipe, save/restore `errno`, and perform no allocation or formatted output.

## `posix_spawnp` executor

Precompute file actions for each stage, signal defaults, and process-group attributes, then spawn without running general-purpose child code after a multithreaded fork. Portability of terminal-group coordination and spawn attributes must be checked explicitly; failure cleanup and status accounting remain necessary.

## AST prepared for redirection

If redirection were later added, model it as ordered actions attached to a command rather than patching strings after tokenization. Ordering matters (`2>&1 >file` differs from `>file 2>&1`). That extension should be a new contract and test suite, not an undocumented interpretation of the current grammar.
