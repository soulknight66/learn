# MIT6.824: Distributed System — Bounded Kickoff Brief

## What this packet is

The supplied catalog describes an MIT distributed-systems course of roughly 200
hours, taught in Go, with paper discussions and four difficult projects that
progress toward a Raft-based key/value service. It reports Computer Architecture
and Parallel Computing as prerequisites.

Only catalog metadata was supplied here. The course schedule is a link that was
not opened, both assignment records are descriptions without specifications, and
the catalog says there is no textbook. The snapshot is also internally
inconsistent about the course number. Consequently, this packet does not infer a
lecture order, paper list, project API, course year, grading policy, or official
equivalence.

This first unit is locally authored preparation. It is not an MIT lecture, lab,
assignment, or substitute for the course.

## The unit

**Title:** Retry-Safe Key/Value Operations: Contract, Traces, and Evidence  
**Expected effort:** 6 hours  
**Hard stop:** 8 hours

You will create a reviewable design dossier for a small fictional key/value
service facing request loss, reply loss, duplication, delay, and reordering. The
work is deliberately narrower than replication or consensus. Its purpose is to
practice the engineering moves that connect an algorithmic idea to reliable
software:

- define the environment before promising behavior;
- distinguish a logical operation from a delivery attempt;
- state client-visible semantics and invariants precisely;
- turn invariants into deterministic event traces and test oracles;
- design useful evidence and observability;
- use counterexamples to revise a design; and
- mark crash, persistence, concurrency, and retention limits honestly.

The exercise is completed entirely in Markdown. No source download, network
access, Go toolchain, or external reading is needed.

## A compact engineering primer

### A failure model is part of the contract

“The network is unreliable” is too vague to test. A useful model names which
events may be lost, duplicated, delayed, reordered, corrupted, or forged; which
processes may crash; and whether storage survives. A guarantee is meaningful only
inside those boundaries.

### A timeout is an observation, not a remote-state report

A caller can observe that no reply arrived before its local deadline. By itself,
that observation does not reveal where a request or reply was lost, nor whether a
remote state transition occurred. A sound API distinguishes outcomes such as
confirmed success, confirmed rejection, and unresolved outcome.

### Operations and attempts have different identities

A retry is another message-delivery attempt for the same logical operation.
Retry-safe protocols carry stable identity across attempts. The identity's
namespace, uniqueness rules, reuse rules, and lifetime all belong in the
contract.

### Safety and liveness answer different questions

A safety property says that a bad event never occurs—for example, that one
accepted logical mutation never changes state twice. A liveness property says
that a desirable event eventually occurs, but only under stated progress
assumptions. “Eventually succeeds” is unjustified if the model permits every
message to be lost forever.

### Deterministic models make failures reproducible

Represent an experiment as an initial state plus an ordered list of delivered
events. For every delivery, record the classification, state transition, and
response. This separates the system's deterministic handling from the network's
nondeterministic choice of which event to deliver.

### Evidence should let another engineer disagree

“Looks correct” and “tests pass” are weak claims without artifacts. Strong
evidence identifies the claim, exact setup, event stream, expected observation,
actual observation, and remaining gap. A useful debugging record preserves failed
hypotheses and the revision they caused.

## Scope boundary

In scope are one volatile server, an in-memory map, request-history metadata,
sequential delivery events, precise contracts, trace-based verification, and
design-level observability.

Out of scope are actual networking, multiple replicas, leader election, log
agreement, Raft, durable recovery, membership change, sharding, performance
benchmarks, and official course artifacts. You may discuss these only as explicit
gaps or later extensions.

Passing this unit would mean only that an independent examiner accepted the
preserved evidence for this local kickoff. It can never establish completion of
MIT6.824, an official assignment, or Raft.

## Working rules

Use only this brief, `STUDY_TASK.md`, and `COMPREHENSION.md`. Do not follow
course links or search for public solutions. Preserve uncertainty rather than
filling a missing fact with a guess. At the hard stop, submit what you can verify
and label everything unfinished.
