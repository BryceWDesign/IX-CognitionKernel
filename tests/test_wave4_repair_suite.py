import pytest

from ix_cognition_kernel.wave4_contracts import (
    WaveFourArtifactKind,
    WaveFourCapabilityArea,
    WaveFourEvidenceRelation,
)
from ix_cognition_kernel.wave4_failure_repair import (
    WaveFourFailureMode,
    WaveFourFailureObservation,
    WaveFourFailureRepairCycle,
    WaveFourRepairAction,
    WaveFourRepairOutcome,
    WaveFourRepairStatus,
    failed_observation,
    passed_rerun_observation,
)
from ix_cognition_kernel.wave4_repair_suite import (
    WaveFourFailureRepairSuite,
    WaveFourRepairNegativeControl,
    WaveFourRepairNegativeControlMode,
)
from ix_cognition_kernel.wave4_trials import (
    WaveFourTrialStatus,
    WaveFourTrialTaskKind,
)


def initial_failure(
    observation_id: str = "observation-hidden-uncertainty-initial",
    *,
    task_id: str = "repair-task-hidden-uncertainty",
    score: float = 0.40,
    failure_modes: tuple[WaveFourFailureMode, ...] = (
        WaveFourFailureMode.HIDDEN_UNCERTAINTY,
    ),
) -> WaveFourFailureObservation:
    return failed_observation(
        observation_id=observation_id,
        task_id=task_id,
        observed_behavior="The first attempt hid uncertainty from the review record.",
        score=score,
        evidence_id=f"evidence:{observation_id}",
        failure_modes=failure_modes,
        uncertainty_notes=("initial failure remains visible",),
    )


def repair_action(
    repair_id: str = "repair-restore-uncertainty",
    *,
    failed_observation_id: str = "observation-hidden-uncertainty-initial",
) -> WaveFourRepairAction:
    return WaveFourRepairAction(
        repair_id=repair_id,
        failed_observation_id=failed_observation_id,
        repair_summary="Restore uncertainty notes and evidence visibility.",
        expected_effect="The re-run preserves uncertainty and improves score.",
        bounded_changes=(
            "require explicit uncertainty note",
            "preserve failed-attempt evidence id",
        ),
        rollback_plan="Rollback to the pre-repair review record if evidence is lost.",
        evidence_ids=(f"evidence:{repair_id}",),
    )


def rerun_observation(
    observation_id: str = "observation-hidden-uncertainty-rerun",
    *,
    task_id: str = "repair-task-hidden-uncertainty",
    score: float = 0.72,
) -> WaveFourFailureObservation:
    return passed_rerun_observation(
        observation_id=observation_id,
        task_id=task_id,
        observed_behavior="The re-run preserved uncertainty and evidence ids.",
        score=score,
        evidence_id=f"evidence:{observation_id}",
        uncertainty_notes=("limitations preserved after repair",),
    )


def repair_cycle(
    cycle_id: str = "cycle-hidden-uncertainty",
    *,
    failure_modes: tuple[WaveFourFailureMode, ...] = (
        WaveFourFailureMode.HIDDEN_UNCERTAINTY,
    ),
    initial_score: float = 0.40,
    rerun_score: float = 0.72,
    scenario_ids: tuple[str, ...] = ("worldtwin:hidden-uncertainty-repair",),
    blackfox_receipt_ids: tuple[str, ...] = ("blackfox:hidden-uncertainty-repair",),
) -> WaveFourFailureRepairCycle:
    initial = initial_failure(
        observation_id=f"observation:{cycle_id}:initial",
        task_id=f"task:{cycle_id}",
        score=initial_score,
        failure_modes=failure_modes,
    )
    return WaveFourFailureRepairCycle(
        cycle_id=cycle_id,
        initial_observation=initial,
        repair_actions=(
            repair_action(
                repair_id=f"repair:{cycle_id}",
                failed_observation_id=initial.observation_id,
            ),
        ),
        rerun_observations=(
            rerun_observation(
                observation_id=f"observation:{cycle_id}:rerun",
                task_id=initial.task_id,
                score=rerun_score,
            ),
        ),
        scenario_ids=scenario_ids,
        blackfox_receipt_ids=blackfox_receipt_ids,
    )


def negative_control(
    control_id: str = "control-suppressed-uncertainty",
    *,
    cycle_id: str = "cycle-hidden-uncertainty",
    detected: bool = True,
    repair_guidance: str = "Reject repair if uncertainty notes are removed.",
) -> WaveFourRepairNegativeControl:
    return WaveFourRepairNegativeControl(
        control_id=control_id,
        cycle_id=cycle_id,
        mode=WaveFourRepairNegativeControlMode.SUPPRESSED_UNCERTAINTY,
        injected_invalid_behavior="The invalid repair suppresses uncertainty notes.",
        expected_detection="Repair review detects suppressed uncertainty.",
        evidence_ids=(f"evidence:{control_id}",),
        detected=detected,
        repair_guidance=repair_guidance,
    )


def ready_suite() -> WaveFourFailureRepairSuite:
    return WaveFourFailureRepairSuite(
        suite_id="repair-suite-001",
        cycles=(
            repair_cycle(),
            repair_cycle(
                "cycle-missing-evidence",
                failure_modes=(WaveFourFailureMode.MISSING_EVIDENCE,),
                initial_score=0.35,
                rerun_score=0.68,
                scenario_ids=("worldtwin:missing-evidence-repair",),
                blackfox_receipt_ids=("blackfox:missing-evidence-repair",),
            ),
        ),
        negative_controls=(
            negative_control(),
            negative_control(
                "control-weakened-evidence-gate",
                cycle_id="cycle-missing-evidence",
                repair_guidance="Reject repair if evidence gates are weakened.",
            ),
        ),
        required_failure_modes=(
            WaveFourFailureMode.HIDDEN_UNCERTAINTY,
            WaveFourFailureMode.MISSING_EVIDENCE,
        ),
        min_ready_cycles=2,
        min_average_improvement_delta=0.20,
        notes=("Failure-repair suite remains review-only.",),
    )


def test_negative_control_requires_evidence() -> None:
    with pytest.raises(ValueError, match="negative controls require evidence ids"):
        WaveFourRepairNegativeControl(
            control_id="control-invalid",
            cycle_id="cycle-hidden-uncertainty",
            mode=WaveFourRepairNegativeControlMode.SUPPRESSED_UNCERTAINTY,
            injected_invalid_behavior="Invalid repair hides uncertainty.",
            expected_detection="The review should detect uncertainty suppression.",
            evidence_ids=(),
            detected=True,
            repair_guidance="Restore uncertainty evidence.",
        )


def test_detected_negative_control_requires_repair_guidance() -> None:
    with pytest.raises(ValueError, match="require repair guidance"):
        negative_control(repair_guidance="")


def test_detected_negative_control_is_resolved() -> None:
    control = negative_control()

    assert control.resolved is True
    assert control.readiness_gap == ""
    assert len(control.fingerprint()) == 64


def test_undetected_negative_control_reports_repair_gap() -> None:
    control = negative_control(
        "control-undetected-suppression",
        detected=False,
        repair_guidance="",
    )

    assert control.resolved is False
    assert control.readiness_gap == (
        "control-undetected-suppression was not detected by repair review"
    )


def test_repair_suite_requires_cycles_and_failure_mode_coverage() -> None:
    with pytest.raises(ValueError, match="require repair cycles"):
        WaveFourFailureRepairSuite(
            suite_id="invalid-suite",
            cycles=(),
            negative_controls=(),
            required_failure_modes=(WaveFourFailureMode.HIDDEN_UNCERTAINTY,),
        )

    with pytest.raises(ValueError, match="require failure-mode coverage"):
        WaveFourFailureRepairSuite(
            suite_id="invalid-suite",
            cycles=(repair_cycle(),),
            negative_controls=(),
            required_failure_modes=(),
        )


def test_repair_suite_rejects_duplicate_cycle_ids() -> None:
    cycle = repair_cycle()

    with pytest.raises(ValueError, match="Duplicate cycle_id"):
        WaveFourFailureRepairSuite(
            suite_id="invalid-suite",
            cycles=(cycle, cycle),
            negative_controls=(),
            required_failure_modes=(WaveFourFailureMode.HIDDEN_UNCERTAINTY,),
        )


def test_repair_suite_rejects_negative_control_for_unknown_cycle() -> None:
    with pytest.raises(ValueError, match="must reference bundled cycles"):
        WaveFourFailureRepairSuite(
            suite_id="invalid-suite",
            cycles=(repair_cycle(),),
            negative_controls=(
                negative_control(cycle_id="cycle-missing-from-suite"),
            ),
            required_failure_modes=(WaveFourFailureMode.HIDDEN_UNCERTAINTY,),
        )


def test_repair_suite_rejects_execution_agi_and_independent_validation() -> None:
    with pytest.raises(ValueError, match="cannot permit execution"):
        WaveFourFailureRepairSuite(
            suite_id="invalid-execution",
            cycles=(repair_cycle(),),
            negative_controls=(),
            required_failure_modes=(WaveFourFailureMode.HIDDEN_UNCERTAINTY,),
            permits_automatic_execution=True,
        )

    with pytest.raises(ValueError, match="cannot claim AGI"):
        WaveFourFailureRepairSuite(
            suite_id="invalid-agi",
            cycles=(repair_cycle(),),
            negative_controls=(),
            required_failure_modes=(WaveFourFailureMode.HIDDEN_UNCERTAINTY,),
            claims_agi=True,
        )

    with pytest.raises(ValueError, match="cannot claim independent validation"):
        WaveFourFailureRepairSuite(
            suite_id="invalid-independent-validation",
            cycles=(repair_cycle(),),
            negative_controls=(),
            required_failure_modes=(WaveFourFailureMode.HIDDEN_UNCERTAINTY,),
            independently_validated=True,
        )


def test_ready_repair_suite_has_required_coverage_and_negative_controls() -> None:
    suite = ready_suite()

    assert suite.status is WaveFourRepairStatus.READY_FOR_CONTROLLED_REVIEW
    assert suite.ready_for_controlled_review is True
    assert suite.ready_cycle_ids == (
        "cycle-hidden-uncertainty",
        "cycle-missing-evidence",
    )
    assert suite.evidence_gap_cycle_ids == ()
    assert suite.repair_cycle_ids == ()
    assert suite.blocked_cycle_ids == ()
    assert suite.covered_failure_modes == (
        WaveFourFailureMode.HIDDEN_UNCERTAINTY,
        WaveFourFailureMode.MISSING_EVIDENCE,
    )
    assert suite.missing_required_failure_modes == ()
    assert suite.average_improvement_delta == 0.325
    assert suite.resolved_negative_control_ids == (
        "control-suppressed-uncertainty",
        "control-weakened-evidence-gate",
    )
    assert suite.unresolved_negative_control_ids == ()
    assert suite.readiness_gaps == ()
    assert suite.permits_automatic_execution is False
    assert suite.claims_agi is False
    assert suite.independently_validated is False
    assert "no AGI claim" in suite.review_summary


def test_repair_suite_reports_missing_required_failure_modes() -> None:
    suite = WaveFourFailureRepairSuite(
        suite_id="repair-suite-missing-mode",
        cycles=(repair_cycle(),),
        negative_controls=(negative_control(),),
        required_failure_modes=(
            WaveFourFailureMode.HIDDEN_UNCERTAINTY,
            WaveFourFailureMode.MISSING_EVIDENCE,
        ),
        min_ready_cycles=1,
    )

    assert suite.status is WaveFourRepairStatus.NEEDS_EVIDENCE
    assert suite.missing_required_failure_modes == (
        WaveFourFailureMode.MISSING_EVIDENCE,
    )
    assert "missing required failure modes" in suite.readiness_gaps[0]


def test_repair_suite_needs_evidence_when_ready_cycle_count_is_too_low() -> None:
    evidence_gap_cycle = WaveFourFailureRepairCycle(
        cycle_id="cycle-evidence-gap",
        initial_observation=initial_failure(
            observation_id="observation:evidence-gap:initial",
            task_id="task:evidence-gap",
        ),
        repair_actions=(),
        rerun_observations=(),
        scenario_ids=("worldtwin:evidence-gap",),
        blackfox_receipt_ids=("blackfox:evidence-gap",),
    )
    suite = WaveFourFailureRepairSuite(
        suite_id="repair-suite-low-ready-count",
        cycles=(repair_cycle(), evidence_gap_cycle),
        negative_controls=(negative_control(),),
        required_failure_modes=(WaveFourFailureMode.HIDDEN_UNCERTAINTY,),
        min_ready_cycles=2,
    )

    assert suite.status is WaveFourRepairStatus.NEEDS_EVIDENCE
    assert suite.ready_cycle_ids == ("cycle-hidden-uncertainty",)
    assert suite.evidence_gap_cycle_ids == ("cycle-evidence-gap",)
    assert "ready repair cycles below minimum" in suite.readiness_gaps[0]


def test_repair_suite_needs_repair_for_unresolved_negative_control() -> None:
    suite = WaveFourFailureRepairSuite(
        suite_id="repair-suite-unresolved-control",
        cycles=(repair_cycle(),),
        negative_controls=(
            negative_control(
                "control-undetected-suppression",
                detected=False,
                repair_guidance="",
            ),
        ),
        required_failure_modes=(WaveFourFailureMode.HIDDEN_UNCERTAINTY,),
        min_ready_cycles=1,
    )

    assert suite.status is WaveFourRepairStatus.NEEDS_REPAIR
    assert suite.unresolved_negative_control_ids == ("control-undetected-suppression",)
    assert (
        "control-undetected-suppression was not detected by repair review"
        in suite.readiness_gaps
    )


def test_repair_suite_needs_repair_when_cycle_needs_repair() -> None:
    weak_cycle = repair_cycle(
        "cycle-weak-repair",
        initial_score=0.40,
        rerun_score=0.43,
    )
    suite = WaveFourFailureRepairSuite(
        suite_id="repair-suite-weak-cycle",
        cycles=(weak_cycle,),
        negative_controls=(
            negative_control(
                cycle_id="cycle-weak-repair",
            ),
        ),
        required_failure_modes=(WaveFourFailureMode.HIDDEN_UNCERTAINTY,),
        min_ready_cycles=1,
    )

    assert weak_cycle.status is WaveFourRepairStatus.NEEDS_REPAIR
    assert weak_cycle.outcome is WaveFourRepairOutcome.NO_MEASURED_IMPROVEMENT
    assert suite.status is WaveFourRepairStatus.NEEDS_REPAIR
    assert suite.repair_cycle_ids == ("cycle-weak-repair",)


def test_repair_suite_blocks_when_cycle_is_blocked() -> None:
    initial = initial_failure(
        observation_id="observation:blocked:initial",
        task_id="task:blocked",
    )
    blocked_cycle = WaveFourFailureRepairCycle(
        cycle_id="cycle-blocked",
        initial_observation=initial,
        repair_actions=(),
        rerun_observations=(),
        scenario_ids=("worldtwin:blocked",),
        blackfox_receipt_ids=("blackfox:blocked",),
        blocked_reasons=("initial failure evidence was contradicted",),
    )
    suite = WaveFourFailureRepairSuite(
        suite_id="repair-suite-blocked",
        cycles=(blocked_cycle,),
        negative_controls=(),
        required_failure_modes=(WaveFourFailureMode.HIDDEN_UNCERTAINTY,),
        min_ready_cycles=1,
    )

    assert suite.status is WaveFourRepairStatus.BLOCKED
    assert suite.blocked_cycle_ids == ("cycle-blocked",)
    assert "cycle-blocked blocked: initial failure evidence was contradicted" in (
        suite.readiness_gaps
    )


def test_repair_suite_converts_to_trial_protocol() -> None:
    protocol = ready_suite().to_trial_protocol()

    assert protocol.status is WaveFourTrialStatus.READY_FOR_CONTROLLED_REVIEW
    assert protocol.ready_for_controlled_review is True
    assert protocol.task_ids == (
        "failure-repair:cycle-hidden-uncertainty",
        "failure-repair:cycle-missing-evidence",
    )
    assert protocol.required_task_kinds == (
        WaveFourTrialTaskKind.FAILURE_REPAIR_PROBE,
    )


def test_repair_suite_converts_to_shared_artifact_bundle() -> None:
    bundle = ready_suite().to_artifact_bundle()

    assert bundle.has_required_kind_coverage is True
    assert bundle.has_required_capability_coverage is True
    assert len(bundle.artifacts) == 2
    assert {artifact.kind for artifact in bundle.artifacts} == {
        WaveFourArtifactKind.FAILURE_REPAIR_CYCLE
    }
    assert {artifact.capability_area for artifact in bundle.artifacts} == {
        WaveFourCapabilityArea.SELF_IMPROVEMENT_AFTER_FAILURE
    }
    assert len(bundle.ready_for_controlled_review_artifact_ids) == 2
    control_links = tuple(
        link
        for link in bundle.evidence_links
        if link.evidence_id.startswith("evidence:control")
    )
    assert len(control_links) == 2
    assert {link.relation for link in control_links} == {WaveFourEvidenceRelation.TESTS}


def test_repair_suite_can_return_cycle_and_negative_controls_by_id() -> None:
    suite = ready_suite()

    assert suite.cycle_by_id("cycle-hidden-uncertainty").cycle_id == (
        "cycle-hidden-uncertainty"
    )
    assert tuple(
        control.control_id
        for control in suite.negative_controls_for_cycle("cycle-hidden-uncertainty")
    ) == ("control-suppressed-uncertainty",)

    with pytest.raises(ValueError, match="Unknown Wave 4 repair cycle_id"):
        suite.cycle_by_id("missing-cycle")


def test_repair_suite_fingerprint_is_deterministic_despite_input_order() -> None:
    first = ready_suite()
    second = WaveFourFailureRepairSuite(
        suite_id="repair-suite-001",
        cycles=tuple(reversed(first.cycles)),
        negative_controls=tuple(reversed(first.negative_controls)),
        required_failure_modes=first.required_failure_modes,
        min_ready_cycles=2,
        min_average_improvement_delta=0.20,
        notes=("Failure-repair suite remains review-only.",),
    )

    assert first.cycle_ids == second.cycle_ids
    assert first.fingerprint() == second.fingerprint()
    assert len(first.fingerprint()) == 64
