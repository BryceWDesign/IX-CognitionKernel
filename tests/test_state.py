import pytest

from ix_cognition_kernel.state import (
    ActionReadiness,
    ClaimRecord,
    EvidenceRecord,
    EvidenceStatus,
    HumanAuthority,
    UncertaintyStatus,
    assess_action_readiness,
    evidence_index,
    foundation_snapshot,
    verified_evidence_for_claim,
)


def verified_evidence() -> EvidenceRecord:
    return EvidenceRecord(
        evidence_id="ev-001",
        summary="A passing test record supports the package identity claim.",
        status=EvidenceStatus.VERIFIED,
        sources=("tests/test_package_identity.py",),
        supports_claim_ids=("claim-001",),
    )


def known_claim() -> ClaimRecord:
    return ClaimRecord(
        claim_id="claim-001",
        statement="The package identity is represented in tested code.",
        confidence=0.95,
        uncertainty=UncertaintyStatus.KNOWN,
        evidence_ids=("ev-001",),
    )


def test_verified_evidence_requires_source() -> None:
    with pytest.raises(ValueError, match="Verified evidence requires"):
        EvidenceRecord(
            evidence_id="ev-missing-source",
            summary="Verified evidence without source should be rejected.",
            status=EvidenceStatus.VERIFIED,
            sources=(),
            supports_claim_ids=("claim-001",),
        )


def test_claim_confidence_must_be_bounded() -> None:
    with pytest.raises(ValueError, match="between 0.0 and 1.0"):
        ClaimRecord(
            claim_id="claim-bad-confidence",
            statement="Impossible confidence should be rejected.",
            confidence=1.1,
            uncertainty=UncertaintyStatus.KNOWN,
            evidence_ids=(),
        )


def test_evidence_index_rejects_duplicate_ids() -> None:
    record = verified_evidence()

    with pytest.raises(ValueError, match="Duplicate evidence_id"):
        evidence_index((record, record))


def test_verified_evidence_for_claim_requires_supporting_claim_id() -> None:
    claim = known_claim()
    unrelated = EvidenceRecord(
        evidence_id="ev-002",
        summary="Verified but unrelated evidence.",
        status=EvidenceStatus.VERIFIED,
        sources=("tests/test_other.py",),
        supports_claim_ids=("other-claim",),
    )

    verified = verified_evidence_for_claim(
        claim,
        evidence_index((verified_evidence(), unrelated)),
    )

    assert tuple(record.evidence_id for record in verified) == ("ev-001",)


def test_unsafe_claim_is_blocked_even_with_verified_evidence_and_authority() -> None:
    claim = ClaimRecord(
        claim_id="claim-001",
        statement="Unsafe claim should not be action-ready.",
        confidence=0.95,
        uncertainty=UncertaintyStatus.UNSAFE_TO_ACT,
        evidence_ids=("ev-001",),
    )

    report = assess_action_readiness(
        claim,
        evidence_index((verified_evidence(),)),
        HumanAuthority.GRANTED,
    )

    assert report.readiness is ActionReadiness.BLOCKED
    assert report.is_ready is False
    assert report.verified_evidence_ids == ("ev-001",)


def test_known_claim_without_verified_evidence_needs_evidence() -> None:
    claim = ClaimRecord(
        claim_id="claim-001",
        statement="Known labels still need verified evidence.",
        confidence=0.7,
        uncertainty=UncertaintyStatus.KNOWN,
        evidence_ids=(),
    )

    report = assess_action_readiness(claim, evidence_index(()), HumanAuthority.GRANTED)

    assert report.readiness is ActionReadiness.NEEDS_EVIDENCE
    assert report.verified_evidence_ids == ()


def test_assumed_claim_needs_evidence_even_if_source_exists() -> None:
    claim = ClaimRecord(
        claim_id="claim-001",
        statement="Assumed claims cannot proceed only because evidence exists.",
        confidence=0.5,
        uncertainty=UncertaintyStatus.ASSUMED,
        evidence_ids=("ev-001",),
    )

    report = assess_action_readiness(
        claim,
        evidence_index((verified_evidence(),)),
        HumanAuthority.GRANTED,
    )

    assert report.readiness is ActionReadiness.NEEDS_EVIDENCE


def test_verified_known_claim_needs_human_authority_before_handoff() -> None:
    report = assess_action_readiness(
        known_claim(),
        evidence_index((verified_evidence(),)),
        HumanAuthority.REQUIRED,
    )

    assert report.readiness is ActionReadiness.NEEDS_HUMAN_AUTHORITY
    assert report.is_ready is False


def test_verified_known_claim_with_authority_is_ready_for_handoff() -> None:
    report = assess_action_readiness(
        known_claim(),
        evidence_index((verified_evidence(),)),
        HumanAuthority.GRANTED,
    )

    assert report.readiness is ActionReadiness.READY_FOR_HANDOFF
    assert report.is_ready is True
    assert report.reasons == ("Verified evidence and human authority are present.",)


def test_foundation_snapshot_uses_current_wave_and_blocks_agi_claim() -> None:
    snapshot = foundation_snapshot(
        claims=(known_claim(),),
        evidence=(verified_evidence(),),
        authority=HumanAuthority.GRANTED,
    )

    assert snapshot.project_name == "IX-CognitionKernel"
    assert snapshot.wave_number == 2
    assert snapshot.wave_label == "Wave 2 — Learnable Causal Cognition Core"
    assert snapshot.permits_agi_claim is False
    assert snapshot.readiness_reports[0].readiness is ActionReadiness.READY_FOR_HANDOFF
