# Reference tradeoffs

| Decision | Benefit | Cost / rejected capability |
|---|---|---|
| Cooperative round robin | Small, inspectable context boundary; deterministic tests | One non-yielding task can starve the kernel |
| Fixed tables | No allocator dependency; bounded work and storage | Hard capacity limits and linear lookup |
| Monotonic PID with terminal exhaustion | No stale PID aliases after slot reuse | Very long-lived systems eventually refuse creation |
| Separate policy and ARM runtime | Host edge-case tests do not emulate registers | Correctness spans two coupled representations |
| Inline RAMFS bytes | Simple lifetime and deletion scrubbing | File size is capped and storage cannot persist |
| Section identity map at boot | Safe MMU transition with little code | Broad supervisor access; no hardware process isolation |
| Software 4 KiB mapping model | Teaches ownership and permissions portably | It is not installed as an ARM L2 page table |
| Domain manager during bring-up | Avoids accidental AP fault while enabling MMU | Hardware permission enforcement is deferred |
| Polling UART | No interrupt-controller dependency | CPU time is wasted while the transmitter is full |
| Semihosted exit in demo | Deterministic automated QEMU completion | That final exit mechanism is emulator-specific |

Alternatives are cataloged in `sealed/alternatives/README.md`. None changes the
core claim: this is a teaching reference, not a production kernel architecture.
