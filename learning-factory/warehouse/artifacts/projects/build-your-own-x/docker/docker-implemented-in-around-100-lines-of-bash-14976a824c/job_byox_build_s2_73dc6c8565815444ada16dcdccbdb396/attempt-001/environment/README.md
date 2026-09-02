# Environment

The controller needs Bash 4 or newer plus common POSIX/GNU userland tools: `cp`, `mkdir`, `mktemp`,
`mv`, `rm`, and `sort`. The Linux runner additionally needs GNU `unshare` from util-linux plus
`mount`, `hostname`, and `chroot`, and a kernel/site policy that permits an unprivileged user
namespace with subordinate namespace creation.

Run:

```bash
bash environment/check.sh
```

The check distinguishes command availability from a live user-namespace probe. A blocked probe is
an honest platform limitation, not a controller test failure. It does not modify Tinybox state.

`fixtures/rootfs` is intentionally not a bootable rootfs; it is only a regular-file tree for testing
copy semantics. A real run needs a rootfs containing the requested executable, its loader and shared
libraries (or a static executable), and writable mount points such as `/proc`.
