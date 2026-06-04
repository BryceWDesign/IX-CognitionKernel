"""Wave 5 independent repeatability and disagreement ledger records.

Wave 5 must preserve more than successful reproductions. It also needs failed
reproduction attempts, reviewer disagreements, unresolved disputes, protocol
variance, and contradictory evidence to remain visible. This module records
repeatability attempts and disagreement entries without erasing dissent or
pretending that internal replay equals independent validation.
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

WAVE_FIVE_REPEATABILITY_ATTEMPT_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave5-repeatability-attempt-v1"
)
WAVE_FIVE_DISAGREEMENT_ENTRY_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave5-reviewer-disagreement-v1"
)
WAVE_FIVE_REPEATABILITY_CONTROL_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave5-repeatability-control-v1"
)
WAVE_FIVE_REPEATABILITY_LEDGER_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave5-repeatability-ledger-v1"
)


class WaveFiveRepeatabilityAttemptKind(StrEnum):
    """Kinds of repeatability attempts required for Wave 5 review."""

    CLEAN_CHECKOUT_REPLAY = "clean-checkout-replay"
    INDEPENDENT_LAB_REPLAY = "independent-lab-replay"
    EXTERNAL_REVIEWER_REPLAY = "external-reviewer-replay"
    CROSS_ENVIRONMENT_REPLAY = "cross-environment-replay"
    NEGATIVE_CONTROL_REPLAY = "negative-control-replay"
    FAILED_REPRODUCTION_CAPTURE = "failed-reproduction-capture"


class WaveFiveRepeatabilityOutcome(StrEnum):
    """Observed outcome of a repeatability attempt."""

    REPRODUCED = "reproduced"
    REPRODUCED_WITH_LIMITS = "reproduced-with-limits"
    FAILED_TO_REPRODUCE = "failed-to-reproduce"
    DISPUTED = "disputed"
    NEEDS_MORE_EVIDENCE = "needs-more-evidence"
    BLOCKED_BY_PROTOCOL_GAP = "blocked-by-protocol-gap"


class WaveFiveDisagreementKind(StrEnum):
    """Kinds of reviewer disagreement that must remain visible."""

    PROTOCOL_INTERPRETATION = "protocol-interpretation"
    EVIDENCE_SUFFICIENCY = "evidence-sufficiency"
    REPRODUCTION_VARIANCE = "reproduction-variance"
    SAFETY_BOUNDARY = "safety-boundary"
    AUTHORITY_BOUNDARY = "authority-boundary"
    CLAIM_SCOPE = "claim-scope"
    DONOR_REPO_COMPATIBILITY = "donor-repo-compatibility"
    WAVE_SIX_READINESS = "wave-six-readiness"


class WaveFiveDisagreementDisposition(StrEnum):
    """Disposition of one reviewer disagreement."""

    RECORDED_FOR_REVIEW = "recorded-for-review"
    RESOLVED_WITH_EVIDENCE = "resolved-with-evidence"
    ACCEPTED_AS_LIMITATION = "accepted-as-limitation"
    UNRESOLVED = "unresolved"
    BLOCKING = "blocking"


class WaveFiveRepeatabilityControlKind(StrEnum):
    """Controls that prevent erasure or cherry-picking of repeatability data."""

    FAILED_ATTEMPTS_RETAINED = "failed-attempts-retained"
    DISAGREEMENTS_RETAINED = "disagreements-retained"
    CONTRADICTORY_EVIDENCE_RETAINED = "contradictory-evidence-retained"
    EXTERNAL_SOURCE_SEPARATION = "external-source-separation"
    PROTOCOL_VARIANCE_RECORDED = "protocol-variance-recorded"
    REVIEWER_DISSENT_VISIBLE = "reviewer-dissent-visible"
    NO_CHERRY_PICKED_REPRODUCTION = "no-cherry-picked-reproduction"
    WAVE_SIX_LIMITATION_VISIBLE = "wave-six-limitation-visible"


class WaveFiveRepeatabilityControlResult(StrEnum):
    """Observed result of one repeatability-control check."""

    PASSED = "passed"
    PASSED_WITH_LIMITS = "passed-with-limits"
    NEEDS_MORE_EVIDENCE = "needs-more-evidence"
    FAILED = "failed"


class WaveFiveRepeatabilityLedgerState(StrEnum):
    """Review state of an independent repeatability ledger."""

    INTERNAL_LEDGER_READY = "internal-ledger-ready"
    READY_FOR_EXTERNAL_REPEATABILITY_REVIEW = (
        "ready-for-external-repeatability-review"
    )
    UNDER_EXTERNAL_REPEATABILITY_REVIEW = "under-external-repeatability-review"
    EXTERNALLY_REVIEWED_WITH_BOUNDARIES = "externally-reviewed-with-boundaries"
    BLOCKED_BY_REPEATABILITY_FAILURE = "blocked-by-repeatability-failure"


SAFE_REPEATABILITY_OUTCOMES: tuple[WaveFiveRepeatabilityOutcome, ...] = (
    WaveFiveRepeatabilityOutcome.REPRODUCED,
    WaveFiveRepeatabilityOutcome.REPRODUCED_WITH_LIMITS,
)

BLOCKING_REPEATABILITY_OUTCOMES: tuple[WaveFiveRepeatabilityOutcome, ...] = (
    WaveFiveRepeatabilityOutcome.FAILED_TO_REPRODUCE,
    WaveFiveRepeatabilityOutcome.DISPUTED,
    WaveFiveRepeatabilityOutcome.NEEDS_MORE_EVIDENCE,
    WaveFiveRepeatabilityOutcome.BLOCKED_BY_PROTOCOL_GAP,
)

REQUIRED_REPEATABILITY_ATTEMPT_KINDS: tuple[
    WaveFiveRepeatabilityAttemptKind, ...
] = (
    WaveFiveRepeatabilityAttemptKind.CLEAN_CHECKOUT_REPLAY,
    WaveFiveRepeatabilityAttemptKind.INDEPENDENT_LAB_REPLAY,
    WaveFiveRepeatabilityAttemptKind.EXTERNAL_REVIEWER_REPLAY,
    WaveFiveRepeatabilityAttemptKind.CROSS_ENVIRONMENT_REPLAY,
    WaveFiveRepeatabilityAttemptKind.NEGATIVE_CONTROL_REPLAY,
    WaveFiveRepeatabilityAttemptKind.FAILED_REPRODUCTION_CAPTURE,
)

REQUIRED_DISAGREEMENT_KINDS: tuple[WaveFiveDisagreementKind, ...] = (
    WaveFiveDisagreementKind.PROTOCOL_INTERPRETATION,
    WaveFiveDisagreementKind.EVIDENCE_SUFFICIENCY,
    WaveFiveDisagreementKind.REPRODUCTION_VARIANCE,
    WaveFiveDisagreementKind.SAFETY_BOUNDARY,
    WaveFiveDisagreementKind.AUTHORITY_BOUNDARY,
    WaveFiveDisagreementKind.CLAIM_SCOPE,
    WaveFiveDisagreementKind.DONOR_REPO_COMPATIBILITY,
    WaveFiveDisagreementKind.WAVE_SIX_READINESS,
)

REQUIRED_REPEATABILITY_CONTROL_KINDS: tuple[
    WaveFiveRepeatabilityControlKind, ...
] = (
    WaveFiveRepeatabilityControlKind.FAILED_ATTEMPTS_RETAINED,
    WaveFiveRepeatabilityControlKind.DISAGREEMENTS_RETAINED,
    WaveFiveRepeatabilityControlKind.CONTRADICTORY_EVIDENCE_RETAINED,
    WaveFiveRepeatabilityControlKind.EXTERNAL_SOURCE_SEPARATION,
    WaveFiveRepeatabilityControlKind.PROTOCOL_VARIANCE_RECORDED,
    WaveFiveRepeatabilityControlKind.REVIEWER_DISSENT_VISIBLE,
    WaveFiveRepeatabilityControlKind.NO_CHERRY_PICKED_REPRODUCTION,
    WaveFiveRepeatabilityControlKind.WAVE_SIX_LIMITATION_VISIBLE,
)

EXTERNAL_REPEATABILITY_SOURCE_SYSTEMS: tuple[WaveFiveSourceSystem, ...] = (
    WaveFiveSourceSystem.EXTERNAL_REVIEW,
    WaveFiveSourceSystem.INDEPENDENT_REVIEWER,
    WaveFiveSourceSystem.INDEPENDENT_REPLICATION_LAB,
)


@dataclass(frozen=True, slots=True)
class WaveFiveRepeatabilityAttempt:
    """One repeatability attempt, successful or failed, preserved for review."""

    attempt_id: str
    attempt_kind: WaveFiveRepeatabilityAttemptKind
    outcome: WaveFiveRepeatabilityOutcome
    source_system: WaveFiveSourceSystem
    artifact_ids: tuple[str, ...]
    protocol_ids: tuple[str, ...]
    reviewer_ids: tuple[str, ...]
    environment_summary: str
    result_summary: str
    evidence_ids: tuple[str, ...]
    retained_failed_output: bool = True
    schema_version: str = WAVE_FIVE_REPEATABILITY_ATTEMPT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate repeatability-attempt evidence and source boundaries."""

        object.__setattr__(self, "attempt_id", _text(self.attempt_id, "attempt_id"))
        object.__setattr__(
            self, "artifact_ids", _unique_text(self.artifact_ids, label="artifact_id")
        )
        object.__setattr__(
            self, "protocol_ids", _unique_text(self.protocol_ids, label="protocol_id")
        )
        object.__setattr__(
            self, "reviewer_ids", _unique_text(self.reviewer_ids, label="reviewer_id")
        )
        object.__setattr__(
            self,
            "environment_summary",
            _text(self.environment_summary, "environment_summary"),
        )
        object.__setattr__(
            self, "result_summary", _text(self.result_summary, "result_summary")
        )
        object.__setattr__(
            self, "evidence_ids", _unique_text(self.evidence_ids, label="evidence_id")
        )
        if not self.artifact_ids:
            raise ValueError("Repeatability attempts require artifact ids.")
        if not self.protocol_ids:
            raise ValueError("Repeatability attempts require protocol ids.")
        if not self.evidence_ids:
            raise ValueError("Repeatability attempts require evidence ids.")
        if self.is_external_attempt:
            if not self.reviewer_ids:
                raise ValueError("External repeatability attempts require reviewers.")
        if self.outcome in BLOCKING_REPEATABILITY_OUTCOMES:
            if not self.retained_failed_output:
                raise ValueError("Failed or disputed repeatability must be retained.")
        object.__setattr__(
            self, "schema_version", _text(self.schema_version, "schema_version")
        )

    @property
    def attempt_key(self) -> str:
        """Return deterministic repeatability-attempt key."""

        return self.attempt_id

    @property
    def is_external_attempt(self) -> bool:
        """Return whether this attempt comes from an external source."""

        return self.source_system in EXTERNAL_REPEATABILITY_SOURCE_SYSTEMS

    @property
    def blocks_wave_five_progress(self) -> bool:
        """Return whether this attempt blocks repeatability readiness."""

        return self.outcome in BLOCKING_REPEATABILITY_OUTCOMES

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic export payload."""

        return {
            "artifact_ids": list(self.artifact_ids),
            "attempt_id": self.attempt_id,
            "attempt_kind": self.attempt_kind.value,
            "environment_summary": self.environment_summary,
            "evidence_ids": list(self.evidence_ids),
            "outcome": self.outcome.value,
            "protocol_ids": list(self.protocol_ids),
            "result_summary": self.result_summary,
            "retained_failed_output": self.retained_failed_output,
            "reviewer_ids": list(self.reviewer_ids),
            "schema_version": self.schema_version,
            "source_system": self.source_system.value,
        }


@dataclass(frozen=True, slots=True)
class WaveFiveReviewerDisagreement:
    """Reviewer disagreement or limitation that must not be erased."""

    disagreement_id: str
    disagreement_kind: WaveFiveDisagreementKind
    disposition: WaveFiveDisagreementDisposition
    reviewer_ids: tuple[str, ...]
    disputed_artifact_ids: tuple[str, ...]
    summary: str
    resolution_summary: str
    evidence_ids: tuple[str, ...]
    contradictory_evidence_ids: tuple[str, ...] = ()
    schema_version: str = WAVE_FIVE_DISAGREEMENT_ENTRY_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate disagreement visibility and evidence retention."""

        object.__setattr__(
            self, "disagreement_id", _text(self.disagreement_id, "disagreement_id")
        )
        object.__setattr__(
            self, "reviewer_ids", _unique_text(self.reviewer_ids, label="reviewer_id")
        )
        object.__setattr__(
            self,
            "disputed_artifact_ids",
            _unique_text(self.disputed_artifact_ids, label="disputed artifact_id"),
        )
        object.__setattr__(self, "summary", _text(self.summary, "summary"))
        object.__setattr__(
            self,
            "resolution_summary",
            _text(self.resolution_summary, "resolution_summary"),
        )
        object.__setattr__(
            self, "evidence_ids", _unique_text(self.evidence_ids, label="evidence_id")
        )
        object.__setattr__(
            self,
            "contradictory_evidence_ids",
            _unique_text(
                self.contradictory_evidence_ids,
                label="contradictory evidence_id",
            ),
        )
        if not self.reviewer_ids:
            raise ValueError("Reviewer disagreements require reviewer ids.")
        if not self.disputed_artifact_ids:
            raise ValueError("Reviewer disagreements require disputed artifacts.")
        if not self.evidence_ids:
            raise ValueError("Reviewer disagreements require evidence ids.")
        if self.disposition in {
            WaveFiveDisagreementDisposition.UNRESOLVED,
            WaveFiveDisagreementDisposition.BLOCKING,
        } and not self.contradictory_evidence_ids:
            raise ValueError(
                "Unresolved or blocking disagreements require contradictory evidence."
            )
        object.__setattr__(
            self, "schema_version", _text(self.schema_version, "schema_version")
        )

    @property
    def disagreement_key(self) -> str:
        """Return deterministic disagreement key."""

        return self.disagreement_id

    @property
    def blocks_wave_five_progress(self) -> bool:
        """Return whether this disagreement blocks repeatability readiness."""

        return self.disposition in {
            WaveFiveDisagreementDisposition.UNRESOLVED,
            WaveFiveDisagreementDisposition.BLOCKING,
        }

    @property
    def preserves_dissent(self) -> bool:
        """Return whether the disagreement remains evidence-visible."""

        return bool(self.reviewer_ids and self.evidence_ids)

    @property
    def all_evidence_ids(self) -> tuple[str, ...]:
        """Return regular and contradictory evidence ids."""

        return _dedupe_text((*self.evidence_ids, *self.contradictory_evidence_ids))

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic export payload."""

        return {
            "contradictory_evidence_ids": list(self.contradictory_evidence_ids),
            "disagreement_id": self.disagreement_id,
            "disagreement_kind": self.disagreement_kind.value,
            "disposition": self.disposition.value,
            "disputed_artifact_ids": list(self.disputed_artifact_ids),
            "evidence_ids": list(self.evidence_ids),
            "preserves_dissent": self.preserves_dissent,
            "resolution_summary": self.resolution_summary,
            "reviewer_ids": list(self.reviewer_ids),
            "schema_version": self.schema_version,
            "summary": self.summary,
        }


@dataclass(frozen=True, slots=True)
class WaveFiveRepeatabilityControl:
    """Control proving repeatability evidence was not cherry-picked."""

    control_id: str
    control_kind: WaveFiveRepeatabilityControlKind
    result: WaveFiveRepeatabilityControlResult
    description: str
    evidence_ids: tuple[str, ...]
    blocking: bool = True
    schema_version: str = WAVE_FIVE_REPEATABILITY_CONTROL_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate repeatability-control evidence."""

        object.__setattr__(self, "control_id", _text(self.control_id, "control_id"))
        object.__setattr__(self, "description", _text(self.description, "description"))
        object.__setattr__(
            self, "evidence_ids", _unique_text(self.evidence_ids, label="evidence_id")
        )
        if not self.evidence_ids:
            raise ValueError("Repeatability controls require evidence ids.")
        object.__setattr__(
            self, "schema_version", _text(self.schema_version, "schema_version")
        )

    @property
    def control_key(self) -> str:
        """Return deterministic repeatability-control key."""

        return self.control_id

    @property
    def passed_with_boundaries(self) -> bool:
        """Return whether this control passed while preserving limitations."""

        return self.result in {
            WaveFiveRepeatabilityControlResult.PASSED,
            WaveFiveRepeatabilityControlResult.PASSED_WITH_LIMITS,
        }

    @property
    def blocks_wave_five_progress(self) -> bool:
        """Return whether this control blocks repeatability readiness."""

        return self.blocking and not self.passed_with_boundaries

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic export payload."""

        return {
            "blocking": self.blocking,
            "control_id": self.control_id,
            "control_kind": self.control_kind.value,
            "description": self.description,
            "evidence_ids": list(self.evidence_ids),
            "result": self.result.value,
            "schema_version": self.schema_version,
        }


@dataclass(frozen=True, slots=True)
class WaveFiveRepeatabilityLedger:
    """Wave 5 ledger preserving repeatability, disagreement, and failed review."""

    ledger_id: str
    title: str
    source_system: WaveFiveSourceSystem
    ledger_state: WaveFiveRepeatabilityLedgerState
    attempts: tuple[WaveFiveRepeatabilityAttempt, ...]
    disagreements: tuple[WaveFiveReviewerDisagreement, ...]
    controls: tuple[WaveFiveRepeatabilityControl, ...]
    protocol_ids: tuple[str, ...]
    reviewer_ids: tuple[str, ...] = ()
    claim_boundaries: tuple[WaveFiveClaimBoundary, ...] = (
        WAVE_FIVE_REQUIRED_CLAIM_BOUNDARIES
    )
    notes: tuple[str, ...] = ()
    schema_version: str = WAVE_FIVE_REPEATABILITY_LEDGER_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate repeatability coverage and non-erasure controls."""

        object.__setattr__(self, "ledger_id", _text(self.ledger_id, "ledger_id"))
        object.__setattr__(self, "title", _text(self.title, "title"))
        attempts = tuple(sorted(self.attempts, key=lambda item: item.attempt_key))
        disagreements = tuple(
            sorted(self.disagreements, key=lambda item: item.disagreement_key)
        )
        controls = tuple(sorted(self.controls, key=lambda item: item.control_key))
        if not attempts:
            raise ValueError("Repeatability ledgers require attempts.")
        if not disagreements:
            raise ValueError("Repeatability ledgers require disagreement entries.")
        if not controls:
            raise ValueError("Repeatability ledgers require controls.")
        _unique_values((item.attempt_id for item in attempts), label="attempt_id")
        _unique_values(
            (item.disagreement_id for item in disagreements),
            label="disagreement_id",
        )
        _unique_values((item.control_id for item in controls), label="control_id")
        object.__setattr__(self, "attempts", attempts)
        object.__setattr__(self, "disagreements", disagreements)
        object.__setattr__(self, "controls", controls)
        object.__setattr__(
            self, "protocol_ids", _unique_text(self.protocol_ids, label="protocol_id")
        )
        if not self.protocol_ids:
            raise ValueError("Repeatability ledgers require protocol ids.")
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
                "Repeatability ledgers must preserve claim boundary: "
                f"{missing_boundaries[0].value}"
            )
        object.__setattr__(self, "notes", _unique_text(self.notes, label="note"))
        object.__setattr__(
            self, "schema_version", _text(self.schema_version, "schema_version")
        )
        if self.externally_reviewed_with_boundaries:
            if self.source_system not in EXTERNAL_REPEATABILITY_SOURCE_SYSTEMS:
                raise ValueError(
                    "Externally reviewed repeatability ledgers require external source."
                )
            if not self.reviewer_ids:
                raise ValueError(
                    "Externally reviewed repeatability ledgers require reviewer ids."
                )
            if self.blocks_repeatability_readiness:
                raise ValueError(
                    "Externally reviewed repeatability ledgers cannot contain blockers."
                )

    @property
    def covered_attempt_kinds(self) -> tuple[WaveFiveRepeatabilityAttemptKind, ...]:
        """Return repeatability-attempt kinds represented in this ledger."""

        kinds: list[WaveFiveRepeatabilityAttemptKind] = []
        seen: set[WaveFiveRepeatabilityAttemptKind] = set()
        for attempt in self.attempts:
            if attempt.attempt_kind not in seen:
                kinds.append(attempt.attempt_kind)
                seen.add(attempt.attempt_kind)
        return tuple(kinds)

    @property
    def missing_required_attempt_kinds(
        self,
    ) -> tuple[WaveFiveRepeatabilityAttemptKind, ...]:
        """Return required attempt kinds absent from this ledger."""

        covered = set(self.covered_attempt_kinds)
        return tuple(
            kind for kind in REQUIRED_REPEATABILITY_ATTEMPT_KINDS if kind not in covered
        )

    @property
    def covered_disagreement_kinds(self) -> tuple[WaveFiveDisagreementKind, ...]:
        """Return disagreement kinds represented in this ledger."""

        kinds: list[WaveFiveDisagreementKind] = []
        seen: set[WaveFiveDisagreementKind] = set()
        for disagreement in self.disagreements:
            if disagreement.disagreement_kind not in seen:
                kinds.append(disagreement.disagreement_kind)
                seen.add(disagreement.disagreement_kind)
        return tuple(kinds)

    @property
    def missing_required_disagreement_kinds(
        self,
    ) -> tuple[WaveFiveDisagreementKind, ...]:
        """Return required disagreement kinds absent from this ledger."""

        covered = set(self.covered_disagreement_kinds)
        return tuple(
            kind for kind in REQUIRED_DISAGREEMENT_KINDS if kind not in covered
        )

    @property
    def covered_control_kinds(self) -> tuple[WaveFiveRepeatabilityControlKind, ...]:
        """Return repeatability-control kinds represented in this ledger."""

        kinds: list[WaveFiveRepeatabilityControlKind] = []
        seen: set[WaveFiveRepeatabilityControlKind] = set()
        for control in self.controls:
            if control.control_kind not in seen:
                kinds.append(control.control_kind)
                seen.add(control.control_kind)
        return tuple(kinds)

    @property
    def missing_required_control_kinds(
        self,
    ) -> tuple[WaveFiveRepeatabilityControlKind, ...]:
        """Return required repeatability controls absent from this ledger."""

        covered = set(self.covered_control_kinds)
        return tuple(
            kind for kind in REQUIRED_REPEATABILITY_CONTROL_KINDS if kind not in covered
        )

    @property
    def blocking_attempt_ids(self) -> tuple[str, ...]:
        """Return repeatability attempts that block Wave 5 progress."""

        return tuple(
            attempt.attempt_id
            for attempt in self.attempts
            if attempt.blocks_wave_five_progress
        )

    @property
    def blocking_disagreement_ids(self) -> tuple[str, ...]:
        """Return reviewer disagreements that block Wave 5 progress."""

        return tuple(
            disagreement.disagreement_id
            for disagreement in self.disagreements
            if disagreement.blocks_wave_five_progress
        )

    @property
    def blocking_control_ids(self) -> tuple[str, ...]:
        """Return repeatability controls that block Wave 5 progress."""

        return tuple(
            control.control_id
            for control in self.controls
            if control.blocks_wave_five_progress
        )

    @property
    def has_external_attempt(self) -> bool:
        """Return whether at least one repeatability attempt is external."""

        return any(attempt.is_external_attempt for attempt in self.attempts)

    @property
    def has_required_attempt_coverage(self) -> bool:
        """Return whether every locked attempt kind is represented."""

        return not self.missing_required_attempt_kinds

    @property
    def has_required_disagreement_coverage(self) -> bool:
        """Return whether every locked disagreement kind is represented."""

        return not self.missing_required_disagreement_kinds

    @property
    def has_required_control_coverage(self) -> bool:
        """Return whether every locked repeatability control is represented."""

        return not self.missing_required_control_kinds

    @property
    def blocks_repeatability_readiness(self) -> bool:
        """Return whether any ledger entry blocks repeatability readiness."""

        return bool(
            self.blocking_attempt_ids
            or self.blocking_disagreement_ids
            or self.blocking_control_ids
        )

    @property
    def ready_for_external_repeatability_review(self) -> bool:
        """Return whether ledger can enter external repeatability review."""

        return (
            self.ledger_state
            in {
                WaveFiveRepeatabilityLedgerState.INTERNAL_LEDGER_READY,
                (
                    WaveFiveRepeatabilityLedgerState.
                    READY_FOR_EXTERNAL_REPEATABILITY_REVIEW
                ),
                WaveFiveRepeatabilityLedgerState.UNDER_EXTERNAL_REPEATABILITY_REVIEW,
            }
            and self.has_external_attempt
            and self.has_required_attempt_coverage
            and self.has_required_disagreement_coverage
            and self.has_required_control_coverage
            and not self.blocks_repeatability_readiness
        )

    @property
    def externally_reviewed_with_boundaries(self) -> bool:
        """Return whether external repeatability review accepted boundaries."""

        return (
            self.ledger_state
            is WaveFiveRepeatabilityLedgerState.EXTERNALLY_REVIEWED_WITH_BOUNDARIES
        )

    @property
    def all_evidence_ids(self) -> tuple[str, ...]:
        """Return all evidence ids bound into this ledger."""

        evidence_ids: list[str] = []
        seen: set[str] = set()
        for evidence_id in self._iter_evidence_ids():
            if evidence_id not in seen:
                evidence_ids.append(evidence_id)
                seen.add(evidence_id)
        return tuple(evidence_ids)

    def to_artifact_ref(self) -> WaveFiveArtifactRef:
        """Return this ledger as a Wave 5 repeatability artifact."""

        decision = WaveFiveArtifactDecision.NEEDS_EXTERNAL_EVIDENCE
        status = WaveFiveValidationStatus.MISSING_EXTERNAL_EVIDENCE
        authority = WaveFiveAuthorityState.HUMAN_REVIEW_REQUIRED
        if self.externally_reviewed_with_boundaries:
            decision = WaveFiveArtifactDecision.EXTERNALLY_REVIEWED
            status = WaveFiveValidationStatus.ACCEPTED_WITH_BOUNDARIES
        elif self.ready_for_external_repeatability_review:
            decision = WaveFiveArtifactDecision.READY_FOR_INDEPENDENT_REVIEW
            status = WaveFiveValidationStatus.UNDER_INDEPENDENT_REVIEW
        elif self.blocks_repeatability_readiness:
            decision = WaveFiveArtifactDecision.BLOCKED
            status = WaveFiveValidationStatus.REJECTED
            authority = WaveFiveAuthorityState.BLOCKED
        return WaveFiveArtifactRef(
            artifact_id=self.ledger_id,
            kind=WaveFiveArtifactKind.REPEATABILITY_LEDGER,
            capability_area=WaveFiveCapabilityArea.REPRODUCIBILITY,
            source_system=self.source_system,
            summary=self.title,
            produced_by_engine_id="wave5-repeatability-ledger-engine",
            produced_by_agent_role_id="repeatability-reviewer",
            evidence_ids=self.all_evidence_ids,
            decision=decision,
            authority_state=authority,
            validation_status=status,
            claim_boundaries=self.claim_boundaries,
        )

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic export payload."""

        return {
            "attempts": [attempt.canonical_payload() for attempt in self.attempts],
            "claim_boundaries": [boundary.value for boundary in self.claim_boundaries],
            "controls": [control.canonical_payload() for control in self.controls],
            "disagreements": [
                disagreement.canonical_payload()
                for disagreement in self.disagreements
            ],
            "ledger_id": self.ledger_id,
            "ledger_state": self.ledger_state.value,
            "notes": list(self.notes),
            "protocol_ids": list(self.protocol_ids),
            "reviewer_ids": list(self.reviewer_ids),
            "schema_version": self.schema_version,
            "source_system": self.source_system.value,
            "title": self.title,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this ledger."""

        return _stable_sha256(self.canonical_payload())

    def _iter_evidence_ids(self) -> Iterable[str]:
        """Yield evidence ids in deterministic ledger traversal order."""

        for attempt in self.attempts:
            yield from attempt.evidence_ids
        for disagreement in self.disagreements:
            yield from disagreement.all_evidence_ids
        for control in self.controls:
            yield from control.evidence_ids


def required_repeatability_attempt_kinds() -> tuple[
    WaveFiveRepeatabilityAttemptKind, ...
]:
    """Return locked repeatability attempt kinds required for Wave 5."""

    return REQUIRED_REPEATABILITY_ATTEMPT_KINDS


def required_disagreement_kinds() -> tuple[WaveFiveDisagreementKind, ...]:
    """Return locked disagreement kinds required for Wave 5 visibility."""

    return REQUIRED_DISAGREEMENT_KINDS


def required_repeatability_control_kinds() -> tuple[
    WaveFiveRepeatabilityControlKind, ...
]:
    """Return locked non-erasure controls required for Wave 5."""

    return REQUIRED_REPEATABILITY_CONTROL_KINDS


def safe_repeatability_outcomes() -> tuple[WaveFiveRepeatabilityOutcome, ...]:
    """Return repeatability outcomes that do not block readiness."""

    return SAFE_REPEATABILITY_OUTCOMES


def blocking_repeatability_outcomes() -> tuple[WaveFiveRepeatabilityOutcome, ...]:
    """Return repeatability outcomes that block Wave 5 progress."""

    return BLOCKING_REPEATABILITY_OUTCOMES


def external_repeatability_source_systems() -> tuple[WaveFiveSourceSystem, ...]:
    """Return source systems allowed to assert external repeatability."""

    return EXTERNAL_REPEATABILITY_SOURCE_SYSTEMS


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


def _dedupe_text(values: Iterable[str]) -> tuple[str, ...]:
    """Return de-duplicated text values in input order."""

    deduped: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value not in seen:
            deduped.append(value)
            seen.add(value)
    return tuple(deduped)


def _stable_sha256(payload: Mapping[str, Any]) -> str:
    """Return deterministic SHA-256 over a canonical JSON payload."""

    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return hashlib.sha256(encoded).hexdigest()
