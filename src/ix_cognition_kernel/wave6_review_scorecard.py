"""Wave 6 review scorecard.

This module converts the Wave 6 evidence package into a compact, deterministic
scorecard for reviewers. It does not replace the underlying ledgers. It records
whether each required proof surface is satisfied, still needs evidence, or blocks
interpretation while preserving the no-AGI claim boundary.
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

WAVE_SIX_REVIEW_SCORECARD_ITEM_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave6-review-scorecard-item-v1"
)
WAVE_SIX_REVIEW_SCORECARD_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave6-review-scorecard-v1"
)


class WaveSixReviewCriterion(StrEnum):
    """Required criteria for bounded Wave 6 external review readiness."""

    CLEAN_MASTER_LOOP = "clean-master-loop"
    CONTRACT_COVERAGE = "contract-coverage"
    DONOR_TRACEABILITY = "donor-traceability"
    REALITY_CORRECTED_REASONING = "reality-corrected-reasoning"
    FUTURE_REASONING_CHANGE = "future-reasoning-change"
    CROSS_DOMAIN_TRANSFER = "cross-domain-transfer"
    NOVELTY_AND_NEGATIVE_CONTROL = "novelty-and-negative-control"
    FALSIFICATION_SURVIVAL = "falsification-survival"
    HUMAN_REVIEW_AUTHORITY = "human-review-authority"
    INDEPENDENT_REVIEW_READINESS = "independent-review-readiness"
    CLAIM_BOUNDARY_DISCIPLINE = "claim-boundary-discipline"


class WaveSixCriterionStatus(StrEnum):
    """Fail-closed status for one scorecard criterion."""

    SATISFIED = "satisfied"
    NEEDS_MORE_EVIDENCE = "needs-more-evidence"
    BLOCKED = "blocked"


class WaveSixReviewScorecardStatus(StrEnum):
    """Overall scorecard status."""

    READY_FOR_EXTERNAL_REVIEW = "ready-for-external-review"
    NEEDS_MORE_EVIDENCE = "needs-more-evidence"
    BLOCKED = "blocked"


WAVE_SIX_REQUIRED_REVIEW_CRITERIA: tuple[WaveSixReviewCriterion, ...] = (
    WaveSixReviewCriterion.CLEAN_MASTER_LOOP,
    WaveSixReviewCriterion.CONTRACT_COVERAGE,
    WaveSixReviewCriterion.DONOR_TRACEABILITY,
    WaveSixReviewCriterion.REALITY_CORRECTED_REASONING,
    WaveSixReviewCriterion.FUTURE_REASONING_CHANGE,
    WaveSixReviewCriterion.CROSS_DOMAIN_TRANSFER,
    WaveSixReviewCriterion.NOVELTY_AND_NEGATIVE_CONTROL,
    WaveSixReviewCriterion.FALSIFICATION_SURVIVAL,
    WaveSixReviewCriterion.HUMAN_REVIEW_AUTHORITY,
    WaveSixReviewCriterion.INDEPENDENT_REVIEW_READINESS,
    WaveSixReviewCriterion.CLAIM_BOUNDARY_DISCIPLINE,
)


@dataclass(frozen=True, slots=True)
class WaveSixReviewScorecardItem:
    """One scored Wave 6 review criterion."""

    item_id: str
    criterion: WaveSixReviewCriterion
    status: WaveSixCriterionStatus
    summary: str
    artifact_fingerprint: str
    evidence_ids: tuple[str, ...]
    reviewer_question: str
    requires_follow_up: bool = False
    blocks_claim: bool = False
    schema_version: str = WAVE_SIX_REVIEW_SCORECARD_ITEM_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate item identity, evidence binding, and status semantics."""

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
            "reviewer_question",
            _require_non_empty(self.reviewer_question, "reviewer_question"),
        )
        object.__setattr__(
            self,
            "schema_version",
            _require_non_empty(self.schema_version, "schema_version"),
        )
        if not self.evidence_ids:
            raise ValueError("Review scorecard items require evidence ids.")
        if self.status is WaveSixCriterionStatus.SATISFIED:
            if self.requires_follow_up:
                raise ValueError("Satisfied scorecard items cannot require follow-up.")
            if self.blocks_claim:
                raise ValueError("Satisfied scorecard items cannot block the claim.")
        if (
            self.status is WaveSixCriterionStatus.NEEDS_MORE_EVIDENCE
            and not self.requires_follow_up
        ):
            raise ValueError("Needs-more-evidence scorecard items require follow-up.")
        if self.status is WaveSixCriterionStatus.BLOCKED and not self.blocks_claim:
            raise ValueError("Blocked scorecard items must block the claim.")

    @property
    def satisfied(self) -> bool:
        """Return whether this criterion is satisfied."""

        return self.status is WaveSixCriterionStatus.SATISFIED

    @property
    def needs_more_evidence(self) -> bool:
        """Return whether this criterion needs more evidence."""

        return self.status is WaveSixCriterionStatus.NEEDS_MORE_EVIDENCE

    @property
    def blocked(self) -> bool:
        """Return whether this criterion blocks interpretation."""

        return self.status is WaveSixCriterionStatus.BLOCKED or self.blocks_claim

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic payload for hashing and review."""

        return {
            "artifact_fingerprint": self.artifact_fingerprint,
            "blocks_claim": self.blocks_claim,
            "criterion": self.criterion.value,
            "evidence_ids": list(self.evidence_ids),
            "item_id": self.item_id,
            "requires_follow_up": self.requires_follow_up,
            "reviewer_question": self.reviewer_question,
            "schema_version": self.schema_version,
            "status": self.status.value,
            "summary": self.summary,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this scorecard item."""

        return _stable_sha256(self.canonical_payload())


@dataclass(frozen=True, slots=True)
class WaveSixReviewScorecard:
    """Compact review scorecard for Wave 6 evidence-package readiness."""

    scorecard_id: str
    package_fingerprint: str
    items: tuple[WaveSixReviewScorecardItem, ...]
    generated_by_engine_id: str
    claim_boundary_statement: str
    required_criteria: tuple[WaveSixReviewCriterion, ...] = (
        WAVE_SIX_REQUIRED_REVIEW_CRITERIA
    )
    claims_agi: bool = False
    claims_production_ready: bool = False
    claims_certified: bool = False
    allows_autonomous_authority: bool = False
    notes: tuple[str, ...] = ()
    schema_version: str = WAVE_SIX_REVIEW_SCORECARD_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate scorecard identity, coverage, and overclaim boundary."""

        object.__setattr__(
            self,
            "scorecard_id",
            _require_non_empty(self.scorecard_id, "scorecard_id"),
        )
        object.__setattr__(
            self,
            "package_fingerprint",
            _require_non_empty(self.package_fingerprint, "package_fingerprint"),
        )
        if not self.items:
            raise ValueError("Wave 6 review scorecards require at least one item.")
        sorted_items = tuple(sorted(self.items, key=lambda item: item.item_id))
        _unique_ids((item.item_id for item in sorted_items), label="item_id")
        _unique_ids((item.criterion for item in sorted_items), label="criterion")
        object.__setattr__(self, "items", sorted_items)
        object.__setattr__(
            self,
            "generated_by_engine_id",
            _require_non_empty(self.generated_by_engine_id, "generated_by_engine_id"),
        )
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
            "required_criteria",
            _normalize_unique_enum_tuple(
                self.required_criteria,
                label="required criterion",
            ),
        )
        object.__setattr__(
            self,
            "notes",
            _normalize_unique_text_tuple(self.notes, label="scorecard note"),
        )
        object.__setattr__(
            self,
            "schema_version",
            _require_non_empty(self.schema_version, "schema_version"),
        )

    @property
    def item_ids(self) -> tuple[str, ...]:
        """Return scorecard item ids in deterministic order."""

        return tuple(item.item_id for item in self.items)

    @property
    def present_criteria(self) -> tuple[WaveSixReviewCriterion, ...]:
        """Return required criteria represented by scorecard items."""

        present = {item.criterion for item in self.items}
        return tuple(
            criterion
            for criterion in self.required_criteria
            if criterion in present
        )

    @property
    def missing_criteria(self) -> tuple[WaveSixReviewCriterion, ...]:
        """Return required criteria missing from the scorecard."""

        present = {item.criterion for item in self.items}
        return tuple(
            criterion
            for criterion in self.required_criteria
            if criterion not in present
        )

    @property
    def satisfied_criteria(self) -> tuple[WaveSixReviewCriterion, ...]:
        """Return criteria satisfied by the scorecard."""

        return tuple(item.criterion for item in self.items if item.satisfied)

    @property
    def follow_up_item_ids(self) -> tuple[str, ...]:
        """Return item ids requiring follow-up evidence."""

        return tuple(item.item_id for item in self.items if item.needs_more_evidence)

    @property
    def blocking_item_ids(self) -> tuple[str, ...]:
        """Return item ids blocking Wave 6 interpretation."""

        return tuple(item.item_id for item in self.items if item.blocked)

    @property
    def overclaim_present(self) -> bool:
        """Return whether this scorecard violates the claim boundary."""

        return (
            self.claims_agi
            or self.claims_production_ready
            or self.claims_certified
            or self.allows_autonomous_authority
        )

    @property
    def status(self) -> WaveSixReviewScorecardStatus:
        """Return fail-closed scorecard status."""

        if self.overclaim_present or self.blocking_item_ids:
            return WaveSixReviewScorecardStatus.BLOCKED
        if self.missing_criteria or self.follow_up_item_ids:
            return WaveSixReviewScorecardStatus.NEEDS_MORE_EVIDENCE
        return WaveSixReviewScorecardStatus.READY_FOR_EXTERNAL_REVIEW

    @property
    def ready_for_external_review(self) -> bool:
        """Return whether the scorecard is ready for external review."""

        return self.status is WaveSixReviewScorecardStatus.READY_FOR_EXTERNAL_REVIEW

    def item_for_criterion(
        self,
        criterion: WaveSixReviewCriterion,
    ) -> WaveSixReviewScorecardItem | None:
        """Return the item for a criterion, if present."""

        for item in self.items:
            if item.criterion is criterion:
                return item
        return None

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic scorecard payload for hashing and review."""

        return {
            "allows_autonomous_authority": self.allows_autonomous_authority,
            "blocking_item_ids": list(self.blocking_item_ids),
            "claim_boundary_statement": self.claim_boundary_statement,
            "claims_agi": self.claims_agi,
            "claims_certified": self.claims_certified,
            "claims_production_ready": self.claims_production_ready,
            "follow_up_item_ids": list(self.follow_up_item_ids),
            "generated_by_engine_id": self.generated_by_engine_id,
            "items": [item.canonical_payload() for item in self.items],
            "missing_criteria": [
                criterion.value for criterion in self.missing_criteria
            ],
            "notes": list(self.notes),
            "package_fingerprint": self.package_fingerprint,
            "present_criteria": [
                criterion.value for criterion in self.present_criteria
            ],
            "required_criteria": [
                criterion.value for criterion in self.required_criteria
            ],
            "satisfied_criteria": [
                criterion.value for criterion in self.satisfied_criteria
            ],
            "schema_version": self.schema_version,
            "scorecard_id": self.scorecard_id,
            "status": self.status.value,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this scorecard."""

        return _stable_sha256(self.canonical_payload())


def build_wave_six_review_scorecard(
    *,
    scorecard_id: str,
    package_fingerprint: str,
    items: Iterable[WaveSixReviewScorecardItem],
    generated_by_engine_id: str,
    claim_boundary_statement: str,
    notes: Iterable[str] = (),
) -> WaveSixReviewScorecard:
    """Build a deterministic Wave 6 review scorecard."""

    return WaveSixReviewScorecard(
        scorecard_id=scorecard_id,
        package_fingerprint=package_fingerprint,
        items=tuple(items),
        generated_by_engine_id=generated_by_engine_id,
        claim_boundary_statement=claim_boundary_statement,
        notes=tuple(notes),
    )


def required_wave_six_review_criteria() -> tuple[WaveSixReviewCriterion, ...]:
    """Return criteria required for the Wave 6 review scorecard."""

    return WAVE_SIX_REQUIRED_REVIEW_CRITERIA


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
