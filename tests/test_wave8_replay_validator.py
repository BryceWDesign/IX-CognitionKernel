"""Tests for Wave 8 replay validator."""

from __future__ import annotations

import pytest

from ix_cognition_kernel.wave8_baseline_comparison import (
    BaselineSystemRecord,
    build_baseline_report,
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
)
from ix_cognition_kernel.wave8_episode_runner import BoundedEpisodeRun
from ix_cognition_kernel.wave8_episode_runner import run_single_step_episode
from ix_cognition_kernel.wave8_replay_validator import (
    ReplayArtifactKind,
    ReplayArtifactRecord,
    ReplayArtifactStatus,
    ReplayValidationDecision,
    artifact_from_baseline_report,
    artifact_from_episode_run,
    artifact_from_transfer_report,
    validate_replay_packet,
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
        environment_id="env-replay",
        name="Replay Grid",
        version="1.0",
        supported_action_kinds=("move",),
        observable_feature_ids=("agent:0,0", "goal:1,0", "agent:1,0", "goal-reached"),
        terminal_feature_ids=("goal-reached",),
        forbidden_action_patterns=("network",),
    )


def _observation(
    *,
    observation_id: str = "obs-replay",
    episode_id: str = "episode-replay",
) -> EnvironmentObservation:
    return EnvironmentObservation(
        observation_id=observation_id,
        environment_id="env-replay",
        episode_id=episode_id,
        visible_features=("agent:0,0", "goal:1,0"),
        hidden_feature_count=1,
    )


def _adapter() -> object:
    from ix_cognition_kernel.wave8_model_adapter import (
        DeterministicModelAdapter,
        ModelAdapterMode,
    )

    return DeterministicModelAdapter(
        adapter_id="adapter-replay",
        mode=ModelAdapterMode.REPLAY_SCRIPT,
        supported_action_kinds=("move",),
        policy={
            "agent:0,0|goal:1,0": {
                "kind": "move",
                "parameters": {"direction": "east"},
                "confidence": 0.9,
                "rationale": "Move to goal.",
            }
        },
    )


def _result(
    *,
    result_id: str = "result-replay",
    action_id: str = "action-replay",
    episode_id: str = "episode-replay",
) -> EnvironmentActionResult:
    return EnvironmentActionResult(
        result_id=result_id,
        action_id=action_id,
        environment_id="env-replay",
        episode_id=episode_id,
        next_features=("agent:1,0", "goal-reached"),
        measured_reward=1.0,
        terminal=True,
    )


def _run(*, run_id: str = "run-replay") -> BoundedEpisodeRun:
    return run_single_step_episode(
        run_id=run_id,
        step_id=f"step-{run_id}",
        output_id=f"output-{run_id}",
        draft_id=f"draft-{run_id}",
        action_id="action-replay",
        frame_id=f"frame-{run_id}",
        environment=_environment(),
        observation=_observation(),
        adapter=_adapter(),
        result=_result(),
    )


def _task(*, task_id: str, band: TaskDifficultyBand) -> UnknownTaskInstance:
    return UnknownTaskInstance(
        task_id=task_id,
        environment_id="env-replay",
        difficulty_band=band,
        initial_observation=_observation(
            observation_id=f"obs-{task_id}",
            episode_id=f"episode-{task_id}",
        ),
        allowed_action_kinds=("move",),
        expected_outcome_features=("goal-reached", "operation:move-east"),
        novelty_factors=("novel-start",),
        transfer_tags=("grid", "move-east"),
        evidence_ids=(f"evidence-{task_id}",),
    )


def _transfer_report() -> object:
    tasks = (
        _task(task_id="task-near", band=TaskDifficultyBand.TRANSFER_NEAR),
        _task(task_id="task-far", band=TaskDifficultyBand.TRANSFER_FAR),
        _task(task_id="task-hidden", band=TaskDifficultyBand.HIDDEN),
    )
    frontier = CurriculumFrontier(
        frontier_id="frontier-replay",
        purpose="Replay validator transfer pressure.",
        pressures=(
            FrontierPressure(
                pressure_id="pressure-replay",
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
    trials = tuple(
        build_transfer_trial(
            trial_id=f"trial-{task.task_id}",
            task=task,
            band=(
                TransferBand.HIDDEN
                if task.difficulty_band is TaskDifficultyBand.HIDDEN
                else TransferBand.FAR
                if task.difficulty_band is TaskDifficultyBand.TRANSFER_FAR
                else TransferBand.NEAR
            ),
            episode_run=run_single_step_episode(
                run_id=f"run-{task.task_id}",
                step_id=f"step-{task.task_id}",
                output_id=f"output-{task.task_id}",
                draft_id=f"draft-{task.task_id}",
                action_id="action-replay",
                frame_id=f"frame-{task.task_id}",
                environment=_environment(),
                observation=task.initial_observation,
                adapter=_adapter(),
                result=_result(
                    result_id=f"result-{task.task_id}",
                    episode_id=f"episode-{task.task_id}",
                ),
            ),
        )
        for task in tasks
    )
    return evaluate_transfer_challenge(
        report_id="transfer-report-replay",
        suite=frontier,
        trials=trials,
    )


def _baseline_report() -> object:
    report = _transfer_report()
    baseline = BaselineSystemRecord(
        baseline_id="baseline-replay",
        name="Static baseline",
        version="0.1",
        replayable_episode_count=1,
        transfer_success_rate=0.2,
        hidden_success_rate=0.1,
        failure_rate=0.8,
        evidence_ids=("baseline-evidence-1",),
    )
    candidate = BaselineSystemRecord(
        baseline_id="candidate-replay",
        name="Wave 8 candidate",
        version="0.1",
        replayable_episode_count=3,
        transfer_success_rate=1.0,
        hidden_success_rate=1.0,
        failure_rate=0.0,
        evidence_ids=("candidate-evidence-1",),
    )
    return build_baseline_report(
        report_id="baseline-report-replay",
        transfer_report=report,
        candidate=candidate,
        baseline=baseline,
        evidence_ids=("baseline-report-evidence-1",),
    )


def test_artifact_from_episode_run_is_replayable() -> None:
    artifact = artifact_from_episode_run(
        artifact_id="artifact-episode",
        run=_run(),
        evidence_ids=("artifact-evidence-1",),
    )

    assert artifact.kind is ReplayArtifactKind.EPISODE_RUN
    assert artifact.status is ReplayArtifactStatus.REPLAYABLE
    assert artifact.replayable


def test_artifact_from_unmeasured_episode_needs_result() -> None:
    run = run_single_step_episode(
        run_id="run-unmeasured",
        step_id="step-unmeasured",
        output_id="output-unmeasured",
        draft_id="draft-unmeasured",
        action_id="action-replay",
        frame_id="frame-unmeasured",
        environment=_environment(),
        observation=_observation(),
        adapter=_adapter(),
        result=None,
    )
    artifact = artifact_from_episode_run(
        artifact_id="artifact-unmeasured",
        run=run,
        evidence_ids=("artifact-evidence-1",),
    )

    assert artifact.status is ReplayArtifactStatus.NEEDS_MEASURED_RESULT


def test_validate_replay_packet_ready_with_required_artifacts() -> None:
    transfer_report = _transfer_report()
    baseline_report = _baseline_report()
    artifacts = (
        artifact_from_episode_run(
            artifact_id="artifact-episode",
            run=_run(),
            evidence_ids=("episode-evidence-1",),
        ),
        artifact_from_transfer_report(
            artifact_id="artifact-transfer",
            report=transfer_report,
            evidence_ids=("transfer-evidence-1",),
        ),
        ReplayArtifactRecord(
            artifact_id="artifact-skill",
            kind=ReplayArtifactKind.SKILL_VALIDATION,
            source_fingerprint="a" * 64,
            status=ReplayArtifactStatus.REPLAYABLE,
            evidence_ids=("skill-evidence-1",),
            summary="Skill validation is bounded replay evidence.",
        ),
        ReplayArtifactRecord(
            artifact_id="artifact-world",
            kind=ReplayArtifactKind.WORLD_MODEL_SNAPSHOT,
            source_fingerprint="b" * 64,
            status=ReplayArtifactStatus.REPLAYABLE,
            evidence_ids=("world-evidence-1",),
            summary="World model snapshot is bounded replay evidence.",
        ),
        artifact_from_baseline_report(
            artifact_id="artifact-baseline",
            report=baseline_report,
            evidence_ids=("baseline-evidence-1",),
        ),
    )

    replay_report = validate_replay_packet(
        report_id="replay-report-ready",
        purpose="Validate bounded replay evidence for review.",
        artifacts=artifacts,
    )

    assert replay_report.decision is ReplayValidationDecision.READY_FOR_REVIEW
    assert replay_report.ready
    assert replay_report.replayable_artifact_count == 5


def test_validate_replay_packet_needs_required_artifacts() -> None:
    replay_report = validate_replay_packet(
        report_id="replay-report-missing",
        purpose="Validate bounded replay evidence for review.",
        artifacts=(
            artifact_from_episode_run(
                artifact_id="artifact-episode",
                run=_run(),
                evidence_ids=("episode-evidence-1",),
            ),
        ),
    )

    assert replay_report.decision is ReplayValidationDecision.NEEDS_REQUIRED_ARTIFACTS
    assert any(
        finding.startswith("missing-required-artifacts")
        for finding in replay_report.findings
    )


def test_validate_replay_packet_blocks_unmeasured_artifacts() -> None:
    run = run_single_step_episode(
        run_id="run-unmeasured",
        step_id="step-unmeasured",
        output_id="output-unmeasured",
        draft_id="draft-unmeasured",
        action_id="action-replay",
        frame_id="frame-unmeasured",
        environment=_environment(),
        observation=_observation(),
        adapter=_adapter(),
        result=None,
    )
    replay_report = validate_replay_packet(
        report_id="replay-report-unmeasured",
        purpose="Validate bounded replay evidence for review.",
        artifacts=(
            artifact_from_episode_run(
                artifact_id="artifact-unmeasured",
                run=run,
                evidence_ids=("episode-evidence-1",),
            ),
        ),
    )

    assert replay_report.decision is ReplayValidationDecision.NEEDS_MEASURED_RESULT
    assert "unmeasured-artifact-present" in replay_report.findings


def test_replay_artifact_rejects_overclaiming_summary() -> None:
    with pytest.raises(ValueError, match="blocked overclaiming"):
        ReplayArtifactRecord(
            artifact_id="artifact-overclaim",
            kind=ReplayArtifactKind.EPISODE_RUN,
            source_fingerprint="a" * 64,
            status=ReplayArtifactStatus.REPLAYABLE,
            evidence_ids=("artifact-evidence-1",),
            summary="This proves AGI.",
        )


def test_replay_artifact_requires_valid_fingerprint() -> None:
    with pytest.raises(ValueError, match="SHA-256"):
        ReplayArtifactRecord(
            artifact_id="artifact-bad-fingerprint",
            kind=ReplayArtifactKind.EPISODE_RUN,
            source_fingerprint="bad",
            status=ReplayArtifactStatus.REPLAYABLE,
            evidence_ids=("artifact-evidence-1",),
            summary="Bounded replay evidence.",
        )
