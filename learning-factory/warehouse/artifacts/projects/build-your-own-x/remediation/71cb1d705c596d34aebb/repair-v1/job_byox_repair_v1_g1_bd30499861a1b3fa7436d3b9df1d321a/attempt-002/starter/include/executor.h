#ifndef MINISH_EXECUTOR_H
#define MINISH_EXECUTOR_H

#include "parser.h"
#include "shell.h"

/* Execute a prevalidated list and update status, jobs, or an exit request. */
ShellResult executor_run_list(const CommandList *list, ShellState *state,
                              ShellError *error);

#endif
