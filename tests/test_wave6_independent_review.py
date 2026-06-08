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
    claims_agi: bool = False,
) -> WaveSixIndependentReviewArtifact:
    return WaveSixIndependentReviewArtifact(
        artifact_id=artifact_id or f"artifact-{kind.value}",
        kind=kind,
        summary=f"Independent review artifact for {kind.value}.",
        artifact_fingerprint=f"fingerprint-{kind.value}",
        evidence_ids=(f"evidence-{kind.value}",),
        reviewer_questions=(f"Can {kind.value} be independently reviewed?",),
        finding=finding,
        replication_notes=(f"Recompute {kind.value} fingerprint.",),
        blocks_external_review=blocks_external_review,
        claims_agi=claims_agi,
    )


def _complete_artifacts() -> tuple[WaveSixIndependentReviewArtifact, ...]:
    return tuple(
        _artifact(kind) for kind in WAVE_SIX_REQUIRED_INDEPENDENT_REVIEW_ARTIFACT_KINDS
    )


def _packet(
    *,
    artifacts: tuple[WaveSixIndependentReviewArtifact, ...] | None = None,
    decision: WaveSixIndependentReviewDecision = (
        WaveSixIndependentReviewDecision.READY_FOR_EXTERNAL_REVIEW
    ),
    claims_agi: bool = False,
) -> WaveSixIndependentReviewPacket:
    return WaveSixIndependentReviewPacket(
        packet_id="independent-review-packet-1",
        title="Wave 6 measured system-level cognition review packet",
        artifacts=artifacts or _complete_artifacts(),
        claim_boundary_statement=(
            "This packet supports bounded independent review only. It is not an "
            "AGI, production, certification, or autonomous authority claim."
        ),
        replication_instructions=(
            "Recompute each artifact fingerprint.",
            "Check every reviewer question against evidence.",
        ),
        generated_by_engine_id="wave6-independent-review-engine",
        decision=decision,
        claims_agi=claims_agi,
        notes=("External review is required before any bounded interpretation.",),
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
    assert artifact.fingerprint() == artifact.fingerprint()
    assert len(artifact.fingerprint()) == 64


def test_independent_review_artifact_rejects_overclaims() -> None:
    with pytest.raises(ValueError, match="must not claim AGI"):
        _artifact(
            WaveSixIndependentReviewArtifactKind.CLAIM_BOUNDARY_DECLARATION,
            claims_agi=True,
        )

    with pytest.raises(ValueError, match="must not claim production readiness"):
        WaveSixIndependentReviewArtifact(
            artifact_id="artifact-production",
            kind=WaveSixIndependentReviewArtifactKind.REPLICATION_INSTRUCTIONS,
            summary="Invalid production claim.",
            artifact_fingerprint="fingerprint-production",
            evidence_ids=("evidence-production",),
            reviewer_questions=("Is this bounded?",),
            finding=WaveSixIndependentReviewFinding.ACCEPTED_FOR_EXTERNAL_REVIEW,
            claims_production_ready=True,
        )


def test_independent_review_artifact_enforces_finding_semantics() -> None:
    with pytest.raises(ValueError, match="must block review"):
        _artifact(
            WaveSixIndependentReviewArtifactKind.FALSIFICATION_LEDGER,
            finding=WaveSixIndependentReviewFinding.CONTRADICTED,
        )

    with pytest.raises(ValueError, match="should not be marked as blocking"):
        _artifact(
            WaveSixIndependentReviewArtifactKind.FALSIFICATION_LEDGER,
            finding=WaveSixIndependentReviewFinding.NEEDS_MORE_EVIDENCE,
            blocks_external_review=True,
        )


def test_independent_review_artifact_requires_evidence_and_questions() -> None:
    with pytest.raises(ValueError, match="require evidence ids"):
        WaveSixIndependentReviewArtifact(
            artifact_id="artifact-no-evidence",
            kind=WaveSixIndependentReviewArtifactKind.MASTER_LOOP_TRACE,
            summary="Invalid empty evidence.",
            artifact_fingerprint="fingerprint",
            evidence_ids=(),
            reviewer_questions=("Can this be reviewed?",),
            finding=WaveSixIndependentReviewFinding.ACCEPTED_FOR_EXTERNAL_REVIEW,
        )

    with pytest.raises(ValueError, match="require reviewer questions"):
        WaveSixIndependentReviewArtifact(
            artifact_id="artifact-no-questions",
            kind=WaveSixIndependentReviewArtifactKind.MASTER_LOOP_TRACE,
            summary="Invalid empty questions.",
            artifact_fingerprint="fingerprint",
            evidence_ids=("evidence-1",),
            reviewer_questions=(),
            finding=WaveSixIndependentReviewFinding.ACCEPTED_FOR_EXTERNAL_REVIEW,
        )


def test_independent_review_packet_is_ready_when_complete() -> None:
    packet = build_wave_six_independent_review_packet(
        packet_id="packet-ready",
        title="Wave 6 bounded independent review packet",
        artifacts=_complete_artifacts(),
        claim_boundary_statement="Bounded review only; this is not an AGI claim.",
        replication_instructions=("Recompute all deterministic fingerprints.",),
        generated_by_engine_id="wave6-independent-review-engine",
        decision=WaveSixIndependentReviewDecision.READY_FOR_EXTERNAL_REVIEW,
        notes=("Independent review remains required.",),
    )

    assert packet.present_artifact_kinds == (
        WAVE_SIX_REQUIRED_INDEPENDENT_REVIEW_ARTIFACT_KINDS
    )
    assert packet.missing_artifact_kinds == ()
    assert packet.needs_more_evidence_artifact_ids == ()
    assert packet.blocking_artifact_ids == ()
    assert packet.ready_for_external_review
    assert not packet.blocks_external_review
    assert packet.fingerprint() == packet.fingerprint()
    assert len(packet.fingerprint()) == 64


def test_independent_review_packet_reports_missing_artifact_kind() -> None:
    packet = _packet(
        artifacts=_complete_artifacts()[:-1],
        decision=WaveSixIndependentReviewDecision.NEEDS_MORE_EVIDENCE,
    )

    assert packet.missing_artifact_kinds == (
        WaveSixIndependentReviewArtifactKind.REPLICATION_INSTRUCTIONS,
    )
    assert not packet.ready_for_external_review


def test_independent_review_packet_tracks_needs_more_evidence_artifact() -> None:
    artifacts = list(_complete_artifacts())
    artifacts[3] = _artifact(
        WaveSixIndependentReviewArtifactKind.REALITY_CORRECTION_LEDGER,
        finding=WaveSixIndependentReviewFinding.NEEDS_MORE_EVIDENCE,
    )
    packet = _packet(
        artifacts=tuple(artifacts),
        decision=WaveSixIndependentReviewDecision.NEEDS_MORE_EVIDENCE,
    )

    assert packet.needs_more_evidence_artifact_ids == (
        "artifact-reality-correction-ledger",
    )
    assert not packet.ready_for_external_review


def test_independent_review_packet_blocks_on_blocking_artifact_or_overclaim() -> None:
    artifacts = list(_complete_artifacts())
    artifacts[6] = _artifact(
        WaveSixIndependentReviewArtifactKind.FALSIFICATION_LEDGER,
        finding=WaveSixIndependentReviewFinding.BLOCKS_EXTERNAL_REVIEW,
        blocks_external_review=True,
    )
    blocked = _packet(
        artifacts=tuple(artifacts),
        decision=WaveSixIndependentReviewDecision.BLOCKED,
    )

    assert blocked.blocking_artifact_ids == ("artifact-falsification-ledger",)
    assert blocked.blocks_external_review
    assert not blocked.ready_for_external_review

    with pytest.raises(ValueError, match="must not claim AGI"):
        _packet(
            decision=WaveSixIndependentReviewDecision.BLOCKED,
            claims_agi=True,
        )


def test_ready_independent_review_packet_rejects_missing_or_follow_up_items() -> None:
    with pytest.raises(ValueError, match="require every independent-review"):
        _packet(artifacts=_complete_artifacts()[:-1])

    artifacts = list(_complete_artifacts())
    artifacts[4] = _artifact(
        WaveSixIndependentReviewArtifactKind.FUTURE_REASONING_CHANGE_LEDGER,
        finding=WaveSixIndependentReviewFinding.NEEDS_MORE_EVIDENCE,
    )

    with pytest.raises(ValueError, match="cannot include needs-more-evidence"):
        _packet(artifacts=tuple(artifacts))


def test_blocked_independent_review_packet_requires_blocking_artifact() -> None:
    with pytest.raises(ValueError, match="require at least one blocking artifact"):
        _packet(decision=WaveSixIndependentReviewDecision.BLOCKED)


def test_independent_review_packet_lookup_and_duplicate_rejection() -> None:
    packet = _packet(
        artifacts=(_artifact(WaveSixIndependentReviewArtifactKind.MASTER_LOOP_TRACE),),
        decision=WaveSixIndependentReviewDecision.NEEDS_MORE_EVIDENCE,
    )

    artifact = packet.artifact_for_kind(
        WaveSixIndependentReviewArtifactKind.MASTER_LOOP_TRACE
    )

    assert artifact is not None
    assert artifact.artifact_id == "artifact-master-loop-trace"
    assert (
        packet.artifact_for_kind(WaveSixIndependentReviewArtifactKind.CONTRACT_BUNDLE)
        is None
    )

    duplicate = _artifact(WaveSixIndependentReviewArtifactKind.MASTER_LOOP_TRACE)
    with pytest.raises(ValueError, match="Duplicate artifact_id"):
        _packet(
            artifacts=(duplicate, duplicate),
            decision=WaveSixIndependentReviewDecision.NEEDS_MORE_EVIDENCE,
        )
