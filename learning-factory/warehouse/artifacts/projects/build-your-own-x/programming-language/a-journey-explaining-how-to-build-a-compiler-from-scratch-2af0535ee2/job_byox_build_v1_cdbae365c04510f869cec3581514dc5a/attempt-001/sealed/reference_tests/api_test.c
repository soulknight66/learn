#include "pebble.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int checks;
static int failures;

#define CHECK(condition) do { \
    checks++; \
    if (!(condition)) { \
        fprintf(stderr, "api_test:%d: check failed: %s\n", __LINE__, #condition); \
        failures++; \
    } \
} while (0)

static int stream_equals(FILE *stream, const char *expected) {
    char buffer[128];
    size_t count;
    if (fflush(stream) != 0 || fseek(stream, 0, SEEK_SET) != 0) return 0;
    count = fread(buffer, 1, sizeof(buffer) - 1, stream);
    buffer[count] = '\0';
    return strcmp(buffer, expected) == 0;
}

int main(void) {
    PebbleProgram *program = NULL;
    PebbleProgram *limited_program = (PebbleProgram *)(void *)&checks;
    PebbleOptions options;
    PebbleResult result;
    const char *diagnostic_path = "build/api_diagnostics.tmp";
    const char *first_path = "build/api_output_first.tmp";
    const char *second_path = "build/api_output_second.tmp";
    FILE *diagnostics = fopen(diagnostic_path, "w+");
    FILE *first_output = fopen(first_path, "w+");
    FILE *second_output = fopen(second_path, "w+");

    CHECK(diagnostics != NULL);
    CHECK(first_output != NULL);
    CHECK(second_output != NULL);
    if (diagnostics == NULL || first_output == NULL || second_output == NULL) {
        if (second_output != NULL) fclose(second_output);
        if (first_output != NULL) fclose(first_output);
        if (diagnostics != NULL) fclose(diagnostics);
        return 1;
    }

    result = pebble_compile("let x=1; x=x+2; print x;", NULL, &program, diagnostics);
    CHECK(result == PEBBLE_OK);
    CHECK(program != NULL);

    result = pebble_execute(program, NULL, first_output, diagnostics);
    CHECK(result == PEBBLE_OK);
    result = pebble_execute(program, NULL, second_output, diagnostics);
    CHECK(result == PEBBLE_OK);
    CHECK(stream_equals(first_output, "3\n"));
    CHECK(stream_equals(second_output, "3\n"));

    options = pebble_default_options();
    options.max_steps = 2;
    result = pebble_execute(program, &options, first_output, diagnostics);
    CHECK(result == PEBBLE_LIMIT_ERROR);

    options = pebble_default_options();
    options.max_code = 1;
    result = pebble_compile("print 1;", &options, &limited_program, diagnostics);
    CHECK(result == PEBBLE_LIMIT_ERROR);
    CHECK(limited_program == NULL);

    options = pebble_default_options();
    options.max_stack = 1;
    limited_program = (PebbleProgram *)(void *)&checks;
    result = pebble_compile("print 1 + 2;", &options, &limited_program, diagnostics);
    CHECK(result == PEBBLE_LIMIT_ERROR);
    CHECK(limited_program == NULL);

    CHECK(pebble_compile(NULL, NULL, &limited_program, diagnostics) == PEBBLE_SYSTEM_ERROR);
    CHECK(pebble_execute(NULL, NULL, first_output, diagnostics) == PEBBLE_SYSTEM_ERROR);
    pebble_program_free(NULL);
    pebble_program_free(program);

    fclose(second_output);
    fclose(first_output);
    fclose(diagnostics);
    (void)remove(second_path);
    (void)remove(first_path);
    (void)remove(diagnostic_path);
    if (failures != 0) return 1;
    printf("api_test: %d checks passed\n", checks);
    return 0;
}
