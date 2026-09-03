#include "minios.h"

#include <stdint.h>
#include <stdio.h>
#include <string.h>

#define PROCESS_STEPS 4000u
#define VM_STEPS 4000u
#define FS_STEPS 4000u

static uint32_t random_state = 0x6d696e69u;

static uint32_t next_random(void)
{
    random_state = random_state * 1664525u + 1013904223u;
    return random_state;
}

static int process_invariants_hold(const proc_table_t *table)
{
    size_t running = 0u;
    size_t i;
    size_t j;

    for (i = 0; i < MINIOS_MAX_PROCESSES; ++i) {
        const process_t *process = &table->slots[i];
        if (process->state == PROC_RUNNING) {
            ++running;
        }
        if (process->state == PROC_UNUSED) {
            if (process->pid != 0u || process->parent_pid != 0u ||
                process->entry_point != (uintptr_t)0 || process->exit_code != 0) {
                return 0;
            }
        } else if (process->state < PROC_READY || process->state > PROC_ZOMBIE ||
                   process->pid == 0u) {
            return 0;
        }
        if (process->state != PROC_UNUSED) {
            for (j = i + 1u; j < MINIOS_MAX_PROCESSES; ++j) {
                if (table->slots[j].state != PROC_UNUSED &&
                    table->slots[j].pid == process->pid) {
                    return 0;
                }
            }
        }
    }
    if (running > 1u) {
        return 0;
    }
    if (table->current_slot == -1) {
        return running == 0u;
    }
    return table->current_slot >= 0 &&
           (size_t)table->current_slot < MINIOS_MAX_PROCESSES &&
           running == 1u &&
           table->slots[(size_t)table->current_slot].state == PROC_RUNNING;
}

static uint32_t choose_pid(const proc_table_t *table, uint32_t value)
{
    size_t slot = (size_t)(value % MINIOS_MAX_PROCESSES);

    if ((value & 1u) != 0u && table->slots[slot].state != PROC_UNUSED) {
        return table->slots[slot].pid;
    }
    return value % 24u;
}

static int exercise_process_sequences(void)
{
    proc_table_t table;
    uint32_t step;

    proc_table_init(&table);
    for (step = 0u; step < PROCESS_STEPS; ++step) {
        proc_table_t before = table;
        uint32_t value = next_random();
        uint32_t pid = choose_pid(&table, value >> 5);
        uint32_t output_pid = 0u;
        int32_t output_code = 0;
        const process_t *output_process = NULL;
        os_status_t status;

        switch (value % 7u) {
        case 0u: {
            uint32_t parent = ((value >> 9) & 3u) == 0u ? pid : 0u;
            status = proc_spawn(&table, parent, (uintptr_t)value, &output_pid);
            break;
        }
        case 1u:
            status = proc_schedule(&table, &output_pid);
            break;
        case 2u:
            status = proc_block(&table, pid);
            break;
        case 3u:
            status = proc_wake(&table, pid);
            break;
        case 4u:
            status = proc_exit(&table, pid, (int32_t)value);
            break;
        case 5u:
            status = proc_reap(&table, pid, &output_code);
            break;
        default:
            status = proc_get(&table, pid, &output_process);
            if (memcmp(&table, &before, sizeof(table)) != 0) {
                return 0;
            }
            break;
        }
        if (status != OS_OK && memcmp(&table, &before, sizeof(table)) != 0) {
            return 0;
        }
        if (!process_invariants_hold(&table)) {
            return 0;
        }
    }
    return 1;
}

static int vm_invariants_hold(const vm_space_t *space)
{
    size_t i;
    size_t j;

    for (i = 0u; i < MINIOS_MAX_MAPPINGS; ++i) {
        const vm_mapping_t *mapping = &space->mappings[i];
        if (mapping->present == 0u) {
            if (mapping->virtual_page != 0u || mapping->physical_frame != 0u ||
                mapping->permissions != 0u || mapping->reserved != 0u) {
                return 0;
            }
            continue;
        }
        if (mapping->present != 1u ||
            mapping->virtual_page % MINIOS_PAGE_SIZE != 0u ||
            mapping->virtual_page >= MINIOS_VIRTUAL_PAGES * MINIOS_PAGE_SIZE ||
            mapping->physical_frame % MINIOS_PAGE_SIZE != 0u ||
            mapping->physical_frame >=
                MINIOS_PHYSICAL_FRAMES * MINIOS_PAGE_SIZE ||
            mapping->permissions == 0u ||
            ((unsigned int)mapping->permissions &
             ~(unsigned int)VM_ALL_PERMISSIONS) != 0u) {
            return 0;
        }
        for (j = i + 1u; j < MINIOS_MAX_MAPPINGS; ++j) {
            if (space->mappings[j].present != 0u &&
                space->mappings[j].virtual_page == mapping->virtual_page) {
                return 0;
            }
        }
    }
    return 1;
}

static int verify_translation(const vm_space_t *space, uint32_t virtual_address,
                              uint8_t permissions, uint32_t physical)
{
    uint32_t base = virtual_address - (virtual_address % MINIOS_PAGE_SIZE);
    uint32_t offset = virtual_address % MINIOS_PAGE_SIZE;
    size_t i;

    for (i = 0u; i < MINIOS_MAX_MAPPINGS; ++i) {
        const vm_mapping_t *mapping = &space->mappings[i];
        if (mapping->present != 0u && mapping->virtual_page == base &&
            (mapping->permissions & permissions) == permissions) {
            return physical == mapping->physical_frame + offset;
        }
    }
    return 0;
}

static int exercise_vm_sequences(void)
{
    vm_space_t space;
    uint32_t step;

    vm_space_init(&space);
    for (step = 0u; step < VM_STEPS; ++step) {
        vm_space_t before = space;
        uint32_t value = next_random();
        uint32_t virtual_address =
            ((value >> 3) % (MINIOS_VIRTUAL_PAGES + 3u)) * MINIOS_PAGE_SIZE;
        uint32_t physical_address =
            ((value >> 11) % (MINIOS_PHYSICAL_FRAMES + 3u)) * MINIOS_PAGE_SIZE;
        uint8_t permissions = (uint8_t)((value >> 19) & 0x1fu);
        uint32_t translated = 0u;
        os_status_t status;

        if ((value & 0x40u) != 0u) {
            ++virtual_address;
        }
        if ((value & 0x80u) != 0u) {
            ++physical_address;
        }
        switch (value % 3u) {
        case 0u:
            status = vm_map(&space, virtual_address, physical_address,
                            permissions);
            if (status != OS_OK && memcmp(&space, &before, sizeof(space)) != 0) {
                return 0;
            }
            break;
        case 1u:
            status = vm_unmap(&space, virtual_address);
            if (status != OS_OK && memcmp(&space, &before, sizeof(space)) != 0) {
                return 0;
            }
            break;
        default:
            virtual_address += (value >> 24) & (MINIOS_PAGE_SIZE - 1u);
            status = vm_translate(&space, virtual_address, permissions,
                                  &translated);
            if (memcmp(&space, &before, sizeof(space)) != 0) {
                return 0;
            }
            if (status == OS_OK &&
                !verify_translation(&space, virtual_address, permissions,
                                    translated)) {
                return 0;
            }
            break;
        }
        if (!vm_invariants_hold(&space)) {
            return 0;
        }
    }
    return 1;
}

static int filesystem_invariants_hold(const ramfs_t *fs)
{
    size_t i;
    size_t j;

    for (i = 0u; i < MINIOS_FS_MAX_FILES; ++i) {
        const fs_file_t *file = &fs->files[i];
        if (file->used == 0u) {
            if (file->size != 0u || file->name[0] != '\0') {
                return 0;
            }
            continue;
        }
        if (file->used != 1u || file->size > MINIOS_FS_FILE_CAPACITY ||
            file->name[0] != '/') {
            return 0;
        }
        for (j = i + 1u; j < MINIOS_FS_MAX_FILES; ++j) {
            if (fs->files[j].used != 0u &&
                strcmp(file->name, fs->files[j].name) == 0) {
                return 0;
            }
        }
    }
    return 1;
}

static int exercise_filesystem_sequences(void)
{
    static const char *const names[] = {
        "/a", "/b", "/c", "/d", "/e", "/f", "/g", "/h",
        "/overflow", "/bad/name"
    };
    ramfs_t fs;
    uint32_t step;

    fs_init(&fs);
    for (step = 0u; step < FS_STEPS; ++step) {
        ramfs_t before = fs;
        uint32_t value = next_random();
        const char *name = names[(value >> 8) %
                                 (sizeof(names) / sizeof(names[0]))];
        size_t offset = (size_t)((value >> 12) % 272u);
        size_t count = (size_t)((value >> 21) % 20u);
        uint8_t bytes[20];
        uint8_t output[20];
        size_t amount = 0u;
        size_t i;
        os_status_t status;

        for (i = 0u; i < sizeof(bytes); ++i) {
            bytes[i] = (uint8_t)(value + (uint32_t)i);
            output[i] = 0xa5u;
        }
        switch (value % 5u) {
        case 0u:
            status = fs_create(&fs, name);
            break;
        case 1u:
            status = fs_unlink(&fs, name);
            break;
        case 2u:
            status = fs_write(&fs, name, offset, bytes, count, &amount);
            break;
        case 3u:
            status = fs_read(&fs, name, offset, output, count, &amount);
            if (memcmp(&fs, &before, sizeof(fs)) != 0) {
                return 0;
            }
            break;
        default:
            status = fs_stat(&fs, name, &amount);
            if (memcmp(&fs, &before, sizeof(fs)) != 0) {
                return 0;
            }
            break;
        }
        if (status != OS_OK && memcmp(&fs, &before, sizeof(fs)) != 0) {
            return 0;
        }
        if (!filesystem_invariants_hold(&fs)) {
            return 0;
        }
    }
    return 1;
}

int main(void)
{
    int processes = exercise_process_sequences();
    int virtual_memory = exercise_vm_sequences();
    int filesystem = exercise_filesystem_sequences();

    (void)printf("[%s] %u deterministic process operations\n",
                 processes != 0 ? "PASS" : "FAIL", PROCESS_STEPS);
    (void)printf("[%s] %u deterministic VM operations\n",
                 virtual_memory != 0 ? "PASS" : "FAIL", VM_STEPS);
    (void)printf("[%s] %u deterministic filesystem operations\n",
                 filesystem != 0 ? "PASS" : "FAIL", FS_STEPS);
    return processes != 0 && virtual_memory != 0 && filesystem != 0 ? 0 : 1;
}
