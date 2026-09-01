# Debugging log

- Hypothesis: one integer reference count would obscure which mapping leaked.
- Experiment: represent mapping owners as `(pid, vpn)` pairs and assert behavior after unlink.
- Observation: a named frame needs a separate lifetime edge even when it has no mappings.
- Resolution: reclaim only when both mapping-owner and name-owner sets are empty.

This is a concise reproducible account, not private chain-of-thought.
