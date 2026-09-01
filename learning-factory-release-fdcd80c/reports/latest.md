# Learning Factory checkpoint

Generated: 2026-08-31T13:01:29.722397+00:00
Paused: True

## Health

| Job state | Count |
|---|---:|
| BLOCKED | 6 |
| CANCELLED | 2 |
| DISCOVERED | 426 |
| FAILED | 1 |
| READY | 426 |
| SUCCEEDED | 217 |

## Corpus

| Item | Count |
|---|---:|
| sources | 2 |
| courses | 82 |
| course_units | 394 |
| projects | 359 |
| students | 3 |
| artifacts | 217 |
| validations | 1054 |
| events | 5961 |

## Scale-out coverage

- BYOX: 359/359 entries planned; builders 359, reviewers 359, graph-complete pairs 359, review outputs succeeded 30, verdict-accepted pairs 0, review outcomes `{"AMBIGUOUS": 0, "FAIL": 1, "PASS": 0, "REVISE": 28, "UNKNOWN": 330}`, specialized builders 8; states `builder={"READY": 326, "SUCCEEDED": 33}` `reviewer={"BLOCKED": 1, "CANCELLED": 1, "DISCOVERED": 325, "READY": 3, "SUCCEEDED": 30}`.
- CSDIY: 82/82 courses planned; managers 82, students 82, examiners 82, graph-complete cohorts 82, workflow-succeeded cohorts 2, archived-output cohorts 20, examiner outcomes `{"AMBIGUOUS": 0, "FAIL": 14, "PASS": 2, "REVISE": 4, "UNKNOWN": 0}`, invalid kickoff revision chains 0; states `{"examiner": {"DISCOVERED": 62, "SUCCEEDED": 20}, "manager": {"READY": 25, "SUCCEEDED": 57}, "student": {"DISCOVERED": 25, "READY": 37, "SUCCEEDED": 20}}`.

## Active workers

None.

## Problems requiring attention

- `job_csdiy_progress_v1_4236718658e6c055a2803a07_examiner` [BLOCKED] (blocked_dependency): dependency did not succeed
- `job_csdiy_progress_v1_4236718658e6c055a2803a07_student_target` [BLOCKED] (blocked_dependency): dependency did not succeed
- `job_student_target_cow_transfer_v2` [FAILED] (timeout): Codex process timed out
- `job_byox_review_v1_22a4d41b09ee36d12fb994cbb5cb997d` [BLOCKED] (blocked_dependency): dependency did not succeed
- `job_examiner_cow_transfer_v2` [BLOCKED] (blocked_dependency): dependency did not succeed
- `job_student_target_cow_transfer` [BLOCKED] (blocked_authentication): Codex authentication is unavailable or invalid; operator login is required
- `job_examiner_cow_transfer` [BLOCKED] (blocked_dependency): dependency did not succeed

## Next ready work

- `job_byox_repair_v1_g1_7e993d3fcc0fbdb66757b01854a8cecb`: codex_task / reference_builder (priority 84.4)
- `job_byox_repair_v1_g1_dc2aaa99eb6a0d40872a0dbbbb6ae014`: codex_task / reference_builder (priority 84.4)
- `job_byox_repair_v1_g1_a562539ca767501ba7adce2081778123`: codex_task / reference_builder (priority 84.4)
- `job_byox_repair_v1_g1_4a1167271423ee56274592541457d0c5`: codex_task / reference_builder (priority 84.4)
- `job_byox_repair_v1_g1_4ad9ecb99658ceef215413de3f56f904`: codex_task / reference_builder (priority 84.4)
- `job_byox_repair_v1_g1_181f6f60b54291ceaeb6e746d627f9d9`: codex_task / reference_builder (priority 84.4)
- `job_byox_repair_v1_g2_8ebb5db64a06a70cbce675c8060cbf35`: codex_task / reference_builder (priority 84.4)
- `job_byox_repair_v1_g1_70c59d0180be35286cb449a00260246e`: codex_task / reference_builder (priority 83.6)
- `job_byox_repair_v1_g1_06e0a3f8392a364385403808962b8132`: codex_task / reference_builder (priority 83.6)
- `job_byox_repair_v1_g1_d689a72b941a7dd2fa5515137acd843c`: codex_task / reference_builder (priority 83.6)

## Operational metrics

- Persisted retries: 18
- Median finished-job duration: 413.2959780693054
- Completed by type: `{"allocator_vertical_slice": 1, "bytecode_vertical_slice": 1, "catalog_synthesis": 2, "codex_task": 201, "course_vertical_slice": 2, "event_service_vertical_slice": 1, "http_service_vertical_slice": 1, "project_vertical_slice": 2, "source_ingest": 6}`
- Artifact labels: `{"BENCHMARKED": 6, "BUILDS": 8, "FUZZED": 5, "GENERATED": 217, "PARTIAL": 52, "REVIEWED": 4, "TESTED": 10, "TRANSFER_VERIFIED": 2}`
