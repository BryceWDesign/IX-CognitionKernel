import pytest

from ix_cognition_kernel.wave7_experience_compiler import (
    ExperienceCompilationDecision,
    FutureConstraintStrength,
    FutureReasoningConstraint,
    LearningDelta,
    LearningDeltaKind,
    MemoryPatch,
    MemoryPatchStatus,
    PredictionOutcomeDelta,
    build_experience_compilation_report,
    compile_experience_record,
)
from ix_cognition_kernel.wave7_observation_action_schema import (
    ActionIntent,
    ActionIntentKind,
    ActionProposalEnvelope,
    EvidenceRequirementStatus,
    ObservedOutcome,
    ObservationActionTrace,
    ObservationFrame,
    ObservationReliability,
    OutcomeAlignment,
    ProposalEvidenceRequirement,
    ProposalReadiness,
    ProposalRisk,
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


def _requirement() -> ProposalEvidenceRequirement:
    return ProposalEvidenceRequirement(
        requirement_id="requirement-1",
        description="Prediction and bounded-surface evidence are required.",
        required_evidence_kinds=("prediction", "bounded-surface"),
        satisfied_evidence_ids=("requirement-evidence-1",),
        status=EvidenceRequirementStatus.SATISFIED,
    )


def _envelope() -> ActionProposalEnvelope:
    return ActionProposalEnvelope(
        envelope_id="envelope-1",
        intent=_intent(),
        observations=(_observation(),),
        evidence_requirements=(
            _requirement(),
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
    measured_state_ids: tuple[str, ...] = ("state-policy-1",),
) -> ObservedOutcome:
    return ObservedOutcome(
        outcome_id="outcome-1",
        envelope_id="envelope-1",
        outcome_summary="The bounded simulation preserved the expected boundary.",
        evidence_ids=("outcome-evidence-1",),
        alignment=alignment,
        measured_state_ids=measured_state_ids,
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
        notes=("Trace is measured and replayable.",),
    )


def test_prediction_outcome_delta_requires_measured_outcome() -> None:
    delta = PredictionOutcomeDelta(
        delta_id="delta-1",
        prediction_id="prediction-1",
        predicted_outcome="Boundary should hold.",
        observed_outcome="Boundary held.",
        alignment=OutcomeAlignment.MATCHED,
        delta_summary="Measured outcome matched prediction.",
        evidence_ids=("delta-evidence-1",),
    )

    assert delta.confirms_prediction
    assert not delta.changes_future_reasoning
    assert not delta.blocks_stronger_claim
    assert delta.fingerprint() == delta.fingerprint()
    assert len(delta.fingerprint()) == 64

    with pytest.raises(ValueError, match="require measured outcomes"):
        PredictionOutcomeDelta(
            delta_id="delta-unmeasured",
            prediction_id="prediction-1",
            predicted_outcome="Boundary should hold.",
            observed_outcome="No measurement.",
            alignment=OutcomeAlignment.NOT_MEASURED,
            delta_summary="Outcome was not measured.",
            evidence_ids=("delta-evidence-1",),
        )


def test_partial_or_mismatched_delta_requires_lesson() -> None:
    partial = PredictionOutcomeDelta(
        delta_id="delta-partial",
        prediction_id="prediction-1",
        predicted_outcome="Boundary should hold.",
        observed_outcome="Boundary held only under one condition.",
        alignment=OutcomeAlignment.PARTIAL,
        delta_summary="Measured outcome partially matched prediction.",
        evidence_ids=("delta-evidence-1",),
        lesson="Future reasoning must test the missing condition first.",
    )

    assert partial.changes_future_reasoning

    with pytest.raises(ValueError, match="require a lesson"):
        PredictionOutcomeDelta(
            delta_id="delta-mismatch",
            prediction_id="prediction-1",
            predicted_outcome="Boundary should hold.",
            observed_outcome="Boundary failed.",
            alignment=OutcomeAlignment.MISMATCHED,
            delta_summary="Measured outcome contradicted prediction.",
            evidence_ids=("delta-evidence-1",),
        )


def test_learning_delta_requires_affected_belief_or_skill() -> None:
    learning = LearningDelta(
        learning_id="learning-1",
        kind=LearningDeltaKind.CORRECTION,
        source_delta_id="delta-1",
        summary="Future reasoning must adjust the causal assumption.",
        evidence_ids=("learning-evidence-1",),
        affected_belief_ids=("belief-1",),
    )

    assert learning.corrective
    assert learning.fingerprint() == learning.fingerprint()
    assert len(learning.fingerprint()) == 64

    with pytest.raises(ValueError, match="affected belief or skill ids"):
        LearningDelta(
            learning_id="learning-empty",
            kind=LearningDeltaKind.CORRECTION,
            source_delta_id="delta-1",
            summary="Bad empty learning.",
            evidence_ids=("learning-evidence-1",),
            affected_belief_ids=(),
            affected_skill_ids=(),
        )


def test_memory_patch_is_quarantined_by_default_and_not_self_approved() -> None:
    patch = MemoryPatch(
        patch_id="patch-1",
        source_learning_id="learning-1",
        target_memory_id="memory-1",
        patch_summary="Quarantine correction until human review.",
        evidence_ids=("patch-evidence-1",),
    )

    assert patch.quarantined
    assert patch.blocks_trusted_memory
    assert not patch.accepted
    assert patch.fingerprint() == patch.fingerprint()
    assert len(patch.fingerprint()) == 64

    with pytest.raises(ValueError, match="must not self-approve"):
        MemoryPatch(
            patch_id="patch-self-approved",
            source_learning_id="learning-1",
            target_memory_id="memory-1",
            patch_summary="Bad self approval.",
            evidence_ids=("patch-evidence-1",),
            self_approved=True,
        )

    with pytest.raises(ValueError, match="must not treat memory as truth"):
        MemoryPatch(
            patch_id="patch-memory-truth",
            source_learning_id="learning-1",
            target_memory_id="memory-1",
            patch_summary="Bad memory truth.",
            evidence_ids=("patch-evidence-1",),
            treats_memory_as_truth=True,
        )


def test_accepted_memory_patch_requires_human_review_ref() -> None:
    accepted = MemoryPatch(
        patch_id="patch-accepted",
        source_learning_id="learning-1",
        target_memory_id="memory-1",
        patch_summary="Human review accepted correction.",
        evidence_ids=("patch-evidence-1",),
        status=MemoryPatchStatus.ACCEPTED_BY_HUMAN_REVIEW,
        human_review_ref="review-1",
    )

    assert accepted.accepted
    assert not accepted.blocks_trusted_memory

    with pytest.raises(ValueError, match="require human_review_ref"):
        MemoryPatch(
            patch_id="patch-accepted-bad",
            source_learning_id="learning-1",
            target_memory_id="memory-1",
            patch_summary="Missing review ref.",
            evidence_ids=("patch-evidence-1",),
            status=MemoryPatchStatus.ACCEPTED_BY_HUMAN_REVIEW,
        )


def test_future_reasoning_constraint_requires_evidence_and_authority() -> None:
    constraint = FutureReasoningConstraint(
        constraint_id="constraint-1",
        source_learning_id="learning-1",
        rule="Check the missing condition before reusing this assumption.",
        strength=FutureConstraintStrength.REQUIRED_CHECK,
        applies_to_domains=("bounded simulation",),
        evidence_ids=("constraint-evidence-1",),
        authority_refs=("human-authority-1",),
    )

    assert not constraint.blocks_future_action
    assert constraint.fingerprint() == constraint.fingerprint()
    assert len(constraint.fingerprint()) == 64

    with pytest.raises(ValueError, match="require authority refs"):
        FutureReasoningConstraint(
            constraint_id="constraint-no-authority",
            source_learning_id="learning-1",
            rule="Bad missing authority.",
            strength=FutureConstraintStrength.REQUIRED_CHECK,
            applies_to_domains=("bounded simulation",),
            evidence_ids=("constraint-evidence-1",),
            authority_refs=(),
        )


def test_compile_experience_record_from_matched_trace() -> None:
    record = compile_experience_record(
        record_id="experience-1",
        trace=_trace(),
        prediction_id="prediction-1",
        affected_belief_ids=("belief-boundary-1",),
        affected_skill_ids=("skill-simulation-1",),
        target_memory_id="memory-boundary-1",
        domains=("bounded simulation",),
        authority_refs=("human-authority-1",),
        notes=("Compiled from measured outcome.",),
    )

    assert record.record_id == "experience-1"
    assert record.ready_for_review
    assert not record.blocks_claim
    assert record.quarantined_patch_ids == ("experience-1-memory-patch",)
    assert record.accepted_patch_ids == ()
    assert record.delta.confirms_prediction
    assert record.learning_delta.kind is LearningDeltaKind.CONFIRMATION
    assert record.future_constraints[0].strength is FutureConstraintStrength.ADVISORY
    assert "outcome-evidence-1" in record.evidence_ids
    assert record.fingerprint() == record.fingerprint()
    assert len(record.fingerprint()) == 64


def test_compile_experience_record_from_partial_trace_changes_reasoning() -> None:
    record = compile_experience_record(
        record_id="experience-partial",
        trace=_trace(
            alignment=OutcomeAlignment.PARTIAL,
            lesson="Future reasoning must check the missing condition first.",
        ),
        prediction_id="prediction-1",
        affected_belief_ids=("belief-boundary-1",),
        target_memory_id="memory-boundary-1",
        domains=("bounded simulation",),
        authority_refs=("human-authority-1",),
    )

    assert record.ready_for_review
    assert record.changes_future_reasoning
    assert record.learning_delta.kind is LearningDeltaKind.LIMITATION
    assert (
        record.future_constraints[0].strength
        is FutureConstraintStrength.REQUIRED_CHECK
    )


def test_compile_experience_record_from_mismatch_blocks_stronger_claim() -> None:
    record = compile_experience_record(
        record_id="experience-mismatch",
        trace=_trace(
            alignment=OutcomeAlignment.MISMATCHED,
            lesson="Future reasoning must block this assumption until revalidated.",
        ),
        prediction_id="prediction-1",
        affected_belief_ids=("belief-boundary-1",),
        target_memory_id="memory-boundary-1",
        domains=("bounded simulation",),
        authority_refs=("human-authority-1",),
    )

    assert record.ready_for_review
    assert record.blocks_claim
    assert record.changes_future_reasoning
    assert record.learning_delta.kind is LearningDeltaKind.CORRECTION
    assert (
        record.future_constraints[0].strength
        is FutureConstraintStrength.BLOCKING_RULE
    )


def test_compile_experience_record_rejects_unmeasured_trace() -> None:
    trace = ObservationActionTrace(
        trace_id="trace-unmeasured",
        envelope=_envelope(),
        outcome=ObservedOutcome(
            outcome_id="outcome-unmeasured",
            envelope_id="envelope-1",
            outcome_summary="Outcome was not measured.",
            evidence_ids=("outcome-evidence-1",),
            alignment=OutcomeAlignment.NOT_MEASURED,
            measured_state_ids=(),
        ),
    )

    with pytest.raises(ValueError, match="requires a measured outcome"):
        compile_experience_record(
            record_id="experience-unmeasured",
            trace=trace,
            prediction_id="prediction-1",
            affected_belief_ids=("belief-boundary-1",),
            target_memory_id="memory-boundary-1",
            domains=("bounded simulation",),
            authority_refs=("human-authority-1",),
        )


def test_experience_record_rejects_bad_learning_delta_link() -> None:
    trace = _trace()
    delta = PredictionOutcomeDelta(
        delta_id="delta-1",
        prediction_id="prediction-1",
        predicted_outcome="Boundary should hold.",
        observed_outcome="Boundary held.",
        alignment=OutcomeAlignment.MATCHED,
        delta_summary="Measured outcome matched prediction.",
        evidence_ids=("delta-evidence-1",),
    )
    learning = LearningDelta(
        learning_id="learning-1",
        kind=LearningDeltaKind.CONFIRMATION,
        source_delta_id="delta-other",
        summary="Experience confirmed prediction.",
        evidence_ids=("learning-evidence-1",),
        affected_belief_ids=("belief-1",),
    )
    patch = MemoryPatch(
        patch_id="patch-1",
        source_learning_id="learning-1",
        target_memory_id="memory-1",
        patch_summary="Quarantine confirmation.",
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

    with pytest.raises(ValueError, match="must reference the prediction delta"):
        from ix_cognition_kernel.wave7_experience_compiler import ExperienceRecord

        ExperienceRecord(
            record_id="experience-bad-link",
            trace=trace,
            delta=delta,
            learning_delta=learning,
            memory_patches=(patch,),
            future_constraints=(constraint,),
            decision=ExperienceCompilationDecision.READY_FOR_REVIEW,
        )


def test_experience_compilation_report_preserves_review_and_blockers() -> None:
    ready_record = compile_experience_record(
        record_id="experience-ready",
        trace=_trace(),
        prediction_id="prediction-1",
        affected_belief_ids=("belief-boundary-1",),
        target_memory_id="memory-boundary-1",
        domains=("bounded simulation",),
        authority_refs=("human-authority-1",),
    )
    blocked_record = compile_experience_record(
        record_id="experience-blocked",
        trace=_trace(
            alignment=OutcomeAlignment.MISMATCHED,
            lesson="Future reasoning must block this assumption until revalidated.",
        ),
        prediction_id="prediction-2",
        affected_belief_ids=("belief-boundary-2",),
        target_memory_id="memory-boundary-2",
        domains=("bounded simulation",),
        authority_refs=("human-authority-1",),
    )
    report = build_experience_compilation_report(
        report_id="experience-report-1",
        records=(ready_record, blocked_record),
        decision=ExperienceCompilationDecision.BLOCKED,
        notes=("Mismatch remains visible to reviewers.",),
    )

    assert report.record_ids == ("experience-blocked", "experience-ready")
    assert report.review_ready_record_ids == (
        "experience-blocked",
        "experience-ready",
    )
    assert report.blocking_record_ids == ("experience-blocked",)
    assert report.future_reasoning_record_ids == ("experience-blocked",)
    assert report.blocks_claim
    assert not report.ready_for_review
    assert "outcome-evidence-1" in report.evidence_ids
    assert report.fingerprint() == report.fingerprint()
    assert len(report.fingerprint()) == 64
