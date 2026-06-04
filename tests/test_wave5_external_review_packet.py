import pytest

from ix_cognition_kernel.wave5_contracts import (
    WAVE_FIVE_REQUIRED_CLAIM_BOUNDARIES,
    WaveFiveArtifactDecision,
    WaveFiveArtifactKind,
    WaveFiveAuthorityState,
    WaveFiveCapabilityArea,
    WaveFiveClaimBoundary,
    WaveFiveSourceSystem,
    WaveFiveValidationStatus,
)
from ix_cognition_kernel.wave5_external_review_packet import (
    BLOCKING_REVIEW_SECTION_STATUSES,
    EXTERNAL_REVIEW_PACKET_SOURCE_SYSTEMS,
    REQUIRED_REVIEW_CHALLENGES,
    REQUIRED_REVIEW_PACKET_SECTIONS,
    SAFE_REVIEW_SECTION_STATUSES,
    WaveFiveExternalReviewPacket,
    WaveFiveExternalReviewPacketState,
    WaveFiveReviewChallengeKind,
    WaveFiveReviewChallengeStatus,
    WaveFiveReviewDisposition,
    WaveFiveReviewDispositionKind,
    WaveFiveReviewPacketSection,
    WaveFiveReviewPacketSectionKind,
    WaveFiveReviewPacketSectionStatus,
    WaveFiveReviewerChallenge,
    blocking_review_section_statuses,
    external_review_packet_source_systems,
    required_review_packet_sections,
    required_reviewer_challenges,
    safe_review_section_statuses,
)


def packet_section(
    section_id: str = "section-reviewer-instructions",
    *,
    section_kind: WaveFiveReviewPacketSectionKind = (
        WaveFiveReviewPacketSectionKind.REVIEWER_INSTRUCTIONS
    ),
    status: WaveFiveReviewPacketSectionStatus = (
        WaveFiveReviewPacketSectionStatus.INCLUDED
    ),
    limitations: tuple[str, ...] = (),
    claim_boundaries: tuple[WaveFiveClaimBoundary, ...] = (
        WAVE_FIVE_REQUIRED_CLAIM_BOUNDARIES
    ),
) -> WaveFiveReviewPacketSection:
    return WaveFiveReviewPacketSection(
        section_id=section_id,
        section_kind=section_kind,
        status=status,
        artifact_ids=(f"artifact-{section_id}",),
        evidence_ids=(f"evidence-{section_id}",),
        reviewer_instruction=(
            "Review this section as bounded Wave 5 evidence only."
        ),
        limitations=limitations,
        claim_boundaries=claim_boundaries,
    )


def challenge(
    challenge_id: str = "challenge-reproduce-evidence",
    *,
    challenge_kind: WaveFiveReviewChallengeKind = (
        WaveFiveReviewChallengeKind.REPRODUCE_EVIDENCE
    ),
    status: WaveFiveReviewChallengeStatus = WaveFiveReviewChallengeStatus.READY,
    blocking: bool = True,
) -> WaveFiveReviewerChallenge:
    return WaveFiveReviewerChallenge(
        challenge_id=challenge_id,
        challenge_kind=challenge_kind,
        status=status,
        prompt="Try to break the evidence trail and record the result.",
        expected_evidence_ids=(f"evidence-{challenge_id}",),
        blocking=blocking,
    )


def disposition(
    disposition_id: str = "disposition-packet-ready",
    *,
    disposition_kind: WaveFiveReviewDispositionKind = (
        WaveFiveReviewDispositionKind.PACKET_READY_FOR_EXTERNAL_REVIEW
    ),
    reviewer_ids: tuple[str, ...] = (),
    dissent_ids: tuple[str, ...] = (),
    blocker_ids: tuple[str, ...] = (),
) -> WaveFiveReviewDisposition:
    return WaveFiveReviewDisposition(
        disposition_id=disposition_id,
        disposition_kind=disposition_kind,
        reviewer_ids=reviewer_ids,
        summary="Review disposition preserves boundaries and dissent visibility.",
        evidence_ids=(f"evidence-{disposition_id}",),
        dissent_ids=dissent_ids,
        blocker_ids=blocker_ids,
    )


def required_sections() -> tuple[WaveFiveReviewPacketSection, ...]:
    return tuple(
        packet_section(
            f"section-{section_kind.value}",
            section_kind=section_kind,
            status=WaveFiveReviewPacketSectionStatus.INCLUDED_WITH_LIMITS,
            limitations=("External review packet is not independent validation.",),
        )
        for section_kind in REQUIRED_REVIEW_PACKET_SECTIONS
    )


def required_challenges() -> tuple[WaveFiveReviewerChallenge, ...]:
    return tuple(
        challenge(f"challenge-{challenge_kind.value}", challenge_kind=challenge_kind)
        for challenge_kind in REQUIRED_REVIEW_CHALLENGES
    )


def packet(
    *,
    source_system: WaveFiveSourceSystem = WaveFiveSourceSystem.IX_COGNITION_KERNEL,
    packet_state: WaveFiveExternalReviewPacketState = (
        WaveFiveExternalReviewPacketState.READY_FOR_EXTERNAL_REVIEW
    ),
    sections: tuple[WaveFiveReviewPacketSection, ...] | None = None,
    challenges: tuple[WaveFiveReviewerChallenge, ...] | None = None,
    dispositions: tuple[WaveFiveReviewDisposition, ...] = (
        disposition(),
    ),
    reviewer_ids: tuple[str, ...] = (),
    attempted_wave_six_promotion: bool = False,
    claims_agi: bool = False,
    grants_execution_authority: bool = False,
    claims_production_ready: bool = False,
    claims_certified: bool = False,
    claims_independent_validation: bool = False,
    claim_boundaries: tuple[WaveFiveClaimBoundary, ...] = (
        WAVE_FIVE_REQUIRED_CLAIM_BOUNDARIES
    ),
) -> WaveFiveExternalReviewPacket:
    resolved_sections = required_sections() if sections is None else sections
    resolved_challenges = required_challenges() if challenges is None else challenges
    return WaveFiveExternalReviewPacket(
        packet_id="wave5-external-review-packet-001",
        title="Wave 5 external review packet for Wave 6 readiness scrutiny.",
        source_system=source_system,
        packet_state=packet_state,
        sections=resolved_sections,
        challenges=resolved_challenges,
        dispositions=dispositions,
        protocol_ids=("wave5-external-protocol-001",),
        reviewer_ids=reviewer_ids,
        attempted_wave_six_promotion=attempted_wave_six_promotion,
        claims_agi=claims_agi,
        grants_execution_authority=grants_execution_authority,
        claims_production_ready=claims_production_ready,
        claims_certified=claims_certified,
        claims_independent_validation=claims_independent_validation,
        claim_boundaries=claim_boundaries,
        notes=("Packet readiness is not Wave 6, AGI, or independent validation.",),
    )


def test_required_review_packet_sections_are_locked() -> None:
    assert required_review_packet_sections() == REQUIRED_REVIEW_PACKET_SECTIONS
    assert len(REQUIRED_REVIEW_PACKET_SECTIONS) == 12
    assert WaveFiveReviewPacketSectionKind.DISSENT_AND_GAP_LOG in (
        REQUIRED_REVIEW_PACKET_SECTIONS
    )


def test_required_reviewer_challenges_are_locked() -> None:
    assert required_reviewer_challenges() == REQUIRED_REVIEW_CHALLENGES
    assert len(REQUIRED_REVIEW_CHALLENGES) == 10
    assert WaveFiveReviewChallengeKind.BLOCK_WAVE_SIX_IF_NEEDED in (
        REQUIRED_REVIEW_CHALLENGES
    )


def test_safe_and_blocking_section_statuses_are_locked() -> None:
    assert safe_review_section_statuses() == SAFE_REVIEW_SECTION_STATUSES
    assert blocking_review_section_statuses() == BLOCKING_REVIEW_SECTION_STATUSES
    assert WaveFiveReviewPacketSectionStatus.INCLUDED in (
        SAFE_REVIEW_SECTION_STATUSES
    )
    assert WaveFiveReviewPacketSectionStatus.DISPUTED in (
        BLOCKING_REVIEW_SECTION_STATUSES
    )


def test_external_review_packet_sources_are_locked() -> None:
    assert external_review_packet_source_systems() == (
        EXTERNAL_REVIEW_PACKET_SOURCE_SYSTEMS
    )
    assert WaveFiveSourceSystem.INDEPENDENT_REVIEWER in (
        EXTERNAL_REVIEW_PACKET_SOURCE_SYSTEMS
    )
    assert WaveFiveSourceSystem.IX_COGNITION_KERNEL not in (
        EXTERNAL_REVIEW_PACKET_SOURCE_SYSTEMS
    )


def test_packet_section_requires_artifacts_and_evidence() -> None:
    with pytest.raises(ValueError, match="artifact ids"):
        WaveFiveReviewPacketSection(
            section_id="section-invalid",
            section_kind=WaveFiveReviewPacketSectionKind.EVIDENCE_DOSSIER,
            status=WaveFiveReviewPacketSectionStatus.INCLUDED,
            artifact_ids=(),
            evidence_ids=("evidence",),
            reviewer_instruction="Review evidence.",
        )

    with pytest.raises(ValueError, match="evidence ids"):
        WaveFiveReviewPacketSection(
            section_id="section-invalid",
            section_kind=WaveFiveReviewPacketSectionKind.EVIDENCE_DOSSIER,
            status=WaveFiveReviewPacketSectionStatus.INCLUDED,
            artifact_ids=("artifact",),
            evidence_ids=(),
            reviewer_instruction="Review evidence.",
        )


def test_limited_packet_section_requires_limitations() -> None:
    with pytest.raises(ValueError, match="require limits"):
        packet_section(status=WaveFiveReviewPacketSectionStatus.INCLUDED_WITH_LIMITS)


def test_packet_section_rejects_missing_claim_boundary() -> None:
    with pytest.raises(ValueError, match="no-self-validation"):
        packet_section(
            claim_boundaries=tuple(
                boundary
                for boundary in WAVE_FIVE_REQUIRED_CLAIM_BOUNDARIES
                if boundary is not WaveFiveClaimBoundary.NO_SELF_VALIDATION
            )
        )


def test_blocking_packet_section_status_blocks_readiness() -> None:
    item = packet_section(status=WaveFiveReviewPacketSectionStatus.DISPUTED)

    assert item.blocks_packet_readiness is True
    assert item.reviewable_with_boundaries is False


def test_reviewer_challenge_requires_expected_evidence() -> None:
    with pytest.raises(ValueError, match="expected evidence ids"):
        WaveFiveReviewerChallenge(
            challenge_id="challenge-invalid",
            challenge_kind=WaveFiveReviewChallengeKind.RECORD_DISSENT,
            status=WaveFiveReviewChallengeStatus.READY,
            prompt="Record dissent.",
            expected_evidence_ids=(),
        )


def test_blocked_challenge_blocks_packet_readiness() -> None:
    item = challenge(status=WaveFiveReviewChallengeStatus.BLOCKED)

    assert item.ready_for_review is False
    assert item.blocks_packet_readiness is True


def test_non_blocking_challenge_does_not_block_readiness() -> None:
    item = challenge(
        status=WaveFiveReviewChallengeStatus.NEEDS_MORE_EVIDENCE,
        blocking=False,
    )

    assert item.blocks_packet_readiness is False


def test_external_disposition_requires_reviewer_ids() -> None:
    with pytest.raises(ValueError, match="require reviewers"):
        disposition(
            disposition_kind=(
                WaveFiveReviewDispositionKind.EXTERNALLY_REVIEWED_WITH_BOUNDARIES
            )
        )


def test_disputed_disposition_requires_dissent_ids() -> None:
    with pytest.raises(ValueError, match="require dissent ids"):
        disposition(
            disposition_kind=WaveFiveReviewDispositionKind.DISPUTED_BY_REVIEWER,
            reviewer_ids=("reviewer-001",),
        )


def test_blocked_disposition_requires_blocker_ids() -> None:
    with pytest.raises(ValueError, match="require blockers"):
        disposition(
            disposition_kind=WaveFiveReviewDispositionKind.BLOCKED_BEFORE_WAVE_SIX,
            reviewer_ids=("reviewer-001",),
        )


def test_blocking_dispositions_block_packet_readiness() -> None:
    disputed = disposition(
        disposition_kind=WaveFiveReviewDispositionKind.DISPUTED_BY_REVIEWER,
        reviewer_ids=("reviewer-001",),
        dissent_ids=("dissent-001",),
    )
    blocked = disposition(
        disposition_kind=WaveFiveReviewDispositionKind.BLOCKED_BEFORE_WAVE_SIX,
        reviewer_ids=("reviewer-001",),
        blocker_ids=("blocker-001",),
    )

    assert disputed.blocks_packet_readiness is True
    assert blocked.blocks_packet_readiness is True


def test_packet_rejects_forbidden_claim_flags() -> None:
    with pytest.raises(ValueError, match="cannot promote to Wave 6"):
        packet(attempted_wave_six_promotion=True)

    with pytest.raises(ValueError, match="cannot claim AGI"):
        packet(claims_agi=True)

    with pytest.raises(ValueError, match="cannot grant execution"):
        packet(grants_execution_authority=True)


def test_packet_rejects_production_certification_and_independent_claims() -> None:
    with pytest.raises(ValueError, match="cannot claim production"):
        packet(claims_production_ready=True)

    with pytest.raises(ValueError, match="cannot claim certification"):
        packet(claims_certified=True)

    with pytest.raises(ValueError, match="independent validation"):
        packet(claims_independent_validation=True)


def test_packet_rejects_missing_claim_boundary() -> None:
    with pytest.raises(ValueError, match="no-self-validation"):
        packet(
            claim_boundaries=tuple(
                boundary
                for boundary in WAVE_FIVE_REQUIRED_CLAIM_BOUNDARIES
                if boundary is not WaveFiveClaimBoundary.NO_SELF_VALIDATION
            )
        )


def test_packet_reports_missing_required_sections_and_challenges() -> None:
    item = packet(
        sections=(packet_section(),),
        challenges=(challenge(),),
    )

    assert item.has_required_section_coverage is False
    assert WaveFiveReviewPacketSectionKind.DISSENT_AND_GAP_LOG in (
        item.missing_required_section_kinds
    )
    assert item.has_required_challenge_coverage is False
    assert WaveFiveReviewChallengeKind.BLOCK_WAVE_SIX_IF_NEEDED in (
        item.missing_required_challenge_kinds
    )
    assert item.ready_for_external_review is False


def test_packet_blocks_when_section_status_is_blocking() -> None:
    sections = tuple(
        packet_section(
            f"section-{section_kind.value}",
            section_kind=section_kind,
            status=(
                WaveFiveReviewPacketSectionStatus.DISPUTED
                if section_kind is WaveFiveReviewPacketSectionKind.REPEATABILITY_LEDGER
                else WaveFiveReviewPacketSectionStatus.INCLUDED
            ),
        )
        for section_kind in REQUIRED_REVIEW_PACKET_SECTIONS
    )
    item = packet(sections=sections)

    assert item.blocking_section_ids == ("section-repeatability-ledger",)
    assert item.blocks_packet_readiness is True


def test_packet_blocks_when_challenge_is_blocked() -> None:
    challenges = tuple(
        challenge(
            f"challenge-{challenge_kind.value}",
            challenge_kind=challenge_kind,
            status=(
                WaveFiveReviewChallengeStatus.BLOCKED
                if challenge_kind
                is WaveFiveReviewChallengeKind.BLOCK_WAVE_SIX_IF_NEEDED
                else WaveFiveReviewChallengeStatus.READY
            ),
        )
        for challenge_kind in REQUIRED_REVIEW_CHALLENGES
    )
    item = packet(challenges=challenges)

    assert item.blocking_challenge_ids == ("challenge-block-wave-six-if-needed",)
    assert item.blocks_packet_readiness is True


def test_packet_blocks_when_disposition_blocks() -> None:
    item = packet(
        dispositions=(
            disposition(
                disposition_kind=WaveFiveReviewDispositionKind.BLOCKED_BEFORE_WAVE_SIX,
                reviewer_ids=("reviewer-001",),
                blocker_ids=("blocker-001",),
            ),
        )
    )

    assert item.blocking_disposition_ids == ("disposition-packet-ready",)
    assert item.blocks_packet_readiness is True


def test_packet_is_ready_for_external_review() -> None:
    item = packet()

    assert item.has_required_section_coverage is True
    assert item.has_required_challenge_coverage is True
    assert item.blocking_section_ids == ()
    assert item.blocking_challenge_ids == ()
    assert item.blocking_disposition_ids == ()
    assert item.makes_no_forbidden_claims is True
    assert item.ready_for_external_review is True


def test_ready_packet_exports_reviewable_traceability_artifact() -> None:
    artifact = packet().to_artifact_ref()

    assert artifact.kind is WaveFiveArtifactKind.ECOSYSTEM_TRACEABILITY_MAP
    assert artifact.capability_area is WaveFiveCapabilityArea.ECOSYSTEM_TRACEABILITY
    assert artifact.source_system is WaveFiveSourceSystem.IX_COGNITION_KERNEL
    assert artifact.decision is WaveFiveArtifactDecision.READY_FOR_INDEPENDENT_REVIEW
    assert artifact.authority_state is WaveFiveAuthorityState.HUMAN_REVIEW_REQUIRED
    assert artifact.validation_status is (
        WaveFiveValidationStatus.UNDER_INDEPENDENT_REVIEW
    )


def test_blocked_packet_exports_blocked_artifact() -> None:
    artifact = packet(
        dispositions=(
            disposition(
                disposition_kind=WaveFiveReviewDispositionKind.BLOCKED_BEFORE_WAVE_SIX,
                reviewer_ids=("reviewer-001",),
                blocker_ids=("blocker-001",),
            ),
        )
    ).to_artifact_ref()

    assert artifact.decision is WaveFiveArtifactDecision.BLOCKED
    assert artifact.authority_state is WaveFiveAuthorityState.BLOCKED
    assert artifact.validation_status is WaveFiveValidationStatus.REJECTED


def test_externally_reviewed_packet_requires_external_source() -> None:
    with pytest.raises(ValueError, match="external source"):
        packet(
            packet_state=(
                WaveFiveExternalReviewPacketState.EXTERNALLY_REVIEWED_WITH_BOUNDARIES
            ),
            reviewer_ids=("reviewer-001",),
        )


def test_externally_reviewed_packet_requires_reviewer_ids() -> None:
    with pytest.raises(ValueError, match="reviewer ids"):
        packet(
            source_system=WaveFiveSourceSystem.INDEPENDENT_REVIEWER,
            packet_state=(
                WaveFiveExternalReviewPacketState.EXTERNALLY_REVIEWED_WITH_BOUNDARIES
            ),
        )


def test_externally_reviewed_packet_exports_bounded_external_artifact() -> None:
    item = packet(
        source_system=WaveFiveSourceSystem.INDEPENDENT_REVIEWER,
        packet_state=(
            WaveFiveExternalReviewPacketState.EXTERNALLY_REVIEWED_WITH_BOUNDARIES
        ),
        reviewer_ids=("reviewer-001",),
        dispositions=(
            disposition(
                disposition_kind=(
                    WaveFiveReviewDispositionKind.
                    EXTERNALLY_REVIEWED_WITH_BOUNDARIES
                ),
                reviewer_ids=("reviewer-001",),
            ),
        ),
    )
    artifact = item.to_artifact_ref()

    assert item.externally_reviewed_with_boundaries is True
    assert artifact.decision is WaveFiveArtifactDecision.EXTERNALLY_REVIEWED
    assert artifact.validation_status is (
        WaveFiveValidationStatus.ACCEPTED_WITH_BOUNDARIES
    )
    assert artifact.externally_validated_with_boundaries is True


def test_packet_collects_unique_evidence_ids() -> None:
    item = packet()

    assert item.all_evidence_ids[0] == "evidence-section-benchmark-gaming-audit"
    assert "evidence-challenge-block-wave-six-if-needed" in item.all_evidence_ids
    assert "evidence-disposition-packet-ready" in item.all_evidence_ids
    assert len(item.all_evidence_ids) == 23


def test_packet_fingerprint_is_deterministic() -> None:
    item = packet()

    assert item.fingerprint() == item.fingerprint()
    assert len(item.fingerprint()) == 64
