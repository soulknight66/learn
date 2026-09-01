---
name: productionize-project
description: Review an academically correct or toy implementation and build a separately validated production variant. Use when adding reliability, observability, lifecycle, security, deployment, compatibility, performance, and operational evidence without obscuring the educational baseline.
---

# Productionize a project

1. Freeze the passing educational baseline and its tests.
2. Write `PRODUCTIONIZATION.md`: users, SLO-shaped goals, threats, resource bounds, and explicit non-goals.
3. Identify the highest-risk gaps in API design, errors, ownership, concurrency, shutdown, recovery,
   configuration, logging/metrics, compatibility, security, and deployment. Add only relevant mechanisms.
4. Implement in a separate `production/implementation` tree with migrations and rollback where applicable.
5. Add unit, integration, fault-injection, load, and graceful-shutdown checks before optimizing.
6. Measure workloads and profile surprises; never fabricate benchmark numbers.
7. Capture runbooks and at least one realistic incident scenario.
8. Compare the toy and production designs with evidence, then request independent review.

Passing course tests is the starting condition, not proof that the result is shippable.
