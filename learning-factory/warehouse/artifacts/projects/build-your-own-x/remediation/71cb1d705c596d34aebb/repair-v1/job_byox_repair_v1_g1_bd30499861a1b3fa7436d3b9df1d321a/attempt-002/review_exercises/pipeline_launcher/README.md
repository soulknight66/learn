# Review: pipeline launcher

`buggy.c` is a reduced two-or-more-stage pipeline executor. Its demo should
count one mebibyte of zero bytes, but commonly hangs because the data exceeds a
pipe's capacity.

From this exercise directory:

```sh
cc -std=c11 -Wall -Wextra -Wpedantic -O0 -g buggy.c -o buggy
timeout 2 ./buggy
```

Review `launch_pipeline` even if your particular host produces a different
symptom. Find at least six independent issues, including:

- one concurrency or ordering issue;
- two descriptor-lifetime issues on distinct paths;
- one child failure-path issue;
- one wait-status issue;
- one partial-launch cleanup issue.

For each, describe an input or injected syscall failure that exposes it. Sketch
the phases of a corrected launcher, but do not replace the exercise with a call
to another shell.
