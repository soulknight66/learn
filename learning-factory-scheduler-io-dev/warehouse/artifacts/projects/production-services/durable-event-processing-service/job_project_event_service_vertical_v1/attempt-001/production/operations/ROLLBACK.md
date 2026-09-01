# Deployment and migration rollback

Use expand/migrate/contract. Deploy readers tolerant of both schemas, apply additive migration,
deploy writers, backfill with checkpoints, then contract only after old binaries are gone.
Roll application code back only while its schema compatibility is proven. Do not reverse a
destructive migration in place during an incident: restore a verified snapshot to a new path,
validate integrity and queue counts, reconcile external effects with idempotency keys, then
switch traffic under an explicit change record.
