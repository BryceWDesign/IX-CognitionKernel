import pytest

from ix_cognition_kernel.wave5_contracts import (
    WaveFiveArtifactBundle,
    WaveFiveArtifactDecision,
    WaveFiveArtifactKind,
    WaveFiveArtifactRef,
    WaveFiveAuthorityState,
    WaveFiveCapabilityArea,
    WaveFiveClaimBoundary,
    WaveFiveEvidenceLink,
    WaveFiveEvidenceRelation,
    WaveFiveSourceSystem,
    WaveFiveValidationStatus,
    external_wave_five_source_systems,
    required_wave_five_artifact_kinds,
    required_wave_five_capability_areas,
    required_wave_five_claim_boundaries,
)


def _artifact_ref(
    *,
    artifact_id: str = "artifact-1",
    kind: WaveFiveArtifactKind = WaveFiveArtifactKind.EXTERNAL_PROTOCOL_MANIFEST,
    capability_area: WaveFiveCapabilityArea = (
        WaveFiveCapabilityArea.EXTERNAL_PROTOCOLS
    ),
    evidence_ids: tuple[str, ...] = ("evidence-1",),
    decision: WaveFiveArtifactDecision = (
        WaveFiveArtifactDecision.READY_FOR_INDEPENDENT_REVIEW
    ),
    validation_status: WaveFiveValidationStatus = (
        WaveFiveValidationStatus.UNDER_INDEPENDENT_REVIEW
    ),
    source_system: WaveFiveSourceSystem = WaveFiveSourceSystem.IX_COGNITION_KERNEL,
) -> WaveFiveArtifactRef:
    return WaveFiveArtifactRef(
        artifact_id=artifact_id,
        kind=kind,
        capability_area=capability_area,
        source_system=source_system,
        summary="Reviewable Wave 5 artifact.",
        produced_by_engine_id="engine-1",
        produced_by_agent_role_id="agent-role-1",
        evidence_ids=evidence_ids,
        decision=decision,
        authority_state=WaveFiveAuthorityState.HUMAN_REVIEW_REQUIRED,
        validation_status=validation_status,
    )


def _evidence_link(
    *,
    evidence_id: str = "evidence-1",
    artifact_id: str = "artifact-1",
    source_system: WaveFiveSourceSystem = WaveFiveSourceSystem.EXTERNAL_REVIEW,
) -> WaveFiveEvidenceLink:
    return WaveFiveEvidenceLink(
        evidence_id=evidence_id,
        artifact_id=artifact_id,
        relation=WaveFiveEvidenceRelation.SUPPORTS,
        summary="Evidence supports the artifact.",
        source_system=source_system,
    )


def test_required_wave_five_contract_sets_are_locked() -> None:
    assert len(required_wave_five_artifact_kinds()) >= 10
    assert len(required_wave_five_capability_areas()) >= 10
    assert WaveFiveClaimBoundary.NO_AGI_CLAIM in required_wave_five_claim_boundaries()
    assert (
        WaveFiveSourceSystem.INDEPENDENT_REVIEWER
        in external_wave_five_source_systems()
    )


def test_artifact_ref_ready_for_independent_review_when_evidence_bound() -> None:
    artifact = _artifact_ref()

    assert artifact.evidence_bound
    assert artifact.ready_for_independent_review
    assert artifact.needs_external_evidence
    assert not artifact.blocks_progress
    assert artifact.fingerprint() == artifact.fingerprint()


def test_artifact_ref_rejects_forbidden_claims() -> None:
    with pytest.raises(ValueError, match="must not claim AGI"):
        WaveFiveArtifactRef(
            artifact_id="artifact-claim",
            kind=WaveFiveArtifactKind.MATURITY_DECLARATION,
            capability_area=WaveFiveCapabilityArea.WAVE_SIX_READINESS_BOUNDARY,
            source_system=WaveFiveSourceSystem.IX_COGNITION_KERNEL,
            summary="Invalid artifact.",
            produced_by_engine_id="engine-1",
            evidence_ids=("evidence-1",),
            claims_agi=True,
        )


def test_artifact_ref_requires_evidence_when_ready_for_review() -> None:
    with pytest.raises(ValueError, match="require evidence ids"):
        _artifact_ref(evidence_ids=())


def test_artifact_ref_requires_all_claim_boundaries() -> None:
    with pytest.raises(ValueError, match="required claim boundary"):
        WaveFiveArtifactRef(
            artifact_id="artifact-boundary",
            kind=WaveFiveArtifactKind.RELEASE_MANIFEST,
            capability_area=WaveFiveCapabilityArea.ECOSYSTEM_TRACEABILITY,
            source_system=WaveFiveSourceSystem.IX_COGNITION_KERNEL,
            summary="Missing required boundaries.",
            produced_by_engine_id="engine-1",
            evidence_ids=("evidence-1",),
            claim_boundaries=(WaveFiveClaimBoundary.NO_AGI_CLAIM,),
        )


def test_artifact_bundle_accepts_matching_evidence_links() -> None:
    artifact = _artifact_ref()
    link = _evidence_link()

    bundle = WaveFiveArtifactBundle(
        bundle_id="bundle-1",
        artifacts=(artifact,),
        evidence_links=(link,),
        required_kinds=(WaveFiveArtifactKind.EXTERNAL_PROTOCOL_MANIFEST,),
        required_capability_areas=(WaveFiveCapabilityArea.EXTERNAL_PROTOCOLS,),
        required_claim_boundaries=required_wave_five_claim_boundaries(),
        notes=("bundle is reviewable",),
    )

    assert bundle.artifact_ids == ("artifact-1",)
    assert bundle.ready_for_independent_review_artifact_ids == ("artifact-1",)
    assert bundle.missing_required_kinds == ()
    assert bundle.has_required_kind_coverage
    assert bundle.has_required_capability_coverage
    assert bundle.has_required_claim_boundary_coverage
    assert bundle.evidence_link_table == {"artifact-1": ("evidence-1",)}
    assert bundle.fingerprint() == bundle.fingerprint()


def test_artifact_bundle_rejects_missing_evidence_links() -> None:
    artifact = _artifact_ref(evidence_ids=("missing-evidence",))
    link = _evidence_link(evidence_id="different-evidence")

    with pytest.raises(ValueError, match="matching evidence links"):
        WaveFiveArtifactBundle(
            bundle_id="bundle-missing-link",
            artifacts=(artifact,),
            evidence_links=(link,),
        )


def test_artifact_bundle_rejects_links_to_unknown_artifacts() -> None:
    artifact = _artifact_ref()
    link = _evidence_link(artifact_id="unknown-artifact")

    with pytest.raises(ValueError, match="bundled artifacts"):
        WaveFiveArtifactBundle(
            bundle_id="bundle-unknown-link",
            artifacts=(artifact,),
            evidence_links=(link,),
        )


def test_externally_validated_artifact_requires_external_link() -> None:
    artifact = _artifact_ref(
        decision=WaveFiveArtifactDecision.EXTERNALLY_REVIEWED,
        validation_status=WaveFiveValidationStatus.ACCEPTED_WITH_BOUNDARIES,
    )
    internal_link = _evidence_link(
        source_system=WaveFiveSourceSystem.IX_COGNITION_KERNEL
    )

    with pytest.raises(ValueError, match="external evidence links"):
        WaveFiveArtifactBundle(
            bundle_id="bundle-no-external-link",
            artifacts=(artifact,),
            evidence_links=(internal_link,),
        )


def test_artifact_bundle_reports_missing_required_coverage() -> None:
    artifact = _artifact_ref()
    link = _evidence_link()

    bundle = WaveFiveArtifactBundle(
        bundle_id="bundle-missing-required",
        artifacts=(artifact,),
        evidence_links=(link,),
        required_kinds=(
            WaveFiveArtifactKind.EXTERNAL_PROTOCOL_MANIFEST,
            WaveFiveArtifactKind.REVIEWER_ATTESTATION,
        ),
        required_capability_areas=(
            WaveFiveCapabilityArea.EXTERNAL_PROTOCOLS,
            WaveFiveCapabilityArea.INDEPENDENT_REVIEW,
        ),
    )

    assert bundle.missing_required_kinds == (
        WaveFiveArtifactKind.REVIEWER_ATTESTATION,
    )
    assert bundle.missing_required_capability_areas == (
        WaveFiveCapabilityArea.INDEPENDENT_REVIEW,
    )
    assert not bundle.has_required_kind_coverage
    assert not bundle.has_required_capability_coverage
