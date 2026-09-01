# Design questions

1. Which failures can a checksum detect, and which can it not prevent?
2. Why is an entire batch encoded in one record instead of several operation records?
3. What guarantee does `flush()` provide compared with `fsync()`?
4. Why must compaction fsync the replacement before rename, and the directory after rename?
5. Should readers block during compaction? What changes with immutable segments?
6. How would multiple processes coordinate writers without trusting process existence?
7. What metrics distinguish healthy append growth from a compaction incident?
