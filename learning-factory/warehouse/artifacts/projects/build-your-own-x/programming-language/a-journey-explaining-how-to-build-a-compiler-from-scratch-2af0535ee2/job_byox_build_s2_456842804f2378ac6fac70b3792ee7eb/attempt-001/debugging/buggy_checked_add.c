#include <limits.h>
#include <stdint.h>

/* Intentionally buggy exercise code: do not reuse in the starter. */
int buggy_checked_add(int64_t left, int64_t right, int64_t *result) {
    int64_t sum = left + right;
    if ((right > 0 && sum < left) || (right < 0 && sum > left)) {
        return 0;
    }
    if (sum > INT64_MAX || sum < INT64_MIN) {
        return 0;
    }
    *result = sum;
    return 1;
}
