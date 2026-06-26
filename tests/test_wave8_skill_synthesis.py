import pytest

from ix_cognition_kernel.wave8_environment_protocol import EnvironmentActionResult
from ix_cognition_kernel.wave8_episode_runner import run_single_step_episode
from ix_cognition_kernel.wave8_model_adapter import (
    DeterministicModelAdapter,
    DeterministicModelPolicy,
)
from ix_cognition_kernel.wave8_skill_synthesis import (
    SkillCandidate,
    SkillPromotionDecision,
    SkillReuseDecision,
    create_skill_library_entry,
    plan_skill_reuse,
    synthesize_skill_candidate,
    validate_skill_candidate,
)
from ix_cognition_kernel.wave8_task_suite import (
    TaskDifficulty,
    TaskDisclosureLevel,
    UnknownTaskSuite,
    build_grid_transition_task,
    build_grid_transition_template,
)
from ix_cognition_kernel.wave8_transfer_challenge import (
    build_transfer_trial_record,
    evaluate_transfer_challenge,
)


def _template():
    return build_grid_transition_template(template_id="grid-template-1")


def _task(task_id: str, difficulty: TaskDifficulty, operation_id: str = "move-east"):
    disclosure = TaskDisclosureLevel.PARTIALLY_WITHHELD
    if difficulty is TaskDifficulty.HIDDEN_VALIDATION:
        disclosure = TaskDisclosureLevel.HIDDEN_GOAL
    return build_grid_transition_task(
        task_id=task_id,
        template=_template(),
        episode_id=f"{task_id}:episode",
        start_state_id=f"{task_id}:state-0",
        empty_direction="east",
        expected_operation_id=operation_id,
        difficulty=difficulty,
        disclosure_level=disclosure,
    )


def _suite() -> UnknownTaskSuite:
    return UnknownTaskSuite(
        suite_id="suite-skill",
        purpose="Exercise skill synthesis from replayable transfer evidence.",
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
        adapter_id="deterministic-adapter-1",
        policy=DeterministicModelPolicy(
            policy_id="policy-1",
            supported_environment_ids=("env-unused",),
            operation_preferences=(operation_id,),
            rationale_template="Use {operation_id} from {state_id}.",
            expected_effect_template="{operation_id} should change the bounded state.",
            evidence_ids=("policy-evidence-1",),
            assumptions=("visible-state-is-current",),
            uncertainty_ids=("uncertainty-grid-transition",),
        ),
    )


def _result(task_id: str, *, measured: bool = True) -> EnvironmentActionResult:
    return EnvironmentActionResult(
        result_id=f"{task_id}:result",
        action_id=f"{task_id}:action",
        environment_id=f"{task_id}:environment",
        episode_id=f"{task_id}:episode",
        prior_state_id=f"{task_id}:state-0",
        resulting_state_id=f"{task_id}:state-1",
        outcome_summary="The bounded task produced a transition.",
        score_delta=1.0,
        evidence_ids=(f"{task_id}:result-evidence",),
        measured=measured,
    )


def _run_for_task(task, *, operation_id: str = "move-east"):
    return run_single_step_episode(
        run_id=f"{task.task_id}:run",
        step_id=f"{task.task_id}:step",
        output_id=f"{task.task_id}:output",
        draft_id=f"{task.task_id}:draft",
        action_id=f"{task.task_id}:action",
        frame_id=f"{task.task_id}:frame",
        environment=task.environment,
        observation=task.initial_observation,
        adapter=_adapter(operation_id),
        result=_result(task.task_id),
    )


def _passing_trial(task):
    return build_transfer_trial_record(
        trial_id=f"{task.task_id}:trial",
        task=task,
        run=_run_for_task(task),
        observed_feature_ids=task.expected_outcome_features,
        evidence_ids=(f"{task.task_id}:trial-evidence",),
    )


def _ready_report():
    suite = _suite()
    trials = tuple(_passing_trial(task) for task in suite.tasks)
    return evaluate_transfer_challenge(
        report_id="report-ready",
        suite=suite,
        trials=trials,
    )


def _candidate():
    report = _ready_report()
    return synthesize_skill_candidate(
        skill_id="skill-grid-east-transition",
        name="Bounded grid transition skill",
        purpose="Reuse measured grid-transition evidence under bounded constraints.",
        trials=report.trials,
        evidence_ids=("skill-synthesis-evidence-1",),
    )


def test_synthesize_skill_candidate_from_replayable_transfer_trials() -> None:
    candidate = _candidate()

    assert candidate.skill_id == "skill-grid-east-transition"
    assert "move-east" in candidate.operation_ids
    assert "family:grid-abstraction" in candidate.transfer_tags
    assert not candidate.failure_modes
    assert candidate.fingerprint() == candidate.fingerprint()
    assert len(candidate.fingerprint()) == 64


def test_skill_candidate_rejects_agi_overclaim_language() -> None:
    with pytest.raises(ValueError, match="blocked overclaiming"):
        SkillCandidate(
            skill_id="skill-overclaim",
            name="AGI achieved skill",
            purpose="This claims too much.",
            source_task_ids=("task-1",),
            operation_ids=("move-east",),
            preconditions=("state-visible",),
            expected_effects=("operation:move-east",),
            transfer_tags=("family:grid-abstraction",),
            failure_modes=(),
            evidence_ids=("evidence-1",),
        )


def test_validate_skill_candidate_promotes_only_after_transfer_demonstration() -> None:
    report = _ready_report()
    candidate = synthesize_skill_candidate(
        skill_id="skill-grid-east-transition",
        name="Bounded grid transition skill",
        purpose="Reuse measured grid-transition evidence under bounded constraints.",
        trials=report.trials,
        evidence_ids=("skill-synthesis-evidence-1",),
    )
    validation = validate_skill_candidate(
        validation_id="validation-ready",
        candidate=candidate,
        transfer_report=report,
    )

    assert validation.ready
    assert validation.decision is SkillPromotionDecision.READY_FOR_REUSE
    assert validation.findings == ()
    assert validation.fingerprint() == validation.fingerprint()


def test_validate_skill_candidate_blocks_when_transfer_report_is_not_ready() -> None:
    suite = _suite()
    seed_trial = _passing_trial(suite.tasks[0])
    report = evaluate_transfer_challenge(
        report_id="report-not-ready",
        suite=suite,
        trials=(seed_trial,),
    )
    candidate = synthesize_skill_candidate(
        skill_id="skill-seed-only",
        name="Seed-only bounded grid transition skill",
        purpose="Insufficient source evidence should not be promoted.",
        trials=(seed_trial,),
        evidence_ids=("skill-synthesis-evidence-1",),
    )
    validation = validate_skill_candidate(
        validation_id="validation-not-ready",
        candidate=candidate,
        transfer_report=report,
    )

    assert not validation.ready
    assert validation.decision is SkillPromotionDecision.BLOCKED_BY_FAILURE
    assert "blocked-transfer-trials-present" not in validation.findings
    assert any(
        finding.startswith("transfer-report-not-ready")
        for finding in validation.findings
    )


def test_skill_library_entry_and_reuse_plan_allow_aligned_valid_skill() -> None:
    report = _ready_report()
    candidate = _candidate()
    validation = validate_skill_candidate(
        validation_id="validation-ready",
        candidate=candidate,
        transfer_report=report,
    )
    entry = create_skill_library_entry(
        entry_id="entry-1",
        validation=validation,
        evidence_ids=("entry-evidence-1",),
    )
    new_task = _task("task-new-near", TaskDifficulty.NEAR_TRANSFER)

    plan = plan_skill_reuse(
        plan_id="reuse-plan-1",
        entry=entry,
        task=new_task,
    )

    assert entry.reusable
    assert plan.ready
    assert plan.decision is SkillReuseDecision.REUSE_READY
    assert "move-east" in plan.matched_expected_operations
    assert "family:grid-abstraction" in plan.matched_transfer_tags
    assert plan.fingerprint() == plan.fingerprint()


def test_skill_reuse_plan_blocks_stale_revoked_and_unvalidated_entries() -> None:
    report = _ready_report()
    candidate = _candidate()
    validation = validate_skill_candidate(
        validation_id="validation-ready",
        candidate=candidate,
        transfer_report=report,
    )
    stale_entry = create_skill_library_entry(
        entry_id="entry-stale",
        validation=validation,
        evidence_ids=("entry-evidence-stale",),
        stale=True,
    )
    revoked_entry = create_skill_library_entry(
        entry_id="entry-revoked",
        validation=validation,
        evidence_ids=("entry-evidence-revoked",),
        revoked=True,
    )
    task = _task("task-new-near", TaskDifficulty.NEAR_TRANSFER)

    stale_plan = plan_skill_reuse(
        plan_id="reuse-plan-stale",
        entry=stale_entry,
        task=task,
    )
    revoked_plan = plan_skill_reuse(
        plan_id="reuse-plan-revoked",
        entry=revoked_entry,
        task=task,
    )

    assert stale_plan.decision is SkillReuseDecision.BLOCKED_STALE
    assert revoked_plan.decision is SkillReuseDecision.BLOCKED_REVOKED


def test_skill_reuse_plan_requires_operation_and_transfer_alignment() -> None:
    report = _ready_report()
    candidate = _candidate()
    validation = validate_skill_candidate(
        validation_id="validation-ready",
        candidate=candidate,
        transfer_report=report,
    )
    entry = create_skill_library_entry(
        entry_id="entry-1",
        validation=validation,
        evidence_ids=("entry-evidence-1",),
    )
    mismatched_task = _task(
        "task-mismatched",
        TaskDifficulty.NEAR_TRANSFER,
        operation_id="move-west",
    )

    plan = plan_skill_reuse(
        plan_id="reuse-plan-mismatch",
        entry=entry,
        task=mismatched_task,
    )

    assert not plan.ready
    assert plan.decision is SkillReuseDecision.NEEDS_TRANSFER_ALIGNMENT
    assert "missing-operation-alignment" in plan.findings
