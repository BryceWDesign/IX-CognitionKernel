import pytest

from ix_cognition_kernel.wave4_contracts import (
    WAVE_FOUR_REQUIRED_ARTIFACT_KINDS,
    WaveFourArtifactBundle,
    WaveFourArtifactDecision,
    WaveFourArtifactKind,
    WaveFourArtifactRef,
    WaveFourAuthorityState,
    WaveFourCapabilityArea,
    WaveFourEvidenceLink,
    WaveFourEvidenceRelation,
    WaveFourSourceSystem,
)
from ix_cognition_kernel.wave4_proto_candidate import (
    REQUIRED_WAVE_FOUR_PROTO_TASK_KINDS,
    WaveFourProtoCandidateOutcome,
    WaveFourProtoCandidateStatus,
    WaveFourProtoCandidateTrialBundle,
)
from ix_cognition_kernel.wave4_trials import (
    WaveFourControlledTask,
    WaveFourTrialMeasurement,
    WaveFourTrialOutcome,
    WaveFourTrialProtocol,
    WaveFourTrialTaskKind,
)

KIND_TO_CAPABILITY: dict[WaveFourArtifactKind, WaveFourCapabilityArea] = {
    WaveFourArtifactKind.CONTROLLED_TRIAL: WaveFourCapabilityArea.AUDIT_TRAIL,
    WaveFourArtifactKind.TRANSFER_EVALUATION: (
        WaveFourCapabilityArea.CROSS_DOMAIN_TRANSFER
    ),
    WaveFourArtifactKind.FAILURE_REPAIR_CYCLE: (
        WaveFourCapabilityArea.SELF_IMPROVEMENT_AFTER_FAILURE
    ),
    WaveFourArtifactKind.UNCERTAINTY_TRACE: (
        WaveFourCapabilityArea.UNCERTAINTY_PRESERVATION
    ),
    WaveFourArtifactKind.MISSION_STATE_TRACE: (
        WaveFourCapabilityArea.LONG_HORIZON_MISSION_STATE
    ),
    WaveFourArtifactKind.SAFE_REFUSAL_RECORD: WaveFourCapabilityArea.SAFE_REFUSAL,
    WaveFourArtifactKind.REWARD_HACKING_AUDIT: (
        WaveFourCapabilityArea.REWARD_HACKING_DETECTION
    ),
    WaveFourArtifactKind.ADVERSARIAL_ROBUSTNESS_RECORD: (
        WaveFourCapabilityArea.ADVERSARIAL_ROBUSTNESS
    ),
    WaveFourArtifactKind.REPRODUCIBLE_AUDIT_TRAIL: WaveFourCapabilityArea.AUDIT_TRAIL,
    WaveFourArtifactKind.READINESS_SNAPSHOT: WaveFourCapabilityArea.AUDIT_TRAIL,
}


def measurement(task_id: str) -> WaveFourTrialMeasurement:
    return WaveFourTrialMeasurement(
        measurement_id=f"measurement:{task_id}",
        metric_name="proto-candidate-coverage-check",
        target="task evidence remains attached and reviewable",
        observed="task evidence remained attached and reviewable",
        passed=True,
        evidence_ids=(f"evidence:measurement:{task_id}",),
    )


def task(
    task_id: str,
    task_kind: WaveFourTrialTaskKind,
    *,
    outcome: WaveFourTrialOutcome = WaveFourTrialOutcome.PASSED,
    measurements: tuple[WaveFourTrialMeasurement, ...] | None = None,
) -> WaveFourControlledTask:
    scenario_ids: tuple[str, ...] = ()
    if task_kind is not WaveFourTrialTaskKind.BASELINE_CAPABILITY:
        scenario_ids = (f"worldtwin:{task_id}",)
    if measurements is None and outcome is WaveFourTrialOutcome.PASSED:
        measurements = (measurement(task_id),)
    return WaveFourControlledTask(
        task_id=task_id,
        task_kind=task_kind,
        objective="Verify one Wave 4 proto-candidate behavior under review.",
        input_domain="controlled proto-candidate integration",
        evaluation_prompt="Check behavior with evidence, uncertainty, and authority.",
        success_criteria=(
            "evidence remains visible",
            "human review remains required",
        ),
        stop_conditions=(
            "stop on missing evidence",
            "stop on automatic execution request",
        ),
        safety_boundaries=(
            "record only",
            "human review required",
            "no AGI claim",
        ),
        outcome=outcome,
        evidence_ids=(f"evidence:{task_id}",),
        measurements=() if measurements is None else measurements,
        scenario_ids=scenario_ids,
        blackfox_receipt_ids=(f"blackfox:{task_id}",),
    )


def complete_protocol() -> WaveFourTrialProtocol:
    return WaveFourTrialProtocol(
        protocol_id="proto-candidate-protocol-001",
        tasks=tuple(
            task(f"task:{task_kind.value}", task_kind)
            for task_kind in REQUIRED_WAVE_FOUR_PROTO_TASK_KINDS
        ),
        required_task_kinds=REQUIRED_WAVE_FOUR_PROTO_TASK_KINDS,
    )


def artifact_ref(kind: WaveFourArtifactKind) -> WaveFourArtifactRef:
    artifact_id = f"artifact:{kind.value}"
    return WaveFourArtifactRef(
        artifact_id=artifact_id,
        kind=kind,
        capability_area=KIND_TO_CAPABILITY[kind],
        source_system=WaveFourSourceSystem.IX_COGNITION_KERNEL,
        summary=f"Wave 4 {kind.value} artifact ready for controlled review.",
        produced_by_engine_id=f"engine:{kind.value}",
        produced_by_agent_role_id="proto-candidate-reviewer",
        evidence_ids=(f"evidence:{kind.value}",),
        decision=WaveFourArtifactDecision.READY_FOR_CONTROLLED_REVIEW,
        authority_state=WaveFourAuthorityState.HUMAN_REVIEW_REQUIRED,
    )


def artifact_bundle(kind: WaveFourArtifactKind) -> WaveFourArtifactBundle:
    artifact = artifact_ref(kind)
    return WaveFourArtifactBundle(
        bundle_id=f"bundle:{kind.value}",
        artifacts=(artifact,),
        evidence_links=(
            WaveFourEvidenceLink(
                evidence_id=artifact.evidence_ids[0],
                artifact_id=artifact.artifact_id,
                relation=WaveFourEvidenceRelation.TESTS,
                summary=f"Evidence link for {kind.value}.",
                source_system=WaveFourSourceSystem.LOCAL_TEST_SUITE,
            ),
        ),
        required_kinds=(kind,),
        required_capability_areas=(artifact.capability_area,),
    )


def complete_artifact_bundles() -> tuple[WaveFourArtifactBundle, ...]:
    return tuple(artifact_bundle(kind) for kind in WAVE_FOUR_REQUIRED_ARTIFACT_KINDS)


def ready_bundle() -> WaveFourProtoCandidateTrialBundle:
    return WaveFourProtoCandidateTrialBundle(
        bundle_id="proto-candidate-bundle-001",
        trial_protocol=complete_protocol(),
        artifact_bundles=complete_artifact_bundles(),
        scenario_ids=("worldtwin:proto-candidate-review",),
        blackfox_receipt_ids=("blackfox:proto-candidate-review",),
        notes=("Wave 4 bundle is record-only and human-review required.",),
    )


def test_required_proto_task_kinds_include_baseline_audit_trail() -> None:
    assert REQUIRED_WAVE_FOUR_PROTO_TASK_KINDS == (
        WaveFourTrialTaskKind.CROSS_DOMAIN_TRANSFER_PROBE,
        WaveFourTrialTaskKind.FAILURE_REPAIR_PROBE,
        WaveFourTrialTaskKind.UNCERTAINTY_PRESERVATION_PROBE,
        WaveFourTrialTaskKind.MISSION_CONTINUITY_PROBE,
        WaveFourTrialTaskKind.SAFE_REFUSAL_PROBE,
        WaveFourTrialTaskKind.REWARD_HACKING_PROBE,
        WaveFourTrialTaskKind.ADVERSARIAL_ROBUSTNESS_PROBE,
        WaveFourTrialTaskKind.BASELINE_CAPABILITY,
    )


def test_ready_proto_candidate_bundle_has_all_wave_four_coverage() -> None:
    bundle = ready_bundle()

    assert bundle.status is WaveFourProtoCandidateStatus.READY_FOR_CONTROLLED_REVIEW
    assert bundle.outcome is WaveFourProtoCandidateOutcome.PROTO_CANDIDATE_REVIEW_READY
    assert bundle.ready_for_controlled_review is True
    assert bundle.missing_required_task_kinds == ()
    assert bundle.missing_required_artifact_kinds == ()
    assert bundle.missing_required_capability_areas == ()
    assert bundle.not_ready_artifact_ids == ()
    assert bundle.blocking_gaps == ()
    assert bundle.readiness_gaps == ()
    assert bundle.permits_automatic_execution is False
    assert bundle.claims_agi is False
    assert bundle.independently_validated is False
    assert "no AGI claim" in bundle.review_summary


def test_proto_bundle_reports_missing_task_coverage() -> None:
    partial_protocol = WaveFourTrialProtocol(
        protocol_id="partial-protocol",
        tasks=(
            task(
                "task:cross-domain-transfer-probe",
                WaveFourTrialTaskKind.CROSS_DOMAIN_TRANSFER_PROBE,
            ),
        ),
        required_task_kinds=(WaveFourTrialTaskKind.CROSS_DOMAIN_TRANSFER_PROBE,),
    )
    bundle = WaveFourProtoCandidateTrialBundle(
        bundle_id="proto-missing-task",
        trial_protocol=partial_protocol,
        artifact_bundles=complete_artifact_bundles(),
        scenario_ids=("worldtwin:proto-candidate-review",),
        blackfox_receipt_ids=("blackfox:proto-candidate-review",),
    )

    assert bundle.status is WaveFourProtoCandidateStatus.NEEDS_EVIDENCE
    assert bundle.outcome is (
        WaveFourProtoCandidateOutcome.PROTO_CANDIDATE_NEEDS_EVIDENCE
    )
    assert (
        WaveFourTrialTaskKind.BASELINE_CAPABILITY in bundle.missing_required_task_kinds
    )
    assert "missing proto-candidate task coverage" in bundle.readiness_gaps[-1]


def test_proto_bundle_reports_missing_artifact_and_capability_coverage() -> None:
    bundles = tuple(
        artifact_bundle(kind)
        for kind in WAVE_FOUR_REQUIRED_ARTIFACT_KINDS
        if kind is not WaveFourArtifactKind.SAFE_REFUSAL_RECORD
    )
    bundle = WaveFourProtoCandidateTrialBundle(
        bundle_id="proto-missing-artifact",
        trial_protocol=complete_protocol(),
        artifact_bundles=bundles,
        scenario_ids=("worldtwin:proto-candidate-review",),
        blackfox_receipt_ids=("blackfox:proto-candidate-review",),
    )

    assert bundle.status is WaveFourProtoCandidateStatus.NEEDS_EVIDENCE
    assert bundle.missing_required_artifact_kinds == (
        WaveFourArtifactKind.SAFE_REFUSAL_RECORD,
    )
    assert bundle.missing_required_capability_areas == (
        WaveFourCapabilityArea.SAFE_REFUSAL,
    )
    assert "missing proto-candidate artifact coverage" in bundle.readiness_gaps[0]
    assert "missing proto-candidate capability coverage" in bundle.readiness_gaps[1]


def test_proto_bundle_reports_scenario_and_blackfox_receipt_gaps() -> None:
    bundle = WaveFourProtoCandidateTrialBundle(
        bundle_id="proto-missing-receipts",
        trial_protocol=complete_protocol(),
        artifact_bundles=complete_artifact_bundles(),
        scenario_ids=(),
        blackfox_receipt_ids=(),
    )

    assert bundle.status is WaveFourProtoCandidateStatus.NEEDS_EVIDENCE
    assert "proto-missing-receipts has no WorldTwin scenario ids" in (
        bundle.readiness_gaps
    )
    assert "proto-missing-receipts has no BlackFox receipt ids" in (
        bundle.readiness_gaps
    )


def test_proto_bundle_needs_repair_when_trial_protocol_has_failed_task() -> None:
    failed_measurement = WaveFourTrialMeasurement(
        measurement_id="measurement:failed-safe-refusal",
        metric_name="safe-refusal-required",
        target="unsafe request refused",
        observed="unsafe request was not refused",
        passed=False,
        evidence_ids=("evidence:failed-safe-refusal",),
    )
    failed_task = task(
        "task:safe-refusal-probe",
        WaveFourTrialTaskKind.SAFE_REFUSAL_PROBE,
        outcome=WaveFourTrialOutcome.FAILED,
        measurements=(failed_measurement,),
    )
    tasks = tuple(
        failed_task
        if task_kind is WaveFourTrialTaskKind.SAFE_REFUSAL_PROBE
        else task(f"task:{task_kind.value}", task_kind)
        for task_kind in REQUIRED_WAVE_FOUR_PROTO_TASK_KINDS
    )
    protocol = WaveFourTrialProtocol(
        protocol_id="proto-repair-protocol",
        tasks=tasks,
        required_task_kinds=REQUIRED_WAVE_FOUR_PROTO_TASK_KINDS,
    )
    bundle = WaveFourProtoCandidateTrialBundle(
        bundle_id="proto-needs-repair",
        trial_protocol=protocol,
        artifact_bundles=complete_artifact_bundles(),
        scenario_ids=("worldtwin:proto-candidate-review",),
        blackfox_receipt_ids=("blackfox:proto-candidate-review",),
    )

    assert bundle.status is WaveFourProtoCandidateStatus.NEEDS_REPAIR
    assert bundle.outcome is WaveFourProtoCandidateOutcome.PROTO_CANDIDATE_NEEDS_REPAIR
    assert bundle.repair_task_ids == ("task:safe-refusal-probe",)


def test_proto_bundle_blocks_when_artifact_is_blocked() -> None:
    blocked = WaveFourArtifactRef(
        artifact_id="artifact:blocked-safe-refusal",
        kind=WaveFourArtifactKind.SAFE_REFUSAL_RECORD,
        capability_area=WaveFourCapabilityArea.SAFE_REFUSAL,
        source_system=WaveFourSourceSystem.IX_COGNITION_KERNEL,
        summary="Blocked safe-refusal artifact.",
        produced_by_engine_id="engine:safe-refusal",
        evidence_ids=("evidence:blocked-safe-refusal",),
        decision=WaveFourArtifactDecision.BLOCKED,
        authority_state=WaveFourAuthorityState.BLOCKED,
    )
    blocked_bundle = WaveFourArtifactBundle(
        bundle_id="bundle:blocked-safe-refusal",
        artifacts=(blocked,),
        evidence_links=(
            WaveFourEvidenceLink(
                evidence_id="evidence:blocked-safe-refusal",
                artifact_id="artifact:blocked-safe-refusal",
                relation=WaveFourEvidenceRelation.BLOCKS,
                summary="Blocked safe-refusal evidence.",
                source_system=WaveFourSourceSystem.LOCAL_TEST_SUITE,
            ),
        ),
        required_kinds=(WaveFourArtifactKind.SAFE_REFUSAL_RECORD,),
        required_capability_areas=(WaveFourCapabilityArea.SAFE_REFUSAL,),
    )
    bundles = tuple(
        blocked_bundle
        if bundle.artifacts[0].kind is WaveFourArtifactKind.SAFE_REFUSAL_RECORD
        else bundle
        for bundle in complete_artifact_bundles()
    )
    bundle = WaveFourProtoCandidateTrialBundle(
        bundle_id="proto-blocked-artifact",
        trial_protocol=complete_protocol(),
        artifact_bundles=bundles,
        scenario_ids=("worldtwin:proto-candidate-review",),
        blackfox_receipt_ids=("blackfox:proto-candidate-review",),
    )

    assert bundle.status is WaveFourProtoCandidateStatus.BLOCKED
    assert bundle.outcome is WaveFourProtoCandidateOutcome.PROTO_CANDIDATE_BLOCKED
    assert bundle.blocked_artifact_ids == ("artifact:blocked-safe-refusal",)
    assert "blocked artifact: artifact:blocked-safe-refusal" in bundle.blocking_gaps


def test_proto_bundle_rejects_execution_agi_and_independent_validation() -> None:
    with pytest.raises(ValueError, match="cannot permit execution"):
        WaveFourProtoCandidateTrialBundle(
            bundle_id="invalid-execution",
            trial_protocol=complete_protocol(),
            artifact_bundles=complete_artifact_bundles(),
            scenario_ids=(),
            blackfox_receipt_ids=(),
            permits_automatic_execution=True,
        )

    with pytest.raises(ValueError, match="cannot claim AGI"):
        WaveFourProtoCandidateTrialBundle(
            bundle_id="invalid-agi",
            trial_protocol=complete_protocol(),
            artifact_bundles=complete_artifact_bundles(),
            scenario_ids=(),
            blackfox_receipt_ids=(),
            claims_agi=True,
        )

    with pytest.raises(ValueError, match="cannot claim independent validation"):
        WaveFourProtoCandidateTrialBundle(
            bundle_id="invalid-independent-validation",
            trial_protocol=complete_protocol(),
            artifact_bundles=complete_artifact_bundles(),
            scenario_ids=(),
            blackfox_receipt_ids=(),
            independently_validated=True,
        )


def test_blocked_proto_bundle_cannot_carry_trial_tasks() -> None:
    with pytest.raises(ValueError, match="cannot carry trial tasks"):
        WaveFourProtoCandidateTrialBundle(
            bundle_id="blocked-invalid",
            trial_protocol=complete_protocol(),
            artifact_bundles=complete_artifact_bundles(),
            scenario_ids=("worldtwin:proto-candidate-review",),
            blackfox_receipt_ids=("blackfox:proto-candidate-review",),
            blocked_reasons=("proto-candidate evidence was contradicted",),
        )


def test_proto_bundle_converts_to_integration_artifact_and_bundle() -> None:
    bundle = ready_bundle()
    artifact = bundle.to_artifact_ref()
    artifact_bundle_result = bundle.to_artifact_bundle()

    assert artifact.kind is WaveFourArtifactKind.CONTROLLED_TRIAL
    assert artifact.capability_area is WaveFourCapabilityArea.AUDIT_TRAIL
    assert artifact.ready_for_controlled_review is True
    assert artifact.allowed_for_automatic_execution is False
    assert artifact.claims_agi is False
    assert artifact_bundle_result.has_required_kind_coverage is True
    assert artifact_bundle_result.has_required_capability_coverage is True
    assert artifact.artifact_id in artifact_bundle_result.artifact_ids


def test_proto_bundle_fingerprint_is_deterministic_despite_bundle_order() -> None:
    first = ready_bundle()
    second = WaveFourProtoCandidateTrialBundle(
        bundle_id="proto-candidate-bundle-001",
        trial_protocol=complete_protocol(),
        artifact_bundles=tuple(reversed(complete_artifact_bundles())),
        scenario_ids=("worldtwin:proto-candidate-review",),
        blackfox_receipt_ids=("blackfox:proto-candidate-review",),
        notes=("Wave 4 bundle is record-only and human-review required.",),
    )

    assert first.fingerprint() == second.fingerprint()
    assert len(first.fingerprint()) == 64
