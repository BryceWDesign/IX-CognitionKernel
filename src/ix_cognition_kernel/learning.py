"""Evidence-event, update-ledger, and belief-update foundation for Wave 2.

Wave 2 starts when IX-CognitionKernel can receive evidence events as structured
inputs, preserve a deterministic audit trail, and compute revised belief state
from evidence pressure. This module still does not execute actions, persist
memory, or claim full learning. It performs bounded evidence-driven belief
revision while leaving deeper contradiction detection, staleness handling, and
belief timelines for later Wave 2 commits.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from enum import StrEnum

from ix_cognition_kernel.state import (
    BeliefDisposition,
    BeliefRecord,
    BeliefState,
    ClaimRecord,
    UncertaintyStatus,
)


class EvidenceEventPolarity(StrEnum):
    """How an evidence event should pressure a target claim."""

    SUPPORTS = "supports"
    WEAKENS = "weakens"
    CONTRADICTS = "contradicts"
    SUPERSEDES = "supersedes"


@dataclass(frozen=True, slots=True)
class EvidenceEvent:
    """Incoming evidence signal used by later Wave 2 belief updates."""

    event_id: str
    summary: str
    source: str
    provenance: tuple[str, ...]
    target_claim_ids: tuple[str, ...]
    polarity: EvidenceEventPolarity
    strength: float
    audit_index: int
    evidence_ids: tuple[str, ...] = ()
    supersedes_event_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        """Validate identity, provenance, target linkage, strength, and ordering."""

        if not self.event_id.strip():
            raise ValueError("Evidence events require a non-empty event_id.")
        if not self.summary.strip():
            raise ValueError("Evidence events require a non-empty summary.")
        if not self.source.strip():
            raise ValueError("Evidence events require a non-empty source.")
        if not self.provenance:
            raise ValueError("Evidence events require at least one provenance entry.")
        if any(not entry.strip() for entry in self.provenance):
            raise ValueError("Evidence event provenance entries cannot be empty.")
        if not self.target_claim_ids:
            raise ValueError("Evidence events require target claim ids.")
        _unique_ids(self.target_claim_ids, label="target_claim_id")
        _unique_ids(self.evidence_ids, label="evidence_id")
        _unique_ids(self.supersedes_event_ids, label="supersedes_event_id")
        if not 0.0 <= self.strength <= 1.0:
            raise ValueError("Evidence event strength must be between 0.0 and 1.0.")
        if self.audit_index < 0:
            raise ValueError("Evidence event audit_index cannot be negative.")
        if (
            self.polarity is EvidenceEventPolarity.SUPERSEDES
            and not self.supersedes_event_ids
        ):
            raise ValueError(
                "Superseding evidence events require supersedes_event_ids."
            )
        if self.event_id in self.supersedes_event_ids:
            raise ValueError("Evidence events cannot supersede themselves.")

    @property
    def increases_confidence(self) -> bool:
        """Return whether this event should increase confidence later."""

        return self.polarity is EvidenceEventPolarity.SUPPORTS

    @property
    def decreases_confidence(self) -> bool:
        """Return whether this event should decrease confidence later."""

        return self.polarity in {
            EvidenceEventPolarity.WEAKENS,
            EvidenceEventPolarity.CONTRADICTS,
        }

    @property
    def blocks_claim(self) -> bool:
        """Return whether this event should block a claim later."""

        return self.polarity is EvidenceEventPolarity.CONTRADICTS

    def targets_claim(self, claim_id: str) -> bool:
        """Return whether this event targets a claim id."""

        return claim_id in self.target_claim_ids


@dataclass(frozen=True, slots=True)
class UpdateLedger:
    """Deterministic ledger of evidence events for Wave 2 update processing."""

    events: tuple[EvidenceEvent, ...]

    def __post_init__(self) -> None:
        """Reject duplicate ids, duplicate audit slots, and bad supersession refs."""

        event_ids = _unique_ids(
            (event.event_id for event in self.events), label="event_id"
        )
        _unique_ids(
            (str(event.audit_index) for event in self.events),
            label="audit_index",
        )
        for event in self.events:
            _validate_reference_subset(
                event.supersedes_event_ids,
                event_ids,
                owner=event.event_id,
                label="supersedes_event_id",
            )

    @property
    def ordered_events(self) -> tuple[EvidenceEvent, ...]:
        """Return events in deterministic audit order."""

        return tuple(sorted(self.events, key=lambda event: event.audit_index))

    @property
    def latest_audit_index(self) -> int | None:
        """Return the latest audit index, or None for an empty ledger."""

        if not self.events:
            return None
        return max(event.audit_index for event in self.events)

    @property
    def next_audit_index(self) -> int:
        """Return the next deterministic audit index for appending an event."""

        latest = self.latest_audit_index
        if latest is None:
            return 0
        return latest + 1

    @property
    def contradiction_events(self) -> tuple[EvidenceEvent, ...]:
        """Return evidence events that contradict target claims."""

        return tuple(
            event
            for event in self.ordered_events
            if event.polarity is EvidenceEventPolarity.CONTRADICTS
        )

    @property
    def superseding_events(self) -> tuple[EvidenceEvent, ...]:
        """Return evidence events that supersede earlier events."""

        return tuple(
            event
            for event in self.ordered_events
            if event.polarity is EvidenceEventPolarity.SUPERSEDES
        )

    def event_by_id(self, event_id: str) -> EvidenceEvent:
        """Return an evidence event by id."""

        for event in self.events:
            if event.event_id == event_id:
                return event
        raise ValueError(f"Unknown evidence event_id: {event_id}")

    def events_for_claim(self, claim_id: str) -> tuple[EvidenceEvent, ...]:
        """Return events targeting a claim id in audit order."""

        return tuple(
            event for event in self.ordered_events if event.targets_claim(claim_id)
        )

    def append_event(self, event: EvidenceEvent) -> UpdateLedger:
        """Return a new ledger with an appended evidence event."""

        if event.audit_index != self.next_audit_index:
            raise ValueError(
                "Appended evidence events must use the ledger's next audit index."
            )
        return UpdateLedger(events=(*self.events, event))


class BeliefUpdateAction(StrEnum):
    """Computed action taken during evidence-driven belief revision."""

    UNCHANGED = "unchanged"
    STRENGTHENED = "strengthened"
    WEAKENED = "weakened"
    NEEDS_EVIDENCE = "needs-evidence"
    BLOCKED = "blocked"


@dataclass(frozen=True, slots=True)
class BeliefUpdatePolicy:
    """Deterministic thresholds and weights for belief updates."""

    support_weight: float = 0.25
    weaken_weight: float = 0.25
    contradiction_weight: float = 0.45
    known_threshold: float = 0.65
    needs_evidence_threshold: float = 0.35

    def __post_init__(self) -> None:
        """Validate belief-update weights and thresholds."""

        for field_name, value in (
            ("support_weight", self.support_weight),
            ("weaken_weight", self.weaken_weight),
            ("contradiction_weight", self.contradiction_weight),
            ("known_threshold", self.known_threshold),
            ("needs_evidence_threshold", self.needs_evidence_threshold),
        ):
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{field_name} must be between 0.0 and 1.0.")
        if self.needs_evidence_threshold > self.known_threshold:
            raise ValueError("needs_evidence_threshold cannot exceed known_threshold.")


@dataclass(frozen=True, slots=True)
class BeliefUpdateRecord:
    """Audit record for one computed belief update."""

    update_id: str
    belief_id: str
    claim_id: str
    action: BeliefUpdateAction
    event_ids: tuple[str, ...]
    before_confidence: float
    after_confidence: float
    before_uncertainty: UncertaintyStatus
    after_uncertainty: UncertaintyStatus
    before_disposition: BeliefDisposition
    after_disposition: BeliefDisposition
    reasons: tuple[str, ...]

    def __post_init__(self) -> None:
        """Validate update record identity and traceability."""

        if not self.update_id.strip():
            raise ValueError("Belief update records require a non-empty update_id.")
        if not self.belief_id.strip():
            raise ValueError("Belief update records require a non-empty belief_id.")
        if not self.claim_id.strip():
            raise ValueError("Belief update records require a non-empty claim_id.")
        if not self.event_ids:
            raise ValueError("Belief update records require event_ids.")
        _unique_ids(self.event_ids, label="belief update event_id")
        if not self.reasons:
            raise ValueError("Belief update records require reasons.")
        if any(not reason.strip() for reason in self.reasons):
            raise ValueError("Belief update reasons cannot be empty.")
        for field_name, value in (
            ("before_confidence", self.before_confidence),
            ("after_confidence", self.after_confidence),
        ):
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{field_name} must be between 0.0 and 1.0.")

    @property
    def changed_confidence(self) -> bool:
        """Return whether the update changed confidence."""

        return self.before_confidence != self.after_confidence

    @property
    def changed_uncertainty(self) -> bool:
        """Return whether the update changed uncertainty."""

        return self.before_uncertainty is not self.after_uncertainty

    @property
    def changed_disposition(self) -> bool:
        """Return whether the update changed belief disposition."""

        return self.before_disposition is not self.after_disposition


@dataclass(frozen=True, slots=True)
class BeliefUpdateResult:
    """Result of applying an update ledger to a belief state."""

    before_state: BeliefState
    after_state: BeliefState
    ledger: UpdateLedger
    updates: tuple[BeliefUpdateRecord, ...]

    @property
    def changed_belief_ids(self) -> tuple[str, ...]:
        """Return belief ids changed by this update result."""

        return tuple(update.belief_id for update in self.updates)

    @property
    def blocked_update_records(self) -> tuple[BeliefUpdateRecord, ...]:
        """Return updates that blocked beliefs."""

        return tuple(
            update
            for update in self.updates
            if update.action is BeliefUpdateAction.BLOCKED
        )


DEFAULT_BELIEF_UPDATE_POLICY = BeliefUpdatePolicy()


def empty_update_ledger() -> UpdateLedger:
    """Return an empty Wave 2 update ledger."""

    return UpdateLedger(events=())


def apply_belief_updates(
    belief_state: BeliefState,
    ledger: UpdateLedger,
    *,
    policy: BeliefUpdatePolicy = DEFAULT_BELIEF_UPDATE_POLICY,
) -> BeliefUpdateResult:
    """Compute a revised belief state from evidence events.

    The original belief state is not mutated. Every changed belief receives a
    BeliefUpdateRecord explaining which events caused the revision.
    """

    _reject_unknown_claim_targets(belief_state, ledger)

    updated_beliefs: list[BeliefRecord] = []
    update_records: list[BeliefUpdateRecord] = []
    for belief in belief_state.beliefs:
        events = ledger.events_for_claim(belief.claim_id)
        if not events:
            updated_beliefs.append(belief)
            continue

        updated_belief, update_record = _apply_events_to_belief(
            belief,
            events,
            policy,
            update_index=len(update_records),
        )
        updated_beliefs.append(updated_belief)
        if update_record.action is not BeliefUpdateAction.UNCHANGED:
            update_records.append(update_record)

    return BeliefUpdateResult(
        before_state=belief_state,
        after_state=BeliefState(
            beliefs=tuple(updated_beliefs),
            evidence=belief_state.evidence,
        ),
        ledger=ledger,
        updates=tuple(update_records),
    )


def _apply_events_to_belief(
    belief: BeliefRecord,
    events: tuple[EvidenceEvent, ...],
    policy: BeliefUpdatePolicy,
    *,
    update_index: int,
) -> tuple[BeliefRecord, BeliefUpdateRecord]:
    """Apply evidence events to a single belief."""

    before_claim = belief.claim
    after_confidence = before_claim.confidence
    event_ids: list[str] = []
    evidence_ids = list(before_claim.evidence_ids)
    contradicted_by = list(before_claim.contradicted_by)
    reasons: list[str] = []
    contradiction_seen = False

    for event in events:
        event_ids.append(event.event_id)
        evidence_ids = _append_unique(evidence_ids, event.evidence_ids)
        if event.polarity is EvidenceEventPolarity.SUPPORTS:
            after_confidence = _clamp_confidence(
                after_confidence + event.strength * policy.support_weight
            )
            reasons.append(f"{event.event_id} supported the claim.")
        elif event.polarity is EvidenceEventPolarity.WEAKENS:
            after_confidence = _clamp_confidence(
                after_confidence - event.strength * policy.weaken_weight
            )
            reasons.append(f"{event.event_id} weakened the claim.")
        elif event.polarity is EvidenceEventPolarity.CONTRADICTS:
            after_confidence = _clamp_confidence(
                after_confidence - event.strength * policy.contradiction_weight
            )
            contradicted_by = _append_unique(contradicted_by, (event.event_id,))
            contradiction_seen = True
            reasons.append(f"{event.event_id} contradicted the claim.")
        elif event.polarity is EvidenceEventPolarity.SUPERSEDES:
            reasons.append(f"{event.event_id} superseded earlier evidence context.")

    after_uncertainty = _next_uncertainty(
        before_claim.uncertainty,
        after_confidence=after_confidence,
        has_evidence=bool(evidence_ids),
        contradiction_seen=contradiction_seen,
        policy=policy,
    )
    after_disposition = _next_disposition(
        belief.disposition,
        after_uncertainty=after_uncertainty,
        after_confidence=after_confidence,
        has_evidence=bool(evidence_ids),
        contradiction_seen=contradiction_seen,
        policy=policy,
    )
    after_claim = ClaimRecord(
        claim_id=before_claim.claim_id,
        statement=before_claim.statement,
        confidence=after_confidence,
        uncertainty=after_uncertainty,
        evidence_ids=tuple(evidence_ids),
        contradicted_by=tuple(contradicted_by),
        stale=before_claim.stale,
    )
    after_belief = BeliefRecord(
        belief_id=belief.belief_id,
        claim=after_claim,
        provenance=tuple(
            _append_unique(list(belief.provenance), ("belief-update-engine",))
        ),
        rationale=belief.rationale,
        disposition=after_disposition,
    )
    action = _update_action(
        before_claim=before_claim,
        after_claim=after_claim,
        before_disposition=belief.disposition,
        after_disposition=after_disposition,
    )
    update_record = BeliefUpdateRecord(
        update_id=f"belief-update-{update_index:03d}",
        belief_id=belief.belief_id,
        claim_id=belief.claim_id,
        action=action,
        event_ids=tuple(event_ids),
        before_confidence=before_claim.confidence,
        after_confidence=after_claim.confidence,
        before_uncertainty=before_claim.uncertainty,
        after_uncertainty=after_claim.uncertainty,
        before_disposition=belief.disposition,
        after_disposition=after_disposition,
        reasons=tuple(reasons),
    )
    return after_belief, update_record


def _next_uncertainty(
    current: UncertaintyStatus,
    *,
    after_confidence: float,
    has_evidence: bool,
    contradiction_seen: bool,
    policy: BeliefUpdatePolicy,
) -> UncertaintyStatus:
    """Compute uncertainty after evidence pressure."""

    if contradiction_seen:
        return UncertaintyStatus.DISPUTED
    if current is UncertaintyStatus.UNSAFE_TO_ACT:
        return current
    if after_confidence <= policy.needs_evidence_threshold:
        return UncertaintyStatus.UNKNOWN
    if has_evidence and after_confidence >= policy.known_threshold:
        return UncertaintyStatus.KNOWN
    if current in {UncertaintyStatus.UNKNOWN, UncertaintyStatus.ASSUMED}:
        return UncertaintyStatus.ASSUMED
    return current


def _next_disposition(
    current: BeliefDisposition,
    *,
    after_uncertainty: UncertaintyStatus,
    after_confidence: float,
    has_evidence: bool,
    contradiction_seen: bool,
    policy: BeliefUpdatePolicy,
) -> BeliefDisposition:
    """Compute belief disposition after evidence pressure."""

    if current is BeliefDisposition.RETIRED:
        return current
    if contradiction_seen or after_uncertainty in {
        UncertaintyStatus.DISPUTED,
        UncertaintyStatus.STALE,
        UncertaintyStatus.UNSAFE_TO_ACT,
    }:
        return BeliefDisposition.BLOCKED
    if not has_evidence or after_confidence <= policy.needs_evidence_threshold:
        return BeliefDisposition.NEEDS_EVIDENCE
    if after_uncertainty in {UncertaintyStatus.UNKNOWN, UncertaintyStatus.ASSUMED}:
        return BeliefDisposition.NEEDS_EVIDENCE
    return BeliefDisposition.ACTIVE


def _update_action(
    *,
    before_claim: ClaimRecord,
    after_claim: ClaimRecord,
    before_disposition: BeliefDisposition,
    after_disposition: BeliefDisposition,
) -> BeliefUpdateAction:
    """Classify a belief update action."""

    if after_disposition is BeliefDisposition.BLOCKED:
        return BeliefUpdateAction.BLOCKED
    if after_disposition is BeliefDisposition.NEEDS_EVIDENCE:
        return BeliefUpdateAction.NEEDS_EVIDENCE
    if after_claim.confidence > before_claim.confidence:
        return BeliefUpdateAction.STRENGTHENED
    if after_claim.confidence < before_claim.confidence:
        return BeliefUpdateAction.WEAKENED
    if (
        after_claim.uncertainty is before_claim.uncertainty
        and after_disposition is before_disposition
        and after_claim.evidence_ids == before_claim.evidence_ids
    ):
        return BeliefUpdateAction.UNCHANGED
    return BeliefUpdateAction.STRENGTHENED


def _reject_unknown_claim_targets(
    belief_state: BeliefState,
    ledger: UpdateLedger,
) -> None:
    """Reject evidence events targeting claims outside the belief state."""

    known_claim_ids = {belief.claim_id for belief in belief_state.beliefs}
    for event in ledger.events:
        for claim_id in event.target_claim_ids:
            if claim_id not in known_claim_ids:
                raise ValueError(
                    f"Evidence event {event.event_id} targets unknown claim_id: "
                    f"{claim_id}"
                )


def _clamp_confidence(value: float) -> float:
    """Clamp confidence into the accepted range with deterministic rounding."""

    return round(min(1.0, max(0.0, value)), 6)


def _append_unique(values: list[str], additions: tuple[str, ...]) -> list[str]:
    """Append unique values while preserving existing order."""

    updated = list(values)
    for value in additions:
        if value not in updated:
            updated.append(value)
    return updated


def _unique_ids(values: Iterable[str], *, label: str) -> set[str]:
    """Return unique ids while rejecting duplicates and blank values."""

    seen: set[str] = set()
    for value in values:
        if not value.strip():
            raise ValueError(f"{label} values cannot be empty.")
        if value in seen:
            raise ValueError(f"Duplicate {label} detected: {value}")
        seen.add(value)
    return seen


def _validate_reference_subset(
    referenced_ids: tuple[str, ...],
    known_ids: set[str],
    *,
    owner: str,
    label: str,
) -> None:
    """Reject references that are not present inside an update ledger."""

    missing = tuple(
        reference_id for reference_id in referenced_ids if reference_id not in known_ids
    )
    if missing:
        raise ValueError(f"{owner} references unknown {label}: {missing[0]}")
