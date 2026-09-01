# Data100 Kickoff: Reproducible Data Cleaning

Artifact provenance: manager-authored from the supplied CSDIY catalog snapshot at commit `adce8e13789dc16aa6d1fbe163e9541736defae4`; no external pages were retrieved.

Validation label: `LEARNER_GUIDANCE_UNVALIDATED` — this brief describes a prepared kickoff, not evidence that the unit or course has been completed.

## What this is

This is a six-hour, self-contained first study unit inspired by the catalog description of UC Berkeley Data100. You will build a small tabular-data auditor while practicing the engineering habits that make later data-science work trustworthy: explicit contracts, deterministic output, failure handling, provenance, and tests.

The unit is manager-authored. It is not presented as an official Data100 lecture, lab, or assignment, and completing it does not complete or certify the approximately 80-hour course.

## Why this unit comes first

A strong algorithms background helps with complexity and abstraction, but production data work also depends on decisions that algorithms exercises can leave implicit. What counts as missing? Which malformed values are rejected? Can every output be traced to an input row? Does a second run produce the same bytes? What remains unchanged after a failure?

The kickoff makes those questions concrete before larger notebooks, libraries, models, or datasets introduce more moving parts.

## Intended outcome

By the end of this unit, you should be able to:

- express cleaning rules as a small, precise data contract;
- keep missing, invalid, and duplicate data as distinct concepts;
- structure Python code so parsing, normalization, validation, aggregation, and I/O can be tested separately;
- generate deterministic JSON with input provenance; and
- explain the time and space costs of the implementation.

## Readiness and tools

You should be comfortable with Python functions, dictionaries, command-line execution, basic `unittest`, and Big-O analysis. Only Python 3's standard library is required. No external course page, textbook page, package download, account, or network access is needed.

## Material boundary

The supplied catalog snapshot contains pointers to `https://ds100.org` and `https://www.textbook.ds100.org/intro.html`, but their page bodies were not retrieved or verified for this unit. The catalog also says assignments are on the course website without providing an assignment body or direct URL. Those records are discovery inputs, not automatically usable or official study units.

The three files in `student_safe/` are the complete learner materials for this kickoff. Future jobs may expand the course only after independently retrieving, identifying, licensing, and validating additional material.

## Unit boundary

Submit only the artifacts named in the study task. A harness-controlled validator, not a prose claim, determines whether this local unit passes. Passing has no course-wide completion effect.
