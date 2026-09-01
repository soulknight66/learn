# Alternative designs

The reference deliberately chooses a copied rootfs, SQLite lifecycle database, and util-linux subprocess backend. Reasonable alternative tracks include:

- an overlayfs snapshotter with a mount journal and restart reconciliation;
- a content-addressed multi-layer image store keyed by verified digests;
- direct `clone3`, mount, pivot-root, and UID/GID-map syscalls through a narrow native helper;
- a long-running supervisor that owns container processes and receives requests over a Unix socket;
- rootless OCI bundle generation followed by an established OCI runtime.

Each alternative expands the trust boundary. It should preserve the same deterministic state graph, expected-state claims, bounded subprocess policy, and explicit evidence labels.
