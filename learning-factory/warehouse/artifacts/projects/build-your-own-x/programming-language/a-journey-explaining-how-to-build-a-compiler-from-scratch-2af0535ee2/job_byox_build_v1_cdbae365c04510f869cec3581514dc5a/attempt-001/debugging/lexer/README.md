# Exercise: the keyword-prefix lexer

The fragment in buggy_keyword.c sometimes classifies identifiers as keywords and may read beyond the
token slice. Identify inputs that expose both issues, explain why a null terminator cannot be assumed,
and replace the helper with a bounded exact-match implementation.
