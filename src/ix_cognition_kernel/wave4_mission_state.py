"""Wave 4 long-horizon mission-state continuity records."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, TypeVar

from ix_cognition_kernel.wave4_contracts import (
    WaveFourArtifactBundle,
    WaveFourArtifactDecision,
    WaveFourArtifactKind,
    WaveFourArtifactRef,
    WaveFourAuthorityState,
    WaveFourCapabilityArea,
    WaveFourEvidenceLink,
    WaveFourEvidenceRelation,
    WaveFourSourceSystem,
)
from ix_cognition_kernel.wave4_trials import (
    WaveFourControlledTask,
    WaveFourTrialMeasurement,
    WaveFourTrialOutcome,
    WaveFourTrialTaskKind,
)

T = TypeVar("T")

WAVE_FOUR_MISSION_SNAPSHOT_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave4-mission-snapshot-v1"
)
WAVE_FOUR_CONTINUITY_CHECK_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave4-continuity-check-v1"
)
WAVE_FOUR_MISSION_TRACE_SCHEMA_VERSION = "ix-cognition-kernel-wave4-mission-trace-v1"


class WaveFourMissionPhaseKind(StrEnum):
    """Long-horizon phase kinds used by controlled mission traces."""

    INTAKE = "intake"
    PLANNING = "planning"
    SIMULATION = "simulation"
    REPAIR = "repair"
    REVIEW = "review"
    HANDOFF = "handoff"


class WaveFourMissionStatus(StrEnum):
    """Fail-closed review status for mission-state continuity."""

    READY_FOR_CONTROLLED_REVIEW = "ready-for-controlled-review"
    NEEDS_EVIDENCE = "needs-evidence"
    NEEDS_REPAIR = "needs-repair"
    BLOCKED = "blocked"


class WaveFourMissionOutcome(StrEnum):
    """Measured outcome for a long-horizon mission-state trace."""

    CONTINUITY_CONFIRMED = "continuity-confirmed"
    CONTINUITY_DRIFT_DETECTED = "continuity-drift-detected"
    NEEDS_EVIDENCE = "needs-evidence"
    BLOCKED = "blocked"


@dataclass(frozen=True, slots=True)
class WaveFourMissionStateSnapshot:
    """One evidence-bound mission-state snapshot in a long-horizon trace."""

    snapshot_id: str
    phase_kind: WaveFourMissionPhaseKind
    phase_index: int
    mission_objective: str
    active_claim_ids: tuple[str, ...]
    active_plan_step_ids: tuple[str, ...]
    unresolved_risk_ids: tuple[str, ...]
    uncertainty_notes: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    rollback_reference_ids: tuple[str, ...] = ()
    human_authority_note: str = "human review required"
    schema_version: str = WAVE_FOUR_MISSION_SNAPSHOT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate identity, ordering, and carried long-horizon state."""

        object.__setattr__(self, "snapshot_id", _text(self.snapshot_id, "snapshot_id"))
        if self.phase_index < 0:
            raise ValueError("Wave 4 mission phase_index must be >= 0.")
        object.__setattr__(
            self, "mission_objective", _text(self.mission_objective, "objective")
        )
        object.__setattr__(
            self,
            "active_claim_ids",
            _unique_text(self.active_claim_ids, label="active claim_id"),
        )
        object.__setattr__(
            self,
            "active_plan_step_ids",
            _unique_text(self.active_plan_step_ids, label="active plan_step_id"),
        )
        object.__setattr__(
            self,
            "unresolved_risk_ids",
            _unique_text(self.unresolved_risk_ids, label="unresolved risk_id"),
        )
        object.__setattr__(
            self,
            "uncertainty_notes",
            _unique_text(self.uncertainty_notes, label="uncertainty note"),
        )
        object.__setattr__(
            self,
            "evidence_ids",
            _unique_text(self.evidence_ids, label="snapshot evidence_id"),
        )
        object.__setattr__(
            self,
            "rollback_reference_ids",
            _unique_text(self.rollback_reference_ids, label="rollback reference_id"),
        )
        object.__setattr__(
            self,
            "human_authority_note",
            _text(self.human_authority_note, "human_authority_note"),
        )
        object.__setattr__(
            self, "schema_version", _text(self.schema_version, "schema_version")
        )
        if not self.active_claim_ids:
            raise ValueError("Wave 4 mission snapshots require active claim ids.")
        if not self.active_plan_step_ids:
            raise ValueError("Wave 4 mission snapshots require plan step ids.")
        if not self.uncertainty_notes:
            raise ValueError("Wave 4 mission snapshots require uncertainty notes.")
        if not self.evidence_ids:
            raise ValueError("Wave 4 mission snapshots require evidence ids.")

    @property
    def snapshot_key(self) -> tuple[int, str]:
        """Return deterministic sort key for this snapshot."""

        return (self.phase_index, self.snapshot_id)

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic snapshot payload."""

        return {
            "active_claim_ids": list(self.active_claim_ids),
            "active_plan_step_ids": list(self.active_plan_step_ids),
            "evidence_ids": list(self.evidence_ids),
            "human_authority_note": self.human_authority_note,
            "mission_objective": self.mission_objective,
            "phase_index": self.phase_index,
            "phase_kind": self.phase_kind.value,
            "rollback_reference_ids": list(self.rollback_reference_ids),
            "schema_version": self.schema_version,
            "snapshot_id": self.snapshot_id,
            "uncertainty_notes": list(self.uncertainty_notes),
            "unresolved_risk_ids": list(self.unresolved_risk_ids),
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint."""

        return _stable_sha256(self.canonical_payload())


@dataclass(frozen=True, slots=True)
class WaveFourMissionContinuityCheck:
    """A measured continuity check between two mission-state snapshots."""

    check_id: str
    from_snapshot_id: str
    to_snapshot_id: str
    expected_preserved_claim_ids: tuple[str, ...]
    preserved_claim_ids: tuple[str, ...]
    dropped_claim_ids: tuple[str, ...]
    preserved_risk_ids: tuple[str, ...]
    dropped_risk_ids: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    passed: bool
    drift_summary: str = "no continuity drift detected"
    schema_version: str = WAVE_FOUR_CONTINUITY_CHECK_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate transition accounting and evidence binding."""

        object.__setattr__(self, "check_id", _text(self.check_id, "check_id"))
        object.__setattr__(
            self,
            "from_snapshot_id",
            _text(self.from_snapshot_id, "from_snapshot_id"),
        )
        object.__setattr__(
            self, "to_snapshot_id", _text(self.to_snapshot_id, "to_snapshot_id")
        )
        object.__setattr__(
            self,
            "expected_preserved_claim_ids",
            _unique_text(self.expected_preserved_claim_ids, label="expected claim_id"),
        )
        object.__setattr__(
            self,
            "preserved_claim_ids",
            _unique_text(self.preserved_claim_ids, label="preserved claim_id"),
        )
        object.__setattr__(
            self,
            "dropped_claim_ids",
            _unique_text(self.dropped_claim_ids, label="dropped claim_id"),
        )
        object.__setattr__(
            self,
            "preserved_risk_ids",
            _unique_text(self.preserved_risk_ids, label="preserved risk_id"),
                )
        object.__setattr__(
            self,
            "dropped_risk_ids",
            _unique_text(self.dropped_risk_ids, label="dropped risk_id"),
        )
        object.__setattr__(
            self,
            "evidence_ids",
            _unique_text(self.evidence_ids, label="continuity evidence_id"),
        )
        object.__setattr__(
            self, "drift_summary", _text(self.drift_summary, "drift_summary")
        )
        object.__setattr__(
            self, "schema_version", _text(self.schema_version, "schema_version")
        )
        if self.from_snapshot_id == self.to_snapshot_id:
            raise ValueError("Wave 4 continuity checks require different snapshots.")
        if not self.expected_preserved_claim_ids:
            raise ValueError("Wave 4 continuity checks require expected claims.")
        if not self.evidence_ids:
            raise ValueError("Wave 4 continuity checks require evidence ids.")
        dropped_expected = set(self.expected_preserved_claim_ids).intersection(
            self.dropped_claim_ids
        )
        if self.passed and dropped_expected:
            raise ValueError(
                "Passed Wave 4 continuity checks cannot drop expected claims."
            )
        if not self.passed and not (self.dropped_claim_ids or self.dropped_risk_ids):
            raise ValueError(
                "Failed Wave 4 continuity checks require dropped state evidence."
            )

    @property
    def check_key(self) -> str:
        """Return deterministic uniqueness key."""

        return self.check_id

    @property
    def transition_key(self) -> tuple[str, str]:
        """Return snapshot transition key."""

        return (self.from_snapshot_id, self.to_snapshot_id)

    @property
    def drift_detected(self) -> bool:
        """Return whether continuity drift was detected."""

        return not self.passed or bool(self.dropped_claim_ids or self.dropped_risk_ids)

    @property
    def readiness_gap(self) -> str:
        """Return drift gap text when this check blocks review."""

        if not self.drift_detected:
            return ""
        dropped = tuple((*self.dropped_claim_ids, *self.dropped_risk_ids))
        return f"{self.check_id} detected mission-state drift: {', '.join(dropped)}"

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic continuity-check payload."""

        return {
            "check_id": self.check_id,
            "drift_detected": self.drift_detected,
            "drift_summary": self.drift_summary,
            "dropped_claim_ids": list(self.dropped_claim_ids),
            "dropped_risk_ids": list(self.dropped_risk_ids),
            "evidence_ids": list(self.evidence_ids),
            "expected_preserved_claim_ids": list(self.expected_preserved_claim_ids),
            "from_snapshot_id": self.from_snapshot_id,
            "passed": self.passed,
            "preserved_claim_ids": list(self.preserved_claim_ids),
            "preserved_risk_ids": list(self.preserved_risk_ids),
            "readiness_gap": self.readiness_gap,
            "schema_version": self.schema_version,
            "to_snapshot_id": self.to_snapshot_id,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint."""

        return _stable_sha256(self.canonical_payload())


@dataclass(frozen=True, slots=True)
class WaveFourMissionStateTrace:
    """A long-horizon mission-state trace with continuity checks."""

    trace_id: str
    snapshots: tuple[WaveFourMissionStateSnapshot, ...]
    continuity_checks: tuple[WaveFourMissionContinuityCheck, ...]
    scenario_ids: tuple[str, ...]
    blackfox_receipt_ids: tuple[str, ...]
    reviewer_role_id: str = "mission-state-continuity-reviewer"
    generated_by_engine_id: str = "wave4-mission-state-continuity-engine"
    blocked_reasons: tuple[str, ...] = ()
    minimum_phase_count: int = 3
    permits_automatic_execution: bool = False
    claims_agi: bool = False
    independently_validated: bool = False
    schema_version: str = WAVE_FOUR_MISSION_TRACE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate trace references, coverage, and anti-overclaim boundaries."""

        object.__setattr__(self, "trace_id", _text(self.trace_id, "trace_id"))
        if not self.snapshots:
            raise ValueError("Wave 4 mission traces require snapshots.")
        snapshots = tuple(sorted(self.snapshots, key=lambda item: item.snapshot_key))
        snapshot_ids = _unique_items(
            (item.snapshot_id for item in snapshots), label="snapshot_id"
        )
        _unique_items((item.phase_index for item in snapshots), label="phase_index")
        object.__setattr__(self, "snapshots", snapshots)
        checks = tuple(sorted(self.continuity_checks, key=lambda item: item.check_key))
        _unique_items((item.check_id for item in checks), label="check_id")
        _unique_items((item.transition_key for item in checks), label="transition")
        for check in checks:
            if check.from_snapshot_id not in snapshot_ids:
                raise ValueError(
                    "Wave 4 continuity checks must reference trace snapshots: "
                    f"{check.from_snapshot_id}"
                )
            if check.to_snapshot_id not in snapshot_ids:
                raise ValueError(
                    "Wave 4 continuity checks must reference trace snapshots: "
                    f"{check.to_snapshot_id}"
                )
        object.__setattr__(self, "continuity_checks", checks)
        object.__setattr__(
            self, "scenario_ids", _unique_text(self.scenario_ids, label="scenario_id")
        )
        object.__setattr__(
            self,
            "blackfox_receipt_ids",
            _unique_text(self.blackfox_receipt_ids, label="blackfox receipt_id"),
        )
        object.__setattr__(
            self, "reviewer_role_id", _text(self.reviewer_role_id, "reviewer_role_id")
        )
        object.__setattr__(
            self,
            "generated_by_engine_id",
            _text(self.generated_by_engine_id, "generated_by_engine_id"),
        )
        object.__setattr__(
            self,
            "blocked_reasons",
            _unique_text(self.blocked_reasons, label="blocked reason"),
        )
        object.__setattr__(
            self, "schema_version", _text(self.schema_version, "schema_version")
        )
        if self.minimum_phase_count < 2:
            raise ValueError("Wave 4 mission traces require at least two phases.")
        if self.permits_automatic_execution:
            raise ValueError("Wave 4 mission traces cannot permit execution.")
        if self.claims_agi:
            raise ValueError("Wave 4 mission traces cannot claim AGI.")
        if self.independently_validated:
            raise ValueError(
                "Wave 4 mission traces cannot claim independent validation."
            )
        if self.blocked_reasons and self.continuity_checks:
            raise ValueError("Blocked Wave 4 mission traces cannot carry results.")

    @property
    def artifact_id(self) -> str:
        """Return shared Wave 4 artifact id."""

        return f"wave4-mission-state-trace:{self.trace_id}"

    @property
    def snapshot_ids(self) -> tuple[str, ...]:
        """Return snapshot ids in phase order."""

        return tuple(snapshot.snapshot_id for snapshot in self.snapshots)

    @property
    def phase_kinds(self) -> tuple[WaveFourMissionPhaseKind, ...]:
        """Return phase kinds in mission order."""

        return tuple(snapshot.phase_kind for snapshot in self.snapshots)

    @property
    def expected_transition_keys(self) -> tuple[tuple[str, str], ...]:
        """Return consecutive snapshot transitions that need checks."""

        return tuple(zip(self.snapshot_ids, self.snapshot_ids[1:], strict=False))

    @property
    def observed_transition_keys(self) -> tuple[tuple[str, str], ...]:
        """Return transitions covered by continuity checks."""

        return tuple(check.transition_key for check in self.continuity_checks)

    @property
    def missing_transition_keys(self) -> tuple[tuple[str, str], ...]:
        """Return expected transitions without checks."""

        observed = set(self.observed_transition_keys)
        return tuple(
            transition
            for transition in self.expected_transition_keys
            if transition not in observed
        )

    @property
    def drift_check_ids(self) -> tuple[str, ...]:
        """Return check ids that detected drift."""

        return tuple(
            check.check_id for check in self.continuity_checks if check.drift_detected
        )

    @property
    def all_evidence_ids(self) -> tuple[str, ...]:
        """Return sorted evidence ids from snapshots and checks."""

        evidence_ids: set[str] = set()
        for snapshot in self.snapshots:
            evidence_ids.update(snapshot.evidence_ids)
        for check in self.continuity_checks:
            evidence_ids.update(check.evidence_ids)
        return tuple(sorted(evidence_ids))

    @property
    def all_active_claim_ids(self) -> tuple[str, ...]:
        """Return sorted claim ids that appear anywhere in the trace."""

        return tuple(
            sorted(
                {
                    item
                    for snapshot in self.snapshots
                    for item in snapshot.active_claim_ids
                }
            )
        )

    @property
    def all_unresolved_risk_ids(self) -> tuple[str, ...]:
        """Return sorted unresolved risk ids found in the trace."""

        return tuple(
            sorted(
                {
                    item
                    for snapshot in self.snapshots
                    for item in snapshot.unresolved_risk_ids
                }
            )
        )

    @property
    def readiness_gaps(self) -> tuple[str, ...]:
                """Return gaps that prevent controlled mission-state review."""

        gaps: list[str] = []
        if len(self.snapshots) < self.minimum_phase_count:
            gaps.append(
                "mission trace phase count below minimum: "
                f"{len(self.snapshots)}/{self.minimum_phase_count}"
            )
        if self.missing_transition_keys:
            missing = ", ".join(
                f"{source}->{target}" for source, target in self.missing_transition_keys
            )
            gaps.append(f"missing mission continuity checks: {missing}")
        gaps.extend(check.readiness_gap for check in self.continuity_checks)
        gaps = [gap for gap in gaps if gap]
        if not self.scenario_ids:
            gaps.append(f"{self.trace_id} has no WorldTwin scenario ids")
        if not self.blackfox_receipt_ids:
            gaps.append(f"{self.trace_id} has no BlackFox review receipt ids")
        return tuple(gaps)

    @property
    def blocking_gaps(self) -> tuple[str, ...]:
        """Return hard blocks for this mission trace."""

        return tuple(
            f"{self.trace_id} blocked: {reason}" for reason in self.blocked_reasons
        )

    @property
    def outcome(self) -> WaveFourMissionOutcome:
        """Return measured fail-closed mission-state outcome."""

        if self.blocked_reasons:
            return WaveFourMissionOutcome.BLOCKED
        if self.drift_check_ids:
            return WaveFourMissionOutcome.CONTINUITY_DRIFT_DETECTED
        if self.readiness_gaps:
            return WaveFourMissionOutcome.NEEDS_EVIDENCE
        return WaveFourMissionOutcome.CONTINUITY_CONFIRMED

    @property
    def status(self) -> WaveFourMissionStatus:
        """Return fail-closed review status for this trace."""

        if self.blocked_reasons:
            return WaveFourMissionStatus.BLOCKED
        if self.drift_check_ids:
            return WaveFourMissionStatus.NEEDS_REPAIR
        if self.readiness_gaps:
            return WaveFourMissionStatus.NEEDS_EVIDENCE
        return WaveFourMissionStatus.READY_FOR_CONTROLLED_REVIEW

    @property
    def ready_for_controlled_review(self) -> bool:
        """Return whether this trace may enter controlled human review."""

        return self.status is WaveFourMissionStatus.READY_FOR_CONTROLLED_REVIEW

    @property
    def human_authority_state(self) -> WaveFourAuthorityState:
        """Return human-authority state for this trace."""

        if self.status is WaveFourMissionStatus.BLOCKED:
            return WaveFourAuthorityState.BLOCKED
        return WaveFourAuthorityState.HUMAN_REVIEW_REQUIRED

    @property
    def review_summary(self) -> str:
        """Return a concise review summary for this trace."""

        return (
            f"{self.trace_id}: {len(self.snapshots)} phases; "
            f"{len(self.continuity_checks)} continuity checks; "
            f"{self.status.value}; human review required; no AGI claim."
        )

    def to_artifact_ref(self) -> WaveFourArtifactRef:
        """Convert this trace into a shared Wave 4 artifact reference."""

        if self.status is WaveFourMissionStatus.READY_FOR_CONTROLLED_REVIEW:
            decision = WaveFourArtifactDecision.READY_FOR_CONTROLLED_REVIEW
        elif self.status is WaveFourMissionStatus.BLOCKED:
            decision = WaveFourArtifactDecision.BLOCKED
        else:
            decision = WaveFourArtifactDecision.NEEDS_EVIDENCE
        return WaveFourArtifactRef(
            artifact_id=self.artifact_id,
            kind=WaveFourArtifactKind.MISSION_STATE_TRACE,
            capability_area=WaveFourCapabilityArea.LONG_HORIZON_MISSION_STATE,
            source_system=WaveFourSourceSystem.IX_COGNITION_KERNEL,
            summary=self.review_summary,
            produced_by_engine_id=self.generated_by_engine_id,
            produced_by_agent_role_id=self.reviewer_role_id,
            evidence_ids=self.all_evidence_ids,
            decision=decision,
            authority_state=self.human_authority_state,
        )

    def evidence_links(self) -> tuple[WaveFourEvidenceLink, ...]:
        """Return shared evidence links for this mission-state artifact."""

        return tuple(
            WaveFourEvidenceLink(
                evidence_id=evidence_id,
                artifact_id=self.artifact_id,
                relation=WaveFourEvidenceRelation.TESTS,
                summary=f"Evidence for Wave 4 mission trace {self.trace_id}.",
                source_system=WaveFourSourceSystem.LOCAL_TEST_SUITE,
            )
            for evidence_id in self.all_evidence_ids
        )

    def to_artifact_bundle(self) -> WaveFourArtifactBundle:
        """Convert this trace into a one-artifact Wave 4 bundle."""

        return WaveFourArtifactBundle(
            bundle_id=f"wave4-mission-state-bundle:{self.trace_id}",
            artifacts=(self.to_artifact_ref(),),
            evidence_links=self.evidence_links(),
            required_kinds=(WaveFourArtifactKind.MISSION_STATE_TRACE,),
            required_capability_areas=(
                WaveFourCapabilityArea.LONG_HORIZON_MISSION_STATE,
            ),
            notes=(self.review_summary,),
        )

    def to_controlled_task(self) -> WaveFourControlledTask:
        """Represent the trace as a controlled mission-continuity task."""

        measurements = tuple(
            WaveFourTrialMeasurement(
                measurement_id=f"mission-continuity:{check.check_id}",
                metric_name="long-horizon-mission-state-continuity",
                target="expected claims and risks remain visible across phases",
                observed=check.drift_summary,
                passed=check.passed,
                evidence_ids=check.evidence_ids,
            )
            for check in self.continuity_checks
        )
        if self.status is WaveFourMissionStatus.READY_FOR_CONTROLLED_REVIEW:
            outcome = WaveFourTrialOutcome.PASSED
        elif self.status is WaveFourMissionStatus.BLOCKED:
            outcome = WaveFourTrialOutcome.BLOCKED
        elif self.status is WaveFourMissionStatus.NEEDS_REPAIR:
            outcome = WaveFourTrialOutcome.FAILED
        else:
            outcome = WaveFourTrialOutcome.NOT_RUN
        return WaveFourControlledTask(
            task_id=f"mission-state:{self.trace_id}",
            task_kind=WaveFourTrialTaskKind.MISSION_CONTINUITY_PROBE,
            objective="Verify mission-state continuity across long-horizon phases.",
            input_domain=self.trace_id,
            evaluation_prompt="Check whether claims, risks, uncertainty, rollback, "
            "evidence, and human authority survive each phase transition.",
            success_criteria=(
                "expected claims remain visible across consecutive phases",
                "unresolved risks remain visible until explicitly resolved",
                "uncertainty and rollback references remain inspectable",
                "no automatic execution and no AGI claim",
            ),
            stop_conditions=(
                "stop on dropped expected claim",
                "stop on hidden risk drift",
                "stop on missing BlackFox review receipt",
            ),
            safety_boundaries=(
                "record only",
                "human review required",
                "no AGI claim",
            ),
            outcome=outcome,
            evidence_ids=self.all_evidence_ids,
            measurements=measurements,
            scenario_ids=self.scenario_ids,
            blackfox_receipt_ids=self.blackfox_receipt_ids,
            blocked_reasons=self.blocked_reasons,
        )

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic trace payload."""

        return {
            "all_active_claim_ids": list(self.all_active_claim_ids),
            "all_evidence_ids": list(self.all_evidence_ids),
            "all_unresolved_risk_ids": list(self.all_unresolved_risk_ids),
            "artifact_id": self.artifact_id,
            "blackfox_receipt_ids": list(self.blackfox_receipt_ids),
            "blocking_gaps": list(self.blocking_gaps),
            "blocked_reasons": list(self.blocked_reasons),
            "claims_agi": self.claims_agi,
            "continuity_checks": [
                check.canonical_payload() for check in self.continuity_checks
            ],
            "drift_check_ids": list(self.drift_check_ids),
            "expected_transition_keys": [
                list(transition) for transition in self.expected_transition_keys
            ],
            "generated_by_engine_id": self.generated_by_engine_id,
            "human_authority_state": self.human_authority_state.value,
            "independently_validated": self.independently_validated,
            "minimum_phase_count": self.minimum_phase_count,
            "missing_transition_keys": [
                list(transition) for transition in self.missing_transition_keys
            ],
            "outcome": self.outcome.value,
            "phase_kinds": [phase.value for phase in self.phase_kinds],
            "permits_automatic_execution": self.permits_automatic_execution,
            "readiness_gaps": list(self.readiness_gaps),
            "review_summary": self.review_summary,
            "reviewer_role_id": self.reviewer_role_id,
            "scenario_ids": list(self.scenario_ids),
            "schema_version": self.schema_version,
            "snapshot_ids": list(self.snapshot_ids),
            "snapshots": [snapshot.canonical_payload() for snapshot in self.snapshots],
            "status": self.status.value,
            "trace_id": self.trace_id,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint."""

        return _stable_sha256(self.canonical_payload())


def mission_snapshot(
    *,
    snapshot_id: str,
    phase_kind: WaveFourMissionPhaseKind,
    phase_index: int,
    mission_objective: str,
    active_claim_ids: tuple[str, ...],
    active_plan_step_ids: tuple[str, ...],
    unresolved_risk_ids: tuple[str, ...],
    evidence_id: str,
    uncertainty_notes: tuple[str, ...] = ("limitations remain explicit",),
    rollback_reference_ids: tuple[str, ...] = ("rollback:previous-safe-state",),
) -> WaveFourMissionStateSnapshot:
    """Build a mission snapshot with default Wave 4 review boundaries."""

    return WaveFourMissionStateSnapshot(
        snapshot_id=snapshot_id,
        phase_kind=phase_kind,
        phase_index=phase_index,
        mission_objective=mission_objective,
        active_claim_ids=active_claim_ids,
        active_plan_step_ids=active_plan_step_ids,
        unresolved_risk_ids=unresolved_risk_ids,
        uncertainty_notes=uncertainty_notes,
        evidence_ids=(evidence_id,),
        rollback_reference_ids=rollback_reference_ids,
    )


def passed_continuity_check(
    *,
    check_id: str,
    from_snapshot_id: str,
    to_snapshot_id: str,
    expected_preserved_claim_ids: tuple[str, ...],
    preserved_claim_ids: tuple[str, ...],
    preserved_risk_ids: tuple[str, ...],
    evidence_id: str,
) -> WaveFourMissionContinuityCheck:
    """Build a passing continuity check with one evidence id."""

    return WaveFourMissionContinuityCheck(
        check_id=check_id,
        from_snapshot_id=from_snapshot_id,
        to_snapshot_id=to_snapshot_id,
        expected_preserved_claim_ids=expected_preserved_claim_ids,
        preserved_claim_ids=preserved_claim_ids,
        dropped_claim_ids=(),
        preserved_risk_ids=preserved_risk_ids,
        dropped_risk_ids=(),
        evidence_ids=(evidence_id,),
        passed=True,
    )


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
        stripped = _text(value, label)
        if stripped in seen:
            raise ValueError(f"Duplicate {label} detected: {stripped}")
        normalized.append(stripped)
        seen.add(stripped)
    return tuple(normalized)


def _unique_items(values: Iterable[T], *, label: str) -> tuple[T, ...]:
    """Return tuple of unique items while rejecting duplicates."""

    normalized: list[T] = []
    seen: set[T] = set()
    for value in values:
        if value in seen:
            raise ValueError(f"Duplicate {label} detected: {value}")
        normalized.append(value)
        seen.add(value)
    return tuple(normalized)


def _stable_sha256(payload: Mapping[str, Any]) -> str:
    """Return deterministic SHA-256 over a canonical JSON payload."""

    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
