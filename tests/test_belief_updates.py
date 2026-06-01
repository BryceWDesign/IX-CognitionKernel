import pytest

from ix_cognition_kernel.learning import (
    BeliefUpdateAction,
    BeliefUpdatePolicy,
    BeliefUpdateRecord,
    EvidenceEvent,
    EvidenceEventPolarity,
    UpdateLedger,
    apply_belief_updates,
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
        summary="Existing verified evidence supports the starting belief.",
        status=EvidenceStatus.VERIFIED,
        sources=("tests/test_belief_updates.py",),
        supports_claim_ids=("claim-001",),
    )


def belief_state(
    *,
    confidence: float = 0.5,
    uncertainty: UncertaintyStatus = UncertaintyStatus.ASSUMED,
    evidence_ids: tuple[str, ...] = ("ev-existing",),
    disposition: BeliefDisposition = BeliefDisposition.NEEDS_EVIDENCE,
) -> BeliefState:
    claim = ClaimRecord(
        claim_id="claim-001",
        statement="The kernel can update a represented belief from evidence events.",
        confidence=confidence,
        uncertainty=uncertainty,
        evidence_ids=evidence_ids,
    )
    belief = BeliefRecord(
        belief_id="belief-001",
        claim=claim,
        provenance=("wave-1-snapshot",),
        rationale="The belief exists so Wave 2 can prove update behavior.",
        disposition=disposition,
    )
    return BeliefState(beliefs=(belief,), evidence=(evidence_record(),))


def support_event(*, audit_index: int = 0, strength: float = 0.8) -> EvidenceEvent:
    return EvidenceEvent(
        event_id="event-support-001",
        summary="A new observation supports the represented claim.",
        source="tests/test_belief_updates.py",
        provenance=("wave-2-commit-2",),
        target_claim_ids=("claim-001",),
        polarity=EvidenceEventPolarity.SUPPORTS,
        strength=strength,
        audit_index=audit_index,
        evidence_ids=("ev-support-001",),
    )


def weaken_event(*, audit_index: int = 0, strength: float = 0.9) -> EvidenceEvent:
    return EvidenceEvent(
        event_id="event-weaken-001",
        summary="A new observation weakens the represented claim.",
        source="tests/test_belief_updates.py",
        provenance=("wave-2-commit-2",),
        target_claim_ids=("claim-001",),
        polarity=EvidenceEventPolarity.WEAKENS,
        strength=strength,
        audit_index=audit_index,
        evidence_ids=("ev-weaken-001",),
    )


def contradict_event(*, audit_index: int = 0, strength: float = 0.95) -> EvidenceEvent:
    return EvidenceEvent(
        event_id="event-contradict-001",
        summary="A new observation contradicts the represented claim.",
        source="tests/test_belief_updates.py",
        provenance=("wave-2-commit-2",),
        target_claim_ids=("claim-001",),
        polarity=EvidenceEventPolarity.CONTRADICTS,
        strength=strength,
        audit_index=audit_index,
        evidence_ids=("ev-contradict-001",),
    )


def test_supporting_evidence_strengthens_belief_and_marks_it_known() -> None:
    state = belief_state(confidence=0.5, uncertainty=UncertaintyStatus.ASSUMED)
    result = apply_belief_updates(state, UpdateLedger(events=(support_event(),)))
    updated_belief = result.after_state.belief_by_id("belief-001")
    update = result.updates[0]

    assert result.before_state == state
    assert updated_belief.confidence == 0.7
    assert updated_belief.uncertainty is UncertaintyStatus.KNOWN
    assert updated_belief.disposition is BeliefDisposition.ACTIVE
    assert updated_belief.evidence_ids == ("ev-existing", "ev-support-001")
    assert updated_belief.provenance == (
        "wave-1-snapshot",
        "belief-update-engine",
    )
    assert result.changed_belief_ids == ("belief-001",)
    assert update.action is BeliefUpdateAction.STRENGTHENED
    assert update.changed_confidence is True
    assert update.changed_uncertainty is True
    assert update.changed_disposition is True
    assert update.reasons == ("event-support-001 supported the claim.",)


def test_weakening_evidence_reduces_confidence_and_requires_evidence() -> None:
    state = belief_state(
        confidence=0.5,
        uncertainty=UncertaintyStatus.KNOWN,
        disposition=BeliefDisposition.ACTIVE,
    )
    result = apply_belief_updates(state, UpdateLedger(events=(weaken_event(),)))
    updated_belief = result.after_state.belief_by_id("belief-001")
    update = result.updates[0]

    assert updated_belief.confidence == 0.275
    assert updated_belief.uncertainty is UncertaintyStatus.UNKNOWN
    assert updated_belief.disposition is BeliefDisposition.NEEDS_EVIDENCE
    assert update.action is BeliefUpdateAction.NEEDS_EVIDENCE
    assert update.changed_confidence is True


def test_contradicting_evidence_blocks_belief_without_manual_flagging() -> None:
    state = belief_state(
        confidence=0.8,
        uncertainty=UncertaintyStatus.KNOWN,
        disposition=BeliefDisposition.ACTIVE,
    )
    result = apply_belief_updates(state, UpdateLedger(events=(contradict_event(),)))
    updated_belief = result.after_state.belief_by_id("belief-001")
    update = result.updates[0]

    assert updated_belief.confidence == 0.3725
    assert updated_belief.uncertainty is UncertaintyStatus.DISPUTED
    assert updated_belief.disposition is BeliefDisposition.BLOCKED
    assert updated_belief.claim.contradicted_by == ("event-contradict-001",)
    assert result.blocked_update_records == (update,)
    assert update.action is BeliefUpdateAction.BLOCKED


def test_belief_updates_are_computed_in_ledger_audit_order() -> None:
    state = belief_state(confidence=0.5, uncertainty=UncertaintyStatus.ASSUMED)
    ledger = UpdateLedger(events=(weaken_event(audit_index=1), support_event()))
    result = apply_belief_updates(state, ledger)
    updated_belief = result.after_state.belief_by_id("belief-001")
    update = result.updates[0]

    assert updated_belief.confidence == 0.475
    assert update.event_ids == ("event-support-001", "event-weaken-001")
    assert update.reasons == (
        "event-support-001 supported the claim.",
        "event-weaken-001 weakened the claim.",
    )


def test_belief_update_rejects_evidence_event_targeting_unknown_claim() -> None:
    unknown_target = EvidenceEvent(
        event_id="event-unknown-target",
        summary="Unknown targets must fail closed.",
        source="tests/test_belief_updates.py",
        provenance=("wave-2-commit-2",),
        target_claim_ids=("claim-missing",),
        polarity=EvidenceEventPolarity.SUPPORTS,
        strength=0.4,
        audit_index=0,
    )

    with pytest.raises(ValueError, match="targets unknown claim_id"):
        apply_belief_updates(
            belief_state(),
            UpdateLedger(events=(unknown_target,)),
        )


def test_belief_update_policy_rejects_invalid_thresholds() -> None:
    with pytest.raises(ValueError, match="needs_evidence_threshold"):
        BeliefUpdatePolicy(known_threshold=0.3, needs_evidence_threshold=0.4)

    with pytest.raises(ValueError, match="support_weight"):
        BeliefUpdatePolicy(support_weight=1.01)


def test_belief_update_result_ignores_untargeted_beliefs() -> None:
    claim = ClaimRecord(
        claim_id="claim-002",
        statement="This second claim is not targeted by the update ledger.",
        confidence=0.6,
        uncertainty=UncertaintyStatus.KNOWN,
        evidence_ids=("ev-existing",),
    )
    untargeted_belief = BeliefRecord(
        belief_id="belief-002",
        claim=claim,
        provenance=("wave-1-snapshot",),
        rationale="Untargeted beliefs should remain unchanged.",
        disposition=BeliefDisposition.ACTIVE,
    )
    state = BeliefState(
        beliefs=(*belief_state().beliefs, untargeted_belief),
        evidence=(evidence_record(),),
    )

    result = apply_belief_updates(state, UpdateLedger(events=(support_event(),)))

    assert result.after_state.belief_by_id("belief-002") == untargeted_belief
    assert result.changed_belief_ids == ("belief-001",)


def test_belief_update_record_requires_traceable_event_ids_and_reasons() -> None:
    with pytest.raises(ValueError, match="event_ids"):
        BeliefUpdateRecord(
            update_id="belief-update-invalid",
            belief_id="belief-001",
            claim_id="claim-001",
            action=BeliefUpdateAction.STRENGTHENED,
            event_ids=(),
            before_confidence=0.4,
            after_confidence=0.6,
            before_uncertainty=UncertaintyStatus.ASSUMED,
            after_uncertainty=UncertaintyStatus.KNOWN,
            before_disposition=BeliefDisposition.NEEDS_EVIDENCE,
            after_disposition=BeliefDisposition.ACTIVE,
            reasons=("Missing event ids should fail.",),
        )

    with pytest.raises(ValueError, match="require reasons"):
        BeliefUpdateRecord(
            update_id="belief-update-invalid",
            belief_id="belief-001",
            claim_id="claim-001",
            action=BeliefUpdateAction.STRENGTHENED,
            event_ids=("event-001",),
            before_confidence=0.4,
            after_confidence=0.6,
            before_uncertainty=UncertaintyStatus.ASSUMED,
            after_uncertainty=UncertaintyStatus.KNOWN,
            before_disposition=BeliefDisposition.NEEDS_EVIDENCE,
            after_disposition=BeliefDisposition.ACTIVE,
            reasons=(),
        )
