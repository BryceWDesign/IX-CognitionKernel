import pytest

from ix_cognition_kernel.wave3_contracts import (
    WaveThreeArtifactKind,
    WaveThreeAuthorityState,
)
from ix_cognition_kernel.wave3_curriculum import (
    REQUIRED_CURRICULUM_TASK_KINDS,
    CurriculumMeasurement,
    CurriculumOutcome,
    CurriculumTaskBundle,
    CurriculumTaskKind,
    CurriculumTaskRecord,
    CurriculumTaskStatus,
    measured_curriculum_task,
    passing_curriculum_measurement,
)


def measurement(measurement_id: str = "measurement-001") -> CurriculumMeasurement:
    return passing_curriculum_measurement(
        measurement_id=measurement_id,
        metric_name="evidence-visible-success-rate",
        target="all required evidence remains visible",
        observed="all required evidence remained visible",
        evidence_id=f"evidence:{measurement_id}",
    )


def staged_task(task_id: str = "task-staged") -> CurriculumTaskRecord:
    return measured_curriculum_task(
        task_id=task_id,
        task_kind=CurriculumTaskKind.STAGED_SELF_PLAY,
        stage=1,
        skill_under_test="belief update after failed prediction",
        objective=(
            "Generate a bounded challenge that improves evidence-backed learning."
        ),
        challenge_description="Compare a predicted result against an observed failure.",
        evidence_ids=(f"evidence:{task_id}",),
        measurements=(measurement(f"measurement:{task_id}"),),
    )


def adversarial_task(task_id: str = "task-adversarial") -> CurriculumTaskRecord:
    return measured_curriculum_task(
        task_id=task_id,
        task_kind=CurriculumTaskKind.ADVERSARIAL_CHALLENGE,
        stage=2,
        skill_under_test="reward-hacking detection",
        objective="Pressure the system to expose metric gaming instead of hiding it.",
        challenge_description="Attempt to improve a score by omitting failed evidence.",
        evidence_ids=(f"evidence:{task_id}",),
        measurements=(measurement(f"measurement:{task_id}"),),
        adversarial_pressures=("metric gaming", "hidden failed check"),
    )


def transfer_task(task_id: str = "task-transfer") -> CurriculumTaskRecord:
    return measured_curriculum_task(
        task_id=task_id,
        task_kind=CurriculumTaskKind.TRANSFER_CHECK,
        stage=3,
        skill_under_test="cross-domain uncertainty preservation",
        objective="Check whether uncertainty discipline transfers to a new domain.",
        challenge_description="Apply uncertainty labels to a novel planning scenario.",
        evidence_ids=(f"evidence:{task_id}",),
        measurements=(measurement(f"measurement:{task_id}"),),
        transfer_domains=("repo governance", "world-model scenario review"),
    )


def complete_bundle() -> CurriculumTaskBundle:
    return CurriculumTaskBundle(
        bundle_id="curriculum-bundle-001",
        tasks=(staged_task(), adversarial_task(), transfer_task()),
    )


def test_required_curriculum_task_kinds_are_locked() -> None:
    assert REQUIRED_CURRICULUM_TASK_KINDS == (
        CurriculumTaskKind.STAGED_SELF_PLAY,
        CurriculumTaskKind.ADVERSARIAL_CHALLENGE,
        CurriculumTaskKind.TRANSFER_CHECK,
    )


def test_passing_curriculum_task_is_reviewable_not_executable() -> None:
    task = staged_task()

    assert task.status is CurriculumTaskStatus.READY_FOR_HUMAN_REVIEW
    assert task.ready_for_human_review is True
    assert task.permits_automatic_execution is False
    assert task.human_authority_state is WaveThreeAuthorityState.HUMAN_REVIEW_REQUIRED
    assert task.readiness_gaps == ()
    assert task.blocking_gaps == ()
    assert "automatic execution is not permitted" in task.review_summary


def test_curriculum_measurement_requires_evidence() -> None:
    with pytest.raises(ValueError, match="measurement evidence_id must not be empty"):
        CurriculumMeasurement(
            measurement_id="measurement-001",
            metric_name="evidence-visible-success-rate",
            target="evidence remains visible",
            observed="evidence was visible",
            passed=True,
            evidence_ids=(" ",),
        )


def test_curriculum_task_requires_stage_success_criteria_and_stop_conditions() -> None:
    with pytest.raises(ValueError, match="stage must be at least 1"):
        CurriculumTaskRecord(
            task_id="task-invalid-stage",
            task_kind=CurriculumTaskKind.STAGED_SELF_PLAY,
            stage=0,
            skill_under_test="belief update",
            objective="Invalid stage should fail closed.",
            challenge_description="Invalid challenge.",
            success_criteria=("criterion",),
            stop_conditions=("stop",),
            outcome=CurriculumOutcome.PASSED,
            evidence_ids=("evidence",),
            measurements=(measurement(),),
        )

    with pytest.raises(ValueError, match="require success criteria"):
        CurriculumTaskRecord(
            task_id="task-no-success",
            task_kind=CurriculumTaskKind.STAGED_SELF_PLAY,
            stage=1,
            skill_under_test="belief update",
            objective="Missing success criteria should fail closed.",
            challenge_description="Invalid challenge.",
            success_criteria=(),
            stop_conditions=("stop",),
            outcome=CurriculumOutcome.PASSED,
            evidence_ids=("evidence",),
            measurements=(measurement(),),
        )

    with pytest.raises(ValueError, match="require stop conditions"):
        CurriculumTaskRecord(
            task_id="task-no-stop",
            task_kind=CurriculumTaskKind.STAGED_SELF_PLAY,
            stage=1,
            skill_under_test="belief update",
            objective="Missing stop conditions should fail closed.",
            challenge_description="Invalid challenge.",
            success_criteria=("criterion",),
            stop_conditions=(),
            outcome=CurriculumOutcome.PASSED,
            evidence_ids=("evidence",),
            measurements=(measurement(),),
        )


def test_adversarial_and_transfer_tasks_require_their_extra_scope() -> None:
    with pytest.raises(ValueError, match="Adversarial curriculum tasks require"):
        measured_curriculum_task(
            task_id="task-adversarial",
            task_kind=CurriculumTaskKind.ADVERSARIAL_CHALLENGE,
            stage=2,
            skill_under_test="reward-hacking detection",
            objective="Missing pressure labels should fail closed.",
            challenge_description="Invalid adversarial task.",
            evidence_ids=("evidence",),
            measurements=(measurement(),),
        )

    with pytest.raises(ValueError, match="Transfer curriculum tasks require"):
        measured_curriculum_task(
            task_id="task-transfer",
            task_kind=CurriculumTaskKind.TRANSFER_CHECK,
            stage=3,
            skill_under_test="transfer behavior",
            objective="Missing transfer domains should fail closed.",
            challenge_description="Invalid transfer task.",
            evidence_ids=("evidence",),
            measurements=(measurement(),),
        )


def test_failed_measurement_needs_repair_before_review() -> None:
    failed_measurement = CurriculumMeasurement(
        measurement_id="measurement-failed",
        metric_name="hidden-failure-rate",
        target="zero hidden failures",
        observed="one hidden failure was detected",
        passed=False,
        evidence_ids=("evidence:measurement-failed",),
    )
    task = CurriculumTaskRecord(
        task_id="task-failed",
        task_kind=CurriculumTaskKind.STAGED_SELF_PLAY,
        stage=1,
        skill_under_test="failure visibility",
        objective="Expose hidden failures.",
        challenge_description="Task fails if any failed check is hidden.",
        success_criteria=("zero hidden failures",),
        stop_conditions=("stop when a hidden failure is detected",),
        outcome=CurriculumOutcome.FAILED,
        evidence_ids=("evidence:task-failed",),
        measurements=(failed_measurement,),
    )

    assert task.status is CurriculumTaskStatus.NEEDS_REPAIR
    assert task.ready_for_human_review is False
    assert task.failed_measurement_ids == ("measurement-failed",)
    assert "task-failed failed curriculum outcome" in task.readiness_gaps
    assert "task-failed failed measurements: measurement-failed" in task.readiness_gaps


def test_not_evaluated_task_needs_evidence() -> None:
    task = CurriculumTaskRecord(
        task_id="task-not-evaluated",
        task_kind=CurriculumTaskKind.STAGED_SELF_PLAY,
        stage=1,
        skill_under_test="measurement discipline",
        objective="Show that unevaluated tasks cannot become readiness evidence.",
        challenge_description="No measurement has run yet.",
        success_criteria=("must have measurement",),
        stop_conditions=("stop without evidence",),
        outcome=CurriculumOutcome.NOT_EVALUATED,
        evidence_ids=(),
    )

    assert task.status is CurriculumTaskStatus.NEEDS_EVIDENCE
    assert "task-not-evaluated has no top-level evidence ids" in task.readiness_gaps
    assert "task-not-evaluated has no curriculum measurements" in task.readiness_gaps
    assert "task-not-evaluated has not been evaluated" in task.readiness_gaps


def test_blocked_curriculum_task_requires_and_reports_reasons() -> None:
    with pytest.raises(ValueError, match="Blocked curriculum tasks require"):
        CurriculumTaskRecord(
            task_id="task-blocked",
            task_kind=CurriculumTaskKind.STAGED_SELF_PLAY,
            stage=1,
            skill_under_test="execution-boundary discipline",
            objective="Blocked task must explain why.",
            challenge_description="Invalid blocked task.",
            success_criteria=("criterion",),
            stop_conditions=("stop",),
            outcome=CurriculumOutcome.BLOCKED,
            evidence_ids=("evidence",),
            measurements=(measurement(),),
        )

    task = CurriculumTaskRecord(
        task_id="task-blocked",
        task_kind=CurriculumTaskKind.STAGED_SELF_PLAY,
        stage=1,
        skill_under_test="execution-boundary discipline",
        objective="Stop tasks that attempt unreviewed execution.",
        challenge_description=(
            "The challenge attempted to treat self-play as authority."
        ),
        success_criteria=("no execution authority",),
        stop_conditions=("stop on authority bypass",),
        outcome=CurriculumOutcome.BLOCKED,
        evidence_ids=("evidence:task-blocked",),
        measurements=(measurement("measurement:task-blocked"),),
        blocked_reasons=("attempted unreviewed execution authority",),
    )

    assert task.status is CurriculumTaskStatus.BLOCKED
    assert task.human_authority_state is WaveThreeAuthorityState.BLOCKED
    assert task.blocking_gaps == (
        "task-blocked blocked: attempted unreviewed execution authority",
    )


def test_curriculum_task_must_be_generated_by_self_play_engine() -> None:
    with pytest.raises(ValueError, match="must be generated by self-play-curriculum"):
        CurriculumTaskRecord(
            task_id="task-wrong-engine",
            task_kind=CurriculumTaskKind.STAGED_SELF_PLAY,
            stage=1,
            skill_under_test="engine boundary",
            objective="Wrong engine should fail closed.",
            challenge_description="Invalid generator.",
            success_criteria=("criterion",),
            stop_conditions=("stop",),
            outcome=CurriculumOutcome.PASSED,
            evidence_ids=("evidence",),
            measurements=(measurement(),),
            generated_by_engine_id="planner",
        )


def test_curriculum_task_converts_to_shared_artifact_ref() -> None:
    artifact = staged_task().to_artifact_ref()

    assert artifact.artifact_id == "curriculum-task:task-staged"
    assert artifact.kind is WaveThreeArtifactKind.CURRICULUM_TASK
    assert artifact.produced_by_engine_id == "self-play-curriculum"
    assert artifact.produced_by_agent_role_id == "curriculum-designer"
    assert artifact.allowed_for_automatic_execution is False
    assert artifact.ready_for_human_review is True


def test_curriculum_bundle_reports_required_kind_coverage() -> None:
    bundle = CurriculumTaskBundle(
        bundle_id="curriculum-bundle-001",
        tasks=(staged_task(),),
    )

    assert bundle.missing_required_task_kinds == (
        CurriculumTaskKind.ADVERSARIAL_CHALLENGE,
        CurriculumTaskKind.TRANSFER_CHECK,
    )
    assert bundle.is_complete_for_required_tasks is False
    assert (
        "missing required curriculum task kinds: adversarial-challenge, transfer-check"
        in bundle.readiness_gaps
    )


def test_complete_curriculum_bundle_is_reviewable() -> None:
    bundle = complete_bundle()

    assert bundle.task_ids == ("task-adversarial", "task-staged", "task-transfer")
    assert bundle.represented_task_kinds == REQUIRED_CURRICULUM_TASK_KINDS
    assert bundle.missing_required_task_kinds == ()
    assert set(bundle.ready_task_ids) == {
        "task-adversarial",
        "task-staged",
        "task-transfer",
    }
    assert bundle.blocked_task_ids == ()
    assert bundle.readiness_gaps == ()
    assert bundle.is_complete_for_required_tasks is True


def test_curriculum_bundle_rejects_duplicate_tasks() -> None:
    task = staged_task()

    with pytest.raises(ValueError, match="Duplicate task_id"):
        CurriculumTaskBundle(
            bundle_id="curriculum-bundle-001",
            tasks=(task, task),
        )


def test_curriculum_bundle_converts_to_shared_artifact_bundle() -> None:
    artifact_bundle = complete_bundle().to_artifact_bundle(
        artifact_bundle_id="curriculum-artifacts"
    )

    assert artifact_bundle.has_required_kind_coverage is True
    assert artifact_bundle.artifact_ids == (
        "curriculum-task:task-adversarial",
        "curriculum-task:task-staged",
        "curriculum-task:task-transfer",
    )
    assert set(artifact_bundle.ready_for_human_review_artifact_ids) == {
        "curriculum-task:task-adversarial",
        "curriculum-task:task-staged",
        "curriculum-task:task-transfer",
    }


def test_curriculum_fingerprints_are_deterministic_despite_input_order() -> None:
    first = CurriculumTaskBundle(
        bundle_id="curriculum-bundle-001",
        tasks=(transfer_task(), staged_task(), adversarial_task()),
    )
    second = CurriculumTaskBundle(
        bundle_id="curriculum-bundle-001",
        tasks=(adversarial_task(), staged_task(), transfer_task()),
    )

    assert first.fingerprint() == second.fingerprint()
    assert len(first.fingerprint()) == 64
