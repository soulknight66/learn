# MIT 6.7960: Deep Learning — Kickoff Brief

## Current scope

This workspace starts one bounded study unit for a larger deep-learning course. The catalog describes MIT 6.7960 as a broad, advanced course spanning theory, model design, and applications, with roughly 90 hours of total work. This kickoff is an 8-hour engineering bridge. Finishing it completes only this unit, not MIT 6.7960 or the wider course plan.

The unit was written by the course manager from the supplied catalog metadata. It is not copied from, ordered by, or represented as an official MIT lecture or assignment.

## Unit 1: Reliable Softmax

You will turn a familiar multiclass objective into a small Python package that is testable, numerically stable, and reproducible. The mathematical model is deliberately modest. The challenge is to produce convincing engineering evidence that the implementation does what you claim.

By the end of the unit, you should be able to:

- turn matrix equations into explicit interface and shape contracts;
- implement stable softmax cross-entropy without an automatic-differentiation or machine-learning framework;
- compare analytic derivatives with an independent numerical check;
- make a training experiment repeatable from one command;
- separate evidence about code correctness from evidence about predictive performance; and
- communicate limitations instead of hiding them behind a successful run.

## Expected background

You should already be comfortable with vectors and matrices, derivatives, probability, asymptotic reasoning, basic supervised learning, and Python. The task uses Python and NumPy. No external dataset or course download is needed.

## Materials you can rely on

The complete learner packet for this unit is:

1. this brief;
2. `STUDY_TASK.md`, containing the implementation contract and deliverables; and
3. `COMPREHENSION.md`, containing the written prompts.

The catalog also points to an MIT OpenCourseWare landing page and describes recordings, lecture notes, papers, and assignments. Their contents were not supplied or verified for this unit. Do not assume that a catalog label is a usable reading or an official unit. The kickoff is intentionally self-contained, so missing external material should not block you.

## Work rhythm and boundary

Budget 6–10 hours:

- about 1 hour to specify contracts and plan tests;
- about 2.5 hours to implement the model and trainer;
- about 2 hours to test and check derivatives;
- about 1 hour to run and record the experiment; and
- about 1.5 hours to write the report and comprehension responses.

Stop when the requested artifacts are reproducible, the stated checks pass, and your report accurately describes the evidence. Do not expand the work into a neural-network framework, web service, GPU implementation, or survey of the full course. Those are outside this first unit.

