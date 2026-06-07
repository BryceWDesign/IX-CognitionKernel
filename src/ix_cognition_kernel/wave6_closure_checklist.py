"""Wave 6 closure checklist.

The final README should not invent status language. This module records the final
pre-documentation closure checklist for Wave 6: which late-stage surfaces are
closed, which require follow-up, which block the bounded claim, and whether the
package may be described as ready for bounded measured system-level cognition
review. It never allows an AGI, production, certification, or autonomy claim.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, TypeVar

E = TypeVar("E", bound=StrEnum)

WAVE_SIX_CLOSURE_ITEM_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave6-closure-item-v1"
)
WAVE_SIX_CLOSURE_CHECKLIST_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave6-closure-checklist-v1"
)


class WaveSixClosureItemKind(StrEnum):
    """Final checklist items required before README/public closure."""

    FINAL_OUTCOME_DECLARATION = "final-outcome-declaration"
    FINAL_DOSSIER = "final-dossier"
    CI_RECEIPT_LEDGER = "ci-receipt-ledger"
    EVIDENCE_GAP_REGISTER = "evidence-gap-register"
    PUBLIC_CLAIM_REPORT = "public-claim-report"
    CONSISTENCY_REPORT = "consistency-report"
    REVIEW_SUMMARY = "review-summary"
    README_BOUNDARY = "readme-boundary"


class WaveSixClosureFinding(StrEnum):
    """Finding for one closure checklist item."""

    CLOSED = "closed"
    NEEDS_MORE_EVIDENCE = "needs-more-evidence"
    BLOCKS_CLOSURE = "blocks-closure"


class WaveSixClosureDecision(StrEnum):
    """Final closure checklist decision."""

    READY_FOR_README_UPDATE = "ready-for-readme-update"
    HOLD_FOR_MORE_EVIDENCE = "hold-for-more-evidence"
    BLOCK_README_UPDATE = "block-readme-update"


class WaveSixClosureStatus(StrEnum):
    """Computed closure status."""

    READY = "ready"
    NEEDS_MORE_EVIDENCE = "needs-more-evidence"
    BLOCKED = "blocked"


WAVE_SIX_REQUIRED_CLOSURE_ITEMS: tuple[WaveSixClosureItemKind, ...] = (
    WaveSixClosureItemKind.FINAL_OUTCOME_DECLARATION,
    WaveSixClosureItemKind.FINAL_DOSSIER,
    WaveSixClosureItemKind.CI_RECEIPT_LEDGER,
    WaveSixClosureItemKind.EVIDENCE_GAP_REGISTER,
    WaveSixClosureItemKind.PUBLIC_CLAIM_REPORT,
    WaveSixClosureItemKind.CONSISTENCY_REPORT,
    WaveSixClosureItemKind.REVIEW_SUMMARY,
    WaveSixClosureItemKind.README_BOUNDARY,
)


@dataclass(frozen=True, slots=True)
class WaveSixClosureItem:
    """One final pre-README closure checklist item."""

    item_id: str
    kind: WaveSixClosureItemKind
    artifact_fingerprint: str
    summary: str
    evidence_ids: tuple[str, ...]
    reviewer_questions: tuple[str, ...]
    finding: WaveSixClosureFinding = WaveSixClosureFinding.CLOSED
    requires_follow_up: bool = False
    blocks_closure: bool = False
    schema_version: str = WAVE_SIX_CLOSURE_ITEM_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate closure item identity, evidence, and finding semantics."""

        object.__setattr__(self, "item_id", _require_non_empty(self.item_id, "item_id"))
        object.__setattr__(
            self,
            "artifact_fingerprint",
            _require_non_empty(self.artifact_fingerprint, "artifact_fingerprint"),
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
            raise ValueError("Wave 6 closure items require evidence ids.")
        if not self.reviewer_questions:
            raise ValueError("Wave 6 closure items require reviewer questions.")
        if self.finding is WaveSixClosureFinding.CLOSED:
            if self.requires_follow_up:
                raise ValueError("Closed closure items cannot require follow-up.")
            if self.blocks_closure:
                raise ValueError("Closed closure items cannot block closure.")
        if (
            self.finding is WaveSixClosureFinding.NEEDS_MORE_EVIDENCE
            and not self.requires_follow_up
        ):
            raise ValueError("Needs-more-evidence closure items require follow-up.")
        if (
            self.finding is WaveSixClosureFinding.BLOCKS_CLOSURE
            and not self.blocks_closure
        ):
            raise ValueError("Blocking closure items must block closure.")

    @property
    def closed(self) -> bool:
        """Return whether this item is closed."""

        return self.finding is WaveSixClosureFinding.CLOSED

    @property
    def needs_more_evidence(self) -> bool:
        """Return whether this item still needs evidence."""

        return self.finding is WaveSixClosureFinding.NEEDS_MORE_EVIDENCE

    @property
    def blocks_bounded_closure(self) -> bool:
        """Return whether this item blocks final bounded closure."""

        return (
            self.blocks_closure
            or self.finding is WaveSixClosureFinding.BLOCKS_CLOSURE
        )

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic item payload for hashing and review."""

        return {
            "artifact_fingerprint": self.artifact_fingerprint,
            "blocks_closure": self.blocks_closure,
            "evidence_ids": list(self.evidence_ids),
            "finding": self.finding.value,
            "item_id": self.item_id,
            "kind": self.kind.value,
            "requires_follow_up": self.requires_follow_up,
            "reviewer_questions": list(self.reviewer_questions),
            "schema_version": self.schema_version,
            "summary": self.summary,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this closure item."""

        return _stable_sha256(self.canonical_payload())


@dataclass(frozen=True, slots=True)
class WaveSixClosureChecklist:
    """Final pre-README closure checklist for bounded Wave 6 review."""

    checklist_id: str
    items: tuple[WaveSixClosureItem, ...]
    decision: WaveSixClosureDecision
    claim_boundary_statement: str
    generated_by_engine_id: str
    human_authority_id: str
    independent_reviewer_id: str
    required_items: tuple[WaveSixClosureItemKind, ...] = (
        WAVE_SIX_REQUIRED_CLOSURE_ITEMS
    )
    claims_agi: bool = False
    claims_production_ready: bool = False
    claims_certified: bool = False
    allows_autonomous_authority: bool = False
    notes: tuple[str, ...] = ()
    schema_version: str = WAVE_SIX_CLOSURE_CHECKLIST_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate checklist coverage, authority fields, and claim boundary."""

        object.__setattr__(
            self,
            "checklist_id",
            _require_non_empty(self.checklist_id, "checklist_id"),
        )
        if not self.items:
            raise ValueError("Wave 6 closure checklists require items.")
        sorted_items = tuple(sorted(self.items, key=lambda item: item.item_id))
        _require_unique_text((item.item_id for item in sorted_items), label="item_id")
        _require_unique_enum((item.kind for item in sorted_items), label="item kind")
        object.__setattr__(self, "items", sorted_items)
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
            "required_items",
            _normalize_unique_enum_tuple(
                self.required_items,
                label="required item kind",
            ),
        )
        object.__setattr__(
            self,
            "notes",
            _normalize_unique_text_tuple(self.notes, label="checklist note"),
        )
        object.__setattr__(
            self,
            "schema_version",
            _require_non_empty(self.schema_version, "schema_version"),
        )
        if self.decision is WaveSixClosureDecision.READY_FOR_README_UPDATE:
            if self.missing_item_kinds:
                raise ValueError("Ready closure checklists require every item kind.")
            if self.follow_up_item_ids:
                raise ValueError("Ready closure checklists cannot need follow-up.")
            if self.blocking_item_ids:
                raise ValueError("Ready closure checklists cannot include blockers.")
            if self.overclaim_present:
                raise ValueError("Ready closure checklists cannot contain overclaims.")
            if not self.claim_boundary_statement_valid:
                raise ValueError("Ready closure checklists require valid boundary.")
        if self.decision is WaveSixClosureDecision.BLOCK_README_UPDATE:
            if not self.blocking_item_ids and not self.overclaim_present:
                raise ValueError(
                    "Blocked closure checklists require blocker or overclaim."
                )

    @property
    def item_ids(self) -> tuple[str, ...]:
        """Return closure item ids in deterministic order."""

        return tuple(item.item_id for item in self.items)

    @property
    def present_item_kinds(self) -> tuple[WaveSixClosureItemKind, ...]:
        """Return required closure item kinds represented by the checklist."""

        present = {item.kind for item in self.items}
        return tuple(kind for kind in self.required_items if kind in present)

    @property
    def missing_item_kinds(self) -> tuple[WaveSixClosureItemKind, ...]:
        """Return required closure item kinds missing from the checklist."""

        present = {item.kind for item in self.items}
        return tuple(kind for kind in self.required_items if kind not in present)

    @property
    def closed_item_ids(self) -> tuple[str, ...]:
        """Return closed item ids."""

        return tuple(item.item_id for item in self.items if item.closed)

    @property
    def follow_up_item_ids(self) -> tuple[str, ...]:
        """Return item ids that still need evidence."""

        return tuple(item.item_id for item in self.items if item.needs_more_evidence)

    @property
    def blocking_item_ids(self) -> tuple[str, ...]:
        """Return item ids that block final closure."""

        return tuple(
            item.item_id for item in self.items if item.blocks_bounded_closure
        )

    @property
    def overclaim_present(self) -> bool:
        """Return whether the checklist violates the claim boundary."""

        return (
            self.claims_agi
            or self.claims_production_ready
            or self.claims_certified
            or self.allows_autonomous_authority
        )

    @property
    def claim_boundary_statement_valid(self) -> bool:
        """Return whether the checklist preserves bounded review language."""

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
    def status(self) -> WaveSixClosureStatus:
        """Return fail-closed closure status."""

        if self.overclaim_present or self.blocking_item_ids:
            return WaveSixClosureStatus.BLOCKED
        if (
            self.missing_item_kinds
            or self.follow_up_item_ids
            or not self.claim_boundary_statement_valid
        ):
            return WaveSixClosureStatus.NEEDS_MORE_EVIDENCE
        return WaveSixClosureStatus.READY

    @property
    def ready_for_readme_update(self) -> bool:
        """Return whether README/public closure can be updated."""

        return self.status is WaveSixClosureStatus.READY

    @property
    def allowed_readme_status_label(self) -> str:
        """Return the only positive README status label allowed by this checklist."""

        if self.status is WaveSixClosureStatus.READY:
            return "Wave 6 bounded review ready"
        if self.status is WaveSixClosureStatus.BLOCKED:
            return "Wave 6 interpretation blocked"
        return "Wave 6 needs more evidence"

    def item_for_kind(
        self,
        kind: WaveSixClosureItemKind,
    ) -> WaveSixClosureItem | None:
        """Return the closure item for a kind, if present."""

        for item in self.items:
            if item.kind is kind:
                return item
        return None

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic checklist payload for hashing and review."""

        return {
            "allowed_readme_status_label": self.allowed_readme_status_label,
            "allows_autonomous_authority": self.allows_autonomous_authority,
            "blocking_item_ids": list(self.blocking_item_ids),
            "checklist_id": self.checklist_id,
            "claim_boundary_statement": self.claim_boundary_statement,
            "claim_boundary_statement_valid": self.claim_boundary_statement_valid,
            "claims_agi": self.claims_agi,
            "claims_certified": self.claims_certified,
            "claims_production_ready": self.claims_production_ready,
            "closed_item_ids": list(self.closed_item_ids),
            "decision": self.decision.value,
            "follow_up_item_ids": list(self.follow_up_item_ids),
            "generated_by_engine_id": self.generated_by_engine_id,
            "human_authority_id": self.human_authority_id,
            "independent_reviewer_id": self.independent_reviewer_id,
            "item_ids": list(self.item_ids),
            "items": [item.canonical_payload() for item in self.items],
            "missing_item_kinds": [kind.value for kind in self.missing_item_kinds],
            "notes": list(self.notes),
            "present_item_kinds": [kind.value for kind in self.present_item_kinds],
            "required_items": [kind.value for kind in self.required_items],
            "schema_version": self.schema_version,
            "status": self.status.value,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this closure checklist."""

        return _stable_sha256(self.canonical_payload())


def build_wave_six_closure_checklist(
    *,
    checklist_id: str,
    items: Iterable[WaveSixClosureItem],
    decision: WaveSixClosureDecision,
    claim_boundary_statement: str,
    generated_by_engine_id: str,
    human_authority_id: str,
    independent_reviewer_id: str,
    notes: Iterable[str] = (),
) -> WaveSixClosureChecklist:
    """Build a deterministic Wave 6 closure checklist."""

    return WaveSixClosureChecklist(
        checklist_id=checklist_id,
        items=tuple(items),
        decision=decision,
        claim_boundary_statement=claim_boundary_statement,
        generated_by_engine_id=generated_by_engine_id,
        human_authority_id=human_authority_id,
        independent_reviewer_id=independent_reviewer_id,
        notes=tuple(notes),
    )


def required_wave_six_closure_items() -> tuple[WaveSixClosureItemKind, ...]:
    """Return required final closure item kinds for Wave 6."""

    return WAVE_SIX_REQUIRED_CLOSURE_ITEMS


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

    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return hashlib.sha256(encoded).hexdigest()
