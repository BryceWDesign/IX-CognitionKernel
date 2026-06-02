import pytest

from ix_cognition_kernel.wave3_contracts import (
    WAVE_THREE_REQUIRED_ARTIFACT_KINDS,
    WaveThreeArtifactBundle,
    WaveThreeArtifactDecision,
    WaveThreeArtifactKind,
    WaveThreeArtifactRef,
    WaveThreeAuthorityState,
    WaveThreeEvidenceLink,
    WaveThreeEvidenceRelation,
    WaveThreeSourceSystem,
    required_wave_three_artifact_kinds,
)


def artifact(
    artifact_id: str = "artifact-001",
    *,
    kind: WaveThreeArtifactKind = WaveThreeArtifactKind.ENGINE_COORDINATION,
    evidence_ids: tuple[str, ...] = ("evidence-001",),
    decision: WaveThreeArtifactDecision = (
        WaveThreeArtifactDecision.READY_FOR_HUMAN_REVIEW
    ),
    authority_state: WaveThreeAuthorityState = (
        WaveThreeAuthorityState.HUMAN_REVIEW_REQUIRED
    ),
    source_system: WaveThreeSourceSystem = WaveThreeSourceSystem.IX_COGNITION_KERNEL,
) -> WaveThreeArtifactRef:
    return WaveThreeArtifactRef(
        artifact_id=artifact_id,
        kind=kind,
        source_system=source_system,
        summary="Structured artifact for Wave 3 substrate coordination.",
        produced_by_engine_id="belief",
        produced_by_agent_role_id="belief-curator",
        evidence_ids=evidence_ids,
        decision=decision,
        authority_state=authority_state,
    )


def evidence_link(
    artifact_id: str = "artifact-001",
    evidence_id: str = "evidence-001",
    *,
    relation: WaveThreeEvidenceRelation = WaveThreeEvidenceRelation.SUPPORTS,
    source_system: WaveThreeSourceSystem = WaveThreeSourceSystem.LOCAL_TEST_SUITE,
) -> WaveThreeEvidenceLink:
    return WaveThreeEvidenceLink(
        evidence_id=evidence_id,
        artifact_id=artifact_id,
        relation=relation,
        summary="A local test evidence record supports the artifact.",
        source_system=source_system,
    )


def test_source_systems_include_green_donor_repos() -> None:
    assert WaveThreeSourceSystem.IX_BLACKFOX.value == "ix-blackfox"
    assert WaveThreeSourceSystem.IX_BLACKFOX_COGNITION.value == "ix-blackfox-cognition"
    assert WaveThreeSourceSystem.IX_BLACKFOX_WORLDTWIN.value == "ix-blackfox-worldtwin"


def test_required_wave_three_artifact_kinds_are_locked() -> None:
    assert required_wave_three_artifact_kinds() == WAVE_THREE_REQUIRED_ARTIFACT_KINDS
    assert len(WAVE_THREE_REQUIRED_ARTIFACT_KINDS) == 12
    assert WaveThreeArtifactKind.BLACKFOX_HANDOFF in WAVE_THREE_REQUIRED_ARTIFACT_KINDS
    assert (
        WaveThreeArtifactKind.WORLDTWIN_SCENARIO in WAVE_THREE_REQUIRED_ARTIFACT_KINDS
    )
    assert WaveThreeArtifactKind.ASSURANCE_RECORD in WAVE_THREE_REQUIRED_ARTIFACT_KINDS


def test_wave_three_artifact_rejects_automatic_execution() -> None:
    with pytest.raises(ValueError, match="never allow automatic execution"):
        WaveThreeArtifactRef(
            artifact_id="artifact-001",
            kind=WaveThreeArtifactKind.BLACKFOX_HANDOFF,
            source_system=WaveThreeSourceSystem.IX_BLACKFOX,
            summary="Invalid automatic execution attempt.",
            produced_by_engine_id="blackfox-handoff",
            produced_by_agent_role_id="execution-liaison",
            evidence_ids=("evidence-001",),
            decision=WaveThreeArtifactDecision.READY_FOR_HUMAN_REVIEW,
            allowed_for_automatic_execution=True,
        )


def test_wave_three_artifact_rejects_missing_human_authority_awareness() -> None:
    with pytest.raises(ValueError, match="require human authority"):
        WaveThreeArtifactRef(
            artifact_id="artifact-001",
            kind=WaveThreeArtifactKind.ROLE_ARTIFACT,
            source_system=WaveThreeSourceSystem.IX_COGNITION_KERNEL,
            summary="Invalid artifact without human authority awareness.",
            produced_by_engine_id="multi-agent-tribunal",
            evidence_ids=("evidence-001",),
            requires_human_authority=False,
        )


def test_ready_artifact_requires_evidence_binding() -> None:
    with pytest.raises(ValueError, match="require evidence ids"):
        artifact(evidence_ids=())


def test_blocked_artifact_cannot_carry_granted_authority() -> None:
    with pytest.raises(ValueError, match="cannot carry granted authority"):
        artifact(
            decision=WaveThreeArtifactDecision.BLOCKED,
            authority_state=WaveThreeAuthorityState.HUMAN_AUTHORITY_GRANTED,
        )


def test_artifact_readiness_and_blocking_properties_are_fail_closed() -> None:
    ready = artifact()
    blocked = artifact(
        artifact_id="artifact-blocked",
        decision=WaveThreeArtifactDecision.BLOCKED,
        authority_state=WaveThreeAuthorityState.BLOCKED,
    )

    assert ready.evidence_bound is True
    assert ready.ready_for_human_review is True
    assert ready.blocks_progress is False
    assert blocked.ready_for_human_review is False
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
    link = evidence_link(relation=WaveThreeEvidenceRelation.TESTS)

    assert link.link_key == ("evidence-001", "artifact-001", "tests")
    assert link.canonical_payload()["source_system"] == "local-test-suite"


def test_bundle_rejects_duplicate_artifact_ids() -> None:
    item = artifact()

    with pytest.raises(ValueError, match="Duplicate artifact_id"):
        WaveThreeArtifactBundle(
            bundle_id="bundle-001",
            artifacts=(item, item),
            evidence_links=(evidence_link(),),
        )


def test_bundle_rejects_links_to_unknown_artifacts() -> None:
    with pytest.raises(ValueError, match="reference bundled artifacts"):
        WaveThreeArtifactBundle(
            bundle_id="bundle-001",
            artifacts=(artifact(),),
            evidence_links=(evidence_link(artifact_id="missing-artifact"),),
        )


def test_bundle_rejects_artifact_evidence_without_matching_link() -> None:
    with pytest.raises(ValueError, match="require matching evidence links"):
        WaveThreeArtifactBundle(
            bundle_id="bundle-001",
            artifacts=(artifact(evidence_ids=("evidence-missing",)),),
            evidence_links=(evidence_link(),),
        )


def test_bundle_sorts_artifacts_and_reports_evidence_link_table() -> None:
    later = artifact("artifact-b", evidence_ids=("evidence-b",))
    earlier = artifact("artifact-a", evidence_ids=("evidence-a",))
    bundle = WaveThreeArtifactBundle(
        bundle_id="bundle-001",
        artifacts=(later, earlier),
        evidence_links=(
            evidence_link("artifact-b", "evidence-b"),
            evidence_link("artifact-a", "evidence-a"),
        ),
    )

    assert bundle.artifact_ids == ("artifact-a", "artifact-b")
    assert bundle.evidence_link_table == {
        "artifact-a": ("evidence-a",),
        "artifact-b": ("evidence-b",),
    }


def test_bundle_reports_missing_required_kind_coverage_without_faking_readiness() -> (
    None
):
    bundle = WaveThreeArtifactBundle(
        bundle_id="bundle-001",
        artifacts=(artifact(kind=WaveThreeArtifactKind.ENGINE_COORDINATION),),
        evidence_links=(evidence_link(),),
        required_kinds=(
            WaveThreeArtifactKind.ENGINE_COORDINATION,
            WaveThreeArtifactKind.BLACKFOX_HANDOFF,
        ),
    )

    assert bundle.has_required_kind_coverage is False
    assert bundle.missing_required_kinds == (WaveThreeArtifactKind.BLACKFOX_HANDOFF,)


def test_bundle_reports_ready_and_blocked_artifacts() -> None:
    ready = artifact("artifact-ready")
    blocked = artifact(
        "artifact-blocked",
        evidence_ids=("evidence-blocked",),
        decision=WaveThreeArtifactDecision.BLOCKED,
        authority_state=WaveThreeAuthorityState.BLOCKED,
    )
    bundle = WaveThreeArtifactBundle(
        bundle_id="bundle-001",
        artifacts=(blocked, ready),
        evidence_links=(
            evidence_link("artifact-ready", "evidence-001"),
            evidence_link("artifact-blocked", "evidence-blocked"),
        ),
    )

    assert bundle.ready_for_human_review_artifact_ids == ("artifact-ready",)
    assert bundle.blocked_artifact_ids == ("artifact-blocked",)


def test_bundle_fingerprint_is_deterministic_despite_input_order() -> None:
    first = WaveThreeArtifactBundle(
        bundle_id="bundle-001",
        artifacts=(
            artifact("artifact-b", evidence_ids=("evidence-b",)),
            artifact("artifact-a", evidence_ids=("evidence-a",)),
        ),
        evidence_links=(
            evidence_link("artifact-b", "evidence-b"),
            evidence_link("artifact-a", "evidence-a"),
        ),
    )
    second = WaveThreeArtifactBundle(
        bundle_id="bundle-001",
        artifacts=(
            artifact("artifact-a", evidence_ids=("evidence-a",)),
            artifact("artifact-b", evidence_ids=("evidence-b",)),
        ),
        evidence_links=(
            evidence_link("artifact-a", "evidence-a"),
            evidence_link("artifact-b", "evidence-b"),
        ),
    )

    assert first.fingerprint() == second.fingerprint()
    assert len(first.fingerprint()) == 64
