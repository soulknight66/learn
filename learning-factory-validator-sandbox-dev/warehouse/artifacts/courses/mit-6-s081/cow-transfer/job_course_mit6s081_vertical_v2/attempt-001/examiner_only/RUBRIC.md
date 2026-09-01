# Examiner rubric (not student-visible)

- 30%: private fork mappings isolate on first write without unnecessary eager copies.
- 25%: unrelated and forked processes retain intentional named sharing.
- 25%: unmap, unlink, exec, and exit preserve exact frame lifetime.
- 15%: concurrent operations leave coherent data and reference accounting.
- 5%: invalid operations fail explicitly and the implementation remains readable.

Mandatory failures override the numeric score: leaked examiner material, hidden-test mutation,
unhandled lifecycle corruption, or a claimed pass unsupported by real command evidence.
