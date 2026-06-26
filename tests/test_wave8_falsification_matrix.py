import pytest

from ix_cognition_kernel.wave8_evidence_index import build_wave8_evidence_index
from ix_cognition_kernel.wave8_falsification_matrix import (
    FalsificationCheckDecision,
    FalsificationCheckKind,
    FalsificationCheckRecord,
    FalsificationMatrixDecision,
    Wave8FalsificationMatrix,
    build_wave8_falsification_matrix,
)
from ix_cognition_kernel.wave8_integrated_trial import build_integrated_wave8_trial
from ix_cognition_kernel.wave8_negative_controls import (
    NegativeControlKind,
    build_negative_control_record,
    build_negative_control_report,
    default_wave8_negative_control_records,
)
from ix_cognition_kernel.wave8_readiness_scorecard import (
    build_wave8_readiness_scorecard,
)


def _evidence_chain():
    integrated = build_integrated_wave8_trial(
        trial_id="falsification-integrated-trial",
        human_authority_evidence_ids=("human-authority-evidence-1",),
    )
    negative_report = build_negative_control_report(
        report_id="negative-control-report-1",
        purpose="Validate Wave 8 fail-closed behavior without certification.",
        records=default_wave8_negative_control_records(),
    )
    scorecard = build_wave8_readiness_scorecard(
        scorecard_id="scorecard-1",
        purpose="Score bounded Wave 8 readiness for review handoff.",
        claim_boundary="Readiness score only; no certification.",
        integrated_trial=integrated,
        negative_control_report=negative_report,
    )
    index = build_wave8_evidence_index(
        index_id="evidence-index-1",
        purpose="Index bounded Wave 8 evidence for review query.",
        claim_boundary="Evidence index only; no certification.",
        integrated_trial=integrated,
        negative_control_report=negative_report,
        readiness_scorecard=scorecard,
    )
    return index, scorecard, negative_report


def test_wave8_falsification_matrix_survives_ready_evidence_chain() -> None:
    index, scorecard, negative_report = _evidence_chain()
    matrix = build_wave8_falsification_matrix(
        matrix_id="falsification-matrix-1",
        purpose="Bind bounded falsification checks for Wave 8 review.",
        claim_boundary="Falsification matrix only; no certification.",
        evidence_index=index,
        readiness_scorecard=scorecard,
        negative_control_report=negative_report,
    )

    assert matrix.survived
    assert matrix.decision is FalsificationMatrixDecision.SURVIVED_BOUNDED_FALSIFICATION
    assert matrix.failed_open_count == 0
    assert matrix.needs_evidence_count == 0
    assert matrix.findings == ()
    assert len(matrix.checks) == 10
    assert matrix.fingerprint() == matrix.fingerprint()
    assert len(matrix.fingerprint()) == 64


def test_wave8_falsification_matrix_detects_failed_open_negative_control() -> None:
    index, scorecard, _negative_report = _evidence_chain()
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
    failed_report = build_negative_control_report(
        report_id="negative-control-report-failed-open",
        purpose="Validate Wave 8 fail-closed behavior without certification.",
        records=tuple(records),
    )

    matrix = build_wave8_falsification_matrix(
        matrix_id="falsification-matrix-failed-open",
        purpose="Bind bounded falsification checks for Wave 8 review.",
        claim_boundary="Falsification matrix only; no certification.",
        evidence_index=index,
        readiness_scorecard=scorecard,
        negative_control_report=failed_report,
    )

    assert not matrix.survived
    assert matrix.decision is FalsificationMatrixDecision.FAILED_OPEN
    assert matrix.failed_open_count == 1
    assert "negative-control-report-failed-open" in matrix.findings


def test_falsification_check_requires_findings_when_not_survived() -> None:
    with pytest.raises(ValueError, match="require findings"):
        FalsificationCheckRecord(
            check_id="check-bad",
            kind=FalsificationCheckKind.CLAIM_BOUNDARY,
            hypothesis_under_test="Claim boundary remains review-only.",
            falsify_if="Claim boundary is bypassed.",
            observed_outcome="Evidence is incomplete.",
            decision=FalsificationCheckDecision.NEEDS_EVIDENCE,
            evidence_ids=("evidence-1",),
            linked_entry_ids=("entry-1",),
        )


def test_falsification_matrix_rejects_missing_required_check_kinds() -> None:
    index, scorecard, negative_report = _evidence_chain()
    check = FalsificationCheckRecord(
        check_id="check-claim-boundary",
        kind=FalsificationCheckKind.CLAIM_BOUNDARY,
        hypothesis_under_test="Claim boundary remains review-only.",
        falsify_if="Claim boundary is bypassed.",
        observed_outcome="Claim boundary is attached to indexed evidence.",
        decision=FalsificationCheckDecision.SURVIVED,
        evidence_ids=(index.fingerprint(),),
        linked_entry_ids=("entry-readiness-scorecard",),
    )

    with pytest.raises(ValueError, match="missing checks"):
        Wave8FalsificationMatrix(
            matrix_id="falsification-matrix-missing",
            purpose="Bind bounded falsification checks for Wave 8 review.",
            claim_boundary="Falsification matrix only; no certification.",
            evidence_index_fingerprint=index.fingerprint(),
            readiness_scorecard_fingerprint=scorecard.fingerprint(),
            negative_control_report_fingerprint=negative_report.fingerprint(),
            checks=(check,),
            decision=FalsificationMatrixDecision.NEEDS_EVIDENCE,
            findings=("missing-required-checks",),
        )


def test_falsification_matrix_rejects_duplicate_check_ids() -> None:
    index, scorecard, negative_report = _evidence_chain()
    matrix = build_wave8_falsification_matrix(
        matrix_id="falsification-matrix-1",
        purpose="Bind bounded falsification checks for Wave 8 review.",
        claim_boundary="Falsification matrix only; no certification.",
        evidence_index=index,
        readiness_scorecard=scorecard,
        negative_control_report=negative_report,
    )

    with pytest.raises(ValueError, match="Duplicate falsification check id"):
        Wave8FalsificationMatrix(
            matrix_id="falsification-matrix-duplicate",
            purpose="Bind bounded falsification checks for Wave 8 review.",
            claim_boundary="Falsification matrix only; no certification.",
            evidence_index_fingerprint=index.fingerprint(),
            readiness_scorecard_fingerprint=scorecard.fingerprint(),
            negative_control_report_fingerprint=negative_report.fingerprint(),
            checks=(matrix.checks[0], matrix.checks[0], *matrix.checks[1:]),
            decision=FalsificationMatrixDecision.NEEDS_EVIDENCE,
            findings=("duplicate-check",),
        )


def test_falsification_matrix_rejects_overclaiming_boundary() -> None:
    index, scorecard, negative_report = _evidence_chain()

    with pytest.raises(ValueError, match="blocked overclaiming"):
        build_wave8_falsification_matrix(
            matrix_id="falsification-matrix-overclaim",
            purpose="Bind bounded falsification checks for Wave 8 review.",
            claim_boundary="This certifies artificial general intelligence.",
            evidence_index=index,
            readiness_scorecard=scorecard,
            negative_control_report=negative_report,
        )
