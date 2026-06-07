"""Wave 6 human-review docket.

Measured system-level cognition evidence must not promote itself. This module
captures human review of the Wave 6 evidence ledgers and claim boundary. It is a
small deterministic review layer: reviewers can approve bounded review, demand
more evidence, or block interpretation. No docket can claim AGI, production
readiness, certification, or autonomous authority.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, TypeVar

T = TypeVar("T")
E = TypeVar("E", bound=StrEnum)

WAVE_SIX_REVIEW_ITEM_SCHEMA_VERSION = "ix-cognition-kernel-wave6-review-item-v1"
WAVE_SIX_HUMAN_REVIEW_DOCKET_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave6-human-review-docket-v1"
)


class WaveSixReviewItemKind(StrEnum):
    """Evidence item kinds that must be reviewable by humans."""

    MASTER_LOOP_TRACE = "master-loop-trace"
    CONTRACT_BUNDLE = "contract-bundle"
    DONOR_TRACEABILITY_MAP = "donor-traceability-map"
    REALITY_CORRECTION_LEDGER = "reality-correction-ledger"
    FUTURE_REASONING_CHANGE_LEDGER = "future-reasoning-change-ledger"
    TRANSFER_NOVELTY_LEDGER = "transfer-novelty-ledger"
    FALSIFICATION_LEDGER = "falsification-ledger"
    CLAIM_BOUNDARY_DECLARATION = "claim-boundary-declaration"


class WaveSixHumanReviewFinding(StrEnum):
    """Human-review findings for a Wave 6 evidence item."""

    ACCEPTED = "accepted"
    NEEDS_MORE_EVIDENCE = "needs-more-evidence"
    CONTRADICTED = "contradicted"
    OUT_OF_SCOPE = "out-of-scope"
    BLOCKS_CLAIM = "blocks-claim"


class WaveSixHumanReviewDecision(StrEnum):
    """Final human-review decision for the Wave 6 docket."""

    APPROVE_BOUNDED_WAVE_SIX_REVIEW = "approve-bounded-wave-six-review"
    NEEDS_MORE_EVIDENCE = "needs-more-evidence"
    BLOCK_CLAIM = "block-claim"


WAVE_SIX_REQUIRED_REVIEW_ITEM_KINDS: tuple[WaveSixReviewItemKind, ...] = (
    WaveSixReviewItemKind.MASTER_LOOP_TRACE,
    WaveSixReviewItemKind.CONTRACT_BUNDLE,
    WaveSixReviewItemKind.DONOR_TRACEABILITY_MAP,
    WaveSixReviewItemKind.REALITY_CORRECTION_LEDGER,
    WaveSixReviewItemKind.FUTURE_REASONING_CHANGE_LEDGER,
    WaveSixReviewItemKind.TRANSFER_NOVELTY_LEDGER,
    WaveSixReviewItemKind.FALSIFICATION_LEDGER,
    WaveSixReviewItemKind.CLAIM_BOUNDARY_DECLARATION,
)


@dataclass(frozen=True, slots=True)
class WaveSixReviewItem:
    """One evidence item submitted for human review."""

    item_id: str
    kind: WaveSixReviewItemKind
    summary: str
    artifact_fingerprint: str
    evidence_ids: tuple[str, ...]
    finding: WaveSixHumanReviewFinding
    reviewer_notes: tuple[str, ...]
    requires_follow_up: bool = False
    blocks_wave_six_claim: bool = False
    schema_version: str = WAVE_SIX_REVIEW_ITEM_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Normalize review item fields and enforce blocking semantics."""

        object.__setattr__(self, "item_id", _require_non_empty(self.item_id, "item_id"))
        object.__setattr__(self, "summary", _require_non_empty(self.summary, "summary"))
        object.__setattr__(
            self,
            "artifact_fingerprint",
            _require_non_empty(self.artifact_fingerprint, "artifact_fingerprint"),
        )
        object.__setattr__(
            self,
            "evidence_ids",
            _normalize_unique_text_tuple(self.evidence_ids, label="evidence_id"),
        )
        object.__setattr__(
            self,
            "reviewer_notes",
            _normalize_unique_text_tuple(self.reviewer_notes, label="reviewer_note"),
        )
        object.__setattr__(
            self,
            "schema_version",
            _require_non_empty(self.schema_version, "schema_version"),
        )
        if not self.evidence_ids:
            raise ValueError("Human-review items require evidence ids.")
        if not self.reviewer_notes:
            raise ValueError("Human-review items require reviewer notes.")
        if self.finding in {
            WaveSixHumanReviewFinding.CONTRADICTED,
            WaveSixHumanReviewFinding.BLOCKS_CLAIM,
        } and not self.blocks_wave_six_claim:
            raise ValueError("Contradicting or blocking findings must block the claim.")
        if (
            self.finding is WaveSixHumanReviewFinding.NEEDS_MORE_EVIDENCE
            and not self.requires_follow_up
        ):
            raise ValueError("Needs-more-evidence findings require follow-up.")

    @property
    def accepted(self) -> bool:
        """Return whether this item is accepted for bounded review."""

        return self.finding is WaveSixHumanReviewFinding.ACCEPTED

    @property
    def needs_more_evidence(self) -> bool:
        """Return whether this item requires more evidence."""

        return self.finding is WaveSixHumanReviewFinding.NEEDS_MORE_EVIDENCE

    @property
    def blocks_claim(self) -> bool:
        """Return whether this item blocks Wave 6 interpretation."""

        return self.blocks_wave_six_claim or self.finding in {
            WaveSixHumanReviewFinding.CONTRADICTED,
            WaveSixHumanReviewFinding.BLOCKS_CLAIM,
            WaveSixHumanReviewFinding.OUT_OF_SCOPE,
        }

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic payload for review and hashing."""

        return {
            "artifact_fingerprint": self.artifact_fingerprint,
            "blocks_wave_six_claim": self.blocks_wave_six_claim,
            "evidence_ids": list(self.evidence_ids),
            "finding": self.finding.value,
            "item_id": self.item_id,
            "kind": self.kind.value,
            "requires_follow_up": self.requires_follow_up,
            "reviewer_notes": list(self.reviewer_notes),
            "schema_version": self.schema_version,
            "summary": self.summary,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this review item."""

        return _stable_sha256(self.canonical_payload())


@dataclass(frozen=True, slots=True)
class WaveSixHumanReviewDocket:
    """Human-review docket for a Wave 6 evidence package."""

    docket_id: str
    reviewer_id: str
    reviewer_role: str
    items: tuple[WaveSixReviewItem, ...]
    decision: WaveSixHumanReviewDecision
    decision_rationale: str
    required_item_kinds: tuple[WaveSixReviewItemKind, ...] = (
        WAVE_SIX_REQUIRED_REVIEW_ITEM_KINDS
    )
    claims_agi: bool = False
    claims_production_ready: bool = False
    claims_certified: bool = False
    allows_autonomous_authority: bool = False
    notes: tuple[str, ...] = ()
    schema_version: str = WAVE_SIX_HUMAN_REVIEW_DOCKET_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate review authority, claim boundary, and evidence coverage."""

        if self.claims_agi:
            raise ValueError("Human-review dockets must not claim AGI.")
        if self.claims_production_ready:
            raise ValueError(
                "Human-review dockets must not claim production readiness."
            )
        if self.claims_certified:
            raise ValueError("Human-review dockets must not claim certification.")
        if self.allows_autonomous_authority:
            raise ValueError(
                "Human-review dockets must not allow autonomous authority."
            )
        object.__setattr__(
            self,
            "docket_id",
            _require_non_empty(self.docket_id, "docket_id"),
        )
        object.__setattr__(
            self,
            "reviewer_id",
            _require_non_empty(self.reviewer_id, "reviewer_id"),
        )
        object.__setattr__(
            self,
            "reviewer_role",
            _require_non_empty(self.reviewer_role, "reviewer_role"),
        )
        if not self.items:
            raise ValueError("Human-review dockets require at least one review item.")
        sorted_items = tuple(sorted(self.items, key=lambda item: item.item_id))
        _unique_ids((item.item_id for item in sorted_items), label="item_id")
        object.__setattr__(self, "items", sorted_items)
        object.__setattr__(
            self,
            "decision_rationale",
            _require_non_empty(self.decision_rationale, "decision_rationale"),
        )
        object.__setattr__(
            self,
            "required_item_kinds",
            _normalize_unique_enum_tuple(
                self.required_item_kinds, label="required review item kind"
            ),
        )
        object.__setattr__(
            self,
            "notes",
            _normalize_unique_text_tuple(self.notes, label="docket note"),
        )
        object.__setattr__(
            self,
            "schema_version",
            _require_non_empty(self.schema_version, "schema_version"),
        )
        if self.decision is WaveSixHumanReviewDecision.APPROVE_BOUNDED_WAVE_SIX_REVIEW:
            if self.missing_item_kinds:
                raise ValueError("Approved dockets require all review item kinds.")
            if self.blocking_item_ids:
                raise ValueError("Approved dockets cannot include blocking items.")
            if self.follow_up_item_ids:
                raise ValueError("Approved dockets cannot require follow-up evidence.")
        if (
            self.decision is WaveSixHumanReviewDecision.BLOCK_CLAIM
            and not self.blocking_item_ids
        ):
            raise ValueError("Blocked dockets require at least one blocking item.")

    @property
    def item_ids(self) -> tuple[str, ...]:
        """Return review item ids in deterministic order."""

        return tuple(item.item_id for item in self.items)

    @property
    def present_item_kinds(self) -> tuple[WaveSixReviewItemKind, ...]:
        """Return required review item kinds represented in the docket."""

        present = {item.kind for item in self.items}
        return tuple(kind for kind in self.required_item_kinds if kind in present)

    @property
    def missing_item_kinds(self) -> tuple[WaveSixReviewItemKind, ...]:
        """Return required review item kinds missing from the docket."""

        present = {item.kind for item in self.items}
        return tuple(kind for kind in self.required_item_kinds if kind not in present)

    @property
    def accepted_item_ids(self) -> tuple[str, ...]:
        """Return accepted review item ids."""

        return tuple(item.item_id for item in self.items if item.accepted)

    @property
    def follow_up_item_ids(self) -> tuple[str, ...]:
        """Return item ids requiring follow-up evidence."""

        return tuple(item.item_id for item in self.items if item.needs_more_evidence)

    @property
    def blocking_item_ids(self) -> tuple[str, ...]:
        """Return review item ids that block Wave 6 interpretation."""

        return tuple(item.item_id for item in self.items if item.blocks_claim)

    @property
    def approves_bounded_wave_six_review(self) -> bool:
        """Return whether human review approves bounded Wave 6 review."""

        return (
            self.decision
            is WaveSixHumanReviewDecision.APPROVE_BOUNDED_WAVE_SIX_REVIEW
            and not self.missing_item_kinds
            and not self.blocking_item_ids
            and not self.follow_up_item_ids
        )

    @property
    def blocks_wave_six_claim(self) -> bool:
        """Return whether human review blocks Wave 6 interpretation."""

        return (
            self.decision is WaveSixHumanReviewDecision.BLOCK_CLAIM
            or bool(self.blocking_item_ids)
        )

    def item_for_kind(self, kind: WaveSixReviewItemKind) -> WaveSixReviewItem | None:
        """Return the first review item for a kind, if present."""

        for item in self.items:
            if item.kind is kind:
                return item
        return None

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic docket payload for hashing and review."""

        return {
            "accepted_item_ids": list(self.accepted_item_ids),
            "allows_autonomous_authority": self.allows_autonomous_authority,
            "blocking_item_ids": list(self.blocking_item_ids),
            "claims_agi": self.claims_agi,
            "claims_certified": self.claims_certified,
            "claims_production_ready": self.claims_production_ready,
            "decision": self.decision.value,
            "decision_rationale": self.decision_rationale,
            "docket_id": self.docket_id,
            "follow_up_item_ids": list(self.follow_up_item_ids),
            "items": [item.canonical_payload() for item in self.items],
            "missing_item_kinds": [kind.value for kind in self.missing_item_kinds],
            "notes": list(self.notes),
            "required_item_kinds": [kind.value for kind in self.required_item_kinds],
            "reviewer_id": self.reviewer_id,
            "reviewer_role": self.reviewer_role,
            "schema_version": self.schema_version,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this docket."""

        return _stable_sha256(self.canonical_payload())


def build_wave_six_human_review_docket(
    *,
    docket_id: str,
    reviewer_id: str,
    reviewer_role: str,
    items: Iterable[WaveSixReviewItem],
    decision: WaveSixHumanReviewDecision,
    decision_rationale: str,
    notes: Iterable[str] = (),
) -> WaveSixHumanReviewDocket:
    """Build a deterministic Wave 6 human-review docket."""

    return WaveSixHumanReviewDocket(
        docket_id=docket_id,
        reviewer_id=reviewer_id,
        reviewer_role=reviewer_role,
        items=tuple(items),
        decision=decision,
        decision_rationale=decision_rationale,
        notes=tuple(notes),
    )


def required_wave_six_review_item_kinds() -> tuple[WaveSixReviewItemKind, ...]:
    """Return item kinds required for a complete Wave 6 review docket."""

    return WAVE_SIX_REQUIRED_REVIEW_ITEM_KINDS


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


def _unique_ids(values: Iterable[T], *, label: str) -> set[T]:
    """Return unique values while rejecting duplicates."""

    seen: set[T] = set()
    for value in values:
        if value in seen:
            raise ValueError(f"Duplicate {label} detected: {value}")
        seen.add(value)
    return seen


def _stable_sha256(payload: Mapping[str, Any]) -> str:
    """Return deterministic SHA-256 over a canonical JSON payload."""

    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
