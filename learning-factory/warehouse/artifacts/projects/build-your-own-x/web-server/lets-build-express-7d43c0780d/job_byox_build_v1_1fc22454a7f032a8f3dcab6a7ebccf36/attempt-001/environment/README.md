# Environment

This challenge has no third-party dependencies. It requires Node.js 18.17 or
newer and uses Node's built-in CommonJS, HTTP, assertion, and test modules. The
reproducible reference runtime is **Node.js 20.19.5**; its npm distribution is
used only as a convenient script runner.

## Current authoring host

Neither `node` nor `npm` is installed on the allocated authoring host. The public
suite was therefore **not run on this host**. This is a host limitation, not a
request to install repository dependencies.

## Reproduce with a local Node installation

If `nvm` is available, the pinned version is recorded in `.nvmrc` in this
directory:

```bash
nvm install "$(cat environment/.nvmrc)"
nvm use "$(cat environment/.nvmrc)"
node environment/check-runtime.js
node --test public_tests/*.test.js
```

Or, from the repository root with any supported Node version:

```bash
node environment/check-runtime.js
npm --prefix starter test
```

No `npm install` step is needed.

The structure and immutable metadata can also be checked with the Python runtime available on the authoring host:

```bash
python3 environment/verify-structure.py
```

That script traverses only the generated artifact roots; it does not inspect factory-control paths.

## Reproduce with a container

From the repository root, a Docker-compatible runtime can run the suite with an
exact published Node image:

```bash
docker run --rm --network none --user node \
  --mount "type=bind,src=$PWD,dst=/work,readonly" -w /work node:20.19.5 \
  node --test public_tests/01_surface.test.js \
  public_tests/02_middleware.test.js \
  public_tests/03_routes_and_requests.test.js \
  public_tests/04_responses_async_errors.test.js \
  public_tests/05_isolation.test.js
```

The tests open only an ephemeral loopback server. They do not need external
network access, credentials, databases, or writable locations outside the
repository.
