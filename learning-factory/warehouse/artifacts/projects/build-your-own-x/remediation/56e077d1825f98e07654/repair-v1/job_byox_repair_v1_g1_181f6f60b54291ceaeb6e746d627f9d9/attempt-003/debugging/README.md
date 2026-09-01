# Debugging exercise: the task that wakes late

Consider a scheduler that increments `now`, selects a task, and only then scans blocked tasks for a
deadline equal to the old time. A sole task sleeps at time 4 with delay 2 but resumes at time 7.

Produce a three-column trace (`tick start`, `wake scan`, `selected PID`) and identify which event order
violates the contract. Propose the smallest state-machine correction and add a regression where all
tasks are blocked. Do not alter sleep deadlines to compensate for the scheduler ordering.

The instructor diagnosis is stored in the matching sealed debugging area.
