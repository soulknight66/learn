# Design questions

Write down your answers before looking at sealed material. More than one design can work, but your
choices must remain consistent with the fixed API contract.

1. Which facts are canonical for frame ownership, and how will you update both views atomically in a
   single-threaded implementation?
2. Why does the scheduler retain its cursor after the current process blocks or exits?
3. In what order should `cairn_map` check duplicate virtual pages, busy frames, and a full mapping
   table? Which observable status follows from the contract?
4. How will every function preserve output arguments and kernel bytes on failure without copying the
   whole kernel object?
5. What bounded name-validation loop remains safe when no NUL byte occurs in `CAIRN_NAME_CAP` bytes?
6. Which process fields must be cleared when an exited table slot is reused?
7. How can `cairn_validate` inspect a corrupt descriptor without indexing outside the inode array?
8. Is rejecting unlink of an open file simpler or more complex than Unix's deferred deletion model?
9. What additional synchronization would be required if timer interrupts could mutate scheduler state
   concurrently with system calls?
10. Which properties can host tests establish, and which require an emulator or real machine?
