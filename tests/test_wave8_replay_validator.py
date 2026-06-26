import pytest

from ix_cognition_kernel.wave8_baseline_comparison import (
    BaselineSystemKind,
    build_baseline_outcome_record,
    compare_baseline_pair,
    evaluate_baseline_comparison,
)
from ix_cognition_kernel.wave8_environment_protocol import EnvironmentActionResult
from ix_cognition_kernel.wave8_episode_runner import run_single_step_episode
from ix_cognition_kernel.wave8_model_adapter import (
    DeterministicModelAdapter,
    DeterministicModelPolicy,
)
from ix_cognition_kernel.wave8_replay_validator import (
    ReplayValidationDecision,
    artifact_from_baseline_report,
    artifact_from_episode_run,
    artifact_from_skill_validation,
    artifact_from_transfer_report,
    artifact_from_world_snapshot,
    validate_replay_packet,
)
from ix_cognition_kernel.wave8_skill_synthesis import (
    create_skill_library_entry,
    synthesize_skill_candidate,
    validate_skill_candidate,
)
from ix_cognition_kernel.wave8_task_suite import (
    TaskDifficulty,
    TaskDisclosureLevel,
    TaskFamily,
    UnknownTaskSuite,
    build_grid_transition_task,
    build_grid_transition_template,
)
from ix_cognition_kernel.wave8_transfer_challenge import (
    build_transfer_trial_record,
    evaluate_transfer_challenge,
)
from ix_cognition_kernel.wave8_world_model import (
    build_world_model_snapshot,
    build_world_model_update,
    derive_world_rule_from_trials,
)


def _template():
    return build_grid_transition_template(template_id="grid-template-1")


def _task(task_id: str, difficulty: TaskDifficulty):
    disclosure = TaskDisclosureLevel.PARTIALLY_WITHHELD
    if difficulty is TaskDifficulty.HIDDEN_VALIDATION:
        disclosure = TaskDisclosureLevel.HIDDEN_GOAL
    return build_grid_transition_task(
        task_id=task_id,
        template=_template(),
        episode_id=f"{task_id}:episode",
        start_state_id=f"{task_id}:state-0",
        empty_direction="east",
        expected_operation_id="move-east",
        difficulty=difficulty,
        disclosure_level=disclosure,
    )


def _suite() -> UnknownTaskSuite:
    return UnknownTaskSuite(
        suite_id="suite-replay",
        purpose="Build a complete replay packet.",
        tasks=(
            _task("task-seed", TaskDifficulty.SEED),
            _task("task-near", TaskDifficulty.NEAR_TRANSFER),
            _task("task-far", TaskDifficulty.FAR_TRANSFER),
            _task("task-adversarial", TaskDifficulty.ADVERSARIAL),
            _task("task-hidden", TaskDifficulty.HIDDEN_VALIDATION),
        ),
        evidence_ids=("suite-evidence-1",),
    )


def _adapter(operation_id: str = "move-east") -> DeterministicModelAdapter:
    return DeterministicModelAdapter(
        adapter_id=f"adapter:{operation_id}",
        policy=DeterministicModelPolicy(
            policy_id=f"policy:{operation_id}",
            supported_environment_ids=("env-unused",),
            operation_preferences=(operation_id,),
            rationale_template="Use {operation_id} from {state_id}.",
            expected_effect_template="{operation_id} should change the bounded state.",
            evidence_ids=(f"policy-evidence:{operation_id}",),
            assumptions=("visible-state-is-current",),
            uncertainty_ids=("uncertainty-grid-transition",),
        ),
    )


def _result(task_id: str, action_id: str, *, measured: bool = True):
    return EnvironmentActionResult(
        result_id=f"{task_id}:result:{action_id}",
        action_id=action_id,
        environment_id=f"{task_id}:environment",
        episode_id=f"{task_id}:episode",
        prior_state_id=f"{task_id}:state-0",
        resulting_state_id=f"{task_id}:state-1",
        outcome_summary="The bounded task produced a transition.",
        score_delta=1.0,
        evidence_ids=(f"{task_id}:result-evidence:{action_id}",),
        measured=measured,
    )


def _run_for_task(task, *, operation_id: str = "move-east", measured: bool = True):
    action_id = f"{task.task_id}:action:{operation_id}:{measured}"
    return run_single_step_episode(
        run_id=f"{task.task_id}:run:{operation_id}:{measured}",
        step_id=f"{task.task_id}:step:{operation_id}:{measured}",
        output_id=f"{task.task_id}:output:{operation_id}:{measured}",
        draft_id=f"{task.task_id}:draft:{operation_id}:{measured}",
        action_id=action_id,
        frame_id=f"{task.task_id}:frame:{operation_id}:{measured}",
        environment=task.environment,
        observation=task.initial_observation,
        adapter=_adapter(operation_id),
        result=_result(task.task_id, action_id, measured=measured),
    )


def _passing_trial(task):
    return build_transfer_trial_record(
        trial_id=f"{task.task_id}:trial",
        task=task,
        run=_run_for_task(task),
        observed_feature_ids=task.expected_outcome_features,
        evidence_ids=(f"{task.task_id}:trial-evidence",),
    )


def _complete_artifacts():
    suite = _suite()
    trials = tuple(_passing_trial(task) for task in suite.tasks)
    transfer_report = evaluate_transfer_challenge(
        report_id="transfer-report-1",
        suite=suite,
        trials=trials,
    )
    candidate = synthesize_skill_candidate(
        skill_id="skill-grid-transition",
        name="Bounded grid transition skill",
        purpose="Reuse measured grid-transition evidence under bounded constraints.",
        trials=trials,
        evidence_ids=("skill-evidence-1",),
    )
    validation = validate_skill_candidate(
        validation_id="skill-validation-1",
        candidate=candidate,
        transfer_report=transfer_report,
    )
    create_skill_library_entry(
        entry_id="entry-1",
        validation=validation,
        evidence_ids=("entry-evidence-1",),
    )
    rule = derive_world_rule_from_trials(
        rule_id="rule-grid-transition",
        statement="Visible east-empty states support a bounded move-east transition.",
        family=TaskFamily.GRID_ABSTRACTION,
        trials=trials,
        evidence_ids=("world-rule-evidence-1",),
    )
    update = build_world_model_update(
        update_id="world-update-1",
        rule=rule,
        trials=trials,
    )
    snapshot = build_world_model_snapshot(
        snapshot_id="world-snapshot-1",
        purpose="Store bounded grid transition rules for replay review.",
        updates=(update,),
        evidence_ids=("snapshot-evidence-1",),
    )

    first_task = suite.tasks[1]
    second_task = suite.tasks[2]
    first_pair = compare_baseline_pair(
        pair_id="pair-1",
        baseline=build_baseline_outcome_record(
            outcome_id="baseline-outcome-1",
            system_kind=BaselineSystemKind.MODEL_ALONE,
            task=first_task,
            run=_run_for_task(first_task),
            observed_feature_ids=("wrong-feature",),
            evidence_ids=("baseline-evidence-1",),
        ),
        candidate=build_baseline_outcome_record(
            outcome_id="candidate-outcome-1",
            system_kind=BaselineSystemKind.COGNITION_KERNEL,
            task=first_task,
            run=_run_for_task(first_task),
            observed_feature_ids=first_task.expected_outcome_features,
            evidence_ids=("candidate-evidence-1",),
        ),
    )
    second_pair = compare_baseline_pair(
        pair_id="pair-2",
        baseline=build_baseline_outcome_record(
            outcome_id="baseline-outcome-2",
            system_kind=BaselineSystemKind.MODEL_ALONE,
            task=second_task,
            run=_run_for_task(second_task),
            observed_feature_ids=("wrong-feature",),
            evidence_ids=("baseline-evidence-2",),
        ),
        candidate=build_baseline_outcome_record(
            outcome_id="candidate-outcome-2",
            system_kind=BaselineSystemKind.COGNITION_KERNEL,
            task=second_task,
            run=_run_for_task(second_task),
            observed_feature_ids=second_task.expected_outcome_features,
            evidence_ids=("candidate-evidence-2",),
        ),
    )
    baseline_report = evaluate_baseline_comparison(
        report_id="baseline-report-1",
        purpose="Compare kernel-assisted outcomes against model-alone outcomes.",
        pairs=(first_pair, second_pair),
    )

    return (
        artifact_from_episode_run(
            artifact_id="artifact-episode",
            run=trials[0].run,
            evidence_ids=("artifact-evidence-episode",),
        ),
        artifact_from_transfer_report(
            artifact_id="artifact-transfer",
            report=transfer_report,
            evidence_ids=("artifact-evidence-transfer",),
        ),
        artifact_from_skill_validation(
            artifact_id="artifact-skill",
            validation=validation,
            evidence_ids=("artifact-evidence-skill",),
        ),
        artifact_from_world_snapshot(
            artifact_id="artifact-world",
            snapshot=snapshot,
            evidence_ids=("artifact-evidence-world",),
        ),
        artifact_from_baseline_report(
            artifact_id="artifact-baseline",
            report=baseline_report,
            evidence_ids=("artifact-evidence-baseline",),
        ),
    )


def test_replay_packet_is_ready_with_all_required_replayable_artifacts() -> None:
    report = validate_replay_packet(
        report_id="replay-report-1",
        purpose="Validate bounded Wave 8 replay packet for human review.",
        artifacts=_complete_artifacts(),
    )

    assert report.ready
    assert report.decision is ReplayValidationDecision.READY_FOR_REVIEW
    assert report.replayable_artifact_count == 5
    assert report.findings == ()
    assert report.fingerprint() == report.fingerprint()
    assert len(report.fingerprint()) == 64


def test_replay_packet_requires_all_required_artifacts() -> None:
    artifacts = _complete_artifacts()
    report = validate_replay_packet(
        report_id="replay-report-missing",
        purpose="Validate incomplete replay packet.",
        artifacts=artifacts[:2],
    )

    assert not report.ready
    assert report.decision is ReplayValidationDecision.NEEDS_REQUIRED_ARTIFACTS
    assert any(
        finding.startswith("missing-required-artifacts")
        for finding in report.findings
    )


def test_replay_packet_blocks_unmeasured_episode_artifact() -> None:
    task = _task("task-unmeasured", TaskDifficulty.NEAR_TRANSFER)
    run = _run_for_task(task, measured=False)
    artifact = artifact_from_episode_run(
        artifact_id="artifact-unmeasured",
        run=run,
        evidence_ids=("artifact-evidence-unmeasured",),
    )
    artifacts = (artifact, *_complete_artifacts()[1:])

    report = validate_replay_packet(
        report_id="replay-report-unmeasured",
        purpose="Validate unmeasured replay packet.",
        artifacts=artifacts,
    )

    assert not report.ready
    assert report.decision is ReplayValidationDecision.NEEDS_MEASURED_RESULT
    assert "unmeasured-artifact-present" in report.findings


def test_replay_packet_blocks_bad_transfer_artifact() -> None:
    suite = UnknownTaskSuite(
        suite_id="suite-bad-transfer",
        purpose="Seed-only suite cannot prove transfer.",
        tasks=(_task("task-seed-only", TaskDifficulty.SEED),),
        evidence_ids=("suite-evidence-bad",),
    )
    seed_trial = _passing_trial(suite.tasks[0])
    bad_transfer_report = evaluate_transfer_challenge(
        report_id="transfer-report-bad",
        suite=suite,
        trials=(seed_trial,),
    )
    bad_artifact = artifact_from_transfer_report(
        artifact_id="artifact-bad-transfer",
        report=bad_transfer_report,
        evidence_ids=("artifact-evidence-bad-transfer",),
    )
    artifacts = (
        _complete_artifacts()[0],
        bad_artifact,
        *_complete_artifacts()[2:],
    )

    report = validate_replay_packet(
        report_id="replay-report-blocked",
        purpose="Validate blocked replay packet.",
        artifacts=artifacts,
    )

    assert not report.ready
    assert report.decision is ReplayValidationDecision.BLOCKED
    assert "blocked-artifact-present" in report.findings


def test_replay_report_rejects_overclaiming_purpose() -> None:
    with pytest.raises(ValueError, match="blocked overclaiming"):
        validate_replay_packet(
            report_id="replay-report-overclaim",
            purpose="This certifies AGI.",
            artifacts=_complete_artifacts(),
        )
