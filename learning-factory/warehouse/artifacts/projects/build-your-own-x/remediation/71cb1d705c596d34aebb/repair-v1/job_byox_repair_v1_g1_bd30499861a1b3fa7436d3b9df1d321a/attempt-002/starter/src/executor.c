#include "executor.h"

ShellResult executor_run_list(const CommandList *list, ShellState *state,
                              ShellError *error)
{
    if (list == NULL || state == NULL) {
        shell_error_set(error, 0U, "invalid executor input");
        return SHELL_RESULT_ERROR;
    }

    if (list->pipeline_count == 0U) {
        return SHELL_RESULT_OK;
    }

    /* TODO: execute each pipeline, including separators and job context. */
    shell_error_set(error, 0U, "execution is a TODO");
    return SHELL_RESULT_TODO;
}
