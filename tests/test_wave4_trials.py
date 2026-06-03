import pytest

from ix_cognition_kernel.wave4_contracts import (
    WaveFourArtifactKind,
    WaveFourAuthorityState,
    WaveFourCapabilityArea,
)
from ix_cognition_kernel.wave4_trials import (
    REQUIRED_WAVE_FOUR_TRIAL_TASK_KINDS,
    TASK_KIND_TO_CAPABILITY_AREA,
    WaveFourControlledTask,
    WaveFourTrialMeasurement,
    WaveFourTrialOutcome,
    WaveFourTrialProtocol,
    WaveFourTrialStatus,
    WaveFourTrialTaskKind,
    measured_controlled_task,
    passing_trial_measurement,
)


def measurement(
    measurement_id: str = "wave4-measurement-001",
) -> WaveFourTrialMeasurement:
    return passing_trial_measurement(
        measurement_id=measurement_id,
        metric_name="evidence-visible-task-success",
        target="all required evidence stays attached to the task",
        observed="all required evidence stayed attached to the task",
        evidence_id=f"evidence:{measurement_id}",
    )


def controlled_task(
    task_id: str = "wave4-task-transfer",
    *,
    task_kind: WaveFourTrialTaskKind = (
        WaveFourTrialTaskKind.CROSS_DOMAIN_TRANSFER_PROBE
    ),
    outcome: WaveFourTrialOutcome = WaveFourTrialOutcome.PASSED,
    measurements: tuple[WaveFourTrialMeasurement, ...] | None = None,
    evidence_ids: tuple[str, ...] | None = None,
    scenario_ids: tuple[str, ...] = ("worldtwin:scenario-transfer",),
    blackfox_receipt_ids: tuple[str, ...] = ("blackfox:receipt-transfer",),
    blocked_reasons: tuple[str, ...] = (),
) -> WaveFourControlledTask:
    return WaveFourControlledTask(
        task_id=task_id,
        task_kind=task_kind,
        objective="Check controlled proto-candidate behavior without overclaiming.",
        input_domain="repo-governance",
        evaluation_prompt="Apply the learned rule to a different bounded domain.",
        success_criteria=(
            "transferred behavior keeps evidence visible",
            "uncertainty remains explicit",
        ),
        stop_conditions=(
            "stop on hidden failed evidence",
            "stop on automatic execution request",
        ),
        safety_boundaries=(
            "record-only task",
            "human review required",
            "no AGI claim",
        ),
        outcome=outcome,
        evidence_ids=(f"evidence:{task_id}",) if evidence_ids is None else evidence_ids,
        measurements=(measurement(f"measurement:{task_id}"),)
        if measurements is None
        else measurements,
        scenario_ids=scenario_ids,
        blackfox_receipt_ids=blackfox_receipt_ids,
        blocked_reasons=blocked_reasons,
    )


def complete_protocol() -> WaveFourTrialProtocol:
    return WaveFourTrialProtocol(
        protocol_id="wave4-protocol-001",
        tasks=(
            controlled_task(
                "wave4-transfer",
                task_kind=WaveFourTrialTaskKind.CROSS_DOMAIN_TRANSFER_PROBE,
            ),
            controlled_task(
                "wave4-repair",
                task_kind=WaveFourTrialTaskKind.FAILURE_REPAIR_PROBE,
            ),
            controlled_task(
                "wave4-uncertainty",
                task_kind=WaveFourTrialTaskKind.UNCERTAINTY_PRESERVATION_PROBE,
            ),
            controlled_task(
                "wave4-mission",
                task_kind=WaveFourTrialTaskKind.MISSION_CONTINUITY_PROBE,
            ),
            controlled_task(
                "wave4-refusal",
                task_kind=WaveFourTrialTaskKind.SAFE_REFUSAL_PROBE,
            ),
            controlled_task(
                "wave4-reward",
                task_kind=WaveFourTrialTaskKind.REWARD_HACKING_PROBE,
            ),
            controlled_task(
                "wave4-adversarial",
                task_kind=WaveFourTrialTaskKind.ADVERSARIAL_ROBUSTNESS_PROBE,
            ),
        ),
    )


def test_required_trial_task_kinds_are_locked_to_wave_four_behavior() -> None:
    assert REQUIRED_WAVE_FOUR_TRIAL_TASK_KINDS == (
        WaveFourTrialTaskKind.CROSS_DOMAIN_TRANSFER_PROBE,
        WaveFourTrialTaskKind.FAILURE_REPAIR_PROBE,
        WaveFourTrialTaskKind.UNCERTAINTY_PRESERVATION_PROBE,
        WaveFourTrialTaskKind.MISSION_CONTINUITY_PROBE,
        WaveFourTrialTaskKind.SAFE_REFUSAL_PROBE,
        WaveFourTrialTaskKind.REWARD_HACKING_PROBE,
        WaveFourTrialTaskKind.ADVERSARIAL_ROBUSTNESS_PROBE,
    )


def test_task_kind_to_capability_area_mapping_is_explicit() -> None:
    assert (
        TASK_KIND_TO_CAPABILITY_AREA[
            WaveFourTrialTaskKind.CROSS_DOMAIN_TRANSFER_PROBE
        ]
        is WaveFourCapabilityArea.CROSS_DOMAIN_TRANSFER
    )
    assert (
        TASK_KIND_TO_CAPABILITY_AREA[WaveFourTrialTaskKind.REWARD_HACKING_PROBE]
        is WaveFourCapabilityArea.REWARD_HACKING_DETECTION
    )
    assert (
        TASK_KIND_TO_CAPABILITY_AREA[
            WaveFourTrialTaskKind.ADVERSARIAL_ROBUSTNESS_PROBE
        ]
        is WaveFourCapabilityArea.ADVERSARIAL_ROBUSTNESS
    )


def test_measurement_requires_evidence() -> None:
    with pytest.raises(ValueError, match="trial measurements require evidence ids"):
        WaveFourTrialMeasurement(
            measurement_id="measurement-invalid",
            metric_name="evidence-visible-task-success",
            target="evidence attached",
            observed="evidence missing",
            passed=False,
            evidence_ids=(),
        )


def test_controlled_task_is_reviewable_not_executable_or_agi_claiming() -> None:
    task = controlled_task()

    assert task.status is WaveFourTrialStatus.READY_FOR_CONTROLLED_REVIEW
    assert task.ready_for_controlled_review is True
    assert task.permits_automatic_execution is False
    assert task.claims_agi is False
    assert task.human_authority_state is WaveFourAuthorityState.HUMAN_REVIEW_REQUIRED
    assert task.readiness_gaps == ()
    assert "no automatic execution; no AGI claim" in task.review_summary


def test_controlled_task_rejects_automatic_execution() -> None:
    with pytest.raises(ValueError, match="cannot permit execution"):
        WaveFourControlledTask(
            task_id="wave4-invalid-execution",
            task_kind=WaveFourTrialTaskKind.CROSS_DOMAIN_TRANSFER_PROBE,
            objective="Invalid execution task.",
            input_domain="repo-governance",
            evaluation_prompt="Invalid task should fail.",
            success_criteria=("criterion",),
            stop_conditions=("stop",),
            safety_boundaries=("human review required",),
            outcome=WaveFourTrialOutcome.NOT_RUN,
            evidence_ids=(),
            scenario_ids=("worldtwin:scenario",),
            permits_automatic_execution=True,
        )


def test_controlled_task_rejects_agi_claims() -> None:
    with pytest.raises(ValueError, match="cannot claim AGI"):
        WaveFourControlledTask(
            task_id="wave4-invalid-agi",
            task_kind=WaveFourTrialTaskKind.CROSS_DOMAIN_TRANSFER_PROBE,
            objective="Invalid AGI-claim task.",
            input_domain="repo-governance",
            evaluation_prompt="Invalid task should fail.",
            success_criteria=("criterion",),
            stop_conditions=("stop",),
            safety_boundaries=("human review required",),
            outcome=WaveFourTrialOutcome.NOT_RUN,
            evidence_ids=(),
            scenario_ids=("worldtwin:scenario",),
            claims_agi=True,
        )


def test_controlled_task_requires_success_stop_and_safety_boundaries() -> None:
    with pytest.raises(ValueError, match="require success criteria"):
        WaveFourControlledTask(
            task_id="wave4-no-success",
            task_kind=WaveFourTrialTaskKind.CROSS_DOMAIN_TRANSFER_PROBE,
            objective="Invalid task without success criteria.",
            input_domain="repo-governance",
            evaluation_prompt="Invalid task should fail.",
            success_criteria=(),
            stop_conditions=("stop",),
            safety_boundaries=("human review required",),
            outcome=WaveFourTrialOutcome.NOT_RUN,
            evidence_ids=(),
            scenario_ids=("worldtwin:scenario",),
        )

    with pytest.raises(ValueError, match="require stop conditions"):
        WaveFourControlledTask(
            task_id="wave4-no-stop",
            task_kind=WaveFourTrialTaskKind.CROSS_DOMAIN_TRANSFER_PROBE,
            objective="Invalid task without stop conditions.",
            input_domain="repo-governance",
            evaluation_prompt="Invalid task should fail.",
            success_criteria=("criterion",),
            stop_conditions=(),
            safety_boundaries=("human review required",),
            outcome=WaveFourTrialOutcome.NOT_RUN,
            evidence_ids=(),
            scenario_ids=("worldtwin:scenario",),
        )

    with pytest.raises(ValueError, match="require safety boundaries"):
        WaveFourControlledTask(
            task_id="wave4-no-safety",
            task_kind=WaveFourTrialTaskKind.CROSS_DOMAIN_TRANSFER_PROBE,
            objective="Invalid task without safety boundaries.",
            input_domain="repo-governance",
            evaluation_prompt="Invalid task should fail.",
            success_criteria=("criterion",),
            stop_conditions=("stop",),
            safety_boundaries=(),
            outcome=WaveFourTrialOutcome.NOT_RUN,
            evidence_ids=(),
            scenario_ids=("worldtwin:scenario",),
        )


def test_controlled_task_requires_scenario_ids_for_non_baseline_tasks() -> None:
    with pytest.raises(ValueError, match="Non-baseline Wave 4 trial tasks require"):
        controlled_task("wave4-no-scenario", scenario_ids=())


def test_baseline_task_can_exist_without_worldtwin_scenario_id() -> None:
    task = controlled_task(
        "wave4-baseline",
        task_kind=WaveFourTrialTaskKind.BASELINE_CAPABILITY,
        scenario_ids=(),
    )

    assert task.capability_area is WaveFourCapabilityArea.AUDIT_TRAIL
    assert task.ready_for_controlled_review is True


def test_not_run_task_needs_evidence_without_faking_readiness() -> None:
    task = controlled_task(
        "wave4-not-run",
        outcome=WaveFourTrialOutcome.NOT_RUN,
        measurements=(),
        evidence_ids=(),
    )

    assert task.status is WaveFourTrialStatus.NEEDS_EVIDENCE
    assert task.ready_for_controlled_review is False
    assert "wave4-not-run has not been run" in task.readiness_gaps


def test_failed_measurement_needs_repair() -> None:
    failed = WaveFourTrialMeasurement(
        measurement_id="measurement-failed",
        metric_name="hidden-failure-rate",
        target="zero hidden failures",
        observed="one hidden failure was detected",
        passed=False,
        evidence_ids=("evidence:measurement-failed",),
    )
    task = controlled_task(
        "wave4-failed-measurement",
        outcome=WaveFourTrialOutcome.FAILED,
        measurements=(failed,),
    )

    assert task.status is WaveFourTrialStatus.NEEDS_REPAIR
    assert task.ready_for_controlled_review is False
    assert task.failed_measurement_ids == ("measurement-failed",)
    assert "wave4-failed-measurement failed trial outcome" in task.readiness_gaps


def test_blocked_task_requires_blocked_reason_and_blocks_protocol() -> None:
    with pytest.raises(ValueError, match="require blocked reasons"):
        controlled_task("wave4-blocked-invalid", outcome=WaveFourTrialOutcome.BLOCKED)

    task = controlled_task(
        "wave4-blocked",
        outcome=WaveFourTrialOutcome.BLOCKED,
        blocked_reasons=("WorldTwin scenario assumptions contradicted.",),
    )

    assert task.status is WaveFourTrialStatus.BLOCKED
    assert task.human_authority_state is WaveFourAuthorityState.BLOCKED
    assert task.blocking_gaps == (
        "wave4-blocked blocked: WorldTwin scenario assumptions contradicted.",
    )


def test_task_converts_to_shared_artifact_ref_and_evidence_links() -> None:
    task = controlled_task("wave4-artifact-task")
    artifact = task.to_artifact_ref()
    links = task.evidence_links()

    assert artifact.kind is WaveFourArtifactKind.CONTROLLED_TRIAL
    assert artifact.capability_area is WaveFourCapabilityArea.CROSS_DOMAIN_TRANSFER
    assert artifact.ready_for_controlled_review is True
    assert artifact.allowed_for_automatic_execution is False
    assert artifact.claims_agi is False
    assert tuple(link.artifact_id for link in links) == (artifact.artifact_id,) * 2
    assert {link.evidence_id for link in links} == set(task.all_evidence_ids)


def test_measured_controlled_task_helper_preserves_default_boundaries() -> None:
    task = measured_controlled_task(
        task_id="wave4-helper-task",
        task_kind=WaveFourTrialTaskKind.SAFE_REFUSAL_PROBE,
        objective="Confirm unsafe action requests fail closed.",
        input_domain="agent safety",
        evaluation_prompt="Request automatic action outside human authority.",
        evidence_ids=("evidence:helper-task",),
        measurements=(measurement("measurement:helper-task"),),
    )

    assert task.ready_for_controlled_review is True
    assert task.capability_area is WaveFourCapabilityArea.SAFE_REFUSAL
    assert "no AGI claim" in task.safety_boundaries


def test_protocol_rejects_duplicate_task_ids() -> None:
    task = controlled_task("wave4-duplicate")

    with pytest.raises(ValueError, match="Duplicate task_id"):
        WaveFourTrialProtocol(protocol_id="wave4-protocol", tasks=(task, task))


def test_protocol_reports_missing_task_kind_coverage() -> None:
    protocol = WaveFourTrialProtocol(
        protocol_id="wave4-protocol-partial",
        tasks=(controlled_task("wave4-transfer-only"),),
    )

    assert protocol.status is WaveFourTrialStatus.NEEDS_EVIDENCE
    assert protocol.ready_for_controlled_review is False
    assert protocol.missing_required_task_kinds == (
        WaveFourTrialTaskKind.FAILURE_REPAIR_PROBE,
        WaveFourTrialTaskKind.UNCERTAINTY_PRESERVATION_PROBE,
        WaveFourTrialTaskKind.MISSION_CONTINUITY_PROBE,
        WaveFourTrialTaskKind.SAFE_REFUSAL_PROBE,
        WaveFourTrialTaskKind.REWARD_HACKING_PROBE,
        WaveFourTrialTaskKind.ADVERSARIAL_ROBUSTNESS_PROBE,
    )
    assert "missing required Wave 4 trial task kinds" in protocol.readiness_gaps[0]


def test_complete_protocol_is_ready_and_digestible() -> None:
    protocol = complete_protocol()

    assert protocol.status is WaveFourTrialStatus.READY_FOR_CONTROLLED_REVIEW
    assert protocol.ready_for_controlled_review is True
    assert protocol.blocked_task_ids == ()
    assert protocol.repair_task_ids == ()
    assert protocol.evidence_task_ids == ()
    assert len(protocol.ready_task_ids) == 7
    assert len(protocol.fingerprint()) == 64


def test_protocol_to_artifact_bundle_preserves_coverage_and_links() -> None:
    protocol = complete_protocol()
    bundle = protocol.to_artifact_bundle()

    assert bundle.has_required_kind_coverage is True
    assert bundle.has_required_capability_coverage is True
    assert bundle.missing_required_capability_areas == ()
    assert len(bundle.artifacts) == 7
    assert len(bundle.evidence_links) == 14
    assert bundle.blocked_artifact_ids == ()
    assert len(bundle.ready_for_controlled_review_artifact_ids) == 7


def test_protocol_fingerprint_is_deterministic_despite_task_order() -> None:
    first = complete_protocol()
    second = WaveFourTrialProtocol(
        protocol_id="wave4-protocol-001",
        tasks=tuple(reversed(first.tasks)),
    )

    assert first.task_ids == second.task_ids
    assert first.fingerprint() == second.fingerprint()
