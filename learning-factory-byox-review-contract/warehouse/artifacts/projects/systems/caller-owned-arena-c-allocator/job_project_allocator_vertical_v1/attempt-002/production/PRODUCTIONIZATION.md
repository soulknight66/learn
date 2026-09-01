# Productionization gap (NOT_PRODUCTION_READY)

This pack is useful for mechanisms, not deployment. A shippable allocator would need a clear
ABI/interposition story, concurrent ownership and race testing, OS-backed regions and return
policy, thread/fork/signal semantics, hardened or out-of-line metadata, corruption response,
double-free/use-after-free defenses, guard/quarantine options, telemetry without recursive
allocation, bounded latency goals, workload-specific size classes, NUMA/cache behavior,
exhaustive overflow review, cross-platform toolchains, long stress and differential tests,
and compatibility/performance evaluation against mature allocators. Sanitizer-clean smoke
tests and this benchmark do not resolve those gaps. Status remains `PARTIAL` and
`NOT_PRODUCTION_READY`; `productionized` is false.
