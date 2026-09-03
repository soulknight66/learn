# Alternative designs

These are design alternatives, not additional claimed-complete solutions.

## `posix_spawn`

`posix_spawn_file_actions_adddup2` and close actions can express a pipeline
stage without running general child-side code after `fork`, which is useful in
multithreaded programs. Portable process-group and controlling-terminal
handoff is less direct, and parent-run built-ins still need a separate path.

## Rolling pipes

The parent can retain only the previous read endpoint while creating the next
pipe. Peak descriptor use becomes constant. Error rollback and the proof that
each forked child inherited only intended descriptors become more subtle.

## Event-loop reaping

A minimal signal handler can write one byte to a nonblocking self-pipe. The
main loop polls terminal input and that pipe, then drains `waitpid` in ordinary
code. Notifications become prompt, at the cost of a more complex input loop
and overflow/coalescing policy.

## AST-based grammar

If sequencing, conditional lists, subshells, or here-documents are added, an
AST with precedence-aware parsing is preferable to the current flat pipeline.
That change should happen before adding expansions, because expansion timing
depends on syntactic context.
