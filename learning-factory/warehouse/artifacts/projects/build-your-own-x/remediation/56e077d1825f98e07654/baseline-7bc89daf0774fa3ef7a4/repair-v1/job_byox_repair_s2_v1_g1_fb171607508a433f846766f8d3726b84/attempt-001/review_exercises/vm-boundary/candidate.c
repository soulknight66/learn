#include <stdbool.h>
#include <stdint.h>

struct mapping {
    uint32_t virtual_base;
    uint32_t physical_base;
    uint8_t flags;
    bool used;
};

bool candidate_translate(const struct mapping *table, uint32_t count,
                         uint32_t virtual_address, uint8_t requested,
                         uint32_t *physical_address) {
    uint32_t page = virtual_address & UINT32_C(0xfffff000);
    uint32_t index;

    for (index = 0u; index < count; ++index) {
        if (table[index].used && table[index].virtual_base == page) {
            *physical_address = table[index].physical_base +
                                (virtual_address & UINT32_C(0xfff));
            return (table[index].flags & requested) != 0u;
        }
    }
    return false;
}
