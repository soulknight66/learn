# `http_boundary` answer

The prefix omits the delimiter itself when the header payload occupies exactly `max_header_bytes`. Search through at most `max_header_bytes + 4` bytes, using saturating or checked addition, then require the delimiter's starting index to be at most `max_header_bytes`.

```rust
let searchable = bytes.len().min(max_header_bytes.saturating_add(4));
let start = bytes[..searchable]
    .windows(4)
    .position(|w| w == b"\r\n\r\n")
    .ok_or(ParseError::MissingBoundary)?;
if start > max_header_bytes {
    return Err(ParseError::HeaderTooLarge);
}
```

The delimiter is framing and does not count toward header payload bytes. Tests should accept starts at `limit - 1` and `limit`, reject `limit + 1`, and include limits below four plus `usize::MAX` arithmetic behavior.
