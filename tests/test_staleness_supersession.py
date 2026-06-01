import pytest

from ix_cognition_kernel.learning import (
    BeliefUpdateAction,
    EvidenceEvent,
    EvidenceEventPolarity,
    StalenessAssessment,
    StalenessPolicy,
    StalenessReason,
    StalenessRecord,
    UpdateLedger,
    apply_belief_updates,
    detect_staleness,
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


def evidence_record() -> EvidenceRecord:
    return EvidenceRecord(
        evidence_id="ev-existing",
        summary="Existing verified evidence supports the starting claim.",
        status=EvidenceStatus.VERIFIED,
        sources=("tests/test_staleness_supersession.py",),
        supports_claim_ids=("claim-001",),
    )


def belief_state() -> BeliefState:
    claim = ClaimRecord(
        claim_id="claim-001",
        statement="Old belief state should become stale when audit evidence ages out.",
        confidence=0.86,
        uncertainty=UncertaintyStatus.KNOWN,
        evidence_ids=("ev-existing",),
    )
    belief = BeliefRecord(
        belief_id="belief-001",
        claim=claim,
        provenance=("wave-1-snapshot",),
        rationale="The belief begins active so staleness can block it.",
        disposition=BeliefDisposition.ACTIVE,
    )
    return BeliefState(beliefs=(belief,), evidence=(evidence_record(),))


def support_event(
    *,
    event_id: str = "event-support-001",
    audit_index: int = 0,
) -> EvidenceEvent:
    return EvidenceEvent(
        event_id=event_id,
        summary="A supporting event establishes the last relevant audit point.",
        source="tests/test_staleness_supersession.py",
        provenance=("wave-2-commit-4",),
        target_claim_ids=("claim-001",),
        polarity=EvidenceEventPolarity.SUPPORTS,
        strength=0.3,
        audit_index=audit_index,
        evidence_ids=(f"ev-{event_id}",),
    )


def superseding_event(*, strength: float = 0.8) -> EvidenceEvent:
    return EvidenceEvent(
        event_id="event-supersede-001",
        summary="A newer event supersedes the prior evidence context.",
        source="tests/test_staleness_supersession.py",
        provenance=("wave-2-commit-4",),
        target_claim_ids=("claim-001",),
        polarity=EvidenceEventPolarity.SUPERSEDES,
        strength=strength,
        audit_index=1,
        evidence_ids=("ev-supersede-001",),
        supersedes_event_ids=("event-support-001",),
    )


def test_detect_staleness_records_audit_gap_from_logical_index() -> None:
    ledger = UpdateLedger(events=(support_event(),))

    assessment = detect_staleness(
        belief_state(),
        ledger,
        current_audit_index=3,
        policy=StalenessPolicy(stale_after_audit_gap=3),
    )
    record = assessment.records[0]

    assert assessment.has_stale_claims is True
    assert assessment.stale_claim_ids == ("claim-001",)
    assert record.staleness_id == "stale-000"
    assert record.reason is StalenessReason.AUDIT_GAP
    assert record.audit_index == 3
    assert record.last_relevant_audit_index == 0
    assert record.trigger_event_id is None
    assert "audit gap 3" in record.reasons[0]


def test_detect_staleness_records_superseded_evidence_context() -> None:
    ledger = UpdateLedger(events=(support_event(), superseding_event()))

    assessment = detect_staleness(belief_state(), ledger)
    record = assessment.supersession_records[0]

    assert record.reason is StalenessReason.SUPERSEDED
    assert record.trigger_event_id == "event-supersede-001"
    assert record.superseded_event_ids == ("event-support-001",)
    assert record.last_relevant_audit_index == 0
    assert assessment.records_for_claim("claim-001") == (record,)


def test_supersession_below_policy_threshold_does_not_mark_stale() -> None:
    ledger = UpdateLedger(events=(support_event(), superseding_event(strength=0.2)))

    assessment = detect_staleness(
        belief_state(),
        ledger,
        policy=StalenessPolicy(supersession_strength_threshold=0.5),
    )

    assert assessment.records == ()


def test_apply_belief_updates_blocks_belief_when_audit_gap_marks_stale() -> None:
    result = apply_belief_updates(
        belief_state(),
        UpdateLedger(events=(support_event(),)),
        current_audit_index=3,
        staleness_policy=StalenessPolicy(stale_after_audit_gap=3),
    )
    updated_belief = result.after_state.belief_by_id("belief-001")
    update = result.updates[0]

    assert updated_belief.claim.stale is True
    assert updated_belief.uncertainty is UncertaintyStatus.STALE
    assert updated_belief.disposition is BeliefDisposition.BLOCKED
    assert update.action is BeliefUpdateAction.BLOCKED
    assert update.staleness_ids == ("stale-000",)
    assert result.stale_update_records == (update,)
    assert "stale-000 marked claim stale via audit-gap." in update.reasons


def test_apply_belief_updates_blocks_belief_when_superseded() -> None:
    ledger = UpdateLedger(events=(support_event(), superseding_event()))

    result = apply_belief_updates(belief_state(), ledger)
    updated_belief = result.after_state.belief_by_id("belief-001")
    update = result.updates[0]

    assert result.staleness_assessment.supersession_records[0].trigger_event_id == (
        "event-supersede-001"
    )
    assert updated_belief.claim.stale is True
    assert updated_belief.uncertainty is UncertaintyStatus.STALE
    assert updated_belief.disposition is BeliefDisposition.BLOCKED
    assert update.staleness_ids == ("stale-000",)
    assert "event-supersede-001 superseded earlier evidence context." in update.reasons


def test_current_audit_index_cannot_move_backward_from_ledger_latest() -> None:
    with pytest.raises(ValueError, match="earlier than ledger latest"):
        detect_staleness(
            belief_state(),
            UpdateLedger(events=(support_event(audit_index=4),)),
            current_audit_index=3,
        )


def test_staleness_policy_rejects_invalid_thresholds() -> None:
    with pytest.raises(ValueError, match="stale_after_audit_gap"):
        StalenessPolicy(stale_after_audit_gap=-1)

    with pytest.raises(ValueError, match="supersession_strength_threshold"):
        StalenessPolicy(supersession_strength_threshold=1.01)


def test_staleness_record_requires_supersession_traceability() -> None:
    with pytest.raises(ValueError, match="trigger_event_id"):
        StalenessRecord(
            staleness_id="stale-invalid",
            claim_id="claim-001",
            reason=StalenessReason.SUPERSEDED,
            audit_index=2,
            last_relevant_audit_index=1,
            trigger_event_id=None,
            superseded_event_ids=("event-support-001",),
            reasons=("Supersession requires a triggering event.",),
        )

    with pytest.raises(ValueError, match="superseded_event_ids"):
        StalenessRecord(
            staleness_id="stale-invalid",
            claim_id="claim-001",
            reason=StalenessReason.SUPERSEDED,
            audit_index=2,
            last_relevant_audit_index=1,
            trigger_event_id="event-supersede-001",
            superseded_event_ids=(),
            reasons=("Supersession requires superseded event ids.",),
        )


def test_staleness_assessment_rejects_duplicate_staleness_ids() -> None:
    record = StalenessRecord(
        staleness_id="stale-duplicate",
        claim_id="claim-001",
        reason=StalenessReason.AUDIT_GAP,
        audit_index=4,
        last_relevant_audit_index=1,
        trigger_event_id=None,
        superseded_event_ids=(),
        reasons=("Duplicate staleness ids must fail closed.",),
    )

    with pytest.raises(ValueError, match="Duplicate staleness_id"):
        StalenessAssessment(records=(record, record))
