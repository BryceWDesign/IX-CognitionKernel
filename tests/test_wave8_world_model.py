import pytest

from ix_cognition_kernel.wave8_environment_protocol import EnvironmentActionResult
from ix_cognition_kernel.wave8_episode_runner import run_single_step_episode
from ix_cognition_kernel.wave8_model_adapter import (
    DeterministicModelAdapter,
    DeterministicModelPolicy,
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
)
from ix_cognition_kernel.wave8_world_model import (
    WorldModelRule,
    WorldModelUpdateDecision,
    WorldRuleApplicationDecision,
    WorldRuleConfidence,
    WorldRuleKind,
    build_world_model_snapshot,
    build_world_model_update,
    derive_world_rule_from_trials,
    plan_world_rule_application,
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


def _failing_trial(task):
    return build_transfer_trial_record(
        trial_id=f"{task.task_id}:trial",
        task=task,
        run=_run_for_task(task),
        observed_feature_ids=("wrong-feature",),
        evidence_ids=(f"{task.task_id}:trial-evidence",),
    )


def test_derive_world_rule_promotes_transfer_supported_confidence() -> None:
    seed = _task("task-seed", TaskDifficulty.SEED)
    far = _task("task-far", TaskDifficulty.FAR_TRANSFER)
    hidden = _task("task-hidden", TaskDifficulty.HIDDEN_VALIDATION)
    rule = derive_world_rule_from_trials(
        rule_id="rule-grid-east-transition",
        statement="Visible east-empty grid states support a bounded move-east transition.",
        family=TaskFamily.GRID_ABSTRACTION,
        trials=(_passing_trial(seed), _passing_trial(far), _passing_trial(hidden)),
        evidence_ids=("world-rule-evidence-1",),
    )

    assert rule.confidence is WorldRuleConfidence.TRANSFER_SUPPORTED
    assert rule.transfer_supported
    assert "move-east" in rule.action_ids
    assert rule.fingerprint() == rule.fingerprint()
    assert len(rule.fingerprint()) == 64


def test_world_rule_rejects_overclaiming_statement() -> None:
    with pytest.raises(ValueError, match="blocked overclaiming"):
        WorldModelRule(
            rule_id="rule-overclaim",
            family=TaskFamily.GRID_ABSTRACTION,
            kind=WorldRuleKind.TRANSITION,
            statement="This proves AGI.",
            antecedent_features=("east-cell-empty",),
            action_ids=("move-east",),
            expected_consequences=("operation:move-east",),
            exception_features=(),
            source_trial_ids=("trial-1",),
            evidence_ids=("evidence-1",),
        )


def test_world_model_update_quarantines_contradicting_trials() -> None:
    seed = _task("task-seed", TaskDifficulty.SEED)
    far = _task("task-far", TaskDifficulty.FAR_TRANSFER)
    rule = derive_world_rule_from_trials(
        rule_id="rule-grid-east-transition",
        statement="Visible east-empty grid states may support a bounded move-east transition.",
        family=TaskFamily.GRID_ABSTRACTION,
        trials=(_passing_trial(seed), _failing_trial(far)),
        evidence_ids=("world-rule-evidence-1",),
    )
    update = build_world_model_update(
        update_id="update-contradiction",
        rule=rule,
        trials=(_passing_trial(seed), _failing_trial(far)),
    )

    assert rule.confidence is WorldRuleConfidence.CONTRADICTED
    assert update.decision is WorldModelUpdateDecision.QUARANTINE_CONTRADICTION
    assert "contradicting-trial-present" in update.findings
    assert update.contradicting_trial_ids == ("task-far:trial",)


def test_world_model_update_promotes_transfer_supported_rule() -> None:
    seed = _task("task-seed", TaskDifficulty.SEED)
    far = _task("task-far", TaskDifficulty.FAR_TRANSFER)
    rule = derive_world_rule_from_trials(
        rule_id="rule-grid-east-transition",
        statement="Visible east-empty grid states support a bounded move-east transition.",
        family=TaskFamily.GRID_ABSTRACTION,
        trials=(_passing_trial(seed), _passing_trial(far)),
        evidence_ids=("world-rule-evidence-1",),
    )
    update = build_world_model_update(
        update_id="update-promote",
        rule=rule,
        trials=(_passing_trial(seed), _passing_trial(far)),
    )

    assert update.promoted
    assert update.decision is WorldModelUpdateDecision.PROMOTE_TRANSFER_SUPPORTED_RULE
    assert update.findings == ()


def test_world_model_snapshot_tracks_active_and_transfer_supported_rules() -> None:
    seed = _task("task-seed", TaskDifficulty.SEED)
    far = _task("task-far", TaskDifficulty.FAR_TRANSFER)
    rule = derive_world_rule_from_trials(
        rule_id="rule-grid-east-transition",
        statement="Visible east-empty grid states support a bounded move-east transition.",
        family=TaskFamily.GRID_ABSTRACTION,
        trials=(_passing_trial(seed), _passing_trial(far)),
        evidence_ids=("world-rule-evidence-1",),
    )
    update = build_world_model_update(
        update_id="update-promote",
        rule=rule,
        trials=(_passing_trial(seed), _passing_trial(far)),
    )
    snapshot = build_world_model_snapshot(
        snapshot_id="snapshot-1",
        purpose="Store bounded grid transition rules for future replay.",
        updates=(update,),
        evidence_ids=("snapshot-evidence-1",),
    )

    assert snapshot.active_rules == (rule,)
    assert snapshot.transfer_supported_rule_count == 1
    assert snapshot.fingerprint() == snapshot.fingerprint()


def test_world_rule_application_requires_action_and_feature_alignment() -> None:
    seed = _task("task-seed", TaskDifficulty.SEED)
    far = _task("task-far", TaskDifficulty.FAR_TRANSFER)
    rule = derive_world_rule_from_trials(
        rule_id="rule-grid-east-transition",
        statement="Visible east-empty grid states support a bounded move-east transition.",
        family=TaskFamily.GRID_ABSTRACTION,
        trials=(_passing_trial(seed), _passing_trial(far)),
        evidence_ids=("world-rule-evidence-1",),
    )
    aligned_plan = plan_world_rule_application(
        plan_id="plan-aligned",
        rule=rule,
        task=_task("task-new", TaskDifficulty.NEAR_TRANSFER),
    )
    mismatched_action_plan = plan_world_rule_application(
        plan_id="plan-action-mismatch",
        rule=rule,
        task=_task("task-west", TaskDifficulty.NEAR_TRANSFER, operation_id="move-west"),
    )

    assert aligned_plan.ready
    assert aligned_plan.decision is WorldRuleApplicationDecision.APPLICATION_READY
    assert "move-east" in aligned_plan.matched_actions
    assert not mismatched_action_plan.ready
    assert (
        mismatched_action_plan.decision
        is WorldRuleApplicationDecision.NEEDS_ACTION_ALIGNMENT
    )


def test_world_rule_application_blocks_contradicted_or_revoked_rules() -> None:
    task = _task("task-new", TaskDifficulty.NEAR_TRANSFER)
    contradicted = WorldModelRule(
        rule_id="rule-contradicted",
        family=TaskFamily.GRID_ABSTRACTION,
        kind=WorldRuleKind.TRANSITION,
        statement="Visible east-empty grid states may support move-east.",
        antecedent_features=("east-cell-empty",),
        action_ids=("move-east",),
        expected_consequences=("operation:move-east",),
        exception_features=("wrong-feature",),
        source_trial_ids=("trial-1",),
        evidence_ids=("evidence-1",),
        confidence=WorldRuleConfidence.CONTRADICTED,
    )
    revoked = WorldModelRule(
        rule_id="rule-revoked",
        family=TaskFamily.GRID_ABSTRACTION,
        kind=WorldRuleKind.TRANSITION,
        statement="Visible east-empty grid states may support move-east.",
        antecedent_features=("east-cell-empty",),
        action_ids=("move-east",),
        expected_consequences=("operation:move-east",),
        exception_features=("blocked-trial",),
        source_trial_ids=("trial-1",),
        evidence_ids=("evidence-1",),
        confidence=WorldRuleConfidence.REVOKED,
    )

    contradicted_plan = plan_world_rule_application(
        plan_id="plan-contradicted",
        rule=contradicted,
        task=task,
    )
    revoked_plan = plan_world_rule_application(
        plan_id="plan-revoked",
        rule=revoked,
        task=task,
    )

    assert contradicted_plan.decision is WorldRuleApplicationDecision.BLOCKED_CONTRADICTED
    assert revoked_plan.decision is WorldRuleApplicationDecision.BLOCKED_REVOKED


def test_snapshot_rejects_duplicate_rule_ids() -> None:
    seed = _task("task-seed", TaskDifficulty.SEED)
    rule = derive_world_rule_from_trials(
        rule_id="rule-grid-east-transition",
        statement="Visible east-empty grid states support a bounded move-east transition.",
        family=TaskFamily.GRID_ABSTRACTION,
        trials=(_passing_trial(seed),),
        evidence_ids=("world-rule-evidence-1",),
    )
    update = build_world_model_update(
        update_id="update-hypothesis",
        rule=rule,
        trials=(_passing_trial(seed),),
    )

    with pytest.raises(ValueError, match="Duplicate rule_id"):
        UnknownTaskSuite(
            suite_id="suite-unused",
            purpose="Unused construction keeps imports exercised.",
            tasks=(seed,),
            evidence_ids=("suite-evidence-1",),
        )
        build_world_model_snapshot(
            snapshot_id="snapshot-duplicate",
            purpose="Duplicate rules should fail.",
            updates=(update, update),
            evidence_ids=("snapshot-evidence-1",),
        )
