# Study Task: Build `cfgcheck`

## Goal and timebox

Build a small command-line analyzer called `cfgcheck`. It reads one function written in the tiny IR below, validates it, constructs a CFG, computes which blocks are reachable from the declared entry, and emits deterministic JSON.

Use Java 17 and its standard library unless your assigned environment fixes another Java version; document any deviation. Timebox the core work to 8 hours (10 hours maximum). Do not add expressions, optimization, liveness, SSA, visualization, or multi-function support.

## 1. Input contract

Input is UTF-8 text. Ignore blank lines and lines whose first non-whitespace character is `#`. All labels must match `[A-Za-z_][A-Za-z0-9_]*`. Whitespace may separate tokens as shown below but has no meaning inside a label.

The first non-comment line must be:

```text
entry <LABEL>
```

It is followed by one or more blocks. A block begins with:

```text
block <LABEL>
```

A block may contain zero or more ordinary instructions:

```text
op <NONEMPTY OPAQUE TEXT>
```

It must end with exactly one terminator, using one of these forms:

```text
goto <LABEL>
branch <NONEMPTY OPAQUE TEXT> -> <TRUE_LABEL>, <FALSE_LABEL>
return
return <NONEMPTY OPAQUE TEXT>
```

The next `block` line or end of file follows the terminator. `op` text, branch-condition text, and return text are stored for traceability but never executed or interpreted. There is no implicit fallthrough.

An illustrative input shape (not a required test case) is:

```text
entry start
block start
  op value = input
  branch value > 0 -> positive, done
block positive
  op value = value - 1
  goto done
block done
  return value
```

## 2. Required validation

Reject the entire input if any of these conditions holds:

- the entry directive is missing, duplicated, or not first;
- no block is defined;
- a label is malformed or defined more than once;
- the declared entry has no corresponding block;
- an instruction occurs outside a block;
- a block has no terminator, has content after its terminator, or has more than one terminator;
- an `op` has no text, or a branch has no condition;
- a `goto` or `branch` target has no corresponding block; or
- a line does not match one of the stated forms.

Do not silently create blocks, choose a new entry, drop bad lines, or add fallthrough edges. Report at least the input line number and a short reason for each detected diagnostic. You may stop after one diagnostic or collect multiple diagnostics, but document and test that choice.

## 3. Graph and analysis contract

Create one graph node per declared block. A `goto` contributes one directed successor, a `branch` contributes its true target followed by its false target, and a `return` contributes none. Duplicate branch targets must not create duplicate predecessor or successor entries.

Derive predecessors from the validated successor relation. Starting at the declared entry, run a standard graph traversal and mark every visited block reachable. Disconnected, valid blocks remain in the model and are reported as unreachable.

## 4. Command-line contract

Support this interface:

```text
cfgcheck <input-file>
```

On valid input:

- write one JSON document to standard output;
- write no routine messages to standard error; and
- exit with code `0`.

On invalid input or an unreadable file:

- write human-readable diagnostics to standard error;
- do not write a partial JSON document to standard output; and
- exit with code `2`.

Do not use the network, execute IR text, or invoke a shell.

## 5. Output contract

Emit this logical JSON shape:

```json
{
  "schema_version": 1,
  "entry": "<entry label>",
  "blocks": [
    {
      "label": "<block label>",
      "successors": ["<label>"],
      "predecessors": ["<label>"],
      "reachable": true
    }
  ],
  "unreachable": ["<label>"]
}
```

Output must be reproducible byte-for-byte for the same input and tool version. Preserve declaration order for `blocks`. Within successor, predecessor, and `unreachable` arrays, remove duplicates and order labels by their block declaration order. Emit valid JSON using a serializer or carefully tested escaping; do not assemble unescaped data into JSON.

## 6. Engineering constraints

Keep these responsibilities independently testable:

1. text parsing with source locations;
2. semantic validation and the immutable validated model;
3. CFG relation construction and reachability;
4. JSON serialization; and
5. the thin command-line adapter.

Use explicit result/error types or documented exceptions rather than terminating the process deep inside parsing or analysis. Avoid global mutable state. Your traversal must terminate on cycles and should run in `O(V + E)` time after parsing.

## 7. Deliverables

Submit:

- buildable source code and the minimal build configuration;
- a `README.md` with exact build, run, and test commands plus your Java version;
- automated tests for valid and invalid inputs, including a cycle, an unreachable block, duplicate labels, an unknown target, a missing terminator, and deterministic repeated output;
- a short `DESIGN.md` stating component boundaries, core invariants, ordering choices, error strategy, and complexity; and
- `COMPREHENSION_RESPONSES.md` answering every prompt in `COMPREHENSION.md` in your own words.

Keep generated build output out of the submission unless your environment explicitly requires it. Preserve test logs when the job harness asks for durable evidence.

---

Provenance: learner-safe, manager-authored task based only on the supplied catalog description of IR/CFG foundations and implementation-oriented Java assignments. No external course material or solution was retrieved or reproduced.
