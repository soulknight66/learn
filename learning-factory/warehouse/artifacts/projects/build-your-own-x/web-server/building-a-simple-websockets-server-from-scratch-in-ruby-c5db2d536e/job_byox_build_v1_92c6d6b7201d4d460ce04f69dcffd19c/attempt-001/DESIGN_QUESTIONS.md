# Design questions

Write down your answers before reading any evaluator feedback.

1. How will the HTTP reader preserve bytes when a client sends the first frame
   in the same TCP write as the upgrade request?
2. At what exact point can the decoder safely reject an advertised 8 GiB frame,
   even if none of its payload has arrived?
3. Which state variables distinguish an idle connection from a fragmented text
   message, and which opcodes are legal in each state?
4. Why should UTF-8 validation happen at message completion rather than on each
   text fragment independently?
5. What owns the right to write to a socket? Could a shutdown path interleave
   bytes with a pong or echo response?
6. When the client limit is reached, should the accept loop block, accept and
   close, or enqueue? State the resource and fairness consequences.
7. What does `stop` guarantee to callers if a worker is blocked in a socket
   read? How do you test that guarantee without sleeps that race?
8. Which exceptions indicate peer protocol errors, which indicate ordinary
   disconnects, and which reveal a server bug? Where is each contained?
9. Is it safe to echo arbitrary close codes and reasons? List the validation
   needed before reflecting peer-controlled close data.
10. What operational evidence would you require before exposing this server to
    anything beyond loopback?

