from __future__ import annotations

import hashlib
import json
import math
import re
import sqlite3
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from .db import Database
from .jobs import _controller_credential_values, _reject_controller_credentials
from .strict_json import MAX_STORED_JSON_BYTES, StrictJsonError, strict_json_loads
from .util import now

if TYPE_CHECKING:
    from .byox_jobs import ByoxProjectSnapshot


BYOX_BASELINE_SCHEMA_VERSION = 1
BYOX_SNAPSHOT_JOB_SCHEME_VERSION = 2
_BYOX_REMEDIATION_BINDING_VERSION_RADIX = 1_000_000

_HEX_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_JOB_ID = re.compile(r"^job_[A-Za-z0-9][A-Za-z0-9_.-]{0,155}$")
_BYOX_ADAPTER = "build_your_own_x"
_SOURCE_MATERIAL_METADATA_KEYS = (
    "adapter",
    "extractor_version",
    "snapshot_reader",
    "tree_hash",
    "license_file",
    "license_sha256",
    "license_source_commit",
    "license_evidence",
    "linked_resource_license",
)

SecretValueProvider = Callable[[], Iterable[str]]


class ByoxBaselineError(ValueError):
    """A baseline or immutable job definition is malformed."""


class ByoxBaselineConflict(ByoxBaselineError):
    """Durable state exists at a deterministic identity with different content."""


@dataclass(frozen=True)
class ByoxBaseline:
    """One content-derived, observation-independent BYOX catalog baseline."""

    baseline_sha256: str
    schema_version: int
    project_id: str
    source_id: str
    source_commit_hash: str
    extractor_version: str
    material_json: str

    def __post_init__(self) -> None:
        _sha256(self.baseline_sha256, "baseline_sha256")
        if self.schema_version != BYOX_BASELINE_SCHEMA_VERSION:
            raise ByoxBaselineError("unsupported BYOX baseline schema version")
        _text(self.project_id, "project_id", limit=200)
        _text(self.source_id, "source_id", limit=200)
        _text(self.source_commit_hash, "source_commit_hash", limit=300)
        _text(self.extractor_version, "extractor_version", limit=200)
        material, canonical = _strict_object_document(
            self.material_json, "baseline material"
        )
        if self.material_json != canonical:
            raise ByoxBaselineError("baseline material must use canonical JSON")
        expected = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        if expected != self.baseline_sha256:
            raise ByoxBaselineError("baseline material digest does not match")
        source = material.get("source")
        project = material.get("project")
        if (
            material.get("schema_version") != self.schema_version
            or not isinstance(source, dict)
            or not isinstance(project, dict)
            or project.get("project_id") != self.project_id
            or project.get("source_id") != self.source_id
            or source.get("source_id") != self.source_id
            or source.get("commit_hash") != self.source_commit_hash
        ):
            raise ByoxBaselineError("baseline columns disagree with material")
        common_source_keys = {
            "source_id",
            "type",
            "commit_hash",
            "license",
            "material_metadata",
        }
        identity_profile = material.get("identity_profile")
        if "identity_profile" not in material:
            legacy_source_keys = common_source_keys | {
                "name",
                "path",
                "upstream_url",
            }
            if set(source) != legacy_source_keys:
                raise ByoxBaselineError(
                    "legacy baseline source identity has an invalid shape"
                )
            _text(source.get("name"), "legacy source name", limit=1_000)
            _text(source.get("path"), "legacy source path", limit=8_000)
            _optional_text(
                source.get("upstream_url"),
                "legacy source upstream_url",
                limit=8_000,
            )
        elif identity_profile == "content-v2":
            if set(source) != common_source_keys:
                raise ByoxBaselineError(
                    "content-v2 baseline source identity has an invalid shape"
                )
        else:
            raise ByoxBaselineError("unknown BYOX baseline identity profile")
        source_metadata = source.get("material_metadata")
        if (
            not isinstance(source_metadata, dict)
            or source_metadata.get("adapter") != _BYOX_ADAPTER
            or source_metadata.get("extractor_version") != self.extractor_version
        ):
            raise ByoxBaselineError("baseline extractor identity is inconsistent")

    def material(self) -> dict[str, Any]:
        value = strict_json_loads(self.material_json)
        assert isinstance(value, dict)
        return value


@dataclass(frozen=True)
class ByoxJobDefinition:
    """The immutable portion of a job, including its complete dependency set."""

    job_id: str
    job_type: str
    worker_type: str
    priority: float
    score_components_json: str
    payload_json: str
    max_attempts: int
    model: str | None
    reasoning_effort: str | None
    dependencies: tuple[str, ...]

    def __post_init__(self) -> None:
        _job_id(self.job_id, "job_id")
        _text(self.job_type, "job_type", limit=300)
        _text(self.worker_type, "worker_type", limit=300)
        _finite_number(self.priority, "priority")
        _, score_json = _strict_object_document(
            self.score_components_json, "score components"
        )
        _, payload_json = _strict_object_document(self.payload_json, "job payload")
        if score_json != self.score_components_json:
            raise ByoxBaselineError("score components must use canonical JSON")
        if payload_json != self.payload_json:
            raise ByoxBaselineError("job payload must use canonical JSON")
        if type(self.max_attempts) is not int or self.max_attempts < 1:
            raise ByoxBaselineError("max_attempts must be a positive integer")
        _optional_text(self.model, "model", limit=300)
        _optional_text(self.reasoning_effort, "reasoning_effort", limit=100)
        if not isinstance(self.dependencies, tuple):
            raise ByoxBaselineError("dependencies must be a canonical tuple")
        expected_dependencies = _dependencies(self.job_id, self.dependencies)
        if self.dependencies != expected_dependencies:
            raise ByoxBaselineError("dependencies must be unique and sorted")

    def score_components(self) -> dict[str, Any]:
        value = strict_json_loads(self.score_components_json)
        assert isinstance(value, dict)
        return value

    def payload(self) -> dict[str, Any]:
        value = strict_json_loads(self.payload_json)
        assert isinstance(value, dict)
        return value

    def material(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "job_id": self.job_id,
            "type": self.job_type,
            "worker_type": self.worker_type,
            "priority": float(self.priority),
            "score_components": self.score_components(),
            "payload": self.payload(),
            "max_attempts": self.max_attempts,
            "model": self.model,
            "reasoning_effort": self.reasoning_effort,
            "dependencies": list(self.dependencies),
        }


@dataclass(frozen=True)
class ByoxBaselineJobBinding:
    """A controller-owned association between one exact job and one baseline."""

    job_id: str
    baseline_sha256: str
    role: str
    policy_version: int
    builder_job_id: str | None
    definition_sha256: str
    bound_at: float

    def __post_init__(self) -> None:
        _job_id(self.job_id, "job_id")
        _sha256(self.baseline_sha256, "baseline_sha256")
        _sha256(self.definition_sha256, "definition_sha256")
        if self.role not in {"builder", "reviewer"}:
            raise ByoxBaselineError("binding role must be builder or reviewer")
        if type(self.policy_version) is not int or self.policy_version < 1:
            raise ByoxBaselineError("policy_version must be a positive integer")
        _finite_timestamp(self.bound_at, "bound_at")
        if self.role == "builder":
            if self.builder_job_id is not None:
                raise ByoxBaselineError("builder binding cannot name a builder")
        else:
            if self.builder_job_id is None:
                raise ByoxBaselineError("reviewer binding requires a builder")
            _job_id(self.builder_job_id, "builder_job_id")
            if self.builder_job_id == self.job_id:
                raise ByoxBaselineError("reviewer cannot review itself")


@dataclass(frozen=True)
class ByoxBoundJobPublication:
    job_created: bool
    binding_created: bool


def derive_byox_baseline(snapshot: ByoxProjectSnapshot) -> ByoxBaseline:
    """Derive immutable material while excluding observation-only source fields."""

    source_metadata, _ = _strict_object_document(
        snapshot.source_metadata_json, "source metadata"
    )
    project_metadata, _ = _strict_object_document(
        snapshot.project_metadata_json, "project metadata"
    )
    adapter = source_metadata.get("adapter")
    extractor_version = source_metadata.get("extractor_version")
    tree_hash = source_metadata.get("tree_hash")
    if adapter != _BYOX_ADAPTER:
        raise ByoxBaselineError("snapshot is not from the BYOX adapter")
    extractor = _text(extractor_version, "extractor_version", limit=200)
    _text(tree_hash, "tree_hash", limit=300)

    source_id = _text(snapshot.source_id, "source_id", limit=200)
    project_id = _text(snapshot.project_id, "project_id", limit=200)
    source_commit = _text(
        snapshot.source_commit_hash, "source_commit_hash", limit=300
    )
    if source_metadata.get("license_source_commit") not in {None, source_commit}:
        raise ByoxBaselineError("license evidence refers to another source commit")
    provenance = project_metadata.get("provenance")
    if isinstance(provenance, dict):
        if provenance.get("source_commit") not in {None, source_commit}:
            raise ByoxBaselineError("project provenance refers to another source commit")
        if provenance.get("adapter") not in {None, adapter}:
            raise ByoxBaselineError("project provenance names another adapter")
        if provenance.get("extractor_version") not in {None, extractor}:
            raise ByoxBaselineError("project provenance names another extractor")

    concepts = snapshot.concepts
    if not isinstance(concepts, tuple) or len(concepts) > 100:
        raise ByoxBaselineError("concepts must be a bounded tuple")
    normalized_concepts = [
        _text(concept, "concept", limit=1_000) for concept in concepts
    ]
    if len(set(normalized_concepts)) != len(normalized_concepts):
        raise ByoxBaselineError("concepts must be unique")
    priority_tier = snapshot.priority_tier
    if type(priority_tier) is not int:
        raise ByoxBaselineError("priority_tier must be an integer")

    material_metadata = {
        key: source_metadata[key]
        for key in _SOURCE_MATERIAL_METADATA_KEYS
        if key in source_metadata
    }
    material = {
        "schema_version": BYOX_BASELINE_SCHEMA_VERSION,
        # The table schema remains v1, while this explicit derivation profile
        # records the tightened identity projection. Host-local locators and
        # display labels are provenance observations, not source material.
        "identity_profile": "content-v2",
        "source": {
            "source_id": source_id,
            "type": _text(snapshot.source_type, "source_type", limit=200),
            "commit_hash": source_commit,
            "license": _optional_text(
                snapshot.source_license, "source_license", limit=300
            )
            or "NOASSERTION",
            "material_metadata": material_metadata,
        },
        "project": {
            "project_id": project_id,
            "source_id": source_id,
            "slug": _text(snapshot.slug, "slug", limit=1_000),
            "title": _text(snapshot.title, "title", limit=4_000),
            "category": _text(snapshot.category, "category", limit=1_000),
            "implementation_language": _optional_text(
                snapshot.implementation_language,
                "implementation_language",
                limit=1_000,
            ),
            "upstream_reference": _text(
                snapshot.upstream_reference, "upstream_reference", limit=8_000
            ),
            "concepts": normalized_concepts,
            "difficulty": _optional_number(snapshot.difficulty, "difficulty"),
            "production_relevance": _optional_number(
                snapshot.production_relevance, "production_relevance"
            ),
            "source_format": _optional_text(
                snapshot.source_format, "source_format", limit=200
            ),
            "priority_tier": priority_tier,
            "metadata": project_metadata,
        },
    }
    material_json = _canonical_document(material, "baseline material")
    digest = hashlib.sha256(material_json.encode("utf-8")).hexdigest()
    return ByoxBaseline(
        baseline_sha256=digest,
        schema_version=BYOX_BASELINE_SCHEMA_VERSION,
        project_id=project_id,
        source_id=source_id,
        source_commit_hash=source_commit,
        extractor_version=extractor,
        material_json=material_json,
    )


def byox_s2_builder_job_id(baseline_sha256: str) -> str:
    """Return the deterministic generic-builder identity for one baseline."""

    baseline = _sha256(baseline_sha256, "baseline_sha256")
    digest = hashlib.sha256(f"byox-builder-s2\0{baseline}".encode("ascii")).hexdigest()
    return f"job_byox_build_s2_{digest[:32]}"


def byox_s2_reviewer_job_id(
    baseline_sha256: str,
    builder_job_id: str,
    *,
    review_contract_version: int,
) -> str:
    """Return a reviewer identity scoped to baseline, builder, and contract."""

    baseline = _sha256(baseline_sha256, "baseline_sha256")
    builder = _job_id(builder_job_id, "builder_job_id")
    if (
        type(review_contract_version) is not int
        or review_contract_version < 1
        or review_contract_version > 999_999
    ):
        raise ByoxBaselineError("review contract version is out of range")
    material = (
        f"byox-review-s2\0{baseline}\0{builder}\0{review_contract_version}"
    )
    digest = hashlib.sha256(material.encode("ascii")).hexdigest()
    return f"job_byox_review_s2_p{review_contract_version}_{digest[:32]}"


def byox_s2_repair_builder_job_id(
    baseline_sha256: str,
    project_id: str,
    generation: int,
    *,
    remediation_policy_version: int = 1,
) -> str:
    """Return the baseline-scoped identity of one remediation builder."""

    baseline = _sha256(baseline_sha256, "baseline_sha256")
    project = _text(project_id, "project_id", limit=200)
    if type(generation) is not int or generation < 1 or generation > 999_999:
        raise ByoxBaselineError("remediation generation is out of range")
    if (
        type(remediation_policy_version) is not int
        or remediation_policy_version < 1
        or remediation_policy_version > 999_999
    ):
        raise ByoxBaselineError("remediation policy version is out of range")
    material = (
        f"s2\0{remediation_policy_version}\0{generation}\0"
        f"{baseline}\0{project}"
    )
    digest = hashlib.sha256(material.encode("utf-8")).hexdigest()[:32]
    return (
        f"job_byox_repair_s2_v{remediation_policy_version}"
        f"_g{generation}_{digest}"
    )


def byox_s2_repair_reviewer_job_id(
    baseline_sha256: str,
    project_id: str,
    generation: int,
    *,
    remediation_policy_version: int = 1,
) -> str:
    """Return the baseline-scoped identity of one remediation reviewer."""

    baseline = _sha256(baseline_sha256, "baseline_sha256")
    project = _text(project_id, "project_id", limit=200)
    if type(generation) is not int or generation < 1 or generation > 999_999:
        raise ByoxBaselineError("remediation generation is out of range")
    if (
        type(remediation_policy_version) is not int
        or remediation_policy_version < 1
        or remediation_policy_version > 999_999
    ):
        raise ByoxBaselineError("remediation policy version is out of range")
    material = (
        f"review-s2\0{remediation_policy_version}\0{generation}\0"
        f"{baseline}\0{project}"
    )
    digest = hashlib.sha256(material.encode("utf-8")).hexdigest()[:32]
    return (
        f"job_byox_repair_review_s2_v{remediation_policy_version}"
        f"_g{generation}_{digest}"
    )


def byox_remediation_binding_policy_version(
    remediation_policy_version: int, generation: int
) -> int:
    """Encode policy and generation injectively for the binding uniqueness key."""

    if (
        type(remediation_policy_version) is not int
        or not 1 <= remediation_policy_version < _BYOX_REMEDIATION_BINDING_VERSION_RADIX
        or type(generation) is not int
        or not 1 <= generation < _BYOX_REMEDIATION_BINDING_VERSION_RADIX
    ):
        raise ByoxBaselineError("remediation binding version is out of range")
    return remediation_policy_version * _BYOX_REMEDIATION_BINDING_VERSION_RADIX + generation


def make_job_definition(
    *,
    job_id: str,
    job_type: str,
    worker_type: str,
    payload: Mapping[str, Any],
    priority: float,
    score_components: Mapping[str, Any],
    dependencies: Sequence[str],
    max_attempts: int,
    model: str | None,
    reasoning_effort: str | None,
) -> ByoxJobDefinition:
    """Normalize all immutable job fields into one exact definition."""

    identifier = _job_id(job_id, "job_id")
    return ByoxJobDefinition(
        job_id=identifier,
        job_type=_text(job_type, "job_type", limit=300),
        worker_type=_text(worker_type, "worker_type", limit=300),
        priority=_finite_number(priority, "priority"),
        score_components_json=_canonical_object(score_components, "score components"),
        payload_json=_canonical_object(payload, "job payload"),
        max_attempts=max_attempts,
        model=_optional_text(model, "model", limit=300),
        reasoning_effort=_optional_text(
            reasoning_effort, "reasoning_effort", limit=100
        ),
        dependencies=_dependencies(identifier, dependencies),
    )


def job_definition_sha256(definition: ByoxJobDefinition) -> str:
    """Hash an exact job definition with an explicit domain/version prefix."""

    if not isinstance(definition, ByoxJobDefinition):
        raise ByoxBaselineError("definition must be ByoxJobDefinition")
    material = _canonical_document(definition.material(), "job definition")
    return hashlib.sha256(
        b"learnfactory-byox-job-definition-v1\0" + material.encode("utf-8")
    ).hexdigest()


def load_job_definition(
    connection: sqlite3.Connection, job_id: str
) -> ByoxJobDefinition | None:
    """Load and strictly normalize the current immutable definition of a job."""

    identifier = _job_id(job_id, "job_id")
    row = connection.execute(
        """
        SELECT job_id,type,worker_type,priority,score_components_json,payload_json,
               max_attempts,model,reasoning_effort
        FROM jobs WHERE job_id=?
        """,
        (identifier,),
    ).fetchone()
    if row is None:
        return None
    dependencies = tuple(
        str(item["depends_on_job_id"])
        for item in connection.execute(
            """
            SELECT depends_on_job_id FROM job_dependencies
            WHERE job_id=? ORDER BY depends_on_job_id
            """,
            (identifier,),
        )
    )
    score, _ = _strict_object_document(
        row["score_components_json"], "stored score components"
    )
    payload, _ = _strict_object_document(row["payload_json"], "stored job payload")
    return make_job_definition(
        job_id=str(row["job_id"]),
        job_type=str(row["type"]),
        worker_type=str(row["worker_type"]),
        payload=payload,
        priority=row["priority"],
        score_components=score,
        dependencies=dependencies,
        max_attempts=row["max_attempts"],
        model=row["model"],
        reasoning_effort=row["reasoning_effort"],
    )


def load_byox_baseline(
    connection: sqlite3.Connection, baseline_sha256: str
) -> ByoxBaseline | None:
    """Load a baseline and independently verify its canonical material digest."""

    digest = _sha256(baseline_sha256, "baseline_sha256")
    row = connection.execute(
        """
        SELECT baseline_sha256,schema_version,project_id,source_id,
               source_commit_hash,extractor_version,material_json,first_observed_at
        FROM byox_baseline_snapshots WHERE baseline_sha256=?
        """,
        (digest,),
    ).fetchone()
    if row is None:
        return None
    _finite_timestamp(row["first_observed_at"], "stored first_observed_at")
    return ByoxBaseline(
        baseline_sha256=str(row["baseline_sha256"]),
        schema_version=int(row["schema_version"]),
        project_id=str(row["project_id"]),
        source_id=str(row["source_id"]),
        source_commit_hash=str(row["source_commit_hash"]),
        extractor_version=str(row["extractor_version"]),
        material_json=str(row["material_json"]),
    )


def insert_or_verify_baseline(
    db: Database,
    connection: sqlite3.Connection,
    baseline: ByoxBaseline,
    *,
    first_observed_at: float | None = None,
) -> bool:
    """Insert one baseline or prove the existing row is byte-for-byte authoritative.

    The caller must own the surrounding transaction.  Returning ``True`` means
    this call inserted the durable row; repeated observation returns ``False``
    without changing the original timestamp.
    """

    _require_transaction(connection)
    if not isinstance(baseline, ByoxBaseline):
        raise ByoxBaselineError("baseline must be ByoxBaseline")
    observed = _finite_timestamp(
        now() if first_observed_at is None else first_observed_at,
        "first_observed_at",
    )
    existing = load_byox_baseline(connection, baseline.baseline_sha256)
    if existing is not None:
        if existing != baseline:
            raise ByoxBaselineConflict("baseline hash is occupied by different material")
        return False
    source = connection.execute(
        "SELECT commit_hash FROM sources WHERE source_id=?",
        (baseline.source_id,),
    ).fetchone()
    if source is None or source["commit_hash"] != baseline.source_commit_hash:
        raise ByoxBaselineConflict("baseline source identity is not authoritative")
    try:
        connection.execute(
            """
            INSERT INTO byox_baseline_snapshots(
                baseline_sha256,schema_version,project_id,source_id,
                source_commit_hash,extractor_version,material_json,first_observed_at
            ) VALUES (?,?,?,?,?,?,?,?)
            """,
            (
                baseline.baseline_sha256,
                baseline.schema_version,
                baseline.project_id,
                baseline.source_id,
                baseline.source_commit_hash,
                baseline.extractor_version,
                baseline.material_json,
                observed,
            ),
        )
    except sqlite3.IntegrityError as error:
        existing = load_byox_baseline(connection, baseline.baseline_sha256)
        if existing == baseline:
            return False
        raise ByoxBaselineConflict("baseline identity conflicts with durable state") from error
    db.emit_event(
        "controller",
        "BYOX_BASELINE_SNAPSHOT_RECORDED",
        payload={
            "baseline_sha256": baseline.baseline_sha256,
            "project_id": baseline.project_id,
            "source_id": baseline.source_id,
        },
        connection=connection,
    )
    return True


def insert_or_verify_job(
    db: Database,
    connection: sqlite3.Connection,
    definition: ByoxJobDefinition,
    *,
    created_at: float | None = None,
    secret_value_provider: SecretValueProvider | None = None,
) -> bool:
    """Publish a DISCOVERED job and all dependencies, or exact-verify it.

    Every dependency is inserted before a baseline binding is created and while
    the new child is DISCOVERED, satisfying migration 018's graph immutability.
    """

    _require_transaction(connection)
    if not isinstance(definition, ByoxJobDefinition):
        raise ByoxBaselineError("definition must be ByoxJobDefinition")
    provider = secret_value_provider or _controller_credential_values
    _reject_controller_credentials(definition.payload_json, provider)
    existing = load_job_definition(connection, definition.job_id)
    if existing is not None:
        if existing != definition:
            raise ByoxBaselineConflict(
                f"job {definition.job_id} has a conflicting immutable definition"
            )
        return False
    for dependency in definition.dependencies:
        if connection.execute(
            "SELECT 1 FROM jobs WHERE job_id=?", (dependency,)
        ).fetchone() is None:
            raise ByoxBaselineConflict(
                f"job {definition.job_id} has a missing prerequisite"
            )
    created = _finite_timestamp(
        now() if created_at is None else created_at, "created_at"
    )
    try:
        connection.execute(
            """
            INSERT INTO jobs(
                job_id,type,worker_type,state,priority,score_components_json,
                payload_json,max_attempts,created_at,model,reasoning_effort
            ) VALUES (?,?,?,'DISCOVERED',?,?,?,?,?,?,?)
            """,
            (
                definition.job_id,
                definition.job_type,
                definition.worker_type,
                definition.priority,
                definition.score_components_json,
                definition.payload_json,
                definition.max_attempts,
                created,
                definition.model,
                definition.reasoning_effort,
            ),
        )
        for dependency in definition.dependencies:
            connection.execute(
                """
                INSERT INTO job_dependencies(job_id,depends_on_job_id)
                VALUES (?,?)
                """,
                (definition.job_id, dependency),
            )
    except sqlite3.IntegrityError as error:
        existing = load_job_definition(connection, definition.job_id)
        if existing == definition:
            return False
        raise ByoxBaselineConflict(
            f"job {definition.job_id} conflicts with durable state"
        ) from error
    db.emit_event(
        "controller",
        "JOB_DISCOVERED",
        job_id=definition.job_id,
        payload={
            "type": definition.job_type,
            "worker_type": definition.worker_type,
            "priority": definition.priority,
            "baseline_publication": True,
        },
        connection=connection,
    )
    return True


def load_verified_binding(
    connection: sqlite3.Connection, job_id: str
) -> ByoxBaselineJobBinding | None:
    """Load a binding and verify its baseline and live job definition digest."""

    identifier = _job_id(job_id, "job_id")
    row = connection.execute(
        """
        SELECT job_id,baseline_sha256,role,policy_version,builder_job_id,
               definition_sha256,bound_at
        FROM byox_baseline_job_bindings WHERE job_id=?
        """,
        (identifier,),
    ).fetchone()
    if row is None:
        return None
    binding = ByoxBaselineJobBinding(
        job_id=str(row["job_id"]),
        baseline_sha256=str(row["baseline_sha256"]),
        role=str(row["role"]),
        policy_version=int(row["policy_version"]),
        builder_job_id=(
            str(row["builder_job_id"])
            if row["builder_job_id"] is not None
            else None
        ),
        definition_sha256=str(row["definition_sha256"]),
        bound_at=float(row["bound_at"]),
    )
    if load_byox_baseline(connection, binding.baseline_sha256) is None:
        raise ByoxBaselineConflict("binding refers to an invalid baseline")
    definition = load_job_definition(connection, binding.job_id)
    if (
        definition is None
        or job_definition_sha256(definition) != binding.definition_sha256
    ):
        raise ByoxBaselineConflict("bound job definition digest does not match")
    if binding.role == "reviewer":
        assert binding.builder_job_id is not None
        builder_row = connection.execute(
            """
            SELECT baseline_sha256,role FROM byox_baseline_job_bindings
            WHERE job_id=?
            """,
            (binding.builder_job_id,),
        ).fetchone()
        if (
            builder_row is None
            or builder_row["role"] != "builder"
            or builder_row["baseline_sha256"] != binding.baseline_sha256
            or binding.builder_job_id not in definition.dependencies
        ):
            raise ByoxBaselineConflict("reviewer is not bound to its exact builder")
    return binding


def insert_or_verify_binding(
    db: Database,
    connection: sqlite3.Connection,
    baseline: ByoxBaseline,
    definition: ByoxJobDefinition,
    *,
    role: str,
    policy_version: int,
    builder_job_id: str | None = None,
    bound_at: float | None = None,
) -> bool:
    """Bind one new S2 definition to controller authority.

    Historical or specialized adoption is deliberately not an option here.  It
    needs a separate API with its own released-spec and causal-evidence policy.
    """

    _require_transaction(connection)
    durable_baseline = load_byox_baseline(connection, baseline.baseline_sha256)
    if durable_baseline != baseline:
        raise ByoxBaselineConflict("baseline must be durably recorded before binding")
    actual = load_job_definition(connection, definition.job_id)
    if actual != definition:
        raise ByoxBaselineConflict("cannot bind a different live job definition")
    observed = _finite_timestamp(now() if bound_at is None else bound_at, "bound_at")
    digest = job_definition_sha256(definition)
    expected = ByoxBaselineJobBinding(
        job_id=definition.job_id,
        baseline_sha256=baseline.baseline_sha256,
        role=role,
        policy_version=policy_version,
        builder_job_id=builder_job_id,
        definition_sha256=digest,
        bound_at=observed,
    )
    _require_s2_binding_identity(baseline, definition, expected)
    existing = load_verified_binding(connection, definition.job_id)
    if existing is not None:
        if (
            existing.job_id != expected.job_id
            or existing.baseline_sha256 != expected.baseline_sha256
            or existing.role != expected.role
            or existing.policy_version != expected.policy_version
            or existing.builder_job_id != expected.builder_job_id
            or existing.definition_sha256 != expected.definition_sha256
        ):
            raise ByoxBaselineConflict("job already has a different baseline binding")
        return False
    baseline_row = connection.execute(
        """
        SELECT first_observed_at FROM byox_baseline_snapshots
        WHERE baseline_sha256=?
        """,
        (baseline.baseline_sha256,),
    ).fetchone()
    job_row = connection.execute(
        """
        SELECT state,attempt_count,owner,lease_token,lease_expires_at,
               heartbeat_at,retry_at,created_at,started_at,finished_at,error,
               failure_kind,workspace,cancel_requested
        FROM jobs WHERE job_id=?
        """,
        (definition.job_id,),
    ).fetchone()
    assert baseline_row is not None and job_row is not None
    first_observed = _finite_timestamp(
        baseline_row["first_observed_at"], "stored first_observed_at"
    )
    job_created = _finite_timestamp(job_row["created_at"], "stored job created_at")
    if (
        job_row["state"] != "DISCOVERED"
        or job_row["attempt_count"] != 0
        or job_row["owner"] is not None
        or job_row["lease_token"] is not None
        or job_row["lease_expires_at"] is not None
        or job_row["heartbeat_at"] is not None
        or job_row["retry_at"] is not None
        or job_row["started_at"] is not None
        or job_row["finished_at"] is not None
        or job_row["error"] is not None
        or job_row["failure_kind"] is not None
        or job_row["workspace"] is not None
        or job_row["cancel_requested"] != 0
    ):
        raise ByoxBaselineConflict(
            "an unbound job must be pristine before controller binding"
        )
    if not first_observed <= job_created <= observed:
        raise ByoxBaselineConflict(
            "job creation is outside its baseline binding interval"
        )
    if role == "reviewer":
        assert builder_job_id is not None
        builder = load_verified_binding(connection, builder_job_id)
        if (
            builder is None
            or builder.role != "builder"
            or builder.baseline_sha256 != baseline.baseline_sha256
            or builder_job_id not in definition.dependencies
        ):
            raise ByoxBaselineConflict(
                "reviewer requires its dependency to be a same-baseline bound builder"
            )
    try:
        connection.execute(
            """
            INSERT INTO byox_baseline_job_bindings(
                job_id,baseline_sha256,role,policy_version,builder_job_id,
                definition_sha256,bound_at
            ) VALUES (?,?,?,?,?,?,?)
            """,
            (
                expected.job_id,
                expected.baseline_sha256,
                expected.role,
                expected.policy_version,
                expected.builder_job_id,
                expected.definition_sha256,
                expected.bound_at,
            ),
        )
    except sqlite3.IntegrityError as error:
        existing = load_verified_binding(connection, definition.job_id)
        if existing is not None and (
            existing.job_id,
            existing.baseline_sha256,
            existing.role,
            existing.policy_version,
            existing.builder_job_id,
            existing.definition_sha256,
        ) == (
            expected.job_id,
            expected.baseline_sha256,
            expected.role,
            expected.policy_version,
            expected.builder_job_id,
            expected.definition_sha256,
        ):
            return False
        raise ByoxBaselineConflict("baseline binding identity conflicts") from error
    db.emit_event(
        "controller",
        "BYOX_BASELINE_JOB_BOUND",
        job_id=definition.job_id,
        payload={
            "baseline_sha256": baseline.baseline_sha256,
            "role": role,
            "policy_version": policy_version,
            "builder_job_id": builder_job_id,
            "definition_sha256": digest,
        },
        connection=connection,
    )
    return True


def insert_or_verify_bound_job(
    db: Database,
    connection: sqlite3.Connection,
    baseline: ByoxBaseline,
    definition: ByoxJobDefinition,
    *,
    role: str,
    policy_version: int,
    builder_job_id: str | None = None,
    created_at: float | None = None,
    bound_at: float | None = None,
    secret_value_provider: SecretValueProvider | None = None,
) -> ByoxBoundJobPublication:
    """Atomically publish or exact-verify a job and its immutable binding."""

    created = insert_or_verify_job(
        db,
        connection,
        definition,
        created_at=created_at,
        secret_value_provider=secret_value_provider,
    )
    bound = insert_or_verify_binding(
        db,
        connection,
        baseline,
        definition,
        role=role,
        policy_version=policy_version,
        builder_job_id=builder_job_id,
        bound_at=bound_at,
    )
    return ByoxBoundJobPublication(created, bound)


def _canonical_object(value: Mapping[str, Any], label: str) -> str:
    if not isinstance(value, Mapping):
        raise ByoxBaselineError(f"{label} must be an object")
    return _canonical_document(dict(value), label)


def _require_s2_binding_identity(
    baseline: ByoxBaseline,
    definition: ByoxJobDefinition,
    binding: ByoxBaselineJobBinding,
) -> None:
    payload = definition.payload()
    policy = payload.get("seed_policy")
    if (
        payload.get("baseline_sha256") != baseline.baseline_sha256
        or payload.get("project_id") != baseline.project_id
        or not isinstance(policy, dict)
    ):
        raise ByoxBaselineConflict(
            "S2 payload does not identify the controller-derived baseline"
        )
    generation = policy.get("remediation_generation")
    if generation is None:
        generation = payload.get("remediation_generation")
    is_remediation = type(generation) is int and generation >= 1
    if binding.role == "builder" and is_remediation:
        if (
            policy.get("kind") != "byox_reference_repair_s2"
            or policy.get("generation") != generation
            or policy.get("baseline_sha256") != baseline.baseline_sha256
            or binding.policy_version
            != byox_remediation_binding_policy_version(
                policy.get("version"), generation
            )
            or definition.job_id
            != byox_s2_repair_builder_job_id(
                baseline.baseline_sha256,
                baseline.project_id,
                generation,
                remediation_policy_version=policy.get("version"),
            )
        ):
            raise ByoxBaselineConflict(
                "binding is not the deterministic S2 remediation builder identity"
            )
        return
    if binding.role == "builder":
        if (
            policy.get("kind") != "byox_reference_build_s2"
            or binding.policy_version != BYOX_SNAPSHOT_JOB_SCHEME_VERSION
            or definition.job_id
            != byox_s2_builder_job_id(baseline.baseline_sha256)
        ):
            raise ByoxBaselineConflict(
                "binding is not the deterministic S2 builder identity"
            )
        return
    assert binding.builder_job_id is not None
    if payload.get("builder_job_id") != binding.builder_job_id:
        raise ByoxBaselineConflict("S2 reviewer payload names another builder")
    if is_remediation:
        if (
            policy.get("kind") != "byox_reference_repair_review_s2"
            or policy.get("baseline_sha256") != baseline.baseline_sha256
            or payload.get("remediation_generation") != generation
            or binding.policy_version
            != byox_remediation_binding_policy_version(
                policy.get("remediation_policy_version"), generation
            )
            or definition.job_id
            != byox_s2_repair_reviewer_job_id(
                baseline.baseline_sha256,
                baseline.project_id,
                generation,
                remediation_policy_version=policy.get(
                    "remediation_policy_version"
                ),
            )
        ):
            raise ByoxBaselineConflict(
                "binding is not the deterministic S2 remediation reviewer identity"
            )
        return
    if policy.get("kind") != "byox_reference_review_s2":
        raise ByoxBaselineConflict("binding is not an S2 base reviewer")
    expected_reviewer = byox_s2_reviewer_job_id(
        baseline.baseline_sha256,
        binding.builder_job_id,
        review_contract_version=binding.policy_version,
    )
    if definition.job_id != expected_reviewer:
        raise ByoxBaselineConflict(
            "binding is not the deterministic S2 reviewer identity"
        )


def _canonical_document(value: Any, label: str) -> str:
    try:
        rendered = json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
        decoded = strict_json_loads(rendered, max_bytes=MAX_STORED_JSON_BYTES)
        return json.dumps(
            decoded,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
    except (StrictJsonError, TypeError, ValueError) as error:
        raise ByoxBaselineError(f"{label} is not bounded strict JSON") from error


def _strict_object_document(raw: object, label: str) -> tuple[dict[str, Any], str]:
    if not isinstance(raw, str):
        raise ByoxBaselineError(f"{label} must be JSON text")
    try:
        value = strict_json_loads(raw, max_bytes=MAX_STORED_JSON_BYTES)
    except StrictJsonError as error:
        raise ByoxBaselineError(f"{label} is not bounded strict JSON") from error
    if not isinstance(value, dict):
        raise ByoxBaselineError(f"{label} must be a JSON object")
    return value, _canonical_document(value, label)


def _dependencies(job_id: str, values: Sequence[str]) -> tuple[str, ...]:
    if isinstance(values, (str, bytes)):
        raise ByoxBaselineError("dependencies must be a sequence of job IDs")
    normalized = tuple(sorted({_job_id(item, "dependency") for item in values}))
    if len(normalized) != len(values):
        raise ByoxBaselineError("dependencies must not contain duplicates")
    if job_id in normalized:
        raise ByoxBaselineError("job cannot depend on itself")
    return normalized


def _require_transaction(connection: sqlite3.Connection) -> None:
    if not connection.in_transaction:
        raise ByoxBaselineError("baseline publication requires a caller-owned transaction")


def _job_id(value: object, label: str) -> str:
    if not isinstance(value, str) or _JOB_ID.fullmatch(value) is None:
        raise ByoxBaselineError(f"{label} is not a valid job ID")
    return value


def _sha256(value: object, label: str) -> str:
    if not isinstance(value, str) or _HEX_SHA256.fullmatch(value) is None:
        raise ByoxBaselineError(f"{label} must be a lowercase SHA-256 digest")
    return value


def _text(value: object, label: str, *, limit: int) -> str:
    if (
        not isinstance(value, str)
        or not value.strip()
        or len(value) > limit
        or "\0" in value
    ):
        raise ByoxBaselineError(f"{label} must be bounded nonempty text")
    return value.strip()


def _optional_text(value: object, label: str, *, limit: int) -> str | None:
    if value is None:
        return None
    return _text(value, label, limit=limit)


def _finite_number(value: object, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ByoxBaselineError(f"{label} must be a finite number")
    rendered = float(value)
    if not math.isfinite(rendered):
        raise ByoxBaselineError(f"{label} must be a finite number")
    return rendered


def _optional_number(value: object, label: str) -> float | None:
    return None if value is None else _finite_number(value, label)


def _finite_timestamp(value: object, label: str) -> float:
    rendered = _finite_number(value, label)
    if rendered < 0:
        raise ByoxBaselineError(f"{label} must be nonnegative")
    return rendered
