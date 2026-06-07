import pytest

from ix_cognition_kernel.wave6_contracts import (
    WAVE_SIX_DONOR_SOURCE_SYSTEMS,
    WaveSixArtifactKind,
    WaveSixCapabilityArea,
    WaveSixDecisionState,
    WaveSixLoopStage,
    WaveSixSourceSystem,
)
from ix_cognition_kernel.wave6_donor_traceability import (
    WaveSixDonorContribution,
    WaveSixDonorIntegrationRisk,
    WaveSixDonorTraceabilityMap,
    build_wave_six_donor_traceability_map,
)


def _contribution(
    source_system: WaveSixSourceSystem = WaveSixSourceSystem.IX_FUNCTION,
    *,
    contribution_id: str = "ix-function-transfer",
    repo_name: str = "IX-Function",
    decision: WaveSixDecisionState = WaveSixDecisionState.READY_FOR_WAVE_SIX_LOOP,
) -> WaveSixDonorContribution:
    return WaveSixDonorContribution(
        contribution_id=contribution_id,
        source_system=source_system,
        repo_name=repo_name,
        contribution_summary="Supplies bounded Wave 6 donor evidence.",
        supported_loop_stages=(WaveSixLoopStage.TRANSFER_CHECK,),
        supplied_capability_areas=(WaveSixCapabilityArea.CROSS_DOMAIN_TRANSFER,),
        supplied_artifact_kinds=(WaveSixArtifactKind.DONOR_TRACEABILITY_MAP,),
        evidence_ids=(f"evidence-{contribution_id}",),
        integration_risks=(WaveSixDonorIntegrationRisk.MESSY_GLUE_CODE,),
        mitigation_summary="Use explicit schemas and deterministic tests.",
        decision=decision,
    )


def _all_donor_contributions() -> tuple[WaveSixDonorContribution, ...]:
    repo_names = {
        WaveSixSourceSystem.IX_FUNCTION: "IX-Function",
        WaveSixSourceSystem.IX_INTENT_REALITY_LOOP: "IX-IntentRealityLoop",
        WaveSixSourceSystem.IX_BLACKFOX: "IX-BlackFox",
        WaveSixSourceSystem.IX_BLACKFOX_COGNITION: "IX-BlackFox-Cognition",
        WaveSixSourceSystem.IX_BLACKFOX_WORLDTWIN: "IX-BlackFox-WorldTwin",
        WaveSixSourceSystem.IX_AUTONOMY_ASSURANCE_RUNTIME: (
            "IX-Autonomy-Assurance-Case-Runtime"
        ),
        WaveSixSourceSystem.IX_MAIN: "IX-main",
    }
    loop_stages = {
        WaveSixSourceSystem.IX_FUNCTION: WaveSixLoopStage.TRANSFER_CHECK,
        WaveSixSourceSystem.IX_INTENT_REALITY_LOOP: WaveSixLoopStage.OUTCOME,
        WaveSixSourceSystem.IX_BLACKFOX: WaveSixLoopStage.HUMAN_REVIEW,
        WaveSixSourceSystem.IX_BLACKFOX_COGNITION: WaveSixLoopStage.PREDICTION,
        WaveSixSourceSystem.IX_BLACKFOX_WORLDTWIN: WaveSixLoopStage.DELTA,
        WaveSixSourceSystem.IX_AUTONOMY_ASSURANCE_RUNTIME: WaveSixLoopStage.PERMISSION,
        WaveSixSourceSystem.IX_MAIN: WaveSixLoopStage.INTENT,
    }
    capability_areas = {
        WaveSixSourceSystem.IX_FUNCTION: WaveSixCapabilityArea.CROSS_DOMAIN_TRANSFER,
        WaveSixSourceSystem.IX_INTENT_REALITY_LOOP: (
            WaveSixCapabilityArea.REALITY_CORRECTED_REASONING
        ),
        WaveSixSourceSystem.IX_BLACKFOX: (
            WaveSixCapabilityArea.HUMAN_AUTHORITY_PRESERVATION
        ),
        WaveSixSourceSystem.IX_BLACKFOX_COGNITION: (
            WaveSixCapabilityArea.MEASURED_SYSTEM_LEVEL_COGNITION
        ),
        WaveSixSourceSystem.IX_BLACKFOX_WORLDTWIN: (
            WaveSixCapabilityArea.FUTURE_REASONING_CHANGE
        ),
        WaveSixSourceSystem.IX_AUTONOMY_ASSURANCE_RUNTIME: (
            WaveSixCapabilityArea.FALSIFICATION_DISCIPLINE
        ),
        WaveSixSourceSystem.IX_MAIN: WaveSixCapabilityArea.MASTER_LOOP,
    }
    return tuple(
        WaveSixDonorContribution(
            contribution_id=f"donor-{source.value}",
            source_system=source,
            repo_name=repo_names[source],
            contribution_summary=(
                f"{repo_names[source]} supplies bounded donor evidence."
            ),
            supported_loop_stages=(loop_stages[source],),
            supplied_capability_areas=(capability_areas[source],),
            supplied_artifact_kinds=(WaveSixArtifactKind.DONOR_TRACEABILITY_MAP,),
            evidence_ids=(f"evidence-{source.value}",),
            integration_risks=(WaveSixDonorIntegrationRisk.MESSY_GLUE_CODE,),
            mitigation_summary="Keep handoff schema-bound and review-gated.",
            decision=WaveSixDecisionState.READY_FOR_WAVE_SIX_LOOP,
        )
        for source in WAVE_SIX_DONOR_SOURCE_SYSTEMS
    )


def test_donor_contribution_converts_to_contract_artifact() -> None:
    contribution = _contribution()
    artifact = contribution.to_contract_artifact()

    assert contribution.review_ready
    assert not contribution.blocked
    assert artifact.artifact_id == "donor-artifact-ix-function-transfer"
    assert artifact.kind is WaveSixArtifactKind.DONOR_TRACEABILITY_MAP
    assert artifact.capability_area is WaveSixCapabilityArea.DONOR_TRACEABILITY
    assert artifact.source_system is WaveSixSourceSystem.IX_FUNCTION
    assert artifact.loop_stages == (WaveSixLoopStage.TRANSFER_CHECK,)
    assert artifact.evidence_ids == ("evidence-ix-function-transfer",)
    assert contribution.fingerprint() == contribution.fingerprint()
    assert len(contribution.fingerprint()) == 64


def test_donor_contribution_rejects_non_donor_source_system() -> None:
    with pytest.raises(ValueError, match="expected donor source"):
        _contribution(
            source_system=WaveSixSourceSystem.HUMAN_REVIEW,
            contribution_id="human-review-not-donor",
            repo_name="Human Review",
        )


def test_donor_contribution_requires_explicit_integration_risk() -> None:
    with pytest.raises(ValueError, match="must name integration risks"):
        WaveSixDonorContribution(
            contribution_id="no-risk",
            source_system=WaveSixSourceSystem.IX_FUNCTION,
            repo_name="IX-Function",
            contribution_summary="Invalid donor contribution.",
            supported_loop_stages=(WaveSixLoopStage.TRANSFER_CHECK,),
            supplied_capability_areas=(WaveSixCapabilityArea.CROSS_DOMAIN_TRANSFER,),
            supplied_artifact_kinds=(WaveSixArtifactKind.DONOR_TRACEABILITY_MAP,),
            evidence_ids=("evidence-no-risk",),
            integration_risks=(),
            mitigation_summary="Invalid because it hides risk.",
        )


def test_donor_traceability_map_reports_complete_donor_coverage() -> None:
    donor_map = build_wave_six_donor_traceability_map(
        map_id="donor-map-complete",
        contributions=_all_donor_contributions(),
        notes=("All donor repos are represented without direct runtime coupling.",),
    )

    assert donor_map.all_required_sources_present
    assert donor_map.has_no_blocked_contributions
    assert donor_map.ready_for_contract_bundle
    assert donor_map.missing_source_systems == ()
    assert donor_map.source_systems_present == WAVE_SIX_DONOR_SOURCE_SYSTEMS
    assert donor_map.review_ready_contribution_ids == donor_map.contribution_ids
    assert WaveSixLoopStage.TRANSFER_CHECK in donor_map.represented_loop_stages
    assert (
        WaveSixCapabilityArea.REALITY_CORRECTED_REASONING
        in donor_map.represented_capability_areas
    )
    assert (
        WaveSixArtifactKind.DONOR_TRACEABILITY_MAP
        in donor_map.represented_artifact_kinds
    )
    assert len(donor_map.to_contract_artifacts()) == len(WAVE_SIX_DONOR_SOURCE_SYSTEMS)
    assert donor_map.fingerprint() == donor_map.fingerprint()
    assert len(donor_map.fingerprint()) == 64


def test_donor_traceability_map_reports_missing_source_systems() -> None:
    donor_map = WaveSixDonorTraceabilityMap(
        map_id="donor-map-partial",
        contributions=(_contribution(),),
    )

    assert not donor_map.all_required_sources_present
    assert not donor_map.ready_for_contract_bundle
    assert donor_map.source_systems_present == (WaveSixSourceSystem.IX_FUNCTION,)
    assert (
        WaveSixSourceSystem.IX_INTENT_REALITY_LOOP in donor_map.missing_source_systems
    )


def test_donor_traceability_map_reports_blocked_contribution() -> None:
    donor_map = WaveSixDonorTraceabilityMap(
        map_id="donor-map-blocked",
        contributions=(_contribution(decision=WaveSixDecisionState.BLOCKED),),
    )

    assert donor_map.blocked_contribution_ids == ("ix-function-transfer",)
    assert not donor_map.has_no_blocked_contributions
    assert not donor_map.ready_for_contract_bundle


def test_donor_traceability_map_rejects_duplicate_source_system() -> None:
    with pytest.raises(ValueError, match="Duplicate source_system"):
        WaveSixDonorTraceabilityMap(
            map_id="donor-map-duplicate-source",
            contributions=(
                _contribution(contribution_id="ix-function-1"),
                _contribution(contribution_id="ix-function-2"),
            ),
        )


def test_donor_traceability_map_can_lookup_contribution_by_source() -> None:
    donor_map = WaveSixDonorTraceabilityMap(
        map_id="donor-map-lookup",
        contributions=(_contribution(),),
    )

    contribution = donor_map.contribution_for_source(WaveSixSourceSystem.IX_FUNCTION)

    assert contribution is not None
    assert contribution.repo_name == "IX-Function"
    assert (
        donor_map.contribution_for_source(WaveSixSourceSystem.IX_INTENT_REALITY_LOOP)
        is None
    )
