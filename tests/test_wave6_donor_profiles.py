import pytest

from ix_cognition_kernel.wave6_contracts import (
    WAVE_SIX_DONOR_SOURCE_SYSTEMS,
    WaveSixArtifactKind,
    WaveSixCapabilityArea,
    WaveSixLoopStage,
    WaveSixSourceSystem,
)
from ix_cognition_kernel.wave6_donor_profiles import (
    WAVE_SIX_CANONICAL_DONOR_MAP_ID,
    WaveSixDonorProfile,
    build_canonical_wave_six_donor_traceability_map,
    canonical_wave_six_donor_profile_for_source,
    canonical_wave_six_donor_profiles,
)
from ix_cognition_kernel.wave6_donor_traceability import (
    WaveSixDonorIntegrationRisk,
)


def test_canonical_profiles_cover_each_required_donor_once() -> None:
    profiles = canonical_wave_six_donor_profiles()

    assert tuple(profile.source_system for profile in profiles) == (
        WAVE_SIX_DONOR_SOURCE_SYSTEMS
    )
    assert len({profile.profile_id for profile in profiles}) == len(profiles)
    assert len({profile.contribution_id() for profile in profiles}) == len(profiles)
    assert all(profile.repo_name for profile in profiles)
    assert all(profile.primary_role for profile in profiles)
    assert all(profile.supported_loop_stages for profile in profiles)
    assert all(profile.supplied_capability_areas for profile in profiles)
    assert all(profile.supplied_artifact_kinds for profile in profiles)
    assert all(profile.default_integration_risks for profile in profiles)


def test_canonical_profiles_cover_the_full_master_loop_surface() -> None:
    profiles = canonical_wave_six_donor_profiles()
    represented_stages = {
        stage for profile in profiles for stage in profile.supported_loop_stages
    }
    represented_capabilities = {
        area for profile in profiles for area in profile.supplied_capability_areas
    }
    represented_artifacts = {
        kind for profile in profiles for kind in profile.supplied_artifact_kinds
    }

    assert set(WaveSixLoopStage).issubset(represented_stages)
    assert WaveSixCapabilityArea.REALITY_CORRECTED_REASONING in (
        represented_capabilities
    )
    assert WaveSixCapabilityArea.FUTURE_REASONING_CHANGE in represented_capabilities
    assert WaveSixCapabilityArea.CROSS_DOMAIN_TRANSFER in represented_capabilities
    assert WaveSixArtifactKind.REALITY_CORRECTION_RECORD in represented_artifacts
    assert WaveSixArtifactKind.FUTURE_REASONING_CHANGE_PROOF in represented_artifacts
    assert WaveSixArtifactKind.TRANSFER_NOVELTY_RECORD in represented_artifacts
    assert WaveSixArtifactKind.CLAIM_BOUNDARY_DECLARATION in represented_artifacts


def test_profile_lookup_returns_only_canonical_donor_sources() -> None:
    ix_function_profile = canonical_wave_six_donor_profile_for_source(
        WaveSixSourceSystem.IX_FUNCTION
    )

    assert ix_function_profile is not None
    assert ix_function_profile.repo_name == "IX-Function"
    assert (
        canonical_wave_six_donor_profile_for_source(WaveSixSourceSystem.HUMAN_REVIEW)
        is None
    )


def test_profile_converts_to_traceability_contribution() -> None:
    profile = canonical_wave_six_donor_profiles()[1]
    contribution = profile.to_contribution()

    assert contribution.contribution_id == profile.contribution_id()
    assert contribution.source_system is profile.source_system
    assert contribution.repo_name == profile.repo_name
    assert contribution.supported_loop_stages == profile.supported_loop_stages
    assert contribution.supplied_capability_areas == profile.supplied_capability_areas
    assert contribution.supplied_artifact_kinds == profile.supplied_artifact_kinds
    assert contribution.evidence_ids == profile.default_evidence_ids()
    assert contribution.integration_risks == profile.default_integration_risks
    assert contribution.mitigation_summary == profile.mitigation_summary
    assert contribution.fingerprint() == contribution.fingerprint()
    assert len(profile.fingerprint()) == 64


def test_canonical_profile_map_is_ready_for_contract_bundle() -> None:
    donor_map = build_canonical_wave_six_donor_traceability_map()

    assert donor_map.map_id == WAVE_SIX_CANONICAL_DONOR_MAP_ID
    assert donor_map.all_required_sources_present
    assert donor_map.ready_for_contract_bundle
    assert donor_map.missing_source_systems == ()
    assert donor_map.blocked_contribution_ids == ()
    assert donor_map.source_systems_present == WAVE_SIX_DONOR_SOURCE_SYSTEMS
    assert len(donor_map.contributions) == len(WAVE_SIX_DONOR_SOURCE_SYSTEMS)
    assert len(donor_map.to_contract_artifacts()) == len(WAVE_SIX_DONOR_SOURCE_SYSTEMS)
    assert donor_map.fingerprint() == donor_map.fingerprint()


def test_donor_profile_rejects_non_donor_source() -> None:
    with pytest.raises(ValueError, match="expected donor source"):
        WaveSixDonorProfile(
            source_system=WaveSixSourceSystem.HUMAN_REVIEW,
            repo_name="Human Review",
            primary_role="Invalid non-donor source.",
            supported_loop_stages=(WaveSixLoopStage.HUMAN_REVIEW,),
            supplied_capability_areas=(
                WaveSixCapabilityArea.HUMAN_AUTHORITY_PRESERVATION,
            ),
            supplied_artifact_kinds=(WaveSixArtifactKind.HUMAN_REVIEW_DOCKET,),
            default_integration_risks=(WaveSixDonorIntegrationRisk.MESSY_GLUE_CODE,),
            mitigation_summary="Reject non-donor profiles.",
        )


def test_donor_profile_rejects_duplicate_loop_stages() -> None:
    with pytest.raises(ValueError, match="Duplicate supported loop stage"):
        WaveSixDonorProfile(
            source_system=WaveSixSourceSystem.IX_FUNCTION,
            repo_name="IX-Function",
            primary_role="Invalid duplicate loop-stage profile.",
            supported_loop_stages=(
                WaveSixLoopStage.TRANSFER_CHECK,
                WaveSixLoopStage.TRANSFER_CHECK,
            ),
            supplied_capability_areas=(WaveSixCapabilityArea.CROSS_DOMAIN_TRANSFER,),
            supplied_artifact_kinds=(WaveSixArtifactKind.TRANSFER_NOVELTY_RECORD,),
            default_integration_risks=(WaveSixDonorIntegrationRisk.SCHEMA_DRIFT,),
            mitigation_summary="Reject duplicate loop-stage coverage.",
        )
