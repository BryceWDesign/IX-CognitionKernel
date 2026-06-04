"""Wave 5 maturity scorecard records.

Wave 5 needs a deterministic scorecard that can summarize evidence readiness
without becoming promotion theater. This module scores required evidence areas,
records review checks, exposes blockers, and preserves claim boundaries. A high
score can make the dossier ready for external review; it cannot declare Wave 6,
AGI, production readiness, certification, autonomous authority, or independent
validation by internal assertion.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, TypeVar

from ix_cognition_kernel.wave5_contracts import (
    WAVE_FIVE_REQUIRED_CLAIM_BOUNDARIES,
    WaveFiveArtifactDecision,
    WaveFiveArtifactKind,
    WaveFiveArtifactRef,
    WaveFiveAuthorityState,
    WaveFiveCapabilityArea,
    WaveFiveClaimBoundary,
    WaveFiveSourceSystem,
    WaveFiveValidationStatus,
)

T = TypeVar("T")
E = TypeVar("E", bound=StrEnum)

WAVE_FIVE_SCORE_SECTION_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave5-maturity-score-section-v1"
)
WAVE_FIVE_SCORE_CHECK_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave5-maturity-score-check-v1"
)
WAVE_FIVE_SCORECARD_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave5-maturity-scorecard-v1"
)


class WaveFiveMaturityScoreArea(StrEnum):
    """Required areas scored by the Wave 5 maturity scorecard."""

    EXTERNAL_PROTOCOLS = "external-protocols"
    INDEPENDENT_REVIEWERS = "independent-reviewers"
    REPRODUCIBLE_EVIDENCE = "reproducible-evidence"
    ADVERSARIAL_SAFETY = "adversarial-safety"
    LONG_HORIZON_VALIDATION = "long-horizon-validation"
    CROSS_DOMAIN_TRANSFER = "cross-domain-transfer"
    BENCHMARK_GAMING_RESISTANCE = "benchmark-gaming-resistance"
    MEMORY_INTEGRITY = "memory-integrity"
    SAFE_REFUSAL = "safe-refusal"
    HUMAN_AUTHORITY = "human-authority"
    REPEATABILITY = "repeatability"
    BLACKFOX_COMPATIBILITY = "blackfox-compatibility"
    WORLDTWIN_SCENARIOS = "worldtwin-scenarios"
    WAVE_SIX_READINESS_GATE = "wave-six-readiness-gate"
    EVIDENCE_DOSSIER = "evidence-dossier"


class WaveFiveMaturityScoreStatus(StrEnum):
    """Status assigned to one maturity score area."""

    PASSING = "passing"
    PASSING_WITH_LIMITS = "passing-with-limits"
    NEEDS_EXTERNAL_EVIDENCE = "needs-external-evidence"
    DISPUTED = "disputed"
    BLOCKED = "blocked"
    MISSING = "missing"


class WaveFiveMaturityCheckKind(StrEnum):
    """Checks required for a scorecard to be reviewable."""

    ALL_REQUIRED_AREAS_SCORED = "all-required-areas-scored"
    SCORE_EVIDENCE_BOUND = "score-evidence-bound"
    LIMITATIONS_VISIBLE = "limitations-visible"
    BLOCKERS_VISIBLE = "blockers-visible"
    CLAIM_BOUNDARIES_PRESERVED = "claim-boundaries-preserved"
    HUMAN_AUTHORITY_PRESERVED = "human-authority-preserved"
    NO_WAVE_SIX_PROMOTION = "no-wave-six-promotion"
    NO_AGI_OR_CERTIFICATION_CLAIM = "no-agi-or-certification-claim"
    NO_EXECUTION_AUTHORITY = "no-execution-authority"
    EXTERNAL_REVIEW_PATH_VISIBLE = "external-review-path-visible"


class WaveFiveMaturityCheckResult(StrEnum):
    """Observed result of a maturity scorecard check."""

    PASSED = "passed"
    PASSED_WITH_LIMITS = "passed-with-limits"
    NEEDS_MORE_EVIDENCE = "needs-more-evidence"
    FAILED = "failed"


class WaveFiveMaturityReviewState(StrEnum):
    """Review state of the Wave 5 maturity scorecard."""

    INTERNAL_SCORECARD_READY = "internal-scorecard-ready"
    READY_FOR_EXTERNAL_SCORECARD_REVIEW = "ready-for-external-scorecard-review"
    UNDER_EXTERNAL_SCORECARD_REVIEW = "under-external-scorecard-review"
    EXTERNALLY_REVIEWED_WITH_BOUNDARIES = "externally-reviewed-with-boundaries"
    BLOCKED_BY_SCORECARD_GAP = "blocked-by-scorecard-gap"


SAFE_SCORE_STATUSES: tuple[WaveFiveMaturityScoreStatus, ...] = (
    WaveFiveMaturityScoreStatus.PASSING,
    WaveFiveMaturityScoreStatus.PASSING_WITH_LIMITS,
)

BLOCKING_SCORE_STATUSES: tuple[WaveFiveMaturityScoreStatus, ...] = (
    WaveFiveMaturityScoreStatus.NEEDS_EXTERNAL_EVIDENCE,
    WaveFiveMaturityScoreStatus.DISPUTED,
    WaveFiveMaturityScoreStatus.BLOCKED,
    WaveFiveMaturityScoreStatus.MISSING,
)

REQUIRED_SCORE_AREAS: tuple[WaveFiveMaturityScoreArea, ...] = (
    WaveFiveMaturityScoreArea.EXTERNAL_PROTOCOLS,
    WaveFiveMaturityScoreArea.INDEPENDENT_REVIEWERS,
    WaveFiveMaturityScoreArea.REPRODUCIBLE_EVIDENCE,
    WaveFiveMaturityScoreArea.ADVERSARIAL_SAFETY,
    WaveFiveMaturityScoreArea.LONG_HORIZON_VALIDATION,
    WaveFiveMaturityScoreArea.CROSS_DOMAIN_TRANSFER,
    WaveFiveMaturityScoreArea.BENCHMARK_GAMING_RESISTANCE,
    WaveFiveMaturityScoreArea.MEMORY_INTEGRITY,
    WaveFiveMaturityScoreArea.SAFE_REFUSAL,
    WaveFiveMaturityScoreArea.HUMAN_AUTHORITY,
    WaveFiveMaturityScoreArea.REPEATABILITY,
    WaveFiveMaturityScoreArea.BLACKFOX_COMPATIBILITY,
    WaveFiveMaturityScoreArea.WORLDTWIN_SCENARIOS,
    WaveFiveMaturityScoreArea.WAVE_SIX_READINESS_GATE,
    WaveFiveMaturityScoreArea.EVIDENCE_DOSSIER,
)

REQUIRED_SCORECARD_CHECKS: tuple[WaveFiveMaturityCheckKind, ...] = (
    WaveFiveMaturityCheckKind.ALL_REQUIRED_AREAS_SCORED,
    WaveFiveMaturityCheckKind.SCORE_EVIDENCE_BOUND,
    WaveFiveMaturityCheckKind.LIMITATIONS_VISIBLE,
    WaveFiveMaturityCheckKind.BLOCKERS_VISIBLE,
    WaveFiveMaturityCheckKind.CLAIM_BOUNDARIES_PRESERVED,
    WaveFiveMaturityCheckKind.HUMAN_AUTHORITY_PRESERVED,
    WaveFiveMaturityCheckKind.NO_WAVE_SIX_PROMOTION,
    WaveFiveMaturityCheckKind.NO_AGI_OR_CERTIFICATION_CLAIM,
    WaveFiveMaturityCheckKind.NO_EXECUTION_AUTHORITY,
    WaveFiveMaturityCheckKind.EXTERNAL_REVIEW_PATH_VISIBLE,
)

EXTERNAL_SCORECARD_REVIEW_SOURCE_SYSTEMS: tuple[WaveFiveSourceSystem, ...] = (
    WaveFiveSourceSystem.EXTERNAL_REVIEW,
    WaveFiveSourceSystem.INDEPENDENT_REVIEWER,
    WaveFiveSourceSystem.HUMAN_REVIEW,
)


@dataclass(frozen=True, slots=True)
class WaveFiveMaturityScoreSection:
    """One scored maturity area in the Wave 5 scorecard."""

    section_id: str
    area: WaveFiveMaturityScoreArea
    status: WaveFiveMaturityScoreStatus
    score: int
    max_score: int
    artifact_ids: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    summary: str
    limitations: tuple[str, ...] = ()
    blocker_ids: tuple[str, ...] = ()
    claim_boundaries: tuple[WaveFiveClaimBoundary, ...] = (
        WAVE_FIVE_REQUIRED_CLAIM_BOUNDARIES
    )
    schema_version: str = WAVE_FIVE_SCORE_SECTION_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate score section evidence, score bounds, and boundaries."""

        object.__setattr__(self, "section_id", _text(self.section_id, "section_id"))
        if self.max_score <= 0:
            raise ValueError("Maturity score sections require positive max_score.")
        if self.score < 0 or self.score > self.max_score:
            raise ValueError("Maturity score must be between zero and max_score.")
        object.__setattr__(
            self, "artifact_ids", _unique_text(self.artifact_ids, label="artifact_id")
        )
        object.__setattr__(
            self, "evidence_ids", _unique_text(self.evidence_ids, label="evidence_id")
        )
        object.__setattr__(self, "summary", _text(self.summary, "summary"))
        object.__setattr__(
            self, "limitations", _unique_text(self.limitations, label="limitation")
        )
        object.__setattr__(
            self, "blocker_ids", _unique_text(self.blocker_ids, label="blocker_id")
        )
        object.__setattr__(
            self,
            "claim_boundaries",
            _unique_enum(self.claim_boundaries, label="claim boundary"),
        )
        if not self.artifact_ids:
            raise ValueError("Maturity score sections require artifact ids.")
        if not self.evidence_ids:
            raise ValueError("Maturity score sections require evidence ids.")
        if self.status is WaveFiveMaturityScoreStatus.PASSING_WITH_LIMITS:
            if not self.limitations:
                raise ValueError("Limited maturity score sections require limits.")
        if self.status in BLOCKING_SCORE_STATUSES and not self.blocker_ids:
            raise ValueError("Blocking maturity score sections require blockers.")
        missing = tuple(
            boundary
            for boundary in WAVE_FIVE_REQUIRED_CLAIM_BOUNDARIES
            if boundary not in self.claim_boundaries
        )
        if missing:
            raise ValueError(
                "Maturity score sections must preserve claim boundary: "
                f"{missing[0].value}"
            )
        object.__setattr__(
            self, "schema_version", _text(self.schema_version, "schema_version")
        )

    @property
    def section_key(self) -> str:
        """Return deterministic section key."""

        return self.section_id

    @property
    def normalized_score(self) -> float:
        """Return normalized score from zero to one."""

        return self.score / self.max_score

    @property
    def blocks_scorecard_readiness(self) -> bool:
        """Return whether this section blocks scorecard readiness."""

        return self.status in BLOCKING_SCORE_STATUSES

    @property
    def reviewable_with_boundaries(self) -> bool:
        """Return whether this score is reviewable without promotion."""

        return self.status in SAFE_SCORE_STATUSES and bool(self.evidence_ids)

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic export payload."""

        return {
            "area": self.area.value,
            "artifact_ids": list(self.artifact_ids),
            "blocker_ids": list(self.blocker_ids),
            "claim_boundaries": [boundary.value for boundary in self.claim_boundaries],
            "evidence_ids": list(self.evidence_ids),
            "limitations": list(self.limitations),
            "max_score": self.max_score,
            "normalized_score": round(self.normalized_score, 6),
            "reviewable_with_boundaries": self.reviewable_with_boundaries,
            "schema_version": self.schema_version,
            "score": self.score,
            "section_id": self.section_id,
            "status": self.status.value,
            "summary": self.summary,
        }


@dataclass(frozen=True, slots=True)
class WaveFiveMaturityScorecardCheck:
    """One integrity check over the Wave 5 maturity scorecard."""

    check_id: str
    check_kind: WaveFiveMaturityCheckKind
    result: WaveFiveMaturityCheckResult
    description: str
    evidence_ids: tuple[str, ...]
    blocking: bool = True
    schema_version: str = WAVE_FIVE_SCORE_CHECK_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate scorecard-check evidence."""

        object.__setattr__(self, "check_id", _text(self.check_id, "check_id"))
        object.__setattr__(self, "description", _text(self.description, "description"))
        object.__setattr__(
            self, "evidence_ids", _unique_text(self.evidence_ids, label="evidence_id")
        )
        if not self.evidence_ids:
            raise ValueError("Maturity scorecard checks require evidence ids.")
        object.__setattr__(
            self, "schema_version", _text(self.schema_version, "schema_version")
        )

    @property
    def check_key(self) -> str:
        """Return deterministic check key."""

        return self.check_id

    @property
    def passed_with_boundaries(self) -> bool:
        """Return whether this check passed without erasing limits."""

        return self.result in {
            WaveFiveMaturityCheckResult.PASSED,
            WaveFiveMaturityCheckResult.PASSED_WITH_LIMITS,
        }

    @property
    def blocks_scorecard_readiness(self) -> bool:
        """Return whether this check blocks scorecard readiness."""

        return self.blocking and not self.passed_with_boundaries

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic export payload."""

        return {
            "blocking": self.blocking,
            "check_id": self.check_id,
            "check_kind": self.check_kind.value,
            "description": self.description,
            "evidence_ids": list(self.evidence_ids),
            "result": self.result.value,
            "schema_version": self.schema_version,
        }


@dataclass(frozen=True, slots=True)
class WaveFiveMaturityScorecard:
    """Deterministic scorecard for Wave 5 maturity review."""

    scorecard_id: str
    title: str
    source_system: WaveFiveSourceSystem
    review_state: WaveFiveMaturityReviewState
    sections: tuple[WaveFiveMaturityScoreSection, ...]
    checks: tuple[WaveFiveMaturityScorecardCheck, ...]
    dossier_artifact_id: str
    readiness_gate_artifact_id: str
    protocol_ids: tuple[str, ...]
    reviewer_ids: tuple[str, ...] = ()
    minimum_average_score: float = 0.9
    attempted_wave_six_promotion: bool = False
    claims_agi: bool = False
    grants_execution_authority: bool = False
    claims_production_ready: bool = False
    claims_certified: bool = False
    claim_boundaries: tuple[WaveFiveClaimBoundary, ...] = (
        WAVE_FIVE_REQUIRED_CLAIM_BOUNDARIES
    )
    notes: tuple[str, ...] = ()
    schema_version: str = WAVE_FIVE_SCORECARD_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate scorecard completeness and anti-promotion gates."""

        object.__setattr__(
            self, "scorecard_id", _text(self.scorecard_id, "scorecard_id")
        )
        object.__setattr__(self, "title", _text(self.title, "title"))
        object.__setattr__(
            self,
            "dossier_artifact_id",
            _text(self.dossier_artifact_id, "dossier_artifact_id"),
        )
        object.__setattr__(
            self,
            "readiness_gate_artifact_id",
            _text(self.readiness_gate_artifact_id, "readiness_gate_artifact_id"),
        )
        if self.minimum_average_score < 0 or self.minimum_average_score > 1:
            raise ValueError("minimum_average_score must be between zero and one.")
        if self.attempted_wave_six_promotion:
            raise ValueError("Maturity scorecards cannot promote to Wave 6.")
        if self.claims_agi:
            raise ValueError("Maturity scorecards cannot claim AGI.")
        if self.grants_execution_authority:
            raise ValueError("Maturity scorecards cannot grant execution authority.")
        if self.claims_production_ready:
            raise ValueError("Maturity scorecards cannot claim production readiness.")
        if self.claims_certified:
            raise ValueError("Maturity scorecards cannot claim certification.")
        sections = tuple(sorted(self.sections, key=lambda item: item.section_key))
        checks = tuple(sorted(self.checks, key=lambda item: item.check_key))
        if not sections:
            raise ValueError("Maturity scorecards require score sections.")
        if not checks:
            raise ValueError("Maturity scorecards require checks.")
        _unique_values((item.section_id for item in sections), label="section_id")
        _unique_values((item.area for item in sections), label="score area")
        _unique_values((item.check_id for item in checks), label="check_id")
        object.__setattr__(self, "sections", sections)
        object.__setattr__(self, "checks", checks)
        object.__setattr__(
            self, "protocol_ids", _unique_text(self.protocol_ids, label="protocol_id")
        )
        if not self.protocol_ids:
            raise ValueError("Maturity scorecards require protocol ids.")
        object.__setattr__(
            self, "reviewer_ids", _unique_text(self.reviewer_ids, label="reviewer_id")
        )
        object.__setattr__(
            self,
            "claim_boundaries",
            _unique_enum(self.claim_boundaries, label="claim boundary"),
        )
        missing_boundaries = tuple(
            boundary
            for boundary in WAVE_FIVE_REQUIRED_CLAIM_BOUNDARIES
            if boundary not in self.claim_boundaries
        )
        if missing_boundaries:
            raise ValueError(
                "Maturity scorecards must preserve claim boundary: "
                f"{missing_boundaries[0].value}"
            )
        object.__setattr__(self, "notes", _unique_text(self.notes, label="note"))
        object.__setattr__(
            self, "schema_version", _text(self.schema_version, "schema_version")
        )
        if self.externally_reviewed_with_boundaries:
            if self.source_system not in EXTERNAL_SCORECARD_REVIEW_SOURCE_SYSTEMS:
                raise ValueError(
                    "Externally reviewed scorecards require external source."
                )
            if not self.reviewer_ids:
                raise ValueError(
                    "Externally reviewed scorecards require reviewer ids."
                )
            if self.blocks_scorecard_readiness:
                raise ValueError(
                    "Externally reviewed scorecards cannot contain blockers."
                )

    @property
    def covered_areas(self) -> tuple[WaveFiveMaturityScoreArea, ...]:
        """Return score areas represented in this scorecard."""

        return tuple(section.area for section in self.sections)

    @property
    def missing_required_areas(self) -> tuple[WaveFiveMaturityScoreArea, ...]:
        """Return required score areas absent from this scorecard."""

        covered = set(self.covered_areas)
        return tuple(area for area in REQUIRED_SCORE_AREAS if area not in covered)

    @property
    def covered_check_kinds(self) -> tuple[WaveFiveMaturityCheckKind, ...]:
        """Return scorecard check kinds represented in this scorecard."""

        kinds: list[WaveFiveMaturityCheckKind] = []
        seen: set[WaveFiveMaturityCheckKind] = set()
        for check in self.checks:
            if check.check_kind not in seen:
                kinds.append(check.check_kind)
                seen.add(check.check_kind)
        return tuple(kinds)

    @property
    def missing_required_check_kinds(self) -> tuple[WaveFiveMaturityCheckKind, ...]:
        """Return required checks absent from this scorecard."""

        covered = set(self.covered_check_kinds)
        return tuple(kind for kind in REQUIRED_SCORECARD_CHECKS if kind not in covered)

    @property
    def blocking_section_ids(self) -> tuple[str, ...]:
        """Return score sections that block scorecard readiness."""

        return tuple(
            section.section_id
            for section in self.sections
            if section.blocks_scorecard_readiness
        )

    @property
    def blocking_check_ids(self) -> tuple[str, ...]:
        """Return checks that block scorecard readiness."""

        return tuple(
            check.check_id for check in self.checks
            if check.blocks_scorecard_readiness
        )

    @property
    def total_score(self) -> int:
        """Return summed score across all sections."""

        return sum(section.score for section in self.sections)

    @property
    def total_max_score(self) -> int:
        """Return summed max score across all sections."""

        return sum(section.max_score for section in self.sections)

    @property
    def average_score(self) -> float:
        """Return weighted average score across all sections."""

        return self.total_score / self.total_max_score

    @property
    def meets_minimum_average_score(self) -> bool:
        """Return whether the weighted score meets the configured threshold."""

        return self.average_score >= self.minimum_average_score

    @property
    def makes_no_forbidden_claims(self) -> bool:
        """Return whether scorecard avoids forbidden promotion claims."""

        return not any(
            (
                self.attempted_wave_six_promotion,
                self.claims_agi,
                self.grants_execution_authority,
                self.claims_production_ready,
                self.claims_certified,
            )
        )

    @property
    def has_required_area_coverage(self) -> bool:
        """Return whether every locked score area is represented."""

        return not self.missing_required_areas

    @property
    def has_required_check_coverage(self) -> bool:
        """Return whether every locked scorecard check is represented."""

        return not self.missing_required_check_kinds

    @property
    def blocks_scorecard_readiness(self) -> bool:
        """Return whether any condition blocks external scorecard review."""

        return bool(
            self.missing_required_areas
            or self.missing_required_check_kinds
            or self.blocking_section_ids
            or self.blocking_check_ids
            or not self.meets_minimum_average_score
            or not self.makes_no_forbidden_claims
        )

    @property
    def ready_for_external_scorecard_review(self) -> bool:
        """Return whether scorecard can enter external review."""

        return (
            self.review_state
            in {
                WaveFiveMaturityReviewState.INTERNAL_SCORECARD_READY,
                WaveFiveMaturityReviewState.READY_FOR_EXTERNAL_SCORECARD_REVIEW,
                WaveFiveMaturityReviewState.UNDER_EXTERNAL_SCORECARD_REVIEW,
            }
            and self.has_required_area_coverage
            and self.has_required_check_coverage
            and not self.blocking_section_ids
            and not self.blocking_check_ids
            and self.meets_minimum_average_score
            and self.makes_no_forbidden_claims
        )

    @property
    def externally_reviewed_with_boundaries(self) -> bool:
        """Return whether external scorecard review accepted boundaries."""

        return (
            self.review_state
            is WaveFiveMaturityReviewState.EXTERNALLY_REVIEWED_WITH_BOUNDARIES
        )

    @property
    def all_evidence_ids(self) -> tuple[str, ...]:
        """Return all evidence ids bound into this scorecard."""

        evidence_ids: list[str] = []
        seen: set[str] = set()
        for evidence_id in self._iter_evidence_ids():
            if evidence_id not in seen:
                evidence_ids.append(evidence_id)
                seen.add(evidence_id)
        return tuple(evidence_ids)

    def to_artifact_ref(self) -> WaveFiveArtifactRef:
        """Return this scorecard as a Wave 5 traceability artifact."""

        decision = WaveFiveArtifactDecision.NEEDS_EXTERNAL_EVIDENCE
        status = WaveFiveValidationStatus.MISSING_EXTERNAL_EVIDENCE
        authority = WaveFiveAuthorityState.HUMAN_REVIEW_REQUIRED
        if self.externally_reviewed_with_boundaries:
            decision = WaveFiveArtifactDecision.EXTERNALLY_REVIEWED
            status = WaveFiveValidationStatus.ACCEPTED_WITH_BOUNDARIES
        elif self.ready_for_external_scorecard_review:
            decision = WaveFiveArtifactDecision.READY_FOR_INDEPENDENT_REVIEW
            status = WaveFiveValidationStatus.UNDER_INDEPENDENT_REVIEW
        elif self.blocks_scorecard_readiness:
            decision = WaveFiveArtifactDecision.BLOCKED
            status = WaveFiveValidationStatus.REJECTED
            authority = WaveFiveAuthorityState.BLOCKED
        return WaveFiveArtifactRef(
            artifact_id=self.scorecard_id,
            kind=WaveFiveArtifactKind.ECOSYSTEM_TRACEABILITY_MAP,
            capability_area=WaveFiveCapabilityArea.ECOSYSTEM_TRACEABILITY,
            source_system=self.source_system,
            summary=self.title,
            produced_by_engine_id="wave5-maturity-scorecard-engine",
            produced_by_agent_role_id="maturity-scorecard-reviewer",
            evidence_ids=self.all_evidence_ids,
            decision=decision,
            authority_state=authority,
            validation_status=status,
            claim_boundaries=self.claim_boundaries,
        )

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic export payload."""

        return {
            "attempted_wave_six_promotion": self.attempted_wave_six_promotion,
            "average_score": round(self.average_score, 6),
            "checks": [check.canonical_payload() for check in self.checks],
            "claim_boundaries": [boundary.value for boundary in self.claim_boundaries],
            "claims_agi": self.claims_agi,
            "claims_certified": self.claims_certified,
            "claims_production_ready": self.claims_production_ready,
            "dossier_artifact_id": self.dossier_artifact_id,
            "grants_execution_authority": self.grants_execution_authority,
            "minimum_average_score": self.minimum_average_score,
            "notes": list(self.notes),
            "protocol_ids": list(self.protocol_ids),
            "readiness_gate_artifact_id": self.readiness_gate_artifact_id,
            "review_state": self.review_state.value,
            "reviewer_ids": list(self.reviewer_ids),
            "schema_version": self.schema_version,
            "scorecard_id": self.scorecard_id,
            "sections": [section.canonical_payload() for section in self.sections],
            "source_system": self.source_system.value,
            "title": self.title,
            "total_max_score": self.total_max_score,
            "total_score": self.total_score,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this scorecard."""

        return _stable_sha256(self.canonical_payload())

    def _iter_evidence_ids(self) -> Iterable[str]:
        """Yield evidence ids in deterministic scorecard traversal order."""

        for section in self.sections:
            yield from section.evidence_ids
        for check in self.checks:
            yield from check.evidence_ids


def required_score_areas() -> tuple[WaveFiveMaturityScoreArea, ...]:
    """Return locked score areas required for Wave 5 maturity review."""

    return REQUIRED_SCORE_AREAS


def required_scorecard_checks() -> tuple[WaveFiveMaturityCheckKind, ...]:
    """Return locked scorecard checks required for Wave 5 maturity review."""

    return REQUIRED_SCORECARD_CHECKS


def safe_score_statuses() -> tuple[WaveFiveMaturityScoreStatus, ...]:
    """Return score statuses that do not block review."""

    return SAFE_SCORE_STATUSES


def blocking_score_statuses() -> tuple[WaveFiveMaturityScoreStatus, ...]:
    """Return score statuses that block scorecard review."""

    return BLOCKING_SCORE_STATUSES


def external_scorecard_review_source_systems() -> tuple[WaveFiveSourceSystem, ...]:
    """Return source systems allowed to assert external scorecard review."""

    return EXTERNAL_SCORECARD_REVIEW_SOURCE_SYSTEMS


def _text(value: str, label: str) -> str:
    """Return stripped text or raise when empty."""

    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{label} must not be empty.")
    return normalized


def _unique_text(values: Iterable[str], *, label: str) -> tuple[str, ...]:
    """Normalize text values while rejecting blanks and duplicates."""

    normalized: list[str] = []
    seen: set[str] = set()
    for value in values:
        item = _text(value, label)
        if item in seen:
            raise ValueError(f"Duplicate {label} detected: {item}")
        normalized.append(item)
        seen.add(item)
    return tuple(normalized)


def _unique_enum(values: Iterable[E], *, label: str) -> tuple[E, ...]:
    """Return enum values while rejecting duplicates."""

    normalized: list[E] = []
    seen: set[E] = set()
    for value in values:
        if value in seen:
            raise ValueError(f"Duplicate {label} detected: {value.value}")
        normalized.append(value)
        seen.add(value)
    return tuple(normalized)


def _unique_values(values: Iterable[T], *, label: str) -> set[T]:
    """Return unique values while rejecting duplicates."""

    seen: set[T] = set()
    for value in values:
        if value in seen:
            raise ValueError(f"Duplicate {label} detected: {value}")
        seen.add(value)
    return seen


def _stable_sha256(payload: Mapping[str, Any]) -> str:
    """Return deterministic SHA-256 over a canonical JSON payload."""

    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return hashlib.sha256(encoded).hexdigest()
