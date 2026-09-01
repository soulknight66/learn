# Regression test

`debugging/lost-delete/test_bug.py` is the authoritative minimal regression. From the archive
root, it fails with `KVSTORE_IMPL=buggy` and passes with `KVSTORE_IMPL=reference` (or the
instrumented teaching variant selected by `KVSTORE_IMPL=production`). Apply the repair from
the archive root with `patch -p1 < debugging/lost-delete/sealed/patch.diff`, then rerun the
buggy target to verify the patch.
