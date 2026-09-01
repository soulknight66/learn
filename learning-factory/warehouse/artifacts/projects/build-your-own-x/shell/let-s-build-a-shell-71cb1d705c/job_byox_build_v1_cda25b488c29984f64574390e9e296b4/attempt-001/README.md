# Build `minish`: a small job-controlling shell in C

This repository is a staged systems-programming challenge. You will turn the
compiling scaffold in `starter/` into a shell that tokenizes a command language,
constructs pipelines, launches processes, redirects file descriptors, and
manages foreground and background jobs. The finished program is intentionally
small, but it must treat process state and terminal ownership precisely.

The catalog link recorded in `PROVENANCE.json` supplies only the topic. This is
an independently authored challenge; it does not reproduce the linked tutorial.

## What you can use

- `REQUIREMENTS.md` is the observable contract.
- `CONCEPTS.md` gives non-solution-oriented background.
- `DESIGN_QUESTIONS.md` asks the questions your design should answer.
- `starter/` is an incomplete but buildable C scaffold.
- `public_tests/` checks the stable CLI and starter-facing contracts.
- `environment/` records tool and platform expectations.

Instructor/reference material is deliberately outside the learner view. Do not
search for or depend on it; independent validation may exercise cases not shown
by the public suite.

## Suggested reveal order

1. **Tokens:** recognize words, quoting, escaping, and operators without
   launching a process.
2. **Syntax:** reject malformed input and represent commands, redirections,
   pipelines, lists, and background markers with owned memory.
3. **A process:** execute one external command and return its status.
4. **File descriptors:** implement `<`, `>`, and `>>`, then connect arbitrary
   pipeline lengths while closing every unused descriptor.
5. **Shell state:** implement `cd`, `pwd`, and `exit` in the process that owns
   shell state; define their behavior in pipelines.
6. **Jobs:** put each pipeline in a process group, reap without zombies, expose
   `jobs`, `fg`, and `bg`, and preserve stopped-job state.
7. **A terminal:** in interactive mode, transfer terminal foreground ownership
   and make Ctrl-C/Ctrl-Z affect the foreground job rather than the shell.
8. **Hardening:** handle interrupted system calls, allocation failures, syntax
   errors, cleanup, and adversarial descriptor/process cases.

Do not jump straight to terminal job control. Each earlier stage establishes an
invariant that the next one relies on.

## First commands

```sh
make -C starter clean all
python3 -m unittest discover -s public_tests -v
./starter/minish --help
```

The initial executable only implements its stable command-line envelope and
empty-input behavior. Passing those tests does **not** mean the shell is
complete. Replace TODOs incrementally and add your own tests alongside each
stage. See `environment/README.md` if the build fails for platform reasons.

## Completion standard

A credible submission builds without warnings under the documented flags,
passes public and independent behavioral tests, leaves no zombies or leaked
descriptors during repeated pipelines, and reports errors without crashing.
Interactive claims require pseudo-terminal evidence; ordinary redirected stdin
is not evidence that terminal job control works.

This generated artifact remains `PARTIAL`: its local observations are recorded
in `VALIDATION.md`, while independent validators alone decide stronger labels.
