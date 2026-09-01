# Debugging exercise 01 answer

TCP reads are not aligned to protocol phases. The HTTP reader discarded the
suffix of the read that contained `\r\n\r\n`; that suffix was already removed
from the socket, so the frame decoder could never recover it.

Return an upgrade request that owns a binary remainder buffer. Split at the
first boundary, parse only the prefix, and pass `request.take_remainder` into
the decoder before its first socket read. The transfer-style method prevents
feeding it twice. A regression should send `request_bytes + masked_frame` in
one socket write and assert that the parsed request remains valid and the exact
frame bytes are returned as the remainder. A second case should split the
terminator across writes to ensure incremental boundary detection still works.

