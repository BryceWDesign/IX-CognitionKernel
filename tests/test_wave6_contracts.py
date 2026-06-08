import pytest

from ix_cognition_kernel.wave6_contracts import (
    WaveSixArtifactKind,
    WaveSixCapabilityArea,
    WaveSixClaimBoundary,
    WaveSixContractArtifact,
    WaveSixContractBundle,
    WaveSixDecisionState,
    WaveSixLoopStage,
    WaveSixSourceSystem,
    required_wave_six_artifact_kinds,
    required_wave_six_capability_areas,
    required_wave_six_claim_boundaries,
    required_wave_six_loop_stages,
    wave_six_donor_source_systems,
)


def _artifact(
    *,
    artifact_id: str = "artifact-1",
    kind: WaveSixArtifactKind = WaveSixArtifactKind.MASTER_LOOP_CONTRACT,
    capability_area: WaveSixCapabilityArea = WaveSixCapabilityArea.MASTER_LOOP,
    source_system: WaveSixSourceSystem = WaveSixSourceSystem.IX_COGNITION_KERNEL,
    loop_stages: tuple[WaveSixLoopStage, ...] = (WaveSixLoopStage.INTENT,),
    evidence_ids: tuple[str, ...] = ("evidence-1",),
    decision: WaveSixDecisionState = WaveSixDecisionState.READY_FOR_WAVE_SIX_LOOP,
) -> WaveSixContractArtifact:
    return WaveSixContractArtifact(
        artifact_id=artifact_id,
        kind=kind,
        capability_area=capability_area,
        source_system=source_system,
        summary="Reviewable Wave 6 measured cognition contract artifact.",
        loop_stages=loop_stages,
        evidence_ids=evidence_ids,
        produced_by_engine_id="wave6-engine-1",
        decision=decision,
    )


def test_wave_six_required_sets_lock_measured_cognition_boundary() -> None:
    assert required_wave_six_loop_stages() == (
        WaveSixLoopStage.INTENT,
        WaveSixLoopStage.PERMISSION,
        WaveSixLoopStage.PREDICTION,
        WaveSixLoopStage.TRIAL,
        WaveSixLoopStage.OUTCOME,
        WaveSixLoopStage.DELTA,
        WaveSixLoopStage.MEMORY_UPDATE,
        WaveSixLoopStage.TRANSFER_CHECK,
        WaveSixLoopStage.FALSIFICATION,
        WaveSixLoopStage.HUMAN_REVIEW,
    )
    assert (
        WaveSixCapabilityArea.REALITY_CORRECTED_REASONING
        in required_wave_six_capability_areas()
    )
    assert (
        WaveSixArtifactKind.FUTURE_REASONING_CHANGE_PROOF
        in required_wave_six_artifact_kinds()
    )
    assert WaveSixClaimBoundary.NO_AGI_CLAIM in required_wave_six_claim_boundaries()
    assert (
        WaveSixClaimBoundary.MEASURED_SYSTEM_LEVEL_COGNITION_ATTEMPT
        in required_wave_six_claim_boundaries()
    )


def test_wave_six_donor_sources_include_all_uploaded_integration_repos() -> None:
    assert wave_six_donor_source_systems() == (
        WaveSixSourceSystem.IX_FUNCTION,
        WaveSixSourceSystem.IX_INTENT_REALITY_LOOP,
        WaveSixSourceSystem.IX_BLACKFOX,
        WaveSixSourceSystem.IX_BLACKFOX_COGNITION,
        WaveSixSourceSystem.IX_BLACKFOX_WORLDTWIN,
        WaveSixSourceSystem.IX_AUTONOMY_ASSURANCE_RUNTIME,
        WaveSixSourceSystem.IX_MAIN,
    )


def test_contract_artifact_is_evidence_bound_and_fingerprinted() -> None:
    artifact = _artifact()

    assert artifact.evidence_bound
    assert artifact.review_ready
    assert artifact.covers_stage(WaveSixLoopStage.INTENT)
    assert not artifact.blocks_wave_six_progress
    assert artifact.fingerprint() == artifact.fingerprint()
    assert len(artifact.fingerprint()) == 64


def test_contract_artifact_rejects_agi_claim() -> None:
    with pytest.raises(ValueError, match="must not claim AGI"):
        WaveSixContractArtifact(
            artifact_id="artifact-agi",
            kind=WaveSixArtifactKind.CLAIM_BOUNDARY_DECLARATION,
            capability_area=WaveSixCapabilityArea.INDEPENDENT_REVIEW_READINESS,
            source_system=WaveSixSourceSystem.IX_COGNITION_KERNEL,
            summary="Invalid Wave 6 claim artifact.",
            loop_stages=(WaveSixLoopStage.HUMAN_REVIEW,),
            evidence_ids=("evidence-agi",),
            produced_by_engine_id="wave6-engine-1",
            claims_agi=True,
        )


def test_contract_artifact_rejects_autonomous_execution() -> None:
    with pytest.raises(ValueError, match="must not allow autonomous execution"):
        WaveSixContractArtifact(
            artifact_id="artifact-auto",
            kind=WaveSixArtifactKind.MASTER_LOOP_CONTRACT,
            capability_area=WaveSixCapabilityArea.MASTER_LOOP,
            source_system=WaveSixSourceSystem.IX_COGNITION_KERNEL,
            summary="Invalid autonomous execution artifact.",
            loop_stages=(WaveSixLoopStage.PERMISSION,),
            evidence_ids=("evidence-auto",),
            produced_by_engine_id="wave6-engine-1",
            allows_autonomous_execution=True,
        )


def test_review_ready_artifact_requires_evidence() -> None:
    with pytest.raises(ValueError, match="require evidence ids"):
        _artifact(evidence_ids=())


def test_contract_artifact_requires_all_claim_boundaries() -> None:
    with pytest.raises(ValueError, match="required claim boundary"):
        WaveSixContractArtifact(
            artifact_id="artifact-boundary",
            kind=WaveSixArtifactKind.CLAIM_BOUNDARY_DECLARATION,
            capability_area=WaveSixCapabilityArea.INDEPENDENT_REVIEW_READINESS,
            source_system=WaveSixSourceSystem.IX_COGNITION_KERNEL,
            summary="Missing required Wave 6 claim boundaries.",
            loop_stages=(WaveSixLoopStage.HUMAN_REVIEW,),
            evidence_ids=("evidence-boundary",),
            produced_by_engine_id="wave6-engine-1",
            claim_boundaries=(WaveSixClaimBoundary.NO_AGI_CLAIM,),
        )


def test_contract_artifact_rejects_duplicate_loop_stages() -> None:
    with pytest.raises(ValueError, match="Duplicate loop stage"):
        _artifact(
            loop_stages=(WaveSixLoopStage.INTENT, WaveSixLoopStage.INTENT),
        )


def test_contract_bundle_reports_missing_coverage_without_pretending_ready() -> None:
    artifact = _artifact()
    bundle = WaveSixContractBundle(
        bundle_id="bundle-1",
        artifacts=(artifact,),
        notes=("Wave 6 starts as a bounded measured cognition attempt.",),
    )

    assert bundle.artifact_ids == ("artifact-1",)
    assert bundle.covered_loop_stages == (WaveSixLoopStage.INTENT,)
    assert WaveSixLoopStage.PERMISSION in bundle.missing_loop_stages
    assert (
        WaveSixCapabilityArea.CROSS_DOMAIN_TRANSFER in bundle.missing_capability_areas
    )
    assert WaveSixArtifactKind.FALSIFICATION_RECORD in bundle.missing_artifact_kinds
    assert bundle.missing_claim_boundaries == ()
    assert not bundle.has_complete_loop_coverage
    assert not bundle.has_required_contract_coverage
    assert bundle.fingerprint() == bundle.fingerprint()


def test_contract_bundle_rejects_duplicate_artifact_ids() -> None:
    with pytest.raises(ValueError, match="Duplicate artifact_id"):
        WaveSixContractBundle(
            bundle_id="bundle-duplicates",
            artifacts=(
                _artifact(artifact_id="duplicate"),
                _artifact(artifact_id="duplicate"),
            ),
        )


def test_contract_bundle_tracks_donor_source_gaps() -> None:
    artifact = _artifact(
        artifact_id="function-donor",
        kind=WaveSixArtifactKind.DONOR_TRACEABILITY_MAP,
        capability_area=WaveSixCapabilityArea.DONOR_TRACEABILITY,
        source_system=WaveSixSourceSystem.IX_FUNCTION,
        loop_stages=(WaveSixLoopStage.TRANSFER_CHECK,),
    )
    bundle = WaveSixContractBundle(bundle_id="bundle-donors", artifacts=(artifact,))

    assert bundle.source_systems == (WaveSixSourceSystem.IX_FUNCTION,)
    assert bundle.donor_source_systems_present == (WaveSixSourceSystem.IX_FUNCTION,)
    assert (
        WaveSixSourceSystem.IX_INTENT_REALITY_LOOP
        in bundle.missing_donor_source_systems
    )
    assert bundle.artifact_ids_by_stage(WaveSixLoopStage.TRANSFER_CHECK) == (
        "function-donor",
    )
