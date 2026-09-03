#ifndef MSH_H
#define MSH_H

#include <stdbool.h>

struct shell {
    int last_status;
    bool should_exit;
    int exit_status;
};

/* Execute one source line and return its shell status. */
int execute_line(struct shell *shell, const char *line);

#endif
