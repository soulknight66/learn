# Exercise 02 answer

JavaScript's `string.length` counts UTF-16 code units, not encoded bytes.
HTTP's Content-Length counts octets, so the original calculation is wrong as
soon as UTF-8 uses a different number of bytes. In addition, HEAD describes the
same selected representation as GET but must not carry its payload on the wire.

Serialize once to a Buffer, derive Content-Length from `buffer.length`, retain
the representation headers, and call `res.end()` without the Buffer for HEAD.
The fixed example in `fixed-respond.js` follows that order and normalizes the
method defensively.

This response helper still is not a complete production sender: streaming,
conditional requests, compression, and backpressure are outside the exercise.
