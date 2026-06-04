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
from ix_cognition_kernel.wave5_maturity_scorecard import (
    BLOCKING_SCORE_STATUSES,
    EXTERNAL_SCORECARD_REVIEW_SOURCE_SYSTEMS,
    REQUIRED_SCORE_AREAS,
    REQUIRED_SCORECARD_CHECKS,
    SAFE_SCORE_STATUSES,
    WaveFiveMaturityCheckKind,
    WaveFiveMaturityCheckResult,
    WaveFiveMaturityReviewState,
    WaveFiveMaturityScoreArea,
    WaveFiveMaturityScoreSection,
    WaveFiveMaturityScoreStatus,
    WaveFiveMaturityScorecard,
    WaveFiveMaturityScorecardCheck,
    blocking_score_statuses,
    external_scorecard_review_source_systems,
    required_score_areas,
    required_scorecard_checks,
    safe_score_statuses,
)


def score_section(
    section_id: str = "score-external-protocols",
    *,
    area: WaveFiveMaturityScoreArea = WaveFiveMaturityScoreArea.EXTERNAL_PROTOCOLS,
    status: WaveFiveMaturityScoreStatus = WaveFiveMaturityScoreStatus.PASSING,
    score: int = 10,
    max_score: int = 10,
    limitations: tuple[str, ...] = (),
    blocker_ids: tuple[str, ...] = (),
    claim_boundaries: tuple[WaveFiveClaimBoundary, ...] = (
        WAVE_FIVE_REQUIRED_CLAIM_BOUNDARIES
    ),
) -> WaveFiveMaturityScoreSection:
    return WaveFiveMaturityScoreSection(
        section_id=section_id,
        area=area,
        status=status,
        score=score,
        max_score=max_score,
        artifact_ids=(f"artifact-{section_id}",),
        evidence_ids=(f"evidence-{section_id}",),
        summary="Score area is evidence-bound and reviewable.",
        limitations=limitations,
        blocker_ids=blocker_ids,
        claim_boundaries=claim_boundaries,
    )


def score_check(
    check_id: str,
    check_kind: WaveFiveMaturityCheckKind,
    *,
    result: WaveFiveMaturityCheckResult = WaveFiveMaturityCheckResult.PASSED,
    blocking: bool = True,
) -> WaveFiveMaturityScorecardCheck:
    return WaveFiveMaturityScorecardCheck(
        check_id=check_id,
        check_kind=check_kind,
        result=result,
        description="Scorecard check preserves Wave 5 maturity boundaries.",
        evidence_ids=(f"evidence-{check_id}",),
        blocking=blocking,
    )


def required_sections() -> tuple[WaveFiveMaturityScoreSection, ...]:
    return tuple(
        score_section(
            f"score-{area.value}",
            area=area,
            status=WaveFiveMaturityScoreStatus.PASSING_WITH_LIMITS,
            score=9,
            max_score=10,
            limitations=("Reviewable maturity evidence only; not Wave 6 proof.",),
        )
        for area in REQUIRED_SCORE_AREAS
    )


def required_checks() -> tuple[WaveFiveMaturityScorecardCheck, ...]:
    return tuple(
        score_check(f"check-{check_kind.value}", check_kind)
        for check_kind in REQUIRED_SCORECARD_CHECKS
    )


def scorecard(
    *,
    source_system: WaveFiveSourceSystem = WaveFiveSourceSystem.IX_COGNITION_KERNEL,
    review_state: WaveFiveMaturityReviewState = (
        WaveFiveMaturityReviewState.READY_FOR_EXTERNAL_SCORECARD_REVIEW
    ),
    sections: tuple[WaveFiveMaturityScoreSection, ...] | None = None,
    checks: tuple[WaveFiveMaturityScorecardCheck, ...] | None = None,
    reviewer_ids: tuple[str, ...] = (),
    minimum_average_score: float = 0.9,
    attempted_wave_six_promotion: bool = False,
    claims_agi: bool = False,
    grants_execution_authority: bool = False,
    claims_production_ready: bool = False,
    claims_certified: bool = False,
    claim_boundaries: tuple[WaveFiveClaimBoundary, ...] = (
        WAVE_FIVE_REQUIRED_CLAIM_BOUNDARIES
    ),
) -> WaveFiveMaturityScorecard:
    resolved_sections = required_sections() if sections is None else sections
    resolved_checks = required_checks() if checks is None else checks
    return WaveFiveMaturityScorecard(
        scorecard_id="wave5-maturity-scorecard-001",
        title="Wave 5 maturity scorecard for external review.",
        source_system=source_system,
        review_state=review_state,
        sections=resolved_sections,
        checks=resolved_checks,
        dossier_artifact_id="wave5-evidence-dossier-001",
        readiness_gate_artifact_id="wave5-wave6-readiness-gate-001",
        protocol_ids=("wave5-external-protocol-001",),
        reviewer_ids=reviewer_ids,
        minimum_average_score=minimum_average_score,
        attempted_wave_six_promotion=attempted_wave_six_promotion,
        claims_agi=claims_agi,
        grants_execution_authority=grants_execution_authority,
        claims_production_ready=claims_production_ready,
        claims_certified=claims_certified,
        claim_boundaries=claim_boundaries,
        notes=("Scorecard readiness is not Wave 6 promotion.",),
    )


def test_required_score_areas_are_locked() -> None:
    assert required_score_areas() == REQUIRED_SCORE_AREAS
    assert len(REQUIRED_SCORE_AREAS) == 15
    assert WaveFiveMaturityScoreArea.EVIDENCE_DOSSIER in REQUIRED_SCORE_AREAS
    assert WaveFiveMaturityScoreArea.WAVE_SIX_READINESS_GATE in REQUIRED_SCORE_AREAS


def test_required_scorecard_checks_are_locked() -> None:
    assert required_scorecard_checks() == REQUIRED_SCORECARD_CHECKS
    assert len(REQUIRED_SCORECARD_CHECKS) == 10
    assert WaveFiveMaturityCheckKind.NO_WAVE_SIX_PROMOTION in (
        REQUIRED_SCORECARD_CHECKS
    )
    assert WaveFiveMaturityCheckKind.EXTERNAL_REVIEW_PATH_VISIBLE in (
        REQUIRED_SCORECARD_CHECKS
    )


def test_safe_and_blocking_score_statuses_are_locked() -> None:
    assert safe_score_statuses() == SAFE_SCORE_STATUSES
    assert blocking_score_statuses() == BLOCKING_SCORE_STATUSES
    assert WaveFiveMaturityScoreStatus.PASSING in SAFE_SCORE_STATUSES
    assert WaveFiveMaturityScoreStatus.DISPUTED in BLOCKING_SCORE_STATUSES


def test_external_scorecard_review_sources_are_locked() -> None:
    assert external_scorecard_review_source_systems() == (
        EXTERNAL_SCORECARD_REVIEW_SOURCE_SYSTEMS
    )
    assert WaveFiveSourceSystem.INDEPENDENT_REVIEWER in (
        EXTERNAL_SCORECARD_REVIEW_SOURCE_SYSTEMS
    )
    assert WaveFiveSourceSystem.IX_COGNITION_KERNEL not in (
        EXTERNAL_SCORECARD_REVIEW_SOURCE_SYSTEMS
    )


def test_score_section_requires_valid_score_bounds() -> None:
    with pytest.raises(ValueError, match="positive max_score"):
        score_section(max_score=0)

    with pytest.raises(ValueError, match="between zero and max_score"):
        score_section(score=11, max_score=10)


def test_score_section_requires_artifacts_and_evidence() -> None:
    with pytest.raises(ValueError, match="artifact ids"):
        WaveFiveMaturityScoreSection(
            section_id="score-invalid",
            area=WaveFiveMaturityScoreArea.EXTERNAL_PROTOCOLS,
            status=WaveFiveMaturityScoreStatus.PASSING,
            score=1,
            max_score=1,
            artifact_ids=(),
            evidence_ids=("evidence",),
            summary="Invalid section.",
        )

    with pytest.raises(ValueError, match="evidence ids"):
        WaveFiveMaturityScoreSection(
            section_id="score-invalid",
            area=WaveFiveMaturityScoreArea.EXTERNAL_PROTOCOLS,
            status=WaveFiveMaturityScoreStatus.PASSING,
            score=1,
            max_score=1,
            artifact_ids=("artifact",),
            evidence_ids=(),
            summary="Invalid section.",
        )


def test_limited_score_section_requires_limitations() -> None:
    with pytest.raises(ValueError, match="require limits"):
        score_section(status=WaveFiveMaturityScoreStatus.PASSING_WITH_LIMITS)


def test_blocking_score_section_requires_blockers() -> None:
    with pytest.raises(ValueError, match="require blockers"):
        score_section(status=WaveFiveMaturityScoreStatus.DISPUTED)


def test_score_section_rejects_missing_claim_boundary() -> None:
    with pytest.raises(ValueError, match="no-self-validation"):
        score_section(
            claim_boundaries=tuple(
                boundary
                for boundary in WAVE_FIVE_REQUIRED_CLAIM_BOUNDARIES
                if boundary is not WaveFiveClaimBoundary.NO_SELF_VALIDATION
            )
        )


def test_score_section_reports_normalized_score_and_blocking_state() -> None:
    passing = score_section(score=8, max_score=10)
    blocking = score_section(
        status=WaveFiveMaturityScoreStatus.BLOCKED,
        blocker_ids=("blocker-001",),
    )

    assert passing.normalized_score == 0.8
    assert passing.reviewable_with_boundaries is True
    assert blocking.blocks_scorecard_readiness is True


def test_scorecard_check_requires_evidence() -> None:
    with pytest.raises(ValueError, match="evidence ids"):
        WaveFiveMaturityScorecardCheck(
            check_id="check-invalid",
            check_kind=WaveFiveMaturityCheckKind.NO_WAVE_SIX_PROMOTION,
            result=WaveFiveMaturityCheckResult.PASSED,
            description="Invalid check without evidence.",
            evidence_ids=(),
        )


def test_failed_scorecard_check_blocks_readiness() -> None:
    item = score_check(
        "check-failed",
        WaveFiveMaturityCheckKind.NO_AGI_OR_CERTIFICATION_CLAIM,
        result=WaveFiveMaturityCheckResult.FAILED,
    )

    assert item.passed_with_boundaries is False
    assert item.blocks_scorecard_readiness is True


def test_non_blocking_scorecard_check_does_not_block_readiness() -> None:
    item = score_check(
        "check-warning",
        WaveFiveMaturityCheckKind.EXTERNAL_REVIEW_PATH_VISIBLE,
        result=WaveFiveMaturityCheckResult.NEEDS_MORE_EVIDENCE,
        blocking=False,
    )

    assert item.blocks_scorecard_readiness is False


def test_scorecard_rejects_bad_minimum_average_score() -> None:
    with pytest.raises(ValueError, match="between zero and one"):
        scorecard(minimum_average_score=1.1)


def test_scorecard_rejects_forbidden_claim_flags() -> None:
    with pytest.raises(ValueError, match="cannot promote to Wave 6"):
        scorecard(attempted_wave_six_promotion=True)

    with pytest.raises(ValueError, match="cannot claim AGI"):
        scorecard(claims_agi=True)

    with pytest.raises(ValueError, match="cannot grant execution authority"):
        scorecard(grants_execution_authority=True)


def test_scorecard_rejects_production_and_certification_claims() -> None:
    with pytest.raises(ValueError, match="production readiness"):
        scorecard(claims_production_ready=True)

    with pytest.raises(ValueError, match="certification"):
        scorecard(claims_certified=True)


def test_scorecard_rejects_missing_claim_boundary() -> None:
    with pytest.raises(ValueError, match="no-self-validation"):
        scorecard(
            claim_boundaries=tuple(
                boundary
                for boundary in WAVE_FIVE_REQUIRED_CLAIM_BOUNDARIES
                if boundary is not WaveFiveClaimBoundary.NO_SELF_VALIDATION
            )
        )


def test_scorecard_reports_missing_area_and_check_coverage() -> None:
    item = scorecard(
        sections=(score_section(),),
        checks=(
            score_check(
                "check-all-required-areas-scored",
                WaveFiveMaturityCheckKind.ALL_REQUIRED_AREAS_SCORED,
            ),
        ),
    )

    assert item.has_required_area_coverage is False
    assert WaveFiveMaturityScoreArea.EVIDENCE_DOSSIER in item.missing_required_areas
    assert item.has_required_check_coverage is False
    assert WaveFiveMaturityCheckKind.NO_WAVE_SIX_PROMOTION in (
        item.missing_required_check_kinds
    )
    assert item.ready_for_external_scorecard_review is False


def test_scorecard_blocks_when_section_status_is_blocking() -> None:
    sections = tuple(
        score_section(
            f"score-{area.value}",
            area=area,
            status=(
                WaveFiveMaturityScoreStatus.BLOCKED
                if area is WaveFiveMaturityScoreArea.REPEATABILITY
                else WaveFiveMaturityScoreStatus.PASSING
            ),
            blocker_ids=(
                ("blocker-repeatability",)
                if area is WaveFiveMaturityScoreArea.REPEATABILITY
                else ()
            ),
        )
        for area in REQUIRED_SCORE_AREAS
    )
    item = scorecard(sections=sections)

    assert item.blocking_section_ids == ("score-repeatability",)
    assert item.blocks_scorecard_readiness is True


def test_scorecard_blocks_when_check_fails() -> None:
    checks = tuple(
        score_check(
            f"check-{check_kind.value}",
            check_kind,
            result=(
                WaveFiveMaturityCheckResult.FAILED
                if check_kind is WaveFiveMaturityCheckKind.NO_WAVE_SIX_PROMOTION
                else WaveFiveMaturityCheckResult.PASSED
            ),
        )
        for check_kind in REQUIRED_SCORECARD_CHECKS
    )
    item = scorecard(checks=checks)

    assert item.blocking_check_ids == ("check-no-wave-six-promotion",)
    assert item.blocks_scorecard_readiness is True


def test_scorecard_blocks_when_average_score_is_below_threshold() -> None:
    sections = tuple(
        score_section(
            f"score-{area.value}",
            area=area,
            score=8,
            max_score=10,
        )
        for area in REQUIRED_SCORE_AREAS
    )
    item = scorecard(sections=sections, minimum_average_score=0.9)

    assert item.average_score == 0.8
    assert item.meets_minimum_average_score is False
    assert item.blocks_scorecard_readiness is True


def test_scorecard_is_ready_for_external_review() -> None:
    item = scorecard()

    assert item.has_required_area_coverage is True
    assert item.has_required_check_coverage is True
    assert item.blocking_section_ids == ()
    assert item.blocking_check_ids == ()
    assert item.total_score == 135
    assert item.total_max_score == 150
    assert item.average_score == 0.9
    assert item.meets_minimum_average_score is True
    assert item.ready_for_external_scorecard_review is True


def test_ready_scorecard_exports_reviewable_traceability_artifact() -> None:
    artifact = scorecard().to_artifact_ref()

    assert artifact.kind is WaveFiveArtifactKind.ECOSYSTEM_TRACEABILITY_MAP
    assert artifact.capability_area is WaveFiveCapabilityArea.ECOSYSTEM_TRACEABILITY
    assert artifact.source_system is WaveFiveSourceSystem.IX_COGNITION_KERNEL
    assert artifact.decision is WaveFiveArtifactDecision.READY_FOR_INDEPENDENT_REVIEW
    assert artifact.authority_state is WaveFiveAuthorityState.HUMAN_REVIEW_REQUIRED
    assert artifact.validation_status is (
        WaveFiveValidationStatus.UNDER_INDEPENDENT_REVIEW
    )


def test_blocked_scorecard_exports_blocked_artifact() -> None:
    sections = tuple(
        score_section(
            f"score-{area.value}",
            area=area,
            score=8,
            max_score=10,
        )
        for area in REQUIRED_SCORE_AREAS
    )
    artifact = scorecard(sections=sections).to_artifact_ref()

    assert artifact.decision is WaveFiveArtifactDecision.BLOCKED
    assert artifact.authority_state is WaveFiveAuthorityState.BLOCKED
    assert artifact.validation_status is WaveFiveValidationStatus.REJECTED


def test_externally_reviewed_scorecard_requires_external_source() -> None:
    with pytest.raises(ValueError, match="external source"):
        scorecard(
            review_state=(
                WaveFiveMaturityReviewState.EXTERNALLY_REVIEWED_WITH_BOUNDARIES
            ),
            reviewer_ids=("reviewer-001",),
        )


def test_externally_reviewed_scorecard_requires_reviewer_ids() -> None:
    with pytest.raises(ValueError, match="reviewer ids"):
        scorecard(
            source_system=WaveFiveSourceSystem.INDEPENDENT_REVIEWER,
            review_state=(
                WaveFiveMaturityReviewState.EXTERNALLY_REVIEWED_WITH_BOUNDARIES
            ),
        )


def test_externally_reviewed_scorecard_exports_bounded_external_artifact() -> None:
    item = scorecard(
        source_system=WaveFiveSourceSystem.INDEPENDENT_REVIEWER,
        review_state=WaveFiveMaturityReviewState.EXTERNALLY_REVIEWED_WITH_BOUNDARIES,
        reviewer_ids=("reviewer-001",),
    )
    artifact = item.to_artifact_ref()

    assert item.externally_reviewed_with_boundaries is True
    assert artifact.decision is WaveFiveArtifactDecision.EXTERNALLY_REVIEWED
    assert artifact.validation_status is (
        WaveFiveValidationStatus.ACCEPTED_WITH_BOUNDARIES
    )
    assert artifact.externally_validated_with_boundaries is True


def test_scorecard_collects_unique_evidence_ids() -> None:
    item = scorecard()

    assert item.all_evidence_ids[0] == "evidence-score-adversarial-safety"
    assert "evidence-score-evidence-dossier" in item.all_evidence_ids
    assert "evidence-check-no-wave-six-promotion" in item.all_evidence_ids
    assert len(item.all_evidence_ids) == 25


def test_scorecard_fingerprint_is_deterministic() -> None:
    item = scorecard()

    assert item.fingerprint() == item.fingerprint()
    assert len(item.fingerprint()) == 64
