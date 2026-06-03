import pytest

from ix_cognition_kernel.wave4_contracts import (
    WAVE_FOUR_REQUIRED_ARTIFACT_KINDS,
    WAVE_FOUR_REQUIRED_CAPABILITY_AREAS,
    WaveFourArtifactBundle,
    WaveFourArtifactDecision,
    WaveFourArtifactKind,
    WaveFourArtifactRef,
    WaveFourAuthorityState,
    WaveFourCapabilityArea,
    WaveFourEvidenceLink,
    WaveFourEvidenceRelation,
    WaveFourSourceSystem,
    required_wave_four_artifact_kinds,
    required_wave_four_capability_areas,
)


def artifact(
    artifact_id: str = "wave4-artifact-001",
    *,
    kind: WaveFourArtifactKind = WaveFourArtifactKind.CONTROLLED_TRIAL,
    capability_area: WaveFourCapabilityArea = (
        WaveFourCapabilityArea.CROSS_DOMAIN_TRANSFER
    ),
    evidence_ids: tuple[str, ...] = ("wave4-evidence-001",),
    decision: WaveFourArtifactDecision = (
        WaveFourArtifactDecision.READY_FOR_CONTROLLED_REVIEW
    ),
    authority_state: WaveFourAuthorityState = (
        WaveFourAuthorityState.HUMAN_REVIEW_REQUIRED
    ),
    source_system: WaveFourSourceSystem = WaveFourSourceSystem.IX_COGNITION_KERNEL,
) -> WaveFourArtifactRef:
    return WaveFourArtifactRef(
        artifact_id=artifact_id,
        kind=kind,
        capability_area=capability_area,
        source_system=source_system,
        summary="Controlled Wave 4 proto-candidate evidence artifact.",
        produced_by_engine_id="proto-candidate-trial-engine",
        produced_by_agent_role_id="evaluator-critic",
        evidence_ids=evidence_ids,
        decision=decision,
        authority_state=authority_state,
    )


def evidence_link(
    artifact_id: str = "wave4-artifact-001",
    evidence_id: str = "wave4-evidence-001",
    *,
    relation: WaveFourEvidenceRelation = WaveFourEvidenceRelation.SUPPORTS,
    source_system: WaveFourSourceSystem = WaveFourSourceSystem.LOCAL_TEST_SUITE,
) -> WaveFourEvidenceLink:
    return WaveFourEvidenceLink(
        evidence_id=evidence_id,
        artifact_id=artifact_id,
        relation=relation,
        summary="A local test evidence record supports the Wave 4 artifact.",
        source_system=source_system,
    )


def test_source_systems_include_control_plane_and_worldtwin_donors() -> None:
    assert WaveFourSourceSystem.IX_BLACKFOX.value == "ix-blackfox"
    assert WaveFourSourceSystem.IX_BLACKFOX_WORLDTWIN.value == "ix-blackfox-worldtwin"
    assert WaveFourSourceSystem.IX_COGNITION_KERNEL.value == "ix-cognition-kernel"


def test_required_wave_four_artifact_kinds_are_locked() -> None:
    assert required_wave_four_artifact_kinds() == WAVE_FOUR_REQUIRED_ARTIFACT_KINDS
    assert len(WAVE_FOUR_REQUIRED_ARTIFACT_KINDS) == 10
    assert WaveFourArtifactKind.CONTROLLED_TRIAL in WAVE_FOUR_REQUIRED_ARTIFACT_KINDS
    assert (
        WaveFourArtifactKind.REWARD_HACKING_AUDIT
        in WAVE_FOUR_REQUIRED_ARTIFACT_KINDS
    )
    assert (
        WaveFourArtifactKind.REPRODUCIBLE_AUDIT_TRAIL
        in WAVE_FOUR_REQUIRED_ARTIFACT_KINDS
    )


def test_required_wave_four_capability_areas_are_locked() -> None:
    assert required_wave_four_capability_areas() == WAVE_FOUR_REQUIRED_CAPABILITY_AREAS
    assert len(WAVE_FOUR_REQUIRED_CAPABILITY_AREAS) == 8
    assert (
        WaveFourCapabilityArea.CROSS_DOMAIN_TRANSFER
        in WAVE_FOUR_REQUIRED_CAPABILITY_AREAS
    )
    assert WaveFourCapabilityArea.SAFE_REFUSAL in WAVE_FOUR_REQUIRED_CAPABILITY_AREAS
    assert (
        WaveFourCapabilityArea.ADVERSARIAL_ROBUSTNESS
        in WAVE_FOUR_REQUIRED_CAPABILITY_AREAS
    )


def test_wave_four_artifact_rejects_automatic_execution() -> None:
    with pytest.raises(ValueError, match="never allow automatic execution"):
        WaveFourArtifactRef(
            artifact_id="wave4-artifact-001",
            kind=WaveFourArtifactKind.REPRODUCIBLE_AUDIT_TRAIL,
            capability_area=WaveFourCapabilityArea.AUDIT_TRAIL,
            source_system=WaveFourSourceSystem.IX_BLACKFOX,
            summary="Invalid automatic execution attempt.",
            produced_by_engine_id="audit-trail-engine",
            evidence_ids=("wave4-evidence-001",),
            decision=WaveFourArtifactDecision.READY_FOR_CONTROLLED_REVIEW,
            allowed_for_automatic_execution=True,
        )


def test_wave_four_artifact_rejects_missing_human_authority_awareness() -> None:
    with pytest.raises(ValueError, match="require human authority"):
        WaveFourArtifactRef(
            artifact_id="wave4-artifact-001",
            kind=WaveFourArtifactKind.CONTROLLED_TRIAL,
            capability_area=WaveFourCapabilityArea.CROSS_DOMAIN_TRANSFER,
            source_system=WaveFourSourceSystem.IX_COGNITION_KERNEL,
            summary="Invalid artifact without human authority awareness.",
            produced_by_engine_id="proto-candidate-trial-engine",
            evidence_ids=("wave4-evidence-001",),
            requires_human_authority=False,
        )


def test_wave_four_artifact_rejects_agi_claims() -> None:
    with pytest.raises(ValueError, match="must not claim AGI"):
        WaveFourArtifactRef(
            artifact_id="wave4-artifact-001",
            kind=WaveFourArtifactKind.CONTROLLED_TRIAL,
            capability_area=WaveFourCapabilityArea.CROSS_DOMAIN_TRANSFER,
            source_system=WaveFourSourceSystem.IX_COGNITION_KERNEL,
            summary="Invalid AGI claim attempt.",
            produced_by_engine_id="proto-candidate-trial-engine",
            evidence_ids=("wave4-evidence-001",),
            claims_agi=True,
        )


def test_wave_four_artifact_rejects_independent_validation_claims() -> None:
    with pytest.raises(ValueError, match="belongs to Wave 5"):
        WaveFourArtifactRef(
            artifact_id="wave4-artifact-001",
            kind=WaveFourArtifactKind.CONTROLLED_TRIAL,
            capability_area=WaveFourCapabilityArea.CROSS_DOMAIN_TRANSFER,
            source_system=WaveFourSourceSystem.EXTERNAL_REVIEW,
            summary="Invalid independent-validation claim attempt.",
            produced_by_engine_id="proto-candidate-trial-engine",
            evidence_ids=("wave4-evidence-001",),
            independently_validated=True,
        )


def test_ready_artifact_requires_evidence_binding() -> None:
    with pytest.raises(ValueError, match="require evidence ids"):
        artifact(evidence_ids=())


def test_blocked_artifact_cannot_carry_granted_authority() -> None:
    with pytest.raises(ValueError, match="cannot carry granted authority"):
        artifact(
            decision=WaveFourArtifactDecision.BLOCKED,
            authority_state=WaveFourAuthorityState.HUMAN_AUTHORITY_GRANTED,
        )


def test_artifact_readiness_and_blocking_properties_are_fail_closed() -> None:
    ready = artifact()
    blocked = artifact(
        artifact_id="wave4-artifact-blocked",
        decision=WaveFourArtifactDecision.BLOCKED,
        authority_state=WaveFourAuthorityState.BLOCKED,
    )

    assert ready.evidence_bound is True
    assert ready.ready_for_controlled_review is True
    assert ready.blocks_progress is False
    assert blocked.ready_for_controlled_review is False
    assert blocked.blocks_progress is True


def test_artifact_fingerprint_is_deterministic() -> None:
    first = artifact().fingerprint()
    second = artifact().fingerprint()

    assert first == second
    assert len(first) == 64


def test_evidence_link_rejects_empty_fields() -> None:
    with pytest.raises(ValueError, match="evidence_id must not be empty"):
        evidence_link(evidence_id=" ")


def test_evidence_link_canonical_payload_preserves_relation_and_source() -> None:
    link = evidence_link(relation=WaveFourEvidenceRelation.TESTS)

    assert link.link_key == ("wave4-evidence-001", "wave4-artifact-001", "tests")
    assert link.canonical_payload()["source_system"] == "local-test-suite"


def test_bundle_rejects_duplicate_artifact_ids() -> None:
    item = artifact()

    with pytest.raises(ValueError, match="Duplicate artifact_id"):
        WaveFourArtifactBundle(
            bundle_id="wave4-bundle-001",
            artifacts=(item, item),
            evidence_links=(evidence_link(),),
        )


def test_bundle_rejects_links_to_unknown_artifacts() -> None:
    with pytest.raises(ValueError, match="reference bundled artifacts"):
        WaveFourArtifactBundle(
            bundle_id="wave4-bundle-001",
            artifacts=(artifact(),),
            evidence_links=(evidence_link(artifact_id="missing-artifact"),),
        )


def test_bundle_rejects_artifact_evidence_without_matching_link() -> None:
    with pytest.raises(ValueError, match="require matching evidence links"):
        WaveFourArtifactBundle(
            bundle_id="wave4-bundle-001",
            artifacts=(artifact(evidence_ids=("missing-evidence",)),),
            evidence_links=(evidence_link(),),
        )


def test_bundle_sorts_artifacts_and_reports_evidence_link_table() -> None:
    later = artifact("wave4-artifact-b", evidence_ids=("wave4-evidence-b",))
    earlier = artifact("wave4-artifact-a", evidence_ids=("wave4-evidence-a",))
    bundle = WaveFourArtifactBundle(
        bundle_id="wave4-bundle-001",
        artifacts=(later, earlier),
        evidence_links=(
            evidence_link("wave4-artifact-b", "wave4-evidence-b"),
            evidence_link("wave4-artifact-a", "wave4-evidence-a"),
        ),
    )

    assert bundle.artifact_ids == ("wave4-artifact-a", "wave4-artifact-b")
    assert bundle.evidence_link_table == {
        "wave4-artifact-a": ("wave4-evidence-a",),
        "wave4-artifact-b": ("wave4-evidence-b",),
    }


def test_bundle_reports_missing_required_kind_coverage_without_faking_readiness() -> (
    None
):
    bundle = WaveFourArtifactBundle(
        bundle_id="wave4-bundle-001",
        artifacts=(artifact(kind=WaveFourArtifactKind.CONTROLLED_TRIAL),),
        evidence_links=(evidence_link(),),
        required_kinds=(
            WaveFourArtifactKind.CONTROLLED_TRIAL,
            WaveFourArtifactKind.REWARD_HACKING_AUDIT,
        ),
    )

    assert bundle.has_required_kind_coverage is False
    assert bundle.missing_required_kinds == (WaveFourArtifactKind.REWARD_HACKING_AUDIT,)


def test_bundle_reports_missing_required_capability_coverage() -> None:
    bundle = WaveFourArtifactBundle(
        bundle_id="wave4-bundle-001",
        artifacts=(
            artifact(capability_area=WaveFourCapabilityArea.CROSS_DOMAIN_TRANSFER),
        ),
        evidence_links=(evidence_link(),),
        required_capability_areas=(
            WaveFourCapabilityArea.CROSS_DOMAIN_TRANSFER,
            WaveFourCapabilityArea.SAFE_REFUSAL,
        ),
    )

    assert bundle.has_required_capability_coverage is False
    assert bundle.missing_required_capability_areas == (
        WaveFourCapabilityArea.SAFE_REFUSAL,
    )


def test_bundle_reports_ready_and_blocked_artifacts() -> None:
    ready = artifact("wave4-artifact-ready")
    blocked = artifact(
        "wave4-artifact-blocked",
        evidence_ids=("wave4-evidence-blocked",),
        decision=WaveFourArtifactDecision.BLOCKED,
        authority_state=WaveFourAuthorityState.BLOCKED,
    )
    bundle = WaveFourArtifactBundle(
        bundle_id="wave4-bundle-001",
        artifacts=(blocked, ready),
        evidence_links=(
            evidence_link("wave4-artifact-ready", "wave4-evidence-001"),
            evidence_link("wave4-artifact-blocked", "wave4-evidence-blocked"),
        ),
    )

    assert bundle.ready_for_controlled_review_artifact_ids == ("wave4-artifact-ready",)
    assert bundle.blocked_artifact_ids == ("wave4-artifact-blocked",)


def test_bundle_can_find_artifacts_by_kind_and_capability_area() -> None:
    transfer = artifact(
        "wave4-transfer",
        kind=WaveFourArtifactKind.TRANSFER_EVALUATION,
        capability_area=WaveFourCapabilityArea.CROSS_DOMAIN_TRANSFER,
        evidence_ids=("wave4-transfer-evidence",),
    )
    refusal = artifact(
        "wave4-refusal",
        kind=WaveFourArtifactKind.SAFE_REFUSAL_RECORD,
        capability_area=WaveFourCapabilityArea.SAFE_REFUSAL,
        evidence_ids=("wave4-refusal-evidence",),
    )
    bundle = WaveFourArtifactBundle(
        bundle_id="wave4-bundle-001",
        artifacts=(refusal, transfer),
        evidence_links=(
            evidence_link("wave4-refusal", "wave4-refusal-evidence"),
            evidence_link("wave4-transfer", "wave4-transfer-evidence"),
        ),
    )

    assert bundle.artifact_ids_by_kind(WaveFourArtifactKind.SAFE_REFUSAL_RECORD) == (
        "wave4-refusal",
    )
    assert bundle.artifact_ids_by_capability_area(
        WaveFourCapabilityArea.SAFE_REFUSAL
    ) == ("wave4-refusal",)


def test_bundle_fingerprint_is_deterministic_despite_input_order() -> None:
    first = WaveFourArtifactBundle(
        bundle_id="wave4-bundle-001",
        artifacts=(
            artifact("wave4-artifact-b", evidence_ids=("wave4-evidence-b",)),
            artifact("wave4-artifact-a", evidence_ids=("wave4-evidence-a",)),
        ),
        evidence_links=(
            evidence_link("wave4-artifact-b", "wave4-evidence-b"),
            evidence_link("wave4-artifact-a", "wave4-evidence-a"),
        ),
    )
    second = WaveFourArtifactBundle(
        bundle_id="wave4-bundle-001",
        artifacts=(
            artifact("wave4-artifact-a", evidence_ids=("wave4-evidence-a",)),
            artifact("wave4-artifact-b", evidence_ids=("wave4-evidence-b",)),
        ),
        evidence_links=(
            evidence_link("wave4-artifact-a", "wave4-evidence-a"),
            evidence_link("wave4-artifact-b", "wave4-evidence-b"),
        ),
    )

    assert first.fingerprint() == second.fingerprint()
    assert len(first.fingerprint()) == 64
