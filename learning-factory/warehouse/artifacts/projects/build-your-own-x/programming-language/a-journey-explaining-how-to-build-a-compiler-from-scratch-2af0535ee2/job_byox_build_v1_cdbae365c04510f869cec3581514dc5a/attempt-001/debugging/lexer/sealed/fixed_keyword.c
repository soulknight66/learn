#include <stddef.h>
#include <string.h>

enum token_kind { TOKEN_NAME, TOKEN_LET };

enum token_kind classify_name(const char *start, size_t length) {
    if (length == 3 && memcmp(start, "let", 3) == 0) {
        return TOKEN_LET;
    }
    return TOKEN_NAME;
}
