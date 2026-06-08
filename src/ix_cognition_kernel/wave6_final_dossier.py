"""Wave 6 final review dossier.

The final Wave 6 handoff should not force reviewers to hunt through every
artifact just to see whether the package is bounded, review-ready, blocked, or
still missing evidence. This module builds a deterministic final dossier over
late-stage review surfaces such as CI receipts, gap registers, public-claim
checks, consistency reports, audit manifests, and release manifests. It is a
handoff index, not an AGI claim or deployment approval.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Protocol, TypeVar

T = TypeVar("T")
E = TypeVar("E", bound=StrEnum)

WAVE_SIX_DOSSIER_ENTRY_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave6-final-dossier-entry-v1"
)
WAVE_SIX_FINAL_DOSSIER_SCHEMA_VERSION = "ix-cognition-kernel-wave6-final-dossier-v1"


class BoundedReviewArtifactLike(Protocol):
    """Structural protocol for late-stage bounded review artifacts."""

    @property
    def ready_for_bounded_review(self) -> bool:
        """Return whether the artifact is ready for bounded review."""

    def fingerprint(self) -> str:
        """Return deterministic artifact fingerprint."""


class WaveSixDossierEntryKind(StrEnum):
    """Late-stage artifacts expected in the final Wave 6 dossier."""

    MATURITY_DECISION_RECORD = "maturity-decision-record"
    AUDIT_MANIFEST = "audit-manifest"
    RELEASE_MANIFEST = "release-manifest"
    REVIEW_SUMMARY = "review-summary"
    CONSISTENCY_REPORT = "consistency-report"
    PUBLIC_CLAIM_REPORT = "public-claim-report"
    EVIDENCE_GAP_REGISTER = "evidence-gap-register"
    CI_RECEIPT_LEDGER = "ci-receipt-ledger"


class WaveSixDossierFinding(StrEnum):
    """Finding for one dossier entry."""

    INCLUDED = "included"
    NEEDS_MORE_EVIDENCE = "needs-more-evidence"
    BLOCKS_DOSSIER = "blocks-dossier"


class WaveSixDossierDecision(StrEnum):
    """Final decision for the Wave 6 dossier."""

    READY_FOR_BOUNDED_HANDOFF = "ready-for-bounded-handoff"
    HOLD_FOR_MORE_EVIDENCE = "hold-for-more-evidence"
    BLOCK_HANDOFF = "block-handoff"


class WaveSixDossierStatus(StrEnum):
    """Computed final dossier status."""

    READY = "ready"
    NEEDS_MORE_EVIDENCE = "needs-more-evidence"
    BLOCKED = "blocked"


WAVE_SIX_REQUIRED_DOSSIER_ENTRY_KINDS: tuple[WaveSixDossierEntryKind, ...] = (
    WaveSixDossierEntryKind.MATURITY_DECISION_RECORD,
    WaveSixDossierEntryKind.AUDIT_MANIFEST,
    WaveSixDossierEntryKind.RELEASE_MANIFEST,
    WaveSixDossierEntryKind.REVIEW_SUMMARY,
    WaveSixDossierEntryKind.CONSISTENCY_REPORT,
    WaveSixDossierEntryKind.PUBLIC_CLAIM_REPORT,
    WaveSixDossierEntryKind.EVIDENCE_GAP_REGISTER,
    WaveSixDossierEntryKind.CI_RECEIPT_LEDGER,
)


@dataclass(frozen=True, slots=True)
class WaveSixFinalDossierEntry:
    """One artifact entry inside the final Wave 6 review dossier."""

    entry_id: str
    kind: WaveSixDossierEntryKind
    artifact_fingerprint: str
    source_label: str
    summary: str
    evidence_ids: tuple[str, ...]
    reviewer_questions: tuple[str, ...]
    finding: WaveSixDossierFinding = WaveSixDossierFinding.INCLUDED
    requires_follow_up: bool = False
    blocks_handoff: bool = False
    schema_version: str = WAVE_SIX_DOSSIER_ENTRY_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate entry identity, evidence, and finding semantics."""

        object.__setattr__(
            self,
            "entry_id",
            _require_non_empty(self.entry_id, "entry_id"),
        )
        object.__setattr__(
            self,
            "artifact_fingerprint",
            _require_non_empty(self.artifact_fingerprint, "artifact_fingerprint"),
        )
        object.__setattr__(
            self,
            "source_label",
            _require_non_empty(self.source_label, "source_label"),
        )
        object.__setattr__(self, "summary", _require_non_empty(self.summary, "summary"))
        object.__setattr__(
            self,
            "evidence_ids",
            _normalize_unique_text_tuple(self.evidence_ids, label="evidence_id"),
        )
        object.__setattr__(
            self,
            "reviewer_questions",
            _normalize_unique_text_tuple(
                self.reviewer_questions,
                label="reviewer_question",
            ),
        )
        object.__setattr__(
            self,
            "schema_version",
            _require_non_empty(self.schema_version, "schema_version"),
        )
        if not self.evidence_ids:
            raise ValueError("Final dossier entries require evidence ids.")
        if not self.reviewer_questions:
            raise ValueError("Final dossier entries require reviewer questions.")
        if self.finding is WaveSixDossierFinding.INCLUDED:
            if self.requires_follow_up:
                raise ValueError("Included dossier entries cannot require follow-up.")
            if self.blocks_handoff:
                raise ValueError("Included dossier entries cannot block handoff.")
        if (
            self.finding is WaveSixDossierFinding.NEEDS_MORE_EVIDENCE
            and not self.requires_follow_up
        ):
            raise ValueError("Needs-more-evidence dossier entries require follow-up.")
        if (
            self.finding is WaveSixDossierFinding.BLOCKS_DOSSIER
            and not self.blocks_handoff
        ):
            raise ValueError("Blocking dossier entries must block handoff.")

    @property
    def included(self) -> bool:
        """Return whether this entry is included in the bounded handoff."""

        return self.finding is WaveSixDossierFinding.INCLUDED

    @property
    def needs_more_evidence(self) -> bool:
        """Return whether this entry still needs evidence."""

        return self.finding is WaveSixDossierFinding.NEEDS_MORE_EVIDENCE

    @property
    def blocks_bounded_handoff(self) -> bool:
        """Return whether this entry blocks the bounded handoff."""

        return (
            self.blocks_handoff or self.finding is WaveSixDossierFinding.BLOCKS_DOSSIER
        )

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic entry payload for hashing and review."""

        return {
            "artifact_fingerprint": self.artifact_fingerprint,
            "blocks_handoff": self.blocks_handoff,
            "entry_id": self.entry_id,
            "evidence_ids": list(self.evidence_ids),
            "finding": self.finding.value,
            "kind": self.kind.value,
            "requires_follow_up": self.requires_follow_up,
            "reviewer_questions": list(self.reviewer_questions),
            "schema_version": self.schema_version,
            "source_label": self.source_label,
            "summary": self.summary,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this entry."""

        return _stable_sha256(self.canonical_payload())


@dataclass(frozen=True, slots=True)
class WaveSixFinalDossier:
    """Final bounded review dossier for Wave 6 handoff."""

    dossier_id: str
    entries: tuple[WaveSixFinalDossierEntry, ...]
    decision: WaveSixDossierDecision
    claim_boundary_statement: str
    generated_by_engine_id: str
    human_authority_id: str
    independent_reviewer_id: str
    required_entry_kinds: tuple[WaveSixDossierEntryKind, ...] = (
        WAVE_SIX_REQUIRED_DOSSIER_ENTRY_KINDS
    )
    claims_agi: bool = False
    claims_production_ready: bool = False
    claims_certified: bool = False
    allows_autonomous_authority: bool = False
    notes: tuple[str, ...] = ()
    schema_version: str = WAVE_SIX_FINAL_DOSSIER_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate dossier coverage, authority fields, and claim boundary."""

        object.__setattr__(
            self,
            "dossier_id",
            _require_non_empty(self.dossier_id, "dossier_id"),
        )
        if not self.entries:
            raise ValueError("Wave 6 final dossiers require entries.")
        sorted_entries = tuple(sorted(self.entries, key=lambda entry: entry.entry_id))
        _require_unique_text(
            (entry.entry_id for entry in sorted_entries),
            label="entry_id",
        )
        _require_unique_enum(
            (entry.kind for entry in sorted_entries),
            label="entry kind",
        )
        object.__setattr__(self, "entries", sorted_entries)
        object.__setattr__(
            self,
            "claim_boundary_statement",
            _require_non_empty(
                self.claim_boundary_statement,
                "claim_boundary_statement",
            ),
        )
        object.__setattr__(
            self,
            "generated_by_engine_id",
            _require_non_empty(self.generated_by_engine_id, "generated_by_engine_id"),
        )
        object.__setattr__(
            self,
            "human_authority_id",
            _require_non_empty(self.human_authority_id, "human_authority_id"),
        )
        object.__setattr__(
            self,
            "independent_reviewer_id",
            _require_non_empty(
                self.independent_reviewer_id,
                "independent_reviewer_id",
            ),
        )
        object.__setattr__(
            self,
            "required_entry_kinds",
            _normalize_unique_enum_tuple(
                self.required_entry_kinds,
                label="required entry kind",
            ),
        )
        object.__setattr__(
            self,
            "notes",
            _normalize_unique_text_tuple(self.notes, label="dossier note"),
        )
        object.__setattr__(
            self,
            "schema_version",
            _require_non_empty(self.schema_version, "schema_version"),
        )
        if self.decision is WaveSixDossierDecision.READY_FOR_BOUNDED_HANDOFF:
            if self.missing_entry_kinds:
                raise ValueError("Ready final dossiers require every entry kind.")
            if self.follow_up_entry_ids:
                raise ValueError("Ready final dossiers cannot require follow-up.")
            if self.blocking_entry_ids:
                raise ValueError("Ready final dossiers cannot include blockers.")
            if self.overclaim_present:
                raise ValueError("Ready final dossiers cannot contain overclaims.")
            if not self.claim_boundary_statement_valid:
                raise ValueError("Ready final dossiers require valid claim boundary.")
        if (
            self.decision is WaveSixDossierDecision.BLOCK_HANDOFF
            and not self.blocking_entry_ids
            and not self.overclaim_present
        ):
            raise ValueError("Blocked final dossiers require blocker or overclaim.")

    @property
    def entry_ids(self) -> tuple[str, ...]:
        """Return dossier entry ids in deterministic order."""

        return tuple(entry.entry_id for entry in self.entries)

    @property
    def present_entry_kinds(self) -> tuple[WaveSixDossierEntryKind, ...]:
        """Return required entry kinds represented in the dossier."""

        present = {entry.kind for entry in self.entries}
        return tuple(kind for kind in self.required_entry_kinds if kind in present)

    @property
    def missing_entry_kinds(self) -> tuple[WaveSixDossierEntryKind, ...]:
        """Return required entry kinds missing from the dossier."""

        present = {entry.kind for entry in self.entries}
        return tuple(kind for kind in self.required_entry_kinds if kind not in present)

    @property
    def included_entry_ids(self) -> tuple[str, ...]:
        """Return included entry ids."""

        return tuple(entry.entry_id for entry in self.entries if entry.included)

    @property
    def follow_up_entry_ids(self) -> tuple[str, ...]:
        """Return entry ids that still need evidence."""

        return tuple(
            entry.entry_id for entry in self.entries if entry.needs_more_evidence
        )

    @property
    def blocking_entry_ids(self) -> tuple[str, ...]:
        """Return entry ids that block the bounded handoff."""

        return tuple(
            entry.entry_id for entry in self.entries if entry.blocks_bounded_handoff
        )

    @property
    def overclaim_present(self) -> bool:
        """Return whether the final dossier violates the claim boundary."""

        return (
            self.claims_agi
            or self.claims_production_ready
            or self.claims_certified
            or self.allows_autonomous_authority
        )

    @property
    def claim_boundary_statement_valid(self) -> bool:
        """Return whether the dossier preserves bounded review language."""

        normalized = self.claim_boundary_statement.casefold()
        required = (
            "measured system-level cognition",
            "bounded review",
            "not an agi",
            "human",
            "independent review",
        )
        return all(fragment in normalized for fragment in required)

    @property
    def status(self) -> WaveSixDossierStatus:
        """Return fail-closed final dossier status."""

        if self.overclaim_present or self.blocking_entry_ids:
            return WaveSixDossierStatus.BLOCKED
        if (
            self.missing_entry_kinds
            or self.follow_up_entry_ids
            or not self.claim_boundary_statement_valid
        ):
            return WaveSixDossierStatus.NEEDS_MORE_EVIDENCE
        return WaveSixDossierStatus.READY

    @property
    def ready_for_bounded_handoff(self) -> bool:
        """Return whether the dossier can be handed off for bounded review."""

        return self.status is WaveSixDossierStatus.READY

    def entry_for_kind(
        self,
        kind: WaveSixDossierEntryKind,
    ) -> WaveSixFinalDossierEntry | None:
        """Return the dossier entry for a kind, if present."""

        for entry in self.entries:
            if entry.kind is kind:
                return entry
        return None

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic dossier payload for hashing and review."""

        return {
            "allows_autonomous_authority": self.allows_autonomous_authority,
            "blocking_entry_ids": list(self.blocking_entry_ids),
            "claim_boundary_statement": self.claim_boundary_statement,
            "claim_boundary_statement_valid": self.claim_boundary_statement_valid,
            "claims_agi": self.claims_agi,
            "claims_certified": self.claims_certified,
            "claims_production_ready": self.claims_production_ready,
            "decision": self.decision.value,
            "dossier_id": self.dossier_id,
            "entries": [entry.canonical_payload() for entry in self.entries],
            "entry_ids": list(self.entry_ids),
            "follow_up_entry_ids": list(self.follow_up_entry_ids),
            "generated_by_engine_id": self.generated_by_engine_id,
            "human_authority_id": self.human_authority_id,
            "included_entry_ids": list(self.included_entry_ids),
            "independent_reviewer_id": self.independent_reviewer_id,
            "missing_entry_kinds": [kind.value for kind in self.missing_entry_kinds],
            "notes": list(self.notes),
            "present_entry_kinds": [kind.value for kind in self.present_entry_kinds],
            "required_entry_kinds": [kind.value for kind in self.required_entry_kinds],
            "schema_version": self.schema_version,
            "status": self.status.value,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this final dossier."""

        return _stable_sha256(self.canonical_payload())


def build_wave_six_final_dossier(
    *,
    dossier_id: str,
    entries: Iterable[WaveSixFinalDossierEntry],
    decision: WaveSixDossierDecision,
    claim_boundary_statement: str,
    generated_by_engine_id: str,
    human_authority_id: str,
    independent_reviewer_id: str,
    notes: Iterable[str] = (),
) -> WaveSixFinalDossier:
    """Build a deterministic final Wave 6 dossier."""

    return WaveSixFinalDossier(
        dossier_id=dossier_id,
        entries=tuple(entries),
        decision=decision,
        claim_boundary_statement=claim_boundary_statement,
        generated_by_engine_id=generated_by_engine_id,
        human_authority_id=human_authority_id,
        independent_reviewer_id=independent_reviewer_id,
        notes=tuple(notes),
    )


def build_dossier_entry_from_artifact(
    *,
    entry_id: str,
    kind: WaveSixDossierEntryKind,
    artifact: BoundedReviewArtifactLike,
    source_label: str,
    summary: str,
    evidence_ids: Iterable[str],
    reviewer_questions: Iterable[str],
) -> WaveSixFinalDossierEntry:
    """Build a dossier entry from any bounded review artifact protocol."""

    finding = WaveSixDossierFinding.INCLUDED
    requires_follow_up = False
    if not artifact.ready_for_bounded_review:
        finding = WaveSixDossierFinding.NEEDS_MORE_EVIDENCE
        requires_follow_up = True
    return WaveSixFinalDossierEntry(
        entry_id=entry_id,
        kind=kind,
        artifact_fingerprint=artifact.fingerprint(),
        source_label=source_label,
        summary=summary,
        evidence_ids=tuple(evidence_ids),
        reviewer_questions=tuple(reviewer_questions),
        finding=finding,
        requires_follow_up=requires_follow_up,
    )


def required_wave_six_dossier_entry_kinds() -> tuple[WaveSixDossierEntryKind, ...]:
    """Return required entry kinds for a final Wave 6 dossier."""

    return WAVE_SIX_REQUIRED_DOSSIER_ENTRY_KINDS


def _require_non_empty(value: str, label: str) -> str:
    """Return stripped text or raise when empty."""

    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{label} must not be empty.")
    return normalized


def _normalize_unique_text_tuple(
    values: Iterable[str], *, label: str
) -> tuple[str, ...]:
    """Normalize text values while rejecting blanks and duplicates."""

    normalized: list[str] = []
    seen: set[str] = set()
    for value in values:
        stripped = _require_non_empty(value, label)
        if stripped in seen:
            raise ValueError(f"Duplicate {label} detected: {stripped}")
        normalized.append(stripped)
        seen.add(stripped)
    return tuple(normalized)


def _normalize_unique_enum_tuple(values: Iterable[E], *, label: str) -> tuple[E, ...]:
    """Return enum values as a tuple while rejecting duplicates."""

    normalized: list[E] = []
    seen: set[E] = set()
    for value in values:
        if value in seen:
            raise ValueError(f"Duplicate {label} detected: {value.value}")
        normalized.append(value)
        seen.add(value)
    return tuple(normalized)


def _require_unique_text(values: Iterable[str], *, label: str) -> None:
    """Reject duplicate text values."""

    seen: set[str] = set()
    for value in values:
        if value in seen:
            raise ValueError(f"Duplicate {label} detected: {value}")
        seen.add(value)


def _require_unique_enum(values: Iterable[E], *, label: str) -> None:
    """Reject duplicate enum values."""

    seen: set[E] = set()
    for value in values:
        if value in seen:
            raise ValueError(f"Duplicate {label} detected: {value.value}")
        seen.add(value)


def _stable_sha256(payload: Mapping[str, Any]) -> str:
    """Return deterministic SHA-256 over a canonical JSON payload."""

    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
