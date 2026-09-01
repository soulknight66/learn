#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/wait.h>
#include <unistd.h>

static void fail(const char *operation)
{
    (void)fprintf(stderr, "%s: %s\n", operation, strerror(errno));
    exit(1);
}

int main(void)
{
    int channel[2];
    pid_t writer;
    pid_t reader;

    if (pipe(channel) < 0) {
        fail("pipe");
    }
    writer = fork();
    if (writer < 0) {
        fail("fork writer");
    }
    if (writer == 0) {
        static const char message[] = "payload\n";
        (void)close(channel[0]);
        if (write(channel[1], message, sizeof(message) - 1) < 0) {
            _exit(2);
        }
        (void)close(channel[1]);
        _exit(0);
    }

    reader = fork();
    if (reader < 0) {
        fail("fork reader");
    }
    if (reader == 0) {
        char buffer[64];
        ssize_t count;

        (void)close(channel[1]);
        while ((count = read(channel[0], buffer, sizeof(buffer))) > 0) {
            if (write(STDOUT_FILENO, buffer, (size_t)count) < 0) {
                _exit(3);
            }
        }
        _exit(count < 0 ? 4 : 0);
    }

    /* One inherited endpoint is intentionally mishandled in this exercise. */
    (void)close(channel[0]);
    if (waitpid(writer, NULL, 0) < 0) {
        fail("wait writer");
    }
    if (waitpid(reader, NULL, 0) < 0) {
        fail("wait reader");
    }
    (void)close(channel[1]);
    return 0;
}
