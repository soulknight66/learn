# Shared alternative contract

Every implementation exports the same seven symbols from `http_service` and accepts the same
`ServiceConfig`. `start()` binds an ephemeral loopback address when port is zero. `address`
becomes available after start. `close()` performs bounded shutdown. All variants use the same
parser, response framing, counter application, public tests, withheld tests, adversarial input,
and benchmark workload. Only connection scheduling/lifecycle architecture differs.
