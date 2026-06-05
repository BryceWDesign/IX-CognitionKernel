"""Wave 5 independent reviewer and conflict-of-interest records.

Wave 5 needs reviewer evidence that cannot be collapsed into self-attestation.
This module models reviewer attestations, conflict disclosures, review scopes,
and panel-level gates. It deliberately rejects self-review, hidden conflicts,
missing dissent, and any attempt to treat internal authorship as independent
validation. The records are evidence artifacts only; they do not claim AGI,
production readiness, certification, or autonomous authority.
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

WAVE_FIVE_CONFLICT_DISCLOSURE_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave5-conflict-disclosure-v1"
)
WAVE_FIVE_REVIEWER_ATTESTATION_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave5-reviewer-attestation-v1"
)
WAVE_FIVE_REVIEW_PANEL_SCHEMA_VERSION = "ix-cognition-kernel-wave5-review-panel-v1"


class WaveFiveReviewerRole(StrEnum):
    """Reviewer roles allowed in a Wave 5 independent-validation panel."""

    INDEPENDENT_REPRODUCER = "independent-reproducer"
    ADVERSARIAL_EVALUATOR = "adversarial-evaluator"
    SAFETY_REVIEWER = "safety-reviewer"
    DOMAIN_REVIEWER = "domain-reviewer"
    GOVERNANCE_REVIEWER = "governance-reviewer"
    HUMAN_AUTHORITY_REVIEWER = "human-authority-reviewer"


class WaveFiveReviewScope(StrEnum):
    """Scope areas a reviewer may attest to."""

    EXTERNAL_PROTOCOLS = "external-protocols"
    REPRODUCIBLE_EVIDENCE = "reproducible-evidence"
    ADVERSARIAL_SAFETY = "adversarial-safety"
    LONG_HORIZON_TASKS = "long-horizon-tasks"
    CROSS_DOMAIN_TRANSFER = "cross-domain-transfer"
    MEMORY_INTEGRITY = "memory-integrity"
    SAFE_REFUSAL = "safe-refusal"
    HUMAN_AUTHORITY = "human-authority"
    ECOSYSTEM_TRACEABILITY = "ecosystem-traceability"
    WAVE_SIX_PRECONDITIONS = "wave-six-preconditions"


class WaveFiveConflictKind(StrEnum):
    """Kinds of conflicts reviewers must disclose."""

    AUTHORSHIP = "authorship"
    EMPLOYMENT = "employment"
    FUNDING = "funding"
    CONTRACTING = "contracting"
    CLOSE_PERSONAL_RELATIONSHIP = "close-personal-relationship"
    COMPETITIVE_INTEREST = "competitive-interest"
    DATA_ACCESS_ADVANTAGE = "data-access-advantage"
    MODEL_PROVIDER_DEPENDENCY = "model-provider-dependency"
    NONE_DECLARED = "none-declared"


class WaveFiveConflictSeverity(StrEnum):
    """Conflict severity used by the fail-closed reviewer gate."""

    NONE = "none"
    LOW = "low"
    MANAGEABLE = "manageable"
    BLOCKING = "blocking"


class WaveFiveIndependenceStatus(StrEnum):
    """Independence status asserted by reviewer evidence."""

    INDEPENDENT = "independent"
    INDEPENDENT_WITH_DISCLOSED_LIMITS = "independent-with-disclosed-limits"
    NOT_INDEPENDENT = "not-independent"
    UNKNOWN = "unknown"


class WaveFiveReviewerDecision(StrEnum):
    """Reviewer decision options that preserve dissent."""

    ACCEPT_WITH_BOUNDARIES = "accept-with-boundaries"
    ACCEPT_PARTIAL = "accept-partial"
    REQUEST_MORE_EVIDENCE = "request-more-evidence"
    DISPUTE = "dispute"
    REJECT = "reject"


REQUIRED_WAVE_FIVE_REVIEW_SCOPES: tuple[WaveFiveReviewScope, ...] = (
    WaveFiveReviewScope.EXTERNAL_PROTOCOLS,
    WaveFiveReviewScope.REPRODUCIBLE_EVIDENCE,
    WaveFiveReviewScope.ADVERSARIAL_SAFETY,
    WaveFiveReviewScope.LONG_HORIZON_TASKS,
    WaveFiveReviewScope.CROSS_DOMAIN_TRANSFER,
    WaveFiveReviewScope.MEMORY_INTEGRITY,
    WaveFiveReviewScope.SAFE_REFUSAL,
    WaveFiveReviewScope.HUMAN_AUTHORITY,
    WaveFiveReviewScope.ECOSYSTEM_TRACEABILITY,
    WaveFiveReviewScope.WAVE_SIX_PRECONDITIONS,
)

BLOCKING_WAVE_FIVE_REVIEWER_DECISIONS: tuple[WaveFiveReviewerDecision, ...] = (
    WaveFiveReviewerDecision.REQUEST_MORE_EVIDENCE,
    WaveFiveReviewerDecision.DISPUTE,
    WaveFiveReviewerDecision.REJECT,
)


@dataclass(frozen=True, slots=True)
class WaveFiveConflictDisclosure:
    """One conflict disclosure attached to an independent reviewer."""

    disclosure_id: str
    conflict_kind: WaveFiveConflictKind
    severity: WaveFiveConflictSeverity
    description: str
    mitigation: str
    evidence_ids: tuple[str, ...]
    schema_version: str = WAVE_FIVE_CONFLICT_DISCLOSURE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate conflict disclosure identity and mitigation."""

        object.__setattr__(
            self, "disclosure_id", _text(self.disclosure_id, "disclosure_id")
        )
        object.__setattr__(self, "description", _text(self.description, "description"))
        object.__setattr__(self, "mitigation", _text(self.mitigation, "mitigation"))
        object.__setattr__(
            self,
            "evidence_ids",
            _unique_text(self.evidence_ids, label="conflict evidence_id"),
        )
        if self.conflict_kind is WaveFiveConflictKind.NONE_DECLARED:
            if self.severity is not WaveFiveConflictSeverity.NONE:
                raise ValueError("No-conflict disclosures must use severity none.")
            if self.evidence_ids:
                raise ValueError("No-conflict disclosures must not bind evidence ids.")
        elif self.severity is WaveFiveConflictSeverity.NONE:
            raise ValueError("Declared conflicts cannot use severity none.")
        object.__setattr__(
            self, "schema_version", _text(self.schema_version, "schema_version")
        )

    @property
    def disclosure_key(self) -> str:
        """Return deterministic disclosure key."""

        return self.disclosure_id

    @property
    def is_blocking(self) -> bool:
        """Return whether this conflict blocks independent reviewer standing."""

        return (
            self.conflict_kind is WaveFiveConflictKind.AUTHORSHIP
            or self.severity is WaveFiveConflictSeverity.BLOCKING
        )

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic export payload."""

        return {
            "conflict_kind": self.conflict_kind.value,
            "description": self.description,
            "disclosure_id": self.disclosure_id,
            "evidence_ids": list(self.evidence_ids),
            "mitigation": self.mitigation,
            "schema_version": self.schema_version,
            "severity": self.severity.value,
        }


@dataclass(frozen=True, slots=True)
class WaveFiveReviewerAttestation:
    """Independent reviewer attestation for Wave 5 validation evidence."""

    attestation_id: str
    reviewer_id: str
    reviewer_label: str
    reviewer_role: WaveFiveReviewerRole
    independence_status: WaveFiveIndependenceStatus
    decision: WaveFiveReviewerDecision
    review_scopes: tuple[WaveFiveReviewScope, ...]
    reviewed_artifact_ids: tuple[str, ...]
    protocol_ids: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    conflict_disclosures: tuple[WaveFiveConflictDisclosure, ...]
    rationale: str
    limitations: tuple[str, ...]
    dissent_notes: tuple[str, ...] = ()
    claim_boundaries: tuple[WaveFiveClaimBoundary, ...] = (
        WAVE_FIVE_REQUIRED_CLAIM_BOUNDARIES
    )
    source_system: WaveFiveSourceSystem = WaveFiveSourceSystem.INDEPENDENT_REVIEWER
    schema_version: str = WAVE_FIVE_REVIEWER_ATTESTATION_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate reviewer independence, conflicts, and evidence binding."""

        object.__setattr__(
            self, "attestation_id", _text(self.attestation_id, "attestation_id")
        )
        object.__setattr__(self, "reviewer_id", _text(self.reviewer_id, "reviewer_id"))
        object.__setattr__(
            self, "reviewer_label", _text(self.reviewer_label, "reviewer_label")
        )
        object.__setattr__(self, "rationale", _text(self.rationale, "rationale"))
        object.__setattr__(
            self,
            "review_scopes",
            _unique_enum(self.review_scopes, label="review scope"),
        )
        object.__setattr__(
            self,
            "reviewed_artifact_ids",
            _unique_text(self.reviewed_artifact_ids, label="reviewed artifact_id"),
        )
        object.__setattr__(
            self, "protocol_ids", _unique_text(self.protocol_ids, label="protocol_id")
        )
        object.__setattr__(
            self, "evidence_ids", _unique_text(self.evidence_ids, label="evidence_id")
        )
        object.__setattr__(
            self, "limitations", _unique_text(self.limitations, label="limitation")
        )
        object.__setattr__(
            self, "dissent_notes", _unique_text(self.dissent_notes, label="dissent")
        )
        object.__setattr__(
            self,
            "claim_boundaries",
            _unique_enum(self.claim_boundaries, label="claim boundary"),
        )
        disclosures = tuple(
            sorted(self.conflict_disclosures, key=lambda item: item.disclosure_key)
        )
        if not disclosures:
            raise ValueError("Reviewer attestations require conflict disclosures.")
        _unique_values(
            (item.disclosure_id for item in disclosures), label="disclosure_id"
        )
        object.__setattr__(self, "conflict_disclosures", disclosures)
        if not self.review_scopes:
            raise ValueError("Reviewer attestations require review scopes.")
        if not self.reviewed_artifact_ids:
            raise ValueError("Reviewer attestations require reviewed artifact ids.")
        if not self.protocol_ids:
            raise ValueError("Reviewer attestations require protocol ids.")
        if not self.evidence_ids:
            raise ValueError("Reviewer attestations require evidence ids.")
        if self.source_system is not WaveFiveSourceSystem.INDEPENDENT_REVIEWER:
            raise ValueError(
                "Reviewer attestations must come from independent reviewers."
            )
        missing_boundaries = tuple(
            boundary
            for boundary in WAVE_FIVE_REQUIRED_CLAIM_BOUNDARIES
            if boundary not in self.claim_boundaries
        )
        if missing_boundaries:
            raise ValueError(
                "Reviewer attestations must preserve claim boundary: "
                f"{missing_boundaries[0].value}"
            )
        if self.has_blocking_conflict:
            raise ValueError("Reviewer attestations cannot include blocking conflicts.")
        if (
            self.independence_status
            is WaveFiveIndependenceStatus.INDEPENDENT_WITH_DISCLOSED_LIMITS
            and not self.limitations
        ):
            raise ValueError("Limited independence requires stated limitations.")
        if self.independence_status in {
            WaveFiveIndependenceStatus.NOT_INDEPENDENT,
            WaveFiveIndependenceStatus.UNKNOWN,
        }:
            raise ValueError("Reviewer attestation is not independently usable.")
        if self.is_dissenting and not self.dissent_notes:
            raise ValueError("Dissenting reviewer decisions require dissent notes.")
        object.__setattr__(
            self, "schema_version", _text(self.schema_version, "schema_version")
        )

    @property
    def has_blocking_conflict(self) -> bool:
        """Return whether any disclosed conflict blocks independence."""

        return any(disclosure.is_blocking for disclosure in self.conflict_disclosures)

    @property
    def is_dissenting(self) -> bool:
        """Return whether this attestation records dissent or rejection."""

        return self.decision in {
            WaveFiveReviewerDecision.DISPUTE,
            WaveFiveReviewerDecision.REJECT,
        }

    @property
    def blocks_wave_five_progress(self) -> bool:
        """Return whether this attestation blocks Wave 5 progress."""

        return self.decision in BLOCKING_WAVE_FIVE_REVIEWER_DECISIONS

    @property
    def usable_for_independent_review(self) -> bool:
        """Return whether this attestation can count as independent evidence."""

        return (
            self.independence_status
            in {
                WaveFiveIndependenceStatus.INDEPENDENT,
                WaveFiveIndependenceStatus.INDEPENDENT_WITH_DISCLOSED_LIMITS,
            }
            and not self.has_blocking_conflict
            and bool(self.review_scopes)
            and bool(self.reviewed_artifact_ids)
            and bool(self.protocol_ids)
            and bool(self.evidence_ids)
        )

    @property
    def all_conflict_evidence_ids(self) -> tuple[str, ...]:
        """Return evidence ids from conflict disclosures."""

        evidence_ids: list[str] = []
        seen: set[str] = set()
        for disclosure in self.conflict_disclosures:
            for evidence_id in disclosure.evidence_ids:
                if evidence_id not in seen:
                    evidence_ids.append(evidence_id)
                    seen.add(evidence_id)
        return tuple(evidence_ids)

    @property
    def all_evidence_ids(self) -> tuple[str, ...]:
        """Return attestation and conflict evidence ids."""

        evidence_ids: list[str] = []
        seen: set[str] = set()
        for evidence_id in (*self.evidence_ids, *self.all_conflict_evidence_ids):
            if evidence_id not in seen:
                evidence_ids.append(evidence_id)
                seen.add(evidence_id)
        return tuple(evidence_ids)

    def to_artifact_ref(self) -> WaveFiveArtifactRef:
        """Return this reviewer attestation as a Wave 5 artifact reference."""

        decision = WaveFiveArtifactDecision.EXTERNALLY_REVIEWED
        validation_status = WaveFiveValidationStatus.ACCEPTED_WITH_BOUNDARIES
        authority_state = WaveFiveAuthorityState.HUMAN_REVIEW_REQUIRED
        if self.blocks_wave_five_progress:
            decision = WaveFiveArtifactDecision.BLOCKED
            validation_status = (
                WaveFiveValidationStatus.DISPUTED
                if self.decision is WaveFiveReviewerDecision.DISPUTE
                else WaveFiveValidationStatus.REJECTED
            )
            authority_state = WaveFiveAuthorityState.BLOCKED
        return WaveFiveArtifactRef(
            artifact_id=self.attestation_id,
            kind=WaveFiveArtifactKind.REVIEWER_ATTESTATION,
            capability_area=WaveFiveCapabilityArea.INDEPENDENT_REVIEW,
            source_system=self.source_system,
            summary=self.rationale,
            produced_by_engine_id="wave5-independent-reviewer-engine",
            produced_by_agent_role_id=self.reviewer_role.value,
            evidence_ids=self.all_evidence_ids,
            decision=decision,
            authority_state=authority_state,
            validation_status=validation_status,
            claim_boundaries=self.claim_boundaries,
        )

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic export payload."""

        return {
            "attestation_id": self.attestation_id,
            "claim_boundaries": [boundary.value for boundary in self.claim_boundaries],
            "conflict_disclosures": [
                disclosure.canonical_payload()
                for disclosure in self.conflict_disclosures
            ],
            "decision": self.decision.value,
            "dissent_notes": list(self.dissent_notes),
            "evidence_ids": list(self.evidence_ids),
            "independence_status": self.independence_status.value,
            "limitations": list(self.limitations),
            "protocol_ids": list(self.protocol_ids),
            "rationale": self.rationale,
            "review_scopes": [scope.value for scope in self.review_scopes],
            "reviewed_artifact_ids": list(self.reviewed_artifact_ids),
            "reviewer_id": self.reviewer_id,
            "reviewer_label": self.reviewer_label,
            "reviewer_role": self.reviewer_role.value,
            "schema_version": self.schema_version,
            "source_system": self.source_system.value,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this attestation."""

        return _stable_sha256(self.canonical_payload())


@dataclass(frozen=True, slots=True)
class WaveFiveReviewPanel:
    """Panel gate for independent reviewer attestations."""

    panel_id: str
    attestations: tuple[WaveFiveReviewerAttestation, ...]
    required_review_scopes: tuple[WaveFiveReviewScope, ...] = (
        REQUIRED_WAVE_FIVE_REVIEW_SCOPES
    )
    minimum_usable_reviewers: int = 2
    notes: tuple[str, ...] = ()
    schema_version: str = WAVE_FIVE_REVIEW_PANEL_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate panel uniqueness and minimum independent-review coverage."""

        object.__setattr__(self, "panel_id", _text(self.panel_id, "panel_id"))
        if self.minimum_usable_reviewers < 1:
            raise ValueError("Review panels require at least one usable reviewer.")
        if not self.attestations:
            raise ValueError("Review panels require reviewer attestations.")
        attestations = tuple(
            sorted(self.attestations, key=lambda item: item.attestation_id)
        )
        _unique_values(
            (item.attestation_id for item in attestations), label="attestation_id"
        )
        _unique_values((item.reviewer_id for item in attestations), label="reviewer_id")
        object.__setattr__(self, "attestations", attestations)
        object.__setattr__(
            self,
            "required_review_scopes",
            _unique_enum(self.required_review_scopes, label="required review scope"),
        )
        object.__setattr__(
            self, "notes", _unique_text(self.notes, label="review panel note")
        )
        object.__setattr__(
            self, "schema_version", _text(self.schema_version, "schema_version")
        )

    @property
    def usable_attestations(self) -> tuple[WaveFiveReviewerAttestation, ...]:
        """Return non-blocking attestations usable as independent evidence."""

        return tuple(
            attestation
            for attestation in self.attestations
            if attestation.usable_for_independent_review
            and not attestation.blocks_wave_five_progress
        )

    @property
    def blocking_attestation_ids(self) -> tuple[str, ...]:
        """Return attestations that block Wave 5 progress."""

        return tuple(
            attestation.attestation_id
            for attestation in self.attestations
            if attestation.blocks_wave_five_progress
        )

    @property
    def dissenting_attestation_ids(self) -> tuple[str, ...]:
        """Return attestations that record dissent."""

        return tuple(
            attestation.attestation_id
            for attestation in self.attestations
            if attestation.is_dissenting
        )

    @property
    def covered_review_scopes(self) -> tuple[WaveFiveReviewScope, ...]:
        """Return review scopes covered by usable attestations."""

        scopes: list[WaveFiveReviewScope] = []
        seen: set[WaveFiveReviewScope] = set()
        for attestation in self.usable_attestations:
            for scope in attestation.review_scopes:
                if scope not in seen:
                    scopes.append(scope)
                    seen.add(scope)
        return tuple(scopes)

    @property
    def missing_required_review_scopes(self) -> tuple[WaveFiveReviewScope, ...]:
        """Return required review scopes not covered by usable attestations."""

        covered = set(self.covered_review_scopes)
        return tuple(
            scope for scope in self.required_review_scopes if scope not in covered
        )

    @property
    def ready_for_independent_review_record(self) -> bool:
        """Return whether the panel can support the Wave 5 review record."""

        return (
            len(self.usable_attestations) >= self.minimum_usable_reviewers
            and not self.blocking_attestation_ids
            and not self.missing_required_review_scopes
        )

    @property
    def all_evidence_ids(self) -> tuple[str, ...]:
        """Return all reviewer evidence ids in deterministic order."""

        evidence_ids: list[str] = []
        seen: set[str] = set()
        for attestation in self.attestations:
            for evidence_id in attestation.all_evidence_ids:
                if evidence_id not in seen:
                    evidence_ids.append(evidence_id)
                    seen.add(evidence_id)
        return tuple(evidence_ids)

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic export payload."""

        return {
            "attestations": [
                attestation.canonical_payload() for attestation in self.attestations
            ],
            "minimum_usable_reviewers": self.minimum_usable_reviewers,
            "notes": list(self.notes),
            "panel_id": self.panel_id,
            "required_review_scopes": [
                scope.value for scope in self.required_review_scopes
            ],
            "schema_version": self.schema_version,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this review panel."""

        return _stable_sha256(self.canonical_payload())


def required_wave_five_review_scopes() -> tuple[WaveFiveReviewScope, ...]:
    """Return locked review scopes needed for Wave 5 independent review."""

    return REQUIRED_WAVE_FIVE_REVIEW_SCOPES


def blocking_wave_five_reviewer_decisions() -> tuple[WaveFiveReviewerDecision, ...]:
    """Return reviewer decisions that block Wave 5 progress."""

    return BLOCKING_WAVE_FIVE_REVIEWER_DECISIONS


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
