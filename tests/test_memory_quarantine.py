import pytest

from ix_cognition_kernel.memory import (
    MemoryCandidate,
    MemoryCandidateKind,
    MemoryQuarantineLedger,
    MemoryQuarantinePolicy,
    MemoryValidationRecord,
    MemoryValidationStatus,
    evaluate_memory_candidate,
    evaluate_memory_quarantine,
)
from ix_cognition_kernel.outcome import (
    OutcomeLearningLedger,
    OutcomeLearningRecord,
    OutcomeLearningStatus,
    OutcomePressure,
    outcome_learning_ledger,
)


def accepted_outcome(outcome_id: str = "outcome-001") -> OutcomeLearningRecord:
    return OutcomeLearningRecord(
        outcome_id=outcome_id,
        summary="Accepted outcome learning supports a memory candidate.",
        status=OutcomeLearningStatus.ACCEPTED,
        pressure=OutcomePressure.CONFIRMED,
        belief_revision_ids=("revision-001",),
        causal_revision_ids=("causal-revision-001",),
        prediction_comparison_ids=("comparison-001",),
        evidence_ids=("ev-outcome-001",),
        learning_summary="Outcome evidence linked belief and causal revisions.",
        reasons=("Outcome learning was accepted with evidence.",),
    )


def blocked_outcome() -> OutcomeLearningRecord:
    return OutcomeLearningRecord(
        outcome_id="outcome-blocked",
        summary="Blocked outcome learning must not validate memory.",
        status=OutcomeLearningStatus.BLOCKED,
        pressure=OutcomePressure.BLOCKED,
        belief_revision_ids=("revision-blocked",),
        causal_revision_ids=(),
        prediction_comparison_ids=("comparison-blocked",),
        evidence_ids=("ev-outcome-blocked",),
        learning_summary="Blocked outcome should not become durable memory.",
        reasons=("Outcome learning was blocked.",),
    )


def memory_candidate(
    *,
    candidate_id: str = "memory-candidate-001",
    confidence: float = 0.82,
    evidence_ids: tuple[str, ...] = ("ev-memory-001",),
    source_outcome_ids: tuple[str, ...] = ("outcome-001",),
    contradiction_ids: tuple[str, ...] = (),
    unsafe_reasons: tuple[str, ...] = (),
    proposed_audit_index: int = 0,
) -> MemoryCandidate:
    return MemoryCandidate(
        candidate_id=candidate_id,
        kind=MemoryCandidateKind.OUTCOME_SUMMARY,
        content="A validated outcome can be reused as a bounded memory summary.",
        provenance=("wave-2-commit-10",),
        evidence_ids=evidence_ids,
        source_outcome_ids=source_outcome_ids,
        confidence=confidence,
        proposed_audit_index=proposed_audit_index,
        contradiction_ids=contradiction_ids,
        unsafe_reasons=unsafe_reasons,
    )


def test_memory_candidate_requires_provenance_and_bounded_confidence() -> None:
    with pytest.raises(ValueError, match="provenance"):
        MemoryCandidate(
            candidate_id="memory-no-provenance",
            kind=MemoryCandidateKind.BELIEF_SUMMARY,
            content="Missing provenance should fail.",
            provenance=(),
            evidence_ids=("ev-memory",),
            source_outcome_ids=("outcome-001",),
            confidence=0.8,
            proposed_audit_index=0,
        )

    with pytest.raises(ValueError, match="between 0.0 and 1.0"):
        memory_candidate(confidence=1.01)


def test_memory_candidate_exposes_known_risk() -> None:
    candidate = memory_candidate(contradiction_ids=("conflict-001",))

    assert candidate.has_known_risk is True


def test_accepted_memory_requires_evidence_and_accepted_outcome_link() -> None:
    candidate = memory_candidate()
    validation = evaluate_memory_candidate(
        candidate=candidate,
        outcome_ledger=outcome_learning_ledger(accepted_outcome()),
        current_audit_index=1,
    )

    assert validation.status is MemoryValidationStatus.ACCEPTED
    assert validation.is_accepted is True
    assert validation.evidence_ids == ("ev-memory-001",)
    assert validation.outcome_ids == ("outcome-001",)
    assert validation.reviewer_role_id == "memory-integrity-specialist"
    assert "passed quarantine gates" in validation.reasons[0]


def test_raw_memory_without_evidence_stays_quarantined() -> None:
    validation = evaluate_memory_candidate(
        candidate=memory_candidate(evidence_ids=()),
        outcome_ledger=outcome_learning_ledger(accepted_outcome()),
        current_audit_index=1,
    )

    assert validation.status is MemoryValidationStatus.QUARANTINED
    assert validation.evidence_ids == ()
    assert "lacks evidence ids" in validation.reasons[0]


def test_low_confidence_memory_stays_quarantined() -> None:
    validation = evaluate_memory_candidate(
        candidate=memory_candidate(confidence=0.4),
        outcome_ledger=outcome_learning_ledger(accepted_outcome()),
        current_audit_index=1,
        policy=MemoryQuarantinePolicy(minimum_confidence=0.65),
    )

    assert validation.status is MemoryValidationStatus.QUARANTINED
    assert "below minimum" in validation.reasons[0]


def test_memory_without_required_outcome_link_stays_quarantined() -> None:
    validation = evaluate_memory_candidate(
        candidate=memory_candidate(source_outcome_ids=()),
        outcome_ledger=outcome_learning_ledger(accepted_outcome()),
        current_audit_index=1,
    )

    assert validation.status is MemoryValidationStatus.QUARANTINED
    assert "lacks required outcome linkage" in validation.reasons[0]


def test_memory_linked_to_blocked_outcome_is_rejected() -> None:
    validation = evaluate_memory_candidate(
        candidate=memory_candidate(source_outcome_ids=("outcome-blocked",)),
        outcome_ledger=outcome_learning_ledger(blocked_outcome()),
        current_audit_index=1,
    )

    assert validation.status is MemoryValidationStatus.REJECTED
    assert validation.is_blocking_status is True
    assert "non-accepted outcome learning" in validation.reasons[0]


def test_memory_with_contradiction_or_unsafe_reason_is_rejected() -> None:
    contradicted = evaluate_memory_candidate(
        candidate=memory_candidate(contradiction_ids=("conflict-001",)),
        outcome_ledger=outcome_learning_ledger(accepted_outcome()),
        current_audit_index=1,
    )
    unsafe = evaluate_memory_candidate(
        candidate=memory_candidate(
            candidate_id="memory-unsafe",
            unsafe_reasons=("The candidate includes unsafe-to-store content.",),
        ),
        outcome_ledger=outcome_learning_ledger(accepted_outcome()),
        current_audit_index=1,
    )

    assert contradicted.status is MemoryValidationStatus.REJECTED
    assert unsafe.status is MemoryValidationStatus.REJECTED


def test_memory_candidate_expires_without_acceptance() -> None:
    validation = evaluate_memory_candidate(
        candidate=memory_candidate(proposed_audit_index=0),
        outcome_ledger=outcome_learning_ledger(accepted_outcome()),
        current_audit_index=6,
        policy=MemoryQuarantinePolicy(expire_after_audit_gap=6),
    )

    assert validation.status is MemoryValidationStatus.EXPIRED
    assert validation.is_blocking_status is True
    assert "expired after audit gap 6" in validation.reasons[0]


def test_memory_quarantine_ledger_groups_candidates_by_validation_status() -> None:
    accepted = memory_candidate(candidate_id="memory-accepted")
    quarantined = memory_candidate(
        candidate_id="memory-quarantined",
        confidence=0.3,
    )
    rejected = memory_candidate(
        candidate_id="memory-rejected",
        contradiction_ids=("conflict-001",),
    )

    ledger = evaluate_memory_quarantine(
        candidates=(accepted, quarantined, rejected),
        outcome_ledger=outcome_learning_ledger(accepted_outcome()),
        current_audit_index=1,
    )

    assert ledger.accepted_candidates == (accepted,)
    assert ledger.quarantined_candidates == (quarantined,)
    assert ledger.rejected_candidates == (rejected,)
    assert ledger.expired_candidates == ()
    assert ledger.candidate_by_id("memory-accepted") == accepted
    assert ledger.validation_for_candidate("memory-rejected").status is (
        MemoryValidationStatus.REJECTED
    )
    assert len(ledger.blocking_validations) == 1


def test_memory_quarantine_ledger_rejects_duplicate_candidate_ids() -> None:
    candidate = memory_candidate()

    with pytest.raises(ValueError, match="Duplicate memory candidate_id"):
        MemoryQuarantineLedger(candidates=(candidate, candidate), validations=())


def test_memory_quarantine_ledger_rejects_validation_for_unknown_candidate() -> None:
    validation = MemoryValidationRecord(
        validation_id="memory-validation-001",
        candidate_id="memory-missing",
        status=MemoryValidationStatus.QUARANTINED,
        evidence_ids=(),
        outcome_ids=(),
        reviewer_role_id="memory-integrity-specialist",
        reasons=("Unknown candidate reference should fail.",),
    )

    with pytest.raises(ValueError, match="unknown candidate_id"):
        MemoryQuarantineLedger(candidates=(), validations=(validation,))


def test_accepted_memory_validation_requires_evidence_and_outcomes() -> None:
    with pytest.raises(ValueError, match="evidence_ids"):
        MemoryValidationRecord(
            validation_id="memory-validation-invalid",
            candidate_id="memory-001",
            status=MemoryValidationStatus.ACCEPTED,
            evidence_ids=(),
            outcome_ids=("outcome-001",),
            reviewer_role_id="memory-integrity-specialist",
            reasons=("Accepted memory requires evidence.",),
        )

    with pytest.raises(ValueError, match="outcome_ids"):
        MemoryValidationRecord(
            validation_id="memory-validation-invalid",
            candidate_id="memory-001",
            status=MemoryValidationStatus.ACCEPTED,
            evidence_ids=("ev-memory",),
            outcome_ids=(),
            reviewer_role_id="memory-integrity-specialist",
            reasons=("Accepted memory requires outcome linkage.",),
        )


def test_unknown_outcome_reference_fails_closed() -> None:
    with pytest.raises(ValueError, match="Unknown outcome_id"):
        evaluate_memory_candidate(
            candidate=memory_candidate(source_outcome_ids=("outcome-missing",)),
            outcome_ledger=OutcomeLearningLedger(records=()),
            current_audit_index=1,
        )
