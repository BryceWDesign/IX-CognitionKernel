import pytest

from ix_cognition_kernel.learning import (
    EvidenceEvent,
    EvidenceEventPolarity,
    UpdateLedger,
    empty_update_ledger,
)


def supporting_event(
    *,
    event_id: str = "event-support-001",
    audit_index: int = 0,
    target_claim_ids: tuple[str, ...] = ("claim-001",),
) -> EvidenceEvent:
    return EvidenceEvent(
        event_id=event_id,
        summary="A verified test observation supports the target claim.",
        source="tests/test_learning_ledger.py",
        provenance=("wave-2-commit-1",),
        target_claim_ids=target_claim_ids,
        polarity=EvidenceEventPolarity.SUPPORTS,
        strength=0.72,
        audit_index=audit_index,
        evidence_ids=("ev-001",),
    )


def contradicting_event() -> EvidenceEvent:
    return EvidenceEvent(
        event_id="event-contradict-001",
        summary="A later observation contradicts the same target claim.",
        source="tests/test_learning_ledger.py",
        provenance=("wave-2-commit-1",),
        target_claim_ids=("claim-001",),
        polarity=EvidenceEventPolarity.CONTRADICTS,
        strength=0.84,
        audit_index=1,
        evidence_ids=("ev-contradiction",),
    )


def test_evidence_event_exposes_update_pressure_properties() -> None:
    support = supporting_event()
    contradiction = contradicting_event()

    assert support.increases_confidence is True
    assert support.decreases_confidence is False
    assert support.blocks_claim is False
    assert support.targets_claim("claim-001") is True
    assert contradiction.increases_confidence is False
    assert contradiction.decreases_confidence is True
    assert contradiction.blocks_claim is True


def test_evidence_event_requires_provenance_and_target_claim_ids() -> None:
    with pytest.raises(ValueError, match="provenance"):
        EvidenceEvent(
            event_id="event-no-provenance",
            summary="Missing provenance must fail closed.",
            source="tests/test_learning_ledger.py",
            provenance=(),
            target_claim_ids=("claim-001",),
            polarity=EvidenceEventPolarity.SUPPORTS,
            strength=0.5,
            audit_index=0,
        )

    with pytest.raises(ValueError, match="target claim ids"):
        EvidenceEvent(
            event_id="event-no-targets",
            summary="Missing target claims must fail closed.",
            source="tests/test_learning_ledger.py",
            provenance=("wave-2-commit-1",),
            target_claim_ids=(),
            polarity=EvidenceEventPolarity.SUPPORTS,
            strength=0.5,
            audit_index=0,
        )


def test_evidence_event_rejects_out_of_range_strength() -> None:
    with pytest.raises(ValueError, match="between 0.0 and 1.0"):
        EvidenceEvent(
            event_id="event-bad-strength",
            summary="Out-of-range strength must be rejected.",
            source="tests/test_learning_ledger.py",
            provenance=("wave-2-commit-1",),
            target_claim_ids=("claim-001",),
            polarity=EvidenceEventPolarity.WEAKENS,
            strength=1.01,
            audit_index=0,
        )


def test_evidence_event_rejects_negative_audit_index() -> None:
    with pytest.raises(ValueError, match="audit_index cannot be negative"):
        EvidenceEvent(
            event_id="event-negative-index",
            summary="Negative audit positions are not deterministic ledger order.",
            source="tests/test_learning_ledger.py",
            provenance=("wave-2-commit-1",),
            target_claim_ids=("claim-001",),
            polarity=EvidenceEventPolarity.WEAKENS,
            strength=0.4,
            audit_index=-1,
        )


def test_superseding_event_requires_superseded_event_ids() -> None:
    with pytest.raises(ValueError, match="supersedes_event_ids"):
        EvidenceEvent(
            event_id="event-supersedes-nothing",
            summary="Supersession without a target event is invalid.",
            source="tests/test_learning_ledger.py",
            provenance=("wave-2-commit-1",),
            target_claim_ids=("claim-001",),
            polarity=EvidenceEventPolarity.SUPERSEDES,
            strength=0.6,
            audit_index=1,
        )


def test_evidence_event_cannot_supersede_itself() -> None:
    with pytest.raises(ValueError, match="cannot supersede themselves"):
        EvidenceEvent(
            event_id="event-self-supersede",
            summary="Self-supersession would corrupt the audit trail.",
            source="tests/test_learning_ledger.py",
            provenance=("wave-2-commit-1",),
            target_claim_ids=("claim-001",),
            polarity=EvidenceEventPolarity.SUPERSEDES,
            strength=0.6,
            audit_index=1,
            supersedes_event_ids=("event-self-supersede",),
        )


def test_update_ledger_orders_events_by_audit_index() -> None:
    first = supporting_event(audit_index=0)
    second = contradicting_event()
    ledger = UpdateLedger(events=(second, first))

    assert ledger.ordered_events == (first, second)
    assert ledger.latest_audit_index == 1
    assert ledger.next_audit_index == 2
    assert ledger.event_by_id("event-support-001") == first
    assert ledger.events_for_claim("claim-001") == (first, second)
    assert ledger.contradiction_events == (second,)


def test_update_ledger_rejects_duplicate_event_ids() -> None:
    event = supporting_event()

    with pytest.raises(ValueError, match="Duplicate event_id"):
        UpdateLedger(events=(event, event))


def test_update_ledger_rejects_duplicate_audit_index_slots() -> None:
    first = supporting_event(event_id="event-a", audit_index=0)
    second = supporting_event(event_id="event-b", audit_index=0)

    with pytest.raises(ValueError, match="Duplicate audit_index"):
        UpdateLedger(events=(first, second))


def test_update_ledger_rejects_unknown_superseded_event_reference() -> None:
    superseding = EvidenceEvent(
        event_id="event-superseding",
        summary="Unknown supersession references must fail closed.",
        source="tests/test_learning_ledger.py",
        provenance=("wave-2-commit-1",),
        target_claim_ids=("claim-001",),
        polarity=EvidenceEventPolarity.SUPERSEDES,
        strength=0.6,
        audit_index=1,
        supersedes_event_ids=("event-missing",),
    )

    with pytest.raises(ValueError, match="unknown supersedes_event_id"):
        UpdateLedger(events=(supporting_event(), superseding))


def test_update_ledger_tracks_superseding_events() -> None:
    first = supporting_event(audit_index=0)
    superseding = EvidenceEvent(
        event_id="event-superseding",
        summary="A newer observation supersedes the first evidence event.",
        source="tests/test_learning_ledger.py",
        provenance=("wave-2-commit-1",),
        target_claim_ids=("claim-001",),
        polarity=EvidenceEventPolarity.SUPERSEDES,
        strength=0.66,
        audit_index=1,
        evidence_ids=("ev-newer",),
        supersedes_event_ids=("event-support-001",),
    )
    ledger = UpdateLedger(events=(first, superseding))

    assert ledger.superseding_events == (superseding,)
    assert ledger.events_for_claim("claim-001") == (first, superseding)


def test_update_ledger_append_event_returns_new_ledger() -> None:
    ledger = empty_update_ledger()
    first = supporting_event(audit_index=0)
    updated = ledger.append_event(first)

    assert ledger.events == ()
    assert updated.events == (first,)
    assert updated.next_audit_index == 1


def test_update_ledger_append_event_requires_next_audit_index() -> None:
    ledger = UpdateLedger(events=(supporting_event(audit_index=0),))
    skipped = supporting_event(event_id="event-skipped", audit_index=2)

    with pytest.raises(ValueError, match="next audit index"):
        ledger.append_event(skipped)


def test_unknown_event_lookup_is_rejected() -> None:
    with pytest.raises(ValueError, match="Unknown evidence event_id"):
        empty_update_ledger().event_by_id("event-missing")
