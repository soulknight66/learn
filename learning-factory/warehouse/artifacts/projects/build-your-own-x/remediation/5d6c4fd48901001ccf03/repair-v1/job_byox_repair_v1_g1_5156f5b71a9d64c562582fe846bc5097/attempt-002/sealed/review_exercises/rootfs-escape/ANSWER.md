# Rootfs-escape review answer

The textual-prefix check is unsound. A root `/srv/root` is a prefix of `/srv/root-other`; `..` can be
normalized before the comparison; and a path lexically beneath the root can contain a symbolic link
whose target is outside it. Even a `commonpath` or `resolve` check followed by later pathname use has a
check-to-use race when an attacker can mutate the tree. The snippet also accepts directories, special
files, and non-executable regular files.

For the intentionally strict educational policy, validate the command as an in-container path, reject
empty and traversal components, and perform `PATH` search only over validated in-container directory
entries. Anchor lookup to a canonical rootfs. Inspect every existing component with no-follow
semantics and reject every symlink, even one that currently points within the tree. Require the final
object to be a regular executable file and return its normalized host-side path beneath the rootfs;
the backend can then derive the absolute guest path sent to the helper. Tests must cover prefix
siblings, absolute and relative traversal, links in the root,
directory, and final-command positions, broken and looping links, non-regular objects, permission
bits, and rootfs mutation.

This rule is simple and deliberately rejects common benign link layouts. It still cannot make
pathname inspection race-free. Production code should keep the root directory open, traverse using
descriptor-relative operations or `openat2` with appropriate no-escape/no-symlink resolution flags,
pin objects through launch, and define interpreter handling. Rootfs ownership must prevent hostile
replacement. A chroot after a host-side check is not by itself a complete security boundary.
