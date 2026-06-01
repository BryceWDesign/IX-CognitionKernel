"""Causal assumption records for IX-CognitionKernel Wave 1 preparation.

This module represents causal structure only. It does not prove reality, execute
plans, update durable memory, or authorize action. Wave 1 needs the kernel to
hold causal assumptions, constraints, expected observations, and counterfactual
notes as structured state before later waves add learning and world-model tests.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from enum import StrEnum

from ix_cognition_kernel.state import UncertaintyStatus


class CausalRelation(StrEnum):
    """Relationship asserted between a cause belief and an effect belief."""

    ENABLES = "enables"
    INHIBITS = "inhibits"
    REQUIRES = "requires"
    RISKS = "risks"
    CONSTRAINS = "constrains"


class ConstraintSeverity(StrEnum):
    """Governance severity for a causal constraint."""

    CONTEXT = "context"
    WARNING = "warning"
    BLOCKING = "blocking"
    HARD_LIMIT = "hard-limit"


@dataclass(frozen=True, slots=True)
class CausalConstraint:
    """A constraint that bounds how a causal assumption may be interpreted."""

    constraint_id: str
    description: str
    severity: ConstraintSeverity
    source_belief_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        """Validate causal constraint identity and evidence linkage."""

        if not self.constraint_id.strip():
            raise ValueError("Causal constraints require a non-empty constraint_id.")
        if not self.description.strip():
            raise ValueError("Causal constraints require a non-empty description.")
        if (
            self.severity
            in {
                ConstraintSeverity.BLOCKING,
                ConstraintSeverity.HARD_LIMIT,
            }
            and not self.source_belief_ids
        ):
            raise ValueError("Blocking causal constraints require source belief ids.")

    @property
    def blocks_actionability(self) -> bool:
        """Return whether the constraint blocks actionability."""

        return self.severity in {
            ConstraintSeverity.BLOCKING,
            ConstraintSeverity.HARD_LIMIT,
        }


@dataclass(frozen=True, slots=True)
class ExpectedObservation:
    """An observation expected if a causal assumption is useful."""

    observation_id: str
    description: str
    linked_evidence_ids: tuple[str, ...]
    required_for_validation: bool

    def __post_init__(self) -> None:
        """Validate expected observation identity and description."""

        if not self.observation_id.strip():
            raise ValueError(
                "Expected observations require a non-empty observation_id."
            )
        if not self.description.strip():
            raise ValueError("Expected observations require a non-empty description.")

    @property
    def is_observed(self) -> bool:
        """Return whether this observation has any linked evidence."""

        return bool(self.linked_evidence_ids)

    @property
    def still_needed(self) -> bool:
        """Return whether validation still needs this observation."""

        return self.required_for_validation and not self.is_observed


@dataclass(frozen=True, slots=True)
class CounterfactualNote:
    """A bounded counterfactual note attached to causal reasoning."""

    note_id: str
    scenario: str
    expected_difference: str
    uncertainty: UncertaintyStatus

    def __post_init__(self) -> None:
        """Validate counterfactual identity, scenario, and expected difference."""

        if not self.note_id.strip():
            raise ValueError("Counterfactual notes require a non-empty note_id.")
        if not self.scenario.strip():
            raise ValueError("Counterfactual notes require a non-empty scenario.")
        if not self.expected_difference.strip():
            raise ValueError(
                "Counterfactual notes require a non-empty expected_difference."
            )

    @property
    def is_safe_to_use_for_planning(self) -> bool:
        """Return whether the counterfactual can inform planning."""

        return self.uncertainty not in {
            UncertaintyStatus.DISPUTED,
            UncertaintyStatus.STALE,
            UncertaintyStatus.UNSAFE_TO_ACT,
        }


@dataclass(frozen=True, slots=True)
class CausalAssumption:
    """A causal assumption connecting two belief records by id."""

    assumption_id: str
    cause_belief_id: str
    effect_belief_id: str
    relation: CausalRelation
    rationale: str
    confidence: float
    uncertainty: UncertaintyStatus
    evidence_ids: tuple[str, ...]
    constraint_ids: tuple[str, ...]
    expected_observation_ids: tuple[str, ...]
    counterfactual_note_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        """Validate causal assumption identity, linkage, and confidence bounds."""

        if not self.assumption_id.strip():
            raise ValueError("Causal assumptions require a non-empty assumption_id.")
        if not self.cause_belief_id.strip():
            raise ValueError("Causal assumptions require a non-empty cause_belief_id.")
        if not self.effect_belief_id.strip():
            raise ValueError("Causal assumptions require a non-empty effect_belief_id.")
        if self.cause_belief_id == self.effect_belief_id:
            raise ValueError(
                "Causal assumptions require distinct cause and effect ids."
            )
        if not self.rationale.strip():
            raise ValueError("Causal assumptions require a non-empty rationale.")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(
                "Causal assumption confidence must be between 0.0 and 1.0."
            )

    @property
    def has_blocking_uncertainty(self) -> bool:
        """Return whether the assumption is blocked by uncertainty."""

        return self.uncertainty in {
            UncertaintyStatus.DISPUTED,
            UncertaintyStatus.STALE,
            UncertaintyStatus.UNSAFE_TO_ACT,
        }

    @property
    def needs_evidence(self) -> bool:
        """Return whether the assumption lacks enough evidence to be testable."""

        return (
            self.uncertainty
            in {
                UncertaintyStatus.UNKNOWN,
                UncertaintyStatus.ASSUMED,
            }
            or not self.evidence_ids
        )


@dataclass(frozen=True, slots=True)
class SimpleCausalModel:
    """Wave 1 container for causal assumptions and related model records."""

    model_id: str
    assumptions: tuple[CausalAssumption, ...]
    constraints: tuple[CausalConstraint, ...]
    expected_observations: tuple[ExpectedObservation, ...]
    counterfactuals: tuple[CounterfactualNote, ...]

    def __post_init__(self) -> None:
        """Validate model identity, uniqueness, and internal references."""

        if not self.model_id.strip():
            raise ValueError("Simple causal models require a non-empty model_id.")

        assumption_ids = _unique_ids(
            (assumption.assumption_id for assumption in self.assumptions),
            label="assumption_id",
        )
        constraint_ids = _unique_ids(
            (constraint.constraint_id for constraint in self.constraints),
            label="constraint_id",
        )
        observation_ids = _unique_ids(
            (observation.observation_id for observation in self.expected_observations),
            label="observation_id",
        )
        counterfactual_ids = _unique_ids(
            (counterfactual.note_id for counterfactual in self.counterfactuals),
            label="counterfactual note_id",
        )

        for assumption in self.assumptions:
            _validate_reference_subset(
                assumption.constraint_ids,
                constraint_ids,
                owner=assumption.assumption_id,
                label="constraint_id",
            )
            _validate_reference_subset(
                assumption.expected_observation_ids,
                observation_ids,
                owner=assumption.assumption_id,
                label="observation_id",
            )
            _validate_reference_subset(
                assumption.counterfactual_note_ids,
                counterfactual_ids,
                owner=assumption.assumption_id,
                label="counterfactual note_id",
            )
        _ = assumption_ids

    @property
    def assumptions_requiring_evidence(self) -> tuple[CausalAssumption, ...]:
        """Return assumptions that still need evidence before testing."""

        return tuple(
            assumption for assumption in self.assumptions if assumption.needs_evidence
        )

    @property
    def blocked_assumptions(self) -> tuple[CausalAssumption, ...]:
        """Return assumptions blocked by uncertainty or blocking constraints."""

        blocking_constraint_ids = {
            constraint.constraint_id
            for constraint in self.constraints
            if constraint.blocks_actionability
        }
        return tuple(
            assumption
            for assumption in self.assumptions
            if assumption.has_blocking_uncertainty
            or bool(blocking_constraint_ids.intersection(assumption.constraint_ids))
        )

    @property
    def testable_assumptions(self) -> tuple[CausalAssumption, ...]:
        """Return assumptions with evidence and no blocking uncertainty/constraints."""

        blocked = set(self.blocked_assumptions)
        return tuple(
            assumption
            for assumption in self.assumptions
            if assumption not in blocked and not assumption.needs_evidence
        )

    @property
    def observations_still_needed(self) -> tuple[ExpectedObservation, ...]:
        """Return required observations that have not yet been observed."""

        return tuple(
            observation
            for observation in self.expected_observations
            if observation.still_needed
        )

    def assumption_by_id(self, assumption_id: str) -> CausalAssumption:
        """Return a causal assumption by id."""

        for assumption in self.assumptions:
            if assumption.assumption_id == assumption_id:
                return assumption
        raise ValueError(f"Unknown causal assumption_id: {assumption_id}")


def _unique_ids(values: Iterable[str], *, label: str) -> set[str]:
    """Return unique ids while rejecting duplicates."""

    seen: set[str] = set()
    for value in values:
        if value in seen:
            raise ValueError(f"Duplicate {label} detected: {value}")
        seen.add(value)
    return seen


def _validate_reference_subset(
    referenced_ids: tuple[str, ...],
    known_ids: set[str],
    *,
    owner: str,
    label: str,
) -> None:
    """Reject references that are not present inside a causal model."""

    missing = tuple(
        reference_id for reference_id in referenced_ids if reference_id not in known_ids
    )
    if missing:
        raise ValueError(f"{owner} references unknown {label}: {missing[0]}")
