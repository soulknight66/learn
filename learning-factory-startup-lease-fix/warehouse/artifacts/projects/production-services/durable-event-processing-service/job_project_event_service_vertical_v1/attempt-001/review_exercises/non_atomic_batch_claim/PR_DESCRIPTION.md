# PR: claim without holding the writer lock during selection

Moves the initial SELECT outside a write transaction so many workers can discover jobs in
parallel. Database exceptions return an empty result so transient contention does not wake the
worker supervisor. The API remains `message_id | None` and no migration is required.
