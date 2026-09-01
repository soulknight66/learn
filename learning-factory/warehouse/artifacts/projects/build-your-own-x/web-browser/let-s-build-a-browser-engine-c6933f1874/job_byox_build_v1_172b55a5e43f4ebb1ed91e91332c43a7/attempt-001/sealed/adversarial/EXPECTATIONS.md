# Adversarial expectations

Malformed or ambiguous URL/HTTP/HTML/CSS inputs must return their stage-specific `BrowserError` without panicking. Exact byte/node/depth limits are accepted; one over is rejected. Unsupported transfer coding is rejected even when a Content-Length also appears. Invalid supported CSS values are rejected even on an unmatched selector because stylesheet validation is global.

Layout rejects a zero viewport, arithmetic overflow, and decorations wider than the available box. Long words are split so a one-column viewport always makes progress. Paint clips all rectangles, and later child fills overwrite parent pixels. A transport is called once per `load` and its oversized result is rejected independently of its claimed compliance.
