# Scheduler cursor resolution

The cursor is scheduling history, not merely a pointer to a currently running process. Clearing it
when slot five blocks makes the next scan begin at slot zero. Preserve slot five as the cursor while
changing only its process state; the next cyclic scan then begins at slot six. A regression should
place ready processes on both sides of the cursor and assert that slot six wins first.
