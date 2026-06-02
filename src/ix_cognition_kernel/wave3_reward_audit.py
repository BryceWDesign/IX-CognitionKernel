"""Wave 3 reward-auditor records for IX-CognitionKernel.

The reward auditor exists to catch objective mismatch, specification gaming,
reward hacking, metric-over-mission behavior, and evaluation gaming before a
plan can be treated as reviewable substrate evidence. These records are
measurement and governance artifacts only. They do not repair objectives by
magic, approve execution, or let a metric outrank the mission boundary.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, TypeVar

from ix_cognition_kernel.wave3_contracts import (
    WaveThreeArtifactBundle,
    WaveThreeArtifactDecision,
    WaveThreeArtifactKind,
    WaveThreeArtifactRef,
    WaveThreeAuthorityState,
    WaveThreeEvidenceLink,
    WaveThreeEvidenceRelation,
    WaveThreeSourceSystem,
)

T = TypeVar("T")
E = TypeVar("E", bound=StrEnum)

WAVE_THREE_REWARD_AUDIT_SCHEMA_VERSION = "ix-cognition-kernel-wave3-reward-audit-v1"
WAVE_THREE_REWARD_FINDING_SCHEMA_VERSION = "ix-cognition-kernel-wave3-reward-finding-v1"


class RewardRiskKind(StrEnum):
    """Risk families the reward auditor must explicitly evaluate."""

    OBJECTIVE_MISMATCH = "objective-mismatch"
    SPECIFICATION_GAMING = "specification-gaming"
    REWARD_HACKING = "reward-hacking"
    METRIC_OVER_MISSION = "metric-over-mission"
    EVALUATION_GAMING = "evaluation-gaming"


class RewardFindingSeverity(StrEnum):
    """Severity level for an evidence-bound reward-audit finding."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RewardAuditStatus(StrEnum):
    """Fail-closed status for a reward audit record."""

    READY_FOR_HUMAN_REVIEW = "ready-for-human-review"
    NEEDS_REPAIR = "needs-repair"
    NEEDS_EVIDENCE = "needs-evidence"
    BLOCKED = "blocked"


REQUIRED_REWARD_RISK_KINDS: tuple[RewardRiskKind, ...] = (
    RewardRiskKind.OBJECTIVE_MISMATCH,
    RewardRiskKind.SPECIFICATION_GAMING,
    RewardRiskKind.REWARD_HACKING,
    RewardRiskKind.METRIC_OVER_MISSION,
    RewardRiskKind.EVALUATION_GAMING,
)

BLOCKING_REWARD_SEVERITIES: frozenset[RewardFindingSeverity] = frozenset(
    {RewardFindingSeverity.HIGH, RewardFindingSeverity.CRITICAL}
)


@dataclass(frozen=True, slots=True)
class RewardAuditFinding:
    """One evidence-bound reward-audit finding."""

    finding_id: str
    risk_kind: RewardRiskKind
    severity: RewardFindingSeverity
    description: str
    affected_metric: str
    evidence_ids: tuple[str, ...]
    repair_recommendation: str
    blocks_progress: bool = False
    schema_version: str = WAVE_THREE_REWARD_FINDING_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate finding evidence, repairability, and blocking discipline."""

        object.__setattr__(
            self, "finding_id", _require_non_empty(self.finding_id, "finding_id")
        )
        object.__setattr__(
            self,
            "description",
            _require_non_empty(self.description, "finding description"),
        )
        object.__setattr__(
            self,
            "affected_metric",
            _require_non_empty(self.affected_metric, "affected_metric"),
        )
        object.__setattr__(
            self,
            "evidence_ids",
            _normalize_unique_text_tuple(
                self.evidence_ids, label="finding evidence_id"
            ),
        )
        object.__setattr__(
            self,
            "repair_recommendation",
            _require_non_empty(self.repair_recommendation, "repair_recommendation"),
        )
        object.__setattr__(
            self,
            "schema_version",
            _require_non_empty(self.schema_version, "schema_version"),
        )
        if self.severity in BLOCKING_REWARD_SEVERITIES and not self.blocks_progress:
            raise ValueError(
                "High and critical reward-audit findings must block progress."
            )

    @property
    def finding_key(self) -> tuple[str, str]:
        """Return deterministic uniqueness key for this finding."""

        return (self.finding_id, self.risk_kind.value)

    def canonical_payload(self) -> dict[str, Any]:
        """Return a deterministic payload for hashing and export."""

        return {
            "affected_metric": self.affected_metric,
            "blocks_progress": self.blocks_progress,
            "description": self.description,
            "evidence_ids": list(self.evidence_ids),
            "finding_id": self.finding_id,
            "repair_recommendation": self.repair_recommendation,
            "risk_kind": self.risk_kind.value,
            "schema_version": self.schema_version,
            "severity": self.severity.value,
        }

    def fingerprint(self) -> str:
        """Return a deterministic SHA-256 fingerprint for this finding."""

        return _stable_sha256(self.canonical_payload())


@dataclass(frozen=True, slots=True)
class RewardAuditRecord:
    """Reviewable Wave 3 reward-auditor record."""

    audit_id: str
    objective: str
    metric: str
    mission_boundary: str
    evaluated_risk_kinds: tuple[RewardRiskKind, ...]
    evidence_ids: tuple[str, ...]
    findings: tuple[RewardAuditFinding, ...] = ()
    auditor_role_id: str = "reward-auditor"
    schema_version: str = WAVE_THREE_REWARD_AUDIT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate risk coverage, evidence binding, and authority boundary."""

        object.__setattr__(
            self, "audit_id", _require_non_empty(self.audit_id, "audit_id")
        )
        object.__setattr__(
            self, "objective", _require_non_empty(self.objective, "objective")
        )
        object.__setattr__(self, "metric", _require_non_empty(self.metric, "metric"))
        object.__setattr__(
            self,
            "mission_boundary",
            _require_non_empty(self.mission_boundary, "mission_boundary"),
        )
        object.__setattr__(
            self,
            "evaluated_risk_kinds",
            _normalize_unique_enum_tuple(
                self.evaluated_risk_kinds, label="evaluated risk kind"
            ),
        )
        object.__setattr__(
            self,
            "evidence_ids",
            _normalize_unique_text_tuple(self.evidence_ids, label="audit evidence_id"),
        )
        sorted_findings = tuple(
            sorted(self.findings, key=lambda item: item.finding_key)
        )
        _unique_ids(
            (finding.finding_id for finding in sorted_findings), label="finding_id"
        )
        object.__setattr__(self, "findings", sorted_findings)
        object.__setattr__(
            self,
            "auditor_role_id",
            _require_non_empty(self.auditor_role_id, "auditor_role_id"),
        )
        if self.auditor_role_id != "reward-auditor":
            raise ValueError("Reward audit records must be produced by reward-auditor.")
        object.__setattr__(
            self,
            "schema_version",
            _require_non_empty(self.schema_version, "schema_version"),
        )
        if not self.evaluated_risk_kinds:
            raise ValueError("Reward audits require evaluated risk kinds.")

    @property
    def artifact_id(self) -> str:
        """Return the shared Wave 3 artifact id for this reward audit."""

        return f"reward-audit:{self.audit_id}"

    @property
    def missing_required_risk_kinds(self) -> tuple[RewardRiskKind, ...]:
        """Return required reward risk families not explicitly evaluated."""

        present = set(self.evaluated_risk_kinds)
        return tuple(kind for kind in REQUIRED_REWARD_RISK_KINDS if kind not in present)

    @property
    def finding_evidence_ids(self) -> tuple[str, ...]:
        """Return sorted unique evidence ids referenced by findings."""

        return tuple(
            sorted(
                {
                    evidence_id
                    for finding in self.findings
                    for evidence_id in finding.evidence_ids
                }
            )
        )

    @property
    def all_evidence_ids(self) -> tuple[str, ...]:
        """Return sorted unique audit and finding evidence ids."""

        return tuple(sorted(set(self.evidence_ids).union(self.finding_evidence_ids)))

    @property
    def blocking_findings(self) -> tuple[RewardAuditFinding, ...]:
        """Return findings that block progress."""

        return tuple(finding for finding in self.findings if finding.blocks_progress)

    @property
    def non_blocking_findings(self) -> tuple[RewardAuditFinding, ...]:
        """Return findings that need repair but do not block progress."""

        return tuple(
            finding for finding in self.findings if not finding.blocks_progress
        )

    @property
    def repair_recommendations(self) -> tuple[str, ...]:
        """Return deterministic repair recommendations from findings."""

        return tuple(
            finding.repair_recommendation
            for finding in self.findings
            if finding.repair_recommendation
        )

    @property
    def readiness_gaps(self) -> tuple[str, ...]:
        """Return gaps that prevent human-review readiness."""

        gaps: list[str] = []
        if self.missing_required_risk_kinds:
            gaps.append(
                "missing reward risk coverage: "
                + ", ".join(kind.value for kind in self.missing_required_risk_kinds)
            )
        if not self.evidence_ids:
            gaps.append("reward audit has no top-level evidence ids")
        if self.non_blocking_findings:
            gaps.append(
                "reward findings need repair: "
                + ", ".join(
                    finding.finding_id for finding in self.non_blocking_findings
                )
            )
        return tuple(gaps)

    @property
    def blocking_gaps(self) -> tuple[str, ...]:
        """Return evidence-bound blocks that stop progress."""

        return tuple(
            f"reward finding blocks progress: {finding.finding_id} "
            f"({finding.risk_kind.value})"
            for finding in self.blocking_findings
        )

    @property
    def status(self) -> RewardAuditStatus:
        """Return the fail-closed reward-audit status."""

        if self.blocking_gaps:
            return RewardAuditStatus.BLOCKED
        if self.non_blocking_findings:
            return RewardAuditStatus.NEEDS_REPAIR
        if self.readiness_gaps:
            return RewardAuditStatus.NEEDS_EVIDENCE
        return RewardAuditStatus.READY_FOR_HUMAN_REVIEW

    @property
    def ready_for_human_review(self) -> bool:
        """Return whether this reward audit may enter human review."""

        return self.status is RewardAuditStatus.READY_FOR_HUMAN_REVIEW

    @property
    def permits_automatic_execution(self) -> bool:
        """Return whether this reward audit permits automatic execution."""

        return False

    @property
    def human_authority_state(self) -> WaveThreeAuthorityState:
        """Return aggregate human-authority state for this reward audit."""

        if self.status is RewardAuditStatus.BLOCKED:
            return WaveThreeAuthorityState.BLOCKED
        return WaveThreeAuthorityState.HUMAN_REVIEW_REQUIRED

    @property
    def review_summary(self) -> str:
        """Return a concise human-review summary."""

        return (
            f"{self.audit_id}: {self.status.value}; "
            f"{len(self.evaluated_risk_kinds)}/{len(REQUIRED_REWARD_RISK_KINDS)} "
            f"risk families evaluated; {len(self.findings)} findings; "
            "automatic execution is not permitted."
        )

    def to_artifact_ref(self) -> WaveThreeArtifactRef:
        """Convert this reward audit into a shared Wave 3 artifact reference."""

        if self.status is RewardAuditStatus.READY_FOR_HUMAN_REVIEW:
            decision = WaveThreeArtifactDecision.READY_FOR_HUMAN_REVIEW
            authority_state = WaveThreeAuthorityState.HUMAN_REVIEW_REQUIRED
        elif self.status is RewardAuditStatus.BLOCKED:
            decision = WaveThreeArtifactDecision.BLOCKED
            authority_state = WaveThreeAuthorityState.BLOCKED
        else:
            decision = WaveThreeArtifactDecision.NEEDS_EVIDENCE
            authority_state = WaveThreeAuthorityState.HUMAN_REVIEW_REQUIRED
        return WaveThreeArtifactRef(
            artifact_id=self.artifact_id,
            kind=WaveThreeArtifactKind.REWARD_AUDIT,
            source_system=WaveThreeSourceSystem.IX_COGNITION_KERNEL,
            summary=self.review_summary,
            produced_by_engine_id="reward-auditor",
            produced_by_agent_role_id=self.auditor_role_id,
            evidence_ids=self.all_evidence_ids,
            decision=decision,
            authority_state=authority_state,
        )

    def to_artifact_bundle(self, *, artifact_bundle_id: str) -> WaveThreeArtifactBundle:
        """Convert the reward audit into a shared Wave 3 artifact bundle."""

        artifact = self.to_artifact_ref()
        evidence_links = tuple(
            WaveThreeEvidenceLink(
                evidence_id=evidence_id,
                artifact_id=artifact.artifact_id,
                relation=WaveThreeEvidenceRelation.TESTS,
                summary="Reward-audit evidence tests objective and metric alignment.",
                source_system=WaveThreeSourceSystem.LOCAL_TEST_SUITE,
            )
            for evidence_id in artifact.evidence_ids
        )
        return WaveThreeArtifactBundle(
            bundle_id=artifact_bundle_id,
            artifacts=(artifact,),
            evidence_links=evidence_links,
            required_kinds=(WaveThreeArtifactKind.REWARD_AUDIT,),
            notes=("Reward audits are review gates, not optimization targets.",),
        )

    def canonical_payload(self) -> dict[str, Any]:
        """Return a deterministic payload for hashing and export."""

        return {
            "all_evidence_ids": list(self.all_evidence_ids),
            "artifact_id": self.artifact_id,
            "audit_id": self.audit_id,
            "auditor_role_id": self.auditor_role_id,
            "blocking_gaps": list(self.blocking_gaps),
            "evaluated_risk_kinds": [kind.value for kind in self.evaluated_risk_kinds],
            "evidence_ids": list(self.evidence_ids),
            "findings": [finding.canonical_payload() for finding in self.findings],
            "human_authority_state": self.human_authority_state.value,
            "metric": self.metric,
            "mission_boundary": self.mission_boundary,
            "objective": self.objective,
            "permits_automatic_execution": self.permits_automatic_execution,
            "readiness_gaps": list(self.readiness_gaps),
            "repair_recommendations": list(self.repair_recommendations),
            "review_summary": self.review_summary,
            "schema_version": self.schema_version,
            "status": self.status.value,
        }

    def fingerprint(self) -> str:
        """Return a deterministic SHA-256 fingerprint for this reward audit."""

        return _stable_sha256(self.canonical_payload())


def clean_reward_audit_record(
    *,
    audit_id: str,
    objective: str,
    metric: str,
    mission_boundary: str,
    evidence_ids: tuple[str, ...],
) -> RewardAuditRecord:
    """Create a complete reward audit with no detected reward-risk findings."""

    return RewardAuditRecord(
        audit_id=audit_id,
        objective=objective,
        metric=metric,
        mission_boundary=mission_boundary,
        evaluated_risk_kinds=REQUIRED_REWARD_RISK_KINDS,
        evidence_ids=evidence_ids,
    )


def _require_non_empty(value: str, label: str) -> str:
    """Return stripped text or raise when empty."""

    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{label} must not be empty.")
    return normalized


def _normalize_unique_text_tuple(
    values: Iterable[str], *, label: str
) -> tuple[str, ...]:
    """Normalize text tuples while rejecting blanks and duplicates."""

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
    """Normalize enum tuples while rejecting duplicates."""

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
