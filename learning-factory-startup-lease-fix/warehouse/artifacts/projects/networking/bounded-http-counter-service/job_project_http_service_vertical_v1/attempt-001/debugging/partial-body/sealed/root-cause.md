# Root cause

The parser treated any body bytes already present after the header as the complete body, even
when fewer than the declared `Content-Length` had arrived. TCP fragmentation therefore caused
early request emission; the application saw truncated JSON and the remaining bytes polluted
subsequent parsing. The single fix is to retain parser state and return no request until the
entire declared body is buffered.
