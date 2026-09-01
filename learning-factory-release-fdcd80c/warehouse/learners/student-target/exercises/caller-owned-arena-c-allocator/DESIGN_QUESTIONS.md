# Design questions

1. Which metadata is needed to coalesce in O(1), and what overwrite attacks does it expose?
2. How do you prove every physical block covers the arena exactly once?
3. When does a split remainder become too small to remain useful?
4. Which additions and rounding operations can overflow before an arena bound check?
5. What is the failure-atomic sequence for a moving resize?
6. How will a segregated implementation update bins when a block changes size class?
7. Which workload could make first-fit outperform best-fit, or vice versa?
8. Why does a throughput number without raw workload/environment data teach little?
9. What synchronization and ownership model would a thread-safe extension require?
10. Which production allocator defenses are intentionally absent here?
