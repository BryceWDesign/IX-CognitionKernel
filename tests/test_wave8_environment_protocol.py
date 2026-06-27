import pytest

from ix_cognition_kernel.wave8_environment_protocol import (
    BoundedEnvironmentSpec,
    EnvironmentActionDecision,
    EnvironmentActionProposal,
    EnvironmentActionResult,
    EnvironmentBoundary,
    EnvironmentKind,
    EnvironmentObservation,
    EnvironmentTransitionStatus,
    assess_environment_action,
    build_environment_replay_frame,
)


def _environment() -> BoundedEnvironmentSpec:
    return BoundedEnvironmentSpec(
        environment_id="env-grid-1",
        kind=EnvironmentKind.GRID_ABSTRACTION,
        objective="Infer the next bounded state transition from visible cells.",
        observation_channels=("grid-visible-state",),
        action_space_ids=("move-east", "move-west", "inspect-cell"),
        scoring_rules=("reward-correct-transition", "penalize-unmeasured-claim"),
        reset_evidence_ids=("reset-evidence-1",),
    )


def _observation(*, measured: bool = True) -> EnvironmentObservation:
    return EnvironmentObservation(
        observation_id="obs-1",
        environment_id="env-grid-1",
        episode_id="episode-1",
        state_id="state-1",
        channel_id="grid-visible-state",
        summary="The agent sees an empty cell to the east.",
        visible_features=("agent-at-0-0", "east-cell-empty"),
        evidence_ids=("obs-evidence-1",),
        step_index=0,
        measured=measured,
    )


def _action(
    *,
    operation_id: str = "move-east",
    boundary: EnvironmentBoundary = EnvironmentBoundary.SIMULATION_ONLY,
) -> EnvironmentActionProposal:
    return EnvironmentActionProposal(
        action_id="action-1",
        environment_id="env-grid-1",
        episode_id="episode-1",
        actor_id="deterministic-model-adapter-1",
        operation_id=operation_id,
        rationale="Move east only inside the bounded environment.",
        expected_effect="The next state should place the agent at 1-0.",
        precondition_state_ids=("state-1",),
        evidence_ids=("action-evidence-1",),
        boundary=boundary,
    )


def _result(*, measured: bool = True) -> EnvironmentActionResult:
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
    )


def test_bounded_environment_spec_is_deterministic_and_rejects_live_actuation() -> None:
    environment = _environment()

    assert environment.fingerprint() == environment.fingerprint()
    assert len(environment.fingerprint()) == 64
    assert environment.canonical_payload()["permits_live_actuation"] is False

    with pytest.raises(ValueError, match="must not permit live actuation"):
        BoundedEnvironmentSpec(
            environment_id="env-live",
            kind=EnvironmentKind.TOOL_USE_SIMULATION,
            objective="Bad live boundary.",
            observation_channels=("tool-state",),
            action_space_ids=("write-file",),
            scoring_rules=("score-live-change",),
            reset_evidence_ids=("reset-evidence-1",),
            permits_live_actuation=True,
        )


def test_environment_observation_rejects_ground_truth_claims() -> None:
    observation = _observation()

    assert observation.fingerprint() == observation.fingerprint()
    assert len(observation.fingerprint()) == 64

    with pytest.raises(ValueError, match="must not claim ground truth"):
        EnvironmentObservation(
            observation_id="obs-ground-truth",
            environment_id="env-grid-1",
            episode_id="episode-1",
            state_id="state-1",
            channel_id="grid-visible-state",
            summary="Bad ground truth claim.",
            visible_features=("agent-at-0-0",),
            evidence_ids=("obs-evidence-1",),
            claims_ground_truth=True,
        )


def test_environment_action_rejects_self_authority_and_completion_claims() -> None:
    with pytest.raises(ValueError, match="must not self-authorize"):
        EnvironmentActionProposal(
            action_id="action-self-authorized",
            environment_id="env-grid-1",
            episode_id="episode-1",
            actor_id="deterministic-model-adapter-1",
            operation_id="move-east",
            rationale="Bad self authority.",
            expected_effect="Bad effect.",
            precondition_state_ids=("state-1",),
            evidence_ids=("action-evidence-1",),
            self_authorized=True,
        )

    with pytest.raises(ValueError, match="must not claim completion"):
        EnvironmentActionProposal(
            action_id="action-completion-claim",
            environment_id="env-grid-1",
            episode_id="episode-1",
            actor_id="deterministic-model-adapter-1",
            operation_id="move-east",
            rationale="Bad completion claim.",
            expected_effect="Bad effect.",
            precondition_state_ids=("state-1",),
            evidence_ids=("action-evidence-1",),
            claims_completion=True,
        )


def test_assess_environment_action_is_fail_closed() -> None:
    environment = _environment()
    observation = _observation()

    assert (
        assess_environment_action(
            environment=environment,
            observation=observation,
            action=_action(),
        )
        is EnvironmentActionDecision.READY_FOR_BOUNDED_RUN
    )
    assert (
        assess_environment_action(
            environment=environment,
            observation=observation,
            action=_action(boundary=EnvironmentBoundary.LIVE_ACTUATION),
        )
        is EnvironmentActionDecision.BLOCKED_LIVE_ACTUATION
    )
    assert (
        assess_environment_action(
            environment=environment,
            observation=observation,
            action=_action(operation_id="write-file"),
        )
        is EnvironmentActionDecision.OUT_OF_SCOPE
    )
    assert (
        assess_environment_action(
            environment=environment,
            observation=_observation(measured=False),
            action=_action(),
        )
        is EnvironmentActionDecision.NEEDS_MORE_EVIDENCE
    )


def test_replay_frame_requires_measured_result_before_learning_claims() -> None:
    frame_without_result = build_environment_replay_frame(
        frame_id="frame-1",
        environment=_environment(),
        observation=_observation(),
        action=_action(),
        result=None,
        notes=("first bounded transition",),
    )
    frame_with_unmeasured_result = build_environment_replay_frame(
        frame_id="frame-2",
        environment=_environment(),
        observation=_observation(),
        action=_action(),
        result=_result(measured=False),
    )
    frame_with_measured_result = build_environment_replay_frame(
        frame_id="frame-3",
        environment=_environment(),
        observation=_observation(),
        action=_action(),
        result=_result(),
    )

    assert (
        frame_without_result.status is EnvironmentTransitionStatus.NEEDS_MEASURED_RESULT
    )
    assert (
        frame_with_unmeasured_result.status
        is EnvironmentTransitionStatus.NEEDS_MEASURED_RESULT
    )
    assert frame_with_measured_result.status is EnvironmentTransitionStatus.REPLAYABLE
    assert frame_with_measured_result.replayable
    assert (
        frame_with_measured_result.fingerprint()
        == frame_with_measured_result.fingerprint()
    )


def test_replay_frame_blocks_out_of_scope_transition() -> None:
    blocked_frame = build_environment_replay_frame(
        frame_id="frame-blocked",
        environment=_environment(),
        observation=_observation(),
        action=_action(operation_id="delete-host-file"),
        result=None,
    )

    assert blocked_frame.status is EnvironmentTransitionStatus.BLOCKED
    assert not blocked_frame.replayable


def test_replay_frame_rejects_inconsistent_result_identity() -> None:
    bad_result = EnvironmentActionResult(
        result_id="bad-result",
        action_id="other-action",
        environment_id="env-grid-1",
        episode_id="episode-1",
        prior_state_id="state-1",
        resulting_state_id="state-2",
        outcome_summary="Mismatched action result.",
        score_delta=0.0,
        evidence_ids=("result-evidence-1",),
        measured=True,
    )

    with pytest.raises(ValueError, match="Mismatched action_id"):
        build_environment_replay_frame(
            frame_id="frame-bad-result",
            environment=_environment(),
            observation=_observation(),
            action=_action(),
            result=bad_result,
        )
