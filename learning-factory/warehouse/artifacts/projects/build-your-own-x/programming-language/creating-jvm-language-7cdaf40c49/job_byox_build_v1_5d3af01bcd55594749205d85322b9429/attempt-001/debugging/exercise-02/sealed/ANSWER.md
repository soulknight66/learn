# Exercise 02 answer

The primitive consumes CR and LF independently, so CRLF becomes two physical
newlines. When consuming CR, inspect the following character and consume an
immediate LF in the same operation; then increment `line` once and reset the
column once. A lone LF or lone CR does the same without a partner.

Comment skipping should stop before either newline form and let the same
`advance` primitive normalize it. Tests should put an invalid token immediately
after LF, CR, CRLF, and mixed sequences, plus immediately after a comment. A
comment at EOF should not synthesize a newline.

