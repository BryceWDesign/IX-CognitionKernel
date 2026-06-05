import pytest

from ix_cognition_kernel.wave5_contracts import (
    WaveFiveArtifactDecision,
    WaveFiveAuthorityState,
    WaveFiveSourceSystem,
    WaveFiveValidationStatus,
)
from ix_cognition_kernel.wave5_maturity_scorecard import (
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


def _score_sections(
    status: WaveFiveMaturityScoreStatus = WaveFiveMaturityScoreStatus.PASSING,
    score: int = 10,
    max_score: int = 10,
) -> tuple[WaveFiveMaturityScoreSection, ...]:
    return tuple(
        WaveFiveMaturityScoreSection(
            section_id=f"section-{area.value}",
            area=area,
            status=status,
            score=score,
            max_score=max_score,
            artifact_ids=(f"artifact-{area.value}",),
            evidence_ids=(f"evidence-{area.value}",),
            summary=f"Maturity score for {area.value}",
            limitations=(
                (f"limited-{area.value}",)
                if status is WaveFiveMaturityScoreStatus.PASSING_WITH_LIMITS
                else ()
            ),
            blocker_ids=(
                (f"blocker-{area.value}",)
                if status in blocking_score_statuses()
                else ()
            ),
        )
        for area in required_score_areas()
    )


def _scorecard_checks(
    result: WaveFiveMaturityCheckResult = WaveFiveMaturityCheckResult.PASSED,
) -> tuple[WaveFiveMaturityScorecardCheck, ...]:
    return tuple(
        WaveFiveMaturityScorecardCheck(
            check_id=f"check-{check_kind.value}",
            check_kind=check_kind,
            result=result,
            description=f"Scorecard check for {check_kind.value}",
            evidence_ids=(f"check-evidence-{check_kind.value}",),
        )
        for check_kind in required_scorecard_checks()
    )


def _scorecard(
    *,
    review_state: WaveFiveMaturityReviewState = (
        WaveFiveMaturityReviewState.READY_FOR_EXTERNAL_SCORECARD_REVIEW
    ),
    source_system: WaveFiveSourceSystem = WaveFiveSourceSystem.IX_COGNITION_KERNEL,
    sections: tuple[WaveFiveMaturityScoreSection, ...] | None = None,
    checks: tuple[WaveFiveMaturityScorecardCheck, ...] | None = None,
    reviewer_ids: tuple[str, ...] = (),
) -> WaveFiveMaturityScorecard:
    return WaveFiveMaturityScorecard(
        scorecard_id="scorecard-1",
        title="Wave 5 maturity scorecard",
        source_system=source_system,
        review_state=review_state,
        sections=sections or _score_sections(),
        checks=checks or _scorecard_checks(),
        dossier_artifact_id="dossier-1",
        readiness_gate_artifact_id="readiness-gate-1",
        protocol_ids=("protocol-1",),
        reviewer_ids=reviewer_ids,
    )


def test_required_scorecard_sets_are_locked() -> None:
    assert len(required_score_areas()) >= 10
    assert len(required_scorecard_checks()) >= 8
    assert WaveFiveMaturityScoreStatus.PASSING in safe_score_statuses()
    assert WaveFiveMaturityScoreStatus.MISSING in blocking_score_statuses()
    assert (
        WaveFiveSourceSystem.INDEPENDENT_REVIEWER
        in external_scorecard_review_source_systems()
    )


def test_scorecard_ready_for_external_review_when_complete() -> None:
    scorecard = _scorecard()

    assert scorecard.has_required_area_coverage
    assert scorecard.has_required_check_coverage
    assert scorecard.meets_minimum_average_score
    assert scorecard.ready_for_external_scorecard_review
    assert not scorecard.blocks_scorecard_readiness
    assert scorecard.average_score == 1.0
    assert scorecard.blocking_section_ids == ()
    assert scorecard.blocking_check_ids == ()

    artifact_ref = scorecard.to_artifact_ref()
    assert artifact_ref.decision is WaveFiveArtifactDecision.READY_FOR_INDEPENDENT_REVIEW
    assert artifact_ref.authority_state is WaveFiveAuthorityState.HUMAN_REVIEW_REQUIRED
    assert artifact_ref.validation_status is WaveFiveValidationStatus.UNDER_INDEPENDENT_REVIEW
    assert artifact_ref.evidence_ids == scorecard.all_evidence_ids


def test_scorecard_reports_missing_required_area() -> None:
    sections = tuple(
        section
        for section in _score_sections()
        if section.area is not WaveFiveMaturityScoreArea.EXTERNAL_PROTOCOLS
    )

    scorecard = _scorecard(sections=sections)

    assert scorecard.missing_required_areas == (
        WaveFiveMaturityScoreArea.EXTERNAL_PROTOCOLS,
    )
    assert scorecard.blocks_scorecard_readiness
    assert not scorecard.ready_for_external_scorecard_review


def test_scorecard_blocks_low_average_score() -> None:
    scorecard = _scorecard(sections=_score_sections(score=8, max_score=10))

    assert scorecard.average_score == 0.8
    assert not scorecard.meets_minimum_average_score
    assert scorecard.blocks_scorecard_readiness
    assert not scorecard.ready_for_external_scorecard_review


def test_scorecard_blocks_failed_check() -> None:
    scorecard = _scorecard(
        checks=_scorecard_checks(result=WaveFiveMaturityCheckResult.FAILED)
    )

    assert scorecard.blocking_check_ids
    assert scorecard.blocks_scorecard_readiness
    assert not scorecard.ready_for_external_scorecard_review


def test_scorecard_section_requires_blocker_for_blocking_status() -> None:
    with pytest.raises(ValueError, match="require blockers"):
        WaveFiveMaturityScoreSection(
            section_id="section-blocked",
            area=WaveFiveMaturityScoreArea.EXTERNAL_PROTOCOLS,
            status=WaveFiveMaturityScoreStatus.BLOCKED,
            score=0,
            max_score=10,
            artifact_ids=("artifact-1",),
            evidence_ids=("evidence-1",),
            summary="Blocked section without blocker ids.",
        )


def test_scorecard_rejects_forbidden_claims() -> None:
    with pytest.raises(ValueError, match="cannot claim AGI"):
        WaveFiveMaturityScorecard(
            scorecard_id="invalid-scorecard",
            title="Invalid scorecard",
            source_system=WaveFiveSourceSystem.IX_COGNITION_KERNEL,
            review_state=WaveFiveMaturityReviewState.INTERNAL_SCORECARD_READY,
            sections=_score_sections(),
            checks=_scorecard_checks(),
            dossier_artifact_id="dossier-1",
            readiness_gate_artifact_id="readiness-gate-1",
            protocol_ids=("protocol-1",),
            claims_agi=True,
        )


def test_externally_reviewed_scorecard_requires_external_source() -> None:
    with pytest.raises(ValueError, match="external source"):
        _scorecard(
            review_state=WaveFiveMaturityReviewState.EXTERNALLY_REVIEWED_WITH_BOUNDARIES,
            source_system=WaveFiveSourceSystem.IX_COGNITION_KERNEL,
            reviewer_ids=("reviewer-1",),
        )


def test_externally_reviewed_scorecard_exports_reviewed_artifact() -> None:
    scorecard = _scorecard(
        review_state=WaveFiveMaturityReviewState.EXTERNALLY_REVIEWED_WITH_BOUNDARIES,
        source_system=WaveFiveSourceSystem.EXTERNAL_REVIEW,
        reviewer_ids=("reviewer-1",),
    )

    assert scorecard.externally_reviewed_with_boundaries
    artifact_ref = scorecard.to_artifact_ref()
    assert artifact_ref.decision is WaveFiveArtifactDecision.EXTERNALLY_REVIEWED
    assert artifact_ref.validation_status is WaveFiveValidationStatus.ACCEPTED_WITH_BOUNDARIES
