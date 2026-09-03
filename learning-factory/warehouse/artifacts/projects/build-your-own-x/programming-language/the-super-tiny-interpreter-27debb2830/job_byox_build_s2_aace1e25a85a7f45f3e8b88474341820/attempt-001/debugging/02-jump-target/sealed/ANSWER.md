# Instructor answer

The false edge must reach an instruction that pushes `nil`; it cannot jump directly to `HALT`.
`JUMP_IF_FALSE` consumes the condition on both outcomes. The true block leaves its statement value,
then an unconditional jump skips the false-side `nil`. Patch the conditional jump to the `nil`
instruction and the unconditional jump to the common continuation. Both incoming edges then have
stack depth one.
