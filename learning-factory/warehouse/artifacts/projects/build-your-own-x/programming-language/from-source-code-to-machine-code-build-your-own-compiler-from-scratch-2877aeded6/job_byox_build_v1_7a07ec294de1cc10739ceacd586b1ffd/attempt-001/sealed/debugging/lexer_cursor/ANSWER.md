# Diagnosis: lexer cursor

The first lookup fails when `index == len(source)`. After consuming a terminal CR, the second lookup
also fails. A lone CR followed by any non-LF happens not to fail, but the returned column is wrong: the
first unread character after a newline is at column 1, not the old column plus one.

Maintain `0 <= index <= len(source)` and only inspect when `index < len(source)`. Require the caller to
point at CR or LF. Consume CR, then consume one following LF if present; otherwise consume exactly the
LF. Increment line once and assign column 1. Cases should include terminal CR, terminal LF, CRLF,
CR-before-text, LF-before-text, and calls at the empty suffix (which should be rejected by contract or
left to the caller, never indexed).
