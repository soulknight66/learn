# Requirements

## 1. Scope and API

Implement every `todo!()` in `starter/src/` without changing public type names or function signatures. Use only the Rust standard library and no `unsafe` code. The engine processes caller-supplied response bytes through a `Transport`; tests must not require external connectivity.

All parsers accept untrusted input. They must return `BrowserError`, never panic, and must enforce `EngineLimits` before excessive allocation or recursion.

## 2. URL and HTTP

`Url::parse` must:

- accept ASCII `http://` URLs only and lowercase the scheme and host;
- reject credentials (`@`), fragments, whitespace, control bytes, empty hosts, IPv6 literals, and malformed ports;
- default the port to 80 and produce a request target beginning with `/`;
- accept DNS-style hosts and IPv4 text made only of ASCII letters, digits, dots, and hyphens, while rejecting empty labels and labels beginning or ending with `-`.

`build_get_request` emits one HTTP/1.1 GET with CRLF line endings and exactly the `Host`, `Connection: close`, `User-Agent: pocket-browser/1`, and `Accept: text/html` headers. Include `:port` in `Host` only for a non-default port. Untrusted URL text must never create another header.

`parse_response` must:

- recognize HTTP/1.0 and HTTP/1.1 status lines;
- locate one CRLF/CRLF boundary within `max_header_bytes`;
- parse ASCII token header names case-insensitively and reject obsolete folded lines and control bytes in values;
- reject every `Transfer-Encoding`, ambiguous/differing `Content-Length` values, truncated bodies, invalid UTF-8 bodies, and bodies over `max_body_bytes`;
- use the exact Content-Length body when present and reject trailing bytes; otherwise use bytes through EOF.

## 3. HTML subset

Parse a document forest containing elements, text, comments, and `<!doctype ...>`. Element and attribute names become ASCII lowercase. Attribute values must be quoted, duplicate attributes are errors, and closing tags must match. Recognize `br`, `img`, `meta`, `link`, `input`, and `hr` as void elements.

Decode only `&amp;`, `&lt;`, `&gt;`, `&quot;`, and `&#39;`. An unknown or unterminated entity is an error. Enforce `max_dom_depth` and `max_nodes`. Comments and doctypes do not become DOM nodes.

## 4. CSS subset and cascade

Parse flat rules of the form `selector-list { declarations }`, including `/* comments */`. A compound selector may contain one optional type or `*`, plus `#id` and `.class` components, with no combinators or whitespace inside it. Reject empty selectors, nested blocks, malformed comments, and malformed declarations.

Selector specificity is `(id_count, class_count, type_count)`. For each property, higher specificity wins; ties go to the later source rule. Supported interpreted properties are `display`, `color`, `background`, `width`, `height`, `margin`, and `padding`. Invalid values for those properties are errors during styling. Text inherits `color`; other properties do not inherit. User-agent defaults make common structural tags block-level and `head`, `style`, and `script` hidden.

## 5. Layout and painting

Lay visible nodes out deterministically in a vertical block flow. Values for dimensions are non-negative integer `px` values. Margin lies outside a box; padding lies inside. Explicit width is clamped to available content width. Explicit height is a minimum. Text collapses ASCII whitespace, wraps greedily at Unicode scalar-count width, and occupies one row per line. A zero viewport width is an error.

Every `LayoutBox` uses half-open integer rectangles. Siblings must not overlap vertically. Hidden nodes produce no boxes. `paint` fills the canvas white, then paints box backgrounds in tree order with clipping; child backgrounds paint over ancestors. Text is retained as layout data but glyph rasterization is out of scope. Reject a canvas larger than `MAX_CANVAS_PIXELS` before allocation and use fallible reservation.

## 6. End-to-end engine

`BrowserEngine::load` must construct the request, call its transport exactly once, parse the response, reject non-2xx status codes, and reject a present Content-Type unless its media type (before `;`) is ASCII-case-insensitively `text/html`. Then it runs HTML, CSS, style, layout, and paint and returns a `Page` containing the request for inspection.

The transport receives a maximum response byte count equal to `max_header_bytes + 4 + max_body_bytes`; checked arithmetic is required.

## 7. Quality

- The public suite must pass without changing it.
- Add focused unit tests for malformed boundaries and limit off-by-one cases.
- Formatting must pass `cargo fmt --check`.
- Explain unsupported browser behaviors and security assumptions in a short submission note.
