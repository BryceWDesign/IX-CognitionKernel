import pytest

from ix_cognition_kernel.wave4_contracts import (
    WaveFourArtifactKind,
    WaveFourCapabilityArea,
)
from ix_cognition_kernel.wave4_mission_state import (
    WaveFourMissionContinuityCheck,
    WaveFourMissionOutcome,
    WaveFourMissionPhaseKind,
    WaveFourMissionStateSnapshot,
    WaveFourMissionStateTrace,
    WaveFourMissionStatus,
    mission_snapshot,
    passed_continuity_check,
)
from ix_cognition_kernel.wave4_trials import (
    WaveFourTrialOutcome,
    WaveFourTrialStatus,
    WaveFourTrialTaskKind,
)


def snapshot(
    snapshot_id: str,
    phase_kind: WaveFourMissionPhaseKind,
    phase_index: int,
) -> WaveFourMissionStateSnapshot:
    return mission_snapshot(
        snapshot_id=snapshot_id,
        phase_kind=phase_kind,
        phase_index=phase_index,
        mission_objective="Preserve evidence-bound mission state across phases.",
        active_claim_ids=("claim:evidence-visible", "claim:human-authority"),
        active_plan_step_ids=(f"plan:{snapshot_id}",),
        unresolved_risk_ids=("risk:hidden-drift",),
        evidence_id=f"evidence:{snapshot_id}",
    )


def continuity(
    check_id: str,
    from_snapshot_id: str,
    to_snapshot_id: str,
) -> WaveFourMissionContinuityCheck:
    return passed_continuity_check(
        check_id=check_id,
        from_snapshot_id=from_snapshot_id,
        to_snapshot_id=to_snapshot_id,
        expected_preserved_claim_ids=("claim:evidence-visible",),
        preserved_claim_ids=("claim:evidence-visible",),
        preserved_risk_ids=("risk:hidden-drift",),
        evidence_id=f"evidence:{check_id}",
    )


def ready_trace() -> WaveFourMissionStateTrace:
    return WaveFourMissionStateTrace(
        trace_id="mission-trace-001",
        snapshots=(
            snapshot("snapshot-intake", WaveFourMissionPhaseKind.INTAKE, 0),
            snapshot("snapshot-planning", WaveFourMissionPhaseKind.PLANNING, 1),
            snapshot("snapshot-review", WaveFourMissionPhaseKind.REVIEW, 2),
        ),
        continuity_checks=(
            continuity("check-intake-planning", "snapshot-intake", "snapshot-planning"),
            continuity("check-planning-review", "snapshot-planning", "snapshot-review"),
        ),
        scenario_ids=("worldtwin:mission-continuity",),
        blackfox_receipt_ids=("blackfox:mission-continuity-review",),
    )


def test_mission_snapshot_requires_claims_steps_uncertainty_and_evidence() -> None:
    with pytest.raises(ValueError, match="require active claim ids"):
        mission_snapshot(
            snapshot_id="snapshot-invalid",
            phase_kind=WaveFourMissionPhaseKind.INTAKE,
            phase_index=0,
            mission_objective="Invalid snapshot.",
            active_claim_ids=(),
            active_plan_step_ids=("plan:one",),
            unresolved_risk_ids=(),
            evidence_id="evidence:snapshot-invalid",
        )

    with pytest.raises(ValueError, match="require plan step ids"):
        mission_snapshot(
            snapshot_id="snapshot-invalid",
            phase_kind=WaveFourMissionPhaseKind.INTAKE,
            phase_index=0,
            mission_objective="Invalid snapshot.",
            active_claim_ids=("claim:one",),
            active_plan_step_ids=(),
            unresolved_risk_ids=(),
            evidence_id="evidence:snapshot-invalid",
        )

    with pytest.raises(ValueError, match="require uncertainty notes"):
        mission_snapshot(
            snapshot_id="snapshot-invalid",
            phase_kind=WaveFourMissionPhaseKind.INTAKE,
            phase_index=0,
            mission_objective="Invalid snapshot.",
            active_claim_ids=("claim:one",),
            active_plan_step_ids=("plan:one",),
            unresolved_risk_ids=(),
            uncertainty_notes=(),
            evidence_id="evidence:snapshot-invalid",
        )


def test_mission_snapshot_rejects_negative_phase_index() -> None:
    with pytest.raises(ValueError, match="phase_index must be >= 0"):
        snapshot("snapshot-invalid", WaveFourMissionPhaseKind.INTAKE, -1)


def test_continuity_check_rejects_same_snapshot_and_missing_expected_claims() -> None:
    with pytest.raises(ValueError, match="require different snapshots"):
        passed_continuity_check(
            check_id="check-invalid",
            from_snapshot_id="snapshot-a",
            to_snapshot_id="snapshot-a",
            expected_preserved_claim_ids=("claim:one",),
            preserved_claim_ids=("claim:one",),
            preserved_risk_ids=(),
            evidence_id="evidence:check-invalid",
        )

    with pytest.raises(ValueError, match="require expected claims"):
        passed_continuity_check(
            check_id="check-invalid",
            from_snapshot_id="snapshot-a",
            to_snapshot_id="snapshot-b",
            expected_preserved_claim_ids=(),
            preserved_claim_ids=(),
            preserved_risk_ids=(),
            evidence_id="evidence:check-invalid",
        )


def test_passed_continuity_check_cannot_drop_expected_claims() -> None:
    with pytest.raises(ValueError, match="cannot drop expected claims"):
        WaveFourMissionContinuityCheck(
            check_id="check-invalid-drop",
            from_snapshot_id="snapshot-a",
            to_snapshot_id="snapshot-b",
            expected_preserved_claim_ids=("claim:evidence-visible",),
            preserved_claim_ids=(),
            dropped_claim_ids=("claim:evidence-visible",),
            preserved_risk_ids=(),
            dropped_risk_ids=(),
            evidence_ids=("evidence:check-invalid-drop",),
            passed=True,
        )


def test_failed_continuity_check_requires_dropped_state_evidence() -> None:
    with pytest.raises(ValueError, match="require dropped state evidence"):
        WaveFourMissionContinuityCheck(
            check_id="check-invalid-fail",
            from_snapshot_id="snapshot-a",
            to_snapshot_id="snapshot-b",
            expected_preserved_claim_ids=("claim:evidence-visible",),
            preserved_claim_ids=("claim:evidence-visible",),
            dropped_claim_ids=(),
            preserved_risk_ids=("risk:hidden-drift",),
            dropped_risk_ids=(),
            evidence_ids=("evidence:check-invalid-fail",),
            passed=False,
        )


def test_ready_mission_trace_confirms_long_horizon_continuity() -> None:
    trace = ready_trace()

    assert trace.status is WaveFourMissionStatus.READY_FOR_CONTROLLED_REVIEW
    assert trace.outcome is WaveFourMissionOutcome.CONTINUITY_CONFIRMED
    assert trace.ready_for_controlled_review is True
    assert trace.snapshot_ids == (
        "snapshot-intake",
        "snapshot-planning",
        "snapshot-review",
    )
    assert trace.missing_transition_keys == ()
    assert trace.drift_check_ids == ()
    assert trace.readiness_gaps == ()
    assert trace.permits_automatic_execution is False
    assert trace.claims_agi is False
    assert "no AGI claim" in trace.review_summary


def test_mission_trace_sorts_snapshots_by_phase_index_deterministically() -> None:
    first = ready_trace()
    second = WaveFourMissionStateTrace(
        trace_id="mission-trace-001",
        snapshots=tuple(reversed(first.snapshots)),
        continuity_checks=tuple(reversed(first.continuity_checks)),
        scenario_ids=("worldtwin:mission-continuity",),
        blackfox_receipt_ids=("blackfox:mission-continuity-review",),
    )

    assert first.snapshot_ids == second.snapshot_ids
    assert first.fingerprint() == second.fingerprint()
    assert len(first.fingerprint()) == 64


def test_mission_trace_reports_missing_transition_checks() -> None:
    trace = WaveFourMissionStateTrace(
        trace_id="mission-trace-missing-check",
        snapshots=ready_trace().snapshots,
        continuity_checks=(
            continuity("check-intake-planning", "snapshot-intake", "snapshot-planning"),
        ),
        scenario_ids=("worldtwin:mission-continuity",),
        blackfox_receipt_ids=("blackfox:mission-continuity-review",),
    )

    assert trace.status is WaveFourMissionStatus.NEEDS_EVIDENCE
    assert trace.outcome is WaveFourMissionOutcome.NEEDS_EVIDENCE
    assert trace.missing_transition_keys == (("snapshot-planning", "snapshot-review"),)
    assert "missing mission continuity checks" in trace.readiness_gaps[0]


def test_mission_trace_reports_phase_count_and_receipt_gaps() -> None:
    trace = WaveFourMissionStateTrace(
        trace_id="mission-trace-gaps",
        snapshots=(
            snapshot("snapshot-intake", WaveFourMissionPhaseKind.INTAKE, 0),
            snapshot("snapshot-review", WaveFourMissionPhaseKind.REVIEW, 1),
        ),
        continuity_checks=(
            continuity("check-intake-review", "snapshot-intake", "snapshot-review"),
        ),
        scenario_ids=(),
        blackfox_receipt_ids=(),
        minimum_phase_count=3,
    )

    assert trace.status is WaveFourMissionStatus.NEEDS_EVIDENCE
    assert "mission trace phase count below minimum" in trace.readiness_gaps[0]
    assert "mission-trace-gaps has no WorldTwin scenario ids" in trace.readiness_gaps
    assert (
        "mission-trace-gaps has no BlackFox review receipt ids" in trace.readiness_gaps
    )


def test_mission_trace_detects_drift_as_repair_needed() -> None:
    drift_check = WaveFourMissionContinuityCheck(
        check_id="check-drift",
        from_snapshot_id="snapshot-intake",
        to_snapshot_id="snapshot-planning",
        expected_preserved_claim_ids=("claim:evidence-visible",),
        preserved_claim_ids=(),
        dropped_claim_ids=("claim:evidence-visible",),
        preserved_risk_ids=(),
        dropped_risk_ids=("risk:hidden-drift",),
        evidence_ids=("evidence:check-drift",),
        passed=False,
        drift_summary="Evidence-visible claim and hidden-drift risk were dropped.",
    )
    trace = WaveFourMissionStateTrace(
        trace_id="mission-trace-drift",
        snapshots=(
            snapshot("snapshot-intake", WaveFourMissionPhaseKind.INTAKE, 0),
            snapshot("snapshot-planning", WaveFourMissionPhaseKind.PLANNING, 1),
            snapshot("snapshot-review", WaveFourMissionPhaseKind.REVIEW, 2),
        ),
        continuity_checks=(
            drift_check,
            continuity("check-planning-review", "snapshot-planning", "snapshot-review"),
        ),
        scenario_ids=("worldtwin:mission-continuity",),
        blackfox_receipt_ids=("blackfox:mission-continuity-review",),
    )

    assert trace.status is WaveFourMissionStatus.NEEDS_REPAIR
    assert trace.outcome is WaveFourMissionOutcome.CONTINUITY_DRIFT_DETECTED
    assert trace.drift_check_ids == ("check-drift",)
    assert "check-drift detected mission-state drift" in trace.readiness_gaps[0]


def test_blocked_mission_trace_cannot_carry_continuity_results() -> None:
    with pytest.raises(ValueError, match="cannot carry results"):
        WaveFourMissionStateTrace(
            trace_id="mission-trace-blocked-invalid",
            snapshots=ready_trace().snapshots,
            continuity_checks=ready_trace().continuity_checks,
            scenario_ids=("worldtwin:mission-continuity",),
            blackfox_receipt_ids=("blackfox:mission-continuity-review",),
            blocked_reasons=("mission objective was contradicted",),
        )

    trace = WaveFourMissionStateTrace(
        trace_id="mission-trace-blocked",
        snapshots=ready_trace().snapshots,
        continuity_checks=(),
        scenario_ids=("worldtwin:mission-continuity",),
        blackfox_receipt_ids=("blackfox:mission-continuity-review",),
        blocked_reasons=("mission objective was contradicted",),
    )

    assert trace.status is WaveFourMissionStatus.BLOCKED
    assert trace.outcome is WaveFourMissionOutcome.BLOCKED
    assert trace.blocking_gaps == (
        "mission-trace-blocked blocked: mission objective was contradicted",
    )


def test_mission_trace_rejects_execution_agi_and_independent_validation() -> None:
    with pytest.raises(ValueError, match="cannot permit execution"):
        WaveFourMissionStateTrace(
            trace_id="invalid-execution",
            snapshots=ready_trace().snapshots,
            continuity_checks=(),
            scenario_ids=(),
            blackfox_receipt_ids=(),
            permits_automatic_execution=True,
        )

    with pytest.raises(ValueError, match="cannot claim AGI"):
        WaveFourMissionStateTrace(
            trace_id="invalid-agi",
            snapshots=ready_trace().snapshots,
            continuity_checks=(),
            scenario_ids=(),
            blackfox_receipt_ids=(),
            claims_agi=True,
        )

    with pytest.raises(ValueError, match="cannot claim independent validation"):
        WaveFourMissionStateTrace(
            trace_id="invalid-independent-validation",
            snapshots=ready_trace().snapshots,
            continuity_checks=(),
            scenario_ids=(),
            blackfox_receipt_ids=(),
            independently_validated=True,
        )


def test_mission_trace_converts_to_shared_artifact_and_bundle() -> None:
    trace = ready_trace()
    artifact = trace.to_artifact_ref()
    bundle = trace.to_artifact_bundle()

    assert artifact.kind is WaveFourArtifactKind.MISSION_STATE_TRACE
    assert artifact.capability_area is WaveFourCapabilityArea.LONG_HORIZON_MISSION_STATE
    assert artifact.ready_for_controlled_review is True
    assert artifact.allowed_for_automatic_execution is False
    assert artifact.claims_agi is False
    assert len(trace.evidence_links()) == 5
    assert bundle.has_required_kind_coverage is True
    assert bundle.has_required_capability_coverage is True
    assert bundle.ready_for_controlled_review_artifact_ids == (artifact.artifact_id,)


def test_mission_trace_converts_to_controlled_trial_task() -> None:
    task = ready_trace().to_controlled_task()

    assert task.task_kind is WaveFourTrialTaskKind.MISSION_CONTINUITY_PROBE
    assert task.outcome is WaveFourTrialOutcome.PASSED
    assert task.status is WaveFourTrialStatus.READY_FOR_CONTROLLED_REVIEW
    assert task.ready_for_controlled_review is True
    assert task.scenario_ids == ("worldtwin:mission-continuity",)
    assert task.blackfox_receipt_ids == ("blackfox:mission-continuity-review",)
    assert len(task.measurements) == 2


def test_drift_mission_trace_converts_to_failed_trial_task() -> None:
    drift_check = WaveFourMissionContinuityCheck(
        check_id="check-drift",
        from_snapshot_id="snapshot-intake",
        to_snapshot_id="snapshot-planning",
        expected_preserved_claim_ids=("claim:evidence-visible",),
        preserved_claim_ids=(),
        dropped_claim_ids=("claim:evidence-visible",),
        preserved_risk_ids=(),
        dropped_risk_ids=("risk:hidden-drift",),
        evidence_ids=("evidence:check-drift",),
        passed=False,
        drift_summary="Evidence-visible claim was dropped.",
    )
    trace = WaveFourMissionStateTrace(
        trace_id="mission-trace-drift",
        snapshots=(
            snapshot("snapshot-intake", WaveFourMissionPhaseKind.INTAKE, 0),
            snapshot("snapshot-planning", WaveFourMissionPhaseKind.PLANNING, 1),
            snapshot("snapshot-review", WaveFourMissionPhaseKind.REVIEW, 2),
        ),
        continuity_checks=(
            drift_check,
            continuity("check-planning-review", "snapshot-planning", "snapshot-review"),
        ),
        scenario_ids=("worldtwin:mission-continuity",),
        blackfox_receipt_ids=("blackfox:mission-continuity-review",),
    )
    task = trace.to_controlled_task()

    assert task.outcome is WaveFourTrialOutcome.FAILED
    assert task.status is WaveFourTrialStatus.NEEDS_REPAIR
    assert task.failed_measurement_ids == ("mission-continuity:check-drift",)


def test_mission_trace_fingerprint_is_deterministic() -> None:
    assert ready_trace().fingerprint() == ready_trace().fingerprint()
    assert len(ready_trace().fingerprint()) == 64
