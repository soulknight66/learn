# Answer: skipped process after block

The minimal trace is spawn 1/2/3, schedule twice, block 2, then schedule. Blocking should clear
`current_slot` because no process owns the CPU, but retain `cursor == slot(2)` because 2 was most
recently selected. The next cyclic scan therefore begins after slot 2 and finds PID 3.

Initialization sets the cursor just before slot zero. Only successful selection updates the cursor;
block and exit update current ownership and state without erasing selection history.
