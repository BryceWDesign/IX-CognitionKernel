import pytest

from ix_cognition_kernel.wave5_contracts import (
    WAVE_FIVE_REQUIRED_CLAIM_BOUNDARIES,
    WaveFiveArtifactDecision,
    WaveFiveArtifactKind,
    WaveFiveAuthorityState,
    WaveFiveCapabilityArea,
    WaveFiveClaimBoundary,
    WaveFiveSourceSystem,
    WaveFiveValidationStatus,
)
from ix_cognition_kernel.wave5_long_horizon import (
    EXTERNAL_LONG_HORIZON_SOURCE_SYSTEMS,
    REQUIRED_LONG_HORIZON_PHASE_KINDS,
    REQUIRED_MISSION_STATE_ELEMENTS,
    SAFE_LONG_HORIZON_OUTCOMES,
    WaveFiveLongHorizonFailureCriterion,
    WaveFiveLongHorizonFailureKind,
    WaveFiveLongHorizonObservation,
    WaveFiveLongHorizonOutcome,
    WaveFiveLongHorizonPhase,
    WaveFiveLongHorizonPhaseKind,
    WaveFiveLongHorizonReviewState,
    WaveFiveLongHorizonTaskRecord,
    WaveFiveMissionStateElement,
    WaveFiveMissionStateSnapshot,
    external_long_horizon_source_systems,
    required_long_horizon_phase_kinds,
    required_mission_state_elements,
    safe_long_horizon_outcomes,
)


def phase(
    phase_id: str = "phase-mission-intake",
    *,
    phase_kind: WaveFiveLongHorizonPhaseKind = (
        WaveFiveLongHorizonPhaseKind.MISSION_INTAKE
    ),
    sequence_index: int = 0,
    elements: tuple[WaveFiveMissionStateElement, ...] = (
        REQUIRED_MISSION_STATE_ELEMENTS
    ),
) -> WaveFiveLongHorizonPhase:
    return WaveFiveLongHorizonPhase(
        phase_id=phase_id,
        phase_kind=phase_kind,
        sequence_index=sequence_index,
        objective="Preserve mission state across this long-horizon phase.",
        expected_state_elements=elements,
        rollback_plan="Escalate to human review and retain reversible state.",
        evidence_ids=(f"evidence-{phase_id}",),
    )


def snapshot(
    phase_id: str = "phase-mission-intake",
    *,
    snapshot_id: str = "snapshot-mission-intake",
    elements: tuple[WaveFiveMissionStateElement, ...] = (
        REQUIRED_MISSION_STATE_ELEMENTS
    ),
) -> WaveFiveMissionStateSnapshot:
    return WaveFiveMissionStateSnapshot(
        snapshot_id=snapshot_id,
        phase_id=phase_id,
        preserved_elements=elements,
        active_goal_summary="Original user objective remains visible.",
        active_constraint_summary=(
            "Authority, evidence, and rollback gates remain active."
        ),
        uncertainty_summary="Known unknowns remain visible and not hidden.",
        authority_boundary_summary="Human authority remains required for escalation.",
        evidence_ids=(f"evidence-{snapshot_id}",),
    )


def observation(
    phase_id: str = "phase-mission-intake",
    *,
    observation_id: str = "observation-mission-intake",
    outcome: WaveFiveLongHorizonOutcome = (
        WaveFiveLongHorizonOutcome.COMPLETED_WITH_EVIDENCE
    ),
    preserved_mission_continuity: bool = True,
    preserved_human_authority: bool = True,
    preserved_uncertainty: bool = True,
) -> WaveFiveLongHorizonObservation:
    return WaveFiveLongHorizonObservation(
        observation_id=observation_id,
        phase_id=phase_id,
        outcome=outcome,
        observed_transition="Phase completed with evidence-linked mission continuity.",
        prediction_delta_summary="No unsupported expansion of mission claim occurred.",
        preserved_mission_continuity=preserved_mission_continuity,
        preserved_human_authority=preserved_human_authority,
        preserved_uncertainty=preserved_uncertainty,
        evidence_ids=(f"evidence-{observation_id}",),
    )


def failure(
    criterion_id: str = "failure-lost-objective",
    *,
    triggered: bool = False,
    blocking: bool = True,
) -> WaveFiveLongHorizonFailureCriterion:
    evidence_ids = (f"evidence-{criterion_id}",) if triggered else ()
    return WaveFiveLongHorizonFailureCriterion(
        criterion_id=criterion_id,
        failure_kind=WaveFiveLongHorizonFailureKind.LOST_USER_OBJECTIVE,
        description="The long-horizon task loses the original user objective.",
        triggered=triggered,
        blocking=blocking,
        mitigation="Block Wave 5 readiness and record the failed continuity path.",
        evidence_ids=evidence_ids,
    )


def required_phases() -> tuple[WaveFiveLongHorizonPhase, ...]:
    return tuple(
        phase(
            phase_id=f"phase-{phase_kind.value}",
            phase_kind=phase_kind,
            sequence_index=index,
        )
        for index, phase_kind in enumerate(REQUIRED_LONG_HORIZON_PHASE_KINDS)
    )


def required_snapshots() -> tuple[WaveFiveMissionStateSnapshot, ...]:
    return tuple(
        snapshot(
            phase_id=f"phase-{phase_kind.value}",
            snapshot_id=f"snapshot-{phase_kind.value}",
        )
        for phase_kind in REQUIRED_LONG_HORIZON_PHASE_KINDS
    )


def required_observations(
    *,
    outcome: WaveFiveLongHorizonOutcome = (
        WaveFiveLongHorizonOutcome.COMPLETED_WITH_EVIDENCE
    ),
) -> tuple[WaveFiveLongHorizonObservation, ...]:
    return tuple(
        observation(
            phase_id=f"phase-{phase_kind.value}",
            observation_id=f"observation-{phase_kind.value}",
            outcome=outcome,
        )
        for phase_kind in REQUIRED_LONG_HORIZON_PHASE_KINDS
    )


def record(
    *,
    source_system: WaveFiveSourceSystem = WaveFiveSourceSystem.IX_COGNITION_KERNEL,
    review_state: WaveFiveLongHorizonReviewState = (
        WaveFiveLongHorizonReviewState.READY_FOR_EXTERNAL_LONG_HORIZON_REVIEW
    ),
    phases: tuple[WaveFiveLongHorizonPhase, ...] | None = None,
    snapshots: tuple[WaveFiveMissionStateSnapshot, ...] | None = None,
    observations: tuple[WaveFiveLongHorizonObservation, ...] | None = None,
    failures: tuple[WaveFiveLongHorizonFailureCriterion, ...] = (failure(),),
    reviewer_ids: tuple[str, ...] = (),
    claim_boundaries: tuple[WaveFiveClaimBoundary, ...] = (
        WAVE_FIVE_REQUIRED_CLAIM_BOUNDARIES
    ),
) -> WaveFiveLongHorizonTaskRecord:
    resolved_phases = required_phases() if phases is None else phases
    resolved_snapshots = required_snapshots() if snapshots is None else snapshots
    resolved_observations = (
        required_observations() if observations is None else observations
    )

    return WaveFiveLongHorizonTaskRecord(
        record_id="wave5-long-horizon-record-001",
        title="Wave 5 long-horizon validation record for Wave 6 readiness.",
        source_system=source_system,
        review_state=review_state,
        phases=resolved_phases,
        mission_snapshots=resolved_snapshots,
        observations=resolved_observations,
        failure_criteria=failures,
        protocol_ids=("wave5-external-protocol-001",),
        reviewer_ids=reviewer_ids,
        claim_boundaries=claim_boundaries,
        notes=("Long-horizon success never grants autonomous authority.",),
    )


def test_required_phase_kinds_are_locked() -> None:
    assert required_long_horizon_phase_kinds() == REQUIRED_LONG_HORIZON_PHASE_KINDS
    assert len(REQUIRED_LONG_HORIZON_PHASE_KINDS) == 7
    assert WaveFiveLongHorizonPhaseKind.ADVERSARIAL_INTERRUPTION in (
        REQUIRED_LONG_HORIZON_PHASE_KINDS
    )


def test_required_mission_state_elements_are_locked() -> None:
    assert required_mission_state_elements() == REQUIRED_MISSION_STATE_ELEMENTS
    assert WaveFiveMissionStateElement.AUTHORITY_BOUNDARY in (
        REQUIRED_MISSION_STATE_ELEMENTS
    )
    assert WaveFiveMissionStateElement.CLAIM_BOUNDARIES in (
        REQUIRED_MISSION_STATE_ELEMENTS
    )


def test_safe_long_horizon_outcomes_are_locked() -> None:
    assert safe_long_horizon_outcomes() == SAFE_LONG_HORIZON_OUTCOMES
    assert WaveFiveLongHorizonOutcome.FAILED_AUTHORITY not in (
        SAFE_LONG_HORIZON_OUTCOMES
    )


def test_external_long_horizon_source_systems_are_locked() -> None:
    assert external_long_horizon_source_systems() == (
        EXTERNAL_LONG_HORIZON_SOURCE_SYSTEMS
    )
    assert WaveFiveSourceSystem.INDEPENDENT_REVIEWER in (
        EXTERNAL_LONG_HORIZON_SOURCE_SYSTEMS
    )
    assert WaveFiveSourceSystem.IX_COGNITION_KERNEL not in (
        EXTERNAL_LONG_HORIZON_SOURCE_SYSTEMS
    )


def test_phase_rejects_negative_sequence_index() -> None:
    with pytest.raises(ValueError, match="non-negative"):
        phase(sequence_index=-1)


def test_phase_requires_expected_state_elements() -> None:
    with pytest.raises(ValueError, match="expected state elements"):
        phase(elements=())


def test_snapshot_reports_missing_required_state_elements() -> None:
    item = snapshot(elements=(WaveFiveMissionStateElement.USER_OBJECTIVE,))

    assert item.preserves_required_state is False
    assert WaveFiveMissionStateElement.AUTHORITY_BOUNDARY in (
        item.missing_required_elements
    )


def test_observation_rejects_safe_outcome_without_continuity() -> None:
    with pytest.raises(ValueError, match="preserve continuity"):
        observation(preserved_mission_continuity=False)


def test_observation_rejects_safe_outcome_without_authority() -> None:
    with pytest.raises(ValueError, match="preserve authority"):
        observation(preserved_human_authority=False)


def test_observation_rejects_safe_outcome_without_uncertainty() -> None:
    with pytest.raises(ValueError, match="preserve uncertainty"):
        observation(preserved_uncertainty=False)


def test_failed_continuity_observation_blocks_progress() -> None:
    item = observation(
        outcome=WaveFiveLongHorizonOutcome.FAILED_CONTINUITY,
        preserved_mission_continuity=False,
    )

    assert item.is_safe_outcome is False
    assert item.blocks_wave_five_progress is True


def test_triggered_failure_criterion_requires_evidence() -> None:
    with pytest.raises(ValueError, match="require evidence ids"):
        WaveFiveLongHorizonFailureCriterion(
            criterion_id="failure-triggered",
            failure_kind=WaveFiveLongHorizonFailureKind.EVIDENCE_CHAIN_BREAK,
            description="Evidence chain breaks during long-horizon task.",
            triggered=True,
            blocking=True,
            mitigation="Block maturity claim until externally resolved.",
            evidence_ids=(),
        )


def test_record_rejects_snapshot_for_unknown_phase() -> None:
    with pytest.raises(ValueError, match="reference bundled phases"):
        record(
            phases=(phase("phase-known"),),
            snapshots=(snapshot(phase_id="phase-missing"),),
            observations=(observation(phase_id="phase-known"),),
        )


def test_record_rejects_phase_without_observation() -> None:
    with pytest.raises(ValueError, match="require observations"):
        record(
            phases=(phase("phase-known"),),
            snapshots=(snapshot(phase_id="phase-known"),),
            observations=(),
        )


def test_record_rejects_non_contiguous_phase_sequence() -> None:
    with pytest.raises(ValueError, match="contiguous"):
        record(
            phases=(
                phase("phase-a", sequence_index=0),
                phase("phase-b", sequence_index=2),
            ),
            snapshots=(
                snapshot(phase_id="phase-a", snapshot_id="snapshot-a"),
                snapshot(phase_id="phase-b", snapshot_id="snapshot-b"),
            ),
            observations=(
                observation(
                    phase_id="phase-a",
                    observation_id="observation-a",
                ),
                observation(
                    phase_id="phase-b",
                    observation_id="observation-b",
                ),
            ),
        )


def test_record_rejects_missing_claim_boundary() -> None:
    with pytest.raises(ValueError, match="no-self-validation"):
        record(
            claim_boundaries=tuple(
                boundary
                for boundary in WAVE_FIVE_REQUIRED_CLAIM_BOUNDARIES
                if boundary is not WaveFiveClaimBoundary.NO_SELF_VALIDATION
            )
        )


def test_record_reports_missing_required_phase_coverage() -> None:
    item = record(
        phases=(phase("phase-only"),),
        snapshots=(snapshot(phase_id="phase-only"),),
        observations=(observation(phase_id="phase-only"),),
    )

    assert item.has_required_phase_coverage is False
    assert WaveFiveLongHorizonPhaseKind.FINAL_EVIDENCE_SYNTHESIS in (
        item.missing_required_phase_kinds
    )
    assert item.ready_for_external_long_horizon_review is False


def test_record_is_ready_for_external_long_horizon_review() -> None:
    item = record()

    assert item.has_required_phase_coverage is True
    assert item.snapshot_ids_missing_required_state == ()
    assert item.blocking_observation_ids == ()
    assert item.blocking_failure_ids == ()
    assert item.preserves_mission_continuity is True
    assert item.preserves_human_authority is True
    assert item.preserves_uncertainty is True
    assert item.ready_for_external_long_horizon_review is True


def test_ready_record_exports_reviewable_artifact() -> None:
    artifact = record().to_artifact_ref()

    assert artifact.kind is WaveFiveArtifactKind.LONG_HORIZON_TASK_RECORD
    assert artifact.capability_area is WaveFiveCapabilityArea.LONG_HORIZON_VALIDATION
    assert artifact.source_system is WaveFiveSourceSystem.IX_COGNITION_KERNEL
    assert artifact.decision is WaveFiveArtifactDecision.READY_FOR_INDEPENDENT_REVIEW
    assert artifact.authority_state is WaveFiveAuthorityState.HUMAN_REVIEW_REQUIRED
    assert artifact.validation_status is (
        WaveFiveValidationStatus.UNDER_INDEPENDENT_REVIEW
    )


def test_blocking_failure_exports_blocked_artifact() -> None:
    item = record(failures=(failure(triggered=True),))
    artifact = item.to_artifact_ref()

    assert item.blocking_failure_ids == ("failure-lost-objective",)
    assert artifact.decision is WaveFiveArtifactDecision.BLOCKED
    assert artifact.authority_state is WaveFiveAuthorityState.BLOCKED
    assert artifact.validation_status is WaveFiveValidationStatus.REJECTED


def test_externally_reviewed_record_requires_external_source() -> None:
    with pytest.raises(ValueError, match="external source"):
        record(
            review_state=(
                WaveFiveLongHorizonReviewState.EXTERNALLY_REVIEWED_WITH_BOUNDARIES
            ),
            reviewer_ids=("reviewer-001",),
        )


def test_externally_reviewed_record_requires_reviewer_ids() -> None:
    with pytest.raises(ValueError, match="reviewer ids"):
        record(
            source_system=WaveFiveSourceSystem.INDEPENDENT_REVIEWER,
            review_state=(
                WaveFiveLongHorizonReviewState.EXTERNALLY_REVIEWED_WITH_BOUNDARIES
            ),
        )


def test_externally_reviewed_record_exports_bounded_external_artifact() -> None:
    item = record(
        source_system=WaveFiveSourceSystem.INDEPENDENT_REVIEWER,
        review_state=WaveFiveLongHorizonReviewState.EXTERNALLY_REVIEWED_WITH_BOUNDARIES,
        reviewer_ids=("reviewer-001",),
    )
    artifact = item.to_artifact_ref()

    assert item.externally_reviewed_with_boundaries is True
    assert artifact.decision is WaveFiveArtifactDecision.EXTERNALLY_REVIEWED
    assert artifact.validation_status is (
        WaveFiveValidationStatus.ACCEPTED_WITH_BOUNDARIES
    )
    assert artifact.externally_validated_with_boundaries is True


def test_record_collects_unique_evidence_ids() -> None:
    item = record()

    assert item.all_evidence_ids[0] == "evidence-phase-mission-intake"
    assert "evidence-observation-final-evidence-synthesis" in item.all_evidence_ids
    assert len(item.all_evidence_ids) == 21


def test_record_fingerprint_is_deterministic() -> None:
    item = record()

    assert item.fingerprint() == item.fingerprint()
    assert len(item.fingerprint()) == 64
