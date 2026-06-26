"""Tests for Wave 8 bounded environment protocol."""

from __future__ import annotations

import pytest

from ix_cognition_kernel.wave8_environment_protocol import (
    ActionAssessment,
    BoundedEnvironmentSpec,
    EnvironmentAction,
    EnvironmentActionResult,
    EnvironmentObservation,
    EnvironmentReplayDecision,
    EnvironmentTransitionStatus,
    assess_environment_action,
    build_environment_replay_frame,
)


def _environment() -> BoundedEnvironmentSpec:
    return BoundedEnvironmentSpec(
        environment_id="env-grid",
        name="Grid Navigation Sandbox",
        version="1.0",
        supported_action_kinds=("move", "inspect"),
        observable_feature_ids=("agent:0,0", "goal:1,0", "agent:1,0", "wall:0,1"),
        terminal_feature_ids=("goal-reached",),
        forbidden_action_patterns=("delete-world", "network"),
    )


def _observation() -> EnvironmentObservation:
    return EnvironmentObservation(
        observation_id="obs-1",
        environment_id="env-grid",
        episode_id="episode-1",
        visible_features=("agent:0,0", "goal:1,0"),
        hidden_feature_count=1,
    )


def test_environment_spec_is_deterministic_and_rejects_overclaiming() -> None:
    spec = _environment()

    assert spec.supports_action_kind("move")
    assert not spec.supports_action_kind("network")
    assert len(spec.fingerprint()) == 64

    with pytest.raises(ValueError, match="blocked overclaiming"):
        BoundedEnvironmentSpec(
            environment_id="env-agi",
            name="AGI environment",
            version="1.0",
            supported_action_kinds=("move",),
            observable_feature_ids=("feature",),
            terminal_feature_ids=("done",),
        )


def test_observation_rejects_duplicate_features() -> None:
    with pytest.raises(ValueError, match="Duplicate visible_feature"):
        EnvironmentObservation(
            observation_id="obs-dup",
            environment_id="env-grid",
            episode_id="episode-1",
            visible_features=("agent:0,0", "agent:0,0"),
            hidden_feature_count=0,
        )


def test_assess_action_allows_supported_action() -> None:
    spec = _environment()
    assessment = assess_environment_action(
        action_id="action-1",
        environment=spec,
        kind="move",
        parameters={"direction": "east"},
    )

    assert assessment.approved
    assert assessment.blocked_reasons == ()
    assert "supported-action-kind" in assessment.reasons


def test_assess_action_blocks_unknown_kind() -> None:
    assessment = assess_environment_action(
        action_id="action-unknown",
        environment=_environment(),
        kind="teleport",
        parameters={"target": "goal"},
    )

    assert not assessment.approved
    assert "unsupported-action-kind:teleport" in assessment.blocked_reasons


def test_assess_action_blocks_forbidden_pattern() -> None:
    assessment = assess_environment_action(
        action_id="action-forbidden",
        environment=_environment(),
        kind="move",
        parameters={"command": "delete-world"},
    )

    assert not assessment.approved
    assert "forbidden-action-pattern:delete-world" in assessment.blocked_reasons


def test_environment_action_requires_approved_assessment() -> None:
    spec = _environment()
    assessment = assess_environment_action(
        action_id="action-1",
        environment=spec,
        kind="move",
        parameters={"direction": "east"},
    )
    action = EnvironmentAction(
        action_id="action-1",
        environment_id="env-grid",
        episode_id="episode-1",
        kind="move",
        parameters=(("direction", "east"),),
        assessment=assessment,
    )

    assert action.ready
    assert len(action.fingerprint()) == 64


def test_environment_action_rejects_mismatched_assessment() -> None:
    assessment = ActionAssessment(
        action_id="different-action",
        environment_id="env-grid",
        approved=True,
        reasons=("supported-action-kind",),
        blocked_reasons=(),
    )

    with pytest.raises(ValueError, match="assessment action_id"):
        EnvironmentAction(
            action_id="action-1",
            environment_id="env-grid",
            episode_id="episode-1",
            kind="move",
            parameters=(("direction", "east"),),
            assessment=assessment,
        )


def test_environment_replay_frame_needs_measured_result_when_result_absent() -> None:
    spec = _environment()
    observation = _observation()
    assessment = assess_environment_action(
        action_id="action-1",
        environment=spec,
        kind="move",
        parameters={"direction": "east"},
    )
    action = EnvironmentAction(
        action_id="action-1",
        environment_id="env-grid",
        episode_id="episode-1",
        kind="move",
        parameters=(("direction", "east"),),
        assessment=assessment,
    )

    frame = build_environment_replay_frame(
        frame_id="frame-1",
        environment=spec,
        observation=observation,
        action=action,
        result=None,
    )

    assert frame.status is EnvironmentTransitionStatus.NEEDS_MEASURED_RESULT
    assert frame.decision is EnvironmentReplayDecision.NEEDS_MEASURED_RESULT
    assert not frame.replayable


def test_environment_replay_frame_is_replayable_with_measured_terminal_result() -> None:
    spec = _environment()
    observation = _observation()
    assessment = assess_environment_action(
        action_id="action-1",
        environment=spec,
        kind="move",
        parameters={"direction": "east"},
    )
    action = EnvironmentAction(
        action_id="action-1",
        environment_id="env-grid",
        episode_id="episode-1",
        kind="move",
        parameters=(("direction", "east"),),
        assessment=assessment,
    )
    result = EnvironmentActionResult(
        result_id="result-1",
        action_id="action-1",
        environment_id="env-grid",
        episode_id="episode-1",
        next_features=("agent:1,0", "goal-reached"),
        measured_reward=1.0,
        terminal=True,
    )

    frame = build_environment_replay_frame(
        frame_id="frame-1",
        environment=spec,
        observation=observation,
        action=action,
        result=result,
    )

    assert frame.status is EnvironmentTransitionStatus.TERMINAL
    assert frame.decision is EnvironmentReplayDecision.REPLAYABLE
    assert frame.replayable
    assert frame.fingerprint() == build_environment_replay_frame(
        frame_id="frame-1",
        environment=spec,
        observation=observation,
        action=action,
        result=result,
    ).fingerprint()


def test_environment_replay_frame_blocks_unapproved_action() -> None:
    spec = _environment()
    observation = _observation()
    assessment = ActionAssessment(
        action_id="action-blocked",
        environment_id="env-grid",
        approved=False,
        reasons=(),
        blocked_reasons=("unsupported-action-kind:network",),
    )
    action = EnvironmentAction(
        action_id="action-blocked",
        environment_id="env-grid",
        episode_id="episode-1",
        kind="network",
        parameters=(("target", "outside"),),
        assessment=assessment,
    )

    frame = build_environment_replay_frame(
        frame_id="frame-blocked",
        environment=spec,
        observation=observation,
        action=action,
        result=None,
    )

    assert frame.status is EnvironmentTransitionStatus.BLOCKED
    assert frame.decision is EnvironmentReplayDecision.BLOCKED
    assert not frame.replayable
