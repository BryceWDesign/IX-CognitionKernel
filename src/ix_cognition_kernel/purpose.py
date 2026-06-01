"""Executable non-attached purpose checks for IX-CognitionKernel Wave 1.

The checks in this module turn the locked doctrine into reviewable machine
state. They do not certify intentions, infer hidden motives, approve execution,
or claim AGI. They provide fail-closed records showing whether a proposed
cognition state preserves truth over winning, evidence over confidence,
uncertainty honesty, no private agenda, no reward-chasing runtime purpose,
human authority, and the AGI evidence boundary.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from ix_cognition_kernel.doctrine import (
    FORBIDDEN_CLAIMS_BEFORE_WAVE_6,
    NON_ATTACHED_PURPOSE_RULES,
    allows_agi_claim,
)
from ix_cognition_kernel.state import HumanAuthority, UncertaintyStatus


class PurposeRule(StrEnum):
    """Executable non-attached purpose rule identifiers."""

    TRUTH_OVER_WINNING = "truth-over-winning"
    EVIDENCE_OVER_CONFIDENCE = "evidence-over-confidence"
    UNCERTAINTY_OVER_THEATER = "uncertainty-over-performance-theater"
    NO_PRIVATE_AGENDA = "no-private-agenda"
    NO_REWARD_CHASING = "no-runtime-reward-chasing-purpose"
    HUMAN_AUTHORITY_PRESERVED = "human-authority-preserved"
    NO_AGI_CLAIM_WITHOUT_EVIDENCE = (
        "no-agi-claim-without-overwhelming-independent-evidence"
    )


class PurposeCheckStatus(StrEnum):
    """Status for a non-attached purpose check."""

    SATISFIED = "satisfied"
    VIOLATED = "violated"


@dataclass(frozen=True, slots=True)
class PurposeAssessmentInput:
    """Signals used to assess whether a cognition state obeys doctrine."""

    statement: str
    wave_number: int
    confidence: float
    evidence_ids: tuple[str, ...]
    uncertainty: UncertaintyStatus
    uncertainty_disclosed: bool
    human_authority: HumanAuthority
    optimizes_for_winning_over_truth: bool = False
    presents_confidence_as_evidence: bool = False
    hides_uncertainty: bool = False
    private_agenda_detected: bool = False
    reward_chasing_detected: bool = False
    requests_agi_claim: bool = False
    overwhelming_independent_evidence: bool = False

    def __post_init__(self) -> None:
        """Validate assessment inputs before doctrine checks run."""

        if not self.statement.strip():
            raise ValueError("Purpose assessment inputs require a non-empty statement.")
        if self.wave_number < 0:
            raise ValueError("Purpose assessment wave_number cannot be negative.")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(
                "Purpose assessment confidence must be between 0.0 and 1.0."
            )
        if len(set(self.evidence_ids)) != len(self.evidence_ids):
            raise ValueError("Purpose assessment evidence_ids must be unique.")

    @property
    def statement_requests_forbidden_claim(self) -> bool:
        """Return whether the statement contains a pre-Wave-6 forbidden claim."""

        normalized = self.statement.casefold()
        return any(
            forbidden.casefold() in normalized
            for forbidden in FORBIDDEN_CLAIMS_BEFORE_WAVE_6
        )

    @property
    def has_evidence(self) -> bool:
        """Return whether the assessment has any evidence ids."""

        return bool(self.evidence_ids)


@dataclass(frozen=True, slots=True)
class PurposeCheckResult:
    """Result of one executable non-attached purpose rule check."""

    rule: PurposeRule
    status: PurposeCheckStatus
    reasons: tuple[str, ...]
    evidence_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        """Validate that check results are explainable."""

        if not self.reasons:
            raise ValueError("Purpose check results require reasons.")
        if any(not reason.strip() for reason in self.reasons):
            raise ValueError("Purpose check reasons cannot be empty.")
        if len(set(self.evidence_ids)) != len(self.evidence_ids):
            raise ValueError("Purpose check evidence_ids must be unique.")

    @property
    def is_violation(self) -> bool:
        """Return whether this check found a doctrine violation."""

        return self.status is PurposeCheckStatus.VIOLATED


@dataclass(frozen=True, slots=True)
class NonAttachedPurposeAssessment:
    """Complete non-attached purpose assessment for a cognition state."""

    assessment_input: PurposeAssessmentInput
    results: tuple[PurposeCheckResult, ...]

    def __post_init__(self) -> None:
        """Validate that each doctrine rule has exactly one result."""

        expected_rules = tuple(PurposeRule)
        actual_rules = tuple(result.rule for result in self.results)
        if actual_rules != expected_rules:
            raise ValueError("Non-attached purpose assessments must cover every rule.")

    @property
    def violations(self) -> tuple[PurposeCheckResult, ...]:
        """Return violated non-attached purpose checks."""

        return tuple(result for result in self.results if result.is_violation)

    @property
    def satisfied_results(self) -> tuple[PurposeCheckResult, ...]:
        """Return satisfied non-attached purpose checks."""

        return tuple(result for result in self.results if not result.is_violation)

    @property
    def passes(self) -> bool:
        """Return whether the assessment satisfies every doctrine check."""

        return not self.violations

    def result_for_rule(self, rule: PurposeRule) -> PurposeCheckResult:
        """Return a result by purpose rule."""

        for result in self.results:
            if result.rule is rule:
                return result
        raise ValueError(f"Unknown non-attached purpose rule: {rule.value}")


def assess_non_attached_purpose(
    assessment_input: PurposeAssessmentInput,
) -> NonAttachedPurposeAssessment:
    """Run all executable non-attached purpose checks."""

    results = (
        _check_truth_over_winning(assessment_input),
        _check_evidence_over_confidence(assessment_input),
        _check_uncertainty_over_theater(assessment_input),
        _check_no_private_agenda(assessment_input),
        _check_no_reward_chasing(assessment_input),
        _check_human_authority_preserved(assessment_input),
        _check_no_agi_claim_without_evidence(assessment_input),
    )
    return NonAttachedPurposeAssessment(
        assessment_input=assessment_input,
        results=results,
    )


def doctrine_rules_are_executable() -> bool:
    """Return whether the locked doctrine rules have executable counterparts."""

    return tuple(rule.value for rule in PurposeRule) == NON_ATTACHED_PURPOSE_RULES


def _check_truth_over_winning(
    assessment_input: PurposeAssessmentInput,
) -> PurposeCheckResult:
    if assessment_input.optimizes_for_winning_over_truth:
        return _violation(
            PurposeRule.TRUTH_OVER_WINNING,
            "The state optimizes for winning over truth.",
            assessment_input.evidence_ids,
        )
    return _satisfied(
        PurposeRule.TRUTH_OVER_WINNING,
        "No truth-subordinating objective was signaled.",
        assessment_input.evidence_ids,
    )


def _check_evidence_over_confidence(
    assessment_input: PurposeAssessmentInput,
) -> PurposeCheckResult:
    if assessment_input.presents_confidence_as_evidence:
        return _violation(
            PurposeRule.EVIDENCE_OVER_CONFIDENCE,
            "Confidence is being presented as evidence.",
            assessment_input.evidence_ids,
        )
    if assessment_input.confidence >= 0.7 and not assessment_input.has_evidence:
        return _violation(
            PurposeRule.EVIDENCE_OVER_CONFIDENCE,
            "High-confidence claims require evidence ids before purpose passes.",
            assessment_input.evidence_ids,
        )
    return _satisfied(
        PurposeRule.EVIDENCE_OVER_CONFIDENCE,
        "Confidence is separated from evidence.",
        assessment_input.evidence_ids,
    )


def _check_uncertainty_over_theater(
    assessment_input: PurposeAssessmentInput,
) -> PurposeCheckResult:
    if assessment_input.hides_uncertainty:
        return _violation(
            PurposeRule.UNCERTAINTY_OVER_THEATER,
            "The state hides uncertainty instead of exposing it.",
            assessment_input.evidence_ids,
        )
    if not assessment_input.uncertainty_disclosed:
        return _violation(
            PurposeRule.UNCERTAINTY_OVER_THEATER,
            "The state does not disclose its uncertainty status.",
            assessment_input.evidence_ids,
        )
    if assessment_input.uncertainty is UncertaintyStatus.UNSAFE_TO_ACT:
        return _violation(
            PurposeRule.UNCERTAINTY_OVER_THEATER,
            "Unsafe-to-act uncertainty cannot pass as performance.",
            assessment_input.evidence_ids,
        )
    return _satisfied(
        PurposeRule.UNCERTAINTY_OVER_THEATER,
        "Uncertainty is disclosed and not hidden for performance theater.",
        assessment_input.evidence_ids,
    )


def _check_no_private_agenda(
    assessment_input: PurposeAssessmentInput,
) -> PurposeCheckResult:
    if assessment_input.private_agenda_detected:
        return _violation(
            PurposeRule.NO_PRIVATE_AGENDA,
            "A private agenda signal was detected.",
            assessment_input.evidence_ids,
        )
    return _satisfied(
        PurposeRule.NO_PRIVATE_AGENDA,
        "No private agenda signal was detected.",
        assessment_input.evidence_ids,
    )


def _check_no_reward_chasing(
    assessment_input: PurposeAssessmentInput,
) -> PurposeCheckResult:
    if assessment_input.reward_chasing_detected:
        return _violation(
            PurposeRule.NO_REWARD_CHASING,
            "A runtime reward-chasing purpose signal was detected.",
            assessment_input.evidence_ids,
        )
    return _satisfied(
        PurposeRule.NO_REWARD_CHASING,
        "No runtime reward-chasing purpose signal was detected.",
        assessment_input.evidence_ids,
    )


def _check_human_authority_preserved(
    assessment_input: PurposeAssessmentInput,
) -> PurposeCheckResult:
    if assessment_input.human_authority is HumanAuthority.ABSENT:
        return _violation(
            PurposeRule.HUMAN_AUTHORITY_PRESERVED,
            "Human authority is absent from the cognition state.",
            assessment_input.evidence_ids,
        )
    return _satisfied(
        PurposeRule.HUMAN_AUTHORITY_PRESERVED,
        "Human authority remains explicit and preserved.",
        assessment_input.evidence_ids,
    )


def _check_no_agi_claim_without_evidence(
    assessment_input: PurposeAssessmentInput,
) -> PurposeCheckResult:
    requested_agi_claim = (
        assessment_input.requests_agi_claim
        or assessment_input.statement_requests_forbidden_claim
    )
    if not requested_agi_claim:
        return _satisfied(
            PurposeRule.NO_AGI_CLAIM_WITHOUT_EVIDENCE,
            "No AGI claim is requested by this state.",
            assessment_input.evidence_ids,
        )
    if allows_agi_claim(
        assessment_input.wave_number,
        overwhelming_evidence=assessment_input.overwhelming_independent_evidence,
    ):
        return _satisfied(
            PurposeRule.NO_AGI_CLAIM_WITHOUT_EVIDENCE,
            (
                "AGI claim gate is satisfied only because Wave 6 and overwhelming "
                "evidence are present."
            ),
            assessment_input.evidence_ids,
        )
    return _violation(
        PurposeRule.NO_AGI_CLAIM_WITHOUT_EVIDENCE,
        (
            "AGI or forbidden capability claims require Wave 6 and overwhelming "
            "independent evidence."
        ),
        assessment_input.evidence_ids,
    )


def _satisfied(
    rule: PurposeRule,
    reason: str,
    evidence_ids: tuple[str, ...],
) -> PurposeCheckResult:
    return PurposeCheckResult(
        rule=rule,
        status=PurposeCheckStatus.SATISFIED,
        reasons=(reason,),
        evidence_ids=evidence_ids,
    )


def _violation(
    rule: PurposeRule,
    reason: str,
    evidence_ids: tuple[str, ...],
) -> PurposeCheckResult:
    return PurposeCheckResult(
        rule=rule,
        status=PurposeCheckStatus.VIOLATED,
        reasons=(reason,),
        evidence_ids=evidence_ids,
    )
