# Investigation

Confirm the log contains both set and delete envelopes, compare state before and after reopen,
then trace the decoded operation list into `_apply`. The smallest regression is one set, one
delete, close, reopen, and get. Avoid deleting the log or special-casing the test key.
