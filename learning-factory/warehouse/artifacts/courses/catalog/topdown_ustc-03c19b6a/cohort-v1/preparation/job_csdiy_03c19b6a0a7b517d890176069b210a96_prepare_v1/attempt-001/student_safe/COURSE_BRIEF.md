# USTC Computer Networking: A Top-Down Approach

## What this package is

This is a six-hour kickoff for a larger course cataloged at roughly 40 hours. It is designed for a learner who is already comfortable with algorithms and now wants practice turning a precise idea into reliable, testable software. Completing this kickoff does **not** complete the catalog course.

The kickoff is manager-authored. It is not presented as an official USTC lecture, textbook chapter, assignment, or exam topic. The catalog's course website, recordings, slide archive, and named seventh-edition textbook were not retrieved or inspected when this package was prepared. You do not need them for this unit.

## Unit 1: HTTP over TCP—boundaries, failures, and testable design

You will build a deliberately small HTTP/1.1 response reader and exercise it against a local scripted server. The point is not to recreate a web library. The point is to practice the engineering work that sits around an algorithm:

- define a narrow contract before implementing it;
- keep transport mechanics separate from parsing and policy;
- make malformed input and resource exhaustion explicit;
- design deterministic tests for behavior the network may expose unpredictably;
- leave useful evidence for another engineer who did not watch you work.

## Working model

TCP carries an ordered stream of bytes. A receive call may return less or more data than an application-level field, regardless of how the peer grouped its writes. An application protocol therefore needs its own framing rules.

For this unit, the response head ends at the first `\r\n\r\n`. A valid response in the supported subset has a parseable HTTP/1.1 status line, header fields, exactly one usable decimal `Content-Length`, and then that many body bytes. Your implementation must accumulate and parse the stream according to that contract rather than according to receive-call boundaries.

Reliability also requires policy. A peer can delay forever, omit a delimiter, claim an enormous body, close early, or send ambiguous framing. Timeouts, byte caps, a clear error taxonomy, and careful logging are part of the design—not cleanup work after the parser is written.

## Boundaries

The exercise uses only in-memory byte streams and the loopback interface. It must not contact public hosts. TLS, DNS, redirects, chunked transfer coding, response bodies framed only by connection close, compression, proxies, authentication, HTTP/2, and HTTP/3 are intentionally outside the supported subset.

You may use your language's socket primitives and ordinary testing tools. Do not use a high-level HTTP client or an HTTP response parser for the core exercise. This is a teaching implementation, and its README must say so.

## Materials status

The supplied preparation data contains catalog metadata and pointers, not retrieved teaching content. The external website, recordings, and slide archive are link-only and unverified. The textbook is a bibliographic reference only; no licensed copy was supplied. Later course jobs may expand the course if they retrieve and validate material lawfully. This kickoff remains usable without that expansion.

---

Provenance: manager-authored from CSDIY catalog metadata at commit `adce8e13789dc16aa6d1fbe163e9541736defae4`; no linked course content was inspected.  
Validation label: `PREPARED_AWAITING_INDEPENDENT_VALIDATION`.
