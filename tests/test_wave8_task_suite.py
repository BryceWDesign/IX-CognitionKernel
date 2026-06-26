"""Tests for Wave 8 unknown task suite."""

from __future__ import annotations

import pytest

from ix_cognition_kernel.wave8_environment_protocol import EnvironmentObservation
from ix_cognition_kernel.wave8_task_suite import (
    TaskDifficultyBand,
    UnknownTaskDecision,
    UnknownTaskInstance,
    UnknownTaskSuite,
    build_unknown_task_suite,
)


def _observation() -> EnvironmentObservation:
    return EnvironmentObservation(
        observation_id="obs-task",
        environment_id="env-grid",
        episode_id="episode-task",
        visible_features=("agent:0,0", "goal:1,0"),
        hidden_feature_count=3,
    )


def _task(
    task_id: str,
    band: TaskDifficultyBand,
    novelty: tuple[str, ...] = ("new-map",),
) -> UnknownTaskInstance:
    return UnknownTaskInstance(
        task_id=task_id,
        environment_id="env-grid",
        difficulty_band=band,
        initial_observation=_observation(),
        allowed_action_kinds=("move", "inspect"),
        expected_outcome_features=("goal-reached",),
        novelty_factors=novelty,
        transfer_tags=("grid-world", "pathfinding"),
        evidence_ids=(f"evidence-{task_id}",),
    )


def test_unknown_task_instance_is_deterministic_and_replayable() -> None:
    task = _task("task-1", TaskDifficultyBand.TRANSFER_NEAR)

    assert task.decision is UnknownTaskDecision.READY_FOR_TRIAL
    assert len(task.fingerprint()) == 64


def test_unknown_task_instance_requires_novelty() -> None:
    task = _task("task-no-novelty", TaskDifficultyBand.TRANSFER_NEAR, novelty=())

    assert task.decision is UnknownTaskDecision.NEEDS_NOVELTY


def test_unknown_task_instance_rejects_overclaiming_expected_outcome() -> None:
    with pytest.raises(ValueError, match="blocked overclaiming"):
        UnknownTaskInstance(
            task_id="task-overclaim",
            environment_id="env-grid",
            difficulty_band=TaskDifficultyBand.TRANSFER_NEAR,
            initial_observation=_observation(),
            allowed_action_kinds=("move",),
            expected_outcome_features=("certifies AGI",),
            novelty_factors=("new-map",),
            transfer_tags=("grid-world",),
            evidence_ids=("task-evidence",),
        )


def test_unknown_task_suite_ready_with_required_bands() -> None:
    suite = build_unknown_task_suite(
        suite_id="suite-ready",
        purpose="Exercise bounded transfer without overclaiming.",
        tasks=(
            _task("task-near", TaskDifficultyBand.TRANSFER_NEAR),
            _task("task-far", TaskDifficultyBand.TRANSFER_FAR),
            _task("task-hidden", TaskDifficultyBand.HIDDEN),
        ),
        required_bands=(
            TaskDifficultyBand.TRANSFER_NEAR,
            TaskDifficultyBand.TRANSFER_FAR,
            TaskDifficultyBand.HIDDEN,
        ),
        evidence_ids=("suite-evidence",),
    )

    assert suite.decision is UnknownTaskDecision.READY_FOR_TRIAL
    assert suite.ready_task_count == 3
    assert len(suite.fingerprint()) == 64


def test_unknown_task_suite_requires_band_coverage() -> None:
    suite = build_unknown_task_suite(
        suite_id="suite-missing-band",
        purpose="Exercise bounded transfer without overclaiming.",
        tasks=(_task("task-near", TaskDifficultyBand.TRANSFER_NEAR),),
        required_bands=(
            TaskDifficultyBand.TRANSFER_NEAR,
            TaskDifficultyBand.TRANSFER_FAR,
        ),
        evidence_ids=("suite-evidence",),
    )

    assert suite.decision is UnknownTaskDecision.NEEDS_BAND_COVERAGE
    assert "missing-required-band:transfer-far" in suite.findings


def test_unknown_task_suite_blocks_shortcut_overlap() -> None:
    task = _task(
        "task-shortcut",
        TaskDifficultyBand.TRANSFER_NEAR,
        novelty=("memorized-start",),
    )
    suite = build_unknown_task_suite(
        suite_id="suite-shortcut",
        purpose="Exercise bounded transfer without overclaiming.",
        tasks=(task,),
        required_bands=(TaskDifficultyBand.TRANSFER_NEAR,),
        forbidden_shortcuts=("memorized-start",),
        evidence_ids=("suite-evidence",),
    )

    assert suite.decision is UnknownTaskDecision.BLOCKED_SHORTCUT
    assert "shortcut-overlap:task-shortcut:memorized-start" in suite.findings


def test_unknown_task_suite_rejects_duplicate_task_id() -> None:
    with pytest.raises(ValueError, match="Duplicate task_id"):
        build_unknown_task_suite(
            suite_id="suite-duplicate",
            purpose="Exercise bounded transfer without overclaiming.",
            tasks=(
                _task("task-same", TaskDifficultyBand.TRANSFER_NEAR),
                _task("task-same", TaskDifficultyBand.TRANSFER_FAR),
            ),
            required_bands=(TaskDifficultyBand.TRANSFER_NEAR,),
            evidence_ids=("suite-evidence",),
        )
