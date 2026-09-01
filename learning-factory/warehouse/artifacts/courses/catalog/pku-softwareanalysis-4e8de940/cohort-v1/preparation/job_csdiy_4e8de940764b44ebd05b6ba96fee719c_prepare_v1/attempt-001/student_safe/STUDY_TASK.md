# Study Task: Engineer a Reaching-Definitions Analyzer

Validation label: LEARNER_SAFE · TASK_SPECIFICATION · NO_SOLUTION_INCLUDED

## Mission

Build a small production-minded analyzer named rd_analyzer. It reads a control-flow graph in JSON, validates the entire input, computes intraprocedural reaching definitions for reachable blocks, and writes canonical JSON. Use only the Python 3.11 standard library.

Keep the analysis core usable as a library. The core must not read process arguments, print, or open files. Put JSON decoding, validation, diagnostics, and atomic output in boundary modules.

## Invocation and exit behavior

The required command is:

    python3 -m rd_analyzer INPUT.json OUTPUT.json

It must:

- exit 0 after a successful analysis and atomic output replacement;
- exit 2 for malformed JSON or a contract violation;
- write one stable, concise diagnostic to standard error on a contract violation;
- emit no traceback for an expected input error; and
- leave OUTPUT.json absent or byte-for-byte unchanged after any input error.

Validate before modifying the destination. On success, serialize to a temporary file beside the destination and atomically replace the destination.

## Input contract

An input has this shape:

    {
      "entry": "A",
      "blocks": [
        {
          "id": "A",
          "statements": [
            {"id": "a1", "defines": "x", "uses": []},
            {"id": "a2", "defines": null, "uses": ["x"]}
          ],
          "successors": ["B"]
        },
        {
          "id": "B",
          "statements": [],
          "successors": []
        }
      ]
    }

Apply all of these validation rules before analysis:

- The root is an object with entry and blocks.
- blocks is a nonempty array; block IDs are globally unique.
- entry names an existing block and has no incoming edge.
- Every successor names an existing block; a successor may not be duplicated within one block.
- Every statements value and successors value is an array.
- Statement IDs are globally unique.
- defines is either null or one variable name; uses is an array of variable names.
- Block IDs, statement IDs, and variables match the ASCII pattern [A-Za-z_][A-Za-z0-9_]*.
- Extra object fields are rejected so misspellings cannot silently change meaning.

Empty blocks, branch nodes, join nodes, cycles away from the entry, and unreachable blocks are valid.

## Analysis semantics

A definition fact is encoded as statement_id:variable. Because identifiers cannot contain a colon, this encoding is unambiguous.

Let D be the finite set of definition facts in reachable blocks. Analysis states are subsets of D. The entry boundary is empty. For every other reachable block, IN is the union of OUT states from its reachable predecessors.

Transfer statements in source order:

1. Record the current state as before for that statement.
2. If defines is null, leave the state unchanged.
3. If the statement defines variable v, remove every fact whose variable is v, then add this statement's fact.

The state after the final statement is the block's OUT state. This sequential rule is equivalent to the usual block GEN/KILL formulation.

Start from empty states and use a fair worklist. Whenever a block's OUT changes, reconsider its reachable successors. The queue and predecessor traversal must have a documented stable order; do not rely on hash or set iteration order. The entry IN state remains the empty boundary value even while analyzing a cyclic graph.

Only blocks reachable from entry participate in equations. Report other valid blocks separately.

## Output contract

Successful output has exactly these top-level fields:

    {
      "reachable_blocks": ["A", "B"],
      "unreachable_blocks": [],
      "in": {
        "A": [],
        "B": ["a1:x"]
      },
      "out": {
        "A": ["a1:x"],
        "B": ["a1:x"]
      },
      "before": {
        "a1": [],
        "a2": ["a1:x"]
      }
    }

This example illustrates the serialization shape, not an assessment answer.

Canonical output means:

- block-keyed objects use lexicographic block-ID order;
- before uses lexicographic statement-ID order for reachable statements;
- block and fact arrays are lexicographically sorted with no duplicates;
- unreachable statements do not appear in before;
- JSON uses UTF-8, two-space indentation, sorted object keys, and one trailing newline; and
- two runs on identical input produce byte-identical output.

## Required engineering structure

Choose names that fit your design, but preserve these responsibilities:

- immutable or defensively isolated model values for blocks, statements, and facts;
- one validation boundary that accumulates or deterministically selects errors;
- a pure reachability/predecessor layer;
- a fixed-point engine independent of JSON and files;
- a serializer that canonicalizes unordered mathematical sets; and
- a thin command-line adapter.

Do not evaluate source text, invoke a shell, use network access, or write outside the requested output and temporary sibling file.

## Verification work

Use unittest and make this command pass from the submission root:

    python3 -m unittest discover -s tests -v

Create your own small fixtures and explicit expected states. Tests must cover at least:

- a straight line with a use before and after a redefinition;
- a diamond in which different definitions meet at a join;
- a reachable loop that requires revisiting at least one block;
- a valid unreachable block whose statements are excluded from analysis output;
- empty blocks and a definition with multiple uses;
- unknown successors, duplicate IDs, bad identifier syntax, a bad entry, duplicate successors, extra fields, and malformed JSON;
- preservation of a pre-existing output sentinel after each representative failure; and
- byte-identical results across repeated successful runs.

At least one test must call the analysis core directly, and at least one must exercise the module command in a fresh temporary directory. Tests must have bounded execution time and no network dependency.

## Deliverables

Submit:

1. the rd_analyzer package and module entry point;
2. the tests directory and any locally created fixtures;
3. README.md with the exact run and test commands;
4. ANALYSIS.md describing module boundaries, the fixed-point invariant, termination, deterministic ordering, complexity, safe-output strategy, and known limitations; and
5. COMPREHENSION_RESPONSES.md answering every prompt in COMPREHENSION.md in your own words.

Record unfinished behavior explicitly. Do not include copied course media, credentials, remote caches, generated virtual environments, or claims that this kickoff completes the course.

## Provenance

This task was authored for the learning factory from the catalog's stated data-flow-analysis topic. It is not an official PKU assignment. Source snapshot: CSDIY commit adce8e13789dc16aa6d1fbe163e9541736defae4; catalog content SHA-256 5c26f67523735d0b6f94bd684d945d637207e18ad98e7ca8268df6c70bc434fd. No remote material was fetched.
