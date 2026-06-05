import pytest

from ix_cognition_kernel.wave5_contracts import (
    WaveFiveArtifactDecision,
    WaveFiveAuthorityState,
    WaveFiveSourceSystem,
    WaveFiveValidationStatus,
)
from ix_cognition_kernel.wave5_release_manifest import (
    WaveFiveManifestCheckResult,
    WaveFiveManifestEntryStatus,
    WaveFiveManifestIntegrityCheckKind,
    WaveFiveReleaseBlocker,
    WaveFiveReleaseBlockerKind,
    WaveFiveReleaseBlockerSeverity,
    WaveFiveReleaseManifest,
    WaveFiveReleaseManifestEntry,
    WaveFiveReleaseManifestIntegrityCheck,
    WaveFiveReleaseManifestState,
    blocking_manifest_entry_statuses,
    external_release_review_source_systems,
    required_manifest_artifact_families,
    required_manifest_check_kinds,
    safe_manifest_entry_statuses,
)

DIGEST = "a" * 64


def _manifest_entries(
    status: WaveFiveManifestEntryStatus = WaveFiveManifestEntryStatus.SEALED,
) -> tuple[WaveFiveReleaseManifestEntry, ...]:
    return tuple(
        WaveFiveReleaseManifestEntry(
            entry_id=f"entry-{artifact_family.value}",
            artifact_family=artifact_family,
            status=status,
            artifact_ids=(f"artifact-{artifact_family.value}",),
            evidence_ids=(f"evidence-{artifact_family.value}",),
            digest=DIGEST,
            summary=f"Release manifest entry for {artifact_family.value}",
            limitations=(
                (f"limited-{artifact_family.value}",)
                if status is WaveFiveManifestEntryStatus.SEALED_WITH_LIMITS
                else ()
            ),
            blocker_ids=(
                (f"blocker-{artifact_family.value}",)
                if status in blocking_manifest_entry_statuses()
                else ()
            ),
        )
        for artifact_family in required_manifest_artifact_families()
    )


def _manifest_checks(
    result: WaveFiveManifestCheckResult = WaveFiveManifestCheckResult.PASSED,
) -> tuple[WaveFiveReleaseManifestIntegrityCheck, ...]:
    return tuple(
        WaveFiveReleaseManifestIntegrityCheck(
            check_id=f"check-{check_kind.value}",
            check_kind=check_kind,
            result=result,
            description=f"Release manifest check for {check_kind.value}",
            evidence_ids=(f"check-evidence-{check_kind.value}",),
        )
        for check_kind in required_manifest_check_kinds()
    )


def _release_manifest(
    *,
    manifest_state: WaveFiveReleaseManifestState = (
        WaveFiveReleaseManifestState.READY_FOR_EXTERNAL_RELEASE_REVIEW
    ),
    source_system: WaveFiveSourceSystem = WaveFiveSourceSystem.IX_COGNITION_KERNEL,
    entries: tuple[WaveFiveReleaseManifestEntry, ...] | None = None,
    checks: tuple[WaveFiveReleaseManifestIntegrityCheck, ...] | None = None,
    blockers: tuple[WaveFiveReleaseBlocker, ...] = (),
    reviewer_ids: tuple[str, ...] = (),
) -> WaveFiveReleaseManifest:
    return WaveFiveReleaseManifest(
        manifest_id="release-manifest-1",
        title="Wave 5 release manifest",
        source_system=source_system,
        manifest_state=manifest_state,
        entries=entries or _manifest_entries(),
        integrity_checks=checks or _manifest_checks(),
        blockers=blockers,
        evidence_dossier_artifact_id="dossier-1",
        maturity_scorecard_artifact_id="scorecard-1",
        external_review_packet_artifact_id="review-packet-1",
        protocol_ids=("protocol-1",),
        reviewer_ids=reviewer_ids,
    )


def test_required_release_manifest_sets_are_locked() -> None:
    assert len(required_manifest_artifact_families()) >= 10
    assert len(required_manifest_check_kinds()) >= 10
    assert WaveFiveManifestEntryStatus.SEALED in safe_manifest_entry_statuses()
    assert WaveFiveManifestEntryStatus.MISSING in blocking_manifest_entry_statuses()
    assert (
        WaveFiveSourceSystem.INDEPENDENT_REVIEWER
        in external_release_review_source_systems()
    )


def test_release_manifest_ready_for_external_review_when_complete() -> None:
    manifest = _release_manifest()

    assert manifest.has_required_family_coverage
    assert manifest.has_required_check_coverage
    assert manifest.ready_for_external_release_review
    assert not manifest.blocks_release
    assert manifest.blocking_entry_ids == ()
    assert manifest.blocking_check_ids == ()
    assert manifest.unresolved_blocker_ids == ()
    assert len(manifest.manifest_bundle_digest) == 64

    artifact_ref = manifest.to_artifact_ref()
    assert artifact_ref.decision is WaveFiveArtifactDecision.READY_FOR_INDEPENDENT_REVIEW
    assert artifact_ref.authority_state is WaveFiveAuthorityState.HUMAN_REVIEW_REQUIRED
    assert artifact_ref.validation_status is WaveFiveValidationStatus.UNDER_INDEPENDENT_REVIEW
    assert artifact_ref.evidence_ids == manifest.all_evidence_ids


def test_release_manifest_reports_missing_required_family() -> None:
    missing_family = required_manifest_artifact_families()[0]
    entries = tuple(
        entry for entry in _manifest_entries() if entry.artifact_family is not missing_family
    )

    manifest = _release_manifest(entries=entries)

    assert manifest.missing_required_artifact_families == (missing_family,)
    assert manifest.blocks_release
    assert not manifest.ready_for_external_release_review


def test_release_manifest_blocks_failed_integrity_check() -> None:
    manifest = _release_manifest(
        checks=_manifest_checks(result=WaveFiveManifestCheckResult.FAILED)
    )

    assert manifest.blocking_check_ids
    assert manifest.blocks_release
    assert not manifest.ready_for_external_release_review


def test_release_manifest_blocks_unresolved_release_blocker() -> None:
    blocker = WaveFiveReleaseBlocker(
        blocker_id="blocker-1",
        blocker_kind=WaveFiveReleaseBlockerKind.UNRESOLVED_FALSIFICATION,
        severity=WaveFiveReleaseBlockerSeverity.BLOCKING,
        artifact_family=required_manifest_artifact_families()[0],
        description="A falsification blocker remains unresolved.",
        mitigation="Resolve the falsification blocker before release review.",
        evidence_ids=("blocker-evidence-1",),
    )

    manifest = _release_manifest(blockers=(blocker,))

    assert manifest.unresolved_blocker_ids == ("blocker-1",)
    assert manifest.blocks_release
    assert not manifest.ready_for_external_release_review


def test_release_manifest_entry_requires_digest_shape() -> None:
    with pytest.raises(ValueError, match="64-character SHA-256"):
        WaveFiveReleaseManifestEntry(
            entry_id="entry-invalid-digest",
            artifact_family=required_manifest_artifact_families()[0],
            status=WaveFiveManifestEntryStatus.SEALED,
            artifact_ids=("artifact-1",),
            evidence_ids=("evidence-1",),
            digest="not-a-digest",
            summary="Invalid digest entry.",
        )


def test_release_manifest_rejects_forbidden_claims() -> None:
    with pytest.raises(ValueError, match="cannot claim AGI"):
        WaveFiveReleaseManifest(
            manifest_id="invalid-release-manifest",
            title="Invalid release manifest",
            source_system=WaveFiveSourceSystem.IX_COGNITION_KERNEL,
            manifest_state=WaveFiveReleaseManifestState.INTERNAL_MANIFEST_READY,
            entries=_manifest_entries(),
            integrity_checks=_manifest_checks(),
            blockers=(),
            evidence_dossier_artifact_id="dossier-1",
            maturity_scorecard_artifact_id="scorecard-1",
            external_review_packet_artifact_id="review-packet-1",
            protocol_ids=("protocol-1",),
            claims_agi=True,
        )


def test_externally_reviewed_manifest_requires_external_source() -> None:
    with pytest.raises(ValueError, match="external source"):
        _release_manifest(
            manifest_state=(
                WaveFiveReleaseManifestState.EXTERNALLY_REVIEWED_WITH_BOUNDARIES
            ),
            source_system=WaveFiveSourceSystem.IX_COGNITION_KERNEL,
            reviewer_ids=("reviewer-1",),
        )


def test_externally_reviewed_manifest_exports_reviewed_artifact() -> None:
    manifest = _release_manifest(
        manifest_state=WaveFiveReleaseManifestState.EXTERNALLY_REVIEWED_WITH_BOUNDARIES,
        source_system=WaveFiveSourceSystem.EXTERNAL_REVIEW,
        reviewer_ids=("reviewer-1",),
    )

    assert manifest.externally_reviewed_with_boundaries
    artifact_ref = manifest.to_artifact_ref()
    assert artifact_ref.decision is WaveFiveArtifactDecision.EXTERNALLY_REVIEWED
    assert artifact_ref.validation_status is WaveFiveValidationStatus.ACCEPTED_WITH_BOUNDARIES
