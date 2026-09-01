# Validation record

Generated on 2026-08-31 in the allocated learning-factory workspace. Results
below are observations from this host, not claims of independent validation.
The manifest intentionally remains `GENERATED` + `PARTIAL`.

## Runtime and unavailable dependency

Command:

```bash
ruby --version
```

Observed:

```text
ruby 2.5.9p229 (2021-04-05 revision 67939) [x86_64-linux]
```

The initially considered test dependency is unavailable, so the artifact uses
its own dependency-free harness.

```bash
ruby -e 'require "minitest/autorun"; puts "minitest available"'
```

Observed exit 1:

```text
/usr/share/rubygems/rubygems/core_ext/kernel_require.rb:59:in `require': cannot load such file -- minitest/autorun (LoadError)
	from /usr/share/rubygems/rubygems/core_ext/kernel_require.rb:59:in `require'
	from -e:1:in `<main>'
```

No gem installation or upstream network access was attempted.

## Syntax and CLI construction

Command:

```bash
ruby -e 'files=(Dir["{starter,public_tests,sealed}/**/*.rb"] + ["starter/bin/tiny_ws", "sealed/reference/bin/tiny_ws"]).uniq.sort; files.each { |file| RubyVM::InstructionSequence.compile_file(file) }; puts "Ruby syntax: #{files.length} files compiled"'
```

Observed exit 0:

```text
Ruby syntax: 22 files compiled
```

Command:

```bash
ruby sealed/reference/bin/tiny_ws --help
```

Observed exit 0:

```text
Usage: tiny_ws [options]
        --host HOST
        --port PORT
        --max-clients N
        --max-header-bytes N
        --max-frame-bytes N
        --max-message-bytes N
        --handshake-timeout SECONDS
        --read-timeout SECONDS
```

## Reference tests

Command:

```bash
ruby -Isealed/reference/lib sealed/reference_tests/run.rb
```

Observed exit 0:

```text
PASS known handshake derivation
PASS strict upgrade accepts tokens case-insensitively
PASS bare LF and folded fields are rejected
PASS duplicate and noncanonical keys are rejected
PASS HTTP reader preserves read-ahead bytes
PASS frame lengths use all three canonical forms
PASS decoder handles bytewise and consecutive frames
PASS decoder rejects RSV, missing mask, and reserved opcode
PASS decoder rejects noncanonical and oversized lengths early
PASS control frame constraints are enforced
PASS fragmentation permits ping and echoes complete message
PASS invalid text closes with 1007
PASS fragmented message bound closes with 1009
PASS invalid close payload sends one protocol close
SKIP loopback server upgrades read-ahead frame and shuts down: loopback TCP unavailable: Errno::EPERM: Operation not permitted - socket(2) for "127.0.0.1" port 0
14 passed, 1 skipped, 0 failed
```

An earlier run reported 13 passes and one ordinary failure because the decoder
reported a noncanonical-length protocol error before a simultaneously breached
configured byte limit. The implementation was changed to enforce the resource
limit as soon as the numeric length is known; the rerun above is the preserved
final result. The TCP skip is an environment blocker, not a pass.

## Public compatibility

Command against the sealed reference:

```bash
TINY_WS_LIB=sealed/reference/lib ruby public_tests/run.rb
```

Observed exit 0:

```text
PASS handshake accept derivation
PASS strict valid upgrade
PASS invalid key is rejected
PASS small server frame encoding
PASS masked frame round trip
PASS decoder waits for split input
PASS oversized advertised frame is rejected early
PASS fragmented control frame is rejected
8/8 public checks passed
```

Command against the untouched learner scaffold:

```bash
ruby -Istarter/lib public_tests/run.rb
```

Observed exit 1, as intended for a challenge starter:

```text
FAIL handshake accept derivation: NotImplementedError: derive Sec-WebSocket-Accept
FAIL strict valid upgrade: NotImplementedError: parse the HTTP upgrade
FAIL invalid key is rejected: NotImplementedError: parse the HTTP upgrade
FAIL small server frame encoding: NotImplementedError: encode a WebSocket frame
FAIL masked frame round trip: NotImplementedError: encode a WebSocket frame
FAIL decoder waits for split input: NotImplementedError: encode a WebSocket frame
FAIL oversized advertised frame is rejected early: NotImplementedError: decode a WebSocket frame
FAIL fragmented control frame is rejected: NotImplementedError: decode a WebSocket frame
0/8 public checks passed
```

## Deterministic adversarial checks

Command:

```bash
ruby sealed/adversarial/run.rb
```

Observed exit 0:

```text
PASS 54 deterministic adversarial checks
```

This enumerated runner is not coverage-guided or randomized fuzzing. No
`FUZZED` label is claimed.

## TCP integration blocker

Command:

```bash
ruby -rsocket -e 'server=TCPServer.new("127.0.0.1",0); puts server.addr[1]; server.close'
```

Observed exit 1:

```text
-e:1:in `initialize': Operation not permitted - socket(2) for "127.0.0.1" port 0 (Errno::EPERM)
	from -e:1:in `new'
	from -e:1:in `<main>'
```

Accordingly, handshake read-ahead and connection behavior ran over local UNIX
socket pairs, but `TCPServer` bind/accept behavior was not runnable here. This
is the principal reason for `PARTIAL` status.

## Packaging gate

Command (run after all files were created):

```bash
ruby sealed/validate_pack.rb
```

Observed exit 0:

```text
PASS structure, forbidden paths, metadata status, regular-file policy, and credential scan
```

The gate checks every authoritative required path, every forbidden path,
strict-JSON manifest fields, linked provenance identifiers, symlinks and special
files, and common credential shapes. Independent validators still need to
compare the complete immutable provenance object and run TCP/conformance tests
on a capable host.

## Labels not claimed

No benchmark was executed, no profiler or fuzzer was run, no external
conformance suite was available, and no production deployment or transfer
verification occurred. Therefore this artifact does not claim `BUILDS`,
`TESTED`, `FUZZED`, `BENCHMARKED`, `REVIEWED`, `TRANSFER_VERIFIED`, or
`PRODUCTIONIZED`; promotion belongs only to the orchestrator's independent
validators.

