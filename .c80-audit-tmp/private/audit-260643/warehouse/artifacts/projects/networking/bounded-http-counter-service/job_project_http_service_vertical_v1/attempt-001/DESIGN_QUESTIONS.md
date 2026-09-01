# Design questions

1. At what exact point can the parser prove a request body is complete?
2. Which ambiguous request forms could enable request smuggling when a proxy disagrees?
3. What is the overload behavior when workers and the queue are both occupied?
4. Which shutdown invariants protect accepted sockets, queued sockets, and worker threads?
5. Does an idempotency key belong globally, per route, or per authenticated principal?
6. How would persistence change acknowledgement and retry semantics?
7. Which handlers are safe in a single selector thread? How would blocking storage alter that?
8. Which benchmark result would falsify your architecture hypothesis, and what profile would
   you capture next?
9. What must be trusted when the service is behind a TLS terminator or reverse proxy?
10. Which facts make `/healthz` insufficient as a readiness or correctness signal?
