# Learning Factory checkpoint

Generated: 2026-09-01T13:01:40.253891+00:00
Paused: True

## Health

| Job state | Count |
|---|---:|
| BLOCKED | 7 |
| CANCELLED | 800 |
| DISCOVERED | 459 |
| FAILED | 8 |
| READY | 465 |
| SUCCEEDED | 221 |

## Corpus

| Item | Count |
|---|---:|
| sources | 2 |
| courses | 82 |
| course_units | 394 |
| projects | 359 |
| students | 3 |
| artifacts | 221 |
| validations | 1082 |
| events | 9424 |

## Scale-out coverage

- BYOX: 359/359 entries planned; builders 359, reviewers 359, graph-complete pairs 359, review outputs succeeded 30, verdict-accepted pairs 0, review outcomes `{"AMBIGUOUS": 0, "FAIL": 1, "PASS": 0, "REVISE": 6, "UNKNOWN": 352}`, specialized builders 4; states `builder={"CANCELLED": 326, "FAILED": 5, "READY": 359, "SUCCEEDED": 33}` `reviewer={"CANCELLED": 330, "DISCOVERED": 359, "SUCCEEDED": 30}`.
- CSDIY: 82/82 courses planned; managers 82, students 82, examiners 82, graph-complete cohorts 82, workflow-succeeded cohorts 0, archived-output cohorts 20, remediated cohorts 82, superseded legacy jobs 64, active-contract complete/archive 82/0, examiner outcomes `{"AMBIGUOUS": 16, "FAIL": 0, "PASS": 0, "REVISE": 0, "UNKNOWN": 4}`, invalid kickoff revision chains 16; states `{"examiner": {"BLOCKED": 3, "CANCELLED": 62, "DISCOVERED": 79, "SUCCEEDED": 20}, "manager": {"READY": 22, "SUCCEEDED": 60}, "student": {"BLOCKED": 1, "CANCELLED": 62, "DISCOVERED": 21, "FAILED": 2, "READY": 58, "SUCCEEDED": 20}}`.

## Active workers

None.

## Problems requiring attention

- `job_byox_repair_v1_g1_4ad9ecb99658ceef215413de3f56f904` [FAILED] (timeout): Codex process timed out
- `job_byox_repair_v1_g1_4a1167271423ee56274592541457d0c5` [FAILED] (timeout): Codex process timed out
- `job_byox_repair_v1_g1_a562539ca767501ba7adce2081778123` [FAILED] (timeout): Codex process timed out
- `job_byox_repair_v1_g1_dc2aaa99eb6a0d40872a0dbbbb6ae014` [FAILED] (timeout): Codex process timed out
- `job_byox_repair_v1_g1_7e993d3fcc0fbdb66757b01854a8cecb` [FAILED] (timeout): Codex process timed out
- `job_csdiy_247fa49f95f2021a5de3fb035ef6e0f8_student_target_v2` [FAILED] (timeout): Codex process timed out
- `job_csdiy_aad609c682157cc0ec08cf8bbc70e729_student_target_v2` [FAILED] (timeout): Codex process timed out
- `job_csdiy_aad609c682157cc0ec08cf8bbc70e729_examiner_v2` [BLOCKED] (blocked_dependency): dependency did not succeed
- `job_csdiy_2ea1d64327b40e9dd1751e342e62a833_examiner_v2` [BLOCKED] (blocked_dependency): dependency did not succeed
- `job_csdiy_2ea1d64327b40e9dd1751e342e62a833_student_target_v2` [BLOCKED] (blocked_dependency): dependency did not succeed

## Next ready work

- `job_byox_repair_v1_g2_8ebb5db64a06a70cbce675c8060cbf35`: codex_task / reference_builder (priority 84.4)
- `job_byox_repair_v1_g1_70c59d0180be35286cb449a00260246e`: codex_task / reference_builder (priority 83.6)
- `job_byox_repair_v1_g1_06e0a3f8392a364385403808962b8132`: codex_task / reference_builder (priority 83.6)
- `job_byox_repair_v1_g1_d689a72b941a7dd2fa5515137acd843c`: codex_task / reference_builder (priority 83.6)
- `job_byox_repair_v1_g1_9c467deedae95373f8a65a4e4bdad98f`: codex_task / reference_builder (priority 83.6)
- `job_byox_repair_v1_g1_963c0d8ceef6edc73944cb4c5dee9b1f`: codex_task / reference_builder (priority 83.6)
- `job_byox_repair_v1_g1_5f6dfb8f08fe6732ade82d4a7e953d49`: codex_task / reference_builder (priority 83.6)
- `job_byox_repair_v1_g1_9cba40396a55870db359e40fa91625f4`: codex_task / reference_builder (priority 83.6)
- `job_byox_repair_v1_g1_de3fa920a8a38e476e2b1ed85d0c8966`: codex_task / reference_builder (priority 83.6)
- `job_byox_repair_v1_g1_68de452e277a0add101cfddca6da2a4d`: codex_task / reference_builder (priority 83.6)

## Operational metrics

- Persisted retries: 30
- Median finished-job duration: 430.6975688934326
- Completed by type: `{"allocator_vertical_slice": 1, "bytecode_vertical_slice": 1, "catalog_synthesis": 2, "codex_task": 205, "course_vertical_slice": 2, "event_service_vertical_slice": 1, "http_service_vertical_slice": 1, "project_vertical_slice": 2, "source_ingest": 6}`
- Artifact labels: `{"BENCHMARKED": 6, "BUILDS": 8, "FUZZED": 5, "GENERATED": 221, "PARTIAL": 53, "REVIEWED": 4, "TESTED": 10, "TRANSFER_VERIFIED": 2}`
