# Debugging exercise: output appears, then the pipeline hangs

The candidate function in `buggy_pipeline.c` runs a producer and consumer. Both children appear to reach the expected code, and the consumer prints all visible bytes, but it never exits and the parent waits forever.

Without running a second shell or changing the commands, identify the missing lifecycle operation. Draw the set of file-descriptor references immediately after both forks, and propose the smallest correct patch. Explain why closing only the read end in the parent is insufficient.
