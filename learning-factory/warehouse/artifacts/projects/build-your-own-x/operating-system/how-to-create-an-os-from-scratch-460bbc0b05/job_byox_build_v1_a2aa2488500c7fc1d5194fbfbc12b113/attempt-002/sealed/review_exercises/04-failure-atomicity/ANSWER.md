# Failure-atomicity review findings

Scheduler operations finish argument, lookup, and transition checks before changing slots. Mapping
finds a free frame before marking it used, then clears it before publishing the page-table entry.
Filesystem creation validates and detects duplicates before occupying a slot; writes validate the whole
destination interval before copying.

The API does not promise rollback after hardware failure because this model has no hardware I/O. Any
future persistent backend needs an explicit crash-consistency contract rather than inheriting the RAM
model's in-process atomicity claim.
