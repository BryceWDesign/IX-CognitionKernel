import pytest

from ix_cognition_kernel.wave7_manipulation_pressure import (
    CrossSessionIntentFragment,
    IntentFragmentRisk,
    ManipulationDecision,
    ManipulationDecisionStatus,
    ManipulationPressureReport,
    ManipulationSeverity,
    ManipulationSignal,
    ManipulationSignalKind,
    PressurePattern,
    PressurePatternKind,
    evaluate_manipulation_pressure,
)


def _fragment(
    *,
    fragment_id: str = "fragment-1",
    session_id: str = "session-1",
    risk_tags: tuple[IntentFragmentRisk, ...] = (),
    evidence_ids: tuple[str, ...] = ("fragment-evidence-1",),
) -> CrossSessionIntentFragment:
    return CrossSessionIntentFragment(
        fragment_id=fragment_id,
        session_id=session_id,
        turn_ids=("turn-1",),
        intent_summary="User requests a bounded review of a cognitive change.",
        normalized_intent_tags=("bounded-review",),
        risk_tags=risk_tags,
        evidence_ids=evidence_ids,
    )


def _signal(
    *,
    signal_id: str = "signal-review",
    severity: ManipulationSeverity = ManipulationSeverity.REVIEW_REQUIRED,
    requires_human_review: bool = True,
    blocks_progress: bool = False,
) -> ManipulationSignal:
    return ManipulationSignal(
        signal_id=signal_id,
        kind=ManipulationSignalKind.BODY_ESCALATION_PRESSURE,
        severity=severity,
        summary="Body escalation requires review.",
        evidence_ids=("signal-evidence-1",),
        fragment_ids=("fragment-1",),
        requires_human_review=requires_human_review,
        blocks_progress=blocks_progress,
    )


def _pattern(
    *,
    pattern_id: str = "pattern-review",
    severity: ManipulationSeverity = ManipulationSeverity.REVIEW_REQUIRED,
    requires_human_review: bool = True,
    blocks_progress: bool = False,
) -> PressurePattern:
    return PressurePattern(
        pattern_id=pattern_id,
        kind=PressurePatternKind.MULTI_TURN,
        severity=severity,
        summary="Multi-turn pressure requires review.",
        fragment_ids=("fragment-1",),
        signal_ids=("signal-review",),
        evidence_ids=("pattern-evidence-1",),
        requires_human_review=requires_human_review,
        blocks_progress=blocks_progress,
    )


def test_intent_fragment_tracks_risk_without_executing_anything() -> None:
    fragment = _fragment(
        risk_tags=(
            IntentFragmentRisk.FRAGMENTED_INTENT,
            IntentFragmentRisk.BODY_ESCALATION,
        )
    )

    assert fragment.risky
    assert fragment.risk_tag_values == (
        "body-escalation",
        "fragmented-intent",
    )
    assert fragment.carries(IntentFragmentRisk.BODY_ESCALATION)
    assert fragment.fingerprint() == fragment.fingerprint()
    assert len(fragment.fingerprint()) == 64

    with pytest.raises(ValueError, match="require turn ids"):
        CrossSessionIntentFragment(
            fragment_id="fragment-no-turns",
            session_id="session-1",
            turn_ids=(),
            intent_summary="Missing turn ids.",
            normalized_intent_tags=("bounded-review",),
            risk_tags=(),
            evidence_ids=("fragment-evidence-1",),
        )


def test_manipulation_signal_enforces_severity_semantics() -> None:
    signal = _signal()

    assert signal.needs_review
    assert not signal.blocking
    assert signal.fingerprint() == signal.fingerprint()
    assert len(signal.fingerprint()) == 64

    with pytest.raises(ValueError, match="must block progress"):
        _signal(
            signal_id="signal-blocking-bad",
            severity=ManipulationSeverity.BLOCKING,
            requires_human_review=False,
            blocks_progress=False,
        )

    with pytest.raises(ValueError, match="must require human review"):
        _signal(
            signal_id="signal-review-bad",
            severity=ManipulationSeverity.REVIEW_REQUIRED,
            requires_human_review=False,
        )


def test_pressure_pattern_enforces_cross_session_and_blocking_rules() -> None:
    pattern = _pattern()

    assert pattern.needs_review
    assert not pattern.blocking
    assert pattern.fingerprint() == pattern.fingerprint()
    assert len(pattern.fingerprint()) == 64

    with pytest.raises(ValueError, match="must block progress"):
        _pattern(
            pattern_id="pattern-blocking-bad",
            severity=ManipulationSeverity.BLOCKING,
            requires_human_review=False,
            blocks_progress=False,
        )

    with pytest.raises(ValueError, match="multiple fragments"):
        PressurePattern(
            pattern_id="pattern-cross-session-bad",
            kind=PressurePatternKind.CROSS_SESSION,
            severity=ManipulationSeverity.REVIEW_REQUIRED,
            summary="Bad cross-session pattern.",
            fragment_ids=("fragment-1",),
            signal_ids=("signal-review",),
            evidence_ids=("pattern-evidence-1",),
            requires_human_review=True,
        )


def test_manipulation_decision_requires_authority_for_review_or_block() -> None:
    decision = ManipulationDecision(
        decision_id="decision-review",
        status=ManipulationDecisionStatus.READY_FOR_HUMAN_REVIEW,
        reason_ids=("human-review-required",),
        required_authority_refs=("human-authority-1",),
        evidence_ids=("decision-evidence-1",),
    )

    assert decision.ready_for_review
    assert not decision.blocked
    assert decision.fingerprint() == decision.fingerprint()
    assert len(decision.fingerprint()) == 64

    with pytest.raises(ValueError, match="require authority refs"):
        ManipulationDecision(
            decision_id="decision-bad-review",
            status=ManipulationDecisionStatus.READY_FOR_HUMAN_REVIEW,
            reason_ids=("human-review-required",),
            required_authority_refs=(),
            evidence_ids=("decision-evidence-1",),
        )


def test_evaluate_clear_pressure_for_clean_fragment() -> None:
    report = evaluate_manipulation_pressure(
        report_id="manipulation-report-clear",
        fragments=(_fragment(),),
        authority_refs=("human-authority-1",),
        notes=("No manipulation pressure detected.",),
    )

    assert report.decision.status is ManipulationDecisionStatus.CLEAR
    assert not report.ready_for_review
    assert not report.blocks_claim
    assert report.signal_ids == ()
    assert report.pattern_ids == ()
    assert report.risky_fragment_ids == ()
    assert report.assembled_intent_tags == ("bounded-review",)
    assert "fragment-evidence-1" in report.evidence_ids
    assert report.fingerprint() == report.fingerprint()
    assert len(report.fingerprint()) == 64


def test_evaluate_body_escalation_routes_to_human_review() -> None:
    report = evaluate_manipulation_pressure(
        report_id="manipulation-report-review",
        fragments=(
            _fragment(
                risk_tags=(IntentFragmentRisk.BODY_ESCALATION,),
            ),
        ),
        authority_refs=("human-authority-1",),
    )

    assert report.decision.status is ManipulationDecisionStatus.READY_FOR_HUMAN_REVIEW
    assert report.ready_for_review
    assert not report.blocks_claim
    assert report.review_signal_ids == ("signal-body-escalation",)
    assert report.decision.required_authority_refs == ("human-authority-1",)


def test_evaluate_authority_laundering_blocks_progress() -> None:
    report = evaluate_manipulation_pressure(
        report_id="manipulation-report-blocked",
        fragments=(
            _fragment(
                risk_tags=(IntentFragmentRisk.AUTHORITY_LAUNDERING,),
            ),
        ),
        authority_refs=("human-authority-1",),
    )

    assert report.decision.status is ManipulationDecisionStatus.BLOCKED
    assert report.blocks_claim
    assert "signal-authority-laundering" in report.blocking_signal_ids
    assert "pattern-authority-chain" in report.blocking_pattern_ids
    assert "authority-laundering" in report.risk_tag_values


def test_evaluate_claim_inflation_and_evidence_skip_block_progress() -> None:
    report = evaluate_manipulation_pressure(
        report_id="manipulation-report-claim-evidence",
        fragments=(
            _fragment(
                fragment_id="fragment-claim",
                risk_tags=(IntentFragmentRisk.CLAIM_INFLATION,),
                evidence_ids=("claim-evidence-1",),
            ),
            _fragment(
                fragment_id="fragment-evidence",
                risk_tags=(IntentFragmentRisk.EVIDENCE_SKIP,),
                evidence_ids=("skip-evidence-1",),
            ),
        ),
        authority_refs=("human-authority-1",),
    )

    assert report.blocks_claim
    assert "signal-claim-inflation" in report.blocking_signal_ids
    assert "signal-evidence-skip" in report.blocking_signal_ids
    assert "pattern-claim-escalation-chain" in report.blocking_pattern_ids
    assert "pattern-evidence-bypass-chain" in report.blocking_pattern_ids
    assert "claim-evidence-1" in report.evidence_ids
    assert "skip-evidence-1" in report.evidence_ids


def test_cross_session_fragmented_intent_assembles_for_review() -> None:
    report = evaluate_manipulation_pressure(
        report_id="manipulation-report-cross-session",
        fragments=(
            _fragment(
                fragment_id="fragment-1",
                session_id="session-1",
                risk_tags=(IntentFragmentRisk.FRAGMENTED_INTENT,),
                evidence_ids=("fragment-evidence-1",),
            ),
            _fragment(
                fragment_id="fragment-2",
                session_id="session-2",
                risk_tags=(IntentFragmentRisk.BODY_ESCALATION,),
                evidence_ids=("fragment-evidence-2",),
            ),
        ),
        authority_refs=("human-authority-1",),
    )

    assert report.ready_for_review
    assert not report.blocks_claim
    assert "signal-fragmented-intent-assembly" in report.review_signal_ids
    assert "signal-body-escalation" in report.review_signal_ids
    assert "pattern-cross-session-pressure" in report.review_pattern_ids
    assert report.risky_fragment_ids == ("fragment-1", "fragment-2")


def test_report_rejects_signal_referencing_missing_fragment() -> None:
    decision = ManipulationDecision(
        decision_id="decision-review",
        status=ManipulationDecisionStatus.READY_FOR_HUMAN_REVIEW,
        reason_ids=("human-review-required",),
        required_authority_refs=("human-authority-1",),
        evidence_ids=("decision-evidence-1",),
    )

    with pytest.raises(ValueError, match="missing fragments"):
        ManipulationPressureReport(
            report_id="bad-report",
            fragments=(_fragment(),),
            signals=(
                ManipulationSignal(
                    signal_id="signal-missing-fragment",
                    kind=ManipulationSignalKind.BODY_ESCALATION_PRESSURE,
                    severity=ManipulationSeverity.REVIEW_REQUIRED,
                    summary="Bad missing fragment.",
                    evidence_ids=("signal-evidence-1",),
                    fragment_ids=("fragment-missing",),
                    requires_human_review=True,
                ),
            ),
            patterns=(),
            decision=decision,
        )


def test_report_rejects_pattern_referencing_missing_signal() -> None:
    decision = ManipulationDecision(
        decision_id="decision-review",
        status=ManipulationDecisionStatus.READY_FOR_HUMAN_REVIEW,
        reason_ids=("human-review-required",),
        required_authority_refs=("human-authority-1",),
        evidence_ids=("decision-evidence-1",),
    )

    with pytest.raises(ValueError, match="missing signals"):
        ManipulationPressureReport(
            report_id="bad-pattern-report",
            fragments=(_fragment(),),
            signals=(_signal(),),
            patterns=(
                PressurePattern(
                    pattern_id="pattern-missing-signal",
                    kind=PressurePatternKind.MULTI_TURN,
                    severity=ManipulationSeverity.REVIEW_REQUIRED,
                    summary="Bad missing signal.",
                    fragment_ids=("fragment-1",),
                    signal_ids=("signal-missing",),
                    evidence_ids=("pattern-evidence-1",),
                    requires_human_review=True,
                ),
            ),
            decision=decision,
        )


def test_evaluate_manipulation_pressure_requires_fragments() -> None:
    with pytest.raises(ValueError, match="requires fragments"):
        evaluate_manipulation_pressure(
            report_id="empty-report",
            fragments=(),
            authority_refs=("human-authority-1",),
        )
