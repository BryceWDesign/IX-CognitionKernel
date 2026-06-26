import pytest

from ix_cognition_kernel.wave8_integrated_trial import build_integrated_wave8_trial
from ix_cognition_kernel.wave8_negative_controls import (
    NegativeControlKind,
    NegativeControlSuiteDecision,
    build_negative_control_record,
    build_negative_control_report,
    default_wave8_negative_control_records,
)
from ix_cognition_kernel.wave8_readiness_scorecard import (
    ReadinessDimensionDecision,
    ReadinessDimensionKind,
    ReadinessDimensionRecord,
    Wave8ReadinessDecision,
    Wave8ReadinessScorecard,
    build_wave8_readiness_scorecard,
)


def _integrated_trial():
    return build_integrated_wave8_trial(
        trial_id="scorecard-integrated-trial",
        human_authority_evidence_ids=("human-authority-evidence-1",),
    )


def _negative_control_report():
    return build_negative_control_report(
        report_id="negative-control-report-1",
        purpose="Validate Wave 8 fail-closed behavior without certification.",
        records=default_wave8_negative_control_records(),
    )


def test_wave8_readiness_scorecard_passes_ready_integrated_trial_and_controls() -> None:
    scorecard = build_wave8_readiness_scorecard(
        scorecard_id="scorecard-1",
        purpose="Score bounded Wave 8 readiness for review handoff.",
        claim_boundary="Readiness score only; no certification.",
        integrated_trial=_integrated_trial(),
        negative_control_report=_negative_control_report(),
    )

    assert scorecard.ready
    assert scorecard.decision is Wave8ReadinessDecision.READY_FOR_REVIEW_HANDOFF
    assert scorecard.total_score == 1000
    assert scorecard.max_score == 1000
    assert scorecard.normalized_score == 1.0
    assert scorecard.blocked_dimension_count == 0
    assert scorecard.warning_dimension_count == 0
    assert scorecard.findings == ()
    assert scorecard.fingerprint() == scorecard.fingerprint()
    assert len(scorecard.fingerprint()) == 64


def test_wave8_readiness_scorecard_blocks_failed_open_negative_control() -> None:
    records = list(default_wave8_negative_control_records())
    records[0] = build_negative_control_record(
        control_id="negative-control-overclaim-failed-open",
        kind=NegativeControlKind.OVERCLAIM_BLOCK,
        expected_block_reason="Overclaiming must be blocked.",
        observed_decision="overclaim-allowed",
        blocked=False,
        evidence_ids=("negative-control-overclaim-evidence",),
        findings=("overclaim-failed-open",),
    )
    negative_report = build_negative_control_report(
        report_id="negative-control-report-failed-open",
        purpose="Validate Wave 8 fail-closed behavior without certification.",
        records=tuple(records),
    )
    scorecard = build_wave8_readiness_scorecard(
        scorecard_id="scorecard-failed-open",
        purpose="Score bounded Wave 8 readiness for review handoff.",
        claim_boundary="Readiness score only; no certification.",
        integrated_trial=_integrated_trial(),
        negative_control_report=negative_report,
    )

    assert negative_report.decision is NegativeControlSuiteDecision.FAILED_OPEN
    assert not scorecard.ready
    assert scorecard.decision is Wave8ReadinessDecision.BLOCKED
    assert scorecard.blocked_dimension_count == 1
    assert "negative-controls-failed-open" in scorecard.findings


def test_readiness_dimension_rejects_blocked_positive_score() -> None:
    with pytest.raises(ValueError, match="must have a zero score"):
        ReadinessDimensionRecord(
            dimension_id="dimension-bad",
            kind=ReadinessDimensionKind.NEGATIVE_CONTROLS,
            decision=ReadinessDimensionDecision.BLOCK,
            score=10,
            summary="Blocked dimension cannot preserve score.",
            evidence_ids=("dimension-evidence-1",),
            findings=("blocked-dimension",),
        )


def test_readiness_scorecard_rejects_missing_required_dimensions() -> None:
    integrated = _integrated_trial()
    negative_report = _negative_control_report()
    dimension = ReadinessDimensionRecord(
        dimension_id="dimension-only",
        kind=ReadinessDimensionKind.CLAIM_BOUNDARY,
        decision=ReadinessDimensionDecision.PASS,
        score=100,
        summary="Claim boundary remains review-only and non-certifying.",
        evidence_ids=("dimension-evidence-1",),
    )

    with pytest.raises(ValueError, match="missing dimensions"):
        Wave8ReadinessScorecard(
            scorecard_id="scorecard-missing-dimensions",
            purpose="Score bounded Wave 8 readiness for review handoff.",
            claim_boundary="Readiness score only; no certification.",
            integrated_trial_fingerprint=integrated.fingerprint(),
            negative_control_report_fingerprint=negative_report.fingerprint(),
            dimensions=(dimension,),
            decision=Wave8ReadinessDecision.BLOCKED,
            findings=("missing-dimensions",),
        )


def test_readiness_scorecard_rejects_overclaiming_purpose_or_boundary() -> None:
    with pytest.raises(ValueError, match="blocked overclaiming"):
        build_wave8_readiness_scorecard(
            scorecard_id="scorecard-overclaim-purpose",
            purpose="This proves AGI.",
            claim_boundary="Readiness score only; no certification.",
            integrated_trial=_integrated_trial(),
            negative_control_report=_negative_control_report(),
        )

    with pytest.raises(ValueError, match="blocked overclaiming"):
        build_wave8_readiness_scorecard(
            scorecard_id="scorecard-overclaim-boundary",
            purpose="Score bounded Wave 8 readiness for review handoff.",
            claim_boundary="This is artificial general intelligence certification.",
            integrated_trial=_integrated_trial(),
            negative_control_report=_negative_control_report(),
        )
