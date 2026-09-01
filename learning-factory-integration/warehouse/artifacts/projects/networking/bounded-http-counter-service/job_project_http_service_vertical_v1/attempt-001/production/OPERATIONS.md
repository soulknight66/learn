# Teaching operations runbook

## Signals

Probe `/healthz` only for process/event-loop reachability. Scrape `/metrics` for request and
contained-application-error counts, understanding they reset on restart. Capture queue/admission
metrics as the first extension. Use benchmark JSON only with its environment and parameters.

## Slow or unavailable service

Check worker/connection saturation, partial-request timeouts, handler latency, and error rate.
Preserve raw requests with secrets removed. Shed load rather than raising limits blindly. A 503
from admission is intentional overload behavior; a timeout while the queue is unbounded would
be a design defect.

## Shutdown

Stop admission, close the listener, bound connection drain, unblock readers, and join owners.
This teaching implementation closes accepted sockets to unblock readers, then joins all owners
against one configured `shutdown_timeout`; it does not guarantee completion of in-flight work.
A real service must publish its termination grace period and retry safety.
