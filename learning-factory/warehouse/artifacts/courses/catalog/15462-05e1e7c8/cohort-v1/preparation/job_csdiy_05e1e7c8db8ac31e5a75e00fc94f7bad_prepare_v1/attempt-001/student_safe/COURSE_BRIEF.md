# CMU 15-462: Computer Graphics — Kickoff Brief

## Status and boundary

This packet prepares one manager-authored kickoff unit: **Sampling and Rasterization: Build a Deterministic Triangle Rasterizer**. The catalog identifies CMU 15-462 and names sampling, rasterization, interpolation, and geometric transformations among many course topics. The detailed CMU pages, recordings, textbook content, and assignment bodies are not available locally and were not retrieved.

This unit is not presented as a CMU lecture or assignment, and it does not establish the institution's unit order. It is a self-contained engineering exercise selected from the catalog's declared topic area. Completing it can establish evidence only for Unit 01; it is never evidence that you completed CMU 15-462 or the broader catalog course.

**Preparation label:** `PREPARED_UNVALIDATED`  
**Authorship:** course-manager synthesis from the supplied CSDIY catalog snapshot  
**External material required:** none

## Why this unit

Triangle rasterization turns familiar algorithmic tools—orientation predicates, affine coordinates, bounding boxes, and invariants—into a small production-style component. The mathematics is compact, but correct behavior depends on decisions that software often leaves implicit: which samples lie on a shared edge, how winding affects coverage, what malformed input does, and how floating-point values become bytes.

The exercise therefore emphasizes the transition from knowing an algorithm to shipping a deterministic, testable implementation with a precise contract.

## Outcomes

By the end of the unit, you should be able to:

- connect pixel-center sampling to discrete coverage;
- implement orientation-independent triangle coverage with a documented shared-edge convention;
- interpolate vertex attributes with barycentric coordinates;
- bound work to a clipped screen-space region and analyze that cost;
- make degeneracy, invalid input, overlap, and byte conversion explicit behaviors;
- separate core logic from file and command-line concerns; and
- support engineering claims with repeatable tests and captured evidence.

## Assumed preparation

You should be comfortable with 2D vectors, affine combinations, asymptotic analysis, and C++17. You do not need a graphics API, GPU programming experience, or an external image library. The task uses a small text scene format and writes a standard PPM image.

## Bounded study path

Budget about 10 focused hours:

1. Read the behavioral contract and sketch invariants and failure cases.
2. Design a core API that does not depend on command-line or PPM code.
3. Implement coverage, interpolation, clipping, and deterministic conversion.
4. Add strict parsing and output handling around the core.
5. Build focused examples, shared-edge tests, and fixed-seed property checks.
6. Run from a clean build, capture evidence, and write the engineering and comprehension notes.

Stop at the stated contract. Perspective-correct interpolation, depth buffering, anti-aliasing, 3D transforms, textures, lighting, and performance parallelism belong to later possible units and are deliberately out of scope.

## Material availability

The local task and question sheets are sufficient. The catalog includes unverified links to a Fall 2022 course website and a YouTube playlist, a description of optional textbooks, commercial book links, and an assignment pointer whose body only says to consult the website. Treat these as discovery metadata, not as required or completed material. Do not bypass access controls or obtain unauthorized copies.

## Completion boundary

Your prose assertion is not completion evidence. Unit completion requires an independent harness-controlled build, test, and review of the submitted revision. Even a validated Unit 01 result remains a unit-level result only; later jobs must retrieve and classify authorized resources and define and validate any broader course sequence.

