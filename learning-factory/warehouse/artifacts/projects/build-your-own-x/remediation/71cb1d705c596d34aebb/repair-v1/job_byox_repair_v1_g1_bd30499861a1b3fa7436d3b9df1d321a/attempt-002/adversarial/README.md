# Adversarial command corpus

This directory contains inputs that put pressure on parser boundaries, pipe
capacity, descriptor closure, built-in context, and asynchronous child bursts.
They are not an oracle and include no reference outputs. Use the requirements to
decide whether each observed stdout, stderr, and exit status is correct.

Run every case against a built learner shell:

```sh
make -C starter
python3 adversarial/run.py starter/minish
```

Run one case with a longer limit:

```sh
python3 adversarial/run.py --case 04-large-pipeline.minish \
  --timeout 8 starter/minish
```

The runner executes each input in a new temporary working directory, captures
stdout and stderr, and labels only whether the process completed, returned
nonzero, was signaled, or exceeded the deadline. `completed` does **not** mean
correct. Inspect the transcript and add explicit assertions in your own tests.

Cases may expose bugs by hanging. Each shell starts a disposable session; at a
deadline the runner uses `ps` to enumerate that session and signals every
process group, including correctly separated pipeline jobs. A command that
deliberately creates a new session can still escape this portable cleanup. Run
adversarial work in a disposable environment and check for leftover processes
after investigating a timeout.

## Corpus map

| Case | Pressure applied |
| --- | --- |
| `01-empty-and-joined-quotes` | empty arguments and joined word fragments |
| `02-quoted-operators` | operator bytes protected by quotes/escapes |
| `03-touching-operators` | precedence without helpful whitespace |
| `04-large-pipeline` | transfer larger than ordinary pipe capacity |
| `05-early-consumer-exit` | downstream exit and upstream `SIGPIPE` |
| `06-redirection-order` | repeated output redirection and input redirection |
| `07-builtin-context` | persistent versus pipeline-local directory changes |
| `08-syntax-recovery` | whole-line rejection followed by a valid line |
| `09-background-burst` | coalesced child-state notifications and `jobs` |
| `10-long-pipeline` | many stages and descriptor accounting |

The corpus intentionally avoids optional expansions and shell comments. Files
are raw `minish` input, not scripts for `/bin/sh`.
