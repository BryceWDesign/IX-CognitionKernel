import pytest

from ix_cognition_kernel.wave8_curriculum_frontier import (
    CurriculumFrontierPlan,
    CurriculumSignal,
    CurriculumSignalKind,
    FrontierItem,
    FrontierPriority,
    build_curriculum_frontier_plan,
)
from ix_cognition_kernel.wave8_environment_protocol import EnvironmentActionResult
from ix_cognition_kernel.wave8_episode_runner import run_single_step_episode
from ix_cognition_kernel.wave8_model_adapter import (
    DeterministicModelAdapter,
    DeterministicModelPolicy,
)
from ix_cognition_kernel.wave8_task_suite import (
    TaskDifficulty,
    TaskDisclosureLevel,
    UnknownTaskSuite,
    build_grid_transition_task,
    build_grid_transition_template,
)
from ix_cognition_kernel.wave8_transfer_challenge import build_transfer_trial_record


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
        suite_id="suite-frontier",
        purpose="Rank seed, transfer, adversarial, and hidden validation tasks.",
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


def _run_for_task(task, *, measured: bool = True, operation_id: str = "move-east"):
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
        result=_result(task.task_id, measured=measured),
    )


def _trial(task, *, observed_matches: bool = True, measured: bool = True):
    observed = task.expected_outcome_features
    if not observed_matches:
        observed = ("wrong-feature",)
    return build_transfer_trial_record(
        trial_id=f"{task.task_id}:trial",
        task=task,
        run=_run_for_task(task, measured=measured),
        observed_feature_ids=observed,
        evidence_ids=(f"{task.task_id}:trial-evidence",),
    )


def test_frontier_selects_highest_value_untried_transfer_task_before_seed() -> None:
    suite = _suite()
    plan = build_curriculum_frontier_plan(
        plan_id="plan-1",
        suite=suite,
        completed_trials=(),
        hold_hidden_validation=True,
    )

    assert plan.has_selection
    assert plan.selected_task_id == "task-adversarial"
    assert plan.selected_item is not None
    assert plan.selected_item.priority is FrontierPriority.SELECT_NOW
    assert "hidden-validation-held" in plan.findings
    assert plan.fingerprint() == plan.fingerprint()
    assert len(plan.fingerprint()) == 64


def test_frontier_holds_hidden_validation_until_explicitly_released() -> None:
    suite = _suite()
    held_plan = build_curriculum_frontier_plan(
        plan_id="plan-held",
        suite=suite,
        hold_hidden_validation=True,
    )
    released_plan = build_curriculum_frontier_plan(
        plan_id="plan-released",
        suite=suite,
        hold_hidden_validation=False,
    )

    hidden_held = next(item for item in held_plan.items if item.task.task_id == "task-hidden")
    hidden_released = next(
        item for item in released_plan.items if item.task.task_id == "task-hidden"
    )

    assert hidden_held.priority is FrontierPriority.HOLD_HIDDEN_VALIDATION
    assert hidden_released.priority is FrontierPriority.SELECT_NOW
    assert released_plan.selected_task_id == "task-hidden"


def test_frontier_prefers_recoverable_transfer_failure_over_replay_pass() -> None:
    suite = _suite()
    seed, near, far, adversarial, hidden = suite.tasks
    plan = build_curriculum_frontier_plan(
        plan_id="plan-failure-pressure",
        suite=suite,
        completed_trials=(
            _trial(seed),
            _trial(near),
            _trial(far, observed_matches=False),
            _trial(adversarial),
            _trial(hidden),
        ),
        hold_hidden_validation=False,
    )

    assert plan.selected_task_id == "task-far"
    assert plan.selected_item is not None
    assert plan.selected_item.priority is FrontierPriority.SELECT_NOW
    assert any(
        signal.kind is CurriculumSignalKind.FAR_TRANSFER_GAP
        for signal in plan.selected_item.signals
    )


def test_frontier_marks_unmeasured_trials_for_replay_before_promotion() -> None:
    suite = _suite()
    seed = suite.tasks[0]
    plan = build_curriculum_frontier_plan(
        plan_id="plan-unmeasured",
        suite=suite,
        completed_trials=(_trial(seed, measured=False),),
        hold_hidden_validation=True,
    )
    seed_item = next(item for item in plan.items if item.task.task_id == "task-seed")

    assert seed_item.priority is FrontierPriority.SELECT_AFTER_REPLAY
    assert seed_item.selectable


def test_frontier_blocks_tasks_with_blocked_prior_trials() -> None:
    suite = _suite()
    seed = suite.tasks[0]
    blocked_trial = build_transfer_trial_record(
        trial_id="blocked-trial",
        task=seed,
        run=_run_for_task(seed, operation_id="delete-host-file"),
        observed_feature_ids=seed.expected_outcome_features,
        evidence_ids=("blocked-trial-evidence",),
    )
    plan = build_curriculum_frontier_plan(
        plan_id="plan-blocked",
        suite=suite,
        completed_trials=(blocked_trial,),
    )
    seed_item = next(item for item in plan.items if item.task.task_id == "task-seed")

    assert seed_item.priority is FrontierPriority.BLOCKED
    assert not seed_item.selectable
    assert "blocked-frontier-item-present" in plan.findings


def test_frontier_plan_rejects_selected_non_selectable_task() -> None:
    suite = _suite()
    hidden = suite.tasks[-1]
    signal = CurriculumSignal(
        signal_id="hidden-signal",
        task=hidden,
        kind=CurriculumSignalKind.HIDDEN_VALIDATION_GAP,
        rationale="Hold hidden validation.",
        evidence_ids=("hidden-evidence",),
        score=60,
    )
    item = FrontierItem(
        item_id="hidden-item",
        task=hidden,
        signals=(signal,),
        priority=FrontierPriority.HOLD_HIDDEN_VALIDATION,
    )

    with pytest.raises(ValueError, match="must cover every suite task"):
        CurriculumFrontierPlan(
            plan_id="bad-plan",
            suite=suite,
            items=(item,),
            selected_task_id=hidden.task_id,
        )


def test_curriculum_signal_rejects_blocked_signal_with_positive_score() -> None:
    task = _suite().tasks[0]

    with pytest.raises(ValueError, match="must have zero score"):
        CurriculumSignal(
            signal_id="bad-blocked-signal",
            task=task,
            kind=CurriculumSignalKind.BLOCKED_EVIDENCE,
            rationale="Blocked evidence cannot have positive score.",
            evidence_ids=("evidence-1",),
            score=1,
        )
