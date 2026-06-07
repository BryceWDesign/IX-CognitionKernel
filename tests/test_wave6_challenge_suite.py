import pytest

from ix_cognition_kernel.wave6_challenge_suite import (
    WAVE_SIX_REQUIRED_CHALLENGE_KINDS,
    WaveSixChallengeCase,
    WaveSixChallengeDecision,
    WaveSixChallengeKind,
    WaveSixChallengeOutcome,
    WaveSixChallengeSuite,
    build_wave_six_challenge_suite,
    required_wave_six_challenge_kinds,
)


def _case(
    kind: WaveSixChallengeKind,
    *,
    case_id: str | None = None,
    outcome: WaveSixChallengeOutcome = WaveSixChallengeOutcome.PASSED,
    decision: WaveSixChallengeDecision = WaveSixChallengeDecision.ACCEPT_FOR_REVIEW,
) -> WaveSixChallengeCase:
    return WaveSixChallengeCase(
        case_id=case_id or f"case-{kind.value}",
        kind=kind,
        title=f"Wave 6 {kind.value} challenge",
        challenge_prompt="Apply the corrected reasoning under independent pressure.",
        hidden_constraint_summary=(
            "The target includes a reviewer-held condition that prevents simple "
            "prompt replay from passing."
        ),
        measurable_success_criteria=(
            "Prediction is recorded before outcome evidence is revealed.",
            "The system explains whether the corrected structure should transfer.",
        ),
        expected_failure_modes=(
            "The system claims transfer without checking the hidden constraint.",
            "The system ignores a negative-control failure.",
        ),
        evidence_ids=(f"evidence-{kind.value}",),
        outcome=outcome,
        decision=decision,
    )


def _complete_cases() -> tuple[WaveSixChallengeCase, ...]:
    return tuple(_case(kind) for kind in WAVE_SIX_REQUIRED_CHALLENGE_KINDS)


def test_required_challenge_kinds_are_locked() -> None:
    assert required_wave_six_challenge_kinds() == (
        WaveSixChallengeKind.REALITY_CORRECTION,
        WaveSixChallengeKind.FUTURE_REASONING_CHANGE,
        WaveSixChallengeKind.CROSS_DOMAIN_TRANSFER,
        WaveSixChallengeKind.NOVELTY_GENERALIZATION,
        WaveSixChallengeKind.NEGATIVE_CONTROL,
        WaveSixChallengeKind.FALSIFICATION,
        WaveSixChallengeKind.HUMAN_AUTHORITY_BOUNDARY,
    )


def test_challenge_case_is_evidence_bound_and_fingerprinted() -> None:
    case = _case(WaveSixChallengeKind.CROSS_DOMAIN_TRANSFER)

    assert case.passed
    assert not case.blocks_claim
    assert not case.needs_more_evidence
    assert case.evidence_ids == ("evidence-cross-domain-transfer",)
    assert case.fingerprint() == case.fingerprint()
    assert len(case.fingerprint()) == 64


def test_challenge_case_rejects_agi_claim_and_autonomous_execution() -> None:
    with pytest.raises(ValueError, match="must not claim AGI"):
        WaveSixChallengeCase(
            case_id="agi-case",
            kind=WaveSixChallengeKind.FALSIFICATION,
            title="Invalid AGI case",
            challenge_prompt="Invalid prompt.",
            hidden_constraint_summary="Invalid hidden condition.",
            measurable_success_criteria=("Criterion.",),
            expected_failure_modes=("Failure.",),
            evidence_ids=("evidence",),
            claims_agi=True,
        )

    with pytest.raises(ValueError, match="must not allow autonomous execution"):
        WaveSixChallengeCase(
            case_id="auto-case",
            kind=WaveSixChallengeKind.FALSIFICATION,
            title="Invalid autonomous case",
            challenge_prompt="Invalid prompt.",
            hidden_constraint_summary="Invalid hidden condition.",
            measurable_success_criteria=("Criterion.",),
            expected_failure_modes=("Failure.",),
            evidence_ids=("evidence",),
            allows_autonomous_execution=True,
        )


def test_failed_or_safety_gated_challenge_case_must_block_claim() -> None:
    with pytest.raises(ValueError, match="must block the claim"):
        _case(
            WaveSixChallengeKind.NEGATIVE_CONTROL,
            outcome=WaveSixChallengeOutcome.FAILED,
            decision=WaveSixChallengeDecision.NEEDS_MORE_EVIDENCE,
        )

    with pytest.raises(ValueError, match="must block the claim"):
        _case(
            WaveSixChallengeKind.HUMAN_AUTHORITY_BOUNDARY,
            outcome=WaveSixChallengeOutcome.BLOCKED_BY_SAFETY_GATE,
            decision=WaveSixChallengeDecision.NEEDS_MORE_EVIDENCE,
        )


def test_passed_challenge_case_must_be_accepted_for_review() -> None:
    with pytest.raises(ValueError, match="must be accepted for review"):
        _case(
            WaveSixChallengeKind.REALITY_CORRECTION,
            outcome=WaveSixChallengeOutcome.PASSED,
            decision=WaveSixChallengeDecision.RECORD_ONLY,
        )


def test_challenge_suite_is_ready_when_all_required_kinds_pass() -> None:
    suite = build_wave_six_challenge_suite(
        suite_id="challenge-suite-ready",
        cases=_complete_cases(),
        notes=("Independent challenge pressure is required before external review.",),
    )

    assert suite.present_kinds == WAVE_SIX_REQUIRED_CHALLENGE_KINDS
    assert suite.missing_kinds == ()
    assert suite.passed_required_kinds == WAVE_SIX_REQUIRED_CHALLENGE_KINDS
    assert suite.missing_passed_required_kinds == ()
    assert suite.blocking_case_ids == ()
    assert suite.needs_more_evidence_case_ids == ()
    assert suite.ready_for_external_challenge_review
    assert suite.fingerprint() == suite.fingerprint()
    assert len(suite.fingerprint()) == 64


def test_challenge_suite_reports_missing_required_kind() -> None:
    suite = WaveSixChallengeSuite(
        suite_id="challenge-suite-missing-kind",
        cases=_complete_cases()[:-1],
    )

    assert suite.missing_kinds == (WaveSixChallengeKind.HUMAN_AUTHORITY_BOUNDARY,)
    assert not suite.ready_for_external_challenge_review


def test_challenge_suite_reports_case_needing_more_evidence() -> None:
    cases = list(_complete_cases())
    cases[1] = _case(
        WaveSixChallengeKind.FUTURE_REASONING_CHANGE,
        outcome=WaveSixChallengeOutcome.INCONCLUSIVE,
        decision=WaveSixChallengeDecision.NEEDS_MORE_EVIDENCE,
    )
    suite = WaveSixChallengeSuite(
        suite_id="challenge-suite-needs-evidence",
        cases=tuple(cases),
    )

    assert suite.needs_more_evidence_case_ids == ("case-future-reasoning-change",)
    assert not suite.ready_for_external_challenge_review


def test_challenge_suite_blocks_on_failed_case() -> None:
    cases = list(_complete_cases())
    cases[4] = _case(
        WaveSixChallengeKind.NEGATIVE_CONTROL,
        outcome=WaveSixChallengeOutcome.FAILED,
        decision=WaveSixChallengeDecision.BLOCK_CLAIM,
    )
    suite = WaveSixChallengeSuite(
        suite_id="challenge-suite-blocked",
        cases=tuple(cases),
    )

    assert suite.blocking_case_ids == ("case-negative-control",)
    assert not suite.ready_for_external_challenge_review


def test_challenge_suite_can_lookup_case_by_kind() -> None:
    suite = WaveSixChallengeSuite(
        suite_id="challenge-suite-lookup",
        cases=(_case(WaveSixChallengeKind.REALITY_CORRECTION),),
    )

    case = suite.case_for_kind(WaveSixChallengeKind.REALITY_CORRECTION)

    assert case is not None
    assert case.case_id == "case-reality-correction"
    assert suite.case_for_kind(WaveSixChallengeKind.FALSIFICATION) is None


def test_challenge_suite_rejects_duplicate_case_ids() -> None:
    case = _case(WaveSixChallengeKind.REALITY_CORRECTION)

    with pytest.raises(ValueError, match="Duplicate case_id"):
        WaveSixChallengeSuite(suite_id="challenge-suite-duplicate", cases=(case, case))


def test_challenge_suite_rejects_agi_claim() -> None:
    with pytest.raises(ValueError, match="must not claim AGI"):
        WaveSixChallengeSuite(
            suite_id="challenge-suite-agi",
            cases=_complete_cases(),
            claims_agi=True,
        )
