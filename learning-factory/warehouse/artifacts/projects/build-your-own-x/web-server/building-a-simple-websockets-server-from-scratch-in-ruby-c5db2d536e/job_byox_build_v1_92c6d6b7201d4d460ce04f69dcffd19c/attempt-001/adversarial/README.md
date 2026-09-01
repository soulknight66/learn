# Adversarial validation prompts

Use these only after ordinary public checks pass. Do not assume that a peer
obeys frame boundaries or closes politely.

1. Split every header form before and after each length and mask byte.
2. Concatenate an upgrade, a data frame, ping, continuation, and close into one
   write; verify no bytes disappear between parsers.
3. Advertise payloads just below, at, and above both frame and message limits.
4. Try reserved opcodes, each RSV bit, unmasked client frames, noncanonical
   lengths, a set 64-bit high bit, and fragmented control frames.
5. Fragment a valid multi-byte UTF-8 sequence across frames, then corrupt its
   final byte. Compare close behavior at message completion.
6. Send close payloads of zero, one, and two bytes; prohibited codes; private
   codes; and malformed reason text.
7. Hold upgrades and frames one byte short until their timeout.
8. Saturate all client slots, race disconnects against new accepts, then invoke
   `stop` repeatedly while callbacks are active.

The deterministic sealed adversarial runner covers a small subset of byte
splits and malformed headers. It is not a fuzzer and earns no fuzzing label.

