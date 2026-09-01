# Diagnosis

The final call expands four variables without quotes. `$*` also joins all
remaining arguments into one intermediate string. The shell then performs
field splitting and pathname expansion, so quoting at the caller cannot
survive this second expansion. Empty arguments disappear.

Keep the incoming argument vector as an array: after shifting the three fixed
parameters, invoke the helper with each fixed value quoted and expand the
remaining positional parameters as `"$@"`. No re-parsing step is needed.

`fixed.sh` is one complete repair. Its final command naturally propagates the
helper's status.

