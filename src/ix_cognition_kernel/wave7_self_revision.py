"""Wave 7 self-revision proposals.

Self-revision is where a persistent cognitive system proposes changes to its
own rules, memories, evaluators, skill boundaries, or runtime handoff logic.
This module keeps that process evidence-bound and human-governed.

Wave 7 self-revision doctrine:

- self-revision is a proposal, not permission,
- the system cannot approve its own changes,
- authority rules cannot be rewritten by proposal,
- high-risk changes require sandboxed review,
- immutable targets fail closed,
- missing evidence blocks readiness,
- human approval is explicit and replayable.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

WAVE_SEVEN_REVISION_TARGET_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave7-revision-target-v1"
)
WAVE_SEVEN_REVISION_IMPACT_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave7-revision-impact-v1"
)
WAVE_SEVEN_REVISION_EVIDENCE_GATE_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave7-revision-evidence-gate-v1"
)
WAVE_SEVEN_SELF_REVISION_PROPOSAL_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave7-self-revision-proposal-v1"
)
WAVE_SEVEN_SELF_REVISION_FINDING_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave7-self-revision-finding-v1"
)
WAVE_SEVEN_SELF_REVISION_DECISION_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave7-self-revision-decision-v1"
)
WAVE_SEVEN_SELF_REVISION_REPORT_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave7-self-revision-report-v1"
)


class RevisionTargetKind(StrEnum):
    """Kinds of internal objects that may be proposed for revision."""

    EVALUATOR_RULE = "evaluator-rule"
    MEMORY_RULE = "memory-rule"
    SKILL_BOUNDARY = "skill-boundary"
    BODY_CONTRACT = "body-contract"
    RUNTIME_AIRLOCK_RULE = "runtime-airlock-rule"
    GOAL_PRESSURE_RULE = "goal-pressure-rule"
    CLAIM_BOUNDARY = "claim-boundary"
    DOCTRINE_RULE = "doctrine-rule"


class RevisionRisk(StrEnum):
    """Risk tier for a proposed self-revision."""

    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


class RevisionScope(StrEnum):
    """Scope touched by a proposed self-revision."""

    RECORD_ONLY = "record-only"
    SIMULATION_ONLY = "simulation-only"
    REVIEW_PACKET = "review-packet"
    RUNTIME_BOUNDARY = "runtime-boundary"
    DOCTRINE_BOUNDARY = "doctrine-boundary"


class RevisionFindingSeverity(StrEnum):
    """Severity for a self-revision finding."""

    INFO = "info"
    REVIEW_REQUIRED = "review-required"
    MISSING_EVIDENCE = "missing-evidence"
    BLOCKING = "blocking"


class SelfRevisionDecisionStatus(StrEnum):
    """Fail-closed status for self-revision decisions."""

    DRAFT = "draft"
    READY_FOR_HUMAN_REVIEW = "ready-for-human-review"
    NEEDS_MORE_EVIDENCE = "needs-more-evidence"
    BLOCKED = "blocked"
    REJECTED = "rejected"
    APPROVED_BY_HUMAN_REVIEW = "approved-by-human-review"


@dataclass(frozen=True, slots=True)
class RevisionTarget:
    """Internal target that a self-revision proposal wants to change."""

    target_id: str
    kind: RevisionTargetKind
    name: str
    current_behavior_summary: str
    protected_invariants: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    authority_refs: tuple[str, ...]
    immutable: bool = False
    schema_version: str = WAVE_SEVEN_REVISION_TARGET_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate target evidence, invariants, and authority boundary."""

        object.__setattr__(
            self,
            "target_id",
            _require_non_empty(self.target_id, "target_id"),
        )
        object.__setattr__(self, "name", _require_non_empty(self.name, "name"))
        object.__setattr__(
            self,
            "current_behavior_summary",
            _require_non_empty(
                self.current_behavior_summary, "current_behavior_summary"
            ),
        )
        object.__setattr__(
            self,
            "protected_invariants",
            _normalize_unique_text_tuple(
                self.protected_invariants, label="protected_invariant"
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
            "schema_version",
            _require_non_empty(self.schema_version, "schema_version"),
        )
        if not self.protected_invariants:
            raise ValueError("Revision targets require protected invariants.")
        if not self.evidence_ids:
            raise ValueError("Revision targets require evidence ids.")
        if not self.authority_refs:
            raise ValueError("Revision targets require authority refs.")

    @property
    def blocks_revision(self) -> bool:
        """Return whether this target blocks revision by policy."""

        return self.immutable

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic target payload."""

        return {
            "authority_refs": list(self.authority_refs),
            "current_behavior_summary": self.current_behavior_summary,
            "evidence_ids": list(self.evidence_ids),
            "immutable": self.immutable,
            "kind": self.kind.value,
            "name": self.name,
            "protected_invariants": list(self.protected_invariants),
            "schema_version": self.schema_version,
            "target_id": self.target_id,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this target."""

        return _stable_sha256(self.canonical_payload())


@dataclass(frozen=True, slots=True)
class RevisionImpactAssessment:
    """Impact assessment for a self-revision proposal."""

    assessment_id: str
    target_id: str
    risk: RevisionRisk
    scope: RevisionScope
    expected_behavior_change: str
    rollback_plan: str
    affected_doctrine_ids: tuple[str, ...]
    affected_capability_ids: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    requires_sandbox: bool = True
    claims_safe_without_review: bool = False
    schema_version: str = WAVE_SEVEN_REVISION_IMPACT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate impact assessment and high-risk sandbox discipline."""

        if self.claims_safe_without_review:
            raise ValueError(
                "Revision impact assessments must not claim safety without review."
            )
        object.__setattr__(
            self,
            "assessment_id",
            _require_non_empty(self.assessment_id, "assessment_id"),
        )
        object.__setattr__(
            self,
            "target_id",
            _require_non_empty(self.target_id, "target_id"),
        )
        object.__setattr__(
            self,
            "expected_behavior_change",
            _require_non_empty(
                self.expected_behavior_change, "expected_behavior_change"
            ),
        )
        object.__setattr__(
            self,
            "rollback_plan",
            _require_non_empty(self.rollback_plan, "rollback_plan"),
        )
        object.__setattr__(
            self,
            "affected_doctrine_ids",
            _normalize_unique_text_tuple(
                self.affected_doctrine_ids, label="affected_doctrine_id"
            ),
        )
        object.__setattr__(
            self,
            "affected_capability_ids",
            _normalize_unique_text_tuple(
                self.affected_capability_ids, label="affected_capability_id"
            ),
        )
        object.__setattr__(
            self,
            "evidence_ids",
            _normalize_unique_text_tuple(self.evidence_ids, label="evidence_id"),
        )
        object.__setattr__(
            self,
            "schema_version",
            _require_non_empty(self.schema_version, "schema_version"),
        )
        if not self.evidence_ids:
            raise ValueError("Revision impact assessments require evidence ids.")
        if self.risk in {RevisionRisk.HIGH, RevisionRisk.CRITICAL}:
            if not self.requires_sandbox:
                raise ValueError("High-risk self-revisions require sandbox review.")
            if not self.affected_doctrine_ids:
                raise ValueError("High-risk self-revisions require doctrine impact.")
        if self.scope is RevisionScope.DOCTRINE_BOUNDARY:
            if not self.affected_doctrine_ids:
                raise ValueError("Doctrine-boundary revisions require doctrine ids.")

    @property
    def elevated_review_required(self) -> bool:
        """Return whether risk or scope requires elevated review."""

        high_risk = self.risk in {RevisionRisk.HIGH, RevisionRisk.CRITICAL}
        boundary_scope = self.scope in {
            RevisionScope.RUNTIME_BOUNDARY,
            RevisionScope.DOCTRINE_BOUNDARY,
        }
        return high_risk or boundary_scope

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic impact payload."""

        return {
            "affected_capability_ids": list(self.affected_capability_ids),
            "affected_doctrine_ids": list(self.affected_doctrine_ids),
            "assessment_id": self.assessment_id,
            "claims_safe_without_review": self.claims_safe_without_review,
            "evidence_ids": list(self.evidence_ids),
            "expected_behavior_change": self.expected_behavior_change,
            "requires_sandbox": self.requires_sandbox,
            "risk": self.risk.value,
            "rollback_plan": self.rollback_plan,
            "schema_version": self.schema_version,
            "scope": self.scope.value,
            "target_id": self.target_id,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this impact."""

        return _stable_sha256(self.canonical_payload())


@dataclass(frozen=True, slots=True)
class RevisionEvidenceGate:
    """Evidence gate for self-revision readiness."""

    gate_id: str
    proposal_id: str
    required_evidence_ids: tuple[str, ...]
    supplied_evidence_ids: tuple[str, ...]
    authority_refs: tuple[str, ...]
    schema_version: str = WAVE_SEVEN_REVISION_EVIDENCE_GATE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate self-revision evidence gate."""

        object.__setattr__(
            self,
            "gate_id",
            _require_non_empty(self.gate_id, "gate_id"),
        )
        object.__setattr__(
            self,
            "proposal_id",
            _require_non_empty(self.proposal_id, "proposal_id"),
        )
        object.__setattr__(
            self,
            "required_evidence_ids",
            _normalize_unique_text_tuple(
                self.required_evidence_ids, label="required_evidence_id"
            ),
        )
        object.__setattr__(
            self,
            "supplied_evidence_ids",
            _normalize_unique_text_tuple(
                self.supplied_evidence_ids, label="supplied_evidence_id"
            ),
        )
        object.__setattr__(
            self,
            "authority_refs",
            _normalize_unique_text_tuple(self.authority_refs, label="authority_ref"),
        )
        object.__setattr__(
            self,
            "schema_version",
            _require_non_empty(self.schema_version, "schema_version"),
        )
        if not self.required_evidence_ids:
            raise ValueError("Revision evidence gates require required evidence ids.")
        if not self.authority_refs:
            raise ValueError("Revision evidence gates require authority refs.")

    @property
    def missing_evidence_ids(self) -> tuple[str, ...]:
        """Return evidence ids required but not supplied."""

        supplied = set(self.supplied_evidence_ids)
        return tuple(
            evidence_id
            for evidence_id in self.required_evidence_ids
            if evidence_id not in supplied
        )

    @property
    def satisfied(self) -> bool:
        """Return whether the revision evidence gate is satisfied."""

        return not self.missing_evidence_ids

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic evidence-gate payload."""

        return {
            "authority_refs": list(self.authority_refs),
            "gate_id": self.gate_id,
            "missing_evidence_ids": list(self.missing_evidence_ids),
            "proposal_id": self.proposal_id,
            "required_evidence_ids": list(self.required_evidence_ids),
            "schema_version": self.schema_version,
            "supplied_evidence_ids": list(self.supplied_evidence_ids),
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this gate."""

        return _stable_sha256(self.canonical_payload())


@dataclass(frozen=True, slots=True)
class SelfRevisionProposal:
    """Proposal for changing an internal cognitive rule or boundary."""

    proposal_id: str
    target: RevisionTarget
    impact: RevisionImpactAssessment
    evidence_gate: RevisionEvidenceGate
    proposed_change_summary: str
    rationale: str
    evidence_ids: tuple[str, ...]
    self_authorized: bool = False
    bypasses_review: bool = False
    modifies_authority_model: bool = False
    schema_version: str = WAVE_SEVEN_SELF_REVISION_PROPOSAL_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate self-revision proposal boundaries."""

        if self.self_authorized:
            raise ValueError("Self-revision proposals must not self-authorize.")
        if self.bypasses_review:
            raise ValueError("Self-revision proposals must not bypass review.")
        if self.modifies_authority_model:
            raise ValueError(
                "Self-revision proposals must not modify authority model."
            )
        object.__setattr__(
            self,
            "proposal_id",
            _require_non_empty(self.proposal_id, "proposal_id"),
        )
        object.__setattr__(
            self,
            "proposed_change_summary",
            _require_non_empty(
                self.proposed_change_summary, "proposed_change_summary"
            ),
        )
        object.__setattr__(
            self,
            "rationale",
            _require_non_empty(self.rationale, "rationale"),
        )
        object.__setattr__(
            self,
            "evidence_ids",
            _normalize_unique_text_tuple(self.evidence_ids, label="evidence_id"),
        )
        object.__setattr__(
            self,
            "schema_version",
            _require_non_empty(self.schema_version, "schema_version"),
        )
        if self.impact.target_id != self.target.target_id:
            raise ValueError("Impact assessment must reference revision target id.")
        if self.evidence_gate.proposal_id != self.proposal_id:
            raise ValueError("Evidence gate must reference proposal id.")
        if not self.evidence_ids:
            raise ValueError("Self-revision proposals require evidence ids.")

    @property
    def missing_evidence_ids(self) -> tuple[str, ...]:
        """Return evidence missing from the proposal gate."""

        return self.evidence_gate.missing_evidence_ids

    @property
    def authority_refs(self) -> tuple[str, ...]:
        """Return authority refs required by target and evidence gate."""

        refs: list[str] = []
        refs.extend(self.target.authority_refs)
        refs.extend(self.evidence_gate.authority_refs)
        return _dedupe_text_tuple(refs, label="authority_ref")

    @property
    def evidence_bundle_ids(self) -> tuple[str, ...]:
        """Return all evidence ids bound to this proposal."""

        evidence: list[str] = list(self.evidence_ids)
        evidence.extend(self.target.evidence_ids)
        evidence.extend(self.impact.evidence_ids)
        evidence.extend(self.evidence_gate.supplied_evidence_ids)
        return _dedupe_text_tuple(evidence, label="evidence_id")

    @property
    def ready_for_human_review(self) -> bool:
        """Return whether proposal is ready for human review."""

        return (
            self.evidence_gate.satisfied
            and not self.target.blocks_revision
            and bool(self.authority_refs)
        )

    @property
    def blocks_revision(self) -> bool:
        """Return whether this proposal must block revision."""

        return self.target.blocks_revision

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic proposal payload."""

        return {
            "authority_refs": list(self.authority_refs),
            "bypasses_review": self.bypasses_review,
            "evidence_bundle_ids": list(self.evidence_bundle_ids),
            "evidence_gate_fingerprint": self.evidence_gate.fingerprint(),
            "evidence_ids": list(self.evidence_ids),
            "impact_fingerprint": self.impact.fingerprint(),
            "missing_evidence_ids": list(self.missing_evidence_ids),
            "modifies_authority_model": self.modifies_authority_model,
            "proposal_id": self.proposal_id,
            "proposed_change_summary": self.proposed_change_summary,
            "rationale": self.rationale,
            "schema_version": self.schema_version,
            "self_authorized": self.self_authorized,
            "target_fingerprint": self.target.fingerprint(),
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this proposal."""

        return _stable_sha256(self.canonical_payload())


@dataclass(frozen=True, slots=True)
class SelfRevisionFinding:
    """Finding produced during self-revision evaluation."""

    finding_id: str
    severity: RevisionFindingSeverity
    summary: str
    evidence_ids: tuple[str, ...]
    blocks_revision: bool = False
    requires_human_review: bool = False
    schema_version: str = WAVE_SEVEN_SELF_REVISION_FINDING_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate self-revision finding severity semantics."""

        object.__setattr__(
            self,
            "finding_id",
            _require_non_empty(self.finding_id, "finding_id"),
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
            "schema_version",
            _require_non_empty(self.schema_version, "schema_version"),
        )
        if not self.evidence_ids:
            raise ValueError("Self-revision findings require evidence ids.")
        if (
            self.severity is RevisionFindingSeverity.BLOCKING
            and not self.blocks_revision
        ):
            raise ValueError("Blocking self-revision findings must block revision.")
        if (
            self.severity is RevisionFindingSeverity.REVIEW_REQUIRED
            and not self.requires_human_review
        ):
            raise ValueError("Review-required findings must require human review.")
        if self.severity is RevisionFindingSeverity.INFO and (
            self.blocks_revision or self.requires_human_review
        ):
            raise ValueError("Info findings cannot block or require review.")

    @property
    def missing_evidence(self) -> bool:
        """Return whether this finding represents missing evidence."""

        return self.severity is RevisionFindingSeverity.MISSING_EVIDENCE

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic finding payload."""

        return {
            "blocks_revision": self.blocks_revision,
            "evidence_ids": list(self.evidence_ids),
            "finding_id": self.finding_id,
            "requires_human_review": self.requires_human_review,
            "schema_version": self.schema_version,
            "severity": self.severity.value,
            "summary": self.summary,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this finding."""

        return _stable_sha256(self.canonical_payload())


@dataclass(frozen=True, slots=True)
class SelfRevisionDecision:
    """Decision for a self-revision proposal."""

    decision_id: str
    proposal: SelfRevisionProposal
    status: SelfRevisionDecisionStatus
    findings: tuple[SelfRevisionFinding, ...]
    required_authority_refs: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    human_review_ref: str = ""
    notes: tuple[str, ...] = ()
    schema_version: str = WAVE_SEVEN_SELF_REVISION_DECISION_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate decision consistency and human-approval boundary."""

        object.__setattr__(
            self,
            "decision_id",
            _require_non_empty(self.decision_id, "decision_id"),
        )
        object.__setattr__(
            self,
            "findings",
            tuple(sorted(self.findings, key=lambda finding: finding.finding_id)),
        )
        object.__setattr__(
            self,
            "required_authority_refs",
            _normalize_unique_text_tuple(
                self.required_authority_refs, label="required_authority_ref"
            ),
        )
        object.__setattr__(
            self,
            "evidence_ids",
            _normalize_unique_text_tuple(self.evidence_ids, label="evidence_id"),
        )
        object.__setattr__(
            self,
            "human_review_ref",
            _normalize_optional_text(self.human_review_ref),
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
        if not self.evidence_ids:
            raise ValueError("Self-revision decisions require evidence ids.")
        _ensure_unique(
            (finding.finding_id for finding in self.findings),
            label="finding_id",
        )
        if self.status is SelfRevisionDecisionStatus.READY_FOR_HUMAN_REVIEW:
            if self.blocking_finding_ids:
                raise ValueError("Review-ready self-revision cannot have blockers.")
            if self.missing_evidence_finding_ids:
                raise ValueError("Review-ready self-revision cannot miss evidence.")
            if not self.required_authority_refs:
                raise ValueError("Review-ready self-revision needs authority refs.")
        if self.status is SelfRevisionDecisionStatus.NEEDS_MORE_EVIDENCE:
            if not self.missing_evidence_finding_ids:
                raise ValueError("Needs-more-evidence decision needs missing evidence.")
        if self.status is SelfRevisionDecisionStatus.BLOCKED:
            if not self.blocking_finding_ids:
                raise ValueError("Blocked self-revision decisions require blockers.")
        if self.status is SelfRevisionDecisionStatus.APPROVED_BY_HUMAN_REVIEW:
            if not self.human_review_ref:
                raise ValueError("Approved self-revisions require human_review_ref.")
            if self.blocking_finding_ids or self.missing_evidence_finding_ids:
                raise ValueError("Approved self-revisions cannot have blockers.")
            if not self.required_authority_refs:
                raise ValueError("Approved self-revisions require authority refs.")
        if self.status is not SelfRevisionDecisionStatus.APPROVED_BY_HUMAN_REVIEW:
            if self.human_review_ref:
                raise ValueError("Only approved self-revisions may include review ref.")

    @property
    def finding_ids(self) -> tuple[str, ...]:
        """Return finding ids."""

        return tuple(finding.finding_id for finding in self.findings)

    @property
    def blocking_finding_ids(self) -> tuple[str, ...]:
        """Return blocking finding ids."""

        return tuple(
            finding.finding_id for finding in self.findings if finding.blocks_revision
        )

    @property
    def review_finding_ids(self) -> tuple[str, ...]:
        """Return review-required finding ids."""

        return tuple(
            finding.finding_id
            for finding in self.findings
            if finding.requires_human_review
        )

    @property
    def missing_evidence_finding_ids(self) -> tuple[str, ...]:
        """Return missing-evidence finding ids."""

        return tuple(
            finding.finding_id for finding in self.findings if finding.missing_evidence
        )

    @property
    def evidence_bundle_ids(self) -> tuple[str, ...]:
        """Return all evidence ids bound to this decision."""

        evidence: list[str] = list(self.evidence_ids)
        evidence.extend(self.proposal.evidence_bundle_ids)
        for finding in self.findings:
            evidence.extend(finding.evidence_ids)
        return _dedupe_text_tuple(evidence, label="evidence_id")

    @property
    def ready_for_review(self) -> bool:
        """Return whether decision is ready for human review."""

        return self.status is SelfRevisionDecisionStatus.READY_FOR_HUMAN_REVIEW

    @property
    def approved(self) -> bool:
        """Return whether human review approved the self-revision."""

        return self.status is SelfRevisionDecisionStatus.APPROVED_BY_HUMAN_REVIEW

    @property
    def blocks_revision(self) -> bool:
        """Return whether decision blocks the self-revision."""

        return self.status is SelfRevisionDecisionStatus.BLOCKED

    @property
    def needs_more_evidence(self) -> bool:
        """Return whether decision needs more evidence."""

        return self.status is SelfRevisionDecisionStatus.NEEDS_MORE_EVIDENCE

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic decision payload."""

        return {
            "blocking_finding_ids": list(self.blocking_finding_ids),
            "decision_id": self.decision_id,
            "evidence_bundle_ids": list(self.evidence_bundle_ids),
            "evidence_ids": list(self.evidence_ids),
            "finding_fingerprints": [
                finding.fingerprint() for finding in self.findings
            ],
            "finding_ids": list(self.finding_ids),
            "human_review_ref": self.human_review_ref,
            "missing_evidence_finding_ids": list(
                self.missing_evidence_finding_ids
            ),
            "notes": list(self.notes),
            "proposal_fingerprint": self.proposal.fingerprint(),
            "required_authority_refs": list(self.required_authority_refs),
            "review_finding_ids": list(self.review_finding_ids),
            "schema_version": self.schema_version,
            "status": self.status.value,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this decision."""

        return _stable_sha256(self.canonical_payload())


@dataclass(frozen=True, slots=True)
class SelfRevisionReport:
    """Review report for self-revision proposals and decisions."""

    report_id: str
    proposals: tuple[SelfRevisionProposal, ...]
    decisions: tuple[SelfRevisionDecision, ...]
    notes: tuple[str, ...] = ()
    schema_version: str = WAVE_SEVEN_SELF_REVISION_REPORT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate report linkage and preserve blockers."""

        object.__setattr__(
            self,
            "report_id",
            _require_non_empty(self.report_id, "report_id"),
        )
        object.__setattr__(
            self,
            "proposals",
            tuple(sorted(self.proposals, key=lambda item: item.proposal_id)),
        )
        object.__setattr__(
            self,
            "decisions",
            tuple(sorted(self.decisions, key=lambda item: item.decision_id)),
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
        if not self.proposals:
            raise ValueError("Self-revision reports require proposals.")
        _ensure_unique(
            (proposal.proposal_id for proposal in self.proposals),
            label="proposal_id",
        )
        _ensure_unique(
            (decision.decision_id for decision in self.decisions),
            label="decision_id",
        )
        proposal_ids = {proposal.proposal_id for proposal in self.proposals}
        for decision in self.decisions:
            if decision.proposal.proposal_id not in proposal_ids:
                raise ValueError("Self-revision decision references missing proposal.")

    @property
    def proposal_ids(self) -> tuple[str, ...]:
        """Return proposal ids."""

        return tuple(proposal.proposal_id for proposal in self.proposals)

    @property
    def decision_ids(self) -> tuple[str, ...]:
        """Return decision ids."""

        return tuple(decision.decision_id for decision in self.decisions)

    @property
    def review_ready_decision_ids(self) -> tuple[str, ...]:
        """Return review-ready decision ids."""

        return tuple(
            decision.decision_id
            for decision in self.decisions
            if decision.ready_for_review
        )

    @property
    def approved_decision_ids(self) -> tuple[str, ...]:
        """Return approved decision ids."""

        return tuple(
            decision.decision_id
            for decision in self.decisions
            if decision.approved
        )

    @property
    def more_evidence_decision_ids(self) -> tuple[str, ...]:
        """Return decisions needing more evidence."""

        return tuple(
            decision.decision_id
            for decision in self.decisions
            if decision.needs_more_evidence
        )

    @property
    def blocked_decision_ids(self) -> tuple[str, ...]:
        """Return blocked decision ids."""

        return tuple(
            decision.decision_id
            for decision in self.decisions
            if decision.blocks_revision
        )

    @property
    def evidence_ids(self) -> tuple[str, ...]:
        """Return all evidence ids bound to this report."""

        evidence: list[str] = []
        for proposal in self.proposals:
            evidence.extend(proposal.evidence_bundle_ids)
        for decision in self.decisions:
            evidence.extend(decision.evidence_bundle_ids)
        return _dedupe_text_tuple(evidence, label="evidence_id")

    @property
    def blocks_claim(self) -> bool:
        """Return whether this report blocks stronger self-revision claims."""

        return bool(self.blocked_decision_ids)

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic report payload."""

        return {
            "approved_decision_ids": list(self.approved_decision_ids),
            "blocked_decision_ids": list(self.blocked_decision_ids),
            "decision_fingerprints": [
                decision.fingerprint() for decision in self.decisions
            ],
            "decision_ids": list(self.decision_ids),
            "evidence_ids": list(self.evidence_ids),
            "more_evidence_decision_ids": list(self.more_evidence_decision_ids),
            "notes": list(self.notes),
            "proposal_fingerprints": [
                proposal.fingerprint() for proposal in self.proposals
            ],
            "proposal_ids": list(self.proposal_ids),
            "report_id": self.report_id,
            "review_ready_decision_ids": list(self.review_ready_decision_ids),
            "schema_version": self.schema_version,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this report."""

        return _stable_sha256(self.canonical_payload())


def evaluate_self_revision(
    *,
    decision_id: str,
    proposal: SelfRevisionProposal,
    supplied_evidence_ids: Iterable[str],
    satisfied_authority_refs: Iterable[str] = (),
    human_review_ref: str = "",
    notes: Iterable[str] = (),
) -> SelfRevisionDecision:
    """Evaluate a self-revision proposal with fail-closed defaults."""

    supplied = set(
        _normalize_unique_text_tuple(supplied_evidence_ids, label="evidence_id")
    )
    satisfied_authorities = set(
        _normalize_unique_text_tuple(satisfied_authority_refs, label="authority_ref")
    )
    findings: list[SelfRevisionFinding] = []

    missing = tuple(
        evidence_id
        for evidence_id in proposal.evidence_gate.required_evidence_ids
        if evidence_id not in supplied
    )
    if missing:
        findings.append(
            SelfRevisionFinding(
                finding_id="missing-revision-evidence",
                severity=RevisionFindingSeverity.MISSING_EVIDENCE,
                summary="Self-revision proposal is missing required evidence.",
                evidence_ids=missing,
            )
        )

    if proposal.target.blocks_revision:
        findings.append(
            SelfRevisionFinding(
                finding_id="immutable-target",
                severity=RevisionFindingSeverity.BLOCKING,
                summary="Revision target is immutable and cannot be changed.",
                evidence_ids=proposal.target.evidence_ids,
                blocks_revision=True,
            )
        )

    if proposal.impact.elevated_review_required:
        findings.append(
            SelfRevisionFinding(
                finding_id="elevated-review-required",
                severity=RevisionFindingSeverity.REVIEW_REQUIRED,
                summary="Self-revision risk or scope requires human review.",
                evidence_ids=proposal.impact.evidence_ids,
                requires_human_review=True,
            )
        )

    required_authority_refs = proposal.authority_refs
    unsatisfied_authority_refs = tuple(
        authority_ref
        for authority_ref in required_authority_refs
        if authority_ref not in satisfied_authorities
    )

    if any(finding.blocks_revision for finding in findings):
        status = SelfRevisionDecisionStatus.BLOCKED
    elif any(finding.missing_evidence for finding in findings):
        status = SelfRevisionDecisionStatus.NEEDS_MORE_EVIDENCE
    elif human_review_ref and not unsatisfied_authority_refs:
        status = SelfRevisionDecisionStatus.APPROVED_BY_HUMAN_REVIEW
    else:
        status = SelfRevisionDecisionStatus.READY_FOR_HUMAN_REVIEW
        if not any(finding.requires_human_review for finding in findings):
            findings.append(
                SelfRevisionFinding(
                    finding_id="human-review-required",
                    severity=RevisionFindingSeverity.REVIEW_REQUIRED,
                    summary="Self-revision requires explicit human review.",
                    evidence_ids=proposal.evidence_ids,
                    requires_human_review=True,
                )
            )

    return SelfRevisionDecision(
        decision_id=decision_id,
        proposal=proposal,
        status=status,
        findings=tuple(findings),
        required_authority_refs=required_authority_refs,
        evidence_ids=tuple(supplied),
        human_review_ref=human_review_ref,
        notes=tuple(notes),
    )


def build_self_revision_report(
    *,
    report_id: str,
    proposals: Iterable[SelfRevisionProposal],
    decisions: Iterable[SelfRevisionDecision],
    notes: Iterable[str] = (),
) -> SelfRevisionReport:
    """Build a deterministic Wave 7 self-revision report."""

    return SelfRevisionReport(
        report_id=report_id,
        proposals=tuple(proposals),
        decisions=tuple(decisions),
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
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return hashlib.sha256(encoded).hexdigest()
