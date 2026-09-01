# Adversarial validation

`fault-injection/` crosses the durable side-effect/lost-ack boundary. `stress/` races duplicate
producers and consumers. `fuzz/` uses a fixed-seed operation model and checks state, ownership,
uniqueness, and DLQ projection after every step. These are bounded probes, not soak evidence.
