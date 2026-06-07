"""Wave 6 measured system-level cognition contracts.

Wave 6 is a measured system-level cognition attempt. It is not an AGI
claim. The contracts in this module lock the proof vocabulary for a clean,
testable master loop before later modules add donor ingestion, reality-delta
learning, transfer pressure, falsification ledgers, and human review.

The central success criterion is intentionally narrow and falsifiable: the
system changed future reasoning because measured reality corrected it. These
contracts preserve that target while blocking automatic execution,
self-validation, production claims, certification claims, and premature AGI
claims.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, TypeVar

T = TypeVar("T")
E = TypeVar("E", bound=StrEnum)

WAVE_SIX_CONTRACT_SCHEMA_VERSION = "ix-cognition-kernel-wave6-contract-v1"
WAVE_SIX_BUNDLE_SCHEMA_VERSION = "ix-cognition-kernel-wave6-contract-bundle-v1"


class WaveSixLoopStage(StrEnum):
    """Canonical Wave 6 master-loop stages."""

    INTENT = "intent"
    PERMISSION = "permission"
    PREDICTION = "prediction"
    TRIAL = "trial"
    OUTCOME = "outcome"
    DELTA = "delta"
    MEMORY_UPDATE = "memory-update"
    TRANSFER_CHECK = "transfer-check"
    FALSIFICATION = "falsification"
    HUMAN_REVIEW = "human-review"


class WaveSixCapabilityArea(StrEnum):
    """Capability areas required for a real Wave 6 attempt."""

    MASTER_LOOP = "master-loop"
    MEASURED_SYSTEM_LEVEL_COGNITION = "measured-system-level-cognition"
    REALITY_CORRECTED_REASONING = "reality-corrected-reasoning"
    FUTURE_REASONING_CHANGE = "future-reasoning-change"
    CROSS_DOMAIN_TRANSFER = "cross-domain-transfer"
    NOVELTY_PRESSURE = "novelty-pressure"
    FALSIFICATION_DISCIPLINE = "falsification-discipline"
    HUMAN_AUTHORITY_PRESERVATION = "human-authority-preservation"
    DONOR_TRACEABILITY = "donor-traceability"
    INDEPENDENT_REVIEW_READINESS = "independent-review-readiness"


class WaveSixArtifactKind(StrEnum):
    """Artifact classes needed before Wave 6 can be reviewed."""

    MASTER_LOOP_CONTRACT = "master-loop-contract"
    MEASURED_COGNITION_RECORD = "measured-cognition-record"
    REALITY_CORRECTION_RECORD = "reality-correction-record"
    FUTURE_REASONING_CHANGE_PROOF = "future-reasoning-change-proof"
    TRANSFER_NOVELTY_RECORD = "transfer-novelty-record"
    FALSIFICATION_RECORD = "falsification-record"
    HUMAN_REVIEW_DOCKET = "human-review-docket"
    DONOR_TRACEABILITY_MAP = "donor-traceability-map"
    INDEPENDENT_REVIEW_PACKET = "independent-review-packet"
    CLAIM_BOUNDARY_DECLARATION = "claim-boundary-declaration"


class WaveSixSourceSystem(StrEnum):
    """Source systems allowed to contribute Wave 6 contract evidence."""

    IX_COGNITION_KERNEL = "ix-cognition-kernel"
    IX_FUNCTION = "ix-function"
    IX_INTENT_REALITY_LOOP = "ix-intent-reality-loop"
    IX_BLACKFOX = "ix-blackfox"
    IX_BLACKFOX_COGNITION = "ix-blackfox-cognition"
    IX_BLACKFOX_WORLDTWIN = "ix-blackfox-worldtwin"
    IX_AUTONOMY_ASSURANCE_RUNTIME = "ix-autonomy-assurance-runtime"
    IX_MAIN = "ix-main"
    LOCAL_TEST_SUITE = "local-test-suite"
    HUMAN_REVIEW = "human-review"
    INDEPENDENT_EVALUATOR = "independent-evaluator"


class WaveSixDecisionState(StrEnum):
    """Fail-closed contract decision states."""

    RECORD_ONLY = "record-only"
    NEEDS_MORE_EVIDENCE = "needs-more-evidence"
    READY_FOR_WAVE_SIX_LOOP = "ready-for-wave-six-loop"
    READY_FOR_INDEPENDENT_REVIEW = "ready-for-independent-review"
    BLOCKED = "blocked"


class WaveSixClaimBoundary(StrEnum):
    """Claim boundaries that keep Wave 6 honest."""

    MEASURED_SYSTEM_LEVEL_COGNITION_ATTEMPT = (
        "measured-system-level-cognition-attempt"
    )
    NO_AGI_CLAIM = "no-agi-claim"
    NO_PRODUCTION_CLAIM = "no-production-claim"
    NO_CERTIFICATION_CLAIM = "no-certification-claim"
    NO_AUTONOMOUS_AUTHORITY = "no-autonomous-authority"
    NO_SELF_VALIDATION = "no-self-validation"
    TRANSFER_NOVELTY_FALSIFICATION_REQUIRED = (
        "transfer-novelty-falsification-required"
    )
    HUMAN_REVIEW_REQUIRED = "human-review-required"


WAVE_SIX_REQUIRED_LOOP_STAGES: tuple[WaveSixLoopStage, ...] = (
    WaveSixLoopStage.INTENT,
    WaveSixLoopStage.PERMISSION,
    WaveSixLoopStage.PREDICTION,
    WaveSixLoopStage.TRIAL,
    WaveSixLoopStage.OUTCOME,
    WaveSixLoopStage.DELTA,
    WaveSixLoopStage.MEMORY_UPDATE,
    WaveSixLoopStage.TRANSFER_CHECK,
    WaveSixLoopStage.FALSIFICATION,
    WaveSixLoopStage.HUMAN_REVIEW,
)

WAVE_SIX_REQUIRED_CAPABILITY_AREAS: tuple[WaveSixCapabilityArea, ...] = (
    WaveSixCapabilityArea.MASTER_LOOP,
    WaveSixCapabilityArea.MEASURED_SYSTEM_LEVEL_COGNITION,
    WaveSixCapabilityArea.REALITY_CORRECTED_REASONING,
    WaveSixCapabilityArea.FUTURE_REASONING_CHANGE,
    WaveSixCapabilityArea.CROSS_DOMAIN_TRANSFER,
    WaveSixCapabilityArea.NOVELTY_PRESSURE,
    WaveSixCapabilityArea.FALSIFICATION_DISCIPLINE,
    WaveSixCapabilityArea.HUMAN_AUTHORITY_PRESERVATION,
    WaveSixCapabilityArea.DONOR_TRACEABILITY,
    WaveSixCapabilityArea.INDEPENDENT_REVIEW_READINESS,
)

WAVE_SIX_REQUIRED_ARTIFACT_KINDS: tuple[WaveSixArtifactKind, ...] = (
    WaveSixArtifactKind.MASTER_LOOP_CONTRACT,
    WaveSixArtifactKind.MEASURED_COGNITION_RECORD,
    WaveSixArtifactKind.REALITY_CORRECTION_RECORD,
    WaveSixArtifactKind.FUTURE_REASONING_CHANGE_PROOF,
    WaveSixArtifactKind.TRANSFER_NOVELTY_RECORD,
    WaveSixArtifactKind.FALSIFICATION_RECORD,
    WaveSixArtifactKind.HUMAN_REVIEW_DOCKET,
    WaveSixArtifactKind.DONOR_TRACEABILITY_MAP,
    WaveSixArtifactKind.INDEPENDENT_REVIEW_PACKET,
    WaveSixArtifactKind.CLAIM_BOUNDARY_DECLARATION,
)

WAVE_SIX_REQUIRED_CLAIM_BOUNDARIES: tuple[WaveSixClaimBoundary, ...] = (
    WaveSixClaimBoundary.MEASURED_SYSTEM_LEVEL_COGNITION_ATTEMPT,
    WaveSixClaimBoundary.NO_AGI_CLAIM,
    WaveSixClaimBoundary.NO_PRODUCTION_CLAIM,
    WaveSixClaimBoundary.NO_CERTIFICATION_CLAIM,
    WaveSixClaimBoundary.NO_AUTONOMOUS_AUTHORITY,
    WaveSixClaimBoundary.NO_SELF_VALIDATION,
    WaveSixClaimBoundary.TRANSFER_NOVELTY_FALSIFICATION_REQUIRED,
    WaveSixClaimBoundary.HUMAN_REVIEW_REQUIRED,
)

WAVE_SIX_DONOR_SOURCE_SYSTEMS: tuple[WaveSixSourceSystem, ...] = (
    WaveSixSourceSystem.IX_FUNCTION,
    WaveSixSourceSystem.IX_INTENT_REALITY_LOOP,
    WaveSixSourceSystem.IX_BLACKFOX,
    WaveSixSourceSystem.IX_BLACKFOX_COGNITION,
    WaveSixSourceSystem.IX_BLACKFOX_WORLDTWIN,
    WaveSixSourceSystem.IX_AUTONOMY_ASSURANCE_RUNTIME,
    WaveSixSourceSystem.IX_MAIN,
)


@dataclass(frozen=True, slots=True)
class WaveSixContractArtifact:
    """One reviewable contract artifact for the Wave 6 master loop."""

    artifact_id: str
    kind: WaveSixArtifactKind
    capability_area: WaveSixCapabilityArea
    source_system: WaveSixSourceSystem
    summary: str
    loop_stages: tuple[WaveSixLoopStage, ...]
    evidence_ids: tuple[str, ...]
    produced_by_engine_id: str
    decision: WaveSixDecisionState = WaveSixDecisionState.NEEDS_MORE_EVIDENCE
    claim_boundaries: tuple[WaveSixClaimBoundary, ...] = (
        WAVE_SIX_REQUIRED_CLAIM_BOUNDARIES
    )
    requires_human_review: bool = True
    allows_autonomous_execution: bool = False
    claims_agi: bool = False
    claims_production_ready: bool = False
    claims_certified: bool = False
    self_validated: bool = False
    schema_version: str = WAVE_SIX_CONTRACT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate identity, claim boundaries, and fail-closed authority."""

        if not self.requires_human_review:
            raise ValueError("Wave 6 artifacts must require human review.")
        if self.allows_autonomous_execution:
            raise ValueError("Wave 6 artifacts must not allow autonomous execution.")
        if self.claims_agi:
            raise ValueError("Wave 6 artifacts must not claim AGI.")
        if self.claims_production_ready:
            raise ValueError("Wave 6 artifacts must not claim production readiness.")
        if self.claims_certified:
            raise ValueError("Wave 6 artifacts must not claim certification.")
        if self.self_validated:
            raise ValueError("Wave 6 artifacts must not claim self-validation.")
        object.__setattr__(
            self,
            "artifact_id",
            _require_non_empty(self.artifact_id, "artifact_id"),
        )
        object.__setattr__(
            self,
            "summary",
            _require_non_empty(self.summary, "artifact summary"),
        )
        object.__setattr__(
            self,
            "produced_by_engine_id",
            _require_non_empty(self.produced_by_engine_id, "produced_by_engine_id"),
        )
        object.__setattr__(
            self,
            "loop_stages",
            _normalize_unique_enum_tuple(self.loop_stages, label="loop stage"),
        )
        object.__setattr__(
            self,
            "evidence_ids",
            _normalize_unique_text_tuple(self.evidence_ids, label="evidence_id"),
        )
        object.__setattr__(
            self,
            "claim_boundaries",
            _normalize_unique_enum_tuple(self.claim_boundaries, label="claim boundary"),
        )
        object.__setattr__(
            self,
            "schema_version",
            _require_non_empty(self.schema_version, "schema_version"),
        )
        if not self.loop_stages:
            raise ValueError("Wave 6 artifacts require at least one loop stage.")
        if self.review_ready and not self.evidence_ids:
            raise ValueError("Review-ready Wave 6 artifacts require evidence ids.")
        if self.decision is WaveSixDecisionState.BLOCKED and self.review_ready:
            raise ValueError("Blocked Wave 6 artifacts cannot be review-ready.")
        missing_boundaries = tuple(
            boundary
            for boundary in WAVE_SIX_REQUIRED_CLAIM_BOUNDARIES
            if boundary not in self.claim_boundaries
        )
        if missing_boundaries:
            raise ValueError(
                "Wave 6 artifacts must preserve required claim boundary: "
                f"{missing_boundaries[0].value}"
            )

    @property
    def evidence_bound(self) -> bool:
        """Return whether this artifact references evidence."""

        return bool(self.evidence_ids)

    @property
    def review_ready(self) -> bool:
        """Return whether the artifact can enter Wave 6 review."""

        return self.decision in {
            WaveSixDecisionState.READY_FOR_WAVE_SIX_LOOP,
            WaveSixDecisionState.READY_FOR_INDEPENDENT_REVIEW,
        }

    @property
    def blocks_wave_six_progress(self) -> bool:
        """Return whether this artifact blocks Wave 6 progress."""

        return self.decision is WaveSixDecisionState.BLOCKED

    def covers_stage(self, stage: WaveSixLoopStage) -> bool:
        """Return whether this artifact covers a master-loop stage."""

        return stage in self.loop_stages

    def canonical_payload(self) -> dict[str, Any]:
        """Return a deterministic payload for artifact hashing."""

        return {
            "allows_autonomous_execution": self.allows_autonomous_execution,
            "artifact_id": self.artifact_id,
            "capability_area": self.capability_area.value,
            "claim_boundaries": [boundary.value for boundary in self.claim_boundaries],
            "claims_agi": self.claims_agi,
            "claims_certified": self.claims_certified,
            "claims_production_ready": self.claims_production_ready,
            "decision": self.decision.value,
            "evidence_ids": list(self.evidence_ids),
            "kind": self.kind.value,
            "loop_stages": [stage.value for stage in self.loop_stages],
            "produced_by_engine_id": self.produced_by_engine_id,
            "requires_human_review": self.requires_human_review,
            "schema_version": self.schema_version,
            "self_validated": self.self_validated,
            "source_system": self.source_system.value,
            "summary": self.summary,
        }

    def fingerprint(self) -> str:
        """Return a deterministic SHA-256 fingerprint for this artifact."""

        return _stable_sha256(self.canonical_payload())


@dataclass(frozen=True, slots=True)
class WaveSixContractBundle:
    """Deterministic bundle of Wave 6 contract artifacts."""

    bundle_id: str
    artifacts: tuple[WaveSixContractArtifact, ...]
    required_loop_stages: tuple[WaveSixLoopStage, ...] = WAVE_SIX_REQUIRED_LOOP_STAGES
    required_capability_areas: tuple[WaveSixCapabilityArea, ...] = (
        WAVE_SIX_REQUIRED_CAPABILITY_AREAS
    )
    required_artifact_kinds: tuple[WaveSixArtifactKind, ...] = (
        WAVE_SIX_REQUIRED_ARTIFACT_KINDS
    )
    required_claim_boundaries: tuple[WaveSixClaimBoundary, ...] = (
        WAVE_SIX_REQUIRED_CLAIM_BOUNDARIES
    )
    notes: tuple[str, ...] = ()
    schema_version: str = WAVE_SIX_BUNDLE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate deterministic ordering, uniqueness, and review boundaries."""

        object.__setattr__(
            self,
            "bundle_id",
            _require_non_empty(self.bundle_id, "bundle_id"),
        )
        if not self.artifacts:
            raise ValueError("Wave 6 contract bundles require at least one artifact.")
        sorted_artifacts = tuple(
            sorted(self.artifacts, key=lambda artifact: artifact.artifact_id)
        )
        _unique_ids(
            (artifact.artifact_id for artifact in sorted_artifacts),
            label="artifact_id",
        )
        object.__setattr__(self, "artifacts", sorted_artifacts)
        object.__setattr__(
            self,
            "required_loop_stages",
            _normalize_unique_enum_tuple(
                self.required_loop_stages, label="required loop stage"
            ),
        )
        object.__setattr__(
            self,
            "required_capability_areas",
            _normalize_unique_enum_tuple(
                self.required_capability_areas, label="required capability area"
            ),
        )
        object.__setattr__(
            self,
            "required_artifact_kinds",
            _normalize_unique_enum_tuple(
                self.required_artifact_kinds, label="required artifact kind"
            ),
        )
        object.__setattr__(
            self,
            "required_claim_boundaries",
            _normalize_unique_enum_tuple(
                self.required_claim_boundaries, label="required claim boundary"
            ),
        )
        object.__setattr__(
            self,
            "notes",
            _normalize_unique_text_tuple(self.notes, label="bundle note"),
        )
        object.__setattr__(
            self,
            "schema_version",
            _require_non_empty(self.schema_version, "schema_version"),
        )

    @property
    def artifact_ids(self) -> tuple[str, ...]:
        """Return artifact ids in deterministic order."""

        return tuple(artifact.artifact_id for artifact in self.artifacts)

    @property
    def blocked_artifact_ids(self) -> tuple[str, ...]:
        """Return artifact ids blocking Wave 6 progress."""

        return tuple(
            artifact.artifact_id
            for artifact in self.artifacts
            if artifact.blocks_wave_six_progress
        )

    @property
    def covered_loop_stages(self) -> tuple[WaveSixLoopStage, ...]:
        """Return required loop stages covered by bundled artifacts."""

        present = {
            stage for artifact in self.artifacts for stage in artifact.loop_stages
        }
        return tuple(
            stage for stage in self.required_loop_stages if stage in present
        )

    @property
    def missing_loop_stages(self) -> tuple[WaveSixLoopStage, ...]:
        """Return required master-loop stages not covered by artifacts."""

        present = {
            stage for artifact in self.artifacts for stage in artifact.loop_stages
        }
        return tuple(
            stage for stage in self.required_loop_stages if stage not in present
        )

    @property
    def missing_capability_areas(self) -> tuple[WaveSixCapabilityArea, ...]:
        """Return required capability areas not represented."""

        present = {artifact.capability_area for artifact in self.artifacts}
        return tuple(
            area for area in self.required_capability_areas if area not in present
        )

    @property
    def missing_artifact_kinds(self) -> tuple[WaveSixArtifactKind, ...]:
        """Return required artifact kinds not represented."""

        present = {artifact.kind for artifact in self.artifacts}
        return tuple(
            kind for kind in self.required_artifact_kinds if kind not in present
        )

    @property
    def missing_claim_boundaries(self) -> tuple[WaveSixClaimBoundary, ...]:
        """Return required claim boundaries not preserved by every artifact."""

        missing: list[WaveSixClaimBoundary] = []
        for boundary in self.required_claim_boundaries:
            boundary_missing = any(
                boundary not in artifact.claim_boundaries for artifact in self.artifacts
            )
            if boundary_missing:
                missing.append(boundary)
        return tuple(missing)

    @property
    def has_complete_loop_coverage(self) -> bool:
        """Return whether every master-loop stage has artifact coverage."""

        return not self.missing_loop_stages

    @property
    def has_required_contract_coverage(self) -> bool:
        """Return whether every required Wave 6 contract dimension is covered."""

        return (
            not self.missing_loop_stages
            and not self.missing_capability_areas
            and not self.missing_artifact_kinds
            and not self.missing_claim_boundaries
            and not self.blocked_artifact_ids
        )

    @property
    def source_systems(self) -> tuple[WaveSixSourceSystem, ...]:
        """Return source systems represented by bundled artifacts."""

        return tuple(
            sorted(
                {artifact.source_system for artifact in self.artifacts},
                key=lambda source_system: source_system.value,
            )
        )

    @property
    def donor_source_systems_present(self) -> tuple[WaveSixSourceSystem, ...]:
        """Return donor source systems represented by bundled artifacts."""

        source_systems = set(self.source_systems)
        return tuple(
            donor for donor in WAVE_SIX_DONOR_SOURCE_SYSTEMS if donor in source_systems
        )

    @property
    def missing_donor_source_systems(self) -> tuple[WaveSixSourceSystem, ...]:
        """Return expected donor source systems not yet represented."""

        source_systems = set(self.source_systems)
        return tuple(
            donor
            for donor in WAVE_SIX_DONOR_SOURCE_SYSTEMS
            if donor not in source_systems
        )

    def artifact_ids_by_stage(self, stage: WaveSixLoopStage) -> tuple[str, ...]:
        """Return artifact ids covering a master-loop stage."""

        return tuple(
            artifact.artifact_id
            for artifact in self.artifacts
            if artifact.covers_stage(stage)
        )

    def canonical_payload(self) -> dict[str, Any]:
        """Return a deterministic payload for bundle hashing."""

        return {
            "artifacts": [artifact.canonical_payload() for artifact in self.artifacts],
            "bundle_id": self.bundle_id,
            "notes": list(self.notes),
            "required_artifact_kinds": [
                kind.value for kind in self.required_artifact_kinds
            ],
            "required_capability_areas": [
                area.value for area in self.required_capability_areas
            ],
            "required_claim_boundaries": [
                boundary.value for boundary in self.required_claim_boundaries
            ],
            "required_loop_stages": [
                stage.value for stage in self.required_loop_stages
            ],
            "schema_version": self.schema_version,
        }

    def fingerprint(self) -> str:
        """Return a deterministic SHA-256 fingerprint for this bundle."""

        return _stable_sha256(self.canonical_payload())


def required_wave_six_loop_stages() -> tuple[WaveSixLoopStage, ...]:
    """Return the locked Wave 6 master-loop stage order."""

    return WAVE_SIX_REQUIRED_LOOP_STAGES


def required_wave_six_capability_areas() -> tuple[WaveSixCapabilityArea, ...]:
    """Return required Wave 6 capability areas."""

    return WAVE_SIX_REQUIRED_CAPABILITY_AREAS


def required_wave_six_artifact_kinds() -> tuple[WaveSixArtifactKind, ...]:
    """Return required Wave 6 artifact kinds."""

    return WAVE_SIX_REQUIRED_ARTIFACT_KINDS


def required_wave_six_claim_boundaries() -> tuple[WaveSixClaimBoundary, ...]:
    """Return the claim boundaries that prevent Wave 6 overclaiming."""

    return WAVE_SIX_REQUIRED_CLAIM_BOUNDARIES


def wave_six_donor_source_systems() -> tuple[WaveSixSourceSystem, ...]:
    """Return the donor repos expected in the Wave 6 integration surface."""

    return WAVE_SIX_DONOR_SOURCE_SYSTEMS


def _require_non_empty(value: str, label: str) -> str:
    """Return stripped text or raise when empty."""

    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{label} must not be empty.")
    return normalized


def _normalize_unique_text_tuple(
    values: Iterable[str], *, label: str
) -> tuple[str, ...]:
    """Normalize text values while rejecting blanks and duplicates."""

    normalized: list[str] = []
    seen: set[str] = set()
    for value in values:
        stripped = _require_non_empty(value, label)
        if stripped in seen:
            raise ValueError(f"Duplicate {label} detected: {stripped}")
        normalized.append(stripped)
        seen.add(stripped)
    return tuple(normalized)


def _normalize_unique_enum_tuple(values: Iterable[E], *, label: str) -> tuple[E, ...]:
    """Return enum values as a tuple while rejecting duplicates."""

    normalized: list[E] = []
    seen: set[E] = set()
    for value in values:
        if value in seen:
            raise ValueError(f"Duplicate {label} detected: {value.value}")
        normalized.append(value)
        seen.add(value)
    return tuple(normalized)


def _unique_ids(values: Iterable[T], *, label: str) -> set[T]:
    """Return unique values while rejecting duplicates."""

    seen: set[T] = set()
    for value in values:
        if value in seen:
            raise ValueError(f"Duplicate {label} detected: {value}")
        seen.add(value)
    return seen


def _stable_sha256(payload: Mapping[str, Any]) -> str:
    """Return deterministic SHA-256 over a canonical JSON payload."""

    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
