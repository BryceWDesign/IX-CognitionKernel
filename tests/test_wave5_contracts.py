import pytest

from ix_cognition_kernel.wave5_contracts import (
    WAVE_FIVE_EXTERNAL_EVIDENCE_SOURCE_SYSTEMS,
    WAVE_FIVE_REQUIRED_ARTIFACT_KINDS,
    WAVE_FIVE_REQUIRED_CAPABILITY_AREAS,
    WAVE_FIVE_REQUIRED_CLAIM_BOUNDARIES,
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


def artifact(
    artifact_id: str = "wave5-artifact-001",
    *,
    kind: WaveFiveArtifactKind = WaveFiveArtifactKind.EXTERNAL_PROTOCOL_MANIFEST,
    capability_area: WaveFiveCapabilityArea = WaveFiveCapabilityArea.EXTERNAL_PROTOCOLS,
    evidence_ids: tuple[str, ...] = ("wave5-evidence-001",),
    decision: WaveFiveArtifactDecision = (
        WaveFiveArtifactDecision.READY_FOR_INDEPENDENT_REVIEW
    ),
    authority_state: WaveFiveAuthorityState = (
        WaveFiveAuthorityState.HUMAN_REVIEW_REQUIRED
    ),
    validation_status: WaveFiveValidationStatus = (
        WaveFiveValidationStatus.UNDER_INDEPENDENT_REVIEW
    ),
    source_system: WaveFiveSourceSystem = WaveFiveSourceSystem.IX_COGNITION_KERNEL,
    claim_boundaries: tuple[WaveFiveClaimBoundary, ...] = (
        WAVE_FIVE_REQUIRED_CLAIM_BOUNDARIES
    ),
    claims_agi: bool = False,
    claims_production_ready: bool = False,
    claims_certified: bool = False,
    self_validated: bool = False,
) -> WaveFiveArtifactRef:
    return WaveFiveArtifactRef(
        artifact_id=artifact_id,
        kind=kind,
        capability_area=capability_area,
        source_system=source_system,
        summary="Wave 5 independent-validation bridge artifact.",
        produced_by_engine_id="independent-validation-contract-engine",
        produced_by_agent_role_id="external-validation-registrar",
        evidence_ids=evidence_ids,
        decision=decision,
        authority_state=authority_state,
        validation_status=validation_status,
        claim_boundaries=claim_boundaries,
        claims_agi=claims_agi,
        claims_production_ready=claims_production_ready,
        claims_certified=claims_certified,
        self_validated=self_validated,
    )


def evidence_link(
    artifact_id: str = "wave5-artifact-001",
    evidence_id: str = "wave5-evidence-001",
    *,
    relation: WaveFiveEvidenceRelation = WaveFiveEvidenceRelation.SUPPORTS,
    source_system: WaveFiveSourceSystem = WaveFiveSourceSystem.LOCAL_TEST_SUITE,
) -> WaveFiveEvidenceLink:
    return WaveFiveEvidenceLink(
        evidence_id=evidence_id,
        artifact_id=artifact_id,
        relation=relation,
        summary="Evidence supports a Wave 5 independent-validation artifact.",
        source_system=source_system,
    )


def external_evidence_link(
    artifact_id: str = "wave5-artifact-001",
    evidence_id: str = "wave5-external-evidence-001",
) -> WaveFiveEvidenceLink:
    return evidence_link(
        artifact_id=artifact_id,
        evidence_id=evidence_id,
        relation=WaveFiveEvidenceRelation.REPRODUCES,
        source_system=WaveFiveSourceSystem.INDEPENDENT_REPLICATION_LAB,
    )


def test_source_systems_include_kernel_and_all_wave_five_donors() -> None:
    assert WaveFiveSourceSystem.IX_COGNITION_KERNEL.value == "ix-cognition-kernel"
    assert WaveFiveSourceSystem.IX_BLACKFOX.value == "ix-blackfox"
    assert WaveFiveSourceSystem.IX_BLACKFOX_COGNITION.value == "ix-blackfox-cognition"
    assert WaveFiveSourceSystem.IX_BLACKFOX_WORLDTWIN.value == "ix-blackfox-worldtwin"
    assert WaveFiveSourceSystem.INDEPENDENT_REVIEWER.value == "independent-reviewer"


def test_required_wave_five_artifact_kinds_are_locked() -> None:
    assert required_wave_five_artifact_kinds() == WAVE_FIVE_REQUIRED_ARTIFACT_KINDS
    assert len(WAVE_FIVE_REQUIRED_ARTIFACT_KINDS) == 18
    assert (
        WaveFiveArtifactKind.EXTERNAL_PROTOCOL_MANIFEST
        in WAVE_FIVE_REQUIRED_ARTIFACT_KINDS
    )
    assert (
        WaveFiveArtifactKind.WAVE_SIX_PRECONDITION_LEDGER
        in WAVE_FIVE_REQUIRED_ARTIFACT_KINDS
    )
    assert WaveFiveArtifactKind.RELEASE_MANIFEST in WAVE_FIVE_REQUIRED_ARTIFACT_KINDS


def test_required_wave_five_capability_areas_are_locked() -> None:
    assert required_wave_five_capability_areas() == WAVE_FIVE_REQUIRED_CAPABILITY_AREAS
    assert len(WAVE_FIVE_REQUIRED_CAPABILITY_AREAS) == 12
    assert WaveFiveCapabilityArea.INDEPENDENT_REVIEW in (
        WAVE_FIVE_REQUIRED_CAPABILITY_AREAS
    )
    assert WaveFiveCapabilityArea.ECOSYSTEM_TRACEABILITY in (
        WAVE_FIVE_REQUIRED_CAPABILITY_AREAS
    )
    assert WaveFiveCapabilityArea.WAVE_SIX_READINESS_BOUNDARY in (
        WAVE_FIVE_REQUIRED_CAPABILITY_AREAS
    )


def test_required_claim_boundaries_are_locked() -> None:
    assert required_wave_five_claim_boundaries() == WAVE_FIVE_REQUIRED_CLAIM_BOUNDARIES
    assert WaveFiveClaimBoundary.NO_AGI_CLAIM in WAVE_FIVE_REQUIRED_CLAIM_BOUNDARIES
    assert (
        WaveFiveClaimBoundary.NO_SELF_VALIDATION
        in WAVE_FIVE_REQUIRED_CLAIM_BOUNDARIES
    )
    assert (
        WaveFiveClaimBoundary.INDEPENDENT_EVIDENCE_REQUIRED
        in WAVE_FIVE_REQUIRED_CLAIM_BOUNDARIES
    )


def test_external_source_systems_are_explicit_and_not_internal() -> None:
    assert external_wave_five_source_systems() == (
        WAVE_FIVE_EXTERNAL_EVIDENCE_SOURCE_SYSTEMS
    )
    assert WaveFiveSourceSystem.INDEPENDENT_REPLICATION_LAB in (
        WAVE_FIVE_EXTERNAL_EVIDENCE_SOURCE_SYSTEMS
    )
    assert WaveFiveSourceSystem.IX_COGNITION_KERNEL not in (
        WAVE_FIVE_EXTERNAL_EVIDENCE_SOURCE_SYSTEMS
    )


def test_wave_five_artifact_rejects_automatic_execution() -> None:
    with pytest.raises(ValueError, match="never allow automatic execution"):
        WaveFiveArtifactRef(
            artifact_id="wave5-artifact-001",
            kind=WaveFiveArtifactKind.REPRODUCIBLE_EVIDENCE_BUNDLE,
            capability_area=WaveFiveCapabilityArea.REPRODUCIBILITY,
            source_system=WaveFiveSourceSystem.IX_BLACKFOX,
            summary="Invalid automatic execution attempt.",
            produced_by_engine_id="reproducibility-engine",
            evidence_ids=("wave5-evidence-001",),
            allowed_for_automatic_execution=True,
        )


def test_wave_five_artifact_rejects_missing_human_authority_awareness() -> None:
    with pytest.raises(ValueError, match="require human authority"):
        WaveFiveArtifactRef(
            artifact_id="wave5-artifact-001",
            kind=WaveFiveArtifactKind.HUMAN_AUTHORITY_PROOF,
            capability_area=WaveFiveCapabilityArea.HUMAN_AUTHORITY_PRESERVATION,
            source_system=WaveFiveSourceSystem.IX_COGNITION_KERNEL,
            summary="Invalid artifact without human authority awareness.",
            produced_by_engine_id="authority-preservation-engine",
            evidence_ids=("wave5-evidence-001",),
            requires_human_authority=False,
        )


def test_wave_five_artifact_rejects_overclaims() -> None:
    with pytest.raises(ValueError, match="must not claim AGI"):
        artifact(claims_agi=True)

    with pytest.raises(ValueError, match="must not claim production readiness"):
        artifact(claims_production_ready=True)

    with pytest.raises(ValueError, match="must not claim certification"):
        artifact(claims_certified=True)

    with pytest.raises(ValueError, match="must not claim self-validation"):
        artifact(self_validated=True)


def test_wave_five_artifact_requires_locked_claim_boundaries() -> None:
    with pytest.raises(ValueError, match="no-self-validation"):
        artifact(
            claim_boundaries=tuple(
                boundary
                for boundary in WAVE_FIVE_REQUIRED_CLAIM_BOUNDARIES
                if boundary is not WaveFiveClaimBoundary.NO_SELF_VALIDATION
            )
        )


def test_ready_artifact_requires_evidence_binding() -> None:
    with pytest.raises(ValueError, match="require evidence ids"):
        artifact(evidence_ids=())


def test_blocked_artifact_cannot_carry_granted_authority() -> None:
    with pytest.raises(ValueError, match="cannot carry granted authority"):
        artifact(
            decision=WaveFiveArtifactDecision.BLOCKED,
            authority_state=WaveFiveAuthorityState.HUMAN_AUTHORITY_GRANTED,
        )


def test_artifact_readiness_and_blocking_properties_are_fail_closed() -> None:
    ready = artifact()
    disputed = artifact(
        artifact_id="wave5-artifact-disputed",
        validation_status=WaveFiveValidationStatus.DISPUTED,
    )

    assert ready.evidence_bound is True
    assert ready.ready_for_independent_review is True
    assert ready.blocks_progress is False
    assert disputed.ready_for_independent_review is True
    assert disputed.blocks_progress is True


def test_artifact_fingerprint_is_deterministic() -> None:
    first = artifact().fingerprint()
    second = artifact().fingerprint()

    assert first == second
    assert len(first) == 64


def test_evidence_link_rejects_empty_fields() -> None:
    with pytest.raises(ValueError, match="evidence_id must not be empty"):
        evidence_link(evidence_id=" ")


def test_evidence_link_canonical_payload_preserves_relation_and_source() -> None:
    link = external_evidence_link()

    assert link.link_key == (
        "wave5-external-evidence-001",
        "wave5-artifact-001",
        "reproduces",
    )
    assert link.is_external_validation_evidence is True
    assert link.canonical_payload()["source_system"] == "independent-replication-lab"


def test_bundle_rejects_duplicate_artifact_ids() -> None:
    item = artifact()

    with pytest.raises(ValueError, match="Duplicate artifact_id"):
        WaveFiveArtifactBundle(
            bundle_id="wave5-bundle-001",
            artifacts=(item, item),
            evidence_links=(evidence_link(),),
        )


def test_bundle_rejects_links_to_unknown_artifacts() -> None:
    with pytest.raises(ValueError, match="reference bundled artifacts"):
        WaveFiveArtifactBundle(
            bundle_id="wave5-bundle-001",
            artifacts=(artifact(),),
            evidence_links=(evidence_link(artifact_id="missing-artifact"),),
        )


def test_bundle_rejects_artifact_evidence_without_matching_link() -> None:
    with pytest.raises(ValueError, match="require matching evidence links"):
        WaveFiveArtifactBundle(
            bundle_id="wave5-bundle-001",
            artifacts=(artifact(evidence_ids=("missing-evidence",)),),
            evidence_links=(evidence_link(),),
        )


def test_bundle_rejects_external_validation_without_external_evidence() -> None:
    externally_validated = artifact(
        decision=WaveFiveArtifactDecision.EXTERNALLY_REVIEWED,
        validation_status=WaveFiveValidationStatus.ACCEPTED_WITH_BOUNDARIES,
    )

    with pytest.raises(ValueError, match="require external evidence links"):
        WaveFiveArtifactBundle(
            bundle_id="wave5-bundle-001",
            artifacts=(externally_validated,),
            evidence_links=(evidence_link(),),
        )


def test_bundle_allows_bounded_external_validation_with_external_evidence() -> None:
    externally_validated = artifact(
        decision=WaveFiveArtifactDecision.EXTERNALLY_REVIEWED,
        validation_status=WaveFiveValidationStatus.ACCEPTED_WITH_BOUNDARIES,
        evidence_ids=("wave5-external-evidence-001",),
    )
    bundle = WaveFiveArtifactBundle(
        bundle_id="wave5-bundle-001",
        artifacts=(externally_validated,),
        evidence_links=(external_evidence_link(),),
    )

    assert bundle.externally_validated_artifact_ids == ("wave5-artifact-001",)
    assert bundle.missing_external_evidence_artifact_ids == ()
    assert bundle.external_evidence_link_table == {
        "wave5-artifact-001": ("wave5-external-evidence-001",)
    }


def test_bundle_sorts_artifacts_and_reports_evidence_link_table() -> None:
    later = artifact("wave5-artifact-b", evidence_ids=("wave5-evidence-b",))
    earlier = artifact("wave5-artifact-a", evidence_ids=("wave5-evidence-a",))
    bundle = WaveFiveArtifactBundle(
        bundle_id="wave5-bundle-001",
        artifacts=(later, earlier),
        evidence_links=(
            evidence_link("wave5-artifact-b", "wave5-evidence-b"),
            evidence_link("wave5-artifact-a", "wave5-evidence-a"),
        ),
    )

    assert bundle.artifact_ids == ("wave5-artifact-a", "wave5-artifact-b")
    assert bundle.evidence_link_table == {
        "wave5-artifact-a": ("wave5-evidence-a",),
        "wave5-artifact-b": ("wave5-evidence-b",),
    }


def test_bundle_reports_missing_required_coverage_without_faking_readiness() -> None:
    bundle = WaveFiveArtifactBundle(
        bundle_id="wave5-bundle-001",
        artifacts=(artifact(kind=WaveFiveArtifactKind.EXTERNAL_PROTOCOL_MANIFEST),),
        evidence_links=(evidence_link(),),
        required_kinds=(
            WaveFiveArtifactKind.EXTERNAL_PROTOCOL_MANIFEST,
            WaveFiveArtifactKind.REVIEWER_ATTESTATION,
        ),
        required_capability_areas=(
            WaveFiveCapabilityArea.EXTERNAL_PROTOCOLS,
            WaveFiveCapabilityArea.INDEPENDENT_REVIEW,
        ),
        required_claim_boundaries=WAVE_FIVE_REQUIRED_CLAIM_BOUNDARIES,
    )

    assert bundle.has_required_kind_coverage is False
    assert bundle.missing_required_kinds == (WaveFiveArtifactKind.REVIEWER_ATTESTATION,)
    assert bundle.has_required_capability_coverage is False
    assert bundle.missing_required_capability_areas == (
        WaveFiveCapabilityArea.INDEPENDENT_REVIEW,
    )
    assert bundle.has_required_claim_boundary_coverage is True


def test_bundle_fingerprint_is_deterministic() -> None:
    bundle = WaveFiveArtifactBundle(
        bundle_id="wave5-bundle-001",
        artifacts=(artifact(),),
        evidence_links=(evidence_link(),),
        notes=("Preserves Wave 6 precondition boundary without claiming AGI.",),
    )

    assert bundle.fingerprint() == bundle.fingerprint()
    assert len(bundle.fingerprint()) == 64
