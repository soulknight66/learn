# Code-review exercise 01 answer

The strategy trusts an attacker-controlled length before applying its resource
policy. A peer can trigger huge allocation or make a worker wait for bytes that
will never arrive. It also misses invalid encodings until too late and risks
mutating the buffer before a complete frame exists.

After two bytes, validate RSV, opcode, mask direction, and the direct 0–125
length. For marker 126, wait only for two more header bytes; for 127, wait only
for eight. Decode without allocating payload storage, reject the 64-bit high
bit, reject noncanonical values, apply the configured maximum, and enforce the
125-byte control limit. Only then wait for four mask bytes and the bounded
payload. Peek from an input buffer and remove bytes only after the entire frame
is present, so partial or rejected frames cannot accidentally consume a later
frame.

