# Review 3: builtin execution context

`candidate.c` dispatches a builtin as soon as the first command name matches.
Its simple demonstrations (`cd /tmp`, `pwd`, and `exit`) seem to work.

Review behavior for:

1. `cd /tmp | pwd`;
2. `cd /tmp &`;
3. `exit &` and `exit | cat`;
4. `pwd > out` followed by another foreground command;
5. `pwd < readable > missing/out`, where opening the output fails after the
   input descriptor was changed;
6. buffered builtin output around `dup2`;
7. a job-control builtin used in a child context.

Specify a dispatch matrix based on builtin kind, pipeline size, and background
flag. Then describe a transactional redirection helper for parent-run builtins.
The parser contract rejects two input or two output redirections on one command.
