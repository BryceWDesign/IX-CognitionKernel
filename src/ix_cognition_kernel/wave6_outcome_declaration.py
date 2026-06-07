"""Wave 6 final outcome declaration.

The Wave 6 attempt needs a final, reviewable outcome that cannot drift into
promotion language. This module declares only three outcomes: bounded review
ready, more evidence needed, or blocked interpretation. It indexes the late-stage
surfaces that justify that outcome while preserving the no-AGI boundary.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Protocol, TypeVar

E = TypeVar("E", bound=StrEnum)

WAVE_SIX_OUTCOME_SURFACE_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave6-outcome-surface-v1"
)
WAVE_SIX_OUTCOME_DECLARATION_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave6-outcome-declaration-v1"
)


class FingerprintedOutcomeArtifactLike(Protocol):
    """Structural protocol for artifacts referenced by the outcome declaration."""

    def fingerprint(self) -> str:
        """Return deterministic artifact fingerprint."""


class WaveSixOutcomeSurfaceKind(StrEnum):
    """Late-stage surfaces required for final Wave 6 outcome declaration."""

    FINAL_DOSSIER = "final-dossier"
    CI_RECEIPT_LEDGER = "ci-receipt-ledger"
    EVIDENCE_GAP_REGISTER = "evidence-gap-register"
    PUBLIC_CLAIM_REPORT = "public-claim-report"
    CONSISTENCY_REPORT = "consistency-report"


class WaveSixOutcomeFinding(StrEnum):
    """Finding for one outcome surface."""

    READY = "ready"
    NEEDS_MORE_EVIDENCE = "needs-more-evidence"
    BLOCKED = "blocked"


class WaveSixOutcomeDecision(StrEnum):
    """Final bounded outcome decision."""

    DECLARE_BOUNDED_REVIEW_READY = "declare-bounded-review-ready"
    CONTINUE_EVIDENCE_COLLECTION = "continue-evidence-collection"
    BLOCK_WAVE_SIX_INTERPRETATION = "block-wave-six-interpretation"


class WaveSixOutcomeStatus(StrEnum):
    """Computed status for the final Wave 6 outcome declaration."""

    BOUNDED_REVIEW_READY = "bounded-review-ready"
    NEEDS_MORE_EVIDENCE = "needs-more-evidence"
    BLOCKED = "blocked"


WAVE_SIX_REQUIRED_OUTCOME_SURFACES: tuple[WaveSixOutcomeSurfaceKind, ...] = (
    WaveSixOutcomeSurfaceKind.FINAL_DOSSIER,
    WaveSixOutcomeSurfaceKind.CI_RECEIPT_LEDGER,
    WaveSixOutcomeSurfaceKind.EVIDENCE_GAP_REGISTER,
    WaveSixOutcomeSurfaceKind.PUBLIC_CLAIM_REPORT,
    WaveSixOutcomeSurfaceKind.CONSISTENCY_REPORT,
)


@dataclass(frozen=True, slots=True)
class WaveSixOutcomeSurface:
    """One late-stage surface supporting the final Wave 6 outcome."""

    surface_id: str
    kind: WaveSixOutcomeSurfaceKind
    artifact_fingerprint: str
    summary: str
    evidence_ids: tuple[str, ...]
    reviewer_questions: tuple[str, ...]
    finding: WaveSixOutcomeFinding = WaveSixOutcomeFinding.READY
    requires_follow_up: bool = False
    blocks_outcome: bool = False
    schema_version: str = WAVE_SIX_OUTCOME_SURFACE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate outcome-surface identity, evidence, and finding semantics."""

        object.__setattr__(
            self,
            "surface_id",
            _require_non_empty(self.surface_id, "surface_id"),
        )
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
            raise ValueError("Outcome surfaces require evidence ids.")
        if not self.reviewer_questions:
            raise ValueError("Outcome surfaces require reviewer questions.")
        if self.finding is WaveSixOutcomeFinding.READY:
            if self.requires_follow_up:
                raise ValueError("Ready outcome surfaces cannot require follow-up.")
            if self.blocks_outcome:
                raise ValueError("Ready outcome surfaces cannot block outcome.")
        if (
            self.finding is WaveSixOutcomeFinding.NEEDS_MORE_EVIDENCE
            and not self.requires_follow_up
        ):
            raise ValueError("Needs-more-evidence outcome surfaces require follow-up.")
        if self.finding is WaveSixOutcomeFinding.BLOCKED and not self.blocks_outcome:
            raise ValueError("Blocked outcome surfaces must block outcome.")

    @property
    def ready(self) -> bool:
        """Return whether this surface is ready for bounded outcome declaration."""

        return self.finding is WaveSixOutcomeFinding.READY

    @property
    def needs_more_evidence(self) -> bool:
        """Return whether this surface still needs evidence."""

        return self.finding is WaveSixOutcomeFinding.NEEDS_MORE_EVIDENCE

    @property
    def blocks_bounded_outcome(self) -> bool:
        """Return whether this surface blocks the final bounded outcome."""

        return self.blocks_outcome or self.finding is WaveSixOutcomeFinding.BLOCKED

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic surface payload for hashing and review."""

        return {
            "artifact_fingerprint": self.artifact_fingerprint,
            "blocks_outcome": self.blocks_outcome,
            "evidence_ids": list(self.evidence_ids),
            "finding": self.finding.value,
            "kind": self.kind.value,
            "requires_follow_up": self.requires_follow_up,
            "reviewer_questions": list(self.reviewer_questions),
            "schema_version": self.schema_version,
            "summary": self.summary,
            "surface_id": self.surface_id,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this outcome surface."""

        return _stable_sha256(self.canonical_payload())


@dataclass(frozen=True, slots=True)
class WaveSixFinalOutcomeDeclaration:
    """Final bounded outcome declaration for the Wave 6 attempt."""

    declaration_id: str
    surfaces: tuple[WaveSixOutcomeSurface, ...]
    decision: WaveSixOutcomeDecision
    claim_boundary_statement: str
    generated_by_engine_id: str
    human_authority_id: str
    independent_reviewer_id: str
    required_surface_kinds: tuple[WaveSixOutcomeSurfaceKind, ...] = (
        WAVE_SIX_REQUIRED_OUTCOME_SURFACES
    )
    claims_agi: bool = False
    claims_production_ready: bool = False
    claims_certified: bool = False
    allows_autonomous_authority: bool = False
    notes: tuple[str, ...] = ()
    schema_version: str = WAVE_SIX_OUTCOME_DECLARATION_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate final outcome coverage, authority, and claim boundary."""

        object.__setattr__(
            self,
            "declaration_id",
            _require_non_empty(self.declaration_id, "declaration_id"),
        )
        if not self.surfaces:
            raise ValueError("Wave 6 final outcome declarations require surfaces.")
        sorted_surfaces = tuple(
            sorted(self.surfaces, key=lambda surface: surface.surface_id)
        )
        _require_unique_text(
            (surface.surface_id for surface in sorted_surfaces),
            label="surface_id",
        )
        _require_unique_enum(
            (surface.kind for surface in sorted_surfaces),
            label="surface kind",
        )
        object.__setattr__(self, "surfaces", sorted_surfaces)
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
            "required_surface_kinds",
            _normalize_unique_enum_tuple(
                self.required_surface_kinds,
                label="required surface kind",
            ),
        )
        object.__setattr__(
            self,
            "notes",
            _normalize_unique_text_tuple(self.notes, label="outcome note"),
        )
        object.__setattr__(
            self,
            "schema_version",
            _require_non_empty(self.schema_version, "schema_version"),
        )
        if self.decision is WaveSixOutcomeDecision.DECLARE_BOUNDED_REVIEW_READY:
            if self.missing_surface_kinds:
                raise ValueError("Ready outcome declarations require every surface.")
            if self.follow_up_surface_ids:
                raise ValueError("Ready outcome declarations cannot require follow-up.")
            if self.blocking_surface_ids:
                raise ValueError("Ready outcome declarations cannot include blockers.")
            if self.overclaim_present:
                raise ValueError(
                    "Ready outcome declarations cannot contain overclaims."
                )
            if not self.claim_boundary_statement_valid:
                raise ValueError("Ready outcome declarations require valid boundary.")
        if self.decision is WaveSixOutcomeDecision.BLOCK_WAVE_SIX_INTERPRETATION:
            if not self.blocking_surface_ids and not self.overclaim_present:
                raise ValueError(
                    "Blocked outcome declarations require blocker or overclaim."
                )

    @property
    def surface_ids(self) -> tuple[str, ...]:
        """Return outcome surface ids in deterministic order."""

        return tuple(surface.surface_id for surface in self.surfaces)

    @property
    def present_surface_kinds(self) -> tuple[WaveSixOutcomeSurfaceKind, ...]:
        """Return required surface kinds represented by the declaration."""

        present = {surface.kind for surface in self.surfaces}
        return tuple(kind for kind in self.required_surface_kinds if kind in present)

    @property
    def missing_surface_kinds(self) -> tuple[WaveSixOutcomeSurfaceKind, ...]:
        """Return required surface kinds missing from the declaration."""

        present = {surface.kind for surface in self.surfaces}
        return tuple(
            kind for kind in self.required_surface_kinds if kind not in present
        )

    @property
    def ready_surface_ids(self) -> tuple[str, ...]:
        """Return surface ids that are ready."""

        return tuple(surface.surface_id for surface in self.surfaces if surface.ready)

    @property
    def follow_up_surface_ids(self) -> tuple[str, ...]:
        """Return surface ids that still need evidence."""

        return tuple(
            surface.surface_id
            for surface in self.surfaces
            if surface.needs_more_evidence
        )

    @property
    def blocking_surface_ids(self) -> tuple[str, ...]:
        """Return surface ids that block the final outcome."""

        return tuple(
            surface.surface_id
            for surface in self.surfaces
            if surface.blocks_bounded_outcome
        )

    @property
    def overclaim_present(self) -> bool:
        """Return whether the declaration violates the claim boundary."""

        return (
            self.claims_agi
            or self.claims_production_ready
            or self.claims_certified
            or self.allows_autonomous_authority
        )

    @property
    def claim_boundary_statement_valid(self) -> bool:
        """Return whether the outcome statement preserves bounded review language."""

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
    def status(self) -> WaveSixOutcomeStatus:
        """Return fail-closed final outcome status."""

        if self.overclaim_present or self.blocking_surface_ids:
            return WaveSixOutcomeStatus.BLOCKED
        if (
            self.missing_surface_kinds
            or self.follow_up_surface_ids
            or not self.claim_boundary_statement_valid
        ):
            return WaveSixOutcomeStatus.NEEDS_MORE_EVIDENCE
        return WaveSixOutcomeStatus.BOUNDED_REVIEW_READY

    @property
    def ready_for_bounded_review(self) -> bool:
        """Return whether the final outcome is bounded-review ready."""

        return self.status is WaveSixOutcomeStatus.BOUNDED_REVIEW_READY

    @property
    def agi_claim_allowed(self) -> bool:
        """Return whether this declaration permits an AGI claim."""

        return False

    @property
    def public_outcome_statement(self) -> str:
        """Return the only allowed public outcome statement for this declaration."""

        if self.status is WaveSixOutcomeStatus.BOUNDED_REVIEW_READY:
            return (
                "Wave 6 is ready for bounded measured system-level cognition "
                "review under human authority and independent review. It is not "
                "an AGI claim."
            )
        if self.status is WaveSixOutcomeStatus.BLOCKED:
            return (
                "Wave 6 interpretation is blocked by the current evidence package. "
                "It is not an AGI claim."
            )
        return (
            "Wave 6 needs more evidence before bounded measured system-level "
            "cognition review. It is not an AGI claim."
        )

    def surface_for_kind(
        self,
        kind: WaveSixOutcomeSurfaceKind,
    ) -> WaveSixOutcomeSurface | None:
        """Return the outcome surface for a kind, if present."""

        for surface in self.surfaces:
            if surface.kind is kind:
                return surface
        return None

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic final outcome payload for hashing and review."""

        return {
            "agi_claim_allowed": self.agi_claim_allowed,
            "allows_autonomous_authority": self.allows_autonomous_authority,
            "blocking_surface_ids": list(self.blocking_surface_ids),
            "claim_boundary_statement": self.claim_boundary_statement,
            "claim_boundary_statement_valid": self.claim_boundary_statement_valid,
            "claims_agi": self.claims_agi,
            "claims_certified": self.claims_certified,
            "claims_production_ready": self.claims_production_ready,
            "decision": self.decision.value,
            "declaration_id": self.declaration_id,
            "follow_up_surface_ids": list(self.follow_up_surface_ids),
            "generated_by_engine_id": self.generated_by_engine_id,
            "human_authority_id": self.human_authority_id,
            "independent_reviewer_id": self.independent_reviewer_id,
            "missing_surface_kinds": [
                kind.value for kind in self.missing_surface_kinds
            ],
            "notes": list(self.notes),
            "present_surface_kinds": [
                kind.value for kind in self.present_surface_kinds
            ],
            "public_outcome_statement": self.public_outcome_statement,
            "ready_surface_ids": list(self.ready_surface_ids),
            "required_surface_kinds": [
                kind.value for kind in self.required_surface_kinds
            ],
            "schema_version": self.schema_version,
            "status": self.status.value,
            "surface_ids": list(self.surface_ids),
            "surfaces": [surface.canonical_payload() for surface in self.surfaces],
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this declaration."""

        return _stable_sha256(self.canonical_payload())


def build_wave_six_final_outcome_declaration(
    *,
    declaration_id: str,
    surfaces: Iterable[WaveSixOutcomeSurface],
    decision: WaveSixOutcomeDecision,
    claim_boundary_statement: str,
    generated_by_engine_id: str,
    human_authority_id: str,
    independent_reviewer_id: str,
    notes: Iterable[str] = (),
) -> WaveSixFinalOutcomeDeclaration:
    """Build a deterministic final Wave 6 outcome declaration."""

    return WaveSixFinalOutcomeDeclaration(
        declaration_id=declaration_id,
        surfaces=tuple(surfaces),
        decision=decision,
        claim_boundary_statement=claim_boundary_statement,
        generated_by_engine_id=generated_by_engine_id,
        human_authority_id=human_authority_id,
        independent_reviewer_id=independent_reviewer_id,
        notes=tuple(notes),
    )


def build_outcome_surface_from_artifact(
    *,
    surface_id: str,
    kind: WaveSixOutcomeSurfaceKind,
    artifact: FingerprintedOutcomeArtifactLike,
    ready: bool,
    summary: str,
    evidence_ids: Iterable[str],
    reviewer_questions: Iterable[str],
) -> WaveSixOutcomeSurface:
    """Build an outcome surface from a fingerprinted artifact."""

    finding = WaveSixOutcomeFinding.READY
    requires_follow_up = False
    if not ready:
        finding = WaveSixOutcomeFinding.NEEDS_MORE_EVIDENCE
        requires_follow_up = True
    return WaveSixOutcomeSurface(
        surface_id=surface_id,
        kind=kind,
        artifact_fingerprint=artifact.fingerprint(),
        summary=summary,
        evidence_ids=tuple(evidence_ids),
        reviewer_questions=tuple(reviewer_questions),
        finding=finding,
        requires_follow_up=requires_follow_up,
    )


def required_wave_six_outcome_surfaces() -> tuple[WaveSixOutcomeSurfaceKind, ...]:
    """Return required surfaces for final Wave 6 outcome declaration."""

    return WAVE_SIX_REQUIRED_OUTCOME_SURFACES


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
