# Concepts

- write-ahead append logs and replay
- checksums versus framing
- atomic logical batches
- torn-tail recovery versus mid-log corruption
- fsync, rename, and directory durability
- compaction and write amplification
- lifecycle, locking, bounds, and observability
- differential/model-based testing

The task intentionally stops short of a B+ tree or LSM tree. Extensions ask the learner to
add indexing and segment rotation only after the durability contract is understood.
