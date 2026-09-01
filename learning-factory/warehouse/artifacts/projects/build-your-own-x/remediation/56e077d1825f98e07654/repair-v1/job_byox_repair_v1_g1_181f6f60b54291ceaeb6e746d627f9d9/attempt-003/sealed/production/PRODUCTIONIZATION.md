# Productionization gap assessment

No productionization was performed or claimed.

Before deployment-oriented use, replace the host callback abstraction with defined exception entry
and userspace ABI; configure MMU permissions, ASIDs, TLB maintenance, cache attributes, and W^X;
introduce interrupt-safe synchronization and SMP memory ordering; validate all user pointers through
fault-aware copies; add resource accounting and denial-of-service controls; use a persistent storage
protocol with recovery; and implement secure boot, signed update, observability, fuzzing, long-running
stress, hardware testing, and threat review.

The ARM demonstration also needs linker-map review, stack guards, exception vectors, timer/GIC setup,
fault diagnostics, toolchain pinning, reproducible builds, and tests on both emulator and target
silicon. None of those claims can be inferred from the portable test suite.
