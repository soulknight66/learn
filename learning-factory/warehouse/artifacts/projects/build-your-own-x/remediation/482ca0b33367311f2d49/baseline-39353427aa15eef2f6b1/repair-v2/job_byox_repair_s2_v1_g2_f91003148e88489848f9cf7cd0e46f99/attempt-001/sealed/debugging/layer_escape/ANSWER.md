# Evaluator answer: sibling-prefix escape

If `root` is `/tmp/case/root`, the resolved sibling `/tmp/case/root-backup/report` begins with the same
characters, so `startswith` reports containment even though the component after `/tmp/case` differs.
Adding a separator manually is still platform-fragile and does not address links.

Normalize the untrusted archive name as strict POSIX components, reject absolute paths and every
`..`, join those components to a resolved root, reject any existing link along the destination path,
resolve the candidate, and require `candidate.is_relative_to(root)`. The regression should create
both sibling directories under one temporary parent and assert that the sibling is never selected.
A separate temporary link-parent regression demonstrates that lexical components alone are not
enough.
