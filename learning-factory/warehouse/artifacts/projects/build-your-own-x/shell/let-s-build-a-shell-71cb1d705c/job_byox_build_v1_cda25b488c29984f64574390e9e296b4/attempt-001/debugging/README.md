# Debugging labs

These small programs isolate failure modes that also occur in a shell. Work on
one lab at a time; each is independent of the `minish` starter.

| Lab | Symptom | Primary evidence |
| --- | --- | --- |
| [`eof_hang`](eof_hang/) | output appears, but the process never exits | bounded run and descriptor trace |
| [`wait_race`](wait_race/) | a foreground result is attributed to the wrong child | printed PIDs and wait status |
| [`token_vector`](token_vector/) | a longer token list corrupts the heap | AddressSanitizer report |

For every lab:

1. reproduce the symptom with the documented command;
2. state an invariant that the program violates;
3. identify the smallest responsible code region;
4. make one focused repair;
5. rerun the reproducer and one boundary case.

Do not merely remove the input that triggers a failure. Shell bugs often hide
under favorable scheduling or small buffers, so the repair must restore the
underlying ownership or state invariant.
