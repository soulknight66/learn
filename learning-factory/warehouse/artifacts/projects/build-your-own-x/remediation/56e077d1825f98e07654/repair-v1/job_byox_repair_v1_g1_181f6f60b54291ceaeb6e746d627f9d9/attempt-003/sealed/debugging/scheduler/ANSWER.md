# Answer: the task that wakes late

The wake scan must occur at the start of the interval, before selection, using the current `now`.
Then a deadline of 6 is eligible during the tick starting at 6. Incrementing first shifts the time
base; selecting before waking adds another lost opportunity when no ready task is found.

The regression should observe callback times 4 and 6 (or, from a fresh kernel, 0 and 2) while counting
the intervening blocked-only tick as successful idle progress.
