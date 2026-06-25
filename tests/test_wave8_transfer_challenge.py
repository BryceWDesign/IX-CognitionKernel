import pytest

from ix_cognition_kernel.wave8_environment_protocol import EnvironmentActionResult
from ix_cognition_kernel.wave8_episode_runner import run_single_step_episode
from ix_cognition_kernel.wave8_model_adapter import (
    DeterministicModelAdapter,
    DeterministicModelPolicy,
)
from ix_cognition_kernel.wave8_task_suite import (
    TaskDifficulty,
    TaskDisclosureLevel,
    UnknownTaskSuite,
    build_grid_transition_task,
    build_grid_transition_template,
)
from ix_cognition_kernel.wave8_transfer_challenge import (
    TransferBand,
    TransferClaimDecision,
    TransferTrialRecord,
    TransferTrialStatus,
    build_transfer_trial_record,
    evaluate_transfer_challenge,
)


def _template():
    return build_grid_transition_template(template_id="grid-template-1")


def _task(task_id: str, difficulty: TaskDifficulty, operation_id: str):
    disclosure = TaskDisclosureLevel.PARTIALLY_WITHHELD
    if difficulty is TaskDifficulty.HIDDEN_VALIDATION:
        disclosure = TaskDisclosureLevel.HIDDEN_GOAL
    return build_grid_transition_task(
        task_id=task_id,
        template=_template(),
        episode_id=f"{task_id}:episode",
        start_state_id=f"{task_id}:state-0",
        empty_direction="east",
        expected_operation_id=operation_id,
        difficulty=difficulty,
        disclosure_level=disclosure,
    )


def _suite() -> UnknownTaskSuite:
    return UnknownTaskSuite(
        suite_id="suite-transfer",
        purpose="Exercise seed, transfer, adversarial, and hidden validation.",
        tasks=(
            _task("task-seed", TaskDifficulty.SEED, "move-east"),
            _task("task-near", TaskDifficulty.NEAR_TRANSFER, "move-east"),
            _task("task-far", TaskDifficulty.FAR_TRANSFER, "move-east"),
            _task("task-adversarial", TaskDifficulty.ADVERSARIAL, "move-east"),
            _task("task-hidden", TaskDifficulty.HIDDEN_VALIDATION, "move-east"),
        ),
        evidence_ids=("suite-evidence-1",),
    )


def _adapter(operation_id: str = "move-east") -> DeterministicModelAdapter:
    return DeterministicModelAdapter(
        adapter_id="deterministic-adapter-1",
        policy=DeterministicModelPolicy(
            policy_id="policy-1",
            supported_environment_ids=("env-unused-by-deterministic-policy",),
            operation_preferences=(operation_id,),
            rationale_template="Use {operation_id} from {state_id}.",
            expected_effect_template="{operation_id} should change the bounded state.",
            evidence_ids=("policy-evidence-1",),
            assumptions=("visible-state-is-current",),
            uncertainty_ids=("uncertainty-grid-transition",),
        ),
    )


def _result(task_id: str, *, measured: bool = True) -> EnvironmentActionResult:
    return EnvironmentActionResult(
        result_id=f"{task_id}:result",
        action_id=f"{task_id}:action",
        environment_id=f"{task_id}:environment",
        episode_id=f"{task_id}:episode",
        prior_state_id=f"{task_id}:state-0",
        resulting_state_id=f"{task_id}:state-1",
        outcome_summary="The bounded task produced the expected transition.",
        score_delta=1.0,
        evidence_ids=(f"{task_id}:result-evidence",),
        measured=measured,
    )


def _run_for_task(task, *, measured: bool = True, operation_id: str = "move-east"):
    return run_single_step_episode(
        run_id=f"{task.task_id}:run",
        step_id=f"{task.task_id}:step",
        output_id=f"{task.task_id}:output",
        draft_id=f"{task.task_id}:draft",
        action_id=f"{task.task_id}:action",
        frame_id=f"{task.task_id}:frame",
        environment=task.environment,
        observation=task.initial_observation,
        adapter=_adapter(operation_id),
        result=_result(task.task_id, measured=measured),
    )


def _passing_trial(task) -> TransferTrialRecord:
    return build_transfer_trial_record(
        trial_id=f"{task.task_id}:trial",
        task=task,
        run=_run_for_task(task),
        observed_feature_ids=task.expected_outcome_features,
        evidence_ids=(f"{task.task_id}:trial-evidence",),
    )


def test_transfer_trial_records_band_status_and_feature_match() -> None:
    task = _task("task-near", TaskDifficulty.NEAR_TRANSFER, "move-east")
    trial = _passing_trial(task)

    assert trial.band is TransferBand.NEAR
    assert trial.status is TransferTrialStatus.REPLAYABLE_PASS
    assert trial.replayable_pass
    assert trial.matched_expected_features == task.expected_outcome_features
    assert trial.fingerprint() == trial.fingerprint()
    assert len(trial.fingerprint()) == 64


def test_transfer_trial_records_replayable_fail_when_features_do_not_match() -> None:
    task = _task("task-far", TaskDifficulty.FAR_TRANSFER, "move-east")
    trial = build_transfer_trial_record(
        trial_id="trial-fail",
        task=task,
        run=_run_for_task(task),
        observed_feature_ids=("wrong-feature",),
        evidence_ids=("trial-evidence-1",),
    )

    assert trial.status is TransferTrialStatus.REPLAYABLE_FAIL
    assert not trial.replayable_pass


def test_transfer_trial_records_unmeasured_result_status() -> None:
    task = _task("task-far", TaskDifficulty.FAR_TRANSFER, "move-east")
    trial = build_transfer_trial_record(
        trial_id="trial-unmeasured",
        task=task,
        run=_run_for_task(task, measured=False),
        observed_feature_ids=task.expected_outcome_features,
        evidence_ids=("trial-evidence-1",),
    )

    assert trial.status is TransferTrialStatus.NEEDS_MEASURED_RESULT


def test_transfer_trial_records_blocked_run_status() -> None:
    task = _task("task-far", TaskDifficulty.FAR_TRANSFER, "move-east")
    trial = build_transfer_trial_record(
        trial_id="trial-blocked",
        task=task,
        run=_run_for_task(task, operation_id="delete-host-file"),
        observed_feature_ids=task.expected_outcome_features,
        evidence_ids=("trial-evidence-1",),
    )

    assert trial.status is TransferTrialStatus.BLOCKED


def test_transfer_challenge_demonstrates_only_with_all_required_bands() -> None:
    suite = _suite()
    report = evaluate_transfer_challenge(
        report_id="report-transfer",
        suite=suite,
        trials=tuple(_passing_trial(task) for task in suite.tasks),
    )

    assert report.decision is TransferClaimDecision.TRANSFER_DEMONSTRATED
    assert report.ready
    assert report.replayable_pass_count == 5
    assert report.pass_count_for_band(TransferBand.HIDDEN) == 1
    assert report.fingerprint() == report.fingerprint()


def test_transfer_challenge_rejects_original_task_only_result() -> None:
    suite = _suite()
    seed_task = suite.tasks[0]
    report = evaluate_transfer_challenge(
        report_id="report-original-only",
        suite=suite,
        trials=(
            _passing_trial(seed_task),
            *(
                build_transfer_trial_record(
                    trial_id=f"{task.task_id}:trial",
                    task=task,
                    run=_run_for_task(task),
                    observed_feature_ids=("wrong-feature",),
                    evidence_ids=(f"{task.task_id}:trial-evidence",),
                )
                for task in suite.tasks[1:]
            ),
        ),
    )

    assert report.decision is TransferClaimDecision.NEEDS_HIDDEN_VALIDATION
    assert not report.ready
    assert "missing-hidden-validation-pass" in report.findings


def test_transfer_challenge_blocks_missing_suite_task_trials() -> None:
    suite = _suite()
    report = evaluate_transfer_challenge(
        report_id="report-missing",
        suite=suite,
        trials=(_passing_trial(suite.tasks[0]),),
    )

    assert report.decision is TransferClaimDecision.BLOCKED
    assert not report.ready
    assert any(
        finding.startswith("missing-suite-task-trials")
        for finding in report.findings
    )


def test_transfer_challenge_report_rejects_duplicate_trial_ids() -> None:
    suite = _suite()
    trial = _passing_trial(suite.tasks[0])

    with pytest.raises(ValueError, match="Duplicate trial_id"):
        evaluate_transfer_challenge(
            report_id="report-duplicate",
            suite=UnknownTaskSuite(
                suite_id="suite-one-task",
                purpose="Duplicate trial id rejection.",
                tasks=(suite.tasks[0],),
                evidence_ids=("suite-evidence-duplicate",),
            ),
            trials=(trial, trial),
        )
