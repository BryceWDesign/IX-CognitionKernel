import pytest

from ix_cognition_kernel.learning import (
    ConflictSeverity,
    ContradictionAssessment,
    ContradictionPolicy,
    EvidenceConflictRecord,
    EvidenceEvent,
    EvidenceEventPolarity,
    UpdateLedger,
    apply_belief_updates,
    detect_evidence_conflicts,
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


def support_event(
    *,
    event_id: str = "event-support-001",
    audit_index: int = 0,
    target_claim_ids: tuple[str, ...] = ("claim-001",),
) -> EvidenceEvent:
    return EvidenceEvent(
        event_id=event_id,
        summary="A supporting observation creates prior evidence context.",
        source="tests/test_contradiction_detection.py",
        provenance=("wave-2-commit-3",),
        target_claim_ids=target_claim_ids,
        polarity=EvidenceEventPolarity.SUPPORTS,
        strength=0.7,
        audit_index=audit_index,
        evidence_ids=(f"ev-{event_id}",),
    )


def contradict_event(
    *,
    event_id: str = "event-contradict-001",
    audit_index: int = 1,
    strength: float = 0.82,
    target_claim_ids: tuple[str, ...] = ("claim-001",),
) -> EvidenceEvent:
    return EvidenceEvent(
        event_id=event_id,
        summary="A contradictory observation pressures the target claim.",
        source="tests/test_contradiction_detection.py",
        provenance=("wave-2-commit-3",),
        target_claim_ids=target_claim_ids,
        polarity=EvidenceEventPolarity.CONTRADICTS,
        strength=strength,
        audit_index=audit_index,
        evidence_ids=(f"ev-{event_id}",),
    )


def belief_state() -> BeliefState:
    evidence = EvidenceRecord(
        evidence_id="ev-existing",
        summary="Existing verified support for the starting claim.",
        status=EvidenceStatus.VERIFIED,
        sources=("tests/test_contradiction_detection.py",),
        supports_claim_ids=("claim-001",),
    )
    claim = ClaimRecord(
        claim_id="claim-001",
        statement="A claim should become disputed when evidence conflicts.",
        confidence=0.8,
        uncertainty=UncertaintyStatus.KNOWN,
        evidence_ids=("ev-existing",),
    )
    belief = BeliefRecord(
        belief_id="belief-001",
        claim=claim,
        provenance=("wave-1-snapshot",),
        rationale="The belief starts active so contradiction detection can block it.",
        disposition=BeliefDisposition.ACTIVE,
    )
    return BeliefState(beliefs=(belief,), evidence=(evidence,))


def test_detect_evidence_conflicts_records_prior_support_and_blocking_severity() -> (
    None
):
    ledger = UpdateLedger(events=(support_event(), contradict_event()))

    assessment = detect_evidence_conflicts(ledger)
    conflict = assessment.conflicts[0]

    assert conflict.conflict_id == "conflict-000"
    assert conflict.claim_id == "claim-001"
    assert conflict.contradicting_event_id == "event-contradict-001"
    assert conflict.prior_event_ids == ("event-support-001",)
    assert conflict.severity is ConflictSeverity.BLOCKING
    assert conflict.blocks_claim is True
    assert assessment.blocking_conflicts == (conflict,)
    assert assessment.claim_ids_with_blocking_conflicts == ("claim-001",)
    assert assessment.conflicts_for_claim("claim-001") == (conflict,)


def test_detect_evidence_conflicts_still_records_claim_level_contradiction() -> None:
    ledger = UpdateLedger(events=(contradict_event(audit_index=0),))

    assessment = detect_evidence_conflicts(ledger)
    conflict = assessment.conflicts[0]

    assert conflict.prior_event_ids == ()
    assert conflict.severity is ConflictSeverity.BLOCKING
    assert "without prior supporting event context" in conflict.reasons[0]


def test_detect_evidence_conflicts_assigns_severity_from_policy_thresholds() -> None:
    policy = ContradictionPolicy(
        moderate_threshold=0.25,
        high_threshold=0.5,
        blocking_threshold=0.9,
    )
    low = detect_evidence_conflicts(
        UpdateLedger(events=(contradict_event(audit_index=0, strength=0.1),)),
        policy=policy,
    ).conflicts[0]
    moderate = detect_evidence_conflicts(
        UpdateLedger(events=(contradict_event(audit_index=0, strength=0.3),)),
        policy=policy,
    ).conflicts[0]
    high = detect_evidence_conflicts(
        UpdateLedger(events=(contradict_event(audit_index=0, strength=0.6),)),
        policy=policy,
    ).conflicts[0]

    assert low.severity is ConflictSeverity.LOW
    assert moderate.severity is ConflictSeverity.MODERATE
    assert high.severity is ConflictSeverity.HIGH


def test_contradiction_policy_rejects_unordered_thresholds() -> None:
    with pytest.raises(ValueError, match="ordered"):
        ContradictionPolicy(
            moderate_threshold=0.7,
            high_threshold=0.5,
            blocking_threshold=0.9,
        )


def test_evidence_conflict_record_rejects_invalid_traceability() -> None:
    with pytest.raises(ValueError, match="cannot be listed as prior"):
        EvidenceConflictRecord(
            conflict_id="conflict-invalid",
            claim_id="claim-001",
            contradicting_event_id="event-001",
            prior_event_ids=("event-001",),
            severity=ConflictSeverity.BLOCKING,
            strength=0.8,
            reasons=("Self-reference is invalid.",),
        )

    with pytest.raises(ValueError, match="require reasons"):
        EvidenceConflictRecord(
            conflict_id="conflict-no-reason",
            claim_id="claim-001",
            contradicting_event_id="event-001",
            prior_event_ids=(),
            severity=ConflictSeverity.BLOCKING,
            strength=0.8,
            reasons=(),
        )


def test_contradiction_assessment_rejects_duplicate_conflict_ids() -> None:
    conflict = EvidenceConflictRecord(
        conflict_id="conflict-001",
        claim_id="claim-001",
        contradicting_event_id="event-contradict-001",
        prior_event_ids=(),
        severity=ConflictSeverity.BLOCKING,
        strength=0.8,
        reasons=("Duplicate conflict ids must fail closed.",),
    )

    with pytest.raises(ValueError, match="Duplicate conflict_id"):
        ContradictionAssessment(conflicts=(conflict, conflict))


def test_apply_belief_updates_returns_explicit_contradiction_assessment() -> None:
    ledger = UpdateLedger(events=(support_event(), contradict_event()))

    result = apply_belief_updates(belief_state(), ledger)
    updated_belief = result.after_state.belief_by_id("belief-001")
    update = result.updates[0]

    assert updated_belief.uncertainty is UncertaintyStatus.DISPUTED
    assert updated_belief.disposition is BeliefDisposition.BLOCKED
    assert result.contradiction_assessment.has_blocking_conflicts is True
    assert (
        result.blocking_conflicts == result.contradiction_assessment.blocking_conflicts
    )
    assert "conflict-000 recorded blocking contradiction pressure." in update.reasons
