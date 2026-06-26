import pytest

from ix_cognition_kernel.wave8_baseline_comparison import (
    BaselineComparisonDecision,
    BaselineImprovementDecision,
    BaselineSystemKind,
    build_baseline_outcome_record,
    compare_baseline_pair,
    evaluate_baseline_comparison,
)
from ix_cognition_kernel.wave8_environment_protocol import EnvironmentActionResult
from ix_cognition_kernel.wave8_episode_runner import run_single_step_episode
from ix_cognition_kernel.wave8_model_adapter import (
    DeterministicModelAdapter,
    DeterministicModelPolicy,
)
from ix_cognition_kernel.wave8_task_suite import (
    TaskDifficulty,
    TaskDisclosureLevel,
    build_grid_transition_task,
    build_grid_transition_template,
)


def _template():
    return build_grid_transition_template(template_id="grid-template-1")


def _task(task_id: str, difficulty: TaskDifficulty, operation_id: str = "move-east"):
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


def _adapter(operation_id: str = "move-east") -> DeterministicModelAdapter:
    return DeterministicModelAdapter(
        adapter_id=f"adapter:{operation_id}",
        policy=DeterministicModelPolicy(
            policy_id=f"policy:{operation_id}",
            supported_environment_ids=("env-unused",),
            operation_preferences=(operation_id,),
            rationale_template="Use {operation_id} from {state_id}.",
            expected_effect_template="{operation_id} should change the bounded state.",
            evidence_ids=(f"policy-evidence:{operation_id}",),
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
        outcome_summary="The bounded task produced a transition.",
        score_delta=1.0,
        evidence_ids=(f"{task_id}:result-evidence",),
        measured=measured,
    )


def _run_for_task(task, *, operation_id: str = "move-east", measured: bool = True):
    return run_single_step_episode(
        run_id=f"{task.task_id}:run:{operation_id}:{measured}",
        step_id=f"{task.task_id}:step:{operation_id}:{measured}",
        output_id=f"{task.task_id}:output:{operation_id}:{measured}",
        draft_id=f"{task.task_id}:draft:{operation_id}:{measured}",
        action_id=f"{task.task_id}:action",
        frame_id=f"{task.task_id}:frame:{operation_id}:{measured}",
        environment=task.environment,
        observation=task.initial_observation,
        adapter=_adapter(operation_id),
        result=_result(task.task_id, measured=measured),
    )


def _outcome(task, system_kind, observed, operation_id="move-east", measured=True):
    return build_baseline_outcome_record(
        outcome_id=f"{task.task_id}:{system_kind.value}:outcome",
        system_kind=system_kind,
        task=task,
        run=_run_for_task(task, operation_id=operation_id, measured=measured),
        observed_feature_ids=observed,
        evidence_ids=(f"{task.task_id}:{system_kind.value}:evidence",),
    )


def test_baseline_outcome_scores_feature_matches() -> None:
    task = _task("task-near", TaskDifficulty.NEAR_TRANSFER)
    outcome = _outcome(
        task,
        BaselineSystemKind.COGNITION_KERNEL,
        task.expected_outcome_features,
    )

    assert outcome.score == 1.0
    assert outcome.matched_feature_count == len(task.expected_outcome_features)
    assert outcome.missed_feature_count == 0
    assert outcome.fingerprint() == outcome.fingerprint()
    assert len(outcome.fingerprint()) == 64


def test_compare_baseline_pair_detects_candidate_improvement() -> None:
    task = _task("task-near", TaskDifficulty.NEAR_TRANSFER)
    baseline = _outcome(
        task,
        BaselineSystemKind.MODEL_ALONE,
        ("wrong-feature",),
    )
    candidate = _outcome(
        task,
        BaselineSystemKind.COGNITION_KERNEL,
        task.expected_outcome_features,
    )

    pair = compare_baseline_pair(
        pair_id="pair-improved",
        baseline=baseline,
        candidate=candidate,
    )

    assert pair.improved
    assert pair.decision is BaselineImprovementDecision.CANDIDATE_IMPROVED
    assert pair.score_delta == 1.0
    assert pair.findings == ()


def test_compare_baseline_pair_detects_candidate_tie_and_regression() -> None:
    task = _task("task-near", TaskDifficulty.NEAR_TRANSFER)
    baseline_pass = _outcome(
        task,
        BaselineSystemKind.MODEL_ALONE,
        task.expected_outcome_features,
    )
    candidate_pass = _outcome(
        task,
        BaselineSystemKind.COGNITION_KERNEL,
        task.expected_outcome_features,
    )
    candidate_fail = _outcome(
        task,
        BaselineSystemKind.COGNITION_KERNEL,
        ("wrong-feature",),
    )

    tied_pair = compare_baseline_pair(
        pair_id="pair-tie",
        baseline=baseline_pass,
        candidate=candidate_pass,
    )
    regressed_pair = compare_baseline_pair(
        pair_id="pair-regressed",
        baseline=baseline_pass,
        candidate=candidate_fail,
    )

    assert tied_pair.decision is BaselineImprovementDecision.CANDIDATE_TIED_BASELINE
    assert "candidate-tied-baseline" in tied_pair.findings
    assert regressed_pair.decision is BaselineImprovementDecision.CANDIDATE_REGRESSED
    assert "candidate-score-below-baseline" in regressed_pair.findings


def test_compare_baseline_pair_requires_replayable_evidence() -> None:
    task = _task("task-near", TaskDifficulty.NEAR_TRANSFER)
    baseline = _outcome(
        task,
        BaselineSystemKind.MODEL_ALONE,
        ("wrong-feature",),
        measured=False,
    )
    candidate = _outcome(
        task,
        BaselineSystemKind.COGNITION_KERNEL,
        task.expected_outcome_features,
    )

    pair = compare_baseline_pair(
        pair_id="pair-unmeasured",
        baseline=baseline,
        candidate=candidate,
    )

    assert pair.decision is BaselineImprovementDecision.NEEDS_REPLAYABLE_EVIDENCE
    assert any(
        finding.startswith("baseline-not-replayable")
        for finding in pair.findings
    )


def test_baseline_comparison_report_demonstrates_improvement_across_pairs() -> None:
    first_task = _task("task-near", TaskDifficulty.NEAR_TRANSFER)
    second_task = _task("task-far", TaskDifficulty.FAR_TRANSFER)
    first_pair = compare_baseline_pair(
        pair_id="pair-first",
        baseline=_outcome(
            first_task,
            BaselineSystemKind.MODEL_ALONE,
            ("wrong-feature",),
        ),
        candidate=_outcome(
            first_task,
            BaselineSystemKind.COGNITION_KERNEL,
            first_task.expected_outcome_features,
        ),
    )
    second_pair = compare_baseline_pair(
        pair_id="pair-second",
        baseline=_outcome(
            second_task,
            BaselineSystemKind.MODEL_ALONE,
            ("wrong-feature",),
        ),
        candidate=_outcome(
            second_task,
            BaselineSystemKind.COGNITION_KERNEL,
            second_task.expected_outcome_features,
        ),
    )

    report = evaluate_baseline_comparison(
        report_id="report-improved",
        purpose="Compare kernel-assisted task outcomes against model-alone outcomes.",
        pairs=(first_pair, second_pair),
    )

    assert report.ready
    assert report.decision is BaselineComparisonDecision.IMPROVEMENT_DEMONSTRATED
    assert report.improved_pair_count == 2
    assert report.findings == ()
    assert report.fingerprint() == report.fingerprint()


def test_baseline_comparison_report_detects_regression_and_small_sample() -> None:
    task = _task("task-near", TaskDifficulty.NEAR_TRANSFER)
    regressed_pair = compare_baseline_pair(
        pair_id="pair-regressed",
        baseline=_outcome(
            task,
            BaselineSystemKind.MODEL_ALONE,
            task.expected_outcome_features,
        ),
        candidate=_outcome(
            task,
            BaselineSystemKind.COGNITION_KERNEL,
            ("wrong-feature",),
        ),
    )

    report = evaluate_baseline_comparison(
        report_id="report-regressed",
        purpose="Compare candidate against baseline without hiding regression.",
        pairs=(regressed_pair,),
    )

    assert not report.ready
    assert report.decision is BaselineComparisonDecision.REGRESSION_DETECTED
    assert report.regression_pair_count == 1
    assert "candidate-regression-present" in report.findings


def test_baseline_report_rejects_overclaiming_purpose() -> None:
    task = _task("task-near", TaskDifficulty.NEAR_TRANSFER)
    pair = compare_baseline_pair(
        pair_id="pair-first",
        baseline=_outcome(
            task,
            BaselineSystemKind.MODEL_ALONE,
            ("wrong-feature",),
        ),
        candidate=_outcome(
            task,
            BaselineSystemKind.COGNITION_KERNEL,
            task.expected_outcome_features,
        ),
    )

    with pytest.raises(ValueError, match="blocked overclaiming"):
        evaluate_baseline_comparison(
            report_id="report-overclaim",
            purpose="This proves AGI.",
            pairs=(pair,),
        )
