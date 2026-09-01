# Study Task: Engineer a Small Buffer Pool

## Goal

Build a standalone C++17 component that keeps a fixed number of pages in memory while delegating persistent reads and writes to an injected page store. The emphasis is not code volume. The emphasis is a clear contract, invariant-preserving behavior, deterministic tests, and an implementation another engineer could maintain.

Do not copy or claim to implement an official CMU or BusTub assignment. No external course content is needed.

## Required submission layout

Place only source evidence under `submission/`:

```text
submission/
├── CMakeLists.txt
├── include/
│   └── buffer_pool.h
├── src/
│   └── buffer_pool.cpp
├── tests/
│   └── buffer_pool_test.cpp
├── ENGINEERING_NOTES.md
└── COMPREHENSION_RESPONSES.md
```

Do not submit generated build directories, downloaded repositories, credentials, or external course solutions.

## Component boundary

Define a `PageId` type and a `PageStore` abstraction. The store must expose the equivalent of these two fallible operations:

- read the bytes for a page ID;
- write bytes for a page ID.

Your tests must supply an in-memory store test double that can seed page data, count calls, preserve written data, and deterministically fail the next selected read or write. Production file I/O is out of scope.

Define a fixed-capacity `BufferPool` with operations equivalent to:

- `Fetch(page_id)`: make a page resident, increment its pin count, and provide its current bytes or an explicit error;
- `Write(page_id, bytes)`: replace the bytes of a resident, pinned page and mark it dirty, or return an explicit error;
- `Unpin(page_id)`: decrement a positive pin count, or return an explicit error without underflow;
- `Flush(page_id)`: persist a dirty resident page and mark it clean only after a successful store write; a clean resident page succeeds without a store write.

Names and concrete result types may differ, but all behavior must be observable without inspecting private fields. If you expose a handle, pointer, reference, callback, or copied value, document its ownership and lifetime. A read-only diagnostic snapshot is acceptable for tests, but test-only mutation of pool internals is not.

## Behavioral contract

Implement all of the following:

1. Construction rejects a capacity of zero. Resident page IDs are unique, and the resident count never exceeds capacity.
2. A successful `Fetch` of a resident page does not call the store. It increments that page's pin count and makes the page most recently used.
3. A successful `Fetch` of a nonresident page reads it through `PageStore`, installs it with pin count one, and makes it most recently used.
4. If an installation needs a victim, choose the least-recently-fetched resident page whose pin count is zero. `Write` and `Unpin` do not change recency. Never evict a pinned page.
5. If every possible victim is pinned, the miss returns an explicit error and changes neither pool state nor store state. It must make no store call.
6. `Write` succeeds only for a resident page with a positive pin count. It replaces that page's bytes and marks it dirty. An invalid write leaves state unchanged.
7. `Unpin` succeeds only for a resident page with a positive pin count. Repeated fetches therefore require matching successful unpins before the page is evictable.
8. Before reusing a dirty victim, persist its latest bytes. A clean victim causes no store write.
9. A failed store read or write makes the triggering pool operation fail without changing the in-memory pool state. A failed flush leaves the page dirty. If a victim write succeeds and the following requested-page read fails, the old page remains resident and dirty; the store may already contain the successfully written bytes.
10. Lookup, successful resident fetch, recency update, write, and unpin should have expected constant-time complexity. Victim selection should be constant-time apart from skipping no ineligible entries; explain the complexity actually achieved.

Use one thread only. Thread safety, real disk semantics, crash atomicity, and background flushing are explicitly out of scope.

## Required tests

Create a self-contained test executable and register it with CTest. It must cover at least:

- zero-capacity rejection;
- first fetch versus repeated resident fetch, including balanced pin counts;
- deterministic LRU selection after at least one recency-changing re-fetch;
- refusal to evict when all frames are pinned, including absence of store calls;
- refusal to write or unpin in invalid states;
- dirty eviction persisting the newest bytes;
- clean eviction performing no write;
- explicit flush success and write failure;
- read failure with a free frame and with a clean victim;
- write failure during dirty eviction;
- successful dirty-victim write followed by requested-page read failure;
- a longer mixed sequence that checks uniqueness, capacity, and pin-count invariants after every operation.

Tests must be deterministic: no sleeps, races, network, random seeds that are not fixed, or dependence on iteration order. You may use the C++ standard library or a testing framework already available in the validation environment, but do not fetch dependencies during the build. A small local assertion-based harness is sufficient.

## Reproducible build

The following commands, run from `submission/`, must configure, build, and run the tests without network access:

```bash
cmake -S . -B build
cmake --build build
ctest --test-dir build --output-on-failure
```

Enable useful compiler warnings in your build. Document the supported compiler assumptions and any additional local diagnostic command in `ENGINEERING_NOTES.md`.

## Engineering notes

Keep `ENGINEERING_NOTES.md` concise but concrete. Include:

- your public contract and result/error model;
- the state representation and ownership/lifetime rules;
- at least four invariants and where each is protected;
- how state is staged so failed store operations remain safe;
- achieved time and space complexity;
- one plausible alternative design and why you did not choose it;
- exact build/test commands and any known limitation inside the stated scope.

Do not write "all tests pass" as a substitute for evidence; the commands and test output must make that claim checkable.

## Suggested work plan

1. **Contract and state sketch — 45 minutes.** Write the observable states, errors, invariants, and storage-call ordering before implementation.
2. **Core implementation — 2.5 to 3 hours.** Implement ordinary fetch, pin, write, unpin, replacement, and flush paths.
3. **Failure behavior and tests — 2 to 2.5 hours.** Build the store double first, then exercise transitions and injected failures.
4. **Review and reasoning — 1 to 1.5 hours.** Simplify ownership, run a clean build, finish engineering notes, and answer the comprehension prompts.

If you reach 10 hours, preserve a buildable state and list specific missing behaviors. Do not expand into BusTub, concurrency, or additional database components.

## Evidence checklist

Before stopping, verify that every required submission file exists, a clean out-of-tree build succeeds, CTest discovers and runs the tests, and the written responses refer to the code you actually submitted. These are candidate completion artifacts; independent validation, not this checklist, decides unit completion.
