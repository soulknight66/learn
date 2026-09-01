# Sprout: a tiny interpreter and bytecode machine

Build a small language twice: first as a tree-walking interpreter, then as a compiler targeting a
stack virtual machine. The language is intentionally compact, but the engineering contract is not:
diagnostics carry locations, lexical scope is observable, logical operators short-circuit, and all
untrusted work is bounded.

This is an independently generated challenge inspired only by the catalog topic “The Super Tiny
Interpreter.” The linked upstream resource was not copied. The complete production artifact records
its provenance and license boundary separately. Newly generated material is for personal educational
use; this pack grants no redistribution license.

## What you build

The starter exports six functions:

```js
tokenize(source, options?)
parse(tokens, options?)
interpret(ast, options?)
compile(ast, options?)
runBytecode(program, options?)
execute(source, { engine: "tree" | "vm", ...limits }?)
```

A successful execution returns `{ value, output }`, where `output` is an array of strings emitted by
`print`. Neither engine writes language output to the host console.

## Progression

1. Tokenize punctuation, operators, literals, identifiers, keywords, comments, and escapes.
2. Parse the precedence grammar into the specified AST.
3. Evaluate the AST with nested lexical environments and deterministic runtime errors.
4. Emit relocatable stack bytecode with absolute jump targets.
5. Validate and execute bytecode with the same observable semantics as the tree walker.
6. Harden limits and use differential tests to keep the two engines aligned.

Read `REQUIREMENTS.md` before coding. `CONCEPTS.md` explains the ideas without giving an
implementation, and `DESIGN_QUESTIONS.md` provides checkpoints. Public tests cover only a narrow
slice of the contract.

## Run

Install Node.js 20 or newer, then:

```sh
cd starter
npm test
npm run test:public
```

No package installation is required. The factory host used to generate this artifact had no
compatible Node.js/ES-module runtime, so original-module execution remains unverified and the
manifest deliberately remains `GENERATED` + `PARTIAL`. The complete production artifact retains an
exact validation record.

## Learner-view boundary

The complete production artifact contains evaluator-only material. A worker harness must distribute
only the explicit allowlist implemented by `environment/learner_view.py`: the six learner-facing
top-level documents plus `starter/`, `public_tests/`, and `environment/`. The tool can export to a
new external directory and verify its exact file set and hashes; it never deletes or merges an
existing destination. Generation checked the policy only and did not create a learner workspace.
