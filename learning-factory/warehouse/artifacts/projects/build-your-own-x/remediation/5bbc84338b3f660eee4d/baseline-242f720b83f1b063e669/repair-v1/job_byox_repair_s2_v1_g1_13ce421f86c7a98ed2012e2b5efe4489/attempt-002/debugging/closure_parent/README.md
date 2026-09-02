# Debugging: caller-dependent closure

`buggy_call.py` contains a reduced function-call fragment. A function that should return a captured global
instead returns a same-named `let` value at its call site.

Find the ownership error and explain why copying the current bindings is not a general correction. Give a
program with two different callers that distinguishes lexical from dynamic scope.
