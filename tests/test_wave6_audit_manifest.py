import pytest

from ix_cognition_kernel.wave6_audit_manifest import (
    WAVE_SIX_REQUIRED_AUDIT_ARTIFACT_KINDS,
    WaveSixAuditArtifact,
    WaveSixAuditArtifactKind,
    WaveSixAuditFinding,
    WaveSixAuditManifest,
    WaveSixAuditManifestDecision,
    WaveSixAuditManifestStatus,
    build_wave_six_audit_manifest,
    required_wave_six_audit_artifact_kinds,
)


def _boundary_statement() -> str:
    return (
        "This is a Wave-6 measured system-level cognition attempt under human "
        "authority and independent review. It is not an AGI claim."
    )


def _artifact(
    kind: WaveSixAuditArtifactKind,
    *,
    artifact_id: str | None = None,
    finding: WaveSixAuditFinding = WaveSixAuditFinding.ACCEPTED,
    requires_follow_up: bool = False,
    blocks_claim: bool = False,
) -> WaveSixAuditArtifact:
    return WaveSixAuditArtifact(
        artifact_id=artifact_id or f"artifact-{kind.value}",
        kind=kind,
        artifact_fingerprint=f"fingerprint-{kind.value}",
        summary=f"Audit manifest artifact for {kind.value}.",
        evidence_ids=(f"evidence-{kind.value}",),
        finding=finding,
        reviewer_questions=(f"Does {kind.value} survive audit review?",),
        requires_follow_up=requires_follow_up,
        blocks_claim=blocks_claim,
    )


def _complete_artifacts() -> tuple[WaveSixAuditArtifact, ...]:
    return tuple(_artifact(kind) for kind in WAVE_SIX_REQUIRED_AUDIT_ARTIFACT_KINDS)


def _manifest(
    *,
    artifacts: tuple[WaveSixAuditArtifact, ...] | None = None,
    decision: WaveSixAuditManifestDecision = (
        WaveSixAuditManifestDecision.ENTER_BOUNDED_WAVE_SIX_REVIEW
    ),
    claims_agi: bool = False,
    claim_boundary_statement: str | None = None,
) -> WaveSixAuditManifest:
    return WaveSixAuditManifest(
        manifest_id="manifest-1",
        artifacts=artifacts or _complete_artifacts(),
        decision=decision,
        claim_boundary_statement=claim_boundary_statement or _boundary_statement(),
        generated_by_engine_id="wave6-audit-manifest-engine",
        human_authority_id="human-authority-1",
        independent_reviewer_id="independent-reviewer-1",
        claims_agi=claims_agi,
        notes=("Audit-ready means bounded review, not AGI achieved.",),
    )


def test_required_audit_artifact_kinds_are_locked() -> None:
    assert required_wave_six_audit_artifact_kinds() == (
        WaveSixAuditArtifactKind.CONTRACT_BUNDLE,
        WaveSixAuditArtifactKind.MASTER_LOOP_TRACE,
        WaveSixAuditArtifactKind.DONOR_TRACEABILITY_MAP,
        WaveSixAuditArtifactKind.REALITY_CORRECTION_LEDGER,
        WaveSixAuditArtifactKind.FUTURE_REASONING_CHANGE_LEDGER,
        WaveSixAuditArtifactKind.TRANSFER_NOVELTY_LEDGER,
        WaveSixAuditArtifactKind.FALSIFICATION_LEDGER,
        WaveSixAuditArtifactKind.HUMAN_REVIEW_DOCKET,
        WaveSixAuditArtifactKind.INDEPENDENT_REVIEW_PACKET,
        WaveSixAuditArtifactKind.CHALLENGE_SUITE,
        WaveSixAuditArtifactKind.REPLICATION_PROTOCOL,
        WaveSixAuditArtifactKind.TRIAL_REPLAY_LEDGER,
        WaveSixAuditArtifactKind.EXTERNAL_VALIDATION_GATE,
        WaveSixAuditArtifactKind.REVIEW_SCORECARD,
        WaveSixAuditArtifactKind.MATURITY_GATE,
        WaveSixAuditArtifactKind.MATURITY_DECISION_RECORD,
        WaveSixAuditArtifactKind.CLAIM_BOUNDARY_DECLARATION,
    )


def test_audit_artifact_is_evidence_bound_and_fingerprinted() -> None:
    artifact = _artifact(WaveSixAuditArtifactKind.MATURITY_GATE)

    assert artifact.accepted
    assert not artifact.needs_more_evidence
    assert not artifact.blocks_interpretation
    assert artifact.fingerprint() == artifact.fingerprint()
    assert len(artifact.fingerprint()) == 64


def test_audit_artifact_enforces_finding_semantics() -> None:
    with pytest.raises(ValueError, match="cannot require follow-up"):
        _artifact(
            WaveSixAuditArtifactKind.REVIEW_SCORECARD,
            finding=WaveSixAuditFinding.ACCEPTED,
            requires_follow_up=True,
        )

    with pytest.raises(ValueError, match="require follow-up"):
        _artifact(
            WaveSixAuditArtifactKind.REVIEW_SCORECARD,
            finding=WaveSixAuditFinding.NEEDS_MORE_EVIDENCE,
        )

    with pytest.raises(ValueError, match="must block the claim"):
        _artifact(
            WaveSixAuditArtifactKind.FALSIFICATION_LEDGER,
            finding=WaveSixAuditFinding.BLOCKS_CLAIM,
        )


def test_audit_manifest_is_ready_when_complete_and_accepted() -> None:
    manifest = build_wave_six_audit_manifest(
        manifest_id="manifest-ready",
        artifacts=_complete_artifacts(),
        decision=WaveSixAuditManifestDecision.ENTER_BOUNDED_WAVE_SIX_REVIEW,
        claim_boundary_statement=_boundary_statement(),
        generated_by_engine_id="wave6-audit-manifest-engine",
        human_authority_id="human-authority-1",
        independent_reviewer_id="independent-reviewer-1",
        notes=("All required audit artifact kinds are present and accepted.",),
    )

    assert manifest.present_artifact_kinds == WAVE_SIX_REQUIRED_AUDIT_ARTIFACT_KINDS
    assert manifest.missing_artifact_kinds == ()
    assert manifest.follow_up_artifact_ids == ()
    assert manifest.blocking_artifact_ids == ()
    assert manifest.claim_boundary_statement_valid
    assert manifest.status is WaveSixAuditManifestStatus.READY_FOR_AUDIT_REVIEW
    assert manifest.ready_for_audit_review
    assert len(manifest.accepted_artifact_ids) == len(
        WAVE_SIX_REQUIRED_AUDIT_ARTIFACT_KINDS
    )
    assert manifest.fingerprint() == manifest.fingerprint()
    assert len(manifest.fingerprint()) == 64


def test_audit_manifest_reports_missing_artifact_kind() -> None:
    manifest = _manifest(
        artifacts=_complete_artifacts()[:-1],
        decision=WaveSixAuditManifestDecision.CONTINUE_EVIDENCE_COLLECTION,
    )

    assert manifest.missing_artifact_kinds == (
        WaveSixAuditArtifactKind.CLAIM_BOUNDARY_DECLARATION,
    )
    assert manifest.status is WaveSixAuditManifestStatus.NEEDS_MORE_EVIDENCE
    assert not manifest.ready_for_audit_review


def test_ready_audit_manifest_rejects_missing_or_follow_up_artifacts() -> None:
    with pytest.raises(ValueError, match="require every artifact kind"):
        _manifest(artifacts=_complete_artifacts()[:-1])

    artifacts = list(_complete_artifacts())
    artifacts[0] = _artifact(
        WaveSixAuditArtifactKind.CONTRACT_BUNDLE,
        finding=WaveSixAuditFinding.NEEDS_MORE_EVIDENCE,
        requires_follow_up=True,
    )
    with pytest.raises(ValueError, match="cannot require follow-up"):
        _manifest(artifacts=tuple(artifacts))


def test_audit_manifest_blocks_on_blocking_artifact_or_overclaim() -> None:
    artifacts = list(_complete_artifacts())
    artifacts[6] = _artifact(
        WaveSixAuditArtifactKind.FALSIFICATION_LEDGER,
        finding=WaveSixAuditFinding.BLOCKS_CLAIM,
        blocks_claim=True,
    )
    blocked = _manifest(
        artifacts=tuple(artifacts),
        decision=WaveSixAuditManifestDecision.BLOCK_WAVE_SIX_INTERPRETATION,
    )

    assert blocked.blocking_artifact_ids == ("artifact-falsification-ledger",)
    assert blocked.status is WaveSixAuditManifestStatus.BLOCKED
    assert not blocked.ready_for_audit_review

    overclaim = _manifest(
        decision=WaveSixAuditManifestDecision.BLOCK_WAVE_SIX_INTERPRETATION,
        claims_agi=True,
    )

    assert overclaim.overclaim_present
    assert overclaim.status is WaveSixAuditManifestStatus.BLOCKED


def test_blocked_audit_manifest_requires_blocker_or_overclaim() -> None:
    with pytest.raises(ValueError, match="require a blocker or overclaim"):
        _manifest(decision=WaveSixAuditManifestDecision.BLOCK_WAVE_SIX_INTERPRETATION)


def test_audit_manifest_reports_invalid_claim_boundary_statement() -> None:
    manifest = _manifest(
        decision=WaveSixAuditManifestDecision.CONTINUE_EVIDENCE_COLLECTION,
        claim_boundary_statement="Wave 6 is complete.",
    )

    assert not manifest.claim_boundary_statement_valid
    assert manifest.status is WaveSixAuditManifestStatus.NEEDS_MORE_EVIDENCE


def test_audit_manifest_lookup_returns_present_artifact_only() -> None:
    manifest = _manifest(
        artifacts=(_artifact(WaveSixAuditArtifactKind.MATURITY_GATE),),
        decision=WaveSixAuditManifestDecision.CONTINUE_EVIDENCE_COLLECTION,
    )

    artifact = manifest.artifact_for_kind(WaveSixAuditArtifactKind.MATURITY_GATE)

    assert artifact is not None
    assert artifact.artifact_id == "artifact-maturity-gate"
    assert manifest.artifact_for_kind(WaveSixAuditArtifactKind.CONTRACT_BUNDLE) is None


def test_audit_manifest_rejects_duplicate_artifact_ids_or_kinds() -> None:
    artifact = _artifact(WaveSixAuditArtifactKind.MATURITY_GATE)

    with pytest.raises(ValueError, match="Duplicate artifact_id"):
        _manifest(
            artifacts=(artifact, artifact),
            decision=WaveSixAuditManifestDecision.CONTINUE_EVIDENCE_COLLECTION,
        )

    with pytest.raises(ValueError, match="Duplicate artifact kind"):
        _manifest(
            artifacts=(
                artifact,
                _artifact(
                    WaveSixAuditArtifactKind.MATURITY_GATE,
                    artifact_id="different-artifact-id",
                ),
            ),
            decision=WaveSixAuditManifestDecision.CONTINUE_EVIDENCE_COLLECTION,
        )
