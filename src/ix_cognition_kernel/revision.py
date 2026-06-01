"""Causal assumption revision engine for IX-CognitionKernel Wave 2.

This module consumes prediction-comparison records and produces revised causal
assumptions with auditable revision records. It does not mutate the original
causal model, execute plans, or claim that a causal assumption is true. It only
lets matched, diverged, inconclusive, and blocked comparison evidence pressure a
represented causal assumption in a deterministic, fail-closed way.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from enum import StrEnum

from ix_cognition_kernel.causal import CausalAssumption, SimpleCausalModel
from ix_cognition_kernel.observations import (
    PredictionComparisonLedger,
    PredictionComparisonRecord,
    PredictionComparisonResult,
)
from ix_cognition_kernel.state import UncertaintyStatus


class CausalRevisionAction(StrEnum):
    """Action produced by causal assumption revision."""

    UNCHANGED = "unchanged"
    STRENGTHENED = "strengthened"
    WEAKENED = "weakened"
    DISPUTED = "disputed"
    BLOCKED = "blocked"
    RETIRED = "retired"


@dataclass(frozen=True, slots=True)
class CausalRevisionPolicy:
    """Deterministic weights and thresholds for causal revision."""

    matched_weight: float = 0.15
    diverged_weight: float = 0.25
    dispute_threshold: float = 0.45
    block_threshold: float = 0.25
    retire_threshold: float = 0.1
    known_threshold: float = 0.65

    def __post_init__(self) -> None:
        """Validate revision weights and thresholds."""

        for field_name, value in (
            ("matched_weight", self.matched_weight),
            ("diverged_weight", self.diverged_weight),
            ("dispute_threshold", self.dispute_threshold),
            ("block_threshold", self.block_threshold),
            ("retire_threshold", self.retire_threshold),
            ("known_threshold", self.known_threshold),
        ):
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{field_name} must be between 0.0 and 1.0.")
        if not self.retire_threshold <= self.block_threshold <= self.dispute_threshold:
            raise ValueError(
                "Causal revision thresholds must be ordered from retire to dispute."
            )


@dataclass(frozen=True, slots=True)
class CausalRevisionRecord:
    """Audit record for one revised causal assumption."""

    revision_id: str
    assumption_id: str
    action: CausalRevisionAction
    comparison_ids: tuple[str, ...]
    before_confidence: float
    after_confidence: float
    before_uncertainty: UncertaintyStatus
    after_uncertainty: UncertaintyStatus
    evidence_ids: tuple[str, ...]
    reasons: tuple[str, ...]

    def __post_init__(self) -> None:
        """Validate revision identity, comparison linkage, and reasons."""

        if not self.revision_id.strip():
            raise ValueError("Causal revision records require a non-empty revision_id.")
        if not self.assumption_id.strip():
            raise ValueError(
                "Causal revision records require a non-empty assumption_id."
            )
        if not self.comparison_ids:
            raise ValueError("Causal revision records require comparison_ids.")
        _unique_ids(self.comparison_ids, label="causal revision comparison_id")
        _unique_ids(self.evidence_ids, label="causal revision evidence_id")
        for field_name, value in (
            ("before_confidence", self.before_confidence),
            ("after_confidence", self.after_confidence),
        ):
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{field_name} must be between 0.0 and 1.0.")
        if not self.reasons:
            raise ValueError("Causal revision records require reasons.")
        if any(not reason.strip() for reason in self.reasons):
            raise ValueError("Causal revision reasons cannot be empty.")

    @property
    def changed_confidence(self) -> bool:
        """Return whether this revision changed confidence."""

        return self.before_confidence != self.after_confidence

    @property
    def changed_uncertainty(self) -> bool:
        """Return whether this revision changed uncertainty."""

        return self.before_uncertainty is not self.after_uncertainty

    @property
    def blocks_assumption(self) -> bool:
        """Return whether this revision blocks the causal assumption."""

        return self.action in {
            CausalRevisionAction.DISPUTED,
            CausalRevisionAction.BLOCKED,
            CausalRevisionAction.RETIRED,
        }


@dataclass(frozen=True, slots=True)
class CausalRevisionResult:
    """Result of revising a causal model from prediction comparisons."""

    before_model: SimpleCausalModel
    after_model: SimpleCausalModel
    comparison_ledger: PredictionComparisonLedger
    revisions: tuple[CausalRevisionRecord, ...]

    @property
    def changed_assumption_ids(self) -> tuple[str, ...]:
        """Return assumption ids changed by revision."""

        return tuple(revision.assumption_id for revision in self.revisions)

    @property
    def strengthened_revisions(self) -> tuple[CausalRevisionRecord, ...]:
        """Return revisions that strengthened causal assumptions."""

        return tuple(
            revision
            for revision in self.revisions
            if revision.action is CausalRevisionAction.STRENGTHENED
        )

    @property
    def weakened_revisions(self) -> tuple[CausalRevisionRecord, ...]:
        """Return revisions that weakened causal assumptions."""

        return tuple(
            revision
            for revision in self.revisions
            if revision.action is CausalRevisionAction.WEAKENED
        )

    @property
    def blocking_revisions(self) -> tuple[CausalRevisionRecord, ...]:
        """Return revisions that block causal assumptions."""

        return tuple(
            revision for revision in self.revisions if revision.blocks_assumption
        )


DEFAULT_CAUSAL_REVISION_POLICY = CausalRevisionPolicy()


def revise_causal_assumptions(
    causal_model: SimpleCausalModel,
    comparison_ledger: PredictionComparisonLedger,
    *,
    policy: CausalRevisionPolicy = DEFAULT_CAUSAL_REVISION_POLICY,
) -> CausalRevisionResult:
    """Revise causal assumptions from prediction comparison records.

    The original causal model is not mutated. Unknown source_assumption_id values
    fail closed instead of being ignored.
    """

    _reject_unknown_assumption_references(causal_model, comparison_ledger)

    revised_assumptions: list[CausalAssumption] = []
    revisions: list[CausalRevisionRecord] = []
    for assumption in causal_model.assumptions:
        comparisons = _comparisons_for_assumption(
            comparison_ledger,
            assumption.assumption_id,
        )
        if not comparisons:
            revised_assumptions.append(assumption)
            continue
        revised_assumption, revision = _revise_assumption(
            assumption,
            comparisons,
            policy,
            revision_index=len(revisions),
        )
        revised_assumptions.append(revised_assumption)
        if revision.action is not CausalRevisionAction.UNCHANGED:
            revisions.append(revision)

    return CausalRevisionResult(
        before_model=causal_model,
        after_model=SimpleCausalModel(
            model_id=causal_model.model_id,
            assumptions=tuple(revised_assumptions),
            constraints=causal_model.constraints,
            expected_observations=causal_model.expected_observations,
            counterfactuals=causal_model.counterfactuals,
        ),
        comparison_ledger=comparison_ledger,
        revisions=tuple(revisions),
    )


def _revise_assumption(
    assumption: CausalAssumption,
    comparisons: tuple[PredictionComparisonRecord, ...],
    policy: CausalRevisionPolicy,
    *,
    revision_index: int,
) -> tuple[CausalAssumption, CausalRevisionRecord]:
    """Revise one causal assumption from its comparison records."""

    after_confidence = assumption.confidence
    evidence_ids = list(assumption.evidence_ids)
    reasons: list[str] = []
    blocked_seen = False
    diverged_seen = False
    matched_seen = False

    for comparison in comparisons:
        evidence_ids = _append_unique(evidence_ids, comparison.evidence_ids)
        if comparison.result is PredictionComparisonResult.MATCHED:
            matched_seen = True
            after_confidence = _clamp_confidence(
                after_confidence
                + _comparison_weight(comparison) * policy.matched_weight
            )
            reasons.append(f"{comparison.comparison_id} matched the prediction.")
        elif comparison.result is PredictionComparisonResult.DIVERGED:
            diverged_seen = True
            after_confidence = _clamp_confidence(
                after_confidence
                - _comparison_weight(comparison) * policy.diverged_weight
            )
            reasons.append(f"{comparison.comparison_id} diverged from the prediction.")
        elif comparison.result is PredictionComparisonResult.BLOCKED:
            blocked_seen = True
            reasons.append(f"{comparison.comparison_id} blocked causal revision.")
        elif comparison.result is PredictionComparisonResult.INCONCLUSIVE:
            reasons.append(f"{comparison.comparison_id} was inconclusive.")

    after_uncertainty = _revised_uncertainty(
        assumption,
        after_confidence=after_confidence,
        blocked_seen=blocked_seen,
        diverged_seen=diverged_seen,
        policy=policy,
    )
    action = _revision_action(
        assumption,
        after_confidence=after_confidence,
        after_uncertainty=after_uncertainty,
        blocked_seen=blocked_seen,
        diverged_seen=diverged_seen,
        matched_seen=matched_seen,
        policy=policy,
    )
    revised_assumption = CausalAssumption(
        assumption_id=assumption.assumption_id,
        cause_belief_id=assumption.cause_belief_id,
        effect_belief_id=assumption.effect_belief_id,
        relation=assumption.relation,
        rationale=assumption.rationale,
        confidence=after_confidence,
        uncertainty=after_uncertainty,
        evidence_ids=tuple(evidence_ids),
        constraint_ids=assumption.constraint_ids,
        expected_observation_ids=assumption.expected_observation_ids,
        counterfactual_note_ids=assumption.counterfactual_note_ids,
    )
    revision = CausalRevisionRecord(
        revision_id=f"causal-revision-{revision_index:03d}",
        assumption_id=assumption.assumption_id,
        action=action,
        comparison_ids=tuple(comparison.comparison_id for comparison in comparisons),
        before_confidence=assumption.confidence,
        after_confidence=after_confidence,
        before_uncertainty=assumption.uncertainty,
        after_uncertainty=after_uncertainty,
        evidence_ids=tuple(evidence_ids),
        reasons=tuple(reasons),
    )
    return revised_assumption, revision


def _revised_uncertainty(
    assumption: CausalAssumption,
    *,
    after_confidence: float,
    blocked_seen: bool,
    diverged_seen: bool,
    policy: CausalRevisionPolicy,
) -> UncertaintyStatus:
    """Compute revised causal-assumption uncertainty."""

    if blocked_seen:
        return UncertaintyStatus.UNSAFE_TO_ACT
    if after_confidence <= policy.dispute_threshold and diverged_seen:
        return UncertaintyStatus.DISPUTED
    if after_confidence >= policy.known_threshold and not assumption.needs_evidence:
        return UncertaintyStatus.KNOWN
    if assumption.uncertainty in {
        UncertaintyStatus.UNKNOWN,
        UncertaintyStatus.ASSUMED,
    }:
        return UncertaintyStatus.ASSUMED
    return assumption.uncertainty


def _revision_action(
    assumption: CausalAssumption,
    *,
    after_confidence: float,
    after_uncertainty: UncertaintyStatus,
    blocked_seen: bool,
    diverged_seen: bool,
    matched_seen: bool,
    policy: CausalRevisionPolicy,
) -> CausalRevisionAction:
    """Classify causal revision action."""

    if blocked_seen:
        return CausalRevisionAction.BLOCKED
    if diverged_seen and after_confidence <= policy.retire_threshold:
        return CausalRevisionAction.RETIRED
    if diverged_seen and after_confidence <= policy.block_threshold:
        return CausalRevisionAction.BLOCKED
    if after_uncertainty is UncertaintyStatus.DISPUTED:
        return CausalRevisionAction.DISPUTED
    if after_confidence < assumption.confidence:
        return CausalRevisionAction.WEAKENED
    if matched_seen and after_confidence > assumption.confidence:
        return CausalRevisionAction.STRENGTHENED
    return CausalRevisionAction.UNCHANGED


def _comparison_weight(comparison: PredictionComparisonRecord) -> float:
    """Return deterministic comparison weight from observation confidence."""

    if comparison.observation_confidence is None:
        return 0.0
    return comparison.observation_confidence


def _reject_unknown_assumption_references(
    causal_model: SimpleCausalModel,
    comparison_ledger: PredictionComparisonLedger,
) -> None:
    """Reject comparison records for assumptions outside the causal model."""

    assumption_ids = {
        assumption.assumption_id for assumption in causal_model.assumptions
    }
    for comparison in comparison_ledger.comparisons:
        if comparison.source_assumption_id not in assumption_ids:
            raise ValueError(
                f"Comparison {comparison.comparison_id} references unknown "
                f"source_assumption_id: {comparison.source_assumption_id}"
            )


def _comparisons_for_assumption(
    comparison_ledger: PredictionComparisonLedger,
    assumption_id: str,
) -> tuple[PredictionComparisonRecord, ...]:
    """Return comparisons for one source assumption id."""

    return tuple(
        comparison
        for comparison in comparison_ledger.comparisons
        if comparison.source_assumption_id == assumption_id
    )


def _clamp_confidence(value: float) -> float:
    """Clamp confidence into the accepted range with deterministic rounding."""

    return round(min(1.0, max(0.0, value)), 6)


def _append_unique(values: list[str], additions: tuple[str, ...]) -> list[str]:
    """Append unique values while preserving existing order."""

    updated = list(values)
    for value in additions:
        if value not in updated:
            updated.append(value)
    return updated


def _unique_ids(values: Iterable[str], *, label: str) -> set[str]:
    """Return unique ids while rejecting duplicates and blank values."""

    seen: set[str] = set()
    for value in values:
        if not value.strip():
            raise ValueError(f"{label} values cannot be empty.")
        if value in seen:
            raise ValueError(f"Duplicate {label} detected: {value}")
        seen.add(value)
    return seen
