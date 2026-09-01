# Alternative designs

- An arena DOM with numeric node IDs avoids cloning and supports parent links. It makes APIs less approachable and requires explicit lifetime/ownership policy.
- A tokenizer followed by a tree builder gives better error spans and incremental input handling. The recursive parser is smaller for this intentionally nested subset.
- A display-list renderer decouples geometry from raster targets and naturally supports inspection, caching, and multiple backends. The RGB canvas makes painting outcomes immediate in tests.
- A typestate pipeline could represent `FramedResponse`, `DecodedHtml`, `Document`, `StyledDocument`, and `LayoutTree` as consuming transitions. This provides stronger compile-time ordering at the cost of more public types.
- An async connector is appropriate for concurrent browsing, but introduces an executor, cancellation semantics, and substantially more dependency surface. It does not change the need for strict address and byte policy.
