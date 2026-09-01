# Exercise 1: argv boundaries

`broken.sh` forwards a rootfs, command, and command arguments to an isolation
helper. Its author reports that spaces, wildcard characters, and empty
arguments change along the way.

Run:

```bash
bash debugging/01-argv-boundaries/test.sh
```

Repair `broken.sh` so every incoming element remains exactly one outgoing argv
element. Do not use `eval`, a shell command string, or escaping-by-rewriting.
The helper's exit status must still be the wrapper's exit status.

