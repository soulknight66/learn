# Independent review

Verdict: **REVISE**.

The pack is unusually candid about its partial status and is useful as a protocol-learning draft. The accessible reference behavior held up under the supplied suites and five independently specified protocol cases. Revision is still needed before learner release because disclosure, starter-interface, packaging, and test-feedback guarantees are not deterministic.

## Prioritized findings

### P1 — High: the learner/evaluator boundary is asserted, not enforced

`AGENTS.md` tells learners not to read `sealed/`, but complete design answers, exercise answers, reference code, and evaluator tests are readable at mode `0444` in the same submitted tree. A directory name and agent instruction do not prove progressive disclosure. The packaging validator checks that certain sealed paths are not nested under `starter/` or `public_tests/`; it does not materialize or inspect a learner view.

If the external harness already filters `sealed/**`, that control was not available to validate here. Before release, create a deterministic allowlisted student-view export and a harness-owned test proving that no sealed/reference/test-answer path or content is present or readable in that view.

### P1 — High: the starter CLI teaches an unsafe and incomplete lifecycle

`starter/bin/tiny_ws` omits `--handshake-timeout` and `--read-timeout`, although both are constructor limits and appear in the reference CLI. This contradicts `starter/README.md`'s statement that the scaffold defines the required CLI surface.

The starter also invokes `server.stop` directly inside `INT`/`TERM` traps. The required server bookkeeping is synchronized; invoking the reference-quality synchronized `stop` from a signal trap independently reproduced `ThreadError: can't be called from trap context`. The starter additionally reports the configured port before binding, so port `0` cannot be reported accurately. Align the learner scaffold with the reference's signal-safe flag/wakeup pattern, expose both timeout options, start before reporting the selected port, and add lifecycle tests.

### P2 — Medium: the package gate can accept a nonfunctional pack

The `REQUIRED` list in `sealed/validate_pack.rb` contains documentation paths but omits all checked core entry points, including:

- `starter/lib/tiny_ws.rb` and `starter/bin/tiny_ws`
- `public_tests/run.rb` and its harness
- `sealed/reference/lib/tiny_ws.rb` and its executable
- `sealed/reference_tests/run.rb`
- `sealed/adversarial/run.rb`

The gate's exit 0 therefore establishes only its narrower self-defined structure, not a complete runnable artifact. Require every authoritative file (or a checked file inventory with hashes), validate executability where needed, and integrate syntax/test command discovery into the deterministic packaging gate.

### P2 — Medium: public feedback stops halfway through the advertised project

The public runner has eight cases but contains no reference to `TinyWS::Connection` or `TinyWS::Server`. A learner can reach 8/8 while the connection state machine and network service remain `NotImplementedError`. This also makes `public_tests/README.md`'s claim of "basic connection state" coverage inaccurate.

Add bounded `Socket.pair` cases for fragmentation, ping/close, UTF-8, and message limits. Add CLI construction and server lifecycle tests, conditionally skipping only the real TCP cases when bind is unavailable.

### P2 — Medium: application protocol exceptions are misclassified as peer failures

`Connection#run` rescues `ProtocolError` around both input processing and the application callback. In an independent socket-pair check, a handler-raised `ProtocolError` with code 1008 produced close frame `880203f0` and the worker returned normally. The application failure was suppressed and attributed to the peer. Handler-triggered `LimitError` has the same class-boundary problem.

This conflicts with `sealed/DESIGN.md`'s distinction between peer protocol errors and callback/internal defects. Contain callback failures per connection, but translate them to 1011 and surface them through a safe error hook or re-raise path; reserve peer close codes for failures arising from decoded peer input.

### P3 — Low: artifact licensing and digest semantics are incomplete

The catalog/linked-resource boundary is clearly and honestly described: catalog metadata is CC0, the article is `NOASSERTION`, and no linked content is claimed copied. However, "generated independently for personal educational use" is not an explicit license grant, and no `LICENSE` or `COPYING` file exists for the generated code, tests, and prose.

Also, `MANIFEST.yaml` calls `aa3c...` `provenance_sha256`; it equals `PROVENANCE.json`'s embedded `snapshot_sha256`, while the actual file SHA-256 is `aeab6f...`. Define what the former authenticates and add a separately named digest/inventory for the emitted artifact. Record explicit reuse terms for generated material.

## Evidence that held up

- Ruby 2.5.9 compiled all 22 Ruby sources/entry points.
- Public tests against the reference passed 8/8.
- The sealed suite passed 14 tests, honestly skipped its one TCP test, and had no failures.
- Five reviewer-authored known-wire/timeout checks passed.
- The deterministic adversarial runner passed 54 checks and is correctly not described as fuzzing.
- The starter's 0/8 result is clearly documented as intentional.
- The manifest remains `GENERATED`/`PARTIAL`, requires independent validation, and makes no elevated validation or production claim.
- No symlink, special file, world-writable file, obvious credential material, or vendored third-party dependency was observed.

## Validation ceiling

TCP behavior could not run in this sandbox. No external conformance suite, source/article comparison, fuzzing, benchmark, multi-runtime CI, security review, transfer check, or production trial was available. The review therefore does not establish or promote `BUILDS`, `TESTED`, `FUZZED`, `BENCHMARKED`, `REVIEWED`, `TRANSFER_VERIFIED`, or `PRODUCTIONIZED`.
