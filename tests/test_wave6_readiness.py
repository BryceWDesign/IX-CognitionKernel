import pytest

from ix_cognition_kernel.wave6_contracts import (
    WAVE_SIX_DONOR_SOURCE_SYSTEMS,
    WAVE_SIX_REQUIRED_ARTIFACT_KINDS,
    WAVE_SIX_REQUIRED_CAPABILITY_AREAS,
    WAVE_SIX_REQUIRED_LOOP_STAGES,
    WaveSixArtifactKind,
    WaveSixCapabilityArea,
    WaveSixContractArtifact,
    WaveSixContractBundle,
    WaveSixDecisionState,
    WaveSixLoopStage,
    WaveSixSourceSystem,
)
from ix_cognition_kernel.wave6_master_loop import (
    WaveSixMasterLoopStep,
    WaveSixMasterLoopTrace,
)
from ix_cognition_kernel.wave6_readiness import (
    WaveSixReadinessBlocker,
    WaveSixReadinessStatus,
    build_wave_six_readiness_assessment,
)


def _loop_step(
    stage: WaveSixLoopStage,
    *,
    index: int,
    prior_step_id: str | None,
    reality_corrected: bool = False,
) -> WaveSixMasterLoopStep:
    return WaveSixMasterLoopStep(
        step_id=f"step-{index:02d}-{stage.value}",
        stage=stage,
        summary=f"Wave 6 {stage.value} stage is evidence-bound.",
        source_system=WaveSixSourceSystem.IX_COGNITION_KERNEL,
        evidence_ids=(f"evidence-{index:02d}",),
        prior_step_id=prior_step_id,
        decision=WaveSixDecisionState.READY_FOR_WAVE_SIX_LOOP,
        measured_reality_signal=reality_corrected,
        changes_future_reasoning=reality_corrected,
    )


def _complete_trace(
    *, include_reality_correction: bool = True
) -> WaveSixMasterLoopTrace:
    steps: list[WaveSixMasterLoopStep] = []
    prior_step_id: str | None = None
    for index, stage in enumerate(WAVE_SIX_REQUIRED_LOOP_STAGES, start=1):
        reality_corrected = (
            include_reality_correction and stage is WaveSixLoopStage.MEMORY_UPDATE
        )
        step = _loop_step(
            stage,
            index=index,
            prior_step_id=prior_step_id,
            reality_corrected=reality_corrected,
        )
        steps.append(step)
        prior_step_id = step.step_id
    return WaveSixMasterLoopTrace(
        trace_id="trace-complete",
        objective="Prove measured reality corrected future reasoning.",
        steps=tuple(steps),
    )


def _artifact(
    *,
    artifact_id: str,
    kind: WaveSixArtifactKind,
    capability_area: WaveSixCapabilityArea,
    source_system: WaveSixSourceSystem,
    stage: WaveSixLoopStage,
    decision: WaveSixDecisionState = WaveSixDecisionState.READY_FOR_WAVE_SIX_LOOP,
) -> WaveSixContractArtifact:
    return WaveSixContractArtifact(
        artifact_id=artifact_id,
        kind=kind,
        capability_area=capability_area,
        source_system=source_system,
        summary="Wave 6 readiness contract artifact.",
        loop_stages=(stage,),
        evidence_ids=(f"evidence-{artifact_id}",),
        produced_by_engine_id="wave6-readiness-engine",
        decision=decision,
    )


def _complete_contract_bundle() -> WaveSixContractBundle:
    source_systems = (
        WaveSixSourceSystem.IX_COGNITION_KERNEL,
        *WAVE_SIX_DONOR_SOURCE_SYSTEMS,
        WaveSixSourceSystem.HUMAN_REVIEW,
        WaveSixSourceSystem.INDEPENDENT_EVALUATOR,
    )
    artifacts = tuple(
        _artifact(
            artifact_id=f"artifact-{index:02d}-{kind.value}",
            kind=kind,
            capability_area=WAVE_SIX_REQUIRED_CAPABILITY_AREAS[index - 1],
            source_system=source_systems[index - 1],
            stage=WAVE_SIX_REQUIRED_LOOP_STAGES[index - 1],
        )
        for index, kind in enumerate(WAVE_SIX_REQUIRED_ARTIFACT_KINDS, start=1)
    )
    return WaveSixContractBundle(
        bundle_id="bundle-complete",
        artifacts=artifacts,
        notes=("Every required Wave 6 contract dimension is represented.",),
    )


def test_readiness_assessment_accepts_complete_measured_cognition_package() -> None:
    assessment = build_wave_six_readiness_assessment(
        assessment_id="assessment-ready",
        trace=_complete_trace(),
        contract_bundle=_complete_contract_bundle(),
        notes=("Ready means ready for human review, not an AGI claim.",),
    )

    assert assessment.blockers == ()
    assert assessment.status is (
        WaveSixReadinessStatus.READY_FOR_MEASURED_COGNITION_REVIEW
    )
    assert assessment.ready_for_measured_cognition_review
    assert assessment.has_reality_corrected_reasoning_proof
    assert assessment.reality_corrected_reasoning_step_ids == (
        "step-07-memory-update",
    )
    assert assessment.missing_donor_source_systems == ()
    assert assessment.has_falsification_stage
    assert assessment.has_falsification_artifact
    assert assessment.has_human_review_stage
    assert assessment.has_human_review_artifact
    assert assessment.fingerprint() == assessment.fingerprint()
    assert len(assessment.fingerprint()) == 64


def test_readiness_assessment_blocks_without_reality_corrected_reasoning() -> None:
    assessment = build_wave_six_readiness_assessment(
        assessment_id="assessment-no-reality-correction",
        trace=_complete_trace(include_reality_correction=False),
        contract_bundle=_complete_contract_bundle(),
    )

    assert assessment.status is WaveSixReadinessStatus.NOT_READY
    assert WaveSixReadinessBlocker.REALITY_CORRECTED_REASONING_MISSING in (
        assessment.blockers
    )
    assert not assessment.ready_for_measured_cognition_review


def test_readiness_assessment_reports_donor_traceability_gap() -> None:
    contract_bundle = WaveSixContractBundle(
        bundle_id="bundle-no-donors",
        artifacts=tuple(
            _artifact(
                artifact_id=f"artifact-{index:02d}-{kind.value}",
                kind=kind,
                capability_area=WAVE_SIX_REQUIRED_CAPABILITY_AREAS[index - 1],
                source_system=WaveSixSourceSystem.IX_COGNITION_KERNEL,
                stage=WAVE_SIX_REQUIRED_LOOP_STAGES[index - 1],
            )
            for index, kind in enumerate(WAVE_SIX_REQUIRED_ARTIFACT_KINDS, start=1)
        ),
    )
    assessment = build_wave_six_readiness_assessment(
        assessment_id="assessment-donor-gap",
        trace=_complete_trace(),
        contract_bundle=contract_bundle,
    )

    assert assessment.status is WaveSixReadinessStatus.NOT_READY
    assert WaveSixReadinessBlocker.DONOR_TRACEABILITY_INCOMPLETE in (
        assessment.blockers
    )
    assert WaveSixSourceSystem.IX_FUNCTION in assessment.missing_donor_source_systems


def test_readiness_assessment_can_relax_donor_requirement_for_unit_review() -> None:
    contract_bundle = WaveSixContractBundle(
        bundle_id="bundle-no-donors-relaxed",
        artifacts=tuple(
            _artifact(
                artifact_id=f"artifact-{index:02d}-{kind.value}",
                kind=kind,
                capability_area=WAVE_SIX_REQUIRED_CAPABILITY_AREAS[index - 1],
                source_system=WaveSixSourceSystem.IX_COGNITION_KERNEL,
                stage=WAVE_SIX_REQUIRED_LOOP_STAGES[index - 1],
            )
            for index, kind in enumerate(WAVE_SIX_REQUIRED_ARTIFACT_KINDS, start=1)
        ),
    )
    assessment = build_wave_six_readiness_assessment(
        assessment_id="assessment-donors-relaxed",
        trace=_complete_trace(),
        contract_bundle=contract_bundle,
        require_all_donor_sources=False,
    )

    assert assessment.missing_donor_source_systems == ()
    assert WaveSixReadinessBlocker.DONOR_TRACEABILITY_INCOMPLETE not in (
        assessment.blockers
    )
    assert assessment.ready_for_measured_cognition_review


def test_readiness_assessment_blocks_when_contract_artifact_is_blocked() -> None:
    artifacts = list(_complete_contract_bundle().artifacts)
    artifacts[0] = _artifact(
        artifact_id="artifact-blocked-master-loop",
        kind=WaveSixArtifactKind.MASTER_LOOP_CONTRACT,
        capability_area=WaveSixCapabilityArea.MASTER_LOOP,
        source_system=WaveSixSourceSystem.IX_COGNITION_KERNEL,
        stage=WaveSixLoopStage.INTENT,
        decision=WaveSixDecisionState.BLOCKED,
    )
    assessment = build_wave_six_readiness_assessment(
        assessment_id="assessment-blocked",
        trace=_complete_trace(),
        contract_bundle=WaveSixContractBundle(
            bundle_id="bundle-blocked",
            artifacts=tuple(artifacts),
        ),
    )

    assert assessment.status is WaveSixReadinessStatus.BLOCKED
    assert WaveSixReadinessBlocker.BLOCKED_CONTRACT_ARTIFACT in assessment.blockers


def test_readiness_assessment_reports_incomplete_master_loop() -> None:
    steps = _complete_trace().steps[:-1]
    trace = WaveSixMasterLoopTrace(
        trace_id="trace-missing-human-review",
        objective="Missing human review must fail closed.",
        steps=steps,
    )
    assessment = build_wave_six_readiness_assessment(
        assessment_id="assessment-incomplete-loop",
        trace=trace,
        contract_bundle=_complete_contract_bundle(),
    )

    assert assessment.status is WaveSixReadinessStatus.NOT_READY
    assert WaveSixReadinessBlocker.MASTER_LOOP_NOT_REVIEW_READY in assessment.blockers
    assert WaveSixReadinessBlocker.HUMAN_REVIEW_STAGE_MISSING in assessment.blockers


def test_readiness_assessment_rejects_empty_identity() -> None:
    with pytest.raises(ValueError, match="assessment_id must not be empty"):
        build_wave_six_readiness_assessment(
            assessment_id=" ",
            trace=_complete_trace(),
            contract_bundle=_complete_contract_bundle(),
        )
