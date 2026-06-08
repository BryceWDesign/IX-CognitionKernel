from ix_cognition_kernel.wave6_contract_assembly import (
    build_canonical_wave_six_contract_assembly,
)
from ix_cognition_kernel.wave6_contracts import (
    WaveSixArtifactKind,
    WaveSixCapabilityArea,
    WaveSixContractArtifact,
    WaveSixContractBundle,
    WaveSixDecisionState,
    WaveSixLoopStage,
    WaveSixSourceSystem,
)
from ix_cognition_kernel.wave6_loop_blueprints import (
    build_canonical_wave_six_master_loop_trace,
)
from ix_cognition_kernel.wave6_master_loop import (
    WaveSixLoopReadiness,
    WaveSixMasterLoopStep,
    WaveSixMasterLoopTrace,
)
from ix_cognition_kernel.wave6_readiness import (
    WaveSixReadinessAssessment,
    WaveSixReadinessBlocker,
    WaveSixReadinessStatus,
    build_wave_six_readiness_assessment,
)


def _minimal_artifact(
    *,
    artifact_id: str,
    kind: WaveSixArtifactKind,
    capability_area: WaveSixCapabilityArea,
    source_system: WaveSixSourceSystem,
    loop_stages: tuple[WaveSixLoopStage, ...],
    decision: WaveSixDecisionState = WaveSixDecisionState.READY_FOR_WAVE_SIX_LOOP,
) -> WaveSixContractArtifact:
    return WaveSixContractArtifact(
        artifact_id=artifact_id,
        kind=kind,
        capability_area=capability_area,
        source_system=source_system,
        summary=f"Artifact for {kind.value}.",
        loop_stages=loop_stages,
        evidence_ids=(f"evidence-{artifact_id}",),
        produced_by_engine_id="wave6-readiness-test-engine",
        decision=decision,
    )


def _complete_trace() -> WaveSixMasterLoopTrace:
    return build_canonical_wave_six_master_loop_trace()


def _complete_bundle() -> WaveSixContractBundle:
    return build_canonical_wave_six_contract_assembly().contract_bundle


def test_readiness_assessment_is_ready_with_complete_trace_and_contract_bundle() -> (
    None
):
    assessment = build_wave_six_readiness_assessment(
        assessment_id="readiness-ready",
        trace=_complete_trace(),
        contract_bundle=_complete_bundle(),
        notes=("Ready means measured-cognition review, not AGI achieved.",),
    )

    assert assessment.trace_readiness is WaveSixLoopReadiness.READY_FOR_HUMAN_REVIEW
    assert assessment.missing_contract_loop_stages == ()
    assert assessment.missing_donor_source_systems == ()
    assert assessment.blockers == ()
    assert assessment.status is (
        WaveSixReadinessStatus.READY_FOR_MEASURED_COGNITION_REVIEW
    )
    assert assessment.ready_for_measured_cognition_review
    assert assessment.has_reality_corrected_reasoning_proof
    assert assessment.reality_corrected_reasoning_step_ids == ("step-07-memory-update",)
    assert assessment.has_falsification_stage
    assert assessment.has_human_review_stage
    assert assessment.has_falsification_artifact
    assert assessment.has_human_review_artifact
    assert assessment.fingerprint() == assessment.fingerprint()
    assert len(assessment.fingerprint()) == 64


def test_readiness_assessment_reports_master_loop_not_review_ready() -> None:
    trace = WaveSixMasterLoopTrace(
        trace_id="trace-missing-human-review",
        objective="Trace with missing human review stage.",
        steps=_complete_trace().steps[:-1],
    )
    assessment = build_wave_six_readiness_assessment(
        assessment_id="readiness-trace-not-ready",
        trace=trace,
        contract_bundle=_complete_bundle(),
    )

    assert assessment.trace_readiness is WaveSixLoopReadiness.INCOMPLETE
    assert WaveSixReadinessBlocker.MASTER_LOOP_NOT_REVIEW_READY in (assessment.blockers)
    assert WaveSixReadinessBlocker.HUMAN_REVIEW_STAGE_MISSING in assessment.blockers
    assert assessment.status is WaveSixReadinessStatus.NOT_READY
    assert not assessment.ready_for_measured_cognition_review


def test_readiness_assessment_reports_missing_contract_coverage() -> None:
    bundle = WaveSixContractBundle(
        bundle_id="partial-contract-bundle",
        artifacts=(
            _minimal_artifact(
                artifact_id="intent-artifact",
                kind=WaveSixArtifactKind.MASTER_LOOP_CONTRACT,
                capability_area=WaveSixCapabilityArea.MASTER_LOOP,
                source_system=WaveSixSourceSystem.IX_MAIN,
                loop_stages=(WaveSixLoopStage.INTENT,),
            ),
        ),
    )
    assessment = build_wave_six_readiness_assessment(
        assessment_id="readiness-contract-gap",
        trace=_complete_trace(),
        contract_bundle=bundle,
        require_all_donor_sources=False,
    )

    assert WaveSixReadinessBlocker.CONTRACT_COVERAGE_INCOMPLETE in (assessment.blockers)
    assert WaveSixReadinessBlocker.FALSIFICATION_ARTIFACT_MISSING in (
        assessment.blockers
    )
    assert WaveSixReadinessBlocker.HUMAN_REVIEW_ARTIFACT_MISSING in (
        assessment.blockers
    )
    assert WaveSixLoopStage.PERMISSION in assessment.missing_contract_loop_stages
    assert assessment.status is WaveSixReadinessStatus.NOT_READY
    assert not assessment.ready_for_measured_cognition_review


def test_readiness_assessment_reports_donor_traceability_gap_when_required() -> None:
    bundle = WaveSixContractBundle(
        bundle_id="single-donor-bundle",
        artifacts=(
            _minimal_artifact(
                artifact_id="ix-function-donor",
                kind=WaveSixArtifactKind.DONOR_TRACEABILITY_MAP,
                capability_area=WaveSixCapabilityArea.DONOR_TRACEABILITY,
                source_system=WaveSixSourceSystem.IX_FUNCTION,
                loop_stages=(WaveSixLoopStage.TRANSFER_CHECK,),
            ),
        ),
        required_artifact_kinds=(WaveSixArtifactKind.DONOR_TRACEABILITY_MAP,),
        required_capability_areas=(WaveSixCapabilityArea.DONOR_TRACEABILITY,),
        required_loop_stages=(WaveSixLoopStage.TRANSFER_CHECK,),
    )
    assessment = build_wave_six_readiness_assessment(
        assessment_id="readiness-donor-gap",
        trace=_complete_trace(),
        contract_bundle=bundle,
        require_all_donor_sources=True,
    )

    assert WaveSixSourceSystem.IX_INTENT_REALITY_LOOP in (
        assessment.missing_donor_source_systems
    )
    assert WaveSixReadinessBlocker.DONOR_TRACEABILITY_INCOMPLETE in (
        assessment.blockers
    )
    assert assessment.status is WaveSixReadinessStatus.NOT_READY


def test_readiness_assessment_can_ignore_donor_traceability_requirement() -> None:
    bundle = WaveSixContractBundle(
        bundle_id="single-donor-bundle-ignored",
        artifacts=(
            _minimal_artifact(
                artifact_id="ix-function-donor",
                kind=WaveSixArtifactKind.DONOR_TRACEABILITY_MAP,
                capability_area=WaveSixCapabilityArea.DONOR_TRACEABILITY,
                source_system=WaveSixSourceSystem.IX_FUNCTION,
                loop_stages=(WaveSixLoopStage.TRANSFER_CHECK,),
            ),
        ),
        required_artifact_kinds=(WaveSixArtifactKind.DONOR_TRACEABILITY_MAP,),
        required_capability_areas=(WaveSixCapabilityArea.DONOR_TRACEABILITY,),
        required_loop_stages=(WaveSixLoopStage.TRANSFER_CHECK,),
    )
    assessment = build_wave_six_readiness_assessment(
        assessment_id="readiness-donor-gap-ignored",
        trace=_complete_trace(),
        contract_bundle=bundle,
        require_all_donor_sources=False,
    )

    assert assessment.missing_donor_source_systems == ()
    assert WaveSixReadinessBlocker.DONOR_TRACEABILITY_INCOMPLETE not in (
        assessment.blockers
    )


def test_readiness_assessment_requires_reality_corrected_reasoning_proof() -> None:
    steps = tuple(
        WaveSixMasterLoopStep(
            step_id=step.step_id,
            stage=step.stage,
            summary=step.summary,
            source_system=step.source_system,
            evidence_ids=step.evidence_ids,
            prior_step_id=step.prior_step_id,
            decision=step.decision,
            measured_reality_signal=step.measured_reality_signal,
            changes_future_reasoning=False,
        )
        for step in _complete_trace().steps
    )
    trace = WaveSixMasterLoopTrace(
        trace_id="trace-no-future-change",
        objective="Trace with no future reasoning change.",
        steps=steps,
    )
    assessment = build_wave_six_readiness_assessment(
        assessment_id="readiness-no-future-change",
        trace=trace,
        contract_bundle=_complete_bundle(),
    )

    assert not assessment.has_reality_corrected_reasoning_proof
    assert WaveSixReadinessBlocker.REALITY_CORRECTED_REASONING_MISSING in (
        assessment.blockers
    )
    assert assessment.status is WaveSixReadinessStatus.NOT_READY


def test_readiness_assessment_blocks_when_trace_or_contract_artifact_blocks() -> None:
    steps = list(_complete_trace().steps)
    steps[8] = WaveSixMasterLoopStep(
        step_id="step-09-falsification",
        stage=WaveSixLoopStage.FALSIFICATION,
        summary="Blocked falsification step.",
        source_system=WaveSixSourceSystem.IX_FUNCTION,
        evidence_ids=("evidence-falsification",),
        prior_step_id="step-08-transfer-check",
        decision=WaveSixDecisionState.BLOCKED,
    )
    trace = WaveSixMasterLoopTrace(
        trace_id="trace-blocked",
        objective="Trace with blocked falsification.",
        steps=tuple(steps),
    )
    trace_blocked = build_wave_six_readiness_assessment(
        assessment_id="readiness-trace-blocked",
        trace=trace,
        contract_bundle=_complete_bundle(),
    )

    assert trace_blocked.trace_readiness is WaveSixLoopReadiness.BLOCKED
    assert trace_blocked.status is WaveSixReadinessStatus.BLOCKED

    artifact = _minimal_artifact(
        artifact_id="blocked-falsification-artifact",
        kind=WaveSixArtifactKind.FALSIFICATION_RECORD,
        capability_area=WaveSixCapabilityArea.FALSIFICATION_DISCIPLINE,
        source_system=WaveSixSourceSystem.IX_FUNCTION,
        loop_stages=(WaveSixLoopStage.FALSIFICATION,),
        decision=WaveSixDecisionState.BLOCKED,
    )
    bundle = WaveSixContractBundle(
        bundle_id="blocked-contract-bundle",
        artifacts=(artifact,),
        required_artifact_kinds=(WaveSixArtifactKind.FALSIFICATION_RECORD,),
        required_capability_areas=(WaveSixCapabilityArea.FALSIFICATION_DISCIPLINE,),
        required_loop_stages=(WaveSixLoopStage.FALSIFICATION,),
    )
    contract_blocked = WaveSixReadinessAssessment(
        assessment_id="readiness-contract-blocked",
        trace=_complete_trace(),
        contract_bundle=bundle,
        require_all_donor_sources=False,
    )

    assert WaveSixReadinessBlocker.BLOCKED_CONTRACT_ARTIFACT in (
        contract_blocked.blockers
    )
    assert contract_blocked.status is WaveSixReadinessStatus.BLOCKED


def test_readiness_assessment_canonical_payload_indexes_trace_and_bundle() -> None:
    assessment = build_wave_six_readiness_assessment(
        assessment_id="readiness-payload",
        trace=_complete_trace(),
        contract_bundle=_complete_bundle(),
        reviewer_role="independent-reviewer",
        notes=("Payload should be deterministic.",),
    )
    payload = assessment.canonical_payload()

    assert payload["assessment_id"] == "readiness-payload"
    assert payload["reviewer_role"] == "independent-reviewer"
    assert payload["trace_fingerprint"] == _complete_trace().fingerprint()
    assert payload["contract_bundle_fingerprint"] == _complete_bundle().fingerprint()
    assert payload["status"] == "ready-for-measured-cognition-review"
