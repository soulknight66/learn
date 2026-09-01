#define _POSIX_C_SOURCE 200809L

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static void free_words(char **words, size_t count)
{
    for (size_t index = 0; index < count; ++index)
        free(words[index]);
    free(words);
}

static int append_word(char ***words, size_t *count, size_t *capacity,
                       const char *text)
{
    if (*count + 1 >= *capacity) {
        *capacity *= 2;
        char **grown = realloc(*words, *capacity);
        if (grown == NULL)
            return -1;
        *words = grown;
    }

    (*words)[*count] = strdup(text);
    if ((*words)[*count] == NULL)
        return -1;
    ++*count;
    (*words)[*count] = NULL;
    return 0;
}

int main(int argc, char **argv)
{
    size_t count = 0;
    size_t capacity = 2;
    char **words = malloc(capacity * sizeof(*words));
    if (words == NULL)
        return 1;
    words[0] = NULL;

    for (int index = 1; index < argc; ++index) {
        if (append_word(&words, &count, &capacity, argv[index]) < 0) {
            free_words(words, count);
            return 1;
        }
    }

    for (size_t index = 0; index < count; ++index)
        printf("%zu: %s\n", index, words[index]);
    free_words(words, count);
    return 0;
}
