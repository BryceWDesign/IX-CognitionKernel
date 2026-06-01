import pytest

from ix_cognition_kernel.history import (
    BeliefHistory,
    BeliefRevisionKind,
    BeliefRevisionRecord,
    BeliefTimeline,
    build_belief_history,
)
from ix_cognition_kernel.learning import (
    EvidenceEvent,
    EvidenceEventPolarity,
    StalenessPolicy,
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
        summary="Existing verified evidence supports the starting claim.",
        status=EvidenceStatus.VERIFIED,
        sources=("tests/test_belief_history.py",),
        supports_claim_ids=("claim-001",),
    )


def belief_state(
    *,
    confidence: float = 0.45,
    uncertainty: UncertaintyStatus = UncertaintyStatus.ASSUMED,
    disposition: BeliefDisposition = BeliefDisposition.NEEDS_EVIDENCE,
) -> BeliefState:
    claim = ClaimRecord(
        claim_id="claim-001",
        statement="Belief history should preserve deterministic revision records.",
        confidence=confidence,
        uncertainty=uncertainty,
        evidence_ids=("ev-existing",),
    )
    belief = BeliefRecord(
        belief_id="belief-001",
        claim=claim,
        provenance=("wave-1-snapshot",),
        rationale="The belief exists so Wave 2 can build history from updates.",
        disposition=disposition,
    )
    return BeliefState(beliefs=(belief,), evidence=(evidence_record(),))


def support_event() -> EvidenceEvent:
    return EvidenceEvent(
        event_id="event-support-001",
        summary="A support event strengthens the target belief.",
        source="tests/test_belief_history.py",
        provenance=("wave-2-commit-5",),
        target_claim_ids=("claim-001",),
        polarity=EvidenceEventPolarity.SUPPORTS,
        strength=0.8,
        audit_index=0,
        evidence_ids=("ev-support-001",),
    )


def weaken_event() -> EvidenceEvent:
    return EvidenceEvent(
        event_id="event-weaken-001",
        summary="A later weakener reduces confidence in the same belief.",
        source="tests/test_belief_history.py",
        provenance=("wave-2-commit-5",),
        target_claim_ids=("claim-001",),
        polarity=EvidenceEventPolarity.WEAKENS,
        strength=0.6,
        audit_index=0,
        evidence_ids=("ev-weaken-001",),
    )


def test_build_belief_history_preserves_revisions_across_update_results() -> None:
    first = apply_belief_updates(
        belief_state(), UpdateLedger(events=(support_event(),))
    )
    second = apply_belief_updates(
        first.after_state, UpdateLedger(events=(weaken_event(),))
    )

    history = build_belief_history(first, second)
    timeline = history.timeline_by_belief_id("belief-001")

    assert history.changed_belief_ids == ("belief-001",)
    assert tuple(revision.revision_id for revision in timeline.ordered_revisions) == (
        "revision-000",
        "revision-001",
    )
    assert tuple(revision.kind for revision in timeline.ordered_revisions) == (
        BeliefRevisionKind.STRENGTHENED,
        BeliefRevisionKind.WEAKENED,
    )
    assert timeline.event_ids == ("event-support-001", "event-weaken-001")
    assert (
        timeline.latest_revision.after_confidence == second.updates[0].after_confidence
    )
    assert history.all_revisions == timeline.ordered_revisions


def test_belief_update_result_can_be_converted_into_belief_history() -> None:
    result = apply_belief_updates(
        belief_state(), UpdateLedger(events=(support_event(),))
    )

    history = build_belief_history(result)

    assert history.timeline_by_belief_id("belief-001").latest_revision.update_id == (
        "belief-update-000"
    )
    assert history.all_revisions[0].changed_confidence is True
    assert history.all_revisions[0].changed_uncertainty is True
    assert history.all_revisions[0].changed_disposition is True


def test_staleness_update_becomes_stale_revision_in_history() -> None:
    result = apply_belief_updates(
        belief_state(
            confidence=0.8,
            uncertainty=UncertaintyStatus.KNOWN,
            disposition=BeliefDisposition.ACTIVE,
        ),
        UpdateLedger(events=(support_event(),)),
        current_audit_index=3,
        staleness_policy=StalenessPolicy(stale_after_audit_gap=3),
    )

    history = build_belief_history(result)
    revision = history.stale_revisions[0]

    assert revision.kind is BeliefRevisionKind.STALE
    assert revision.staleness_ids == ("stale-000",)
    assert revision.blocks_belief is True
    assert history.blocking_revisions == (revision,)


def test_empty_belief_history_is_valid_and_querying_missing_timeline_fails() -> None:
    history = build_belief_history()

    assert history.timelines == ()
    assert history.all_revisions == ()
    with pytest.raises(ValueError, match="Unknown belief timeline belief_id"):
        history.timeline_by_belief_id("belief-missing")


def test_belief_revision_record_requires_traceable_event_or_staleness_ids() -> None:
    with pytest.raises(ValueError, match="event_ids or staleness_ids"):
        BeliefRevisionRecord(
            revision_id="revision-invalid",
            revision_index=0,
            belief_id="belief-001",
            claim_id="claim-001",
            update_id="belief-update-000",
            kind=BeliefRevisionKind.UNCHANGED,
            event_ids=(),
            staleness_ids=(),
            before_confidence=0.4,
            after_confidence=0.4,
            before_uncertainty=UncertaintyStatus.ASSUMED,
            after_uncertainty=UncertaintyStatus.ASSUMED,
            before_disposition=BeliefDisposition.NEEDS_EVIDENCE,
            after_disposition=BeliefDisposition.NEEDS_EVIDENCE,
            reasons=("This invalid revision has no trigger.",),
        )


def test_belief_timeline_rejects_mixed_belief_ids() -> None:
    revision = BeliefRevisionRecord(
        revision_id="revision-000",
        revision_index=0,
        belief_id="belief-other",
        claim_id="claim-001",
        update_id="belief-update-000",
        kind=BeliefRevisionKind.STRENGTHENED,
        event_ids=("event-support-001",),
        staleness_ids=(),
        before_confidence=0.4,
        after_confidence=0.6,
        before_uncertainty=UncertaintyStatus.ASSUMED,
        after_uncertainty=UncertaintyStatus.KNOWN,
        before_disposition=BeliefDisposition.NEEDS_EVIDENCE,
        after_disposition=BeliefDisposition.ACTIVE,
        reasons=("Revision belongs to a different belief.",),
    )

    with pytest.raises(ValueError, match="cannot mix belief ids"):
        BeliefTimeline(
            belief_id="belief-001",
            claim_id="claim-001",
            revisions=(revision,),
        )


def test_belief_history_rejects_duplicate_timelines() -> None:
    result = apply_belief_updates(
        belief_state(), UpdateLedger(events=(support_event(),))
    )
    timeline = build_belief_history(result).timeline_by_belief_id("belief-001")

    with pytest.raises(ValueError, match="Duplicate timeline belief_id"):
        BeliefHistory(timelines=(timeline, timeline))
