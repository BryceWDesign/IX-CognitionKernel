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
from ix_cognition_kernel.wave5_release_manifest import (
    BLOCKING_RELEASE_ARTIFACT_STATUSES,
    EXTERNAL_RELEASE_REVIEW_SOURCE_SYSTEMS,
    REQUIRED_RELEASE_ARTIFACT_KINDS,
    REQUIRED_RELEASE_CHECK_KINDS,
    SAFE_RELEASE_ARTIFACT_STATUSES,
    WaveFiveReleaseArtifactKind,
    WaveFiveReleaseArtifactRecord,
    WaveFiveReleaseArtifactStatus,
    WaveFiveReleaseBlocker,
    WaveFiveReleaseBlockerKind,
    WaveFiveReleaseBlockerSeverity,
    WaveFiveReleaseCheckKind,
    WaveFiveReleaseCheckResult,
    WaveFiveReleaseManifest,
    WaveFiveReleaseManifestCheck,
    WaveFiveReleaseManifestState,
    blocking_release_artifact_statuses,
    external_release_review_source_systems,
    required_release_artifact_kinds,
    required_release_check_kinds,
    safe_release_artifact_statuses,
)

DIGEST_A = "a" * 64
DIGEST_B = "b" * 64


def artifact_record(
    artifact_id: str = "artifact-external-protocol-suite",
    *,
    artifact_kind: WaveFiveReleaseArtifactKind = (
        WaveFiveReleaseArtifactKind.EXTERNAL_PROTOCOL_SUITE
    ),
    status: WaveFiveReleaseArtifactStatus = WaveFiveReleaseArtifactStatus.INCLUDED,
    digest: str = DIGEST_A,
    limitations: tuple[str, ...] = (),
    claim_boundaries: tuple[WaveFiveClaimBoundary, ...] = (
        WAVE_FIVE_REQUIRED_CLAIM_BOUNDARIES
    ),
) -> WaveFiveReleaseArtifactRecord:
    return WaveFiveReleaseArtifactRecord(
        artifact_id=artifact_id,
        artifact_kind=artifact_kind,
        status=status,
        digest=digest,
        evidence_ids=(f"evidence-{artifact_id}",),
        source_system=WaveFiveSourceSystem.IX_COGNITION_KERNEL,
        summary="Release artifact is evidence-bound and reviewable.",
        limitations=limitations,
        reviewer_ids=("reviewer-001",),
        claim_boundaries=claim_boundaries,
    )


def release_check(
    check_id: str,
    check_kind: WaveFiveReleaseCheckKind,
    *,
    result: WaveFiveReleaseCheckResult = WaveFiveReleaseCheckResult.PASSED,
    blocking: bool = True,
) -> WaveFiveReleaseManifestCheck:
    return WaveFiveReleaseManifestCheck(
        check_id=check_id,
        check_kind=check_kind,
        result=result,
        description="Release manifest check preserves Wave 5 boundaries.",
        evidence_ids=(f"evidence-{check_id}",),
        blocking=blocking,
    )


def blocker(
    blocker_id: str = "blocker-review-packet-gap",
    *,
    artifact_kind: WaveFiveReleaseArtifactKind = (
        WaveFiveReleaseArtifactKind.EXTERNAL_REVIEW_PACKET
    ),
    blocker_kind: WaveFiveReleaseBlockerKind = (
        WaveFiveReleaseBlockerKind.REVIEW_PACKET_GAP
    ),
    severity: WaveFiveReleaseBlockerSeverity = (
        WaveFiveReleaseBlockerSeverity.LIMITATION
    ),
    resolved: bool = False,
) -> WaveFiveReleaseBlocker:
    return WaveFiveReleaseBlocker(
        blocker_id=blocker_id,
        blocker_kind=blocker_kind,
        severity=severity,
        artifact_kind=artifact_kind,
        description="Release blocker remains visible to reviewers.",
        mitigation="Resolve blocker or preserve it as a release limitation.",
        evidence_ids=(f"evidence-{blocker_id}",),
        resolved=resolved,
    )


def required_artifacts() -> tuple[WaveFiveReleaseArtifactRecord, ...]:
    return tuple(
        artifact_record(
            f"artifact-{artifact_kind.value}",
            artifact_kind=artifact_kind,
            status=WaveFiveReleaseArtifactStatus.INCLUDED_WITH_LIMITS,
            digest=(DIGEST_A if index % 2 == 0 else DIGEST_B),
            limitations=("Release bundle is reviewable evidence, not Wave 6 proof.",),
        )
        for index, artifact_kind in enumerate(REQUIRED_RELEASE_ARTIFACT_KINDS)
    )


def required_checks() -> tuple[WaveFiveReleaseManifestCheck, ...]:
    return tuple(
        release_check(f"check-{check_kind.value}", check_kind)
        for check_kind in REQUIRED_RELEASE_CHECK_KINDS
    )


def manifest(
    *,
    source_system: WaveFiveSourceSystem = WaveFiveSourceSystem.IX_COGNITION_KERNEL,
    manifest_state: WaveFiveReleaseManifestState = (
        WaveFiveReleaseManifestState.READY_FOR_EXTERNAL_RELEASE_REVIEW
    ),
    artifacts: tuple[WaveFiveReleaseArtifactRecord, ...] | None = None,
    checks: tuple[WaveFiveReleaseManifestCheck, ...] | None = None,
    blockers: tuple[WaveFiveReleaseBlocker, ...] = (),
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
) -> WaveFiveReleaseManifest:
    resolved_artifacts = required_artifacts() if artifacts is None else artifacts
    resolved_checks = required_checks() if checks is None else checks
    return WaveFiveReleaseManifest(
        manifest_id="wave5-release-manifest-001",
        title="Wave 5 release manifest for external evidence-bundle review.",
        source_system=source_system,
        manifest_state=manifest_state,
        artifacts=resolved_artifacts,
        checks=resolved_checks,
        blockers=blockers,
        protocol_ids=("wave5-external-protocol-001",),
        reviewer_ids=reviewer_ids,
        attempted_wave_six_promotion=attempted_wave_six_promotion,
        claims_agi=claims_agi,
        grants_execution_authority=grants_execution_authority,
        claims_production_ready=claims_production_ready,
        claims_certified=claims_certified,
        claims_independent_validation=claims_independent_validation,
        claim_boundaries=claim_boundaries,
        notes=("Release manifest is a review bundle, not Wave 6 promotion.",),
    )


def test_required_release_artifacts_are_locked() -> None:
    assert required_release_artifact_kinds() == REQUIRED_RELEASE_ARTIFACT_KINDS
    assert len(REQUIRED_RELEASE_ARTIFACT_KINDS) == 18
    assert WaveFiveReleaseArtifactKind.FALSIFICATION_LEDGER in (
        REQUIRED_RELEASE_ARTIFACT_KINDS
    )
    assert WaveFiveReleaseArtifactKind.EXTERNAL_REVIEW_PACKET in (
        REQUIRED_RELEASE_ARTIFACT_KINDS
    )


def test_required_release_checks_are_locked() -> None:
    assert required_release_check_kinds() == REQUIRED_RELEASE_CHECK_KINDS
    assert len(REQUIRED_RELEASE_CHECK_KINDS) == 11
    assert WaveFiveReleaseCheckKind.NO_WAVE_SIX_PROMOTION in (
        REQUIRED_RELEASE_CHECK_KINDS
    )
    assert WaveFiveReleaseCheckKind.NO_EXECUTION_AUTHORITY in (
        REQUIRED_RELEASE_CHECK_KINDS
    )


def test_safe_and_blocking_release_statuses_are_locked() -> None:
    assert safe_release_artifact_statuses() == SAFE_RELEASE_ARTIFACT_STATUSES
    assert blocking_release_artifact_statuses() == (
        BLOCKING_RELEASE_ARTIFACT_STATUSES
    )
    assert WaveFiveReleaseArtifactStatus.INCLUDED in SAFE_RELEASE_ARTIFACT_STATUSES
    assert WaveFiveReleaseArtifactStatus.DISPUTED in (
        BLOCKING_RELEASE_ARTIFACT_STATUSES
    )


def test_external_release_review_sources_are_locked() -> None:
    assert external_release_review_source_systems() == (
        EXTERNAL_RELEASE_REVIEW_SOURCE_SYSTEMS
    )
    assert WaveFiveSourceSystem.INDEPENDENT_REVIEWER in (
        EXTERNAL_RELEASE_REVIEW_SOURCE_SYSTEMS
    )
    assert WaveFiveSourceSystem.IX_COGNITION_KERNEL not in (
        EXTERNAL_RELEASE_REVIEW_SOURCE_SYSTEMS
    )


def test_artifact_record_requires_valid_digest_and_evidence() -> None:
    with pytest.raises(ValueError, match="64-character"):
        artifact_record(digest="not-a-digest")

    with pytest.raises(ValueError, match="evidence ids"):
        WaveFiveReleaseArtifactRecord(
            artifact_id="artifact-invalid",
            artifact_kind=WaveFiveReleaseArtifactKind.EVIDENCE_DOSSIER,
            status=WaveFiveReleaseArtifactStatus.INCLUDED,
            digest=DIGEST_A,
            evidence_ids=(),
            source_system=WaveFiveSourceSystem.IX_COGNITION_KERNEL,
            summary="Invalid artifact.",
        )


def test_limited_artifact_record_requires_limitations() -> None:
    with pytest.raises(ValueError, match="require limitations"):
        artifact_record(status=WaveFiveReleaseArtifactStatus.INCLUDED_WITH_LIMITS)


def test_artifact_record_rejects_missing_claim_boundary() -> None:
    with pytest.raises(ValueError, match="no-self-validation"):
        artifact_record(
            claim_boundaries=tuple(
                boundary
                for boundary in WAVE_FIVE_REQUIRED_CLAIM_BOUNDARIES
                if boundary is not WaveFiveClaimBoundary.NO_SELF_VALIDATION
            )
        )


def test_blocking_artifact_status_blocks_release_readiness() -> None:
    item = artifact_record(status=WaveFiveReleaseArtifactStatus.DISPUTED)

    assert item.blocks_release_readiness is True
    assert item.reviewable_with_boundaries is False


def test_release_check_requires_evidence() -> None:
    with pytest.raises(ValueError, match="evidence ids"):
        WaveFiveReleaseManifestCheck(
            check_id="check-invalid",
            check_kind=WaveFiveReleaseCheckKind.NO_WAVE_SIX_PROMOTION,
            result=WaveFiveReleaseCheckResult.PASSED,
            description="Invalid check without evidence.",
            evidence_ids=(),
        )


def test_failed_release_check_blocks_readiness() -> None:
    item = release_check(
        "check-failed",
        WaveFiveReleaseCheckKind.NO_AGI_OR_CERTIFICATION_CLAIM,
        result=WaveFiveReleaseCheckResult.FAILED,
    )

    assert item.passed_with_boundaries is False
    assert item.blocks_release_readiness is True


def test_non_blocking_release_check_does_not_block_readiness() -> None:
    item = release_check(
        "check-warning",
        WaveFiveReleaseCheckKind.EXTERNAL_REVIEW_PATH_PRESENT,
        result=WaveFiveReleaseCheckResult.NEEDS_MORE_EVIDENCE,
        blocking=False,
    )

    assert item.blocks_release_readiness is False


def test_release_blocker_requires_evidence() -> None:
    with pytest.raises(ValueError, match="evidence ids"):
        WaveFiveReleaseBlocker(
            blocker_id="blocker-invalid",
            blocker_kind=WaveFiveReleaseBlockerKind.MISSING_EVIDENCE,
            severity=WaveFiveReleaseBlockerSeverity.BLOCKING,
            artifact_kind=WaveFiveReleaseArtifactKind.EVIDENCE_DOSSIER,
            description="Invalid blocker.",
            mitigation="Resolve blocker.",
            evidence_ids=(),
        )


def test_unresolved_blocking_release_blocker_blocks_readiness() -> None:
    item = blocker(severity=WaveFiveReleaseBlockerSeverity.BLOCKING)

    assert item.blocks_release_readiness is True


def test_resolved_blocking_release_blocker_does_not_block_readiness() -> None:
    item = blocker(severity=WaveFiveReleaseBlockerSeverity.BLOCKING, resolved=True)

    assert item.blocks_release_readiness is False


def test_manifest_rejects_forbidden_claim_flags() -> None:
    with pytest.raises(ValueError, match="cannot promote to Wave 6"):
        manifest(attempted_wave_six_promotion=True)

    with pytest.raises(ValueError, match="cannot claim AGI"):
        manifest(claims_agi=True)

    with pytest.raises(ValueError, match="cannot grant execution authority"):
        manifest(grants_execution_authority=True)


def test_manifest_rejects_production_certification_and_independent_claims() -> None:
    with pytest.raises(ValueError, match="production readiness"):
        manifest(claims_production_ready=True)

    with pytest.raises(ValueError, match="certification"):
        manifest(claims_certified=True)

    with pytest.raises(ValueError, match="independent validation"):
        manifest(claims_independent_validation=True)


def test_manifest_rejects_missing_claim_boundary() -> None:
    with pytest.raises(ValueError, match="no-self-validation"):
        manifest(
            claim_boundaries=tuple(
                boundary
                for boundary in WAVE_FIVE_REQUIRED_CLAIM_BOUNDARIES
                if boundary is not WaveFiveClaimBoundary.NO_SELF_VALIDATION
            )
        )


def test_manifest_reports_missing_required_artifacts_and_checks() -> None:
    item = manifest(
        artifacts=(artifact_record(),),
        checks=(
            release_check(
                "check-required-artifacts-present",
                WaveFiveReleaseCheckKind.REQUIRED_ARTIFACTS_PRESENT,
            ),
        ),
    )

    assert item.has_required_artifact_coverage is False
    assert WaveFiveReleaseArtifactKind.FALSIFICATION_LEDGER in (
        item.missing_required_artifact_kinds
    )
    assert item.has_required_check_coverage is False
    assert WaveFiveReleaseCheckKind.NO_WAVE_SIX_PROMOTION in (
        item.missing_required_check_kinds
    )
    assert item.ready_for_external_release_review is False


def test_manifest_blocks_when_artifact_status_is_blocking() -> None:
    artifacts = tuple(
        artifact_record(
            f"artifact-{artifact_kind.value}",
            artifact_kind=artifact_kind,
            status=(
                WaveFiveReleaseArtifactStatus.DISPUTED
                if artifact_kind is WaveFiveReleaseArtifactKind.REPEATABILITY_LEDGER
                else WaveFiveReleaseArtifactStatus.INCLUDED
            ),
            digest=(DIGEST_A if index % 2 == 0 else DIGEST_B),
        )
        for index, artifact_kind in enumerate(REQUIRED_RELEASE_ARTIFACT_KINDS)
    )
    item = manifest(artifacts=artifacts)

    assert item.blocking_artifact_ids == ("artifact-repeatability-ledger",)
    assert item.blocks_release_readiness is True


def test_manifest_blocks_when_check_fails() -> None:
    checks = tuple(
        release_check(
            f"check-{check_kind.value}",
            check_kind,
            result=(
                WaveFiveReleaseCheckResult.FAILED
                if check_kind is WaveFiveReleaseCheckKind.NO_WAVE_SIX_PROMOTION
                else WaveFiveReleaseCheckResult.PASSED
            ),
        )
        for check_kind in REQUIRED_RELEASE_CHECK_KINDS
    )
    item = manifest(checks=checks)

    assert item.blocking_check_ids == ("check-no-wave-six-promotion",)
    assert item.blocks_release_readiness is True


def test_manifest_blocks_when_unresolved_blocker_exists() -> None:
    item = manifest(
        blockers=(blocker(severity=WaveFiveReleaseBlockerSeverity.BLOCKING),)
    )

    assert item.unresolved_blocker_ids == ("blocker-review-packet-gap",)
    assert item.blocks_release_readiness is True


def test_manifest_is_ready_for_external_release_review() -> None:
    item = manifest(blockers=(blocker(),))

    assert item.has_required_artifact_coverage is True
    assert item.has_required_check_coverage is True
    assert item.blocking_artifact_ids == ()
    assert item.blocking_check_ids == ()
    assert item.unresolved_blocker_ids == ()
    assert item.makes_no_forbidden_claims is True
    assert item.blocks_release_readiness is False
    assert item.ready_for_external_release_review is True


def test_manifest_bundle_digest_is_deterministic() -> None:
    item = manifest()

    assert item.bundle_digest == item.bundle_digest
    assert len(item.bundle_digest) == 64


def test_ready_manifest_exports_reviewable_traceability_artifact() -> None:
    artifact = manifest().to_artifact_ref()

    assert artifact.kind is WaveFiveArtifactKind.ECOSYSTEM_TRACEABILITY_MAP
    assert artifact.capability_area is WaveFiveCapabilityArea.ECOSYSTEM_TRACEABILITY
    assert artifact.source_system is WaveFiveSourceSystem.IX_COGNITION_KERNEL
    assert artifact.decision is WaveFiveArtifactDecision.READY_FOR_INDEPENDENT_REVIEW
    assert artifact.authority_state is WaveFiveAuthorityState.HUMAN_REVIEW_REQUIRED
    assert artifact.validation_status is (
        WaveFiveValidationStatus.UNDER_INDEPENDENT_REVIEW
    )


def test_blocked_manifest_exports_blocked_artifact() -> None:
    artifact = manifest(
        blockers=(blocker(severity=WaveFiveReleaseBlockerSeverity.BLOCKING),)
    ).to_artifact_ref()

    assert artifact.decision is WaveFiveArtifactDecision.BLOCKED
    assert artifact.authority_state is WaveFiveAuthorityState.BLOCKED
    assert artifact.validation_status is WaveFiveValidationStatus.REJECTED


def test_externally_reviewed_manifest_requires_external_source() -> None:
    with pytest.raises(ValueError, match="external source"):
        manifest(
            manifest_state=(
                WaveFiveReleaseManifestState.EXTERNALLY_REVIEWED_WITH_BOUNDARIES
            ),
            reviewer_ids=("reviewer-001",),
        )


def test_externally_reviewed_manifest_requires_reviewer_ids() -> None:
    with pytest.raises(ValueError, match="reviewer ids"):
        manifest(
            source_system=WaveFiveSourceSystem.INDEPENDENT_REVIEWER,
            manifest_state=(
                WaveFiveReleaseManifestState.EXTERNALLY_REVIEWED_WITH_BOUNDARIES
            ),
        )


def test_externally_reviewed_manifest_exports_bounded_external_artifact() -> None:
    item = manifest(
        source_system=WaveFiveSourceSystem.INDEPENDENT_REVIEWER,
        manifest_state=(
            WaveFiveReleaseManifestState.EXTERNALLY_REVIEWED_WITH_BOUNDARIES
        ),
        reviewer_ids=("reviewer-001",),
    )
    artifact = item.to_artifact_ref()

    assert item.externally_reviewed_with_boundaries is True
    assert artifact.decision is WaveFiveArtifactDecision.EXTERNALLY_REVIEWED
    assert artifact.validation_status is (
        WaveFiveValidationStatus.ACCEPTED_WITH_BOUNDARIES
    )
    assert artifact.externally_validated_with_boundaries is True


def test_manifest_collects_unique_evidence_ids() -> None:
    item = manifest(blockers=(blocker(),))

    assert "evidence-artifact-falsification-ledger" in item.all_evidence_ids
    assert "evidence-check-no-wave-six-promotion" in item.all_evidence_ids
    assert "evidence-blocker-review-packet-gap" in item.all_evidence_ids
    assert len(item.all_evidence_ids) == 30


def test_manifest_fingerprint_is_deterministic() -> None:
    item = manifest()

    assert item.fingerprint() == item.fingerprint()
    assert len(item.fingerprint()) == 64
