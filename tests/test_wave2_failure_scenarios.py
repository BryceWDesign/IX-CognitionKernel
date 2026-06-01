import pytest

from ix_cognition_kernel.causal import (
    CausalAssumption,
    CausalRelation,
    ExpectedObservation,
    SimpleCausalModel,
)
from ix_cognition_kernel.history import BeliefRevisionKind, build_belief_history
from ix_cognition_kernel.learning import (
    EvidenceEvent,
    EvidenceEventPolarity,
    StalenessPolicy,
    UpdateLedger,
    apply_belief_updates,
)
from ix_cognition_kernel.memory import (
    MemoryCandidate,
    MemoryCandidateKind,
    MemoryQuarantinePolicy,
    MemoryValidationStatus,
    evaluate_memory_candidate,
    evaluate_memory_quarantine,
)
from ix_cognition_kernel.observations import (
    ObservationLedger,
    ObservationRecord,
    ObservationStatus,
    PredictionComparisonResult,
    compare_prediction_set_to_observations,
)
from ix_cognition_kernel.outcome import (
    OutcomeLearningRecord,
    OutcomeLearningStatus,
    OutcomePressure,
    build_outcome_learning_record,
    outcome_learning_ledger,
)
from ix_cognition_kernel.prediction import (
    PredictionDirection,
    prediction_set_from_causal_model,
)
from ix_cognition_kernel.purpose import (
    PurposeAssessmentInput,
    PurposeRule,
    assess_non_attached_purpose,
)
from ix_cognition_kernel.revision import (
    CausalRevisionAction,
    CausalRevisionResult,
    revise_causal_assumptions,
)
from ix_cognition_kernel.skills import (
    SkillCandidate,
    SkillCandidateKind,
    SkillValidationStatus,
    evaluate_skill_candidate,
)
from ix_cognition_kernel.state import (
    BeliefDisposition,
    BeliefRecord,
    BeliefState,
    ClaimRecord,
    EvidenceRecord,
    EvidenceStatus,
    HumanAuthority,
    UncertaintyStatus,
)


def belief_state(
    *,
    confidence: float = 0.8,
    uncertainty: UncertaintyStatus = UncertaintyStatus.KNOWN,
    disposition: BeliefDisposition = BeliefDisposition.ACTIVE,
) -> BeliefState:
    evidence = EvidenceRecord(
        evidence_id="ev-belief-existing",
        summary="Existing evidence anchors the starting belief.",
        status=EvidenceStatus.VERIFIED,
        sources=("tests/test_wave2_failure_scenarios.py",),
        supports_claim_ids=("claim-001",),
    )
    claim = ClaimRecord(
        claim_id="claim-001",
        statement="The belief must survive adversarial Wave 2 update pressure.",
        confidence=confidence,
        uncertainty=uncertainty,
        evidence_ids=("ev-belief-existing",),
    )
    belief = BeliefRecord(
        belief_id="belief-001",
        claim=claim,
        provenance=("wave-2-failure-scenario",),
        rationale="The belief starts valid so failure pressure can change it.",
        disposition=disposition,
    )
    return BeliefState(beliefs=(belief,), evidence=(evidence,))


def support_event(*, audit_index: int = 0) -> EvidenceEvent:
    return EvidenceEvent(
        event_id="event-support-001",
        summary="A support event creates positive evidence context.",
        source="tests/test_wave2_failure_scenarios.py",
        provenance=("wave-2-failure-scenario",),
        target_claim_ids=("claim-001",),
        polarity=EvidenceEventPolarity.SUPPORTS,
        strength=0.4,
        audit_index=audit_index,
        evidence_ids=("ev-support-001",),
    )


def contradiction_event(*, audit_index: int = 1) -> EvidenceEvent:
    return EvidenceEvent(
        event_id="event-contradict-001",
        summary="A contradiction event challenges the same claim.",
        source="tests/test_wave2_failure_scenarios.py",
        provenance=("wave-2-failure-scenario",),
        target_claim_ids=("claim-001",),
        polarity=EvidenceEventPolarity.CONTRADICTS,
        strength=0.95,
        audit_index=audit_index,
        evidence_ids=("ev-contradict-001",),
    )


def causal_model(*, confidence: float = 0.55) -> SimpleCausalModel:
    assumption = CausalAssumption(
        assumption_id="assumption-001",
        cause_belief_id="belief-cause-001",
        effect_belief_id="belief-effect-001",
        relation=CausalRelation.ENABLES,
        rationale="The assumption should weaken when prediction evidence diverges.",
        confidence=confidence,
        uncertainty=UncertaintyStatus.KNOWN,
        evidence_ids=("ev-causal-001",),
        constraint_ids=(),
        expected_observation_ids=("observation-001",),
        counterfactual_note_ids=(),
    )
    observation = ExpectedObservation(
        observation_id="observation-001",
        description="The expected observation should become present.",
        linked_evidence_ids=("ev-causal-001",),
        required_for_validation=True,
    )
    return SimpleCausalModel(
        model_id="causal-model-001",
        assumptions=(assumption,),
        constraints=(),
        expected_observations=(observation,),
        counterfactuals=(),
    )


def diverging_observation_ledger() -> ObservationLedger:
    return ObservationLedger(
        observations=(
            ObservationRecord(
                observation_id="observation-001",
                description="The actual observation diverged from the prediction.",
                status=ObservationStatus.OBSERVED,
                observed_direction=PredictionDirection.ABSENT,
                confidence=1.0,
                evidence_ids=("ev-observation-diverged",),
                audit_index=0,
                source="tests/test_wave2_failure_scenarios.py",
                provenance=("wave-2-failure-scenario",),
            ),
        )
    )


def accepted_outcome(outcome_id: str = "outcome-accepted-001") -> OutcomeLearningRecord:
    return OutcomeLearningRecord(
        outcome_id=outcome_id,
        summary="Accepted outcome used only for quarantine and skill pressure tests.",
        status=OutcomeLearningStatus.ACCEPTED,
        pressure=OutcomePressure.CONFIRMED,
        belief_revision_ids=("revision-accepted",),
        causal_revision_ids=("causal-revision-accepted",),
        prediction_comparison_ids=("comparison-accepted",),
        evidence_ids=("ev-outcome-accepted",),
        learning_summary="Accepted evidence-backed outcome.",
        reasons=("Outcome was accepted with evidence.",),
    )


def memory_candidate(
    *,
    candidate_id: str = "memory-candidate-001",
    evidence_ids: tuple[str, ...] = ("ev-memory-001",),
    source_outcome_ids: tuple[str, ...] = ("outcome-accepted-001",),
    confidence: float = 0.82,
) -> MemoryCandidate:
    return MemoryCandidate(
        candidate_id=candidate_id,
        kind=MemoryCandidateKind.OUTCOME_SUMMARY,
        content="Only accepted, evidence-backed outcome summaries may become memory.",
        provenance=("wave-2-failure-scenario",),
        evidence_ids=evidence_ids,
        source_outcome_ids=source_outcome_ids,
        confidence=confidence,
        proposed_audit_index=0,
    )


def skill_candidate() -> SkillCandidate:
    return SkillCandidate(
        skill_id="skill-001",
        kind=SkillCandidateKind.PROCEDURE,
        name="Evidence-backed outcome reuse procedure",
        procedure_steps=(
            "Use only accepted outcome evidence.",
            "Require accepted memory before skill validation.",
            "Reject reuse if failure modes appear.",
        ),
        applicability_conditions=("accepted-outcome", "accepted-memory"),
        failure_modes=("missing-reuse-evidence", "memory-not-accepted"),
        source_memory_candidate_ids=("memory-candidate-001",),
        source_outcome_ids=("outcome-accepted-001",),
        confidence=0.82,
        provenance=("wave-2-failure-scenario",),
        proposed_audit_index=1,
    )


def test_contradictory_evidence_blocks_belief_and_history_records_failure() -> None:
    result = apply_belief_updates(
        belief_state(),
        UpdateLedger(events=(support_event(), contradiction_event())),
    )
    updated_belief = result.after_state.belief_by_id("belief-001")
    history = build_belief_history(result)
    revision = history.blocking_revisions[0]

    assert updated_belief.uncertainty is UncertaintyStatus.DISPUTED
    assert updated_belief.disposition is BeliefDisposition.BLOCKED
    assert updated_belief.claim.contradicted_by == ("event-contradict-001",)
    assert result.contradiction_assessment.has_blocking_conflicts is True
    assert revision.kind is BeliefRevisionKind.CONTRADICTED
    assert revision.blocks_belief is True


def test_stale_belief_blocks_outcome_learning_and_rejects_memory() -> None:
    update_result = apply_belief_updates(
        belief_state(),
        UpdateLedger(events=(support_event(),)),
        current_audit_index=3,
        staleness_policy=StalenessPolicy(stale_after_audit_gap=3),
    )
    history = build_belief_history(update_result)
    model = causal_model()
    comparison_ledger = compare_prediction_set_to_observations(
        prediction_set=prediction_set_from_causal_model(
            prediction_set_id="prediction-set-001",
            causal_model=model,
        ),
        observations=ObservationLedger(observations=()),
    )
    causal_result = CausalRevisionResult(
        before_model=model,
        after_model=model,
        comparison_ledger=comparison_ledger,
        revisions=(),
    )
    outcome_record = build_outcome_learning_record(
        outcome_id="outcome-stale-001",
        summary="Stale belief history should block accepted outcome learning.",
        belief_history=history,
        causal_revision_result=causal_result,
        comparison_ledger=comparison_ledger,
        evidence_ids=("ev-outcome-stale",),
    )
    memory_validation = evaluate_memory_candidate(
        candidate=memory_candidate(source_outcome_ids=("outcome-stale-001",)),
        outcome_ledger=outcome_learning_ledger(outcome_record),
        current_audit_index=4,
    )

    assert history.stale_revisions[0].kind is BeliefRevisionKind.STALE
    assert outcome_record.status is OutcomeLearningStatus.BLOCKED
    assert memory_validation.status is MemoryValidationStatus.REJECTED


def test_false_prediction_disputes_causal_assumption_under_pressure() -> None:
    model = causal_model(confidence=0.55)
    comparison_ledger = compare_prediction_set_to_observations(
        prediction_set=prediction_set_from_causal_model(
            prediction_set_id="prediction-set-001",
            causal_model=model,
        ),
        observations=diverging_observation_ledger(),
    )
    revision_result = revise_causal_assumptions(model, comparison_ledger)
    revision = revision_result.revisions[0]
    revised_assumption = revision_result.after_model.assumption_by_id("assumption-001")

    assert comparison_ledger.diverged_comparisons[0].result is (
        PredictionComparisonResult.DIVERGED
    )
    assert revision.action is CausalRevisionAction.DISPUTED
    assert revision.blocks_assumption is True
    assert revised_assumption.uncertainty is UncertaintyStatus.DISPUTED


def test_raw_memory_without_evidence_cannot_become_durable() -> None:
    ledger = evaluate_memory_quarantine(
        candidates=(memory_candidate(evidence_ids=()),),
        outcome_ledger=outcome_learning_ledger(accepted_outcome()),
        current_audit_index=1,
    )

    assert ledger.accepted_candidates == ()
    assert ledger.quarantined_candidates == (memory_candidate(evidence_ids=()),)
    assert "lacks evidence ids" in ledger.validations[0].reasons[0]


def test_skill_without_reuse_evidence_is_not_validated() -> None:
    memory_ledger = evaluate_memory_quarantine(
        candidates=(memory_candidate(),),
        outcome_ledger=outcome_learning_ledger(accepted_outcome()),
        current_audit_index=1,
    )
    validation = evaluate_skill_candidate(
        candidate=skill_candidate(),
        reuse_records=(),
        memory_ledger=memory_ledger,
        outcome_ledger=outcome_learning_ledger(accepted_outcome()),
    )

    assert memory_ledger.accepted_candidates == (memory_candidate(),)
    assert validation.status is SkillValidationStatus.NEEDS_REUSE_EVIDENCE
    assert "lacks required successful reuse evidence" in validation.reasons[0]


def test_high_confidence_without_evidence_and_agi_claim_are_blocked() -> None:
    unsupported = assess_non_attached_purpose(
        PurposeAssessmentInput(
            statement="A high-confidence claim without evidence must fail.",
            wave_number=2,
            confidence=0.91,
            evidence_ids=(),
            uncertainty=UncertaintyStatus.KNOWN,
            uncertainty_disclosed=True,
            human_authority=HumanAuthority.REQUIRED,
        )
    )
    agi_claim = assess_non_attached_purpose(
        PurposeAssessmentInput(
            statement="AGI achieved by this Wave 2 system.",
            wave_number=2,
            confidence=0.9,
            evidence_ids=("ev-claim",),
            uncertainty=UncertaintyStatus.KNOWN,
            uncertainty_disclosed=True,
            human_authority=HumanAuthority.REQUIRED,
        )
    )

    assert unsupported.passes is False
    assert unsupported.result_for_rule(
        PurposeRule.EVIDENCE_OVER_CONFIDENCE
    ).is_violation
    assert agi_claim.passes is False
    assert agi_claim.result_for_rule(
        PurposeRule.NO_AGI_CLAIM_WITHOUT_EVIDENCE
    ).is_violation


def test_memory_quarantine_expiry_policy_fails_closed() -> None:
    validation = evaluate_memory_candidate(
        candidate=memory_candidate(),
        outcome_ledger=outcome_learning_ledger(accepted_outcome()),
        current_audit_index=6,
        policy=MemoryQuarantinePolicy(expire_after_audit_gap=6),
    )

    assert validation.status is MemoryValidationStatus.EXPIRED
    assert validation.is_blocking_status is True
    assert "expired after audit gap 6" in validation.reasons[0]


@pytest.mark.parametrize(
    "bad_confidence",
    (-0.01, 1.01),
)
def test_memory_candidate_confidence_bounds_fail_closed(bad_confidence: float) -> None:
    with pytest.raises(ValueError, match="between 0.0 and 1.0"):
        memory_candidate(confidence=bad_confidence)
