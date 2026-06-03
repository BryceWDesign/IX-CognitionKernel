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
from ix_cognition_kernel.wave4_scorecard import (
    REQUIRED_WAVE_FOUR_SCORECARD_GATE_KINDS,
    WaveFourProtoCandidateScorecard,
    WaveFourScorecardDecision,
    WaveFourScorecardGate,
    WaveFourScorecardGateKind,
    WaveFourScorecardGateSeverity,
    WaveFourScorecardStatus,
    build_wave_four_proto_candidate_scorecard,
)
from ix_cognition_kernel.wave4_trials import (
    WaveFourControlledTask,
    WaveFourTrialMeasurement,
    WaveFourTrialOutcome,
    WaveFourTrialProtocol,
    WaveFourTrialStatus,
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
        metric_name="scorecard-controlled-task-check",
        target="task evidence remains attached and reviewable",
        observed="task evidence remained attached" if passed else "evidence failed",
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
        objective="Verify a Wave 4 scorecard behavior under review.",
        input_domain="scorecard integration",
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
        protocol_id="scorecard-protocol-001",
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
        summary=f"Wave 4 {kind.value} artifact for scorecard review.",
        produced_by_engine_id=f"engine:{kind.value}",
        produced_by_agent_role_id="scorecard-reviewer",
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


def ready_bundle() -> WaveFourProtoCandidateTrialBundle:
    return WaveFourProtoCandidateTrialBundle(
        bundle_id="proto-scorecard-bundle-001",
        trial_protocol=complete_protocol(),
        artifact_bundles=complete_artifact_bundles(),
        scenario_ids=("worldtwin:scorecard-review",),
        blackfox_receipt_ids=("blackfox:scorecard-review",),
    )


def test_required_scorecard_gate_kinds_are_locked() -> None:
    assert REQUIRED_WAVE_FOUR_SCORECARD_GATE_KINDS == (
        WaveFourScorecardGateKind.PROTOCOL_STATUS,
        WaveFourScorecardGateKind.TASK_COVERAGE,
        WaveFourScorecardGateKind.ARTIFACT_COVERAGE,
        WaveFourScorecardGateKind.CAPABILITY_COVERAGE,
        WaveFourScorecardGateKind.ARTIFACT_READINESS,
        WaveFourScorecardGateKind.EVIDENCE_BINDING,
        WaveFourScorecardGateKind.SCENARIO_COVERAGE,
        WaveFourScorecardGateKind.BLACKFOX_RECEIPT_COVERAGE,
        WaveFourScorecardGateKind.HUMAN_AUTHORITY_PRESERVED,
        WaveFourScorecardGateKind.ANTI_OVERCLAIM_BOUNDARY,
        WaveFourScorecardGateKind.NO_AUTOMATIC_EXECUTION,
    )


def test_scorecard_gate_requires_failure_text_when_failed() -> None:
    with pytest.raises(ValueError, match="Failed Wave 4 scorecard gates require"):
        WaveFourScorecardGate(
            gate_id="gate:invalid",
            gate_kind=WaveFourScorecardGateKind.EVIDENCE_BINDING,
            severity=WaveFourScorecardGateSeverity.EVIDENCE,
            passed=False,
            summary="Invalid gate without failure text.",
        )

    with pytest.raises(ValueError, match="Passed Wave 4 scorecard gates cannot"):
        WaveFourScorecardGate(
            gate_id="gate:invalid",
            gate_kind=WaveFourScorecardGateKind.EVIDENCE_BINDING,
            severity=WaveFourScorecardGateSeverity.EVIDENCE,
            passed=True,
            summary="Invalid gate with failure text.",
            failure_summary="should not be here",
        )


def test_ready_scorecard_allows_controlled_review_without_overclaim() -> None:
    scorecard = build_wave_four_proto_candidate_scorecard(
        scorecard_id="scorecard-001",
        proto_candidate_bundle=ready_bundle(),
    )

    assert scorecard.status is WaveFourScorecardStatus.READY_FOR_CONTROLLED_REVIEW
    assert scorecard.decision is WaveFourScorecardDecision.ALLOW_CONTROLLED_REVIEW
    assert scorecard.ready_for_controlled_review is True
    assert scorecard.passing_score == 1.0
    assert scorecard.failed_gate_ids == ()
    assert scorecard.missing_required_gate_kinds == ()
    assert scorecard.readiness_gaps == ()
    assert scorecard.blocking_gaps == ()
    assert scorecard.permits_automatic_execution is False
    assert scorecard.claims_agi is False
    assert scorecard.independently_validated is False
    assert "no AGI claim" in scorecard.review_summary


def test_scorecard_holds_for_evidence_when_task_coverage_is_missing() -> None:
    partial_protocol = WaveFourTrialProtocol(
        protocol_id="partial-scorecard-protocol",
        tasks=(
            task(
                "task:cross-domain-transfer-probe",
                WaveFourTrialTaskKind.CROSS_DOMAIN_TRANSFER_PROBE,
            ),
        ),
        required_task_kinds=(WaveFourTrialTaskKind.CROSS_DOMAIN_TRANSFER_PROBE,),
    )
    bundle = WaveFourProtoCandidateTrialBundle(
        bundle_id="proto-scorecard-missing-task",
        trial_protocol=partial_protocol,
        artifact_bundles=complete_artifact_bundles(),
        scenario_ids=("worldtwin:scorecard-review",),
        blackfox_receipt_ids=("blackfox:scorecard-review",),
    )
    scorecard = build_wave_four_proto_candidate_scorecard(
        scorecard_id="scorecard-missing-task",
        proto_candidate_bundle=bundle,
    )

    assert scorecard.status is WaveFourScorecardStatus.NEEDS_EVIDENCE
    assert scorecard.decision is WaveFourScorecardDecision.HOLD_FOR_EVIDENCE
    assert "gate:task-coverage" in scorecard.failed_evidence_gate_ids
    assert "missing task kinds" in scorecard.gate_by_id(
        "gate:task-coverage"
    ).failure_summary


def test_scorecard_holds_for_repair_when_protocol_task_fails() -> None:
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
        protocol_id="scorecard-repair-protocol",
        tasks=tasks,
        required_task_kinds=REQUIRED_WAVE_FOUR_PROTO_TASK_KINDS,
    )
    bundle = WaveFourProtoCandidateTrialBundle(
        bundle_id="proto-scorecard-needs-repair",
        trial_protocol=protocol,
        artifact_bundles=complete_artifact_bundles(),
        scenario_ids=("worldtwin:scorecard-review",),
        blackfox_receipt_ids=("blackfox:scorecard-review",),
    )
    scorecard = build_wave_four_proto_candidate_scorecard(
        scorecard_id="scorecard-needs-repair",
        proto_candidate_bundle=bundle,
    )

    assert scorecard.status is WaveFourScorecardStatus.NEEDS_REPAIR
    assert scorecard.decision is WaveFourScorecardDecision.HOLD_FOR_REPAIR
    assert "gate:protocol-status" in scorecard.failed_repair_gate_ids
    assert scorecard.proto_candidate_bundle.trial_protocol.status is (
        WaveFourTrialStatus.NEEDS_REPAIR
    )


def test_scorecard_blocks_when_artifact_readiness_blocks() -> None:
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
    bundle = WaveFourProtoCandidateTrialBundle(
        bundle_id="proto-scorecard-blocked-artifact",
        trial_protocol=complete_protocol(),
        artifact_bundles=bundles,
        scenario_ids=("worldtwin:scorecard-review",),
        blackfox_receipt_ids=("blackfox:scorecard-review",),
    )
    scorecard = build_wave_four_proto_candidate_scorecard(
        scorecard_id="scorecard-blocked-artifact",
        proto_candidate_bundle=bundle,
    )

    assert scorecard.status is WaveFourScorecardStatus.BLOCKED
    assert scorecard.decision is WaveFourScorecardDecision.BLOCK_REVIEW
    assert "gate:artifact-readiness" in scorecard.failed_blocking_gate_ids
    assert "blocked artifact" in scorecard.blocking_gaps[-1]


def test_scorecard_reports_missing_scenario_and_receipts() -> None:
    bundle = WaveFourProtoCandidateTrialBundle(
        bundle_id="proto-scorecard-gaps",
        trial_protocol=complete_protocol(),
        artifact_bundles=complete_artifact_bundles(),
        scenario_ids=(),
        blackfox_receipt_ids=(),
    )
    scorecard = build_wave_four_proto_candidate_scorecard(
        scorecard_id="scorecard-gaps",
        proto_candidate_bundle=bundle,
    )

    assert scorecard.status is WaveFourScorecardStatus.NEEDS_EVIDENCE
    assert "gate:scenario-coverage" in scorecard.failed_evidence_gate_ids
    assert "gate:blackfox-receipt-coverage" in scorecard.failed_evidence_gate_ids
    assert "scorecard-gaps has no WorldTwin scenario ids" in scorecard.readiness_gaps
    assert "scorecard-gaps has no BlackFox receipt ids" in scorecard.readiness_gaps


def test_scorecard_requires_gate_coverage_and_rejects_duplicates() -> None:
    gate = WaveFourScorecardGate(
        gate_id="gate:single",
        gate_kind=WaveFourScorecardGateKind.EVIDENCE_BINDING,
        severity=WaveFourScorecardGateSeverity.EVIDENCE,
        passed=True,
        summary="Single gate is intentionally incomplete.",
    )
    scorecard = WaveFourProtoCandidateScorecard(
        scorecard_id="scorecard-incomplete",
        proto_candidate_bundle=ready_bundle(),
        gates=(gate,),
        scenario_ids=("worldtwin:scorecard-review",),
        blackfox_receipt_ids=("blackfox:scorecard-review",),
    )

    assert scorecard.status is WaveFourScorecardStatus.NEEDS_EVIDENCE
    assert WaveFourScorecardGateKind.PROTOCOL_STATUS in (
        scorecard.missing_required_gate_kinds
    )

    with pytest.raises(ValueError, match="Duplicate gate_id"):
        WaveFourProtoCandidateScorecard(
            scorecard_id="scorecard-duplicate",
            proto_candidate_bundle=ready_bundle(),
            gates=(gate, gate),
            scenario_ids=("worldtwin:scorecard-review",),
            blackfox_receipt_ids=("blackfox:scorecard-review",),
        )


def test_scorecard_rejects_execution_agi_and_independent_validation() -> None:
    scorecard = build_wave_four_proto_candidate_scorecard(
        scorecard_id="scorecard-valid",
        proto_candidate_bundle=ready_bundle(),
    )

    with pytest.raises(ValueError, match="cannot permit execution"):
        WaveFourProtoCandidateScorecard(
            scorecard_id="invalid-execution",
            proto_candidate_bundle=ready_bundle(),
            gates=scorecard.gates,
            scenario_ids=("worldtwin:scorecard-review",),
            blackfox_receipt_ids=("blackfox:scorecard-review",),
            permits_automatic_execution=True,
        )

    with pytest.raises(ValueError, match="cannot claim AGI"):
        WaveFourProtoCandidateScorecard(
            scorecard_id="invalid-agi",
            proto_candidate_bundle=ready_bundle(),
            gates=scorecard.gates,
            scenario_ids=("worldtwin:scorecard-review",),
            blackfox_receipt_ids=("blackfox:scorecard-review",),
            claims_agi=True,
        )

    with pytest.raises(ValueError, match="cannot claim independent validation"):
        WaveFourProtoCandidateScorecard(
            scorecard_id="invalid-independent-validation",
            proto_candidate_bundle=ready_bundle(),
            gates=scorecard.gates,
            scenario_ids=("worldtwin:scorecard-review",),
            blackfox_receipt_ids=("blackfox:scorecard-review",),
            independently_validated=True,
        )


def test_scorecard_converts_to_readiness_artifact_and_bundle() -> None:
    scorecard = build_wave_four_proto_candidate_scorecard(
        scorecard_id="scorecard-001",
        proto_candidate_bundle=ready_bundle(),
    )
    artifact = scorecard.to_artifact_ref()
    artifact_bundle_result = scorecard.to_artifact_bundle()

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


def test_scorecard_fingerprint_is_deterministic_despite_gate_order() -> None:
    first = build_wave_four_proto_candidate_scorecard(
        scorecard_id="scorecard-001",
        proto_candidate_bundle=ready_bundle(),
    )
    second = WaveFourProtoCandidateScorecard(
        scorecard_id="scorecard-001",
        proto_candidate_bundle=ready_bundle(),
        gates=tuple(reversed(first.gates)),
        scenario_ids=("worldtwin:scorecard-review",),
        blackfox_receipt_ids=("blackfox:scorecard-review",),
    )

    assert first.fingerprint() == second.fingerprint()
    assert len(first.fingerprint()) == 64
