# Debugging exercises

These prompts are maintained for staged instructor use. Solution material is stored separately in each exercise's sealed area.

## Process-state ghost

Observed sequence:

```text
create -> pid 1
schedule -> pid 1
block(1) -> OK
schedule -> NOT_FOUND
pebble_check -> "running slot mismatch"
```

The process record is `BLOCKED`, but `current_slot` still equals zero immediately after `block`. Identify the violated invariant, the transition that owns the repair, and two regression assertions. Avoid “fixing” the invariant checker.

## Copy-on-write alias

A parent maps page 0 read/write, stores `0x21`, and forks. Both mappings name frame 0, whose reference count is 2. The child stores `0x44`; afterward the parent reads `0x44` too, and the reference count remains 2. Explain which pre-write phases are missing, what capacity must be reserved before a cross-page store, and which flags/references should result after a successful one-page split.
