#define _POSIX_C_SOURCE 200809L

#include <stdio.h>
#include <stdlib.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <unistd.h>

static int launch_pipeline(char ***commands, size_t command_count)
{
    int previous_read = -1;
    int status = 0;

    for (size_t index = 0; index < command_count; ++index) {
        int next_pipe[2] = {-1, -1};
        if (index + 1 < command_count && pipe(next_pipe) < 0) {
            perror("pipe");
            return 1;
        }

        pid_t child = fork();
        if (child < 0) {
            perror("fork");
            return 1;
        }
        if (child == 0) {
            if (previous_read >= 0 && dup2(previous_read, STDIN_FILENO) < 0) {
                perror("dup2 stdin");
                exit(125);
            }
            if (next_pipe[1] >= 0 && dup2(next_pipe[1], STDOUT_FILENO) < 0) {
                perror("dup2 stdout");
                exit(125);
            }
            execvp(commands[index][0], commands[index]);
            perror(commands[index][0]);
            exit(127);
        }

        if (waitpid(child, &status, 0) < 0) {
            perror("waitpid");
            return 1;
        }

        if (previous_read >= 0)
            close(previous_read);
        if (next_pipe[1] >= 0)
            close(next_pipe[1]);
        previous_read = next_pipe[0];
    }

    if (previous_read >= 0)
        close(previous_read);
    return WEXITSTATUS(status);
}

int main(void)
{
    char *producer[] = {"head", "-c", "1048576", "/dev/zero", NULL};
    char *consumer[] = {"wc", "-c", NULL};
    char **commands[] = {producer, consumer};

    int status = launch_pipeline(commands, 2);
    fprintf(stderr, "pipeline status: %d\n", status);
    return status;
}
