# Exercise: the rootfs prefix escape

A developer validates an archive destination with this condition:

```text
destination = absolute(normalize(join(rootfs, member_name)))
accept when string(destination).starts_with(string(absolute(rootfs)))
```

During a test, rootfs is `/srv/run/root`, and a member causes `/srv/run/root-backup/changed` to be written. In a second test, a pre-existing directory inside rootfs is swapped for a symlink between validation and open.

Questions:

1. Give the member shape that exploits the string-prefix check.
2. Explain why resolving a path once does not prevent the symlink race.
3. Propose a repair suitable for this educational project and a stronger production repair.
