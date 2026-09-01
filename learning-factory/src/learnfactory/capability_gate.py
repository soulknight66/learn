from __future__ import annotations

import copy
import hashlib
from dataclasses import dataclass
from typing import Any, Mapping

from .backend_policy import with_mass_seed_backend_policy


CODEX_BACKEND_GATE_JOB_ID = "job_codex_backend_gate_v1"
CODEX_BACKEND_GATE_OUTPUT = "CODEX_BACKEND_READY_V1\n"
CODEX_BACKEND_GATE_OUTPUT_SHA256 = hashlib.sha256(
    CODEX_BACKEND_GATE_OUTPUT.encode("utf-8")
).hexdigest()
CODEX_BACKEND_GATE_ARTIFACT_TYPE = "backend-capability-gate"
CODEX_BACKEND_GATE_REQUIRED_PATHS_VALIDATOR = "backend-gate-output"
CODEX_BACKEND_GATE_CONTENT_VALIDATOR = "backend-gate-exact-content"
CODEX_BACKEND_GATE_POLICY_VERSION = 1

_LEGACY_EXACT_CONTENT_COMMAND = (
    "from pathlib import Path; assert Path('BACKEND_READY.txt').read_text("
    "encoding='utf-8') == 'CODEX_BACKEND_READY_V1\\n'"
)
CODEX_BACKEND_GATE_LEGACY_COMMAND = (
    "python3",
    "-c",
    _LEGACY_EXACT_CONTENT_COMMAND,
)

CODEX_BACKEND_GATE_SCORE_COMPONENTS: Mapping[str, float] = {
    "prerequisite_value": 10,
    "source_availability": 10,
    "agent_compute_cost": 0.1,
}


@dataclass(frozen=True)
class CodexBackendGateJobSpec:
    """Complete deterministic definition of one backend capability gate.

    ``payload`` is the current definition persisted on a fresh installation.
    ``released_payloads`` also includes the single historical command-validator
    definition deployed before host command validators were fenced.  They are
    whole definitions, not normalization templates: hybrids are never admitted.
    """

    job_id: str
    job_type: str
    worker_type: str
    seed_payload: dict[str, Any]
    payload: dict[str, Any]
    released_payloads: tuple[dict[str, Any], ...]
    priority: float
    score_components: dict[str, float]
    max_attempts: int
    model: str
    reasoning_effort: str
    dependencies: tuple[str, ...]

    def normalized_identity(
        self, *, payload: Mapping[str, Any] | None = None
    ) -> dict[str, Any]:
        """Return the named, portable full-spec fingerprint schema."""

        selected = self.payload if payload is None else payload
        return {
            "job_id": self.job_id,
            "type": self.job_type,
            "worker_type": self.worker_type,
            "payload": copy.deepcopy(dict(selected)),
            "priority": self.priority,
            "score_components": copy.deepcopy(self.score_components),
            "max_attempts": self.max_attempts,
            "model": self.model,
            "reasoning_effort": self.reasoning_effort,
            "dependencies": list(self.dependencies),
        }


def build_codex_backend_gate_job_spec(
    job_id: str = CODEX_BACKEND_GATE_JOB_ID,
) -> CodexBackendGateJobSpec:
    """Construct fresh current and released gate definitions for ``job_id``."""

    if not isinstance(job_id, str) or not job_id:
        raise ValueError("backend gate job ID must be nonempty text")
    common: dict[str, Any] = {
        "seed_policy": {
            "kind": "codex_backend_gate",
            "version": CODEX_BACKEND_GATE_POLICY_VERSION,
        },
        "prompt": (
            "This is a bounded backend capability probe. Create BACKEND_READY.txt "
            "containing exactly CODEX_BACKEND_READY_V1 followed by a newline. Do "
            "not inspect unrelated paths, use the network, or create any other file."
        ),
        "artifact_type": CODEX_BACKEND_GATE_ARTIFACT_TYPE,
        "artifact_path": "internal/backend-gates/codex-v1",
        "validation_status": "GENERATED_CANDIDATE",
        "provenance": {
            "classification": "deterministic control-plane capability probe",
            "policy_version": CODEX_BACKEND_GATE_POLICY_VERSION,
            "codex_api_transport_required": True,
            "external_resource_network_allowed": False,
        },
        "timeout_seconds": 120,
    }
    seed_payload = copy.deepcopy(common)
    seed_payload["validators"] = [
        {
            "type": "required_paths",
            "name": CODEX_BACKEND_GATE_REQUIRED_PATHS_VALIDATOR,
            "paths": ["BACKEND_READY.txt"],
        },
        {
            "type": "input_integrity",
            "name": CODEX_BACKEND_GATE_CONTENT_VALIDATOR,
            "inputs": [
                {
                    "path": "BACKEND_READY.txt",
                    "kind": "file",
                    "checksum_algorithm": "file-sha256",
                    "checksum": CODEX_BACKEND_GATE_OUTPUT_SHA256,
                }
            ],
        },
    ]
    current_payload = with_mass_seed_backend_policy(seed_payload)

    legacy_payload = copy.deepcopy(common)
    legacy_payload["validators"] = [
        {
            "type": "required_paths",
            "name": CODEX_BACKEND_GATE_REQUIRED_PATHS_VALIDATOR,
            "paths": ["BACKEND_READY.txt"],
        },
        {
            "type": "command",
            "name": CODEX_BACKEND_GATE_CONTENT_VALIDATOR,
            "argv": list(CODEX_BACKEND_GATE_LEGACY_COMMAND),
            "timeout_seconds": 10,
        },
    ]
    return CodexBackendGateJobSpec(
        job_id=job_id,
        job_type="codex_task",
        worker_type="maintenance",
        seed_payload=copy.deepcopy(seed_payload),
        payload=copy.deepcopy(current_payload),
        released_payloads=(
            copy.deepcopy(current_payload),
            copy.deepcopy(legacy_payload),
        ),
        priority=100.0,
        score_components=dict(CODEX_BACKEND_GATE_SCORE_COMPONENTS),
        max_attempts=1,
        model="gpt-5.6-sol",
        reasoning_effort="ultra",
        dependencies=(),
    )
