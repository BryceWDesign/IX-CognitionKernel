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
from ix_cognition_kernel.cycle import (
    LearnableCognitionCycleInput,
    run_learnable_cognition_cycle,
)
from ix_cognition_kernel.learning import (
    EvidenceEvent,
    EvidenceEventPolarity,
    UpdateLedger,
)
from ix_cognition_kernel.memory import MemoryCandidate, MemoryCandidateKind
from ix_cognition_kernel.observations import (
    ObservationLedger,
    ObservationRecord,
    ObservationStatus,
)
from ix_cognition_kernel.prediction import (
    PredictionDirection,
    prediction_set_from_causal_model,
)
from ix_cognition_kernel.skills import (
    SkillCandidate,
    SkillCandidateKind,
    SkillReuseEvidenceRecord,
)
from ix_cognition_kernel.state import (
    BeliefDisposition,
    BeliefRecord,
    BeliefState,
    ClaimRecord,
    EvidenceRecord,
    EvidenceStatus,
    UncertaintyStatus,
)


def belief_state() -> BeliefState:
    evidence = EvidenceRecord(
        evidence_id="ev-existing-belief",
        summary="Existing evidence anchors the initial belief before learning.",
        status=EvidenceStatus.VERIFIED,
        sources=("tests/test_learning_cycle.py",),
        supports_claim_ids=("claim-001",),
    )
    claim = ClaimRecord(
        claim_id="claim-001",
        statement="The cycle can update a belief from new evidence.",
        confidence=0.5,
        uncertainty=UncertaintyStatus.ASSUMED,
        evidence_ids=("ev-existing-belief",),
    )
    belief = BeliefRecord(
        belief_id="belief-001",
        claim=claim,
        provenance=("wave-1-snapshot",),
        rationale="The belief begins as assumed so Wave 2 can revise it.",
        disposition=BeliefDisposition.NEEDS_EVIDENCE,
    )
    return BeliefState(beliefs=(belief,), evidence=(evidence,))


def update_ledger() -> UpdateLedger:
    return UpdateLedger(
        events=(
            EvidenceEvent(
                event_id="event-support-001",
                summary="New evidence supports the target belief.",
                source="tests/test_learning_cycle.py",
                provenance=("wave-2-cycle",),
                target_claim_ids=("claim-001",),
                polarity=EvidenceEventPolarity.SUPPORTS,
                strength=0.8,
                audit_index=0,
                evidence_ids=("ev-support-001",),
            ),
        )
    )


def causal_model() -> SimpleCausalModel:
    assumption = CausalAssumption(
        assumption_id="assumption-001",
        cause_belief_id="belief-cause-001",
        effect_belief_id="belief-effect-001",
        relation=CausalRelation.ENABLES,
        rationale="The assumption predicts a concrete observation.",
        confidence=0.7,
        uncertainty=UncertaintyStatus.KNOWN,
        evidence_ids=("ev-causal-001",),
        constraint_ids=("constraint-001",),
        expected_observation_ids=("observation-001",),
        counterfactual_note_ids=("counterfactual-001",),
    )
    return SimpleCausalModel(
        model_id="causal-model-001",
        assumptions=(assumption,),
        constraints=(
            CausalConstraint(
                constraint_id="constraint-001",
                description="The assumption is scoped to a controlled Wave 2 cycle.",
                severity=ConstraintSeverity.CONTEXT,
                source_belief_ids=("belief-cause-001",),
            ),
        ),
        expected_observations=(
            ExpectedObservation(
                observation_id="observation-001",
                description="The expected observation becomes present.",
                linked_evidence_ids=("ev-causal-001",),
                required_for_validation=True,
            ),
        ),
        counterfactuals=(
            CounterfactualNote(
                note_id="counterfactual-001",
                scenario="If the assumption fails, the observation should not appear.",
                expected_difference="The observation would be absent.",
                uncertainty=UncertaintyStatus.KNOWN,
            ),
        ),
    )


def observation_ledger() -> ObservationLedger:
    return ObservationLedger(
        observations=(
            ObservationRecord(
                observation_id="observation-001",
                description="The prediction target was observed as present.",
                status=ObservationStatus.OBSERVED,
                observed_direction=PredictionDirection.PRESENT,
                confidence=0.9,
                evidence_ids=("ev-observation-001",),
                audit_index=1,
                source="tests/test_learning_cycle.py",
                provenance=("wave-2-cycle",),
            ),
        )
    )


def memory_candidate(
    *,
    evidence_ids: tuple[str, ...] = ("ev-memory-001",),
) -> MemoryCandidate:
    return MemoryCandidate(
        candidate_id="memory-candidate-001",
        kind=MemoryCandidateKind.OUTCOME_SUMMARY,
        content="The matched cycle outcome can be reused as bounded memory.",
        provenance=("wave-2-cycle",),
        evidence_ids=evidence_ids,
        source_outcome_ids=("outcome-cycle-001",),
        confidence=0.84,
        proposed_audit_index=1,
    )


def skill_candidate() -> SkillCandidate:
    return SkillCandidate(
        skill_id="skill-001",
        kind=SkillCandidateKind.PROCEDURE,
        name="Evidence update and causal revision cycle",
        procedure_steps=(
            "Apply belief updates from evidence events.",
            "Compare causal predictions with observations.",
            "Validate memory and skill only after accepted outcome evidence.",
        ),
        applicability_conditions=("accepted-outcome", "accepted-memory"),
        failure_modes=("missing-outcome-evidence", "memory-not-accepted"),
        source_memory_candidate_ids=("memory-candidate-001",),
        source_outcome_ids=("outcome-cycle-001",),
        confidence=0.86,
        provenance=("wave-2-cycle",),
        proposed_audit_index=2,
    )


def successful_skill_reuse() -> SkillReuseEvidenceRecord:
    return SkillReuseEvidenceRecord(
        reuse_id="reuse-001",
        skill_id="skill-001",
        outcome_id="outcome-cycle-001",
        evidence_ids=("ev-reuse-001",),
        succeeded=True,
        audit_index=2,
        applicability_condition_ids=("accepted-outcome",),
        failure_mode_ids=(),
        reasons=("The skill was reused successfully under the stated condition.",),
    )


def cycle_input(
    *,
    outcome_evidence_ids: tuple[str, ...] = ("ev-cycle-outcome",),
    memory_candidates: tuple[MemoryCandidate, ...] | None = None,
    skill_candidates: tuple[SkillCandidate, ...] | None = None,
    skill_reuse_records: tuple[SkillReuseEvidenceRecord, ...] | None = None,
) -> LearnableCognitionCycleInput:
    model = causal_model()
    return LearnableCognitionCycleInput(
        belief_state=belief_state(),
        causal_model=model,
        update_ledger=update_ledger(),
        prediction_set=prediction_set_from_causal_model(
            prediction_set_id="prediction-set-001",
            causal_model=model,
        ),
        observation_ledger=observation_ledger(),
        memory_candidates=(memory_candidate(),)
        if memory_candidates is None
        else memory_candidates,
        skill_candidates=(skill_candidate(),)
        if skill_candidates is None
        else skill_candidates,
        skill_reuse_records=(successful_skill_reuse(),)
        if skill_reuse_records is None
        else skill_reuse_records,
        outcome_id="outcome-cycle-001",
        outcome_summary="A bounded Wave 2 cycle produced accepted learning evidence.",
        outcome_evidence_ids=outcome_evidence_ids,
        current_audit_index=2,
    )


def test_learning_cycle_integrates_wave_two_artifacts() -> None:
    result = run_learnable_cognition_cycle(cycle_input())

    assert result.is_complete_learning_cycle is True
    assert result.readiness_gaps == ()
    assert result.changed_belief_ids == ("belief-001",)
    assert result.changed_assumption_ids == ("assumption-001",)
    assert result.outcome_record.outcome_id == "outcome-cycle-001"
    assert result.memory_ledger.accepted_candidates == (memory_candidate(),)
    assert result.skill_ledger.validated_candidates == (skill_candidate(),)
    assert result.after_belief_state.belief_by_id("belief-001").confidence == 0.7
    assert result.after_causal_model.assumption_by_id("assumption-001").confidence == (
        0.835
    )


def test_learning_cycle_reports_gap_when_outcome_learning_is_not_accepted() -> None:
    result = run_learnable_cognition_cycle(
        cycle_input(
            outcome_evidence_ids=(),
            memory_candidates=(),
            skill_candidates=(),
            skill_reuse_records=(),
        )
    )

    assert result.is_complete_learning_cycle is False
    assert "outcome-learning-record is not accepted" in result.readiness_gaps


def test_learning_cycle_reports_gap_when_memory_candidate_stays_quarantined() -> None:
    result = run_learnable_cognition_cycle(
        cycle_input(
            memory_candidates=(memory_candidate(evidence_ids=()),),
            skill_candidates=(),
            skill_reuse_records=(),
        )
    )

    assert result.memory_ledger.quarantined_candidates == (
        memory_candidate(evidence_ids=()),
    )
    assert "memory-quarantine-ledger did not accept every candidate" in (
        result.readiness_gaps
    )


def test_learning_cycle_reports_gap_when_skill_lacks_reuse_evidence() -> None:
    result = run_learnable_cognition_cycle(cycle_input(skill_reuse_records=()))

    assert result.skill_ledger.candidates_needing_reuse_evidence == (skill_candidate(),)
    assert "skill-validation-ledger did not validate every candidate" in (
        result.readiness_gaps
    )


def test_learning_cycle_input_rejects_prediction_set_for_wrong_model() -> None:
    model = causal_model()
    wrong_prediction_set = prediction_set_from_causal_model(
        prediction_set_id="prediction-set-001",
        causal_model=model,
    )
    wrong_prediction_set = wrong_prediction_set.__class__(
        prediction_set_id=wrong_prediction_set.prediction_set_id,
        source_model_id="wrong-model",
        predictions=wrong_prediction_set.predictions,
    )

    with pytest.raises(ValueError, match="prediction_set"):
        LearnableCognitionCycleInput(
            belief_state=belief_state(),
            causal_model=model,
            update_ledger=update_ledger(),
            prediction_set=wrong_prediction_set,
            observation_ledger=observation_ledger(),
            memory_candidates=(),
            skill_candidates=(),
            skill_reuse_records=(),
            outcome_id="outcome-cycle-001",
            outcome_summary="Prediction-set mismatch should fail closed.",
            outcome_evidence_ids=("ev-cycle-outcome",),
            current_audit_index=2,
        )
