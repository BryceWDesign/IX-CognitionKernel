import pytest

from ix_cognition_kernel.memory import (
    MemoryCandidate,
    MemoryCandidateKind,
    MemoryQuarantineLedger,
    MemoryValidationRecord,
    MemoryValidationStatus,
)
from ix_cognition_kernel.outcome import (
    OutcomeLearningRecord,
    OutcomeLearningStatus,
    OutcomePressure,
    outcome_learning_ledger,
)
from ix_cognition_kernel.skills import (
    SkillCandidate,
    SkillCandidateKind,
    SkillReuseEvidenceRecord,
    SkillValidationLedger,
    SkillValidationPolicy,
    SkillValidationRecord,
    SkillValidationStatus,
    evaluate_skill_candidate,
    evaluate_skill_candidates,
)


def accepted_outcome(outcome_id: str = "outcome-001") -> OutcomeLearningRecord:
    return OutcomeLearningRecord(
        outcome_id=outcome_id,
        summary="Accepted outcome learning supports skill validation.",
        status=OutcomeLearningStatus.ACCEPTED,
        pressure=OutcomePressure.CONFIRMED,
        belief_revision_ids=("revision-001",),
        causal_revision_ids=("causal-revision-001",),
        prediction_comparison_ids=("comparison-001",),
        evidence_ids=(f"ev-{outcome_id}",),
        learning_summary="Accepted outcome evidence supports reuse validation.",
        reasons=("Outcome learning was accepted with evidence.",),
    )


def blocked_outcome() -> OutcomeLearningRecord:
    return OutcomeLearningRecord(
        outcome_id="outcome-blocked",
        summary="Blocked outcome learning cannot validate reusable skill.",
        status=OutcomeLearningStatus.BLOCKED,
        pressure=OutcomePressure.BLOCKED,
        belief_revision_ids=("revision-blocked",),
        causal_revision_ids=(),
        prediction_comparison_ids=("comparison-blocked",),
        evidence_ids=("ev-outcome-blocked",),
        learning_summary="Blocked outcome should not validate skill reuse.",
        reasons=("Outcome learning was blocked.",),
    )


def memory_candidate(candidate_id: str = "memory-candidate-001") -> MemoryCandidate:
    return MemoryCandidate(
        candidate_id=candidate_id,
        kind=MemoryCandidateKind.PROCEDURE_HINT,
        content="A successful outcome suggests a reusable bounded procedure.",
        provenance=("wave-2-commit-11",),
        evidence_ids=("ev-memory-001",),
        source_outcome_ids=("outcome-001",),
        confidence=0.82,
        proposed_audit_index=0,
    )


def memory_ledger(
    *,
    validation_status: MemoryValidationStatus = MemoryValidationStatus.ACCEPTED,
) -> MemoryQuarantineLedger:
    candidate = memory_candidate()
    validation = MemoryValidationRecord(
        validation_id="memory-validation-001",
        candidate_id="memory-candidate-001",
        status=validation_status,
        evidence_ids=("ev-memory-001",)
        if validation_status is MemoryValidationStatus.ACCEPTED
        else (),
        outcome_ids=("outcome-001",)
        if validation_status is MemoryValidationStatus.ACCEPTED
        else (),
        reviewer_role_id="memory-integrity-specialist",
        reasons=("Memory candidate was reviewed.",),
    )
    return MemoryQuarantineLedger(candidates=(candidate,), validations=(validation,))


def skill_candidate(
    *,
    confidence: float = 0.82,
    source_outcome_ids: tuple[str, ...] = ("outcome-001",),
) -> SkillCandidate:
    return SkillCandidate(
        skill_id="skill-001",
        kind=SkillCandidateKind.PROCEDURE,
        name="Bounded evidence update procedure",
        procedure_steps=(
            "Collect accepted outcome evidence.",
            "Check memory quarantine acceptance.",
            "Apply only inside matching applicability conditions.",
        ),
        applicability_conditions=("accepted-outcome-present", "memory-accepted"),
        failure_modes=("outcome-blocked", "memory-not-accepted"),
        source_memory_candidate_ids=("memory-candidate-001",),
        source_outcome_ids=source_outcome_ids,
        confidence=confidence,
        provenance=("wave-2-commit-11",),
        proposed_audit_index=1,
    )


def successful_reuse(
    *,
    reuse_id: str = "reuse-001",
    outcome_id: str = "outcome-001",
) -> SkillReuseEvidenceRecord:
    return SkillReuseEvidenceRecord(
        reuse_id=reuse_id,
        skill_id="skill-001",
        outcome_id=outcome_id,
        evidence_ids=(f"ev-{reuse_id}",),
        succeeded=True,
        audit_index=2,
        applicability_condition_ids=("accepted-outcome-present",),
        failure_mode_ids=(),
        reasons=("The skill was reused successfully under stated conditions.",),
    )


def failed_reuse() -> SkillReuseEvidenceRecord:
    return SkillReuseEvidenceRecord(
        reuse_id="reuse-failed",
        skill_id="skill-001",
        outcome_id="outcome-001",
        evidence_ids=("ev-reuse-failed",),
        succeeded=False,
        audit_index=2,
        applicability_condition_ids=("accepted-outcome-present",),
        failure_mode_ids=("memory-not-accepted",),
        reasons=("The skill failed during reuse validation.",),
    )


def test_skill_candidate_requires_structure_and_traceability() -> None:
    with pytest.raises(ValueError, match="procedure_steps"):
        SkillCandidate(
            skill_id="skill-invalid",
            kind=SkillCandidateKind.PROCEDURE,
            name="Invalid skill",
            procedure_steps=(),
            applicability_conditions=("condition",),
            failure_modes=("failure",),
            source_memory_candidate_ids=("memory-candidate-001",),
            source_outcome_ids=("outcome-001",),
            confidence=0.8,
            provenance=("wave-2-commit-11",),
            proposed_audit_index=0,
        )

    with pytest.raises(ValueError, match="failure_modes"):
        SkillCandidate(
            skill_id="skill-invalid",
            kind=SkillCandidateKind.PROCEDURE,
            name="Invalid skill",
            procedure_steps=("Do the thing.",),
            applicability_conditions=("condition",),
            failure_modes=(),
            source_memory_candidate_ids=("memory-candidate-001",),
            source_outcome_ids=("outcome-001",),
            confidence=0.8,
            provenance=("wave-2-commit-11",),
            proposed_audit_index=0,
        )


def test_successful_reuse_evidence_requires_evidence_and_conditions() -> None:
    with pytest.raises(ValueError, match="evidence_ids"):
        SkillReuseEvidenceRecord(
            reuse_id="reuse-invalid",
            skill_id="skill-001",
            outcome_id="outcome-001",
            evidence_ids=(),
            succeeded=True,
            audit_index=1,
            applicability_condition_ids=("condition",),
            failure_mode_ids=(),
            reasons=("Successful reuse requires evidence.",),
        )

    with pytest.raises(ValueError, match="applicability_condition_ids"):
        SkillReuseEvidenceRecord(
            reuse_id="reuse-invalid",
            skill_id="skill-001",
            outcome_id="outcome-001",
            evidence_ids=("ev-reuse",),
            succeeded=True,
            audit_index=1,
            applicability_condition_ids=(),
            failure_mode_ids=(),
            reasons=("Successful reuse requires applicability conditions.",),
        )


def test_failed_reuse_evidence_requires_failure_modes() -> None:
    with pytest.raises(ValueError, match="failure_mode_ids"):
        SkillReuseEvidenceRecord(
            reuse_id="reuse-invalid-failure",
            skill_id="skill-001",
            outcome_id="outcome-001",
            evidence_ids=("ev-failed",),
            succeeded=False,
            audit_index=1,
            applicability_condition_ids=("condition",),
            failure_mode_ids=(),
            reasons=("Failed reuse must identify failure modes.",),
        )


def test_validated_skill_requires_accepted_memory_outcome_and_reuse_evidence() -> None:
    validation = evaluate_skill_candidate(
        candidate=skill_candidate(),
        reuse_records=(successful_reuse(),),
        memory_ledger=memory_ledger(),
        outcome_ledger=outcome_learning_ledger(accepted_outcome()),
    )

    assert validation.status is SkillValidationStatus.VALIDATED
    assert validation.is_validated is True
    assert validation.source_memory_candidate_ids == ("memory-candidate-001",)
    assert validation.source_outcome_ids == ("outcome-001",)
    assert validation.reuse_evidence_ids == ("reuse-001",)
    assert "passed validation gates" in validation.reasons[0]


def test_skill_without_successful_reuse_evidence_is_not_validated() -> None:
    validation = evaluate_skill_candidate(
        candidate=skill_candidate(),
        reuse_records=(),
        memory_ledger=memory_ledger(),
        outcome_ledger=outcome_learning_ledger(accepted_outcome()),
    )

    assert validation.status is SkillValidationStatus.NEEDS_REUSE_EVIDENCE
    assert validation.reuse_evidence_ids == ()
    assert "lacks required successful reuse evidence" in validation.reasons[0]


def test_low_confidence_skill_needs_reuse_evidence() -> None:
    validation = evaluate_skill_candidate(
        candidate=skill_candidate(confidence=0.4),
        reuse_records=(successful_reuse(),),
        memory_ledger=memory_ledger(),
        outcome_ledger=outcome_learning_ledger(accepted_outcome()),
        policy=SkillValidationPolicy(minimum_confidence=0.7),
    )

    assert validation.status is SkillValidationStatus.NEEDS_REUSE_EVIDENCE
    assert "below minimum" in validation.reasons[0]


def test_unaccepted_memory_blocks_skill_validation() -> None:
    validation = evaluate_skill_candidate(
        candidate=skill_candidate(),
        reuse_records=(successful_reuse(),),
        memory_ledger=memory_ledger(
            validation_status=MemoryValidationStatus.QUARANTINED
        ),
        outcome_ledger=outcome_learning_ledger(accepted_outcome()),
    )

    assert validation.status is SkillValidationStatus.BLOCKED
    assert validation.is_blocking_status is True
    assert "source memory is not accepted" in validation.reasons[0]


def test_blocked_source_outcome_blocks_skill_validation() -> None:
    validation = evaluate_skill_candidate(
        candidate=skill_candidate(source_outcome_ids=("outcome-blocked",)),
        reuse_records=(successful_reuse(outcome_id="outcome-blocked"),),
        memory_ledger=memory_ledger(),
        outcome_ledger=outcome_learning_ledger(blocked_outcome()),
    )

    assert validation.status is SkillValidationStatus.BLOCKED
    assert "source outcome is not accepted" in validation.reasons[0]


def test_failed_reuse_rejects_skill_candidate() -> None:
    validation = evaluate_skill_candidate(
        candidate=skill_candidate(),
        reuse_records=(failed_reuse(),),
        memory_ledger=memory_ledger(),
        outcome_ledger=outcome_learning_ledger(accepted_outcome()),
    )

    assert validation.status is SkillValidationStatus.REJECTED
    assert validation.is_blocking_status is True
    assert "failed reuse evidence" in validation.reasons[0]


def test_skill_validation_ledger_groups_candidates() -> None:
    candidate = skill_candidate()
    validation_ledger = evaluate_skill_candidates(
        candidates=(candidate,),
        reuse_records=(successful_reuse(),),
        memory_ledger=memory_ledger(),
        outcome_ledger=outcome_learning_ledger(accepted_outcome()),
    )

    assert validation_ledger.validated_candidates == (candidate,)
    assert validation_ledger.candidates_needing_reuse_evidence == ()
    assert validation_ledger.rejected_candidates == ()
    assert validation_ledger.blocked_candidates == ()
    assert validation_ledger.candidate_by_id("skill-001") == candidate
    assert validation_ledger.validation_for_skill("skill-001").status is (
        SkillValidationStatus.VALIDATED
    )
    assert validation_ledger.reuse_records_for_skill("skill-001") == (
        successful_reuse(),
    )


def test_skill_validation_ledger_rejects_duplicate_skill_ids() -> None:
    candidate = skill_candidate()

    with pytest.raises(ValueError, match="Duplicate skill_id"):
        SkillValidationLedger(
            candidates=(candidate, candidate),
            reuse_records=(),
            validations=(),
        )


def test_skill_validation_ledger_rejects_reuse_for_unknown_skill() -> None:
    with pytest.raises(ValueError, match="unknown skill_id"):
        SkillValidationLedger(
            candidates=(),
            reuse_records=(successful_reuse(),),
            validations=(),
        )


def test_validated_skill_record_requires_memory_outcomes_and_reuse_evidence() -> None:
    with pytest.raises(ValueError, match="source memory ids"):
        SkillValidationRecord(
            validation_id="skill-validation-invalid",
            skill_id="skill-001",
            status=SkillValidationStatus.VALIDATED,
            source_memory_candidate_ids=(),
            source_outcome_ids=("outcome-001",),
            reuse_evidence_ids=("reuse-001",),
            reviewer_role_id="learning-archivist",
            reasons=("Validated skills require memory ids.",),
        )

    with pytest.raises(ValueError, match="reuse evidence ids"):
        SkillValidationRecord(
            validation_id="skill-validation-invalid",
            skill_id="skill-001",
            status=SkillValidationStatus.VALIDATED,
            source_memory_candidate_ids=("memory-candidate-001",),
            source_outcome_ids=("outcome-001",),
            reuse_evidence_ids=(),
            reviewer_role_id="learning-archivist",
            reasons=("Validated skills require reuse evidence ids.",),
        )


def test_unknown_memory_or_outcome_reference_fails_closed() -> None:
    with pytest.raises(ValueError, match="Unknown memory validation candidate_id"):
        evaluate_skill_candidate(
            candidate=skill_candidate(),
            reuse_records=(successful_reuse(),),
            memory_ledger=MemoryQuarantineLedger(candidates=(), validations=()),
            outcome_ledger=outcome_learning_ledger(accepted_outcome()),
        )

    with pytest.raises(ValueError, match="Unknown outcome_id"):
        evaluate_skill_candidate(
            candidate=skill_candidate(source_outcome_ids=("outcome-missing",)),
            reuse_records=(successful_reuse(outcome_id="outcome-missing"),),
            memory_ledger=memory_ledger(),
            outcome_ledger=outcome_learning_ledger(accepted_outcome()),
        )
