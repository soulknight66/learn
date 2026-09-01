# Starter

`src/index.js` is a runnable but intentionally incomplete scaffold. It exports
the required CommonJS factory, creates a callable application, exposes all
required method names, records registrations, and can listen as a Node HTTP
server. Its dispatcher currently emits the empty-stack 404 response and does not
execute registered layers.

Implement the contract in [../REQUIREMENTS.md](../REQUIREMENTS.md) here. You may
replace the internal scaffold freely, but keep this public entry point:

```js
const createApplication = require('./src/index.js');
const app = createApplication();
```

No installation is necessary because the project has no dependencies. With a
supported Node.js runtime, run all public tests from this directory with:

```bash
npm test
```

Or run them from the repository root:

```bash
node --test public_tests/*.test.js
```

The tests are staged. A few surface and empty-app checks pass against the
scaffold; later tests are expected to fail until the corresponding behavior is
implemented. A failing starter is therefore intentional, not an environment
installation problem.

