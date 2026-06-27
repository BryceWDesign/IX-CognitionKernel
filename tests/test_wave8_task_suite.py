import pytest

from ix_cognition_kernel.wave8_environment_protocol import (
    BoundedEnvironmentSpec,
    EnvironmentKind,
    EnvironmentObservation,
)
from ix_cognition_kernel.wave8_task_suite import (
    TaskDifficulty,
    TaskDisclosureLevel,
    TaskSuiteValidationDecision,
    UnknownTaskInstance,
    UnknownTaskSuite,
    build_grid_transition_task,
    build_grid_transition_template,
    validate_unknown_task_suite,
)


def _template():
    return build_grid_transition_template(template_id="grid-template-1")


def _seed_task():
    return build_grid_transition_task(
        task_id="task-seed",
        template=_template(),
        episode_id="episode-seed",
        start_state_id="state-0-0",
        empty_direction="east",
        expected_operation_id="move-east",
        difficulty=TaskDifficulty.SEED,
        disclosure_level=TaskDisclosureLevel.PARTIALLY_WITHHELD,
    )


def _transfer_task():
    return build_grid_transition_task(
        task_id="task-transfer",
        template=_template(),
        episode_id="episode-transfer",
        start_state_id="state-1-0",
        empty_direction="west",
        expected_operation_id="move-west",
        difficulty=TaskDifficulty.NEAR_TRANSFER,
        disclosure_level=TaskDisclosureLevel.PARTIALLY_WITHHELD,
    )


def _hidden_task():
    return build_grid_transition_task(
        task_id="task-hidden",
        template=_template(),
        episode_id="episode-hidden",
        start_state_id="state-2-0",
        empty_direction="east",
        expected_operation_id="move-east",
        difficulty=TaskDifficulty.HIDDEN_VALIDATION,
        disclosure_level=TaskDisclosureLevel.HIDDEN_GOAL,
    )


def test_grid_transition_template_is_deterministic() -> None:
    template = _template()

    assert template.family.value == "grid-abstraction"
    assert template.fingerprint() == template.fingerprint()
    assert len(template.fingerprint()) == 64
    assert "move-east" in template.allowed_action_space_ids


def test_grid_transition_task_binds_environment_and_measured_observation() -> None:
    task = _seed_task()

    assert task.environment.environment_id == "task-seed:environment"
    assert task.initial_observation.environment_id == task.environment.environment_id
    assert task.initial_observation.measured
    assert task.withheld_features
    assert not task.is_transfer_pressure
    assert task.fingerprint() == task.fingerprint()


def test_hidden_validation_task_counts_as_hidden_and_transfer_pressure() -> None:
    task = _hidden_task()

    assert task.is_transfer_pressure
    assert task.is_hidden_validation
    assert task.environment.hidden_goal
    assert task.disclosure_level is TaskDisclosureLevel.HIDDEN_GOAL


def test_task_instance_rejects_unmeasured_initial_observation() -> None:
    template = _template()
    environment = BoundedEnvironmentSpec(
        environment_id="env-bad",
        kind=EnvironmentKind.GRID_ABSTRACTION,
        objective=template.objective,
        observation_channels=("grid-visible-state",),
        action_space_ids=template.allowed_action_space_ids,
        scoring_rules=template.scoring_rules,
        reset_evidence_ids=("reset-evidence-1",),
    )
    observation = EnvironmentObservation(
        observation_id="obs-bad",
        environment_id="env-bad",
        episode_id="episode-bad",
        state_id="state-bad",
        channel_id="grid-visible-state",
        summary="Unmeasured observation.",
        visible_features=("state-bad",),
        evidence_ids=("obs-evidence-1",),
        measured=False,
    )

    with pytest.raises(ValueError, match="require measured observations"):
        UnknownTaskInstance(
            task_id="task-bad",
            template=template,
            environment=environment,
            initial_observation=observation,
            expected_outcome_features=("operation:move-east",),
            withheld_features=("expected-operation:move-east",),
            transfer_tags=("family:grid-abstraction",),
            evidence_ids=("task-evidence-1",),
        )


def test_task_instance_rejects_fully_visible_task_with_withheld_features() -> None:
    task = _seed_task()

    with pytest.raises(ValueError, match="Fully visible tasks must not include"):
        UnknownTaskInstance(
            task_id="task-visible-bad",
            template=task.template,
            environment=task.environment,
            initial_observation=task.initial_observation,
            expected_outcome_features=task.expected_outcome_features,
            withheld_features=("should-not-be-withheld",),
            transfer_tags=task.transfer_tags,
            evidence_ids=("task-evidence-visible",),
            disclosure_level=TaskDisclosureLevel.FULLY_VISIBLE,
        )


def test_unknown_task_suite_validates_transfer_and_hidden_pressure() -> None:
    seed_only_suite = UnknownTaskSuite(
        suite_id="suite-seed-only",
        purpose="Seed-only suite should not make transfer claims.",
        tasks=(_seed_task(),),
        evidence_ids=("suite-evidence-1",),
    )
    transfer_only_suite = UnknownTaskSuite(
        suite_id="suite-transfer-only",
        purpose="Transfer-only suite still needs hidden validation.",
        tasks=(_seed_task(), _transfer_task()),
        evidence_ids=("suite-evidence-2",),
    )
    ready_suite = UnknownTaskSuite(
        suite_id="suite-ready",
        purpose="Suite contains seed, transfer, and hidden validation pressure.",
        tasks=(_seed_task(), _transfer_task(), _hidden_task()),
        evidence_ids=("suite-evidence-3",),
    )

    seed_report = validate_unknown_task_suite(
        report_id="report-seed-only",
        suite=seed_only_suite,
    )
    transfer_report = validate_unknown_task_suite(
        report_id="report-transfer-only",
        suite=transfer_only_suite,
    )
    ready_report = validate_unknown_task_suite(
        report_id="report-ready",
        suite=ready_suite,
    )

    assert seed_report.decision is TaskSuiteValidationDecision.NEEDS_TRANSFER_PRESSURE
    assert (
        transfer_report.decision is TaskSuiteValidationDecision.NEEDS_HIDDEN_VALIDATION
    )
    assert ready_report.decision is TaskSuiteValidationDecision.READY_FOR_EPISODES
    assert ready_report.ready


def test_unknown_task_suite_rejects_duplicate_task_ids() -> None:
    task = _seed_task()

    with pytest.raises(ValueError, match="Duplicate task_id"):
        UnknownTaskSuite(
            suite_id="suite-duplicate",
            purpose="Duplicate task ids should fail.",
            tasks=(task, task),
            evidence_ids=("suite-evidence-1",),
        )
