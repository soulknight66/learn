#include <limits.h>

#define SLOT_COUNT 4u
#define READY 1u

unsigned choose_slot(const unsigned states[SLOT_COUNT], unsigned current) {
    unsigned distance;

    for (distance = 0u; distance < SLOT_COUNT; ++distance) {
        unsigned slot = (current + distance) % SLOT_COUNT;
        if (states[slot] == READY) {
            return slot;
        }
    }
    return UINT_MAX;
}
