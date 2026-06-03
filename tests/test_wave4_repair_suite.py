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
    observation_id: str,
    task_id: str,
    mode: WaveFourFailureMode,
    *,
    score: float = 0.30,
) -> WaveFourFailureObservation:
    return failed_observation(
        observation_id=observation_id,
        task_id=task_id,
        observed_behavior=f"Initial attempt exposed {mode.value}.",
        score=score,
        evidence_id=f"evidence:{observation_id}",
        failure_modes=(mode,),
    )


def repair_action(
    repair_id: str,
    failed_observation_id: str,
) -> WaveFourRepairAction:
    return WaveFourRepairAction(
        repair_id=repair_id,
        failed_observation_id=failed_observation_id,
        repair_summary="Apply a bounded evaluator repair with evidence retained.",
        expected_effect="The re-run improves without hiding limitations.",
        bounded_changes=(
            "tighten the evidence gate",
            "preserve original failure evidence",
        ),
        rollback_plan="Restore the previous evaluator rule if regression appears.",
        evidence_ids=(f"evidence:{repair_id}",),
    )


def rerun(
    observation_id: str,
    task_id: str,
    *,
    score: float = 0.74,
) -> WaveFourFailureObservation:
    return passed_rerun_observation(
        observation_id=observation_id,
        task_id=task_id,
        observed_behavior="The re-run preserved evidence and improved the score.",
        score=score,
        evidence_id=f"evidence:{observation_id}",
    )


def cycle(
    cycle_id: str,
    mode: WaveFourFailureMode,
    *,
    score_before: float = 0.30,
    score_after: float = 0.74,
) -> WaveFourFailureRepairCycle:
    failed = initial_failure(
        f"failure:{cycle_id}",
        f"task:{cycle_id}",
        mode,
        score=score_before,
    )
    return WaveFourFailureRepairCycle(
        cycle_id=cycle_id,
        initial_observation=failed,
        repair_actions=(repair_action(f"repair:{cycle_id}", failed.observation_id),),
        rerun_observations=(
            rerun(f"rerun:{cycle_id}", failed.task_id, score=score_after),
        ),
        scenario_ids=(f"worldtwin:{cycle_id}",),
        blackfox_receipt_ids=(f"blackfox:{cycle_id}",),
        minimum_improvement_delta=0.15,
    )


def negative_control(
    control_id: str,
    cycle_id: str,
    *,
    detected: bool = True,
    repair_guidance: str = "Reject the invalid repair and restore the gate.",
) -> WaveFourRepairNegativeControl:
    return WaveFourRepairNegativeControl(
        control_id=control_id,
        cycle_id=cycle_id,
        mode=WaveFourRepairNegativeControlMode.WEAKENED_EVIDENCE_GATE,
        injected_invalid_behavior="The repair tried to weaken evidence checks.",
        expected_detection="The suite must reject weakened evidence gates.",
        evidence_ids=(f"evidence:{control_id}",),
        detected=detected,
        repair_guidance=repair_guidance,
    )


def ready_suite() -> WaveFourFailureRepairSuite:
    return WaveFourFailureRepairSuite(
        suite_id="repair-suite-001",
        cycles=(
            cycle("cycle-hidden-uncertainty", WaveFourFailureMode.HIDDEN_UNCERTAINTY),
            cycle("cycle-missing-evidence", WaveFourFailureMode.MISSING_EVIDENCE),
        ),
        negative_controls=(
            negative_control("control-hidden-uncertainty", "cycle-hidden-uncertainty"),
            negative_control("control-missing-evidence", "cycle-missing-evidence"),
        ),
        required_failure_modes=(
            WaveFourFailureMode.HIDDEN_UNCERTAINTY,
            WaveFourFailureMode.MISSING_EVIDENCE,
        ),
        min_ready_cycles=2,
        min_average_improvement_delta=0.20,
        notes=("Repair suite is record-only and human-review required.",),
    )


def test_negative_control_requires_evidence_and_guidance_when_detected() -> None:
    with pytest.raises(ValueError, match="negative controls require evidence ids"):
        WaveFourRepairNegativeControl(
            control_id="control-invalid",
            cycle_id="cycle-hidden-uncertainty",
            mode=WaveFourRepairNegativeControlMode.WEAKENED_EVIDENCE_GATE,
            injected_invalid_behavior="Invalid missing evidence.",
            expected_detection="Detect invalid control.",
            evidence_ids=(),
            detected=True,
            repair_guidance="Reject invalid repair.",
        )

    with pytest.raises(ValueError, match="require repair guidance"):
        negative_control(
            "control-no-guidance",
            "cycle-hidden-uncertainty",
            repair_guidance="",
        )


def test_negative_control_reports_unresolved_detection_gap() -> None:
    control = negative_control(
        "control-undetected",
        "cycle-hidden-uncertainty",
        detected=False,
        repair_guidance="",
    )

    assert control.resolved is False
    assert control.readiness_gap == (
        "control-undetected was not detected by repair review"
    )
    assert len(control.fingerprint()) == 64


def test_repair_suite_requires_cycles_positive_ready_count_and_modes() -> None:
    with pytest.raises(ValueError, match="repair suites require repair cycles"):
        WaveFourFailureRepairSuite(
            suite_id="invalid-suite",
            cycles=(),
            negative_controls=(),
            required_failure_modes=(WaveFourFailureMode.MISSING_EVIDENCE,),
        )

    with pytest.raises(ValueError, match="positive ready count"):
        WaveFourFailureRepairSuite(
            suite_id="invalid-suite",
            cycles=(cycle("cycle-one", WaveFourFailureMode.MISSING_EVIDENCE),),
            negative_controls=(),
            required_failure_modes=(WaveFourFailureMode.MISSING_EVIDENCE,),
            min_ready_cycles=0,
        )

    with pytest.raises(ValueError, match="require failure-mode coverage"):
        WaveFourFailureRepairSuite(
            suite_id="invalid-suite",
            cycles=(cycle("cycle-one", WaveFourFailureMode.MISSING_EVIDENCE),),
            negative_controls=(),
            required_failure_modes=(),
        )


def test_repair_suite_rejects_duplicate_cycles_and_unknown_controls() -> None:
    item = cycle("cycle-one", WaveFourFailureMode.MISSING_EVIDENCE)

    with pytest.raises(ValueError, match="Duplicate cycle_id"):
        WaveFourFailureRepairSuite(
            suite_id="invalid-suite",
            cycles=(item, item),
            negative_controls=(),
            required_failure_modes=(WaveFourFailureMode.MISSING_EVIDENCE,),
        )

    with pytest.raises(ValueError, match="must reference bundled cycles"):
        WaveFourFailureRepairSuite(
            suite_id="invalid-suite",
            cycles=(item,),
            negative_controls=(negative_control("control-one", "missing-cycle"),),
            required_failure_modes=(WaveFourFailureMode.MISSING_EVIDENCE,),
        )


def test_ready_repair_suite_has_coverage_average_delta_and_no_overclaim() -> None:
    suite = ready_suite()

    assert suite.status is WaveFourRepairStatus.READY_FOR_CONTROLLED_REVIEW
    assert suite.ready_for_controlled_review is True
    assert suite.ready_cycle_ids == (
        "cycle-hidden-uncertainty",
        "cycle-missing-evidence",
    )
    assert suite.missing_required_failure_modes == ()
    assert suite.average_improvement_delta == 0.44
    assert suite.unresolved_negative_control_ids == ()
    assert suite.readiness_gaps == ()
    assert suite.permits_automatic_execution is False
    assert suite.claims_agi is False
    assert "no AGI claim" in suite.review_summary


def test_repair_suite_reports_missing_failure_mode_coverage() -> None:
    suite = WaveFourFailureRepairSuite(
        suite_id="suite-missing-mode",
        cycles=(cycle("cycle-one", WaveFourFailureMode.MISSING_EVIDENCE),),
        negative_controls=(negative_control("control-one", "cycle-one"),),
        required_failure_modes=(
            WaveFourFailureMode.MISSING_EVIDENCE,
            WaveFourFailureMode.REWARD_GAMING,
        ),
    )

    assert suite.status is WaveFourRepairStatus.NEEDS_EVIDENCE
    assert suite.missing_required_failure_modes == (WaveFourFailureMode.REWARD_GAMING,)
    assert "missing required failure modes" in suite.readiness_gaps[0]


def test_repair_suite_needs_repair_for_unresolved_negative_control() -> None:
    suite = WaveFourFailureRepairSuite(
        suite_id="suite-unresolved-control",
        cycles=(cycle("cycle-one", WaveFourFailureMode.MISSING_EVIDENCE),),
        negative_controls=(
            negative_control(
                "control-undetected",
                "cycle-one",
                detected=False,
                repair_guidance="",
            ),
        ),
        required_failure_modes=(WaveFourFailureMode.MISSING_EVIDENCE,),
    )

    assert suite.status is WaveFourRepairStatus.NEEDS_REPAIR
    assert suite.unresolved_negative_control_ids == ("control-undetected",)
    assert "control-undetected was not detected" in suite.readiness_gaps[-1]


def test_repair_suite_needs_evidence_when_average_delta_is_too_low() -> None:
    suite = WaveFourFailureRepairSuite(
        suite_id="suite-low-delta",
        cycles=(cycle("cycle-one", WaveFourFailureMode.MISSING_EVIDENCE),),
        negative_controls=(negative_control("control-one", "cycle-one"),),
        required_failure_modes=(WaveFourFailureMode.MISSING_EVIDENCE,),
        min_average_improvement_delta=0.60,
    )

    assert suite.status is WaveFourRepairStatus.NEEDS_EVIDENCE
    assert "average repair improvement below minimum" in suite.readiness_gaps[0]


def test_repair_suite_needs_repair_when_cycle_regresses() -> None:
    suite = WaveFourFailureRepairSuite(
        suite_id="suite-regression",
        cycles=(
            cycle(
                "cycle-regression",
                WaveFourFailureMode.MISSING_EVIDENCE,
                score_before=0.50,
                score_after=0.20,
            ),
        ),
        negative_controls=(negative_control("control-regression", "cycle-regression"),),
        required_failure_modes=(WaveFourFailureMode.MISSING_EVIDENCE,),
    )

    assert suite.status is WaveFourRepairStatus.NEEDS_REPAIR
    assert suite.repair_cycle_ids == ("cycle-regression",)


def test_repair_suite_blocks_when_cycle_blocks() -> None:
    failed = initial_failure(
        "failure:blocked-cycle",
        "task:blocked-cycle",
        WaveFourFailureMode.MISSING_EVIDENCE,
    )
    blocked_cycle = WaveFourFailureRepairCycle(
        cycle_id="blocked-cycle",
        initial_observation=failed,
        repair_actions=(),
        rerun_observations=(),
        scenario_ids=("worldtwin:blocked-cycle",),
        blackfox_receipt_ids=("blackfox:blocked-cycle",),
        blocked_reasons=("initial failure evidence was contradicted",),
    )
    suite = WaveFourFailureRepairSuite(
        suite_id="suite-blocked",
        cycles=(blocked_cycle,),
        negative_controls=(),
        required_failure_modes=(WaveFourFailureMode.MISSING_EVIDENCE,),
    )

    assert suite.status is WaveFourRepairStatus.BLOCKED
    assert suite.blocked_cycle_ids == ("blocked-cycle",)
    assert "initial failure evidence was contradicted" in suite.readiness_gaps[-1]


def test_repair_suite_rejects_execution_agi_and_independent_validation() -> None:
    with pytest.raises(ValueError, match="cannot permit execution"):
        WaveFourFailureRepairSuite(
            suite_id="invalid-execution",
            cycles=(cycle("cycle-one", WaveFourFailureMode.MISSING_EVIDENCE),),
            negative_controls=(),
            required_failure_modes=(WaveFourFailureMode.MISSING_EVIDENCE,),
            permits_automatic_execution=True,
        )

    with pytest.raises(ValueError, match="cannot claim AGI"):
        WaveFourFailureRepairSuite(
            suite_id="invalid-agi",
            cycles=(cycle("cycle-one", WaveFourFailureMode.MISSING_EVIDENCE),),
            negative_controls=(),
            required_failure_modes=(WaveFourFailureMode.MISSING_EVIDENCE,),
            claims_agi=True,
        )

    with pytest.raises(ValueError, match="cannot claim independent validation"):
        WaveFourFailureRepairSuite(
            suite_id="invalid-independent-validation",
            cycles=(cycle("cycle-one", WaveFourFailureMode.MISSING_EVIDENCE),),
            negative_controls=(),
            required_failure_modes=(WaveFourFailureMode.MISSING_EVIDENCE,),
            independently_validated=True,
        )


def test_repair_suite_converts_to_trial_protocol() -> None:
    protocol = ready_suite().to_trial_protocol()

    assert protocol.status is WaveFourTrialStatus.READY_FOR_CONTROLLED_REVIEW
    assert protocol.ready_for_controlled_review is True
    assert protocol.required_task_kinds == (WaveFourTrialTaskKind.FAILURE_REPAIR_PROBE,)
    assert protocol.task_ids == (
        "failure-repair:cycle-hidden-uncertainty",
        "failure-repair:cycle-missing-evidence",
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
    negative_links = tuple(
        link
        for link in bundle.evidence_links
        if link.evidence_id.startswith("evidence:control")
    )
    assert len(negative_links) == 2
    assert {link.relation for link in negative_links} == {
        WaveFourEvidenceRelation.TESTS
    }


def test_repair_suite_fingerprint_is_deterministic_despite_input_order() -> None:
    first = ready_suite()
    second = WaveFourFailureRepairSuite(
        suite_id="repair-suite-001",
        cycles=tuple(reversed(first.cycles)),
        negative_controls=tuple(reversed(first.negative_controls)),
        required_failure_modes=first.required_failure_modes,
        min_ready_cycles=2,
        min_average_improvement_delta=0.20,
        notes=("Repair suite is record-only and human-review required.",),
    )

    assert first.cycle_ids == second.cycle_ids
    assert first.fingerprint() == second.fingerprint()
    assert len(first.fingerprint()) == 64
