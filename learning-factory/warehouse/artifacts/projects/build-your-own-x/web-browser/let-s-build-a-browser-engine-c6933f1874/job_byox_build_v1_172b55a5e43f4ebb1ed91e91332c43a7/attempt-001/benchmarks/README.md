# Benchmark reveal

No benchmark was executed during generation, and this artifact makes no performance claim.

For a reproducible assessment, create deterministic fixtures at 1 KiB, 64 KiB, and the configured maximum for each parser. Record fixture SHA-256, Rust version, target triple, optimization profile, warm-up policy, sample count, and full command. Measure stages separately: HTTP framing, HTML tree construction, CSS parse/style, layout, and paint.

Useful counters are elapsed time, peak resident memory measured by a declared external tool, DOM nodes per second, and painted pixels per second. Include hostile near-limit inputs. Do not compare runs from different hosts or silently discard errors. Store raw observations before summaries, and do not label the project `BENCHMARKED` until an independent harness validates the method and results.
