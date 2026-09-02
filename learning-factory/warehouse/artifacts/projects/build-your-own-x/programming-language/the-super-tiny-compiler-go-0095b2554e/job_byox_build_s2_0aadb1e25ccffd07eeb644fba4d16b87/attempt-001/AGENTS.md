# Learner-agent instructions

Work only in `starter/` unless a test command explicitly reads `public_tests/`.
Treat `REQUIREMENTS.md` as normative and keep every exported signature supplied
by the scaffold. Do not inspect or copy material under `sealed/`; it is reserved
for independent validation and instructor use.

Use deterministic Go code with no network dependencies. Preserve source spans,
return errors instead of panicking on user input, bound parser and VM resources,
and write tests for every defect you repair. Do not weaken, delete, or special-case
public tests. A robust solution should also survive valid inputs not shown there.

Recommended loop:

```bash
cd starter
gofmt -w .
go test ./...
cd ../public_tests
go test ./...
```

Completion claims are not validation. Record commands honestly and expect an
independent harness to exercise malformed tokens, deep nesting, jump targets,
stack discipline, output behavior, and interpreter/compiler agreement.
