"""Wave 5 benchmark-gaming and contamination audit records.

Wave 5 cannot treat benchmark success, cherry-picked examples, memorized tasks,
or metric-optimized behavior as evidence of general intelligence. This module
records benchmark provenance, contamination risks, negative controls, failed-case
retention, metric-gaming checks, and claim-boundary controls. The audit can make
an artifact reviewable only when benchmark evidence is bounded, evidence-linked,
externally reviewable, and explicitly insufficient by itself for Wave 6 or AGI.
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

WAVE_FIVE_BENCHMARK_SOURCE_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave5-benchmark-source-v1"
)
WAVE_FIVE_BENCHMARK_RISK_SCHEMA_VERSION = "ix-cognition-kernel-wave5-benchmark-risk-v1"
WAVE_FIVE_BENCHMARK_CONTROL_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave5-benchmark-control-v1"
)
WAVE_FIVE_BENCHMARK_AUDIT_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave5-benchmark-audit-v1"
)


class WaveFiveBenchmarkUse(StrEnum):
    """Allowed use of a benchmark-like evaluation inside Wave 5."""

    SMOKE_TEST = "smoke-test"
    REGRESSION_CHECK = "regression-check"
    NEGATIVE_CONTROL = "negative-control"
    STRESS_TEST = "stress-test"
    EXTERNAL_COMPARISON = "external-comparison"


class WaveFiveBenchmarkProvenanceStatus(StrEnum):
    """Provenance status of a benchmark or evaluation source."""

    FULLY_DOCUMENTED = "fully-documented"
    PARTIALLY_DOCUMENTED = "partially-documented"
    EXTERNAL_HELD_OUT = "external-held-out"
    UNKNOWN = "unknown"
    CONTAMINATED = "contaminated"


class WaveFiveBenchmarkRiskKind(StrEnum):
    """Risks that can make benchmark evidence unsafe to overinterpret."""

    BENCHMARK_MEMORIZATION = "benchmark-memorization"
    DATA_CONTAMINATION = "data-contamination"
    CHERRY_PICKING = "cherry-picking"
    METRIC_GAMING = "metric-gaming"
    TRAINING_TEST_LEAKAGE = "training-test-leakage"
    EVALUATOR_OVERFITTING = "evaluator-overfitting"
    PROMPT_TEMPLATE_LEAKAGE = "prompt-template-leakage"
    CLAIM_INFLATION = "claim-inflation"


class WaveFiveBenchmarkRiskDisposition(StrEnum):
    """Disposition of one benchmark-gaming or contamination risk."""

    NOT_OBSERVED = "not-observed"
    MITIGATED_WITH_EVIDENCE = "mitigated-with-evidence"
    EXTERNALLY_DISPUTED = "externally-disputed"
    NEEDS_MORE_EVIDENCE = "needs-more-evidence"
    BLOCKING = "blocking"


class WaveFiveBenchmarkControlKind(StrEnum):
    """Controls required to keep benchmark evidence bounded."""

    PROVENANCE_REVIEW = "provenance-review"
    CONTAMINATION_SCAN = "contamination-scan"
    HELD_OUT_NEGATIVE_CONTROL = "held-out-negative-control"
    METRIC_DIVERSITY_CHECK = "metric-diversity-check"
    FAILED_CASE_RETENTION = "failed-case-retention"
    CLAIM_BOUNDARY_CHECK = "claim-boundary-check"
    EXTERNAL_AUDIT_READY = "external-audit-ready"


class WaveFiveBenchmarkControlResult(StrEnum):
    """Observed result of an anti-gaming control."""

    PASSED = "passed"
    PASSED_WITH_LIMITS = "passed-with-limits"
    NEEDS_MORE_EVIDENCE = "needs-more-evidence"
    FAILED = "failed"


class WaveFiveBenchmarkAuditState(StrEnum):
    """Review state of a Wave 5 benchmark-contamination audit."""

    INTERNAL_AUDIT_READY = "internal-audit-ready"
    READY_FOR_EXTERNAL_AUDIT = "ready-for-external-audit"
    UNDER_EXTERNAL_AUDIT = "under-external-audit"
    EXTERNALLY_REVIEWED_WITH_BOUNDARIES = "externally-reviewed-with-boundaries"
    BLOCKED_BY_BENCHMARK_RISK = "blocked-by-benchmark-risk"


REQUIRED_WAVE_FIVE_BENCHMARK_RISKS: tuple[WaveFiveBenchmarkRiskKind, ...] = (
    WaveFiveBenchmarkRiskKind.BENCHMARK_MEMORIZATION,
    WaveFiveBenchmarkRiskKind.DATA_CONTAMINATION,
    WaveFiveBenchmarkRiskKind.CHERRY_PICKING,
    WaveFiveBenchmarkRiskKind.METRIC_GAMING,
    WaveFiveBenchmarkRiskKind.TRAINING_TEST_LEAKAGE,
    WaveFiveBenchmarkRiskKind.EVALUATOR_OVERFITTING,
    WaveFiveBenchmarkRiskKind.PROMPT_TEMPLATE_LEAKAGE,
    WaveFiveBenchmarkRiskKind.CLAIM_INFLATION,
)

REQUIRED_WAVE_FIVE_BENCHMARK_CONTROLS: tuple[WaveFiveBenchmarkControlKind, ...] = (
    WaveFiveBenchmarkControlKind.PROVENANCE_REVIEW,
    WaveFiveBenchmarkControlKind.CONTAMINATION_SCAN,
    WaveFiveBenchmarkControlKind.HELD_OUT_NEGATIVE_CONTROL,
    WaveFiveBenchmarkControlKind.METRIC_DIVERSITY_CHECK,
    WaveFiveBenchmarkControlKind.FAILED_CASE_RETENTION,
    WaveFiveBenchmarkControlKind.CLAIM_BOUNDARY_CHECK,
    WaveFiveBenchmarkControlKind.EXTERNAL_AUDIT_READY,
)

SAFE_WAVE_FIVE_BENCHMARK_RISK_DISPOSITIONS: tuple[
    WaveFiveBenchmarkRiskDisposition, ...
] = (
    WaveFiveBenchmarkRiskDisposition.NOT_OBSERVED,
    WaveFiveBenchmarkRiskDisposition.MITIGATED_WITH_EVIDENCE,
)

EXTERNAL_BENCHMARK_AUDIT_SOURCE_SYSTEMS: tuple[WaveFiveSourceSystem, ...] = (
    WaveFiveSourceSystem.EXTERNAL_REVIEW,
    WaveFiveSourceSystem.INDEPENDENT_REVIEWER,
    WaveFiveSourceSystem.INDEPENDENT_REPLICATION_LAB,
)


@dataclass(frozen=True, slots=True)
class WaveFiveBenchmarkSource:
    """One benchmark-like evaluation source with bounded allowed use."""

    benchmark_id: str
    name: str
    allowed_use: WaveFiveBenchmarkUse
    provenance_status: WaveFiveBenchmarkProvenanceStatus
    scope_summary: str
    known_limitations: tuple[str, ...]
    prohibited_claims: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    schema_version: str = WAVE_FIVE_BENCHMARK_SOURCE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate benchmark source provenance and claim boundaries."""

        object.__setattr__(
            self, "benchmark_id", _text(self.benchmark_id, "benchmark_id")
        )
        object.__setattr__(self, "name", _text(self.name, "name"))
        object.__setattr__(
            self, "scope_summary", _text(self.scope_summary, "scope_summary")
        )
        object.__setattr__(
            self,
            "known_limitations",
            _unique_text(self.known_limitations, label="known limitation"),
        )
        object.__setattr__(
            self,
            "prohibited_claims",
            _unique_text(self.prohibited_claims, label="prohibited claim"),
        )
        object.__setattr__(
            self, "evidence_ids", _unique_text(self.evidence_ids, label="evidence_id")
        )
        if not self.known_limitations:
            raise ValueError("Benchmark sources require known limitations.")
        if not self.prohibited_claims:
            raise ValueError("Benchmark sources require prohibited claims.")
        if not self.evidence_ids:
            raise ValueError("Benchmark sources require evidence ids.")
        if (
            self.provenance_status
            in {
                WaveFiveBenchmarkProvenanceStatus.UNKNOWN,
                WaveFiveBenchmarkProvenanceStatus.CONTAMINATED,
            }
            and self.allowed_use is not WaveFiveBenchmarkUse.NEGATIVE_CONTROL
        ):
            raise ValueError(
                "Unknown or contaminated benchmark sources can only be "
                "negative controls."
            )
        object.__setattr__(
            self, "schema_version", _text(self.schema_version, "schema_version")
        )

    @property
    def source_key(self) -> str:
        """Return deterministic source key."""

        return self.benchmark_id

    @property
    def reviewable_as_positive_evidence(self) -> bool:
        """Return whether the source can count as bounded positive evidence."""

        return (
            self.provenance_status
            in {
                WaveFiveBenchmarkProvenanceStatus.FULLY_DOCUMENTED,
                WaveFiveBenchmarkProvenanceStatus.EXTERNAL_HELD_OUT,
            }
            and self.allowed_use is not WaveFiveBenchmarkUse.NEGATIVE_CONTROL
        )

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic export payload."""

        return {
            "allowed_use": self.allowed_use.value,
            "benchmark_id": self.benchmark_id,
            "evidence_ids": list(self.evidence_ids),
            "known_limitations": list(self.known_limitations),
            "name": self.name,
            "prohibited_claims": list(self.prohibited_claims),
            "provenance_status": self.provenance_status.value,
            "schema_version": self.schema_version,
            "scope_summary": self.scope_summary,
        }


@dataclass(frozen=True, slots=True)
class WaveFiveBenchmarkRiskFinding:
    """One benchmark-gaming or contamination risk finding."""

    finding_id: str
    benchmark_id: str
    risk_kind: WaveFiveBenchmarkRiskKind
    disposition: WaveFiveBenchmarkRiskDisposition
    risk_summary: str
    mitigation: str
    evidence_ids: tuple[str, ...]
    reviewer_ids: tuple[str, ...] = ()
    schema_version: str = WAVE_FIVE_BENCHMARK_RISK_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate risk-finding evidence and blocking state."""

        object.__setattr__(self, "finding_id", _text(self.finding_id, "finding_id"))
        object.__setattr__(
            self, "benchmark_id", _text(self.benchmark_id, "benchmark_id")
        )
        object.__setattr__(
            self, "risk_summary", _text(self.risk_summary, "risk_summary")
        )
        object.__setattr__(self, "mitigation", _text(self.mitigation, "mitigation"))
        object.__setattr__(
            self, "evidence_ids", _unique_text(self.evidence_ids, label="evidence_id")
        )
        object.__setattr__(
            self, "reviewer_ids", _unique_text(self.reviewer_ids, label="reviewer_id")
        )
        if not self.evidence_ids:
            raise ValueError("Benchmark risk findings require evidence ids.")
        if (
            self.disposition is WaveFiveBenchmarkRiskDisposition.EXTERNALLY_DISPUTED
            and not self.reviewer_ids
        ):
            raise ValueError("Disputed benchmark risks require reviewer ids.")
        object.__setattr__(
            self, "schema_version", _text(self.schema_version, "schema_version")
        )

    @property
    def finding_key(self) -> str:
        """Return deterministic finding key."""

        return self.finding_id

    @property
    def blocks_wave_five_progress(self) -> bool:
        """Return whether this finding blocks benchmark-audit readiness."""

        return self.disposition in {
            WaveFiveBenchmarkRiskDisposition.EXTERNALLY_DISPUTED,
            WaveFiveBenchmarkRiskDisposition.NEEDS_MORE_EVIDENCE,
            WaveFiveBenchmarkRiskDisposition.BLOCKING,
        }

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic export payload."""

        return {
            "benchmark_id": self.benchmark_id,
            "disposition": self.disposition.value,
            "evidence_ids": list(self.evidence_ids),
            "finding_id": self.finding_id,
            "mitigation": self.mitigation,
            "reviewer_ids": list(self.reviewer_ids),
            "risk_kind": self.risk_kind.value,
            "risk_summary": self.risk_summary,
            "schema_version": self.schema_version,
        }


@dataclass(frozen=True, slots=True)
class WaveFiveBenchmarkControl:
    """One anti-gaming control applied to benchmark evidence."""

    control_id: str
    control_kind: WaveFiveBenchmarkControlKind
    result: WaveFiveBenchmarkControlResult
    description: str
    evidence_ids: tuple[str, ...]
    blocking: bool = True
    schema_version: str = WAVE_FIVE_BENCHMARK_CONTROL_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate control identity and evidence binding."""

        object.__setattr__(self, "control_id", _text(self.control_id, "control_id"))
        object.__setattr__(self, "description", _text(self.description, "description"))
        object.__setattr__(
            self, "evidence_ids", _unique_text(self.evidence_ids, label="evidence_id")
        )
        if not self.evidence_ids:
            raise ValueError("Benchmark controls require evidence ids.")
        object.__setattr__(
            self, "schema_version", _text(self.schema_version, "schema_version")
        )

    @property
    def control_key(self) -> str:
        """Return deterministic control key."""

        return self.control_id

    @property
    def passed_with_boundaries(self) -> bool:
        """Return whether this control passed without erasing limitations."""

        return self.result in {
            WaveFiveBenchmarkControlResult.PASSED,
            WaveFiveBenchmarkControlResult.PASSED_WITH_LIMITS,
        }

    @property
    def blocks_wave_five_progress(self) -> bool:
        """Return whether this control blocks benchmark-audit readiness."""

        return self.blocking and not self.passed_with_boundaries

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic export payload."""

        return {
            "blocking": self.blocking,
            "control_id": self.control_id,
            "control_kind": self.control_kind.value,
            "description": self.description,
            "evidence_ids": list(self.evidence_ids),
            "result": self.result.value,
            "schema_version": self.schema_version,
        }


@dataclass(frozen=True, slots=True)
class WaveFiveBenchmarkContaminationAudit:
    """Wave 5 benchmark-gaming and contamination audit record."""

    audit_id: str
    title: str
    source_system: WaveFiveSourceSystem
    audit_state: WaveFiveBenchmarkAuditState
    benchmark_sources: tuple[WaveFiveBenchmarkSource, ...]
    risk_findings: tuple[WaveFiveBenchmarkRiskFinding, ...]
    controls: tuple[WaveFiveBenchmarkControl, ...]
    protocol_ids: tuple[str, ...]
    reviewer_ids: tuple[str, ...] = ()
    benchmark_score_used_as_agi_evidence: bool = False
    retained_failed_cases: bool = True
    claim_boundaries: tuple[WaveFiveClaimBoundary, ...] = (
        WAVE_FIVE_REQUIRED_CLAIM_BOUNDARIES
    )
    notes: tuple[str, ...] = ()
    schema_version: str = WAVE_FIVE_BENCHMARK_AUDIT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate audit coverage, anti-gaming controls, and claim boundaries."""

        object.__setattr__(self, "audit_id", _text(self.audit_id, "audit_id"))
        object.__setattr__(self, "title", _text(self.title, "title"))
        if self.benchmark_score_used_as_agi_evidence:
            raise ValueError("Benchmark scores must not be used as AGI evidence.")
        if not self.retained_failed_cases:
            raise ValueError("Benchmark audits must retain failed cases.")
        sources = tuple(
            sorted(self.benchmark_sources, key=lambda item: item.source_key)
        )
        findings = tuple(sorted(self.risk_findings, key=lambda item: item.finding_key))
        controls = tuple(sorted(self.controls, key=lambda item: item.control_key))
        if not sources:
            raise ValueError("Benchmark audits require benchmark sources.")
        if not findings:
            raise ValueError("Benchmark audits require risk findings.")
        if not controls:
            raise ValueError("Benchmark audits require controls.")
        source_ids = _unique_values(
            (item.benchmark_id for item in sources), label="benchmark_id"
        )
        _unique_values((item.finding_id for item in findings), label="finding_id")
        _unique_values((item.control_id for item in controls), label="control_id")
        for finding in findings:
            if finding.benchmark_id not in source_ids:
                raise ValueError(
                    "Benchmark risk findings must reference bundled sources: "
                    f"{finding.benchmark_id}"
                )
        object.__setattr__(self, "benchmark_sources", sources)
        object.__setattr__(self, "risk_findings", findings)
        object.__setattr__(self, "controls", controls)
        object.__setattr__(
            self, "protocol_ids", _unique_text(self.protocol_ids, label="protocol_id")
        )
        if not self.protocol_ids:
            raise ValueError("Benchmark audits require protocol ids.")
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
                "Benchmark audits must preserve claim boundary: "
                f"{missing_boundaries[0].value}"
            )
        object.__setattr__(self, "notes", _unique_text(self.notes, label="audit note"))
        object.__setattr__(
            self, "schema_version", _text(self.schema_version, "schema_version")
        )
        if self.externally_reviewed_with_boundaries:
            if self.source_system not in EXTERNAL_BENCHMARK_AUDIT_SOURCE_SYSTEMS:
                raise ValueError(
                    "Externally reviewed benchmark audits require external source."
                )
            if not self.reviewer_ids:
                raise ValueError(
                    "Externally reviewed benchmark audits require reviewer ids."
                )
            if self.blocking_finding_ids or self.blocking_control_ids:
                raise ValueError(
                    "Externally reviewed benchmark audits cannot contain blockers."
                )

    @property
    def benchmark_ids(self) -> tuple[str, ...]:
        """Return benchmark ids in deterministic order."""

        return tuple(source.benchmark_id for source in self.benchmark_sources)

    @property
    def covered_risk_kinds(self) -> tuple[WaveFiveBenchmarkRiskKind, ...]:
        """Return benchmark risk kinds covered by findings."""

        risks: list[WaveFiveBenchmarkRiskKind] = []
        seen: set[WaveFiveBenchmarkRiskKind] = set()
        for finding in self.risk_findings:
            if finding.risk_kind not in seen:
                risks.append(finding.risk_kind)
                seen.add(finding.risk_kind)
        return tuple(risks)

    @property
    def missing_required_risk_kinds(self) -> tuple[WaveFiveBenchmarkRiskKind, ...]:
        """Return required benchmark risk kinds absent from this audit."""

        covered = set(self.covered_risk_kinds)
        return tuple(
            risk for risk in REQUIRED_WAVE_FIVE_BENCHMARK_RISKS if risk not in covered
        )

    @property
    def covered_control_kinds(self) -> tuple[WaveFiveBenchmarkControlKind, ...]:
        """Return anti-gaming control kinds represented in this audit."""

        controls: list[WaveFiveBenchmarkControlKind] = []
        seen: set[WaveFiveBenchmarkControlKind] = set()
        for control in self.controls:
            if control.control_kind not in seen:
                controls.append(control.control_kind)
                seen.add(control.control_kind)
        return tuple(controls)

    @property
    def missing_required_control_kinds(
        self,
    ) -> tuple[WaveFiveBenchmarkControlKind, ...]:
        """Return required anti-gaming controls absent from this audit."""

        covered = set(self.covered_control_kinds)
        return tuple(
            control
            for control in REQUIRED_WAVE_FIVE_BENCHMARK_CONTROLS
            if control not in covered
        )

    @property
    def blocking_finding_ids(self) -> tuple[str, ...]:
        """Return benchmark risk findings that block Wave 5 progress."""

        return tuple(
            finding.finding_id
            for finding in self.risk_findings
            if finding.blocks_wave_five_progress
        )

    @property
    def blocking_control_ids(self) -> tuple[str, ...]:
        """Return anti-gaming controls that block Wave 5 progress."""

        return tuple(
            control.control_id
            for control in self.controls
            if control.blocks_wave_five_progress
        )

    @property
    def has_required_risk_coverage(self) -> bool:
        """Return whether every locked benchmark risk is represented."""

        return not self.missing_required_risk_kinds

    @property
    def has_required_control_coverage(self) -> bool:
        """Return whether every locked anti-gaming control is represented."""

        return not self.missing_required_control_kinds

    @property
    def has_reviewable_positive_source(self) -> bool:
        """Return whether at least one bounded positive source is reviewable."""

        return any(
            source.reviewable_as_positive_evidence for source in self.benchmark_sources
        )

    @property
    def ready_for_external_benchmark_audit(self) -> bool:
        """Return whether the audit can enter external benchmark review."""

        return (
            self.audit_state
            in {
                WaveFiveBenchmarkAuditState.INTERNAL_AUDIT_READY,
                WaveFiveBenchmarkAuditState.READY_FOR_EXTERNAL_AUDIT,
                WaveFiveBenchmarkAuditState.UNDER_EXTERNAL_AUDIT,
            }
            and self.has_required_risk_coverage
            and self.has_required_control_coverage
            and self.has_reviewable_positive_source
            and not self.blocking_finding_ids
            and not self.blocking_control_ids
            and self.retained_failed_cases
            and not self.benchmark_score_used_as_agi_evidence
        )

    @property
    def externally_reviewed_with_boundaries(self) -> bool:
        """Return whether external benchmark audit accepted boundaries."""

        return (
            self.audit_state
            is WaveFiveBenchmarkAuditState.EXTERNALLY_REVIEWED_WITH_BOUNDARIES
        )

    @property
    def all_evidence_ids(self) -> tuple[str, ...]:
        """Return all evidence ids bound into this audit."""

        evidence_ids: list[str] = []
        seen: set[str] = set()
        for evidence_id in self._iter_evidence_ids():
            if evidence_id not in seen:
                evidence_ids.append(evidence_id)
                seen.add(evidence_id)
        return tuple(evidence_ids)

    def to_artifact_ref(self) -> WaveFiveArtifactRef:
        """Return this audit as a Wave 5 benchmark-contamination artifact."""

        decision = WaveFiveArtifactDecision.NEEDS_EXTERNAL_EVIDENCE
        status = WaveFiveValidationStatus.MISSING_EXTERNAL_EVIDENCE
        authority = WaveFiveAuthorityState.HUMAN_REVIEW_REQUIRED
        if self.externally_reviewed_with_boundaries:
            decision = WaveFiveArtifactDecision.EXTERNALLY_REVIEWED
            status = WaveFiveValidationStatus.ACCEPTED_WITH_BOUNDARIES
        elif self.ready_for_external_benchmark_audit:
            decision = WaveFiveArtifactDecision.READY_FOR_INDEPENDENT_REVIEW
            status = WaveFiveValidationStatus.UNDER_INDEPENDENT_REVIEW
        elif self.blocking_finding_ids or self.blocking_control_ids:
            decision = WaveFiveArtifactDecision.BLOCKED
            status = WaveFiveValidationStatus.REJECTED
            authority = WaveFiveAuthorityState.BLOCKED
        return WaveFiveArtifactRef(
            artifact_id=self.audit_id,
            kind=WaveFiveArtifactKind.BENCHMARK_CONTAMINATION_AUDIT,
            capability_area=WaveFiveCapabilityArea.BENCHMARK_GAMING_RESISTANCE,
            source_system=self.source_system,
            summary=self.title,
            produced_by_engine_id="wave5-benchmark-contamination-audit-engine",
            produced_by_agent_role_id="benchmark-gaming-auditor",
            evidence_ids=self.all_evidence_ids,
            decision=decision,
            authority_state=authority,
            validation_status=status,
            claim_boundaries=self.claim_boundaries,
        )

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic export payload."""

        return {
            "audit_id": self.audit_id,
            "audit_state": self.audit_state.value,
            "benchmark_score_used_as_agi_evidence": (
                self.benchmark_score_used_as_agi_evidence
            ),
            "benchmark_sources": [
                source.canonical_payload() for source in self.benchmark_sources
            ],
            "claim_boundaries": [boundary.value for boundary in self.claim_boundaries],
            "controls": [control.canonical_payload() for control in self.controls],
            "notes": list(self.notes),
            "protocol_ids": list(self.protocol_ids),
            "retained_failed_cases": self.retained_failed_cases,
            "reviewer_ids": list(self.reviewer_ids),
            "risk_findings": [
                finding.canonical_payload() for finding in self.risk_findings
            ],
            "schema_version": self.schema_version,
            "source_system": self.source_system.value,
            "title": self.title,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this audit."""

        return _stable_sha256(self.canonical_payload())

    def _iter_evidence_ids(self) -> Iterable[str]:
        """Yield evidence ids in deterministic audit traversal order."""

        for source in self.benchmark_sources:
            yield from source.evidence_ids
        for finding in self.risk_findings:
            yield from finding.evidence_ids
        for control in self.controls:
            yield from control.evidence_ids


def required_wave_five_benchmark_risks() -> tuple[WaveFiveBenchmarkRiskKind, ...]:
    """Return locked benchmark risks required for Wave 5 audit coverage."""

    return REQUIRED_WAVE_FIVE_BENCHMARK_RISKS


def required_wave_five_benchmark_controls() -> tuple[WaveFiveBenchmarkControlKind, ...]:
    """Return locked anti-gaming controls required for Wave 5 audit coverage."""

    return REQUIRED_WAVE_FIVE_BENCHMARK_CONTROLS


def safe_wave_five_benchmark_risk_dispositions() -> tuple[
    WaveFiveBenchmarkRiskDisposition, ...
]:
    """Return dispositions that do not block benchmark-audit readiness."""

    return SAFE_WAVE_FIVE_BENCHMARK_RISK_DISPOSITIONS


def external_benchmark_audit_source_systems() -> tuple[WaveFiveSourceSystem, ...]:
    """Return source systems allowed to assert external benchmark audit."""

    return EXTERNAL_BENCHMARK_AUDIT_SOURCE_SYSTEMS


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

    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
