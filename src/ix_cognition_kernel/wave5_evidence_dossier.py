"""Wave 5 evidence dossier compiler.

Wave 5 needs a single reviewable dossier that ties together the evidence families
built across the bridge into Wave 6. This module aggregates required evidence
sections, readiness-gate binding, integrity checks, and unresolved gaps while
preserving anti-overclaim boundaries. A complete dossier may become reviewable;
it cannot promote the project to Wave 6, claim AGI, grant execution authority,
or substitute internal evidence for independent validation.
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

WAVE_FIVE_DOSSIER_SECTION_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave5-dossier-section-v1"
)
WAVE_FIVE_DOSSIER_CHECK_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave5-dossier-integrity-check-v1"
)
WAVE_FIVE_DOSSIER_GAP_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave5-dossier-gap-v1"
)
WAVE_FIVE_EVIDENCE_DOSSIER_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave5-evidence-dossier-v1"
)


class WaveFiveDossierSectionKind(StrEnum):
    """Required sections in the Wave 5 evidence dossier."""

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
    WAVE_SIX_READINESS_GATE = "wave-six-readiness-gate"


class WaveFiveDossierSectionStatus(StrEnum):
    """Status of one dossier section."""

    REVIEWABLE = "reviewable"
    REVIEWABLE_WITH_LIMITS = "reviewable-with-limits"
    NEEDS_EXTERNAL_EVIDENCE = "needs-external-evidence"
    DISPUTED = "disputed"
    BLOCKED = "blocked"
    MISSING = "missing"


class WaveFiveDossierIntegrityCheckKind(StrEnum):
    """Integrity checks required for the compiled dossier."""

    REQUIRED_SECTIONS_PRESENT = "required-sections-present"
    SECTION_ARTIFACTS_PRESENT = "section-artifacts-present"
    SECTION_EVIDENCE_PRESENT = "section-evidence-present"
    READINESS_GATE_BOUND = "readiness-gate-bound"
    CLAIM_BOUNDARIES_PRESERVED = "claim-boundaries-preserved"
    HUMAN_AUTHORITY_PRESERVED = "human-authority-preserved"
    UNRESOLVED_GAPS_VISIBLE = "unresolved-gaps-visible"
    NO_WAVE_SIX_PROMOTION = "no-wave-six-promotion"
    NO_AGI_OR_CERTIFICATION_CLAIM = "no-agi-or-certification-claim"
    DETERMINISTIC_FINGERPRINT_PRESENT = "deterministic-fingerprint-present"


class WaveFiveDossierCheckResult(StrEnum):
    """Observed result for one dossier integrity check."""

    PASSED = "passed"
    PASSED_WITH_LIMITS = "passed-with-limits"
    NEEDS_MORE_EVIDENCE = "needs-more-evidence"
    FAILED = "failed"


class WaveFiveDossierGapKind(StrEnum):
    """Gap classes that must remain visible in the dossier."""

    MISSING_SECTION = "missing-section"
    MISSING_EVIDENCE = "missing-evidence"
    EXTERNAL_REVIEW_GAP = "external-review-gap"
    REPRODUCTION_GAP = "reproduction-gap"
    SAFETY_GAP = "safety-gap"
    AUTHORITY_GAP = "authority-gap"
    CLAIM_BOUNDARY_GAP = "claim-boundary-gap"
    WAVE_SIX_READINESS_GAP = "wave-six-readiness-gap"


class WaveFiveDossierGapSeverity(StrEnum):
    """Severity of a dossier gap."""

    INFORMATIONAL = "informational"
    LIMITATION = "limitation"
    NEEDS_MORE_EVIDENCE = "needs-more-evidence"
    BLOCKING = "blocking"


class WaveFiveDossierReviewState(StrEnum):
    """Review state of the compiled Wave 5 dossier."""

    INTERNAL_DOSSIER_READY = "internal-dossier-ready"
    READY_FOR_EXTERNAL_DOSSIER_REVIEW = "ready-for-external-dossier-review"
    UNDER_EXTERNAL_DOSSIER_REVIEW = "under-external-dossier-review"
    EXTERNALLY_REVIEWED_WITH_BOUNDARIES = "externally-reviewed-with-boundaries"
    BLOCKED_BY_DOSSIER_GAP = "blocked-by-dossier-gap"


REQUIRED_DOSSIER_SECTION_KINDS: tuple[WaveFiveDossierSectionKind, ...] = (
    WaveFiveDossierSectionKind.EXTERNAL_PROTOCOLS,
    WaveFiveDossierSectionKind.INDEPENDENT_REVIEWERS,
    WaveFiveDossierSectionKind.REPRODUCIBLE_EVIDENCE,
    WaveFiveDossierSectionKind.ADVERSARIAL_SAFETY,
    WaveFiveDossierSectionKind.LONG_HORIZON_VALIDATION,
    WaveFiveDossierSectionKind.CROSS_DOMAIN_TRANSFER,
    WaveFiveDossierSectionKind.BENCHMARK_GAMING_AUDIT,
    WaveFiveDossierSectionKind.MEMORY_INTEGRITY,
    WaveFiveDossierSectionKind.SAFE_REFUSAL,
    WaveFiveDossierSectionKind.HUMAN_AUTHORITY,
    WaveFiveDossierSectionKind.REPEATABILITY_LEDGER,
    WaveFiveDossierSectionKind.BLACKFOX_COMPATIBILITY,
    WaveFiveDossierSectionKind.WORLDTWIN_SCENARIOS,
    WaveFiveDossierSectionKind.WAVE_SIX_READINESS_GATE,
)

REQUIRED_DOSSIER_CHECK_KINDS: tuple[WaveFiveDossierIntegrityCheckKind, ...] = (
    WaveFiveDossierIntegrityCheckKind.REQUIRED_SECTIONS_PRESENT,
    WaveFiveDossierIntegrityCheckKind.SECTION_ARTIFACTS_PRESENT,
    WaveFiveDossierIntegrityCheckKind.SECTION_EVIDENCE_PRESENT,
    WaveFiveDossierIntegrityCheckKind.READINESS_GATE_BOUND,
    WaveFiveDossierIntegrityCheckKind.CLAIM_BOUNDARIES_PRESERVED,
    WaveFiveDossierIntegrityCheckKind.HUMAN_AUTHORITY_PRESERVED,
    WaveFiveDossierIntegrityCheckKind.UNRESOLVED_GAPS_VISIBLE,
    WaveFiveDossierIntegrityCheckKind.NO_WAVE_SIX_PROMOTION,
    WaveFiveDossierIntegrityCheckKind.NO_AGI_OR_CERTIFICATION_CLAIM,
    WaveFiveDossierIntegrityCheckKind.DETERMINISTIC_FINGERPRINT_PRESENT,
)

SAFE_DOSSIER_SECTION_STATUSES: tuple[WaveFiveDossierSectionStatus, ...] = (
    WaveFiveDossierSectionStatus.REVIEWABLE,
    WaveFiveDossierSectionStatus.REVIEWABLE_WITH_LIMITS,
)

BLOCKING_DOSSIER_SECTION_STATUSES: tuple[WaveFiveDossierSectionStatus, ...] = (
    WaveFiveDossierSectionStatus.NEEDS_EXTERNAL_EVIDENCE,
    WaveFiveDossierSectionStatus.DISPUTED,
    WaveFiveDossierSectionStatus.BLOCKED,
    WaveFiveDossierSectionStatus.MISSING,
)

EXTERNAL_DOSSIER_REVIEW_SOURCE_SYSTEMS: tuple[WaveFiveSourceSystem, ...] = (
    WaveFiveSourceSystem.EXTERNAL_REVIEW,
    WaveFiveSourceSystem.INDEPENDENT_REVIEWER,
    WaveFiveSourceSystem.HUMAN_REVIEW,
)


@dataclass(frozen=True, slots=True)
class WaveFiveDossierSection:
    """One required section in the compiled Wave 5 evidence dossier."""

    section_id: str
    section_kind: WaveFiveDossierSectionKind
    status: WaveFiveDossierSectionStatus
    artifact_ids: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    summary: str
    source_system: WaveFiveSourceSystem
    limitations: tuple[str, ...] = ()
    reviewer_ids: tuple[str, ...] = ()
    claim_boundaries: tuple[WaveFiveClaimBoundary, ...] = (
        WAVE_FIVE_REQUIRED_CLAIM_BOUNDARIES
    )
    schema_version: str = WAVE_FIVE_DOSSIER_SECTION_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate section identity, evidence binding, and boundaries."""

        object.__setattr__(self, "section_id", _text(self.section_id, "section_id"))
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
            raise ValueError("Dossier sections require artifact ids.")
        if not self.evidence_ids:
            raise ValueError("Dossier sections require evidence ids.")
        if self.status is WaveFiveDossierSectionStatus.REVIEWABLE_WITH_LIMITS:
            if not self.limitations:
                raise ValueError("Limited dossier sections require limitations.")
        missing = tuple(
            boundary
            for boundary in WAVE_FIVE_REQUIRED_CLAIM_BOUNDARIES
            if boundary not in self.claim_boundaries
        )
        if missing:
            raise ValueError(
                "Dossier sections must preserve claim boundary: "
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
    def blocks_dossier_readiness(self) -> bool:
        """Return whether this section blocks dossier review."""

        return self.status in BLOCKING_DOSSIER_SECTION_STATUSES

    @property
    def reviewable_with_boundaries(self) -> bool:
        """Return whether this section is reviewable without promotion."""

        return self.status in SAFE_DOSSIER_SECTION_STATUSES and bool(self.evidence_ids)

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic export payload."""

        return {
            "artifact_ids": list(self.artifact_ids),
            "claim_boundaries": [boundary.value for boundary in self.claim_boundaries],
            "evidence_ids": list(self.evidence_ids),
            "limitations": list(self.limitations),
            "reviewable_with_boundaries": self.reviewable_with_boundaries,
            "reviewer_ids": list(self.reviewer_ids),
            "schema_version": self.schema_version,
            "section_id": self.section_id,
            "section_kind": self.section_kind.value,
            "source_system": self.source_system.value,
            "status": self.status.value,
            "summary": self.summary,
        }


@dataclass(frozen=True, slots=True)
class WaveFiveDossierIntegrityCheck:
    """One integrity check over the compiled evidence dossier."""

    check_id: str
    check_kind: WaveFiveDossierIntegrityCheckKind
    result: WaveFiveDossierCheckResult
    description: str
    evidence_ids: tuple[str, ...]
    blocking: bool = True
    schema_version: str = WAVE_FIVE_DOSSIER_CHECK_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate dossier-check evidence."""

        object.__setattr__(self, "check_id", _text(self.check_id, "check_id"))
        object.__setattr__(self, "description", _text(self.description, "description"))
        object.__setattr__(
            self, "evidence_ids", _unique_text(self.evidence_ids, label="evidence_id")
        )
        if not self.evidence_ids:
            raise ValueError("Dossier integrity checks require evidence ids.")
        object.__setattr__(
            self, "schema_version", _text(self.schema_version, "schema_version")
        )

    @property
    def check_key(self) -> str:
        """Return deterministic check key."""

        return self.check_id

    @property
    def passed_with_boundaries(self) -> bool:
        """Return whether this check passed without erasing limitations."""

        return self.result in {
            WaveFiveDossierCheckResult.PASSED,
            WaveFiveDossierCheckResult.PASSED_WITH_LIMITS,
        }

    @property
    def blocks_dossier_readiness(self) -> bool:
        """Return whether this check blocks dossier review."""

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
class WaveFiveDossierGap:
    """Visible gap or limitation preserved inside the dossier."""

    gap_id: str
    gap_kind: WaveFiveDossierGapKind
    severity: WaveFiveDossierGapSeverity
    section_kind: WaveFiveDossierSectionKind
    description: str
    mitigation: str
    evidence_ids: tuple[str, ...]
    resolved: bool = False
    schema_version: str = WAVE_FIVE_DOSSIER_GAP_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate dossier-gap visibility and mitigation."""

        object.__setattr__(self, "gap_id", _text(self.gap_id, "gap_id"))
        object.__setattr__(self, "description", _text(self.description, "description"))
        object.__setattr__(self, "mitigation", _text(self.mitigation, "mitigation"))
        object.__setattr__(
            self, "evidence_ids", _unique_text(self.evidence_ids, label="evidence_id")
        )
        if not self.evidence_ids:
            raise ValueError("Dossier gaps require evidence ids.")
        object.__setattr__(
            self, "schema_version", _text(self.schema_version, "schema_version")
        )

    @property
    def gap_key(self) -> str:
        """Return deterministic gap key."""

        return self.gap_id

    @property
    def blocks_dossier_readiness(self) -> bool:
        """Return whether this unresolved gap blocks dossier review."""

        return (
            self.severity is WaveFiveDossierGapSeverity.BLOCKING
            and not self.resolved
        )

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic export payload."""

        return {
            "description": self.description,
            "evidence_ids": list(self.evidence_ids),
            "gap_id": self.gap_id,
            "gap_kind": self.gap_kind.value,
            "mitigation": self.mitigation,
            "resolved": self.resolved,
            "schema_version": self.schema_version,
            "section_kind": self.section_kind.value,
            "severity": self.severity.value,
        }


@dataclass(frozen=True, slots=True)
class WaveFiveEvidenceDossier:
    """Compiled Wave 5 evidence dossier for external review."""

    dossier_id: str
    title: str
    source_system: WaveFiveSourceSystem
    review_state: WaveFiveDossierReviewState
    sections: tuple[WaveFiveDossierSection, ...]
    integrity_checks: tuple[WaveFiveDossierIntegrityCheck, ...]
    gaps: tuple[WaveFiveDossierGap, ...]
    readiness_gate_artifact_id: str
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
    schema_version: str = WAVE_FIVE_EVIDENCE_DOSSIER_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate dossier completeness, gap handling, and claim boundaries."""

        object.__setattr__(self, "dossier_id", _text(self.dossier_id, "dossier_id"))
        object.__setattr__(self, "title", _text(self.title, "title"))
        object.__setattr__(
            self,
            "readiness_gate_artifact_id",
            _text(self.readiness_gate_artifact_id, "readiness_gate_artifact_id"),
        )
        if self.attempted_wave_six_promotion:
            raise ValueError("Evidence dossiers cannot promote to Wave 6.")
        if self.claims_agi:
            raise ValueError("Evidence dossiers cannot claim AGI.")
        if self.grants_execution_authority:
            raise ValueError("Evidence dossiers cannot grant execution authority.")
        if self.claims_production_ready:
            raise ValueError("Evidence dossiers cannot claim production readiness.")
        if self.claims_certified:
            raise ValueError("Evidence dossiers cannot claim certification.")
        sections = tuple(sorted(self.sections, key=lambda item: item.section_key))
        checks = tuple(
            sorted(self.integrity_checks, key=lambda item: item.check_key)
        )
        gaps = tuple(sorted(self.gaps, key=lambda item: item.gap_key))
        if not sections:
            raise ValueError("Evidence dossiers require sections.")
        if not checks:
            raise ValueError("Evidence dossiers require integrity checks.")
        _unique_values((item.section_id for item in sections), label="section_id")
        _unique_values((item.section_kind for item in sections), label="section kind")
        _unique_values((item.check_id for item in checks), label="check_id")
        _unique_values((item.gap_id for item in gaps), label="gap_id")
        object.__setattr__(self, "sections", sections)
        object.__setattr__(self, "integrity_checks", checks)
        object.__setattr__(self, "gaps", gaps)
        object.__setattr__(
            self, "protocol_ids", _unique_text(self.protocol_ids, label="protocol_id")
        )
        if not self.protocol_ids:
            raise ValueError("Evidence dossiers require protocol ids.")
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
                "Evidence dossiers must preserve claim boundary: "
                f"{missing_boundaries[0].value}"
            )
        object.__setattr__(self, "notes", _unique_text(self.notes, label="note"))
        object.__setattr__(
            self, "schema_version", _text(self.schema_version, "schema_version")
        )
        if self.externally_reviewed_with_boundaries:
            if self.source_system not in EXTERNAL_DOSSIER_REVIEW_SOURCE_SYSTEMS:
                raise ValueError(
                    "Externally reviewed dossiers require external source."
                )
            if not self.reviewer_ids:
                raise ValueError(
                    "Externally reviewed dossiers require reviewer ids."
                )
            if self.blocks_dossier_readiness:
                raise ValueError(
                    "Externally reviewed dossiers cannot contain blockers."
                )

    @property
    def covered_section_kinds(self) -> tuple[WaveFiveDossierSectionKind, ...]:
        """Return dossier section kinds represented in this dossier."""

        return tuple(section.section_kind for section in self.sections)

    @property
    def missing_required_section_kinds(self) -> tuple[WaveFiveDossierSectionKind, ...]:
        """Return required dossier sections absent from this dossier."""

        covered = set(self.covered_section_kinds)
        return tuple(
            kind for kind in REQUIRED_DOSSIER_SECTION_KINDS if kind not in covered
        )

    @property
    def covered_check_kinds(self) -> tuple[WaveFiveDossierIntegrityCheckKind, ...]:
        """Return integrity check kinds represented in this dossier."""

        kinds: list[WaveFiveDossierIntegrityCheckKind] = []
        seen: set[WaveFiveDossierIntegrityCheckKind] = set()
        for check in self.integrity_checks:
            if check.check_kind not in seen:
                kinds.append(check.check_kind)
                seen.add(check.check_kind)
        return tuple(kinds)

    @property
    def missing_required_check_kinds(
        self,
    ) -> tuple[WaveFiveDossierIntegrityCheckKind, ...]:
        """Return required dossier checks absent from this dossier."""

        covered = set(self.covered_check_kinds)
        return tuple(
            kind for kind in REQUIRED_DOSSIER_CHECK_KINDS if kind not in covered
        )

    @property
    def blocking_section_ids(self) -> tuple[str, ...]:
        """Return dossier sections that block dossier readiness."""

        return tuple(
            section.section_id
            for section in self.sections
            if section.blocks_dossier_readiness
        )

    @property
    def blocking_check_ids(self) -> tuple[str, ...]:
        """Return integrity checks that block dossier readiness."""

        return tuple(
            check.check_id
            for check in self.integrity_checks
            if check.blocks_dossier_readiness
        )

    @property
    def unresolved_gap_ids(self) -> tuple[str, ...]:
        """Return unresolved blocking dossier gaps."""

        return tuple(gap.gap_id for gap in self.gaps if gap.blocks_dossier_readiness)

    @property
    def has_required_section_coverage(self) -> bool:
        """Return whether every locked dossier section is represented."""

        return not self.missing_required_section_kinds

    @property
    def has_required_check_coverage(self) -> bool:
        """Return whether every locked dossier check is represented."""

        return not self.missing_required_check_kinds

    @property
    def makes_no_forbidden_claims(self) -> bool:
        """Return whether dossier avoids forbidden Wave 6 and AGI claims."""

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
    def blocks_dossier_readiness(self) -> bool:
        """Return whether any condition blocks dossier review."""

        return bool(
            self.missing_required_section_kinds
            or self.missing_required_check_kinds
            or self.blocking_section_ids
            or self.blocking_check_ids
            or self.unresolved_gap_ids
            or not self.makes_no_forbidden_claims
        )

    @property
    def ready_for_external_dossier_review(self) -> bool:
        """Return whether dossier can enter external review."""

        return (
            self.review_state
            in {
                WaveFiveDossierReviewState.INTERNAL_DOSSIER_READY,
                WaveFiveDossierReviewState.READY_FOR_EXTERNAL_DOSSIER_REVIEW,
                WaveFiveDossierReviewState.UNDER_EXTERNAL_DOSSIER_REVIEW,
            }
            and self.has_required_section_coverage
            and self.has_required_check_coverage
            and not self.blocking_section_ids
            and not self.blocking_check_ids
            and not self.unresolved_gap_ids
            and self.makes_no_forbidden_claims
        )

    @property
    def externally_reviewed_with_boundaries(self) -> bool:
        """Return whether external dossier review accepted boundaries."""

        return (
            self.review_state
            is WaveFiveDossierReviewState.EXTERNALLY_REVIEWED_WITH_BOUNDARIES
        )

    @property
    def all_evidence_ids(self) -> tuple[str, ...]:
        """Return all evidence ids bound into this dossier."""

        evidence_ids: list[str] = []
        seen: set[str] = set()
        for evidence_id in self._iter_evidence_ids():
            if evidence_id not in seen:
                evidence_ids.append(evidence_id)
                seen.add(evidence_id)
        return tuple(evidence_ids)

    def to_artifact_ref(self) -> WaveFiveArtifactRef:
        """Return this dossier as a Wave 5 traceability artifact."""

        decision = WaveFiveArtifactDecision.NEEDS_EXTERNAL_EVIDENCE
        status = WaveFiveValidationStatus.MISSING_EXTERNAL_EVIDENCE
        authority = WaveFiveAuthorityState.HUMAN_REVIEW_REQUIRED
        if self.externally_reviewed_with_boundaries:
            decision = WaveFiveArtifactDecision.EXTERNALLY_REVIEWED
            status = WaveFiveValidationStatus.ACCEPTED_WITH_BOUNDARIES
        elif self.ready_for_external_dossier_review:
            decision = WaveFiveArtifactDecision.READY_FOR_INDEPENDENT_REVIEW
            status = WaveFiveValidationStatus.UNDER_INDEPENDENT_REVIEW
        elif self.blocks_dossier_readiness:
            decision = WaveFiveArtifactDecision.BLOCKED
            status = WaveFiveValidationStatus.REJECTED
            authority = WaveFiveAuthorityState.BLOCKED
        return WaveFiveArtifactRef(
            artifact_id=self.dossier_id,
            kind=WaveFiveArtifactKind.ECOSYSTEM_TRACEABILITY_MAP,
            capability_area=WaveFiveCapabilityArea.ECOSYSTEM_TRACEABILITY,
            source_system=self.source_system,
            summary=self.title,
            produced_by_engine_id="wave5-evidence-dossier-compiler",
            produced_by_agent_role_id="evidence-dossier-reviewer",
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
            "claim_boundaries": [boundary.value for boundary in self.claim_boundaries],
            "claims_agi": self.claims_agi,
            "claims_certified": self.claims_certified,
            "claims_production_ready": self.claims_production_ready,
            "dossier_id": self.dossier_id,
            "gaps": [gap.canonical_payload() for gap in self.gaps],
            "grants_execution_authority": self.grants_execution_authority,
            "integrity_checks": [
                check.canonical_payload() for check in self.integrity_checks
            ],
            "notes": list(self.notes),
            "protocol_ids": list(self.protocol_ids),
            "readiness_gate_artifact_id": self.readiness_gate_artifact_id,
            "review_state": self.review_state.value,
            "reviewer_ids": list(self.reviewer_ids),
            "schema_version": self.schema_version,
            "sections": [section.canonical_payload() for section in self.sections],
            "source_system": self.source_system.value,
            "title": self.title,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this dossier."""

        return _stable_sha256(self.canonical_payload())

    def _iter_evidence_ids(self) -> Iterable[str]:
        """Yield evidence ids in deterministic dossier traversal order."""

        for section in self.sections:
            yield from section.evidence_ids
        for check in self.integrity_checks:
            yield from check.evidence_ids
        for gap in self.gaps:
            yield from gap.evidence_ids


def required_dossier_section_kinds() -> tuple[WaveFiveDossierSectionKind, ...]:
    """Return locked dossier sections required for Wave 5 compilation."""

    return REQUIRED_DOSSIER_SECTION_KINDS


def required_dossier_check_kinds() -> tuple[WaveFiveDossierIntegrityCheckKind, ...]:
    """Return locked dossier checks required for Wave 5 compilation."""

    return REQUIRED_DOSSIER_CHECK_KINDS


def safe_dossier_section_statuses() -> tuple[WaveFiveDossierSectionStatus, ...]:
    """Return dossier statuses that do not block external review."""

    return SAFE_DOSSIER_SECTION_STATUSES


def blocking_dossier_section_statuses() -> tuple[WaveFiveDossierSectionStatus, ...]:
    """Return dossier statuses that block external review."""

    return BLOCKING_DOSSIER_SECTION_STATUSES


def external_dossier_review_source_systems() -> tuple[WaveFiveSourceSystem, ...]:
    """Return source systems allowed to assert external dossier review."""

    return EXTERNAL_DOSSIER_REVIEW_SOURCE_SYSTEMS


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
