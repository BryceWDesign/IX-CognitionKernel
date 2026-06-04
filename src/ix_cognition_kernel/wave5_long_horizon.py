"""Wave 5 long-horizon task validation records.

Wave 5 cannot be a credible bridge into Wave 6 if evidence only covers short,
friendly, one-shot tasks. This module records long-horizon validation evidence:
ordered task phases, mission-state snapshots, continuity observations, explicit
failure criteria, rollback expectations, and external-review boundaries. The
records preserve uncertainty, human authority, and no-AGI/no-production/no-
certification claim boundaries.
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

WAVE_FIVE_LONG_HORIZON_PHASE_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave5-long-horizon-phase-v1"
)
WAVE_FIVE_MISSION_STATE_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave5-mission-state-snapshot-v1"
)
WAVE_FIVE_LONG_HORIZON_OBSERVATION_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave5-long-horizon-observation-v1"
)
WAVE_FIVE_LONG_HORIZON_FAILURE_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave5-long-horizon-failure-v1"
)
WAVE_FIVE_LONG_HORIZON_RECORD_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave5-long-horizon-record-v1"
)


class WaveFiveLongHorizonPhaseKind(StrEnum):
    """Required long-horizon task phases before Wave 5 review."""

    MISSION_INTAKE = "mission-intake"
    PLAN_FORMATION = "plan-formation"
    TOOL_OR_EVIDENCE_SELECTION = "tool-or-evidence-selection"
    MIDCOURSE_REVISION = "midcourse-revision"
    ADVERSARIAL_INTERRUPTION = "adversarial-interruption"
    RECOVERY_OR_ROLLBACK = "recovery-or-rollback"
    FINAL_EVIDENCE_SYNTHESIS = "final-evidence-synthesis"


class WaveFiveMissionStateElement(StrEnum):
    """Mission-state elements that must survive a long-horizon task."""

    USER_OBJECTIVE = "user-objective"
    AUTHORITY_BOUNDARY = "authority-boundary"
    ACTIVE_CONSTRAINTS = "active-constraints"
    UNCERTAINTY_STATE = "uncertainty-state"
    EVIDENCE_REQUIREMENTS = "evidence-requirements"
    ROLLBACK_PATH = "rollback-path"
    CLAIM_BOUNDARIES = "claim-boundaries"


class WaveFiveLongHorizonOutcome(StrEnum):
    """Observed outcome for one long-horizon phase."""

    COMPLETED_WITH_EVIDENCE = "completed-with-evidence"
    REVISED_WITH_EVIDENCE = "revised-with-evidence"
    ESCALATED_TO_HUMAN_REVIEW = "escalated-to-human-review"
    SAFE_ROLLBACK = "safe-rollback"
    NEEDS_MORE_EVIDENCE = "needs-more-evidence"
    FAILED_CONTINUITY = "failed-continuity"
    FAILED_AUTHORITY = "failed-authority"


class WaveFiveLongHorizonFailureKind(StrEnum):
    """Failure modes that can block long-horizon validation."""

    LOST_USER_OBJECTIVE = "lost-user-objective"
    LOST_AUTHORITY_BOUNDARY = "lost-authority-boundary"
    HIDDEN_UNCERTAINTY = "hidden-uncertainty"
    UNSUPPORTED_CLAIM = "unsupported-claim"
    UNSAFE_TOOL_HANDOFF = "unsafe-tool-handoff"
    IRREVERSIBLE_ACTION = "irreversible-action"
    EVIDENCE_CHAIN_BREAK = "evidence-chain-break"


class WaveFiveLongHorizonReviewState(StrEnum):
    """Review state of a long-horizon task record."""

    INTERNAL_REPLAY_READY = "internal-replay-ready"
    READY_FOR_EXTERNAL_LONG_HORIZON_REVIEW = (
        "ready-for-external-long-horizon-review"
    )
    UNDER_EXTERNAL_LONG_HORIZON_REVIEW = "under-external-long-horizon-review"
    EXTERNALLY_REVIEWED_WITH_BOUNDARIES = "externally-reviewed-with-boundaries"
    BLOCKED_BY_LONG_HORIZON_FAILURE = "blocked-by-long-horizon-failure"


SAFE_LONG_HORIZON_OUTCOMES: tuple[WaveFiveLongHorizonOutcome, ...] = (
    WaveFiveLongHorizonOutcome.COMPLETED_WITH_EVIDENCE,
    WaveFiveLongHorizonOutcome.REVISED_WITH_EVIDENCE,
    WaveFiveLongHorizonOutcome.ESCALATED_TO_HUMAN_REVIEW,
    WaveFiveLongHorizonOutcome.SAFE_ROLLBACK,
)

REQUIRED_LONG_HORIZON_PHASE_KINDS: tuple[WaveFiveLongHorizonPhaseKind, ...] = (
    WaveFiveLongHorizonPhaseKind.MISSION_INTAKE,
    WaveFiveLongHorizonPhaseKind.PLAN_FORMATION,
    WaveFiveLongHorizonPhaseKind.TOOL_OR_EVIDENCE_SELECTION,
    WaveFiveLongHorizonPhaseKind.MIDCOURSE_REVISION,
    WaveFiveLongHorizonPhaseKind.ADVERSARIAL_INTERRUPTION,
    WaveFiveLongHorizonPhaseKind.RECOVERY_OR_ROLLBACK,
    WaveFiveLongHorizonPhaseKind.FINAL_EVIDENCE_SYNTHESIS,
)

REQUIRED_MISSION_STATE_ELEMENTS: tuple[WaveFiveMissionStateElement, ...] = (
    WaveFiveMissionStateElement.USER_OBJECTIVE,
    WaveFiveMissionStateElement.AUTHORITY_BOUNDARY,
    WaveFiveMissionStateElement.ACTIVE_CONSTRAINTS,
    WaveFiveMissionStateElement.UNCERTAINTY_STATE,
    WaveFiveMissionStateElement.EVIDENCE_REQUIREMENTS,
    WaveFiveMissionStateElement.ROLLBACK_PATH,
    WaveFiveMissionStateElement.CLAIM_BOUNDARIES,
)

EXTERNAL_LONG_HORIZON_SOURCE_SYSTEMS: tuple[WaveFiveSourceSystem, ...] = (
    WaveFiveSourceSystem.EXTERNAL_REVIEW,
    WaveFiveSourceSystem.INDEPENDENT_REVIEWER,
    WaveFiveSourceSystem.INDEPENDENT_REPLICATION_LAB,
)


@dataclass(frozen=True, slots=True)
class WaveFiveLongHorizonPhase:
    """One ordered phase in a long-horizon validation task."""

    phase_id: str
    phase_kind: WaveFiveLongHorizonPhaseKind
    sequence_index: int
    objective: str
    expected_state_elements: tuple[WaveFiveMissionStateElement, ...]
    rollback_plan: str
    evidence_ids: tuple[str, ...]
    schema_version: str = WAVE_FIVE_LONG_HORIZON_PHASE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate long-horizon phase metadata."""

        object.__setattr__(self, "phase_id", _text(self.phase_id, "phase_id"))
        if self.sequence_index < 0:
            raise ValueError("Long-horizon phase sequence_index must be non-negative.")
        object.__setattr__(self, "objective", _text(self.objective, "objective"))
        object.__setattr__(
            self,
            "expected_state_elements",
            _unique_enum(
                self.expected_state_elements, label="expected state element"
            ),
        )
        if not self.expected_state_elements:
            raise ValueError("Long-horizon phases require expected state elements.")
        object.__setattr__(
            self, "rollback_plan", _text(self.rollback_plan, "rollback_plan")
        )
        object.__setattr__(
            self, "evidence_ids", _unique_text(self.evidence_ids, label="evidence_id")
        )
        if not self.evidence_ids:
            raise ValueError("Long-horizon phases require evidence ids.")
        object.__setattr__(
            self, "schema_version", _text(self.schema_version, "schema_version")
        )

    @property
    def phase_key(self) -> tuple[int, str]:
        """Return deterministic phase sort key."""

        return (self.sequence_index, self.phase_id)

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic export payload."""

        return {
            "evidence_ids": list(self.evidence_ids),
            "expected_state_elements": [
                element.value for element in self.expected_state_elements
            ],
            "objective": self.objective,
            "phase_id": self.phase_id,
            "phase_kind": self.phase_kind.value,
            "rollback_plan": self.rollback_plan,
            "schema_version": self.schema_version,
            "sequence_index": self.sequence_index,
        }


@dataclass(frozen=True, slots=True)
class WaveFiveMissionStateSnapshot:
    """Mission-state snapshot captured during a long-horizon task."""

    snapshot_id: str
    phase_id: str
    preserved_elements: tuple[WaveFiveMissionStateElement, ...]
    active_goal_summary: str
    active_constraint_summary: str
    uncertainty_summary: str
    authority_boundary_summary: str
    evidence_ids: tuple[str, ...]
    schema_version: str = WAVE_FIVE_MISSION_STATE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate mission-state continuity metadata."""

        object.__setattr__(self, "snapshot_id", _text(self.snapshot_id, "snapshot_id"))
        object.__setattr__(self, "phase_id", _text(self.phase_id, "phase_id"))
        object.__setattr__(
            self,
            "preserved_elements",
            _unique_enum(self.preserved_elements, label="preserved element"),
        )
        if not self.preserved_elements:
            raise ValueError("Mission-state snapshots require preserved elements.")
        object.__setattr__(
            self,
            "active_goal_summary",
            _text(self.active_goal_summary, "active_goal_summary"),
        )
        object.__setattr__(
            self,
            "active_constraint_summary",
            _text(self.active_constraint_summary, "active_constraint_summary"),
        )
        object.__setattr__(
            self,
            "uncertainty_summary",
            _text(self.uncertainty_summary, "uncertainty_summary"),
        )
        object.__setattr__(
            self,
            "authority_boundary_summary",
            _text(self.authority_boundary_summary, "authority_boundary_summary"),
        )
        object.__setattr__(
            self, "evidence_ids", _unique_text(self.evidence_ids, label="evidence_id")
        )
        if not self.evidence_ids:
            raise ValueError("Mission-state snapshots require evidence ids.")
        object.__setattr__(
            self, "schema_version", _text(self.schema_version, "schema_version")
        )

    @property
    def snapshot_key(self) -> str:
        """Return deterministic snapshot key."""

        return self.snapshot_id

    @property
    def missing_required_elements(self) -> tuple[WaveFiveMissionStateElement, ...]:
        """Return required mission-state elements absent from this snapshot."""

        present = set(self.preserved_elements)
        return tuple(
            element
            for element in REQUIRED_MISSION_STATE_ELEMENTS
            if element not in present
        )

    @property
    def preserves_required_state(self) -> bool:
        """Return whether every required mission-state element is preserved."""

        return not self.missing_required_elements

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic export payload."""

        return {
            "active_constraint_summary": self.active_constraint_summary,
            "active_goal_summary": self.active_goal_summary,
            "authority_boundary_summary": self.authority_boundary_summary,
            "evidence_ids": list(self.evidence_ids),
            "phase_id": self.phase_id,
            "preserved_elements": [
                element.value for element in self.preserved_elements
            ],
            "schema_version": self.schema_version,
            "snapshot_id": self.snapshot_id,
            "uncertainty_summary": self.uncertainty_summary,
        }


@dataclass(frozen=True, slots=True)
class WaveFiveLongHorizonObservation:
    """Observed continuity behavior for one long-horizon phase."""

    observation_id: str
    phase_id: str
    outcome: WaveFiveLongHorizonOutcome
    observed_transition: str
    prediction_delta_summary: str
    preserved_mission_continuity: bool
    preserved_human_authority: bool
    preserved_uncertainty: bool
    evidence_ids: tuple[str, ...]
    schema_version: str = WAVE_FIVE_LONG_HORIZON_OBSERVATION_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate observed phase continuity."""

        object.__setattr__(
            self, "observation_id", _text(self.observation_id, "observation_id")
        )
        object.__setattr__(self, "phase_id", _text(self.phase_id, "phase_id"))
        object.__setattr__(
            self,
            "observed_transition",
            _text(self.observed_transition, "observed_transition"),
        )
        object.__setattr__(
            self,
            "prediction_delta_summary",
            _text(self.prediction_delta_summary, "prediction_delta_summary"),
        )
        object.__setattr__(
            self, "evidence_ids", _unique_text(self.evidence_ids, label="evidence_id")
        )
        if not self.evidence_ids:
            raise ValueError("Long-horizon observations require evidence ids.")
        if self.is_safe_outcome:
            if not self.preserved_mission_continuity:
                raise ValueError("Safe long-horizon outcomes must preserve continuity.")
            if not self.preserved_human_authority:
                raise ValueError("Safe long-horizon outcomes must preserve authority.")
            if not self.preserved_uncertainty:
                raise ValueError(
                    "Safe long-horizon outcomes must preserve uncertainty."
                )
        object.__setattr__(
            self, "schema_version", _text(self.schema_version, "schema_version")
        )

    @property
    def observation_key(self) -> str:
        """Return deterministic observation key."""

        return self.observation_id

    @property
    def is_safe_outcome(self) -> bool:
        """Return whether this observation is long-horizon safe."""

        return self.outcome in SAFE_LONG_HORIZON_OUTCOMES

    @property
    def blocks_wave_five_progress(self) -> bool:
        """Return whether this observation blocks long-horizon readiness."""

        return self.outcome in {
            WaveFiveLongHorizonOutcome.NEEDS_MORE_EVIDENCE,
            WaveFiveLongHorizonOutcome.FAILED_CONTINUITY,
            WaveFiveLongHorizonOutcome.FAILED_AUTHORITY,
        }

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic export payload."""

        return {
            "evidence_ids": list(self.evidence_ids),
            "observation_id": self.observation_id,
            "observed_transition": self.observed_transition,
            "outcome": self.outcome.value,
            "phase_id": self.phase_id,
            "prediction_delta_summary": self.prediction_delta_summary,
            "preserved_human_authority": self.preserved_human_authority,
            "preserved_mission_continuity": self.preserved_mission_continuity,
            "preserved_uncertainty": self.preserved_uncertainty,
            "schema_version": self.schema_version,
        }


@dataclass(frozen=True, slots=True)
class WaveFiveLongHorizonFailureCriterion:
    """Explicit failure criterion for a long-horizon task."""

    criterion_id: str
    failure_kind: WaveFiveLongHorizonFailureKind
    description: str
    triggered: bool
    blocking: bool
    mitigation: str
    evidence_ids: tuple[str, ...]
    schema_version: str = WAVE_FIVE_LONG_HORIZON_FAILURE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate failure criterion metadata."""

        object.__setattr__(
            self, "criterion_id", _text(self.criterion_id, "criterion_id")
        )
        object.__setattr__(self, "description", _text(self.description, "description"))
        object.__setattr__(self, "mitigation", _text(self.mitigation, "mitigation"))
        object.__setattr__(
            self, "evidence_ids", _unique_text(self.evidence_ids, label="evidence_id")
        )
        if self.triggered and not self.evidence_ids:
            raise ValueError("Triggered long-horizon failures require evidence ids.")
        object.__setattr__(
            self, "schema_version", _text(self.schema_version, "schema_version")
        )

    @property
    def criterion_key(self) -> str:
        """Return deterministic failure-criterion key."""

        return self.criterion_id

    @property
    def blocks_wave_five_progress(self) -> bool:
        """Return whether this criterion blocks long-horizon readiness."""

        return self.triggered and self.blocking

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic export payload."""

        return {
            "blocking": self.blocking,
            "criterion_id": self.criterion_id,
            "description": self.description,
            "evidence_ids": list(self.evidence_ids),
            "failure_kind": self.failure_kind.value,
            "mitigation": self.mitigation,
            "schema_version": self.schema_version,
            "triggered": self.triggered,
        }


@dataclass(frozen=True, slots=True)
class WaveFiveLongHorizonTaskRecord:
    """Long-horizon task evidence record for Wave 5 review."""

    record_id: str
    title: str
    source_system: WaveFiveSourceSystem
    review_state: WaveFiveLongHorizonReviewState
    phases: tuple[WaveFiveLongHorizonPhase, ...]
    mission_snapshots: tuple[WaveFiveMissionStateSnapshot, ...]
    observations: tuple[WaveFiveLongHorizonObservation, ...]
    failure_criteria: tuple[WaveFiveLongHorizonFailureCriterion, ...]
    protocol_ids: tuple[str, ...]
    reviewer_ids: tuple[str, ...] = ()
    claim_boundaries: tuple[WaveFiveClaimBoundary, ...] = (
        WAVE_FIVE_REQUIRED_CLAIM_BOUNDARIES
    )
    notes: tuple[str, ...] = ()
    schema_version: str = WAVE_FIVE_LONG_HORIZON_RECORD_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate long-horizon coverage, continuity, and review state."""

        object.__setattr__(self, "record_id", _text(self.record_id, "record_id"))
        object.__setattr__(self, "title", _text(self.title, "title"))
        phases = tuple(sorted(self.phases, key=lambda item: item.phase_key))
        snapshots = tuple(
            sorted(self.mission_snapshots, key=lambda item: item.snapshot_key)
        )
        observations = tuple(
            sorted(self.observations, key=lambda item: item.observation_key)
        )
        failures = tuple(
            sorted(self.failure_criteria, key=lambda item: item.criterion_key)
        )
        if not phases:
            raise ValueError("Long-horizon task records require phases.")
        if not snapshots:
            raise ValueError("Long-horizon task records require mission snapshots.")
        if not observations:
            raise ValueError("Long-horizon task records require observations.")
        if not failures:
            raise ValueError("Long-horizon task records require failure criteria.")
        phase_ids = _unique_values((item.phase_id for item in phases), label="phase_id")
        _unique_values((item.sequence_index for item in phases), label="sequence_index")
        _unique_values((item.snapshot_id for item in snapshots), label="snapshot_id")
        _unique_values(
            (item.observation_id for item in observations), label="observation_id"
        )
        _unique_values((item.criterion_id for item in failures), label="criterion_id")
        self._validate_phase_references(phase_ids, snapshots, observations)
        self._validate_phase_contiguity(phases)
        object.__setattr__(self, "phases", phases)
        object.__setattr__(self, "mission_snapshots", snapshots)
        object.__setattr__(self, "observations", observations)
        object.__setattr__(self, "failure_criteria", failures)
        object.__setattr__(
            self, "protocol_ids", _unique_text(self.protocol_ids, label="protocol_id")
        )
        if not self.protocol_ids:
            raise ValueError("Long-horizon task records require protocol ids.")
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
                "Long-horizon records must preserve claim boundary: "
                f"{missing_boundaries[0].value}"
            )
        object.__setattr__(
            self, "notes", _unique_text(self.notes, label="long-horizon note")
        )
        object.__setattr__(
            self, "schema_version", _text(self.schema_version, "schema_version")
        )
        if self.externally_reviewed_with_boundaries:
            if self.source_system not in EXTERNAL_LONG_HORIZON_SOURCE_SYSTEMS:
                raise ValueError(
                    "Externally reviewed long-horizon records require external source."
                )
            if not self.reviewer_ids:
                raise ValueError(
                    "Externally reviewed long-horizon records require reviewer ids."
                )
            if self.blocking_observation_ids or self.blocking_failure_ids:
                raise ValueError(
                    "Externally reviewed long-horizon records cannot contain blockers."
                )

    @property
    def phase_ids(self) -> tuple[str, ...]:
        """Return phase ids in deterministic sequence order."""

        return tuple(item.phase_id for item in self.phases)

    @property
    def covered_phase_kinds(self) -> tuple[WaveFiveLongHorizonPhaseKind, ...]:
        """Return phase kinds covered by this record."""

        kinds: list[WaveFiveLongHorizonPhaseKind] = []
        seen: set[WaveFiveLongHorizonPhaseKind] = set()
        for phase in self.phases:
            if phase.phase_kind not in seen:
                kinds.append(phase.phase_kind)
                seen.add(phase.phase_kind)
        return tuple(kinds)

    @property
    def missing_required_phase_kinds(self) -> tuple[WaveFiveLongHorizonPhaseKind, ...]:
        """Return required long-horizon phases absent from this record."""

        covered = set(self.covered_phase_kinds)
        return tuple(
            phase_kind
            for phase_kind in REQUIRED_LONG_HORIZON_PHASE_KINDS
            if phase_kind not in covered
        )

    @property
    def has_required_phase_coverage(self) -> bool:
        """Return whether every locked long-horizon phase kind is covered."""

        return not self.missing_required_phase_kinds

    @property
    def snapshot_ids_missing_required_state(self) -> tuple[str, ...]:
        """Return snapshot ids missing required mission-state elements."""

        return tuple(
            snapshot.snapshot_id
            for snapshot in self.mission_snapshots
            if not snapshot.preserves_required_state
        )

    @property
    def blocking_observation_ids(self) -> tuple[str, ...]:
        """Return observations that block long-horizon readiness."""

        return tuple(
            observation.observation_id
            for observation in self.observations
            if observation.blocks_wave_five_progress
        )

    @property
    def blocking_failure_ids(self) -> tuple[str, ...]:
        """Return triggered blocking failure criteria."""

        return tuple(
            criterion.criterion_id
            for criterion in self.failure_criteria
            if criterion.blocks_wave_five_progress
        )

    @property
    def preserves_mission_continuity(self) -> bool:
        """Return whether all observations preserve mission continuity."""

        return all(
            observation.preserved_mission_continuity
            for observation in self.observations
        )

    @property
    def preserves_human_authority(self) -> bool:
        """Return whether all observations preserve human authority."""

        return all(
            observation.preserved_human_authority for observation in self.observations
        )

    @property
    def preserves_uncertainty(self) -> bool:
        """Return whether all observations preserve uncertainty."""

        return all(
            observation.preserved_uncertainty for observation in self.observations
        )

    @property
    def ready_for_external_long_horizon_review(self) -> bool:
        """Return whether the record can enter external long-horizon review."""

        return (
            self.review_state
            in {
                WaveFiveLongHorizonReviewState.INTERNAL_REPLAY_READY,
                WaveFiveLongHorizonReviewState.READY_FOR_EXTERNAL_LONG_HORIZON_REVIEW,
                WaveFiveLongHorizonReviewState.UNDER_EXTERNAL_LONG_HORIZON_REVIEW,
            }
            and self.has_required_phase_coverage
            and not self.snapshot_ids_missing_required_state
            and not self.blocking_observation_ids
            and not self.blocking_failure_ids
            and self.preserves_mission_continuity
            and self.preserves_human_authority
            and self.preserves_uncertainty
        )

    @property
    def externally_reviewed_with_boundaries(self) -> bool:
        """Return whether external long-horizon review accepted boundaries."""

        return (
            self.review_state
            is WaveFiveLongHorizonReviewState.EXTERNALLY_REVIEWED_WITH_BOUNDARIES
        )

    @property
    def all_evidence_ids(self) -> tuple[str, ...]:
        """Return all evidence ids bound into this record."""

        evidence_ids: list[str] = []
        seen: set[str] = set()
        for evidence_id in self._iter_evidence_ids():
            if evidence_id not in seen:
                evidence_ids.append(evidence_id)
                seen.add(evidence_id)
        return tuple(evidence_ids)

    def to_artifact_ref(self) -> WaveFiveArtifactRef:
        """Return this record as a Wave 5 long-horizon artifact."""

        decision = WaveFiveArtifactDecision.NEEDS_EXTERNAL_EVIDENCE
        status = WaveFiveValidationStatus.MISSING_EXTERNAL_EVIDENCE
        authority = WaveFiveAuthorityState.HUMAN_REVIEW_REQUIRED
        if self.externally_reviewed_with_boundaries:
            decision = WaveFiveArtifactDecision.EXTERNALLY_REVIEWED
            status = WaveFiveValidationStatus.ACCEPTED_WITH_BOUNDARIES
        elif self.ready_for_external_long_horizon_review:
            decision = WaveFiveArtifactDecision.READY_FOR_INDEPENDENT_REVIEW
            status = WaveFiveValidationStatus.UNDER_INDEPENDENT_REVIEW
        elif self.blocking_observation_ids or self.blocking_failure_ids:
            decision = WaveFiveArtifactDecision.BLOCKED
            status = WaveFiveValidationStatus.REJECTED
            authority = WaveFiveAuthorityState.BLOCKED
        return WaveFiveArtifactRef(
            artifact_id=self.record_id,
            kind=WaveFiveArtifactKind.LONG_HORIZON_TASK_RECORD,
            capability_area=WaveFiveCapabilityArea.LONG_HORIZON_VALIDATION,
            source_system=self.source_system,
            summary=self.title,
            produced_by_engine_id="wave5-long-horizon-validation-engine",
            produced_by_agent_role_id="long-horizon-reviewer",
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
            "failure_criteria": [
                criterion.canonical_payload() for criterion in self.failure_criteria
            ],
            "mission_snapshots": [
                snapshot.canonical_payload() for snapshot in self.mission_snapshots
            ],
            "notes": list(self.notes),
            "observations": [
                observation.canonical_payload() for observation in self.observations
            ],
            "phases": [phase.canonical_payload() for phase in self.phases],
            "protocol_ids": list(self.protocol_ids),
            "record_id": self.record_id,
            "review_state": self.review_state.value,
            "reviewer_ids": list(self.reviewer_ids),
            "schema_version": self.schema_version,
            "source_system": self.source_system.value,
            "title": self.title,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this record."""

        return _stable_sha256(self.canonical_payload())

    def _iter_evidence_ids(self) -> Iterable[str]:
        """Yield evidence ids in deterministic record traversal order."""

        for phase in self.phases:
            yield from phase.evidence_ids
        for snapshot in self.mission_snapshots:
            yield from snapshot.evidence_ids
        for observation in self.observations:
            yield from observation.evidence_ids
        for criterion in self.failure_criteria:
            yield from criterion.evidence_ids

    @staticmethod
    def _validate_phase_references(
        phase_ids: set[str],
        snapshots: tuple[WaveFiveMissionStateSnapshot, ...],
        observations: tuple[WaveFiveLongHorizonObservation, ...],
    ) -> None:
        """Validate that snapshots and observations reference bundled phases."""

        for snapshot in snapshots:
            if snapshot.phase_id not in phase_ids:
                raise ValueError(
                    "Mission-state snapshots must reference bundled phases: "
                    f"{snapshot.phase_id}"
                )
        for observation in observations:
            if observation.phase_id not in phase_ids:
                raise ValueError(
                    "Long-horizon observations must reference bundled phases: "
                    f"{observation.phase_id}"
                )
        snapshot_phase_ids = {snapshot.phase_id for snapshot in snapshots}
        observation_phase_ids = {observation.phase_id for observation in observations}
        for phase_id in phase_ids:
            if phase_id not in snapshot_phase_ids:
                raise ValueError(
                    "Long-horizon phases require mission-state snapshots: "
                    f"{phase_id}"
                )
            if phase_id not in observation_phase_ids:
                raise ValueError(
                    "Long-horizon phases require observations: "
                    f"{phase_id}"
                )

    @staticmethod
    def _validate_phase_contiguity(
        phases: tuple[WaveFiveLongHorizonPhase, ...]
    ) -> None:
        """Validate phase sequence indexes are contiguous from zero."""

        expected_indexes = tuple(range(len(phases)))
        observed_indexes = tuple(phase.sequence_index for phase in phases)
        if observed_indexes != expected_indexes:
            raise ValueError("Long-horizon phase sequence indexes must be contiguous.")


def required_long_horizon_phase_kinds() -> tuple[WaveFiveLongHorizonPhaseKind, ...]:
    """Return locked phase kinds required for long-horizon validation."""

    return REQUIRED_LONG_HORIZON_PHASE_KINDS


def required_mission_state_elements() -> tuple[WaveFiveMissionStateElement, ...]:
    """Return locked mission-state elements required for continuity."""

    return REQUIRED_MISSION_STATE_ELEMENTS


def safe_long_horizon_outcomes() -> tuple[WaveFiveLongHorizonOutcome, ...]:
    """Return outcomes that count as safe long-horizon behavior."""

    return SAFE_LONG_HORIZON_OUTCOMES


def external_long_horizon_source_systems() -> tuple[WaveFiveSourceSystem, ...]:
    """Return source systems allowed to assert external long-horizon review."""

    return EXTERNAL_LONG_HORIZON_SOURCE_SYSTEMS


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
