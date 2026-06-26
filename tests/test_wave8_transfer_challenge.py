"""Tests for Wave 8 transfer challenge."""

from __future__ import annotations

from ix_cognition_kernel.wave8_curriculum_frontier import (
    CurriculumFrontier,
    FrontierPressure,
)
from ix_cognition_kernel.wave8_environment_protocol import (
    BoundedEnvironmentSpec,
    EnvironmentActionResult,
    EnvironmentObservation,
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
    TransferClaimDecision,
    TransferTrialStatus,
    build_transfer_trial,
    evaluate_transfer_challenge,
)


def _environment() -> BoundedEnvironmentSpec:
    return BoundedEnvironmentSpec(
        environment_id="env-transfer",
        name="Transfer Grid",
        version="1.0",
        supported_action_kinds=("move",),
        observable_feature_ids=("agent:0,0", "goal:1,0", "agent:1,0", "goal-reached"),
        terminal_feature_ids=("goal-reached",),
        forbidden_action_patterns=("network",),
    )


def _observation(*, task_id: str) -> EnvironmentObservation:
    return EnvironmentObservation(
        observation_id=f"obs-{task_id}",
        environment_id="env-transfer",
        episode_id=f"episode-{task_id}",
        visible_features=("agent:0,0", "goal:1,0"),
        hidden_feature_count=2,
    )


def _task(task_id: str, band: TaskDifficultyBand) -> UnknownTaskInstance:
    return UnknownTaskInstance(
        task_id=task_id,
        environment_id="env-transfer",
        difficulty_band=band,
        initial_observation=_observation(task_id=task_id),
        allowed_action_kinds=("move",),
        expected_outcome_features=("goal-reached", "operation:move-east"),
        novelty_factors=("novel-map",),
        transfer_tags=("grid", "move-east"),
        evidence_ids=(f"task-evidence-{task_id}",),
    )


def _adapter() -> DeterministicModelAdapter:
    return DeterministicModelAdapter(
        adapter_id="adapter-transfer",
        mode=ModelAdapterMode.REPLAY_SCRIPT,
        supported_action_kinds=("move",),
        policy={
            "agent:0,0|goal:1,0": {
                "kind": "move",
                "parameters": {"direction": "east"},
                "confidence": 0.9,
                "rationale": "Move east toward goal.",
            }
        },
    )


def _passing_run(*, task: UnknownTaskInstance) -> object:
    result = EnvironmentActionResult(
        result_id=f"result-{task.task_id}",
        action_id=f"action-{task.task_id}",
        environment_id="env-transfer",
        episode_id=task.initial_observation.episode_id,
        next_features=("agent:1,0", "goal-reached"),
        measured_reward=1.0,
        terminal=True,
    )
    return run_single_step_episode(
        run_id=f"run-{task.task_id}",
        step_id=f"step-{task.task_id}",
        output_id=f"output-{task.task_id}",
        draft_id=f"draft-{task.task_id}",
        action_id=f"action-{task.task_id}",
        frame_id=f"frame-{task.task_id}",
        environment=_environment(),
        observation=task.initial_observation,
        adapter=_adapter(),
        result=result,
    )


def _suite() -> CurriculumFrontier:
    tasks = (
        _task("task-near", TaskDifficultyBand.TRANSFER_NEAR),
        _task("task-far", TaskDifficultyBand.TRANSFER_FAR),
        _task("task-hidden", TaskDifficultyBand.HIDDEN),
    )
    return CurriculumFrontier(
        frontier_id="frontier-transfer",
        purpose="Exercise bounded transfer challenge.",
        pressures=(
            FrontierPressure(
                pressure_id="pressure-transfer",
                target_skill="move-east",
                difficulty_band=TaskDifficultyBand.TRANSFER_NEAR,
                transfer_tags=("grid",),
                required_feature_ids=("goal-reached",),
                forbidden_shortcuts=("memorized-start",),
            ),
        ),
        tasks=tasks,
        evidence_ids=("frontier-evidence-1",),
    )


def test_transfer_trial_passes_with_replayable_episode() -> None:
    task = _task("task-near", TaskDifficultyBand.TRANSFER_NEAR)
    trial = build_transfer_trial(
        trial_id="trial-near",
        task=task,
        band=TransferBand.NEAR,
        episode_run=_passing_run(task=task),
    )

    assert trial.status is TransferTrialStatus.REPLAYABLE_PASS
    assert trial.ready
    assert trial.observed_feature_ids == ("agent:1,0", "goal-reached")


def test_transfer_trial_needs_measured_result_when_episode_is_unmeasured() -> None:
    task = _task("task-unmeasured", TaskDifficultyBand.TRANSFER_NEAR)
    run = run_single_step_episode(
        run_id="run-unmeasured",
        step_id="step-unmeasured",
        output_id="output-unmeasured",
        draft_id="draft-unmeasured",
        action_id="action-unmeasured",
        frame_id="frame-unmeasured",
        environment=_environment(),
        observation=task.initial_observation,
        adapter=_adapter(),
        result=None,
    )
    trial = build_transfer_trial(
        trial_id="trial-unmeasured",
        task=task,
        band=TransferBand.NEAR,
        episode_run=run,
    )

    assert trial.status is TransferTrialStatus.NEEDS_MEASURED_RESULT
    assert not trial.ready
    assert "episode-run-not-replayable" in trial.findings


def test_transfer_report_demonstrates_transfer_with_required_bands() -> None:
    suite = _suite()
    trials = tuple(
        build_transfer_trial(
            trial_id=f"trial-{task.task_id}",
            task=task,
            band=(
                TransferBand.NEAR
                if task.difficulty_band is TaskDifficultyBand.TRANSFER_NEAR
                else TransferBand.FAR
                if task.difficulty_band is TaskDifficultyBand.TRANSFER_FAR
                else TransferBand.HIDDEN
            ),
            episode_run=_passing_run(task=task),
        )
        for task in suite.tasks
    )
    report = evaluate_transfer_challenge(
        report_id="report-transfer",
        suite=suite,
        trials=trials,
    )

    assert report.decision is TransferClaimDecision.TRANSFER_DEMONSTRATED
    assert report.pass_count == 3
    assert report.hidden_pass_count == 1


def test_transfer_report_needs_hidden_validation() -> None:
    suite = _suite()
    tasks = suite.tasks[:2]
    trials = tuple(
        build_transfer_trial(
            trial_id=f"trial-{task.task_id}",
            task=task,
            band=(
                TransferBand.NEAR
                if task.difficulty_band is TaskDifficultyBand.TRANSFER_NEAR
                else TransferBand.FAR
            ),
            episode_run=_passing_run(task=task),
        )
        for task in tasks
    )
    report = evaluate_transfer_challenge(
        report_id="report-needs-hidden",
        suite=suite,
        trials=trials,
    )

    assert report.decision is TransferClaimDecision.NEEDS_HIDDEN_VALIDATION
    assert "missing-required-band:hidden" in report.findings


def test_transfer_report_blocks_with_failed_trial() -> None:
    task = _task("task-unmeasured", TaskDifficultyBand.TRANSFER_NEAR)
    run = run_single_step_episode(
        run_id="run-unmeasured",
        step_id="step-unmeasured",
        output_id="output-unmeasured",
        draft_id="draft-unmeasured",
        action_id="action-unmeasured",
        frame_id="frame-unmeasured",
        environment=_environment(),
        observation=task.initial_observation,
        adapter=_adapter(),
        result=None,
    )
    suite = _suite()
    trial = build_transfer_trial(
        trial_id="trial-unmeasured",
        task=task,
        band=TransferBand.NEAR,
        episode_run=run,
    )
    report = evaluate_transfer_challenge(
        report_id="report-blocked",
        suite=suite,
        trials=(trial,),
    )

    assert report.decision is TransferClaimDecision.BLOCKED
    assert report.blocked_count == 1
