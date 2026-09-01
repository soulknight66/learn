# Exercise 02: phantom blank lines

The scanner fragment in `BrokenNewline.java.txt` reports correct locations for
LF files but adds an extra line for every CRLF pair.

Explain which scanner primitive should own physical newline normalization and
how a comment ending at CRLF interacts with it. Specify tests for LF, CR, CRLF,
mixed endings, and end-of-input comments.

