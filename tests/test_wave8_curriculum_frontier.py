"""Tests for Wave 8 curriculum frontier."""

from __future__ import annotations

import pytest

from ix_cognition_kernel.wave8_curriculum_frontier import (
    CurriculumDecision,
    CurriculumFrontier,
    FrontierPressure,
    FrontierPressureDecision,
    generate_frontier_tasks,
    review_curriculum_frontier,
)
from ix_cognition_kernel.wave8_task_suite import (
    TaskDifficultyBand,
    UnknownTaskDecision,
    UnknownTaskInstance,
    UnknownTaskSuite,
)


def _pressure(
    *,
    pressure_id: str = "pressure-grid-transfer",
    difficulty_band: TaskDifficultyBand = TaskDifficultyBand.TRANSFER_NEAR,
    forbidden_shortcuts: tuple[str, ...] = ("memorize-start-cell",),
) -> FrontierPressure:
    return FrontierPressure(
        pressure_id=pressure_id,
        target_skill="grid navigation",
        difficulty_band=difficulty_band,
        transfer_tags=("grid-world", "pathfinding"),
        required_feature_ids=("goal-visible", "agent-visible"),
        forbidden_shortcuts=forbidden_shortcuts,
        evidence_ids=("pressure-evidence-1",),
    )


def _task(
    *,
    task_id: str,
    difficulty_band: TaskDifficultyBand,
    transfer_tags: tuple[str, ...] = ("grid-world", "pathfinding"),
    expected_outcome_features: tuple[str, ...] = ("goal-reached",),
    novelty_factors: tuple[str, ...] = ("new-map",),
) -> UnknownTaskInstance:
    from ix_cognition_kernel.wave8_environment_protocol import EnvironmentObservation

    return UnknownTaskInstance(
        task_id=task_id,
        environment_id="env-grid",
        difficulty_band=difficulty_band,
        initial_observation=EnvironmentObservation(
            observation_id=f"obs-{task_id}",
            environment_id="env-grid",
            episode_id=f"episode-{task_id}",
            visible_features=("agent-visible", "goal-visible"),
            hidden_feature_count=1,
        ),
        allowed_action_kinds=("move", "inspect"),
        expected_outcome_features=expected_outcome_features,
        novelty_factors=novelty_factors,
        transfer_tags=transfer_tags,
        evidence_ids=(f"evidence-{task_id}",),
    )


def test_frontier_pressure_is_ready_when_fields_are_complete() -> None:
    pressure = _pressure()

    assert pressure.decision is FrontierPressureDecision.READY
    assert len(pressure.fingerprint()) == 64


def test_frontier_pressure_rejects_forbidden_shortcut_overlap() -> None:
    pressure = FrontierPressure(
        pressure_id="pressure-overlap",
        target_skill="grid navigation",
        difficulty_band=TaskDifficultyBand.TRANSFER_NEAR,
        transfer_tags=("grid-world",),
        required_feature_ids=("shortcut-token",),
        forbidden_shortcuts=("shortcut-token",),
        evidence_ids=("pressure-evidence-1",),
    )

    assert pressure.decision is FrontierPressureDecision.REJECTED_SHORTCUT


def test_frontier_pressure_requires_transfer_tags() -> None:
    pressure = FrontierPressure(
        pressure_id="pressure-missing-tags",
        target_skill="grid navigation",
        difficulty_band=TaskDifficultyBand.TRANSFER_NEAR,
        transfer_tags=(),
        required_feature_ids=("goal-visible",),
        forbidden_shortcuts=("memorize-start",),
        evidence_ids=("pressure-evidence-1",),
    )

    assert pressure.decision is FrontierPressureDecision.NEEDS_TRANSFER_TAGS


def test_curriculum_frontier_ready_when_pressure_and_tasks_align() -> None:
    pressure = _pressure()
    task = _task(task_id="task-near-1", difficulty_band=TaskDifficultyBand.TRANSFER_NEAR)
    frontier = CurriculumFrontier(
        frontier_id="frontier-ready",
        purpose="Exercise bounded transfer.",
        pressures=(pressure,),
        tasks=(task,),
        evidence_ids=("frontier-evidence-1",),
    )

    assert frontier.decision is CurriculumDecision.READY
    assert frontier.task_count == 1


def test_curriculum_frontier_detects_pressure_without_task() -> None:
    pressure = _pressure(difficulty_band=TaskDifficultyBand.TRANSFER_FAR)
    task = _task(task_id="task-near-1", difficulty_band=TaskDifficultyBand.TRANSFER_NEAR)
    frontier = CurriculumFrontier(
        frontier_id="frontier-gap",
        purpose="Exercise bounded transfer.",
        pressures=(pressure,),
        tasks=(task,),
        evidence_ids=("frontier-evidence-1",),
    )

    assert frontier.decision is CurriculumDecision.NEEDS_TASK_COVERAGE
    assert "pressure-without-task:pressure-grid-transfer" in frontier.findings


def test_curriculum_frontier_blocks_shortcut_task() -> None:
    pressure = _pressure()
    task = _task(
        task_id="task-shortcut",
        difficulty_band=TaskDifficultyBand.TRANSFER_NEAR,
        novelty_factors=("memorize-start-cell",),
    )
    frontier = CurriculumFrontier(
        frontier_id="frontier-shortcut",
        purpose="Exercise bounded transfer.",
        pressures=(pressure,),
        tasks=(task,),
        evidence_ids=("frontier-evidence-1",),
    )

    assert frontier.decision is CurriculumDecision.BLOCKED_SHORTCUT
    assert "shortcut-leakage:task-shortcut:memorize-start-cell" in frontier.findings


def test_curriculum_frontier_rejects_overclaiming_purpose() -> None:
    with pytest.raises(ValueError, match="blocked overclaiming"):
        CurriculumFrontier(
            frontier_id="frontier-overclaim",
            purpose="Prove AGI transfer.",
            pressures=(_pressure(),),
            tasks=(
                _task(
                    task_id="task-near-1",
                    difficulty_band=TaskDifficultyBand.TRANSFER_NEAR,
                ),
            ),
            evidence_ids=("frontier-evidence-1",),
        )


def test_generate_frontier_tasks_from_pressure() -> None:
    pressure = _pressure()
    tasks = generate_frontier_tasks(
        environment_id="env-grid",
        suite_id="suite-generated",
        pressures=(pressure,),
        seed_visible_features=("agent-visible", "goal-visible"),
        allowed_action_kinds=("move", "inspect"),
        evidence_prefix="generated-evidence",
    )

    assert len(tasks) == 1
    assert tasks[0].difficulty_band is TaskDifficultyBand.TRANSFER_NEAR
    assert tasks[0].expected_outcome_features == (
        "goal-visible",
        "agent-visible",
    )
    assert tasks[0].transfer_tags == ("grid-world", "pathfinding")


def test_review_curriculum_frontier_builds_suite() -> None:
    pressure = _pressure()
    task = _task(task_id="task-near-1", difficulty_band=TaskDifficultyBand.TRANSFER_NEAR)
    frontier = CurriculumFrontier(
        frontier_id="frontier-review",
        purpose="Exercise bounded transfer.",
        pressures=(pressure,),
        tasks=(task,),
        evidence_ids=("frontier-evidence-1",),
    )
    suite = review_curriculum_frontier(
        suite_id="suite-frontier",
        frontier=frontier,
        evidence_ids=("suite-evidence-1",),
    )

    assert isinstance(suite, UnknownTaskSuite)
    assert suite.decision is UnknownTaskDecision.READY_FOR_TRIAL
    assert suite.tasks == (task,)


def test_frontier_rejects_empty_pressure_and_tasks() -> None:
    with pytest.raises(ValueError, match="Curriculum frontiers require pressures"):
        CurriculumFrontier(
            frontier_id="frontier-empty",
            purpose="Exercise bounded transfer.",
            pressures=(),
            tasks=(),
            evidence_ids=("frontier-evidence-1",),
        )
