import pytest

from ix_cognition_kernel.wave7_organism_scorecard import (
    OrganismDimensionId,
    OrganismEvaluationSummary,
    OrganismScorecard,
    ScorecardDimension,
    ScorecardDimensionStatus,
    build_organism_evaluation_summary,
    build_organism_scorecard,
    build_scorecard_dimension,
)
from ix_cognition_kernel.wave7_release_manifest import (
    REQUIRED_WAVE7_ARTIFACT_KINDS,
    Wave7ReleaseArtifact,
    Wave7ReleaseArtifactKind,
    Wave7ReleaseDecision,
    Wave7ReleaseGate,
    Wave7ReleaseGateStatus,
    Wave7ReleaseManifest,
    build_wave7_release_artifacts,
    build_wave7_release_gates,
    build_wave7_release_manifest,
    build_wave7_release_review_packet,
    infer_wave7_release_decision,
)


def _dimension(
    dimension_id: OrganismDimensionId,
    *,
    status: ScorecardDimensionStatus = ScorecardDimensionStatus.READY_FOR_REVIEW,
    score: float = 0.86,
    blocker_ids: tuple[str, ...] = (),
) -> ScorecardDimension:
    return build_scorecard_dimension(
        dimension_id=dimension_id,
        status=status,
        summary=f"{dimension_id.value} is evidence-bound and reviewable.",
        evidence_ids=(f"{dimension_id.value}-evidence",),
        authority_refs=("human-authority-1",),
        blocker_ids=blocker_ids,
        review_notes=(f"{dimension_id.value} checked for Wave 7 release.",),
        score=score,
    )


def _scorecard() -> OrganismScorecard:
    return build_organism_scorecard(
        scorecard_id="wave7-scorecard-1",
        dimensions=tuple(
            _dimension(dimension_id) for dimension_id in OrganismDimensionId
        ),
        evaluator_ref="wave7-release-evaluator",
        notes=("Scorecard covers all Wave 7 organism dimensions.",),
    )


def _summary(scorecard: OrganismScorecard) -> OrganismEvaluationSummary:
    return build_organism_evaluation_summary(
        summary_id="wave7-summary-1",
        scorecard=scorecard,
        headline="Wave 7 cognitive organism substrate is ready for human review.",
        strengths=(
            "Identity, continuity, experience, prediction lifecycle, skill memory, "
            "airlock, manipulation pressure, and self-revision are evidence-bound.",
        ),
        required_next_reviews=(
            "Independent review of the Wave 7 release manifest and evidence packet.",
        ),
        claim_boundary=(
            "Wave 7 cognitive organism-substrate candidate under human review; "
            "not an AGI claim and not autonomous authority."
        ),
    )


def _manifest() -> Wave7ReleaseManifest:
    scorecard = _scorecard()
    summary = _summary(scorecard)
    artifacts = build_wave7_release_artifacts(
        manifest_fingerprint_ref="release-manifest-fingerprint-ref",
        scorecard_fingerprint_ref=scorecard.fingerprint(),
    )
    gates = build_wave7_release_gates(
        status=Wave7ReleaseGateStatus.READY_FOR_HUMAN_REVIEW,
        authority_refs=("human-authority-1",),
    )
    return build_wave7_release_manifest(
        manifest_id="wave7-release-manifest-1",
        artifacts=artifacts,
        gates=gates,
        scorecard=scorecard,
        evaluation_summary=summary,
        claim_boundary=(
            "Wave 7 cognitive organism-substrate candidate under human review; "
            "not an AGI claim and not autonomous authority."
        ),
        authority_refs=("human-authority-1",),
        notes=("Manifest binds all Wave 7 evidence for review.",),
    )


def test_release_artifact_requires_evidence_and_fingerprint_ref() -> None:
    artifact = Wave7ReleaseArtifact(
        artifact_id="artifact-test",
        kind=Wave7ReleaseArtifactKind.RELEASE_MANIFEST,
        path="src/ix_cognition_kernel/wave7_release_manifest.py",
        summary="Release manifest artifact.",
        evidence_ids=("artifact-evidence-1",),
        fingerprint_ref="fingerprint-ref-1",
    )

    assert artifact.kind is Wave7ReleaseArtifactKind.RELEASE_MANIFEST
    assert artifact.fingerprint() == artifact.fingerprint()
    assert len(artifact.fingerprint()) == 64

    with pytest.raises(ValueError, match="require evidence ids"):
        Wave7ReleaseArtifact(
            artifact_id="artifact-no-evidence",
            kind=Wave7ReleaseArtifactKind.RELEASE_MANIFEST,
            path="src/ix_cognition_kernel/wave7_release_manifest.py",
            summary="Bad artifact.",
            evidence_ids=(),
            fingerprint_ref="fingerprint-ref-1",
        )


def test_release_gate_enforces_blocker_and_authority_semantics() -> None:
    gate = Wave7ReleaseGate(
        gate_id="gate-ready",
        status=Wave7ReleaseGateStatus.READY_FOR_HUMAN_REVIEW,
        summary="Gate is ready for review.",
        required_artifact_kinds=(Wave7ReleaseArtifactKind.RELEASE_MANIFEST,),
        evidence_ids=("gate-evidence-1",),
        authority_refs=("human-authority-1",),
    )

    assert gate.satisfied_or_reviewable
    assert not gate.needs_more_evidence
    assert not gate.blocks_release
    assert gate.fingerprint() == gate.fingerprint()
    assert len(gate.fingerprint()) == 64

    with pytest.raises(ValueError, match="require blocker ids"):
        Wave7ReleaseGate(
            gate_id="gate-blocked-bad",
            status=Wave7ReleaseGateStatus.BLOCKED,
            summary="Bad blocked gate.",
            required_artifact_kinds=(Wave7ReleaseArtifactKind.RELEASE_MANIFEST,),
            evidence_ids=("gate-evidence-1",),
            authority_refs=("human-authority-1",),
        )


def test_canonical_release_artifacts_cover_every_required_kind() -> None:
    scorecard = _scorecard()
    artifacts = build_wave7_release_artifacts(
        manifest_fingerprint_ref="release-manifest-fingerprint-ref",
        scorecard_fingerprint_ref=scorecard.fingerprint(),
    )

    assert len(artifacts) == len(REQUIRED_WAVE7_ARTIFACT_KINDS)
    assert (
        tuple(artifact.kind for artifact in artifacts) == REQUIRED_WAVE7_ARTIFACT_KINDS
    )
    assert artifacts[-1].kind is Wave7ReleaseArtifactKind.RELEASE_MANIFEST
    assert all(artifact.evidence_ids for artifact in artifacts)


def test_release_decision_ready_when_gates_and_scorecard_are_review_ready() -> None:
    scorecard = _scorecard()
    gates = build_wave7_release_gates(
        status=Wave7ReleaseGateStatus.READY_FOR_HUMAN_REVIEW,
        authority_refs=("human-authority-1",),
    )

    assert (
        infer_wave7_release_decision(gates=gates, scorecard=scorecard)
        is Wave7ReleaseDecision.READY_FOR_HUMAN_REVIEW
    )


def test_release_decision_needs_evidence_when_any_gate_needs_evidence() -> None:
    scorecard = _scorecard()
    gates = build_wave7_release_gates(
        status=Wave7ReleaseGateStatus.NEEDS_MORE_EVIDENCE,
        authority_refs=("human-authority-1",),
    )

    assert (
        infer_wave7_release_decision(gates=gates, scorecard=scorecard)
        is Wave7ReleaseDecision.NEEDS_MORE_EVIDENCE
    )


def test_release_decision_blocks_when_gate_blocks() -> None:
    scorecard = _scorecard()
    gates = (
        Wave7ReleaseGate(
            gate_id="gate-blocked",
            status=Wave7ReleaseGateStatus.BLOCKED,
            summary="Deployment authority claim blocks release.",
            required_artifact_kinds=(Wave7ReleaseArtifactKind.RUNTIME_AIRLOCK,),
            evidence_ids=("gate-evidence-1",),
            authority_refs=("human-authority-1",),
            blocker_ids=("deployment-authority-claim",),
        ),
    )

    assert (
        infer_wave7_release_decision(gates=gates, scorecard=scorecard)
        is Wave7ReleaseDecision.BLOCKED
    )


def test_release_manifest_is_ready_for_human_review() -> None:
    manifest = _manifest()

    assert manifest.decision is Wave7ReleaseDecision.READY_FOR_HUMAN_REVIEW
    assert manifest.ready_for_human_review
    assert not manifest.blocks_claim
    assert manifest.missing_artifact_kinds == ()
    assert manifest.evidence_gap_gate_ids == ()
    assert manifest.blocking_gate_ids == ()
    assert "wave7-release-manifest-evidence" in manifest.evidence_ids
    assert "identity-continuity-evidence" in manifest.evidence_ids
    assert manifest.fingerprint() == manifest.fingerprint()
    assert len(manifest.fingerprint()) == 64


def test_release_manifest_rejects_missing_required_artifact_kind() -> None:
    scorecard = _scorecard()
    summary = _summary(scorecard)
    artifacts = tuple(
        artifact
        for artifact in build_wave7_release_artifacts(
            manifest_fingerprint_ref="release-manifest-fingerprint-ref",
            scorecard_fingerprint_ref=scorecard.fingerprint(),
        )
        if artifact.kind is not Wave7ReleaseArtifactKind.SELF_REVISION
    )
    gates = build_wave7_release_gates(
        status=Wave7ReleaseGateStatus.READY_FOR_HUMAN_REVIEW,
        authority_refs=("human-authority-1",),
    )

    with pytest.raises(ValueError, match="missing artifacts"):
        build_wave7_release_manifest(
            manifest_id="wave7-release-manifest-missing",
            artifacts=artifacts,
            gates=gates,
            scorecard=scorecard,
            evaluation_summary=summary,
            claim_boundary=(
                "Wave 7 cognitive organism-substrate candidate under human review; "
                "not an AGI claim."
            ),
            authority_refs=("human-authority-1",),
        )


def test_release_manifest_rejects_agi_or_autonomous_authority_claims() -> None:
    manifest = _manifest()

    with pytest.raises(ValueError, match="must not claim AGI"):
        Wave7ReleaseManifest(
            manifest_id="manifest-agi",
            artifacts=manifest.artifacts,
            gates=manifest.gates,
            scorecard=manifest.scorecard,
            evaluation_summary=manifest.evaluation_summary,
            decision=manifest.decision,
            claim_boundary=manifest.claim_boundary,
            authority_refs=manifest.authority_refs,
            claims_agi=True,
        )

    with pytest.raises(ValueError, match="must not claim autonomous authority"):
        Wave7ReleaseManifest(
            manifest_id="manifest-authority",
            artifacts=manifest.artifacts,
            gates=manifest.gates,
            scorecard=manifest.scorecard,
            evaluation_summary=manifest.evaluation_summary,
            decision=manifest.decision,
            claim_boundary=manifest.claim_boundary,
            authority_refs=manifest.authority_refs,
            claims_autonomous_authority=True,
        )


def test_release_manifest_rejects_unbounded_agi_claim_boundary() -> None:
    manifest = _manifest()

    with pytest.raises(ValueError, match="must not assert AGI"):
        Wave7ReleaseManifest(
            manifest_id="manifest-bad-boundary",
            artifacts=manifest.artifacts,
            gates=manifest.gates,
            scorecard=manifest.scorecard,
            evaluation_summary=manifest.evaluation_summary,
            decision=manifest.decision,
            claim_boundary="This release is AGI.",
            authority_refs=manifest.authority_refs,
        )


def test_release_manifest_rejects_review_ready_state_with_evidence_gap_gate() -> None:
    manifest = _manifest()
    gap_gate = Wave7ReleaseGate(
        gate_id="gate-gap",
        status=Wave7ReleaseGateStatus.NEEDS_MORE_EVIDENCE,
        summary="Evidence gap remains.",
        required_artifact_kinds=(Wave7ReleaseArtifactKind.RELEASE_MANIFEST,),
        evidence_ids=("gate-gap-evidence",),
        authority_refs=("human-authority-1",),
    )

    with pytest.raises(ValueError, match="cannot have evidence gaps"):
        Wave7ReleaseManifest(
            manifest_id="manifest-bad-gap",
            artifacts=manifest.artifacts,
            gates=(gap_gate,),
            scorecard=manifest.scorecard,
            evaluation_summary=manifest.evaluation_summary,
            decision=Wave7ReleaseDecision.READY_FOR_HUMAN_REVIEW,
            claim_boundary=manifest.claim_boundary,
            authority_refs=manifest.authority_refs,
        )


def test_release_review_packet_wraps_review_ready_manifest() -> None:
    packet = build_wave7_release_review_packet(
        packet_id="wave7-review-packet-1",
        manifest=_manifest(),
        reviewer_instructions=(
            "Review scorecard dimensions, gate evidence, and claim boundary.",
            "Confirm no capability, goal, or self-revision grants authority.",
        ),
        evidence_export_ids=("wave7-release-evidence-export-1",),
    )

    assert packet.ready_for_human_review
    assert not packet.blocks_claim
    assert "wave7-release-manifest-evidence" in packet.evidence_ids
    assert packet.fingerprint() == packet.fingerprint()
    assert len(packet.fingerprint()) == 64


def test_release_review_packet_requires_review_ready_or_blocked_manifest() -> None:
    scorecard = _scorecard()
    summary = _summary(scorecard)
    artifacts = build_wave7_release_artifacts(
        manifest_fingerprint_ref="release-manifest-fingerprint-ref",
        scorecard_fingerprint_ref=scorecard.fingerprint(),
    )
    gates = build_wave7_release_gates(
        status=Wave7ReleaseGateStatus.SATISFIED,
        authority_refs=("human-authority-1",),
    )
    manifest = Wave7ReleaseManifest(
        manifest_id="manifest-record-only",
        artifacts=artifacts,
        gates=gates,
        scorecard=scorecard,
        evaluation_summary=summary,
        decision=Wave7ReleaseDecision.RECORD_ONLY,
        claim_boundary=(
            "Wave 7 cognitive organism-substrate candidate under human review; "
            "not an AGI claim."
        ),
        authority_refs=("human-authority-1",),
    )

    with pytest.raises(ValueError, match="requires review-ready or explicitly blocked"):
        build_wave7_release_review_packet(
            packet_id="packet-bad",
            manifest=manifest,
            reviewer_instructions=("Review packet.",),
            evidence_export_ids=("export-1",),
        )
