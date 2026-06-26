"""Tests for Wave 8 bounded episode runner."""

from __future__ import annotations

from ix_cognition_kernel.wave8_environment_protocol import (
    ActionAssessment,
    BoundedEnvironmentSpec,
    EnvironmentAction,
    EnvironmentActionResult,
    EnvironmentObservation,
)
from ix_cognition_kernel.wave8_episode_runner import (
    EpisodeRunStatus,
    EpisodeStepDecision,
    build_episode_run,
    run_single_step_episode,
)
from ix_cognition_kernel.wave8_model_adapter import (
    DeterministicModelAdapter,
    ModelAdapterMode,
    build_model_action_draft,
)


def _environment() -> BoundedEnvironmentSpec:
    return BoundedEnvironmentSpec(
        environment_id="env-runner",
        name="Episode Runner Grid",
        version="1.0",
        supported_action_kinds=("move", "inspect"),
        observable_feature_ids=("agent:0,0", "goal:1,0", "agent:1,0", "goal-reached"),
        terminal_feature_ids=("goal-reached",),
        forbidden_action_patterns=("network",),
    )


def _observation() -> EnvironmentObservation:
    return EnvironmentObservation(
        observation_id="obs-runner",
        environment_id="env-runner",
        episode_id="episode-runner",
        visible_features=("agent:0,0", "goal:1,0"),
        hidden_feature_count=1,
    )


def _adapter() -> DeterministicModelAdapter:
    return DeterministicModelAdapter(
        adapter_id="adapter-runner",
        mode=ModelAdapterMode.REPLAY_SCRIPT,
        supported_action_kinds=("move", "inspect"),
        policy={
            "agent:0,0|goal:1,0": {
                "kind": "move",
                "parameters": {"direction": "east"},
                "confidence": 0.91,
                "rationale": "Move toward visible goal.",
            }
        },
    )


def _result() -> EnvironmentActionResult:
    return EnvironmentActionResult(
        result_id="result-runner",
        action_id="action-runner",
        environment_id="env-runner",
        episode_id="episode-runner",
        next_features=("agent:1,0", "goal-reached"),
        measured_reward=1.0,
        terminal=True,
    )


def test_single_step_episode_is_replayable_with_measured_result() -> None:
    run = run_single_step_episode(
        run_id="run-1",
        step_id="step-1",
        output_id="output-1",
        draft_id="draft-1",
        action_id="action-runner",
        frame_id="frame-1",
        environment=_environment(),
        observation=_observation(),
        adapter=_adapter(),
        result=_result(),
    )

    assert run.status is EpisodeRunStatus.REPLAYABLE
    assert run.replayable
    assert run.terminal
    assert run.steps[0].decision is EpisodeStepDecision.COMPLETED_REPLAYABLE
    assert len(run.fingerprint()) == 64


def test_single_step_episode_needs_measured_result_without_result() -> None:
    run = run_single_step_episode(
        run_id="run-unmeasured",
        step_id="step-unmeasured",
        output_id="output-unmeasured",
        draft_id="draft-unmeasured",
        action_id="action-runner",
        frame_id="frame-unmeasured",
        environment=_environment(),
        observation=_observation(),
        adapter=_adapter(),
        result=None,
    )

    assert run.status is EpisodeRunStatus.NEEDS_MEASURED_RESULT
    assert not run.replayable
    assert run.steps[0].decision is EpisodeStepDecision.NEEDS_MEASURED_RESULT


def test_single_step_episode_blocks_unknown_model_action() -> None:
    adapter = DeterministicModelAdapter(
        adapter_id="adapter-blocked",
        mode=ModelAdapterMode.REPLAY_SCRIPT,
        supported_action_kinds=("move", "inspect"),
        policy={
            "agent:0,0|goal:1,0": {
                "kind": "network",
                "parameters": {"target": "outside"},
                "confidence": 0.9,
                "rationale": "Attempt forbidden external action.",
            }
        },
    )
    run = run_single_step_episode(
        run_id="run-blocked",
        step_id="step-blocked",
        output_id="output-blocked",
        draft_id="draft-blocked",
        action_id="action-blocked",
        frame_id="frame-blocked",
        environment=_environment(),
        observation=_observation(),
        adapter=adapter,
        result=None,
    )

    assert run.status is EpisodeRunStatus.BLOCKED
    assert not run.replayable
    assert run.steps[0].decision is EpisodeStepDecision.BLOCKED_MODEL_ACTION_DRAFT
    assert run.steps[0].replay_frame is None


def test_episode_run_builder_preserves_step_continuity() -> None:
    run = run_single_step_episode(
        run_id="run-builder",
        step_id="step-builder",
        output_id="output-builder",
        draft_id="draft-builder",
        action_id="action-runner",
        frame_id="frame-builder",
        environment=_environment(),
        observation=_observation(),
        adapter=_adapter(),
        result=_result(),
    )
    rebuilt = build_episode_run(
        run_id="run-rebuilt",
        episode_id="episode-runner",
        environment=_environment(),
        initial_observation=_observation(),
        steps=run.steps,
        terminal=True,
        notes=("rebuilt-for-test",),
    )

    assert rebuilt.status is EpisodeRunStatus.REPLAYABLE
    assert rebuilt.steps == run.steps
    assert rebuilt.notes == ("rebuilt-for-test",)


def test_episode_run_blocks_environment_rejected_action() -> None:
    environment = _environment()
    observation = _observation()
    model_output = _adapter().generate_output(
        output_id="output-direct",
        environment=environment,
        observation=observation,
    )
    action_draft = build_model_action_draft(
        draft_id="draft-direct",
        action_id="action-direct",
        environment=environment,
        observation=observation,
        model_output=model_output,
    )
    assert action_draft.action_proposal is not None
    blocked_assessment = ActionAssessment(
        action_id="action-direct",
        environment_id="env-runner",
        approved=False,
        reasons=(),
        blocked_reasons=("policy-block",),
    )
    blocked_action = EnvironmentAction(
        action_id="action-direct",
        environment_id="env-runner",
        episode_id="episode-runner",
        kind="move",
        parameters=(("direction", "east"),),
        assessment=blocked_assessment,
    )
    from ix_cognition_kernel.wave8_environment_protocol import (
        build_environment_replay_frame,
    )

    frame = build_environment_replay_frame(
        frame_id="frame-direct",
        environment=environment,
        observation=observation,
        action=blocked_action,
        result=None,
    )
    from ix_cognition_kernel.wave8_episode_runner import EpisodeStepTrace

    step = EpisodeStepTrace(
        step_id="step-direct",
        step_index=0,
        model_output=model_output,
        action_draft=action_draft,
        replay_frame=frame,
        decision=EpisodeStepDecision.BLOCKED_ENVIRONMENT_ACTION,
    )
    run = build_episode_run(
        run_id="run-direct",
        episode_id="episode-runner",
        environment=environment,
        initial_observation=observation,
        steps=(step,),
    )

    assert run.status is EpisodeRunStatus.BLOCKED
