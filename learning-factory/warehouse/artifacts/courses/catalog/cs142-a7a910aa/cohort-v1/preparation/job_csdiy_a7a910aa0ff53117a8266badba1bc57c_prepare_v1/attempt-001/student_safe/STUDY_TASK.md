# Study Task: Algorithm Run Log

## Goal

Build a dependency-free browser application that lets a user record, inspect, persist, and remove measurements from algorithm runs. Favor a small, reviewable implementation over extra features.

Timebox the work to approximately eight hours. If a stretch goal threatens the required behavior, omit it and document that choice.

## Deliverables

Place the work in a `submission/` directory with this minimum shape:

```text
submission/
├── README.md
├── index.html
├── styles.css
├── src/
│   ├── model.mjs
│   ├── storage.mjs
│   └── app.mjs
├── tests/
│   ├── model.test.mjs
│   └── storage.test.mjs
└── COMPREHENSION_RESPONSE.md
```

You may add small supporting files. Do not add a framework, build system, network service, analytics, or third-party runtime dependency.

## Data contract

Each accepted run has exactly these domain fields:

| Field | Required behavior |
| --- | --- |
| `id` | Non-empty string, unique among current records |
| `algorithm` | Trimmed, non-empty string of at most 60 Unicode characters |
| `n` | Positive safe integer |
| `milliseconds` | Finite number greater than or equal to zero |

The collection must not contain two records with the same `id`. Invalid input must produce useful field-specific feedback and must not partially change the collection.

## Required application behavior

1. Show a labeled form for algorithm name, input size `n`, and elapsed milliseconds.
2. On a valid submission, add one record, clear the form, save the new collection, and update the view.
3. On an invalid submission, show useful errors, preserve the user's entered values, and leave stored state unchanged.
4. Display records in ascending `n`; break ties by algorithm name and then by `id` so the result is deterministic.
5. For each displayed record, provide a remove action that removes only that record and persists the result.
6. Display a summary containing the record count and the lowest elapsed time. Define a clear empty-state display rather than emitting `Infinity`, `NaN`, or a fabricated measurement.
7. Persist the collection in browser `localStorage` and restore it after a reload.
8. If stored text is malformed JSON or has an invalid shape, do not crash or silently overwrite it during initial load. Start with an empty in-memory collection and show a non-blocking recovery notice.
9. Treat an algorithm name such as `<img src=x onerror=alert(1)>` as visible text, never as markup or executable content.
10. Support keyboard-only form submission and removal. Associate every input with a visible label, make errors perceivable, and keep the layout usable at 360 CSS pixels wide.

## Engineering constraints

- `model.mjs` owns validation, immutable collection transitions, ordering, and summary calculation. It must not read the DOM, `localStorage`, the clock, or network state.
- `storage.mjs` owns serialization and storage access. Its public load operation must distinguish a successful empty load from a malformed or invalid stored value.
- `app.mjs` composes the model, storage, and DOM. Browser globals belong at this outer boundary.
- Model operations must not mutate arrays or record objects supplied by their caller.
- Any generated identifier must enter the model as explicit input so model tests remain deterministic.
- Keep a single named storage key and document it in `README.md`.
- Use semantic HTML and ES modules. The page must not require a package installation or external network request to run.

Choose and document the public function names and return shapes for the model and storage modules. Consistency and explicit contracts matter more than matching a particular naming style.

## Automated verification

Use the test runner built into a current Node release so tests can run with:

```bash
node --test submission/tests/*.test.mjs
```

Write at least 12 deterministic tests. Together they must cover:

- every validation rule and representative multiple-error input;
- valid insertion and duplicate-identifier rejection;
- non-mutation of caller-owned inputs;
- deterministic ordering, including a complete tie-break case;
- removing an existing and a missing identifier;
- summaries for empty, one-record, and multiple-record collections;
- storage round-trip behavior; and
- absent, malformed, and structurally invalid stored data.

Do not make test success depend on current time, randomness, network access, test order, or an existing browser storage area.

## Manual verification

Exercise the page in a browser and record the observed result for each of these checks in `README.md`:

1. valid add, reload, and remove;
2. several simultaneous validation failures;
3. deterministic ordering for tied values;
4. literal display of the markup-like algorithm name from requirement 9;
5. recovery from deliberately malformed stored text;
6. keyboard-only operation; and
7. the 360-pixel-wide layout.

Label these as manual observations, separate from automated-test results. Include exact run instructions and a brief architecture note explaining dependency direction and error handling.

## Suggested work sequence

1. Restate the contracts and invariants in your own notes.
2. Implement and test the pure model.
3. Implement and test the storage boundary using a fake storage object.
4. Build the semantic page and connect it through `app.mjs`.
5. Run the automated and manual checks from a clean reload.
6. Complete `COMPREHENSION_RESPONSE.md` using the separate prompts.

## Scope guard

Do not add editing, charting, authentication, a backend, multi-user synchronization, framework migration, or performance benchmarking. You may list such ideas as future work, but they are not part of this unit.

---

**Provenance and status:** Manager-authored learner task based only on the supplied catalog's broad HTML/CSS/JavaScript scope. No external course page, recording, assignment, starter code, or solution was retrieved. Validation label: task specification, not validated work.
