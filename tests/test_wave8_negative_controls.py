import pytest

from ix_cognition_kernel.wave8_negative_controls import (
    NegativeControlDecision,
    NegativeControlKind,
    NegativeControlSuiteDecision,
    build_negative_control_record,
    build_negative_control_report,
    default_wave8_negative_control_records,
)


def test_default_negative_controls_pass_as_blocked_as_designed() -> None:
    records = default_wave8_negative_control_records()
    report = build_negative_control_report(
        report_id="negative-control-report-1",
        purpose="Validate Wave 8 fail-closed behavior without certification.",
        records=records,
    )

    assert len(records) == 8
    assert all(record.passed for record in records)
    assert report.passed
    assert report.decision is NegativeControlSuiteDecision.PASSED
    assert report.findings == ()
    assert report.failed_open_count == 0
    assert report.fingerprint() == report.fingerprint()
    assert len(report.fingerprint()) == 64


def test_negative_control_record_reports_failed_open_control() -> None:
    record = build_negative_control_record(
        control_id="control-failed-open",
        kind=NegativeControlKind.LIVE_ACTUATION_BLOCK,
        expected_block_reason="Live actuation must be blocked.",
        observed_decision="live-actuation-allowed",
        blocked=False,
        evidence_ids=("control-evidence-1",),
        findings=("live-actuation-failed-open",),
    )

    assert record.decision is NegativeControlDecision.FAILED_OPEN
    assert not record.passed
    assert record.fingerprint() == record.fingerprint()


def test_negative_control_record_requires_findings_when_failed_open() -> None:
    with pytest.raises(ValueError, match="require findings"):
        build_negative_control_record(
            control_id="control-failed-open",
            kind=NegativeControlKind.LIVE_ACTUATION_BLOCK,
            expected_block_reason="Live actuation must be blocked.",
            observed_decision="live-actuation-allowed",
            blocked=False,
            evidence_ids=("control-evidence-1",),
        )


def test_negative_control_report_detects_failed_open_records() -> None:
    records = list(default_wave8_negative_control_records())
    records[0] = build_negative_control_record(
        control_id="control-overclaim-failed-open",
        kind=NegativeControlKind.OVERCLAIM_BLOCK,
        expected_block_reason="Overclaiming must be blocked.",
        observed_decision="overclaim-allowed",
        blocked=False,
        evidence_ids=("control-evidence-overclaim",),
        findings=("overclaim-failed-open",),
    )

    report = build_negative_control_report(
        report_id="negative-control-report-failed-open",
        purpose="Validate Wave 8 fail-closed behavior without certification.",
        records=tuple(records),
    )

    assert not report.passed
    assert report.decision is NegativeControlSuiteDecision.FAILED_OPEN
    assert report.failed_open_count == 1
    assert any(
        finding.startswith("negative-controls-failed-open")
        for finding in report.findings
    )


def test_negative_control_report_rejects_missing_required_controls() -> None:
    records = default_wave8_negative_control_records()[:-1]

    with pytest.raises(ValueError, match="missing required controls"):
        build_negative_control_report(
            report_id="negative-control-report-missing",
            purpose="Validate incomplete negative controls.",
            records=records,
        )


def test_negative_control_report_rejects_duplicate_control_ids() -> None:
    record = default_wave8_negative_control_records()[0]

    with pytest.raises(ValueError, match="Duplicate control_id"):
        build_negative_control_report(
            report_id="negative-control-report-duplicate",
            purpose="Validate duplicate negative controls.",
            records=(record, record),
        )


def test_negative_control_report_rejects_overclaiming_purpose() -> None:
    with pytest.raises(ValueError, match="blocked overclaiming"):
        build_negative_control_report(
            report_id="negative-control-report-overclaim",
            purpose="This proves AGI.",
            records=default_wave8_negative_control_records(),
        )
