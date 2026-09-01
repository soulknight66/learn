# Debugging challenge: the returning key

A deleted key is absent until the service restarts, then unexpectedly returns. Reproduce with
`KVSTORE_IMPL=buggy python3 debugging/lost-delete/test_bug.py` from the archive root (a failing
test is the expected reproduction). Investigate the on-disk records and replay path. Do not
inspect `sealed/` until you have written a hypothesis, an experiment, and a regression test.
