# Design answers

1. `Transport` and the HTTP layer own bytes. UTF-8 is required only after response framing selects the exact body.
2. Search at most `max_header_bytes + 4` bytes for CRLF/CRLF, then verify the delimiter begins no later than the budget.
3. Different intermediaries may choose different length signals, so this subset rejects every Transfer-Encoding and inconsistent lengths.
4. Charge a DOM node immediately before inserting it. Charge element depth before descending into its children.
5. Recursive descent carries the expected closing name. Seeing a close consumes it and either returns to the caller or reports a mismatch.
6. Each winning declaration is keyed by `(specificity, source_order)`; tuple ordering gives the cascade.
7. Only color inherits. The parent color is an argument to recursive styling, including for text nodes.
8. Rectangles are half-open: `[x, x + width)` by `[y, y + height)`.
9. Greedy wrapping splits an over-wide word at Unicode scalar-count boundaries, guaranteeing progress.
10. The transport budget and every coordinate, area, and doubled decoration use checked arithmetic.
11. A real connector needs an explicit host allowlist, DNS-result address filtering, connect-to-the-approved-address semantics, timeouts, redirect revalidation, and byte caps.
12. HTTPS, IPv6, transfer coding, compressed bodies, charset conversion, CSS combinators, malformed-markup recovery, fonts, scripts, and external resources fail or remain unsupported rather than being guessed.

The key architectural choice is to keep stage outputs distinct. It makes invalid transitions difficult and permits tests to target one trust boundary at a time.
