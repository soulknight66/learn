# Diagnosis

In Bash, a script with no explicit `exit` returns the status of its last
command. The final successful `printf` therefore hides the helper's status.

Capture `$?` immediately after the helper returns, perform cleanup, then exit
with the captured value. The example treats failure to restore lifecycle state
as an internal error only when the child itself succeeded; otherwise it keeps
the more useful child failure. A full runtime should also arrange bounded
signal cleanup and avoid allowing an old process to erase a newer run record.

