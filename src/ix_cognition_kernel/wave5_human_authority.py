"""Wave 5 human-authority preservation proof records.

Wave 5 can only bridge into Wave 6 if every evidence path keeps humans in
charge. This module records authority boundaries, review-only decisions,
bypass-attempt handling, and authority-preservation checks. The proof is
reviewable only when autonomous execution is denied, self-approval is blocked,
escalation is visible, evidence packets are required, donor-repo authority does
not leak into Kernel, and no maturity or AGI claim can be self-authorized.
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

WAVE_FIVE_AUTHORITY_BOUNDARY_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave5-authority-boundary-v1"
)
WAVE_FIVE_AUTHORITY_DECISION_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave5-authority-decision-v1"
)
WAVE_FIVE_AUTHORITY_BYPASS_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave5-authority-bypass-v1"
)
WAVE_FIVE_AUTHORITY_CHECK_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave5-authority-check-v1"
)
WAVE_FIVE_HUMAN_AUTHORITY_PROOF_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave5-human-authority-proof-v1"
)


class WaveFiveAuthorityBoundaryKind(StrEnum):
    """Authority boundaries that Wave 5 must preserve."""

    HUMAN_APPROVAL_REQUIRED = "human-approval-required"
    NO_AUTONOMOUS_EXECUTION = "no-autonomous-execution"
    NO_SELF_APPROVAL = "no-self-approval"
    EVIDENCE_REVIEW_REQUIRED = "evidence-review-required"
    REVOCATION_AVAILABLE = "revocation-available"
    ESCALATION_VISIBLE = "escalation-visible"
    DONOR_REPO_AUTHORITY_ISOLATED = "donor-repo-authority-isolated"
    MATURITY_CLAIM_REVIEW_REQUIRED = "maturity-claim-review-required"


class WaveFiveAuthorityDecisionKind(StrEnum):
    """Decision outcomes allowed in authority-preservation records."""

    APPROVED_FOR_REVIEW_ONLY = "approved-for-review-only"
    ESCALATED_TO_HUMAN_REVIEW = "escalated-to-human-review"
    REJECTED = "rejected"
    NEEDS_MORE_EVIDENCE = "needs-more-evidence"
    BLOCKED_UNAUTHORIZED_ACTION = "blocked-unauthorized-action"
    UNAUTHORIZED_ACTION_ATTEMPTED = "unauthorized-action-attempted"


class WaveFiveAuthorityBypassKind(StrEnum):
    """Bypass attempts that must be detected and blocked."""

    SELF_APPROVAL = "self-approval"
    AUTONOMOUS_EXECUTION = "autonomous-execution"
    HUMAN_REVIEW_OMITTED = "human-review-omitted"
    EVIDENCE_PACKET_SKIPPED = "evidence-packet-skipped"
    DONOR_REPO_AUTHORITY_LEAK = "donor-repo-authority-leak"
    MATURITY_SELF_PROMOTION = "maturity-self-promotion"
    HIDDEN_IRREVERSIBLE_ACTION = "hidden-irreversible-action"


class WaveFiveAuthorityCheckKind(StrEnum):
    """Required checks before authority proof can enter external review."""

    HUMAN_APPROVAL_GATE_PRESENT = "human-approval-gate-present"
    NO_AUTONOMOUS_EXECUTION_GRANTED = "no-autonomous-execution-granted"
    SELF_APPROVAL_BLOCKED = "self-approval-blocked"
    EVIDENCE_PACKET_REQUIRED = "evidence-packet-required"
    REVOCATION_PATH_PRESENT = "revocation-path-present"
    ESCALATION_PATH_VISIBLE = "escalation-path-visible"
    DONOR_AUTHORITY_ISOLATED = "donor-authority-isolated"
    MATURITY_CLAIM_REVIEW_GATED = "maturity-claim-review-gated"
    AUDIT_TRACE_VISIBLE = "audit-trace-visible"


class WaveFiveAuthorityCheckResult(StrEnum):
    """Observed result of one authority-preservation check."""

    PASSED = "passed"
    PASSED_WITH_LIMITS = "passed-with-limits"
    NEEDS_MORE_EVIDENCE = "needs-more-evidence"
    FAILED = "failed"


class WaveFiveAuthorityReviewState(StrEnum):
    """Review state of a Wave 5 human-authority proof."""

    INTERNAL_REPLAY_READY = "internal-replay-ready"
    READY_FOR_EXTERNAL_AUTHORITY_REVIEW = "ready-for-external-authority-review"
    UNDER_EXTERNAL_AUTHORITY_REVIEW = "under-external-authority-review"
    EXTERNALLY_REVIEWED_WITH_BOUNDARIES = "externally-reviewed-with-boundaries"
    BLOCKED_BY_AUTHORITY_FAILURE = "blocked-by-authority-failure"


SAFE_AUTHORITY_DECISIONS: tuple[WaveFiveAuthorityDecisionKind, ...] = (
    WaveFiveAuthorityDecisionKind.APPROVED_FOR_REVIEW_ONLY,
    WaveFiveAuthorityDecisionKind.ESCALATED_TO_HUMAN_REVIEW,
    WaveFiveAuthorityDecisionKind.REJECTED,
    WaveFiveAuthorityDecisionKind.BLOCKED_UNAUTHORIZED_ACTION,
)

BLOCKING_AUTHORITY_DECISIONS: tuple[WaveFiveAuthorityDecisionKind, ...] = (
    WaveFiveAuthorityDecisionKind.NEEDS_MORE_EVIDENCE,
    WaveFiveAuthorityDecisionKind.UNAUTHORIZED_ACTION_ATTEMPTED,
)

REQUIRED_AUTHORITY_BOUNDARIES: tuple[WaveFiveAuthorityBoundaryKind, ...] = (
    WaveFiveAuthorityBoundaryKind.HUMAN_APPROVAL_REQUIRED,
    WaveFiveAuthorityBoundaryKind.NO_AUTONOMOUS_EXECUTION,
    WaveFiveAuthorityBoundaryKind.NO_SELF_APPROVAL,
    WaveFiveAuthorityBoundaryKind.EVIDENCE_REVIEW_REQUIRED,
    WaveFiveAuthorityBoundaryKind.REVOCATION_AVAILABLE,
    WaveFiveAuthorityBoundaryKind.ESCALATION_VISIBLE,
    WaveFiveAuthorityBoundaryKind.DONOR_REPO_AUTHORITY_ISOLATED,
    WaveFiveAuthorityBoundaryKind.MATURITY_CLAIM_REVIEW_REQUIRED,
)

REQUIRED_AUTHORITY_BYPASS_KINDS: tuple[WaveFiveAuthorityBypassKind, ...] = (
    WaveFiveAuthorityBypassKind.SELF_APPROVAL,
    WaveFiveAuthorityBypassKind.AUTONOMOUS_EXECUTION,
    WaveFiveAuthorityBypassKind.HUMAN_REVIEW_OMITTED,
    WaveFiveAuthorityBypassKind.EVIDENCE_PACKET_SKIPPED,
    WaveFiveAuthorityBypassKind.DONOR_REPO_AUTHORITY_LEAK,
    WaveFiveAuthorityBypassKind.MATURITY_SELF_PROMOTION,
    WaveFiveAuthorityBypassKind.HIDDEN_IRREVERSIBLE_ACTION,
)

REQUIRED_AUTHORITY_CHECKS: tuple[WaveFiveAuthorityCheckKind, ...] = (
    WaveFiveAuthorityCheckKind.HUMAN_APPROVAL_GATE_PRESENT,
    WaveFiveAuthorityCheckKind.NO_AUTONOMOUS_EXECUTION_GRANTED,
    WaveFiveAuthorityCheckKind.SELF_APPROVAL_BLOCKED,
    WaveFiveAuthorityCheckKind.EVIDENCE_PACKET_REQUIRED,
    WaveFiveAuthorityCheckKind.REVOCATION_PATH_PRESENT,
    WaveFiveAuthorityCheckKind.ESCALATION_PATH_VISIBLE,
    WaveFiveAuthorityCheckKind.DONOR_AUTHORITY_ISOLATED,
    WaveFiveAuthorityCheckKind.MATURITY_CLAIM_REVIEW_GATED,
    WaveFiveAuthorityCheckKind.AUDIT_TRACE_VISIBLE,
)

EXTERNAL_AUTHORITY_REVIEW_SOURCE_SYSTEMS: tuple[WaveFiveSourceSystem, ...] = (
    WaveFiveSourceSystem.EXTERNAL_REVIEW,
    WaveFiveSourceSystem.INDEPENDENT_REVIEWER,
    WaveFiveSourceSystem.HUMAN_REVIEW,
)


@dataclass(frozen=True, slots=True)
class WaveFiveAuthorityBoundary:
    """One human-authority boundary that protects a high-risk action."""

    boundary_id: str
    boundary_kind: WaveFiveAuthorityBoundaryKind
    protected_action: str
    required_human_role: str
    enforcement_summary: str
    evidence_ids: tuple[str, ...]
    enforced: bool = True
    revocable: bool = True
    schema_version: str = WAVE_FIVE_AUTHORITY_BOUNDARY_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate authority-boundary identity and enforceability."""

        object.__setattr__(self, "boundary_id", _text(self.boundary_id, "boundary_id"))
        object.__setattr__(
            self, "protected_action", _text(self.protected_action, "protected_action")
        )
        object.__setattr__(
            self,
            "required_human_role",
            _text(self.required_human_role, "required_human_role"),
        )
        object.__setattr__(
            self,
            "enforcement_summary",
            _text(self.enforcement_summary, "enforcement_summary"),
        )
        object.__setattr__(
            self, "evidence_ids", _unique_text(self.evidence_ids, label="evidence_id")
        )
        if not self.evidence_ids:
            raise ValueError("Authority boundaries require evidence ids.")
        if self.boundary_kind is WaveFiveAuthorityBoundaryKind.REVOCATION_AVAILABLE:
            if not self.revocable:
                raise ValueError("Revocation boundaries must be revocable.")
        object.__setattr__(
            self, "schema_version", _text(self.schema_version, "schema_version")
        )

    @property
    def boundary_key(self) -> str:
        """Return deterministic boundary key."""

        return self.boundary_id

    @property
    def blocks_wave_five_progress(self) -> bool:
        """Return whether the boundary is missing enforcement."""

        return not self.enforced or not self.revocable

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic export payload."""

        return {
            "boundary_id": self.boundary_id,
            "boundary_kind": self.boundary_kind.value,
            "enforced": self.enforced,
            "enforcement_summary": self.enforcement_summary,
            "evidence_ids": list(self.evidence_ids),
            "protected_action": self.protected_action,
            "required_human_role": self.required_human_role,
            "revocable": self.revocable,
            "schema_version": self.schema_version,
        }


@dataclass(frozen=True, slots=True)
class WaveFiveAuthorityDecisionRecord:
    """Review-only decision that preserves human authority."""

    decision_id: str
    boundary_id: str
    decision_kind: WaveFiveAuthorityDecisionKind
    requested_action: str
    decision_summary: str
    human_reviewer_id: str
    evidence_ids: tuple[str, ...]
    granted_execution_authority: bool = False
    self_approved: bool = False
    approved_maturity_claim: bool = False
    preserved_human_authority: bool = True
    schema_version: str = WAVE_FIVE_AUTHORITY_DECISION_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate that decisions never create autonomous authority."""

        object.__setattr__(self, "decision_id", _text(self.decision_id, "decision_id"))
        object.__setattr__(self, "boundary_id", _text(self.boundary_id, "boundary_id"))
        object.__setattr__(
            self, "requested_action", _text(self.requested_action, "requested_action")
        )
        object.__setattr__(
            self, "decision_summary", _text(self.decision_summary, "decision_summary")
        )
        object.__setattr__(self, "human_reviewer_id", self.human_reviewer_id.strip())
        object.__setattr__(
            self, "evidence_ids", _unique_text(self.evidence_ids, label="evidence_id")
        )
        if not self.evidence_ids:
            raise ValueError("Authority decisions require evidence ids.")
        if self.granted_execution_authority:
            raise ValueError("Wave 5 authority decisions cannot grant execution.")
        if self.self_approved:
            raise ValueError("Wave 5 authority decisions cannot be self-approved.")
        if self.approved_maturity_claim:
            raise ValueError("Wave 5 decisions cannot approve maturity claims.")
        if self.decision_kind in SAFE_AUTHORITY_DECISIONS:
            if not self.human_reviewer_id:
                raise ValueError("Safe authority decisions require a human reviewer.")
            if not self.preserved_human_authority:
                raise ValueError("Safe authority decisions must preserve authority.")
        object.__setattr__(
            self, "schema_version", _text(self.schema_version, "schema_version")
        )

    @property
    def decision_key(self) -> str:
        """Return deterministic decision key."""

        return self.decision_id

    @property
    def is_safe_decision(self) -> bool:
        """Return whether this decision preserves human authority."""

        return self.decision_kind in SAFE_AUTHORITY_DECISIONS

    @property
    def blocks_wave_five_progress(self) -> bool:
        """Return whether this decision blocks authority readiness."""

        return self.decision_kind in BLOCKING_AUTHORITY_DECISIONS

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic export payload."""

        return {
            "approved_maturity_claim": self.approved_maturity_claim,
            "boundary_id": self.boundary_id,
            "decision_id": self.decision_id,
            "decision_kind": self.decision_kind.value,
            "decision_summary": self.decision_summary,
            "evidence_ids": list(self.evidence_ids),
            "granted_execution_authority": self.granted_execution_authority,
            "human_reviewer_id": self.human_reviewer_id,
            "preserved_human_authority": self.preserved_human_authority,
            "requested_action": self.requested_action,
            "schema_version": self.schema_version,
            "self_approved": self.self_approved,
        }


@dataclass(frozen=True, slots=True)
class WaveFiveAuthorityBypassAttempt:
    """Detected bypass attempt that must be blocked and reviewer visible."""

    attempt_id: str
    boundary_id: str
    bypass_kind: WaveFiveAuthorityBypassKind
    attempt_summary: str
    detected: bool
    blocked: bool
    reviewer_visible: bool
    mitigation: str
    evidence_ids: tuple[str, ...]
    schema_version: str = WAVE_FIVE_AUTHORITY_BYPASS_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate bypass-attempt visibility and mitigation."""

        object.__setattr__(self, "attempt_id", _text(self.attempt_id, "attempt_id"))
        object.__setattr__(self, "boundary_id", _text(self.boundary_id, "boundary_id"))
        object.__setattr__(
            self, "attempt_summary", _text(self.attempt_summary, "attempt_summary")
        )
        object.__setattr__(self, "mitigation", _text(self.mitigation, "mitigation"))
        object.__setattr__(
            self, "evidence_ids", _unique_text(self.evidence_ids, label="evidence_id")
        )
        if not self.evidence_ids:
            raise ValueError("Authority bypass attempts require evidence ids.")
        if not self.reviewer_visible:
            raise ValueError("Authority bypass attempts must be reviewer visible.")
        object.__setattr__(
            self, "schema_version", _text(self.schema_version, "schema_version")
        )

    @property
    def attempt_key(self) -> str:
        """Return deterministic bypass-attempt key."""

        return self.attempt_id

    @property
    def resolved(self) -> bool:
        """Return whether the bypass attempt was detected, blocked, and visible."""

        return self.detected and self.blocked and self.reviewer_visible

    @property
    def blocks_wave_five_progress(self) -> bool:
        """Return whether this bypass attempt blocks authority readiness."""

        return not self.resolved

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic export payload."""

        return {
            "attempt_id": self.attempt_id,
            "attempt_summary": self.attempt_summary,
            "blocked": self.blocked,
            "boundary_id": self.boundary_id,
            "bypass_kind": self.bypass_kind.value,
            "detected": self.detected,
            "evidence_ids": list(self.evidence_ids),
            "mitigation": self.mitigation,
            "resolved": self.resolved,
            "reviewer_visible": self.reviewer_visible,
            "schema_version": self.schema_version,
        }


@dataclass(frozen=True, slots=True)
class WaveFiveAuthorityPreservationCheck:
    """One check proving human authority is preserved."""

    check_id: str
    check_kind: WaveFiveAuthorityCheckKind
    result: WaveFiveAuthorityCheckResult
    description: str
    evidence_ids: tuple[str, ...]
    blocking: bool = True
    schema_version: str = WAVE_FIVE_AUTHORITY_CHECK_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate authority-preservation check evidence."""

        object.__setattr__(self, "check_id", _text(self.check_id, "check_id"))
        object.__setattr__(self, "description", _text(self.description, "description"))
        object.__setattr__(
            self, "evidence_ids", _unique_text(self.evidence_ids, label="evidence_id")
        )
        if not self.evidence_ids:
            raise ValueError("Authority preservation checks require evidence ids.")
        object.__setattr__(
            self, "schema_version", _text(self.schema_version, "schema_version")
        )

    @property
    def check_key(self) -> str:
        """Return deterministic check key."""

        return self.check_id

    @property
    def passed_with_boundaries(self) -> bool:
        """Return whether this check passed while preserving limitations."""

        return self.result in {
            WaveFiveAuthorityCheckResult.PASSED,
            WaveFiveAuthorityCheckResult.PASSED_WITH_LIMITS,
        }

    @property
    def blocks_wave_five_progress(self) -> bool:
        """Return whether this check blocks authority readiness."""

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
class WaveFiveHumanAuthorityProof:
    """Wave 5 proof that humans remain the authority boundary."""

    proof_id: str
    title: str
    source_system: WaveFiveSourceSystem
    review_state: WaveFiveAuthorityReviewState
    boundaries: tuple[WaveFiveAuthorityBoundary, ...]
    decisions: tuple[WaveFiveAuthorityDecisionRecord, ...]
    bypass_attempts: tuple[WaveFiveAuthorityBypassAttempt, ...]
    checks: tuple[WaveFiveAuthorityPreservationCheck, ...]
    protocol_ids: tuple[str, ...]
    reviewer_ids: tuple[str, ...] = ()
    claim_boundaries: tuple[WaveFiveClaimBoundary, ...] = (
        WAVE_FIVE_REQUIRED_CLAIM_BOUNDARIES
    )
    notes: tuple[str, ...] = ()
    schema_version: str = WAVE_FIVE_HUMAN_AUTHORITY_PROOF_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate human-authority coverage and external-review boundaries."""

        object.__setattr__(self, "proof_id", _text(self.proof_id, "proof_id"))
        object.__setattr__(self, "title", _text(self.title, "title"))
        boundaries = tuple(sorted(self.boundaries, key=lambda item: item.boundary_key))
        decisions = tuple(sorted(self.decisions, key=lambda item: item.decision_key))
        attempts = tuple(
            sorted(self.bypass_attempts, key=lambda item: item.attempt_key)
        )
        checks = tuple(sorted(self.checks, key=lambda item: item.check_key))
        if not boundaries:
            raise ValueError("Human-authority proofs require boundaries.")
        if not decisions:
            raise ValueError("Human-authority proofs require decisions.")
        if not attempts:
            raise ValueError("Human-authority proofs require bypass attempts.")
        if not checks:
            raise ValueError("Human-authority proofs require checks.")
        boundary_ids = _unique_values(
            (item.boundary_id for item in boundaries), label="boundary_id"
        )
        _unique_values((item.decision_id for item in decisions), label="decision_id")
        _unique_values((item.attempt_id for item in attempts), label="attempt_id")
        _unique_values((item.check_id for item in checks), label="check_id")
        self._validate_boundary_references(boundary_ids, decisions, attempts)
        object.__setattr__(self, "boundaries", boundaries)
        object.__setattr__(self, "decisions", decisions)
        object.__setattr__(self, "bypass_attempts", attempts)
        object.__setattr__(self, "checks", checks)
        object.__setattr__(
            self, "protocol_ids", _unique_text(self.protocol_ids, label="protocol_id")
        )
        if not self.protocol_ids:
            raise ValueError("Human-authority proofs require protocol ids.")
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
                "Human-authority proofs must preserve claim boundary: "
                f"{missing_boundaries[0].value}"
            )
        object.__setattr__(self, "notes", _unique_text(self.notes, label="note"))
        object.__setattr__(
            self, "schema_version", _text(self.schema_version, "schema_version")
        )
        if self.externally_reviewed_with_boundaries:
            if self.source_system not in EXTERNAL_AUTHORITY_REVIEW_SOURCE_SYSTEMS:
                raise ValueError(
                    "Externally reviewed authority proofs require external source."
                )
            if not self.reviewer_ids:
                raise ValueError(
                    "Externally reviewed authority proofs require reviewer ids."
                )
            if self.blocks_authority_readiness:
                raise ValueError(
                    "Externally reviewed authority proofs cannot contain blockers."
                )

    @property
    def covered_boundary_kinds(self) -> tuple[WaveFiveAuthorityBoundaryKind, ...]:
        """Return authority boundary kinds represented in this proof."""

        kinds: list[WaveFiveAuthorityBoundaryKind] = []
        seen: set[WaveFiveAuthorityBoundaryKind] = set()
        for boundary in self.boundaries:
            if boundary.boundary_kind not in seen:
                kinds.append(boundary.boundary_kind)
                seen.add(boundary.boundary_kind)
        return tuple(kinds)

    @property
    def missing_required_boundary_kinds(
        self,
    ) -> tuple[WaveFiveAuthorityBoundaryKind, ...]:
        """Return required authority boundary kinds absent from this proof."""

        covered = set(self.covered_boundary_kinds)
        return tuple(
            kind for kind in REQUIRED_AUTHORITY_BOUNDARIES if kind not in covered
        )

    @property
    def covered_bypass_kinds(self) -> tuple[WaveFiveAuthorityBypassKind, ...]:
        """Return bypass-attempt kinds represented in this proof."""

        kinds: list[WaveFiveAuthorityBypassKind] = []
        seen: set[WaveFiveAuthorityBypassKind] = set()
        for attempt in self.bypass_attempts:
            if attempt.bypass_kind not in seen:
                kinds.append(attempt.bypass_kind)
                seen.add(attempt.bypass_kind)
        return tuple(kinds)

    @property
    def missing_required_bypass_kinds(self) -> tuple[WaveFiveAuthorityBypassKind, ...]:
        """Return required bypass-attempt kinds absent from this proof."""

        covered = set(self.covered_bypass_kinds)
        return tuple(
            kind for kind in REQUIRED_AUTHORITY_BYPASS_KINDS if kind not in covered
        )

    @property
    def covered_check_kinds(self) -> tuple[WaveFiveAuthorityCheckKind, ...]:
        """Return authority-check kinds represented in this proof."""

        kinds: list[WaveFiveAuthorityCheckKind] = []
        seen: set[WaveFiveAuthorityCheckKind] = set()
        for check in self.checks:
            if check.check_kind not in seen:
                kinds.append(check.check_kind)
                seen.add(check.check_kind)
        return tuple(kinds)

    @property
    def missing_required_check_kinds(self) -> tuple[WaveFiveAuthorityCheckKind, ...]:
        """Return required authority checks absent from this proof."""

        covered = set(self.covered_check_kinds)
        return tuple(kind for kind in REQUIRED_AUTHORITY_CHECKS if kind not in covered)

    @property
    def blocking_boundary_ids(self) -> tuple[str, ...]:
        """Return authority boundaries that are not enforceable."""

        return tuple(
            boundary.boundary_id
            for boundary in self.boundaries
            if boundary.blocks_wave_five_progress
        )

    @property
    def blocking_decision_ids(self) -> tuple[str, ...]:
        """Return decisions that block human-authority readiness."""

        return tuple(
            decision.decision_id
            for decision in self.decisions
            if decision.blocks_wave_five_progress
        )

    @property
    def blocking_bypass_attempt_ids(self) -> tuple[str, ...]:
        """Return bypass attempts that were not resolved."""

        return tuple(
            attempt.attempt_id
            for attempt in self.bypass_attempts
            if attempt.blocks_wave_five_progress
        )

    @property
    def blocking_check_ids(self) -> tuple[str, ...]:
        """Return authority checks that block readiness."""

        return tuple(
            check.check_id for check in self.checks if check.blocks_wave_five_progress
        )

    @property
    def grants_no_execution_authority(self) -> bool:
        """Return whether no decision grants execution authority."""

        return not any(
            decision.granted_execution_authority for decision in self.decisions
        )

    @property
    def blocks_self_approval(self) -> bool:
        """Return whether no decision is self-approved."""

        return not any(decision.self_approved for decision in self.decisions)

    @property
    def blocks_maturity_self_promotion(self) -> bool:
        """Return whether no decision approves maturity claims."""

        return not any(decision.approved_maturity_claim for decision in self.decisions)

    @property
    def preserves_human_authority(self) -> bool:
        """Return whether all decisions preserve human authority."""

        return all(decision.preserved_human_authority for decision in self.decisions)

    @property
    def has_required_boundary_coverage(self) -> bool:
        """Return whether every locked authority boundary is represented."""

        return not self.missing_required_boundary_kinds

    @property
    def has_required_bypass_coverage(self) -> bool:
        """Return whether every locked bypass kind is represented."""

        return not self.missing_required_bypass_kinds

    @property
    def has_required_check_coverage(self) -> bool:
        """Return whether every locked authority check is represented."""

        return not self.missing_required_check_kinds

    @property
    def blocks_authority_readiness(self) -> bool:
        """Return whether any authority subrecord blocks Wave 5 readiness."""

        return bool(
            self.blocking_boundary_ids
            or self.blocking_decision_ids
            or self.blocking_bypass_attempt_ids
            or self.blocking_check_ids
        )

    @property
    def ready_for_external_authority_review(self) -> bool:
        """Return whether proof can enter external authority review."""

        return (
            self.review_state
            in {
                WaveFiveAuthorityReviewState.INTERNAL_REPLAY_READY,
                WaveFiveAuthorityReviewState.READY_FOR_EXTERNAL_AUTHORITY_REVIEW,
                WaveFiveAuthorityReviewState.UNDER_EXTERNAL_AUTHORITY_REVIEW,
            }
            and self.has_required_boundary_coverage
            and self.has_required_bypass_coverage
            and self.has_required_check_coverage
            and not self.blocks_authority_readiness
            and self.grants_no_execution_authority
            and self.blocks_self_approval
            and self.blocks_maturity_self_promotion
            and self.preserves_human_authority
        )

    @property
    def externally_reviewed_with_boundaries(self) -> bool:
        """Return whether external authority review accepted boundaries."""

        return (
            self.review_state
            is WaveFiveAuthorityReviewState.EXTERNALLY_REVIEWED_WITH_BOUNDARIES
        )

    @property
    def all_evidence_ids(self) -> tuple[str, ...]:
        """Return all evidence ids bound into this proof."""

        evidence_ids: list[str] = []
        seen: set[str] = set()
        for evidence_id in self._iter_evidence_ids():
            if evidence_id not in seen:
                evidence_ids.append(evidence_id)
                seen.add(evidence_id)
        return tuple(evidence_ids)

    def to_artifact_ref(self) -> WaveFiveArtifactRef:
        """Return this proof as a Wave 5 human-authority artifact."""

        decision = WaveFiveArtifactDecision.NEEDS_EXTERNAL_EVIDENCE
        status = WaveFiveValidationStatus.MISSING_EXTERNAL_EVIDENCE
        authority = WaveFiveAuthorityState.HUMAN_REVIEW_REQUIRED
        if self.externally_reviewed_with_boundaries:
            decision = WaveFiveArtifactDecision.EXTERNALLY_REVIEWED
            status = WaveFiveValidationStatus.ACCEPTED_WITH_BOUNDARIES
        elif self.ready_for_external_authority_review:
            decision = WaveFiveArtifactDecision.READY_FOR_INDEPENDENT_REVIEW
            status = WaveFiveValidationStatus.UNDER_INDEPENDENT_REVIEW
        elif self.blocks_authority_readiness:
            decision = WaveFiveArtifactDecision.BLOCKED
            status = WaveFiveValidationStatus.REJECTED
            authority = WaveFiveAuthorityState.BLOCKED
        return WaveFiveArtifactRef(
            artifact_id=self.proof_id,
            kind=WaveFiveArtifactKind.HUMAN_AUTHORITY_PROOF,
            capability_area=WaveFiveCapabilityArea.HUMAN_AUTHORITY_PRESERVATION,
            source_system=self.source_system,
            summary=self.title,
            produced_by_engine_id="wave5-human-authority-proof-engine",
            produced_by_agent_role_id="human-authority-reviewer",
            evidence_ids=self.all_evidence_ids,
            decision=decision,
            authority_state=authority,
            validation_status=status,
            claim_boundaries=self.claim_boundaries,
        )

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic export payload."""

        return {
            "boundaries": [
                boundary.canonical_payload() for boundary in self.boundaries
            ],
            "bypass_attempts": [
                attempt.canonical_payload() for attempt in self.bypass_attempts
            ],
            "checks": [check.canonical_payload() for check in self.checks],
            "claim_boundaries": [boundary.value for boundary in self.claim_boundaries],
            "decisions": [decision.canonical_payload() for decision in self.decisions],
            "notes": list(self.notes),
            "proof_id": self.proof_id,
            "protocol_ids": list(self.protocol_ids),
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

        for boundary in self.boundaries:
            yield from boundary.evidence_ids
        for decision in self.decisions:
            yield from decision.evidence_ids
        for attempt in self.bypass_attempts:
            yield from attempt.evidence_ids
        for check in self.checks:
            yield from check.evidence_ids

    @staticmethod
    def _validate_boundary_references(
        boundary_ids: set[str],
        decisions: tuple[WaveFiveAuthorityDecisionRecord, ...],
        attempts: tuple[WaveFiveAuthorityBypassAttempt, ...],
    ) -> None:
        """Validate that decisions and bypass attempts reference boundaries."""

        for decision in decisions:
            if decision.boundary_id not in boundary_ids:
                raise ValueError(
                    "Authority decisions must reference bundled boundaries: "
                    f"{decision.boundary_id}"
                )
        for attempt in attempts:
            if attempt.boundary_id not in boundary_ids:
                raise ValueError(
                    "Authority bypass attempts must reference bundled boundaries: "
                    f"{attempt.boundary_id}"
                )


def required_authority_boundaries() -> tuple[WaveFiveAuthorityBoundaryKind, ...]:
    """Return locked authority boundaries required for Wave 5 review."""

    return REQUIRED_AUTHORITY_BOUNDARIES


def required_authority_bypass_kinds() -> tuple[WaveFiveAuthorityBypassKind, ...]:
    """Return locked bypass kinds required for Wave 5 authority review."""

    return REQUIRED_AUTHORITY_BYPASS_KINDS


def required_authority_checks() -> tuple[WaveFiveAuthorityCheckKind, ...]:
    """Return locked authority checks required for Wave 5 review."""

    return REQUIRED_AUTHORITY_CHECKS


def safe_authority_decisions() -> tuple[WaveFiveAuthorityDecisionKind, ...]:
    """Return authority decisions that preserve human authority."""

    return SAFE_AUTHORITY_DECISIONS


def blocking_authority_decisions() -> tuple[WaveFiveAuthorityDecisionKind, ...]:
    """Return authority decisions that block Wave 5 progress."""

    return BLOCKING_AUTHORITY_DECISIONS


def external_authority_review_source_systems() -> tuple[WaveFiveSourceSystem, ...]:
    """Return source systems allowed to assert external authority review."""

    return EXTERNAL_AUTHORITY_REVIEW_SOURCE_SYSTEMS


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
