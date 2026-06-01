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
from ix_cognition_kernel.state import UncertaintyStatus


def context_constraint() -> CausalConstraint:
    return CausalConstraint(
        constraint_id="constraint-context-001",
        description="The assumption only applies inside the Wave 1 research prototype.",
        severity=ConstraintSeverity.CONTEXT,
        source_belief_ids=("belief-scope-001",),
    )


def observed_expected_observation() -> ExpectedObservation:
    return ExpectedObservation(
        observation_id="observation-001",
        description="The model can retrieve the represented assumption by id.",
        linked_evidence_ids=("ev-causal-001",),
        required_for_validation=True,
    )


def safe_counterfactual() -> CounterfactualNote:
    return CounterfactualNote(
        note_id="counterfactual-001",
        scenario=(
            "If the evidence link were removed, the assumption would need evidence."
        ),
        expected_difference="The assumption would no longer be testable.",
        uncertainty=UncertaintyStatus.KNOWN,
    )


def make_testable_assumption() -> CausalAssumption:
    return CausalAssumption(
        assumption_id="assumption-001",
        cause_belief_id="belief-cause-001",
        effect_belief_id="belief-effect-001",
        relation=CausalRelation.ENABLES,
        rationale="A represented belief can enable structured causal reasoning.",
        confidence=0.82,
        uncertainty=UncertaintyStatus.KNOWN,
        evidence_ids=("ev-causal-001",),
        constraint_ids=("constraint-context-001",),
        expected_observation_ids=("observation-001",),
        counterfactual_note_ids=("counterfactual-001",),
    )


def simple_model() -> SimpleCausalModel:
    return SimpleCausalModel(
        model_id="causal-model-001",
        assumptions=(make_testable_assumption(),),
        constraints=(context_constraint(),),
        expected_observations=(observed_expected_observation(),),
        counterfactuals=(safe_counterfactual(),),
    )


def test_causal_assumption_requires_distinct_cause_and_effect_beliefs() -> None:
    with pytest.raises(ValueError, match="distinct cause and effect"):
        CausalAssumption(
            assumption_id="assumption-loop",
            cause_belief_id="belief-001",
            effect_belief_id="belief-001",
            relation=CausalRelation.REQUIRES,
            rationale="Self-causation should not pass as a simple assumption.",
            confidence=0.7,
            uncertainty=UncertaintyStatus.KNOWN,
            evidence_ids=("ev-001",),
            constraint_ids=(),
            expected_observation_ids=(),
            counterfactual_note_ids=(),
        )


def test_causal_assumption_confidence_must_be_bounded() -> None:
    with pytest.raises(ValueError, match="between 0.0 and 1.0"):
        CausalAssumption(
            assumption_id="assumption-bad-confidence",
            cause_belief_id="belief-cause",
            effect_belief_id="belief-effect",
            relation=CausalRelation.RISKS,
            rationale="Out-of-range confidence must be rejected.",
            confidence=1.01,
            uncertainty=UncertaintyStatus.KNOWN,
            evidence_ids=("ev-001",),
            constraint_ids=(),
            expected_observation_ids=(),
            counterfactual_note_ids=(),
        )


def test_blocking_constraint_requires_source_belief_ids() -> None:
    with pytest.raises(ValueError, match="source belief ids"):
        CausalConstraint(
            constraint_id="constraint-blocking",
            description="A blocking constraint must identify what belief created it.",
            severity=ConstraintSeverity.BLOCKING,
            source_belief_ids=(),
        )


def test_expected_observation_reports_when_validation_still_needs_it() -> None:
    observation = ExpectedObservation(
        observation_id="observation-needed",
        description="A required observation without evidence remains needed.",
        linked_evidence_ids=(),
        required_for_validation=True,
    )

    assert observation.is_observed is False
    assert observation.still_needed is True


def test_counterfactual_with_unsafe_uncertainty_is_not_safe_for_planning() -> None:
    counterfactual = CounterfactualNote(
        note_id="counterfactual-unsafe",
        scenario="Unsafe causal branch.",
        expected_difference="Planning cannot rely on this branch.",
        uncertainty=UncertaintyStatus.UNSAFE_TO_ACT,
    )

    assert counterfactual.is_safe_to_use_for_planning is False


def test_simple_causal_model_returns_testable_assumptions() -> None:
    model = simple_model()

    assert model.assumption_by_id("assumption-001").relation is CausalRelation.ENABLES
    assert model.testable_assumptions == (make_testable_assumption(),)
    assert model.assumptions_requiring_evidence == ()
    assert model.blocked_assumptions == ()
    assert model.observations_still_needed == ()


def test_simple_causal_model_rejects_duplicate_assumption_ids() -> None:
    assumption = make_testable_assumption()

    with pytest.raises(ValueError, match="Duplicate assumption_id"):
        SimpleCausalModel(
            model_id="causal-model-duplicates",
            assumptions=(assumption, assumption),
            constraints=(context_constraint(),),
            expected_observations=(observed_expected_observation(),),
            counterfactuals=(safe_counterfactual(),),
        )


def test_simple_causal_model_rejects_unknown_constraint_reference() -> None:
    assumption = CausalAssumption(
        assumption_id="assumption-unknown-constraint",
        cause_belief_id="belief-cause",
        effect_belief_id="belief-effect",
        relation=CausalRelation.CONSTRAINS,
        rationale="Unknown constraint ids must not pass validation.",
        confidence=0.8,
        uncertainty=UncertaintyStatus.KNOWN,
        evidence_ids=("ev-001",),
        constraint_ids=("constraint-missing",),
        expected_observation_ids=(),
        counterfactual_note_ids=(),
    )

    with pytest.raises(ValueError, match="unknown constraint_id"):
        SimpleCausalModel(
            model_id="causal-model-missing-reference",
            assumptions=(assumption,),
            constraints=(),
            expected_observations=(),
            counterfactuals=(),
        )


def test_simple_causal_model_lists_assumptions_requiring_evidence() -> None:
    assumption = CausalAssumption(
        assumption_id="assumption-needs-evidence",
        cause_belief_id="belief-cause",
        effect_belief_id="belief-effect",
        relation=CausalRelation.REQUIRES,
        rationale="Assumed causal claims require evidence before testing.",
        confidence=0.45,
        uncertainty=UncertaintyStatus.ASSUMED,
        evidence_ids=(),
        constraint_ids=(),
        expected_observation_ids=(),
        counterfactual_note_ids=(),
    )
    model = SimpleCausalModel(
        model_id="causal-model-needs-evidence",
        assumptions=(assumption,),
        constraints=(),
        expected_observations=(),
        counterfactuals=(),
    )

    assert model.testable_assumptions == ()
    assert model.assumptions_requiring_evidence == (assumption,)


def test_simple_causal_model_lists_blocked_assumptions() -> None:
    constraint = CausalConstraint(
        constraint_id="constraint-hard-limit",
        description="Hard limits block causal actionability.",
        severity=ConstraintSeverity.HARD_LIMIT,
        source_belief_ids=("belief-limit",),
    )
    assumption = CausalAssumption(
        assumption_id="assumption-blocked",
        cause_belief_id="belief-cause",
        effect_belief_id="belief-effect",
        relation=CausalRelation.RISKS,
        rationale="A hard-limit constraint blocks this assumption.",
        confidence=0.72,
        uncertainty=UncertaintyStatus.KNOWN,
        evidence_ids=("ev-risk",),
        constraint_ids=("constraint-hard-limit",),
        expected_observation_ids=(),
        counterfactual_note_ids=(),
    )
    model = SimpleCausalModel(
        model_id="causal-model-blocked",
        assumptions=(assumption,),
        constraints=(constraint,),
        expected_observations=(),
        counterfactuals=(),
    )

    assert model.testable_assumptions == ()
    assert model.blocked_assumptions == (assumption,)


def test_unknown_causal_assumption_lookup_is_rejected() -> None:
    with pytest.raises(ValueError, match="Unknown causal assumption_id"):
        simple_model().assumption_by_id("assumption-missing")
