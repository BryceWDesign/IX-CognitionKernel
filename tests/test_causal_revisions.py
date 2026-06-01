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
from ix_cognition_kernel.observations import (
    PredictionComparisonLedger,
    PredictionComparisonRecord,
    PredictionComparisonResult,
)
from ix_cognition_kernel.prediction import PredictionDirection
from ix_cognition_kernel.revision import (
    CausalRevisionAction,
    CausalRevisionPolicy,
    CausalRevisionRecord,
    revise_causal_assumptions,
)
from ix_cognition_kernel.state import UncertaintyStatus


def assumption(
    *,
    confidence: float = 0.7,
    uncertainty: UncertaintyStatus = UncertaintyStatus.KNOWN,
) -> CausalAssumption:
    return CausalAssumption(
        assumption_id="assumption-001",
        cause_belief_id="belief-cause-001",
        effect_belief_id="belief-effect-001",
        relation=CausalRelation.ENABLES,
        rationale="The assumption can be revised from prediction comparison evidence.",
        confidence=confidence,
        uncertainty=uncertainty,
        evidence_ids=("ev-causal-001",),
        constraint_ids=("constraint-001",),
        expected_observation_ids=("observation-001",),
        counterfactual_note_ids=("counterfactual-001",),
    )


def causal_model(
    source_assumption: CausalAssumption | None = None,
) -> SimpleCausalModel:
    return SimpleCausalModel(
        model_id="causal-model-001",
        assumptions=(source_assumption or assumption(),),
        constraints=(
            CausalConstraint(
                constraint_id="constraint-001",
                description="The causal assumption is scoped to a controlled test.",
                severity=ConstraintSeverity.CONTEXT,
                source_belief_ids=("belief-cause-001",),
            ),
        ),
        expected_observations=(
            ExpectedObservation(
                observation_id="observation-001",
                description="The expected observation target exists.",
                linked_evidence_ids=("ev-causal-001",),
                required_for_validation=True,
            ),
        ),
        counterfactuals=(
            CounterfactualNote(
                note_id="counterfactual-001",
                scenario="If the assumption fails, the observation may diverge.",
                expected_difference="The expected observation is absent or reversed.",
                uncertainty=UncertaintyStatus.KNOWN,
            ),
        ),
    )


def comparison(
    *,
    comparison_id: str = "comparison-001",
    result: PredictionComparisonResult = PredictionComparisonResult.MATCHED,
    observation_confidence: float | None = 0.8,
    evidence_ids: tuple[str, ...] = ("ev-comparison-001",),
    source_assumption_id: str = "assumption-001",
) -> PredictionComparisonRecord:
    return PredictionComparisonRecord(
        comparison_id=comparison_id,
        prediction_id="prediction-001",
        source_assumption_id=source_assumption_id,
        observation_id="observation-001",
        result=result,
        expected_direction=PredictionDirection.PRESENT,
        observed_direction=PredictionDirection.PRESENT
        if result is PredictionComparisonResult.MATCHED
        else PredictionDirection.ABSENT
        if result is PredictionComparisonResult.DIVERGED
        else None,
        prediction_confidence=0.7,
        observation_confidence=observation_confidence,
        evidence_ids=evidence_ids,
        reasons=(f"{comparison_id} generated revision pressure.",),
    )


def test_matched_comparison_strengthens_causal_assumption() -> None:
    ledger = PredictionComparisonLedger(comparisons=(comparison(),))

    result = revise_causal_assumptions(causal_model(), ledger)
    revised = result.after_model.assumption_by_id("assumption-001")
    revision = result.revisions[0]

    assert result.before_model.assumption_by_id("assumption-001").confidence == 0.7
    assert revised.confidence == 0.82
    assert revised.uncertainty is UncertaintyStatus.KNOWN
    assert revised.evidence_ids == ("ev-causal-001", "ev-comparison-001")
    assert revision.action is CausalRevisionAction.STRENGTHENED
    assert revision.changed_confidence is True
    assert revision.changed_uncertainty is False
    assert result.strengthened_revisions == (revision,)
    assert result.changed_assumption_ids == ("assumption-001",)


def test_diverged_comparison_weakens_causal_assumption() -> None:
    ledger = PredictionComparisonLedger(
        comparisons=(comparison(result=PredictionComparisonResult.DIVERGED),)
    )

    result = revise_causal_assumptions(causal_model(), ledger)
    revised = result.after_model.assumption_by_id("assumption-001")
    revision = result.revisions[0]

    assert revised.confidence == 0.5
    assert revised.uncertainty is UncertaintyStatus.KNOWN
    assert revision.action is CausalRevisionAction.WEAKENED
    assert result.weakened_revisions == (revision,)


def test_strong_divergence_disputes_causal_assumption() -> None:
    ledger = PredictionComparisonLedger(
        comparisons=(
            comparison(
                result=PredictionComparisonResult.DIVERGED,
                observation_confidence=1.0,
            ),
        )
    )

    result = revise_causal_assumptions(
        causal_model(assumption(confidence=0.55)),
        ledger,
    )
    revised = result.after_model.assumption_by_id("assumption-001")
    revision = result.revisions[0]

    assert revised.confidence == 0.3
    assert revised.uncertainty is UncertaintyStatus.DISPUTED
    assert revision.action is CausalRevisionAction.DISPUTED
    assert revision.blocks_assumption is True
    assert result.blocking_revisions == (revision,)


def test_repeated_divergence_blocks_or_retires_low_confidence_assumption() -> None:
    first = comparison(
        comparison_id="comparison-diverged-001",
        result=PredictionComparisonResult.DIVERGED,
        observation_confidence=1.0,
        evidence_ids=("ev-diverged-001",),
    )
    second = comparison(
        comparison_id="comparison-diverged-002",
        result=PredictionComparisonResult.DIVERGED,
        observation_confidence=1.0,
        evidence_ids=("ev-diverged-002",),
    )
    ledger = PredictionComparisonLedger(comparisons=(first, second))

    result = revise_causal_assumptions(
        causal_model(assumption(confidence=0.5)),
        ledger,
    )
    revised = result.after_model.assumption_by_id("assumption-001")
    revision = result.revisions[0]

    assert revised.confidence == 0.0
    assert revised.uncertainty is UncertaintyStatus.DISPUTED
    assert revision.action is CausalRevisionAction.RETIRED
    assert revision.evidence_ids == (
        "ev-causal-001",
        "ev-diverged-001",
        "ev-diverged-002",
    )


def test_blocked_comparison_blocks_causal_assumption_fail_closed() -> None:
    ledger = PredictionComparisonLedger(
        comparisons=(
            comparison(
                result=PredictionComparisonResult.BLOCKED,
                observation_confidence=None,
                evidence_ids=(),
            ),
        )
    )

    result = revise_causal_assumptions(causal_model(), ledger)
    revised = result.after_model.assumption_by_id("assumption-001")
    revision = result.revisions[0]

    assert revised.confidence == 0.7
    assert revised.uncertainty is UncertaintyStatus.UNSAFE_TO_ACT
    assert revision.action is CausalRevisionAction.BLOCKED
    assert revision.blocks_assumption is True


def test_inconclusive_comparison_does_not_create_revision_record() -> None:
    ledger = PredictionComparisonLedger(
        comparisons=(
            comparison(
                result=PredictionComparisonResult.INCONCLUSIVE,
                observation_confidence=None,
                evidence_ids=(),
            ),
        )
    )

    result = revise_causal_assumptions(causal_model(), ledger)

    assert result.after_model == result.before_model
    assert result.revisions == ()


def test_unknown_assumption_reference_is_rejected() -> None:
    ledger = PredictionComparisonLedger(
        comparisons=(comparison(source_assumption_id="assumption-missing"),)
    )

    with pytest.raises(ValueError, match="unknown source_assumption_id"):
        revise_causal_assumptions(causal_model(), ledger)


def test_causal_revision_policy_rejects_invalid_thresholds() -> None:
    with pytest.raises(ValueError, match="ordered"):
        CausalRevisionPolicy(
            retire_threshold=0.3,
            block_threshold=0.2,
            dispute_threshold=0.4,
        )

    with pytest.raises(ValueError, match="matched_weight"):
        CausalRevisionPolicy(matched_weight=1.01)


def test_causal_revision_record_requires_traceability_and_reasons() -> None:
    with pytest.raises(ValueError, match="comparison_ids"):
        CausalRevisionRecord(
            revision_id="causal-revision-invalid",
            assumption_id="assumption-001",
            action=CausalRevisionAction.STRENGTHENED,
            comparison_ids=(),
            before_confidence=0.5,
            after_confidence=0.6,
            before_uncertainty=UncertaintyStatus.KNOWN,
            after_uncertainty=UncertaintyStatus.KNOWN,
            evidence_ids=("ev-001",),
            reasons=("Missing comparison ids should fail.",),
        )

    with pytest.raises(ValueError, match="require reasons"):
        CausalRevisionRecord(
            revision_id="causal-revision-invalid",
            assumption_id="assumption-001",
            action=CausalRevisionAction.STRENGTHENED,
            comparison_ids=("comparison-001",),
            before_confidence=0.5,
            after_confidence=0.6,
            before_uncertainty=UncertaintyStatus.KNOWN,
            after_uncertainty=UncertaintyStatus.KNOWN,
            evidence_ids=("ev-001",),
            reasons=(),
        )
