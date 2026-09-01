# Preparation: two kinds of writable sharing

A page-table mapping and a physical frame have different lifetimes. Unmapping removes one
mapping; it does not necessarily free the frame because another process or a persistent name
may still own it. Track every ownership edge explicitly enough that teardown can remove it once.

After `fork`, a private writable mapping initially points at the same bytes in both processes,
but neither process may overwrite those shared bytes. The first writer receives a private copy
only when another mapping still exists. In contrast, a named shared mapping is intentionally
writable by multiple unrelated processes, so a write must remain visible through every mapping.

Before coding, trace these events on paper: private allocate → fork → child write → parent exit;
and name create → two maps → unlink → first unmap → second unmap. At each arrow list the process
mappings, name owners, and frames that remain live.

Checkpoint questions:

1. Why is one undifferentiated reference count harder to debug than reciprocal owner sets?
2. When can a COW writer safely reuse its existing frame instead of copying?
3. Why must unlink preserve existing mappings?
4. Which multi-step changes need the same lock to avoid a lost lifetime edge?
