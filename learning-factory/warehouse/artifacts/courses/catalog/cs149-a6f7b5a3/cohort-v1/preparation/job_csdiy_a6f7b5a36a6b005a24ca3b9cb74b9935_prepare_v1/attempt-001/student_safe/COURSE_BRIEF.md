# Parallel Computing Kickoff

This packet begins a study path inspired by the catalog entry for CMU 15-418 and Stanford CS149. It is a deliberately small first unit, not a reconstruction or completion of either course. You will practice a central parallel-software habit: establish correctness before interpreting speed.

## The unit

You will build a C++ byte-histogram program twice: first as a clear sequential reference, then as a race-free `std::thread` implementation. You will test the two implementations against each other, retain raw timing measurements, and explain what the evidence does and does not show.

By the end of this unit, you should be able to:

- turn an algorithm into an explicit software contract with boundary behavior;
- use a sequential implementation as a correctness oracle;
- connect work/span reasoning to a concrete decomposition;
- distinguish races, synchronization costs, load balance, and measurement noise;
- make a performance claim whose scope is supported by retained data.

## Assumed background

You should be comfortable with asymptotic analysis, arrays, integer types, functions, a C++ compiler, and a command-line build tool. Familiarity with caches and threads is useful but not required.

The catalog data is inconsistent about a prerequisite: one normalized field says C, while the original prerequisite and programming-language fields say C++. This unit explicitly uses C++17 or later.

## Material boundary

Everything required for the kickoff is in this learner packet. The catalog lists CMU and Stanford websites, recording indexes, and a Stanford assignment index, but their contents were not retrieved for this unit. The catalog also explicitly lists no textbook. None of those external resources is required, and no official lecture or assignment ordering has been inferred from their links.

Do not use solution repositories or answer-bearing implementations. If you consult any optional public reference on C++ library behavior, cite the exact page and state what you used it for.

## Suggested schedule

Plan for about eight focused hours:

1. contract and design reasoning — 1 hour;
2. sequential and parallel implementation — 3 hours;
3. automated tests and fault finding — 2 hours;
4. bounded benchmarking and analysis — 1.5 hours;
5. comprehension responses and cleanup — 0.5 hour.

## What completion means

Your own statement that the work is done is not completion evidence. A validator must be able to build the project in a clean, offline workspace, run the tests, compare parallel outputs with the sequential oracle, and inspect the retained benchmark data. Passing this validation completes only this kickoff unit. It does not complete the cataloged course.
