# Review 1: parser ownership and capacity

Assume `candidate.c` receives a correct token array from the lexer. The excerpt
only handles WORD and PIPE because redirection parsing is outside this review.
Its author reports that simple commands print correctly when inspected inside
`parse_tokens`.

Review the function for:

1. lifetime and aliasing of every stored `argv` pointer;
2. the exact write that occurs for the first over-capacity argument or command;
3. NUL termination of the argv vectors;
4. validation of leading, adjacent, and trailing pipes;
5. the meaning of an explicitly empty WORD token;
6. output state after a parse error.

Rank findings by their ability to cause memory corruption or execution of a
different command than the input describes. Propose a lifetime strategy that
fits the fixed-capacity, input-line-borrowing starter API, and contrast it with
an owning parser.
