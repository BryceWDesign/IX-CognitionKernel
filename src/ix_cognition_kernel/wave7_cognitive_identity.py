"""Wave 7 cognitive identity models.

Wave 7 treats identity as an auditable continuity substrate, not a personality
claim. Persistent cognition only matters when measured outcomes, known
weaknesses, and future-reasoning changes remain visible across trials without
treating memory as truth or granting autonomous authority.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

WAVE_SEVEN_COGNITIVE_IDENTITY_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave7-cognitive-identity-v1"
)
WAVE_SEVEN_CONTINUITY_MARKER_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave7-continuity-marker-v1"
)
WAVE_SEVEN_KNOWN_WEAKNESS_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave7-known-weakness-v1"
)
WAVE_SEVEN_IDENTITY_REVISION_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave7-identity-revision-v1"
)
WAVE_SEVEN_IDENTITY_REPORT_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave7-identity-continuity-report-v1"
)


class WeaknessStatus(StrEnum):
    """Reviewable status for a known cognitive weakness."""

    ACTIVE = "active"
    MITIGATED = "mitigated"
    SUPERSEDED = "superseded"


class IdentityContinuityDecision(StrEnum):
    """Fail-closed decisions for Wave 7 identity continuity review."""

    RECORD_ONLY = "record-only"
    READY_FOR_REVIEW = "ready-for-review"
    NEEDS_MORE_EVIDENCE = "needs-more-evidence"
    BLOCKED = "blocked"


@dataclass(frozen=True, slots=True)
class ContinuityMarker:
    """Auditable marker that preserves identity continuity across trials."""

    marker_id: str
    stage: str
    summary: str
    evidence_ids: tuple[str, ...]
    previous_marker_id: str = ""
    claims_memory_truth: bool = False
    allows_autonomous_execution: bool = False
    schema_version: str = WAVE_SEVEN_CONTINUITY_MARKER_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Normalize marker fields and reject inflated continuity claims."""

        if self.claims_memory_truth:
            raise ValueError("Continuity markers must not treat memory as truth.")
        if self.allows_autonomous_execution:
            raise ValueError(
                "Continuity markers must not allow autonomous execution."
            )
        object.__setattr__(
            self,
            "marker_id",
            _require_non_empty(self.marker_id, "marker_id"),
        )
        object.__setattr__(
            self,
            "stage",
            _require_non_empty(self.stage, "stage"),
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
            "previous_marker_id",
            _normalize_optional_text(self.previous_marker_id),
        )
        object.__setattr__(
            self,
            "schema_version",
            _require_non_empty(self.schema_version, "schema_version"),
        )
        if not self.evidence_ids:
            raise ValueError("Continuity markers require evidence ids.")

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic marker payload for hashing."""

        return {
            "allows_autonomous_execution": self.allows_autonomous_execution,
            "claims_memory_truth": self.claims_memory_truth,
            "evidence_ids": list(self.evidence_ids),
            "marker_id": self.marker_id,
            "previous_marker_id": self.previous_marker_id,
            "schema_version": self.schema_version,
            "stage": self.stage,
            "summary": self.summary,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this marker."""

        return _stable_sha256(self.canonical_payload())


@dataclass(frozen=True, slots=True)
class KnownWeakness:
    """Persistent weakness record that remains visible until resolved."""

    weakness_id: str
    domain: str
    description: str
    evidence_ids: tuple[str, ...]
    status: WeaknessStatus = WeaknessStatus.ACTIVE
    superseded_by_revision_id: str = ""
    schema_version: str = WAVE_SEVEN_KNOWN_WEAKNESS_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Normalize weakness fields and preserve evidence discipline."""

        object.__setattr__(
            self,
            "weakness_id",
            _require_non_empty(self.weakness_id, "weakness_id"),
        )
        object.__setattr__(
            self,
            "domain",
            _require_non_empty(self.domain, "domain"),
        )
        object.__setattr__(
            self,
            "description",
            _require_non_empty(self.description, "description"),
        )
        object.__setattr__(
            self,
            "evidence_ids",
            _normalize_unique_text_tuple(self.evidence_ids, label="evidence_id"),
        )
        object.__setattr__(
            self,
            "superseded_by_revision_id",
            _normalize_optional_text(self.superseded_by_revision_id),
        )
        object.__setattr__(
            self,
            "schema_version",
            _require_non_empty(self.schema_version, "schema_version"),
        )
        if not self.evidence_ids:
            raise ValueError("Known weaknesses require evidence ids.")
        if (
            self.status is WeaknessStatus.SUPERSEDED
            and not self.superseded_by_revision_id
        ):
            raise ValueError(
                "Superseded weaknesses require superseded_by_revision_id."
            )
        if (
            self.status is not WeaknessStatus.SUPERSEDED
            and self.superseded_by_revision_id
        ):
            raise ValueError(
                "Only superseded weaknesses may name superseding revisions."
            )

    @property
    def active(self) -> bool:
        """Return whether this weakness remains an active blocker or caution."""

        return self.status is WeaknessStatus.ACTIVE

    @property
    def resolved(self) -> bool:
        """Return whether this weakness is no longer active."""

        return self.status in {WeaknessStatus.MITIGATED, WeaknessStatus.SUPERSEDED}

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic weakness payload for hashing."""

        return {
            "description": self.description,
            "domain": self.domain,
            "evidence_ids": list(self.evidence_ids),
            "schema_version": self.schema_version,
            "status": self.status.value,
            "superseded_by_revision_id": self.superseded_by_revision_id,
            "weakness_id": self.weakness_id,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this weakness."""

        return _stable_sha256(self.canonical_payload())


@dataclass(frozen=True, slots=True)
class IdentityRevision:
    """Evidence-bound revision to persistent cognitive identity."""

    revision_id: str
    previous_identity_id: str
    revised_identity_id: str
    reason: str
    evidence_ids: tuple[str, ...]
    changed_belief_ids: tuple[str, ...]
    changed_memory_ids: tuple[str, ...]
    future_reasoning_change: str
    requires_human_review: bool = True
    self_approved: bool = False
    claims_agi: bool = False
    allows_autonomous_execution: bool = False
    schema_version: str = WAVE_SEVEN_IDENTITY_REVISION_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate identity revisions without allowing self-approval."""

        if not self.requires_human_review:
            raise ValueError("Identity revisions must require human review.")
        if self.self_approved:
            raise ValueError("Identity revisions must not self-approve.")
        if self.claims_agi:
            raise ValueError("Identity revisions must not claim AGI.")
        if self.allows_autonomous_execution:
            raise ValueError(
                "Identity revisions must not allow autonomous execution."
            )
        object.__setattr__(
            self,
            "revision_id",
            _require_non_empty(self.revision_id, "revision_id"),
        )
        object.__setattr__(
            self,
            "previous_identity_id",
            _require_non_empty(self.previous_identity_id, "previous_identity_id"),
        )
        object.__setattr__(
            self,
            "revised_identity_id",
            _require_non_empty(self.revised_identity_id, "revised_identity_id"),
        )
        object.__setattr__(
            self,
            "reason",
            _require_non_empty(self.reason, "reason"),
        )
        object.__setattr__(
            self,
            "evidence_ids",
            _normalize_unique_text_tuple(self.evidence_ids, label="evidence_id"),
        )
        object.__setattr__(
            self,
            "changed_belief_ids",
            _normalize_unique_text_tuple(
                self.changed_belief_ids, label="changed_belief_id"
            ),
        )
        object.__setattr__(
            self,
            "changed_memory_ids",
            _normalize_unique_text_tuple(
                self.changed_memory_ids, label="changed_memory_id"
            ),
        )
        object.__setattr__(
            self,
            "future_reasoning_change",
            _require_non_empty(
                self.future_reasoning_change, "future_reasoning_change"
            ),
        )
        object.__setattr__(
            self,
            "schema_version",
            _require_non_empty(self.schema_version, "schema_version"),
        )
        if self.previous_identity_id == self.revised_identity_id:
            raise ValueError("Identity revisions require a changed identity id.")
        if not self.evidence_ids:
            raise ValueError("Identity revisions require evidence ids.")
        if not self.changed_belief_ids and not self.changed_memory_ids:
            raise ValueError(
                "Identity revisions require changed belief or memory ids."
            )

    @property
    def changes_future_reasoning(self) -> bool:
        """Return whether the revision records future-reasoning change."""

        return bool(self.future_reasoning_change)

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic revision payload for hashing."""

        return {
            "allows_autonomous_execution": self.allows_autonomous_execution,
            "changed_belief_ids": list(self.changed_belief_ids),
            "changed_memory_ids": list(self.changed_memory_ids),
            "claims_agi": self.claims_agi,
            "evidence_ids": list(self.evidence_ids),
            "future_reasoning_change": self.future_reasoning_change,
            "previous_identity_id": self.previous_identity_id,
            "reason": self.reason,
            "requires_human_review": self.requires_human_review,
            "revised_identity_id": self.revised_identity_id,
            "revision_id": self.revision_id,
            "schema_version": self.schema_version,
            "self_approved": self.self_approved,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this revision."""

        return _stable_sha256(self.canonical_payload())


@dataclass(frozen=True, slots=True)
class CognitiveIdentity:
    """Persistent identity ledger for Wave 7 cognitive organism continuity."""

    identity_id: str
    mission: str
    doctrine_ids: tuple[str, ...]
    continuity_marker_ids: tuple[str, ...]
    known_weakness_ids: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    human_authority_ref: str
    treats_memory_as_truth: bool = False
    claims_agi: bool = False
    allows_autonomous_execution: bool = False
    schema_version: str = WAVE_SEVEN_COGNITIVE_IDENTITY_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Normalize identity state and reject overclaiming."""

        if self.treats_memory_as_truth:
            raise ValueError("Cognitive identity must not treat memory as truth.")
        if self.claims_agi:
            raise ValueError("Cognitive identity must not claim AGI.")
        if self.allows_autonomous_execution:
            raise ValueError(
                "Cognitive identity must not allow autonomous execution."
            )
        object.__setattr__(
            self,
            "identity_id",
            _require_non_empty(self.identity_id, "identity_id"),
        )
        object.__setattr__(
            self,
            "mission",
            _require_non_empty(self.mission, "mission"),
        )
        object.__setattr__(
            self,
            "doctrine_ids",
            _normalize_unique_text_tuple(self.doctrine_ids, label="doctrine_id"),
        )
        object.__setattr__(
            self,
            "continuity_marker_ids",
            _normalize_unique_text_tuple(
                self.continuity_marker_ids, label="continuity_marker_id"
            ),
        )
        object.__setattr__(
            self,
            "known_weakness_ids",
            _normalize_unique_text_tuple(
                self.known_weakness_ids, label="known_weakness_id"
            ),
        )
        object.__setattr__(
            self,
            "evidence_ids",
            _normalize_unique_text_tuple(self.evidence_ids, label="evidence_id"),
        )
        object.__setattr__(
            self,
            "human_authority_ref",
            _require_non_empty(self.human_authority_ref, "human_authority_ref"),
        )
        object.__setattr__(
            self,
            "schema_version",
            _require_non_empty(self.schema_version, "schema_version"),
        )
        if not self.doctrine_ids:
            raise ValueError("Cognitive identity requires doctrine ids.")
        if not self.continuity_marker_ids:
            raise ValueError("Cognitive identity requires continuity marker ids.")
        if not self.evidence_ids:
            raise ValueError("Cognitive identity requires evidence ids.")

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic identity payload for hashing."""

        return {
            "allows_autonomous_execution": self.allows_autonomous_execution,
            "claims_agi": self.claims_agi,
            "continuity_marker_ids": list(self.continuity_marker_ids),
            "doctrine_ids": list(self.doctrine_ids),
            "evidence_ids": list(self.evidence_ids),
            "human_authority_ref": self.human_authority_ref,
            "identity_id": self.identity_id,
            "known_weakness_ids": list(self.known_weakness_ids),
            "mission": self.mission,
            "schema_version": self.schema_version,
            "treats_memory_as_truth": self.treats_memory_as_truth,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this identity."""

        return _stable_sha256(self.canonical_payload())


@dataclass(frozen=True, slots=True)
class IdentityContinuityReport:
    """Review report for persistent cognitive identity continuity."""

    report_id: str
    identity: CognitiveIdentity
    markers: tuple[ContinuityMarker, ...]
    revisions: tuple[IdentityRevision, ...] = ()
    weaknesses: tuple[KnownWeakness, ...] = ()
    notes: tuple[str, ...] = ()
    decision: IdentityContinuityDecision = IdentityContinuityDecision.RECORD_ONLY
    schema_version: str = WAVE_SEVEN_IDENTITY_REPORT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate report linkage and preserve visible unresolved weaknesses."""

        object.__setattr__(
            self,
            "report_id",
            _require_non_empty(self.report_id, "report_id"),
        )
        object.__setattr__(
            self,
            "markers",
            tuple(sorted(self.markers, key=lambda marker: marker.marker_id)),
        )
        object.__setattr__(
            self,
            "revisions",
            tuple(sorted(self.revisions, key=lambda revision: revision.revision_id)),
        )
        object.__setattr__(
            self,
            "weaknesses",
            tuple(sorted(self.weaknesses, key=lambda weakness: weakness.weakness_id)),
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
        _ensure_unique(
            (marker.marker_id for marker in self.markers), label="marker_id"
        )
        _ensure_unique(
            (revision.revision_id for revision in self.revisions),
            label="revision_id",
        )
        _ensure_unique(
            (weakness.weakness_id for weakness in self.weaknesses),
            label="weakness_id",
        )
        marker_ids = {marker.marker_id for marker in self.markers}
        missing_markers = tuple(
            marker_id
            for marker_id in self.identity.continuity_marker_ids
            if marker_id not in marker_ids
        )
        if missing_markers:
            missing = ", ".join(missing_markers)
            raise ValueError(f"Report missing continuity markers: {missing}")

        weakness_ids = {weakness.weakness_id for weakness in self.weaknesses}
        missing_weaknesses = tuple(
            weakness_id
            for weakness_id in self.identity.known_weakness_ids
            if weakness_id not in weakness_ids
        )
        if missing_weaknesses:
            missing = ", ".join(missing_weaknesses)
            raise ValueError(f"Report missing known weaknesses: {missing}")

    @property
    def marker_ids(self) -> tuple[str, ...]:
        """Return continuity marker ids included in this report."""

        return tuple(marker.marker_id for marker in self.markers)

    @property
    def revision_ids(self) -> tuple[str, ...]:
        """Return identity revision ids included in this report."""

        return tuple(revision.revision_id for revision in self.revisions)

    @property
    def active_weakness_ids(self) -> tuple[str, ...]:
        """Return active weakness ids that remain visible to reviewers."""

        return tuple(
            weakness.weakness_id for weakness in self.weaknesses if weakness.active
        )

    @property
    def resolved_weakness_ids(self) -> tuple[str, ...]:
        """Return mitigated or superseded weakness ids."""

        return tuple(
            weakness.weakness_id for weakness in self.weaknesses if weakness.resolved
        )

    @property
    def evidence_ids(self) -> tuple[str, ...]:
        """Return all evidence ids bound to identity continuity."""

        evidence: list[str] = list(self.identity.evidence_ids)
        for marker in self.markers:
            evidence.extend(marker.evidence_ids)
        for revision in self.revisions:
            evidence.extend(revision.evidence_ids)
        for weakness in self.weaknesses:
            evidence.extend(weakness.evidence_ids)
        return _normalize_unique_text_tuple(evidence, label="evidence_id")

    @property
    def has_future_reasoning_revision(self) -> bool:
        """Return whether any revision records future-reasoning change."""

        return any(revision.changes_future_reasoning for revision in self.revisions)

    @property
    def blocks_claim(self) -> bool:
        """Return whether the report blocks stronger maturity claims."""

        return self.decision is IdentityContinuityDecision.BLOCKED

    @property
    def ready_for_review(self) -> bool:
        """Return whether identity continuity is ready for Wave 7 review."""

        return (
            self.decision is IdentityContinuityDecision.READY_FOR_REVIEW
            and bool(self.markers)
            and bool(self.evidence_ids)
            and not self.identity.claims_agi
            and not self.identity.allows_autonomous_execution
        )

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic report payload for hashing."""

        return {
            "active_weakness_ids": list(self.active_weakness_ids),
            "decision": self.decision.value,
            "evidence_ids": list(self.evidence_ids),
            "identity": self.identity.canonical_payload(),
            "marker_fingerprints": [marker.fingerprint() for marker in self.markers],
            "notes": list(self.notes),
            "report_id": self.report_id,
            "resolved_weakness_ids": list(self.resolved_weakness_ids),
            "revision_fingerprints": [
                revision.fingerprint() for revision in self.revisions
            ],
            "schema_version": self.schema_version,
            "weakness_fingerprints": [
                weakness.fingerprint() for weakness in self.weaknesses
            ],
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this report."""

        return _stable_sha256(self.canonical_payload())


def build_identity_continuity_report(
    *,
    report_id: str,
    identity: CognitiveIdentity,
    markers: Iterable[ContinuityMarker],
    revisions: Iterable[IdentityRevision] = (),
    weaknesses: Iterable[KnownWeakness] = (),
    notes: Iterable[str] = (),
    decision: IdentityContinuityDecision = IdentityContinuityDecision.RECORD_ONLY,
) -> IdentityContinuityReport:
    """Build a sorted Wave 7 identity continuity report."""

    return IdentityContinuityReport(
        report_id=report_id,
        identity=identity,
        markers=tuple(markers),
        revisions=tuple(revisions),
        weaknesses=tuple(weaknesses),
        notes=tuple(notes),
        decision=decision,
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


def _ensure_unique(values: Iterable[str], *, label: str) -> None:
    seen: set[str] = set()
    for value in values:
        if value in seen:
            raise ValueError(f"Duplicate {label}: {value}")
        seen.add(value)


def _stable_sha256(payload: Mapping[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return hashlib.sha256(encoded).hexdigest()
