"""Evidence-event and update-ledger foundation for Wave 2.

Wave 2 starts when IX-CognitionKernel can receive evidence events as structured
inputs and preserve a deterministic audit trail for later belief updates. This
module does not update beliefs yet. It defines the event and ledger contracts the
belief-update engine must consume in later commits.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from enum import StrEnum


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


def empty_update_ledger() -> UpdateLedger:
    """Return an empty Wave 2 update ledger."""

    return UpdateLedger(events=())


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
