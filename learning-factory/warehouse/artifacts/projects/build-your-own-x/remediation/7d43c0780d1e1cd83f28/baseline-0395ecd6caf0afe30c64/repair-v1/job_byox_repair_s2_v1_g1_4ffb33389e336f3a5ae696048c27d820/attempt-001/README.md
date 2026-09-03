# Build a Small Express-Like HTTP Framework

Create a dependency-free Node.js framework on top of `node:http`. The finished framework will
register middleware and routes, parse JSON bodies, decorate requests and responses, isolate
concurrent requests, and turn failures into deliberate HTTP responses.

This is a progressive challenge pack. Begin with [REQUIREMENTS.md](REQUIREMENTS.md), review the
background in [CONCEPTS.md](CONCEPTS.md), and answer [DESIGN_QUESTIONS.md](DESIGN_QUESTIONS.md)
before changing `starter/`. Public checks intentionally cover only part of the contract; the
independent validator may exercise every requirement and edge case.

## Suggested progression

1. Implement middleware composition and the terminal 404 response.
2. Implement route compilation, method selection, parameters, and query parsing.
3. Add response helpers and consistent error translation.
4. Add bounded JSON body parsing and aborted-request handling.
5. Test concurrent traffic and audit all request-specific state.

The starter exposes this shape:

```js
const tiny = require('./starter');
const app = tiny();

app.use(tiny.json({ limit: 64 * 1024 }));
app.get('/hello/:name', (req, res) => {
  res.status(200).json({ hello: req.params.name });
});

const server = app.listen(3000, '127.0.0.1');
```

Run the public suite from the repository root when Node.js 18 or newer is available:

```sh
node --test public_tests/*.test.js
```

## Learner-view boundary

The full production pack is not a learner workspace because it also carries evaluator material. A
control plane must project a separate view using the deterministic tool documented in
`environment/README.md`. That view contains exactly `README.md`, `AGENTS.md`, `MANIFEST.yaml`,
`REQUIREMENTS.md`, `CONCEPTS.md`, `DESIGN_QUESTIONS.md`, `starter/`, `public_tests/`, and
`environment/`. If evaluator directories appear in a learner workspace, treat that as an isolation
failure and stop rather than inspecting them.

The artifact remains `GENERATED` + `PARTIAL`. A configured Node.js runtime executed syntax checks
and socket-free regressions, but this build sandbox denied loopback listeners, so the HTTP suites
could not complete. The evaluator-only validation record contains the exact outcomes. Independent
validation and a harness-captured learner-view transfer remain mandatory.
