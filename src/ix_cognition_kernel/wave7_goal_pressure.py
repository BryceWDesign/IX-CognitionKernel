"""Wave 7 goal pressure engine.

Goal pressure gives a persistent cognitive organism substrate long-horizon
research direction without granting autonomous authority. It records goals,
subgoals, conflicts, retirements, evidence requirements, and bounded trial
recommendations while preserving the doctrine that ambition never overrides
human authority.

Wave 7 goal doctrine:

- goals are not permission,
- priority is not authority,
- pressure is not execution,
- subgoals remain bounded,
- conflicts remain visible,
- retired goals preserve evidence,
- blocked goals cannot support organism maturity claims.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

WAVE_SEVEN_RESEARCH_GOAL_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave7-research-goal-v1"
)
WAVE_SEVEN_SUBGOAL_SCHEMA_VERSION = "ix-cognition-kernel-wave7-subgoal-v1"
WAVE_SEVEN_GOAL_CONFLICT_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave7-goal-conflict-v1"
)
WAVE_SEVEN_GOAL_RETIREMENT_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave7-goal-retirement-v1"
)
WAVE_SEVEN_GOAL_PRESSURE_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave7-goal-pressure-v1"
)
WAVE_SEVEN_GOAL_PRESSURE_REPORT_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave7-goal-pressure-report-v1"
)


class GoalStatus(StrEnum):
    """Reviewable status for a Wave 7 research goal."""

    PROPOSED = "proposed"
    ACTIVE = "active"
    READY_FOR_REVIEW = "ready-for-review"
    BLOCKED = "blocked"
    RETIRED = "retired"


class GoalPriority(StrEnum):
    """Priority level for bounded research direction."""

    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


class SubgoalStatus(StrEnum):
    """Reviewable status for a bounded subgoal."""

    PROPOSED = "proposed"
    IN_PROGRESS = "in-progress"
    READY_FOR_REVIEW = "ready-for-review"
    BLOCKED = "blocked"
    COMPLETE = "complete"
    RETIRED = "retired"


class GoalConflictKind(StrEnum):
    """Kinds of conflicts that constrain goal pressure."""

    DOCTRINE_CONFLICT = "doctrine-conflict"
    AUTHORITY_CONFLICT = "authority-conflict"
    EVIDENCE_CONFLICT = "evidence-conflict"
    CAPABILITY_CONFLICT = "capability-conflict"
    SAFETY_CONFLICT = "safety-conflict"
    CLAIM_BOUNDARY_CONFLICT = "claim-boundary-conflict"


class GoalPressureDecision(StrEnum):
    """Fail-closed decision for goal pressure review."""

    RECORD_ONLY = "record-only"
    READY_FOR_REVIEW = "ready-for-review"
    NEEDS_MORE_EVIDENCE = "needs-more-evidence"
    BLOCKED = "blocked"


@dataclass(frozen=True, slots=True)
class ResearchGoal:
    """Long-horizon research goal without autonomous authority."""

    goal_id: str
    title: str
    mission_alignment: str
    status: GoalStatus
    priority: GoalPriority
    subgoal_ids: tuple[str, ...]
    success_criteria: tuple[str, ...]
    non_goal_ids: tuple[str, ...]
    doctrine_ids: tuple[str, ...]
    authority_refs: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    blocked_reason: str = ""
    claims_autonomous_authority: bool = False
    overrides_doctrine: bool = False
    schema_version: str = WAVE_SEVEN_RESEARCH_GOAL_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate goal boundaries and reject authority inflation."""

        if self.claims_autonomous_authority:
            raise ValueError("Research goals must not claim autonomous authority.")
        if self.overrides_doctrine:
            raise ValueError("Research goals must not override doctrine.")
        object.__setattr__(
            self,
            "goal_id",
            _require_non_empty(self.goal_id, "goal_id"),
        )
        object.__setattr__(
            self,
            "title",
            _require_non_empty(self.title, "title"),
        )
        object.__setattr__(
            self,
            "mission_alignment",
            _require_non_empty(self.mission_alignment, "mission_alignment"),
        )
        object.__setattr__(
            self,
            "subgoal_ids",
            _normalize_unique_text_tuple(self.subgoal_ids, label="subgoal_id"),
        )
        object.__setattr__(
            self,
            "success_criteria",
            _normalize_unique_text_tuple(
                self.success_criteria, label="success_criterion"
            ),
        )
        object.__setattr__(
            self,
            "non_goal_ids",
            _normalize_unique_text_tuple(self.non_goal_ids, label="non_goal_id"),
        )
        object.__setattr__(
            self,
            "doctrine_ids",
            _normalize_unique_text_tuple(self.doctrine_ids, label="doctrine_id"),
        )
        object.__setattr__(
            self,
            "authority_refs",
            _normalize_unique_text_tuple(self.authority_refs, label="authority_ref"),
        )
        object.__setattr__(
            self,
            "evidence_ids",
            _normalize_unique_text_tuple(self.evidence_ids, label="evidence_id"),
        )
        object.__setattr__(
            self,
            "blocked_reason",
            _normalize_optional_text(self.blocked_reason),
        )
        object.__setattr__(
            self,
            "schema_version",
            _require_non_empty(self.schema_version, "schema_version"),
        )
        if not self.doctrine_ids:
            raise ValueError("Research goals require doctrine ids.")
        if not self.authority_refs:
            raise ValueError("Research goals require authority refs.")
        if not self.evidence_ids:
            raise ValueError("Research goals require evidence ids.")
        if self.status is GoalStatus.BLOCKED and not self.blocked_reason:
            raise ValueError("Blocked research goals require blocked_reason.")
        if self.status is not GoalStatus.BLOCKED and self.blocked_reason:
            raise ValueError("Only blocked research goals may include reason.")
        if self.status in {
            GoalStatus.ACTIVE,
            GoalStatus.READY_FOR_REVIEW,
        }:
            if not self.subgoal_ids:
                raise ValueError("Active research goals require subgoals.")
            if not self.success_criteria:
                raise ValueError("Active research goals require success criteria.")

    @property
    def blocked(self) -> bool:
        """Return whether the goal is blocked."""

        return self.status is GoalStatus.BLOCKED

    @property
    def retired(self) -> bool:
        """Return whether the goal is retired."""

        return self.status is GoalStatus.RETIRED

    @property
    def ready_for_review(self) -> bool:
        """Return whether the goal is ready for bounded review."""

        return self.status is GoalStatus.READY_FOR_REVIEW

    @property
    def requires_elevated_review(self) -> bool:
        """Return whether priority requires review before pressure is used."""

        return self.priority in {GoalPriority.HIGH, GoalPriority.CRITICAL}

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic research-goal payload."""

        return {
            "authority_refs": list(self.authority_refs),
            "blocked_reason": self.blocked_reason,
            "claims_autonomous_authority": self.claims_autonomous_authority,
            "doctrine_ids": list(self.doctrine_ids),
            "evidence_ids": list(self.evidence_ids),
            "goal_id": self.goal_id,
            "mission_alignment": self.mission_alignment,
            "non_goal_ids": list(self.non_goal_ids),
            "overrides_doctrine": self.overrides_doctrine,
            "priority": self.priority.value,
            "schema_version": self.schema_version,
            "status": self.status.value,
            "subgoal_ids": list(self.subgoal_ids),
            "success_criteria": list(self.success_criteria),
            "title": self.title,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this goal."""

        return _stable_sha256(self.canonical_payload())


@dataclass(frozen=True, slots=True)
class Subgoal:
    """Bounded subgoal that can recommend trials but not authorize them."""

    subgoal_id: str
    parent_goal_id: str
    title: str
    status: SubgoalStatus
    bounded_trial_recommendations: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    authority_refs: tuple[str, ...]
    completion_criteria: tuple[str, ...]
    blocked_reason: str = ""
    grants_permission: bool = False
    schema_version: str = WAVE_SEVEN_SUBGOAL_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate subgoal boundaries and permission separation."""

        if self.grants_permission:
            raise ValueError("Subgoals must not grant permission.")
        object.__setattr__(
            self,
            "subgoal_id",
            _require_non_empty(self.subgoal_id, "subgoal_id"),
        )
        object.__setattr__(
            self,
            "parent_goal_id",
            _require_non_empty(self.parent_goal_id, "parent_goal_id"),
        )
        object.__setattr__(
            self,
            "title",
            _require_non_empty(self.title, "title"),
        )
        object.__setattr__(
            self,
            "bounded_trial_recommendations",
            _normalize_unique_text_tuple(
                self.bounded_trial_recommendations,
                label="bounded_trial_recommendation",
            ),
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
            "completion_criteria",
            _normalize_unique_text_tuple(
                self.completion_criteria, label="completion_criterion"
            ),
        )
        object.__setattr__(
            self,
            "blocked_reason",
            _normalize_optional_text(self.blocked_reason),
        )
        object.__setattr__(
            self,
            "schema_version",
            _require_non_empty(self.schema_version, "schema_version"),
        )
        if not self.evidence_ids:
            raise ValueError("Subgoals require evidence ids.")
        if not self.authority_refs:
            raise ValueError("Subgoals require authority refs.")
        if self.status is SubgoalStatus.BLOCKED and not self.blocked_reason:
            raise ValueError("Blocked subgoals require blocked_reason.")
        if self.status is not SubgoalStatus.BLOCKED and self.blocked_reason:
            raise ValueError("Only blocked subgoals may include reason.")
        if self.status in {
            SubgoalStatus.IN_PROGRESS,
            SubgoalStatus.READY_FOR_REVIEW,
            SubgoalStatus.COMPLETE,
        }:
            if not self.completion_criteria:
                raise ValueError("Active subgoals require completion criteria.")

    @property
    def blocked(self) -> bool:
        """Return whether the subgoal is blocked."""

        return self.status is SubgoalStatus.BLOCKED

    @property
    def complete(self) -> bool:
        """Return whether the subgoal is complete."""

        return self.status is SubgoalStatus.COMPLETE

    @property
    def ready_for_review(self) -> bool:
        """Return whether the subgoal is ready for bounded review."""

        return self.status is SubgoalStatus.READY_FOR_REVIEW

    @property
    def recommends_trials(self) -> bool:
        """Return whether this subgoal recommends bounded trials."""

        return bool(self.bounded_trial_recommendations)

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic subgoal payload."""

        return {
            "authority_refs": list(self.authority_refs),
            "blocked_reason": self.blocked_reason,
            "bounded_trial_recommendations": list(
                self.bounded_trial_recommendations
            ),
            "completion_criteria": list(self.completion_criteria),
            "evidence_ids": list(self.evidence_ids),
            "grants_permission": self.grants_permission,
            "parent_goal_id": self.parent_goal_id,
            "schema_version": self.schema_version,
            "status": self.status.value,
            "subgoal_id": self.subgoal_id,
            "title": self.title,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this subgoal."""

        return _stable_sha256(self.canonical_payload())


@dataclass(frozen=True, slots=True)
class GoalConflict:
    """Conflict that constrains or blocks goal pressure."""

    conflict_id: str
    goal_id: str
    kind: GoalConflictKind
    summary: str
    evidence_ids: tuple[str, ...]
    authority_refs: tuple[str, ...]
    unresolved: bool = True
    mitigation: str = ""
    schema_version: str = WAVE_SEVEN_GOAL_CONFLICT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate conflict evidence and resolution state."""

        object.__setattr__(
            self,
            "conflict_id",
            _require_non_empty(self.conflict_id, "conflict_id"),
        )
        object.__setattr__(
            self,
            "goal_id",
            _require_non_empty(self.goal_id, "goal_id"),
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
            "authority_refs",
            _normalize_unique_text_tuple(self.authority_refs, label="authority_ref"),
        )
        object.__setattr__(
            self,
            "mitigation",
            _normalize_optional_text(self.mitigation),
        )
        object.__setattr__(
            self,
            "schema_version",
            _require_non_empty(self.schema_version, "schema_version"),
        )
        if not self.evidence_ids:
            raise ValueError("Goal conflicts require evidence ids.")
        if not self.authority_refs:
            raise ValueError("Goal conflicts require authority refs.")
        if not self.unresolved and not self.mitigation:
            raise ValueError("Resolved goal conflicts require mitigation.")

    @property
    def blocks_goal(self) -> bool:
        """Return whether this conflict blocks stronger goal claims."""

        return self.unresolved and self.kind in {
            GoalConflictKind.DOCTRINE_CONFLICT,
            GoalConflictKind.AUTHORITY_CONFLICT,
            GoalConflictKind.SAFETY_CONFLICT,
            GoalConflictKind.CLAIM_BOUNDARY_CONFLICT,
        }

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic goal-conflict payload."""

        return {
            "authority_refs": list(self.authority_refs),
            "conflict_id": self.conflict_id,
            "evidence_ids": list(self.evidence_ids),
            "goal_id": self.goal_id,
            "kind": self.kind.value,
            "mitigation": self.mitigation,
            "schema_version": self.schema_version,
            "summary": self.summary,
            "unresolved": self.unresolved,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this conflict."""

        return _stable_sha256(self.canonical_payload())


@dataclass(frozen=True, slots=True)
class GoalRetirement:
    """Evidence-preserving retirement record for a research goal."""

    retirement_id: str
    goal_id: str
    reason: str
    preserved_evidence_ids: tuple[str, ...]
    authority_refs: tuple[str, ...]
    lesson: str
    schema_version: str = WAVE_SEVEN_GOAL_RETIREMENT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate retirement evidence and lesson preservation."""

        object.__setattr__(
            self,
            "retirement_id",
            _require_non_empty(self.retirement_id, "retirement_id"),
        )
        object.__setattr__(
            self,
            "goal_id",
            _require_non_empty(self.goal_id, "goal_id"),
        )
        object.__setattr__(
            self,
            "reason",
            _require_non_empty(self.reason, "reason"),
        )
        object.__setattr__(
            self,
            "preserved_evidence_ids",
            _normalize_unique_text_tuple(
                self.preserved_evidence_ids,
                label="preserved_evidence_id",
            ),
        )
        object.__setattr__(
            self,
            "authority_refs",
            _normalize_unique_text_tuple(self.authority_refs, label="authority_ref"),
        )
        object.__setattr__(
            self,
            "lesson",
            _require_non_empty(self.lesson, "lesson"),
        )
        object.__setattr__(
            self,
            "schema_version",
            _require_non_empty(self.schema_version, "schema_version"),
        )
        if not self.preserved_evidence_ids:
            raise ValueError("Goal retirements require preserved evidence ids.")
        if not self.authority_refs:
            raise ValueError("Goal retirements require authority refs.")

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic goal-retirement payload."""

        return {
            "authority_refs": list(self.authority_refs),
            "goal_id": self.goal_id,
            "lesson": self.lesson,
            "preserved_evidence_ids": list(self.preserved_evidence_ids),
            "reason": self.reason,
            "retirement_id": self.retirement_id,
            "schema_version": self.schema_version,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this retirement."""

        return _stable_sha256(self.canonical_payload())


@dataclass(frozen=True, slots=True)
class GoalPressure:
    """Bounded pressure state for a research goal and its subgoals."""

    pressure_id: str
    goal: ResearchGoal
    subgoals: tuple[Subgoal, ...]
    conflicts: tuple[GoalConflict, ...]
    retirements: tuple[GoalRetirement, ...]
    decision: GoalPressureDecision
    recommended_next_trial_ids: tuple[str, ...]
    notes: tuple[str, ...] = ()
    schema_version: str = WAVE_SEVEN_GOAL_PRESSURE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate goal pressure linkage and fail-closed status."""

        object.__setattr__(
            self,
            "pressure_id",
            _require_non_empty(self.pressure_id, "pressure_id"),
        )
        object.__setattr__(
            self,
            "subgoals",
            tuple(sorted(self.subgoals, key=lambda subgoal: subgoal.subgoal_id)),
        )
        object.__setattr__(
            self,
            "conflicts",
            tuple(
                sorted(
                    self.conflicts,
                    key=lambda conflict: conflict.conflict_id,
                )
            ),
        )
        object.__setattr__(
            self,
            "retirements",
            tuple(
                sorted(
                    self.retirements,
                    key=lambda retirement: retirement.retirement_id,
                )
            ),
        )
        object.__setattr__(
            self,
            "recommended_next_trial_ids",
            _normalize_unique_text_tuple(
                self.recommended_next_trial_ids,
                label="recommended_next_trial_id",
            ),
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
            (subgoal.subgoal_id for subgoal in self.subgoals),
            label="subgoal_id",
        )
        _ensure_unique(
            (conflict.conflict_id for conflict in self.conflicts),
            label="conflict_id",
        )
        _ensure_unique(
            (retirement.retirement_id for retirement in self.retirements),
            label="retirement_id",
        )
        subgoal_ids = {subgoal.subgoal_id for subgoal in self.subgoals}
        missing_subgoals = tuple(
            subgoal_id
            for subgoal_id in self.goal.subgoal_ids
            if subgoal_id not in subgoal_ids
        )
        if missing_subgoals:
            missing = ", ".join(missing_subgoals)
            raise ValueError(f"Goal pressure missing subgoals: {missing}")

        for subgoal in self.subgoals:
            if subgoal.parent_goal_id != self.goal.goal_id:
                raise ValueError("Subgoals must reference parent goal id.")
        for conflict in self.conflicts:
            if conflict.goal_id != self.goal.goal_id:
                raise ValueError("Conflicts must reference goal id.")
        for retirement in self.retirements:
            if retirement.goal_id != self.goal.goal_id:
                raise ValueError("Retirements must reference goal id.")
        if (
            self.decision is GoalPressureDecision.READY_FOR_REVIEW
            and self.blocking_reason_ids
        ):
            raise ValueError("Review-ready goal pressure cannot have blockers.")
        if (
            self.decision is GoalPressureDecision.BLOCKED
            and not self.blocking_reason_ids
        ):
            raise ValueError("Blocked goal pressure requires blockers.")

    @property
    def subgoal_ids(self) -> tuple[str, ...]:
        """Return subgoal ids in pressure state."""

        return tuple(subgoal.subgoal_id for subgoal in self.subgoals)

    @property
    def conflict_ids(self) -> tuple[str, ...]:
        """Return conflict ids in pressure state."""

        return tuple(conflict.conflict_id for conflict in self.conflicts)

    @property
    def retirement_ids(self) -> tuple[str, ...]:
        """Return retirement ids in pressure state."""

        return tuple(retirement.retirement_id for retirement in self.retirements)

    @property
    def complete_subgoal_ids(self) -> tuple[str, ...]:
        """Return complete subgoal ids."""

        return tuple(subgoal.subgoal_id for subgoal in self.subgoals if subgoal.complete)

    @property
    def blocked_subgoal_ids(self) -> tuple[str, ...]:
        """Return blocked subgoal ids."""

        return tuple(subgoal.subgoal_id for subgoal in self.subgoals if subgoal.blocked)

    @property
    def unresolved_conflict_ids(self) -> tuple[str, ...]:
        """Return unresolved conflict ids."""

        return tuple(
            conflict.conflict_id for conflict in self.conflicts if conflict.unresolved
        )

    @property
    def blocking_conflict_ids(self) -> tuple[str, ...]:
        """Return conflicts that block stronger goal claims."""

        return tuple(
            conflict.conflict_id for conflict in self.conflicts if conflict.blocks_goal
        )

    @property
    def evidence_ids(self) -> tuple[str, ...]:
        """Return all evidence ids bound to goal pressure."""

        evidence: list[str] = list(self.goal.evidence_ids)
        for subgoal in self.subgoals:
            evidence.extend(subgoal.evidence_ids)
        for conflict in self.conflicts:
            evidence.extend(conflict.evidence_ids)
        for retirement in self.retirements:
            evidence.extend(retirement.preserved_evidence_ids)
        return _normalize_unique_text_tuple(evidence, label="evidence_id")

    @property
    def blocking_reason_ids(self) -> tuple[str, ...]:
        """Return goal-pressure blockers."""

        reasons: list[str] = []
        if self.goal.blocked:
            reasons.append("goal-blocked")
        if self.blocked_subgoal_ids:
            reasons.append("subgoal-blocked")
        if self.blocking_conflict_ids:
            reasons.append("conflict-blocks-goal")
        if self.goal.retired and not self.retirements:
            reasons.append("retired-goal-missing-retirement-record")
        return _normalize_unique_text_tuple(reasons, label="blocking_reason_id")

    @property
    def ready_for_review(self) -> bool:
        """Return whether goal pressure is ready for bounded review."""

        return (
            self.decision is GoalPressureDecision.READY_FOR_REVIEW
            and not self.blocking_reason_ids
            and bool(self.evidence_ids)
        )

    @property
    def blocks_claim(self) -> bool:
        """Return whether goal pressure blocks stronger organism claims."""

        return (
            self.decision is GoalPressureDecision.BLOCKED
            or bool(self.blocking_reason_ids)
        )

    @property
    def recommends_trials(self) -> bool:
        """Return whether pressure recommends next bounded trials."""

        return bool(self.recommended_next_trial_ids) or any(
            subgoal.recommends_trials for subgoal in self.subgoals
        )

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic goal-pressure payload."""

        return {
            "blocked_subgoal_ids": list(self.blocked_subgoal_ids),
            "blocking_conflict_ids": list(self.blocking_conflict_ids),
            "blocking_reason_ids": list(self.blocking_reason_ids),
            "complete_subgoal_ids": list(self.complete_subgoal_ids),
            "conflict_fingerprints": [
                conflict.fingerprint() for conflict in self.conflicts
            ],
            "decision": self.decision.value,
            "evidence_ids": list(self.evidence_ids),
            "goal_fingerprint": self.goal.fingerprint(),
            "notes": list(self.notes),
            "pressure_id": self.pressure_id,
            "recommended_next_trial_ids": list(self.recommended_next_trial_ids),
            "retirement_fingerprints": [
                retirement.fingerprint() for retirement in self.retirements
            ],
            "schema_version": self.schema_version,
            "subgoal_fingerprints": [
                subgoal.fingerprint() for subgoal in self.subgoals
            ],
            "unresolved_conflict_ids": list(self.unresolved_conflict_ids),
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this pressure state."""

        return _stable_sha256(self.canonical_payload())


@dataclass(frozen=True, slots=True)
class GoalPressureReport:
    """Review report for Wave 7 goal pressure."""

    report_id: str
    pressures: tuple[GoalPressure, ...]
    decision: GoalPressureDecision
    notes: tuple[str, ...] = ()
    schema_version: str = WAVE_SEVEN_GOAL_PRESSURE_REPORT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate report and preserve unresolved goal blockers."""

        object.__setattr__(
            self,
            "report_id",
            _require_non_empty(self.report_id, "report_id"),
        )
        object.__setattr__(
            self,
            "pressures",
            tuple(
                sorted(
                    self.pressures,
                    key=lambda pressure: pressure.pressure_id,
                )
            ),
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
        if not self.pressures:
            raise ValueError("Goal pressure reports require pressures.")
        _ensure_unique(
            (pressure.pressure_id for pressure in self.pressures),
            label="pressure_id",
        )
        if (
            self.decision is GoalPressureDecision.READY_FOR_REVIEW
            and self.blocking_pressure_ids
        ):
            raise ValueError("Review-ready goal pressure reports cannot block.")

    @property
    def pressure_ids(self) -> tuple[str, ...]:
        """Return pressure ids in this report."""

        return tuple(pressure.pressure_id for pressure in self.pressures)

    @property
    def review_ready_pressure_ids(self) -> tuple[str, ...]:
        """Return review-ready pressure ids."""

        return tuple(
            pressure.pressure_id
            for pressure in self.pressures
            if pressure.ready_for_review
        )

    @property
    def blocking_pressure_ids(self) -> tuple[str, ...]:
        """Return pressure ids that block stronger claims."""

        return tuple(
            pressure.pressure_id
            for pressure in self.pressures
            if pressure.blocks_claim
        )

    @property
    def trial_recommending_pressure_ids(self) -> tuple[str, ...]:
        """Return pressure ids recommending bounded trials."""

        return tuple(
            pressure.pressure_id
            for pressure in self.pressures
            if pressure.recommends_trials
        )

    @property
    def evidence_ids(self) -> tuple[str, ...]:
        """Return all evidence ids bound to this report."""

        evidence: list[str] = []
        for pressure in self.pressures:
            evidence.extend(pressure.evidence_ids)
        return _normalize_unique_text_tuple(evidence, label="evidence_id")

    @property
    def ready_for_review(self) -> bool:
        """Return whether this report is ready for review."""

        return (
            self.decision is GoalPressureDecision.READY_FOR_REVIEW
            and bool(self.review_ready_pressure_ids)
            and not self.blocking_pressure_ids
        )

    @property
    def blocks_claim(self) -> bool:
        """Return whether this report blocks stronger goal claims."""

        return (
            self.decision is GoalPressureDecision.BLOCKED
            or bool(self.blocking_pressure_ids)
        )

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic goal-pressure-report payload."""

        return {
            "blocking_pressure_ids": list(self.blocking_pressure_ids),
            "decision": self.decision.value,
            "evidence_ids": list(self.evidence_ids),
            "notes": list(self.notes),
            "pressure_fingerprints": [
                pressure.fingerprint() for pressure in self.pressures
            ],
            "pressure_ids": list(self.pressure_ids),
            "report_id": self.report_id,
            "review_ready_pressure_ids": list(self.review_ready_pressure_ids),
            "schema_version": self.schema_version,
            "trial_recommending_pressure_ids": list(
                self.trial_recommending_pressure_ids
            ),
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this report."""

        return _stable_sha256(self.canonical_payload())


def assess_goal_pressure(
    *,
    pressure_id: str,
    goal: ResearchGoal,
    subgoals: Iterable[Subgoal],
    conflicts: Iterable[GoalConflict] = (),
    retirements: Iterable[GoalRetirement] = (),
    recommended_next_trial_ids: Iterable[str] = (),
    notes: Iterable[str] = (),
) -> GoalPressure:
    """Assess goal pressure with fail-closed defaults."""

    subgoal_tuple = tuple(subgoals)
    conflict_tuple = tuple(conflicts)
    retirement_tuple = tuple(retirements)

    temporary = GoalPressure(
        pressure_id=pressure_id,
        goal=goal,
        subgoals=subgoal_tuple,
        conflicts=conflict_tuple,
        retirements=retirement_tuple,
        decision=GoalPressureDecision.RECORD_ONLY,
        recommended_next_trial_ids=tuple(recommended_next_trial_ids),
        notes=tuple(notes),
    )
    if temporary.blocking_reason_ids:
        decision = GoalPressureDecision.BLOCKED
    elif goal.ready_for_review or any(
        subgoal.ready_for_review for subgoal in temporary.subgoals
    ):
        decision = GoalPressureDecision.READY_FOR_REVIEW
    elif not temporary.evidence_ids:
        decision = GoalPressureDecision.NEEDS_MORE_EVIDENCE
    else:
        decision = GoalPressureDecision.RECORD_ONLY

    return GoalPressure(
        pressure_id=pressure_id,
        goal=goal,
        subgoals=subgoal_tuple,
        conflicts=conflict_tuple,
        retirements=retirement_tuple,
        decision=decision,
        recommended_next_trial_ids=tuple(recommended_next_trial_ids),
        notes=tuple(notes),
    )


def build_goal_pressure_report(
    *,
    report_id: str,
    pressures: Iterable[GoalPressure],
    decision: GoalPressureDecision,
    notes: Iterable[str] = (),
) -> GoalPressureReport:
    """Build a deterministic Wave 7 goal pressure report."""

    return GoalPressureReport(
        report_id=report_id,
        pressures=tuple(pressures),
        decision=decision,
        notes=tuple(notes),
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
