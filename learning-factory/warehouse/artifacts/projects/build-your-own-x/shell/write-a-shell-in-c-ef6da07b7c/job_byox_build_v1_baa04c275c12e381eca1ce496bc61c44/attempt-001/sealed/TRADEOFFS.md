# Design tradeoffs

## Chosen: dynamic tokens and argument arrays

Dynamic storage accepts lines beyond an arbitrary classroom constant and makes empty arguments natural. It costs more allocation sites and therefore more cleanup paths. An arena could reduce allocation bookkeeping, but transferring individual word pointers keeps the supplied API conventional and easy to inspect.

## Chosen: create every pipe before forking

This makes descriptor topology and partial cleanup explicit. A rolling two-pipe implementation can keep descriptor usage constant for very deep pipelines, but is easier to get wrong and still must launch all children before waiting. The reference consequently reaches the process file-descriptor limit sooner for unusually deep pipelines; production hardening should consider rolling pipe ownership.

## Chosen: polling at command boundaries, without a SIGCHLD handler

Draining `waitpid` before each prompt and builtin is deterministic and avoids async-signal-safe communication. A background child that changes state while the interactive shell is blocked in `getline` is not reported until the next command boundary. A production interactive shell would use a self-pipe or signalfd-style event source and integrate it with input handling.

## Chosen: completed jobs remain visible until `wait`

This makes fast jobs observable in deterministic tests. It can grow memory without bound in a long session that launches background work but never calls `wait`. Real shells usually notify once and prune according to a documented lifecycle.

## Chosen: no `fg` or `bg`

The challenge still exercises stopped states, process groups, and terminal ownership, but deliberately omits a resume interface. This keeps the public grammar narrow. It also means an interactively stopped job can only be inspected or affected by an external signal; this is a major usability gap, explicitly outside the requirements.

## Chosen: direct `fork`/`execvp`

Those calls expose the concepts the learner is meant to practice. `posix_spawnp` can be preferable in large, multithreaded applications and can express common file actions, but it obscures parts of the fork-side descriptor and signal setup central to this exercise.

## Chosen: exact minimal grammar

Characters commonly special to mature shells are plain bytes here. This avoids pretending that ad-hoc parsing is safe for a full shell language. It also means `msh` must never be presented as a drop-in command interpreter for untrusted scripts.
