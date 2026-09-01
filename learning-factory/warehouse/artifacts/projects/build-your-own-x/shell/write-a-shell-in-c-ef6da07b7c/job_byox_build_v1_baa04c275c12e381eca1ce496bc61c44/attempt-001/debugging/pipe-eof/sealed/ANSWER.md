# Diagnosis and repair

The parent retains `channel[1]` while it waits for the reader. A pipe read returns zero only when its buffer is empty **and every descriptor referring to the write end is closed**. The writer child closes its copy, but the parent's copy still makes a writer exist. The reader therefore blocks, while the parent waits for the reader: a cycle.

The parent uses neither endpoint after both forks. It must close both before either wait. The reader already closes its write end, and the writer already closes its read end. The repaired ordering is shown in `fixed.c`.

In a shell pipeline, the same defect often comes from the shell retaining one pipe write end. Output can look correct for small input, then the final consumer hangs waiting for EOF. Waiting earlier or teaching the reader to time out only hides the ownership error.
