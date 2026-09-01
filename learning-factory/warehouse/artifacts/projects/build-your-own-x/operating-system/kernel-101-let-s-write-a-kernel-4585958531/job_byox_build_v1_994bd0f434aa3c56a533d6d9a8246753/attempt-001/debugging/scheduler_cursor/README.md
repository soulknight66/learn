# Skipped process after block

With three ready processes, scheduling selects PIDs 1 then 2. PID 2 blocks. A buggy implementation
clears both `current_slot` and its scheduling cursor; the next schedule returns PID 1 instead of PID
3.

Tasks:

1. Reduce the symptom to the shortest state-transition trace.
2. Explain why “no process is running” does not mean “there is no scheduling history.”
3. State which field each transition should update.
