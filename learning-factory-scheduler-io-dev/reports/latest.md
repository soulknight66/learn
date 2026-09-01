# Learning Factory checkpoint

Generated: 2026-08-30T21:42:56.135632+00:00
Paused: False

## Health

| Job state | Count |
|---|---:|
| BLOCKED | 4 |
| SUCCEEDED | 16 |

## Corpus

| Item | Count |
|---|---:|
| sources | 2 |
| courses | 82 |
| course_units | 394 |
| projects | 359 |
| students | 3 |
| artifacts | 16 |
| validations | 153 |
| events | 355 |

## Active workers

None.

## Problems requiring attention

- `job_student_target_cow_transfer_v2` [BLOCKED] (blocked_authentication): Codex authentication is unavailable or invalid; operator login is required
- `job_examiner_cow_transfer_v2` [BLOCKED] (blocked_dependency): dependency did not succeed
- `job_student_target_cow_transfer` [BLOCKED] (blocked_authentication): Codex authentication is unavailable or invalid; operator login is required
- `job_examiner_cow_transfer` [BLOCKED] (blocked_dependency): dependency did not succeed

## Next ready work

None.

## Operational metrics

- Persisted retries: 3
- Median finished-job duration: 1.0960838794708252
- Completed by type: `{"allocator_vertical_slice": 1, "bytecode_vertical_slice": 1, "catalog_synthesis": 2, "course_vertical_slice": 2, "event_service_vertical_slice": 1, "http_service_vertical_slice": 1, "project_vertical_slice": 2, "source_ingest": 6}`
- Artifact labels: `{"BENCHMARKED": 6, "BUILDS": 8, "FUZZED": 5, "GENERATED": 16, "PARTIAL": 11, "REVIEWED": 4, "TESTED": 10, "TRANSFER_VERIFIED": 2}`
