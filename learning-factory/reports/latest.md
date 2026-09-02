# Learning Factory checkpoint

Generated: 2026-09-02T15:18:08.360393+00:00
Paused: True

## Health

| Job state | Count |
|---|---:|
| BLOCKED | 6 |
| CANCELLED | 800 |
| DISCOVERED | 446 |
| FAILED | 11 |
| READY | 451 |
| SUCCEEDED | 253 |

## Corpus

| Item | Count |
|---|---:|
| sources | 2 |
| courses | 82 |
| course_units | 394 |
| projects | 359 |
| students | 3 |
| artifacts | 253 |
| validations | 1270 |
| events | 10037 |

## Scale-out coverage

- BYOX: 359/359 entries planned; builders 359, reviewers 359, graph-complete pairs 359, review outputs succeeded 30, verdict-accepted pairs 0, review outcomes `{"AMBIGUOUS": 0, "FAIL": 1, "PASS": 0, "REVISE": 12, "UNKNOWN": 346}`, specialized builders 4; states `builder={"CANCELLED": 326, "FAILED": 7, "READY": 350, "SUCCEEDED": 33}` `reviewer={"CANCELLED": 330, "DISCOVERED": 350, "SUCCEEDED": 30}`.
- CSDIY: 82/82 courses planned; managers 82, students 82, examiners 82, graph-complete cohorts 82, workflow-succeeded cohorts 0, archived-output cohorts 20, remediated cohorts 82, superseded legacy jobs 64, active-contract complete/archive 82/0, examiner outcomes `{"AMBIGUOUS": 16, "FAIL": 0, "PASS": 0, "REVISE": 0, "UNKNOWN": 4}`, invalid kickoff revision chains 16; states `{"examiner": {"BLOCKED": 4, "CANCELLED": 62, "DISCOVERED": 78, "SUCCEEDED": 20}, "manager": {"READY": 18, "SUCCEEDED": 64}, "student": {"CANCELLED": 62, "DISCOVERED": 18, "FAILED": 3, "READY": 61, "SUCCEEDED": 20}}`.

## Active workers

None.

## Problems requiring attention

- `job_examiner_cow_transfer_v2` [FAILED] (validation_failure): examiner learner evidence is invalid: examiner learner evidence requires exactly one matching JSON-schema validator
- `job_byox_repair_v1_g1_d689a72b941a7dd2fa5515137acd843c` [FAILED] (timeout): Codex process timed out
- `job_byox_repair_v1_g1_06e0a3f8392a364385403808962b8132` [FAILED] (timeout): Codex process timed out
- `job_csdiy_0c0beb8e3224cbbc66b740fe95689163_student_target_v2` [FAILED] (timeout): Codex process timed out
- `job_byox_repair_v1_g1_4ad9ecb99658ceef215413de3f56f904` [FAILED] (timeout): Codex process timed out
- `job_byox_repair_v1_g1_4a1167271423ee56274592541457d0c5` [FAILED] (timeout): Codex process timed out
- `job_byox_repair_v1_g1_a562539ca767501ba7adce2081778123` [FAILED] (timeout): Codex process timed out
- `job_byox_repair_v1_g1_dc2aaa99eb6a0d40872a0dbbbb6ae014` [FAILED] (timeout): Codex process timed out
- `job_byox_repair_v1_g1_7e993d3fcc0fbdb66757b01854a8cecb` [FAILED] (timeout): Codex process timed out
- `job_csdiy_247fa49f95f2021a5de3fb035ef6e0f8_student_target_v2` [FAILED] (timeout): Codex process timed out

## Next ready work

- `job_byox_repair_v1_g1_9c467deedae95373f8a65a4e4bdad98f`: codex_task / reference_builder (priority 83.6)
- `job_byox_repair_v1_g1_963c0d8ceef6edc73944cb4c5dee9b1f`: codex_task / reference_builder (priority 83.6)
- `job_byox_repair_v1_g1_5f6dfb8f08fe6732ade82d4a7e953d49`: codex_task / reference_builder (priority 83.6)
- `job_byox_repair_v1_g1_9cba40396a55870db359e40fa91625f4`: codex_task / reference_builder (priority 83.6)
- `job_byox_repair_v1_g1_de3fa920a8a38e476e2b1ed85d0c8966`: codex_task / reference_builder (priority 83.6)
- `job_byox_repair_v1_g1_68de452e277a0add101cfddca6da2a4d`: codex_task / reference_builder (priority 83.6)
- `job_byox_repair_v1_g1_e6961df0be5a1b3666a34cbed0e6d564`: codex_task / reference_builder (priority 83.6)
- `job_byox_build_s2_92f1729913192a0b80158e00fb6475f4`: codex_task / reference_builder (priority 82.4)
- `job_byox_build_s2_a7444fc01bbed158b7bcf7820b3d98a5`: codex_task / reference_builder (priority 82.4)
- `job_byox_build_s2_aace1e25a85a7f45f3e8b88474341820`: codex_task / reference_builder (priority 82.4)

## Operational metrics

- Persisted retries: 41
- Median finished-job duration: 494.8691635131836
- Completed by type: `{"allocator_vertical_slice": 1, "bytecode_vertical_slice": 1, "catalog_synthesis": 2, "codex_task": 237, "course_vertical_slice": 2, "event_service_vertical_slice": 1, "http_service_vertical_slice": 1, "project_vertical_slice": 2, "source_ingest": 6}`
- Artifact labels: `{"BENCHMARKED": 6, "BUILDS": 8, "FUZZED": 5, "GENERATED": 253, "PARTIAL": 68, "REVIEWED": 4, "TESTED": 10, "TRANSFER_VERIFIED": 2}`
