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
from ix_cognition_kernel.wave5_review_index import (
    BLOCKING_INDEX_ENTRY_STATUSES,
    EXTERNAL_INDEX_REVIEW_SOURCE_SYSTEMS,
    REQUIRED_REVIEW_INDEX_CHECK_KINDS,
    REQUIRED_REVIEW_INDEX_ENTRY_KINDS,
    SAFE_INDEX_ENTRY_STATUSES,
    WaveFiveReviewIndex,
    WaveFiveReviewIndexBlocker,
    WaveFiveReviewIndexBlockerKind,
    WaveFiveReviewIndexBlockerSeverity,
    WaveFiveReviewIndexCheck,
    WaveFiveReviewIndexCheckKind,
    WaveFiveReviewIndexCheckResult,
    WaveFiveReviewIndexEntry,
    WaveFiveReviewIndexEntryKind,
    WaveFiveReviewIndexEntryStatus,
    WaveFiveReviewIndexState,
    blocking_review_index_entry_statuses,
    external_index_review_source_systems,
    required_review_index_check_kinds,
    required_review_index_entry_kinds,
    safe_review_index_entry_statuses,
)

DIGEST_A = "a" * 64
DIGEST_B = "b" * 64
RELEASE_MANIFEST_ARTIFACT_ID = "wave5-release-manifest-001"
BOUNDED_DECLARATION_ARTIFACT_ID = "wave5-bounded-declaration-001"


def entry(
    entry_id: str = "entry-release-manifest",
    *,
    entry_kind: WaveFiveReviewIndexEntryKind = (
        WaveFiveReviewIndexEntryKind.RELEASE_MANIFEST
    ),
    artifact_id: str = RELEASE_MANIFEST_ARTIFACT_ID,
    status: WaveFiveReviewIndexEntryStatus = WaveFiveReviewIndexEntryStatus.INDEXED,
    digest: str = DIGEST_A,
    limitations: tuple[str, ...] = (),
    blocker_ids: tuple[str, ...] = (),
    claim_boundaries: tuple[WaveFiveClaimBoundary, ...] = (
        WAVE_FIVE_REQUIRED_CLAIM_BOUNDARIES
    ),
) -> WaveFiveReviewIndexEntry:
    return WaveFiveReviewIndexEntry(
        entry_id=entry_id,
        entry_kind=entry_kind,
        status=status,
        artifact_id=artifact_id,
        digest=digest,
        evidence_ids=(f"evidence-{entry_id}",),
        reviewer_route=f"review/{entry_kind.value}",
        source_system=WaveFiveSourceSystem.IX_COGNITION_KERNEL,
        summary="Review index entry is evidence-bound and navigable.",
        limitations=limitations,
        blocker_ids=blocker_ids,
        claim_boundaries=claim_boundaries,
    )


def index_check(
    check_id: str,
    check_kind: WaveFiveReviewIndexCheckKind,
    *,
    result: WaveFiveReviewIndexCheckResult = WaveFiveReviewIndexCheckResult.PASSED,
    blocking: bool = True,
) -> WaveFiveReviewIndexCheck:
    return WaveFiveReviewIndexCheck(
        check_id=check_id,
        check_kind=check_kind,
        result=result,
        description="Review index check preserves Wave 5 navigation boundaries.",
        evidence_ids=(f"evidence-{check_id}",),
        blocking=blocking,
    )


def blocker(
    blocker_id: str = "blocker-release-manifest",
    *,
    entry_kind: WaveFiveReviewIndexEntryKind = (
        WaveFiveReviewIndexEntryKind.RELEASE_MANIFEST
    ),
    blocker_kind: WaveFiveReviewIndexBlockerKind = (
        WaveFiveReviewIndexBlockerKind.UNRESOLVED_RELEASE_BLOCKER
    ),
    severity: WaveFiveReviewIndexBlockerSeverity = (
        WaveFiveReviewIndexBlockerSeverity.LIMITATION
    ),
    resolved: bool = False,
) -> WaveFiveReviewIndexBlocker:
    return WaveFiveReviewIndexBlocker(
        blocker_id=blocker_id,
        blocker_kind=blocker_kind,
        severity=severity,
        entry_kind=entry_kind,
        description="Review index blocker remains visible to reviewers.",
        mitigation="Resolve blocker or preserve it as a visible limitation.",
        evidence_ids=(f"evidence-{blocker_id}",),
        resolved=resolved,
    )


def required_entries() -> tuple[WaveFiveReviewIndexEntry, ...]:
    records: list[WaveFiveReviewIndexEntry] = []
    for index, entry_kind in enumerate(REQUIRED_REVIEW_INDEX_ENTRY_KINDS):
        artifact_id = f"wave5-{entry_kind.value}-001"
        if entry_kind is WaveFiveReviewIndexEntryKind.RELEASE_MANIFEST:
            artifact_id = RELEASE_MANIFEST_ARTIFACT_ID
        elif entry_kind is WaveFiveReviewIndexEntryKind.BOUNDED_DECLARATION:
            artifact_id = BOUNDED_DECLARATION_ARTIFACT_ID
        records.append(
            entry(
                f"entry-{entry_kind.value}",
                entry_kind=entry_kind,
                artifact_id=artifact_id,
                status=WaveFiveReviewIndexEntryStatus.INDEXED_WITH_LIMITS,
                digest=(DIGEST_A if index % 2 == 0 else DIGEST_B),
                limitations=("Review index navigation only; not Wave 6 proof.",),
            )
        )
    return tuple(records)


def required_checks() -> tuple[WaveFiveReviewIndexCheck, ...]:
    return tuple(
        index_check(f"check-{check_kind.value}", check_kind)
        for check_kind in REQUIRED_REVIEW_INDEX_CHECK_KINDS
    )


def review_index(
    *,
    source_system: WaveFiveSourceSystem = WaveFiveSourceSystem.IX_COGNITION_KERNEL,
    index_state: WaveFiveReviewIndexState = (
        WaveFiveReviewIndexState.READY_FOR_EXTERNAL_INDEX_REVIEW
    ),
    entries: tuple[WaveFiveReviewIndexEntry, ...] | None = None,
    checks: tuple[WaveFiveReviewIndexCheck, ...] | None = None,
    blockers: tuple[WaveFiveReviewIndexBlocker, ...] = (),
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
) -> WaveFiveReviewIndex:
    resolved_entries = required_entries() if entries is None else entries
    resolved_checks = required_checks() if checks is None else checks
    return WaveFiveReviewIndex(
        index_id="wave5-review-index-001",
        title="Wave 5 external review evidence index.",
        source_system=source_system,
        index_state=index_state,
        entries=resolved_entries,
        checks=resolved_checks,
        blockers=blockers,
        release_manifest_artifact_id=RELEASE_MANIFEST_ARTIFACT_ID,
        bounded_declaration_artifact_id=BOUNDED_DECLARATION_ARTIFACT_ID,
        protocol_ids=("wave5-external-protocol-001",),
        reviewer_ids=reviewer_ids,
        attempted_wave_six_promotion=attempted_wave_six_promotion,
        claims_agi=claims_agi,
        grants_execution_authority=grants_execution_authority,
        claims_production_ready=claims_production_ready,
        claims_certified=claims_certified,
        claims_independent_validation=claims_independent_validation,
        claim_boundaries=claim_boundaries,
        notes=("Review index points to bounded Wave 5 evidence only.",),
    )


def test_required_review_index_entries_are_locked() -> None:
    assert required_review_index_entry_kinds() == REQUIRED_REVIEW_INDEX_ENTRY_KINDS
    assert len(REQUIRED_REVIEW_INDEX_ENTRY_KINDS) == 14
    assert WaveFiveReviewIndexEntryKind.RELEASE_MANIFEST in (
        REQUIRED_REVIEW_INDEX_ENTRY_KINDS
    )
    assert WaveFiveReviewIndexEntryKind.WORLDTWIN_SCENARIO_BRIDGE in (
        REQUIRED_REVIEW_INDEX_ENTRY_KINDS
    )


def test_required_review_index_checks_are_locked() -> None:
    assert required_review_index_check_kinds() == REQUIRED_REVIEW_INDEX_CHECK_KINDS
    assert len(REQUIRED_REVIEW_INDEX_CHECK_KINDS) == 13
    assert WaveFiveReviewIndexCheckKind.NO_WAVE_SIX_PROMOTION in (
        REQUIRED_REVIEW_INDEX_CHECK_KINDS
    )
    assert WaveFiveReviewIndexCheckKind.NO_EXECUTION_AUTHORITY in (
        REQUIRED_REVIEW_INDEX_CHECK_KINDS
    )


def test_safe_and_blocking_entry_statuses_are_locked() -> None:
    assert safe_review_index_entry_statuses() == SAFE_INDEX_ENTRY_STATUSES
    assert blocking_review_index_entry_statuses() == BLOCKING_INDEX_ENTRY_STATUSES
    assert WaveFiveReviewIndexEntryStatus.INDEXED in SAFE_INDEX_ENTRY_STATUSES
    assert WaveFiveReviewIndexEntryStatus.DISPUTED in BLOCKING_INDEX_ENTRY_STATUSES


def test_external_index_review_sources_are_locked() -> None:
    assert external_index_review_source_systems() == (
        EXTERNAL_INDEX_REVIEW_SOURCE_SYSTEMS
    )
    assert WaveFiveSourceSystem.INDEPENDENT_REVIEWER in (
        EXTERNAL_INDEX_REVIEW_SOURCE_SYSTEMS
    )
    assert WaveFiveSourceSystem.IX_COGNITION_KERNEL not in (
        EXTERNAL_INDEX_REVIEW_SOURCE_SYSTEMS
    )


def test_entry_requires_valid_digest_and_evidence() -> None:
    with pytest.raises(ValueError, match="64-character"):
        entry(digest="not-a-digest")

    with pytest.raises(ValueError, match="evidence ids"):
        WaveFiveReviewIndexEntry(
            entry_id="entry-invalid",
            entry_kind=WaveFiveReviewIndexEntryKind.RELEASE_MANIFEST,
            status=WaveFiveReviewIndexEntryStatus.INDEXED,
            artifact_id=RELEASE_MANIFEST_ARTIFACT_ID,
            digest=DIGEST_A,
            evidence_ids=(),
            reviewer_route="review/release-manifest",
            source_system=WaveFiveSourceSystem.IX_COGNITION_KERNEL,
            summary="Invalid entry.",
        )


def test_limited_entry_requires_limitations() -> None:
    with pytest.raises(ValueError, match="require limitations"):
        entry(status=WaveFiveReviewIndexEntryStatus.INDEXED_WITH_LIMITS)


def test_blocking_entry_requires_blocker_ids() -> None:
    with pytest.raises(ValueError, match="require blocker ids"):
        entry(status=WaveFiveReviewIndexEntryStatus.DISPUTED)


def test_entry_rejects_missing_claim_boundary() -> None:
    with pytest.raises(ValueError, match="no-self-validation"):
        entry(
            claim_boundaries=tuple(
                boundary
                for boundary in WAVE_FIVE_REQUIRED_CLAIM_BOUNDARIES
                if boundary is not WaveFiveClaimBoundary.NO_SELF_VALIDATION
            )
        )


def test_blocking_entry_status_blocks_index_readiness() -> None:
    item = entry(
        status=WaveFiveReviewIndexEntryStatus.DISPUTED,
        blocker_ids=("blocker-001",),
    )

    assert item.blocks_index_readiness is True
    assert item.reviewable_with_boundaries is False


def test_review_index_check_requires_evidence() -> None:
    with pytest.raises(ValueError, match="evidence ids"):
        WaveFiveReviewIndexCheck(
            check_id="check-invalid",
            check_kind=WaveFiveReviewIndexCheckKind.NO_WAVE_SIX_PROMOTION,
            result=WaveFiveReviewIndexCheckResult.PASSED,
            description="Invalid check without evidence.",
            evidence_ids=(),
        )


def test_failed_review_index_check_blocks_readiness() -> None:
    item = index_check(
        "check-failed",
        WaveFiveReviewIndexCheckKind.NO_AGI_OR_CERTIFICATION_CLAIM,
        result=WaveFiveReviewIndexCheckResult.FAILED,
    )

    assert item.passed_with_boundaries is False
    assert item.blocks_index_readiness is True


def test_non_blocking_review_index_check_does_not_block_readiness() -> None:
    item = index_check(
        "check-warning",
        WaveFiveReviewIndexCheckKind.REVIEWER_ROUTES_PRESENT,
        result=WaveFiveReviewIndexCheckResult.NEEDS_MORE_EVIDENCE,
        blocking=False,
    )

    assert item.blocks_index_readiness is False


def test_review_index_blocker_requires_evidence() -> None:
    with pytest.raises(ValueError, match="evidence ids"):
        WaveFiveReviewIndexBlocker(
            blocker_id="blocker-invalid",
            blocker_kind=WaveFiveReviewIndexBlockerKind.MISSING_ENTRY,
            severity=WaveFiveReviewIndexBlockerSeverity.BLOCKING,
            entry_kind=WaveFiveReviewIndexEntryKind.RELEASE_MANIFEST,
            description="Invalid blocker.",
            mitigation="Resolve blocker.",
            evidence_ids=(),
        )


def test_unresolved_blocking_review_index_blocker_blocks_readiness() -> None:
    item = blocker(severity=WaveFiveReviewIndexBlockerSeverity.BLOCKING)

    assert item.blocks_index_readiness is True


def test_resolved_blocking_review_index_blocker_does_not_block_readiness() -> None:
    item = blocker(severity=WaveFiveReviewIndexBlockerSeverity.BLOCKING, resolved=True)

    assert item.blocks_index_readiness is False


def test_index_rejects_manifest_reference_mismatch() -> None:
    entries = tuple(
        entry(
            item.entry_id,
            entry_kind=item.entry_kind,
            artifact_id=(
                "wrong-manifest-id"
                if item.entry_kind is WaveFiveReviewIndexEntryKind.RELEASE_MANIFEST
                else item.artifact_id
            ),
            status=item.status,
            digest=item.digest,
            limitations=item.limitations,
        )
        for item in required_entries()
    )

    with pytest.raises(ValueError, match="release manifest reference"):
        review_index(entries=entries)


def test_index_rejects_declaration_reference_mismatch() -> None:
    entries = tuple(
        entry(
            item.entry_id,
            entry_kind=item.entry_kind,
            artifact_id=(
                "wrong-declaration-id"
                if item.entry_kind is WaveFiveReviewIndexEntryKind.BOUNDED_DECLARATION
                else item.artifact_id
            ),
            status=item.status,
            digest=item.digest,
            limitations=item.limitations,
        )
        for item in required_entries()
    )

    with pytest.raises(ValueError, match="bounded declaration reference"):
        review_index(entries=entries)


def test_index_rejects_forbidden_claim_flags() -> None:
    with pytest.raises(ValueError, match="cannot promote to Wave 6"):
        review_index(attempted_wave_six_promotion=True)

    with pytest.raises(ValueError, match="cannot claim AGI"):
        review_index(claims_agi=True)

    with pytest.raises(ValueError, match="cannot grant execution authority"):
        review_index(grants_execution_authority=True)


def test_index_rejects_production_certification_and_independent_claims() -> None:
    with pytest.raises(ValueError, match="production readiness"):
        review_index(claims_production_ready=True)

    with pytest.raises(ValueError, match="certification"):
        review_index(claims_certified=True)

    with pytest.raises(ValueError, match="independent validation"):
        review_index(claims_independent_validation=True)


def test_index_rejects_missing_claim_boundary() -> None:
    with pytest.raises(ValueError, match="no-self-validation"):
        review_index(
            claim_boundaries=tuple(
                boundary
                for boundary in WAVE_FIVE_REQUIRED_CLAIM_BOUNDARIES
                if boundary is not WaveFiveClaimBoundary.NO_SELF_VALIDATION
            )
        )


def test_index_reports_missing_required_entries_and_checks() -> None:
    item = review_index(
        entries=(entry(),),
        checks=(
            index_check(
                "check-required-entries-present",
                WaveFiveReviewIndexCheckKind.REQUIRED_ENTRIES_PRESENT,
            ),
        ),
    )

    assert item.has_required_entry_coverage is False
    assert WaveFiveReviewIndexEntryKind.WORLDTWIN_SCENARIO_BRIDGE in (
        item.missing_required_entry_kinds
    )
    assert item.has_required_check_coverage is False
    assert WaveFiveReviewIndexCheckKind.NO_WAVE_SIX_PROMOTION in (
        item.missing_required_check_kinds
    )
    assert item.ready_for_external_index_review is False


def test_index_blocks_when_entry_status_is_blocking() -> None:
    entries = tuple(
        entry(
            f"entry-{entry_kind.value}",
            entry_kind=entry_kind,
            artifact_id=(
                RELEASE_MANIFEST_ARTIFACT_ID
                if entry_kind is WaveFiveReviewIndexEntryKind.RELEASE_MANIFEST
                else BOUNDED_DECLARATION_ARTIFACT_ID
                if entry_kind is WaveFiveReviewIndexEntryKind.BOUNDED_DECLARATION
                else f"wave5-{entry_kind.value}-001"
            ),
            status=(
                WaveFiveReviewIndexEntryStatus.DISPUTED
                if entry_kind is WaveFiveReviewIndexEntryKind.FALSIFICATION_LEDGER
                else WaveFiveReviewIndexEntryStatus.INDEXED
            ),
            digest=(DIGEST_A if index % 2 == 0 else DIGEST_B),
            blocker_ids=(
                ("blocker-falsification",)
                if entry_kind is WaveFiveReviewIndexEntryKind.FALSIFICATION_LEDGER
                else ()
            ),
        )
        for index, entry_kind in enumerate(REQUIRED_REVIEW_INDEX_ENTRY_KINDS)
    )
    item = review_index(entries=entries)

    assert item.blocking_entry_ids == ("entry-falsification-ledger",)
    assert item.blocks_index_readiness is True


def test_index_blocks_when_check_fails() -> None:
    checks = tuple(
        index_check(
            f"check-{check_kind.value}",
            check_kind,
            result=(
                WaveFiveReviewIndexCheckResult.FAILED
                if check_kind is WaveFiveReviewIndexCheckKind.NO_WAVE_SIX_PROMOTION
                else WaveFiveReviewIndexCheckResult.PASSED
            ),
        )
        for check_kind in REQUIRED_REVIEW_INDEX_CHECK_KINDS
    )
    item = review_index(checks=checks)

    assert item.blocking_check_ids == ("check-no-wave-six-promotion",)
    assert item.blocks_index_readiness is True


def test_index_blocks_when_unresolved_blocker_exists() -> None:
    item = review_index(
        blockers=(blocker(severity=WaveFiveReviewIndexBlockerSeverity.BLOCKING),)
    )

    assert item.unresolved_blocker_ids == ("blocker-release-manifest",)
    assert item.blocks_index_readiness is True


def test_index_is_ready_for_external_review() -> None:
    item = review_index(blockers=(blocker(),))

    assert item.has_required_entry_coverage is True
    assert item.has_required_check_coverage is True
    assert item.blocking_entry_ids == ()
    assert item.blocking_check_ids == ()
    assert item.unresolved_blocker_ids == ()
    assert item.makes_no_forbidden_claims is True
    assert item.blocks_index_readiness is False
    assert item.ready_for_external_index_review is True


def test_index_bundle_digest_is_deterministic() -> None:
    item = review_index()

    assert item.index_bundle_digest == item.index_bundle_digest
    assert len(item.index_bundle_digest) == 64


def test_ready_index_exports_reviewable_traceability_artifact() -> None:
    artifact = review_index().to_artifact_ref()

    assert artifact.kind is WaveFiveArtifactKind.ECOSYSTEM_TRACEABILITY_MAP
    assert artifact.capability_area is WaveFiveCapabilityArea.ECOSYSTEM_TRACEABILITY
    assert artifact.source_system is WaveFiveSourceSystem.IX_COGNITION_KERNEL
    assert artifact.decision is WaveFiveArtifactDecision.READY_FOR_INDEPENDENT_REVIEW
    assert artifact.authority_state is WaveFiveAuthorityState.HUMAN_REVIEW_REQUIRED
    assert artifact.validation_status is (
        WaveFiveValidationStatus.UNDER_INDEPENDENT_REVIEW
    )


def test_blocked_index_exports_blocked_artifact() -> None:
    artifact = review_index(
        blockers=(blocker(severity=WaveFiveReviewIndexBlockerSeverity.BLOCKING),)
    ).to_artifact_ref()

    assert artifact.decision is WaveFiveArtifactDecision.BLOCKED
    assert artifact.authority_state is WaveFiveAuthorityState.BLOCKED
    assert artifact.validation_status is WaveFiveValidationStatus.REJECTED


def test_externally_reviewed_index_requires_external_source() -> None:
    with pytest.raises(ValueError, match="external source"):
        review_index(
            index_state=WaveFiveReviewIndexState.EXTERNALLY_REVIEWED_WITH_BOUNDARIES,
            reviewer_ids=("reviewer-001",),
        )


def test_externally_reviewed_index_requires_reviewer_ids() -> None:
    with pytest.raises(ValueError, match="reviewer ids"):
        review_index(
            source_system=WaveFiveSourceSystem.INDEPENDENT_REVIEWER,
            index_state=WaveFiveReviewIndexState.EXTERNALLY_REVIEWED_WITH_BOUNDARIES,
        )


def test_externally_reviewed_index_exports_bounded_external_artifact() -> None:
    item = review_index(
        source_system=WaveFiveSourceSystem.INDEPENDENT_REVIEWER,
        index_state=WaveFiveReviewIndexState.EXTERNALLY_REVIEWED_WITH_BOUNDARIES,
        reviewer_ids=("reviewer-001",),
    )
    artifact = item.to_artifact_ref()

    assert item.externally_reviewed_with_boundaries is True
    assert artifact.decision is WaveFiveArtifactDecision.EXTERNALLY_REVIEWED
    assert artifact.validation_status is (
        WaveFiveValidationStatus.ACCEPTED_WITH_BOUNDARIES
    )
    assert artifact.externally_validated_with_boundaries is True


def test_index_collects_unique_evidence_ids() -> None:
    item = review_index(blockers=(blocker(),))

    assert "evidence-entry-release-manifest" in item.all_evidence_ids
    assert "evidence-entry-worldtwin-scenario-bridge" in item.all_evidence_ids
    assert "evidence-check-no-wave-six-promotion" in item.all_evidence_ids
    assert "evidence-blocker-release-manifest" in item.all_evidence_ids
    assert len(item.all_evidence_ids) == 28


def test_index_fingerprint_is_deterministic() -> None:
    item = review_index()

    assert item.fingerprint() == item.fingerprint()
    assert len(item.fingerprint()) == 64
