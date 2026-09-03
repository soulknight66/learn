# Debugging exercises

Two small failure investigations accompany the challenge:

- `scheduler_wrap/` examines a wraparound bound that silently omits a slot.
- `fs_partial_write/` examines mutation before full-range validation.

Each prompt is outside its local `sealed/` subdirectory. Its diagnosis and
repair notes live only in that exercise's own sealed directory.
