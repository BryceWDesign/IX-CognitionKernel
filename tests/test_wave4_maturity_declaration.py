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
from ix_cognition_kernel.wave4_maturity_declaration import (
    REQUIRED_WAVE_FOUR_MATURITY_BOUNDARIES,
    WaveFourMaturityBoundaryCheck,
    WaveFourMaturityBoundaryKind,
    WaveFourMaturityDeclaration,
    WaveFourMaturityDeclarationDecision,
    WaveFourMaturityDeclarationStatus,
    build_wave_four_maturity_declaration,
)
from ix_cognition_kernel.wave4_proto_candidate import (
    REQUIRED_WAVE_FOUR_PROTO_TASK_KINDS,
    WaveFourProtoCandidateTrialBundle,
)
from ix_cognition_kernel.wave4_review_packet import (
    WaveFourHumanReviewDecision,
    WaveFourHumanReviewPacket,
    WaveFourHumanReviewPacketStatus,
    build_wave_four_human_review_packet,
)
from ix_cognition_kernel.wave4_scorecard import (
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


def measurement(task_id: str) -> WaveFourTrialMeasurement:
    return WaveFourTrialMeasurement(
        measurement_id=f"measurement:{task_id}",
        metric_name="maturity-declaration-controlled-task-check",
        target="task evidence remains attached and reviewable",
        observed="task evidence remained attached and reviewable",
        passed=True,
        evidence_ids=(f"evidence:measurement:{task_id}",),
    )


def task(
    task_id: str,
    task_kind: WaveFourTrialTaskKind,
) -> WaveFourControlledTask:
    scenario_ids: tuple[str, ...] = ()
    if task_kind is not WaveFourTrialTaskKind.BASELINE_CAPABILITY:
        scenario_ids = (f"worldtwin:{task_id}",)
    return WaveFourControlledTask(
        task_id=task_id,
        task_kind=task_kind,
        objective="Verify a Wave 4 declaration behavior under review.",
        input_domain="maturity declaration integration",
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
        outcome=WaveFourTrialOutcome.PASSED,
        evidence_ids=(f"evidence:{task_id}",),
        measurements=(measurement(task_id),),
        scenario_ids=scenario_ids,
        blackfox_receipt_ids=(f"blackfox:{task_id}",),
    )


def complete_protocol() -> WaveFourTrialProtocol:
    return WaveFourTrialProtocol(
        protocol_id="maturity-declaration-protocol-001",
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
        summary=f"Wave 4 {kind.value} artifact for declaration review.",
        produced_by_engine_id=f"engine:{kind.value}",
        produced_by_agent_role_id="maturity-declaration-reviewer",
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


def proto_bundle(
    *,
    scenario_ids: tuple[str, ...] = ("worldtwin:maturity-declaration",),
    blackfox_receipt_ids: tuple[str, ...] = ("blackfox:maturity-declaration",),
) -> WaveFourProtoCandidateTrialBundle:
    return WaveFourProtoCandidateTrialBundle(
        bundle_id="proto-maturity-declaration-bundle-001",
        trial_protocol=complete_protocol(),
        artifact_bundles=tuple(
            artifact_bundle(kind) for kind in WAVE_FOUR_REQUIRED_ARTIFACT_KINDS
        ),
        scenario_ids=scenario_ids,
        blackfox_receipt_ids=blackfox_receipt_ids,
    )


def ready_packet() -> WaveFourHumanReviewPacket:
    scorecard = build_wave_four_proto_candidate_scorecard(
        scorecard_id="scorecard-maturity-declaration-001",
        proto_candidate_bundle=proto_bundle(),
    )
    return build_wave_four_human_review_packet(
        packet_id="review-packet-maturity-declaration-001",
        scorecard=scorecard,
    )


def ready_declaration() -> WaveFourMaturityDeclaration:
    return build_wave_four_maturity_declaration(
        declaration_id="maturity-declaration-001",
        review_packet=ready_packet(),
    )


def test_required_maturity_boundaries_are_locked() -> None:
    assert REQUIRED_WAVE_FOUR_MATURITY_BOUNDARIES == (
        WaveFourMaturityBoundaryKind.REVIEW_PACKET_READY,
        WaveFourMaturityBoundaryKind.EVIDENCE_BOUND,
        WaveFourMaturityBoundaryKind.HUMAN_REVIEW_REQUIRED,
        WaveFourMaturityBoundaryKind.NO_AUTOMATIC_EXECUTION,
        WaveFourMaturityBoundaryKind.NO_AUTOMATIC_PROMOTION,
        WaveFourMaturityBoundaryKind.NO_AGI_CLAIM,
        WaveFourMaturityBoundaryKind.NO_INDEPENDENT_VALIDATION_CLAIM,
        WaveFourMaturityBoundaryKind.NO_PRODUCTION_CLAIM,
    )


def test_boundary_check_requires_failure_text_when_failed() -> None:
    with pytest.raises(ValueError, match="require failure text"):
        WaveFourMaturityBoundaryCheck(
            check_id="boundary:invalid",
            boundary_kind=WaveFourMaturityBoundaryKind.NO_AGI_CLAIM,
            passed=False,
            summary="Invalid failed boundary without failure text.",
        )

    with pytest.raises(ValueError, match="cannot carry failure text"):
        WaveFourMaturityBoundaryCheck(
            check_id="boundary:invalid",
            boundary_kind=WaveFourMaturityBoundaryKind.NO_AGI_CLAIM,
            passed=True,
            summary="Invalid passed boundary with failure text.",
            failure_summary="should not exist",
        )


def test_ready_maturity_declaration_is_review_only_without_overclaim() -> None:
    declaration = ready_declaration()

    assert declaration.status is (
        WaveFourMaturityDeclarationStatus.DECLARABLE_FOR_HUMAN_REVIEW
    )
    assert declaration.decision is (
        WaveFourMaturityDeclarationDecision.DECLARE_WAVE_FOUR_REVIEW_READY
    )
    assert declaration.declarable_for_human_review is True
    assert declaration.missing_required_boundary_kinds == ()
    assert declaration.failed_boundary_ids == ()
    assert declaration.readiness_gaps == ()
    assert declaration.blocking_gaps == ()
    assert declaration.permits_automatic_execution is False
    assert declaration.permits_automatic_promotion is False
    assert declaration.claims_agi is False
    assert declaration.independently_validated is False
    assert declaration.production_ready is False
    assert "human review only; no AGI claim" in declaration.review_summary


def test_maturity_declaration_holds_when_packet_needs_evidence() -> None:
    scorecard = build_wave_four_proto_candidate_scorecard(
        scorecard_id="scorecard-missing-scenario",
        proto_candidate_bundle=proto_bundle(scenario_ids=(), blackfox_receipt_ids=()),
    )
    packet = build_wave_four_human_review_packet(
        packet_id="review-packet-missing-scenario",
        scorecard=scorecard,
    )
    declaration = build_wave_four_maturity_declaration(
        declaration_id="declaration-missing-evidence",
        review_packet=packet,
    )

    assert packet.status is WaveFourHumanReviewPacketStatus.NEEDS_EVIDENCE
    assert packet.decision is WaveFourHumanReviewDecision.HOLD_FOR_EVIDENCE
    assert declaration.status is WaveFourMaturityDeclarationStatus.NEEDS_REPAIR
    assert declaration.decision is WaveFourMaturityDeclarationDecision.HOLD_FOR_REPAIR
    assert "boundary:review-packet-ready" in declaration.failed_boundary_ids


def test_maturity_declaration_reports_missing_boundary_coverage() -> None:
    check = WaveFourMaturityBoundaryCheck(
        check_id="boundary:evidence-bound",
        boundary_kind=WaveFourMaturityBoundaryKind.EVIDENCE_BOUND,
        passed=True,
        summary="Evidence is present.",
    )
    declaration = WaveFourMaturityDeclaration(
        declaration_id="declaration-incomplete",
        review_packet=ready_packet(),
        boundary_checks=(check,),
    )

    assert declaration.status is WaveFourMaturityDeclarationStatus.NEEDS_EVIDENCE
    assert WaveFourMaturityBoundaryKind.REVIEW_PACKET_READY in (
        declaration.missing_required_boundary_kinds
    )
    assert "missing maturity boundary coverage" in declaration.readiness_gaps[0]


def test_failed_boundary_causes_repair_hold() -> None:
    declaration = WaveFourMaturityDeclaration(
        declaration_id="declaration-failed-boundary",
        review_packet=ready_packet(),
        boundary_checks=(
            *ready_declaration().boundary_checks,
            WaveFourMaturityBoundaryCheck(
                check_id="boundary:manual-failure",
                boundary_kind=WaveFourMaturityBoundaryKind.NO_PRODUCTION_CLAIM,
                passed=False,
                summary="Manual negative-control boundary.",
                failure_summary="production readiness language was detected",
            ),
        ),
    )

    assert declaration.status is WaveFourMaturityDeclarationStatus.NEEDS_REPAIR
    assert declaration.decision is WaveFourMaturityDeclarationDecision.HOLD_FOR_REPAIR
    assert "boundary:manual-failure" in declaration.failed_boundary_ids


def test_blocked_declaration_blocks_even_with_ready_packet() -> None:
    declaration = WaveFourMaturityDeclaration(
        declaration_id="declaration-blocked",
        review_packet=ready_packet(),
        boundary_checks=ready_declaration().boundary_checks,
        blocked_reasons=("maturity declaration evidence was contradicted",),
    )

    assert declaration.status is WaveFourMaturityDeclarationStatus.BLOCKED
    assert declaration.decision is WaveFourMaturityDeclarationDecision.BLOCK_DECLARATION
    assert declaration.blocking_gaps == (
        "declaration-blocked blocked: maturity declaration evidence was contradicted",
    )


def test_declaration_rejects_execution_promotion_agi_validation_and_production() -> (
    None
):
    checks = ready_declaration().boundary_checks
    packet = ready_packet()

    with pytest.raises(ValueError, match="cannot permit execution"):
        WaveFourMaturityDeclaration(
            declaration_id="invalid-execution",
            review_packet=packet,
            boundary_checks=checks,
            permits_automatic_execution=True,
        )

    with pytest.raises(ValueError, match="cannot permit promotion"):
        WaveFourMaturityDeclaration(
            declaration_id="invalid-promotion",
            review_packet=packet,
            boundary_checks=checks,
            permits_automatic_promotion=True,
        )

    with pytest.raises(ValueError, match="cannot claim AGI"):
        WaveFourMaturityDeclaration(
            declaration_id="invalid-agi",
            review_packet=packet,
            boundary_checks=checks,
            claims_agi=True,
        )

    with pytest.raises(ValueError, match="cannot claim independent validation"):
        WaveFourMaturityDeclaration(
            declaration_id="invalid-validation",
            review_packet=packet,
            boundary_checks=checks,
            independently_validated=True,
        )

    with pytest.raises(ValueError, match="cannot claim production readiness"):
        WaveFourMaturityDeclaration(
            declaration_id="invalid-production",
            review_packet=packet,
            boundary_checks=checks,
            production_ready=True,
        )


def test_declaration_converts_to_readiness_artifact_and_bundle() -> None:
    declaration = ready_declaration()
    artifact = declaration.to_artifact_ref()
    artifact_bundle_result = declaration.to_artifact_bundle()

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


def test_declaration_fingerprint_is_deterministic_despite_boundary_order() -> None:
    first = ready_declaration()
    second = WaveFourMaturityDeclaration(
        declaration_id="maturity-declaration-001",
        review_packet=ready_packet(),
        boundary_checks=tuple(reversed(first.boundary_checks)),
    )

    assert first.fingerprint() == second.fingerprint()
    assert len(first.fingerprint()) == 64
