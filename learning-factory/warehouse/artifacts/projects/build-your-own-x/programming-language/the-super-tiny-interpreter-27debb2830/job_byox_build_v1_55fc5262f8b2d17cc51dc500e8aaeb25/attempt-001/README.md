# Sprout: a tiny interpreter and bytecode machine

Build a small language twice: first as a tree-walking interpreter, then as a compiler targeting a
stack virtual machine. The language is intentionally compact, but the engineering contract is not:
diagnostics carry locations, lexical scope is observable, logical operators short-circuit, and all
untrusted work is bounded.

This is an independently generated challenge inspired only by the catalog topic “The Super Tiny
Interpreter.” The linked upstream resource was not copied; see `LICENSE_BOUNDARY.md`.

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
compatible Node.js/ES-module runtime, so original-module execution remains unverified and the manifest deliberately remains
`GENERATED` + `PARTIAL`. Exact observations are in `VALIDATION.md`.
