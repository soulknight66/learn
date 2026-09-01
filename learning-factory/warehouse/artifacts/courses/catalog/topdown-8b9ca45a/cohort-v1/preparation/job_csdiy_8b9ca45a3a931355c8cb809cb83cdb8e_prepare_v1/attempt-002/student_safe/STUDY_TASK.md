# Study task: one observable HTTP exchange

Build a small command-line client and a loopback test fixture that make one plain-text HTTP/1.1 `GET` exchange over a raw TCP socket. The client is an exercise in protocol boundaries and defensive engineering, not a general HTTP library.

## Deliverables

Keep these together in a small project directory:

1. Client source code with transport I/O separated from response-head parsing.
2. An automated test suite that starts its own server fixture on an ephemeral loopback port.
3. A short `README` containing exact build and test commands, language/runtime version, assumptions, and declared non-goals.
4. A sanitized evidence record from one successful local run. Show the request bytes in an unambiguous escaped or hexadecimal form, the order and sizes of bytes returned by the fixture, the parsed status and headers, the body byte count, and the program's exit result. Do not include secrets or external traffic.
5. A brief design note stating the parser states, the invariant maintained after each received fragment, the resource bounds, and the error categories exposed to callers.

## Required behavior

Your client must:

- accept a loopback host, port, and origin-form path without invoking a shell;
- construct one HTTP/1.1 `GET` request with a valid `Host` field and request connection closure;
- send the complete request even if a socket write accepts only part of the buffer;
- recognize the end of the response head even when its delimiter crosses receive boundaries;
- validate the response status line and parse header field names case-insensitively;
- preserve body bytes exactly as received after the response-head delimiter;
- distinguish at least timeout, premature EOF before a complete head, malformed status or header syntax, connection failure, and configured-size-limit failure;
- apply an explicit per-operation timeout, a response-head limit no greater than 64 KiB, and a total-response limit no greater than 1 MiB; and
- terminate deterministically with a nonzero result for the defined failures.

For this unit, the fixture may delimit the body by closing the connection. If the response uses a transfer coding, the client must report that it is unsupported rather than silently presenting encoded bytes as a decoded entity body. Do not add TLS, redirects, cookies, compression, or public-host crawling.

## Experiments and tests

Your automated tests must cover at least these cases without contacting the public network:

- a valid response delivered in one write;
- the same logical response divided at several different byte boundaries, including inside the end-of-head delimiter and status line;
- valid header names using mixed letter case;
- body bytes that are not valid text;
- EOF before the response head is complete;
- a malformed status line or header line;
- a fixture that stalls long enough to trigger the configured timeout; and
- input that crosses each configured size limit.

At least one test should generate multiple fragmentations from a single canonical response rather than maintaining unrelated hand-written expected results. Report which fragmentations were exercised and make failures reproducible.

## Suggested work sequence

First write down the states and limits. Build the deterministic loopback fixture next, then implement the smallest successful exchange. Add fragmented-delivery tests before extending error handling. Finish by running the project from a clean process, saving sanitized evidence, and answering the separate comprehension prompts.

External course links and packet capture are optional enrichment. If you voluntarily use packet capture, restrict it to the loopback experiment and document the filter and tool version; it does not replace application-level tests.
