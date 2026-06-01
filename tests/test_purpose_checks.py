import pytest

from ix_cognition_kernel.purpose import (
    NonAttachedPurposeAssessment,
    PurposeAssessmentInput,
    PurposeCheckResult,
    PurposeCheckStatus,
    PurposeRule,
    assess_non_attached_purpose,
    doctrine_rules_are_executable,
)
from ix_cognition_kernel.state import HumanAuthority, UncertaintyStatus


def safe_input() -> PurposeAssessmentInput:
    return PurposeAssessmentInput(
        statement=(
            "IX-CognitionKernel represents a bounded Wave 1 research prototype state."
        ),
        wave_number=1,
        confidence=0.82,
        evidence_ids=("ev-purpose-001",),
        uncertainty=UncertaintyStatus.KNOWN,
        uncertainty_disclosed=True,
        human_authority=HumanAuthority.REQUIRED,
    )


def test_doctrine_rules_have_executable_counterparts() -> None:
    assert doctrine_rules_are_executable() is True


def test_safe_non_attached_purpose_input_passes_all_checks() -> None:
    assessment = assess_non_attached_purpose(safe_input())

    assert assessment.passes is True
    assert assessment.violations == ()
    assert tuple(result.rule for result in assessment.results) == tuple(PurposeRule)
    assert assessment.result_for_rule(PurposeRule.TRUTH_OVER_WINNING).status is (
        PurposeCheckStatus.SATISFIED
    )


def test_purpose_input_rejects_empty_statement() -> None:
    with pytest.raises(ValueError, match="non-empty statement"):
        PurposeAssessmentInput(
            statement=" ",
            wave_number=1,
            confidence=0.5,
            evidence_ids=(),
            uncertainty=UncertaintyStatus.KNOWN,
            uncertainty_disclosed=True,
            human_authority=HumanAuthority.REQUIRED,
        )


def test_purpose_input_rejects_out_of_range_confidence() -> None:
    with pytest.raises(ValueError, match="between 0.0 and 1.0"):
        PurposeAssessmentInput(
            statement="Invalid confidence must fail closed.",
            wave_number=1,
            confidence=1.01,
            evidence_ids=(),
            uncertainty=UncertaintyStatus.KNOWN,
            uncertainty_disclosed=True,
            human_authority=HumanAuthority.REQUIRED,
        )


def test_purpose_input_rejects_duplicate_evidence_ids() -> None:
    with pytest.raises(ValueError, match="evidence_ids must be unique"):
        PurposeAssessmentInput(
            statement="Duplicate evidence ids must fail closed.",
            wave_number=1,
            confidence=0.5,
            evidence_ids=("ev-001", "ev-001"),
            uncertainty=UncertaintyStatus.KNOWN,
            uncertainty_disclosed=True,
            human_authority=HumanAuthority.REQUIRED,
        )


def test_truth_over_winning_violation_blocks_purpose_pass() -> None:
    assessment_input = safe_input().__class__(
        statement=safe_input().statement,
        wave_number=safe_input().wave_number,
        confidence=safe_input().confidence,
        evidence_ids=safe_input().evidence_ids,
        uncertainty=safe_input().uncertainty,
        uncertainty_disclosed=safe_input().uncertainty_disclosed,
        human_authority=safe_input().human_authority,
        optimizes_for_winning_over_truth=True,
    )

    assessment = assess_non_attached_purpose(assessment_input)

    assert assessment.passes is False
    assert assessment.result_for_rule(PurposeRule.TRUTH_OVER_WINNING).is_violation


def test_evidence_over_confidence_blocks_high_confidence_without_evidence() -> None:
    assessment = assess_non_attached_purpose(
        PurposeAssessmentInput(
            statement="A high-confidence claim without evidence must not pass.",
            wave_number=1,
            confidence=0.9,
            evidence_ids=(),
            uncertainty=UncertaintyStatus.KNOWN,
            uncertainty_disclosed=True,
            human_authority=HumanAuthority.REQUIRED,
        )
    )

    assert assessment.passes is False
    assert assessment.result_for_rule(PurposeRule.EVIDENCE_OVER_CONFIDENCE).is_violation


def test_confidence_presented_as_evidence_is_a_violation() -> None:
    assessment_input = safe_input().__class__(
        statement=safe_input().statement,
        wave_number=safe_input().wave_number,
        confidence=safe_input().confidence,
        evidence_ids=safe_input().evidence_ids,
        uncertainty=safe_input().uncertainty,
        uncertainty_disclosed=safe_input().uncertainty_disclosed,
        human_authority=safe_input().human_authority,
        presents_confidence_as_evidence=True,
    )

    assessment = assess_non_attached_purpose(assessment_input)

    assert assessment.result_for_rule(PurposeRule.EVIDENCE_OVER_CONFIDENCE).is_violation


def test_hidden_uncertainty_is_a_violation() -> None:
    assessment = assess_non_attached_purpose(
        PurposeAssessmentInput(
            statement="Hidden uncertainty must not pass doctrine checks.",
            wave_number=1,
            confidence=0.65,
            evidence_ids=("ev-uncertainty",),
            uncertainty=UncertaintyStatus.ASSUMED,
            uncertainty_disclosed=False,
            human_authority=HumanAuthority.REQUIRED,
        )
    )

    assert assessment.passes is False
    assert assessment.result_for_rule(PurposeRule.UNCERTAINTY_OVER_THEATER).is_violation


def test_unsafe_to_act_uncertainty_cannot_pass_as_performance() -> None:
    assessment = assess_non_attached_purpose(
        PurposeAssessmentInput(
            statement="Unsafe uncertainty must be blocked even when disclosed.",
            wave_number=1,
            confidence=0.4,
            evidence_ids=("ev-unsafe",),
            uncertainty=UncertaintyStatus.UNSAFE_TO_ACT,
            uncertainty_disclosed=True,
            human_authority=HumanAuthority.REQUIRED,
        )
    )

    assert assessment.result_for_rule(PurposeRule.UNCERTAINTY_OVER_THEATER).is_violation


def test_private_agenda_and_reward_chasing_are_violations() -> None:
    assessment = assess_non_attached_purpose(
        PurposeAssessmentInput(
            statement="Private agenda and reward chasing must fail closed.",
            wave_number=1,
            confidence=0.6,
            evidence_ids=("ev-purpose",),
            uncertainty=UncertaintyStatus.KNOWN,
            uncertainty_disclosed=True,
            human_authority=HumanAuthority.REQUIRED,
            private_agenda_detected=True,
            reward_chasing_detected=True,
        )
    )

    assert assessment.result_for_rule(PurposeRule.NO_PRIVATE_AGENDA).is_violation
    assert assessment.result_for_rule(PurposeRule.NO_REWARD_CHASING).is_violation


def test_absent_human_authority_is_a_violation() -> None:
    assessment = assess_non_attached_purpose(
        PurposeAssessmentInput(
            statement="Human authority cannot be absent from governed cognition state.",
            wave_number=1,
            confidence=0.6,
            evidence_ids=("ev-authority",),
            uncertainty=UncertaintyStatus.KNOWN,
            uncertainty_disclosed=True,
            human_authority=HumanAuthority.ABSENT,
        )
    )

    assert assessment.result_for_rule(
        PurposeRule.HUMAN_AUTHORITY_PRESERVED
    ).is_violation


def test_denied_human_authority_still_preserves_human_authority() -> None:
    assessment = assess_non_attached_purpose(
        PurposeAssessmentInput(
            statement="A denied human decision still preserves human authority.",
            wave_number=1,
            confidence=0.6,
            evidence_ids=("ev-authority-denied",),
            uncertainty=UncertaintyStatus.KNOWN,
            uncertainty_disclosed=True,
            human_authority=HumanAuthority.DENIED,
        )
    )

    assert assessment.result_for_rule(PurposeRule.HUMAN_AUTHORITY_PRESERVED).status is (
        PurposeCheckStatus.SATISFIED
    )


def test_agi_claim_is_blocked_before_wave_six_even_when_requested_by_statement() -> (
    None
):
    assessment = assess_non_attached_purpose(
        PurposeAssessmentInput(
            statement="AGI achieved by this prototype.",
            wave_number=1,
            confidence=0.8,
            evidence_ids=("ev-claim",),
            uncertainty=UncertaintyStatus.KNOWN,
            uncertainty_disclosed=True,
            human_authority=HumanAuthority.REQUIRED,
        )
    )

    assert assessment.passes is False
    assert assessment.result_for_rule(
        PurposeRule.NO_AGI_CLAIM_WITHOUT_EVIDENCE
    ).is_violation


def test_agi_claim_requires_wave_six_and_overwhelming_independent_evidence() -> None:
    blocked = assess_non_attached_purpose(
        PurposeAssessmentInput(
            statement="Request AGI claim gate review.",
            wave_number=6,
            confidence=0.8,
            evidence_ids=("ev-agi-review",),
            uncertainty=UncertaintyStatus.KNOWN,
            uncertainty_disclosed=True,
            human_authority=HumanAuthority.REQUIRED,
            requests_agi_claim=True,
            overwhelming_independent_evidence=False,
        )
    )
    allowed = assess_non_attached_purpose(
        PurposeAssessmentInput(
            statement="Request AGI claim gate review.",
            wave_number=6,
            confidence=0.8,
            evidence_ids=("ev-agi-review",),
            uncertainty=UncertaintyStatus.KNOWN,
            uncertainty_disclosed=True,
            human_authority=HumanAuthority.REQUIRED,
            requests_agi_claim=True,
            overwhelming_independent_evidence=True,
        )
    )

    assert blocked.result_for_rule(
        PurposeRule.NO_AGI_CLAIM_WITHOUT_EVIDENCE
    ).is_violation
    assert allowed.result_for_rule(
        PurposeRule.NO_AGI_CLAIM_WITHOUT_EVIDENCE
    ).status is (PurposeCheckStatus.SATISFIED)


def test_purpose_check_result_requires_reasons() -> None:
    with pytest.raises(ValueError, match="require reasons"):
        PurposeCheckResult(
            rule=PurposeRule.TRUTH_OVER_WINNING,
            status=PurposeCheckStatus.SATISFIED,
            reasons=(),
            evidence_ids=(),
        )


def test_assessment_requires_every_rule_in_order() -> None:
    with pytest.raises(ValueError, match="cover every rule"):
        NonAttachedPurposeAssessment(
            assessment_input=safe_input(),
            results=(
                PurposeCheckResult(
                    rule=PurposeRule.TRUTH_OVER_WINNING,
                    status=PurposeCheckStatus.SATISFIED,
                    reasons=("Only one rule is not enough.",),
                    evidence_ids=(),
                ),
            ),
        )
