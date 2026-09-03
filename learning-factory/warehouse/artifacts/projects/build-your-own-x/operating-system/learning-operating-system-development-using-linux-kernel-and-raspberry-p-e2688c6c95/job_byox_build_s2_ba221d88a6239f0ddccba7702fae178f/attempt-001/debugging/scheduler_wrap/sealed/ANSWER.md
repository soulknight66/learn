# Diagnosis

The modulus is seven, so every result is in `[0, 6]`; slot seven is unreachable
regardless of trace length. Populate only slot seven as ready and use any
non-running cursor state that initiates a schedule: the buggy loop reports no
candidate.

The index domain must equal the slot-array domain. Use
`(start + step) % MINIOS_MAX_PROCESSES`, with `step` spanning exactly one
through `MINIOS_MAX_PROCESSES`. The reference also treats a sole current
running process as a virtual ready candidate so preemption can select it again.
