# Diagnosis

The existence check and `mkdir -p` are separate operations. Both processes can
observe absence, both cross the gate, and `mkdir -p` reports success to both.
The two redirections then race to replace the same metadata.

Use plain `mkdir` as the atomic name claim. It succeeds for one process and
fails for the other. Only the winner writes metadata. If later initialization
fails, the winner must remove only the directory it claimed; the losing
process must never clean up shared state.

`fixed.sh` keeps the gate before the atomic claim so the same test exercises
the repair.

