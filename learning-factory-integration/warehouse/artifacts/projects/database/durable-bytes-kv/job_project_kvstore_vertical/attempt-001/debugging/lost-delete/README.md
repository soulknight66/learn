# Debugging challenge: the returning key

A deleted key is absent until the service restarts, then unexpectedly returns. Reproduce with
`python3 test_bug.py`. Investigate the on-disk records and replay path. Do not inspect `sealed/`
until you have written a hypothesis, an experiment, and a regression test.
