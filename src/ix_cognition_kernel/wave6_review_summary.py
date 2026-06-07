"""Wave 6 bounded review summary artifact.

The actual README remains last. This module creates a deterministic summary
artifact that can feed the release manifest's README-summary slot without
turning documentation into an overclaim. It summarizes what Wave 6 is, what was
tested, what blocks interpretation, and what remains under human and independent
review.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, TypeVar

E = TypeVar("E", bound=StrEnum)

WAVE_SIX_REVIEW_SUMMARY_SECTION_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave6-review-summary-section-v1"
)
WAVE_SIX_REVIEW_SUMMARY_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave6-review-summary-v1"
)


class WaveSixReviewSummarySectionKind(StrEnum):
    """Sections required in a bounded Wave 6 review summary."""

    CLAIM_BOUNDARY = "claim-boundary"
    WHAT_WAS_ASSEMBLED = "what-was-assembled"
    WHAT_WAS_TESTED = "what-was-tested"
    WHAT_CAN_BLOCK = "what-can-block"
    HUMAN_AUTHORITY = "human-authority"
    INDEPENDENT_REVIEW = "independent-review"
    NON_CLAIMS = "non-claims"
    NEXT_REVIEW_ACTIONS = "next-review-actions"


class WaveSixReviewSummaryFinding(StrEnum):
    """Finding for one review-summary section."""

    INCLUDED = "included"
    NEEDS_MORE_EVIDENCE = "needs-more-evidence"
    BLOCKS_SUMMARY = "blocks-summary"


class WaveSixReviewSummaryDecision(StrEnum):
    """Final decision for the bounded review summary artifact."""

    READY_FOR_RELEASE_SUMMARY = "ready-for-release-summary"
    HOLD_FOR_MORE_EVIDENCE = "hold-for-more-evidence"
    BLOCK_SUMMARY = "block-summary"


class WaveSixReviewSummaryStatus(StrEnum):
    """Fail-closed status for the bounded review summary."""

    READY_FOR_BOUNDED_RELEASE = "ready-for-bounded-release"
    NEEDS_MORE_EVIDENCE = "needs-more-evidence"
    BLOCKED = "blocked"


WAVE_SIX_REQUIRED_REVIEW_SUMMARY_SECTIONS: tuple[
    WaveSixReviewSummarySectionKind, ...
] = (
    WaveSixReviewSummarySectionKind.CLAIM_BOUNDARY,
    WaveSixReviewSummarySectionKind.WHAT_WAS_ASSEMBLED,
    WaveSixReviewSummarySectionKind.WHAT_WAS_TESTED,
    WaveSixReviewSummarySectionKind.WHAT_CAN_BLOCK,
    WaveSixReviewSummarySectionKind.HUMAN_AUTHORITY,
    WaveSixReviewSummarySectionKind.INDEPENDENT_REVIEW,
    WaveSixReviewSummarySectionKind.NON_CLAIMS,
    WaveSixReviewSummarySectionKind.NEXT_REVIEW_ACTIONS,
)


@dataclass(frozen=True, slots=True)
class WaveSixReviewSummarySection:
    """One bounded section in a Wave 6 review summary artifact."""

    section_id: str
    kind: WaveSixReviewSummarySectionKind
    title: str
    body: str
    evidence_ids: tuple[str, ...]
    reviewer_questions: tuple[str, ...]
    finding: WaveSixReviewSummaryFinding = WaveSixReviewSummaryFinding.INCLUDED
    requires_follow_up: bool = False
    blocks_summary: bool = False
    schema_version: str = WAVE_SIX_REVIEW_SUMMARY_SECTION_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate section identity, evidence binding, and finding semantics."""

        object.__setattr__(
            self,
            "section_id",
            _require_non_empty(self.section_id, "section_id"),
        )
        object.__setattr__(self, "title", _require_non_empty(self.title, "title"))
        object.__setattr__(self, "body", _require_non_empty(self.body, "body"))
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
            raise ValueError("Review summary sections require evidence ids.")
        if not self.reviewer_questions:
            raise ValueError("Review summary sections require reviewer questions.")
        if self.finding is WaveSixReviewSummaryFinding.INCLUDED:
            if self.requires_follow_up:
                raise ValueError("Included summary sections cannot require follow-up.")
            if self.blocks_summary:
                raise ValueError("Included summary sections cannot block summary.")
        if (
            self.finding is WaveSixReviewSummaryFinding.NEEDS_MORE_EVIDENCE
            and not self.requires_follow_up
        ):
            raise ValueError("Needs-more-evidence sections require follow-up.")
        if (
            self.finding is WaveSixReviewSummaryFinding.BLOCKS_SUMMARY
            and not self.blocks_summary
        ):
            raise ValueError("Blocking summary sections must block summary.")

    @property
    def included(self) -> bool:
        """Return whether this section is included for bounded release."""

        return self.finding is WaveSixReviewSummaryFinding.INCLUDED

    @property
    def needs_more_evidence(self) -> bool:
        """Return whether this section still needs evidence."""

        return self.finding is WaveSixReviewSummaryFinding.NEEDS_MORE_EVIDENCE

    @property
    def blocks_bounded_summary(self) -> bool:
        """Return whether this section blocks the summary artifact."""

        return (
            self.blocks_summary
            or self.finding is WaveSixReviewSummaryFinding.BLOCKS_SUMMARY
        )

    def markdown_block(self) -> str:
        """Return deterministic markdown for this section."""

        return f"## {self.title}\n\n{self.body}"

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic section payload for hashing and review."""

        return {
            "blocks_summary": self.blocks_summary,
            "body": self.body,
            "evidence_ids": list(self.evidence_ids),
            "finding": self.finding.value,
            "kind": self.kind.value,
            "requires_follow_up": self.requires_follow_up,
            "reviewer_questions": list(self.reviewer_questions),
            "schema_version": self.schema_version,
            "section_id": self.section_id,
            "title": self.title,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this section."""

        return _stable_sha256(self.canonical_payload())


@dataclass(frozen=True, slots=True)
class WaveSixReviewSummaryArtifact:
    """Bounded review summary artifact for Wave 6 release handoff."""

    summary_id: str
    title: str
    source_release_manifest_fingerprint: str
    sections: tuple[WaveSixReviewSummarySection, ...]
    decision: WaveSixReviewSummaryDecision
    claim_boundary_statement: str
    generated_by_engine_id: str
    human_authority_id: str
    independent_reviewer_id: str
    required_sections: tuple[WaveSixReviewSummarySectionKind, ...] = (
        WAVE_SIX_REQUIRED_REVIEW_SUMMARY_SECTIONS
    )
    claims_agi: bool = False
    claims_production_ready: bool = False
    claims_certified: bool = False
    allows_autonomous_authority: bool = False
    notes: tuple[str, ...] = ()
    schema_version: str = WAVE_SIX_REVIEW_SUMMARY_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate summary inventory, authority, and no-overclaim boundary."""

        object.__setattr__(
            self,
            "summary_id",
            _require_non_empty(self.summary_id, "summary_id"),
        )
        object.__setattr__(self, "title", _require_non_empty(self.title, "title"))
        object.__setattr__(
            self,
            "source_release_manifest_fingerprint",
            _require_non_empty(
                self.source_release_manifest_fingerprint,
                "source_release_manifest_fingerprint",
            ),
        )
        if not self.sections:
            raise ValueError("Wave 6 review summaries require sections.")
        sorted_sections = tuple(
            sorted(self.sections, key=lambda section: section.section_id)
        )
        _require_unique_text(
            (section.section_id for section in sorted_sections),
            label="section_id",
        )
        _require_unique_enum(
            (section.kind for section in sorted_sections),
            label="section kind",
        )
        object.__setattr__(self, "sections", sorted_sections)
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
            "required_sections",
            _normalize_unique_enum_tuple(
                self.required_sections,
                label="required section",
            ),
        )
        object.__setattr__(
            self,
            "notes",
            _normalize_unique_text_tuple(self.notes, label="summary note"),
        )
        object.__setattr__(
            self,
            "schema_version",
            _require_non_empty(self.schema_version, "schema_version"),
        )
        if self.decision is WaveSixReviewSummaryDecision.READY_FOR_RELEASE_SUMMARY:
            if self.missing_section_kinds:
                raise ValueError("Ready review summaries require every section.")
            if self.follow_up_section_ids:
                raise ValueError("Ready review summaries cannot require follow-up.")
            if self.blocking_section_ids:
                raise ValueError("Ready review summaries cannot include blockers.")
            if self.overclaim_present:
                raise ValueError("Ready review summaries cannot contain overclaims.")
            if not self.claim_boundary_statement_valid:
                raise ValueError("Ready review summaries need valid claim boundary.")
        if self.decision is WaveSixReviewSummaryDecision.BLOCK_SUMMARY:
            if not self.blocking_section_ids and not self.overclaim_present:
                raise ValueError("Blocked summaries require blocker or overclaim.")

    @property
    def section_ids(self) -> tuple[str, ...]:
        """Return section ids in deterministic order."""

        return tuple(section.section_id for section in self.sections)

    @property
    def present_section_kinds(self) -> tuple[WaveSixReviewSummarySectionKind, ...]:
        """Return required section kinds represented by the artifact."""

        present = {section.kind for section in self.sections}
        return tuple(kind for kind in self.required_sections if kind in present)

    @property
    def missing_section_kinds(self) -> tuple[WaveSixReviewSummarySectionKind, ...]:
        """Return required section kinds missing from the artifact."""

        present = {section.kind for section in self.sections}
        return tuple(kind for kind in self.required_sections if kind not in present)

    @property
    def included_section_ids(self) -> tuple[str, ...]:
        """Return included section ids."""

        return tuple(section.section_id for section in self.sections if section.included)

    @property
    def follow_up_section_ids(self) -> tuple[str, ...]:
        """Return section ids requiring follow-up evidence."""

        return tuple(
            section.section_id for section in self.sections if section.needs_more_evidence
        )

    @property
    def blocking_section_ids(self) -> tuple[str, ...]:
        """Return section ids that block summary release."""

        return tuple(
            section.section_id
            for section in self.sections
            if section.blocks_bounded_summary
        )

    @property
    def overclaim_present(self) -> bool:
        """Return whether this summary violates the claim boundary."""

        return (
            self.claims_agi
            or self.claims_production_ready
            or self.claims_certified
            or self.allows_autonomous_authority
        )

    @property
    def claim_boundary_statement_valid(self) -> bool:
        """Return whether the summary statement preserves bounded review only."""

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
    def status(self) -> WaveSixReviewSummaryStatus:
        """Return fail-closed review summary status."""

        if self.overclaim_present or self.blocking_section_ids:
            return WaveSixReviewSummaryStatus.BLOCKED
        if (
            self.missing_section_kinds
            or self.follow_up_section_ids
            or not self.claim_boundary_statement_valid
        ):
            return WaveSixReviewSummaryStatus.NEEDS_MORE_EVIDENCE
        return WaveSixReviewSummaryStatus.READY_FOR_BOUNDED_RELEASE

    @property
    def ready_for_bounded_release(self) -> bool:
        """Return whether the summary can be included in bounded release."""

        return self.status is WaveSixReviewSummaryStatus.READY_FOR_BOUNDED_RELEASE

    def section_for_kind(
        self,
        kind: WaveSixReviewSummarySectionKind,
    ) -> WaveSixReviewSummarySection | None:
        """Return the summary section for a kind, if present."""

        for section in self.sections:
            if section.kind is kind:
                return section
        return None

    def render_markdown(self) -> str:
        """Return deterministic markdown for release-summary review."""

        section_blocks = "\n\n".join(section.markdown_block() for section in self.sections)
        return (
            f"# {self.title}\n\n"
            f"{self.claim_boundary_statement}\n\n"
            f"{section_blocks}"
        )

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic summary payload for hashing and review."""

        return {
            "allows_autonomous_authority": self.allows_autonomous_authority,
            "blocking_section_ids": list(self.blocking_section_ids),
            "claim_boundary_statement": self.claim_boundary_statement,
            "claim_boundary_statement_valid": self.claim_boundary_statement_valid,
            "claims_agi": self.claims_agi,
            "claims_certified": self.claims_certified,
            "claims_production_ready": self.claims_production_ready,
            "decision": self.decision.value,
            "follow_up_section_ids": list(self.follow_up_section_ids),
            "generated_by_engine_id": self.generated_by_engine_id,
            "human_authority_id": self.human_authority_id,
            "included_section_ids": list(self.included_section_ids),
            "independent_reviewer_id": self.independent_reviewer_id,
            "markdown": self.render_markdown(),
            "missing_section_kinds": [
                kind.value for kind in self.missing_section_kinds
            ],
            "notes": list(self.notes),
            "present_section_kinds": [
                kind.value for kind in self.present_section_kinds
            ],
            "required_sections": [kind.value for kind in self.required_sections],
            "schema_version": self.schema_version,
            "sections": [section.canonical_payload() for section in self.sections],
            "source_release_manifest_fingerprint": (
                self.source_release_manifest_fingerprint
            ),
            "status": self.status.value,
            "summary_id": self.summary_id,
            "title": self.title,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this summary."""

        return _stable_sha256(self.canonical_payload())


def build_wave_six_review_summary_artifact(
    *,
    summary_id: str,
    title: str,
    source_release_manifest_fingerprint: str,
    sections: Iterable[WaveSixReviewSummarySection],
    decision: WaveSixReviewSummaryDecision,
    claim_boundary_statement: str,
    generated_by_engine_id: str,
    human_authority_id: str,
    independent_reviewer_id: str,
    notes: Iterable[str] = (),
) -> WaveSixReviewSummaryArtifact:
    """Build a deterministic bounded Wave 6 review summary artifact."""

    return WaveSixReviewSummaryArtifact(
        summary_id=summary_id,
        title=title,
        source_release_manifest_fingerprint=source_release_manifest_fingerprint,
        sections=tuple(sections),
        decision=decision,
        claim_boundary_statement=claim_boundary_statement,
        generated_by_engine_id=generated_by_engine_id,
        human_authority_id=human_authority_id,
        independent_reviewer_id=independent_reviewer_id,
        notes=tuple(notes),
    )


def required_wave_six_review_summary_sections() -> tuple[
    WaveSixReviewSummarySectionKind, ...
]:
    """Return required sections for a bounded Wave 6 review summary."""

    return WAVE_SIX_REQUIRED_REVIEW_SUMMARY_SECTIONS


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
