#include <stddef.h>

/* Proposed PR: centralize rounding so the fast path performs one expression. */
size_t proposed_round_request(size_t bytes, size_t alignment) {
    return (bytes + alignment - 1U) & ~(alignment - 1U);
}
