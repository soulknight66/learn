# Build a tiny Forth in x86-64 assembly

This is a clean-room language implementation challenge inspired only by the catalog topic
“Jonesforth.” The goal is to build **Cinder**, a small batch-mode Forth, directly in GNU x86-64
assembly on Linux. No code or prose from the linked resource is included.

Your program reads one source stream from standard input, evaluates it, writes language output to
standard output, and reports deterministic diagnostics on standard error. It must tokenize source,
maintain a checked data stack, compile colon definitions into an internal instruction stream, patch
structured branches, and execute user words on a bounded return stack.

## Suggested progression

1. Assemble and link `starter/forth.S`, then make the empty program exit successfully.
2. Add tokenization, comments, and checked signed-decimal conversion.
3. Implement the data stack and primitive dictionary.
4. Add colon definitions and calls.
5. Compile `if` / `else` / `then` with a patch stack.
6. Add resource limits and deterministic errors, then run all public tests.

The complete observable contract is in `REQUIREMENTS.md`; `CONCEPTS.md` explains the underlying
ideas without giving an implementation. `DESIGN_QUESTIONS.md` is a checkpoint worksheet.

## Build and test

From the repository root:

```text
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 environment/build.py starter/forth.S -o starter/build/cinder
CINDER_BIN=starter/build/cinder /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -m unittest discover -s public_tests -v
```

The scaffold deliberately returns a not-implemented error, so public behavioral tests fail until
you implement it. The build-sanity test should pass immediately. Try a completed interpreter with:

```text
printf ': square dup * ; 12 square .\n' | starter/build/cinder
```

Expected language output is `144` followed by a newline.

## Scope and status

This artifact targets x86-64 Linux and the GNU assembler syntax accepted by the recorded toolchain.
It is a bounded educational interpreter, not a production Forth system. The manifest intentionally
remains `GENERATED` + `PARTIAL`; only an independent harness can award stronger validation labels.
