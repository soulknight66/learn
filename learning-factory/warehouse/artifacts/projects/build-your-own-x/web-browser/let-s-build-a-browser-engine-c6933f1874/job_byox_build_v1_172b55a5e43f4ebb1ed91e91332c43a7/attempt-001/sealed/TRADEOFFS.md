# Tradeoffs

The implementation chooses a small accepted language over compatibility. Real browsers recover from malformed URLs, HTTP, HTML, and CSS; this engine rejects ambiguity so behavior stays deterministic and teachable.

The DOM is owned and cloned into styled nodes. That is simple but memory-heavy. An indexed arena could share structure and make parent links easier, at the cost of lifetime and mutation complexity.

Layout treats every visible element as vertical flow even when its computed display is inline. It preserves the pipeline boundary but does not model inline formatting contexts. Text uses Unicode scalar counts, not grapheme clusters or font metrics.

Painting stores a full RGB canvas and fills only backgrounds. A display list would use less memory before rasterization and is a better production boundary. Omitting glyph rasterization avoids platform-dependent fonts and keeps tests deterministic.

The core accepts an injected transport rather than opening sockets. That leaves connection policy explicit and prevents deterministic tests from becoming network tests. It also means this crate alone is not an interactive browser.
