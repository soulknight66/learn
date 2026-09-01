# Study Task: Engineer a Bounded Byte Stream

Unit ID: kickoff_01_bounded_byte_stream  
Language: C++17  
Target time: 6 hours; hard timebox: 8 hours  
Network access: not required

## Scenario

Build a reusable in-memory byte stream that sits between a producer and a consumer. The producer may offer more bytes than the stream can currently hold, so writes can be partially accepted. The consumer can inspect or remove the oldest buffered bytes. The producer can close its side while already accepted bytes remain readable.

The component is deliberately small. Your deliverable is not only working code: it must also show contract reasoning, deterministic tests, appropriate complexity, and a reproducible local workflow.

## Required public interface

Provide this interface in src/byte_stream.hh and its implementation in src/byte_stream.cc:

~~~cpp
#pragma once

#include <cstddef>
#include <cstdint>
#include <string>
#include <string_view>

namespace kickoff {

class ByteStream final {
public:
  explicit ByteStream(std::size_t capacity);

  std::size_t push(std::string_view data);
  std::string peek(std::size_t len) const;
  void pop(std::size_t len);
  std::string read(std::size_t len);

  void close() noexcept;
  void set_error() noexcept;

  bool is_closed() const noexcept;
  bool is_finished() const noexcept;
  bool has_error() const noexcept;

  std::size_t capacity() const noexcept;
  std::size_t buffered_bytes() const noexcept;
  std::size_t remaining_capacity() const noexcept;
  std::uint64_t bytes_pushed() const noexcept;
  std::uint64_t bytes_popped() const noexcept;
};

} // namespace kickoff
~~~

You may add private members and private helpers. Do not change the public signatures.

## Behavioral contract

Treat input as arbitrary bytes. Embedded null bytes are data, not terminators.

1. Capacity is fixed at construction and may be zero. The buffer never holds more than that capacity.
2. push accepts the longest prefix that fits and returns the number of accepted bytes. It accepts nothing after close. An unaccepted suffix remains the caller's responsibility.
3. peek returns up to len oldest buffered bytes without changing state.
4. pop removes up to len oldest buffered bytes. Asking for more than is buffered removes everything available and is not an error.
5. read returns and removes up to len oldest buffered bytes. Its observable result and state change must match a peek followed by a pop of the returned length.
6. close is idempotent. Closing rejects future pushes but does not discard buffered data.
7. is_finished is true exactly when the stream is closed and no bytes remain buffered.
8. set_error makes the error flag sticky and is idempotent. The flag is diagnostic: setting it does not close the stream, discard data, alter counters, or otherwise change the operations above.
9. bytes_pushed counts bytes actually accepted, not bytes offered. bytes_popped counts bytes actually removed by pop or read. Neither peek nor rejected input changes a counter.
10. All query methods reflect the state after the most recent operation. Assume cumulative accepted and removed byte counts fit in std::uint64_t during this exercise.

Preserve byte order exactly.

## Complexity and resource targets

- capacity, buffered_bytes, remaining_capacity, counter queries, and state queries: O(1);
- push: O(k) for k accepted bytes;
- peek: O(k) for k returned bytes;
- pop: O(k) or better for k removed bytes;
- read: O(k) for k returned bytes;
- live payload storage: O(capacity), apart from returned values and bounded container bookkeeping.

A workload made of many small removals must not repeatedly shift the entire remaining buffer. Explain how your representation meets these targets, but do not expose that representation through the public API.

## Required deliverables

Submit exactly this minimum project shape:

~~~text
CMakeLists.txt
src/
  byte_stream.hh
  byte_stream.cc
tests/
  byte_stream_test.cc
DESIGN.md
TESTING.md
COMPREHENSION_ANSWERS.md
~~~

CMakeLists.txt must define a library for the implementation, a test executable, and a CTest test. Build with C++17, disable compiler extensions, and enable useful warnings. The project must not download dependencies. A standard-library-only test executable is sufficient.

DESIGN.md must be 300–600 words and contain:

- the representation invariants you relied on;
- ownership and invalidation decisions;
- a complexity argument tied to the chosen representation;
- one rejected alternative and its concrete tradeoff;
- any ambiguity or blocker you encountered.

TESTING.md must record the compiler identity, exact configure/build/test commands, and a short result summary. This file is a reproduction aid, not a substitute for executable tests.

Answer the prompts in COMPREHENSION.md in COMPREHENSION_ANSWERS.md. Keep that response to 600–900 words, excluding the trace table.

## Required test evidence

Write deterministic black-box tests through the public interface. Cover at least:

- zero capacity and zero-length operations;
- empty reads and peeks;
- exact fill, overflow, and preservation of an unaccepted suffix;
- interleaved push, peek, pop, and read operations;
- ordering across storage-boundary reuse;
- embedded null bytes;
- closing an empty stream and closing with buffered data;
- repeated close and push after close;
- sticky error state and its independence from closure;
- counter behavior for accepted, rejected, inspected, and removed bytes;
- one deterministic reference-model sequence of at least 10,000 mixed operations.

The model sequence must use a fixed seed committed in the test source. On failure, report the seed and operation index. Keep the workload bounded so it completes quickly on an ordinary development machine.

## Workflow

1. Write the contract table and invariants in DESIGN.md before choosing storage.
2. Establish a compiling project and one failing behavior test.
3. Implement in small steps, keeping the test command reproducible.
4. Add boundary and transition cases, then the deterministic model sequence.
5. Run a clean configure, build, and CTest invocation. If available locally, also run with address and undefined-behavior sanitizers and record whether that check was available.
6. Complete the comprehension response without consulting solution repositories.

Do not add sockets, files, threads, templates, packet parsing, benchmarking infrastructure, or networking protocols. They are outside this unit.

Provenance: manager-authored kickoff specification based on the supplied CSDIY catalog snapshot at source commit adce8e13789dc16aa6d1fbe163e9541736defae4; no official assignment text was supplied or fetched.

Validation label: ASSIGNMENT_SPECIFICATION_PREPARED_NOT_VALIDATED.
