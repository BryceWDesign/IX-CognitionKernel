"""Wave 6 public-claim guard.

Evidence can be bounded while public wording still drifts into overclaiming. This
module checks public-facing Wave 6 language before README, GitHub, release, or
social copy can be treated as review-ready. The scanner is deliberately simple
and deterministic: required boundary fragments must be present, prohibited
phrases block publication, and human plus independent review remain explicit.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, TypeVar

E = TypeVar("E", bound=StrEnum)

WAVE_SIX_PUBLIC_CLAIM_SCHEMA_VERSION = "ix-cognition-kernel-wave6-public-claim-v1"
WAVE_SIX_PUBLIC_CLAIM_REPORT_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave6-public-claim-report-v1"
)


class WaveSixPublicClaimSurface(StrEnum):
    """Public surfaces that may describe the Wave 6 package."""

    README = "readme"
    GITHUB_ABOUT = "github-about"
    RELEASE_SUMMARY = "release-summary"
    AUDIT_MANIFEST = "audit-manifest"
    INDEPENDENT_REVIEW_PACKET = "independent-review-packet"
    SOCIAL_POST = "social-post"


class WaveSixPublicClaimFinding(StrEnum):
    """Finding for one public claim statement."""

    ACCEPTED = "accepted"
    NEEDS_MORE_EVIDENCE = "needs-more-evidence"
    BLOCKS_PUBLICATION = "blocks-publication"


class WaveSixPublicClaimDecision(StrEnum):
    """Final decision for the public-claim report."""

    APPROVE_BOUNDED_PUBLICATION = "approve-bounded-publication"
    HOLD_FOR_MORE_EVIDENCE = "hold-for-more-evidence"
    BLOCK_PUBLICATION = "block-publication"


class WaveSixPublicClaimStatus(StrEnum):
    """Fail-closed public-claim status."""

    READY_FOR_BOUNDED_PUBLICATION = "ready-for-bounded-publication"
    NEEDS_MORE_EVIDENCE = "needs-more-evidence"
    BLOCKED = "blocked"


WAVE_SIX_REQUIRED_PUBLIC_CLAIM_SURFACES: tuple[WaveSixPublicClaimSurface, ...] = (
    WaveSixPublicClaimSurface.README,
    WaveSixPublicClaimSurface.GITHUB_ABOUT,
    WaveSixPublicClaimSurface.RELEASE_SUMMARY,
    WaveSixPublicClaimSurface.INDEPENDENT_REVIEW_PACKET,
)

WAVE_SIX_REQUIRED_PUBLIC_CLAIM_FRAGMENTS: tuple[str, ...] = (
    "measured system-level cognition",
    "bounded review",
    "not an agi",
    "human",
    "independent review",
)

WAVE_SIX_PROHIBITED_PUBLIC_CLAIM_FRAGMENTS: tuple[str, ...] = (
    "agi achieved",
    "true agi",
    "artificial general intelligence achieved",
    "production ready",
    "certified safe",
    "autonomous authority",
    "self-validated intelligence",
    "human review not required",
    "universal transfer proven",
)


@dataclass(frozen=True, slots=True)
class WaveSixPublicClaimStatement:
    """One public-facing Wave 6 claim statement under review."""

    statement_id: str
    surface: WaveSixPublicClaimSurface
    text: str
    intended_audience: str
    evidence_ids: tuple[str, ...]
    reviewer_questions: tuple[str, ...]
    finding: WaveSixPublicClaimFinding = WaveSixPublicClaimFinding.ACCEPTED
    required_fragments: tuple[str, ...] = WAVE_SIX_REQUIRED_PUBLIC_CLAIM_FRAGMENTS
    prohibited_fragments: tuple[str, ...] = WAVE_SIX_PROHIBITED_PUBLIC_CLAIM_FRAGMENTS
    requires_follow_up: bool = False
    blocks_publication: bool = False
    claims_agi: bool = False
    claims_production_ready: bool = False
    claims_certified: bool = False
    allows_autonomous_authority: bool = False
    schema_version: str = WAVE_SIX_PUBLIC_CLAIM_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate statement evidence, phrase lists, and finding semantics."""

        object.__setattr__(
            self,
            "statement_id",
            _require_non_empty(self.statement_id, "statement_id"),
        )
        object.__setattr__(self, "text", _require_non_empty(self.text, "text"))
        object.__setattr__(
            self,
            "intended_audience",
            _require_non_empty(self.intended_audience, "intended_audience"),
        )
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
            "required_fragments",
            _normalize_unique_lower_tuple(
                self.required_fragments,
                label="required_fragment",
            ),
        )
        object.__setattr__(
            self,
            "prohibited_fragments",
            _normalize_unique_lower_tuple(
                self.prohibited_fragments,
                label="prohibited_fragment",
            ),
        )
        object.__setattr__(
            self,
            "schema_version",
            _require_non_empty(self.schema_version, "schema_version"),
        )
        if not self.evidence_ids:
            raise ValueError("Public claim statements require evidence ids.")
        if not self.reviewer_questions:
            raise ValueError("Public claim statements require reviewer questions.")
        if self.finding is WaveSixPublicClaimFinding.ACCEPTED:
            if self.requires_follow_up:
                raise ValueError("Accepted public claims cannot require follow-up.")
            if self.blocks_publication:
                raise ValueError("Accepted public claims cannot block publication.")
            if self.overclaim_present or self.prohibited_matches:
                raise ValueError("Accepted public claims cannot contain overclaims.")
            if self.missing_required_fragments:
                raise ValueError("Accepted public claims require boundary fragments.")
        if (
            self.finding is WaveSixPublicClaimFinding.NEEDS_MORE_EVIDENCE
            and not self.requires_follow_up
        ):
            raise ValueError("Needs-more-evidence public claims require follow-up.")
        if (
            self.finding is WaveSixPublicClaimFinding.BLOCKS_PUBLICATION
            and not self.blocks_publication
            and not self.overclaim_present
            and not self.prohibited_matches
        ):
            raise ValueError("Blocking public claims require blocker or overclaim.")

    @property
    def normalized_text(self) -> str:
        """Return normalized text used for deterministic phrase checks."""

        return " ".join(self.text.casefold().split())

    @property
    def missing_required_fragments(self) -> tuple[str, ...]:
        """Return required boundary fragments missing from the text."""

        normalized = self.normalized_text
        return tuple(
            fragment
            for fragment in self.required_fragments
            if fragment not in normalized
        )

    @property
    def prohibited_matches(self) -> tuple[str, ...]:
        """Return prohibited public-claim fragments found in the text."""

        normalized = self.normalized_text
        return tuple(
            fragment for fragment in self.prohibited_fragments if fragment in normalized
        )

    @property
    def overclaim_present(self) -> bool:
        """Return whether this statement carries explicit overclaim flags."""

        return (
            self.claims_agi
            or self.claims_production_ready
            or self.claims_certified
            or self.allows_autonomous_authority
        )

    @property
    def accepted(self) -> bool:
        """Return whether this statement is accepted for bounded publication."""

        return self.finding is WaveSixPublicClaimFinding.ACCEPTED

    @property
    def needs_more_evidence(self) -> bool:
        """Return whether this statement still needs evidence or boundary text."""

        return self.finding is WaveSixPublicClaimFinding.NEEDS_MORE_EVIDENCE or bool(
            self.missing_required_fragments
        )

    @property
    def blocks_bounded_publication(self) -> bool:
        """Return whether this statement blocks bounded public release."""

        return (
            self.blocks_publication
            or self.finding is WaveSixPublicClaimFinding.BLOCKS_PUBLICATION
            or self.overclaim_present
            or bool(self.prohibited_matches)
        )

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic statement payload for hashing and review."""

        return {
            "allows_autonomous_authority": self.allows_autonomous_authority,
            "blocks_publication": self.blocks_publication,
            "claims_agi": self.claims_agi,
            "claims_certified": self.claims_certified,
            "claims_production_ready": self.claims_production_ready,
            "evidence_ids": list(self.evidence_ids),
            "finding": self.finding.value,
            "intended_audience": self.intended_audience,
            "missing_required_fragments": list(self.missing_required_fragments),
            "prohibited_matches": list(self.prohibited_matches),
            "requires_follow_up": self.requires_follow_up,
            "required_fragments": list(self.required_fragments),
            "prohibited_fragments": list(self.prohibited_fragments),
            "reviewer_questions": list(self.reviewer_questions),
            "schema_version": self.schema_version,
            "statement_id": self.statement_id,
            "surface": self.surface.value,
            "text": self.text,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this statement."""

        return _stable_sha256(self.canonical_payload())


@dataclass(frozen=True, slots=True)
class WaveSixPublicClaimReport:
    """Report that gates public Wave 6 wording before bounded publication."""

    report_id: str
    statements: tuple[WaveSixPublicClaimStatement, ...]
    decision: WaveSixPublicClaimDecision
    generated_by_engine_id: str
    human_authority_id: str
    independent_reviewer_id: str
    required_surfaces: tuple[WaveSixPublicClaimSurface, ...] = (
        WAVE_SIX_REQUIRED_PUBLIC_CLAIM_SURFACES
    )
    notes: tuple[str, ...] = ()
    schema_version: str = WAVE_SIX_PUBLIC_CLAIM_REPORT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate report coverage, uniqueness, and decision semantics."""

        object.__setattr__(
            self,
            "report_id",
            _require_non_empty(self.report_id, "report_id"),
        )
        if not self.statements:
            raise ValueError("Public claim reports require statements.")
        sorted_statements = tuple(
            sorted(self.statements, key=lambda statement: statement.statement_id)
        )
        _require_unique_text(
            (statement.statement_id for statement in sorted_statements),
            label="statement_id",
        )
        _require_unique_enum(
            (statement.surface for statement in sorted_statements),
            label="surface",
        )
        object.__setattr__(self, "statements", sorted_statements)
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
            "required_surfaces",
            _normalize_unique_enum_tuple(
                self.required_surfaces,
                label="required surface",
            ),
        )
        object.__setattr__(
            self,
            "notes",
            _normalize_unique_text_tuple(self.notes, label="report note"),
        )
        object.__setattr__(
            self,
            "schema_version",
            _require_non_empty(self.schema_version, "schema_version"),
        )
        if self.decision is WaveSixPublicClaimDecision.APPROVE_BOUNDED_PUBLICATION:
            if self.missing_surfaces:
                raise ValueError("Approved public-claim reports require every surface.")
            if self.follow_up_statement_ids:
                raise ValueError("Approved public-claim reports cannot need follow-up.")
            if self.blocking_statement_ids:
                raise ValueError(
                    "Approved public-claim reports cannot include blockers."
                )
        if (
            self.decision is WaveSixPublicClaimDecision.BLOCK_PUBLICATION
            and not self.blocking_statement_ids
        ):
            raise ValueError("Blocked public-claim reports require a blocker.")

    @property
    def statement_ids(self) -> tuple[str, ...]:
        """Return statement ids in deterministic order."""

        return tuple(statement.statement_id for statement in self.statements)

    @property
    def present_surfaces(self) -> tuple[WaveSixPublicClaimSurface, ...]:
        """Return required public surfaces represented by statements."""

        present = {statement.surface for statement in self.statements}
        return tuple(
            surface for surface in self.required_surfaces if surface in present
        )

    @property
    def missing_surfaces(self) -> tuple[WaveSixPublicClaimSurface, ...]:
        """Return required public surfaces missing from the report."""

        present = {statement.surface for statement in self.statements}
        return tuple(
            surface for surface in self.required_surfaces if surface not in present
        )

    @property
    def accepted_statement_ids(self) -> tuple[str, ...]:
        """Return statements accepted for bounded publication."""

        return tuple(
            statement.statement_id
            for statement in self.statements
            if statement.accepted
        )

    @property
    def follow_up_statement_ids(self) -> tuple[str, ...]:
        """Return statements that need evidence or boundary text."""

        return tuple(
            statement.statement_id
            for statement in self.statements
            if statement.needs_more_evidence
        )

    @property
    def blocking_statement_ids(self) -> tuple[str, ...]:
        """Return statements that block bounded publication."""

        return tuple(
            statement.statement_id
            for statement in self.statements
            if statement.blocks_bounded_publication
        )

    @property
    def status(self) -> WaveSixPublicClaimStatus:
        """Return fail-closed public-claim status."""

        if self.blocking_statement_ids:
            return WaveSixPublicClaimStatus.BLOCKED
        if self.missing_surfaces or self.follow_up_statement_ids:
            return WaveSixPublicClaimStatus.NEEDS_MORE_EVIDENCE
        return WaveSixPublicClaimStatus.READY_FOR_BOUNDED_PUBLICATION

    @property
    def ready_for_bounded_publication(self) -> bool:
        """Return whether public wording can be published for bounded review."""

        return self.status is WaveSixPublicClaimStatus.READY_FOR_BOUNDED_PUBLICATION

    def statement_for_surface(
        self,
        surface: WaveSixPublicClaimSurface,
    ) -> WaveSixPublicClaimStatement | None:
        """Return the statement for a public surface, if present."""

        for statement in self.statements:
            if statement.surface is surface:
                return statement
        return None

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic report payload for hashing and review."""

        return {
            "accepted_statement_ids": list(self.accepted_statement_ids),
            "blocking_statement_ids": list(self.blocking_statement_ids),
            "decision": self.decision.value,
            "follow_up_statement_ids": list(self.follow_up_statement_ids),
            "generated_by_engine_id": self.generated_by_engine_id,
            "human_authority_id": self.human_authority_id,
            "independent_reviewer_id": self.independent_reviewer_id,
            "missing_surfaces": [surface.value for surface in self.missing_surfaces],
            "notes": list(self.notes),
            "present_surfaces": [surface.value for surface in self.present_surfaces],
            "report_id": self.report_id,
            "required_surfaces": [surface.value for surface in self.required_surfaces],
            "schema_version": self.schema_version,
            "statements": [
                statement.canonical_payload() for statement in self.statements
            ],
            "status": self.status.value,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this report."""

        return _stable_sha256(self.canonical_payload())


def build_wave_six_public_claim_report(
    *,
    report_id: str,
    statements: Iterable[WaveSixPublicClaimStatement],
    decision: WaveSixPublicClaimDecision,
    generated_by_engine_id: str,
    human_authority_id: str,
    independent_reviewer_id: str,
    notes: Iterable[str] = (),
) -> WaveSixPublicClaimReport:
    """Build a deterministic Wave 6 public-claim report."""

    return WaveSixPublicClaimReport(
        report_id=report_id,
        statements=tuple(statements),
        decision=decision,
        generated_by_engine_id=generated_by_engine_id,
        human_authority_id=human_authority_id,
        independent_reviewer_id=independent_reviewer_id,
        notes=tuple(notes),
    )


def required_wave_six_public_claim_surfaces() -> tuple[WaveSixPublicClaimSurface, ...]:
    """Return required public surfaces before bounded publication."""

    return WAVE_SIX_REQUIRED_PUBLIC_CLAIM_SURFACES


def prohibited_wave_six_public_claim_fragments() -> tuple[str, ...]:
    """Return phrases that block bounded Wave 6 public wording."""

    return WAVE_SIX_PROHIBITED_PUBLIC_CLAIM_FRAGMENTS


def required_wave_six_public_claim_fragments() -> tuple[str, ...]:
    """Return fragments required in bounded Wave 6 public wording."""

    return WAVE_SIX_REQUIRED_PUBLIC_CLAIM_FRAGMENTS


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


def _normalize_unique_lower_tuple(
    values: Iterable[str], *, label: str
) -> tuple[str, ...]:
    """Normalize text fragments to lowercase while rejecting duplicates."""

    normalized: list[str] = []
    seen: set[str] = set()
    for value in values:
        stripped = _require_non_empty(value, label).casefold()
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
