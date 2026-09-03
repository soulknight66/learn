/* Optional learner test helper: deterministic writes to stdout and stderr. */
#include <stdio.h>

int main(void) {
    fputs("stdout-line\n", stdout);
    fputs("stderr-line\n", stderr);
    return 0;
}
