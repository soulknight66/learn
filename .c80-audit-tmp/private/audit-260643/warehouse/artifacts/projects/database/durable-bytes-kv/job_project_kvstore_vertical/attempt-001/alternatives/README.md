# Architecture alternatives

`memory.py` establishes the lowest-complexity semantics but has no recovery. `sqlite_store.py`
delegates transactions, locking, indexing, and recovery to SQLite. Compare both with the
append-log implementations using the same set/get/delete workload; do not infer superiority
from a single smoke run. Useful follow-ups include a segmented log and an ordered B+ tree.
