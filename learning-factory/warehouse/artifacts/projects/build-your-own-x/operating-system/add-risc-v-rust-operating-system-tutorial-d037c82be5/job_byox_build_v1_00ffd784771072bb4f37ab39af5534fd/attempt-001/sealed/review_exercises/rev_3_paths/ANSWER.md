# REV-3 answer

Normalization contradicts R5.2: those spellings are required errors. Accepting
them makes several input strings name the same object, complicates audit logs,
authorization boundaries, cache keys, and error precedence. Resolving `..`
also introduces root-escape and symlink-style policy questions absent from the
model.

Reject-only parsing can finish before inode traversal and mutation. Every
published name then has one canonical absolute spelling, parent splitting is
unambiguous, and a lexical error trivially preserves filesystem state.
