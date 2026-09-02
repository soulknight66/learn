# Public tests

These black-box tests import the learner module through the local `replace` in
`go.mod`. They reveal one representative slice of each milestone: token spans,
tree shape, checking, bytecode execution, laziness, differential behavior, and
malformed-bytecode rejection.

From this directory run:

```bash
go test ./...
```

The tests intentionally fail against the untouched scaffold. Passing them is
necessary but not sufficient: exact examples are not a complete language
definition, and independent validators use additional boundary and adversarial
cases. Do not add implementation code or solution notes here.
