import pytest

from ix_cognition_kernel.wave4_contracts import (
    WaveFourArtifactKind,
    WaveFourCapabilityArea,
)
from ix_cognition_kernel.wave4_mission_state import WaveFourMissionPhaseKind
from ix_cognition_kernel.wave4_trials import (
    WaveFourTrialOutcome,
    WaveFourTrialStatus,
    WaveFourTrialTaskKind,
)
from ix_cognition_kernel.wave4_uncertainty import (
    WaveFourUncertaintyItem,
    WaveFourUncertaintyKind,
    WaveFourUncertaintyOutcome,
    WaveFourUncertaintyPreservationTrace,
    WaveFourUncertaintySnapshot,
    WaveFourUncertaintyStatus,
    WaveFourUncertaintyTransitionCheck,
    passed_uncertainty_check,
    uncertainty_item,
)


def item(
    uncertainty_id: str,
    kind: WaveFourUncertaintyKind = WaveFourUncertaintyKind.EVIDENCE_GAP,
) -> WaveFourUncertaintyItem:
    return uncertainty_item(
        uncertainty_id=uncertainty_id,
        kind=kind,
        statement=f"{uncertainty_id} remains unresolved and must stay visible.",
        evidence_id=f"evidence:{uncertainty_id}",
        caveats=(f"caveat:{uncertainty_id}",),
        confidence_lower_bound=0.20,
        confidence_upper_bound=0.70,
    )


def snapshot(
    snapshot_id: str,
    phase_kind: WaveFourMissionPhaseKind,
    phase_index: int,
) -> WaveFourUncertaintySnapshot:
    return WaveFourUncertaintySnapshot(
        snapshot_id=snapshot_id,
        phase_kind=phase_kind,
        phase_index=phase_index,
        items=(
            item("uncertainty:evidence-gap"),
            item("uncertainty:safety-risk", WaveFourUncertaintyKind.SAFETY_RISK),
        ),
        evidence_ids=(f"evidence:{snapshot_id}",),
    )


def check(
    check_id: str,
    source: str,
    target: str,
) -> WaveFourUncertaintyTransitionCheck:
    return passed_uncertainty_check(
        check_id=check_id,
        from_snapshot_id=source,
        to_snapshot_id=target,
        required_uncertainty_ids=(
            "uncertainty:evidence-gap",
            "uncertainty:safety-risk",
        ),
        preserved_uncertainty_ids=("uncertainty:evidence-gap",),
        escalated_uncertainty_ids=("uncertainty:safety-risk",),
        confidence_drift_by_uncertainty_id={
            "uncertainty:evidence-gap": 0.05,
            "uncertainty:safety-risk": -0.03,
        },
        evidence_id=f"evidence:{check_id}",
    )


def ready_trace() -> WaveFourUncertaintyPreservationTrace:
    return WaveFourUncertaintyPreservationTrace(
        trace_id="uncertainty-trace-001",
        snapshots=(
            snapshot("snapshot-intake", WaveFourMissionPhaseKind.INTAKE, 0),
            snapshot("snapshot-planning", WaveFourMissionPhaseKind.PLANNING, 1),
            snapshot("snapshot-review", WaveFourMissionPhaseKind.REVIEW, 2),
        ),
        transition_checks=(
            check("check-intake-planning", "snapshot-intake", "snapshot-planning"),
            check("check-planning-review", "snapshot-planning", "snapshot-review"),
        ),
        scenario_ids=("worldtwin:uncertainty-preservation",),
        blackfox_receipt_ids=("blackfox:uncertainty-preservation-review",),
    )


def test_uncertainty_item_requires_confidence_bounds_evidence_and_caveats() -> None:
    with pytest.raises(ValueError, match="lower bound cannot exceed upper"):
        WaveFourUncertaintyItem(
            uncertainty_id="uncertainty-invalid",
            kind=WaveFourUncertaintyKind.ASSUMPTION,
            statement="Invalid confidence interval.",
            confidence_lower_bound=0.80,
            confidence_upper_bound=0.40,
            evidence_ids=("evidence:uncertainty-invalid",),
            caveats=("invalid caveat",),
        )

    with pytest.raises(ValueError, match="uncertainty items require evidence ids"):
        WaveFourUncertaintyItem(
            uncertainty_id="uncertainty-invalid",
            kind=WaveFourUncertaintyKind.ASSUMPTION,
            statement="Invalid missing evidence.",
            confidence_lower_bound=0.20,
            confidence_upper_bound=0.40,
            evidence_ids=(),
            caveats=("invalid caveat",),
        )

    with pytest.raises(ValueError, match="uncertainty items require caveats"):
        WaveFourUncertaintyItem(
            uncertainty_id="uncertainty-invalid",
            kind=WaveFourUncertaintyKind.ASSUMPTION,
            statement="Invalid missing caveat.",
            confidence_lower_bound=0.20,
            confidence_upper_bound=0.40,
            evidence_ids=("evidence:uncertainty-invalid",),
            caveats=(),
        )


def test_uncertainty_snapshot_requires_items_and_evidence() -> None:
    with pytest.raises(ValueError, match="uncertainty snapshots require items"):
        WaveFourUncertaintySnapshot(
            snapshot_id="snapshot-invalid",
            phase_kind=WaveFourMissionPhaseKind.INTAKE,
            phase_index=0,
            items=(),
            evidence_ids=("evidence:snapshot-invalid",),
        )

    with pytest.raises(ValueError, match="uncertainty snapshots require evidence ids"):
        WaveFourUncertaintySnapshot(
            snapshot_id="snapshot-invalid",
            phase_kind=WaveFourMissionPhaseKind.INTAKE,
            phase_index=0,
            items=(item("uncertainty:one"),),
            evidence_ids=(),
        )


def test_uncertainty_snapshot_sorts_items_and_reports_evidence() -> None:
    snap = WaveFourUncertaintySnapshot(
        snapshot_id="snapshot-one",
        phase_kind=WaveFourMissionPhaseKind.INTAKE,
        phase_index=0,
        items=(item("uncertainty:b"), item("uncertainty:a")),
        evidence_ids=("evidence:snapshot-one",),
    )

    assert snap.uncertainty_ids == ("uncertainty:a", "uncertainty:b")
    assert snap.item_evidence_ids == (
        "evidence:uncertainty:a",
        "evidence:uncertainty:b",
    )
    assert snap.item_by_id("uncertainty:a").uncertainty_id == "uncertainty:a"


def test_uncertainty_check_rejects_same_snapshot_and_empty_required_ids() -> None:
    with pytest.raises(ValueError, match="require different snapshots"):
        passed_uncertainty_check(
            check_id="check-invalid",
            from_snapshot_id="snapshot-a",
            to_snapshot_id="snapshot-a",
            required_uncertainty_ids=("uncertainty:one",),
            preserved_uncertainty_ids=("uncertainty:one",),
            evidence_id="evidence:check-invalid",
        )

    with pytest.raises(ValueError, match="checks require uncertainty ids"):
        passed_uncertainty_check(
            check_id="check-invalid",
            from_snapshot_id="snapshot-a",
            to_snapshot_id="snapshot-b",
            required_uncertainty_ids=(),
            preserved_uncertainty_ids=(),
            evidence_id="evidence:check-invalid",
        )


def test_passed_uncertainty_check_cannot_erase_or_omit_uncertainty() -> None:
    with pytest.raises(ValueError, match="cannot erase or omit uncertainty"):
        WaveFourUncertaintyTransitionCheck(
            check_id="check-invalid-erase",
            from_snapshot_id="snapshot-a",
            to_snapshot_id="snapshot-b",
            required_uncertainty_ids=("uncertainty:one",),
            preserved_uncertainty_ids=(),
            escalated_uncertainty_ids=(),
            resolved_uncertainty_ids=(),
            erased_uncertainty_ids=("uncertainty:one",),
            confidence_drift_by_uncertainty_id={},
            evidence_ids=("evidence:check-invalid-erase",),
            passed=True,
        )

    with pytest.raises(ValueError, match="cannot erase or omit uncertainty"):
        WaveFourUncertaintyTransitionCheck(
            check_id="check-invalid-missing",
            from_snapshot_id="snapshot-a",
            to_snapshot_id="snapshot-b",
            required_uncertainty_ids=("uncertainty:one",),
            preserved_uncertainty_ids=(),
            escalated_uncertainty_ids=(),
            resolved_uncertainty_ids=(),
            erased_uncertainty_ids=(),
            confidence_drift_by_uncertainty_id={},
            evidence_ids=("evidence:check-invalid-missing",),
            passed=True,
        )


def test_passed_uncertainty_check_cannot_exceed_confidence_drift() -> None:
    with pytest.raises(ValueError, match="cannot exceed confidence drift"):
        WaveFourUncertaintyTransitionCheck(
            check_id="check-invalid-drift",
            from_snapshot_id="snapshot-a",
            to_snapshot_id="snapshot-b",
            required_uncertainty_ids=("uncertainty:one",),
            preserved_uncertainty_ids=("uncertainty:one",),
            escalated_uncertainty_ids=(),
            resolved_uncertainty_ids=(),
            erased_uncertainty_ids=(),
            confidence_drift_by_uncertainty_id={"uncertainty:one": 0.45},
            evidence_ids=("evidence:check-invalid-drift",),
            passed=True,
            max_allowed_confidence_drift=0.20,
        )


def test_failed_uncertainty_check_reports_erasure_and_drift_reasons() -> None:
    failed = WaveFourUncertaintyTransitionCheck(
        check_id="check-failed",
        from_snapshot_id="snapshot-a",
        to_snapshot_id="snapshot-b",
        required_uncertainty_ids=("uncertainty:one", "uncertainty:two"),
        preserved_uncertainty_ids=("uncertainty:one",),
        escalated_uncertainty_ids=(),
        resolved_uncertainty_ids=(),
        erased_uncertainty_ids=("uncertainty:two",),
        confidence_drift_by_uncertainty_id={"uncertainty:one": 0.35},
        evidence_ids=("evidence:check-failed",),
        passed=False,
    )

    assert failed.failure_reasons == (
        "erased: uncertainty:two",
        "confidence drift: uncertainty:one",
    )
    assert "uncertainty preservation failed" in failed.readiness_gap


def test_uncertainty_check_rejects_overlapping_dispositions() -> None:
    with pytest.raises(ValueError, match="disposition is not disjoint"):
        WaveFourUncertaintyTransitionCheck(
            check_id="check-overlap",
            from_snapshot_id="snapshot-a",
            to_snapshot_id="snapshot-b",
            required_uncertainty_ids=("uncertainty:one",),
            preserved_uncertainty_ids=("uncertainty:one",),
            escalated_uncertainty_ids=("uncertainty:one",),
            resolved_uncertainty_ids=(),
            erased_uncertainty_ids=(),
            confidence_drift_by_uncertainty_id={},
            evidence_ids=("evidence:check-overlap",),
            passed=True,
        )


def test_ready_uncertainty_trace_confirms_preservation_without_overclaim() -> None:
    trace = ready_trace()

    assert trace.status is WaveFourUncertaintyStatus.READY_FOR_CONTROLLED_REVIEW
    assert trace.outcome is WaveFourUncertaintyOutcome.PRESERVATION_CONFIRMED
    assert trace.ready_for_controlled_review is True
    assert trace.snapshot_ids == (
        "snapshot-intake",
        "snapshot-planning",
        "snapshot-review",
    )
    assert trace.failed_check_ids == ()
    assert trace.missing_transition_keys == ()
    assert trace.readiness_gaps == ()
    assert trace.permits_automatic_execution is False
    assert trace.claims_agi is False
    assert "no AGI claim" in trace.review_summary


def test_uncertainty_trace_sorts_snapshots_and_checks_deterministically() -> None:
    first = ready_trace()
    second = WaveFourUncertaintyPreservationTrace(
        trace_id="uncertainty-trace-001",
        snapshots=tuple(reversed(first.snapshots)),
        transition_checks=tuple(reversed(first.transition_checks)),
        scenario_ids=("worldtwin:uncertainty-preservation",),
        blackfox_receipt_ids=("blackfox:uncertainty-preservation-review",),
    )

    assert first.snapshot_ids == second.snapshot_ids
    assert first.fingerprint() == second.fingerprint()
    assert len(first.fingerprint()) == 64


def test_uncertainty_trace_reports_missing_transition_and_receipts() -> None:
    trace = WaveFourUncertaintyPreservationTrace(
        trace_id="trace-missing-transition",
        snapshots=ready_trace().snapshots,
        transition_checks=(
            check("check-intake-planning", "snapshot-intake", "snapshot-planning"),
        ),
        scenario_ids=(),
        blackfox_receipt_ids=(),
    )

    assert trace.status is WaveFourUncertaintyStatus.NEEDS_EVIDENCE
    assert trace.outcome is WaveFourUncertaintyOutcome.NEEDS_EVIDENCE
    assert trace.missing_transition_keys == (("snapshot-planning", "snapshot-review"),)
    assert "missing uncertainty transition checks" in trace.readiness_gaps[0]
    assert (
        "trace-missing-transition has no WorldTwin scenario ids" in trace.readiness_gaps
    )
    assert (
        "trace-missing-transition has no BlackFox review receipt ids"
        in trace.readiness_gaps
    )


def test_uncertainty_trace_detects_erasure_as_repair_need() -> None:
    failed = WaveFourUncertaintyTransitionCheck(
        check_id="check-erasure",
        from_snapshot_id="snapshot-intake",
        to_snapshot_id="snapshot-planning",
        required_uncertainty_ids=("uncertainty:evidence-gap",),
        preserved_uncertainty_ids=(),
        escalated_uncertainty_ids=(),
        resolved_uncertainty_ids=(),
        erased_uncertainty_ids=("uncertainty:evidence-gap",),
        confidence_drift_by_uncertainty_id={},
        evidence_ids=("evidence:check-erasure",),
        passed=False,
    )
    trace = WaveFourUncertaintyPreservationTrace(
        trace_id="trace-erasure",
        snapshots=ready_trace().snapshots,
        transition_checks=(
            failed,
            check("check-planning-review", "snapshot-planning", "snapshot-review"),
        ),
        scenario_ids=("worldtwin:uncertainty-preservation",),
        blackfox_receipt_ids=("blackfox:uncertainty-preservation-review",),
    )

    assert trace.status is WaveFourUncertaintyStatus.NEEDS_REPAIR
    assert trace.outcome is WaveFourUncertaintyOutcome.UNCERTAINTY_ERASURE_DETECTED
    assert trace.failed_check_ids == ("check-erasure",)
    assert "check-erasure uncertainty preservation failed" in trace.readiness_gaps[0]


def test_blocked_uncertainty_trace_cannot_carry_results() -> None:
    with pytest.raises(ValueError, match="cannot carry results"):
        WaveFourUncertaintyPreservationTrace(
            trace_id="trace-blocked-invalid",
            snapshots=ready_trace().snapshots,
            transition_checks=ready_trace().transition_checks,
            scenario_ids=("worldtwin:uncertainty-preservation",),
            blackfox_receipt_ids=("blackfox:uncertainty-preservation-review",),
            blocked_reasons=("uncertainty evidence was contradicted",),
        )

    trace = WaveFourUncertaintyPreservationTrace(
        trace_id="trace-blocked",
        snapshots=ready_trace().snapshots,
        transition_checks=(),
        scenario_ids=("worldtwin:uncertainty-preservation",),
        blackfox_receipt_ids=("blackfox:uncertainty-preservation-review",),
        blocked_reasons=("uncertainty evidence was contradicted",),
    )

    assert trace.status is WaveFourUncertaintyStatus.BLOCKED
    assert trace.outcome is WaveFourUncertaintyOutcome.BLOCKED
    assert trace.blocking_gaps == (
        "trace-blocked blocked: uncertainty evidence was contradicted",
    )


def test_uncertainty_trace_rejects_execution_agi_and_independent_validation() -> None:
    with pytest.raises(ValueError, match="cannot permit execution"):
        WaveFourUncertaintyPreservationTrace(
            trace_id="invalid-execution",
            snapshots=ready_trace().snapshots,
            transition_checks=(),
            scenario_ids=(),
            blackfox_receipt_ids=(),
            permits_automatic_execution=True,
        )

    with pytest.raises(ValueError, match="cannot claim AGI"):
        WaveFourUncertaintyPreservationTrace(
            trace_id="invalid-agi",
            snapshots=ready_trace().snapshots,
            transition_checks=(),
            scenario_ids=(),
            blackfox_receipt_ids=(),
            claims_agi=True,
        )

    with pytest.raises(ValueError, match="cannot claim independent validation"):
        WaveFourUncertaintyPreservationTrace(
            trace_id="invalid-independent-validation",
            snapshots=ready_trace().snapshots,
            transition_checks=(),
            scenario_ids=(),
            blackfox_receipt_ids=(),
            independently_validated=True,
        )


def test_uncertainty_trace_converts_to_shared_artifact_and_bundle() -> None:
    trace = ready_trace()
    artifact = trace.to_artifact_ref()
    bundle = trace.to_artifact_bundle()

    assert artifact.kind is WaveFourArtifactKind.UNCERTAINTY_TRACE
    assert artifact.capability_area is WaveFourCapabilityArea.UNCERTAINTY_PRESERVATION
    assert artifact.ready_for_controlled_review is True
    assert artifact.allowed_for_automatic_execution is False
    assert artifact.claims_agi is False
    assert len(trace.evidence_links()) == 7
    assert bundle.has_required_kind_coverage is True
    assert bundle.has_required_capability_coverage is True
    assert bundle.ready_for_controlled_review_artifact_ids == (artifact.artifact_id,)


def test_uncertainty_trace_converts_to_controlled_trial_task() -> None:
    task = ready_trace().to_controlled_task()

    assert task.task_kind is WaveFourTrialTaskKind.UNCERTAINTY_PRESERVATION_PROBE
    assert task.outcome is WaveFourTrialOutcome.PASSED
    assert task.status is WaveFourTrialStatus.READY_FOR_CONTROLLED_REVIEW
    assert task.ready_for_controlled_review is True
    assert task.scenario_ids == ("worldtwin:uncertainty-preservation",)
    assert task.blackfox_receipt_ids == ("blackfox:uncertainty-preservation-review",)
    assert len(task.measurements) == 2


def test_failed_uncertainty_trace_converts_to_failed_trial_task() -> None:
    failed = WaveFourUncertaintyTransitionCheck(
        check_id="check-erasure",
        from_snapshot_id="snapshot-intake",
        to_snapshot_id="snapshot-planning",
        required_uncertainty_ids=("uncertainty:evidence-gap",),
        preserved_uncertainty_ids=(),
        escalated_uncertainty_ids=(),
        resolved_uncertainty_ids=(),
        erased_uncertainty_ids=("uncertainty:evidence-gap",),
        confidence_drift_by_uncertainty_id={},
        evidence_ids=("evidence:check-erasure",),
        passed=False,
    )
    trace = WaveFourUncertaintyPreservationTrace(
        trace_id="trace-erasure",
        snapshots=ready_trace().snapshots,
        transition_checks=(
            failed,
            check("check-planning-review", "snapshot-planning", "snapshot-review"),
        ),
        scenario_ids=("worldtwin:uncertainty-preservation",),
        blackfox_receipt_ids=("blackfox:uncertainty-preservation-review",),
    )
    task = trace.to_controlled_task()

    assert task.outcome is WaveFourTrialOutcome.FAILED
    assert task.status is WaveFourTrialStatus.NEEDS_REPAIR
    assert task.failed_measurement_ids == ("uncertainty-preservation:check-erasure",)
