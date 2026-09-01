# Reference design

Each newline-delimited envelope contains a canonical JSON body and CRC32. The body contains
one logical batch, so replay never observes a prefix of a validated batch. The index is an
in-memory dictionary reconstructed at startup. A single re-entrant lock serializes appends and
index changes. Compaction emits one snapshot batch to a sibling temporary file, fsyncs it,
atomically renames it, and fsyncs the directory where supported.

CRC32 detects accidental corruption but is not authentication. A final unterminated line is
ignored as a torn append; malformed complete lines fail closed. This distinction is tested.
