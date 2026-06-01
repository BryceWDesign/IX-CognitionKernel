"""Belief timeline and audit-history records for Wave 2.

Wave 2 cannot merely produce revised state. It must preserve why a belief changed,
what evidence or staleness records triggered the change, and how the belief moved
through confidence, uncertainty, and disposition over time. This module turns
belief update results into durable, deterministic timelines without mutating the
underlying belief state or claiming autonomous memory.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from enum import StrEnum

from ix_cognition_kernel.learning import (
    BeliefUpdateAction,
    BeliefUpdateRecord,
    BeliefUpdateResult,
)
from ix_cognition_kernel.state import BeliefDisposition, UncertaintyStatus


class BeliefRevisionKind(StrEnum):
    """Classification for a durable belief revision timeline record."""

    STRENGTHENED = "strengthened"
    WEAKENED = "weakened"
    NEEDS_EVIDENCE = "needs-evidence"
    CONTRADICTED = "contradicted"
    STALE = "stale"
    UNCHANGED = "unchanged"


@dataclass(frozen=True, slots=True)
class BeliefRevisionRecord:
    """Durable history record for one belief revision."""

    revision_id: str
    revision_index: int
    belief_id: str
    claim_id: str
    update_id: str
    kind: BeliefRevisionKind
    event_ids: tuple[str, ...]
    staleness_ids: tuple[str, ...]
    before_confidence: float
    after_confidence: float
    before_uncertainty: UncertaintyStatus
    after_uncertainty: UncertaintyStatus
    before_disposition: BeliefDisposition
    after_disposition: BeliefDisposition
    reasons: tuple[str, ...]

    def __post_init__(self) -> None:
        """Validate revision identity, ordering, state bounds, and traceability."""

        if not self.revision_id.strip():
            raise ValueError("Belief revision records require a non-empty revision_id.")
        if self.revision_index < 0:
            raise ValueError("Belief revision_index cannot be negative.")
        if not self.belief_id.strip():
            raise ValueError("Belief revision records require a non-empty belief_id.")
        if not self.claim_id.strip():
            raise ValueError("Belief revision records require a non-empty claim_id.")
        if not self.update_id.strip():
            raise ValueError("Belief revision records require a non-empty update_id.")
        if not self.event_ids and not self.staleness_ids:
            raise ValueError(
                "Belief revision records require event_ids or staleness_ids."
            )
        _unique_ids(self.event_ids, label="belief revision event_id")
        _unique_ids(self.staleness_ids, label="belief revision staleness_id")
        if not self.reasons:
            raise ValueError("Belief revision records require reasons.")
        if any(not reason.strip() for reason in self.reasons):
            raise ValueError("Belief revision reasons cannot be empty.")
        for field_name, value in (
            ("before_confidence", self.before_confidence),
            ("after_confidence", self.after_confidence),
        ):
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{field_name} must be between 0.0 and 1.0.")

    @property
    def changed_confidence(self) -> bool:
        """Return whether the revision changed confidence."""

        return self.before_confidence != self.after_confidence

    @property
    def changed_uncertainty(self) -> bool:
        """Return whether the revision changed uncertainty."""

        return self.before_uncertainty is not self.after_uncertainty

    @property
    def changed_disposition(self) -> bool:
        """Return whether the revision changed disposition."""

        return self.before_disposition is not self.after_disposition

    @property
    def blocks_belief(self) -> bool:
        """Return whether this revision blocks the belief."""

        return self.after_disposition is BeliefDisposition.BLOCKED


@dataclass(frozen=True, slots=True)
class BeliefTimeline:
    """Ordered revision history for one belief."""

    belief_id: str
    claim_id: str
    revisions: tuple[BeliefRevisionRecord, ...]

    def __post_init__(self) -> None:
        """Validate revision identity, order, and belief/claim consistency."""

        if not self.belief_id.strip():
            raise ValueError("Belief timelines require a non-empty belief_id.")
        if not self.claim_id.strip():
            raise ValueError("Belief timelines require a non-empty claim_id.")
        if not self.revisions:
            raise ValueError("Belief timelines require at least one revision.")
        _unique_ids(
            (revision.revision_id for revision in self.revisions),
            label="revision_id",
        )
        _unique_ids(
            (str(revision.revision_index) for revision in self.revisions),
            label="revision_index",
        )
        for revision in self.revisions:
            if revision.belief_id != self.belief_id:
                raise ValueError("Belief timelines cannot mix belief ids.")
            if revision.claim_id != self.claim_id:
                raise ValueError("Belief timelines cannot mix claim ids.")

    @property
    def ordered_revisions(self) -> tuple[BeliefRevisionRecord, ...]:
        """Return revisions in deterministic revision order."""

        return tuple(
            sorted(self.revisions, key=lambda revision: revision.revision_index)
        )

    @property
    def latest_revision(self) -> BeliefRevisionRecord:
        """Return the latest revision in this timeline."""

        return self.ordered_revisions[-1]

    @property
    def event_ids(self) -> tuple[str, ...]:
        """Return all event ids referenced by the timeline, preserving order."""

        event_ids: list[str] = []
        for revision in self.ordered_revisions:
            event_ids = _append_unique(event_ids, revision.event_ids)
        return tuple(event_ids)

    @property
    def staleness_ids(self) -> tuple[str, ...]:
        """Return all staleness ids referenced by the timeline, preserving order."""

        staleness_ids: list[str] = []
        for revision in self.ordered_revisions:
            staleness_ids = _append_unique(staleness_ids, revision.staleness_ids)
        return tuple(staleness_ids)

    @property
    def blocking_revisions(self) -> tuple[BeliefRevisionRecord, ...]:
        """Return revisions that block the belief."""

        return tuple(
            revision for revision in self.ordered_revisions if revision.blocks_belief
        )


@dataclass(frozen=True, slots=True)
class BeliefHistory:
    """Durable review history across one or more belief update results."""

    timelines: tuple[BeliefTimeline, ...]

    def __post_init__(self) -> None:
        """Reject duplicate belief timelines."""

        _unique_ids(
            (timeline.belief_id for timeline in self.timelines),
            label="timeline belief_id",
        )

    @property
    def all_revisions(self) -> tuple[BeliefRevisionRecord, ...]:
        """Return all revisions in deterministic cross-timeline order."""

        return tuple(
            sorted(
                (
                    revision
                    for timeline in self.timelines
                    for revision in timeline.revisions
                ),
                key=lambda revision: revision.revision_index,
            )
        )

    @property
    def blocking_revisions(self) -> tuple[BeliefRevisionRecord, ...]:
        """Return all belief-blocking revisions."""

        return tuple(
            revision for revision in self.all_revisions if revision.blocks_belief
        )

    @property
    def stale_revisions(self) -> tuple[BeliefRevisionRecord, ...]:
        """Return revisions that marked beliefs stale."""

        return tuple(
            revision
            for revision in self.all_revisions
            if revision.kind is BeliefRevisionKind.STALE
        )

    @property
    def changed_belief_ids(self) -> tuple[str, ...]:
        """Return belief ids with at least one revision."""

        return tuple(timeline.belief_id for timeline in self.timelines)

    def timeline_by_belief_id(self, belief_id: str) -> BeliefTimeline:
        """Return a timeline by belief id."""

        for timeline in self.timelines:
            if timeline.belief_id == belief_id:
                return timeline
        raise ValueError(f"Unknown belief timeline belief_id: {belief_id}")


def build_belief_history(*results: BeliefUpdateResult) -> BeliefHistory:
    """Build durable belief timelines from one or more update results."""

    revisions_by_belief: dict[str, list[BeliefRevisionRecord]] = {}
    claim_by_belief: dict[str, str] = {}
    revision_index = 0
    for result in results:
        for update in result.updates:
            revision = _revision_from_update(update, revision_index=revision_index)
            revisions_by_belief.setdefault(update.belief_id, []).append(revision)
            existing_claim_id = claim_by_belief.setdefault(
                update.belief_id,
                update.claim_id,
            )
            if existing_claim_id != update.claim_id:
                raise ValueError("Belief history cannot mix claim ids per belief.")
            revision_index += 1
    timelines = tuple(
        BeliefTimeline(
            belief_id=belief_id,
            claim_id=claim_by_belief[belief_id],
            revisions=tuple(revisions),
        )
        for belief_id, revisions in revisions_by_belief.items()
    )
    return BeliefHistory(timelines=timelines)


def _revision_from_update(
    update: BeliefUpdateRecord,
    *,
    revision_index: int,
) -> BeliefRevisionRecord:
    """Create a durable revision record from a belief update record."""

    return BeliefRevisionRecord(
        revision_id=f"revision-{revision_index:03d}",
        revision_index=revision_index,
        belief_id=update.belief_id,
        claim_id=update.claim_id,
        update_id=update.update_id,
        kind=_revision_kind(update),
        event_ids=update.event_ids,
        staleness_ids=update.staleness_ids,
        before_confidence=update.before_confidence,
        after_confidence=update.after_confidence,
        before_uncertainty=update.before_uncertainty,
        after_uncertainty=update.after_uncertainty,
        before_disposition=update.before_disposition,
        after_disposition=update.after_disposition,
        reasons=update.reasons,
    )


def _revision_kind(update: BeliefUpdateRecord) -> BeliefRevisionKind:
    """Classify a durable revision from an update record."""

    if update.staleness_ids:
        return BeliefRevisionKind.STALE
    if update.action is BeliefUpdateAction.BLOCKED:
        return BeliefRevisionKind.CONTRADICTED
    if update.action is BeliefUpdateAction.NEEDS_EVIDENCE:
        return BeliefRevisionKind.NEEDS_EVIDENCE
    if update.action is BeliefUpdateAction.STRENGTHENED:
        return BeliefRevisionKind.STRENGTHENED
    if update.action is BeliefUpdateAction.WEAKENED:
        return BeliefRevisionKind.WEAKENED
    return BeliefRevisionKind.UNCHANGED


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
