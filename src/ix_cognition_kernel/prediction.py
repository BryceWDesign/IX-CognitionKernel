"""Causal prediction records for IX-CognitionKernel Wave 2.

Wave 2 needs causal assumptions to become testable predictions. This module
turns a represented causal assumption into explicit prediction artifacts with an
expected observation, expected direction, confidence, and evaluation criteria.
It does not compare observations yet and does not revise causal assumptions.
Those steps belong to later Wave 2 commits.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from enum import StrEnum

from ix_cognition_kernel.causal import CausalAssumption, SimpleCausalModel
from ix_cognition_kernel.state import UncertaintyStatus


class PredictionDirection(StrEnum):
    """Expected direction or presence of a future observation."""

    INCREASE = "increase"
    DECREASE = "decrease"
    PRESENT = "present"
    ABSENT = "absent"
    STABLE = "stable"


class PredictionStatus(StrEnum):
    """Readiness status for a causal prediction artifact."""

    TESTABLE = "testable"
    NEEDS_EVIDENCE = "needs-evidence"
    BLOCKED = "blocked"


@dataclass(frozen=True, slots=True)
class PredictionCriterion:
    """Criterion used later to compare a prediction against an observation."""

    criterion_id: str
    description: str
    expected_observation_id: str
    expected_direction: PredictionDirection
    required: bool = True

    def __post_init__(self) -> None:
        """Validate prediction-criterion identity and observation linkage."""

        if not self.criterion_id.strip():
            raise ValueError("Prediction criteria require a non-empty criterion_id.")
        if not self.description.strip():
            raise ValueError("Prediction criteria require a non-empty description.")
        if not self.expected_observation_id.strip():
            raise ValueError(
                "Prediction criteria require a non-empty expected_observation_id."
            )


@dataclass(frozen=True, slots=True)
class CausalPrediction:
    """Testable prediction derived from one causal assumption."""

    prediction_id: str
    source_assumption_id: str
    statement: str
    expected_observation_id: str
    expected_direction: PredictionDirection
    confidence: float
    uncertainty: UncertaintyStatus
    status: PredictionStatus
    evaluation_criteria: tuple[PredictionCriterion, ...]
    evidence_ids: tuple[str, ...]
    source_belief_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        """Validate prediction identity, linkage, confidence, and criteria."""

        if not self.prediction_id.strip():
            raise ValueError("Causal predictions require a non-empty prediction_id.")
        if not self.source_assumption_id.strip():
            raise ValueError(
                "Causal predictions require a non-empty source_assumption_id."
            )
        if not self.statement.strip():
            raise ValueError("Causal predictions require a non-empty statement.")
        if not self.expected_observation_id.strip():
            raise ValueError(
                "Causal predictions require a non-empty expected_observation_id."
            )
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(
                "Causal prediction confidence must be between 0.0 and 1.0."
            )
        if not self.evaluation_criteria:
            raise ValueError("Causal predictions require evaluation criteria.")
        _unique_ids(
            (criterion.criterion_id for criterion in self.evaluation_criteria),
            label="prediction criterion_id",
        )
        _unique_ids(self.evidence_ids, label="prediction evidence_id")
        _unique_ids(self.source_belief_ids, label="prediction source_belief_id")
        if self.status is PredictionStatus.TESTABLE:
            self._validate_testable_prediction()

    @property
    def required_criteria(self) -> tuple[PredictionCriterion, ...]:
        """Return criteria required for later observation comparison."""

        return tuple(
            criterion for criterion in self.evaluation_criteria if criterion.required
        )

    @property
    def is_testable(self) -> bool:
        """Return whether the prediction is ready for later observation comparison."""

        return self.status is PredictionStatus.TESTABLE

    @property
    def is_blocked(self) -> bool:
        """Return whether the prediction is blocked by causal uncertainty."""

        return self.status is PredictionStatus.BLOCKED

    def _validate_testable_prediction(self) -> None:
        """Validate stricter requirements for testable predictions."""

        if self.uncertainty in {
            UncertaintyStatus.DISPUTED,
            UncertaintyStatus.STALE,
            UncertaintyStatus.UNSAFE_TO_ACT,
        }:
            raise ValueError(
                "Testable predictions cannot contain blocking uncertainty."
            )
        if not self.evidence_ids:
            raise ValueError("Testable predictions require evidence ids.")
        if not self.source_belief_ids:
            raise ValueError("Testable predictions require source belief ids.")
        if not self.required_criteria:
            raise ValueError("Testable predictions require required criteria.")
        for criterion in self.required_criteria:
            if criterion.expected_observation_id != self.expected_observation_id:
                raise ValueError(
                    "Required prediction criteria must target the prediction's "
                    "expected_observation_id."
                )
            if criterion.expected_direction is not self.expected_direction:
                raise ValueError(
                    "Required prediction criteria must match the prediction's "
                    "expected_direction."
                )


@dataclass(frozen=True, slots=True)
class CausalPredictionSet:
    """Container for causal predictions produced from a causal model."""

    prediction_set_id: str
    source_model_id: str
    predictions: tuple[CausalPrediction, ...]

    def __post_init__(self) -> None:
        """Validate prediction set identity and duplicate prediction ids."""

        if not self.prediction_set_id.strip():
            raise ValueError("Prediction sets require a non-empty prediction_set_id.")
        if not self.source_model_id.strip():
            raise ValueError("Prediction sets require a non-empty source_model_id.")
        _unique_ids(
            (prediction.prediction_id for prediction in self.predictions),
            label="prediction_id",
        )

    @property
    def testable_predictions(self) -> tuple[CausalPrediction, ...]:
        """Return predictions ready for observation comparison."""

        return tuple(
            prediction for prediction in self.predictions if prediction.is_testable
        )

    @property
    def blocked_predictions(self) -> tuple[CausalPrediction, ...]:
        """Return predictions blocked by unsafe or disputed causal state."""

        return tuple(
            prediction for prediction in self.predictions if prediction.is_blocked
        )

    @property
    def predictions_requiring_evidence(self) -> tuple[CausalPrediction, ...]:
        """Return predictions that need more evidence before comparison."""

        return tuple(
            prediction
            for prediction in self.predictions
            if prediction.status is PredictionStatus.NEEDS_EVIDENCE
        )

    def prediction_by_id(self, prediction_id: str) -> CausalPrediction:
        """Return a prediction by id."""

        for prediction in self.predictions:
            if prediction.prediction_id == prediction_id:
                return prediction
        raise ValueError(f"Unknown causal prediction_id: {prediction_id}")

    def predictions_for_assumption(
        self,
        assumption_id: str,
    ) -> tuple[CausalPrediction, ...]:
        """Return predictions derived from one causal assumption."""

        return tuple(
            prediction
            for prediction in self.predictions
            if prediction.source_assumption_id == assumption_id
        )


def prediction_from_causal_assumption(
    *,
    prediction_id: str,
    assumption: CausalAssumption,
    expected_observation_id: str,
    expected_direction: PredictionDirection,
    criteria: tuple[PredictionCriterion, ...],
    statement: str | None = None,
) -> CausalPrediction:
    """Create a causal prediction from a represented causal assumption."""

    status = _prediction_status_for_assumption(assumption)
    prediction_statement = statement or (
        f"If {assumption.cause_belief_id} remains true, then "
        f"{expected_observation_id} should be {expected_direction.value}."
    )
    return CausalPrediction(
        prediction_id=prediction_id,
        source_assumption_id=assumption.assumption_id,
        statement=prediction_statement,
        expected_observation_id=expected_observation_id,
        expected_direction=expected_direction,
        confidence=assumption.confidence,
        uncertainty=assumption.uncertainty,
        status=status,
        evaluation_criteria=criteria,
        evidence_ids=assumption.evidence_ids,
        source_belief_ids=(assumption.cause_belief_id, assumption.effect_belief_id),
    )


def prediction_set_from_causal_model(
    *,
    prediction_set_id: str,
    causal_model: SimpleCausalModel,
) -> CausalPredictionSet:
    """Create one prediction per causal assumption and expected observation link."""

    predictions: list[CausalPrediction] = []
    observations_by_id = {
        observation.observation_id: observation
        for observation in causal_model.expected_observations
    }
    for assumption in causal_model.assumptions:
        for expected_observation_id in assumption.expected_observation_ids:
            if expected_observation_id not in observations_by_id:
                raise ValueError(
                    f"{assumption.assumption_id} references unknown "
                    f"expected_observation_id: {expected_observation_id}"
                )
            prediction_index = len(predictions)
            criterion = PredictionCriterion(
                criterion_id=f"criterion-{prediction_index:03d}",
                description=(
                    "Later observation comparison must check the expected "
                    "observation direction."
                ),
                expected_observation_id=expected_observation_id,
                expected_direction=PredictionDirection.PRESENT,
            )
            predictions.append(
                prediction_from_causal_assumption(
                    prediction_id=f"prediction-{prediction_index:03d}",
                    assumption=assumption,
                    expected_observation_id=expected_observation_id,
                    expected_direction=PredictionDirection.PRESENT,
                    criteria=(criterion,),
                )
            )
    return CausalPredictionSet(
        prediction_set_id=prediction_set_id,
        source_model_id=causal_model.model_id,
        predictions=tuple(predictions),
    )


def _prediction_status_for_assumption(
    assumption: CausalAssumption,
) -> PredictionStatus:
    """Return prediction readiness from causal-assumption state."""

    if assumption.has_blocking_uncertainty:
        return PredictionStatus.BLOCKED
    if assumption.needs_evidence:
        return PredictionStatus.NEEDS_EVIDENCE
    return PredictionStatus.TESTABLE


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
