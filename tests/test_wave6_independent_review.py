import pytest

from ix_cognition_kernel.wave6_independent_review import (
    WAVE_SIX_REQUIRED_INDEPENDENT_REVIEW_ARTIFACT_KINDS,
    WaveSixIndependentReviewArtifact,
    WaveSixIndependentReviewArtifactKind,
    WaveSixIndependentReviewDecision,
    WaveSixIndependentReviewFinding,
    WaveSixIndependentReviewPacket,
    build_wave_six_independent_review_packet,
    required_wave_six_independent_review_artifact_kinds,
)


def _artifact(
    kind: WaveSixIndependentReviewArtifactKind,
    *,
    artifact_id: str | None = None,
    finding: WaveSixIndependentReviewFinding = (
        WaveSixIndependentReviewFinding.ACCEPTED_FOR_EXTERNAL_REVIEW
    ),
    blocks_external_review: bool = False,
) -> WaveSixIndependentReviewArtifact:
    return WaveSixIndependentReviewArtifact(
        artifact_id=artifact_id or f"artifact-{kind.value}",
        kind=kind,
        summary=f"Independent-review artifact for {kind.value}.",
        artifact_fingerprint=f"fingerprint-{kind.value}",
        evidence_ids=(f"evidence-{kind.value}",),
        reviewer_questions=(
            "Can this artifact be reproduced without trusting the Kernel's claim?",
        ),
        finding=finding,
        replication_notes=("Use the referenced fingerprint and evidence ids.",),
        blocks_external_review=blocks_external_review,
    )


def _complete_artifacts() -> tuple[WaveSixIndependentReviewArtifact, ...]:
    return tuple(
        _artifact(kind) for kind in WAVE_SIX_REQUIRED_INDEPENDENT_REVIEW_ARTIFACT_KINDS
    )


def _ready_packet() -> WaveSixIndependentReviewPacket:
    return build_wave_six_independent_review_packet(
        packet_id="packet-ready",
        title="Wave 6 measured system-level cognition independent-review packet",
        artifacts=_complete_artifacts(),
        claim_boundary_statement=(
            "This is a Wave-6 measured system-level cognition attempt, not an "
            "AGI, production, certification, or autonomous-authority claim."
        ),
        replication_instructions=(
            "Recompute every artifact fingerprint from its canonical payload.",
            "Review transfer, novelty, falsification, and human-review evidence.",
        ),
        generated_by_engine_id="wave6-independent-review-engine",
        decision=WaveSixIndependentReviewDecision.READY_FOR_EXTERNAL_REVIEW,
        notes=("External reviewers decide whether evidence survives review.",),
    )


def test_required_independent_review_artifact_kinds_are_locked() -> None:
    assert required_wave_six_independent_review_artifact_kinds() == (
        WaveSixIndependentReviewArtifactKind.MASTER_LOOP_TRACE,
        WaveSixIndependentReviewArtifactKind.CONTRACT_BUNDLE,
        WaveSixIndependentReviewArtifactKind.DONOR_TRACEABILITY_MAP,
        WaveSixIndependentReviewArtifactKind.REALITY_CORRECTION_LEDGER,
        WaveSixIndependentReviewArtifactKind.FUTURE_REASONING_CHANGE_LEDGER,
        WaveSixIndependentReviewArtifactKind.TRANSFER_NOVELTY_LEDGER,
        WaveSixIndependentReviewArtifactKind.FALSIFICATION_LEDGER,
        WaveSixIndependentReviewArtifactKind.HUMAN_REVIEW_DOCKET,
        WaveSixIndependentReviewArtifactKind.CLAIM_BOUNDARY_DECLARATION,
        WaveSixIndependentReviewArtifactKind.REPLICATION_INSTRUCTIONS,
    )


def test_independent_review_artifact_is_evidence_bound_and_fingerprinted() -> None:
    artifact = _artifact(WaveSixIndependentReviewArtifactKind.MASTER_LOOP_TRACE)

    assert artifact.accepted_for_external_review
    assert not artifact.needs_more_evidence
    assert not artifact.blocks_review
    assert artifact.evidence_ids == ("evidence-master-loop-trace",)
    assert artifact.fingerprint() == artifact.fingerprint()
    assert len(artifact.fingerprint()) == 64


def test_independent_review_artifact_rejects_missing_evidence_or_questions() -> None:
    with pytest.raises(ValueError, match="require evidence ids"):
        WaveSixIndependentReviewArtifact(
            artifact_id="missing-evidence",
            kind=WaveSixIndependentReviewArtifactKind.MASTER_LOOP_TRACE,
            summary="Invalid independent-review artifact.",
            artifact_fingerprint="fingerprint",
            evidence_ids=(),
            reviewer_questions=("Can this be reproduced?",),
            finding=WaveSixIndependentReviewFinding.ACCEPTED_FOR_EXTERNAL_REVIEW,
        )

    with pytest.raises(ValueError, match="require reviewer questions"):
        WaveSixIndependentReviewArtifact(
            artifact_id="missing-questions",
            kind=WaveSixIndependentReviewArtifactKind.MASTER_LOOP_TRACE,
            summary="Invalid independent-review artifact.",
            artifact_fingerprint="fingerprint",
            evidence_ids=("evidence",),
            reviewer_questions=(),
            finding=WaveSixIndependentReviewFinding.ACCEPTED_FOR_EXTERNAL_REVIEW,
        )


def test_blocking_artifact_findings_must_block_review() -> None:
    with pytest.raises(ValueError, match="must block review"):
        _artifact(
            WaveSixIndependentReviewArtifactKind.FALSIFICATION_LEDGER,
            finding=WaveSixIndependentReviewFinding.CONTRADICTED,
            blocks_external_review=False,
        )


def test_independent_review_artifact_rejects_overclaims() -> None:
    with pytest.raises(ValueError, match="must not claim AGI"):
        WaveSixIndependentReviewArtifact(
            artifact_id="agi-artifact",
            kind=WaveSixIndependentReviewArtifactKind.CLAIM_BOUNDARY_DECLARATION,
            summary="Invalid artifact.",
            artifact_fingerprint="fingerprint",
            evidence_ids=("evidence",),
            reviewer_questions=("Can this be reproduced?",),
            finding=WaveSixIndependentReviewFinding.ACCEPTED_FOR_EXTERNAL_REVIEW,
            claims_agi=True,
        )

    with pytest.raises(ValueError, match="must not allow autonomous authority"):
        WaveSixIndependentReviewArtifact(
            artifact_id="authority-artifact",
            kind=WaveSixIndependentReviewArtifactKind.CLAIM_BOUNDARY_DECLARATION,
            summary="Invalid artifact.",
            artifact_fingerprint="fingerprint",
            evidence_ids=("evidence",),
            reviewer_questions=("Can this be reproduced?",),
            finding=WaveSixIndependentReviewFinding.ACCEPTED_FOR_EXTERNAL_REVIEW,
            allows_autonomous_authority=True,
        )


def test_independent_review_packet_accepts_complete_external_review_surface() -> None:
    packet = _ready_packet()

    assert packet.present_artifact_kinds == (
        WAVE_SIX_REQUIRED_INDEPENDENT_REVIEW_ARTIFACT_KINDS
    )
    assert packet.missing_artifact_kinds == ()
    assert packet.blocking_artifact_ids == ()
    assert packet.needs_more_evidence_artifact_ids == ()
    assert len(packet.accepted_artifact_ids) == len(
        WAVE_SIX_REQUIRED_INDEPENDENT_REVIEW_ARTIFACT_KINDS
    )
    assert packet.ready_for_external_review
    assert not packet.blocks_external_review
    assert packet.fingerprint() == packet.fingerprint()
    assert len(packet.fingerprint()) == 64


def test_independent_review_packet_reports_missing_artifact_kinds() -> None:
    packet = WaveSixIndependentReviewPacket(
        packet_id="packet-incomplete",
        title="Incomplete Wave 6 independent-review packet",
        artifacts=_complete_artifacts()[:-1],
        claim_boundary_statement="Not an AGI claim.",
        replication_instructions=("Recompute fingerprints.",),
        generated_by_engine_id="wave6-independent-review-engine",
        decision=WaveSixIndependentReviewDecision.NEEDS_MORE_EVIDENCE,
    )

    assert packet.missing_artifact_kinds == (
        WaveSixIndependentReviewArtifactKind.REPLICATION_INSTRUCTIONS,
    )
    assert not packet.ready_for_external_review
    assert not packet.blocks_external_review


def test_ready_independent_review_packet_rejects_missing_artifact_kinds() -> None:
    with pytest.raises(ValueError, match="every independent-review artifact kind"):
        WaveSixIndependentReviewPacket(
            packet_id="packet-invalid-ready",
            title="Invalid ready packet",
            artifacts=_complete_artifacts()[:-1],
            claim_boundary_statement="Not an AGI claim.",
            replication_instructions=("Recompute fingerprints.",),
            generated_by_engine_id="wave6-independent-review-engine",
            decision=WaveSixIndependentReviewDecision.READY_FOR_EXTERNAL_REVIEW,
        )


def test_ready_independent_review_packet_rejects_follow_up_artifacts() -> None:
    artifacts = list(_complete_artifacts())
    artifacts[0] = _artifact(
        WaveSixIndependentReviewArtifactKind.MASTER_LOOP_TRACE,
        finding=WaveSixIndependentReviewFinding.NEEDS_MORE_EVIDENCE,
    )

    with pytest.raises(ValueError, match="needs-more-evidence artifacts"):
        WaveSixIndependentReviewPacket(
            packet_id="packet-follow-up",
            title="Invalid follow-up packet",
            artifacts=tuple(artifacts),
            claim_boundary_statement="Not an AGI claim.",
            replication_instructions=("Recompute fingerprints.",),
            generated_by_engine_id="wave6-independent-review-engine",
            decision=WaveSixIndependentReviewDecision.READY_FOR_EXTERNAL_REVIEW,
        )


def test_ready_independent_review_packet_rejects_blocking_artifacts() -> None:
    artifacts = list(_complete_artifacts())
    artifacts[6] = _artifact(
        WaveSixIndependentReviewArtifactKind.FALSIFICATION_LEDGER,
        finding=WaveSixIndependentReviewFinding.BLOCKS_EXTERNAL_REVIEW,
        blocks_external_review=True,
    )

    with pytest.raises(ValueError, match="blocking artifacts"):
        WaveSixIndependentReviewPacket(
            packet_id="packet-blocking-ready",
            title="Invalid blocking packet",
            artifacts=tuple(artifacts),
            claim_boundary_statement="Not an AGI claim.",
            replication_instructions=("Recompute fingerprints.",),
            generated_by_engine_id="wave6-independent-review-engine",
            decision=WaveSixIndependentReviewDecision.READY_FOR_EXTERNAL_REVIEW,
        )


def test_blocked_packet_requires_blocking_artifact() -> None:
    with pytest.raises(ValueError, match="at least one blocking artifact"):
        WaveSixIndependentReviewPacket(
            packet_id="packet-invalid-blocked",
            title="Invalid blocked packet",
            artifacts=_complete_artifacts(),
            claim_boundary_statement="Not an AGI claim.",
            replication_instructions=("Recompute fingerprints.",),
            generated_by_engine_id="wave6-independent-review-engine",
            decision=WaveSixIndependentReviewDecision.BLOCKED,
        )


def test_independent_review_packet_blocks_external_review() -> None:
    artifacts = list(_complete_artifacts())
    artifacts[6] = _artifact(
        WaveSixIndependentReviewArtifactKind.FALSIFICATION_LEDGER,
        finding=WaveSixIndependentReviewFinding.CONTRADICTED,
        blocks_external_review=True,
    )
    packet = WaveSixIndependentReviewPacket(
        packet_id="packet-blocked",
        title="Blocked Wave 6 independent-review packet",
        artifacts=tuple(artifacts),
        claim_boundary_statement="Not an AGI claim.",
        replication_instructions=("Recompute fingerprints.",),
        generated_by_engine_id="wave6-independent-review-engine",
        decision=WaveSixIndependentReviewDecision.BLOCKED,
    )

    assert packet.blocking_artifact_ids == ("artifact-falsification-ledger",)
    assert packet.blocks_external_review
    assert not packet.ready_for_external_review


def test_independent_review_packet_rejects_overclaims() -> None:
    with pytest.raises(ValueError, match="must not claim AGI"):
        WaveSixIndependentReviewPacket(
            packet_id="packet-agi",
            title="Invalid packet",
            artifacts=_complete_artifacts(),
            claim_boundary_statement="Invalid AGI claim.",
            replication_instructions=("Recompute fingerprints.",),
            generated_by_engine_id="wave6-independent-review-engine",
            decision=WaveSixIndependentReviewDecision.NEEDS_MORE_EVIDENCE,
            claims_agi=True,
        )

    with pytest.raises(ValueError, match="must not allow autonomous authority"):
        WaveSixIndependentReviewPacket(
            packet_id="packet-authority",
            title="Invalid packet",
            artifacts=_complete_artifacts(),
            claim_boundary_statement="Invalid authority claim.",
            replication_instructions=("Recompute fingerprints.",),
            generated_by_engine_id="wave6-independent-review-engine",
            decision=WaveSixIndependentReviewDecision.NEEDS_MORE_EVIDENCE,
            allows_autonomous_authority=True,
        )


def test_independent_review_packet_rejects_duplicate_artifact_ids() -> None:
    artifact = _artifact(WaveSixIndependentReviewArtifactKind.MASTER_LOOP_TRACE)

    with pytest.raises(ValueError, match="Duplicate artifact_id"):
        WaveSixIndependentReviewPacket(
            packet_id="packet-duplicate",
            title="Duplicate packet",
            artifacts=(artifact, artifact),
            claim_boundary_statement="Not an AGI claim.",
            replication_instructions=("Recompute fingerprints.",),
            generated_by_engine_id="wave6-independent-review-engine",
            decision=WaveSixIndependentReviewDecision.NEEDS_MORE_EVIDENCE,
        )


def test_artifact_for_kind_returns_present_artifact_only() -> None:
    packet = WaveSixIndependentReviewPacket(
        packet_id="packet-lookup",
        title="Lookup packet",
        artifacts=(
            _artifact(WaveSixIndependentReviewArtifactKind.MASTER_LOOP_TRACE),
        ),
        claim_boundary_statement="Not an AGI claim.",
        replication_instructions=("Recompute fingerprints.",),
        generated_by_engine_id="wave6-independent-review-engine",
        decision=WaveSixIndependentReviewDecision.NEEDS_MORE_EVIDENCE,
    )

    artifact = packet.artifact_for_kind(
        WaveSixIndependentReviewArtifactKind.MASTER_LOOP_TRACE
    )

    assert artifact is not None
    assert artifact.artifact_id == "artifact-master-loop-trace"
    assert packet.artifact_for_kind(
        WaveSixIndependentReviewArtifactKind.CONTRACT_BUNDLE
    ) is None
