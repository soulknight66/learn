# Sealed design alternatives

Several valid implementations meet the observable contract:

- A Pratt parser can replace one function per precedence level. It becomes attractive when adding
  calls, indexing, or user-defined operators, but its binding-power table is less immediately
  visible to a first-time parser author.
- A resolver pass can assign each identifier a lexical `(depth, slot)` pair before either backend
  runs. This detects some errors earlier and removes repeated string searches.
- A register VM can reduce stack shuffling and make data flow explicit. It requires register
  allocation and wider instructions, which distract from this challenge's control-flow objective.
- Bytecode can be encoded into integer arrays rather than instruction objects. That is smaller and
  closer to real VMs, but object instructions make public invariants and diagnostic spans easier to
  inspect.
- A typed intermediate representation between AST and bytecode could centralize control-flow
  lowering. For this grammar it adds more representation than behavior; it becomes useful with
  functions, loops, or optimizations.

These alternatives are not required extensions. Any replacement must preserve the specified API,
evaluation order, diagnostics, and backend parity.
