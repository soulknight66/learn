# Prerequisites

- Translate a virtual page number through a per-process mapping.
- Explain why a writable fork mapping cannot stay writable in both processes.
- Distinguish a mapping reference from ownership of a physical frame.
- Understand fork, page-fault handling, unmap, exec, and exit lifecycle events.
- Use a lock to make a multi-step reference-count update atomic.

Suggested remediation is to study the public xv6 book and relevant MIT 6.S081 schedule
entries linked by `PROVENANCE.json`; no course solution is bundled.
