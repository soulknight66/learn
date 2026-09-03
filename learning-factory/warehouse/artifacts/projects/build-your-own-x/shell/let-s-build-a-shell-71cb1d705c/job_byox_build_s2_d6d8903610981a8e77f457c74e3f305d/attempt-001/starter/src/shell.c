#include "msh.h"

#include <ctype.h>
#include <stdio.h>

int execute_line(struct shell *shell, const char *line) {
    (void)shell;
    const unsigned char *cursor = (const unsigned char *)line;
    while (*cursor != '\0' && isspace(*cursor)) {
        ++cursor;
    }
    if (*cursor == '\0') {
        return 0;
    }

    /* TODO: parse the complete line before constructing its process graph. */
    fprintf(stderr, "msh: syntax: command execution is not implemented\n");
    return 2;
}
