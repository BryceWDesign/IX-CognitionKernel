import pytest

from ix_cognition_kernel.causal import (
    CausalAssumption,
    CausalConstraint,
    CausalRelation,
    ConstraintSeverity,
    CounterfactualNote,
    ExpectedObservation,
    SimpleCausalModel,
)
from ix_cognition_kernel.prediction import (
    CausalPrediction,
    CausalPredictionSet,
    PredictionCriterion,
    PredictionDirection,
    PredictionStatus,
    prediction_from_causal_assumption,
    prediction_set_from_causal_model,
)
from ix_cognition_kernel.state import UncertaintyStatus


def assumption(
    *,
    confidence: float = 0.8,
    uncertainty: UncertaintyStatus = UncertaintyStatus.KNOWN,
    evidence_ids: tuple[str, ...] = ("ev-causal-001",),
) -> CausalAssumption:
    return CausalAssumption(
        assumption_id="assumption-001",
        cause_belief_id="belief-cause-001",
        effect_belief_id="belief-effect-001",
        relation=CausalRelation.ENABLES,
        rationale="The causal assumption is ready to produce a testable prediction.",
        confidence=confidence,
        uncertainty=uncertainty,
        evidence_ids=evidence_ids,
        constraint_ids=("constraint-001",),
        expected_observation_ids=("observation-001",),
        counterfactual_note_ids=("counterfactual-001",),
    )


def criterion() -> PredictionCriterion:
    return PredictionCriterion(
        criterion_id="criterion-001",
        description="The expected observation should be present later.",
        expected_observation_id="observation-001",
        expected_direction=PredictionDirection.PRESENT,
    )


def causal_model() -> SimpleCausalModel:
    return SimpleCausalModel(
        model_id="causal-model-001",
        assumptions=(assumption(),),
        constraints=(
            CausalConstraint(
                constraint_id="constraint-001",
                description="The prediction is scoped to a controlled test.",
                severity=ConstraintSeverity.CONTEXT,
                source_belief_ids=("belief-cause-001",),
            ),
        ),
        expected_observations=(
            ExpectedObservation(
                observation_id="observation-001",
                description="The expected downstream observation appears.",
                linked_evidence_ids=("ev-causal-001",),
                required_for_validation=True,
            ),
        ),
        counterfactuals=(
            CounterfactualNote(
                note_id="counterfactual-001",
                scenario=(
                    "If the cause belief fails, the observation should not appear."
                ),
                expected_difference="The expected observation is absent.",
                uncertainty=UncertaintyStatus.KNOWN,
            ),
        ),
    )


def test_prediction_criterion_requires_observation_linkage() -> None:
    with pytest.raises(ValueError, match="expected_observation_id"):
        PredictionCriterion(
            criterion_id="criterion-invalid",
            description="Invalid missing observation id.",
            expected_observation_id=" ",
            expected_direction=PredictionDirection.PRESENT,
        )


def test_causal_prediction_created_from_testable_assumption() -> None:
    prediction = prediction_from_causal_assumption(
        prediction_id="prediction-001",
        assumption=assumption(),
        expected_observation_id="observation-001",
        expected_direction=PredictionDirection.PRESENT,
        criteria=(criterion(),),
    )

    assert prediction.prediction_id == "prediction-001"
    assert prediction.source_assumption_id == "assumption-001"
    assert prediction.confidence == 0.8
    assert prediction.uncertainty is UncertaintyStatus.KNOWN
    assert prediction.status is PredictionStatus.TESTABLE
    assert prediction.is_testable is True
    assert prediction.evidence_ids == ("ev-causal-001",)
    assert prediction.source_belief_ids == ("belief-cause-001", "belief-effect-001")
    assert prediction.required_criteria == (criterion(),)


def test_testable_prediction_rejects_blocking_uncertainty() -> None:
    with pytest.raises(ValueError, match="blocking uncertainty"):
        CausalPrediction(
            prediction_id="prediction-blocked",
            source_assumption_id="assumption-001",
            statement="Blocked uncertainty cannot be called testable.",
            expected_observation_id="observation-001",
            expected_direction=PredictionDirection.PRESENT,
            confidence=0.7,
            uncertainty=UncertaintyStatus.DISPUTED,
            status=PredictionStatus.TESTABLE,
            evaluation_criteria=(criterion(),),
            evidence_ids=("ev-causal-001",),
            source_belief_ids=("belief-cause-001", "belief-effect-001"),
        )


def test_testable_prediction_requires_evidence_and_source_beliefs() -> None:
    with pytest.raises(ValueError, match="evidence ids"):
        CausalPrediction(
            prediction_id="prediction-no-evidence",
            source_assumption_id="assumption-001",
            statement="Testable predictions require evidence.",
            expected_observation_id="observation-001",
            expected_direction=PredictionDirection.PRESENT,
            confidence=0.7,
            uncertainty=UncertaintyStatus.KNOWN,
            status=PredictionStatus.TESTABLE,
            evaluation_criteria=(criterion(),),
            evidence_ids=(),
            source_belief_ids=("belief-cause-001", "belief-effect-001"),
        )

    with pytest.raises(ValueError, match="source belief ids"):
        CausalPrediction(
            prediction_id="prediction-no-beliefs",
            source_assumption_id="assumption-001",
            statement="Testable predictions require source beliefs.",
            expected_observation_id="observation-001",
            expected_direction=PredictionDirection.PRESENT,
            confidence=0.7,
            uncertainty=UncertaintyStatus.KNOWN,
            status=PredictionStatus.TESTABLE,
            evaluation_criteria=(criterion(),),
            evidence_ids=("ev-causal-001",),
            source_belief_ids=(),
        )


def test_testable_prediction_requires_matching_criteria() -> None:
    wrong_observation = PredictionCriterion(
        criterion_id="criterion-wrong-observation",
        description="Wrong observation linkage should fail.",
        expected_observation_id="observation-other",
        expected_direction=PredictionDirection.PRESENT,
    )
    wrong_direction = PredictionCriterion(
        criterion_id="criterion-wrong-direction",
        description="Wrong direction should fail.",
        expected_observation_id="observation-001",
        expected_direction=PredictionDirection.ABSENT,
    )

    with pytest.raises(ValueError, match="expected_observation_id"):
        prediction_from_causal_assumption(
            prediction_id="prediction-wrong-observation",
            assumption=assumption(),
            expected_observation_id="observation-001",
            expected_direction=PredictionDirection.PRESENT,
            criteria=(wrong_observation,),
        )

    with pytest.raises(ValueError, match="expected_direction"):
        prediction_from_causal_assumption(
            prediction_id="prediction-wrong-direction",
            assumption=assumption(),
            expected_observation_id="observation-001",
            expected_direction=PredictionDirection.PRESENT,
            criteria=(wrong_direction,),
        )


def test_prediction_from_assumption_marks_needs_evidence_and_blocked_states() -> None:
    needs_evidence = prediction_from_causal_assumption(
        prediction_id="prediction-needs-evidence",
        assumption=assumption(
            confidence=0.4,
            uncertainty=UncertaintyStatus.ASSUMED,
            evidence_ids=(),
        ),
        expected_observation_id="observation-001",
        expected_direction=PredictionDirection.PRESENT,
        criteria=(criterion(),),
    )
    blocked = prediction_from_causal_assumption(
        prediction_id="prediction-blocked",
        assumption=assumption(uncertainty=UncertaintyStatus.UNSAFE_TO_ACT),
        expected_observation_id="observation-001",
        expected_direction=PredictionDirection.PRESENT,
        criteria=(criterion(),),
    )

    assert needs_evidence.status is PredictionStatus.NEEDS_EVIDENCE
    assert needs_evidence.is_testable is False
    assert blocked.status is PredictionStatus.BLOCKED
    assert blocked.is_blocked is True


def test_prediction_set_from_causal_model_creates_testable_prediction() -> None:
    prediction_set = prediction_set_from_causal_model(
        prediction_set_id="prediction-set-001",
        causal_model=causal_model(),
    )
    prediction = prediction_set.prediction_by_id("prediction-000")

    assert prediction_set.source_model_id == "causal-model-001"
    assert prediction_set.testable_predictions == (prediction,)
    assert prediction_set.blocked_predictions == ()
    assert prediction_set.predictions_requiring_evidence == ()
    assert prediction_set.predictions_for_assumption("assumption-001") == (prediction,)
    assert prediction.expected_observation_id == "observation-001"
    assert prediction.expected_direction is PredictionDirection.PRESENT


def test_prediction_set_rejects_duplicate_prediction_ids() -> None:
    prediction = prediction_from_causal_assumption(
        prediction_id="prediction-duplicate",
        assumption=assumption(),
        expected_observation_id="observation-001",
        expected_direction=PredictionDirection.PRESENT,
        criteria=(criterion(),),
    )

    with pytest.raises(ValueError, match="Duplicate prediction_id"):
        CausalPredictionSet(
            prediction_set_id="prediction-set-duplicates",
            source_model_id="causal-model-001",
            predictions=(prediction, prediction),
        )


def test_unknown_prediction_lookup_is_rejected() -> None:
    prediction_set = prediction_set_from_causal_model(
        prediction_set_id="prediction-set-001",
        causal_model=causal_model(),
    )

    with pytest.raises(ValueError, match="Unknown causal prediction_id"):
        prediction_set.prediction_by_id("prediction-missing")
