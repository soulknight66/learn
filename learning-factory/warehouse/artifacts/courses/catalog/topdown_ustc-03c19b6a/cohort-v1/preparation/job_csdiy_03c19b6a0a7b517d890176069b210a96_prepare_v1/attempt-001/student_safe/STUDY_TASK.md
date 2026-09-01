# Study Task: Build a bounded HTTP/1.1 response reader

## Goal and budget

Produce a small command-line client, a response-reader component, deterministic tests, and a short engineering report. Budget about six focused hours. Stop at the stated protocol boundary; breadth is not the goal.

## 1. State the contract

Before implementing, put a supported/unsupported table in your README. Your supported response subset is:

- TCP over IPv4 or IPv6 loopback only;
- one `GET` request using origin-form `/` and `Connection: close`;
- an HTTP/1.1 status line;
- a response head terminated by `\r\n\r\n`;
- case-insensitive header names;
- exactly one syntactically valid, non-negative decimal `Content-Length` value;
- a body of exactly that declared length, including a zero-length body;
- arbitrary fragmentation across reads, including a delimiter or body split at any byte.

Reject behavior outside that subset with a named error; do not silently guess. In particular, reject malformed status/header lines, obsolete folded headers, missing, duplicate, or conflicting `Content-Length`, any `Transfer-Encoding`, a premature EOF, excess configured sizes, and a timeout.

Use configurable limits with documented defaults no greater than:

- 16 KiB for the complete response head;
- 1 MiB for the response body;
- 2 seconds for each local connect/read operation in normal tests.

Do not use a high-level HTTP library or an existing HTTP parser for the core. Socket, byte-buffer, clock, logging, and test libraries are allowed.

## 2. Design seams before socket code

Make the response reader testable independently of a live socket. It should consume a byte-source abstraction, iterator, callback, or equivalent seam that can return deliberately chosen fragment sizes. Keep these concerns visibly separate:

1. transport and timeout handling;
2. byte accumulation and framing;
3. status/header parsing and validation;
4. size and supported-subset policy;
5. result presentation and diagnostic events.

Define stable result fields for HTTP version, numeric status, reason text, headers, and body. Define a small error taxonomy that lets callers distinguish malformed input, unsupported framing, limit violations, premature EOF, and timeout/transport failures.

## 3. Implement the loopback client

Accept a loopback host and numeric port from the command line. Reject non-loopback targets before connecting. Send a minimal, valid request as bytes; then parse the response through the same response-reader component used by tests.

Emit concise diagnostic events to standard error or a dedicated log sink. Include a stable event name, phase, byte counts where applicable, elapsed time from a monotonic clock, and the final result/error category. Do not log the response body or pretend that timing proves correctness. Send a human-readable summary to standard output.

Avoid unbounded reads and busy waits. Close resources on both success and failure. Do not retry automatically in this unit.

## 4. Build deterministic evidence

Create an in-process scripted server bound to an ephemeral loopback port, or use an in-memory scripted byte source when a real socket is not relevant. No test may depend on an external host, sleep-based race, or a fixed port.

Cover at least these cases:

- a valid response delivered in one fragment;
- the same valid response split at every possible single byte boundary;
- a delimiter split across multiple fragments;
- headers and body arriving in the same read;
- zero-length and binary bodies (including a zero byte);
- mixed-case header names;
- malformed status and header lines;
- missing, invalid, duplicate, and conflicting `Content-Length` cases;
- unsupported `Transfer-Encoding`;
- premature EOF during both head and body;
- configured head and body limits at the boundary and one byte over;
- a deterministic timeout using an injected/fake byte source or a tightly controlled loopback peer;
- rejection of a non-loopback target without attempting a connection.

For malformed-input tests, assert the public error category rather than incidental exception text. A test helper may generate fragmentation schedules, but keep the schedules reproducible.

## 5. Package the work

Submit:

- source files;
- automated tests;
- a README containing prerequisites, exact build/test/run commands, the contract table, default limits, and a prominent non-production warning;
- `REPORT.md`, limited to about 800 words, containing the test command and observed result, a short architecture explanation, one failure discovered while testing, remaining risks, and what would have to change for a production client;
- responses to every prompt in `COMPREHENSION.md`, with references to relevant code or tests where requested.

Run all documented commands from a clean checkout or equivalent clean build state. Keep generated dependencies and build output out of the submission unless your ecosystem requires a lockfile.

## Completion boundary

Your work is ready for examination when all submitted commands run locally without public-network access and the artifacts above are present. A controlled validator will make the completion decision. Finishing this task is evidence only for this kickoff unit, never for the complete catalog course.

---

Provenance: manager-authored kickoff based only on the supplied CSDIY catalog snapshot; no linked course content was used.  
Validation label: `PREPARED_AWAITING_INDEPENDENT_VALIDATION`.
