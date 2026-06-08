import pytest

from ix_cognition_kernel.wave6_review_scorecard import (
    WAVE_SIX_REQUIRED_REVIEW_CRITERIA,
    WaveSixCriterionStatus,
    WaveSixReviewCriterion,
    WaveSixReviewScorecard,
    WaveSixReviewScorecardItem,
    WaveSixReviewScorecardStatus,
    build_wave_six_review_scorecard,
    required_wave_six_review_criteria,
)


def _boundary_statement() -> str:
    return (
        "This Wave-6 measured system-level cognition package is ready for "
        "bounded review under human authority and independent review. It is not "
        "an AGI claim."
    )


def _item(
    criterion: WaveSixReviewCriterion,
    *,
    item_id: str | None = None,
    status: WaveSixCriterionStatus = WaveSixCriterionStatus.SATISFIED,
    requires_follow_up: bool = False,
    blocks_claim: bool = False,
) -> WaveSixReviewScorecardItem:
    return WaveSixReviewScorecardItem(
        item_id=item_id or f"item-{criterion.value}",
        criterion=criterion,
        status=status,
        summary=f"Review scorecard item for {criterion.value}.",
        artifact_fingerprint=f"fingerprint-{criterion.value}",
        evidence_ids=(f"evidence-{criterion.value}",),
        reviewer_question=f"Is {criterion.value} satisfied for bounded review?",
        requires_follow_up=requires_follow_up,
        blocks_claim=blocks_claim,
    )


def _complete_items() -> tuple[WaveSixReviewScorecardItem, ...]:
    return tuple(_item(criterion) for criterion in WAVE_SIX_REQUIRED_REVIEW_CRITERIA)


def _scorecard(
    *,
    items: tuple[WaveSixReviewScorecardItem, ...] | None = None,
    claims_agi: bool = False,
) -> WaveSixReviewScorecard:
    return WaveSixReviewScorecard(
        scorecard_id="scorecard-1",
        package_fingerprint="package-fingerprint-1",
        items=items or _complete_items(),
        generated_by_engine_id="wave6-review-scorecard-engine",
        claim_boundary_statement=_boundary_statement(),
        claims_agi=claims_agi,
        notes=("This scorecard is bounded review evidence, not AGI proof.",),
    )


def test_required_review_criteria_are_locked() -> None:
    assert required_wave_six_review_criteria() == (
        WaveSixReviewCriterion.CLEAN_MASTER_LOOP,
        WaveSixReviewCriterion.CONTRACT_COVERAGE,
        WaveSixReviewCriterion.DONOR_TRACEABILITY,
        WaveSixReviewCriterion.REALITY_CORRECTED_REASONING,
        WaveSixReviewCriterion.FUTURE_REASONING_CHANGE,
        WaveSixReviewCriterion.CROSS_DOMAIN_TRANSFER,
        WaveSixReviewCriterion.NOVELTY_AND_NEGATIVE_CONTROL,
        WaveSixReviewCriterion.FALSIFICATION_SURVIVAL,
        WaveSixReviewCriterion.HUMAN_REVIEW_AUTHORITY,
        WaveSixReviewCriterion.INDEPENDENT_REVIEW_READINESS,
        WaveSixReviewCriterion.CLAIM_BOUNDARY_DISCIPLINE,
    )


def test_scorecard_item_is_satisfied_and_fingerprinted() -> None:
    item = _item(WaveSixReviewCriterion.CLEAN_MASTER_LOOP)

    assert item.satisfied
    assert not item.needs_more_evidence
    assert not item.blocked
    assert item.fingerprint() == item.fingerprint()
    assert len(item.fingerprint()) == 64


def test_scorecard_item_enforces_status_semantics() -> None:
    with pytest.raises(ValueError, match="cannot require follow-up"):
        _item(
            WaveSixReviewCriterion.CONTRACT_COVERAGE,
            status=WaveSixCriterionStatus.SATISFIED,
            requires_follow_up=True,
        )

    with pytest.raises(ValueError, match="require follow-up"):
        _item(
            WaveSixReviewCriterion.DONOR_TRACEABILITY,
            status=WaveSixCriterionStatus.NEEDS_MORE_EVIDENCE,
        )

    with pytest.raises(ValueError, match="must block the claim"):
        _item(
            WaveSixReviewCriterion.FALSIFICATION_SURVIVAL,
            status=WaveSixCriterionStatus.BLOCKED,
        )


def test_scorecard_item_requires_evidence() -> None:
    with pytest.raises(ValueError, match="require evidence ids"):
        WaveSixReviewScorecardItem(
            item_id="item-no-evidence",
            criterion=WaveSixReviewCriterion.CLEAN_MASTER_LOOP,
            status=WaveSixCriterionStatus.SATISFIED,
            summary="Invalid item without evidence.",
            artifact_fingerprint="fingerprint",
            evidence_ids=(),
            reviewer_question="Can this be reviewed?",
        )


def test_review_scorecard_is_ready_when_all_criteria_are_satisfied() -> None:
    scorecard = build_wave_six_review_scorecard(
        scorecard_id="scorecard-ready",
        package_fingerprint="package-fingerprint-1",
        items=_complete_items(),
        generated_by_engine_id="wave6-review-scorecard-engine",
        claim_boundary_statement=_boundary_statement(),
        notes=("All criteria are satisfied for bounded external review.",),
    )

    assert scorecard.present_criteria == WAVE_SIX_REQUIRED_REVIEW_CRITERIA
    assert scorecard.missing_criteria == ()
    assert scorecard.follow_up_item_ids == ()
    assert scorecard.blocking_item_ids == ()
    assert scorecard.status is WaveSixReviewScorecardStatus.READY_FOR_EXTERNAL_REVIEW
    assert scorecard.ready_for_external_review
    assert not scorecard.overclaim_present
    assert scorecard.fingerprint() == scorecard.fingerprint()
    assert len(scorecard.fingerprint()) == 64


def test_review_scorecard_reports_missing_criteria() -> None:
    scorecard = _scorecard(items=_complete_items()[:-1])

    assert scorecard.missing_criteria == (
        WaveSixReviewCriterion.CLAIM_BOUNDARY_DISCIPLINE,
    )
    assert scorecard.status is WaveSixReviewScorecardStatus.NEEDS_MORE_EVIDENCE
    assert not scorecard.ready_for_external_review


def test_review_scorecard_tracks_follow_up_items() -> None:
    items = list(_complete_items())
    items[3] = _item(
        WaveSixReviewCriterion.REALITY_CORRECTED_REASONING,
        status=WaveSixCriterionStatus.NEEDS_MORE_EVIDENCE,
        requires_follow_up=True,
    )
    scorecard = _scorecard(items=tuple(items))

    assert scorecard.follow_up_item_ids == (
        "item-reality-corrected-reasoning",
    )
    assert scorecard.status is WaveSixReviewScorecardStatus.NEEDS_MORE_EVIDENCE
    assert not scorecard.ready_for_external_review


def test_review_scorecard_blocks_on_blocking_item_or_overclaim() -> None:
    items = list(_complete_items())
    items[7] = _item(
        WaveSixReviewCriterion.FALSIFICATION_SURVIVAL,
        status=WaveSixCriterionStatus.BLOCKED,
        blocks_claim=True,
    )
    blocked = _scorecard(items=tuple(items))

    assert blocked.blocking_item_ids == ("item-falsification-survival",)
    assert blocked.status is WaveSixReviewScorecardStatus.BLOCKED
    assert not blocked.ready_for_external_review

    overclaim = _scorecard(claims_agi=True)

    assert overclaim.overclaim_present
    assert overclaim.status is WaveSixReviewScorecardStatus.BLOCKED


def test_review_scorecard_lookup_and_duplicate_rejection() -> None:
    scorecard = _scorecard(items=(_item(WaveSixReviewCriterion.CLEAN_MASTER_LOOP),))

    item = scorecard.item_for_criterion(WaveSixReviewCriterion.CLEAN_MASTER_LOOP)

    assert item is not None
    assert item.item_id == "item-clean-master-loop"
    assert (
        scorecard.item_for_criterion(WaveSixReviewCriterion.CLAIM_BOUNDARY_DISCIPLINE)
        is None
    )

    duplicate = _item(WaveSixReviewCriterion.CLEAN_MASTER_LOOP)
    with pytest.raises(ValueError, match="Duplicate item_id"):
        _scorecard(items=(duplicate, duplicate))

    with pytest.raises(ValueError, match="Duplicate criterion"):
        _scorecard(
            items=(
                duplicate,
                _item(
                    WaveSixReviewCriterion.CLEAN_MASTER_LOOP,
                    item_id="different-item-id",
                ),
            )
        )


def test_review_scorecard_requires_non_empty_package_fingerprint() -> None:
    with pytest.raises(ValueError, match="package_fingerprint must not be empty"):
        WaveSixReviewScorecard(
            scorecard_id="scorecard-invalid",
            package_fingerprint=" ",
            items=_complete_items(),
            generated_by_engine_id="wave6-review-scorecard-engine",
            claim_boundary_statement=_boundary_statement(),
        )
