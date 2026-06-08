import pytest

from ix_cognition_kernel.wave6_consistency import (
    WAVE_SIX_REQUIRED_CONSISTENCY_CHECKS,
    WaveSixConsistencyCheck,
    WaveSixConsistencyCheckKind,
    WaveSixConsistencyDecision,
    WaveSixConsistencyFinding,
    WaveSixConsistencyReport,
    WaveSixConsistencyStatus,
    build_fingerprint_presence_check,
    build_wave_six_consistency_report,
    required_wave_six_consistency_checks,
)


class _FingerprintedArtifact:
    def __init__(self, value: str) -> None:
        self._value = value

    def fingerprint(self) -> str:
        return self._value


def _boundary_statement() -> str:
    return (
        "This Wave-6 measured system-level cognition package is released for "
        "bounded review under human authority and independent review. It is not "
        "an AGI claim."
    )


def _check(
    kind: WaveSixConsistencyCheckKind,
    *,
    check_id: str | None = None,
    finding: WaveSixConsistencyFinding = WaveSixConsistencyFinding.PASSED,
    expected_value: str = "aligned",
    observed_value: str = "aligned",
    requires_follow_up: bool = False,
    blocks_review: bool = False,
) -> WaveSixConsistencyCheck:
    return WaveSixConsistencyCheck(
        check_id=check_id or f"check-{kind.value}",
        kind=kind,
        summary=f"Consistency check for {kind.value}.",
        expected_value=expected_value,
        observed_value=observed_value,
        evidence_ids=(f"evidence-{kind.value}",),
        finding=finding,
        reviewer_question=f"Does {kind.value} remain aligned?",
        requires_follow_up=requires_follow_up,
        blocks_review=blocks_review,
    )


def _complete_checks() -> tuple[WaveSixConsistencyCheck, ...]:
    return tuple(_check(kind) for kind in WAVE_SIX_REQUIRED_CONSISTENCY_CHECKS)


def _report(
    *,
    checks: tuple[WaveSixConsistencyCheck, ...] | None = None,
    decision: WaveSixConsistencyDecision = (
        WaveSixConsistencyDecision.ACCEPT_FOR_BOUNDED_REVIEW
    ),
    claims_agi: bool = False,
    claim_boundary_statement: str | None = None,
) -> WaveSixConsistencyReport:
    return WaveSixConsistencyReport(
        report_id="consistency-report-1",
        checks=checks or _complete_checks(),
        decision=decision,
        claim_boundary_statement=claim_boundary_statement or _boundary_statement(),
        generated_by_engine_id="wave6-consistency-engine",
        human_authority_id="human-authority-1",
        independent_reviewer_id="independent-reviewer-1",
        claims_agi=claims_agi,
        notes=("Consistency means cross-artifact alignment, not AGI achieved.",),
    )


def test_required_consistency_checks_are_locked() -> None:
    assert required_wave_six_consistency_checks() == (
        WaveSixConsistencyCheckKind.CLAIM_BOUNDARY_ALIGNMENT,
        WaveSixConsistencyCheckKind.HUMAN_AUTHORITY_ALIGNMENT,
        WaveSixConsistencyCheckKind.INDEPENDENT_REVIEW_ALIGNMENT,
        WaveSixConsistencyCheckKind.RELEASE_SUMMARY_LINK,
        WaveSixConsistencyCheckKind.AUDIT_RELEASE_LINK,
        WaveSixConsistencyCheckKind.MATURITY_DECISION_LINK,
        WaveSixConsistencyCheckKind.EXTERNAL_VALIDATION_LINK,
        WaveSixConsistencyCheckKind.REQUIRED_FINGERPRINT_PRESENT,
        WaveSixConsistencyCheckKind.NO_OVERCLAIM_PRESENT,
    )


def test_consistency_check_is_evidence_bound_and_fingerprinted() -> None:
    check = _check(WaveSixConsistencyCheckKind.CLAIM_BOUNDARY_ALIGNMENT)

    assert check.passed
    assert not check.needs_more_evidence
    assert not check.blocks_bounded_review
    assert check.fingerprint() == check.fingerprint()
    assert len(check.fingerprint()) == 64


def test_consistency_check_enforces_finding_semantics() -> None:
    with pytest.raises(ValueError, match="cannot require follow-up"):
        _check(
            WaveSixConsistencyCheckKind.AUDIT_RELEASE_LINK,
            finding=WaveSixConsistencyFinding.PASSED,
            requires_follow_up=True,
        )

    with pytest.raises(ValueError, match="require follow-up"):
        _check(
            WaveSixConsistencyCheckKind.AUDIT_RELEASE_LINK,
            finding=WaveSixConsistencyFinding.NEEDS_MORE_EVIDENCE,
        )

    with pytest.raises(ValueError, match="must block review"):
        _check(
            WaveSixConsistencyCheckKind.NO_OVERCLAIM_PRESENT,
            finding=WaveSixConsistencyFinding.BLOCKS_REVIEW,
        )


def test_mismatched_consistency_check_cannot_pass() -> None:
    with pytest.raises(ValueError, match="cannot pass"):
        _check(
            WaveSixConsistencyCheckKind.RELEASE_SUMMARY_LINK,
            expected_value="release-fingerprint-a",
            observed_value="release-fingerprint-b",
        )


def test_consistency_report_is_ready_when_complete_and_aligned() -> None:
    report = build_wave_six_consistency_report(
        report_id="consistency-report-ready",
        checks=_complete_checks(),
        decision=WaveSixConsistencyDecision.ACCEPT_FOR_BOUNDED_REVIEW,
        claim_boundary_statement=_boundary_statement(),
        generated_by_engine_id="wave6-consistency-engine",
        human_authority_id="human-authority-1",
        independent_reviewer_id="independent-reviewer-1",
        notes=("All consistency checks passed for bounded review.",),
    )

    assert report.present_check_kinds == WAVE_SIX_REQUIRED_CONSISTENCY_CHECKS
    assert report.missing_check_kinds == ()
    assert report.follow_up_check_ids == ()
    assert report.blocking_check_ids == ()
    assert report.status is WaveSixConsistencyStatus.READY
    assert report.ready_for_bounded_review
    assert report.fingerprint() == report.fingerprint()
    assert len(report.fingerprint()) == 64


def test_consistency_report_reports_missing_check() -> None:
    report = _report(
        checks=_complete_checks()[:-1],
        decision=WaveSixConsistencyDecision.HOLD_FOR_MORE_EVIDENCE,
    )

    assert report.missing_check_kinds == (
        WaveSixConsistencyCheckKind.NO_OVERCLAIM_PRESENT,
    )
    assert report.status is WaveSixConsistencyStatus.NEEDS_MORE_EVIDENCE
    assert not report.ready_for_bounded_review


def test_consistency_report_blocks_on_blocking_check_or_overclaim() -> None:
    checks = list(_complete_checks())
    checks[-1] = _check(
        WaveSixConsistencyCheckKind.NO_OVERCLAIM_PRESENT,
        finding=WaveSixConsistencyFinding.BLOCKS_REVIEW,
        expected_value="no-overclaim",
        observed_value="overclaim",
        blocks_review=True,
    )
    report = _report(
        checks=tuple(checks),
        decision=WaveSixConsistencyDecision.BLOCK_REVIEW,
    )

    assert report.blocking_check_ids == ("check-no-overclaim-present",)
    assert report.status is WaveSixConsistencyStatus.BLOCKED
    assert not report.ready_for_bounded_review

    overclaim = _report(
        decision=WaveSixConsistencyDecision.BLOCK_REVIEW,
        claims_agi=True,
    )

    assert overclaim.overclaim_present
    assert overclaim.status is WaveSixConsistencyStatus.BLOCKED


def test_accepted_consistency_report_rejects_missing_or_follow_up_checks() -> None:
    with pytest.raises(ValueError, match="require every check"):
        _report(checks=_complete_checks()[:-1])

    checks = list(_complete_checks())
    checks[2] = _check(
        WaveSixConsistencyCheckKind.INDEPENDENT_REVIEW_ALIGNMENT,
        finding=WaveSixConsistencyFinding.NEEDS_MORE_EVIDENCE,
        requires_follow_up=True,
    )

    with pytest.raises(ValueError, match="cannot need follow-up"):
        _report(checks=tuple(checks))


def test_blocked_consistency_report_requires_blocker_or_overclaim() -> None:
    with pytest.raises(ValueError, match="require blocker or overclaim"):
        _report(decision=WaveSixConsistencyDecision.BLOCK_REVIEW)


def test_consistency_report_reports_invalid_claim_boundary_statement() -> None:
    report = _report(
        decision=WaveSixConsistencyDecision.HOLD_FOR_MORE_EVIDENCE,
        claim_boundary_statement="Wave 6 is done.",
    )

    assert not report.claim_boundary_statement_valid
    assert report.status is WaveSixConsistencyStatus.NEEDS_MORE_EVIDENCE


def test_consistency_report_lookup_returns_present_check_only() -> None:
    report = _report(
        checks=(_check(WaveSixConsistencyCheckKind.CLAIM_BOUNDARY_ALIGNMENT),),
        decision=WaveSixConsistencyDecision.HOLD_FOR_MORE_EVIDENCE,
    )

    check = report.check_for_kind(WaveSixConsistencyCheckKind.CLAIM_BOUNDARY_ALIGNMENT)

    assert check is not None
    assert check.check_id == "check-claim-boundary-alignment"
    assert (
        report.check_for_kind(WaveSixConsistencyCheckKind.NO_OVERCLAIM_PRESENT) is None
    )


def test_consistency_report_rejects_duplicate_check_ids_or_kinds() -> None:
    check = _check(WaveSixConsistencyCheckKind.CLAIM_BOUNDARY_ALIGNMENT)

    with pytest.raises(ValueError, match="Duplicate check_id"):
        _report(
            checks=(check, check),
            decision=WaveSixConsistencyDecision.HOLD_FOR_MORE_EVIDENCE,
        )

    with pytest.raises(ValueError, match="Duplicate check kind"):
        _report(
            checks=(
                check,
                _check(
                    WaveSixConsistencyCheckKind.CLAIM_BOUNDARY_ALIGNMENT,
                    check_id="different-check-id",
                ),
            ),
            decision=WaveSixConsistencyDecision.HOLD_FOR_MORE_EVIDENCE,
        )


def test_fingerprint_presence_check_uses_structural_artifact_protocol() -> None:
    check = build_fingerprint_presence_check(
        check_id="fingerprint-present",
        artifact_id="release-manifest",
        artifact=_FingerprintedArtifact("abc123"),
        evidence_ids=("evidence-release-manifest",),
    )

    assert check.passed
    assert check.kind is WaveSixConsistencyCheckKind.REQUIRED_FINGERPRINT_PRESENT
    assert check.expected_value == "fingerprint-present"
    assert check.observed_value == "fingerprint-present"
