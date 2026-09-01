#define _POSIX_C_SOURCE 200809L

#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <unistd.h>

static void fail(const char *operation)
{
    perror(operation);
    exit(EXIT_FAILURE);
}

static int write_all(int fd, const char *data, size_t length)
{
    while (length > 0) {
        ssize_t written = write(fd, data, length);
        if (written < 0 && errno == EINTR)
            continue;
        if (written < 0)
            return -1;
        data += (size_t)written;
        length -= (size_t)written;
    }
    return 0;
}

int main(void)
{
    int channel[2];
    if (pipe(channel) < 0)
        fail("pipe");

    pid_t producer = fork();
    if (producer < 0)
        fail("fork producer");
    if (producer == 0) {
        static const char payload[] = "message reached consumer\n";
        close(channel[0]);
        if (write_all(channel[1], payload, sizeof(payload) - 1) < 0)
            _exit(20);
        close(channel[1]);
        _exit(0);
    }

    pid_t consumer = fork();
    if (consumer < 0)
        fail("fork consumer");
    if (consumer == 0) {
        char buffer[64];
        close(channel[1]);
        for (;;) {
            ssize_t count = read(channel[0], buffer, sizeof(buffer));
            if (count < 0 && errno == EINTR)
                continue;
            if (count < 0)
                _exit(21);
            if (count == 0)
                break;
            if (write_all(STDOUT_FILENO, buffer, (size_t)count) < 0)
                _exit(22);
        }
        close(channel[0]);
        _exit(0);
    }

    close(channel[0]);
    close(channel[1]);

    int status;
    if (waitpid(producer, &status, 0) < 0)
        fail("waitpid producer");
    if (waitpid(consumer, &status, 0) < 0)
        fail("waitpid consumer");
    return 0;
}
