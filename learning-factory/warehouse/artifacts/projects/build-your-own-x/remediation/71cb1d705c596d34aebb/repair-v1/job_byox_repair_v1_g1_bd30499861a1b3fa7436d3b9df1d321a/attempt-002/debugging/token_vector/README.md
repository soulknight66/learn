# Debugging lab: token-vector corruption

This reduced tokenizer handles whitespace-delimited words only. That limited
grammar is intentional: investigate the memory failure, not quote semantics.

From this exercise directory, build with AddressSanitizer (when the runtime is
installed) and pass enough arguments to grow the result vector:

```sh
cc -std=c11 -Wall -Wextra -Wpedantic -O0 -g \
  -fsanitize=address -fno-omit-frame-pointer buggy.c -o buggy
./buggy one two three four five six
```

Then try one word and compare. Read the first invalid-write report rather than
later symptoms.

Questions:

1. How many elements fit in the initial allocation?
2. What units do `malloc` and `realloc` receive, and what units does `capacity`
   represent?
3. Which write first exceeds the allocation after growth?
4. How can growth preserve the old allocation if allocation fails?
5. Which overflow check is needed before multiplying element count by element
   size?

Success means the six-word run prints six indexed words with no sanitizer
finding, the zero-word run is valid, and allocation failures have a defined
cleanup path.
