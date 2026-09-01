# Debugging reveal: boundary search

Exercise ID: `http_boundary`.

A response whose header is exactly the configured maximum is being rejected. The implementation searches only this prefix:

```rust
let prefix = &bytes[..bytes.len().min(max_header_bytes)];
let delimiter = prefix.windows(4).position(|w| w == b"\r\n\r\n");
```

Tasks:

1. Write three tests with the delimiter beginning before, at, and after the limit.
2. Explain whether the four delimiter bytes count as header bytes.
3. Repair the search without permitting an oversized header and without slicing past the input.
4. Identify the arithmetic edge case when the configured limit is near `usize::MAX`.

The answer for validators is isolated under `sealed/debugging/http_boundary/sealed/`.
