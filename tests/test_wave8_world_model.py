"""Tests for Wave 8 world model."""

from __future__ import annotations

import pytest

from ix_cognition_kernel.wave8_environment_protocol import (
    BoundedEnvironmentSpec,
    EnvironmentActionResult,
    EnvironmentObservation,
)
from ix_cognition_kernel.wave8_episode_runner import BoundedEpisodeRun
from ix_cognition_kernel.wave8_episode_runner import run_single_step_episode
from ix_cognition_kernel.wave8_model_adapter import (
    DeterministicModelAdapter,
    ModelAdapterMode,
)
from ix_cognition_kernel.wave8_world_model import (
    RevisionDecision,
    WorldModelDecision,
    WorldModelRevision,
    WorldModelRule,
    WorldModelRuleStatus,
    WorldModelSnapshot,
    derive_rule_from_episode,
    revise_world_model,
)


def _environment() -> BoundedEnvironmentSpec:
    return BoundedEnvironmentSpec(
        environment_id="env-world",
        name="World Model Grid",
        version="1.0",
        supported_action_kinds=("move",),
        observable_feature_ids=("agent:0,0", "goal:1,0", "agent:1,0", "goal-reached"),
        terminal_feature_ids=("goal-reached",),
        forbidden_action_patterns=("network",),
    )


def _observation(
    *,
    observation_id: str = "obs-world",
    episode_id: str = "episode-world",
) -> EnvironmentObservation:
    return EnvironmentObservation(
        observation_id=observation_id,
        environment_id="env-world",
        episode_id=episode_id,
        visible_features=("agent:0,0", "goal:1,0"),
        hidden_feature_count=1,
    )


def _adapter() -> DeterministicModelAdapter:
    return DeterministicModelAdapter(
        adapter_id="adapter-world",
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


def _result(
    *,
    result_id: str = "result-world",
    action_id: str = "action-world",
    episode_id: str = "episode-world",
) -> EnvironmentActionResult:
    return EnvironmentActionResult(
        result_id=result_id,
        action_id=action_id,
        environment_id="env-world",
        episode_id=episode_id,
        next_features=("agent:1,0", "goal-reached"),
        measured_reward=1.0,
        terminal=True,
    )


def _run() -> BoundedEpisodeRun:
    return run_single_step_episode(
        run_id="run-world",
        step_id="step-world",
        output_id="output-world",
        draft_id="draft-world",
        action_id="action-world",
        frame_id="frame-world",
        environment=_environment(),
        observation=_observation(),
        adapter=_adapter(),
        result=_result(),
    )


def test_derive_rule_from_episode_run() -> None:
    rule = derive_rule_from_episode(
        rule_id="rule-move-east",
        episode_run=_run(),
        evidence_ids=("rule-evidence-1",),
    )

    assert rule.status is WorldModelRuleStatus.ACTIVE
    assert rule.precondition_features == ("agent:0,0", "goal:1,0")
    assert rule.effect_features == ("agent:1,0", "goal-reached")
    assert rule.confidence == pytest.approx(1.0)
    assert len(rule.fingerprint()) == 64


def test_derive_rule_from_unmeasured_episode_is_blocked() -> None:
    run = run_single_step_episode(
        run_id="run-unmeasured",
        step_id="step-unmeasured",
        output_id="output-unmeasured",
        draft_id="draft-unmeasured",
        action_id="action-unmeasured",
        frame_id="frame-unmeasured",
        environment=_environment(),
        observation=_observation(),
        adapter=_adapter(),
        result=None,
    )
    rule = derive_rule_from_episode(
        rule_id="rule-unmeasured",
        episode_run=run,
        evidence_ids=("rule-evidence-1",),
    )

    assert rule.status is WorldModelRuleStatus.BLOCKED
    assert "episode-not-replayable" in rule.findings


def test_world_model_snapshot_reports_active_rules() -> None:
    rule = derive_rule_from_episode(
        rule_id="rule-move-east",
        episode_run=_run(),
        evidence_ids=("rule-evidence-1",),
    )
    snapshot = WorldModelSnapshot(
        snapshot_id="snapshot-1",
        environment_id="env-world",
        rules=(rule,),
        evidence_ids=("snapshot-evidence-1",),
    )

    assert snapshot.decision is WorldModelDecision.READY_FOR_TRANSFER
    assert snapshot.active_rules == (rule,)


def test_world_model_snapshot_needs_rules() -> None:
    snapshot = WorldModelSnapshot(
        snapshot_id="snapshot-empty",
        environment_id="env-world",
        rules=(),
        evidence_ids=("snapshot-evidence-1",),
    )

    assert snapshot.decision is WorldModelDecision.NEEDS_RULES
    assert "no-active-rules" in snapshot.findings


def test_revise_world_model_adds_rule() -> None:
    rule = derive_rule_from_episode(
        rule_id="rule-move-east",
        episode_run=_run(),
        evidence_ids=("rule-evidence-1",),
    )
    snapshot = WorldModelSnapshot(
        snapshot_id="snapshot-before",
        environment_id="env-world",
        rules=(),
        evidence_ids=("snapshot-before-evidence",),
    )
    revision = revise_world_model(
        revision_id="revision-add",
        snapshot=snapshot,
        candidate_rules=(rule,),
        evidence_ids=("revision-evidence-1",),
    )

    assert revision.decision is RevisionDecision.REVISED
    assert revision.after.active_rules == (rule,)


def test_revise_world_model_rejects_contradicting_rule() -> None:
    rule = derive_rule_from_episode(
        rule_id="rule-move-east",
        episode_run=_run(),
        evidence_ids=("rule-evidence-1",),
    )
    contradictory = WorldModelRule(
        rule_id="rule-contradict",
        environment_id="env-world",
        action_kind="move",
        precondition_features=rule.precondition_features,
        effect_features=("agent:0,0",),
        confidence=0.9,
        status=WorldModelRuleStatus.ACTIVE,
        evidence_ids=("rule-evidence-2",),
    )
    snapshot = WorldModelSnapshot(
        snapshot_id="snapshot-before",
        environment_id="env-world",
        rules=(rule,),
        evidence_ids=("snapshot-before-evidence",),
    )
    revision = revise_world_model(
        revision_id="revision-contradiction",
        snapshot=snapshot,
        candidate_rules=(contradictory,),
        evidence_ids=("revision-evidence-1",),
    )

    assert revision.decision is RevisionDecision.REJECTED_CONTRADICTION
    assert any(
        finding.startswith("contradiction:")
        for finding in revision.findings
    )


def test_world_model_rule_rejects_overclaiming_effect() -> None:
    with pytest.raises(ValueError, match="blocked overclaiming"):
        WorldModelRule(
            rule_id="rule-overclaim",
            environment_id="env-world",
            action_kind="move",
            precondition_features=("agent:0,0",),
            effect_features=("certifies AGI",),
            confidence=0.5,
            status=WorldModelRuleStatus.ACTIVE,
            evidence_ids=("rule-evidence-1",),
        )
