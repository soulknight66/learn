# Study task: build a reliable work queue

## Scenario

A developer wants a tiny browser tool for ordering the next pieces of work. Build a page that accepts work items, displays them in a deterministic order, lets the user mark them complete, and restores valid saved state after a reload.

The application must be useful without any upstream course website, recording, or assignment.

## Timebox and constraints

Timebox the work to about six hours. Use plain HTML, CSS, and JavaScript. Do not add a backend, authentication, a UI framework, or a database. A lightweight local test runner is allowed, but record how to install and invoke it; prefer facilities already available in your environment.

Keep domain logic independent of the DOM and `localStorage`. The same validation, ordering, and transition functions should be callable from automated tests without opening a browser.

## Required behavior

Each work item has:

- a title: trim surrounding whitespace, then require 1–80 characters;
- a priority: an integer from 1 through 3, where 3 is highest;
- an estimate: an integer from 1 through 240 minutes;
- a completion state; and
- a creation sequence assigned by the application.

The page must provide labeled controls for those three user-entered fields and an Add action. Invalid input must not change stored state. Show a specific, visible error associated with the relevant input, and make the error available to assistive technology.

Render all items in this exact order:

1. incomplete before complete;
2. higher priority before lower priority;
3. lower estimate before higher estimate;
4. lower creation sequence before higher creation sequence.

Changing an item's completion state must immediately re-render it in the correct position. Display text as text rather than interpreting it as HTML.

Persist the collection and the next creation sequence under one documented `localStorage` key. On startup, restore a saved collection only after checking its shape and field constraints. If saved data is absent or malformed, start with an empty collection, keep the interface usable, and show a non-destructive notice. Do not silently repair malformed records into apparently valid ones.

The interface must remain usable by keyboard and at a narrow viewport. Use semantic controls, programmatic labels, a visible focus indicator, and a status/error region that does not rely on color alone.

## Required project evidence

Submit a small, clearly organized project containing:

- an HTML entry page and a stylesheet;
- browser integration code for events, rendering, and storage;
- a domain module for validation, deterministic comparison, and state transitions;
- automated tests for the domain module;
- `ENGINEERING_NOTE.md` with the run command, test command, supported environment, module boundaries, storage schema/key, known limitations, and a short list of any references used; and
- `VERIFICATION.md` containing the exact automated-test command and captured result, plus dated manual observations for keyboard use, narrow layout, reload persistence, malformed saved data, and a title containing markup-like characters.

Do not put secrets, copied solutions, or inaccessible upstream course content in the submission.

## Minimum test set

Create deterministic automated tests that cover at least:

- each valid boundary and an invalid case for title length, priority, and estimate;
- trimming a title before validation;
- every ordering rule, including a complete tie resolved by creation sequence;
- a completion transition without mutation of the prior state;
- rejection of malformed restored data; and
- safe round-trip serialization of a valid state if serialization is implemented in the domain module.

Tests must make failures visible through a nonzero exit status. Do not replace automated assertions with screenshots.

## Suggested work sequence

First restate the behaviors as examples and choose a state shape. Implement and test the domain module next. Then build semantic markup and rendering, connect events and storage, and exercise the boundary cases manually. Finish by writing the engineering and verification notes while the commands and observations are fresh.

Stop when the required vertical slice and evidence are complete. Features such as editing, deletion, search, remote synchronization, animation, and deployment are outside this unit.
