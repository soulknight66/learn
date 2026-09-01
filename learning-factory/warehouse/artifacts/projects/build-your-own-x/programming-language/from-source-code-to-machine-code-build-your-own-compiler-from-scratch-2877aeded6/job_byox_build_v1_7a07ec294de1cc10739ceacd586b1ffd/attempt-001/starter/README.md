# Starter scaffold

`minnow/` contains public data structures, API wiring, and deliberate implementation gaps. Search for
`TODO` and implement in this order: lexer, parser, compiler, bytecode validation, VM. Keeping those
boundaries makes failures easier to localize, but you may refactor internals while preserving the API.

The CLI is already wired to the API. Its atomic file replacement helper is part of the scaffold so the
challenge can focus on language mechanics; you should still test its failure behavior.

On this host, use the explicit Python 3.11 interpreter in `environment/README.md`.
