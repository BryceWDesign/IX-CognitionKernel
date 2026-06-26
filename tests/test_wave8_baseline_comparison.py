"""Tests for Wave 8 baseline comparison."""

from __future__ import annotations

import pytest

from ix_cognition_kernel.wave8_baseline_comparison import (
    BaselineComparisonDecision,
    BaselineMetric,
    BaselineMetricDirection,
    BaselineMetricRecord,
    BaselineSystemRecord,
    build_baseline_report,
    build_metric_record,
)
from ix_cognition_kernel.wave8_curriculum_frontier import (
    CurriculumFrontier,
    FrontierPressure,
)
from ix_cognition_kernel.wave8_environment_protocol import (
    ActionAssessment,
    BoundedEnvironmentSpec,
    EnvironmentAction,
    EnvironmentActionResult,
    EnvironmentObservation,
    build_environment_replay_frame,
)
from ix_cognition_kernel.wave8_episode_runner import run_single_step_episode
from ix_cognition_kernel.wave8_model_adapter import (
    DeterministicModelAdapter,
    ModelAdapterMode,
)
from ix_cognition_kernel.wave8_task_suite import (
    TaskDifficultyBand,
    UnknownTaskInstance,
)
from ix_cognition_kernel.wave8_transfer_challenge import (
    TransferBand,
    build_transfer_trial,
    evaluate_transfer_challenge,
)


def _environment() -> BoundedEnvironmentSpec:
    return BoundedEnvironmentSpec(
        environment_id="env-baseline",
        name="Baseline Grid",
        version="1.0",
        supported_action_kinds=("move",),
        observable_feature_ids=("agent:0,0", "goal:1,0", "agent:1,0", "goal-reached"),
        terminal_feature_ids=("goal-reached",),
        forbidden_action_patterns=("delete-world",),
    )


def _observation(
    *,
    observation_id: str = "obs-baseline",
    episode_id: str = "episode-baseline",
) -> EnvironmentObservation:
    return EnvironmentObservation(
        observation_id=observation_id,
        environment_id="env-baseline",
        episode_id=episode_id,
        visible_features=("agent:0,0", "goal:1,0"),
        hidden_feature_count=1,
    )


def _task(*, task_id: str, band: TaskDifficultyBand) -> UnknownTaskInstance:
    return UnknownTaskInstance(
        task_id=task_id,
        environment_id="env-baseline",
        difficulty_band=band,
        initial_observation=_observation(
            observation_id=f"obs-{task_id}",
            episode_id=f"episode-{task_id}",
        ),
        allowed_action_kinds=("move",),
        expected_outcome_features=("goal-reached", "operation:move-east"),
        novelty_factors=("new-start",),
        transfer_tags=("grid-move", "spatial-transfer"),
        evidence_ids=(f"evidence-{task_id}",),
    )


def _adapter() -> DeterministicModelAdapter:
    return DeterministicModelAdapter(
        adapter_id="adapter-baseline",
        mode=ModelAdapterMode.REPLAY_SCRIPT,
        supported_action_kinds=("move",),
        policy={
            "agent:0,0|goal:1,0": {
                "kind": "move",
                "parameters": {"direction": "east"},
                "confidence": 0.88,
                "rationale": "Move east toward the goal.",
            }
        },
    )


def _passing_action(
    *,
    action_id: str,
    observation: EnvironmentObservation,
) -> EnvironmentAction:
    assessment = ActionAssessment(
        action_id=action_id,
        environment_id="env-baseline",
        approved=True,
        reasons=("allowed-action-kind",),
        blocked_reasons=(),
    )
    return EnvironmentAction(
        action_id=action_id,
        environment_id="env-baseline",
        episode_id=observation.episode_id,
        kind="move",
        parameters=(("direction", "east"),),
        assessment=assessment,
    )


def _passing_result(
    *,
    result_id: str,
    action: EnvironmentAction,
) -> EnvironmentActionResult:
    return EnvironmentActionResult(
        result_id=result_id,
        action_id=action.action_id,
        environment_id="env-baseline",
        episode_id=action.episode_id,
        next_features=("agent:1,0", "goal-reached"),
        measured_reward=1.0,
        terminal=True,
    )


def _replayable_run(*, run_id: str, task: UnknownTaskInstance) -> object:
    observation = task.initial_observation
    action = _passing_action(
        action_id=f"action-{task.task_id}",
        observation=observation,
    )
    result = _passing_result(
        result_id=f"result-{task.task_id}",
        action=action,
    )
    return run_single_step_episode(
        run_id=run_id,
        step_id=f"step-{task.task_id}",
        output_id=f"output-{task.task_id}",
        draft_id=f"draft-{task.task_id}",
        action_id=action.action_id,
        frame_id=f"frame-{task.task_id}",
        environment=_environment(),
        observation=observation,
        adapter=_adapter(),
        result=result,
    )


def _passing_transfer_report() -> object:
    near = _task(task_id="task-near", band=TaskDifficultyBand.TRANSFER_NEAR)
    far = _task(task_id="task-far", band=TaskDifficultyBand.TRANSFER_FAR)
    hidden = _task(task_id="task-hidden", band=TaskDifficultyBand.HIDDEN)
    trials = (
        build_transfer_trial(
            trial_id="trial-near",
            task=near,
            band=TransferBand.NEAR,
            episode_run=_replayable_run(run_id="run-near", task=near),
        ),
        build_transfer_trial(
            trial_id="trial-far",
            task=far,
            band=TransferBand.FAR,
            episode_run=_replayable_run(run_id="run-far", task=far),
        ),
        build_transfer_trial(
            trial_id="trial-hidden",
            task=hidden,
            band=TransferBand.HIDDEN,
            episode_run=_replayable_run(run_id="run-hidden", task=hidden),
        ),
    )
    return evaluate_transfer_challenge(
        report_id="transfer-report-baseline",
        suite=CurriculumFrontier(
            frontier_id="frontier-baseline",
            purpose="Baseline comparison transfer pressure.",
            pressures=(
                FrontierPressure(
                    pressure_id="pressure-baseline",
                    target_skill="move-east",
                    difficulty_band=TaskDifficultyBand.TRANSFER_NEAR,
                    transfer_tags=("grid-move",),
                    required_feature_ids=("goal-reached",),
                    forbidden_shortcuts=("memorized-start",),
                ),
            ),
            tasks=(near, far, hidden),
            evidence_ids=("frontier-evidence-1",),
        ),
        trials=trials,
    )


def test_metric_record_scores_improvement_for_higher_is_better() -> None:
    metric = build_metric_record(
        metric_id="metric-transfer-rate",
        metric=BaselineMetric.TRANSFER_SUCCESS_RATE,
        direction=BaselineMetricDirection.HIGHER_IS_BETTER,
        candidate_value=0.9,
        baseline_value=0.5,
        evidence_ids=("metric-evidence-1",),
    )

    assert metric.improved
    assert metric.delta == pytest.approx(0.4)
    assert len(metric.fingerprint()) == 64


def test_metric_record_scores_improvement_for_lower_is_better() -> None:
    metric = build_metric_record(
        metric_id="metric-failure-rate",
        metric=BaselineMetric.FAILURE_RATE,
        direction=BaselineMetricDirection.LOWER_IS_BETTER,
        candidate_value=0.1,
        baseline_value=0.4,
        evidence_ids=("metric-evidence-1",),
    )

    assert metric.improved
    assert metric.delta == pytest.approx(0.3)


def test_metric_record_rejects_invalid_numeric_values() -> None:
    with pytest.raises(ValueError, match="candidate_value must be finite"):
        build_metric_record(
            metric_id="metric-invalid",
            metric=BaselineMetric.REPLAYABLE_EPISODE_COUNT,
            direction=BaselineMetricDirection.HIGHER_IS_BETTER,
            candidate_value=float("nan"),
            baseline_value=1.0,
            evidence_ids=("metric-evidence-1",),
        )


def test_metric_record_rejects_empty_evidence() -> None:
    with pytest.raises(ValueError, match="require evidence ids"):
        build_metric_record(
            metric_id="metric-no-evidence",
            metric=BaselineMetric.REPLAYABLE_EPISODE_COUNT,
            direction=BaselineMetric.HIGHER_IS_BETTER,
            candidate_value=2.0,
            baseline_value=1.0,
            evidence_ids=(),
        )


def test_baseline_report_demonstrates_improvement() -> None:
    report = _passing_transfer_report()
    baseline = BaselineSystemRecord(
        baseline_id="baseline-static",
        name="Static prompt baseline",
        version="0.1",
        replayable_episode_count=1,
        transfer_success_rate=0.2,
        hidden_success_rate=0.1,
        failure_rate=0.8,
        evidence_ids=("baseline-evidence-1",),
    )
    candidate = BaselineSystemRecord(
        baseline_id="candidate-wave8",
        name="Wave 8 bounded learner",
        version="0.1",
        replayable_episode_count=3,
        transfer_success_rate=1.0,
        hidden_success_rate=1.0,
        failure_rate=0.0,
        evidence_ids=("candidate-evidence-1",),
    )

    baseline_report = build_baseline_report(
        report_id="baseline-report-1",
        transfer_report=report,
        candidate=candidate,
        baseline=baseline,
        evidence_ids=("comparison-evidence-1",),
    )

    assert baseline_report.decision is BaselineComparisonDecision.IMPROVEMENT_DEMONSTRATED
    assert baseline_report.improved_metric_count == 4
    assert not baseline_report.regressed_metrics


def test_baseline_report_detects_regression() -> None:
    report = _passing_transfer_report()
    baseline = BaselineSystemRecord(
        baseline_id="baseline-strong",
        name="Strong baseline",
        version="1.0",
        replayable_episode_count=5,
        transfer_success_rate=1.0,
        hidden_success_rate=1.0,
        failure_rate=0.0,
        evidence_ids=("baseline-evidence-1",),
    )
    candidate = BaselineSystemRecord(
        baseline_id="candidate-weak",
        name="Weak candidate",
        version="0.1",
        replayable_episode_count=1,
        transfer_success_rate=0.2,
        hidden_success_rate=0.1,
        failure_rate=0.9,
        evidence_ids=("candidate-evidence-1",),
    )

    baseline_report = build_baseline_report(
        report_id="baseline-report-regression",
        transfer_report=report,
        candidate=candidate,
        baseline=baseline,
        evidence_ids=("comparison-evidence-1",),
    )

    assert baseline_report.decision is BaselineComparisonDecision.REGRESSION_DETECTED
    assert baseline_report.regressed_metrics


def test_baseline_report_needs_transfer_before_comparison() -> None:
    baseline = BaselineSystemRecord(
        baseline_id="baseline-static",
        name="Static prompt baseline",
        version="0.1",
        replayable_episode_count=1,
        transfer_success_rate=0.2,
        hidden_success_rate=0.1,
        failure_rate=0.8,
        evidence_ids=("baseline-evidence-1",),
    )

    baseline_report = build_baseline_report(
        report_id="baseline-report-blocked",
        transfer_report=_passing_transfer_report(),
        candidate=baseline,
        baseline=baseline,
        evidence_ids=("comparison-evidence-1",),
    )

    assert baseline_report.decision is BaselineComparisonDecision.NO_IMPROVEMENT
