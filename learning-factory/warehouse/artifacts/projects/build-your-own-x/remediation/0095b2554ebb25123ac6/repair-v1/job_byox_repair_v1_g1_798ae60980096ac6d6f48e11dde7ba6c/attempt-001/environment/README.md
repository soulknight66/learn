# Environment

The project uses only the Go standard library and targets Go 1.21 or newer. There are two learner-facing modules:

- `starter/go.mod` — the implementation module `example.com/pebble`;
- `public_tests/go.mod` — a black-box test module with a local `replace` directive.

No download, service, database, environment variable, credential, code generator, or C toolchain is required. `GOTOOLCHAIN=local` may be used in an offline environment to prevent automatic toolchain downloads.

`learner-view.json` is the machine-readable disclosure policy. It allowlists exactly the six learner documents and three learner directories, makes only `starter/` writable, and requires the production source pack not to be mounted in the learner process. Evaluator code under `sealed/validation/` constructs this view by copying only allowlisted regular entries and can launch an isolation probe with bubblewrap. Merely placing a `sealed/` directory beside learner files is not an acceptable deployment.

Expected verification on a machine with Go installed:

```bash
GOTOOLCHAIN=local go version
(cd starter && GOTOOLCHAIN=local go test ./...)
(cd public_tests && GOTOOLCHAIN=local go test ./...)
```

At generation time on this host, both `command -v go` and `go version` established that no `go` executable was available. No attempt was made to fetch a toolchain because network access and unrecorded dependencies would undermine reproducibility. The evaluator-owned validation record contains the literal observed commands and results.
