# Single selector event loop

One thread owns nonblocking sockets and explicit parser/output state. It caps live connection
objects and expires inactive clients. This reduces idle-thread cost, but `CounterApp.handle`
runs on the loop: any future blocking database or DNS call would create head-of-line blocking.
A production design would separate nonblocking I/O ownership from bounded application work.
