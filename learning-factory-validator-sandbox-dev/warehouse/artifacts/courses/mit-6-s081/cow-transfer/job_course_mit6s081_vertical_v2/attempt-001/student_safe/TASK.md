# Transfer task: named shared pages with COW coexistence

Build a thread-safe semantic model that lets unrelated processes map a named physical page.
Ordinary private writable mappings must become copy-on-write across `fork`; named shared
mappings must remain genuinely shared across unrelated processes and across `fork`.

Implement the exact `SharedPageSystem` contract in `API.md`: process creation, private allocation,
named-segment creation, mapping, reading, writing, fork, unmap, exec, exit, unlink, and stats.

Required invariants:

- every page-table entry contributes exactly one mapping reference;
- a private COW write clones only when another mapping still refers to the frame;
- a named page is not reclaimed while named or mapped;
- unlink removes the name but existing mappings remain valid;
- exec/exit release every old mapping exactly once;
- duplicate processes/mappings and out-of-range accesses fail explicitly;
- all compound state changes are serialized so concurrent calls preserve invariants.

This differs materially from merely implementing canonical COW fork: two unrelated processes
can intentionally share writable state, so COW and shared mappings need distinct semantics.
