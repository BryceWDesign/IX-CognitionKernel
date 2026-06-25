import pytest

from ix_cognition_kernel.wave8_environment_protocol import (
    BoundedEnvironmentSpec,
    EnvironmentActionResult,
    EnvironmentKind,
    EnvironmentObservation,
)
from ix_cognition_kernel.wave8_episode_runner import (
    BoundedEpisodeRun,
    EpisodeRunStatus,
    EpisodeStepDecision,
    run_single_step_episode,
)
from ix_cognition_kernel.wave8_model_adapter import (
    DeterministicModelAdapter,
    DeterministicModelPolicy,
)


def _environment() -> BoundedEnvironmentSpec:
    return BoundedEnvironmentSpec(
        environment_id="env-grid-1",
        kind=EnvironmentKind.GRID_ABSTRACTION,
        objective="Infer a bounded grid transition.",
        observation_channels=("grid-visible-state",),
        action_space_ids=("move-east", "inspect-cell"),
        scoring_rules=("score-correct-transition",),
        reset_evidence_ids=("reset-evidence-1",),
    )


def _observation(*, measured: bool = True) -> EnvironmentObservation:
    return EnvironmentObservation(
        observation_id="obs-1",
        environment_id="env-grid-1",
        episode_id="episode-1",
        state_id="state-1",
        channel_id="grid-visible-state",
        summary="The east cell is visibly empty.",
        visible_features=("agent-at-0-0", "east-cell-empty"),
        evidence_ids=("obs-evidence-1",),
        measured=measured,
    )


def _result(*, measured: bool = True, terminal: bool = False) -> EnvironmentActionResult:
    return EnvironmentActionResult(
        result_id="result-1",
        action_id="action-1",
        environment_id="env-grid-1",
        episode_id="episode-1",
        prior_state_id="state-1",
        resulting_state_id="state-2",
        outcome_summary="The bounded grid transitioned to agent-at-1-0.",
        score_delta=1.0,
        evidence_ids=("result-evidence-1",),
        measured=measured,
        terminal=terminal,
    )


def _adapter(
    *, operation_preferences: tuple[str, ...] = ("move-east",)
) -> DeterministicModelAdapter:
    return DeterministicModelAdapter(
        adapter_id="deterministic-adapter-1",
        policy=DeterministicModelPolicy(
            policy_id="policy-1",
            supported_environment_ids=("env-grid-1",),
            operation_preferences=operation_preferences,
            rationale_template="Use {operation_id} from {state_id}.",
            expected_effect_template="{operation_id} should change the bounded state.",
            evidence_ids=("policy-evidence-1",),
            assumptions=("visible-state-is-current",),
            uncertainty_ids=("uncertainty-grid-transition",),
        ),
    )


def test_single_step_episode_becomes_replayable_with_measured_result() -> None:
    run = run_single_step_episode(
        run_id="run-1",
        step_id="step-1",
        output_id="model-output-1",
        draft_id="draft-1",
        action_id="action-1",
        frame_id="frame-1",
        environment=_environment(),
        observation=_observation(),
        adapter=_adapter(),
        result=_result(terminal=True),
        notes=("first bounded episode",),
    )

    assert run.status is EpisodeRunStatus.REPLAYABLE
    assert run.replayable
    assert run.terminal
    assert run.steps[0].decision is EpisodeStepDecision.COMPLETED_REPLAYABLE
    assert run.fingerprint() == run.fingerprint()
    assert len(run.fingerprint()) == 64


def test_single_step_episode_requires_measured_result_before_learning_claim() -> None:
    run_without_result = run_single_step_episode(
        run_id="run-1",
        step_id="step-1",
        output_id="model-output-1",
        draft_id="draft-1",
        action_id="action-1",
        frame_id="frame-1",
        environment=_environment(),
        observation=_observation(),
        adapter=_adapter(),
        result=None,
    )
    run_with_unmeasured_result = run_single_step_episode(
        run_id="run-2",
        step_id="step-1",
        output_id="model-output-1",
        draft_id="draft-1",
        action_id="action-1",
        frame_id="frame-1",
        environment=_environment(),
        observation=_observation(),
        adapter=_adapter(),
        result=_result(measured=False),
    )

    assert run_without_result.status is EpisodeRunStatus.NEEDS_MEASURED_RESULT
    assert not run_without_result.replayable
    assert run_without_result.steps[0].decision is EpisodeStepDecision.NEEDS_MEASURED_RESULT
    assert run_with_unmeasured_result.status is EpisodeRunStatus.NEEDS_MEASURED_RESULT
    assert not run_with_unmeasured_result.replayable


def test_single_step_episode_blocks_unsupported_model_operation() -> None:
    run = run_single_step_episode(
        run_id="run-blocked",
        step_id="step-1",
        output_id="model-output-1",
        draft_id="draft-1",
        action_id="action-1",
        frame_id="frame-1",
        environment=_environment(),
        observation=_observation(),
        adapter=_adapter(operation_preferences=("delete-host-file",)),
        result=None,
    )

    assert run.status is EpisodeRunStatus.BLOCKED
    assert not run.replayable
    assert run.steps[0].decision is EpisodeStepDecision.BLOCKED_MODEL_ACTION_DRAFT
    assert run.steps[0].replay_frame is None


def test_single_step_episode_blocks_unmeasured_observation() -> None:
    run = run_single_step_episode(
        run_id="run-unmeasured-observation",
        step_id="step-1",
        output_id="model-output-1",
        draft_id="draft-1",
        action_id="action-1",
        frame_id="frame-1",
        environment=_environment(),
        observation=_observation(measured=False),
        adapter=_adapter(),
        result=None,
    )

    assert run.status is EpisodeRunStatus.BLOCKED
    assert not run.replayable
    assert run.steps[0].decision is EpisodeStepDecision.BLOCKED_MODEL_ACTION_DRAFT


def test_episode_run_rejects_empty_steps() -> None:
    with pytest.raises(ValueError, match="require at least one step"):
        BoundedEpisodeRun(
            run_id="run-empty",
            episode_id="episode-1",
            environment=_environment(),
            initial_observation=_observation(),
            steps=(),
        )


def test_episode_run_rejects_non_contiguous_step_indexes() -> None:
    first_run = run_single_step_episode(
        run_id="run-1",
        step_id="step-1",
        output_id="model-output-1",
        draft_id="draft-1",
        action_id="action-1",
        frame_id="frame-1",
        environment=_environment(),
        observation=_observation(),
        adapter=_adapter(),
        result=_result(),
    )
    bad_step = first_run.steps[0].__class__(
        step_id="step-2",
        step_index=2,
        model_output=first_run.steps[0].model_output,
        action_draft=first_run.steps[0].action_draft,
        replay_frame=first_run.steps[0].replay_frame,
        decision=first_run.steps[0].decision,
    )

    with pytest.raises(ValueError, match="step indexes must be contiguous"):
        BoundedEpisodeRun(
            run_id="run-bad-index",
            episode_id="episode-1",
            environment=_environment(),
            initial_observation=_observation(),
            steps=(first_run.steps[0], bad_step),
        )
