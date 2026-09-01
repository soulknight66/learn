# Starter

This directory is the learner workspace. The exported API is wired up, shared token names and error
classes are supplied, and each unfinished phase throws `NotImplementedError`.

Implement in this order:

1. `src/lexer.js`
2. `src/parser.js`
3. `src/interpreter.js`
4. `src/compiler.js`
5. `src/vm.js`
6. orchestration in `src/index.js`

Do not change public test imports or error class names. You may add modules and tests. Read the full
contract in `../REQUIREMENTS.md`; the TODO comments are navigation aids, not a substitute for it.

With Node.js 20 or newer:

```sh
npm test
npm run test:public
```
