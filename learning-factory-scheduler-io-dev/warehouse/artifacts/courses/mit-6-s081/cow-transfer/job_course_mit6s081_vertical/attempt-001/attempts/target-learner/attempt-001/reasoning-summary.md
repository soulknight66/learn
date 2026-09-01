# Reasoning summary

The attempt separates intentionally shared mappings from private mappings before implementing
fork. It models both names and page tables as owners that can keep a frame alive. All mutations
occur under one re-entrant lock so lifecycle operations can call common release logic safely.
