# Diagnosis

The new parameter frame is parented to `caller_environment`, producing dynamic scope. It must be parented
to `function.definition_environment`, the frame retained when `fn` was evaluated. Copying the caller's
current bindings still chooses the wrong owner, breaks nested parent chains, and cannot model later global
updates consistently. Define `x`, create a zero-argument function returning `x`, and invoke it inside two
separate `let` forms that shadow `x`; lexical scope returns the definition-site value both times.
