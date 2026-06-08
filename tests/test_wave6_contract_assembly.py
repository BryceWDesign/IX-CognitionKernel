import pytest

from ix_cognition_kernel.wave6_contract_assembly import (
    WAVE_SIX_CANONICAL_CONTRACT_ASSEMBLY_ID,
    WAVE_SIX_CANONICAL_CONTRACT_BUNDLE_ID,
    WaveSixContractAssemblyStatus,
    WaveSixContractBlueprint,
    build_canonical_wave_six_contract_assembly,
    build_wave_six_contract_assembly,
    canonical_wave_six_contract_blueprints,
)
from ix_cognition_kernel.wave6_contracts import (
    WAVE_SIX_DONOR_SOURCE_SYSTEMS,
    WAVE_SIX_REQUIRED_ARTIFACT_KINDS,
    WAVE_SIX_REQUIRED_CAPABILITY_AREAS,
    WAVE_SIX_REQUIRED_LOOP_STAGES,
    WaveSixArtifactKind,
    WaveSixCapabilityArea,
    WaveSixDecisionState,
    WaveSixLoopStage,
    WaveSixSourceSystem,
)
from ix_cognition_kernel.wave6_donor_profiles import (
    build_canonical_wave_six_donor_traceability_map,
)
from ix_cognition_kernel.wave6_donor_traceability import (
    WaveSixDonorContribution,
    WaveSixDonorIntegrationRisk,
    WaveSixDonorTraceabilityMap,
)


def test_canonical_contract_blueprints_cover_required_contract_surface() -> None:
    blueprints = canonical_wave_six_contract_blueprints()

    assert tuple(blueprint.artifact_kind for blueprint in blueprints) == (
        WAVE_SIX_REQUIRED_ARTIFACT_KINDS
    )
    assert {blueprint.capability_area for blueprint in blueprints} == set(
        WAVE_SIX_REQUIRED_CAPABILITY_AREAS
    )
    represented_stages = {
        stage for blueprint in blueprints for stage in blueprint.loop_stages
    }

    assert set(WAVE_SIX_REQUIRED_LOOP_STAGES).issubset(represented_stages)
    assert len({blueprint.blueprint_id for blueprint in blueprints}) == len(blueprints)
    assert all(blueprint.evidence_ids for blueprint in blueprints)
    assert all(blueprint.fingerprint() for blueprint in blueprints)


def test_blueprint_converts_to_contract_artifact() -> None:
    blueprint = canonical_wave_six_contract_blueprints()[3]
    artifact = blueprint.to_artifact()

    assert artifact.artifact_id == blueprint.artifact_id
    assert artifact.kind is WaveSixArtifactKind.FUTURE_REASONING_CHANGE_PROOF
    assert artifact.capability_area is WaveSixCapabilityArea.FUTURE_REASONING_CHANGE
    assert artifact.source_system is WaveSixSourceSystem.IX_INTENT_REALITY_LOOP
    assert artifact.loop_stages == (WaveSixLoopStage.MEMORY_UPDATE,)
    assert artifact.evidence_ids == blueprint.evidence_ids
    assert artifact.review_ready


def test_canonical_contract_assembly_is_ready_for_readiness_gate() -> None:
    assembly = build_canonical_wave_six_contract_assembly()
    bundle = assembly.contract_bundle

    assert assembly.assembly_id == WAVE_SIX_CANONICAL_CONTRACT_ASSEMBLY_ID
    assert assembly.bundle_id == WAVE_SIX_CANONICAL_CONTRACT_BUNDLE_ID
    assert assembly.status is WaveSixContractAssemblyStatus.READY_FOR_READINESS_GATE
    assert assembly.ready_for_readiness_gate
    assert assembly.missing_artifact_kinds == ()
    assert assembly.missing_capability_areas == ()
    assert assembly.missing_loop_stages == ()
    assert assembly.blocked_artifact_ids == ()
    assert bundle.has_required_contract_coverage
    assert bundle.missing_donor_source_systems == ()
    assert bundle.donor_source_systems_present == WAVE_SIX_DONOR_SOURCE_SYSTEMS
    assert len(assembly.core_artifacts) == len(WAVE_SIX_REQUIRED_ARTIFACT_KINDS)
    assert len(assembly.donor_artifacts) == len(WAVE_SIX_DONOR_SOURCE_SYSTEMS)
    assert assembly.fingerprint() == assembly.fingerprint()
    assert len(assembly.fingerprint()) == 64


def test_contract_assembly_reports_incomplete_when_blueprint_is_missing() -> None:
    assembly = build_wave_six_contract_assembly(
        assembly_id="assembly-missing-blueprint",
        donor_map=build_canonical_wave_six_donor_traceability_map(),
        core_blueprints=canonical_wave_six_contract_blueprints()[:-1],
    )

    assert assembly.status is WaveSixContractAssemblyStatus.INCOMPLETE
    assert WaveSixArtifactKind.CLAIM_BOUNDARY_DECLARATION in (
        assembly.missing_artifact_kinds
    )
    assert WaveSixCapabilityArea.INDEPENDENT_REVIEW_READINESS in (
        assembly.missing_capability_areas
    )
    assert not assembly.ready_for_readiness_gate


def test_contract_assembly_reports_incomplete_when_donor_map_has_gap() -> None:
    donor_map = WaveSixDonorTraceabilityMap(
        map_id="donor-map-single-source",
        contributions=(
            WaveSixDonorContribution(
                contribution_id="only-ix-function",
                source_system=WaveSixSourceSystem.IX_FUNCTION,
                repo_name="IX-Function",
                contribution_summary="Partial donor evidence.",
                supported_loop_stages=(WaveSixLoopStage.TRANSFER_CHECK,),
                supplied_capability_areas=(
                    WaveSixCapabilityArea.CROSS_DOMAIN_TRANSFER,
                ),
                supplied_artifact_kinds=(WaveSixArtifactKind.DONOR_TRACEABILITY_MAP,),
                evidence_ids=("evidence-only-ix-function",),
                integration_risks=(WaveSixDonorIntegrationRisk.SCHEMA_DRIFT,),
                mitigation_summary="Partial donor maps cannot advance.",
            ),
        ),
    )
    assembly = build_wave_six_contract_assembly(
        assembly_id="assembly-donor-gap",
        donor_map=donor_map,
        core_blueprints=canonical_wave_six_contract_blueprints(),
    )

    assert assembly.status is WaveSixContractAssemblyStatus.INCOMPLETE
    assert WaveSixSourceSystem.IX_INTENT_REALITY_LOOP in (
        assembly.donor_map.missing_source_systems
    )
    assert not assembly.ready_for_readiness_gate


def test_contract_assembly_reports_blocked_blueprint_artifact() -> None:
    blueprints = list(canonical_wave_six_contract_blueprints())
    blueprints[0] = WaveSixContractBlueprint(
        blueprint_id="01-master-loop-contract-blocked",
        artifact_kind=WaveSixArtifactKind.MASTER_LOOP_CONTRACT,
        capability_area=WaveSixCapabilityArea.MASTER_LOOP,
        source_system=WaveSixSourceSystem.IX_MAIN,
        loop_stages=(WaveSixLoopStage.INTENT,),
        summary="Blocked master loop contract.",
        evidence_ids=("evidence-blocked-master-loop",),
        decision=WaveSixDecisionState.BLOCKED,
    )
    assembly = build_wave_six_contract_assembly(
        assembly_id="assembly-blocked",
        donor_map=build_canonical_wave_six_donor_traceability_map(),
        core_blueprints=tuple(blueprints),
    )

    assert assembly.status is WaveSixContractAssemblyStatus.BLOCKED
    assert "contract-artifact-01-master-loop-contract-blocked" in (
        assembly.blocked_artifact_ids
    )


def test_contract_blueprint_rejects_empty_evidence() -> None:
    with pytest.raises(ValueError, match="require evidence ids"):
        WaveSixContractBlueprint(
            blueprint_id="invalid-no-evidence",
            artifact_kind=WaveSixArtifactKind.MASTER_LOOP_CONTRACT,
            capability_area=WaveSixCapabilityArea.MASTER_LOOP,
            source_system=WaveSixSourceSystem.IX_MAIN,
            loop_stages=(WaveSixLoopStage.INTENT,),
            summary="Invalid because it has no evidence.",
            evidence_ids=(),
        )


def test_contract_assembly_rejects_duplicate_blueprint_ids() -> None:
    blueprint = canonical_wave_six_contract_blueprints()[0]

    with pytest.raises(ValueError, match="Duplicate blueprint_id"):
        build_wave_six_contract_assembly(
            assembly_id="assembly-duplicate-blueprints",
            donor_map=build_canonical_wave_six_donor_traceability_map(),
            core_blueprints=(blueprint, blueprint),
        )
