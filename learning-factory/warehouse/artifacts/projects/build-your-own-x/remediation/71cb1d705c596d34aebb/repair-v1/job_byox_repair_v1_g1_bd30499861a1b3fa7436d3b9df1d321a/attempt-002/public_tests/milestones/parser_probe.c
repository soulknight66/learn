#include <stdio.h>
#include <string.h>

#include "lexer.h"
#include "parser.h"

int main(void)
{
    const char *source = "printf one | cat > out &";
    TokenList tokens;
    CommandList list;
    ShellError error;
    Pipeline *pipeline;
    int failed = 0;

    token_list_init(&tokens);
    command_list_init(&list);
    shell_error_clear(&error);
    if (lexer_tokenize(source, &tokens, &error) != SHELL_RESULT_OK ||
        parser_parse_list(source, &tokens, &list, &error) != SHELL_RESULT_OK) {
        fprintf(stderr, "parse failed at byte %zu: %s\n", error.offset,
                error.message);
        failed = 1;
        goto done;
    }
    if (list.pipeline_count != 1U) {
        fprintf(stderr, "expected one pipeline, got %zu\n",
                list.pipeline_count);
        failed = 1;
        goto done;
    }
    pipeline = &list.pipelines[0];
    if (!pipeline->background || pipeline->command_count != 2U ||
        pipeline->source_text == NULL ||
        strcmp(pipeline->source_text, "printf one | cat > out") != 0) {
        fputs("pipeline shape or retained source text is incorrect\n", stderr);
        failed = 1;
        goto done;
    }
    if (pipeline->commands[0].argc != 2U ||
        strcmp(pipeline->commands[0].argv[0], "printf") != 0 ||
        strcmp(pipeline->commands[0].argv[1], "one") != 0 ||
        pipeline->commands[1].argc != 1U ||
        strcmp(pipeline->commands[1].argv[0], "cat") != 0 ||
        pipeline->commands[1].redirection_count != 1U ||
        pipeline->commands[1].redirections[0].kind !=
            REDIRECTION_OUTPUT_TRUNCATE ||
        strcmp(pipeline->commands[1].redirections[0].path, "out") != 0) {
        fputs("command or redirection tree is incorrect\n", stderr);
        failed = 1;
    }

done:
    command_list_destroy(&list);
    token_list_destroy(&tokens);
    return failed;
}
