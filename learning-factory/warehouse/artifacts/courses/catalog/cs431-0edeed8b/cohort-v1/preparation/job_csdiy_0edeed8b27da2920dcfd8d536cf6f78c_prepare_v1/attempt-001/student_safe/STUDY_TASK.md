# Study Task: Build a Concurrent FIFO Cache

## Goal and timebox

In about six hours, build a small Rust library whose behavior is precise enough for another engineer to validate without consulting external course material. Use stable Rust and the standard library only.

Suggested allocation:

1. Contract and state design — 60 minutes
2. Implementation — 120 minutes
3. Sequential and concurrent tests — 120 minutes
4. Documentation, evidence, and comprehension responses — 60 minutes

If you reach the timebox with a failing check, preserve the failure output and explain the remaining gap in `EVIDENCE.md`; do not claim completion.

## Required public contract

Create a library crate named `concurrent_fifo_cache`. Expose these public types and operations (equivalent generic `where` placement is fine):

```rust
#[derive(Debug, PartialEq, Eq)]
pub enum CacheError {
    ZeroCapacity,
    Poisoned,
}

#[derive(Debug, PartialEq, Eq)]
pub enum InsertOutcome<K, V> {
    Inserted,
    Updated { previous: V },
    Evicted { key: K, value: V },
}

pub struct ConcurrentFifoCache<K, V> {
    // private representation
}

impl<K, V> ConcurrentFifoCache<K, V>
where
    K: Eq + std::hash::Hash + Clone,
    V: Clone,
{
    pub fn new(capacity: usize) -> Result<Self, CacheError>;
    pub fn capacity(&self) -> usize;
    pub fn len(&self) -> Result<usize, CacheError>;
    pub fn get(&self, key: &K) -> Result<Option<V>, CacheError>;
    pub fn insert(&self, key: K, value: V)
        -> Result<InsertOutcome<K, V>, CacheError>;
    pub fn remove(&self, key: &K) -> Result<Option<V>, CacheError>;
}
```

The abstract state is a positive fixed capacity, a finite mapping from unique keys to values, and a FIFO order containing exactly those keys.

The required behavior is:

- `new(0)` returns `ZeroCapacity`; a positive capacity creates an empty cache.
- `capacity` is fixed and does not require locking.
- `len` is the number of currently mapped keys and never exceeds capacity.
- `get` returns a cloned snapshot of the value and does not change FIFO order.
- Inserting an absent key below capacity appends it as newest and returns `Inserted`.
- Inserting an existing key replaces its value, returns the prior value in `Updated`, and leaves that key's FIFO position unchanged.
- Inserting an absent key at capacity first evicts the oldest key/value pair, appends the new key as newest, and returns the evicted pair in `Evicted`.
- `remove` returns the removed value when present, removes the key from both mapping and FIFO order, and otherwise returns `None` without changing state.
- Removing and later reinserting a key makes it newest.
- Every operation that reads or changes shared state is linearizable. No mutex guard or borrowed reference into protected state may escape the call.
- If the state mutex is poisoned, every operation that needs it returns `CacheError::Poisoned`. Do not use `unsafe`, silently recover poison, or panic via `unwrap`/`expect` on the production lock path.

You may choose the private representation. Keep the synchronization boundary auditable and document the average and worst-case complexity implied by your choice.

## Work sequence

### 1. Write the design first

In `DESIGN.md`, record:

- the protected state and its representation invariants;
- preconditions, state transition, and result for each operation;
- the proposed linearization point for each lock-taking operation;
- why all related fields are changed atomically with respect to other calls;
- the mutex-poisoning policy;
- time and space complexity, including any linear queue scan;
- two plausible failure modes and the tests intended to expose them.

This should be a design argument, not a narration of source lines.

### 2. Implement the smallest conforming library

Keep fields private and use safe Rust. Avoid extra features such as expiration, LRU promotion, asynchronous APIs, sharding, persistence, or lock-free code. These change the contract and dilute the unit.

### 3. Build deterministic evidence

Put sequential behavior tests in `tests/cache_contract.rs`. At minimum cover zero capacity, insertion below capacity, lookup, update without FIFO promotion, eviction order, removal, reinsertion, missing keys, returned outcomes, and the capacity invariant after state transitions.

Put concurrency tests in `tests/cache_concurrency.rs`. Include both of these cases:

- At least four barrier-started threads insert distinct keys into a shared cache whose capacity is smaller than the total insertion count. Assert schedule-independent facts such as successful returns, exact outcome-category counts, key uniqueness, and final bounded length; do not predict which thread wins.
- At least four barrier-started threads insert different values for one shared key. Assert exactly one `Inserted`, all remaining outcomes are `Updated`, no eviction, length one, and a final value belonging to the submitted value set.

Join every worker and make worker failures visible to the test. Do not use sleeps, timing thresholds, random seeds, network access, or assumptions about thread execution order. Additional tests are welcome when they test a stated risk rather than inflate coverage counts.

### 4. Record reproducible evidence

Run the following from the crate root and paste the commands, exit status, and complete relevant summary into `EVIDENCE.md`:

```text
cargo fmt --check
cargo clippy --all-targets -- -D warnings
cargo test --all-targets
```

Also record `rustc --version`, `cargo --version`, the test names exercised, and any known limitation. Evidence must describe actual runs. A statement that the code "should pass" is not a run result.

Answer every prompt from `COMPREHENSION.md` in `COMPREHENSION_RESPONSES.md` without copying the prompt file into your source documentation.

## Submission inventory

Submit exactly the relevant crate and study evidence:

```text
Cargo.toml
src/lib.rs
tests/cache_contract.rs
tests/cache_concurrency.rs
DESIGN.md
EVIDENCE.md
COMPREHENSION_RESPONSES.md
```

Build directories are not evidence and should not be submitted. Unit completion is decided by an independent validator. Completing these files or reporting passing commands does not by itself complete this unit or the broader course.
