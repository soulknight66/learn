# Answer

For length one, the token l is compared with only the first byte of let and is misclassified. For a
length greater than three, strncmp reads past the three-byte keyword string while trying to compare the
requested token length. The token slice itself also need not be null-terminated.

Require length exactly three, then use memcmp over exactly three bytes. Representative tests include l,
le, let, lets, letter, and a three-byte slice followed immediately by a nonzero byte.
