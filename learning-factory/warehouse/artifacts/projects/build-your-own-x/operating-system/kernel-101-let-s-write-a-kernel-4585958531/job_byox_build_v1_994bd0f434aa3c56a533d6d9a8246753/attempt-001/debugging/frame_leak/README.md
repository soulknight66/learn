# Frame leak on duplicate map

A candidate implementation allocates a frame, then scans for a duplicate virtual page. Mapping the
same address twice correctly returns `-1`, but `tk_frame_available` decreases after the second call.

Tasks:

1. Write a three-assertion reproducer.
2. Identify which state changed during an operation required to be atomic.
3. Propose an ordering or rollback strategy and explain why it also works when the mapping table is
   full.
