# Bounded thread per connection

Admission uses a semaphore; each admitted socket receives a dedicated short-lived thread.
Shutdown snapshots sockets/threads under a lock, closes sockets to unblock reads, then joins.
The model is locally readable and accommodates blocking handlers, but thread churn and stack
memory scale with the connection cap.
