import pytest

from ix_cognition_kernel.wave6_release_manifest import (
    WAVE_SIX_REQUIRED_RELEASE_ARTIFACT_KINDS,
    WAVE_SIX_REQUIRED_RELEASE_AUDIENCES,
    WaveSixReleaseArtifact,
    WaveSixReleaseArtifactKind,
    WaveSixReleaseAudience,
    WaveSixReleaseDecision,
    WaveSixReleaseFinding,
    WaveSixReleaseManifest,
    WaveSixReleaseStatus,
    build_wave_six_release_manifest,
    required_wave_six_release_artifact_kinds,
    required_wave_six_release_audiences,
)


def _boundary_statement() -> str:
    return (
        "This Wave-6 measured system-level cognition package is released for "
        "bounded review under human authority. It is not an AGI claim."
    )


def _artifact(
    kind: WaveSixReleaseArtifactKind,
    *,
    artifact_id: str | None = None,
    finding: WaveSixReleaseFinding = WaveSixReleaseFinding.INCLUDED,
    requires_follow_up: bool = False,
    blocks_release: bool = False,
) -> WaveSixReleaseArtifact:
    return WaveSixReleaseArtifact(
        artifact_id=artifact_id or f"artifact-{kind.value}",
        kind=kind,
        artifact_fingerprint=f"fingerprint-{kind.value}",
        source_path=f"artifacts/wave6/{kind.value}.json",
        summary=f"Release artifact for {kind.value}.",
        evidence_ids=(f"evidence-{kind.value}",),
        finding=finding,
        reviewer_questions=(f"Can {kind.value} be released for bounded review?",),
        requires_follow_up=requires_follow_up,
        blocks_release=blocks_release,
    )


def _complete_artifacts() -> tuple[WaveSixReleaseArtifact, ...]:
    return tuple(_artifact(kind) for kind in WAVE_SIX_REQUIRED_RELEASE_ARTIFACT_KINDS)


def _manifest(
    *,
    artifacts: tuple[WaveSixReleaseArtifact, ...] | None = None,
    allowed_audiences: tuple[WaveSixReleaseAudience, ...] | None = None,
    decision: WaveSixReleaseDecision = (
        WaveSixReleaseDecision.RELEASE_FOR_BOUNDED_REVIEW
    ),
    claims_agi: bool = False,
    claim_boundary_statement: str | None = None,
) -> WaveSixReleaseManifest:
    return WaveSixReleaseManifest(
        manifest_id="release-manifest-1",
        release_version="wave6-bounded-review-v1",
        artifacts=artifacts or _complete_artifacts(),
        allowed_audiences=allowed_audiences or WAVE_SIX_REQUIRED_RELEASE_AUDIENCES,
        decision=decision,
        claim_boundary_statement=claim_boundary_statement or _boundary_statement(),
        generated_by_engine_id="wave6-release-manifest-engine",
        human_authority_id="human-authority-1",
        claims_agi=claims_agi,
        notes=("Release is bounded review handoff, not production deployment.",),
    )


def test_required_release_artifacts_and_audiences_are_locked() -> None:
    assert required_wave_six_release_artifact_kinds() == (
        WaveSixReleaseArtifactKind.AUDIT_MANIFEST,
        WaveSixReleaseArtifactKind.MATURITY_DECISION_RECORD,
        WaveSixReleaseArtifactKind.EXTERNAL_VALIDATION_GATE,
        WaveSixReleaseArtifactKind.EVIDENCE_PACKAGE,
        WaveSixReleaseArtifactKind.REVIEW_SCORECARD,
        WaveSixReleaseArtifactKind.REPLICATION_PROTOCOL,
        WaveSixReleaseArtifactKind.CHALLENGE_SUITE,
        WaveSixReleaseArtifactKind.CLAIM_BOUNDARY_DECLARATION,
        WaveSixReleaseArtifactKind.README_SUMMARY,
    )
    assert required_wave_six_release_audiences() == (
        WaveSixReleaseAudience.HUMAN_AUTHORITY,
        WaveSixReleaseAudience.INDEPENDENT_EVALUATOR,
        WaveSixReleaseAudience.REPLICATION_REVIEWER,
        WaveSixReleaseAudience.AUDIT_REVIEWER,
    )


def test_release_artifact_is_included_and_fingerprinted() -> None:
    artifact = _artifact(WaveSixReleaseArtifactKind.AUDIT_MANIFEST)

    assert artifact.included
    assert not artifact.needs_more_evidence
    assert not artifact.blocks_bounded_release
    assert artifact.fingerprint() == artifact.fingerprint()
    assert len(artifact.fingerprint()) == 64


def test_release_artifact_enforces_finding_semantics() -> None:
    with pytest.raises(ValueError, match="cannot require follow-up"):
        _artifact(
            WaveSixReleaseArtifactKind.AUDIT_MANIFEST,
            finding=WaveSixReleaseFinding.INCLUDED,
            requires_follow_up=True,
        )

    with pytest.raises(ValueError, match="require follow-up"):
        _artifact(
            WaveSixReleaseArtifactKind.REVIEW_SCORECARD,
            finding=WaveSixReleaseFinding.NEEDS_MORE_EVIDENCE,
        )

    with pytest.raises(ValueError, match="must block release"):
        _artifact(
            WaveSixReleaseArtifactKind.CLAIM_BOUNDARY_DECLARATION,
            finding=WaveSixReleaseFinding.BLOCKS_RELEASE,
        )


def test_release_artifact_requires_evidence_ids() -> None:
    with pytest.raises(ValueError, match="require evidence ids"):
        WaveSixReleaseArtifact(
            artifact_id="artifact-no-evidence",
            kind=WaveSixReleaseArtifactKind.AUDIT_MANIFEST,
            artifact_fingerprint="fingerprint",
            source_path="artifacts/wave6/audit.json",
            summary="Invalid release artifact.",
            evidence_ids=(),
        )


def test_release_manifest_is_ready_when_complete_and_bounded() -> None:
    manifest = build_wave_six_release_manifest(
        manifest_id="release-manifest-ready",
        release_version="wave6-bounded-review-v1",
        artifacts=_complete_artifacts(),
        allowed_audiences=WAVE_SIX_REQUIRED_RELEASE_AUDIENCES,
        decision=WaveSixReleaseDecision.RELEASE_FOR_BOUNDED_REVIEW,
        claim_boundary_statement=_boundary_statement(),
        generated_by_engine_id="wave6-release-manifest-engine",
        human_authority_id="human-authority-1",
        notes=("All required release artifacts are included.",),
    )

    assert manifest.present_artifact_kinds == WAVE_SIX_REQUIRED_RELEASE_ARTIFACT_KINDS
    assert manifest.missing_artifact_kinds == ()
    assert manifest.missing_required_audiences == ()
    assert manifest.follow_up_artifact_ids == ()
    assert manifest.blocking_artifact_ids == ()
    assert manifest.status is WaveSixReleaseStatus.READY_FOR_BOUNDED_REVIEW_RELEASE
    assert manifest.ready_for_bounded_review_release
    assert manifest.claim_boundary_statement_valid
    assert not manifest.overclaim_present
    assert manifest.fingerprint() == manifest.fingerprint()
    assert len(manifest.fingerprint()) == 64


def test_release_manifest_reports_missing_artifact_kind() -> None:
    manifest = _manifest(
        artifacts=_complete_artifacts()[:-1],
        decision=WaveSixReleaseDecision.HOLD_FOR_MORE_EVIDENCE,
    )

    assert manifest.missing_artifact_kinds == (
        WaveSixReleaseArtifactKind.README_SUMMARY,
    )
    assert manifest.status is WaveSixReleaseStatus.NEEDS_MORE_EVIDENCE
    assert not manifest.ready_for_bounded_review_release


def test_release_manifest_reports_missing_required_audience() -> None:
    manifest = _manifest(
        allowed_audiences=(
            WaveSixReleaseAudience.HUMAN_AUTHORITY,
            WaveSixReleaseAudience.INDEPENDENT_EVALUATOR,
        ),
        decision=WaveSixReleaseDecision.HOLD_FOR_MORE_EVIDENCE,
    )

    assert manifest.missing_required_audiences == (
        WaveSixReleaseAudience.REPLICATION_REVIEWER,
        WaveSixReleaseAudience.AUDIT_REVIEWER,
    )
    assert manifest.status is WaveSixReleaseStatus.NEEDS_MORE_EVIDENCE


def test_release_manifest_tracks_follow_up_artifact() -> None:
    artifacts = list(_complete_artifacts())
    artifacts[4] = _artifact(
        WaveSixReleaseArtifactKind.REVIEW_SCORECARD,
        finding=WaveSixReleaseFinding.NEEDS_MORE_EVIDENCE,
        requires_follow_up=True,
    )
    manifest = _manifest(
        artifacts=tuple(artifacts),
        decision=WaveSixReleaseDecision.HOLD_FOR_MORE_EVIDENCE,
    )

    assert manifest.follow_up_artifact_ids == ("artifact-review-scorecard",)
    assert manifest.status is WaveSixReleaseStatus.NEEDS_MORE_EVIDENCE
    assert not manifest.ready_for_bounded_review_release


def test_release_manifest_blocks_on_blocking_artifact_or_overclaim() -> None:
    artifacts = list(_complete_artifacts())
    artifacts[7] = _artifact(
        WaveSixReleaseArtifactKind.CLAIM_BOUNDARY_DECLARATION,
        finding=WaveSixReleaseFinding.BLOCKS_RELEASE,
        blocks_release=True,
    )
    blocked = _manifest(
        artifacts=tuple(artifacts),
        decision=WaveSixReleaseDecision.BLOCK_RELEASE,
    )

    assert blocked.blocking_artifact_ids == (
        "artifact-claim-boundary-declaration",
    )
    assert blocked.status is WaveSixReleaseStatus.BLOCKED

    overclaim = _manifest(
        decision=WaveSixReleaseDecision.BLOCK_RELEASE,
        claims_agi=True,
    )

    assert overclaim.overclaim_present
    assert overclaim.status is WaveSixReleaseStatus.BLOCKED


def test_ready_release_manifest_rejects_missing_or_follow_up_artifacts() -> None:
    with pytest.raises(ValueError, match="require every artifact kind"):
        _manifest(artifacts=_complete_artifacts()[:-1])

    artifacts = list(_complete_artifacts())
    artifacts[5] = _artifact(
        WaveSixReleaseArtifactKind.REPLICATION_PROTOCOL,
        finding=WaveSixReleaseFinding.NEEDS_MORE_EVIDENCE,
        requires_follow_up=True,
    )

    with pytest.raises(ValueError, match="cannot require follow-up"):
        _manifest(artifacts=tuple(artifacts))


def test_blocked_release_manifest_requires_blocker_or_overclaim() -> None:
    with pytest.raises(ValueError, match="require blocker or overclaim"):
        _manifest(decision=WaveSixReleaseDecision.BLOCK_RELEASE)


def test_release_manifest_reports_invalid_claim_boundary_statement() -> None:
    manifest = _manifest(
        decision=WaveSixReleaseDecision.HOLD_FOR_MORE_EVIDENCE,
        claim_boundary_statement="Wave 6 release is ready.",
    )

    assert not manifest.claim_boundary_statement_valid
    assert manifest.status is WaveSixReleaseStatus.NEEDS_MORE_EVIDENCE


def test_release_manifest_lookup_and_duplicate_rejection() -> None:
    manifest = _manifest(
        artifacts=(_artifact(WaveSixReleaseArtifactKind.AUDIT_MANIFEST),),
        decision=WaveSixReleaseDecision.HOLD_FOR_MORE_EVIDENCE,
    )

    artifact = manifest.artifact_for_kind(WaveSixReleaseArtifactKind.AUDIT_MANIFEST)

    assert artifact is not None
    assert artifact.artifact_id == "artifact-audit-manifest"
    assert (
        manifest.artifact_for_kind(WaveSixReleaseArtifactKind.REVIEW_SCORECARD) is None
    )

    duplicate = _artifact(WaveSixReleaseArtifactKind.AUDIT_MANIFEST)
    with pytest.raises(ValueError, match="Duplicate artifact_id"):
        _manifest(
            artifacts=(duplicate, duplicate),
            decision=WaveSixReleaseDecision.HOLD_FOR_MORE_EVIDENCE,
        )

    with pytest.raises(ValueError, match="Duplicate artifact kind"):
        _manifest(
            artifacts=(
                duplicate,
                _artifact(
                    WaveSixReleaseArtifactKind.AUDIT_MANIFEST,
                    artifact_id="different-artifact-id",
                ),
            ),
            decision=WaveSixReleaseDecision.HOLD_FOR_MORE_EVIDENCE,
        )
