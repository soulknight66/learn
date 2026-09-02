# Environment

Required runtime: Node.js 18 or newer with CommonJS and the built-in `node:test` module. No npm packages, build step, browser, network access, or environment variables are required.

From the repository root:

```text
node --version
node --test public_tests/compiler.test.js
```

Optional syntax check:

```text
node --check starter/compiler.js
```

The build host used to generate this pack did not expose `node` or `npm`; see `VALIDATION.md`. That is an artifact-generation limitation, not a requirement to emulate.
