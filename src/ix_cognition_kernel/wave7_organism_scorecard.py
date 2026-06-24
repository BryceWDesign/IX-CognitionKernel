"""Wave 7 organism scorecard.

The organism scorecard summarizes whether the Wave 7 cognitive organism
substrate is evidence-bound, reviewable, bounded by authority, corrected by
measured outcomes, resistant to manipulation pressure, and unable to turn
capability into permission.

The scorecard does not declare AGI. It records whether the system has enough
replayable evidence to be treated as a credible Wave 7 organism-substrate
candidate under human review.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

WAVE_SEVEN_SCORECARD_DIMENSION_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave7-scorecard-dimension-v1"
)
WAVE_SEVEN_ORGANISM_SCORECARD_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave7-organism-scorecard-v1"
)
WAVE_SEVEN_ORGANISM_EVALUATION_SUMMARY_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave7-organism-evaluation-summary-v1"
)


class OrganismDimensionId(StrEnum):
    """Required Wave 7 organism-substrate dimensions."""

    IDENTITY_CONTINUITY = "identity-continuity"
    CONTINUITY_LEDGER = "continuity-ledger"
    BODY_CONTRACT = "body-contract"
    CAPABILITY_SURFACE = "capability-surface"
    OBSERVATION_ACTION_TRACE = "observation-action-trace"
    EXPERIENCE_COMPILATION = "experience-compilation"
    PREDICTION_OUTCOME_LIFECYCLE = "prediction-outcome-lifecycle"
    SKILL_GENOME = "skill-genome"
    GOAL_PRESSURE = "goal-pressure"
    RUNTIME_AIRLOCK = "runtime-airlock"
    MANIPULATION_PRESSURE = "manipulation-pressure"
    SELF_REVISION = "self-revision"


class ScorecardDimensionStatus(StrEnum):
    """Reviewable status for one organism scorecard dimension."""

    NOT_EVALUATED = "not-evaluated"
    NEEDS_MORE_EVIDENCE = "needs-more-evidence"
    READY_FOR_REVIEW = "ready-for-review"
    PASSED_REVIEW = "passed-review"
    BLOCKED = "blocked"


class OrganismScorecardDecision(StrEnum):
    """Fail-closed Wave 7 organism scorecard decision."""

    RECORD_ONLY = "record-only"
    READY_FOR_REVIEW = "ready-for-review"
    NEEDS_MORE_EVIDENCE = "needs-more-evidence"
    BLOCKED = "blocked"


@dataclass(frozen=True, slots=True)
class ScorecardDimension:
    """One evidence-bound dimension in the Wave 7 organism scorecard."""

    dimension_id: OrganismDimensionId
    status: ScorecardDimensionStatus
    summary: str
    evidence_ids: tuple[str, ...]
    authority_refs: tuple[str, ...]
    blocker_ids: tuple[str, ...] = ()
    review_notes: tuple[str, ...] = ()
    score: float = 0.0
    schema_version: str = WAVE_SEVEN_SCORECARD_DIMENSION_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate scorecard dimension evidence, authority, and score."""

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
            "authority_refs",
            _normalize_unique_text_tuple(self.authority_refs, label="authority_ref"),
        )
        object.__setattr__(
            self,
            "blocker_ids",
            _normalize_unique_text_tuple(self.blocker_ids, label="blocker_id"),
        )
        object.__setattr__(
            self,
            "review_notes",
            _normalize_unique_text_tuple(self.review_notes, label="review_note"),
        )
        object.__setattr__(
            self,
            "schema_version",
            _require_non_empty(self.schema_version, "schema_version"),
        )
        if not 0.0 <= self.score <= 1.0:
            raise ValueError("Scorecard dimension score must be between 0.0 and 1.0.")
        if self.status is not ScorecardDimensionStatus.NOT_EVALUATED:
            if not self.evidence_ids:
                raise ValueError("Evaluated scorecard dimensions require evidence.")
            if not self.authority_refs:
                raise ValueError("Evaluated scorecard dimensions require authority.")
        if self.status is ScorecardDimensionStatus.BLOCKED and not self.blocker_ids:
            raise ValueError("Blocked scorecard dimensions require blocker ids.")
        if self.status is not ScorecardDimensionStatus.BLOCKED and self.blocker_ids:
            raise ValueError("Only blocked scorecard dimensions may list blockers.")
        if self.status is ScorecardDimensionStatus.NOT_EVALUATED and self.score > 0.0:
            raise ValueError("Unevaluated scorecard dimensions must have zero score.")
        if (
            self.status is ScorecardDimensionStatus.NEEDS_MORE_EVIDENCE
            and self.score >= 1.0
        ):
            raise ValueError("Evidence-deficient dimensions cannot have full score.")

    @property
    def ready_or_passed(self) -> bool:
        """Return whether dimension is ready for review or passed review."""

        return self.status in {
            ScorecardDimensionStatus.READY_FOR_REVIEW,
            ScorecardDimensionStatus.PASSED_REVIEW,
        }

    @property
    def needs_more_evidence(self) -> bool:
        """Return whether dimension needs more evidence."""

        return self.status in {
            ScorecardDimensionStatus.NOT_EVALUATED,
            ScorecardDimensionStatus.NEEDS_MORE_EVIDENCE,
        }

    @property
    def blocks_claim(self) -> bool:
        """Return whether dimension blocks stronger Wave 7 claims."""

        return self.status is ScorecardDimensionStatus.BLOCKED

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic dimension payload."""

        return {
            "authority_refs": list(self.authority_refs),
            "blocker_ids": list(self.blocker_ids),
            "dimension_id": self.dimension_id.value,
            "evidence_ids": list(self.evidence_ids),
            "review_notes": list(self.review_notes),
            "schema_version": self.schema_version,
            "score": self.score,
            "status": self.status.value,
            "summary": self.summary,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this dimension."""

        return _stable_sha256(self.canonical_payload())


@dataclass(frozen=True, slots=True)
class OrganismScorecard:
    """Evidence-bound scorecard for the Wave 7 cognitive organism substrate."""

    scorecard_id: str
    dimensions: tuple[ScorecardDimension, ...]
    decision: OrganismScorecardDecision
    evaluator_ref: str
    notes: tuple[str, ...] = ()
    claims_agi: bool = False
    claims_autonomous_authority: bool = False
    schema_version: str = WAVE_SEVEN_ORGANISM_SCORECARD_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate organism scorecard coverage and fail-closed decision."""

        if self.claims_agi:
            raise ValueError("Wave 7 organism scorecards must not claim AGI.")
        if self.claims_autonomous_authority:
            raise ValueError(
                "Wave 7 organism scorecards must not claim autonomous authority."
            )
        object.__setattr__(
            self,
            "scorecard_id",
            _require_non_empty(self.scorecard_id, "scorecard_id"),
        )
        object.__setattr__(
            self,
            "dimensions",
            tuple(
                sorted(
                    self.dimensions,
                    key=lambda dimension: dimension.dimension_id.value,
                )
            ),
        )
        object.__setattr__(
            self,
            "evaluator_ref",
            _require_non_empty(self.evaluator_ref, "evaluator_ref"),
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
        if not self.dimensions:
            raise ValueError("Organism scorecards require dimensions.")
        _ensure_unique(
            (dimension.dimension_id.value for dimension in self.dimensions),
            label="dimension_id",
        )
        missing = tuple(
            dimension.value
            for dimension in OrganismDimensionId
            if dimension not in {item.dimension_id for item in self.dimensions}
        )
        if missing:
            raise ValueError(
                "Organism scorecard missing required dimensions: " + ", ".join(missing)
            )
        if self.decision is OrganismScorecardDecision.READY_FOR_REVIEW:
            if self.blocking_dimension_ids:
                raise ValueError("Review-ready scorecards cannot have blockers.")
            if self.evidence_gap_dimension_ids:
                raise ValueError("Review-ready scorecards cannot have evidence gaps.")
            if self.overall_score < 0.75:
                raise ValueError("Review-ready scorecards require score >= 0.75.")
        if (
            self.decision is OrganismScorecardDecision.NEEDS_MORE_EVIDENCE
            and not self.evidence_gap_dimension_ids
        ):
            raise ValueError("Needs-more-evidence scorecards require evidence gaps.")
        if (
            self.decision is OrganismScorecardDecision.BLOCKED
            and not self.blocking_dimension_ids
        ):
            raise ValueError("Blocked scorecards require blocking dimensions.")

    @property
    def dimension_ids(self) -> tuple[str, ...]:
        """Return dimension ids in scorecard order."""

        return tuple(dimension.dimension_id.value for dimension in self.dimensions)

    @property
    def ready_dimension_ids(self) -> tuple[str, ...]:
        """Return dimensions ready for or passed through review."""

        return tuple(
            dimension.dimension_id.value
            for dimension in self.dimensions
            if dimension.ready_or_passed
        )

    @property
    def evidence_gap_dimension_ids(self) -> tuple[str, ...]:
        """Return dimensions that need more evidence."""

        return tuple(
            dimension.dimension_id.value
            for dimension in self.dimensions
            if dimension.needs_more_evidence
        )

    @property
    def blocking_dimension_ids(self) -> tuple[str, ...]:
        """Return dimensions that block stronger claims."""

        return tuple(
            dimension.dimension_id.value
            for dimension in self.dimensions
            if dimension.blocks_claim
        )

    @property
    def evidence_ids(self) -> tuple[str, ...]:
        """Return all evidence ids bound to this scorecard."""

        evidence: list[str] = []
        for dimension in self.dimensions:
            evidence.extend(dimension.evidence_ids)
        return _dedupe_text_tuple(evidence, label="evidence_id")

    @property
    def authority_refs(self) -> tuple[str, ...]:
        """Return all authority refs bound to this scorecard."""

        refs: list[str] = []
        for dimension in self.dimensions:
            refs.extend(dimension.authority_refs)
        return _dedupe_text_tuple(refs, label="authority_ref")

    @property
    def overall_score(self) -> float:
        """Return average score across required dimensions."""

        total = sum(dimension.score for dimension in self.dimensions)
        return round(total / len(self.dimensions), 4)

    @property
    def ready_for_review(self) -> bool:
        """Return whether scorecard is ready for human review."""

        return (
            self.decision is OrganismScorecardDecision.READY_FOR_REVIEW
            and not self.blocking_dimension_ids
            and not self.evidence_gap_dimension_ids
        )

    @property
    def blocks_claim(self) -> bool:
        """Return whether scorecard blocks stronger organism claims."""

        return self.decision is OrganismScorecardDecision.BLOCKED or bool(
            self.blocking_dimension_ids
        )

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic organism scorecard payload."""

        return {
            "authority_refs": list(self.authority_refs),
            "blocking_dimension_ids": list(self.blocking_dimension_ids),
            "claims_agi": self.claims_agi,
            "claims_autonomous_authority": self.claims_autonomous_authority,
            "decision": self.decision.value,
            "dimension_fingerprints": [
                dimension.fingerprint() for dimension in self.dimensions
            ],
            "dimension_ids": list(self.dimension_ids),
            "evaluator_ref": self.evaluator_ref,
            "evidence_gap_dimension_ids": list(self.evidence_gap_dimension_ids),
            "evidence_ids": list(self.evidence_ids),
            "notes": list(self.notes),
            "overall_score": self.overall_score,
            "ready_dimension_ids": list(self.ready_dimension_ids),
            "ready_for_review": self.ready_for_review,
            "schema_version": self.schema_version,
            "scorecard_id": self.scorecard_id,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this scorecard."""

        return _stable_sha256(self.canonical_payload())


@dataclass(frozen=True, slots=True)
class OrganismEvaluationSummary:
    """Human-readable but deterministic Wave 7 evaluation summary."""

    summary_id: str
    scorecard: OrganismScorecard
    headline: str
    strengths: tuple[str, ...]
    gaps: tuple[str, ...]
    required_next_reviews: tuple[str, ...]
    claim_boundary: str
    schema_version: str = WAVE_SEVEN_ORGANISM_EVALUATION_SUMMARY_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate scorecard summary and claim boundary."""

        object.__setattr__(
            self,
            "summary_id",
            _require_non_empty(self.summary_id, "summary_id"),
        )
        object.__setattr__(
            self,
            "headline",
            _require_non_empty(self.headline, "headline"),
        )
        object.__setattr__(
            self,
            "strengths",
            _normalize_unique_text_tuple(self.strengths, label="strength"),
        )
        object.__setattr__(
            self,
            "gaps",
            _normalize_unique_text_tuple(self.gaps, label="gap"),
        )
        object.__setattr__(
            self,
            "required_next_reviews",
            _normalize_unique_text_tuple(
                self.required_next_reviews,
                label="required_next_review",
            ),
        )
        object.__setattr__(
            self,
            "claim_boundary",
            _require_non_empty(self.claim_boundary, "claim_boundary"),
        )
        object.__setattr__(
            self,
            "schema_version",
            _require_non_empty(self.schema_version, "schema_version"),
        )
        if not self.strengths:
            raise ValueError("Organism evaluation summaries require strengths.")
        if self.scorecard.evidence_gap_dimension_ids and not self.gaps:
            raise ValueError("Evidence gaps require summary gaps.")
        if self.scorecard.blocks_claim and not self.gaps:
            raise ValueError("Blocked scorecards require summary gaps.")
        if self.scorecard.ready_for_review and not self.required_next_reviews:
            raise ValueError("Review-ready summaries require next reviews.")
        lowered = self.claim_boundary.lower()
        if "agi" in lowered and "not" not in lowered:
            raise ValueError("Claim boundary must not assert AGI.")

    @property
    def evidence_ids(self) -> tuple[str, ...]:
        """Return all evidence ids behind the summary."""

        return self.scorecard.evidence_ids

    @property
    def ready_for_review(self) -> bool:
        """Return whether summary says scorecard is ready for review."""

        return self.scorecard.ready_for_review

    @property
    def blocks_claim(self) -> bool:
        """Return whether summary blocks stronger claims."""

        return self.scorecard.blocks_claim

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic evaluation summary payload."""

        return {
            "blocks_claim": self.blocks_claim,
            "claim_boundary": self.claim_boundary,
            "evidence_ids": list(self.evidence_ids),
            "gaps": list(self.gaps),
            "headline": self.headline,
            "ready_for_review": self.ready_for_review,
            "required_next_reviews": list(self.required_next_reviews),
            "schema_version": self.schema_version,
            "scorecard_fingerprint": self.scorecard.fingerprint(),
            "strengths": list(self.strengths),
            "summary_id": self.summary_id,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this summary."""

        return _stable_sha256(self.canonical_payload())


def build_scorecard_dimension(
    *,
    dimension_id: OrganismDimensionId,
    status: ScorecardDimensionStatus,
    summary: str,
    evidence_ids: Iterable[str],
    authority_refs: Iterable[str],
    blocker_ids: Iterable[str] = (),
    review_notes: Iterable[str] = (),
    score: float = 0.0,
) -> ScorecardDimension:
    """Build one deterministic Wave 7 scorecard dimension."""

    return ScorecardDimension(
        dimension_id=dimension_id,
        status=status,
        summary=summary,
        evidence_ids=tuple(evidence_ids),
        authority_refs=tuple(authority_refs),
        blocker_ids=tuple(blocker_ids),
        review_notes=tuple(review_notes),
        score=score,
    )


def build_organism_scorecard(
    *,
    scorecard_id: str,
    dimensions: Iterable[ScorecardDimension],
    evaluator_ref: str,
    notes: Iterable[str] = (),
) -> OrganismScorecard:
    """Build a Wave 7 scorecard with fail-closed decision inference."""

    dimension_tuple = tuple(dimensions)
    if any(dimension.blocks_claim for dimension in dimension_tuple):
        decision = OrganismScorecardDecision.BLOCKED
    elif any(dimension.needs_more_evidence for dimension in dimension_tuple):
        decision = OrganismScorecardDecision.NEEDS_MORE_EVIDENCE
    elif _average_score(dimension_tuple) >= 0.75:
        decision = OrganismScorecardDecision.READY_FOR_REVIEW
    else:
        decision = OrganismScorecardDecision.RECORD_ONLY

    return OrganismScorecard(
        scorecard_id=scorecard_id,
        dimensions=dimension_tuple,
        decision=decision,
        evaluator_ref=evaluator_ref,
        notes=tuple(notes),
    )


def build_organism_evaluation_summary(
    *,
    summary_id: str,
    scorecard: OrganismScorecard,
    headline: str,
    strengths: Iterable[str],
    gaps: Iterable[str] = (),
    required_next_reviews: Iterable[str] = (),
    claim_boundary: str,
) -> OrganismEvaluationSummary:
    """Build a deterministic Wave 7 organism evaluation summary."""

    return OrganismEvaluationSummary(
        summary_id=summary_id,
        scorecard=scorecard,
        headline=headline,
        strengths=tuple(strengths),
        gaps=tuple(gaps),
        required_next_reviews=tuple(required_next_reviews),
        claim_boundary=claim_boundary,
    )


def _average_score(dimensions: tuple[ScorecardDimension, ...]) -> float:
    if not dimensions:
        return 0.0
    return round(
        sum(dimension.score for dimension in dimensions) / len(dimensions),
        4,
    )


def _require_non_empty(value: str, label: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{label} must not be empty.")
    return normalized


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
