# Instructor answer

The wrapper destroys `MicaSyntaxError` versus `MicaRuntimeError`, stable codes, spans, original
causality, and tree/VM parity evidence. It also turns programmer bugs and malformed internal ASTs
into apparent user errors. Structured errors should cross the library API unchanged. The CLI may
format their code, message, and position for a terminal while retaining a nonzero exit status;
unexpected host errors should remain distinguishable.
