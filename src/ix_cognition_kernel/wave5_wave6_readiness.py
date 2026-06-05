"""Wave 5 to Wave 6 readiness-gate records.

Wave 5 can prepare evidence for Wave 6, but it cannot promote itself into Wave 6.
This module records the preconditions that must be visible before independent
Wave 6 validation can even be considered: external protocols, independent
reviewers, reproducibility, adversarial pressure, long-horizon continuity,
cross-domain transfer, safe refusal, human authority, memory integrity,
falsification, repeatability, ecosystem bridges, and unresolved blockers.

A passing gate means "ready to submit for independent Wave 6-style scrutiny." It
does not mean AGI, production readiness, certification, autonomous authority, or
independent validation has been achieved.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, TypeVar

from ix_cognition_kernel.wave5_contracts import (
    WAVE_FIVE_REQUIRED_CLAIM_BOUNDARIES,
    WaveFiveArtifactDecision,
    WaveFiveArtifactKind,
    WaveFiveArtifactRef,
    WaveFiveAuthorityState,
    WaveFiveCapabilityArea,
    WaveFiveClaimBoundary,
    WaveFiveSourceSystem,
    WaveFiveValidationStatus,
)

T = TypeVar("T")
E = TypeVar("E", bound=StrEnum)

WAVE_FIVE_WAVE_SIX_PRECONDITION_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave5-wave6-precondition-v1"
)
WAVE_FIVE_WAVE_SIX_BLOCKER_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave5-wave6-blocker-v1"
)
WAVE_FIVE_WAVE_SIX_GATE_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave5-wave6-readiness-gate-v1"
)


class WaveFiveWaveSixPreconditionKind(StrEnum):
    """Preconditions required before Wave 6 independent validation work."""

    EXTERNAL_PROTOCOLS_PREREGISTERED = "external-protocols-preregistered"
    INDEPENDENT_REVIEWERS_AVAILABLE = "independent-reviewers-available"
    REPRODUCIBLE_EVIDENCE_BUNDLE_READY = "reproducible-evidence-bundle-ready"
    REPEATABILITY_AND_DISSENT_LEDGER_READY = "repeatability-and-dissent-ledger-ready"
    ADVERSARIAL_SAFETY_PRESSURE_READY = "adversarial-safety-pressure-ready"
    LONG_HORIZON_VALIDATION_READY = "long-horizon-validation-ready"
    CROSS_DOMAIN_TRANSFER_READY = "cross-domain-transfer-ready"
    BENCHMARK_GAMING_AUDIT_READY = "benchmark-gaming-audit-ready"
    MEMORY_INTEGRITY_PROOF_READY = "memory-integrity-proof-ready"
    SAFE_REFUSAL_PROOF_READY = "safe-refusal-proof-ready"
    HUMAN_AUTHORITY_PROOF_READY = "human-authority-proof-ready"
    BLACKFOX_BRIDGE_READY = "blackfox-bridge-ready"
    WORLDTWIN_BRIDGE_READY = "worldtwin-bridge-ready"
    FALSIFICATION_LEDGER_READY = "falsification-ledger-ready"
    EVIDENCE_DOSSIER_READY = "evidence-dossier-ready"


class WaveFiveWaveSixPreconditionStatus(StrEnum):
    """Status of one Wave 6 precondition."""

    SATISFIED = "satisfied"
    SATISFIED_WITH_LIMITS = "satisfied-with-limits"
    NEEDS_EXTERNAL_EVIDENCE = "needs-external-evidence"
    DISPUTED = "disputed"
    BLOCKED = "blocked"
    MISSING = "missing"


class WaveFiveWaveSixBlockerKind(StrEnum):
    """Blockers that prevent Wave 6 readiness submission."""

    MISSING_PRECONDITION = "missing-precondition"
    UNRESOLVED_FALSIFICATION = "unresolved-falsification"
    REPRODUCTION_GAP = "reproduction-gap"
    EXTERNAL_REVIEW_GAP = "external-review-gap"
    SAFETY_FAILURE = "safety-failure"
    AUTHORITY_FAILURE = "authority-failure"
    MEMORY_INTEGRITY_FAILURE = "memory-integrity-failure"
    ECOSYSTEM_BRIDGE_GAP = "ecosystem-bridge-gap"
    CLAIM_BOUNDARY_GAP = "claim-boundary-gap"
    AGI_OR_CERTIFICATION_OVERCLAIM = "agi-or-certification-overclaim"
    SELF_CLAIMED_INDEPENDENT_VALIDATION = "self-claimed-independent-validation"


class WaveFiveWaveSixBlockerSeverity(StrEnum):
    """Severity of a Wave 6 readiness blocker."""

    INFORMATIONAL = "informational"
    LIMITATION = "limitation"
    NEEDS_MORE_EVIDENCE = "needs-more-evidence"
    BLOCKING = "blocking"


class WaveFiveWaveSixReadinessState(StrEnum):
    """Review state of the Wave 6 readiness gate."""

    INTERNAL_GATE_READY = "internal-gate-ready"
    READY_FOR_EXTERNAL_WAVE_SIX_REVIEW = "ready-for-external-wave-six-review"
    UNDER_EXTERNAL_WAVE_SIX_REVIEW = "under-external-wave-six-review"
    EXTERNALLY_REVIEWED_WITH_BOUNDARIES = "externally-reviewed-with-boundaries"
    BLOCKED_BY_WAVE_SIX_GAP = "blocked-by-wave-six-gap"


SAFE_WAVE_SIX_PRECONDITION_STATUSES: tuple[
    WaveFiveWaveSixPreconditionStatus, ...
] = (
    WaveFiveWaveSixPreconditionStatus.SATISFIED,
    WaveFiveWaveSixPreconditionStatus.SATISFIED_WITH_LIMITS,
)

BLOCKING_WAVE_SIX_PRECONDITION_STATUSES: tuple[
    WaveFiveWaveSixPreconditionStatus, ...
] = (
    WaveFiveWaveSixPreconditionStatus.NEEDS_EXTERNAL_EVIDENCE,
    WaveFiveWaveSixPreconditionStatus.DISPUTED,
    WaveFiveWaveSixPreconditionStatus.BLOCKED,
    WaveFiveWaveSixPreconditionStatus.MISSING,
)

REQUIRED_WAVE_SIX_PRECONDITIONS: tuple[WaveFiveWaveSixPreconditionKind, ...] = (
    WaveFiveWaveSixPreconditionKind.EXTERNAL_PROTOCOLS_PREREGISTERED,
    WaveFiveWaveSixPreconditionKind.INDEPENDENT_REVIEWERS_AVAILABLE,
    WaveFiveWaveSixPreconditionKind.REPRODUCIBLE_EVIDENCE_BUNDLE_READY,
    WaveFiveWaveSixPreconditionKind.REPEATABILITY_AND_DISSENT_LEDGER_READY,
    WaveFiveWaveSixPreconditionKind.ADVERSARIAL_SAFETY_PRESSURE_READY,
    WaveFiveWaveSixPreconditionKind.LONG_HORIZON_VALIDATION_READY,
    WaveFiveWaveSixPreconditionKind.CROSS_DOMAIN_TRANSFER_READY,
    WaveFiveWaveSixPreconditionKind.BENCHMARK_GAMING_AUDIT_READY,
    WaveFiveWaveSixPreconditionKind.MEMORY_INTEGRITY_PROOF_READY,
    WaveFiveWaveSixPreconditionKind.SAFE_REFUSAL_PROOF_READY,
    WaveFiveWaveSixPreconditionKind.HUMAN_AUTHORITY_PROOF_READY,
    WaveFiveWaveSixPreconditionKind.BLACKFOX_BRIDGE_READY,
    WaveFiveWaveSixPreconditionKind.WORLDTWIN_BRIDGE_READY,
    WaveFiveWaveSixPreconditionKind.FALSIFICATION_LEDGER_READY,
    WaveFiveWaveSixPreconditionKind.EVIDENCE_DOSSIER_READY,
)

EXTERNAL_WAVE_SIX_REVIEW_SOURCE_SYSTEMS: tuple[WaveFiveSourceSystem, ...] = (
    WaveFiveSourceSystem.EXTERNAL_REVIEW,
    WaveFiveSourceSystem.INDEPENDENT_REVIEWER,
    WaveFiveSourceSystem.INDEPENDENT_REPLICATION_LAB,
    WaveFiveSourceSystem.HUMAN_REVIEW,
)


@dataclass(frozen=True, slots=True)
class WaveFiveWaveSixPreconditionRecord:
    """One precondition required before Wave 6 review can begin."""

    precondition_id: str
    precondition_kind: WaveFiveWaveSixPreconditionKind
    status: WaveFiveWaveSixPreconditionStatus
    artifact_ids: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    summary: str
    limitations: tuple[str, ...] = ()
    blocker_ids: tuple[str, ...] = ()
    source_system: WaveFiveSourceSystem = WaveFiveSourceSystem.IX_COGNITION_KERNEL
    claim_boundaries: tuple[WaveFiveClaimBoundary, ...] = (
        WAVE_FIVE_REQUIRED_CLAIM_BOUNDARIES
    )
    schema_version: str = WAVE_FIVE_WAVE_SIX_PRECONDITION_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate precondition evidence, artifacts, status, and boundaries."""

        object.__setattr__(
            self, "precondition_id", _text(self.precondition_id, "precondition_id")
        )
        object.__setattr__(
            self, "artifact_ids", _unique_text(self.artifact_ids, label="artifact_id")
        )
        object.__setattr__(
            self, "evidence_ids", _unique_text(self.evidence_ids, label="evidence_id")
        )
        object.__setattr__(self, "summary", _text(self.summary, "summary"))
        object.__setattr__(
            self, "limitations", _unique_text(self.limitations, label="limitation")
        )
        object.__setattr__(
            self, "blocker_ids", _unique_text(self.blocker_ids, label="blocker_id")
        )
        object.__setattr__(
            self,
            "claim_boundaries",
            _unique_enum(self.claim_boundaries, label="claim boundary"),
        )
        if not self.artifact_ids:
            raise ValueError("Wave 6 preconditions require artifact ids.")
        if not self.evidence_ids:
            raise ValueError("Wave 6 preconditions require evidence ids.")
        if (
            self.status is WaveFiveWaveSixPreconditionStatus.SATISFIED_WITH_LIMITS
            and not self.limitations
        ):
            raise ValueError("Limited Wave 6 preconditions require limitations.")
        if (
            self.status in BLOCKING_WAVE_SIX_PRECONDITION_STATUSES
            and not self.blocker_ids
        ):
            raise ValueError("Blocking Wave 6 preconditions require blocker ids.")
        missing_boundaries = tuple(
            boundary
            for boundary in WAVE_FIVE_REQUIRED_CLAIM_BOUNDARIES
            if boundary not in self.claim_boundaries
        )
        if missing_boundaries:
            raise ValueError(
                "Wave 6 preconditions must preserve claim boundary: "
                f"{missing_boundaries[0].value}"
            )
        object.__setattr__(
            self, "schema_version", _text(self.schema_version, "schema_version")
        )

    @property
    def precondition_key(self) -> str:
        """Return deterministic precondition key."""

        return self.precondition_id

    @property
    def blocks_wave_six_readiness(self) -> bool:
        """Return whether this precondition blocks Wave 6 readiness submission."""

        return self.status in BLOCKING_WAVE_SIX_PRECONDITION_STATUSES

    @property
    def satisfied_with_boundaries(self) -> bool:
        """Return whether this precondition is satisfied without promotion."""

        return (
            self.status in SAFE_WAVE_SIX_PRECONDITION_STATUSES
            and bool(self.evidence_ids)
            and bool(self.artifact_ids)
        )

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic export payload."""

        return {
            "artifact_ids": list(self.artifact_ids),
            "blocker_ids": list(self.blocker_ids),
            "claim_boundaries": [boundary.value for boundary in self.claim_boundaries],
            "evidence_ids": list(self.evidence_ids),
            "limitations": list(self.limitations),
            "precondition_id": self.precondition_id,
            "precondition_kind": self.precondition_kind.value,
            "satisfied_with_boundaries": self.satisfied_with_boundaries,
            "schema_version": self.schema_version,
            "source_system": self.source_system.value,
            "status": self.status.value,
            "summary": self.summary,
        }


@dataclass(frozen=True, slots=True)
class WaveFiveWaveSixReadinessBlocker:
    """Visible blocker that prevents Wave 6 readiness submission."""

    blocker_id: str
    blocker_kind: WaveFiveWaveSixBlockerKind
    severity: WaveFiveWaveSixBlockerSeverity
    precondition_kind: WaveFiveWaveSixPreconditionKind
    description: str
    mitigation: str
    evidence_ids: tuple[str, ...]
    resolved: bool = False
    schema_version: str = WAVE_FIVE_WAVE_SIX_BLOCKER_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate readiness blocker identity and evidence."""

        object.__setattr__(self, "blocker_id", _text(self.blocker_id, "blocker_id"))
        object.__setattr__(self, "description", _text(self.description, "description"))
        object.__setattr__(self, "mitigation", _text(self.mitigation, "mitigation"))
        object.__setattr__(
            self, "evidence_ids", _unique_text(self.evidence_ids, label="evidence_id")
        )
        if not self.evidence_ids:
            raise ValueError("Wave 6 readiness blockers require evidence ids.")
        object.__setattr__(
            self, "schema_version", _text(self.schema_version, "schema_version")
        )

    @property
    def blocker_key(self) -> str:
        """Return deterministic blocker key."""

        return self.blocker_id

    @property
    def blocks_wave_six_readiness(self) -> bool:
        """Return whether this blocker prevents readiness submission."""

        return (
            self.severity is WaveFiveWaveSixBlockerSeverity.BLOCKING
            and not self.resolved
        )

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic export payload."""

        return {
            "blocker_id": self.blocker_id,
            "blocker_kind": self.blocker_kind.value,
            "description": self.description,
            "evidence_ids": list(self.evidence_ids),
            "mitigation": self.mitigation,
            "precondition_kind": self.precondition_kind.value,
            "resolved": self.resolved,
            "schema_version": self.schema_version,
            "severity": self.severity.value,
        }


@dataclass(frozen=True, slots=True)
class WaveFiveWaveSixReadinessGate:
    """Fail-closed Wave 5 gate for possible Wave 6 independent review."""

    gate_id: str
    title: str
    source_system: WaveFiveSourceSystem
    readiness_state: WaveFiveWaveSixReadinessState
    preconditions: tuple[WaveFiveWaveSixPreconditionRecord, ...]
    blockers: tuple[WaveFiveWaveSixReadinessBlocker, ...]
    protocol_ids: tuple[str, ...]
    reviewer_ids: tuple[str, ...] = ()
    attempted_wave_six_promotion: bool = False
    claims_agi: bool = False
    grants_execution_authority: bool = False
    claims_production_ready: bool = False
    claims_certified: bool = False
    claims_independent_validation: bool = False
    claim_boundaries: tuple[WaveFiveClaimBoundary, ...] = (
        WAVE_FIVE_REQUIRED_CLAIM_BOUNDARIES
    )
    notes: tuple[str, ...] = ()
    schema_version: str = WAVE_FIVE_WAVE_SIX_GATE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate Wave 6 readiness coverage and anti-overclaim boundaries."""

        object.__setattr__(self, "gate_id", _text(self.gate_id, "gate_id"))
        object.__setattr__(self, "title", _text(self.title, "title"))
        if self.attempted_wave_six_promotion:
            raise ValueError("Wave 6 readiness gates cannot promote to Wave 6.")
        if self.claims_agi:
            raise ValueError("Wave 6 readiness gates cannot claim AGI.")
        if self.grants_execution_authority:
            raise ValueError("Wave 6 readiness gates cannot grant execution authority.")
        if self.claims_production_ready:
            raise ValueError(
                "Wave 6 readiness gates cannot claim production readiness."
            )
        if self.claims_certified:
            raise ValueError("Wave 6 readiness gates cannot claim certification.")
        if self.claims_independent_validation:
            raise ValueError(
                "Wave 6 readiness gates cannot self-claim independent validation."
            )
        preconditions = tuple(
            sorted(self.preconditions, key=lambda item: item.precondition_key)
        )
        blockers = tuple(sorted(self.blockers, key=lambda item: item.blocker_key))
        if not preconditions:
            raise ValueError("Wave 6 readiness gates require preconditions.")
        _unique_values(
            (item.precondition_id for item in preconditions),
            label="precondition_id",
        )
        _unique_values(
            (item.precondition_kind for item in preconditions),
            label="precondition kind",
        )
        _unique_values((item.blocker_id for item in blockers), label="blocker_id")
        object.__setattr__(self, "preconditions", preconditions)
        object.__setattr__(self, "blockers", blockers)
        object.__setattr__(
            self, "protocol_ids", _unique_text(self.protocol_ids, label="protocol_id")
        )
        if not self.protocol_ids:
            raise ValueError("Wave 6 readiness gates require protocol ids.")
        object.__setattr__(
            self, "reviewer_ids", _unique_text(self.reviewer_ids, label="reviewer_id")
        )
        object.__setattr__(
            self,
            "claim_boundaries",
            _unique_enum(self.claim_boundaries, label="claim boundary"),
        )
        missing_boundaries = tuple(
            boundary
            for boundary in WAVE_FIVE_REQUIRED_CLAIM_BOUNDARIES
            if boundary not in self.claim_boundaries
        )
        if missing_boundaries:
            raise ValueError(
                "Wave 6 readiness gates must preserve claim boundary: "
                f"{missing_boundaries[0].value}"
            )
        object.__setattr__(self, "notes", _unique_text(self.notes, label="note"))
        object.__setattr__(
            self, "schema_version", _text(self.schema_version, "schema_version")
        )
        if self.externally_reviewed_with_boundaries:
            if self.source_system not in EXTERNAL_WAVE_SIX_REVIEW_SOURCE_SYSTEMS:
                raise ValueError(
                    "Externally reviewed Wave 6 gates require external source."
                )
            if not self.reviewer_ids:
                raise ValueError(
                    "Externally reviewed Wave 6 gates require reviewer ids."
                )
            if self.blocks_wave_six_readiness:
                raise ValueError(
                    "Externally reviewed Wave 6 gates cannot contain blockers."
                )

    @property
    def covered_precondition_kinds(
        self,
    ) -> tuple[WaveFiveWaveSixPreconditionKind, ...]:
        """Return Wave 6 precondition kinds represented in the gate."""

        return tuple(item.precondition_kind for item in self.preconditions)

    @property
    def missing_required_precondition_kinds(
        self,
    ) -> tuple[WaveFiveWaveSixPreconditionKind, ...]:
        """Return required Wave 6 preconditions absent from the gate."""

        covered = set(self.covered_precondition_kinds)
        return tuple(
            kind for kind in REQUIRED_WAVE_SIX_PRECONDITIONS if kind not in covered
        )

    @property
    def blocking_precondition_ids(self) -> tuple[str, ...]:
        """Return preconditions that block Wave 6 readiness submission."""

        return tuple(
            precondition.precondition_id
            for precondition in self.preconditions
            if precondition.blocks_wave_six_readiness
        )

    @property
    def unresolved_blocker_ids(self) -> tuple[str, ...]:
        """Return unresolved blocking readiness blockers."""

        return tuple(
            blocker.blocker_id
            for blocker in self.blockers
            if blocker.blocks_wave_six_readiness
        )

    @property
    def has_required_precondition_coverage(self) -> bool:
        """Return whether every locked Wave 6 precondition is represented."""

        return not self.missing_required_precondition_kinds

    @property
    def makes_no_forbidden_claims(self) -> bool:
        """Return whether gate avoids forbidden maturity claims."""

        return not any(
            (
                self.attempted_wave_six_promotion,
                self.claims_agi,
                self.grants_execution_authority,
                self.claims_production_ready,
                self.claims_certified,
                self.claims_independent_validation,
            )
        )

    @property
    def blocks_wave_six_readiness(self) -> bool:
        """Return whether any condition blocks Wave 6 readiness submission."""

        return bool(
            self.missing_required_precondition_kinds
            or self.blocking_precondition_ids
            or self.unresolved_blocker_ids
            or not self.makes_no_forbidden_claims
        )

    @property
    def ready_for_external_wave_six_review(self) -> bool:
        """Return whether the package can enter external Wave 6 review."""

        return (
            self.readiness_state
            in {
                WaveFiveWaveSixReadinessState.INTERNAL_GATE_READY,
                WaveFiveWaveSixReadinessState.READY_FOR_EXTERNAL_WAVE_SIX_REVIEW,
                WaveFiveWaveSixReadinessState.UNDER_EXTERNAL_WAVE_SIX_REVIEW,
            }
            and self.has_required_precondition_coverage
            and not self.blocking_precondition_ids
            and not self.unresolved_blocker_ids
            and self.makes_no_forbidden_claims
        )

    @property
    def externally_reviewed_with_boundaries(self) -> bool:
        """Return whether external review accepted the readiness gate boundaries."""

        return (
            self.readiness_state
            is WaveFiveWaveSixReadinessState.EXTERNALLY_REVIEWED_WITH_BOUNDARIES
        )

    @property
    def all_evidence_ids(self) -> tuple[str, ...]:
        """Return all evidence ids bound into the readiness gate."""

        evidence_ids: list[str] = []
        seen: set[str] = set()
        for evidence_id in self._iter_evidence_ids():
            if evidence_id not in seen:
                evidence_ids.append(evidence_id)
                seen.add(evidence_id)
        return tuple(evidence_ids)

    def to_artifact_ref(self) -> WaveFiveArtifactRef:
        """Return this readiness gate as a Wave 5 precondition artifact."""

        decision = WaveFiveArtifactDecision.NEEDS_EXTERNAL_EVIDENCE
        status = WaveFiveValidationStatus.MISSING_EXTERNAL_EVIDENCE
        authority = WaveFiveAuthorityState.HUMAN_REVIEW_REQUIRED
        if self.externally_reviewed_with_boundaries:
            decision = WaveFiveArtifactDecision.EXTERNALLY_REVIEWED
            status = WaveFiveValidationStatus.ACCEPTED_WITH_BOUNDARIES
        elif self.ready_for_external_wave_six_review:
            decision = WaveFiveArtifactDecision.READY_FOR_INDEPENDENT_REVIEW
            status = WaveFiveValidationStatus.UNDER_INDEPENDENT_REVIEW
        elif self.blocks_wave_six_readiness:
            decision = WaveFiveArtifactDecision.BLOCKED
            status = WaveFiveValidationStatus.REJECTED
            authority = WaveFiveAuthorityState.BLOCKED
        return WaveFiveArtifactRef(
            artifact_id=self.gate_id,
            kind=WaveFiveArtifactKind.WAVE_SIX_PRECONDITION_LEDGER,
            capability_area=WaveFiveCapabilityArea.WAVE_SIX_READINESS_BOUNDARY,
            source_system=self.source_system,
            summary=self.title,
            produced_by_engine_id="wave5-wave6-readiness-gate-engine",
            produced_by_agent_role_id="wave-six-readiness-reviewer",
            evidence_ids=self.all_evidence_ids,
            decision=decision,
            authority_state=authority,
            validation_status=status,
            claim_boundaries=self.claim_boundaries,
        )

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic export payload."""

        return {
            "attempted_wave_six_promotion": self.attempted_wave_six_promotion,
            "blockers": [blocker.canonical_payload() for blocker in self.blockers],
            "claim_boundaries": [boundary.value for boundary in self.claim_boundaries],
            "claims_agi": self.claims_agi,
            "claims_certified": self.claims_certified,
            "claims_independent_validation": self.claims_independent_validation,
            "claims_production_ready": self.claims_production_ready,
            "gate_id": self.gate_id,
            "grants_execution_authority": self.grants_execution_authority,
            "notes": list(self.notes),
            "preconditions": [
                precondition.canonical_payload()
                for precondition in self.preconditions
            ],
            "protocol_ids": list(self.protocol_ids),
            "readiness_state": self.readiness_state.value,
            "reviewer_ids": list(self.reviewer_ids),
            "schema_version": self.schema_version,
            "source_system": self.source_system.value,
            "title": self.title,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this readiness gate."""

        return _stable_sha256(self.canonical_payload())

    def _iter_evidence_ids(self) -> Iterable[str]:
        """Yield evidence ids in deterministic readiness-gate order."""

        for precondition in self.preconditions:
            yield from precondition.evidence_ids
        for blocker in self.blockers:
            yield from blocker.evidence_ids


def required_wave_six_preconditions() -> tuple[
    WaveFiveWaveSixPreconditionKind, ...
]:
    """Return locked preconditions required before Wave 6 review."""

    return REQUIRED_WAVE_SIX_PRECONDITIONS


def safe_wave_six_precondition_statuses() -> tuple[
    WaveFiveWaveSixPreconditionStatus, ...
]:
    """Return Wave 6 precondition statuses that do not block review."""

    return SAFE_WAVE_SIX_PRECONDITION_STATUSES


def blocking_wave_six_precondition_statuses() -> tuple[
    WaveFiveWaveSixPreconditionStatus, ...
]:
    """Return Wave 6 precondition statuses that block review."""

    return BLOCKING_WAVE_SIX_PRECONDITION_STATUSES


def external_wave_six_review_source_systems() -> tuple[WaveFiveSourceSystem, ...]:
    """Return source systems allowed to assert external Wave 6 review."""

    return EXTERNAL_WAVE_SIX_REVIEW_SOURCE_SYSTEMS


def _text(value: str, label: str) -> str:
    """Return stripped text or raise when empty."""

    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{label} must not be empty.")
    return normalized


def _unique_text(values: Iterable[str], *, label: str) -> tuple[str, ...]:
    """Normalize text values while rejecting blanks and duplicates."""

    normalized: list[str] = []
    seen: set[str] = set()
    for value in values:
        item = _text(value, label)
        if item in seen:
            raise ValueError(f"Duplicate {label} detected: {item}")
        normalized.append(item)
        seen.add(item)
    return tuple(normalized)


def _unique_enum(values: Iterable[E], *, label: str) -> tuple[E, ...]:
    """Return enum values while rejecting duplicates."""

    normalized: list[E] = []
    seen: set[E] = set()
    for value in values:
        if value in seen:
            raise ValueError(f"Duplicate {label} detected: {value.value}")
        normalized.append(value)
        seen.add(value)
    return tuple(normalized)


def _unique_values(values: Iterable[T], *, label: str) -> set[T]:
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
