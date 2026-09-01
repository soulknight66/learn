from __future__ import annotations

import json
import sqlite3
from difflib import unified_diff
from pathlib import Path
from textwrap import dedent
from typing import Any

from .db import Database
from .util import redact, tree_sha256
from .vertical_slices import SliceResult


PROJECT_ID = "project_62500cd7d143a95230c724df71a56c4a"

_DEFAULT_PROVENANCE: dict[str, str] = {
    "source_id": "source_eac489a34bed5db9a1f2a580b457bcef",
    "source_name": "Build Your Own X",
    "source_path": "../build-your-own-x",
    "upstream_url": "https://github.com/codecrafters-io/build-your-own-x",
    "commit_hash": "aa17439b62f384511a5561ce308e9598b94d8989",
    "catalog_license": "CC0-1.0",
    "linked_resource_license": "NOASSERTION",
    "project_id": PROJECT_ID,
    "project_slug": "malloc-is-not-magic-implementing-your-own-memory-allocator",
    "project_title": "Malloc is not magic -- Implementing your own memory allocator",
    "source_reference": "README.md:247",
    "external_reference": "https://medium.com/p/e0354e914402",
}


def _clean(value: object, *, limit: int = 2_000) -> str:
    return redact(str(value), limit=limit).strip()


def _target(workspace: Path, relative: str) -> Path:
    candidate = Path(relative)
    if candidate.is_absolute() or not candidate.parts or any(
        part in {"", ".", ".."} for part in candidate.parts
    ):
        raise ValueError(f"unsafe generated path: {relative!r}")
    root = workspace.resolve()
    path = workspace / candidate
    try:
        path.resolve().relative_to(root)
    except ValueError as error:
        raise ValueError(f"generated path escapes workspace: {relative!r}") from error
    current = workspace
    for part in candidate.parts[:-1]:
        current = current / part
        if current.is_symlink():
            raise ValueError(f"generated path traverses symlink: {relative!r}")
        current.mkdir(exist_ok=True)
    if path.is_symlink():
        raise ValueError(f"refusing to overwrite symlink: {relative!r}")
    return path


def _write(workspace: Path, relative: str, content: str) -> None:
    rendered = dedent(content).lstrip("\n")
    if rendered and not rendered.endswith("\n"):
        rendered += "\n"
    _target(workspace, relative).write_text(
        rendered, encoding="utf-8", newline="\n"
    )


def _write_json(workspace: Path, relative: str, value: object) -> None:
    _write(
        workspace,
        relative,
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False),
    )


def _provenance(db: Database, payload: dict[str, Any]) -> dict[str, Any]:
    """Resolve the one active catalog record; payload cannot rewrite source identity."""

    result: dict[str, Any] = dict(_DEFAULT_PROVENANCE)
    result["lookup_status"] = "fallback_no_active_record"
    try:
        with db.connect() as connection:
            row = connection.execute(
                """
                SELECT s.source_id,s.name AS source_name,s.path AS source_path,
                       s.upstream_url,s.commit_hash,s.license AS catalog_license,
                       p.project_id,p.slug AS project_slug,p.title AS project_title,
                       p.upstream_reference AS external_reference,p.metadata_json,
                       s.metadata_json AS source_metadata_json
                FROM build_projects p
                JOIN sources s ON s.source_id=p.source_id
                WHERE p.project_id=? AND s.is_active=1
                """,
                (PROJECT_ID,),
            ).fetchone()
    except sqlite3.Error as error:
        result["lookup_status"] = (
            "database_lookup_unavailable: " + _clean(error, limit=300)
        )
        row = None
    if row is not None:
        for field in (
            "source_id",
            "source_name",
            "source_path",
            "upstream_url",
            "commit_hash",
            "catalog_license",
            "project_id",
            "project_slug",
            "project_title",
            "external_reference",
        ):
            if row[field] is not None:
                result[field] = _clean(row[field])
        for raw_metadata in (row["metadata_json"], row["source_metadata_json"]):
            try:
                metadata = json.loads(raw_metadata or "{}")
            except (TypeError, json.JSONDecodeError):
                continue
            if isinstance(metadata, dict) and metadata.get("linked_resource_license"):
                result["linked_resource_license"] = _clean(
                    metadata["linked_resource_license"]
                )
                break
        result["lookup_status"] = "active_database_record"
    if payload.get("job_id"):
        result["job_id"] = _clean(payload["job_id"])
    return result


_HEADER = r'''
    #ifndef LEARNING_FACTORY_ALLOCATOR_H
    #define LEARNING_FACTORY_ALLOCATOR_H

    #include <stddef.h>

    enum {
        LF_OK = 0,
        LF_ERR_ARGUMENT = 1,
        LF_ERR_ARENA_TOO_SMALL = 2,
        LF_ERR_INVALID_POINTER = 3,
        LF_ERR_DOUBLE_FREE = 4,
        LF_ERR_CORRUPT = 5
    };

    typedef struct lf_allocator_stats {
        size_t arena_bytes;
        size_t block_count;
        size_t live_blocks;
        size_t live_bytes;
        size_t free_blocks;
        size_t free_bytes;
        size_t largest_free_block;
    } lf_allocator_stats;

    size_t lf_state_size(void);
    const char *lf_architecture(void);
    /*
     * Portable C11 storage contract: state_storage and arena designate disjoint
     * regions returned by malloc/aligned_alloc (or equivalent storage with no
     * incompatible declared object type).  state_storage is max_align_t-aligned.
     * A casted, declared unsigned char array is outside this portable contract:
     * alignment alone does not change its effective type.
     */
    int lf_init(void *state_storage, size_t state_bytes, void *arena, size_t arena_bytes);
    void *lf_alloc(void *state_storage, size_t bytes);
    /*
     * LF_ERR_DOUBLE_FREE is returned while the freed block is still represented
     * in the physical list.  Coalescing removes interior block identities, so a
     * later stale pointer to a coalesced block is rejected as
     * LF_ERR_INVALID_POINTER rather than being accepted or dereferenced.
     */
    int lf_dealloc(void *state_storage, void *pointer);
    void *lf_resize(void *state_storage, void *pointer, size_t bytes);
    int lf_check(const void *state_storage);
    int lf_get_stats(const void *state_storage, lf_allocator_stats *output);

    #endif
'''


_LINEAR_ALLOCATOR_TEMPLATE = r'''
    #include "allocator.h"

    #include <stdint.h>
    #include <stdalign.h>
    #include <string.h>

    #define LF_STATE_MAGIC UINT64_C(0x4c46414c4c4f4331)
    #define LF_BLOCK_MAGIC UINT32_C(0xb10ca110)

    typedef struct block block;
    struct block {
        size_t size;
        block *previous;
        block *next;
        uint32_t magic;
        unsigned char is_free;
    };

    typedef struct state {
        uint64_t magic;
        unsigned char *begin;
        unsigned char *end;
        block *head;
    } state;

    #define LF_ALIGNMENT ((size_t)alignof(max_align_t))
    #define HEADER_SIZE ((sizeof(block) + LF_ALIGNMENT - 1U) & ~(LF_ALIGNMENT - 1U))

    static size_t aligned_size(size_t value) {
        if (value == 0U || value > SIZE_MAX - (LF_ALIGNMENT - 1U)) {
            return 0U;
        }
        return (value + LF_ALIGNMENT - 1U) & ~(LF_ALIGNMENT - 1U);
    }

    static int state_is_plausible(const state *allocator) {
        return allocator != NULL && allocator->magic == LF_STATE_MAGIC &&
               allocator->begin != NULL && allocator->end > allocator->begin &&
               allocator->head == (block *)allocator->begin;
    }

    static block *find_pointer(state *allocator, void *pointer) {
        block *item;
        size_t guard = 0U;
        size_t limit;
        if (!state_is_plausible(allocator) || pointer == NULL) {
            return NULL;
        }
        limit = (size_t)(allocator->end - allocator->begin) / HEADER_SIZE + 1U;
        for (item = allocator->head; item != NULL && guard++ < limit; item = item->next) {
            if (item->magic != LF_BLOCK_MAGIC) {
                return NULL;
            }
            if ((void *)((unsigned char *)item + HEADER_SIZE) == pointer) {
                return item;
            }
        }
        return NULL;
    }

    static void merge_next(block *item) {
        block *next = item->next;
        item->size += HEADER_SIZE + next->size;
        item->next = next->next;
        if (item->next != NULL) {
            item->next->previous = item;
        }
    }

    static block *split_block(block *item, size_t need) {
        block *remainder;
        if (item->size < need + HEADER_SIZE + LF_ALIGNMENT) {
            return NULL;
        }
        remainder = (block *)((unsigned char *)item + HEADER_SIZE + need);
        remainder->size = item->size - need - HEADER_SIZE;
        remainder->previous = item;
        remainder->next = item->next;
        remainder->magic = LF_BLOCK_MAGIC;
        remainder->is_free = 1U;
        if (remainder->next != NULL) {
            remainder->next->previous = remainder;
        }
        item->next = remainder;
        item->size = need;
        return remainder;
    }

    static block *select_block(state *allocator, size_t need) {
__SELECTION__
    }

    size_t lf_state_size(void) {
        return sizeof(state);
    }

    const char *lf_architecture(void) {
        return "__ARCHITECTURE__";
    }

    int lf_init(void *state_storage, size_t state_bytes, void *arena, size_t arena_bytes) {
        uintptr_t raw;
        uintptr_t aligned;
        uintptr_t state_raw;
        uintptr_t state_end;
        uintptr_t arena_end;
        size_t prefix;
        size_t usable;
        state *allocator;
        block *initial;
        if (state_storage == NULL || arena == NULL || state_bytes < sizeof(state) ||
            ((uintptr_t)state_storage % LF_ALIGNMENT) != 0U) {
            return LF_ERR_ARGUMENT;
        }
        raw = (uintptr_t)arena;
        state_raw = (uintptr_t)state_storage;
        if (raw > UINTPTR_MAX - (LF_ALIGNMENT - 1U) ||
            state_raw > UINTPTR_MAX - sizeof(state) ||
            arena_bytes > UINTPTR_MAX - raw) {
            return LF_ERR_ARGUMENT;
        }
        state_end = state_raw + sizeof(state);
        arena_end = raw + arena_bytes;
        if (state_raw < arena_end && raw < state_end) {
            return LF_ERR_ARGUMENT;
        }
        aligned = (raw + LF_ALIGNMENT - 1U) & ~(uintptr_t)(LF_ALIGNMENT - 1U);
        prefix = (size_t)(aligned - raw);
        if (arena_bytes <= prefix) {
            return LF_ERR_ARENA_TOO_SMALL;
        }
        usable = (arena_bytes - prefix) & ~(LF_ALIGNMENT - 1U);
        if (usable < HEADER_SIZE + LF_ALIGNMENT) {
            return LF_ERR_ARENA_TOO_SMALL;
        }
        memset(state_storage, 0, sizeof(state));
        allocator = (state *)state_storage;
        allocator->magic = LF_STATE_MAGIC;
        allocator->begin = (unsigned char *)aligned;
        allocator->end = allocator->begin + usable;
        allocator->head = (block *)allocator->begin;
        initial = allocator->head;
        initial->size = usable - HEADER_SIZE;
        initial->previous = NULL;
        initial->next = NULL;
        initial->magic = LF_BLOCK_MAGIC;
        initial->is_free = 1U;
        return LF_OK;
    }

    void *lf_alloc(void *state_storage, size_t bytes) {
        state *allocator = (state *)state_storage;
        size_t need = aligned_size(bytes);
        block *selected;
        if (need == 0U || !state_is_plausible(allocator)) {
            return NULL;
        }
        selected = select_block(allocator, need);
        if (selected == NULL) {
            return NULL;
        }
        (void)split_block(selected, need);
        selected->is_free = 0U;
        return (unsigned char *)selected + HEADER_SIZE;
    }

    int lf_dealloc(void *state_storage, void *pointer) {
        state *allocator = (state *)state_storage;
        block *item;
        if (pointer == NULL) {
            return LF_OK;
        }
        if (!state_is_plausible(allocator)) {
            return LF_ERR_ARGUMENT;
        }
        item = find_pointer(allocator, pointer);
        if (item == NULL) {
            return LF_ERR_INVALID_POINTER;
        }
        if (item->is_free != 0U) {
            return LF_ERR_DOUBLE_FREE;
        }
        item->is_free = 1U;
        if (item->next != NULL && item->next->is_free != 0U) {
            merge_next(item);
        }
        if (item->previous != NULL && item->previous->is_free != 0U) {
            item = item->previous;
            merge_next(item);
        }
        return LF_OK;
    }

    void *lf_resize(void *state_storage, void *pointer, size_t bytes) {
        state *allocator = (state *)state_storage;
        block *item;
        block *remainder;
        size_t need;
        void *replacement;
        if (pointer == NULL) {
            return lf_alloc(state_storage, bytes);
        }
        item = find_pointer(allocator, pointer);
        if (item == NULL || item->is_free != 0U) {
            return NULL;
        }
        if (bytes == 0U) {
            (void)lf_dealloc(state_storage, pointer);
            return NULL;
        }
        need = aligned_size(bytes);
        if (need == 0U) {
            return NULL;
        }
        if (need <= item->size) {
            remainder = split_block(item, need);
            if (remainder != NULL && remainder->next != NULL &&
                remainder->next->is_free != 0U) {
                merge_next(remainder);
            }
            return pointer;
        }
        if (item->next != NULL && item->next->is_free != 0U &&
            item->size + HEADER_SIZE + item->next->size >= need) {
            merge_next(item);
            (void)split_block(item, need);
            item->is_free = 0U;
            return pointer;
        }
        replacement = lf_alloc(state_storage, bytes);
        if (replacement == NULL) {
            return NULL;
        }
        memcpy(replacement, pointer, item->size < bytes ? item->size : bytes);
        (void)lf_dealloc(state_storage, pointer);
        return replacement;
    }

    int lf_check(const void *state_storage) {
        const state *allocator = (const state *)state_storage;
        const block *item;
        const block *previous = NULL;
        const unsigned char *expected;
        size_t guard = 0U;
        size_t limit;
        if (!state_is_plausible(allocator)) {
            return LF_ERR_CORRUPT;
        }
        expected = allocator->begin;
        limit = (size_t)(allocator->end - allocator->begin) / HEADER_SIZE + 1U;
        for (item = allocator->head; item != NULL; item = item->next) {
            const unsigned char *after;
            size_t remaining;
            if (++guard > limit || (const unsigned char *)item != expected) {
                return LF_ERR_CORRUPT;
            }
            remaining = (size_t)(allocator->end - expected);
            if (remaining < HEADER_SIZE || item->magic != LF_BLOCK_MAGIC ||
                item->previous != previous || item->size == 0U ||
                (item->size % LF_ALIGNMENT) != 0U ||
                item->size > remaining - HEADER_SIZE ||
                (previous != NULL && previous->is_free != 0U && item->is_free != 0U)) {
                return LF_ERR_CORRUPT;
            }
            after = expected + HEADER_SIZE + item->size;
            if (after > allocator->end ||
                (after == allocator->end && item->next != NULL) ||
                (after != allocator->end &&
                 (const unsigned char *)item->next != after)) {
                return LF_ERR_CORRUPT;
            }
            expected = after;
            previous = item;
        }
        return LF_OK;
    }

    int lf_get_stats(const void *state_storage, lf_allocator_stats *output) {
        const state *allocator = (const state *)state_storage;
        const block *item;
        if (output == NULL || lf_check(state_storage) != LF_OK) {
            return LF_ERR_CORRUPT;
        }
        memset(output, 0, sizeof(*output));
        output->arena_bytes = (size_t)(allocator->end - allocator->begin);
        for (item = allocator->head; item != NULL; item = item->next) {
            output->block_count++;
            if (item->is_free != 0U) {
                output->free_blocks++;
                output->free_bytes += item->size;
                if (item->size > output->largest_free_block) {
                    output->largest_free_block = item->size;
                }
            } else {
                output->live_blocks++;
                output->live_bytes += item->size;
            }
        }
        return LF_OK;
    }
'''


_FIRST_FIT_SELECTION = r'''
        block *item;
        for (item = allocator->head; item != NULL; item = item->next) {
            if (item->magic != LF_BLOCK_MAGIC) {
                return NULL;
            }
            if (item->is_free != 0U && item->size >= need) {
                return item;
            }
        }
        return NULL;
'''


_BEST_FIT_SELECTION = r'''
        block *item;
        block *best = NULL;
        for (item = allocator->head; item != NULL; item = item->next) {
            if (item->magic != LF_BLOCK_MAGIC) {
                return NULL;
            }
            if (item->is_free != 0U && item->size >= need &&
                (best == NULL || item->size < best->size)) {
                best = item;
            }
        }
        return best;
'''


def _linear_allocator(architecture: str, selection: str) -> str:
    return _LINEAR_ALLOCATOR_TEMPLATE.replace(
        "__ARCHITECTURE__", architecture
    ).replace("__SELECTION__", dedent(selection).rstrip())


_REFERENCE_C = _linear_allocator("address-ordered-first-fit", _FIRST_FIT_SELECTION)
_BEST_FIT_C = _linear_allocator("address-ordered-best-fit", _BEST_FIT_SELECTION)


_SEGREGATED_C = r'''
    #include "allocator.h"

    #include <stdint.h>
    #include <stdalign.h>
    #include <string.h>

    #define LF_STATE_MAGIC UINT64_C(0x4c4642494e533031)
    #define LF_BLOCK_MAGIC UINT32_C(0xb10ca110)
    #define BIN_COUNT 10U

    typedef struct block block;
    struct block {
        size_t size;
        block *previous;
        block *next;
        block *free_previous;
        block *free_next;
        uint32_t magic;
        unsigned char is_free;
    };

    typedef struct state {
        uint64_t magic;
        unsigned char *begin;
        unsigned char *end;
        block *head;
        block *bins[BIN_COUNT];
    } state;

    #define LF_ALIGNMENT ((size_t)alignof(max_align_t))
    #define HEADER_SIZE ((sizeof(block) + LF_ALIGNMENT - 1U) & ~(LF_ALIGNMENT - 1U))

    static size_t aligned_size(size_t value) {
        if (value == 0U || value > SIZE_MAX - (LF_ALIGNMENT - 1U)) {
            return 0U;
        }
        return (value + LF_ALIGNMENT - 1U) & ~(LF_ALIGNMENT - 1U);
    }

    static size_t bin_index(size_t size) {
        size_t index = 0U;
        size_t upper = 32U;
        while (index + 1U < BIN_COUNT && size > upper) {
            upper *= 2U;
            index++;
        }
        return index;
    }

    static int state_is_plausible(const state *allocator) {
        return allocator != NULL && allocator->magic == LF_STATE_MAGIC &&
               allocator->begin != NULL && allocator->end > allocator->begin &&
               allocator->head == (block *)allocator->begin;
    }

    static void free_remove(state *allocator, block *item) {
        size_t index = bin_index(item->size);
        if (item->free_previous != NULL) {
            item->free_previous->free_next = item->free_next;
        } else {
            allocator->bins[index] = item->free_next;
        }
        if (item->free_next != NULL) {
            item->free_next->free_previous = item->free_previous;
        }
        item->free_previous = NULL;
        item->free_next = NULL;
    }

    static void free_insert(state *allocator, block *item) {
        size_t index = bin_index(item->size);
        item->is_free = 1U;
        item->free_previous = NULL;
        item->free_next = allocator->bins[index];
        if (item->free_next != NULL) {
            item->free_next->free_previous = item;
        }
        allocator->bins[index] = item;
    }

    static void merge_physical(block *item) {
        block *next = item->next;
        item->size += HEADER_SIZE + next->size;
        item->next = next->next;
        if (item->next != NULL) {
            item->next->previous = item;
        }
    }

    static block *split_allocated(state *allocator, block *item, size_t need) {
        block *remainder;
        if (item->size < need + HEADER_SIZE + LF_ALIGNMENT) {
            item->is_free = 0U;
            return NULL;
        }
        remainder = (block *)((unsigned char *)item + HEADER_SIZE + need);
        remainder->size = item->size - need - HEADER_SIZE;
        remainder->previous = item;
        remainder->next = item->next;
        remainder->free_previous = NULL;
        remainder->free_next = NULL;
        remainder->magic = LF_BLOCK_MAGIC;
        remainder->is_free = 1U;
        if (remainder->next != NULL) {
            remainder->next->previous = remainder;
        }
        item->next = remainder;
        item->size = need;
        item->is_free = 0U;
        free_insert(allocator, remainder);
        return remainder;
    }

    static block *find_pointer(state *allocator, void *pointer) {
        block *item;
        size_t guard = 0U;
        size_t limit;
        if (!state_is_plausible(allocator) || pointer == NULL) {
            return NULL;
        }
        limit = (size_t)(allocator->end - allocator->begin) / HEADER_SIZE + 1U;
        for (item = allocator->head; item != NULL && guard++ < limit; item = item->next) {
            if (item->magic != LF_BLOCK_MAGIC) {
                return NULL;
            }
            if ((void *)((unsigned char *)item + HEADER_SIZE) == pointer) {
                return item;
            }
        }
        return NULL;
    }

    size_t lf_state_size(void) {
        return sizeof(state);
    }

    const char *lf_architecture(void) {
        return "segregated-size-class-bins";
    }

    int lf_init(void *state_storage, size_t state_bytes, void *arena, size_t arena_bytes) {
        uintptr_t raw;
        uintptr_t aligned;
        uintptr_t state_raw;
        uintptr_t state_end;
        uintptr_t arena_end;
        size_t prefix;
        size_t usable;
        state *allocator;
        block *initial;
        if (state_storage == NULL || arena == NULL || state_bytes < sizeof(state) ||
            ((uintptr_t)state_storage % LF_ALIGNMENT) != 0U) {
            return LF_ERR_ARGUMENT;
        }
        raw = (uintptr_t)arena;
        state_raw = (uintptr_t)state_storage;
        if (raw > UINTPTR_MAX - (LF_ALIGNMENT - 1U) ||
            state_raw > UINTPTR_MAX - sizeof(state) ||
            arena_bytes > UINTPTR_MAX - raw) {
            return LF_ERR_ARGUMENT;
        }
        state_end = state_raw + sizeof(state);
        arena_end = raw + arena_bytes;
        if (state_raw < arena_end && raw < state_end) {
            return LF_ERR_ARGUMENT;
        }
        aligned = (raw + LF_ALIGNMENT - 1U) & ~(uintptr_t)(LF_ALIGNMENT - 1U);
        prefix = (size_t)(aligned - raw);
        if (arena_bytes <= prefix) {
            return LF_ERR_ARENA_TOO_SMALL;
        }
        usable = (arena_bytes - prefix) & ~(LF_ALIGNMENT - 1U);
        if (usable < HEADER_SIZE + LF_ALIGNMENT) {
            return LF_ERR_ARENA_TOO_SMALL;
        }
        memset(state_storage, 0, sizeof(state));
        allocator = (state *)state_storage;
        allocator->magic = LF_STATE_MAGIC;
        allocator->begin = (unsigned char *)aligned;
        allocator->end = allocator->begin + usable;
        allocator->head = (block *)allocator->begin;
        initial = allocator->head;
        initial->size = usable - HEADER_SIZE;
        initial->previous = NULL;
        initial->next = NULL;
        initial->free_previous = NULL;
        initial->free_next = NULL;
        initial->magic = LF_BLOCK_MAGIC;
        initial->is_free = 1U;
        free_insert(allocator, initial);
        return LF_OK;
    }

    void *lf_alloc(void *state_storage, size_t bytes) {
        state *allocator = (state *)state_storage;
        size_t need = aligned_size(bytes);
        size_t index;
        block *item;
        if (need == 0U || !state_is_plausible(allocator)) {
            return NULL;
        }
        for (index = bin_index(need); index < BIN_COUNT; index++) {
            for (item = allocator->bins[index]; item != NULL; item = item->free_next) {
                if (item->size >= need) {
                    free_remove(allocator, item);
                    (void)split_allocated(allocator, item, need);
                    item->is_free = 0U;
                    return (unsigned char *)item + HEADER_SIZE;
                }
            }
        }
        return NULL;
    }

    int lf_dealloc(void *state_storage, void *pointer) {
        state *allocator = (state *)state_storage;
        block *item;
        if (pointer == NULL) {
            return LF_OK;
        }
        if (!state_is_plausible(allocator)) {
            return LF_ERR_ARGUMENT;
        }
        item = find_pointer(allocator, pointer);
        if (item == NULL) {
            return LF_ERR_INVALID_POINTER;
        }
        if (item->is_free != 0U) {
            return LF_ERR_DOUBLE_FREE;
        }
        item->is_free = 1U;
        if (item->next != NULL && item->next->is_free != 0U) {
            free_remove(allocator, item->next);
            merge_physical(item);
        }
        if (item->previous != NULL && item->previous->is_free != 0U) {
            block *previous = item->previous;
            free_remove(allocator, previous);
            merge_physical(previous);
            item = previous;
        }
        free_insert(allocator, item);
        return LF_OK;
    }

    void *lf_resize(void *state_storage, void *pointer, size_t bytes) {
        state *allocator = (state *)state_storage;
        block *item;
        block *remainder;
        size_t need;
        size_t old_size;
        void *replacement;
        if (pointer == NULL) {
            return lf_alloc(state_storage, bytes);
        }
        item = find_pointer(allocator, pointer);
        if (item == NULL || item->is_free != 0U) {
            return NULL;
        }
        if (bytes == 0U) {
            (void)lf_dealloc(state_storage, pointer);
            return NULL;
        }
        need = aligned_size(bytes);
        if (need == 0U) {
            return NULL;
        }
        if (need <= item->size) {
            remainder = split_allocated(allocator, item, need);
            if (remainder != NULL && remainder->next != NULL &&
                remainder->next->is_free != 0U) {
                free_remove(allocator, remainder);
                free_remove(allocator, remainder->next);
                merge_physical(remainder);
                free_insert(allocator, remainder);
            }
            return pointer;
        }
        if (item->next != NULL && item->next->is_free != 0U &&
            item->size + HEADER_SIZE + item->next->size >= need) {
            free_remove(allocator, item->next);
            merge_physical(item);
            (void)split_allocated(allocator, item, need);
            item->is_free = 0U;
            return pointer;
        }
        old_size = item->size;
        replacement = lf_alloc(state_storage, bytes);
        if (replacement == NULL) {
            return NULL;
        }
        memcpy(replacement, pointer, old_size < bytes ? old_size : bytes);
        (void)lf_dealloc(state_storage, pointer);
        return replacement;
    }

    static int physical_contains(
        const state *allocator, const block *candidate, size_t block_limit
    ) {
        const block *item;
        size_t guard = 0U;
        for (item = allocator->head; item != NULL && guard++ < block_limit;
             item = item->next) {
            if (item == candidate) {
                return 1;
            }
        }
        return 0;
    }

    int lf_check(const void *state_storage) {
        const state *allocator = (const state *)state_storage;
        const block *item;
        const block *previous = NULL;
        const unsigned char *expected;
        size_t guard = 0U;
        size_t limit;
        size_t index;
        size_t physical_blocks = 0U;
        if (!state_is_plausible(allocator)) {
            return LF_ERR_CORRUPT;
        }
        expected = allocator->begin;
        limit = (size_t)(allocator->end - allocator->begin) / HEADER_SIZE + 1U;
        for (item = allocator->head; item != NULL; item = item->next) {
            const unsigned char *after;
            size_t remaining;
            if (++guard > limit || (const unsigned char *)item != expected) {
                return LF_ERR_CORRUPT;
            }
            remaining = (size_t)(allocator->end - expected);
            if (remaining < HEADER_SIZE || item->magic != LF_BLOCK_MAGIC ||
                item->previous != previous || item->size == 0U ||
                (item->size % LF_ALIGNMENT) != 0U ||
                item->size > remaining - HEADER_SIZE ||
                (previous != NULL && previous->is_free != 0U && item->is_free != 0U)) {
                return LF_ERR_CORRUPT;
            }
            after = expected + HEADER_SIZE + item->size;
            if (after > allocator->end ||
                (after == allocator->end && item->next != NULL) ||
                (after != allocator->end &&
                 (const unsigned char *)item->next != after)) {
                return LF_ERR_CORRUPT;
            }
            physical_blocks++;
            expected = after;
            previous = item;
        }
        if (physical_blocks == 0U) {
            return LF_ERR_CORRUPT;
        }

        /* Validate every bin node before dereferencing its links. */
        for (index = 0U; index < BIN_COUNT; index++) {
            const block *free_item = allocator->bins[index];
            const block *free_previous = NULL;
            size_t free_guard = 0U;
            while (free_item != NULL) {
                if (++free_guard > physical_blocks ||
                    !physical_contains(allocator, free_item, physical_blocks)) {
                    return LF_ERR_CORRUPT;
                }
                if (free_item->magic != LF_BLOCK_MAGIC || free_item->is_free == 0U ||
                    bin_index(free_item->size) != index ||
                    free_item->free_previous != free_previous) {
                    return LF_ERR_CORRUPT;
                }
                free_previous = free_item;
                free_item = free_item->free_next;
            }
        }

        /* Every physical free block must occur exactly once; allocated blocks never occur. */
        for (item = allocator->head; item != NULL; item = item->next) {
            size_t occurrences = 0U;
            for (index = 0U; index < BIN_COUNT; index++) {
                const block *free_item;
                size_t free_guard = 0U;
                for (free_item = allocator->bins[index]; free_item != NULL;
                     free_item = free_item->free_next) {
                    if (++free_guard > physical_blocks) {
                        return LF_ERR_CORRUPT;
                    }
                    if (free_item == item) {
                        occurrences++;
                    }
                }
            }
            if ((item->is_free != 0U && occurrences != 1U) ||
                (item->is_free == 0U && occurrences != 0U)) {
                return LF_ERR_CORRUPT;
            }
        }
        return LF_OK;
    }

    int lf_get_stats(const void *state_storage, lf_allocator_stats *output) {
        const state *allocator = (const state *)state_storage;
        const block *item;
        if (output == NULL || lf_check(state_storage) != LF_OK) {
            return LF_ERR_CORRUPT;
        }
        memset(output, 0, sizeof(*output));
        output->arena_bytes = (size_t)(allocator->end - allocator->begin);
        for (item = allocator->head; item != NULL; item = item->next) {
            output->block_count++;
            if (item->is_free != 0U) {
                output->free_blocks++;
                output->free_bytes += item->size;
                if (item->size > output->largest_free_block) {
                    output->largest_free_block = item->size;
                }
            } else {
                output->live_blocks++;
                output->live_bytes += item->size;
            }
        }
        return LF_OK;
    }
'''


_STARTER_C = r'''
    #include "allocator.h"

    size_t lf_state_size(void) {
        /* Decide what durable allocator state belongs outside the managed arena. */
        return 0U;
    }

    const char *lf_architecture(void) {
        return "learner-design-not-implemented";
    }

    int lf_init(void *state_storage, size_t state_bytes, void *arena, size_t arena_bytes) {
        (void)state_storage;
        (void)state_bytes;
        (void)arena;
        (void)arena_bytes;
        return LF_ERR_ARGUMENT;
    }

    void *lf_alloc(void *state_storage, size_t bytes) {
        (void)state_storage;
        (void)bytes;
        return NULL;
    }

    int lf_dealloc(void *state_storage, void *pointer) {
        (void)state_storage;
        (void)pointer;
        return LF_ERR_ARGUMENT;
    }

    void *lf_resize(void *state_storage, void *pointer, size_t bytes) {
        (void)state_storage;
        (void)pointer;
        (void)bytes;
        return NULL;
    }

    int lf_check(const void *state_storage) {
        (void)state_storage;
        return LF_ERR_CORRUPT;
    }

    int lf_get_stats(const void *state_storage, lf_allocator_stats *output) {
        (void)state_storage;
        (void)output;
        return LF_ERR_CORRUPT;
    }
'''


_PUBLIC_TEST = r'''
    #include "allocator.h"

    #include <stdint.h>
    #include <stdio.h>
    #include <stdalign.h>
    #include <stdlib.h>
    #include <string.h>

    #define REQUIRE(condition, message) do { \
        if (!(condition)) { \
            fprintf(stderr, "public contract: %s (line %d)\n", message, __LINE__); \
            return 1; \
        } \
    } while (0)

    int main(void) {
        void *state_storage;
        unsigned char *arena;
        lf_allocator_stats stats;
        unsigned char *first;
        unsigned char *second;
        size_t index;
        size_t state_bytes = lf_state_size();

        REQUIRE(state_bytes > 0U && state_bytes <= 512U, "state contract exceeds fixture");
        state_storage = malloc(state_bytes);
        arena = (unsigned char *)malloc(32768U);
        REQUIRE(state_storage != NULL && arena != NULL, "fixture storage allocation failed");
        REQUIRE(lf_init(state_storage, state_bytes, arena, 32768U) == LF_OK,
                "initialization failed");
        REQUIRE(lf_alloc(state_storage, 0U) == NULL, "zero-size allocation must be NULL");
        first = (unsigned char *)lf_alloc(state_storage, 37U);
        second = (unsigned char *)lf_alloc(state_storage, 200U);
        REQUIRE(first != NULL && second != NULL && first != second, "distinct allocations failed");
        REQUIRE(((uintptr_t)first % alignof(max_align_t)) == 0U, "first pointer is misaligned");
        REQUIRE(((uintptr_t)second % alignof(max_align_t)) == 0U, "second pointer is misaligned");
        memset(first, 0xa5, 37U);
        memset(second, 0x5a, 200U);
        for (index = 0U; index < 37U; index++) {
            REQUIRE(first[index] == 0xa5U, "first allocation changed unexpectedly");
        }
        REQUIRE(lf_check(state_storage) == LF_OK, "invariants failed after allocation");
        REQUIRE(lf_dealloc(state_storage, first) == LF_OK, "free failed");
        REQUIRE(lf_dealloc(state_storage, first) == LF_ERR_DOUBLE_FREE,
                "double free was not rejected");
        REQUIRE(lf_dealloc(state_storage, second) == LF_OK, "second free failed");
        REQUIRE(lf_get_stats(state_storage, &stats) == LF_OK, "stats failed");
        REQUIRE(stats.live_blocks == 0U && stats.free_blocks == 1U,
                "adjacent free blocks were not fully coalesced");
        free(arena);
        free(state_storage);
        puts("public allocator contract passed");
        return 0;
    }
'''


_HIDDEN_TEST = r'''
    #include "allocator.h"

    #include <stdint.h>
    #include <stdio.h>
    #include <stdalign.h>
    #include <stdlib.h>
    #include <string.h>

    #define REQUIRE(condition, message) do { \
        if (!(condition)) { \
            fprintf(stderr, "withheld contract: %s (line %d)\n", message, __LINE__); \
            return 1; \
        } \
    } while (0)

    int main(void) {
        void *state_storage;
        unsigned char *arena_storage;
        void *overlap_storage;
        lf_allocator_stats before;
        lf_allocator_stats after;
        unsigned char *a;
        unsigned char *b;
        unsigned char *c;
        unsigned char *grown;
        unsigned char outsider = 0U;
        size_t index;
        size_t state_bytes = lf_state_size();

        REQUIRE(state_bytes > 0U && state_bytes <= 512U, "state contract exceeds fixture");
        state_storage = malloc(state_bytes);
        arena_storage = (unsigned char *)malloc(65536U);
        overlap_storage = malloc(512U);
        REQUIRE(state_storage != NULL && arena_storage != NULL && overlap_storage != NULL,
                "fixture storage allocation failed");
        REQUIRE(lf_init(overlap_storage, state_bytes, overlap_storage, 512U) == LF_ERR_ARGUMENT,
                "overlapping state and arena storage was accepted");
        REQUIRE(lf_init(state_storage, state_bytes, arena_storage + 1, 65535U) == LF_OK,
                "unaligned arena base was not normalized");
        a = (unsigned char *)lf_alloc(state_storage, 113U);
        b = (unsigned char *)lf_alloc(state_storage, 257U);
        c = (unsigned char *)lf_alloc(state_storage, 521U);
        REQUIRE(a != NULL && b != NULL && c != NULL, "setup allocation failed");
        memset(b, 0x3c, 257U);
        REQUIRE(lf_dealloc(state_storage, c) == LF_OK, "tail free failed");
        grown = (unsigned char *)lf_resize(state_storage, b, 900U);
        REQUIRE(grown != NULL, "growth into or around a free neighbor failed");
        for (index = 0U; index < 257U; index++) {
            REQUIRE(grown[index] == 0x3cU, "resize did not preserve the old prefix");
        }
        REQUIRE(lf_resize(state_storage, grown, 80U) == grown, "shrink should stay in place");
        REQUIRE(lf_dealloc(state_storage, &outsider) == LF_ERR_INVALID_POINTER,
                "foreign pointer was accepted");
        REQUIRE(lf_get_stats(state_storage, &before) == LF_OK, "pre-failure stats failed");
        REQUIRE(lf_alloc(state_storage, SIZE_MAX) == NULL, "overflowing request was accepted");
        REQUIRE(lf_get_stats(state_storage, &after) == LF_OK, "post-failure stats failed");
        REQUIRE(before.block_count == after.block_count &&
                before.live_bytes == after.live_bytes && before.free_bytes == after.free_bytes,
                "failed allocation changed allocator state");
        REQUIRE(lf_dealloc(state_storage, a) == LF_OK, "a free failed");
        REQUIRE(lf_dealloc(state_storage, grown) == LF_OK, "grown free failed");
        REQUIRE(lf_dealloc(state_storage, grown) == LF_ERR_INVALID_POINTER,
                "stale pointer to a coalesced block was not safely rejected");
        REQUIRE(lf_check(state_storage) == LF_OK, "final invariant check failed");
        REQUIRE(lf_get_stats(state_storage, &after) == LF_OK &&
                after.live_blocks == 0U && after.free_blocks == 1U,
                "final arena did not coalesce");
        free(overlap_storage);
        free(arena_storage);
        free(state_storage);
        printf("withheld allocator contract passed for %s\n", lf_architecture());
        return 0;
    }
'''


_SEGREGATED_INTEGRITY_TEST = r'''
    #include "allocator.h"

    #include <stdio.h>
    #include <stdalign.h>
    #include <stdlib.h>

    /* Deliberately white-box and sealed: exercise the alternative's second topology. */
    #include "../alternatives/segregated_bins/allocator.c"

    #define REQUIRE(condition, message) do { \
        if (!(condition)) { \
            fprintf(stderr, "segregated integrity: %s (line %d)\n", message, __LINE__); \
            return 1; \
        } \
    } while (0)

    int main(void) {
        void *state_storage;
        unsigned char *arena;
        state *allocator;
        block *initial;
        block *forged;
        void *payload;
        size_t index;

        state_storage = malloc(lf_state_size());
        arena = (unsigned char *)malloc(8192U);
        REQUIRE(state_storage != NULL && arena != NULL, "fixture storage allocation failed");
        REQUIRE(lf_init(state_storage, lf_state_size(), arena, 8192U) == LF_OK,
                "missing-node fixture initialization failed");
        allocator = (state *)state_storage;
        initial = allocator->head;
        index = bin_index(initial->size);
        allocator->bins[index] = NULL;
        REQUIRE(lf_check(state_storage) == LF_ERR_CORRUPT,
                "missing physical free block was accepted");

        REQUIRE(lf_init(state_storage, lf_state_size(), arena, 8192U) == LF_OK,
                "wrong-bin fixture initialization failed");
        allocator = (state *)state_storage;
        initial = allocator->head;
        index = bin_index(initial->size);
        allocator->bins[index] = NULL;
        allocator->bins[(index + 1U) % BIN_COUNT] = initial;
        REQUIRE(lf_check(state_storage) == LF_ERR_CORRUPT,
                "size-class mismatch was accepted");

        REQUIRE(lf_init(state_storage, lf_state_size(), arena, 8192U) == LF_OK,
                "duplicate-node fixture initialization failed");
        allocator = (state *)state_storage;
        initial = allocator->head;
        initial->free_next = initial;
        REQUIRE(lf_check(state_storage) == LF_ERR_CORRUPT,
                "duplicate/cyclic bin node was accepted");

        REQUIRE(lf_init(state_storage, lf_state_size(), arena, 8192U) == LF_OK,
                "extraneous-node fixture initialization failed");
        allocator = (state *)state_storage;
        payload = lf_alloc(state_storage, 256U);
        REQUIRE(payload != NULL, "extraneous-node fixture allocation failed");
        forged = (block *)payload;
        forged->size = LF_ALIGNMENT;
        forged->previous = NULL;
        forged->next = NULL;
        forged->free_previous = NULL;
        forged->free_next = NULL;
        forged->magic = LF_BLOCK_MAGIC;
        forged->is_free = 1U;
        allocator->bins[bin_index(forged->size)] = forged;
        REQUIRE(lf_check(state_storage) == LF_ERR_CORRUPT,
                "extraneous non-physical bin node was accepted");

        free(arena);
        free(state_storage);
        puts("segregated bins reject missing, inconsistent, duplicate, and extraneous nodes");
        return 0;
    }
'''


_MODEL_TEST = r'''
    #include "allocator.h"

    #include <stdint.h>
    #include <stdio.h>
    #include <stdalign.h>
    #include <stdlib.h>
    #include <string.h>

    #define SLOT_COUNT 96U
    #define ITERATIONS 4000U
    #define ARENA_BYTES 32768U

    typedef struct slot {
        unsigned char *pointer;
        size_t size;
        unsigned char tag;
    } slot;

    static uint32_t next_random(uint32_t *state) {
        uint32_t value = *state;
        value ^= value << 13;
        value ^= value >> 17;
        value ^= value << 5;
        *state = value;
        return value;
    }

    static int verify_slot(const slot *item) {
        size_t index;
        if (item->pointer == NULL) {
            return 1;
        }
        for (index = 0U; index < item->size; index++) {
            if (item->pointer[index] != item->tag) {
                return 0;
            }
        }
        return 1;
    }

    int main(void) {
        void *state_storage = malloc(lf_state_size());
        unsigned char *arena = (unsigned char *)malloc(ARENA_BYTES);
        slot slots[SLOT_COUNT] = {{0}};
        uint32_t random_state = UINT32_C(0x20260830);
        size_t operation;
        size_t completed = 0U;
        size_t allocation_failures = 0U;
        size_t resize_failures = 0U;

        if (state_storage == NULL || arena == NULL ||
            lf_init(state_storage, lf_state_size(), arena, ARENA_BYTES) != LF_OK) {
            fputs("model: initialization failed\n", stderr);
            return 1;
        }
        for (operation = 0U; operation < ITERATIONS; operation++) {
            size_t index = (size_t)(next_random(&random_state) % SLOT_COUNT);
            uint32_t choice = next_random(&random_state) % 100U;
            slot *item = &slots[index];
            size_t check_index;
            for (check_index = 0U; check_index < SLOT_COUNT; check_index++) {
                if (!verify_slot(&slots[check_index])) {
                    fprintf(stderr, "model: payload corruption in slot %zu at operation %zu\n",
                            check_index, operation);
                    return 1;
                }
            }
            if (item->pointer == NULL && choice < 62U) {
                size_t size = 1U + (size_t)(next_random(&random_state) % 1536U);
                unsigned char *pointer = (unsigned char *)lf_alloc(state_storage, size);
                if (pointer == NULL) {
                    allocation_failures++;
                } else {
                    uintptr_t address = (uintptr_t)pointer;
                    uintptr_t arena_begin = (uintptr_t)arena;
                    uintptr_t arena_end = arena_begin + ARENA_BYTES;
                    if ((address % alignof(max_align_t)) != 0U || address < arena_begin ||
                        address > arena_end || size > (size_t)(arena_end - address)) {
                        fputs("model: allocation pointer violates alignment or arena bounds\n", stderr);
                        return 1;
                    }
                    item->pointer = pointer;
                    item->size = size;
                    item->tag = (unsigned char)(1U + (next_random(&random_state) % 254U));
                    memset(item->pointer, item->tag, item->size);
                    completed++;
                }
            } else if (item->pointer != NULL && choice < 35U) {
                if (lf_dealloc(state_storage, item->pointer) != LF_OK) {
                    fputs("model: valid free rejected\n", stderr);
                    return 1;
                }
                memset(item, 0, sizeof(*item));
                completed++;
            } else if (item->pointer != NULL && choice < 75U) {
                size_t new_size = 1U + (size_t)(next_random(&random_state) % 2048U);
                size_t preserved = item->size < new_size ? item->size : new_size;
                unsigned char *replacement =
                    (unsigned char *)lf_resize(state_storage, item->pointer, new_size);
                if (replacement == NULL) {
                    if (!verify_slot(item)) {
                        fputs("model: failed resize modified original allocation\n", stderr);
                        return 1;
                    }
                    allocation_failures++;
                    resize_failures++;
                } else {
                    size_t byte;
                    uintptr_t address = (uintptr_t)replacement;
                    uintptr_t arena_begin = (uintptr_t)arena;
                    uintptr_t arena_end = arena_begin + ARENA_BYTES;
                    if ((address % alignof(max_align_t)) != 0U || address < arena_begin ||
                        address > arena_end || new_size > (size_t)(arena_end - address)) {
                        fputs("model: resized pointer violates alignment or arena bounds\n", stderr);
                        return 1;
                    }
                    for (byte = 0U; byte < preserved; byte++) {
                        if (replacement[byte] != item->tag) {
                            fputs("model: resize prefix mismatch\n", stderr);
                            return 1;
                        }
                    }
                    item->pointer = replacement;
                    item->size = new_size;
                    memset(item->pointer, item->tag, item->size);
                    completed++;
                }
            }
            if (lf_check(state_storage) != LF_OK) {
                fprintf(stderr, "model: invariant failure at operation %zu\n", operation);
                return 1;
            }
        }
        for (operation = 0U; operation < SLOT_COUNT; operation++) {
            if (!verify_slot(&slots[operation])) {
                fputs("model: final payload mismatch\n", stderr);
                return 1;
            }
            if (slots[operation].pointer != NULL &&
                lf_dealloc(state_storage, slots[operation].pointer) != LF_OK) {
                fputs("model: cleanup free failed\n", stderr);
                return 1;
            }
        }
        if (lf_check(state_storage) != LF_OK) {
            fputs("model: final invariant failure\n", stderr);
            return 1;
        }
        if (resize_failures == 0U) {
            fputs("model: fixture did not exercise resize failure atomicity\n", stderr);
            return 1;
        }
        printf("deterministic model passed architecture=%s seed=0x20260830 "
               "iterations=%u completed=%zu allocation_failures=%zu resize_failures=%zu\n",
               lf_architecture(), (unsigned int)ITERATIONS, completed, allocation_failures,
               resize_failures);
        free(arena);
        free(state_storage);
        return 0;
    }
'''


_BENCHMARK_C = r'''
    #define _POSIX_C_SOURCE 200809L
    #include "allocator.h"

    #include <stdint.h>
    #include <stdio.h>
    #include <stdalign.h>
    #include <stdlib.h>
    #include <string.h>
    #include <time.h>

    #define TIMED_OPERATIONS 80000U
    #define SLOT_COUNT 256U
    #define ARENA_BYTES 2097152U

    static uint64_t nanoseconds(void) {
        struct timespec value;
        if (clock_gettime(CLOCK_MONOTONIC, &value) != 0) {
            return 0U;
        }
        return (uint64_t)value.tv_sec * UINT64_C(1000000000) + (uint64_t)value.tv_nsec;
    }

    int main(void) {
        void *state_storage = malloc(lf_state_size());
        unsigned char *arena = (unsigned char *)malloc(ARENA_BYTES);
        void *slots[SLOT_COUNT] = {0};
        size_t sizes[SLOT_COUNT] = {0};
        lf_allocator_stats stats;
        uint64_t start;
        uint64_t end;
        size_t operation;
        size_t successful_allocations = 0U;
        size_t failed_allocations = 0U;
        double external_fragmentation;

        if (state_storage == NULL || arena == NULL ||
            lf_init(state_storage, lf_state_size(), arena, ARENA_BYTES) != LF_OK) {
            return 2;
        }
        start = nanoseconds();
        for (operation = 0U; operation < TIMED_OPERATIONS; operation++) {
            size_t index = (operation * 73U + 19U) % SLOT_COUNT;
            if (slots[index] != NULL) {
                if (lf_dealloc(state_storage, slots[index]) != LF_OK) {
                    return 3;
                }
                slots[index] = NULL;
            } else {
                size_t size = 8U + ((operation * 131U) % 2041U);
                slots[index] = lf_alloc(state_storage, size);
                sizes[index] = size;
                if (slots[index] != NULL) {
                    unsigned char *bytes = (unsigned char *)slots[index];
                    bytes[0] = (unsigned char)operation;
                    bytes[size - 1U] = (unsigned char)(operation >> 8);
                    successful_allocations++;
                } else {
                    failed_allocations++;
                }
            }
        }
        end = nanoseconds();
        if (end <= start || lf_check(state_storage) != LF_OK) {
            return 4;
        }
        for (operation = 0U; operation < SLOT_COUNT; operation++) {
            if (slots[operation] != NULL) {
                unsigned char *bytes = (unsigned char *)slots[operation];
                (void)sizes[operation];
                bytes[0] ^= 0U;
                if (lf_dealloc(state_storage, slots[operation]) != LF_OK) {
                    return 5;
                }
                slots[operation] = NULL;
            }
        }

        if (lf_init(state_storage, lf_state_size(), arena, ARENA_BYTES) != LF_OK) {
            return 6;
        }
        for (operation = 0U; operation < 900U; operation++) {
            size_t index = operation % SLOT_COUNT;
            size_t size = 24U + ((operation * 97U) % 3072U);
            if (slots[index] != NULL) {
                if (lf_dealloc(state_storage, slots[index]) != LF_OK) {
                    return 7;
                }
            }
            slots[index] = lf_alloc(state_storage, size);
        }
        for (operation = 0U; operation < SLOT_COUNT; operation += 2U) {
            if (slots[operation] != NULL) {
                if (lf_dealloc(state_storage, slots[operation]) != LF_OK) {
                    return 8;
                }
                slots[operation] = NULL;
            }
        }
        if (lf_get_stats(state_storage, &stats) != LF_OK || stats.free_bytes == 0U) {
            return 9;
        }
        external_fragmentation = 1.0 -
            ((double)stats.largest_free_block / (double)stats.free_bytes);
        printf("{\"architecture\":\"%s\",\"timed_operations\":%u,"
               "\"elapsed_ns\":%llu,\"operations_per_second\":%.3f,"
               "\"successful_allocations\":%zu,\"failed_allocations\":%zu,"
               "\"fragmentation_workload\":{\"block_count\":%zu,"
               "\"live_blocks\":%zu,\"live_bytes\":%zu,\"free_blocks\":%zu,"
               "\"free_bytes\":%zu,\"largest_free_block\":%zu,"
               "\"external_fragmentation_ratio\":%.9f}}\n",
               lf_architecture(), (unsigned int)TIMED_OPERATIONS,
               (unsigned long long)(end - start),
               (double)TIMED_OPERATIONS * 1000000000.0 / (double)(end - start),
               successful_allocations, failed_allocations, stats.block_count,
               stats.live_blocks, stats.live_bytes, stats.free_blocks,
               stats.free_bytes, stats.largest_free_block, external_fragmentation);
        free(arena);
        free(state_storage);
        return 0;
    }
'''


_DEBUG_REGRESSION = r'''
    #include "allocator.h"

    #include <stdio.h>
    #include <stdlib.h>

    int main(void) {
        void *state_storage = malloc(lf_state_size());
        unsigned char *arena = (unsigned char *)malloc(8192U);
        void *first;
        void *middle;
        void *last;
        if (state_storage == NULL || arena == NULL ||
            lf_init(state_storage, lf_state_size(), arena, 8192U) != LF_OK) {
            return 2;
        }
        first = lf_alloc(state_storage, 128U);
        middle = lf_alloc(state_storage, 256U);
        last = lf_alloc(state_storage, 128U);
        if (first == NULL || middle == NULL || last == NULL) {
            return 3;
        }
        if (lf_dealloc(state_storage, middle) != LF_OK ||
            lf_dealloc(state_storage, first) != LF_OK) {
            return 4;
        }
        if (lf_check(state_storage) != LF_OK) {
            fputs("detected allocator metadata corruption after adjacent coalescing\n", stderr);
            return 1;
        }
        if (lf_dealloc(state_storage, last) != LF_OK || lf_check(state_storage) != LF_OK) {
            return 5;
        }
        free(arena);
        free(state_storage);
        puts("adjacent coalescing retained the exact physical arena span");
        return 0;
    }
'''


_REVIEW_PROPOSAL = r'''
    #include <stddef.h>

    /* Proposed PR: centralize rounding so the fast path performs one expression. */
    size_t proposed_round_request(size_t bytes, size_t alignment) {
        return (bytes + alignment - 1U) & ~(alignment - 1U);
    }
'''


_REVIEW_DEMONSTRATION = r'''
    #include <stdint.h>
    #include <stdio.h>

    size_t proposed_round_request(size_t bytes, size_t alignment);

    int main(void) {
        size_t rounded = proposed_round_request(SIZE_MAX, 16U);
        if (rounded != 0U) {
            fputs("fixture assumption changed\n", stderr);
            return 1;
        }
        puts("reproduced request-size overflow: SIZE_MAX rounded down to zero");
        return 0;
    }
'''


_BUILD_SCRIPT = r'''
    from __future__ import annotations

    import json
    import os
    import platform
    import shutil
    import subprocess
    from pathlib import Path


    ROOT = Path(__file__).resolve().parents[1]
    OUTPUT = ROOT / "validation-output"
    BIN = OUTPUT / "bin"
    GCC = shutil.which("gcc")
    FLAGS = [
        "-std=c11", "-Wall", "-Wextra", "-Werror", "-pedantic", "-O2",
        "-fno-omit-frame-pointer", "-I", str(ROOT / "include"),
    ]
    IMPLEMENTATIONS = {
        "reference": ROOT / "sealed/reference/allocator.c",
        "best-fit": ROOT / "sealed/alternatives/best_fit/allocator.c",
        "segregated-bins": ROOT / "sealed/alternatives/segregated_bins/allocator.c",
    }


    def command(argv: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            argv,
            cwd=ROOT,
            env={
                "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
                "LANG": "C.UTF-8",
                "LC_ALL": "C.UTF-8",
                "ASAN_OPTIONS": "detect_leaks=0:abort_on_error=1",
                "UBSAN_OPTIONS": "halt_on_error=1",
            },
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=check,
        )


    def compile_binary(name: str, sources: list[Path], extra: list[str] | None = None) -> None:
        assert GCC is not None
        argv = [GCC, *FLAGS, *(extra or []), *map(str, sources), "-o", str(BIN / name)]
        result = command(argv, check=False)
        if result.returncode != 0:
            raise SystemExit(
                f"compile failed for {name}\nargv={argv!r}\nstdout={result.stdout}\nstderr={result.stderr}"
            )


    def sanitizer_probe() -> tuple[bool, str]:
        assert GCC is not None
        probe_source = ROOT / "environment/sanitizer_probe.c"
        probe_binary = BIN / "sanitizer-probe"
        argv = [
            GCC, "-std=c11", "-fsanitize=address,undefined", str(probe_source),
            "-o", str(probe_binary),
        ]
        compiled = command(argv, check=False)
        if compiled.returncode != 0:
            return False, "compiler probe rejected address/undefined sanitizers"
        executed = command([str(probe_binary)], check=False)
        if executed.returncode != 0:
            return False, "sanitizer runtime probe did not execute successfully"
        return True, "compiler and runtime probe executed successfully"


    def main() -> int:
        if GCC is None:
            raise SystemExit("gcc is required for this C challenge pack")
        BIN.mkdir(parents=True, exist_ok=True)
        version = command([GCC, "--version"]).stdout.splitlines()[0]
        for architecture, implementation in IMPLEMENTATIONS.items():
            compile_binary(f"{architecture}-public", [implementation, ROOT / "public_tests/contract.c"])
            compile_binary(
                f"{architecture}-withheld",
                [implementation, ROOT / "sealed/reference_tests/contract.c"],
            )
            compile_binary(
                f"{architecture}-model",
                [implementation, ROOT / "adversarial/model_randomized.c"],
            )
            compile_binary(
                f"{architecture}-benchmark",
                [implementation, ROOT / "benchmarks/benchmark.c"],
            )
        compile_binary(
            "segregated-integrity",
            [ROOT / "sealed/reference_tests/segregated_integrity.c"],
        )
        compile_binary(
            "debug-buggy",
            [ROOT / "debugging/coalesce-span/buggy/allocator.c",
             ROOT / "debugging/coalesce-span/regression.c"],
        )
        compile_binary(
            "debug-reference",
            [ROOT / "sealed/reference/allocator.c",
             ROOT / "debugging/coalesce-span/regression.c"],
        )
        compile_binary(
            "review-demonstration",
            [ROOT / "review_exercises/rounding-overflow/proposed/rounding.c",
             ROOT / "review_exercises/rounding-overflow/sealed/demonstrate.c"],
        )
        sanitizer_available, sanitizer_reason = sanitizer_probe()
        if sanitizer_available:
            for architecture, implementation in IMPLEMENTATIONS.items():
                compile_binary(
                    f"{architecture}-model-sanitized",
                    [implementation, ROOT / "adversarial/model_randomized.c"],
                    ["-O1", "-fsanitize=address,undefined"],
                )
        report = {
            "schema_version": 1,
            "compiler": version,
            "compiler_path": GCC,
            "strict_flags": FLAGS,
            "platform": platform.platform(),
            "sanitizer": {
                "available": sanitizer_available,
                "probe": "compile and execute address+undefined sanitizer fixture",
                "reason": sanitizer_reason,
                "requested_architectures": list(IMPLEMENTATIONS),
            },
            "network_used": False,
            "binary_count": len(list(BIN.iterdir())),
        }
        (OUTPUT / "toolchain.json").write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        print(json.dumps(report, sort_keys=True))
        return 0


    if __name__ == "__main__":
        raise SystemExit(main())
'''


_SANITIZER_RUNNER = r'''
    from __future__ import annotations

    import json
    import os
    import subprocess
    from pathlib import Path


    ROOT = Path(__file__).resolve().parents[1]
    REPORT = ROOT / "validation-output/toolchain.json"
    RESULT = ROOT / "validation-output/sanitizer-result.json"
    ARCHITECTURES = ["reference", "best-fit", "segregated-bins"]


    def main() -> int:
        toolchain = json.loads(REPORT.read_text(encoding="utf-8"))
        available = bool(toolchain["sanitizer"]["available"])
        result: dict[str, object] = {
            "schema_version": 1,
            "probe_available": available,
            "probe_reason": toolchain["sanitizer"]["reason"],
            "requested_architectures": ARCHITECTURES,
            "architectures": {},
        }
        if not available:
            result["status"] = "SKIPPED_UNAVAILABLE"
            result["exit_code"] = None
        else:
            architecture_results: dict[str, object] = {}
            for architecture in ARCHITECTURES:
                completed = subprocess.run(
                    [str(ROOT / "validation-output/bin" /
                         f"{architecture}-model-sanitized")],
                    cwd=ROOT,
                    env={
                        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
                        "LANG": "C.UTF-8",
                        "LC_ALL": "C.UTF-8",
                        "ASAN_OPTIONS": "detect_leaks=0:abort_on_error=1",
                        "UBSAN_OPTIONS": "halt_on_error=1",
                    },
                    text=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    check=False,
                    timeout=20,
                )
                architecture_results[architecture] = {
                    "exit_code": completed.returncode,
                    "stdout": completed.stdout[-2000:],
                    "stderr": completed.stderr[-2000:],
                }
            passed = all(
                details["exit_code"] == 0
                for details in architecture_results.values()
                if isinstance(details, dict)
            )
            result.update(
                status="PASS" if passed else "FAIL",
                exit_code=0 if passed else 1,
                architectures=architecture_results,
            )
        RESULT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps(result, sort_keys=True))
        return 0 if result["status"] in {"PASS", "SKIPPED_UNAVAILABLE"} else 1


    if __name__ == "__main__":
        raise SystemExit(main())
'''


_BENCHMARK_RUNNER = r'''
    from __future__ import annotations

    import argparse
    import json
    import os
    import platform
    import subprocess
    from datetime import datetime, timezone
    from pathlib import Path


    ROOT = Path(__file__).resolve().parents[1]
    ARCHITECTURES = ["reference", "best-fit", "segregated-bins"]


    def main() -> int:
        parser = argparse.ArgumentParser()
        parser.add_argument("--output", required=True, type=Path)
        arguments = parser.parse_args()
        raw_results: dict[str, object] = {}
        commands: dict[str, list[str]] = {}
        for name in ARCHITECTURES:
            argv = [str(ROOT / "validation-output/bin" / f"{name}-benchmark")]
            commands[name] = [f"validation-output/bin/{name}-benchmark"]
            completed = subprocess.run(
                argv,
                cwd=ROOT,
                env={
                    "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
                    "LANG": "C.UTF-8",
                    "LC_ALL": "C.UTF-8",
                },
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
                timeout=20,
            )
            if completed.returncode != 0:
                raise SystemExit(
                    f"benchmark {name} failed: exit={completed.returncode} stderr={completed.stderr}"
                )
            raw_results[name] = json.loads(completed.stdout)
        toolchain = json.loads(
            (ROOT / "validation-output/toolchain.json").read_text(encoding="utf-8")
        )
        report = {
            "schema_version": 1,
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "hypothesis": (
                "segregated bins should reduce search work under mixed sizes, while first-fit "
                "and best-fit may produce different external fragmentation; smoke data is not "
                "a universal ranking"
            ),
            "parameters": {
                "timed_operations": 80000,
                "arena_bytes": 2097152,
                "slot_count": 256,
                "fragmentation_pattern": "900 deterministic replacements then free even slots",
            },
            "environment": {
                "platform": platform.platform(),
                "python": platform.python_version(),
                "compiler": toolchain["compiler"],
                "strict_flags": toolchain["strict_flags"],
                "network": "not used",
            },
            "commands": commands,
            "raw_results": raw_results,
            "interpretation_boundary": (
                "One bounded in-process smoke workload on this machine; allocator metadata, "
                "cache state, compiler, and timer resolution affect results. Re-run and profile "
                "before drawing production conclusions."
            ),
        }
        output = arguments.output
        if not output.is_absolute():
            output = ROOT / output
        output.resolve().relative_to((ROOT / "benchmarks").resolve())
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps({
            name: round(float(value["operations_per_second"]), 3)
            for name, value in raw_results.items()
        }, sort_keys=True))
        return 0


    if __name__ == "__main__":
        raise SystemExit(main())
'''


_SANITIZER_PROBE = r'''
    #include <stddef.h>

    int main(void) {
        volatile size_t value = 1U;
        return value == 1U ? 0 : 1;
    }
'''


def generate_allocator_slice(
    workspace: Path, payload: dict[str, Any], db: Database
) -> SliceResult:
    """Generate a deterministic C allocator challenge candidate for external validation."""

    if not workspace.is_dir() or workspace.is_symlink():
        raise ValueError("allocator workspace must be an existing real directory")
    entries = list(workspace.iterdir())
    marker = workspace / ".factory-workspace"
    if marker.exists() and (not marker.is_file() or marker.is_symlink()):
        raise ValueError("allocator workspace marker must be a regular file")
    if any(entry.name != ".factory-workspace" for entry in entries):
        raise ValueError("allocator workspace must be empty to preserve artifact boundaries")
    provenance = _provenance(db, payload)

    _write(
        workspace,
        "README.md",
        """
        # Caller-Owned-Arena C Allocator Challenge

        Build an allocator over a fixed byte arena supplied by the caller. This keeps metadata,
        alignment, overflow, splitting, coalescing, `realloc` preservation, fragmentation, and
        corruption detection visible without interposing on the process's libc allocator.

        The portable C11 contract deliberately uses disjoint storage returned by `malloc` or
        `aligned_alloc` (or equivalent storage with no incompatible declared object type). Merely
        aligning and casting a declared `unsigned char[]` does not create `state` or `block` objects;
        such stack/static arenas are outside this reference's portable effective-type contract.
        Supporting them portably is a worthwhile representation-design extension, documented in the
        sealed tradeoffs, rather than something these validators pretend to detect at runtime.

        Start with `REQUIREMENTS.md`, `DESIGN_QUESTIONS.md`, `include/allocator.h`, `starter/`, and
        `public_tests/`. Do not expose `sealed/` to a learner workspace. When ready, reveal an
        address-ordered first-fit reference and compare it with best-fit and segregated-size-bin
        implementations through the same C API, strict compiler flags, contracts, deterministic
        model workload, and benchmark.

        Factory validation runs `python3 scripts/build_all.py`, executes every architecture's
        public/withheld/model checks, gates sanitizers on a compile-and-execute probe, reproduces one
        metadata-corruption bug, demonstrates a review finding, and only then generates actual raw
        benchmark evidence. `benchmarks/results/smoke.json` deliberately does not exist at generation
        time.

        This is a bounded educational allocator, not a `malloc` replacement and not production
        ready. Passing evidence can support `BUILDS`, `TESTED`, `BENCHMARKED`, and
        `REVIEWED`, always with `PARTIAL`; it cannot support `PRODUCTIONIZED`.
        """,
    )
    _write_json(
        workspace,
        "MANIFEST.yaml",
        {
            "schema_version": 1,
            "artifact_revision": 1,
            "project_id": "caller-owned-arena-c-allocator",
            "source_project_id": PROJECT_ID,
            "title": "Caller-Owned-Arena C Allocator",
            "family": "systems-memory-management",
            "type": "build-your-own-x-challenge-pack",
            "languages": ["C11", "Python 3 standard library (harness only)"],
            "architectures": [
                "address-ordered-first-fit",
                "address-ordered-best-fit",
                "segregated-size-class-bins",
            ],
            "concepts": [
                "alignment",
                "integer-overflow",
                "intrusive-metadata",
                "splitting-and-coalescing",
                "external-fragmentation",
                "realloc-semantics",
                "invariant-checking",
                "sanitizer-gating",
            ],
            "difficulty": 8,
            "estimated_human_hours": 16,
            "status": "GENERATED_CANDIDATE",
            "deployment_status": "NOT_PRODUCTION_READY",
            "productionized": False,
            "validation_targets": [
                "BUILDS",
                "TESTED",
                "BENCHMARKED",
                "REVIEWED",
                "PARTIAL",
            ],
            "provenance_file": "PROVENANCE.json",
        },
    )
    _write_json(
        workspace,
        "PROVENANCE.json",
        {
            "schema_version": 1,
            "catalog_source": provenance,
            "derivation": {
                "source_derived": [
                    "catalog project identity, category, language, outbound URL, and source commit",
                ],
                "agent_generated": [
                    "requirements, all C implementations and tests, exercises, and notes",
                ],
                "measured": [
                    "validation-output/toolchain.json only after build execution",
                    "benchmarks/results/smoke.json only after benchmark execution",
                    "controller-owned validator exit codes and logs",
                ],
                "inferred": [
                    "difficulty, time estimate, concepts, architecture selection, and production relevance",
                ],
            },
            "license_boundary": {
                "catalog": "Build Your Own X catalog metadata is recorded under its catalog license.",
                "linked_tutorial": (
                    "The outbound tutorial license is NOASSERTION and its prose/code is not mirrored. "
                    "A learner must retrieve it independently and honor its terms."
                ),
                "generated_pack": "Newly agent-generated educational material; no tutorial text or code copied.",
            },
            "network_used_during_generation": False,
        },
    )
    _write_json(
        workspace,
        "CATALOG_ENTRY.json",
        {
            "schema_version": 1,
            "id": "caller-owned-arena-c-allocator",
            "source_project_id": PROJECT_ID,
            "family": "memory-management",
            "type": "build",
            "languages": ["c"],
            "concepts": [
                "allocators",
                "fragmentation",
                "memory-safety",
                "systems-programming",
                "debugging",
            ],
            "difficulty": 8,
            "estimated_human_hours": 16,
            "production_relevance": 8,
            "prerequisites": ["c-pointers", "object-lifetimes", "integer-overflow"],
            "next": ["slab-allocator", "thread-safe-allocator", "virtual-memory-manager"],
            "artifact_paths": {
                "starter": "starter/",
                "public_tests": "public_tests/",
                "sealed_reference": "sealed/reference/",
                "alternatives": 2,
                "debugging_challenges": 1,
                "review_exercises": 1,
                "benchmark": "benchmarks/benchmark.c",
            },
            "validation_status": "CANDIDATE_REQUIRES_EXTERNAL_VALIDATION",
            "deployment_status": "NOT_PRODUCTION_READY",
            "productionized": False,
            "provenance": "PROVENANCE.json",
        },
    )
    _write(
        workspace,
        "REQUIREMENTS.md",
        """
        # Allocator contract

        Implement the API in `include/allocator.h` over only the supplied arena. The allocator must
        return pointers aligned for `max_align_t`, reject size-rounding overflow, split reusable free
        space, coalesce physical neighbors, preserve the old prefix on successful resize, and leave
        the original allocation unchanged when resize fails. Zero-size allocation returns `NULL`;
        freeing `NULL` succeeds. An immediate second free of a block still present in the physical
        list returns `LF_ERR_DOUBLE_FREE`. Once coalescing removes that block identity, the stale
        pointer returns `LF_ERR_INVALID_POINTER`; this bounded design does not retain tombstones.

        The caller owns disjoint storage returned by `malloc`/`aligned_alloc` (or equivalent storage
        with no incompatible declared object type): a `max_align_t`-aligned state region of at least
        `lf_state_size()` bytes and an arena span whose start may be unaligned within its allocation.
        Initialization rejects overlapping spans, may align the arena start inward, and must never
        access bytes outside it. A declared character array remains a character array in portable C;
        alignment and a cast do not change its effective type. Such stack/static backing is outside
        this reference contract. The caller/harness may acquire storage, but allocator implementations
        may not call `malloc`, `calloc`, `realloc`, `free`, `sbrk`, or `mmap` themselves. `lf_check`
        validates physical coverage and core list invariants; `lf_get_stats` reports aligned capacity,
        not caller's unrounded request sizes.

        This API is deliberately single-threaded, fixed-capacity, and non-interposing. It has no
        concurrent ownership protocol, OS page acquisition/return, hardened metadata, guard pages,
        quarantine, per-thread caches, ABI compatibility, or latency guarantee. Those omissions make
        every result `PARTIAL` and `NOT_PRODUCTION_READY`.

        Definition of done requires strict C11 compilation, public and withheld contracts,
        deterministic randomized model/data-integrity testing, optional sanitizer execution only
        after runtime detection, actual benchmark output with raw values/environment, and honest
        limitation documentation. Learner-authored claims are not validation evidence.
        """,
    )
    _write(
        workspace,
        "CONCEPTS.md",
        """
        # Concepts

        - Alignment turns payload addresses and header sizes into invariants, not preferences.
        - Alignment is distinct from C effective type. Standard allocated storage can acquire the
          internal metadata type through stores; casting a declared character array cannot.
        - Integer-overflow checks must precede rounding and size addition.
        - An address-ordered physical list makes adjacent coalescing simple but allocation search
          linear. Best-fit changes selection, not that cost class.
        - Segregated free bins accelerate candidate lookup but add a second topology whose membership
          must agree with the physical list through every split, merge, and resize.
        - Internal fragmentation is padding/capacity within allocated blocks. External fragmentation
          is free capacity divided among blocks; this pack records `1 - largest_free/free_total`.
        - A failed resize must be transactional from the caller's perspective: the old pointer and
          bytes remain valid.
        - An invariant checker detects metadata damage early but is not memory-safety hardening.
        """,
    )
    _write(
        workspace,
        "DESIGN_QUESTIONS.md",
        """
        # Design questions

        1. Which metadata is needed to coalesce in O(1), and what overwrite attacks does it expose?
        2. How do you prove every physical block covers the arena exactly once?
        3. When does a split remainder become too small to remain useful?
        4. Which additions and rounding operations can overflow before an arena bound check?
        5. What is the failure-atomic sequence for a moving resize?
        6. How will a segregated implementation update bins when a block changes size class?
        7. Which workload could make first-fit outperform best-fit, or vice versa?
        8. Why does a throughput number without raw workload/environment data teach little?
        9. What synchronization and ownership model would a thread-safe extension require?
        10. Which production allocator defenses are intentionally absent here?
        """,
    )
    _write(
        workspace,
        "AGENTS.md",
        """
        # Learner boundary

        Work in a copied view containing only top-level learner documents, `include/`, `starter/`,
        and `public_tests/`. Do not mount or search `sealed/`, `debugging/*/sealed/`, or
        `review_exercises/*/sealed/`. Use local argv-based compiler commands; this exercise requires
        no network. Record commands, failures, and concise debugging hypotheses. Do not claim success
        from prose or from editing an authoritative test.
        """,
    )
    _write(workspace, "include/allocator.h", _HEADER)
    _write(workspace, "starter/allocator.c", _STARTER_C)
    _write(
        workspace,
        "starter/README.md",
        """
        # Starter

        Implement `allocator.c` against `../include/allocator.h`. A first milestone is one aligned
        free block plus allocation; then add split, exact-pointer free, coalescing, resize, overflow
        handling, statistics, and an invariant checker. Compile against the public contract with the
        same warning policy documented in `environment/README.md`. The caller-owned harness acquires
        effective-type-compatible backing storage; your allocator must not allocate its own arena.
        Public tests are intentionally incomplete; add tests before revealing sealed material.
        """,
    )
    _write(workspace, "public_tests/contract.c", _PUBLIC_TEST)

    _write(workspace, "sealed/reference/allocator.c", _REFERENCE_C)
    _write(workspace, "sealed/reference_tests/contract.c", _HIDDEN_TEST)
    _write(
        workspace,
        "sealed/reference_tests/segregated_integrity.c",
        _SEGREGATED_INTEGRITY_TEST,
    )
    _write(workspace, "sealed/alternatives/best_fit/allocator.c", _BEST_FIT_C)
    _write(workspace, "sealed/alternatives/segregated_bins/allocator.c", _SEGREGATED_C)
    _write(
        workspace,
        "sealed/DESIGN.md",
        """
        # Sealed design

        The reference keeps one address-ordered doubly linked physical block list. Allocation selects
        the first sufficient free block; headers are aligned, splits retain a minimum aligned payload,
        and free coalesces both neighbors. This is compact and auditable but allocation is O(number of
        blocks).

        The best-fit alternative shares the topology and chooses the smallest sufficient block. It
        may reduce some remainders yet scans the whole list and can leave numerous tiny holes. The
        segregated alternative maintains ten intrusive free lists indexed by size in addition to the
        physical list. Candidate lookup starts at the request class; every split, free, merge, and
        resize updates bin membership. Its stronger `lf_check` cross-validates both topologies.

        All three intentionally serialize through caller discipline and retain metadata inside the
        writable arena. No architecture is presented as production-ready.
        """,
    )
    _write(
        workspace,
        "sealed/TRADEOFFS.md",
        """
        # Tradeoffs and measurement questions

        First-fit tends to stop searching early and preserve larger tail regions, but placement
        depends strongly on history. Best-fit spends more search work hoping to leave larger regions;
        its small remainders can be harmful. Segregated bins bound much candidate search in common
        cases but cost larger headers, more state, and complex updates. The included benchmark emits
        raw elapsed nanoseconds, operation counts, free-block layout, and external-fragmentation ratio
        for one deterministic smoke workload. Treat it as a hypothesis probe, not a universal rank.
        Profile repeated, warmed, workload-representative runs before changing an architecture.

        The references place typed metadata directly in standard dynamically allocated storage. They
        intentionally do not promise portable typed access over a declared `unsigned char[]`; alignment
        alone cannot change that array's effective type. An extension for effective-type-safe
        stack/static arenas should replace direct struct lvalues with an offset/byte representation and
        `memcpy`-based metadata access (or expose a compatible storage type), then repeat all tests under
        optimizing compilers. This is a known contract boundary, not a runtime-detected property.
        """,
    )
    _write(workspace, "adversarial/model_randomized.c", _MODEL_TEST)
    _write(
        workspace,
        "adversarial/README.md",
        """
        # Deterministic model workload

        `model_randomized.c` uses a fixed xorshift seed (`0x20260830`) to allocate, free, and resize
        independent slots in a deliberately constrained arena. A byte-tag model verifies non-overlap,
        alignment, arena bounds, prefix preservation, and failed-resize atomicity, while the
        implementation invariant checker runs after each operation. The fixture fails unless ordinary
        out-of-capacity resize failures occur. This is reproducible randomized model checking, not
        exhaustive proof and not a general-purpose fuzzer.
        """,
    )
    _write(workspace, "benchmarks/benchmark.c", _BENCHMARK_C)
    _write(workspace, "benchmarks/run.py", _BENCHMARK_RUNNER)
    _write(
        workspace,
        "benchmarks/README.md",
        """
        # Benchmark

        The validator first builds each implementation with the recorded compiler and flags. `run.py`
        then executes an identical 80,000-operation throughput workload and a deterministic mixed-size
        fragmentation workload, preserving each implementation's raw JSON plus machine/toolchain
        context in `results/smoke.json`. Generation never creates that result. Re-run repeatedly and
        add profiling before interpreting small differences.
        """,
    )

    buggy = _REFERENCE_C.replace(
        "item->size += HEADER_SIZE + next->size;",
        "item->size += (2U * HEADER_SIZE) + next->size;",
        1,
    )
    if buggy == _REFERENCE_C:
        raise RuntimeError("debug mutation anchor was not found")
    patch = "".join(
        unified_diff(
            buggy.splitlines(keepends=True),
            _REFERENCE_C.splitlines(keepends=True),
            fromfile="a/debugging/coalesce-span/buggy/allocator.c",
            tofile="b/debugging/coalesce-span/buggy/allocator.c",
        )
    )
    _write(workspace, "debugging/coalesce-span/buggy/allocator.c", buggy)
    _write(workspace, "debugging/coalesce-span/regression.c", _DEBUG_REGRESSION)
    _write(
        workspace,
        "debugging/coalesce-span/README.md",
        """
        # Debugging challenge: corrupted physical span

        The allocator builds and simple allocate/free use can appear normal, but freeing two adjacent
        blocks makes `lf_check` report corrupt metadata. There is exactly one intentional source-code
        mutation. Reproduce the failure, draw the arena/header/payload layout, identify the violated
        invariant, add the smallest regression, and repair it before opening `sealed/`.
        """,
    )
    _write(
        workspace,
        "debugging/coalesce-span/sealed/root-cause.md",
        """
        # Root cause

        `merge_next` recovers two header widths even though combining adjacent blocks removes exactly
        one intervening header. The merged size therefore claims bytes beyond the next physical block,
        corrupting the arena coverage invariant and enabling a later split/allocation to overlap
        metadata or escape the arena. The patch restores `current payload + one header + next payload`.
        """,
    )
    _write(workspace, "debugging/coalesce-span/sealed/patch.diff", patch)
    _write(
        workspace,
        "debugging/coalesce-span/sealed/investigation.md",
        """
        # Investigation

        1. Confirm the reference regression exits zero and the buggy binary exits one.
        2. Reduce the history to three allocations and two adjacent frees.
        3. Compare the sum of physical header/payload spans before and after the second free.
        4. Observe that the list's claimed final address advances by one extra header.
        5. Apply `patch.diff`; strict contracts and the deterministic model must still pass.
        """,
    )

    _write(
        workspace,
        "review_exercises/rounding-overflow/README.md",
        """
        # Review exercise: centralize request rounding

        Review the proposed C helper as if it were a performance cleanup in an allocator hot path.
        Write `REVIEW.md` with severity, triggering inputs, caller impact, a repair strategy, and tests.
        Consider validity of alignment as well as arithmetic. Reveal the expected review only after
        submitting yours.
        """,
    )
    _write(
        workspace,
        "review_exercises/rounding-overflow/proposed/rounding.c",
        _REVIEW_PROPOSAL,
    )
    _write(
        workspace,
        "review_exercises/rounding-overflow/sealed/demonstrate.c",
        _REVIEW_DEMONSTRATION,
    )
    _write(
        workspace,
        "review_exercises/rounding-overflow/sealed/EXPECTED_REVIEW.md",
        """
        # Expected review

        **Block / memory-safety:** `bytes + alignment - 1` can wrap before masking. For `SIZE_MAX`
        and alignment 16 the helper returns zero, so a nonzero request can be treated as a zero/tiny
        allocation and later overwritten by the caller. Reject zero/non-power-of-two alignments and
        check `bytes > SIZE_MAX - (alignment - 1)` before addition. Add boundary tests around every
        supported alignment. The separate demonstration records the overflow without writing through
        the resulting size.
        """,
    )
    _write(
        workspace,
        "production/PRODUCTIONIZATION.md",
        """
        # Productionization gap (NOT_PRODUCTION_READY)

        This pack is useful for mechanisms, not deployment. A shippable allocator would need a clear
        ABI/interposition story, concurrent ownership and race testing, OS-backed regions and return
        policy, thread/fork/signal semantics, hardened or out-of-line metadata, corruption response,
        double-free/use-after-free defenses, guard/quarantine options, telemetry without recursive
        allocation, bounded latency goals, workload-specific size classes, NUMA/cache behavior,
        exhaustive overflow review, cross-platform toolchains, long stress and differential tests,
        and compatibility/performance evaluation against mature allocators. Sanitizer-clean smoke
        tests and this benchmark do not resolve those gaps. Status remains `PARTIAL` and
        `NOT_PRODUCTION_READY`; `productionized` is false.
        """,
    )
    _write(
        workspace,
        "environment/README.md",
        """
        # Environment

        Required: Python 3 standard library and a C11-capable `gcc`. The build harness uses
        `-Wall -Wextra -Werror -pedantic -O2 -fno-omit-frame-pointer` and records the exact compiler,
        platform, and flags during validation. Address/undefined sanitizers are compiled and executed
        on a harmless probe; sanitized model testing runs only if both steps succeed. No sanitizer is
        assumed and no network is used.
        """,
    )
    _write(workspace, "environment/sanitizer_probe.c", _SANITIZER_PROBE)
    _write(workspace, "scripts/build_all.py", _BUILD_SCRIPT)
    _write(workspace, "scripts/run_sanitizer.py", _SANITIZER_RUNNER)

    validators: list[dict[str, Any]] = [
        {
            "type": "required_paths",
            "name": "allocator-pack-layout",
            "paths": [
                "README.md",
                "MANIFEST.yaml",
                "PROVENANCE.json",
                "CATALOG_ENTRY.json",
                "REQUIREMENTS.md",
                "include/allocator.h",
                "starter/allocator.c",
                "public_tests/contract.c",
                "sealed/reference/allocator.c",
                "sealed/reference_tests/contract.c",
                "sealed/reference_tests/segregated_integrity.c",
                "sealed/alternatives/best_fit/allocator.c",
                "sealed/alternatives/segregated_bins/allocator.c",
                "adversarial/model_randomized.c",
                "benchmarks/benchmark.c",
                "benchmarks/run.py",
                "debugging/coalesce-span/buggy/allocator.c",
                "debugging/coalesce-span/regression.c",
                "debugging/coalesce-span/sealed/root-cause.md",
                "debugging/coalesce-span/sealed/patch.diff",
                "review_exercises/rounding-overflow/proposed/rounding.c",
                "review_exercises/rounding-overflow/sealed/EXPECTED_REVIEW.md",
                "production/PRODUCTIONIZATION.md",
                "scripts/build_all.py",
            ],
        },
        {
            "type": "forbidden_paths",
            "name": "learner-reveal-boundary",
            "paths": [
                "starter/sealed",
                "starter/reference",
                "starter/hidden_tests",
                "starter/EXPECTED_REVIEW.md",
                "public_tests/sealed",
                "public_tests/reference",
            ],
        },
        {
            "type": "json_fields",
            "name": "allocator-provenance-fields",
            "path": "PROVENANCE.json",
            "required": [
                "schema_version",
                "catalog_source",
                "derivation",
                "license_boundary",
                "network_used_during_generation",
            ],
        },
        {
            "type": "json_fields",
            "name": "allocator-catalog-fields",
            "path": "CATALOG_ENTRY.json",
            "required": [
                "schema_version",
                "id",
                "source_project_id",
                "family",
                "languages",
                "concepts",
                "artifact_paths",
                "validation_status",
                "deployment_status",
                "provenance",
            ],
        },
        {
            "type": "command",
            "name": "strict-c-build-and-toolchain-probe",
            "argv": ["python3", "scripts/build_all.py"],
            "produces": ["validation-output"],
            "timeout_seconds": 60,
            "claims": ["BUILDS", "PARTIAL"],
        },
        {
            "type": "json_fields",
            "name": "toolchain-evidence-fields",
            "path": "validation-output/toolchain.json",
            "required": [
                "schema_version",
                "compiler",
                "compiler_path",
                "strict_flags",
                "platform",
                "sanitizer",
                "network_used",
                "binary_count",
            ],
        },
    ]
    for architecture in ("reference", "best-fit", "segregated-bins"):
        validators.extend(
            [
                {
                    "type": "command",
                    "name": f"{architecture}-public-contract",
                    "argv": [f"validation-output/bin/{architecture}-public"],
                    "timeout_seconds": 20,
                    "claims": ["TESTED", "PARTIAL"],
                },
                {
                    "type": "command",
                    "name": f"{architecture}-withheld-contract",
                    "argv": [f"validation-output/bin/{architecture}-withheld"],
                    "timeout_seconds": 20,
                    "claims": ["TESTED", "PARTIAL"],
                },
                {
                    "type": "command",
                    "name": f"{architecture}-deterministic-model",
                    "argv": [f"validation-output/bin/{architecture}-model"],
                    "timeout_seconds": 30,
                    "claims": ["TESTED", "PARTIAL"],
                },
            ]
        )
    validators.extend(
        [
            {
                "type": "command",
                "name": "segregated-bin-topology-corruption",
                "argv": ["validation-output/bin/segregated-integrity"],
                "timeout_seconds": 20,
                "claims": ["TESTED", "PARTIAL"],
            },
            {
                "type": "command",
                "name": "runtime-gated-sanitizer-model",
                "argv": ["python3", "scripts/run_sanitizer.py"],
                "produces": ["validation-output/sanitizer-result.json"],
                "timeout_seconds": 30,
                "claims": ["PARTIAL"],
            },
            {
                "type": "json_fields",
                "name": "sanitizer-evidence-fields",
                "path": "validation-output/sanitizer-result.json",
                "required": [
                    "schema_version",
                    "probe_available",
                    "probe_reason",
                    "requested_architectures",
                    "architectures",
                    "status",
                    "exit_code",
                ],
            },
            {
                "type": "command",
                "name": "debugging-corruption-reproduces",
                "argv": ["validation-output/bin/debug-buggy"],
                "expected_exit": 1,
                "timeout_seconds": 20,
                "claims": ["TESTED", "PARTIAL"],
            },
            {
                "type": "command",
                "name": "debugging-patch-regression",
                "argv": ["validation-output/bin/debug-reference"],
                "timeout_seconds": 20,
                "claims": ["TESTED", "PARTIAL"],
            },
            {
                "type": "command",
                "name": "review-overflow-demonstration",
                "argv": ["validation-output/bin/review-demonstration"],
                "timeout_seconds": 20,
                "claims": ["TESTED", "REVIEWED", "PARTIAL"],
            },
            {
                "type": "command",
                "name": "measured-allocator-benchmark",
                "argv": [
                    "python3",
                    "benchmarks/run.py",
                    "--output",
                    "benchmarks/results/smoke.json",
                ],
                "produces": ["benchmarks/results/smoke.json"],
                "timeout_seconds": 60,
                "claims": ["BENCHMARKED", "PARTIAL"],
            },
            {
                "type": "json_fields",
                "name": "allocator-benchmark-evidence-fields",
                "path": "benchmarks/results/smoke.json",
                "required": [
                    "schema_version",
                    "generated_at_utc",
                    "hypothesis",
                    "parameters",
                    "environment",
                    "commands",
                    "raw_results",
                    "interpretation_boundary",
                ],
            },
            {"type": "tree_checksum", "name": "allocator-pack-tree-checksum"},
        ]
    )

    generated_files = sorted(path for path in workspace.rglob("*") if path.is_file())
    metadata = {
        "name": "Caller-Owned-Arena C Allocator",
        "family": "systems-memory-management",
        "type": "build-your-own-x-challenge-pack",
        "languages": ["C11", "Python 3"],
        "concepts": [
            "allocation",
            "alignment",
            "fragmentation",
            "metadata-corruption",
            "invariant-checking",
        ],
        "difficulty": 8,
        "estimated_human_hours": 16,
        "production_relevance": 8,
        "source_project_id": PROJECT_ID,
        "provenance": provenance,
        "architecture_count": 3,
        "alternative_architecture_count": 2,
        "validation_targets": [
            "BUILDS",
            "TESTED",
            "BENCHMARKED",
            "REVIEWED",
            "PARTIAL",
        ],
        "deployment_status": "NOT_PRODUCTION_READY",
        "productionized": False,
    }
    evidence = {
        "handler": "generate_allocator_slice",
        "source_project_id": PROJECT_ID,
        "external_validation_required": True,
        "validator_count": len(validators),
        "generated_file_count": len(generated_files),
        "generated_bytes": sum(path.stat().st_size for path in generated_files),
        "candidate_tree_sha256": tree_sha256(workspace),
        "benchmark_generated_during_validation": True,
        "toolchain_detected_during_validation": True,
        "deployment_status": "NOT_PRODUCTION_READY",
    }
    return SliceResult(
        evidence=evidence,
        validators=validators,
        artifact_type="allocator_challenge_pack",
        semantic_path="projects/systems/caller-owned-arena-c-allocator",
        metadata=metadata,
    )
