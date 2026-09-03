# Transactional output review

Writing zero at function entry violates the rule that outputs remain unchanged on every error,
including missing pages, permission failures, invalid write flags, and corrupt ownership. Compute the
candidate physical address in a local variable, complete all validation, and assign the caller's
output only on `CAIRN_OK`. Test each error with a distinct sentinel so an accidental zero is visible.
