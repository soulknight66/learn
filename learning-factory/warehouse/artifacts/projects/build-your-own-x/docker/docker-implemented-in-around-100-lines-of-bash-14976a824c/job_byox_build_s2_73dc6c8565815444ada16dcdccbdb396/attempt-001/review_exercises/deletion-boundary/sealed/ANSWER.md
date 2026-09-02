# Sealed review findings

The name is not validated, so absolute/traversal components can escape the intended directory. The
unquoted target undergoes splitting and glob expansion. An empty or unset state root broadens scope.
The existence check follows symlinks and does not prove the container directory itself is a real
directory. Status content and permitted transition are ignored. Another run/delete can race between
check and removal. Failures have no diagnostic, and partial removal is not considered.

A defensible small implementation first rejects empty or `/` state, canonicalizes and privately owns
the state layout, validates the complete name grammar, constructs exactly `containers_dir/name`,
checks that exact prefix/equality invariant, atomically claims a per-name lock, rechecks a non-symlink
container and an allowed `CREATED` or `EXITED` status as inert data, and finally invokes
`rm -rf -- "$target"`. It releases the lock on every exit.

Tests should use traversal, absolute, whitespace, glob, and empty names; symlink both the container
and its status; attempt delete while a controlled run is blocked; race two deletes; and place a
sentinel immediately outside `containers/` that must remain byte-for-byte unchanged.
