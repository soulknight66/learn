#include "kernel/mmu.h"

#include <stdint.h>

#define L1_ENTRY_COUNT 4096u
#define SECTION_DESCRIPTOR 0x2u
#define SECTION_AP_FULL_ACCESS (3u << 10)

static uint32_t l1_table[L1_ENTRY_COUNT] __attribute__((aligned(16384)));

static void map_identity_sections(uint32_t first, uint32_t count) {
    uint32_t section;

    for (section = first; section < first + count; ++section) {
        l1_table[section] = (section << 20) | SECTION_AP_FULL_ACCESS |
                            SECTION_DESCRIPTOR;
    }
}

bool lf_mmu_enable_identity(void) {
    uint32_t index;
    uint32_t zero = 0u;
    uint32_t domain_access = 3u;
    uint32_t table_base = (uint32_t)(uintptr_t)l1_table;
    uint32_t control;

    if ((table_base & UINT32_C(0x3fff)) != 0u) {
        return false;
    }
    for (index = 0u; index < L1_ENTRY_COUNT; ++index) {
        l1_table[index] = 0u;
    }
    map_identity_sections(0u, 128u);
    map_identity_sections(UINT32_C(0x100), 16u);

    __asm__ volatile("mcr p15, 0, %0, c2, c0, 0" : : "r"(table_base) : "memory");
    __asm__ volatile("mcr p15, 0, %0, c3, c0, 0" : : "r"(domain_access) : "memory");
    __asm__ volatile("mcr p15, 0, %0, c8, c7, 0" : : "r"(zero) : "memory");
    __asm__ volatile("mcr p15, 0, %0, c7, c10, 4" : : "r"(zero) : "memory");
    __asm__ volatile("mrc p15, 0, %0, c1, c0, 0" : "=r"(control));
    control |= 1u;
    __asm__ volatile("mcr p15, 0, %0, c1, c0, 0" : : "r"(control) : "memory");
    __asm__ volatile("mrc p15, 0, %0, c2, c0, 0" : "=r"(control) : : "memory");
    return (control & UINT32_C(0xffffc000)) == table_base;
}
