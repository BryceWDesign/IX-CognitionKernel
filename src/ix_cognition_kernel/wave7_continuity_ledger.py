"""Wave 7 continuity ledger.

The continuity ledger links persistent cognitive identity to ordered review
events. It records what changed, which evidence supports the change, whether
review is required, and whether any entry blocks stronger Wave 7 organism
claims.

The ledger does not treat memory as truth. It does not grant execution power.
It creates replayable continuity for AGI-directed cognitive research under
human authority.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from ix_cognition_kernel.wave7_cognitive_identity import CognitiveIdentity

WAVE_SEVEN_LEDGER_ENTRY_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave7-continuity-ledger-entry-v1"
)
WAVE_SEVEN_CONTINUITY_LEDGER_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave7-continuity-ledger-v1"
)


class ContinuityLedgerEntryKind(StrEnum):
    """Kinds of events that may preserve Wave 7 cognitive continuity."""

    IDENTITY_SNAPSHOT = "identity-snapshot"
    CONTINUITY_MARKER = "continuity-marker"
    MEASURED_OUTCOME = "measured-outcome"
    MEMORY_QUARANTINE = "memory-quarantine"
    FUTURE_REASONING_CHANGE = "future-reasoning-change"
    KNOWN_WEAKNESS = "known-weakness"
    IDENTITY_REVISION = "identity-revision"
    HUMAN_REVIEW = "human-review"
    CLAIM_BOUNDARY = "claim-boundary"


class ContinuityLedgerFinding(StrEnum):
    """Review finding for a continuity ledger entry."""

    RECORDED = "recorded"
    NEEDS_REVIEW = "needs-review"
    NEEDS_MORE_EVIDENCE = "needs-more-evidence"
    BLOCKS_CONTINUITY = "blocks-continuity"


class ContinuityLedgerDecision(StrEnum):
    """Overall fail-closed decision for a Wave 7 continuity ledger."""

    RECORD_ONLY = "record-only"
    READY_FOR_REVIEW = "ready-for-review"
    NEEDS_MORE_EVIDENCE = "needs-more-evidence"
    BLOCKED = "blocked"


@dataclass(frozen=True, slots=True)
class ContinuityLedgerEntry:
    """One replayable event in a persistent cognitive continuity ledger."""

    entry_id: str
    kind: ContinuityLedgerEntryKind
    subject_id: str
    summary: str
    evidence_ids: tuple[str, ...]
    previous_entry_id: str = ""
    marker_id: str = ""
    revision_id: str = ""
    weakness_id: str = ""
    finding: ContinuityLedgerFinding = ContinuityLedgerFinding.RECORDED
    requires_human_review: bool = False
    blocks_continuity: bool = False
    claims_memory_truth: bool = False
    allows_autonomous_execution: bool = False
    schema_version: str = WAVE_SEVEN_LEDGER_ENTRY_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate entry evidence, linkage, and fail-closed semantics."""

        if self.claims_memory_truth:
            raise ValueError("Continuity ledger entries must not claim memory truth.")
        if self.allows_autonomous_execution:
            raise ValueError(
                "Continuity ledger entries must not allow autonomous execution."
            )
        object.__setattr__(
            self,
            "entry_id",
            _require_non_empty(self.entry_id, "entry_id"),
        )
        object.__setattr__(
            self,
            "subject_id",
            _require_non_empty(self.subject_id, "subject_id"),
        )
        object.__setattr__(
            self,
            "summary",
            _require_non_empty(self.summary, "summary"),
        )
        object.__setattr__(
            self,
            "evidence_ids",
            _normalize_unique_text_tuple(self.evidence_ids, label="evidence_id"),
        )
        object.__setattr__(
            self,
            "previous_entry_id",
            _normalize_optional_text(self.previous_entry_id),
        )
        object.__setattr__(
            self,
            "marker_id",
            _normalize_optional_text(self.marker_id),
        )
        object.__setattr__(
            self,
            "revision_id",
            _normalize_optional_text(self.revision_id),
        )
        object.__setattr__(
            self,
            "weakness_id",
            _normalize_optional_text(self.weakness_id),
        )
        object.__setattr__(
            self,
            "schema_version",
            _require_non_empty(self.schema_version, "schema_version"),
        )
        if not self.evidence_ids:
            raise ValueError("Continuity ledger entries require evidence ids.")
        if (
            self.kind is ContinuityLedgerEntryKind.CONTINUITY_MARKER
            and not self.marker_id
        ):
            raise ValueError("Continuity marker entries require marker_id.")
        if (
            self.kind is ContinuityLedgerEntryKind.IDENTITY_REVISION
            and not self.revision_id
        ):
            raise ValueError("Identity revision entries require revision_id.")
        if (
            self.kind is ContinuityLedgerEntryKind.KNOWN_WEAKNESS
            and not self.weakness_id
        ):
            raise ValueError("Known weakness entries require weakness_id.")
        if (
            self.finding is ContinuityLedgerFinding.NEEDS_REVIEW
            and not self.requires_human_review
        ):
            raise ValueError("Needs-review ledger entries require human review.")
        if (
            self.finding is ContinuityLedgerFinding.BLOCKS_CONTINUITY
            and not self.blocks_continuity
        ):
            raise ValueError("Blocking ledger entries must block continuity.")
        if self.finding is ContinuityLedgerFinding.RECORDED and self.blocks_continuity:
            raise ValueError("Recorded ledger entries cannot block continuity.")

    @property
    def needs_review(self) -> bool:
        """Return whether this entry requires human review."""

        return (
            self.requires_human_review
            or self.finding is ContinuityLedgerFinding.NEEDS_REVIEW
        )

    @property
    def needs_more_evidence(self) -> bool:
        """Return whether this entry needs more evidence."""

        return self.finding is ContinuityLedgerFinding.NEEDS_MORE_EVIDENCE

    @property
    def blocks_claim(self) -> bool:
        """Return whether this entry blocks stronger continuity claims."""

        return (
            self.blocks_continuity
            or self.finding is ContinuityLedgerFinding.BLOCKS_CONTINUITY
        )

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic payload for review and hashing."""

        return {
            "allows_autonomous_execution": self.allows_autonomous_execution,
            "blocks_continuity": self.blocks_continuity,
            "claims_memory_truth": self.claims_memory_truth,
            "entry_id": self.entry_id,
            "evidence_ids": list(self.evidence_ids),
            "finding": self.finding.value,
            "kind": self.kind.value,
            "marker_id": self.marker_id,
            "previous_entry_id": self.previous_entry_id,
            "requires_human_review": self.requires_human_review,
            "revision_id": self.revision_id,
            "schema_version": self.schema_version,
            "subject_id": self.subject_id,
            "summary": self.summary,
            "weakness_id": self.weakness_id,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this entry."""

        return _stable_sha256(self.canonical_payload())


@dataclass(frozen=True, slots=True)
class ContinuityLedger:
    """Replayable Wave 7 ledger for persistent cognitive identity continuity."""

    ledger_id: str
    identity: CognitiveIdentity
    entries: tuple[ContinuityLedgerEntry, ...]
    decision: ContinuityLedgerDecision = ContinuityLedgerDecision.RECORD_ONLY
    notes: tuple[str, ...] = ()
    schema_version: str = WAVE_SEVEN_CONTINUITY_LEDGER_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate ledger linkage and preserve fail-closed status."""

        object.__setattr__(
            self,
            "ledger_id",
            _require_non_empty(self.ledger_id, "ledger_id"),
        )
        object.__setattr__(
            self,
            "entries",
            tuple(sorted(self.entries, key=lambda entry: entry.entry_id)),
        )
        object.__setattr__(
            self,
            "notes",
            _normalize_unique_text_tuple(self.notes, label="note"),
        )
        object.__setattr__(
            self,
            "schema_version",
            _require_non_empty(self.schema_version, "schema_version"),
        )
        if not self.entries:
            raise ValueError("Continuity ledgers require entries.")
        _ensure_unique((entry.entry_id for entry in self.entries), label="entry_id")
        entry_ids = {entry.entry_id for entry in self.entries}
        missing_previous = tuple(
            entry.previous_entry_id
            for entry in self.entries
            if entry.previous_entry_id and entry.previous_entry_id not in entry_ids
        )
        if missing_previous:
            missing = ", ".join(sorted(missing_previous))
            raise ValueError(
                f"Ledger entries reference missing previous ids: {missing}"
            )

        marker_ids = {entry.marker_id for entry in self.entries if entry.marker_id}
        missing_markers = tuple(
            marker_id
            for marker_id in self.identity.continuity_marker_ids
            if marker_id not in marker_ids
        )
        if missing_markers:
            missing = ", ".join(missing_markers)
            raise ValueError(f"Ledger missing identity continuity markers: {missing}")

    @property
    def entry_ids(self) -> tuple[str, ...]:
        """Return ledger entry ids."""

        return tuple(entry.entry_id for entry in self.entries)

    @property
    def marker_ids(self) -> tuple[str, ...]:
        """Return continuity marker ids referenced by ledger entries."""

        return _normalize_unique_text_tuple(
            (entry.marker_id for entry in self.entries if entry.marker_id),
            label="marker_id",
        )

    @property
    def revision_ids(self) -> tuple[str, ...]:
        """Return identity revision ids referenced by ledger entries."""

        return _normalize_unique_text_tuple(
            (entry.revision_id for entry in self.entries if entry.revision_id),
            label="revision_id",
        )

    @property
    def weakness_ids(self) -> tuple[str, ...]:
        """Return known weakness ids referenced by ledger entries."""

        return _normalize_unique_text_tuple(
            (entry.weakness_id for entry in self.entries if entry.weakness_id),
            label="weakness_id",
        )

    @property
    def evidence_ids(self) -> tuple[str, ...]:
        """Return all evidence ids bound to this continuity ledger."""

        evidence: list[str] = list(self.identity.evidence_ids)
        for entry in self.entries:
            evidence.extend(entry.evidence_ids)
        return _dedupe_text_tuple(evidence, label="evidence_id")

    @property
    def review_entry_ids(self) -> tuple[str, ...]:
        """Return entries requiring human review."""

        return tuple(entry.entry_id for entry in self.entries if entry.needs_review)

    @property
    def more_evidence_entry_ids(self) -> tuple[str, ...]:
        """Return entries needing more evidence."""

        return tuple(
            entry.entry_id for entry in self.entries if entry.needs_more_evidence
        )

    @property
    def blocked_entry_ids(self) -> tuple[str, ...]:
        """Return entries that block stronger continuity claims."""

        return tuple(entry.entry_id for entry in self.entries if entry.blocks_claim)

    @property
    def chain_complete(self) -> bool:
        """Return whether every previous-entry reference resolves."""

        entry_ids = {entry.entry_id for entry in self.entries}
        return all(
            not entry.previous_entry_id or entry.previous_entry_id in entry_ids
            for entry in self.entries
        )

    @property
    def ready_for_review(self) -> bool:
        """Return whether the ledger is ready for bounded Wave 7 review."""

        return (
            self.decision is ContinuityLedgerDecision.READY_FOR_REVIEW
            and self.chain_complete
            and bool(self.evidence_ids)
            and not self.blocked_entry_ids
            and not self.more_evidence_entry_ids
            and not self.identity.claims_agi
            and not self.identity.allows_autonomous_execution
        )

    @property
    def blocks_claim(self) -> bool:
        """Return whether this ledger blocks stronger Wave 7 claims."""

        return self.decision is ContinuityLedgerDecision.BLOCKED or bool(
            self.blocked_entry_ids
        )

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic ledger payload for review and hashing."""

        return {
            "blocked_entry_ids": list(self.blocked_entry_ids),
            "decision": self.decision.value,
            "entry_fingerprints": [entry.fingerprint() for entry in self.entries],
            "entry_ids": list(self.entry_ids),
            "evidence_ids": list(self.evidence_ids),
            "identity_fingerprint": self.identity.fingerprint(),
            "ledger_id": self.ledger_id,
            "marker_ids": list(self.marker_ids),
            "more_evidence_entry_ids": list(self.more_evidence_entry_ids),
            "notes": list(self.notes),
            "review_entry_ids": list(self.review_entry_ids),
            "revision_ids": list(self.revision_ids),
            "schema_version": self.schema_version,
            "weakness_ids": list(self.weakness_ids),
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this ledger."""

        return _stable_sha256(self.canonical_payload())


def build_continuity_ledger(
    *,
    ledger_id: str,
    identity: CognitiveIdentity,
    entries: Iterable[ContinuityLedgerEntry],
    decision: ContinuityLedgerDecision = ContinuityLedgerDecision.RECORD_ONLY,
    notes: Iterable[str] = (),
) -> ContinuityLedger:
    """Build a sorted Wave 7 continuity ledger."""

    return ContinuityLedger(
        ledger_id=ledger_id,
        identity=identity,
        entries=tuple(entries),
        decision=decision,
        notes=tuple(notes),
    )


def _require_non_empty(value: str, label: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{label} must not be empty.")
    return normalized


def _normalize_optional_text(value: str) -> str:
    return value.strip()


def _normalize_unique_text_tuple(
    values: Iterable[str], *, label: str
) -> tuple[str, ...]:
    normalized: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = _require_non_empty(value, label)
        if text in seen:
            raise ValueError(f"Duplicate {label}: {text}")
        seen.add(text)
        normalized.append(text)
    return tuple(sorted(normalized))


def _dedupe_text_tuple(values: Iterable[str], *, label: str) -> tuple[str, ...]:
    normalized: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = _require_non_empty(value, label)
        if text in seen:
            continue
        seen.add(text)
        normalized.append(text)
    return tuple(sorted(normalized))


def _ensure_unique(values: Iterable[str], *, label: str) -> None:
    seen: set[str] = set()
    for value in values:
        if value in seen:
            raise ValueError(f"Duplicate {label}: {value}")
        seen.add(value)


def _stable_sha256(payload: Mapping[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
