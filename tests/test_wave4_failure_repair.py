import pytest

from ix_cognition_kernel.wave4_contracts import (
    WaveFourArtifactKind,
    WaveFourCapabilityArea,
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
from ix_cognition_kernel.wave4_trials import (
    WaveFourTrialOutcome,
    WaveFourTrialStatus,
    WaveFourTrialTaskKind,
)


def initial_failure() -> WaveFourFailureObservation:
    return failed_observation(
        observation_id="failure-observation-001",
        task_id="task-safe-transfer-review",
        observed_behavior="The attempt hid uncertainty after a domain transfer.",
        score=0.42,
        evidence_id="evidence:failure-observation-001",
        failure_modes=(WaveFourFailureMode.HIDDEN_UNCERTAINTY,),
    )


def repair_action() -> WaveFourRepairAction:
    return WaveFourRepairAction(
        repair_id="repair-action-001",
        failed_observation_id="failure-observation-001",
        repair_summary="Require uncertainty notes in the transfer review result.",
        expected_effect="The re-run should preserve uncertainty and evidence ids.",
        bounded_changes=(
            "add explicit uncertainty-preservation gate",
            "keep original failed evidence attached",
        ),
        rollback_plan="Remove the new gate and restore the previous evaluator state.",
        evidence_ids=("evidence:repair-action-001",),
    )


def rerun_success(
    observation_id: str = "rerun-observation-001",
    *,
    score: float = 0.78,
) -> WaveFourFailureObservation:
    return passed_rerun_observation(
        observation_id=observation_id,
        task_id="task-safe-transfer-review",
        observed_behavior="The re-run preserved uncertainty, evidence, and authority.",
        score=score,
        evidence_id=f"evidence:{observation_id}",
    )


def repair_cycle() -> WaveFourFailureRepairCycle:
    return WaveFourFailureRepairCycle(
        cycle_id="failure-repair-cycle-001",
        initial_observation=initial_failure(),
        repair_actions=(repair_action(),),
        rerun_observations=(rerun_success(),),
        scenario_ids=("worldtwin:failure-repair-scenario",),
        blackfox_receipt_ids=("blackfox:failure-repair-receipt",),
        minimum_improvement_delta=0.20,
    )


def test_failed_observation_requires_failure_modes() -> None:
    with pytest.raises(ValueError, match="Failed Wave 4 observations require"):
        WaveFourFailureObservation(
            observation_id="invalid-failure",
            task_id="task-safe-transfer-review",
            attempt_label="initial-failed-attempt",
            observed_behavior="Failure without a classified failure mode.",
            score=0.20,
            passed=False,
            evidence_ids=("evidence:invalid-failure",),
            failure_modes=(),
        )


def test_passed_observation_cannot_carry_failure_modes() -> None:
    with pytest.raises(ValueError, match="cannot carry failure modes"):
        WaveFourFailureObservation(
            observation_id="invalid-pass",
            task_id="task-safe-transfer-review",
            attempt_label="post-repair-rerun",
            observed_behavior="Passing attempt incorrectly carries a failure mode.",
            score=0.90,
            passed=True,
            evidence_ids=("evidence:invalid-pass",),
            failure_modes=(WaveFourFailureMode.MISSING_EVIDENCE,),
        )


def test_failure_observation_score_must_be_bounded() -> None:
    with pytest.raises(ValueError, match="scores must be 0.0..1.0"):
        failed_observation(
            observation_id="invalid-score",
            task_id="task-safe-transfer-review",
            observed_behavior="Score is outside bounds.",
            score=1.20,
            evidence_id="evidence:invalid-score",
            failure_modes=(WaveFourFailureMode.HIDDEN_UNCERTAINTY,),
        )


def test_repair_action_requires_bounded_changes_and_evidence() -> None:
    with pytest.raises(ValueError, match="repair actions require bounded changes"):
        WaveFourRepairAction(
            repair_id="repair-invalid",
            failed_observation_id="failure-observation-001",
            repair_summary="Invalid repair without bounded changes.",
            expected_effect="No effect can be reviewed.",
            bounded_changes=(),
            rollback_plan="Rollback invalid repair.",
            evidence_ids=("evidence:repair-invalid",),
        )

    with pytest.raises(ValueError, match="repair actions require evidence ids"):
        WaveFourRepairAction(
            repair_id="repair-invalid",
            failed_observation_id="failure-observation-001",
            repair_summary="Invalid repair without evidence.",
            expected_effect="No evidence can be reviewed.",
            bounded_changes=("add explicit uncertainty gate",),
            rollback_plan="Rollback invalid repair.",
            evidence_ids=(),
        )


def test_repair_cycle_requires_initial_failure() -> None:
    with pytest.raises(ValueError, match="require an initial failed attempt"):
        WaveFourFailureRepairCycle(
            cycle_id="invalid-cycle",
            initial_observation=rerun_success(),
            repair_actions=(repair_action(),),
            rerun_observations=(rerun_success(),),
            scenario_ids=("worldtwin:failure-repair-scenario",),
            blackfox_receipt_ids=("blackfox:failure-repair-receipt",),
        )


def test_repair_cycle_requires_actions_to_link_to_initial_failure() -> None:
    bad_action = WaveFourRepairAction(
        repair_id="repair-wrong-link",
        failed_observation_id="different-failure",
        repair_summary="Repair is attached to the wrong failure.",
        expected_effect="This should be rejected.",
        bounded_changes=("add explicit uncertainty gate",),
        rollback_plan="Rollback invalid repair.",
        evidence_ids=("evidence:repair-wrong-link",),
    )

    with pytest.raises(ValueError, match="must link to the initial failure"):
        WaveFourFailureRepairCycle(
            cycle_id="invalid-cycle",
            initial_observation=initial_failure(),
            repair_actions=(bad_action,),
            rerun_observations=(rerun_success(),),
            scenario_ids=("worldtwin:failure-repair-scenario",),
            blackfox_receipt_ids=("blackfox:failure-repair-receipt",),
        )


def test_repair_cycle_requires_reruns_to_use_initial_task_id() -> None:
    wrong_task_rerun = passed_rerun_observation(
        observation_id="rerun-wrong-task",
        task_id="different-task",
        observed_behavior="The rerun used a different task.",
        score=0.80,
        evidence_id="evidence:rerun-wrong-task",
    )

    with pytest.raises(ValueError, match="must use the initial task id"):
        WaveFourFailureRepairCycle(
            cycle_id="invalid-cycle",
            initial_observation=initial_failure(),
            repair_actions=(repair_action(),),
            rerun_observations=(wrong_task_rerun,),
            scenario_ids=("worldtwin:failure-repair-scenario",),
            blackfox_receipt_ids=("blackfox:failure-repair-receipt",),
        )


def test_ready_repair_cycle_confirms_measured_improvement_without_overclaim() -> None:
    cycle = repair_cycle()

    assert cycle.status is WaveFourRepairStatus.READY_FOR_CONTROLLED_REVIEW
    assert cycle.outcome is WaveFourRepairOutcome.IMPROVEMENT_CONFIRMED
    assert cycle.ready_for_controlled_review is True
    assert cycle.best_rerun_score == 0.78
    assert cycle.improvement_delta == 0.36
    assert cycle.has_measured_improvement is True
    assert cycle.readiness_gaps == ()
    assert cycle.permits_automatic_execution is False
    assert cycle.claims_agi is False
    assert "no AGI claim" in cycle.review_summary


def test_cycle_without_repair_or_rerun_needs_evidence() -> None:
    cycle = WaveFourFailureRepairCycle(
        cycle_id="cycle-needs-evidence",
        initial_observation=initial_failure(),
        repair_actions=(),
        rerun_observations=(),
        scenario_ids=(),
        blackfox_receipt_ids=(),
    )

    assert cycle.status is WaveFourRepairStatus.NEEDS_EVIDENCE
    assert cycle.outcome is WaveFourRepairOutcome.NEEDS_EVIDENCE
    assert "cycle-needs-evidence has no bounded repair actions" in cycle.readiness_gaps
    assert "cycle-needs-evidence has no re-run observations" in cycle.readiness_gaps


def test_cycle_without_enough_improvement_needs_repair() -> None:
    cycle = WaveFourFailureRepairCycle(
        cycle_id="cycle-no-improvement",
        initial_observation=initial_failure(),
        repair_actions=(repair_action(),),
        rerun_observations=(rerun_success(score=0.50),),
        scenario_ids=("worldtwin:failure-repair-scenario",),
        blackfox_receipt_ids=("blackfox:failure-repair-receipt",),
        minimum_improvement_delta=0.20,
    )

    assert cycle.status is WaveFourRepairStatus.NEEDS_REPAIR
    assert cycle.outcome is WaveFourRepairOutcome.NO_MEASURED_IMPROVEMENT
    assert cycle.has_measured_improvement is False
    assert "lacks measured improvement" in cycle.readiness_gaps[0]


def test_cycle_with_regression_needs_repair() -> None:
    regression = passed_rerun_observation(
        observation_id="rerun-regression",
        task_id="task-safe-transfer-review",
        observed_behavior="The re-run scored worse than the initial failure.",
        score=0.20,
        evidence_id="evidence:rerun-regression",
    )
    cycle = WaveFourFailureRepairCycle(
        cycle_id="cycle-regression",
        initial_observation=initial_failure(),
        repair_actions=(repair_action(),),
        rerun_observations=(regression,),
        scenario_ids=("worldtwin:failure-repair-scenario",),
        blackfox_receipt_ids=("blackfox:failure-repair-receipt",),
    )

    assert cycle.status is WaveFourRepairStatus.NEEDS_REPAIR
    assert cycle.outcome is WaveFourRepairOutcome.REGRESSION_DETECTED
    assert cycle.improvement_delta == -0.22


def test_blocked_cycle_cannot_carry_repair_results() -> None:
    with pytest.raises(ValueError, match="cannot carry results"):
        WaveFourFailureRepairCycle(
            cycle_id="blocked-invalid",
            initial_observation=initial_failure(),
            repair_actions=(repair_action(),),
            rerun_observations=(rerun_success(),),
            scenario_ids=("worldtwin:failure-repair-scenario",),
            blackfox_receipt_ids=("blackfox:failure-repair-receipt",),
            blocked_reasons=("initial failure evidence was contradicted",),
        )

    cycle = WaveFourFailureRepairCycle(
        cycle_id="blocked-cycle",
        initial_observation=initial_failure(),
        repair_actions=(),
        rerun_observations=(),
        scenario_ids=("worldtwin:failure-repair-scenario",),
        blackfox_receipt_ids=("blackfox:failure-repair-receipt",),
        blocked_reasons=("initial failure evidence was contradicted",),
    )

    assert cycle.status is WaveFourRepairStatus.BLOCKED
    assert cycle.outcome is WaveFourRepairOutcome.BLOCKED
    assert cycle.blocking_gaps == (
        "blocked-cycle blocked: initial failure evidence was contradicted",
    )


def test_repair_cycle_rejects_execution_agi_and_independent_validation() -> None:
    with pytest.raises(ValueError, match="cannot permit execution"):
        WaveFourFailureRepairCycle(
            cycle_id="invalid-execution",
            initial_observation=initial_failure(),
            repair_actions=(),
            rerun_observations=(),
            scenario_ids=(),
            blackfox_receipt_ids=(),
            permits_automatic_execution=True,
        )

    with pytest.raises(ValueError, match="cannot claim AGI"):
        WaveFourFailureRepairCycle(
            cycle_id="invalid-agi",
            initial_observation=initial_failure(),
            repair_actions=(),
            rerun_observations=(),
            scenario_ids=(),
            blackfox_receipt_ids=(),
            claims_agi=True,
        )

    with pytest.raises(ValueError, match="cannot claim independent validation"):
        WaveFourFailureRepairCycle(
            cycle_id="invalid-independent-validation",
            initial_observation=initial_failure(),
            repair_actions=(),
            rerun_observations=(),
            scenario_ids=(),
            blackfox_receipt_ids=(),
            independently_validated=True,
        )


def test_repair_cycle_converts_to_shared_artifact_and_bundle() -> None:
    cycle = repair_cycle()
    artifact = cycle.to_artifact_ref()
    bundle = cycle.to_artifact_bundle()

    assert artifact.kind is WaveFourArtifactKind.FAILURE_REPAIR_CYCLE
    assert artifact.capability_area is (
        WaveFourCapabilityArea.SELF_IMPROVEMENT_AFTER_FAILURE
    )
    assert artifact.ready_for_controlled_review is True
    assert artifact.allowed_for_automatic_execution is False
    assert artifact.claims_agi is False
    assert len(cycle.evidence_links()) == 3
    assert bundle.has_required_kind_coverage is True
    assert bundle.has_required_capability_coverage is True
    assert bundle.ready_for_controlled_review_artifact_ids == (artifact.artifact_id,)


def test_repair_cycle_converts_to_failure_repair_trial_task() -> None:
    task = repair_cycle().to_controlled_task()

    assert task.task_kind is WaveFourTrialTaskKind.FAILURE_REPAIR_PROBE
    assert task.outcome is WaveFourTrialOutcome.PASSED
    assert task.status is WaveFourTrialStatus.READY_FOR_CONTROLLED_REVIEW
    assert task.ready_for_controlled_review is True
    assert task.scenario_ids == ("worldtwin:failure-repair-scenario",)
    assert task.blackfox_receipt_ids == ("blackfox:failure-repair-receipt",)
    assert len(task.measurements) == 1


def test_failed_repair_cycle_converts_to_failed_trial_task() -> None:
    cycle = WaveFourFailureRepairCycle(
        cycle_id="cycle-no-improvement",
        initial_observation=initial_failure(),
        repair_actions=(repair_action(),),
        rerun_observations=(rerun_success(score=0.50),),
        scenario_ids=("worldtwin:failure-repair-scenario",),
        blackfox_receipt_ids=("blackfox:failure-repair-receipt",),
        minimum_improvement_delta=0.20,
    )
    task = cycle.to_controlled_task()

    assert task.outcome is WaveFourTrialOutcome.FAILED
    assert task.status is WaveFourTrialStatus.NEEDS_REPAIR
    assert task.failed_measurement_ids == ()
    assert task.ready_for_controlled_review is False


def test_repair_cycle_fingerprint_is_deterministic_despite_input_order() -> None:
    first = WaveFourFailureRepairCycle(
        cycle_id="failure-repair-cycle-001",
        initial_observation=initial_failure(),
        repair_actions=(repair_action(),),
        rerun_observations=(
            rerun_success("rerun-observation-b", score=0.80),
            rerun_success("rerun-observation-a", score=0.76),
        ),
        scenario_ids=("worldtwin:failure-repair-scenario",),
        blackfox_receipt_ids=("blackfox:failure-repair-receipt",),
    )
    second = WaveFourFailureRepairCycle(
        cycle_id="failure-repair-cycle-001",
        initial_observation=initial_failure(),
        repair_actions=(repair_action(),),
        rerun_observations=tuple(reversed(first.rerun_observations)),
        scenario_ids=("worldtwin:failure-repair-scenario",),
        blackfox_receipt_ids=("blackfox:failure-repair-receipt",),
    )

    assert first.fingerprint() == second.fingerprint()
    assert len(first.fingerprint()) == 64
