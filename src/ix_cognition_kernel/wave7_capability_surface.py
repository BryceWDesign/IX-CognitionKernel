"""Wave 7 capability surface models.

Capability surfaces map measured skills, operations, surfaces, restrictions,
authority references, stale evidence, and revoked permissions into explicit
reviewable boundaries.

A capability is not authorization. A demonstrated skill is not permission to
use a tool or body surface. Wave 7 keeps those ideas separate so organism-level
growth can be pursued without letting capability claims become execution power.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

WAVE_SEVEN_CAPABILITY_SCOPE_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave7-capability-scope-v1"
)
WAVE_SEVEN_CAPABILITY_RESTRICTION_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave7-capability-restriction-v1"
)
WAVE_SEVEN_CAPABILITY_SURFACE_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave7-capability-surface-v1"
)
WAVE_SEVEN_CAPABILITY_USE_REQUEST_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave7-capability-use-request-v1"
)
WAVE_SEVEN_CAPABILITY_USE_DECISION_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave7-capability-use-decision-v1"
)
WAVE_SEVEN_CAPABILITY_SURFACE_REPORT_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave7-capability-surface-report-v1"
)


class CapabilityStatus(StrEnum):
    """Reviewable status for a capability."""

    UNPROVEN = "unproven"
    ALLOWED = "allowed"
    RESTRICTED = "restricted"
    STALE = "stale"
    REVOKED = "revoked"


class CapabilityRisk(StrEnum):
    """Risk tier for using a capability."""

    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


class CapabilityRestrictionKind(StrEnum):
    """Kinds of restrictions applied to a capability surface."""

    HUMAN_REVIEW_REQUIRED = "human-review-required"
    SIMULATION_ONLY = "simulation-only"
    EVIDENCE_REQUIRED = "evidence-required"
    DOMAIN_LIMITED = "domain-limited"
    SURFACE_LIMITED = "surface-limited"
    REVOKED_OPERATION = "revoked-operation"


class CapabilityUseDecisionStatus(StrEnum):
    """Fail-closed decision for requested capability use."""

    ALLOWED_FOR_SIMULATION = "allowed-for-simulation"
    READY_FOR_HUMAN_REVIEW = "ready-for-human-review"
    NEEDS_MORE_EVIDENCE = "needs-more-evidence"
    BLOCKED = "blocked"


@dataclass(frozen=True, slots=True)
class CapabilityScope:
    """Bounded domain, operation, and surface scope for a capability."""

    scope_id: str
    domain: str
    operations: tuple[str, ...]
    surface_ids: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    authority_refs: tuple[str, ...]
    schema_version: str = WAVE_SEVEN_CAPABILITY_SCOPE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Normalize scope fields and require evidence plus authority."""

        object.__setattr__(
            self,
            "scope_id",
            _require_non_empty(self.scope_id, "scope_id"),
        )
        object.__setattr__(
            self,
            "domain",
            _require_non_empty(self.domain, "domain"),
        )
        object.__setattr__(
            self,
            "operations",
            _normalize_unique_text_tuple(self.operations, label="operation"),
        )
        object.__setattr__(
            self,
            "surface_ids",
            _normalize_unique_text_tuple(self.surface_ids, label="surface_id"),
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
        if not self.operations:
            raise ValueError("Capability scopes require operations.")
        if not self.surface_ids:
            raise ValueError("Capability scopes require surface ids.")
        if not self.evidence_ids:
            raise ValueError("Capability scopes require evidence ids.")
        if not self.authority_refs:
            raise ValueError("Capability scopes require authority refs.")

    def supports(self, *, operation: str, surface_id: str) -> bool:
        """Return whether this scope supports the requested operation."""

        return (
            operation.strip() in self.operations
            and surface_id.strip() in self.surface_ids
        )

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic scope payload for hashing."""

        return {
            "authority_refs": list(self.authority_refs),
            "domain": self.domain,
            "evidence_ids": list(self.evidence_ids),
            "operations": list(self.operations),
            "schema_version": self.schema_version,
            "scope_id": self.scope_id,
            "surface_ids": list(self.surface_ids),
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this scope."""

        return _stable_sha256(self.canonical_payload())


@dataclass(frozen=True, slots=True)
class CapabilityRestriction:
    """Restriction that constrains capability use."""

    restriction_id: str
    kind: CapabilityRestrictionKind
    summary: str
    affected_operations: tuple[str, ...]
    affected_surface_ids: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    authority_refs: tuple[str, ...]
    blocks_use: bool = False
    schema_version: str = WAVE_SEVEN_CAPABILITY_RESTRICTION_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate a capability restriction."""

        object.__setattr__(
            self,
            "restriction_id",
            _require_non_empty(self.restriction_id, "restriction_id"),
        )
        object.__setattr__(
            self,
            "summary",
            _require_non_empty(self.summary, "summary"),
        )
        object.__setattr__(
            self,
            "affected_operations",
            _normalize_unique_text_tuple(
                self.affected_operations, label="affected_operation"
            ),
        )
        object.__setattr__(
            self,
            "affected_surface_ids",
            _normalize_unique_text_tuple(
                self.affected_surface_ids, label="affected_surface_id"
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
        if not self.affected_operations:
            raise ValueError("Capability restrictions require operations.")
        if not self.affected_surface_ids:
            raise ValueError("Capability restrictions require surface ids.")
        if not self.evidence_ids:
            raise ValueError("Capability restrictions require evidence ids.")
        if not self.authority_refs:
            raise ValueError("Capability restrictions require authority refs.")
        if (
            self.kind is CapabilityRestrictionKind.REVOKED_OPERATION
            and not self.blocks_use
        ):
            raise ValueError("Revoked-operation restrictions must block use.")

    def applies_to(self, *, operation: str, surface_id: str) -> bool:
        """Return whether this restriction applies to the requested use."""

        return (
            operation.strip() in self.affected_operations
            and surface_id.strip() in self.affected_surface_ids
        )

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic restriction payload for hashing."""

        return {
            "affected_operations": list(self.affected_operations),
            "affected_surface_ids": list(self.affected_surface_ids),
            "authority_refs": list(self.authority_refs),
            "blocks_use": self.blocks_use,
            "evidence_ids": list(self.evidence_ids),
            "kind": self.kind.value,
            "restriction_id": self.restriction_id,
            "schema_version": self.schema_version,
            "summary": self.summary,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this restriction."""

        return _stable_sha256(self.canonical_payload())


@dataclass(frozen=True, slots=True)
class CapabilitySurface:
    """Measured capability boundary for Wave 7 organism growth."""

    capability_id: str
    name: str
    description: str
    status: CapabilityStatus
    risk: CapabilityRisk
    scopes: tuple[CapabilityScope, ...]
    restrictions: tuple[CapabilityRestriction, ...]
    evidence_ids: tuple[str, ...]
    confidence: float
    stale_reason: str = ""
    revoked_reason: str = ""
    claims_authorization: bool = False
    schema_version: str = WAVE_SEVEN_CAPABILITY_SURFACE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate capability surface without allowing authorization claims."""

        if self.claims_authorization:
            raise ValueError("Capability surfaces must not claim authorization.")
        object.__setattr__(
            self,
            "capability_id",
            _require_non_empty(self.capability_id, "capability_id"),
        )
        object.__setattr__(self, "name", _require_non_empty(self.name, "name"))
        object.__setattr__(
            self,
            "description",
            _require_non_empty(self.description, "description"),
        )
        object.__setattr__(
            self,
            "scopes",
            tuple(sorted(self.scopes, key=lambda scope: scope.scope_id)),
        )
        object.__setattr__(
            self,
            "restrictions",
            tuple(
                sorted(
                    self.restrictions,
                    key=lambda restriction: restriction.restriction_id,
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
            "stale_reason",
            _normalize_optional_text(self.stale_reason),
        )
        object.__setattr__(
            self,
            "revoked_reason",
            _normalize_optional_text(self.revoked_reason),
        )
        object.__setattr__(
            self,
            "schema_version",
            _require_non_empty(self.schema_version, "schema_version"),
        )
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("Capability confidence must be between 0.0 and 1.0.")
        if not self.scopes:
            raise ValueError("Capability surfaces require scopes.")
        if not self.evidence_ids:
            raise ValueError("Capability surfaces require evidence ids.")
        _ensure_unique((scope.scope_id for scope in self.scopes), label="scope_id")
        _ensure_unique(
            (restriction.restriction_id for restriction in self.restrictions),
            label="restriction_id",
        )
        if self.status is CapabilityStatus.STALE and not self.stale_reason:
            raise ValueError("Stale capabilities require stale_reason.")
        if self.status is CapabilityStatus.REVOKED and not self.revoked_reason:
            raise ValueError("Revoked capabilities require revoked_reason.")
        if self.status is CapabilityStatus.UNPROVEN and self.confidence > 0.0:
            raise ValueError("Unproven capabilities must have zero confidence.")
        if self.status is CapabilityStatus.REVOKED and self.confidence > 0.0:
            raise ValueError("Revoked capabilities must have zero confidence.")

    @property
    def scope_ids(self) -> tuple[str, ...]:
        """Return scope ids covered by this capability surface."""

        return tuple(scope.scope_id for scope in self.scopes)

    @property
    def restriction_ids(self) -> tuple[str, ...]:
        """Return restriction ids attached to this capability surface."""

        return tuple(restriction.restriction_id for restriction in self.restrictions)

    @property
    def active_restriction_ids(self) -> tuple[str, ...]:
        """Return restriction ids that block or constrain use."""

        return self.restriction_ids

    @property
    def blocks_use(self) -> bool:
        """Return whether this capability blocks use by status or restriction."""

        return self.status is CapabilityStatus.REVOKED or any(
            restriction.blocks_use for restriction in self.restrictions
        )

    @property
    def needs_more_evidence(self) -> bool:
        """Return whether this capability needs more evidence."""

        return self.status in {CapabilityStatus.UNPROVEN, CapabilityStatus.STALE}

    @property
    def needs_review(self) -> bool:
        """Return whether this capability needs review before use."""

        return (
            self.status is CapabilityStatus.RESTRICTED
            or self.risk in {CapabilityRisk.HIGH, CapabilityRisk.CRITICAL}
            or any(
                restriction.kind is CapabilityRestrictionKind.HUMAN_REVIEW_REQUIRED
                for restriction in self.restrictions
            )
        )

    def supports(self, *, operation: str, surface_id: str) -> bool:
        """Return whether any scope supports the requested use."""

        return any(
            scope.supports(operation=operation, surface_id=surface_id)
            for scope in self.scopes
        )

    def matching_restrictions(
        self, *, operation: str, surface_id: str
    ) -> tuple[CapabilityRestriction, ...]:
        """Return restrictions applying to the requested use."""

        return tuple(
            restriction
            for restriction in self.restrictions
            if restriction.applies_to(operation=operation, surface_id=surface_id)
        )

    @property
    def evidence_bundle_ids(self) -> tuple[str, ...]:
        """Return all evidence ids bound to the capability surface."""

        evidence: list[str] = list(self.evidence_ids)
        for scope in self.scopes:
            evidence.extend(scope.evidence_ids)
        for restriction in self.restrictions:
            evidence.extend(restriction.evidence_ids)
        return _dedupe_text_tuple(evidence, label="evidence_id")

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic capability-surface payload."""

        return {
            "active_restriction_ids": list(self.active_restriction_ids),
            "capability_id": self.capability_id,
            "claims_authorization": self.claims_authorization,
            "confidence": self.confidence,
            "description": self.description,
            "evidence_bundle_ids": list(self.evidence_bundle_ids),
            "evidence_ids": list(self.evidence_ids),
            "name": self.name,
            "restriction_fingerprints": [
                restriction.fingerprint() for restriction in self.restrictions
            ],
            "revoked_reason": self.revoked_reason,
            "risk": self.risk.value,
            "schema_version": self.schema_version,
            "scope_fingerprints": [scope.fingerprint() for scope in self.scopes],
            "stale_reason": self.stale_reason,
            "status": self.status.value,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this surface."""

        return _stable_sha256(self.canonical_payload())


@dataclass(frozen=True, slots=True)
class CapabilityUseRequest:
    """Request to use a capability for a bounded operation."""

    request_id: str
    capability_id: str
    operation: str
    surface_id: str
    purpose: str
    evidence_ids: tuple[str, ...]
    claims_permission: bool = False
    schema_version: str = WAVE_SEVEN_CAPABILITY_USE_REQUEST_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate capability use request without permission claims."""

        if self.claims_permission:
            raise ValueError("Capability use requests must not claim permission.")
        object.__setattr__(
            self,
            "request_id",
            _require_non_empty(self.request_id, "request_id"),
        )
        object.__setattr__(
            self,
            "capability_id",
            _require_non_empty(self.capability_id, "capability_id"),
        )
        object.__setattr__(
            self,
            "operation",
            _require_non_empty(self.operation, "operation"),
        )
        object.__setattr__(
            self,
            "surface_id",
            _require_non_empty(self.surface_id, "surface_id"),
        )
        object.__setattr__(
            self,
            "purpose",
            _require_non_empty(self.purpose, "purpose"),
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
            raise ValueError("Capability use requests require evidence ids.")

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic capability-use-request payload."""

        return {
            "capability_id": self.capability_id,
            "claims_permission": self.claims_permission,
            "evidence_ids": list(self.evidence_ids),
            "operation": self.operation,
            "purpose": self.purpose,
            "request_id": self.request_id,
            "schema_version": self.schema_version,
            "surface_id": self.surface_id,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this request."""

        return _stable_sha256(self.canonical_payload())


@dataclass(frozen=True, slots=True)
class CapabilityUseDecision:
    """Fail-closed decision for requested capability use."""

    decision_id: str
    request: CapabilityUseRequest
    capability: CapabilitySurface
    status: CapabilityUseDecisionStatus
    reasons: tuple[str, ...]
    required_authority_refs: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    matched_restriction_ids: tuple[str, ...] = ()
    schema_version: str = WAVE_SEVEN_CAPABILITY_USE_DECISION_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate use decision linkage and fail-closed state."""

        object.__setattr__(
            self,
            "decision_id",
            _require_non_empty(self.decision_id, "decision_id"),
        )
        object.__setattr__(
            self,
            "reasons",
            _normalize_unique_text_tuple(self.reasons, label="reason"),
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
            "matched_restriction_ids",
            _normalize_unique_text_tuple(
                self.matched_restriction_ids, label="matched_restriction_id"
            ),
        )
        object.__setattr__(
            self,
            "schema_version",
            _require_non_empty(self.schema_version, "schema_version"),
        )
        if self.request.capability_id != self.capability.capability_id:
            raise ValueError("Request and capability ids must match.")
        if not self.reasons:
            raise ValueError("Capability use decisions require reasons.")
        if not self.evidence_ids:
            raise ValueError("Capability use decisions require evidence ids.")
        if self.status is CapabilityUseDecisionStatus.ALLOWED_FOR_SIMULATION:
            if self.required_authority_refs:
                raise ValueError("Simulation decisions cannot require authority refs.")
            if self.matched_restriction_ids:
                raise ValueError(
                    "Simulation decisions cannot have matched restrictions."
                )
        elif not self.required_authority_refs:
            raise ValueError(
                "Non-simulation capability decisions require authority refs."
            )

    @property
    def blocked(self) -> bool:
        """Return whether requested capability use is blocked."""

        return self.status is CapabilityUseDecisionStatus.BLOCKED

    @property
    def ready_for_review(self) -> bool:
        """Return whether the request is ready for human review."""

        return self.status is CapabilityUseDecisionStatus.READY_FOR_HUMAN_REVIEW

    @property
    def needs_more_evidence(self) -> bool:
        """Return whether the request needs more evidence."""

        return self.status is CapabilityUseDecisionStatus.NEEDS_MORE_EVIDENCE

    @property
    def allowed_for_simulation(self) -> bool:
        """Return whether the request is allowed only for simulation."""

        return self.status is CapabilityUseDecisionStatus.ALLOWED_FOR_SIMULATION

    @property
    def evidence_bundle_ids(self) -> tuple[str, ...]:
        """Return all evidence ids bound to this use decision."""

        evidence: list[str] = list(self.evidence_ids)
        evidence.extend(self.request.evidence_ids)
        evidence.extend(self.capability.evidence_bundle_ids)
        return _dedupe_text_tuple(evidence, label="evidence_id")

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic capability-use-decision payload."""

        return {
            "capability_fingerprint": self.capability.fingerprint(),
            "decision_id": self.decision_id,
            "evidence_bundle_ids": list(self.evidence_bundle_ids),
            "evidence_ids": list(self.evidence_ids),
            "matched_restriction_ids": list(self.matched_restriction_ids),
            "reasons": list(self.reasons),
            "request_fingerprint": self.request.fingerprint(),
            "required_authority_refs": list(self.required_authority_refs),
            "schema_version": self.schema_version,
            "status": self.status.value,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this decision."""

        return _stable_sha256(self.canonical_payload())


@dataclass(frozen=True, slots=True)
class CapabilitySurfaceReport:
    """Review report for a set of Wave 7 capability surfaces."""

    report_id: str
    capabilities: tuple[CapabilitySurface, ...]
    decisions: tuple[CapabilityUseDecision, ...]
    notes: tuple[str, ...] = ()
    schema_version: str = WAVE_SEVEN_CAPABILITY_SURFACE_REPORT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate capability report and keep unresolved blockers visible."""

        object.__setattr__(
            self,
            "report_id",
            _require_non_empty(self.report_id, "report_id"),
        )
        object.__setattr__(
            self,
            "capabilities",
            tuple(
                sorted(
                    self.capabilities,
                    key=lambda capability: capability.capability_id,
                )
            ),
        )
        object.__setattr__(
            self,
            "decisions",
            tuple(sorted(self.decisions, key=lambda decision: decision.decision_id)),
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
        if not self.capabilities:
            raise ValueError("Capability surface reports require capabilities.")
        _ensure_unique(
            (capability.capability_id for capability in self.capabilities),
            label="capability_id",
        )
        _ensure_unique(
            (decision.decision_id for decision in self.decisions),
            label="decision_id",
        )

    @property
    def capability_ids(self) -> tuple[str, ...]:
        """Return capability ids in this report."""

        return tuple(capability.capability_id for capability in self.capabilities)

    @property
    def blocked_capability_ids(self) -> tuple[str, ...]:
        """Return capability ids that block use."""

        return tuple(
            capability.capability_id
            for capability in self.capabilities
            if capability.blocks_use
        )

    @property
    def stale_capability_ids(self) -> tuple[str, ...]:
        """Return stale capability ids."""

        return tuple(
            capability.capability_id
            for capability in self.capabilities
            if capability.status is CapabilityStatus.STALE
        )

    @property
    def unproven_capability_ids(self) -> tuple[str, ...]:
        """Return unproven capability ids."""

        return tuple(
            capability.capability_id
            for capability in self.capabilities
            if capability.status is CapabilityStatus.UNPROVEN
        )

    @property
    def review_capability_ids(self) -> tuple[str, ...]:
        """Return capability ids that require review."""

        return tuple(
            capability.capability_id
            for capability in self.capabilities
            if capability.needs_review
        )

    @property
    def decision_ids(self) -> tuple[str, ...]:
        """Return use decision ids in this report."""

        return tuple(decision.decision_id for decision in self.decisions)

    @property
    def blocked_decision_ids(self) -> tuple[str, ...]:
        """Return blocked decision ids."""

        return tuple(
            decision.decision_id for decision in self.decisions if decision.blocked
        )

    @property
    def more_evidence_decision_ids(self) -> tuple[str, ...]:
        """Return decision ids needing more evidence."""

        return tuple(
            decision.decision_id
            for decision in self.decisions
            if decision.needs_more_evidence
        )

    @property
    def ready_for_review_decision_ids(self) -> tuple[str, ...]:
        """Return decision ids ready for human review."""

        return tuple(
            decision.decision_id
            for decision in self.decisions
            if decision.ready_for_review
        )

    @property
    def evidence_ids(self) -> tuple[str, ...]:
        """Return all evidence ids bound to this report."""

        evidence: list[str] = []
        for capability in self.capabilities:
            evidence.extend(capability.evidence_bundle_ids)
        for decision in self.decisions:
            evidence.extend(decision.evidence_bundle_ids)
        return _dedupe_text_tuple(evidence, label="evidence_id")

    @property
    def blocks_claim(self) -> bool:
        """Return whether this report blocks stronger capability claims."""

        return bool(self.blocked_capability_ids or self.blocked_decision_ids)

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic report payload."""

        return {
            "blocked_capability_ids": list(self.blocked_capability_ids),
            "blocked_decision_ids": list(self.blocked_decision_ids),
            "capability_fingerprints": [
                capability.fingerprint() for capability in self.capabilities
            ],
            "capability_ids": list(self.capability_ids),
            "decision_fingerprints": [
                decision.fingerprint() for decision in self.decisions
            ],
            "decision_ids": list(self.decision_ids),
            "evidence_ids": list(self.evidence_ids),
            "more_evidence_decision_ids": list(self.more_evidence_decision_ids),
            "notes": list(self.notes),
            "ready_for_review_decision_ids": list(self.ready_for_review_decision_ids),
            "report_id": self.report_id,
            "review_capability_ids": list(self.review_capability_ids),
            "schema_version": self.schema_version,
            "stale_capability_ids": list(self.stale_capability_ids),
            "unproven_capability_ids": list(self.unproven_capability_ids),
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this report."""

        return _stable_sha256(self.canonical_payload())


def decide_capability_use(
    *,
    decision_id: str,
    request: CapabilityUseRequest,
    capability: CapabilitySurface,
    evidence_ids: Iterable[str],
) -> CapabilityUseDecision:
    """Evaluate requested capability use with fail-closed defaults."""

    reasons: list[str] = []
    authority_refs: list[str] = []
    matched_restrictions = capability.matching_restrictions(
        operation=request.operation,
        surface_id=request.surface_id,
    )

    if request.capability_id != capability.capability_id:
        reasons.append("request-capability-mismatch")
        status = CapabilityUseDecisionStatus.BLOCKED
        authority_refs.extend(_capability_authority_refs(capability))
    elif not capability.supports(
        operation=request.operation, surface_id=request.surface_id
    ):
        reasons.append("capability-scope-does-not-support-use")
        status = CapabilityUseDecisionStatus.BLOCKED
        authority_refs.extend(_capability_authority_refs(capability))
    elif capability.blocks_use or any(
        restriction.blocks_use for restriction in matched_restrictions
    ):
        reasons.append("capability-use-blocked")
        status = CapabilityUseDecisionStatus.BLOCKED
        authority_refs.extend(_capability_authority_refs(capability))
    elif capability.needs_more_evidence:
        reasons.append("capability-needs-more-evidence")
        status = CapabilityUseDecisionStatus.NEEDS_MORE_EVIDENCE
        authority_refs.extend(_capability_authority_refs(capability))
    elif capability.needs_review or matched_restrictions:
        reasons.append("capability-human-review-required")
        status = CapabilityUseDecisionStatus.READY_FOR_HUMAN_REVIEW
        authority_refs.extend(_capability_authority_refs(capability))
        for restriction in matched_restrictions:
            authority_refs.extend(restriction.authority_refs)
    elif capability.status is CapabilityStatus.ALLOWED:
        reasons.append("capability-allowed-for-simulation-only")
        status = CapabilityUseDecisionStatus.ALLOWED_FOR_SIMULATION
    else:
        reasons.append("capability-status-not-sufficient")
        status = CapabilityUseDecisionStatus.NEEDS_MORE_EVIDENCE
        authority_refs.extend(_capability_authority_refs(capability))

    return CapabilityUseDecision(
        decision_id=decision_id,
        request=request,
        capability=capability,
        status=status,
        reasons=tuple(reasons),
        required_authority_refs=_dedupe_text_tuple(
            authority_refs, label="required_authority_ref"
        ),
        evidence_ids=tuple(evidence_ids),
        matched_restriction_ids=tuple(
            restriction.restriction_id for restriction in matched_restrictions
        ),
    )


def build_capability_surface_report(
    *,
    report_id: str,
    capabilities: Iterable[CapabilitySurface],
    decisions: Iterable[CapabilityUseDecision] = (),
    notes: Iterable[str] = (),
) -> CapabilitySurfaceReport:
    """Build a deterministic Wave 7 capability surface report."""

    return CapabilitySurfaceReport(
        report_id=report_id,
        capabilities=tuple(capabilities),
        decisions=tuple(decisions),
        notes=tuple(notes),
    )


def _capability_authority_refs(
    capability: CapabilitySurface,
) -> tuple[str, ...]:
    authority_refs: list[str] = []
    for scope in capability.scopes:
        authority_refs.extend(scope.authority_refs)
    for restriction in capability.restrictions:
        authority_refs.extend(restriction.authority_refs)
    return _dedupe_text_tuple(authority_refs, label="authority_ref")


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
