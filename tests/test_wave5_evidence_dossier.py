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
from ix_cognition_kernel.wave5_evidence_dossier import (
    BLOCKING_DOSSIER_SECTION_STATUSES,
    EXTERNAL_DOSSIER_REVIEW_SOURCE_SYSTEMS,
    REQUIRED_DOSSIER_CHECK_KINDS,
    REQUIRED_DOSSIER_SECTION_KINDS,
    SAFE_DOSSIER_SECTION_STATUSES,
    WaveFiveDossierCheckResult,
    WaveFiveDossierGap,
    WaveFiveDossierGapKind,
    WaveFiveDossierGapSeverity,
    WaveFiveDossierIntegrityCheck,
    WaveFiveDossierIntegrityCheckKind,
    WaveFiveDossierReviewState,
    WaveFiveDossierSection,
    WaveFiveDossierSectionKind,
    WaveFiveDossierSectionStatus,
    WaveFiveEvidenceDossier,
    blocking_dossier_section_statuses,
    external_dossier_review_source_systems,
    required_dossier_check_kinds,
    required_dossier_section_kinds,
    safe_dossier_section_statuses,
)


def section(
    section_id: str = "section-external-protocols",
    *,
    section_kind: WaveFiveDossierSectionKind = (
        WaveFiveDossierSectionKind.EXTERNAL_PROTOCOLS
    ),
    status: WaveFiveDossierSectionStatus = WaveFiveDossierSectionStatus.REVIEWABLE,
    limitations: tuple[str, ...] = (),
    claim_boundaries: tuple[WaveFiveClaimBoundary, ...] = (
        WAVE_FIVE_REQUIRED_CLAIM_BOUNDARIES
    ),
) -> WaveFiveDossierSection:
    return WaveFiveDossierSection(
        section_id=section_id,
        section_kind=section_kind,
        status=status,
        artifact_ids=(f"artifact-{section_id}",),
        evidence_ids=(f"evidence-{section_id}",),
        summary="Dossier section is evidence-bound and reviewable.",
        source_system=WaveFiveSourceSystem.IX_COGNITION_KERNEL,
        limitations=limitations,
        reviewer_ids=("reviewer-001",),
        claim_boundaries=claim_boundaries,
    )


def integrity_check(
    check_id: str,
    check_kind: WaveFiveDossierIntegrityCheckKind,
    *,
    result: WaveFiveDossierCheckResult = WaveFiveDossierCheckResult.PASSED,
    blocking: bool = True,
) -> WaveFiveDossierIntegrityCheck:
    return WaveFiveDossierIntegrityCheck(
        check_id=check_id,
        check_kind=check_kind,
        result=result,
        description="Dossier integrity check preserves Wave 5 boundaries.",
        evidence_ids=(f"evidence-{check_id}",),
        blocking=blocking,
    )


def gap(
    gap_id: str = "gap-external-review",
    *,
    section_kind: WaveFiveDossierSectionKind = (
        WaveFiveDossierSectionKind.INDEPENDENT_REVIEWERS
    ),
    gap_kind: WaveFiveDossierGapKind = WaveFiveDossierGapKind.EXTERNAL_REVIEW_GAP,
    severity: WaveFiveDossierGapSeverity = WaveFiveDossierGapSeverity.LIMITATION,
    resolved: bool = False,
) -> WaveFiveDossierGap:
    return WaveFiveDossierGap(
        gap_id=gap_id,
        gap_kind=gap_kind,
        severity=severity,
        section_kind=section_kind,
        description="Dossier gap is visible to reviewers.",
        mitigation="Resolve or preserve as a visible limitation before overclaim.",
        evidence_ids=(f"evidence-{gap_id}",),
        resolved=resolved,
    )


def required_sections() -> tuple[WaveFiveDossierSection, ...]:
    return tuple(
        section(
            f"section-{section_kind.value}",
            section_kind=section_kind,
            status=WaveFiveDossierSectionStatus.REVIEWABLE_WITH_LIMITS,
            limitations=("Reviewable for Wave 5 evidence only; not Wave 6 proof.",),
        )
        for section_kind in REQUIRED_DOSSIER_SECTION_KINDS
    )


def required_checks() -> tuple[WaveFiveDossierIntegrityCheck, ...]:
    return tuple(
        integrity_check(f"check-{check_kind.value}", check_kind)
        for check_kind in REQUIRED_DOSSIER_CHECK_KINDS
    )


def dossier(
    *,
    source_system: WaveFiveSourceSystem = WaveFiveSourceSystem.IX_COGNITION_KERNEL,
    review_state: WaveFiveDossierReviewState = (
        WaveFiveDossierReviewState.READY_FOR_EXTERNAL_DOSSIER_REVIEW
    ),
    sections: tuple[WaveFiveDossierSection, ...] | None = None,
    checks: tuple[WaveFiveDossierIntegrityCheck, ...] | None = None,
    gaps: tuple[WaveFiveDossierGap, ...] = (),
    reviewer_ids: tuple[str, ...] = (),
    attempted_wave_six_promotion: bool = False,
    claims_agi: bool = False,
    grants_execution_authority: bool = False,
    claims_production_ready: bool = False,
    claims_certified: bool = False,
    claim_boundaries: tuple[WaveFiveClaimBoundary, ...] = (
        WAVE_FIVE_REQUIRED_CLAIM_BOUNDARIES
    ),
) -> WaveFiveEvidenceDossier:
    resolved_sections = required_sections() if sections is None else sections
    resolved_checks = required_checks() if checks is None else checks
    return WaveFiveEvidenceDossier(
        dossier_id="wave5-evidence-dossier-001",
        title="Wave 5 compiled evidence dossier for Wave 6 readiness review.",
        source_system=source_system,
        review_state=review_state,
        sections=resolved_sections,
        integrity_checks=resolved_checks,
        gaps=gaps,
        readiness_gate_artifact_id="wave5-wave6-readiness-gate-001",
        protocol_ids=("wave5-external-protocol-001",),
        reviewer_ids=reviewer_ids,
        attempted_wave_six_promotion=attempted_wave_six_promotion,
        claims_agi=claims_agi,
        grants_execution_authority=grants_execution_authority,
        claims_production_ready=claims_production_ready,
        claims_certified=claims_certified,
        claim_boundaries=claim_boundaries,
        notes=("The dossier is evidence compilation, not Wave 6 promotion.",),
    )


def test_required_dossier_sections_are_locked() -> None:
    assert required_dossier_section_kinds() == REQUIRED_DOSSIER_SECTION_KINDS
    assert len(REQUIRED_DOSSIER_SECTION_KINDS) == 14
    assert WaveFiveDossierSectionKind.WAVE_SIX_READINESS_GATE in (
        REQUIRED_DOSSIER_SECTION_KINDS
    )


def test_required_dossier_checks_are_locked() -> None:
    assert required_dossier_check_kinds() == REQUIRED_DOSSIER_CHECK_KINDS
    assert len(REQUIRED_DOSSIER_CHECK_KINDS) == 10
    assert WaveFiveDossierIntegrityCheckKind.NO_WAVE_SIX_PROMOTION in (
        REQUIRED_DOSSIER_CHECK_KINDS
    )


def test_safe_and_blocking_dossier_statuses_are_locked() -> None:
    assert safe_dossier_section_statuses() == SAFE_DOSSIER_SECTION_STATUSES
    assert blocking_dossier_section_statuses() == BLOCKING_DOSSIER_SECTION_STATUSES
    assert WaveFiveDossierSectionStatus.REVIEWABLE in SAFE_DOSSIER_SECTION_STATUSES
    assert WaveFiveDossierSectionStatus.DISPUTED in (
        BLOCKING_DOSSIER_SECTION_STATUSES
    )


def test_external_dossier_review_sources_are_locked() -> None:
    assert external_dossier_review_source_systems() == (
        EXTERNAL_DOSSIER_REVIEW_SOURCE_SYSTEMS
    )
    assert WaveFiveSourceSystem.INDEPENDENT_REVIEWER in (
        EXTERNAL_DOSSIER_REVIEW_SOURCE_SYSTEMS
    )
    assert WaveFiveSourceSystem.IX_COGNITION_KERNEL not in (
        EXTERNAL_DOSSIER_REVIEW_SOURCE_SYSTEMS
    )


def test_section_requires_artifacts_and_evidence() -> None:
    with pytest.raises(ValueError, match="artifact ids"):
        WaveFiveDossierSection(
            section_id="section-invalid",
            section_kind=WaveFiveDossierSectionKind.EXTERNAL_PROTOCOLS,
            status=WaveFiveDossierSectionStatus.REVIEWABLE,
            artifact_ids=(),
            evidence_ids=("evidence",),
            summary="Invalid section.",
            source_system=WaveFiveSourceSystem.IX_COGNITION_KERNEL,
        )

    with pytest.raises(ValueError, match="evidence ids"):
        WaveFiveDossierSection(
            section_id="section-invalid",
            section_kind=WaveFiveDossierSectionKind.EXTERNAL_PROTOCOLS,
            status=WaveFiveDossierSectionStatus.REVIEWABLE,
            artifact_ids=("artifact",),
            evidence_ids=(),
            summary="Invalid section.",
            source_system=WaveFiveSourceSystem.IX_COGNITION_KERNEL,
        )


def test_limited_section_requires_limitations() -> None:
    with pytest.raises(ValueError, match="require limitations"):
        section(status=WaveFiveDossierSectionStatus.REVIEWABLE_WITH_LIMITS)


def test_section_rejects_missing_claim_boundary() -> None:
    with pytest.raises(ValueError, match="no-self-validation"):
        section(
            claim_boundaries=tuple(
                boundary
                for boundary in WAVE_FIVE_REQUIRED_CLAIM_BOUNDARIES
                if boundary is not WaveFiveClaimBoundary.NO_SELF_VALIDATION
            )
        )


def test_blocking_section_status_blocks_dossier_readiness() -> None:
    item = section(status=WaveFiveDossierSectionStatus.DISPUTED)

    assert item.blocks_dossier_readiness is True
    assert item.reviewable_with_boundaries is False


def test_check_requires_evidence() -> None:
    with pytest.raises(ValueError, match="evidence ids"):
        WaveFiveDossierIntegrityCheck(
            check_id="check-invalid",
            check_kind=WaveFiveDossierIntegrityCheckKind.NO_WAVE_SIX_PROMOTION,
            result=WaveFiveDossierCheckResult.PASSED,
            description="Invalid check without evidence.",
            evidence_ids=(),
        )


def test_failed_check_blocks_dossier_readiness() -> None:
    item = integrity_check(
        "check-failed",
        WaveFiveDossierIntegrityCheckKind.NO_AGI_OR_CERTIFICATION_CLAIM,
        result=WaveFiveDossierCheckResult.FAILED,
    )

    assert item.passed_with_boundaries is False
    assert item.blocks_dossier_readiness is True


def test_non_blocking_check_does_not_block_dossier_readiness() -> None:
    item = integrity_check(
        "check-warning",
        WaveFiveDossierIntegrityCheckKind.UNRESOLVED_GAPS_VISIBLE,
        result=WaveFiveDossierCheckResult.NEEDS_MORE_EVIDENCE,
        blocking=False,
    )

    assert item.blocks_dossier_readiness is False


def test_gap_requires_evidence() -> None:
    with pytest.raises(ValueError, match="evidence ids"):
        WaveFiveDossierGap(
            gap_id="gap-invalid",
            gap_kind=WaveFiveDossierGapKind.MISSING_EVIDENCE,
            severity=WaveFiveDossierGapSeverity.BLOCKING,
            section_kind=WaveFiveDossierSectionKind.MEMORY_INTEGRITY,
            description="Invalid gap.",
            mitigation="Resolve gap.",
            evidence_ids=(),
        )


def test_unresolved_blocking_gap_blocks_dossier_readiness() -> None:
    item = gap(severity=WaveFiveDossierGapSeverity.BLOCKING)

    assert item.blocks_dossier_readiness is True


def test_resolved_blocking_gap_does_not_block_dossier_readiness() -> None:
    item = gap(severity=WaveFiveDossierGapSeverity.BLOCKING, resolved=True)

    assert item.blocks_dossier_readiness is False


def test_dossier_rejects_forbidden_claim_flags() -> None:
    with pytest.raises(ValueError, match="cannot promote to Wave 6"):
        dossier(attempted_wave_six_promotion=True)

    with pytest.raises(ValueError, match="cannot claim AGI"):
        dossier(claims_agi=True)

    with pytest.raises(ValueError, match="cannot grant execution authority"):
        dossier(grants_execution_authority=True)


def test_dossier_rejects_production_and_certification_claims() -> None:
    with pytest.raises(ValueError, match="production readiness"):
        dossier(claims_production_ready=True)

    with pytest.raises(ValueError, match="certification"):
        dossier(claims_certified=True)


def test_dossier_rejects_missing_claim_boundary() -> None:
    with pytest.raises(ValueError, match="no-self-validation"):
        dossier(
            claim_boundaries=tuple(
                boundary
                for boundary in WAVE_FIVE_REQUIRED_CLAIM_BOUNDARIES
                if boundary is not WaveFiveClaimBoundary.NO_SELF_VALIDATION
            )
        )


def test_dossier_reports_missing_required_sections_and_checks() -> None:
    item = dossier(
        sections=(section(),),
        checks=(
            integrity_check(
                "check-required-sections-present",
                WaveFiveDossierIntegrityCheckKind.REQUIRED_SECTIONS_PRESENT,
            ),
        ),
    )

    assert item.has_required_section_coverage is False
    assert WaveFiveDossierSectionKind.WAVE_SIX_READINESS_GATE in (
        item.missing_required_section_kinds
    )
    assert item.has_required_check_coverage is False
    assert WaveFiveDossierIntegrityCheckKind.NO_WAVE_SIX_PROMOTION in (
        item.missing_required_check_kinds
    )
    assert item.ready_for_external_dossier_review is False


def test_dossier_blocks_when_section_status_is_blocking() -> None:
    sections = tuple(
        section(
            f"section-{section_kind.value}",
            section_kind=section_kind,
            status=(
                WaveFiveDossierSectionStatus.DISPUTED
                if section_kind is WaveFiveDossierSectionKind.REPEATABILITY_LEDGER
                else WaveFiveDossierSectionStatus.REVIEWABLE
            ),
        )
        for section_kind in REQUIRED_DOSSIER_SECTION_KINDS
    )
    item = dossier(sections=sections)

    assert item.blocking_section_ids == ("section-repeatability-ledger",)
    assert item.blocks_dossier_readiness is True


def test_dossier_blocks_when_integrity_check_fails() -> None:
    checks = tuple(
        integrity_check(
            f"check-{check_kind.value}",
            check_kind,
            result=(
                WaveFiveDossierCheckResult.FAILED
                if check_kind
                is WaveFiveDossierIntegrityCheckKind.NO_WAVE_SIX_PROMOTION
                else WaveFiveDossierCheckResult.PASSED
            ),
        )
        for check_kind in REQUIRED_DOSSIER_CHECK_KINDS
    )
    item = dossier(checks=checks)

    assert item.blocking_check_ids == ("check-no-wave-six-promotion",)
    assert item.blocks_dossier_readiness is True


def test_dossier_blocks_when_unresolved_gap_exists() -> None:
    item = dossier(gaps=(gap(severity=WaveFiveDossierGapSeverity.BLOCKING),))

    assert item.unresolved_gap_ids == ("gap-external-review",)
    assert item.blocks_dossier_readiness is True


def test_dossier_is_ready_for_external_review() -> None:
    item = dossier(gaps=(gap(),))

    assert item.has_required_section_coverage is True
    assert item.has_required_check_coverage is True
    assert item.blocking_section_ids == ()
    assert item.blocking_check_ids == ()
    assert item.unresolved_gap_ids == ()
    assert item.makes_no_forbidden_claims is True
    assert item.blocks_dossier_readiness is False
    assert item.ready_for_external_dossier_review is True


def test_ready_dossier_exports_reviewable_traceability_artifact() -> None:
    artifact = dossier().to_artifact_ref()

    assert artifact.kind is WaveFiveArtifactKind.ECOSYSTEM_TRACEABILITY_MAP
    assert artifact.capability_area is WaveFiveCapabilityArea.ECOSYSTEM_TRACEABILITY
    assert artifact.source_system is WaveFiveSourceSystem.IX_COGNITION_KERNEL
    assert artifact.decision is WaveFiveArtifactDecision.READY_FOR_INDEPENDENT_REVIEW
    assert artifact.authority_state is WaveFiveAuthorityState.HUMAN_REVIEW_REQUIRED
    assert artifact.validation_status is (
        WaveFiveValidationStatus.UNDER_INDEPENDENT_REVIEW
    )


def test_blocked_dossier_exports_blocked_artifact() -> None:
    artifact = dossier(
        gaps=(gap(severity=WaveFiveDossierGapSeverity.BLOCKING),)
    ).to_artifact_ref()

    assert artifact.decision is WaveFiveArtifactDecision.BLOCKED
    assert artifact.authority_state is WaveFiveAuthorityState.BLOCKED
    assert artifact.validation_status is WaveFiveValidationStatus.REJECTED


def test_externally_reviewed_dossier_requires_external_source() -> None:
    with pytest.raises(ValueError, match="external source"):
        dossier(
            review_state=WaveFiveDossierReviewState.EXTERNALLY_REVIEWED_WITH_BOUNDARIES,
            reviewer_ids=("reviewer-001",),
        )


def test_externally_reviewed_dossier_requires_reviewer_ids() -> None:
    with pytest.raises(ValueError, match="reviewer ids"):
        dossier(
            source_system=WaveFiveSourceSystem.INDEPENDENT_REVIEWER,
            review_state=WaveFiveDossierReviewState.EXTERNALLY_REVIEWED_WITH_BOUNDARIES,
        )


def test_externally_reviewed_dossier_exports_bounded_external_artifact() -> None:
    item = dossier(
        source_system=WaveFiveSourceSystem.INDEPENDENT_REVIEWER,
        review_state=WaveFiveDossierReviewState.EXTERNALLY_REVIEWED_WITH_BOUNDARIES,
        reviewer_ids=("reviewer-001",),
    )
    artifact = item.to_artifact_ref()

    assert item.externally_reviewed_with_boundaries is True
    assert artifact.decision is WaveFiveArtifactDecision.EXTERNALLY_REVIEWED
    assert artifact.validation_status is (
        WaveFiveValidationStatus.ACCEPTED_WITH_BOUNDARIES
    )
    assert artifact.externally_validated_with_boundaries is True


def test_dossier_collects_unique_evidence_ids() -> None:
    item = dossier(gaps=(gap(),))

    assert item.all_evidence_ids[0] == "evidence-section-adversarial-safety"
    assert "evidence-section-wave-six-readiness-gate" in item.all_evidence_ids
    assert "evidence-check-no-wave-six-promotion" in item.all_evidence_ids
    assert "evidence-gap-external-review" in item.all_evidence_ids
    assert len(item.all_evidence_ids) == 25


def test_dossier_fingerprint_is_deterministic() -> None:
    item = dossier()

    assert item.fingerprint() == item.fingerprint()
    assert len(item.fingerprint()) == 64
