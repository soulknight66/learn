# Working agreement

Implement only the learner-facing code under `starter/`. Do not inspect `sealed/`; it contains evaluator material and reference work that invalidates the exercise if viewed.

Use Ruby's standard library only. Run commands from the repository root:

```sh
ruby -Istarter/lib public_tests/test_public.rb
ruby starter/bin/pebble examples/program.peb
```

The second command assumes you create your own input program. Preserve the documented API and error classes because additional validators may exercise them. Avoid global mutable state, shell command execution, network access, and nondeterministic output. A passing public suite is necessary but not sufficient; check all requirements and add your own tests.
