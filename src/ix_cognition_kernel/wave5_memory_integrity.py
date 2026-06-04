"""Wave 5 memory-integrity proof records.

Wave 6 cannot safely build on memory that is unproven, stale, contradicted,
poisoned, or accepted from quarantine by convenience. This module records
memory provenance, validation checks, quarantine findings, contradiction and
staleness handling, replay visibility, and external-review boundaries. A proof
is reviewable only when memory is evidence-bound, quarantined memory is rejected,
stale or contradicted memory is exposed, and human authority remains preserved.
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

WAVE_FIVE_MEMORY_CLAIM_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave5-memory-claim-v1"
)
WAVE_FIVE_MEMORY_CHECK_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave5-memory-check-v1"
)
WAVE_FIVE_MEMORY_QUARANTINE_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave5-memory-quarantine-v1"
)
WAVE_FIVE_MEMORY_PROOF_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave5-memory-integrity-proof-v1"
)


class WaveFiveMemoryProvenance(StrEnum):
    """Where a memory claim originated before validation."""

    HUMAN_PROVIDED = "human-provided"
    TEST_OBSERVED = "test-observed"
    OUTCOME_LEARNED = "outcome-learned"
    EXTERNAL_REVIEWED = "external-reviewed"
    MODEL_INFERRED = "model-inferred"
    IMPORTED_FROM_DONOR_REPO = "imported-from-donor-repo"
    UNKNOWN = "unknown"


class WaveFiveMemoryIntegrityState(StrEnum):
    """Current integrity state of a memory claim."""

    VALIDATED = "validated"
    VALIDATED_WITH_LIMITS = "validated-with-limits"
    QUARANTINED = "quarantined"
    CONTRADICTED = "contradicted"
    STALE = "stale"
    UNSAFE_TO_ACT = "unsafe-to-act"
    REJECTED = "rejected"


class WaveFiveMemoryCheckKind(StrEnum):
    """Required memory-integrity checks before Wave 5 review."""

    PROVENANCE_BOUND = "provenance-bound"
    EVIDENCE_BOUND = "evidence-bound"
    QUARANTINE_ENFORCED = "quarantine-enforced"
    CONTRADICTION_EXPOSED = "contradiction-exposed"
    STALENESS_EXPOSED = "staleness-exposed"
    UNSAFE_TO_ACT_BLOCKED = "unsafe-to-act-blocked"
    REPLAY_TRACE_VISIBLE = "replay-trace-visible"
    HUMAN_AUTHORITY_PRESERVED = "human-authority-preserved"


class WaveFiveMemoryCheckResult(StrEnum):
    """Observed result of one memory-integrity check."""

    PASSED = "passed"
    PASSED_WITH_LIMITS = "passed-with-limits"
    NEEDS_MORE_EVIDENCE = "needs-more-evidence"
    FAILED = "failed"


class WaveFiveMemoryQuarantineReason(StrEnum):
    """Reasons a memory claim must not be promoted into trusted state."""

    UNKNOWN_PROVENANCE = "unknown-provenance"
    CONTRADICTED_BY_EVIDENCE = "contradicted-by-evidence"
    STALE_CONTEXT = "stale-context"
    UNSAFE_ACTION_RISK = "unsafe-action-risk"
    DONOR_REPO_MISMATCH = "donor-repo-mismatch"
    MODEL_ONLY_ASSERTION = "model-only-assertion"
    HUMAN_REVIEW_REQUIRED = "human-review-required"


class WaveFiveMemoryProofReviewState(StrEnum):
    """Review state of a Wave 5 memory-integrity proof."""

    INTERNAL_REPLAY_READY = "internal-replay-ready"
    READY_FOR_EXTERNAL_MEMORY_REVIEW = "ready-for-external-memory-review"
    UNDER_EXTERNAL_MEMORY_REVIEW = "under-external-memory-review"
    EXTERNALLY_REVIEWED_WITH_BOUNDARIES = "externally-reviewed-with-boundaries"
    BLOCKED_BY_MEMORY_FAILURE = "blocked-by-memory-failure"


REQUIRED_WAVE_FIVE_MEMORY_CHECKS: tuple[WaveFiveMemoryCheckKind, ...] = (
    WaveFiveMemoryCheckKind.PROVENANCE_BOUND,
    WaveFiveMemoryCheckKind.EVIDENCE_BOUND,
    WaveFiveMemoryCheckKind.QUARANTINE_ENFORCED,
    WaveFiveMemoryCheckKind.CONTRADICTION_EXPOSED,
    WaveFiveMemoryCheckKind.STALENESS_EXPOSED,
    WaveFiveMemoryCheckKind.UNSAFE_TO_ACT_BLOCKED,
    WaveFiveMemoryCheckKind.REPLAY_TRACE_VISIBLE,
    WaveFiveMemoryCheckKind.HUMAN_AUTHORITY_PRESERVED,
)

SAFE_MEMORY_INTEGRITY_STATES: tuple[WaveFiveMemoryIntegrityState, ...] = (
    WaveFiveMemoryIntegrityState.VALIDATED,
    WaveFiveMemoryIntegrityState.VALIDATED_WITH_LIMITS,
)

BLOCKING_MEMORY_INTEGRITY_STATES: tuple[WaveFiveMemoryIntegrityState, ...] = (
    WaveFiveMemoryIntegrityState.QUARANTINED,
    WaveFiveMemoryIntegrityState.CONTRADICTED,
    WaveFiveMemoryIntegrityState.UNSAFE_TO_ACT,
    WaveFiveMemoryIntegrityState.REJECTED,
)

EXTERNAL_MEMORY_REVIEW_SOURCE_SYSTEMS: tuple[WaveFiveSourceSystem, ...] = (
    WaveFiveSourceSystem.EXTERNAL_REVIEW,
    WaveFiveSourceSystem.INDEPENDENT_REVIEWER,
    WaveFiveSourceSystem.INDEPENDENT_REPLICATION_LAB,
)


@dataclass(frozen=True, slots=True)
class WaveFiveMemoryClaim:
    """One memory claim with provenance, evidence, and integrity state."""

    memory_id: str
    summary: str
    provenance: WaveFiveMemoryProvenance
    integrity_state: WaveFiveMemoryIntegrityState
    source_system: WaveFiveSourceSystem
    evidence_ids: tuple[str, ...]
    contradiction_ids: tuple[str, ...] = ()
    staleness_evidence_ids: tuple[str, ...] = ()
    allowed_for_planning: bool = False
    allowed_for_action: bool = False
    requires_human_review: bool = True
    schema_version: str = WAVE_FIVE_MEMORY_CLAIM_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate memory provenance, evidence binding, and action limits."""

        object.__setattr__(self, "memory_id", _text(self.memory_id, "memory_id"))
        object.__setattr__(self, "summary", _text(self.summary, "summary"))
        object.__setattr__(
            self, "evidence_ids", _unique_text(self.evidence_ids, label="evidence_id")
        )
        object.__setattr__(
            self,
            "contradiction_ids",
            _unique_text(self.contradiction_ids, label="contradiction_id"),
        )
        object.__setattr__(
            self,
            "staleness_evidence_ids",
            _unique_text(
                self.staleness_evidence_ids, label="staleness evidence_id"
            ),
        )
        if self.provenance is WaveFiveMemoryProvenance.UNKNOWN:
            if self.integrity_state not in {
                WaveFiveMemoryIntegrityState.QUARANTINED,
                WaveFiveMemoryIntegrityState.REJECTED,
            }:
                raise ValueError("Unknown-provenance memory must be quarantined.")
        if self.integrity_state in SAFE_MEMORY_INTEGRITY_STATES:
            if not self.evidence_ids:
                raise ValueError("Validated memory claims require evidence ids.")
        if self.integrity_state is WaveFiveMemoryIntegrityState.CONTRADICTED:
            if not self.contradiction_ids:
                raise ValueError("Contradicted memory requires contradiction ids.")
        if self.integrity_state is WaveFiveMemoryIntegrityState.STALE:
            if not self.staleness_evidence_ids:
                raise ValueError("Stale memory requires staleness evidence ids.")
        if self.integrity_state not in SAFE_MEMORY_INTEGRITY_STATES:
            if self.allowed_for_planning or self.allowed_for_action:
                raise ValueError("Unsafe memory cannot be allowed for planning/action.")
        if self.allowed_for_action:
            raise ValueError("Wave 5 memory claims cannot authorize action.")
        if not self.requires_human_review:
            raise ValueError("Wave 5 memory claims require human-review awareness.")
        object.__setattr__(
            self, "schema_version", _text(self.schema_version, "schema_version")
        )

    @property
    def claim_key(self) -> str:
        """Return deterministic memory-claim key."""

        return self.memory_id

    @property
    def is_safe_for_bounded_planning(self) -> bool:
        """Return whether memory may support bounded planning evidence."""

        return (
            self.integrity_state in SAFE_MEMORY_INTEGRITY_STATES
            and self.allowed_for_planning
            and not self.allowed_for_action
            and bool(self.evidence_ids)
        )

    @property
    def blocks_wave_five_progress(self) -> bool:
        """Return whether this memory claim blocks memory-integrity readiness."""

        return self.integrity_state in BLOCKING_MEMORY_INTEGRITY_STATES

    @property
    def needs_visibility_not_trust(self) -> bool:
        """Return whether claim must remain visible but not trusted."""

        return self.integrity_state in {
            WaveFiveMemoryIntegrityState.QUARANTINED,
            WaveFiveMemoryIntegrityState.CONTRADICTED,
            WaveFiveMemoryIntegrityState.STALE,
            WaveFiveMemoryIntegrityState.UNSAFE_TO_ACT,
        }

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic export payload."""

        return {
            "allowed_for_action": self.allowed_for_action,
            "allowed_for_planning": self.allowed_for_planning,
            "contradiction_ids": list(self.contradiction_ids),
            "evidence_ids": list(self.evidence_ids),
            "integrity_state": self.integrity_state.value,
            "memory_id": self.memory_id,
            "provenance": self.provenance.value,
            "requires_human_review": self.requires_human_review,
            "schema_version": self.schema_version,
            "source_system": self.source_system.value,
            "staleness_evidence_ids": list(self.staleness_evidence_ids),
            "summary": self.summary,
        }


@dataclass(frozen=True, slots=True)
class WaveFiveMemoryIntegrityCheck:
    """One check that verifies a memory-integrity requirement."""

    check_id: str
    check_kind: WaveFiveMemoryCheckKind
    result: WaveFiveMemoryCheckResult
    description: str
    evidence_ids: tuple[str, ...]
    blocking: bool = True
    schema_version: str = WAVE_FIVE_MEMORY_CHECK_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate memory-integrity check evidence."""

        object.__setattr__(self, "check_id", _text(self.check_id, "check_id"))
        object.__setattr__(self, "description", _text(self.description, "description"))
        object.__setattr__(
            self, "evidence_ids", _unique_text(self.evidence_ids, label="evidence_id")
        )
        if not self.evidence_ids:
            raise ValueError("Memory-integrity checks require evidence ids.")
        object.__setattr__(
            self, "schema_version", _text(self.schema_version, "schema_version")
        )

    @property
    def check_key(self) -> str:
        """Return deterministic memory-check key."""

        return self.check_id

    @property
    def passed_with_boundaries(self) -> bool:
        """Return whether check passed while preserving limitations."""

        return self.result in {
            WaveFiveMemoryCheckResult.PASSED,
            WaveFiveMemoryCheckResult.PASSED_WITH_LIMITS,
        }

    @property
    def blocks_wave_five_progress(self) -> bool:
        """Return whether this check blocks memory-integrity readiness."""

        return self.blocking and not self.passed_with_boundaries

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic export payload."""

        return {
            "blocking": self.blocking,
            "check_id": self.check_id,
            "check_kind": self.check_kind.value,
            "description": self.description,
            "evidence_ids": list(self.evidence_ids),
            "result": self.result.value,
            "schema_version": self.schema_version,
        }


@dataclass(frozen=True, slots=True)
class WaveFiveMemoryQuarantineFinding:
    """Quarantine record proving unsafe memory was not silently promoted."""

    finding_id: str
    memory_id: str
    reason: WaveFiveMemoryQuarantineReason
    rejected_from_trusted_memory: bool
    reviewer_visible: bool
    mitigation: str
    evidence_ids: tuple[str, ...]
    schema_version: str = WAVE_FIVE_MEMORY_QUARANTINE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate quarantine finding and reviewer visibility."""

        object.__setattr__(self, "finding_id", _text(self.finding_id, "finding_id"))
        object.__setattr__(self, "memory_id", _text(self.memory_id, "memory_id"))
        object.__setattr__(self, "mitigation", _text(self.mitigation, "mitigation"))
        object.__setattr__(
            self, "evidence_ids", _unique_text(self.evidence_ids, label="evidence_id")
        )
        if not self.evidence_ids:
            raise ValueError("Memory quarantine findings require evidence ids.")
        if not self.reviewer_visible:
            raise ValueError("Memory quarantine findings must be reviewer visible.")
        object.__setattr__(
            self, "schema_version", _text(self.schema_version, "schema_version")
        )

    @property
    def finding_key(self) -> str:
        """Return deterministic quarantine-finding key."""

        return self.finding_id

    @property
    def resolved(self) -> bool:
        """Return whether unsafe memory was rejected and exposed."""

        return self.rejected_from_trusted_memory and self.reviewer_visible

    @property
    def blocks_wave_five_progress(self) -> bool:
        """Return whether this finding blocks memory-integrity readiness."""

        return not self.resolved

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic export payload."""

        return {
            "evidence_ids": list(self.evidence_ids),
            "finding_id": self.finding_id,
            "memory_id": self.memory_id,
            "mitigation": self.mitigation,
            "reason": self.reason.value,
            "rejected_from_trusted_memory": self.rejected_from_trusted_memory,
            "resolved": self.resolved,
            "reviewer_visible": self.reviewer_visible,
            "schema_version": self.schema_version,
        }


@dataclass(frozen=True, slots=True)
class WaveFiveMemoryIntegrityProof:
    """Wave 5 proof that memory is evidence-bound and safely quarantined."""

    proof_id: str
    title: str
    source_system: WaveFiveSourceSystem
    review_state: WaveFiveMemoryProofReviewState
    memory_claims: tuple[WaveFiveMemoryClaim, ...]
    integrity_checks: tuple[WaveFiveMemoryIntegrityCheck, ...]
    quarantine_findings: tuple[WaveFiveMemoryQuarantineFinding, ...]
    protocol_ids: tuple[str, ...]
    reviewer_ids: tuple[str, ...] = ()
    claim_boundaries: tuple[WaveFiveClaimBoundary, ...] = (
        WAVE_FIVE_REQUIRED_CLAIM_BOUNDARIES
    )
    notes: tuple[str, ...] = ()
    schema_version: str = WAVE_FIVE_MEMORY_PROOF_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate memory-integrity coverage and external-review boundaries."""

        object.__setattr__(self, "proof_id", _text(self.proof_id, "proof_id"))
        object.__setattr__(self, "title", _text(self.title, "title"))
        claims = tuple(sorted(self.memory_claims, key=lambda item: item.claim_key))
        checks = tuple(sorted(self.integrity_checks, key=lambda item: item.check_key))
        findings = tuple(
            sorted(self.quarantine_findings, key=lambda item: item.finding_key)
        )
        if not claims:
            raise ValueError("Memory-integrity proofs require memory claims.")
        if not checks:
            raise ValueError("Memory-integrity proofs require integrity checks.")
        claim_ids = _unique_values(
            (item.memory_id for item in claims), label="memory_id"
        )
        _unique_values((item.check_id for item in checks), label="check_id")
        _unique_values((item.finding_id for item in findings), label="finding_id")
        for finding in findings:
            if finding.memory_id not in claim_ids:
                raise ValueError(
                    "Memory quarantine findings must reference bundled memory: "
                    f"{finding.memory_id}"
                )
        object.__setattr__(self, "memory_claims", claims)
        object.__setattr__(self, "integrity_checks", checks)
        object.__setattr__(self, "quarantine_findings", findings)
        object.__setattr__(
            self, "protocol_ids", _unique_text(self.protocol_ids, label="protocol_id")
        )
        if not self.protocol_ids:
            raise ValueError("Memory-integrity proofs require protocol ids.")
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
                "Memory-integrity proofs must preserve claim boundary: "
                f"{missing_boundaries[0].value}"
            )
        object.__setattr__(self, "notes", _unique_text(self.notes, label="note"))
        object.__setattr__(
            self, "schema_version", _text(self.schema_version, "schema_version")
        )
        if self.externally_reviewed_with_boundaries:
            if self.source_system not in EXTERNAL_MEMORY_REVIEW_SOURCE_SYSTEMS:
                raise ValueError(
                    "Externally reviewed memory proofs require external source."
                )
            if not self.reviewer_ids:
                raise ValueError(
                    "Externally reviewed memory proofs require reviewer ids."
                )
            if self.blocking_claim_ids or self.blocking_check_ids:
                raise ValueError(
                    "Externally reviewed memory proofs cannot contain blockers."
                )

    @property
    def memory_ids(self) -> tuple[str, ...]:
        """Return memory ids in deterministic order."""

        return tuple(claim.memory_id for claim in self.memory_claims)

    @property
    def covered_check_kinds(self) -> tuple[WaveFiveMemoryCheckKind, ...]:
        """Return memory-integrity check kinds represented by this proof."""

        kinds: list[WaveFiveMemoryCheckKind] = []
        seen: set[WaveFiveMemoryCheckKind] = set()
        for check in self.integrity_checks:
            if check.check_kind not in seen:
                kinds.append(check.check_kind)
                seen.add(check.check_kind)
        return tuple(kinds)

    @property
    def missing_required_check_kinds(self) -> tuple[WaveFiveMemoryCheckKind, ...]:
        """Return required memory checks absent from this proof."""

        covered = set(self.covered_check_kinds)
        return tuple(
            check_kind
            for check_kind in REQUIRED_WAVE_FIVE_MEMORY_CHECKS
            if check_kind not in covered
        )

    @property
    def blocking_claim_ids(self) -> tuple[str, ...]:
        """Return memory claims that block Wave 5 memory readiness."""

        return tuple(
            claim.memory_id
            for claim in self.memory_claims
            if claim.blocks_wave_five_progress
        )

    @property
    def visible_untrusted_memory_ids(self) -> tuple[str, ...]:
        """Return untrusted memory ids kept visible for reviewers."""

        return tuple(
            claim.memory_id
            for claim in self.memory_claims
            if claim.needs_visibility_not_trust
        )

    @property
    def blocking_check_ids(self) -> tuple[str, ...]:
        """Return memory-integrity checks that block Wave 5 progress."""

        return tuple(
            check.check_id
            for check in self.integrity_checks
            if check.blocks_wave_five_progress
        )

    @property
    def blocking_quarantine_finding_ids(self) -> tuple[str, ...]:
        """Return quarantine findings that fail to reject unsafe memory."""

        return tuple(
            finding.finding_id
            for finding in self.quarantine_findings
            if finding.blocks_wave_five_progress
        )

    @property
    def has_required_check_coverage(self) -> bool:
        """Return whether every locked memory-integrity check is represented."""

        return not self.missing_required_check_kinds

    @property
    def rejects_untrusted_memory(self) -> bool:
        """Return whether every untrusted memory claim has a resolved quarantine."""

        visible_untrusted = set(self.visible_untrusted_memory_ids)
        if not visible_untrusted:
            return True
        resolved = {
            finding.memory_id
            for finding in self.quarantine_findings
            if finding.resolved
        }
        return visible_untrusted.issubset(resolved)

    @property
    def ready_for_external_memory_review(self) -> bool:
        """Return whether the proof can enter external memory review."""

        return (
            self.review_state
            in {
                WaveFiveMemoryProofReviewState.INTERNAL_REPLAY_READY,
                WaveFiveMemoryProofReviewState.READY_FOR_EXTERNAL_MEMORY_REVIEW,
                WaveFiveMemoryProofReviewState.UNDER_EXTERNAL_MEMORY_REVIEW,
            }
            and self.has_required_check_coverage
            and self.rejects_untrusted_memory
            and not self.blocking_check_ids
            and not self.blocking_quarantine_finding_ids
        )

    @property
    def externally_reviewed_with_boundaries(self) -> bool:
        """Return whether external memory review accepted boundaries."""

        return (
            self.review_state
            is WaveFiveMemoryProofReviewState.EXTERNALLY_REVIEWED_WITH_BOUNDARIES
        )

    @property
    def all_evidence_ids(self) -> tuple[str, ...]:
        """Return all evidence ids bound into this memory proof."""

        evidence_ids: list[str] = []
        seen: set[str] = set()
        for evidence_id in self._iter_evidence_ids():
            if evidence_id not in seen:
                evidence_ids.append(evidence_id)
                seen.add(evidence_id)
        return tuple(evidence_ids)

    def to_artifact_ref(self) -> WaveFiveArtifactRef:
        """Return this proof as a Wave 5 memory-integrity artifact."""

        decision = WaveFiveArtifactDecision.NEEDS_EXTERNAL_EVIDENCE
        status = WaveFiveValidationStatus.MISSING_EXTERNAL_EVIDENCE
        authority = WaveFiveAuthorityState.HUMAN_REVIEW_REQUIRED
        if self.externally_reviewed_with_boundaries:
            decision = WaveFiveArtifactDecision.EXTERNALLY_REVIEWED
            status = WaveFiveValidationStatus.ACCEPTED_WITH_BOUNDARIES
        elif self.ready_for_external_memory_review:
            decision = WaveFiveArtifactDecision.READY_FOR_INDEPENDENT_REVIEW
            status = WaveFiveValidationStatus.UNDER_INDEPENDENT_REVIEW
        elif self.blocking_check_ids or self.blocking_quarantine_finding_ids:
            decision = WaveFiveArtifactDecision.BLOCKED
            status = WaveFiveValidationStatus.REJECTED
            authority = WaveFiveAuthorityState.BLOCKED
        elif self.blocking_claim_ids and not self.rejects_untrusted_memory:
            decision = WaveFiveArtifactDecision.BLOCKED
            status = WaveFiveValidationStatus.REJECTED
            authority = WaveFiveAuthorityState.BLOCKED
        return WaveFiveArtifactRef(
            artifact_id=self.proof_id,
            kind=WaveFiveArtifactKind.MEMORY_INTEGRITY_PROOF,
            capability_area=WaveFiveCapabilityArea.MEMORY_INTEGRITY,
            source_system=self.source_system,
            summary=self.title,
            produced_by_engine_id="wave5-memory-integrity-engine",
            produced_by_agent_role_id="memory-integrity-reviewer",
            evidence_ids=self.all_evidence_ids,
            decision=decision,
            authority_state=authority,
            validation_status=status,
            claim_boundaries=self.claim_boundaries,
        )

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic export payload."""

        return {
            "claim_boundaries": [boundary.value for boundary in self.claim_boundaries],
            "integrity_checks": [
                check.canonical_payload() for check in self.integrity_checks
            ],
            "memory_claims": [
                claim.canonical_payload() for claim in self.memory_claims
            ],
            "notes": list(self.notes),
            "proof_id": self.proof_id,
            "protocol_ids": list(self.protocol_ids),
            "quarantine_findings": [
                finding.canonical_payload() for finding in self.quarantine_findings
            ],
            "review_state": self.review_state.value,
            "reviewer_ids": list(self.reviewer_ids),
            "schema_version": self.schema_version,
            "source_system": self.source_system.value,
            "title": self.title,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this proof."""

        return _stable_sha256(self.canonical_payload())

    def _iter_evidence_ids(self) -> Iterable[str]:
        """Yield evidence ids in deterministic proof traversal order."""

        for claim in self.memory_claims:
            yield from claim.evidence_ids
            yield from claim.contradiction_ids
            yield from claim.staleness_evidence_ids
        for check in self.integrity_checks:
            yield from check.evidence_ids
        for finding in self.quarantine_findings:
            yield from finding.evidence_ids


def required_wave_five_memory_checks() -> tuple[WaveFiveMemoryCheckKind, ...]:
    """Return locked checks required for Wave 5 memory-integrity review."""

    return REQUIRED_WAVE_FIVE_MEMORY_CHECKS


def safe_memory_integrity_states() -> tuple[WaveFiveMemoryIntegrityState, ...]:
    """Return memory states that can support bounded planning evidence."""

    return SAFE_MEMORY_INTEGRITY_STATES


def blocking_memory_integrity_states() -> tuple[WaveFiveMemoryIntegrityState, ...]:
    """Return memory states that block trust unless quarantined visibly."""

    return BLOCKING_MEMORY_INTEGRITY_STATES


def external_memory_review_source_systems() -> tuple[WaveFiveSourceSystem, ...]:
    """Return source systems allowed to assert external memory review."""

    return EXTERNAL_MEMORY_REVIEW_SOURCE_SYSTEMS


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

    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return hashlib.sha256(encoded).hexdigest()
