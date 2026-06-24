"""Wave 7 runtime airlock.

The runtime airlock is the authority membrane between cognition and any bounded
body, tool, surface, review packet, or execution-adjacent handoff. It can allow
simulation, route to human review, request more evidence, or block. It never
creates deployment permission by itself.

Wave 7 airlock doctrine:

- intent is not permission,
- capability is not authorization,
- simulation permission is not deployment permission,
- missing evidence fails closed,
- authority requirements must remain explicit,
- self-authorization is blocked,
- runtime handoff is reviewable and replayable.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

WAVE_SEVEN_RUNTIME_AIRLOCK_REQUEST_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave7-runtime-airlock-request-v1"
)
WAVE_SEVEN_AIRLOCK_FINDING_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave7-airlock-finding-v1"
)
WAVE_SEVEN_AIRLOCK_AUTHORITY_REQUIREMENT_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave7-airlock-authority-requirement-v1"
)
WAVE_SEVEN_RUNTIME_AIRLOCK_DECISION_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave7-runtime-airlock-decision-v1"
)
WAVE_SEVEN_AIRLOCK_REPORT_SCHEMA_VERSION = "ix-cognition-kernel-wave7-airlock-report-v1"


class AirlockRequestKind(StrEnum):
    """Kinds of runtime-adjacent requests that may enter the airlock."""

    SIMULATION = "simulation"
    OBSERVATION = "observation"
    REVIEW_PACKET = "review-packet"
    BODY_HANDOFF = "body-handoff"
    TOOL_STAGING = "tool-staging"
    MESSAGE_STAGING = "message-staging"
    SELF_REVISION_STAGING = "self-revision-staging"


class AirlockFindingSeverity(StrEnum):
    """Severity of a runtime airlock finding."""

    INFO = "info"
    REVIEW_REQUIRED = "review-required"
    MISSING_EVIDENCE = "missing-evidence"
    BLOCKING = "blocking"


class AirlockDecisionStatus(StrEnum):
    """Fail-closed runtime airlock decision status."""

    ALLOWED_FOR_SIMULATION = "allowed-for-simulation"
    READY_FOR_HUMAN_REVIEW = "ready-for-human-review"
    NEEDS_MORE_EVIDENCE = "needs-more-evidence"
    BLOCKED = "blocked"


@dataclass(frozen=True, slots=True)
class RuntimeAirlockRequest:
    """Request to move a cognitive proposal toward a bounded runtime surface."""

    request_id: str
    kind: AirlockRequestKind
    subject_id: str
    surface_id: str
    proposed_operation: str
    intent_summary: str
    evidence_ids: tuple[str, ...]
    upstream_decision_ids: tuple[str, ...]
    required_authority_refs: tuple[str, ...]
    requests_deployment: bool = False
    self_authorized: bool = False
    claims_permission: bool = False
    schema_version: str = WAVE_SEVEN_RUNTIME_AIRLOCK_REQUEST_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate request boundaries before any airlock decision."""

        if self.self_authorized:
            raise ValueError("Runtime airlock requests must not self-authorize.")
        if self.claims_permission:
            raise ValueError("Runtime airlock requests must not claim permission.")
        object.__setattr__(
            self,
            "request_id",
            _require_non_empty(self.request_id, "request_id"),
        )
        object.__setattr__(
            self,
            "subject_id",
            _require_non_empty(self.subject_id, "subject_id"),
        )
        object.__setattr__(
            self,
            "surface_id",
            _require_non_empty(self.surface_id, "surface_id"),
        )
        object.__setattr__(
            self,
            "proposed_operation",
            _require_non_empty(self.proposed_operation, "proposed_operation"),
        )
        object.__setattr__(
            self,
            "intent_summary",
            _require_non_empty(self.intent_summary, "intent_summary"),
        )
        object.__setattr__(
            self,
            "evidence_ids",
            _normalize_unique_text_tuple(self.evidence_ids, label="evidence_id"),
        )
        object.__setattr__(
            self,
            "upstream_decision_ids",
            _normalize_unique_text_tuple(
                self.upstream_decision_ids, label="upstream_decision_id"
            ),
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
            "schema_version",
            _require_non_empty(self.schema_version, "schema_version"),
        )
        if not self.evidence_ids:
            raise ValueError("Runtime airlock requests require evidence ids.")
        if (
            self.kind is not AirlockRequestKind.SIMULATION
            and not self.upstream_decision_ids
        ):
            raise ValueError("Non-simulation airlock requests need upstream decisions.")
        if self.requests_deployment and not self.required_authority_refs:
            raise ValueError("Deployment requests require authority refs.")

    @property
    def simulation_only(self) -> bool:
        """Return whether this request is simulation-only."""

        return (
            self.kind is AirlockRequestKind.SIMULATION and not self.requests_deployment
        )

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic request payload."""

        return {
            "claims_permission": self.claims_permission,
            "evidence_ids": list(self.evidence_ids),
            "intent_summary": self.intent_summary,
            "kind": self.kind.value,
            "proposed_operation": self.proposed_operation,
            "request_id": self.request_id,
            "requests_deployment": self.requests_deployment,
            "required_authority_refs": list(self.required_authority_refs),
            "schema_version": self.schema_version,
            "self_authorized": self.self_authorized,
            "subject_id": self.subject_id,
            "surface_id": self.surface_id,
            "upstream_decision_ids": list(self.upstream_decision_ids),
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this request."""

        return _stable_sha256(self.canonical_payload())


@dataclass(frozen=True, slots=True)
class AirlockFinding:
    """Reviewable finding produced by the runtime airlock."""

    finding_id: str
    severity: AirlockFindingSeverity
    summary: str
    evidence_ids: tuple[str, ...]
    blocks_handoff: bool = False
    requires_human_review: bool = False
    schema_version: str = WAVE_SEVEN_AIRLOCK_FINDING_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate airlock finding fail-closed semantics."""

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
            raise ValueError("Airlock findings require evidence ids.")
        if self.severity is AirlockFindingSeverity.BLOCKING and not self.blocks_handoff:
            raise ValueError("Blocking airlock findings must block handoff.")
        if (
            self.severity is AirlockFindingSeverity.REVIEW_REQUIRED
            and not self.requires_human_review
        ):
            raise ValueError("Review-required findings must require human review.")
        if self.severity is AirlockFindingSeverity.INFO and (
            self.blocks_handoff or self.requires_human_review
        ):
            raise ValueError("Info findings cannot block or require review.")

    @property
    def needs_more_evidence(self) -> bool:
        """Return whether this finding requests more evidence."""

        return self.severity is AirlockFindingSeverity.MISSING_EVIDENCE

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic finding payload."""

        return {
            "blocks_handoff": self.blocks_handoff,
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
class AirlockAuthorityRequirement:
    """Authority requirement that must remain explicit at runtime boundary."""

    requirement_id: str
    authority_ref: str
    reason: str
    evidence_ids: tuple[str, ...]
    satisfied_by_review_ref: str = ""
    schema_version: str = WAVE_SEVEN_AIRLOCK_AUTHORITY_REQUIREMENT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate authority requirement evidence."""

        object.__setattr__(
            self,
            "requirement_id",
            _require_non_empty(self.requirement_id, "requirement_id"),
        )
        object.__setattr__(
            self,
            "authority_ref",
            _require_non_empty(self.authority_ref, "authority_ref"),
        )
        object.__setattr__(
            self,
            "reason",
            _require_non_empty(self.reason, "reason"),
        )
        object.__setattr__(
            self,
            "evidence_ids",
            _normalize_unique_text_tuple(self.evidence_ids, label="evidence_id"),
        )
        object.__setattr__(
            self,
            "satisfied_by_review_ref",
            _normalize_optional_text(self.satisfied_by_review_ref),
        )
        object.__setattr__(
            self,
            "schema_version",
            _require_non_empty(self.schema_version, "schema_version"),
        )
        if not self.evidence_ids:
            raise ValueError("Airlock authority requirements need evidence ids.")

    @property
    def satisfied(self) -> bool:
        """Return whether this authority requirement has review satisfaction."""

        return bool(self.satisfied_by_review_ref)

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic authority-requirement payload."""

        return {
            "authority_ref": self.authority_ref,
            "evidence_ids": list(self.evidence_ids),
            "reason": self.reason,
            "requirement_id": self.requirement_id,
            "satisfied_by_review_ref": self.satisfied_by_review_ref,
            "schema_version": self.schema_version,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this authority requirement."""

        return _stable_sha256(self.canonical_payload())


@dataclass(frozen=True, slots=True)
class RuntimeAirlockDecision:
    """Runtime airlock decision for a bounded handoff request."""

    decision_id: str
    request: RuntimeAirlockRequest
    status: AirlockDecisionStatus
    findings: tuple[AirlockFinding, ...]
    authority_requirements: tuple[AirlockAuthorityRequirement, ...]
    evidence_ids: tuple[str, ...]
    notes: tuple[str, ...] = ()
    schema_version: str = WAVE_SEVEN_RUNTIME_AIRLOCK_DECISION_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate runtime decision consistency."""

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
            "authority_requirements",
            tuple(
                sorted(
                    self.authority_requirements,
                    key=lambda requirement: requirement.requirement_id,
                )
            ),
        )
        object.__setattr__(
            self,
            "evidence_ids",
            _normalize_unique_text_tuple(self.evidence_ids, label="evidence_id"),
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
            raise ValueError("Runtime airlock decisions require evidence ids.")
        _ensure_unique(
            (finding.finding_id for finding in self.findings),
            label="finding_id",
        )
        _ensure_unique(
            (requirement.requirement_id for requirement in self.authority_requirements),
            label="requirement_id",
        )
        if self.status is AirlockDecisionStatus.ALLOWED_FOR_SIMULATION:
            if self.blocking_finding_ids:
                raise ValueError("Simulation-allowed airlock cannot have blockers.")
            if self.missing_evidence_finding_ids:
                raise ValueError("Simulation-allowed airlock cannot miss evidence.")
            if self.unsatisfied_authority_refs:
                raise ValueError("Simulation-allowed airlock cannot require authority.")
            if self.request.requests_deployment:
                raise ValueError("Deployment requests cannot be simulation-allowed.")
        if self.status is AirlockDecisionStatus.READY_FOR_HUMAN_REVIEW:
            if self.blocking_finding_ids:
                raise ValueError("Review-ready airlock cannot have blockers.")
            if not self.authority_requirements:
                raise ValueError("Review-ready airlock needs authority requirements.")
        if (
            self.status is AirlockDecisionStatus.NEEDS_MORE_EVIDENCE
            and not self.missing_evidence_finding_ids
        ):
            raise ValueError("Needs-more-evidence airlock needs missing evidence.")
        if (
            self.status is AirlockDecisionStatus.BLOCKED
            and not self.blocking_finding_ids
        ):
            raise ValueError("Blocked airlock decisions require blockers.")

    @property
    def finding_ids(self) -> tuple[str, ...]:
        """Return finding ids attached to this decision."""

        return tuple(finding.finding_id for finding in self.findings)

    @property
    def authority_requirement_ids(self) -> tuple[str, ...]:
        """Return authority requirement ids."""

        return tuple(
            requirement.requirement_id for requirement in self.authority_requirements
        )

    @property
    def blocking_finding_ids(self) -> tuple[str, ...]:
        """Return finding ids that block handoff."""

        return tuple(
            finding.finding_id for finding in self.findings if finding.blocks_handoff
        )

    @property
    def review_finding_ids(self) -> tuple[str, ...]:
        """Return finding ids that require human review."""

        return tuple(
            finding.finding_id
            for finding in self.findings
            if finding.requires_human_review
        )

    @property
    def missing_evidence_finding_ids(self) -> tuple[str, ...]:
        """Return finding ids that request more evidence."""

        return tuple(
            finding.finding_id
            for finding in self.findings
            if finding.needs_more_evidence
        )

    @property
    def unsatisfied_authority_refs(self) -> tuple[str, ...]:
        """Return authority refs not yet satisfied by review."""

        return _normalize_unique_text_tuple(
            (
                requirement.authority_ref
                for requirement in self.authority_requirements
                if not requirement.satisfied
            ),
            label="authority_ref",
        )

    @property
    def evidence_bundle_ids(self) -> tuple[str, ...]:
        """Return all evidence ids bound to this decision."""

        evidence: list[str] = list(self.evidence_ids)
        evidence.extend(self.request.evidence_ids)
        for finding in self.findings:
            evidence.extend(finding.evidence_ids)
        for requirement in self.authority_requirements:
            evidence.extend(requirement.evidence_ids)
        return _dedupe_text_tuple(evidence, label="evidence_id")

    @property
    def allowed_for_simulation(self) -> bool:
        """Return whether request is allowed only for simulation."""

        return self.status is AirlockDecisionStatus.ALLOWED_FOR_SIMULATION

    @property
    def ready_for_review(self) -> bool:
        """Return whether request is ready for human review."""

        return self.status is AirlockDecisionStatus.READY_FOR_HUMAN_REVIEW

    @property
    def blocks_handoff(self) -> bool:
        """Return whether request is blocked."""

        return self.status is AirlockDecisionStatus.BLOCKED

    @property
    def needs_more_evidence(self) -> bool:
        """Return whether request needs more evidence."""

        return self.status is AirlockDecisionStatus.NEEDS_MORE_EVIDENCE

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic decision payload."""

        return {
            "authority_requirement_fingerprints": [
                requirement.fingerprint() for requirement in self.authority_requirements
            ],
            "authority_requirement_ids": list(self.authority_requirement_ids),
            "blocking_finding_ids": list(self.blocking_finding_ids),
            "decision_id": self.decision_id,
            "evidence_bundle_ids": list(self.evidence_bundle_ids),
            "evidence_ids": list(self.evidence_ids),
            "finding_fingerprints": [
                finding.fingerprint() for finding in self.findings
            ],
            "finding_ids": list(self.finding_ids),
            "missing_evidence_finding_ids": list(self.missing_evidence_finding_ids),
            "notes": list(self.notes),
            "request_fingerprint": self.request.fingerprint(),
            "review_finding_ids": list(self.review_finding_ids),
            "schema_version": self.schema_version,
            "status": self.status.value,
            "unsatisfied_authority_refs": list(self.unsatisfied_authority_refs),
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this runtime decision."""

        return _stable_sha256(self.canonical_payload())


@dataclass(frozen=True, slots=True)
class AirlockReport:
    """Review report for Wave 7 runtime airlock decisions."""

    report_id: str
    decisions: tuple[RuntimeAirlockDecision, ...]
    notes: tuple[str, ...] = ()
    schema_version: str = WAVE_SEVEN_AIRLOCK_REPORT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate report and preserve blocked airlock decisions."""

        object.__setattr__(
            self,
            "report_id",
            _require_non_empty(self.report_id, "report_id"),
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
        if not self.decisions:
            raise ValueError("Airlock reports require decisions.")
        _ensure_unique(
            (decision.decision_id for decision in self.decisions),
            label="decision_id",
        )

    @property
    def decision_ids(self) -> tuple[str, ...]:
        """Return decision ids in this report."""

        return tuple(decision.decision_id for decision in self.decisions)

    @property
    def simulation_allowed_decision_ids(self) -> tuple[str, ...]:
        """Return simulation-allowed decision ids."""

        return tuple(
            decision.decision_id
            for decision in self.decisions
            if decision.allowed_for_simulation
        )

    @property
    def review_ready_decision_ids(self) -> tuple[str, ...]:
        """Return review-ready decision ids."""

        return tuple(
            decision.decision_id
            for decision in self.decisions
            if decision.ready_for_review
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
            if decision.blocks_handoff
        )

    @property
    def evidence_ids(self) -> tuple[str, ...]:
        """Return all evidence ids bound to this report."""

        evidence: list[str] = []
        for decision in self.decisions:
            evidence.extend(decision.evidence_bundle_ids)
        return _dedupe_text_tuple(evidence, label="evidence_id")

    @property
    def blocks_claim(self) -> bool:
        """Return whether this report blocks stronger runtime claims."""

        return bool(self.blocked_decision_ids)

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic report payload."""

        return {
            "blocked_decision_ids": list(self.blocked_decision_ids),
            "decision_fingerprints": [
                decision.fingerprint() for decision in self.decisions
            ],
            "decision_ids": list(self.decision_ids),
            "evidence_ids": list(self.evidence_ids),
            "more_evidence_decision_ids": list(self.more_evidence_decision_ids),
            "notes": list(self.notes),
            "report_id": self.report_id,
            "review_ready_decision_ids": list(self.review_ready_decision_ids),
            "schema_version": self.schema_version,
            "simulation_allowed_decision_ids": list(
                self.simulation_allowed_decision_ids
            ),
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this report."""

        return _stable_sha256(self.canonical_payload())


def evaluate_runtime_airlock(
    *,
    decision_id: str,
    request: RuntimeAirlockRequest,
    supplied_evidence_ids: Iterable[str],
    satisfied_authority_refs: Iterable[str] = (),
    notes: Iterable[str] = (),
) -> RuntimeAirlockDecision:
    """Evaluate a runtime airlock request with fail-closed defaults."""

    supplied = set(
        _normalize_unique_text_tuple(supplied_evidence_ids, label="evidence_id")
    )
    satisfied_authorities = set(
        _normalize_unique_text_tuple(satisfied_authority_refs, label="authority_ref")
    )
    findings: list[AirlockFinding] = []
    requirements: list[AirlockAuthorityRequirement] = []

    missing_request_evidence = tuple(
        evidence_id
        for evidence_id in request.evidence_ids
        if evidence_id not in supplied
    )
    if missing_request_evidence:
        findings.append(
            AirlockFinding(
                finding_id="missing-request-evidence",
                severity=AirlockFindingSeverity.MISSING_EVIDENCE,
                summary="Runtime request is missing required evidence.",
                evidence_ids=missing_request_evidence,
            )
        )

    if request.requests_deployment:
        findings.append(
            AirlockFinding(
                finding_id="deployment-requested",
                severity=AirlockFindingSeverity.BLOCKING,
                summary="Runtime airlock cannot authorize deployment.",
                evidence_ids=request.evidence_ids,
                blocks_handoff=True,
            )
        )

    if request.kind in {
        AirlockRequestKind.BODY_HANDOFF,
        AirlockRequestKind.TOOL_STAGING,
        AirlockRequestKind.MESSAGE_STAGING,
        AirlockRequestKind.SELF_REVISION_STAGING,
    }:
        findings.append(
            AirlockFinding(
                finding_id="human-review-required",
                severity=AirlockFindingSeverity.REVIEW_REQUIRED,
                summary="Runtime-adjacent handoff requires human review.",
                evidence_ids=request.evidence_ids,
                requires_human_review=True,
            )
        )

    if (
        not request.upstream_decision_ids
        and request.kind is not AirlockRequestKind.SIMULATION
    ):
        findings.append(
            AirlockFinding(
                finding_id="missing-upstream-decision",
                severity=AirlockFindingSeverity.MISSING_EVIDENCE,
                summary="Non-simulation handoff needs upstream decision evidence.",
                evidence_ids=request.evidence_ids,
            )
        )

    for index, authority_ref in enumerate(request.required_authority_refs, start=1):
        requirements.append(
            AirlockAuthorityRequirement(
                requirement_id=f"authority-{index}",
                authority_ref=authority_ref,
                reason="Runtime boundary requires explicit human authority.",
                evidence_ids=request.evidence_ids,
                satisfied_by_review_ref=authority_ref
                if authority_ref in satisfied_authorities
                else "",
            )
        )

    blocking = any(finding.blocks_handoff for finding in findings)
    missing = any(finding.needs_more_evidence for finding in findings)
    review = any(finding.requires_human_review for finding in findings) or any(
        not requirement.satisfied for requirement in requirements
    )

    if blocking:
        status = AirlockDecisionStatus.BLOCKED
    elif missing:
        status = AirlockDecisionStatus.NEEDS_MORE_EVIDENCE
    elif review:
        status = AirlockDecisionStatus.READY_FOR_HUMAN_REVIEW
    else:
        status = AirlockDecisionStatus.ALLOWED_FOR_SIMULATION

    if not findings:
        findings.append(
            AirlockFinding(
                finding_id="simulation-only-boundary",
                severity=AirlockFindingSeverity.INFO,
                summary="Request is allowed only within bounded simulation.",
                evidence_ids=request.evidence_ids,
            )
        )

    return RuntimeAirlockDecision(
        decision_id=decision_id,
        request=request,
        status=status,
        findings=tuple(findings),
        authority_requirements=tuple(requirements),
        evidence_ids=tuple(supplied),
        notes=tuple(notes),
    )


def build_airlock_report(
    *,
    report_id: str,
    decisions: Iterable[RuntimeAirlockDecision],
    notes: Iterable[str] = (),
) -> AirlockReport:
    """Build a deterministic Wave 7 runtime airlock report."""

    return AirlockReport(
        report_id=report_id,
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
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
