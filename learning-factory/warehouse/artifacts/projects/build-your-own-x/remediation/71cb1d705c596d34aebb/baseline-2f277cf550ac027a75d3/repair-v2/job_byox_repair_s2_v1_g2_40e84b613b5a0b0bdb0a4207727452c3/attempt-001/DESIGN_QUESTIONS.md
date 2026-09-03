# Design questions

Write down your answers before each milestone. These prompts intentionally do
not contain solutions.

## Parsing

1. How will the lexer distinguish “no word yet” from a deliberately empty word
   produced by `''`?
2. Which layer owns token strings after a command is assembled, and what frees
   a partially parsed line?
3. How will you reject an error anywhere in the line before forking anything?
4. Does a redirection token attach to a lexical position or to its command?

## Pipeline construction

1. For stage `i` of `n`, exactly which descriptors are open immediately before
   `exec`?
2. What cleanup occurs if pipe creation succeeds twice and the third `fork`
   fails?
3. Where do you establish the process group, and which races does that leave?
4. How does explicit redirection interact with the first or last pipe endpoint?
5. What happens if the launching process has descriptor 0, 1, or 2 closed and
   `pipe` or `open` reuses that number?

## Built-ins

1. Which contexts require a built-in to run in the parent, and which require a
   child?
2. How will you restore standard descriptors if opening or running a redirected
   built-in fails halfway through?
3. When is the shell's “most recent status” updated?

## Job control

1. What per-process facts are needed to derive a whole job's Running, Stopped,
   or Done state?
2. How will an asynchronously completed job be matched to a `waitpid` result?
3. Which process's status defines the pipeline result?
4. What terminal and signal state must be restored on every foreground exit
   path?

## Testing

1. Which tests can use ordinary pipes, and which genuinely require a PTY?
2. How will a test prove that no process holds a stray pipe writer?
3. How will timeouts clean up an entire process group without killing the test
   runner?
4. Which inherited signal dispositions could invalidate assumptions made by
   your foreground wait loop?
