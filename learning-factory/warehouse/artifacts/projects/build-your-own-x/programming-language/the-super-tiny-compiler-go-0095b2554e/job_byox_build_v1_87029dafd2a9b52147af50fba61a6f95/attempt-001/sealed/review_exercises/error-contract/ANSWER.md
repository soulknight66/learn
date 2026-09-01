# Error-contract review answer

Formatting with `%v` destroys the wrapped error chain, so `errors.As` can no longer recover `*pebble.Error`. It also replaces the required stage error with generic text and can invite unstable message-only assertions. `Build` should return the first scanner, parser, analyzer, or compiler error unchanged. If contextual wrapping were allowed elsewhere, `%w` would preserve the chain, but this contract explicitly requires unchanged propagation.
