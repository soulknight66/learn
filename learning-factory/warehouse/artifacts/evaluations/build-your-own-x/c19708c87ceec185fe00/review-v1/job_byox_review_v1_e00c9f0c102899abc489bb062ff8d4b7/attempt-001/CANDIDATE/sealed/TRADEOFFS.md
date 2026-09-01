# Architecture tradeoffs

The worker pool reuses a bounded number of threads and makes blocking handlers tolerable, but
slow clients occupy workers unless reads time out. Per-connection threads make ownership and
stack traces direct, but thread creation and memory grow to the admission bound. The selector
loop keeps one explicit state object per connection and avoids a thread per idle socket, but
one blocking application call stalls every connection and lifecycle code becomes less linear.

All three share parser and application semantics so tests and benchmark workloads compare the
concurrency mechanisms rather than three accidental APIs. One bounded smoke run cannot rank
them generally; profile under representative handlers, connection reuse, slow clients, and
saturation before choosing.
