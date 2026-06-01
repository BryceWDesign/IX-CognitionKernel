import pytest

from ix_cognition_kernel.causal import (
    CausalAssumption,
    CausalRelation,
    SimpleCausalModel,
)
from ix_cognition_kernel.history import (
    BeliefHistory,
    BeliefRevisionKind,
    BeliefRevisionRecord,
    BeliefTimeline,
)
from ix_cognition_kernel.observations import (
    PredictionComparisonLedger,
    PredictionComparisonRecord,
    PredictionComparisonResult,
)
from ix_cognition_kernel.outcome import (
    OutcomeLearningLedger,
    OutcomeLearningRecord,
    OutcomeLearningStatus,
    OutcomePressure,
    build_outcome_learning_record,
    outcome_learning_ledger,
)
from ix_cognition_kernel.prediction import PredictionDirection
from ix_cognition_kernel.revision import (
    CausalRevisionAction,
    CausalRevisionRecord,
    CausalRevisionResult,
)
from ix_cognition_kernel.state import BeliefDisposition, UncertaintyStatus


def belief_revision(
    *,
    kind: BeliefRevisionKind = BeliefRevisionKind.STRENGTHENED,
    after_disposition: BeliefDisposition = BeliefDisposition.ACTIVE,
) -> BeliefRevisionRecord:
    return BeliefRevisionRecord(
        revision_id="revision-001",
        revision_index=0,
        belief_id="belief-001",
        claim_id="claim-001",
        update_id="belief-update-001",
        kind=kind,
        event_ids=("event-001",),
        staleness_ids=(),
        before_confidence=0.5,
        after_confidence=0.7,
        before_uncertainty=UncertaintyStatus.ASSUMED,
        after_uncertainty=UncertaintyStatus.KNOWN,
        before_disposition=BeliefDisposition.NEEDS_EVIDENCE,
        after_disposition=after_disposition,
        reasons=("The belief revision was derived from evidence.",),
    )


def belief_history(
    *,
    revision: BeliefRevisionRecord | None = None,
) -> BeliefHistory:
    revision_record = revision or belief_revision()
    return BeliefHistory(
        timelines=(
            BeliefTimeline(
                belief_id="belief-001",
                claim_id="claim-001",
                revisions=(revision_record,),
            ),
        )
    )


def causal_assumption() -> CausalAssumption:
    return CausalAssumption(
        assumption_id="assumption-001",
        cause_belief_id="belief-cause-001",
        effect_belief_id="belief-effect-001",
        relation=CausalRelation.ENABLES,
        rationale="The assumption participates in outcome learning.",
        confidence=0.7,
        uncertainty=UncertaintyStatus.KNOWN,
        evidence_ids=("ev-causal-001",),
        constraint_ids=(),
        expected_observation_ids=(),
        counterfactual_note_ids=(),
    )


def causal_model() -> SimpleCausalModel:
    return SimpleCausalModel(
        model_id="causal-model-001",
        assumptions=(causal_assumption(),),
        constraints=(),
        expected_observations=(),
        counterfactuals=(),
    )


def causal_revision(
    *,
    action: CausalRevisionAction = CausalRevisionAction.STRENGTHENED,
) -> CausalRevisionRecord:
    return CausalRevisionRecord(
        revision_id="causal-revision-001",
        assumption_id="assumption-001",
        action=action,
        comparison_ids=("comparison-001",),
        before_confidence=0.7,
        after_confidence=0.82 if action is CausalRevisionAction.STRENGTHENED else 0.3,
        before_uncertainty=UncertaintyStatus.KNOWN,
        after_uncertainty=UncertaintyStatus.KNOWN
        if action is CausalRevisionAction.STRENGTHENED
        else UncertaintyStatus.DISPUTED,
        evidence_ids=("ev-causal-001", "ev-comparison-001"),
        reasons=("The causal revision was derived from prediction comparison.",),
    )


def causal_revision_result(
    *,
    revision: CausalRevisionRecord | None = None,
) -> CausalRevisionResult:
    source_model = causal_model()
    return CausalRevisionResult(
        before_model=source_model,
        after_model=source_model,
        comparison_ledger=comparison_ledger(),
        revisions=(revision or causal_revision(),),
    )


def comparison_record(
    *,
    result: PredictionComparisonResult = PredictionComparisonResult.MATCHED,
) -> PredictionComparisonRecord:
    return PredictionComparisonRecord(
        comparison_id="comparison-001",
        prediction_id="prediction-001",
        source_assumption_id="assumption-001",
        observation_id="observation-001",
        result=result,
        expected_direction=PredictionDirection.PRESENT,
        observed_direction=PredictionDirection.PRESENT
        if result is PredictionComparisonResult.MATCHED
        else PredictionDirection.ABSENT
        if result is PredictionComparisonResult.DIVERGED
        else None,
        prediction_confidence=0.7,
        observation_confidence=0.9
        if result
        in {
            PredictionComparisonResult.MATCHED,
            PredictionComparisonResult.DIVERGED,
        }
        else None,
        evidence_ids=("ev-comparison-001",)
        if result
        in {
            PredictionComparisonResult.MATCHED,
            PredictionComparisonResult.DIVERGED,
        }
        else (),
        reasons=("The comparison result was produced from observation evidence.",),
    )


def comparison_ledger(
    *,
    comparison: PredictionComparisonRecord | None = None,
) -> PredictionComparisonLedger:
    return PredictionComparisonLedger(comparisons=(comparison or comparison_record(),))


def test_build_outcome_learning_record_accepts_evidence_linked_learning() -> None:
    record = build_outcome_learning_record(
        outcome_id="outcome-001",
        summary="A matched outcome strengthened belief and causal state.",
        belief_history=belief_history(),
        causal_revision_result=causal_revision_result(),
        comparison_ledger=comparison_ledger(),
        evidence_ids=("ev-outcome-001",),
    )

    assert record.status is OutcomeLearningStatus.ACCEPTED
    assert record.pressure is OutcomePressure.CONFIRMED
    assert record.belief_revision_ids == ("revision-001",)
    assert record.causal_revision_ids == ("causal-revision-001",)
    assert record.prediction_comparison_ids == ("comparison-001",)
    assert record.evidence_ids == ("ev-outcome-001",)
    assert record.has_belief_learning is True
    assert record.has_causal_learning is True
    assert record.is_accepted is True
    assert "belief_revisions=1" in record.learning_summary


def test_diverged_prediction_comparison_creates_corrected_outcome_pressure() -> None:
    diverged = comparison_record(result=PredictionComparisonResult.DIVERGED)
    weakened_revision = causal_revision(action=CausalRevisionAction.WEAKENED)

    record = build_outcome_learning_record(
        outcome_id="outcome-corrected",
        summary="A diverged outcome corrected causal confidence.",
        belief_history=belief_history(
            revision=belief_revision(kind=BeliefRevisionKind.WEAKENED)
        ),
        causal_revision_result=causal_revision_result(revision=weakened_revision),
        comparison_ledger=comparison_ledger(comparison=diverged),
        evidence_ids=("ev-outcome-corrected",),
    )

    assert record.status is OutcomeLearningStatus.ACCEPTED
    assert record.pressure is OutcomePressure.CORRECTED
    assert "divergence" in record.reasons[-1]


def test_blocking_revision_blocks_outcome_learning_record() -> None:
    blocked_revision = causal_revision(action=CausalRevisionAction.BLOCKED)

    record = build_outcome_learning_record(
        outcome_id="outcome-blocked",
        summary="Blocked causal revision prevents accepted outcome learning.",
        belief_history=belief_history(),
        causal_revision_result=causal_revision_result(revision=blocked_revision),
        comparison_ledger=comparison_ledger(),
        evidence_ids=("ev-outcome-blocked",),
    )

    assert record.status is OutcomeLearningStatus.BLOCKED
    assert record.pressure is OutcomePressure.BLOCKED
    assert record.is_blocked is True
    assert "Causal revision result contains blocking revisions." in record.reasons


def test_missing_evidence_marks_outcome_learning_needs_evidence() -> None:
    record = build_outcome_learning_record(
        outcome_id="outcome-needs-evidence",
        summary="Outcome learning cannot be accepted without evidence ids.",
        belief_history=belief_history(),
        causal_revision_result=causal_revision_result(),
        comparison_ledger=comparison_ledger(),
        evidence_ids=(),
    )

    assert record.status is OutcomeLearningStatus.NEEDS_EVIDENCE
    assert record.pressure is OutcomePressure.CONFIRMED
    assert "Outcome learning lacks evidence ids." in record.reasons


def test_accepted_outcome_learning_requires_evidence_and_links() -> None:
    with pytest.raises(
        ValueError, match="Accepted outcome learning records require evidence_ids"
    ):
        OutcomeLearningRecord(
            outcome_id="outcome-invalid",
            summary="Invalid accepted outcome.",
            status=OutcomeLearningStatus.ACCEPTED,
            pressure=OutcomePressure.CONFIRMED,
            belief_revision_ids=("revision-001",),
            causal_revision_ids=(),
            prediction_comparison_ids=(),
            evidence_ids=(),
            learning_summary="Invalid accepted outcome has no evidence.",
            reasons=("Accepted outcomes need evidence.",),
        )

    with pytest.raises(ValueError, match="linked revisions or prediction comparisons"):
        OutcomeLearningRecord(
            outcome_id="outcome-invalid",
            summary="Invalid accepted outcome.",
            status=OutcomeLearningStatus.ACCEPTED,
            pressure=OutcomePressure.CONFIRMED,
            belief_revision_ids=(),
            causal_revision_ids=(),
            prediction_comparison_ids=(),
            evidence_ids=("ev-outcome",),
            learning_summary="Invalid accepted outcome has no links.",
            reasons=("Accepted outcomes need linked learning artifacts.",),
        )


def test_blocked_outcome_learning_requires_blocked_pressure() -> None:
    with pytest.raises(ValueError, match="blocked pressure"):
        OutcomeLearningRecord(
            outcome_id="outcome-invalid-blocked",
            summary="Blocked status must match pressure.",
            status=OutcomeLearningStatus.BLOCKED,
            pressure=OutcomePressure.CONFIRMED,
            belief_revision_ids=("revision-001",),
            causal_revision_ids=(),
            prediction_comparison_ids=(),
            evidence_ids=("ev-outcome",),
            learning_summary="Blocked status cannot use confirmed pressure.",
            reasons=("Blocked pressure mismatch should fail.",),
        )


def test_outcome_learning_ledger_groups_and_retrieves_records() -> None:
    record = build_outcome_learning_record(
        outcome_id="outcome-001",
        summary="A matched outcome strengthened belief and causal state.",
        belief_history=belief_history(),
        causal_revision_result=causal_revision_result(),
        comparison_ledger=comparison_ledger(),
        evidence_ids=("ev-outcome-001",),
    )
    ledger = outcome_learning_ledger(record)

    assert ledger.record_by_id("outcome-001") == record
    assert ledger.accepted_records == (record,)
    assert ledger.blocked_records == ()
    assert ledger.needs_evidence_records == ()
    assert ledger.records_for_belief_revision("revision-001") == (record,)
    assert ledger.records_for_causal_revision("causal-revision-001") == (record,)
    assert ledger.records_for_prediction_comparison("comparison-001") == (record,)


def test_outcome_learning_ledger_rejects_duplicate_outcome_ids() -> None:
    record = build_outcome_learning_record(
        outcome_id="outcome-001",
        summary="A matched outcome strengthened belief and causal state.",
        belief_history=belief_history(),
        causal_revision_result=causal_revision_result(),
        comparison_ledger=comparison_ledger(),
        evidence_ids=("ev-outcome-001",),
    )

    with pytest.raises(ValueError, match="Duplicate outcome_id"):
        OutcomeLearningLedger(records=(record, record))


def test_unknown_outcome_lookup_is_rejected() -> None:
    with pytest.raises(ValueError, match="Unknown outcome_id"):
        outcome_learning_ledger().record_by_id("outcome-missing")
