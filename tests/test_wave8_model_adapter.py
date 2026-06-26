"""Tests for Wave 8 bounded model adapter."""

from __future__ import annotations

import pytest

from ix_cognition_kernel.wave8_environment_protocol import (
    BoundedEnvironmentSpec,
    EnvironmentObservation,
)
from ix_cognition_kernel.wave8_model_adapter import (
    DeterministicModelAdapter,
    ModelActionDraft,
    ModelAdapterDecision,
    ModelAdapterMode,
    ModelOutputDecision,
    build_model_action_draft,
)


def _environment() -> BoundedEnvironmentSpec:
    return BoundedEnvironmentSpec(
        environment_id="env-adapter",
        name="Adapter Grid",
        version="1.0",
        supported_action_kinds=("move", "inspect"),
        observable_feature_ids=("agent:0,0", "goal:1,0"),
        terminal_feature_ids=("goal-reached",),
        forbidden_action_patterns=("network",),
    )


def _observation() -> EnvironmentObservation:
    return EnvironmentObservation(
        observation_id="obs-adapter",
        environment_id="env-adapter",
        episode_id="episode-adapter",
        visible_features=("agent:0,0", "goal:1,0"),
        hidden_feature_count=2,
    )


def _adapter() -> DeterministicModelAdapter:
    return DeterministicModelAdapter(
        adapter_id="adapter-script",
        mode=ModelAdapterMode.REPLAY_SCRIPT,
        supported_action_kinds=("move", "inspect"),
        policy={
            "agent:0,0|goal:1,0": {
                "kind": "move",
                "parameters": {"direction": "east"},
                "confidence": 0.9,
                "rationale": "Move toward the visible goal.",
            }
        },
    )


def test_model_adapter_generates_bounded_output() -> None:
    output = _adapter().generate_output(
        output_id="output-1",
        environment=_environment(),
        observation=_observation(),
    )

    assert output.decision is ModelOutputDecision.ACTION_PROPOSED
    assert output.proposed_action_kind == "move"
    assert output.ready_for_action_draft
    assert len(output.fingerprint()) == 64


def test_model_adapter_blocks_unknown_observation_script() -> None:
    observation = EnvironmentObservation(
        observation_id="obs-unknown",
        environment_id="env-adapter",
        episode_id="episode-adapter",
        visible_features=("agent:9,9", "goal:1,0"),
        hidden_feature_count=1,
    )
    output = _adapter().generate_output(
        output_id="output-unknown",
        environment=_environment(),
        observation=observation,
    )

    assert output.decision is ModelOutputDecision.NO_ACTION
    assert not output.ready_for_action_draft
    assert "no-scripted-policy-match" in output.findings


def test_model_adapter_blocks_unsupported_action_kind() -> None:
    adapter = DeterministicModelAdapter(
        adapter_id="adapter-unsupported",
        mode=ModelAdapterMode.REPLAY_SCRIPT,
        supported_action_kinds=("move",),
        policy={
            "agent:0,0|goal:1,0": {
                "kind": "network",
                "parameters": {"target": "outside"},
                "confidence": 0.8,
                "rationale": "Try an unsupported action.",
            }
        },
    )
    output = adapter.generate_output(
        output_id="output-unsupported",
        environment=_environment(),
        observation=_observation(),
    )

    assert output.decision is ModelOutputDecision.BLOCKED_UNSUPPORTED_ACTION
    assert "unsupported-action-kind:network" in output.findings


def test_model_adapter_blocks_low_confidence() -> None:
    adapter = DeterministicModelAdapter(
        adapter_id="adapter-low-confidence",
        mode=ModelAdapterMode.REPLAY_SCRIPT,
        supported_action_kinds=("move",),
        policy={
            "agent:0,0|goal:1,0": {
                "kind": "move",
                "parameters": {"direction": "east"},
                "confidence": 0.1,
                "rationale": "Weak guess.",
            }
        },
    )
    output = adapter.generate_output(
        output_id="output-low-confidence",
        environment=_environment(),
        observation=_observation(),
    )

    assert output.decision is ModelOutputDecision.BLOCKED_LOW_CONFIDENCE
    assert "confidence-below-threshold" in output.findings


def test_model_action_draft_builds_environment_action() -> None:
    environment = _environment()
    observation = _observation()
    output = _adapter().generate_output(
        output_id="output-1",
        environment=environment,
        observation=observation,
    )
    draft = build_model_action_draft(
        draft_id="draft-1",
        action_id="action-1",
        environment=environment,
        observation=observation,
        model_output=output,
    )

    assert isinstance(draft, ModelActionDraft)
    assert draft.decision is ModelAdapterDecision.DRAFT_READY
    assert draft.ready
    assert draft.action_proposal is not None
    assert draft.action_proposal.kind == "move"


def test_model_action_draft_blocks_non_ready_model_output() -> None:
    environment = _environment()
    observation = EnvironmentObservation(
        observation_id="obs-unknown",
        environment_id="env-adapter",
        episode_id="episode-adapter",
        visible_features=("agent:9,9", "goal:1,0"),
        hidden_feature_count=1,
    )
    output = _adapter().generate_output(
        output_id="output-unknown",
        environment=environment,
        observation=observation,
    )
    draft = build_model_action_draft(
        draft_id="draft-blocked",
        action_id="action-blocked",
        environment=environment,
        observation=observation,
        model_output=output,
    )

    assert draft.decision is ModelAdapterDecision.MODEL_OUTPUT_BLOCKED
    assert not draft.ready
    assert draft.action_proposal is None


def test_model_adapter_rejects_overclaiming_identity() -> None:
    with pytest.raises(ValueError, match="blocked overclaiming"):
        DeterministicModelAdapter(
            adapter_id="adapter-agi",
            mode=ModelAdapterMode.REPLAY_SCRIPT,
            supported_action_kinds=("move",),
            policy={},
            notes=("certifies AGI",),
        )
