# Repair and artifact reconstruction record

This pack is repair generation 1 for project
`project_0211acfa0bef3a271027fdcfd888e86a`.

Factory identities retained from the immutable remediation snapshot:

- repair allocation: `job_byox_repair_v1_g1_70c59d0180be35286cb449a00260246e`
- prior builder job: `job_byox_build_v1_80876d491bcba78a3466ae3480aaaea5`
- prior artifact ID: `artifact_9fecb75972a44948bd381f4901c77b39`
- prior tree-sha256-v2 checksum:
  `4ed3d5c6663d6ff31289aed063cd7c586b71608f60985161ee0025d723598aa8`
- independent review job: `job_byox_review_v1_80876d491bcba78a3466ae3480aaaea5`
- independent review artifact: `artifact_a744a85a982e465a95685e848a423d06`
- remediation snapshot SHA-256:
  `dcb88ef2e0206418a78f7e4c8c6fb2a77c7e0e50b1fcc33028074863e36a69c0`

The generation worker is OpenAI Codex; the locally installed executable reported
`codex-cli 0.146.0`. The exact hosted model identifier and factory-side invocation
were not exposed inside this allocated workspace and are therefore not invented
here. All available compiler and platform facts are recorded in `VALIDATION.md`.

`make_artifact_record.py --write` creates `ARTIFACT_TREE.json`. Its canonical
SHA-256 covers a compact sorted JSON payload containing every artifact directory
and every regular file's relative path, permission mode, byte length, and SHA-256,
except for `ARTIFACT_TREE.json` itself (an embedded digest cannot include its own
bytes). The script traverses an explicit artifact-root allowlist, so factory
staging and workspace-control entries are excluded. `--verify` recomputes and
compares the complete record.
