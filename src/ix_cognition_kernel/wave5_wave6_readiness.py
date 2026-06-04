"""Wave 5 to Wave 6 readiness gate records.

Wave 5 is only useful as a bridge if Wave 6 cannot be started from incomplete,
self-validating, or overclaimed evidence. This module records the required
Wave 5 evidence families, readiness checks, unresolved blockers, and explicit
non-promotion boundaries. Passing this gate can make a Wave 6 design review
eligible to begin; it cannot declare Wave 6, AGI, production readiness,
certification, autonomous authority, or independent validation.
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

WAVE_FIVE_READINESS_FAMILY_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave5-readiness-family-v1"
)
WAVE_FIVE_READINESS_CHECK_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave5-readiness-check-v1"
)
WAVE_FIVE_READINESS_BLOCKER_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave5-readiness-blocker-v1"
)
WAVE_FIVE_WAVE_SIX_READINESS_GATE_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave5-wave6-readiness-gate-v1"
)


class WaveFiveReadinessFamily(StrEnum):
    """Evidence families required before Wave 6 design review can begin."""

    EXTERNAL_PROTOCOLS = "external-protocols"
    INDEPENDENT_REVIEWERS = "independent-reviewers"
    REPRODUCIBLE_EVIDENCE = "reproducible-evidence"
    ADVERSARIAL_SAFETY = "adversarial-safety"
    LONG_HORIZON_VALIDATION = "long-horizon-validation"
    CROSS_DOMAIN_TRANSFER = "cross-domain-transfer"
    BENCHMARK_GAMING_AUDIT = "benchmark-gaming-audit"
    MEMORY_INTEGRITY = "memory-integrity"
    SAFE_REFUSAL = "safe-refusal"
    HUMAN_AUTHORITY = "human-authority"
    REPEATABILITY_LEDGER = "repeatability-ledger"
    BLACKFOX_COMPATIBILITY = "blackfox-compatibility"
    WORLDTWIN_SCENARIOS = "worldtwin-scenarios"


class WaveFiveReadinessStatus(StrEnum):
    """Status of one Wave 5 evidence family."""

    SATISFIED = "satisfied"
    SATISFIED_WITH_LIMITS = "satisfied-with-limits"
    NEEDS_EXTERNAL_EVIDENCE = "needs-external-evidence"
    DISPUTED = "disputed"
    BLOCKED = "blocked"
    MISSING = "missing"


class WaveFiveReadinessCheckKind(StrEnum):
    """Checks required before a Wave 6 design review is allowed."""

    ARTIFACTS_PRESENT = "artifacts-present"
    EVIDENCE_IDS_PRESENT = "evidence-ids-present"
    CLAIM_BOUNDARIES_PRESERVED = "claim-boundaries-preserved"
    HUMAN_AUTHORITY_PRESERVED = "human-authority-preserved"
    EXTERNAL_REVIEW_PATH_PRESENT = "external-review-path-present"
    BLOCKER_SCAN_COMPLETE = "blocker-scan-complete"
    NO_AGI_CLAIM = "no-agi-claim"
    NO_EXECUTION_AUTHORITY = "no-execution-authority"
    NO_PRODUCTION_OR_CERTIFICATION_CLAIM = "no-production-or-certification-claim"
    WAVE_SIX_SCOPE_BOUND = "wave-six-scope-bound"


class WaveFiveReadinessCheckResult(StrEnum):
    """Observed result of one Wave 6 readiness check."""

    PASSED = "passed"
    PASSED_WITH_LIMITS = "passed-with-limits"
    NEEDS_MORE_EVIDENCE = "needs-more-evidence"
    FAILED = "failed"


class WaveFiveReadinessBlockerKind(StrEnum):
    """Blocker classes that prevent Wave 6 work from starting cleanly."""

    MISSING_EVIDENCE_FAMILY = "missing-evidence-family"
    FAILED_REPRODUCTION = "failed-reproduction"
    UNRESOLVED_DISAGREEMENT = "unresolved-disagreement"
    AUTHORITY_GAP = "authority-gap"
    UNSAFE_REFUSAL_GAP = "unsafe-refusal-gap"
    MEMORY_INTEGRITY_GAP = "memory-integrity-gap"
    BENCHMARK_OVERCLAIM_GAP = "benchmark-overclaim-gap"
    SCENARIO_OVERCLAIM_GAP = "scenario-overclaim-gap"
    BLACKFOX_HANDOFF_GAP = "blackfox-handoff-gap"
    CLAIM_BOUNDARY_GAP = "claim-boundary-gap"


class WaveFiveReadinessReviewState(StrEnum):
    """Review state of the Wave 5 to Wave 6 readiness gate."""

    INTERNAL_GATE_READY = "internal-gate-ready"
    READY_FOR_WAVE_SIX_DESIGN_REVIEW = "ready-for-wave-six-design-review"
    UNDER_WAVE_SIX_READINESS_REVIEW = "under-wave-six-readiness-review"
    EXTERNALLY_REVIEWED_WITH_BOUNDARIES = "externally-reviewed-with-boundaries"
    BLOCKED_BEFORE_WAVE_SIX = "blocked-before-wave-six"


SAFE_READINESS_STATUSES: tuple[WaveFiveReadinessStatus, ...] = (
    WaveFiveReadinessStatus.SATISFIED,
    WaveFiveReadinessStatus.SATISFIED_WITH_LIMITS,
)

BLOCKING_READINESS_STATUSES: tuple[WaveFiveReadinessStatus, ...] = (
    WaveFiveReadinessStatus.NEEDS_EXTERNAL_EVIDENCE,
    WaveFiveReadinessStatus.DISPUTED,
    WaveFiveReadinessStatus.BLOCKED,
    WaveFiveReadinessStatus.MISSING,
)

REQUIRED_READINESS_FAMILIES: tuple[WaveFiveReadinessFamily, ...] = (
    WaveFiveReadinessFamily.EXTERNAL_PROTOCOLS,
    WaveFiveReadinessFamily.INDEPENDENT_REVIEWERS,
    WaveFiveReadinessFamily.REPRODUCIBLE_EVIDENCE,
    WaveFiveReadinessFamily.ADVERSARIAL_SAFETY,
    WaveFiveReadinessFamily.LONG_HORIZON_VALIDATION,
    WaveFiveReadinessFamily.CROSS_DOMAIN_TRANSFER,
    WaveFiveReadinessFamily.BENCHMARK_GAMING_AUDIT,
    WaveFiveReadinessFamily.MEMORY_INTEGRITY,
    WaveFiveReadinessFamily.SAFE_REFUSAL,
    WaveFiveReadinessFamily.HUMAN_AUTHORITY,
    WaveFiveReadinessFamily.REPEATABILITY_LEDGER,
    WaveFiveReadinessFamily.BLACKFOX_COMPATIBILITY,
    WaveFiveReadinessFamily.WORLDTWIN_SCENARIOS,
)

REQUIRED_READINESS_CHECKS: tuple[WaveFiveReadinessCheckKind, ...] = (
    WaveFiveReadinessCheckKind.ARTIFACTS_PRESENT,
    WaveFiveReadinessCheckKind.EVIDENCE_IDS_PRESENT,
    WaveFiveReadinessCheckKind.CLAIM_BOUNDARIES_PRESERVED,
    WaveFiveReadinessCheckKind.HUMAN_AUTHORITY_PRESERVED,
    WaveFiveReadinessCheckKind.EXTERNAL_REVIEW_PATH_PRESENT,
    WaveFiveReadinessCheckKind.BLOCKER_SCAN_COMPLETE,
    WaveFiveReadinessCheckKind.NO_AGI_CLAIM,
    WaveFiveReadinessCheckKind.NO_EXECUTION_AUTHORITY,
    WaveFiveReadinessCheckKind.NO_PRODUCTION_OR_CERTIFICATION_CLAIM,
    WaveFiveReadinessCheckKind.WAVE_SIX_SCOPE_BOUND,
)

EXTERNAL_READINESS_REVIEW_SOURCE_SYSTEMS: tuple[WaveFiveSourceSystem, ...] = (
    WaveFiveSourceSystem.EXTERNAL_REVIEW,
    WaveFiveSourceSystem.INDEPENDENT_REVIEWER,
    WaveFiveSourceSystem.HUMAN_REVIEW,
)


@dataclass(frozen=True, slots=True)
class WaveFiveReadinessEvidenceFamilyRecord:
    """One required Wave 5 evidence family bound to reviewable artifacts."""

    family_id: str
    family: WaveFiveReadinessFamily
    status: WaveFiveReadinessStatus
    artifact_ids: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    source_system: WaveFiveSourceSystem
    summary: str
    limitations: tuple[str, ...] = ()
    reviewer_ids: tuple[str, ...] = ()
    claim_boundaries: tuple[WaveFiveClaimBoundary, ...] = (
        WAVE_FIVE_REQUIRED_CLAIM_BOUNDARIES
    )
    schema_version: str = WAVE_FIVE_READINESS_FAMILY_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate family record evidence and claim boundaries."""

        object.__setattr__(self, "family_id", _text(self.family_id, "family_id"))
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
            self, "reviewer_ids", _unique_text(self.reviewer_ids, label="reviewer_id")
        )
        object.__setattr__(
            self,
            "claim_boundaries",
            _unique_enum(self.claim_boundaries, label="claim boundary"),
        )
        if not self.artifact_ids:
            raise ValueError("Readiness family records require artifact ids.")
        if not self.evidence_ids:
            raise ValueError("Readiness family records require evidence ids.")
        if self.status is WaveFiveReadinessStatus.SATISFIED_WITH_LIMITS:
            if not self.limitations:
                raise ValueError("Limited readiness families require limitations.")
        missing_boundaries = tuple(
            boundary
            for boundary in WAVE_FIVE_REQUIRED_CLAIM_BOUNDARIES
            if boundary not in self.claim_boundaries
        )
        if missing_boundaries:
            raise ValueError(
                "Readiness family records must preserve claim boundary: "
                f"{missing_boundaries[0].value}"
            )
        object.__setattr__(
            self, "schema_version", _text(self.schema_version, "schema_version")
        )

    @property
    def family_key(self) -> str:
        """Return deterministic family key."""

        return self.family_id

    @property
    def blocks_wave_six_entry(self) -> bool:
        """Return whether this family blocks Wave 6 design review."""

        return self.status in BLOCKING_READINESS_STATUSES

    @property
    def reviewable_with_boundaries(self) -> bool:
        """Return whether this family is reviewable without promotion."""

        return self.status in SAFE_READINESS_STATUSES and bool(self.evidence_ids)

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic export payload."""

        return {
            "artifact_ids": list(self.artifact_ids),
            "claim_boundaries": [boundary.value for boundary in self.claim_boundaries],
            "evidence_ids": list(self.evidence_ids),
            "family": self.family.value,
            "family_id": self.family_id,
            "limitations": list(self.limitations),
            "reviewable_with_boundaries": self.reviewable_with_boundaries,
            "reviewer_ids": list(self.reviewer_ids),
            "schema_version": self.schema_version,
            "source_system": self.source_system.value,
            "status": self.status.value,
            "summary": self.summary,
        }


@dataclass(frozen=True, slots=True)
class WaveFiveReadinessGateCheck:
    """One gate check required before Wave 6 design review can begin."""

    check_id: str
    check_kind: WaveFiveReadinessCheckKind
    result: WaveFiveReadinessCheckResult
    description: str
    evidence_ids: tuple[str, ...]
    blocking: bool = True
    schema_version: str = WAVE_FIVE_READINESS_CHECK_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate readiness-check evidence."""

        object.__setattr__(self, "check_id", _text(self.check_id, "check_id"))
        object.__setattr__(self, "description", _text(self.description, "description"))
        object.__setattr__(
            self, "evidence_ids", _unique_text(self.evidence_ids, label="evidence_id")
        )
        if not self.evidence_ids:
            raise ValueError("Readiness checks require evidence ids.")
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
            WaveFiveReadinessCheckResult.PASSED,
            WaveFiveReadinessCheckResult.PASSED_WITH_LIMITS,
        }

    @property
    def blocks_wave_six_entry(self) -> bool:
        """Return whether this check blocks Wave 6 design review."""

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
class WaveFiveWaveSixReadinessBlocker:
    """One blocker that must be resolved before Wave 6 work can start."""

    blocker_id: str
    blocker_kind: WaveFiveReadinessBlockerKind
    family: WaveFiveReadinessFamily
    description: str
    mitigation: str
    evidence_ids: tuple[str, ...]
    resolved: bool = False
    blocking: bool = True
    schema_version: str = WAVE_FIVE_READINESS_BLOCKER_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate blocker visibility and mitigation."""

        object.__setattr__(self, "blocker_id", _text(self.blocker_id, "blocker_id"))
        object.__setattr__(self, "description", _text(self.description, "description"))
        object.__setattr__(self, "mitigation", _text(self.mitigation, "mitigation"))
        object.__setattr__(
            self, "evidence_ids", _unique_text(self.evidence_ids, label="evidence_id")
        )
        if not self.evidence_ids:
            raise ValueError("Wave 6 readiness blockers require evidence ids.")
        object.__setattr__(
            self, "schema_version", _text(self.schema_version, "schema_version")
        )

    @property
    def blocker_key(self) -> str:
        """Return deterministic blocker key."""

        return self.blocker_id

    @property
    def blocks_wave_six_entry(self) -> bool:
        """Return whether this blocker prevents Wave 6 design review."""

        return self.blocking and not self.resolved

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic export payload."""

        return {
            "blocker_id": self.blocker_id,
            "blocker_kind": self.blocker_kind.value,
            "blocking": self.blocking,
            "description": self.description,
            "evidence_ids": list(self.evidence_ids),
            "family": self.family.value,
            "mitigation": self.mitigation,
            "resolved": self.resolved,
            "schema_version": self.schema_version,
        }


@dataclass(frozen=True, slots=True)
class WaveFiveWaveSixReadinessGate:
    """Fail-closed bridge from complete Wave 5 evidence into Wave 6 design review."""

    gate_id: str
    title: str
    source_system: WaveFiveSourceSystem
    review_state: WaveFiveReadinessReviewState
    evidence_families: tuple[WaveFiveReadinessEvidenceFamilyRecord, ...]
    checks: tuple[WaveFiveReadinessGateCheck, ...]
    blockers: tuple[WaveFiveWaveSixReadinessBlocker, ...]
    protocol_ids: tuple[str, ...]
    reviewer_ids: tuple[str, ...] = ()
    attempted_wave_six_promotion: bool = False
    claims_agi: bool = False
    grants_execution_authority: bool = False
    claims_production_ready: bool = False
    claims_certified: bool = False
    claim_boundaries: tuple[WaveFiveClaimBoundary, ...] = (
        WAVE_FIVE_REQUIRED_CLAIM_BOUNDARIES
    )
    notes: tuple[str, ...] = ()
    schema_version: str = WAVE_FIVE_WAVE_SIX_READINESS_GATE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate readiness family coverage and anti-promotion boundaries."""

        object.__setattr__(self, "gate_id", _text(self.gate_id, "gate_id"))
        object.__setattr__(self, "title", _text(self.title, "title"))
        if self.attempted_wave_six_promotion:
            raise ValueError("Wave 5 readiness gates cannot promote to Wave 6.")
        if self.claims_agi:
            raise ValueError("Wave 5 readiness gates cannot claim AGI.")
        if self.grants_execution_authority:
            raise ValueError("Wave 5 readiness gates cannot grant execution.")
        if self.claims_production_ready:
            raise ValueError(
                "Wave 5 readiness gates cannot claim production readiness."
            )
        if self.claims_certified:
            raise ValueError("Wave 5 readiness gates cannot claim certification.")
        families = tuple(
            sorted(self.evidence_families, key=lambda item: item.family_key)
        )
        checks = tuple(sorted(self.checks, key=lambda item: item.check_key))
        blockers = tuple(sorted(self.blockers, key=lambda item: item.blocker_key))
        if not families:
            raise ValueError("Wave 6 readiness gates require evidence families.")
        if not checks:
            raise ValueError("Wave 6 readiness gates require checks.")
        _unique_values((item.family_id for item in families), label="family_id")
        _unique_values((item.family for item in families), label="readiness family")
        _unique_values((item.check_id for item in checks), label="check_id")
        _unique_values((item.blocker_id for item in blockers), label="blocker_id")
        object.__setattr__(self, "evidence_families", families)
        object.__setattr__(self, "checks", checks)
        object.__setattr__(self, "blockers", blockers)
        object.__setattr__(
            self, "protocol_ids", _unique_text(self.protocol_ids, label="protocol_id")
        )
        if not self.protocol_ids:
            raise ValueError("Wave 6 readiness gates require protocol ids.")
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
                "Wave 6 readiness gates must preserve claim boundary: "
                f"{missing_boundaries[0].value}"
            )
        object.__setattr__(self, "notes", _unique_text(self.notes, label="note"))
        object.__setattr__(
            self, "schema_version", _text(self.schema_version, "schema_version")
        )
        if self.externally_reviewed_with_boundaries:
            if self.source_system not in EXTERNAL_READINESS_REVIEW_SOURCE_SYSTEMS:
                raise ValueError(
                    "Externally reviewed readiness gates require external source."
                )
            if not self.reviewer_ids:
                raise ValueError(
                    "Externally reviewed readiness gates require reviewer ids."
                )
            if self.blocks_wave_six_design_review:
                raise ValueError(
                    "Externally reviewed readiness gates cannot contain blockers."
                )

    @property
    def covered_families(self) -> tuple[WaveFiveReadinessFamily, ...]:
        """Return readiness families represented in this gate."""

        return tuple(family.family for family in self.evidence_families)

    @property
    def missing_required_families(self) -> tuple[WaveFiveReadinessFamily, ...]:
        """Return required Wave 5 families absent from this gate."""

        covered = set(self.covered_families)
        return tuple(
            family for family in REQUIRED_READINESS_FAMILIES if family not in covered
        )

    @property
    def covered_check_kinds(self) -> tuple[WaveFiveReadinessCheckKind, ...]:
        """Return readiness check kinds represented in this gate."""

        kinds: list[WaveFiveReadinessCheckKind] = []
        seen: set[WaveFiveReadinessCheckKind] = set()
        for check in self.checks:
            if check.check_kind not in seen:
                kinds.append(check.check_kind)
                seen.add(check.check_kind)
        return tuple(kinds)

    @property
    def missing_required_check_kinds(self) -> tuple[WaveFiveReadinessCheckKind, ...]:
        """Return required readiness checks absent from this gate."""

        covered = set(self.covered_check_kinds)
        return tuple(kind for kind in REQUIRED_READINESS_CHECKS if kind not in covered)

    @property
    def blocking_family_ids(self) -> tuple[str, ...]:
        """Return family records that block Wave 6 design review."""

        return tuple(
            family.family_id
            for family in self.evidence_families
            if family.blocks_wave_six_entry
        )

    @property
    def blocking_check_ids(self) -> tuple[str, ...]:
        """Return checks that block Wave 6 design review."""

        return tuple(
            check.check_id for check in self.checks if check.blocks_wave_six_entry
        )

    @property
    def unresolved_blocker_ids(self) -> tuple[str, ...]:
        """Return unresolved blockers that prevent Wave 6 design review."""

        return tuple(
            blocker.blocker_id for blocker in self.blockers
            if blocker.blocks_wave_six_entry
        )

    @property
    def has_required_family_coverage(self) -> bool:
        """Return whether every locked Wave 5 family is represented."""

        return not self.missing_required_families

    @property
    def has_required_check_coverage(self) -> bool:
        """Return whether every locked readiness check is represented."""

        return not self.missing_required_check_kinds

    @property
    def makes_no_forbidden_claims(self) -> bool:
        """Return whether the gate avoids forbidden maturity/authority claims."""

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
    def blocks_wave_six_design_review(self) -> bool:
        """Return whether any condition blocks Wave 6 design review."""

        return bool(
            self.missing_required_families
            or self.missing_required_check_kinds
            or self.blocking_family_ids
            or self.blocking_check_ids
            or self.unresolved_blocker_ids
            or not self.makes_no_forbidden_claims
        )

    @property
    def ready_for_wave_six_design_review(self) -> bool:
        """Return whether Wave 6 design work may begin under review."""

        return (
            self.review_state
            in {
                WaveFiveReadinessReviewState.INTERNAL_GATE_READY,
                WaveFiveReadinessReviewState.READY_FOR_WAVE_SIX_DESIGN_REVIEW,
                WaveFiveReadinessReviewState.UNDER_WAVE_SIX_READINESS_REVIEW,
            }
            and self.has_required_family_coverage
            and self.has_required_check_coverage
            and not self.blocking_family_ids
            and not self.blocking_check_ids
            and not self.unresolved_blocker_ids
            and self.makes_no_forbidden_claims
        )

    @property
    def externally_reviewed_with_boundaries(self) -> bool:
        """Return whether external readiness review accepted boundaries."""

        return (
            self.review_state
            is WaveFiveReadinessReviewState.EXTERNALLY_REVIEWED_WITH_BOUNDARIES
        )

    @property
    def all_evidence_ids(self) -> tuple[str, ...]:
        """Return all evidence ids bound into the readiness gate."""

        evidence_ids: list[str] = []
        seen: set[str] = set()
        for evidence_id in self._iter_evidence_ids():
            if evidence_id not in seen:
                evidence_ids.append(evidence_id)
                seen.add(evidence_id)
        return tuple(evidence_ids)

    def to_artifact_ref(self) -> WaveFiveArtifactRef:
        """Return this gate as a Wave 5 ecosystem traceability artifact."""

        decision = WaveFiveArtifactDecision.NEEDS_EXTERNAL_EVIDENCE
        status = WaveFiveValidationStatus.MISSING_EXTERNAL_EVIDENCE
        authority = WaveFiveAuthorityState.HUMAN_REVIEW_REQUIRED
        if self.externally_reviewed_with_boundaries:
            decision = WaveFiveArtifactDecision.EXTERNALLY_REVIEWED
            status = WaveFiveValidationStatus.ACCEPTED_WITH_BOUNDARIES
        elif self.ready_for_wave_six_design_review:
            decision = WaveFiveArtifactDecision.READY_FOR_INDEPENDENT_REVIEW
            status = WaveFiveValidationStatus.UNDER_INDEPENDENT_REVIEW
        elif self.blocks_wave_six_design_review:
            decision = WaveFiveArtifactDecision.BLOCKED
            status = WaveFiveValidationStatus.REJECTED
            authority = WaveFiveAuthorityState.BLOCKED
        return WaveFiveArtifactRef(
            artifact_id=self.gate_id,
            kind=WaveFiveArtifactKind.ECOSYSTEM_TRACEABILITY_MAP,
            capability_area=WaveFiveCapabilityArea.ECOSYSTEM_TRACEABILITY,
            source_system=self.source_system,
            summary=self.title,
            produced_by_engine_id="wave5-wave6-readiness-gate",
            produced_by_agent_role_id="wave-six-readiness-reviewer",
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
            "blockers": [blocker.canonical_payload() for blocker in self.blockers],
            "checks": [check.canonical_payload() for check in self.checks],
            "claim_boundaries": [boundary.value for boundary in self.claim_boundaries],
            "claims_agi": self.claims_agi,
            "claims_certified": self.claims_certified,
            "claims_production_ready": self.claims_production_ready,
            "evidence_families": [
                family.canonical_payload() for family in self.evidence_families
            ],
            "gate_id": self.gate_id,
            "grants_execution_authority": self.grants_execution_authority,
            "notes": list(self.notes),
            "protocol_ids": list(self.protocol_ids),
            "review_state": self.review_state.value,
            "reviewer_ids": list(self.reviewer_ids),
            "schema_version": self.schema_version,
            "source_system": self.source_system.value,
            "title": self.title,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this readiness gate."""

        return _stable_sha256(self.canonical_payload())

    def _iter_evidence_ids(self) -> Iterable[str]:
        """Yield evidence ids in deterministic readiness-gate order."""

        for family in self.evidence_families:
            yield from family.evidence_ids
        for check in self.checks:
            yield from check.evidence_ids
        for blocker in self.blockers:
            yield from blocker.evidence_ids


def required_readiness_families() -> tuple[WaveFiveReadinessFamily, ...]:
    """Return locked Wave 5 evidence families required before Wave 6."""

    return REQUIRED_READINESS_FAMILIES


def required_readiness_checks() -> tuple[WaveFiveReadinessCheckKind, ...]:
    """Return locked checks required before Wave 6 design review."""

    return REQUIRED_READINESS_CHECKS


def safe_readiness_statuses() -> tuple[WaveFiveReadinessStatus, ...]:
    """Return readiness statuses that do not block Wave 6 design review."""

    return SAFE_READINESS_STATUSES


def blocking_readiness_statuses() -> tuple[WaveFiveReadinessStatus, ...]:
    """Return readiness statuses that block Wave 6 design review."""

    return BLOCKING_READINESS_STATUSES


def external_readiness_review_source_systems() -> tuple[WaveFiveSourceSystem, ...]:
    """Return source systems allowed to assert external readiness review."""

    return EXTERNAL_READINESS_REVIEW_SOURCE_SYSTEMS


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
