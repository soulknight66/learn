# State-corruption analysis

The parse error is evidence that the persistence boundary failed; it is not evidence that the target
did or did not run. Preserve the damaged file and logs before attempting recovery. Do not manufacture
`EXITED` from a process message or reuse the identifier automatically.

A correct update builds and validates the complete next record in memory from an allowed predecessor,
increments the predecessor revision exactly once, and sets the store-generated update timestamp. The
reference holds an exclusive `flock` on a per-ID lock opened with no-follow semantics and verified as
regular. It writes JSON to a uniquely named, exclusively created, no-follow temporary regular file in
the same directory, `fsync`s that file, publishes with `os.replace`, and `fsync`s the directory.
Cleanup of an unpublished temporary file is safe; rewriting the visible record in place is not.

Atomic rename alone would not serialize two writers; the reference's lock is therefore held across
read, predecessor validation, write, and replace. Two local processes cannot both accept revision N
under that protocol. A transactional compare-and-swap remains a stronger choice for cross-record or
distributed coordination, and `flock` semantics must be validated for the deployed filesystem.

The diagnosis should inject a failure after temporary creation, after writing, after file `fsync`,
after replacement, and after directory `fsync`. At every point, a fresh reader must see either the
old complete record or the new complete record, never a partial document. A second test races two
legal transitions and requires at most one winner. Tests must also show that `CREATED -> EXITED`, any
transition out of a terminal state, a skipped revision, and malformed on-disk JSON fail closed.

Initial creation follows a separate no-overwrite path. It exclusively creates a secure temporary
regular file in the state directory, writes the complete record, `fsync`s it, then atomically creates
the absent public name as a hard link to that inode. It unlinks the temporary name and `fsync`s the
directory. If the public name already exists, linking fails without replacing it. A crash may leave
an unpublished temporary name, but cannot expose its partial bytes as the record; a crash after the
link may leave a complete record plus scratch name.

Because the reference implements these steps, a reproducible partial visible document points to
external modification, an unsupported filesystem guarantee, or a bug and must not be papered over.
A failure after link/replacement but before directory-sync confirmation is a commit-ambiguity case:
the operation raises `StateCommitUncertain` with the exact proposal rather than reporting an
ordinary failed mutation. Pass that value to `StateStore.recover` for the same directory; it locks,
requires the visible complete record to equal the proposal, retries the directory sync, and returns
the record. Missing, different, or superseded evidence is not rewritten. After controller restart,
the intent must come from durable controller evidence because the in-memory exception is gone; do
not blindly replay `create` or `transition`.
