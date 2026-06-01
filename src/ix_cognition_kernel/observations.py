"""Observation records and prediction comparison for IX-CognitionKernel Wave 2.

Wave 2 needs causal predictions to be pressure-tested against observations. This
module records observations and compares them with prediction artifacts to
produce matched, diverged, inconclusive, or blocked comparison records. It does
not revise causal assumptions; revision belongs to the next Wave 2 commit.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from enum import StrEnum

from ix_cognition_kernel.prediction import (
    CausalPrediction,
    CausalPredictionSet,
    PredictionDirection,
)


class ObservationStatus(StrEnum):
    """Observed state for a prediction target."""

    OBSERVED = "observed"
    MISSING = "missing"
    INCONCLUSIVE = "inconclusive"
    BLOCKED = "blocked"


class PredictionComparisonResult(StrEnum):
    """Result of comparing a prediction against an observation."""

    MATCHED = "matched"
    DIVERGED = "diverged"
    INCONCLUSIVE = "inconclusive"
    BLOCKED = "blocked"


@dataclass(frozen=True, slots=True)
class ObservationRecord:
    """Observation record used to compare against a causal prediction."""

    observation_id: str
    description: str
    status: ObservationStatus
    observed_direction: PredictionDirection | None
    confidence: float
    evidence_ids: tuple[str, ...]
    audit_index: int
    source: str
    provenance: tuple[str, ...]
    reasons: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        """Validate observation identity, evidence, confidence, and status rules."""

        if not self.observation_id.strip():
            raise ValueError("Observation records require a non-empty observation_id.")
        if not self.description.strip():
            raise ValueError("Observation records require a non-empty description.")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("Observation confidence must be between 0.0 and 1.0.")
        if self.audit_index < 0:
            raise ValueError("Observation audit_index cannot be negative.")
        if not self.source.strip():
            raise ValueError("Observation records require a non-empty source.")
        if not self.provenance:
            raise ValueError("Observation records require provenance.")
        if any(not entry.strip() for entry in self.provenance):
            raise ValueError("Observation provenance entries cannot be empty.")
        _unique_ids(self.evidence_ids, label="observation evidence_id")
        if self.status is ObservationStatus.OBSERVED:
            if self.observed_direction is None:
                raise ValueError("Observed records require observed_direction.")
            if not self.evidence_ids:
                raise ValueError("Observed records require evidence_ids.")
        if (
            self.status in {ObservationStatus.MISSING, ObservationStatus.INCONCLUSIVE}
            and self.observed_direction is not None
        ):
            raise ValueError(
                "Missing or inconclusive observations cannot carry observed_direction."
            )
        if self.status is ObservationStatus.BLOCKED and not self.reasons:
            raise ValueError("Blocked observations require reasons.")
        if any(not reason.strip() for reason in self.reasons):
            raise ValueError("Observation reasons cannot be empty.")

    @property
    def is_observed(self) -> bool:
        """Return whether the observation has observed evidence."""

        return self.status is ObservationStatus.OBSERVED

    @property
    def is_blocked(self) -> bool:
        """Return whether the observation is blocked from comparison."""

        return self.status is ObservationStatus.BLOCKED


@dataclass(frozen=True, slots=True)
class ObservationLedger:
    """Deterministic ledger of observations for prediction comparison."""

    observations: tuple[ObservationRecord, ...]

    def __post_init__(self) -> None:
        """Reject duplicate observation ids and audit slots."""

        _unique_ids(
            (observation.observation_id for observation in self.observations),
            label="observation_id",
        )
        _unique_ids(
            (str(observation.audit_index) for observation in self.observations),
            label="observation audit_index",
        )

    @property
    def ordered_observations(self) -> tuple[ObservationRecord, ...]:
        """Return observations in deterministic audit order."""

        return tuple(
            sorted(self.observations, key=lambda observation: observation.audit_index)
        )

    @property
    def blocked_observations(self) -> tuple[ObservationRecord, ...]:
        """Return blocked observations."""

        return tuple(
            observation for observation in self.observations if observation.is_blocked
        )

    def observation_by_id(self, observation_id: str) -> ObservationRecord:
        """Return an observation by id."""

        for observation in self.observations:
            if observation.observation_id == observation_id:
                return observation
        raise ValueError(f"Unknown observation_id: {observation_id}")

    def observation_for_prediction(
        self,
        prediction: CausalPrediction,
    ) -> ObservationRecord | None:
        """Return the observation targeted by a prediction, if present."""

        for observation in self.observations:
            if observation.observation_id == prediction.expected_observation_id:
                return observation
        return None


@dataclass(frozen=True, slots=True)
class PredictionComparisonRecord:
    """Result of comparing one prediction with one observation target."""

    comparison_id: str
    prediction_id: str
    source_assumption_id: str
    observation_id: str
    result: PredictionComparisonResult
    expected_direction: PredictionDirection
    observed_direction: PredictionDirection | None
    prediction_confidence: float
    observation_confidence: float | None
    evidence_ids: tuple[str, ...]
    reasons: tuple[str, ...]

    def __post_init__(self) -> None:
        """Validate comparison identity, confidence, evidence, and reasons."""

        if not self.comparison_id.strip():
            raise ValueError(
                "Prediction comparisons require a non-empty comparison_id."
            )
        if not self.prediction_id.strip():
            raise ValueError(
                "Prediction comparisons require a non-empty prediction_id."
            )
        if not self.source_assumption_id.strip():
            raise ValueError(
                "Prediction comparisons require a non-empty source_assumption_id."
            )
        if not self.observation_id.strip():
            raise ValueError(
                "Prediction comparisons require a non-empty observation_id."
            )
        if not 0.0 <= self.prediction_confidence <= 1.0:
            raise ValueError(
                "Prediction comparison prediction_confidence must be between 0.0 "
                "and 1.0."
            )
        if self.observation_confidence is not None and not (
            0.0 <= self.observation_confidence <= 1.0
        ):
            raise ValueError(
                "Prediction comparison observation_confidence must be between 0.0 "
                "and 1.0."
            )
        _unique_ids(self.evidence_ids, label="prediction comparison evidence_id")
        if not self.reasons:
            raise ValueError("Prediction comparisons require reasons.")
        if any(not reason.strip() for reason in self.reasons):
            raise ValueError("Prediction comparison reasons cannot be empty.")
        if self.result in {
            PredictionComparisonResult.MATCHED,
            PredictionComparisonResult.DIVERGED,
        }:
            if self.observed_direction is None:
                raise ValueError(
                    "Matched or diverged comparisons require observed_direction."
                )
            if not self.evidence_ids:
                raise ValueError(
                    "Matched or diverged comparisons require evidence_ids."
                )

    @property
    def supports_prediction(self) -> bool:
        """Return whether the comparison supports the prediction."""

        return self.result is PredictionComparisonResult.MATCHED

    @property
    def challenges_prediction(self) -> bool:
        """Return whether the comparison challenges the prediction."""

        return self.result is PredictionComparisonResult.DIVERGED

    @property
    def blocks_revision(self) -> bool:
        """Return whether the comparison is blocked from later causal revision."""

        return self.result is PredictionComparisonResult.BLOCKED


@dataclass(frozen=True, slots=True)
class PredictionComparisonLedger:
    """Container for prediction-vs-observation comparison records."""

    comparisons: tuple[PredictionComparisonRecord, ...]

    def __post_init__(self) -> None:
        """Reject duplicate comparison ids."""

        _unique_ids(
            (comparison.comparison_id for comparison in self.comparisons),
            label="comparison_id",
        )

    @property
    def matched_comparisons(self) -> tuple[PredictionComparisonRecord, ...]:
        """Return comparisons that matched predictions."""

        return tuple(
            comparison
            for comparison in self.comparisons
            if comparison.result is PredictionComparisonResult.MATCHED
        )

    @property
    def diverged_comparisons(self) -> tuple[PredictionComparisonRecord, ...]:
        """Return comparisons that diverged from predictions."""

        return tuple(
            comparison
            for comparison in self.comparisons
            if comparison.result is PredictionComparisonResult.DIVERGED
        )

    @property
    def inconclusive_comparisons(self) -> tuple[PredictionComparisonRecord, ...]:
        """Return inconclusive comparisons."""

        return tuple(
            comparison
            for comparison in self.comparisons
            if comparison.result is PredictionComparisonResult.INCONCLUSIVE
        )

    @property
    def blocked_comparisons(self) -> tuple[PredictionComparisonRecord, ...]:
        """Return blocked comparisons."""

        return tuple(
            comparison
            for comparison in self.comparisons
            if comparison.result is PredictionComparisonResult.BLOCKED
        )

    def comparison_by_id(self, comparison_id: str) -> PredictionComparisonRecord:
        """Return a comparison record by id."""

        for comparison in self.comparisons:
            if comparison.comparison_id == comparison_id:
                return comparison
        raise ValueError(f"Unknown prediction comparison_id: {comparison_id}")

    def comparisons_for_prediction(
        self,
        prediction_id: str,
    ) -> tuple[PredictionComparisonRecord, ...]:
        """Return comparison records for a prediction id."""

        return tuple(
            comparison
            for comparison in self.comparisons
            if comparison.prediction_id == prediction_id
        )


def compare_prediction_to_observation(
    *,
    comparison_id: str,
    prediction: CausalPrediction,
    observation: ObservationRecord,
) -> PredictionComparisonRecord:
    """Compare one prediction against its targeted observation."""

    if prediction.expected_observation_id != observation.observation_id:
        raise ValueError(
            f"Prediction {prediction.prediction_id} expected observation "
            f"{prediction.expected_observation_id}, not {observation.observation_id}."
        )
    result, reasons = _comparison_result_and_reasons(prediction, observation)
    return PredictionComparisonRecord(
        comparison_id=comparison_id,
        prediction_id=prediction.prediction_id,
        source_assumption_id=prediction.source_assumption_id,
        observation_id=observation.observation_id,
        result=result,
        expected_direction=prediction.expected_direction,
        observed_direction=observation.observed_direction,
        prediction_confidence=prediction.confidence,
        observation_confidence=observation.confidence,
        evidence_ids=_merge_unique(prediction.evidence_ids, observation.evidence_ids),
        reasons=reasons,
    )


def compare_prediction_set_to_observations(
    *,
    prediction_set: CausalPredictionSet,
    observations: ObservationLedger,
) -> PredictionComparisonLedger:
    """Compare every prediction in a set against available observations."""

    comparisons: list[PredictionComparisonRecord] = []
    for prediction in prediction_set.predictions:
        observation = observations.observation_for_prediction(prediction)
        comparison_index = len(comparisons)
        if observation is None:
            comparisons.append(
                _missing_observation_comparison(
                    comparison_id=f"comparison-{comparison_index:03d}",
                    prediction=prediction,
                )
            )
            continue
        comparisons.append(
            compare_prediction_to_observation(
                comparison_id=f"comparison-{comparison_index:03d}",
                prediction=prediction,
                observation=observation,
            )
        )
    return PredictionComparisonLedger(comparisons=tuple(comparisons))


def _comparison_result_and_reasons(
    prediction: CausalPrediction,
    observation: ObservationRecord,
) -> tuple[PredictionComparisonResult, tuple[str, ...]]:
    """Return comparison result and reasons for a prediction/observation pair."""

    if not prediction.is_testable:
        return (
            PredictionComparisonResult.BLOCKED,
            (
                f"Prediction {prediction.prediction_id} is {prediction.status.value} "
                "and cannot be used for causal revision.",
            ),
        )
    if observation.status is ObservationStatus.BLOCKED:
        return (
            PredictionComparisonResult.BLOCKED,
            (
                f"Observation {observation.observation_id} is blocked and cannot "
                "support comparison.",
            ),
        )
    if observation.status in {
        ObservationStatus.MISSING,
        ObservationStatus.INCONCLUSIVE,
    }:
        return (
            PredictionComparisonResult.INCONCLUSIVE,
            (
                f"Observation {observation.observation_id} is "
                f"{observation.status.value}.",
            ),
        )
    if observation.observed_direction is prediction.expected_direction:
        return (
            PredictionComparisonResult.MATCHED,
            (
                f"Observation {observation.observation_id} matched expected "
                f"direction {prediction.expected_direction.value}.",
            ),
        )
    observed_direction = observation.observed_direction
    if observed_direction is None:
        raise ValueError("Observed comparisons require observed_direction.")
    return (
        PredictionComparisonResult.DIVERGED,
        (
            f"Observation {observation.observation_id} was "
            f"{observed_direction.value} instead of expected "
            f"{prediction.expected_direction.value}.",
        ),
    )


def _missing_observation_comparison(
    *,
    comparison_id: str,
    prediction: CausalPrediction,
) -> PredictionComparisonRecord:
    """Return an inconclusive comparison for a missing observation target."""

    return PredictionComparisonRecord(
        comparison_id=comparison_id,
        prediction_id=prediction.prediction_id,
        source_assumption_id=prediction.source_assumption_id,
        observation_id=prediction.expected_observation_id,
        result=PredictionComparisonResult.INCONCLUSIVE,
        expected_direction=prediction.expected_direction,
        observed_direction=None,
        prediction_confidence=prediction.confidence,
        observation_confidence=None,
        evidence_ids=prediction.evidence_ids,
        reasons=(
            f"No observation record exists for expected observation "
            f"{prediction.expected_observation_id}.",
        ),
    )


def _merge_unique(first: tuple[str, ...], second: tuple[str, ...]) -> tuple[str, ...]:
    """Merge ids while preserving first-seen order."""

    merged: list[str] = []
    for value in (*first, *second):
        if value not in merged:
            merged.append(value)
    return tuple(merged)


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
