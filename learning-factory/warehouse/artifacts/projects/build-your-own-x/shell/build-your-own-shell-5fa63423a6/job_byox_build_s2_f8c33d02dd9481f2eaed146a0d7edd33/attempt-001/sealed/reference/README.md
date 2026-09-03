# Reference implementation

This sealed implementation supplies an independently authored solution to the public API. It uses a character-state lexer, an owned pipeline representation, one process group per pipeline, parent-and-child `setpgid`, explicit descriptor closure, and parent-side built-ins.

It is a teaching reference, not a production shell. In particular, stopped foreground jobs are observed and the terminal is restored, but there is no persistent job-selection interface; interactive PTY behavior still requires independent validation. See the sealed design and production review for limitations.
