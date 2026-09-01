/* Benign payload for an explicitly opted-in namespace smoke test. */
#define _POSIX_C_SOURCE 200809L

#include <stdio.h>
#include <string.h>
#include <unistd.h>

int main(void) {
    char hostname[64] = {0};
    int hostname_ok = gethostname(hostname, sizeof(hostname) - 1) == 0;
    int pid_ok = getpid() == 1;
    int proc_ok = access("/proc/self/status", R_OK) == 0;

    (void)printf(
        "pid=%ld\nhostname=%s\nproc=%s\n",
        (long)getpid(),
        hostname_ok ? hostname : "<error>",
        proc_ok ? "visible" : "missing"
    );
    if (!hostname_ok || strcmp(hostname, "minibox") != 0 || !pid_ok || !proc_ok) {
        return 70;
    }
    return 17;
}
