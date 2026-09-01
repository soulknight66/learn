# Answer: the rootfs prefix escape

`../root-backup/changed` normalizes to `/srv/run/root-backup/changed`, whose text begins with `/srv/run/root` even though it is a sibling. Component-aware containment (for example, a relative-path check) fixes the prefix confusion, but a check followed by a separate pathname open still has a time-of-check/time-of-use race.

For the challenge, reject absolute names, `..`, backslashes, special files, and all links; walk existing destination components with `lstat`; prevalidate every member; and assume the owned rootfs is not concurrently mutated. Deterministic tests should include the sibling-prefix case and existing parent/leaf symlinks.

For hostile concurrent mutation, operate descriptor-relatively and use `openat2`-style resolution constraints such as beneath-root and no-symlink rules. Create each path with no-follow flags, keep trusted directory descriptors open, and apply the layer to a private snapshot before atomic publication.
