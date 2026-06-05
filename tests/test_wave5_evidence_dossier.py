import pytest

from ix_cognition_kernel.wave5_contracts import (
    WaveFiveArtifactDecision,
    WaveFiveAuthorityState,
    WaveFiveSourceSystem,
    WaveFiveValidationStatus,
)
from ix_cognition_kernel.wave5_evidence_dossier import (
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


def _dossier_sections(
    status: WaveFiveDossierSectionStatus = WaveFiveDossierSectionStatus.REVIEWABLE,
) -> tuple[WaveFiveDossierSection, ...]:
    return tuple(
        WaveFiveDossierSection(
            section_id=f"section-{section_kind.value}",
            section_kind=section_kind,
            status=status,
            artifact_ids=(f"artifact-{section_kind.value}",),
            evidence_ids=(f"evidence-{section_kind.value}",),
            summary=f"Dossier section for {section_kind.value}",
            source_system=WaveFiveSourceSystem.IX_COGNITION_KERNEL,
            limitations=(
                (f"limited-{section_kind.value}",)
                if status is WaveFiveDossierSectionStatus.REVIEWABLE_WITH_LIMITS
                else ()
            ),
        )
        for section_kind in required_dossier_section_kinds()
    )


def _dossier_checks(
    result: WaveFiveDossierCheckResult = WaveFiveDossierCheckResult.PASSED,
) -> tuple[WaveFiveDossierIntegrityCheck, ...]:
    return tuple(
        WaveFiveDossierIntegrityCheck(
            check_id=f"check-{check_kind.value}",
            check_kind=check_kind,
            result=result,
            description=f"Dossier check for {check_kind.value}",
            evidence_ids=(f"check-evidence-{check_kind.value}",),
        )
        for check_kind in required_dossier_check_kinds()
    )


def _evidence_dossier(
    *,
    review_state: WaveFiveDossierReviewState = (
        WaveFiveDossierReviewState.READY_FOR_EXTERNAL_DOSSIER_REVIEW
    ),
    source_system: WaveFiveSourceSystem = WaveFiveSourceSystem.IX_COGNITION_KERNEL,
    sections: tuple[WaveFiveDossierSection, ...] | None = None,
    checks: tuple[WaveFiveDossierIntegrityCheck, ...] | None = None,
    gaps: tuple[WaveFiveDossierGap, ...] = (),
) -> WaveFiveEvidenceDossier:
    return WaveFiveEvidenceDossier(
        dossier_id="dossier-1",
        title="Wave 5 evidence dossier",
        source_system=source_system,
        review_state=review_state,
        sections=sections or _dossier_sections(),
        integrity_checks=checks or _dossier_checks(),
        gaps=gaps,
        readiness_gate_artifact_id="readiness-gate-1",
        protocol_ids=("protocol-1",),
        reviewer_ids=(
            ("reviewer-1",)
            if source_system != WaveFiveSourceSystem.IX_COGNITION_KERNEL
            else ()
        ),
    )


def test_required_dossier_sets_are_locked() -> None:
    assert len(required_dossier_section_kinds()) >= 10
    assert len(required_dossier_check_kinds()) >= 8
    assert WaveFiveDossierSectionStatus.REVIEWABLE in safe_dossier_section_statuses()
    assert WaveFiveDossierSectionStatus.MISSING in blocking_dossier_section_statuses()
    assert (
        WaveFiveSourceSystem.INDEPENDENT_REVIEWER
        in external_dossier_review_source_systems()
    )


def test_evidence_dossier_ready_for_external_review_when_complete() -> None:
    dossier = _evidence_dossier()

    assert dossier.has_required_section_coverage
    assert dossier.has_required_check_coverage
    assert dossier.ready_for_external_dossier_review
    assert not dossier.blocks_dossier_readiness
    assert dossier.blocking_section_ids == ()
    assert dossier.blocking_check_ids == ()
    assert dossier.unresolved_gap_ids == ()

    artifact_ref = dossier.to_artifact_ref()
    assert artifact_ref.decision is WaveFiveArtifactDecision.READY_FOR_INDEPENDENT_REVIEW
    assert artifact_ref.authority_state is WaveFiveAuthorityState.HUMAN_REVIEW_REQUIRED
    assert artifact_ref.validation_status is WaveFiveValidationStatus.UNDER_INDEPENDENT_REVIEW
    assert artifact_ref.evidence_ids == dossier.all_evidence_ids


def test_evidence_dossier_reports_missing_required_section() -> None:
    sections = tuple(
        section
        for section in _dossier_sections()
        if section.section_kind is not WaveFiveDossierSectionKind.EXTERNAL_PROTOCOLS
    )

    dossier = _evidence_dossier(sections=sections)

    assert dossier.missing_required_section_kinds == (
        WaveFiveDossierSectionKind.EXTERNAL_PROTOCOLS,
    )
    assert dossier.blocks_dossier_readiness
    assert not dossier.ready_for_external_dossier_review


def test_evidence_dossier_blocks_unresolved_blocking_gap() -> None:
    gap = WaveFiveDossierGap(
        gap_id="gap-1",
        gap_kind=WaveFiveDossierGapKind.EXTERNAL_REVIEW_GAP,
        severity=WaveFiveDossierGapSeverity.BLOCKING,
        section_kind=WaveFiveDossierSectionKind.INDEPENDENT_REVIEWERS,
        description="Independent reviewer evidence is missing.",
        mitigation="Attach independent reviewer evidence before closure.",
        evidence_ids=("gap-evidence-1",),
    )

    dossier = _evidence_dossier(gaps=(gap,))

    assert dossier.blocks_dossier_readiness
    assert dossier.unresolved_gap_ids == ("gap-1",)
    assert not dossier.ready_for_external_dossier_review


def test_evidence_dossier_blocks_failed_integrity_check() -> None:
    checks = _dossier_checks(result=WaveFiveDossierCheckResult.FAILED)

    dossier = _evidence_dossier(checks=checks)

    assert dossier.blocks_dossier_readiness
    assert dossier.blocking_check_ids
    assert not dossier.ready_for_external_dossier_review


def test_evidence_dossier_rejects_forbidden_claims() -> None:
    with pytest.raises(ValueError, match="cannot claim AGI"):
        WaveFiveEvidenceDossier(
            dossier_id="invalid-dossier",
            title="Invalid Wave 5 dossier",
            source_system=WaveFiveSourceSystem.IX_COGNITION_KERNEL,
            review_state=WaveFiveDossierReviewState.INTERNAL_DOSSIER_READY,
            sections=_dossier_sections(),
            integrity_checks=_dossier_checks(),
            gaps=(),
            readiness_gate_artifact_id="readiness-gate-1",
            protocol_ids=("protocol-1",),
            claims_agi=True,
        )


def test_externally_reviewed_dossier_requires_external_source() -> None:
    with pytest.raises(ValueError, match="external source"):
        _evidence_dossier(
            review_state=WaveFiveDossierReviewState.EXTERNALLY_REVIEWED_WITH_BOUNDARIES,
            source_system=WaveFiveSourceSystem.IX_COGNITION_KERNEL,
        )


def test_externally_reviewed_dossier_exports_reviewed_artifact() -> None:
    dossier = _evidence_dossier(
        review_state=WaveFiveDossierReviewState.EXTERNALLY_REVIEWED_WITH_BOUNDARIES,
        source_system=WaveFiveSourceSystem.EXTERNAL_REVIEW,
    )

    assert dossier.externally_reviewed_with_boundaries
    artifact_ref = dossier.to_artifact_ref()
    assert artifact_ref.decision is WaveFiveArtifactDecision.EXTERNALLY_REVIEWED
    assert artifact_ref.validation_status is WaveFiveValidationStatus.ACCEPTED_WITH_BOUNDARIES
