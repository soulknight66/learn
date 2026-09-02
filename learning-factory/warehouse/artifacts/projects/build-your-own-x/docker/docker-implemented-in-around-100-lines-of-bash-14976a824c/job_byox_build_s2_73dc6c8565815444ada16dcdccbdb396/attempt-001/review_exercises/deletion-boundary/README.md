# Review: deletion boundary

Review this proposed implementation:

```bash
delete_container() {
    target="$TINYBOX_STATE_DIR/containers/$1"
    [ -e "$target/status" ] || return 1
    rm -rf $target
}
```

List correctness, safety, concurrency, and diagnosability problems. Describe behavioral tests that
would detect them. Your replacement must state the invariants that justify recursive deletion; do
not merely add quotes and call it complete.
