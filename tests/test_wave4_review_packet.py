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
    WaveFourProtoCandidateTrialBundle,
)
from ix_cognition_kernel.wave4_review_packet import (
    REQUIRED_WAVE_FOUR_REVIEW_REQUIREMENT_KINDS,
    WaveFourHumanReviewDecision,
    WaveFourHumanReviewPacket,
    WaveFourHumanReviewPacketStatus,
    WaveFourReviewRequirement,
    WaveFourReviewRequirementKind,
    build_wave_four_human_review_packet,
)
from ix_cognition_kernel.wave4_scorecard import (
    WaveFourProtoCandidateScorecard,
    WaveFourScorecardGateSeverity,
    build_wave_four_proto_candidate_scorecard,
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


def measurement(task_id: str, *, passed: bool = True) -> WaveFourTrialMeasurement:
    return WaveFourTrialMeasurement(
        measurement_id=f"measurement:{task_id}",
        metric_name="review-packet-controlled-task-check",
        target="task evidence remains attached and reviewable",
        observed="task evidence remained attached" if passed else "task failed",
        passed=passed,
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
        objective="Verify a Wave 4 review-packet behavior under review.",
        input_domain="human-review packet integration",
        evaluation_prompt="Check behavior with evidence and authority preserved.",
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
        protocol_id="review-packet-protocol-001",
        tasks=tuple(
            task(f"task:{task_kind.value}", task_kind)
            for task_kind in REQUIRED_WAVE_FOUR_PROTO_TASK_KINDS
        ),
        required_task_kinds=REQUIRED_WAVE_FOUR_PROTO_TASK_KINDS,
    )


def artifact_ref(
    kind: WaveFourArtifactKind,
    *,
    decision: WaveFourArtifactDecision = (
        WaveFourArtifactDecision.READY_FOR_CONTROLLED_REVIEW
    ),
    authority_state: WaveFourAuthorityState = (
        WaveFourAuthorityState.HUMAN_REVIEW_REQUIRED
    ),
) -> WaveFourArtifactRef:
    artifact_id = f"artifact:{kind.value}"
    return WaveFourArtifactRef(
        artifact_id=artifact_id,
        kind=kind,
        capability_area=KIND_TO_CAPABILITY[kind],
        source_system=WaveFourSourceSystem.IX_COGNITION_KERNEL,
        summary=f"Wave 4 {kind.value} artifact for review-packet testing.",
        produced_by_engine_id=f"engine:{kind.value}",
        produced_by_agent_role_id="review-packet-tester",
        evidence_ids=(f"evidence:{kind.value}",),
        decision=decision,
        authority_state=authority_state,
    )


def artifact_bundle(
    kind: WaveFourArtifactKind,
    *,
    artifact: WaveFourArtifactRef | None = None,
) -> WaveFourArtifactBundle:
    item = artifact_ref(kind) if artifact is None else artifact
    relation = WaveFourEvidenceRelation.TESTS
    if item.blocks_progress:
        relation = WaveFourEvidenceRelation.BLOCKS
    return WaveFourArtifactBundle(
        bundle_id=f"bundle:{kind.value}",
        artifacts=(item,),
        evidence_links=(
            WaveFourEvidenceLink(
                evidence_id=item.evidence_ids[0],
                artifact_id=item.artifact_id,
                relation=relation,
                summary=f"Evidence link for {kind.value}.",
                source_system=WaveFourSourceSystem.LOCAL_TEST_SUITE,
            ),
        ),
        required_kinds=(kind,),
        required_capability_areas=(item.capability_area,),
    )


def complete_artifact_bundles() -> tuple[WaveFourArtifactBundle, ...]:
    return tuple(artifact_bundle(kind) for kind in WAVE_FOUR_REQUIRED_ARTIFACT_KINDS)


def proto_bundle(
    *,
    protocol: WaveFourTrialProtocol | None = None,
    artifact_bundles: tuple[WaveFourArtifactBundle, ...] | None = None,
    scenario_ids: tuple[str, ...] = ("worldtwin:review-packet",),
    blackfox_receipt_ids: tuple[str, ...] = ("blackfox:review-packet",),
) -> WaveFourProtoCandidateTrialBundle:
    return WaveFourProtoCandidateTrialBundle(
        bundle_id="proto-review-packet-bundle-001",
        trial_protocol=complete_protocol() if protocol is None else protocol,
        artifact_bundles=(
            complete_artifact_bundles()
            if artifact_bundles is None
            else artifact_bundles
        ),
        scenario_ids=scenario_ids,
        blackfox_receipt_ids=blackfox_receipt_ids,
    )


def ready_scorecard() -> WaveFourProtoCandidateScorecard:
    return build_wave_four_proto_candidate_scorecard(
        scorecard_id="scorecard-review-packet-001",
        proto_candidate_bundle=proto_bundle(),
    )


def ready_packet() -> WaveFourHumanReviewPacket:
    return build_wave_four_human_review_packet(
        packet_id="review-packet-001",
        scorecard=ready_scorecard(),
    )


def test_required_review_requirement_kinds_are_locked() -> None:
    assert REQUIRED_WAVE_FOUR_REVIEW_REQUIREMENT_KINDS == (
        WaveFourReviewRequirementKind.SCORECARD_READY,
        WaveFourReviewRequirementKind.EVIDENCE_TRACEABLE,
        WaveFourReviewRequirementKind.SCENARIO_CONTEXT_ATTACHED,
        WaveFourReviewRequirementKind.BLACKFOX_RECEIPTS_ATTACHED,
        WaveFourReviewRequirementKind.HUMAN_AUTHORITY_PRESERVED,
        WaveFourReviewRequirementKind.REVIEWER_ROLES_ASSIGNED,
        WaveFourReviewRequirementKind.NO_AUTOMATIC_PROMOTION,
        WaveFourReviewRequirementKind.NO_AUTOMATIC_EXECUTION,
        WaveFourReviewRequirementKind.NO_AGI_CLAIM,
        WaveFourReviewRequirementKind.NO_INDEPENDENT_VALIDATION_CLAIM,
    )


def test_review_requirement_requires_failure_text_when_failed() -> None:
    with pytest.raises(ValueError, match="require failure text"):
        WaveFourReviewRequirement(
            requirement_id="requirement:invalid",
            requirement_kind=WaveFourReviewRequirementKind.EVIDENCE_TRACEABLE,
            severity=WaveFourScorecardGateSeverity.EVIDENCE,
            passed=False,
            summary="Invalid failed requirement without text.",
        )

    with pytest.raises(ValueError, match="cannot carry failure text"):
        WaveFourReviewRequirement(
            requirement_id="requirement:invalid",
            requirement_kind=WaveFourReviewRequirementKind.EVIDENCE_TRACEABLE,
            severity=WaveFourScorecardGateSeverity.EVIDENCE,
            passed=True,
            summary="Invalid passed requirement with failure text.",
            failure_summary="should not exist",
        )


def test_ready_review_packet_submits_for_human_review_without_overclaim() -> None:
    packet = ready_packet()

    assert packet.status is WaveFourHumanReviewPacketStatus.READY_FOR_HUMAN_REVIEW
    assert packet.decision is WaveFourHumanReviewDecision.SUBMIT_FOR_HUMAN_REVIEW
    assert packet.ready_for_human_review is True
    assert packet.missing_required_requirement_kinds == ()
    assert packet.failed_requirement_ids == ()
    assert packet.readiness_gaps == ()
    assert packet.blocking_gaps == ()
    assert packet.permits_automatic_execution is False
    assert packet.permits_automatic_promotion is False
    assert packet.claims_agi is False
    assert packet.independently_validated is False
    assert "no automatic promotion; no AGI claim" in packet.review_summary


def test_review_packet_holds_for_evidence_when_reviewer_roles_are_missing() -> None:
    packet = build_wave_four_human_review_packet(
        packet_id="review-packet-no-reviewers",
        scorecard=ready_scorecard(),
        required_reviewer_role_ids=(),
    )

    assert packet.status is WaveFourHumanReviewPacketStatus.NEEDS_EVIDENCE
    assert packet.decision is WaveFourHumanReviewDecision.HOLD_FOR_EVIDENCE
    assert "requirement:reviewer-roles-assigned" in (
        packet.failed_evidence_requirement_ids
    )
    assert "review-packet-no-reviewers has no required reviewer roles" in (
        packet.readiness_gaps
    )


def test_review_packet_holds_for_evidence_when_scorecard_lacks_task_coverage() -> None:
    partial_protocol = WaveFourTrialProtocol(
        protocol_id="partial-review-packet-protocol",
        tasks=(
            task(
                "task:cross-domain-transfer-probe",
                WaveFourTrialTaskKind.CROSS_DOMAIN_TRANSFER_PROBE,
            ),
        ),
        required_task_kinds=(WaveFourTrialTaskKind.CROSS_DOMAIN_TRANSFER_PROBE,),
    )
    scorecard = build_wave_four_proto_candidate_scorecard(
        scorecard_id="scorecard-missing-task",
        proto_candidate_bundle=proto_bundle(protocol=partial_protocol),
    )
    packet = build_wave_four_human_review_packet(
        packet_id="review-packet-missing-task",
        scorecard=scorecard,
    )

    assert packet.status is WaveFourHumanReviewPacketStatus.NEEDS_EVIDENCE
    assert packet.decision is WaveFourHumanReviewDecision.HOLD_FOR_EVIDENCE
    assert "requirement:scorecard-ready" in packet.failed_evidence_requirement_ids
    assert any("missing task kinds" in gap for gap in packet.readiness_gaps)


def test_review_packet_holds_for_repair_when_scorecard_needs_repair() -> None:
    failed_measurement = measurement("task:safe-refusal-probe", passed=False)
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
        protocol_id="repair-review-packet-protocol",
        tasks=tasks,
        required_task_kinds=REQUIRED_WAVE_FOUR_PROTO_TASK_KINDS,
    )
    scorecard = build_wave_four_proto_candidate_scorecard(
        scorecard_id="scorecard-needs-repair",
        proto_candidate_bundle=proto_bundle(protocol=protocol),
    )
    packet = build_wave_four_human_review_packet(
        packet_id="review-packet-needs-repair",
        scorecard=scorecard,
    )

    assert packet.status is WaveFourHumanReviewPacketStatus.NEEDS_REPAIR
    assert packet.decision is WaveFourHumanReviewDecision.HOLD_FOR_REPAIR
    assert "requirement:scorecard-ready" in packet.failed_repair_requirement_ids


def test_review_packet_blocks_when_scorecard_blocks() -> None:
    blocked_artifact = artifact_ref(
        WaveFourArtifactKind.SAFE_REFUSAL_RECORD,
        decision=WaveFourArtifactDecision.BLOCKED,
        authority_state=WaveFourAuthorityState.BLOCKED,
    )
    bundles = tuple(
        artifact_bundle(
            WaveFourArtifactKind.SAFE_REFUSAL_RECORD,
            artifact=blocked_artifact,
        )
        if bundle.artifacts[0].kind is WaveFourArtifactKind.SAFE_REFUSAL_RECORD
        else bundle
        for bundle in complete_artifact_bundles()
    )
    scorecard = build_wave_four_proto_candidate_scorecard(
        scorecard_id="scorecard-blocked",
        proto_candidate_bundle=proto_bundle(artifact_bundles=bundles),
    )
    packet = build_wave_four_human_review_packet(
        packet_id="review-packet-blocked",
        scorecard=scorecard,
    )

    assert packet.status is WaveFourHumanReviewPacketStatus.BLOCKED
    assert packet.decision is WaveFourHumanReviewDecision.BLOCK_REVIEW
    assert "requirement:scorecard-ready" in packet.failed_blocking_requirement_ids
    assert packet.blocking_gaps


def test_review_packet_reports_missing_scenarios_and_receipts() -> None:
    scorecard = build_wave_four_proto_candidate_scorecard(
        scorecard_id="scorecard-gaps",
        proto_candidate_bundle=proto_bundle(
            scenario_ids=(),
            blackfox_receipt_ids=(),
        ),
    )
    packet = build_wave_four_human_review_packet(
        packet_id="review-packet-gaps",
        scorecard=scorecard,
    )

    assert packet.status is WaveFourHumanReviewPacketStatus.NEEDS_EVIDENCE
    assert "requirement:scenario-context-attached" in (
        packet.failed_evidence_requirement_ids
    )
    assert "requirement:blackfox-receipts-attached" in (
        packet.failed_evidence_requirement_ids
    )
    assert "review-packet-gaps has no WorldTwin scenario ids" in packet.readiness_gaps
    assert "review-packet-gaps has no BlackFox receipt ids" in packet.readiness_gaps


def test_review_packet_rejects_execution_promotion_agi_and_validation_claims() -> None:
    packet = ready_packet()

    with pytest.raises(ValueError, match="cannot permit execution"):
        WaveFourHumanReviewPacket(
            packet_id="invalid-execution",
            scorecard=ready_scorecard(),
            requirements=packet.requirements,
            required_reviewer_role_ids=packet.required_reviewer_role_ids,
            scenario_ids=packet.scenario_ids,
            blackfox_receipt_ids=packet.blackfox_receipt_ids,
            permits_automatic_execution=True,
        )

    with pytest.raises(ValueError, match="cannot permit promotion"):
        WaveFourHumanReviewPacket(
            packet_id="invalid-promotion",
            scorecard=ready_scorecard(),
            requirements=packet.requirements,
            required_reviewer_role_ids=packet.required_reviewer_role_ids,
            scenario_ids=packet.scenario_ids,
            blackfox_receipt_ids=packet.blackfox_receipt_ids,
            permits_automatic_promotion=True,
        )

    with pytest.raises(ValueError, match="cannot claim AGI"):
        WaveFourHumanReviewPacket(
            packet_id="invalid-agi",
            scorecard=ready_scorecard(),
            requirements=packet.requirements,
            required_reviewer_role_ids=packet.required_reviewer_role_ids,
            scenario_ids=packet.scenario_ids,
            blackfox_receipt_ids=packet.blackfox_receipt_ids,
            claims_agi=True,
        )

    with pytest.raises(ValueError, match="cannot claim independent validation"):
        WaveFourHumanReviewPacket(
            packet_id="invalid-validation",
            scorecard=ready_scorecard(),
            requirements=packet.requirements,
            required_reviewer_role_ids=packet.required_reviewer_role_ids,
            scenario_ids=packet.scenario_ids,
            blackfox_receipt_ids=packet.blackfox_receipt_ids,
            independently_validated=True,
        )


def test_review_packet_converts_to_readiness_artifact_and_bundle() -> None:
    packet = ready_packet()
    artifact = packet.to_artifact_ref()
    artifact_bundle_result = packet.to_artifact_bundle()

    assert artifact.kind is WaveFourArtifactKind.READINESS_SNAPSHOT
    assert artifact.capability_area is WaveFourCapabilityArea.AUDIT_TRAIL
    assert artifact.ready_for_controlled_review is True
    assert artifact.allowed_for_automatic_execution is False
    assert artifact.claims_agi is False
    assert artifact_bundle_result.has_required_kind_coverage is True
    assert artifact_bundle_result.has_required_capability_coverage is True
    assert artifact_bundle_result.ready_for_controlled_review_artifact_ids == (
        artifact.artifact_id,
    )


def test_review_packet_fingerprint_is_deterministic_despite_requirement_order() -> None:
    first = ready_packet()
    second = WaveFourHumanReviewPacket(
        packet_id="review-packet-001",
        scorecard=ready_scorecard(),
        requirements=tuple(reversed(first.requirements)),
        required_reviewer_role_ids=first.required_reviewer_role_ids,
        scenario_ids=first.scenario_ids,
        blackfox_receipt_ids=first.blackfox_receipt_ids,
    )

    assert first.fingerprint() == second.fingerprint()
    assert len(first.fingerprint()) == 64
