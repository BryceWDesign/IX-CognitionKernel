import pytest

from ix_cognition_kernel.wave7_experience_compiler import (
    ExperienceRecord,
    FutureConstraintStrength,
    FutureReasoningConstraint,
    LearningDelta,
    LearningDeltaKind,
    MemoryPatch,
    PredictionOutcomeDelta,
)
from ix_cognition_kernel.wave7_observation_action_schema import (
    ActionIntent,
    ActionIntentKind,
    ActionProposalEnvelope,
    EvidenceRequirementStatus,
    ObservationActionTrace,
    ObservationFrame,
    ObservationReliability,
    ObservedOutcome,
    OutcomeAlignment,
    ProposalEvidenceRequirement,
    ProposalReadiness,
    ProposalRisk,
)
from ix_cognition_kernel.wave7_prediction_outcome_lifecycle import (
    BoundedPrediction,
    OutcomeDeltaReview,
    OutcomeDeltaSeverity,
    PredictionConfidence,
    PredictionEvidenceGate,
    PredictionLifecycleDecision,
    PredictionOutcomeLifecycle,
    PredictionTrialPlan,
    TrialBoundary,
    build_outcome_delta_review,
    build_prediction_lifecycle_report,
    build_prediction_outcome_lifecycle,
)


def _prediction() -> BoundedPrediction:
    return BoundedPrediction(
        prediction_id="prediction-1",
        subject_id="bounded-trial-1",
        predicted_outcome="The simulation should preserve the safety boundary.",
        claim_scope="bounded simulation only",
        assumptions=("surface remains deterministic",),
        uncertainty_ids=("uncertainty-transfer-1",),
        evidence_ids=("prediction-evidence-1",),
        confidence=PredictionConfidence.MODERATE,
    )


def _gate(
    *,
    supplied: tuple[str, ...] = (
        "prediction-evidence-1",
        "trial-evidence-1",
    ),
) -> PredictionEvidenceGate:
    return PredictionEvidenceGate(
        gate_id="gate-1",
        prediction_id="prediction-1",
        required_evidence_ids=("prediction-evidence-1", "trial-evidence-1"),
        supplied_evidence_ids=supplied,
        authority_refs=("human-authority-1",),
        evidence_notes=("Evidence gate controls trial entry.",),
    )


def _trial_plan() -> PredictionTrialPlan:
    return PredictionTrialPlan(
        trial_id="trial-1",
        prediction_id="prediction-1",
        boundary=TrialBoundary.SIMULATION_ONLY,
        operation="simulate-trial",
        success_criteria=("boundary preserved",),
        failure_criteria=("boundary violated",),
        evidence_ids=("trial-evidence-1",),
        authority_refs=("human-authority-1",),
    )


def _observation() -> ObservationFrame:
    return ObservationFrame(
        frame_id="frame-1",
        surface_id="surface-sim-1",
        channel_id="channel-sim-1",
        observed_state_ids=("state-policy-1",),
        observation_summary="The bounded simulation state was measured.",
        evidence_ids=("observation-evidence-1",),
        reliability=ObservationReliability.MEASURED,
        captured_after_action_id="prior-action-1",
    )


def _intent() -> ActionIntent:
    return ActionIntent(
        intent_id="intent-1",
        kind=ActionIntentKind.SIMULATE,
        surface_id="surface-sim-1",
        requested_operation="simulate-trial",
        purpose="Run a bounded simulation before runtime handoff.",
        expected_state_change="Simulation should preserve the boundary.",
        evidence_ids=("intent-evidence-1",),
        originating_observation_ids=("frame-1",),
    )


def _envelope() -> ActionProposalEnvelope:
    return ActionProposalEnvelope(
        envelope_id="envelope-1",
        intent=_intent(),
        observations=(_observation(),),
        evidence_requirements=(
            ProposalEvidenceRequirement(
                requirement_id="requirement-1",
                description="Prediction and surface evidence are required.",
                required_evidence_kinds=("prediction", "bounded-surface"),
                satisfied_evidence_ids=("requirement-evidence-1",),
                status=EvidenceRequirementStatus.SATISFIED,
            ),
            ProposalEvidenceRequirement(
                requirement_id="requirement-review-1",
                description="Human review authority is required.",
                required_evidence_kinds=("human-review",),
                satisfied_evidence_ids=(),
                status=EvidenceRequirementStatus.REQUIRES_REVIEW,
                authority_refs=("human-authority-1",),
            ),
        ),
        risk=ProposalRisk.MODERATE,
        predicted_outcome="The simulation should preserve the safety boundary.",
        readiness=ProposalReadiness.READY_FOR_REVIEW,
    )


def _outcome(
    *,
    alignment: OutcomeAlignment = OutcomeAlignment.MATCHED,
    lesson: str = "",
) -> ObservedOutcome:
    return ObservedOutcome(
        outcome_id="outcome-1",
        envelope_id="envelope-1",
        outcome_summary="The bounded simulation preserved the expected boundary.",
        evidence_ids=("outcome-evidence-1",),
        alignment=alignment,
        measured_state_ids=("state-policy-1",),
        lesson=lesson,
    )


def _trace(
    *,
    alignment: OutcomeAlignment = OutcomeAlignment.MATCHED,
    lesson: str = "",
) -> ObservationActionTrace:
    return ObservationActionTrace(
        trace_id="trace-1",
        envelope=_envelope(),
        outcome=_outcome(alignment=alignment, lesson=lesson),
    )


def _experience_record(trace: ObservationActionTrace) -> ExperienceRecord:
    from ix_cognition_kernel.wave7_experience_compiler import (
        ExperienceCompilationDecision,
    )

    delta = PredictionOutcomeDelta(
        delta_id="delta-1",
        prediction_id="prediction-1",
        predicted_outcome="The simulation should preserve the safety boundary.",
        observed_outcome="The bounded simulation preserved the expected boundary.",
        alignment=trace.outcome.alignment
        if trace.outcome
        else OutcomeAlignment.MATCHED,
        delta_summary="Measured outcome matched prediction.",
        evidence_ids=("delta-evidence-1",),
        lesson=trace.outcome.lesson if trace.outcome else "",
    )
    learning = LearningDelta(
        learning_id="learning-1",
        kind=LearningDeltaKind.CONFIRMATION,
        source_delta_id="delta-1",
        summary="Experience confirmed the bounded prediction.",
        evidence_ids=("learning-evidence-1",),
        affected_belief_ids=("belief-1",),
    )
    patch = MemoryPatch(
        patch_id="patch-1",
        source_learning_id="learning-1",
        target_memory_id="memory-1",
        patch_summary="Quarantine confirmation before trusting memory.",
        evidence_ids=("patch-evidence-1",),
    )
    constraint = FutureReasoningConstraint(
        constraint_id="constraint-1",
        source_learning_id="learning-1",
        rule="Reuse only with matching evidence.",
        strength=FutureConstraintStrength.ADVISORY,
        applies_to_domains=("bounded simulation",),
        evidence_ids=("constraint-evidence-1",),
        authority_refs=("human-authority-1",),
    )
    return ExperienceRecord(
        record_id="experience-1",
        trace=trace,
        delta=delta,
        learning_delta=learning,
        memory_patches=(patch,),
        future_constraints=(constraint,),
        decision=ExperienceCompilationDecision.READY_FOR_REVIEW,
    )


def test_bounded_prediction_requires_evidence_and_rejects_truth_claims() -> None:
    prediction = _prediction()

    assert prediction.confidence is PredictionConfidence.MODERATE
    assert not prediction.review_required
    assert prediction.fingerprint() == prediction.fingerprint()
    assert len(prediction.fingerprint()) == 64

    with pytest.raises(ValueError, match="must not claim truth"):
        BoundedPrediction(
            prediction_id="prediction-truth",
            subject_id="bounded-trial-1",
            predicted_outcome="Bad truth claim.",
            claim_scope="bounded simulation only",
            assumptions=("surface remains deterministic",),
            uncertainty_ids=("uncertainty-transfer-1",),
            evidence_ids=("prediction-evidence-1",),
            claims_truth=True,
        )


def test_bounded_prediction_rejects_execution_authority() -> None:
    with pytest.raises(ValueError, match="must not grant execution authority"):
        BoundedPrediction(
            prediction_id="prediction-authority",
            subject_id="bounded-trial-1",
            predicted_outcome="Bad authority claim.",
            claim_scope="bounded simulation only",
            assumptions=("surface remains deterministic",),
            uncertainty_ids=("uncertainty-transfer-1",),
            evidence_ids=("prediction-evidence-1",),
            grants_execution_authority=True,
        )


def test_prediction_evidence_gate_reports_missing_evidence() -> None:
    gate = _gate(supplied=("prediction-evidence-1",))

    assert not gate.satisfied
    assert gate.missing_evidence_ids == ("trial-evidence-1",)
    assert gate.fingerprint() == gate.fingerprint()
    assert len(gate.fingerprint()) == 64


def test_prediction_trial_plan_is_bounded_and_never_deployment() -> None:
    plan = _trial_plan()

    assert plan.simulation_only
    assert plan.fingerprint() == plan.fingerprint()
    assert len(plan.fingerprint()) == 64

    with pytest.raises(ValueError, match="must not permit deployment"):
        PredictionTrialPlan(
            trial_id="trial-deploy",
            prediction_id="prediction-1",
            boundary=TrialBoundary.SIMULATION_ONLY,
            operation="simulate-trial",
            success_criteria=("boundary preserved",),
            failure_criteria=("boundary violated",),
            evidence_ids=("trial-evidence-1",),
            authority_refs=("human-authority-1",),
            permits_deployment=True,
        )


def test_build_outcome_delta_review_from_measured_trace() -> None:
    review = build_outcome_delta_review(
        review_id="review-1",
        prediction=_prediction(),
        trace=_trace(),
    )

    assert review.severity is OutcomeDeltaSeverity.NONE
    assert not review.blocks_claim
    assert not review.changes_future_reasoning
    assert review.fingerprint() == review.fingerprint()
    assert len(review.fingerprint()) == 64


def test_outcome_delta_review_requires_lesson_for_material_delta() -> None:
    review = build_outcome_delta_review(
        review_id="review-partial",
        prediction=_prediction(),
        trace=_trace(
            alignment=OutcomeAlignment.PARTIAL,
            lesson="Future reasoning must check the missing condition first.",
        ),
    )

    assert review.severity is OutcomeDeltaSeverity.MODERATE
    assert review.changes_future_reasoning

    with pytest.raises(ValueError, match="require a lesson"):
        OutcomeDeltaReview(
            review_id="review-bad",
            prediction_id="prediction-1",
            trace_id="trace-1",
            alignment=OutcomeAlignment.MISMATCHED,
            severity=OutcomeDeltaSeverity.BLOCKING,
            summary="Measured outcome contradicted prediction.",
            evidence_ids=("outcome-evidence-1",),
        )


def test_lifecycle_ready_for_review_when_gate_trace_and_experience_exist() -> None:
    trace = _trace()
    lifecycle = build_prediction_outcome_lifecycle(
        lifecycle_id="lifecycle-1",
        prediction=_prediction(),
        evidence_gate=_gate(),
        trial_plan=_trial_plan(),
        trace=trace,
        experience_record=_experience_record(trace),
        notes=("Prediction lifecycle is replayable.",),
    )

    assert lifecycle.ready_for_review
    assert lifecycle.measured
    assert not lifecycle.blocks_claim
    assert not lifecycle.changes_future_reasoning
    assert lifecycle.missing_evidence_ids == ()
    assert "prediction-evidence-1" in lifecycle.evidence_ids
    assert "outcome-evidence-1" in lifecycle.evidence_ids
    assert lifecycle.fingerprint() == lifecycle.fingerprint()
    assert len(lifecycle.fingerprint()) == 64


def test_lifecycle_needs_more_evidence_when_gate_is_missing_evidence() -> None:
    trace = _trace()
    lifecycle = build_prediction_outcome_lifecycle(
        lifecycle_id="lifecycle-missing-evidence",
        prediction=_prediction(),
        evidence_gate=_gate(supplied=("prediction-evidence-1",)),
        trial_plan=_trial_plan(),
        trace=trace,
        experience_record=_experience_record(trace),
    )

    assert lifecycle.decision is PredictionLifecycleDecision.NEEDS_MORE_EVIDENCE
    assert lifecycle.missing_evidence_ids == ("trial-evidence-1",)
    assert lifecycle.blocks_claim


def test_lifecycle_needs_measured_outcome_when_trace_missing() -> None:
    lifecycle = build_prediction_outcome_lifecycle(
        lifecycle_id="lifecycle-no-trace",
        prediction=_prediction(),
        evidence_gate=_gate(),
        trial_plan=_trial_plan(),
    )

    assert lifecycle.decision is PredictionLifecycleDecision.NEEDS_MEASURED_OUTCOME
    assert not lifecycle.measured
    assert not lifecycle.ready_for_review


def test_lifecycle_blocks_when_outcome_delta_blocks_claim() -> None:
    trace = _trace(
        alignment=OutcomeAlignment.MISMATCHED,
        lesson="Future reasoning must block this assumption until revalidated.",
    )
    lifecycle = build_prediction_outcome_lifecycle(
        lifecycle_id="lifecycle-blocked",
        prediction=_prediction(),
        evidence_gate=_gate(),
        trial_plan=_trial_plan(),
        trace=trace,
        experience_record=None,
    )

    assert lifecycle.decision is PredictionLifecycleDecision.BLOCKED
    assert lifecycle.blocks_claim
    assert "outcome-delta-blocks-claim" in lifecycle.blocking_reason_ids
    assert lifecycle.changes_future_reasoning


def test_lifecycle_rejects_bad_gate_link() -> None:
    bad_gate = PredictionEvidenceGate(
        gate_id="gate-bad-link",
        prediction_id="prediction-other",
        required_evidence_ids=("prediction-evidence-1",),
        supplied_evidence_ids=("prediction-evidence-1",),
        authority_refs=("human-authority-1",),
    )

    with pytest.raises(ValueError, match="must reference prediction id"):
        PredictionOutcomeLifecycle(
            lifecycle_id="lifecycle-bad-gate",
            prediction=_prediction(),
            evidence_gate=bad_gate,
            trial_plan=_trial_plan(),
            trace=None,
            outcome_review=None,
            experience_record=None,
            decision=PredictionLifecycleDecision.NEEDS_MEASURED_OUTCOME,
        )


def test_report_preserves_review_ready_and_blocked_lifecycles() -> None:
    ready_trace = _trace()
    ready_lifecycle = build_prediction_outcome_lifecycle(
        lifecycle_id="lifecycle-ready",
        prediction=_prediction(),
        evidence_gate=_gate(),
        trial_plan=_trial_plan(),
        trace=ready_trace,
        experience_record=_experience_record(ready_trace),
    )
    blocked_trace = _trace(
        alignment=OutcomeAlignment.MISMATCHED,
        lesson="Future reasoning must block this assumption until revalidated.",
    )
    blocked_lifecycle = build_prediction_outcome_lifecycle(
        lifecycle_id="lifecycle-blocked",
        prediction=_prediction(),
        evidence_gate=_gate(),
        trial_plan=_trial_plan(),
        trace=blocked_trace,
        experience_record=None,
    )
    report = build_prediction_lifecycle_report(
        report_id="prediction-report-1",
        lifecycles=(ready_lifecycle, blocked_lifecycle),
        decision=PredictionLifecycleDecision.BLOCKED,
        notes=("Blocked lifecycle remains visible.",),
    )

    assert report.lifecycle_ids == ("lifecycle-blocked", "lifecycle-ready")
    assert report.review_ready_lifecycle_ids == ("lifecycle-ready",)
    assert report.blocking_lifecycle_ids == ("lifecycle-blocked",)
    assert report.future_reasoning_lifecycle_ids == ("lifecycle-blocked",)
    assert report.blocks_claim
    assert not report.ready_for_review
    assert "prediction-evidence-1" in report.evidence_ids
    assert report.fingerprint() == report.fingerprint()
    assert len(report.fingerprint()) == 64
