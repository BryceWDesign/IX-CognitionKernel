"""Wave 7 body contract models.

A body contract represents a bounded surface through which the cognitive
substrate can observe, simulate, ask for review, or propose action. It never
turns intent into permission. It exposes capability grants, authority
requirements, denied proposals, and review requirements before any runtime
handoff can be considered.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

WAVE_SEVEN_BODY_SURFACE_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave7-body-surface-v1"
)
WAVE_SEVEN_OBSERVATION_CHANNEL_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave7-observation-channel-v1"
)
WAVE_SEVEN_CAPABILITY_GRANT_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave7-capability-grant-v1"
)
WAVE_SEVEN_ACTION_PROPOSAL_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave7-action-proposal-v1"
)
WAVE_SEVEN_EXECUTION_BOUNDARY_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave7-execution-boundary-v1"
)
WAVE_SEVEN_BODY_CONTRACT_DECISION_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave7-body-contract-decision-v1"
)


class BodySurfaceKind(StrEnum):
    """Kinds of bounded surfaces a cognitive substrate may model."""

    SIMULATION = "simulation"
    OBSERVATION = "observation"
    REVIEW_PACKET = "review-packet"
    FILESYSTEM_STAGING = "filesystem-staging"
    TOOL_STAGING = "tool-staging"
    MESSAGE_STAGING = "message-staging"
    HUMAN_REVIEW = "human-review"


class BodySurfaceRisk(StrEnum):
    """Risk tier for a body surface."""

    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    PROHIBITED = "prohibited"


class CapabilityGrantStatus(StrEnum):
    """Status of a body capability grant."""

    ALLOWED = "allowed"
    RESTRICTED = "restricted"
    REVIEW_REQUIRED = "review-required"
    REVOKED = "revoked"


class ActionProposalKind(StrEnum):
    """Kinds of proposed interaction with a body surface."""

    OBSERVE = "observe"
    SIMULATE = "simulate"
    PREPARE_REVIEW_PACKET = "prepare-review-packet"
    STAGE_TOOL_CALL = "stage-tool-call"
    STAGE_MESSAGE = "stage-message"
    REQUEST_HUMAN_REVIEW = "request-human-review"


class BodyContractDecisionStatus(StrEnum):
    """Fail-closed decision for a proposed body interaction."""

    ALLOWED_FOR_SIMULATION = "allowed-for-simulation"
    READY_FOR_HUMAN_REVIEW = "ready-for-human-review"
    NEEDS_MORE_EVIDENCE = "needs-more-evidence"
    BLOCKED = "blocked"


@dataclass(frozen=True, slots=True)
class BodySurface:
    """Bounded surface through which cognition may observe or propose action."""

    surface_id: str
    kind: BodySurfaceKind
    name: str
    description: str
    allowed_operations: tuple[str, ...]
    risk: BodySurfaceRisk = BodySurfaceRisk.LOW
    requires_human_review: bool = False
    allows_live_execution: bool = False
    schema_version: str = WAVE_SEVEN_BODY_SURFACE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate body surface without granting uncontrolled execution."""

        if self.allows_live_execution:
            raise ValueError("Body surfaces must not allow live execution directly.")
        object.__setattr__(
            self,
            "surface_id",
            _require_non_empty(self.surface_id, "surface_id"),
        )
        object.__setattr__(self, "name", _require_non_empty(self.name, "name"))
        object.__setattr__(
            self,
            "description",
            _require_non_empty(self.description, "description"),
        )
        object.__setattr__(
            self,
            "allowed_operations",
            _normalize_unique_text_tuple(
                self.allowed_operations, label="allowed_operation"
            ),
        )
        object.__setattr__(
            self,
            "schema_version",
            _require_non_empty(self.schema_version, "schema_version"),
        )
        if not self.allowed_operations:
            raise ValueError("Body surfaces require allowed operations.")
        if self.risk is BodySurfaceRisk.PROHIBITED and not self.requires_human_review:
            raise ValueError("Prohibited body surfaces require human review.")

    @property
    def prohibited(self) -> bool:
        """Return whether this surface is prohibited for direct use."""

        return self.risk is BodySurfaceRisk.PROHIBITED

    def supports(self, operation: str) -> bool:
        """Return whether this surface supports the named operation."""

        return operation.strip() in self.allowed_operations

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic surface payload for hashing."""

        return {
            "allowed_operations": list(self.allowed_operations),
            "allows_live_execution": self.allows_live_execution,
            "description": self.description,
            "kind": self.kind.value,
            "name": self.name,
            "requires_human_review": self.requires_human_review,
            "risk": self.risk.value,
            "schema_version": self.schema_version,
            "surface_id": self.surface_id,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this surface."""

        return _stable_sha256(self.canonical_payload())


@dataclass(frozen=True, slots=True)
class ObservationChannel:
    """Evidence-bound channel for bounded observation."""

    channel_id: str
    surface_id: str
    observable_state_ids: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    description: str
    claims_ground_truth: bool = False
    schema_version: str = WAVE_SEVEN_OBSERVATION_CHANNEL_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate observation channel without claiming ground truth."""

        if self.claims_ground_truth:
            raise ValueError("Observation channels must not claim ground truth.")
        object.__setattr__(
            self,
            "channel_id",
            _require_non_empty(self.channel_id, "channel_id"),
        )
        object.__setattr__(
            self,
            "surface_id",
            _require_non_empty(self.surface_id, "surface_id"),
        )
        object.__setattr__(
            self,
            "observable_state_ids",
            _normalize_unique_text_tuple(
                self.observable_state_ids, label="observable_state_id"
            ),
        )
        object.__setattr__(
            self,
            "evidence_ids",
            _normalize_unique_text_tuple(self.evidence_ids, label="evidence_id"),
        )
        object.__setattr__(
            self,
            "description",
            _require_non_empty(self.description, "description"),
        )
        object.__setattr__(
            self,
            "schema_version",
            _require_non_empty(self.schema_version, "schema_version"),
        )
        if not self.observable_state_ids:
            raise ValueError("Observation channels require observable state ids.")
        if not self.evidence_ids:
            raise ValueError("Observation channels require evidence ids.")

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic observation-channel payload."""

        return {
            "channel_id": self.channel_id,
            "claims_ground_truth": self.claims_ground_truth,
            "description": self.description,
            "evidence_ids": list(self.evidence_ids),
            "observable_state_ids": list(self.observable_state_ids),
            "schema_version": self.schema_version,
            "surface_id": self.surface_id,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this channel."""

        return _stable_sha256(self.canonical_payload())


@dataclass(frozen=True, slots=True)
class CapabilityGrant:
    """Bounded grant that may support an action proposal."""

    grant_id: str
    surface_id: str
    operation: str
    status: CapabilityGrantStatus
    evidence_ids: tuple[str, ...]
    authority_ref: str
    restrictions: tuple[str, ...] = ()
    schema_version: str = WAVE_SEVEN_CAPABILITY_GRANT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate a capability grant with explicit authority."""

        object.__setattr__(
            self,
            "grant_id",
            _require_non_empty(self.grant_id, "grant_id"),
        )
        object.__setattr__(
            self,
            "surface_id",
            _require_non_empty(self.surface_id, "surface_id"),
        )
        object.__setattr__(
            self,
            "operation",
            _require_non_empty(self.operation, "operation"),
        )
        object.__setattr__(
            self,
            "evidence_ids",
            _normalize_unique_text_tuple(self.evidence_ids, label="evidence_id"),
        )
        object.__setattr__(
            self,
            "authority_ref",
            _require_non_empty(self.authority_ref, "authority_ref"),
        )
        object.__setattr__(
            self,
            "restrictions",
            _normalize_unique_text_tuple(self.restrictions, label="restriction"),
        )
        object.__setattr__(
            self,
            "schema_version",
            _require_non_empty(self.schema_version, "schema_version"),
        )
        if not self.evidence_ids:
            raise ValueError("Capability grants require evidence ids.")
        if self.status in {
            CapabilityGrantStatus.RESTRICTED,
            CapabilityGrantStatus.REVIEW_REQUIRED,
        } and not self.restrictions:
            raise ValueError("Restricted or review-required grants need restrictions.")

    @property
    def usable_without_review(self) -> bool:
        """Return whether this grant can support simulation without review."""

        return self.status is CapabilityGrantStatus.ALLOWED

    @property
    def blocks_use(self) -> bool:
        """Return whether this grant blocks proposed use."""

        return self.status is CapabilityGrantStatus.REVOKED

    @property
    def needs_review(self) -> bool:
        """Return whether this grant requires review before use."""

        return self.status is CapabilityGrantStatus.REVIEW_REQUIRED

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic capability-grant payload."""

        return {
            "authority_ref": self.authority_ref,
            "evidence_ids": list(self.evidence_ids),
            "grant_id": self.grant_id,
            "operation": self.operation,
            "restrictions": list(self.restrictions),
            "schema_version": self.schema_version,
            "status": self.status.value,
            "surface_id": self.surface_id,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this grant."""

        return _stable_sha256(self.canonical_payload())


@dataclass(frozen=True, slots=True)
class ActionProposal:
    """Intent-bearing proposal that is not permission."""

    proposal_id: str
    kind: ActionProposalKind
    surface_id: str
    requested_operation: str
    intent_summary: str
    predicted_outcome: str
    evidence_ids: tuple[str, ...]
    required_grant_ids: tuple[str, ...]
    risk_notes: tuple[str, ...] = ()
    self_authorized: bool = False
    claims_permission: bool = False
    schema_version: str = WAVE_SEVEN_ACTION_PROPOSAL_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate proposal without permitting self-authorization."""

        if self.self_authorized:
            raise ValueError("Action proposals must not self-authorize.")
        if self.claims_permission:
            raise ValueError("Action proposals must not claim permission.")
        object.__setattr__(
            self,
            "proposal_id",
            _require_non_empty(self.proposal_id, "proposal_id"),
        )
        object.__setattr__(
            self,
            "surface_id",
            _require_non_empty(self.surface_id, "surface_id"),
        )
        object.__setattr__(
            self,
            "requested_operation",
            _require_non_empty(self.requested_operation, "requested_operation"),
        )
        object.__setattr__(
            self,
            "intent_summary",
            _require_non_empty(self.intent_summary, "intent_summary"),
        )
        object.__setattr__(
            self,
            "predicted_outcome",
            _require_non_empty(self.predicted_outcome, "predicted_outcome"),
        )
        object.__setattr__(
            self,
            "evidence_ids",
            _normalize_unique_text_tuple(self.evidence_ids, label="evidence_id"),
        )
        object.__setattr__(
            self,
            "required_grant_ids",
            _normalize_unique_text_tuple(
                self.required_grant_ids, label="required_grant_id"
            ),
        )
        object.__setattr__(
            self,
            "risk_notes",
            _normalize_unique_text_tuple(self.risk_notes, label="risk_note"),
        )
        object.__setattr__(
            self,
            "schema_version",
            _require_non_empty(self.schema_version, "schema_version"),
        )
        if not self.evidence_ids:
            raise ValueError("Action proposals require evidence ids.")
        if not self.required_grant_ids:
            raise ValueError("Action proposals require capability grant ids.")

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic action-proposal payload."""

        return {
            "claims_permission": self.claims_permission,
            "evidence_ids": list(self.evidence_ids),
            "intent_summary": self.intent_summary,
            "kind": self.kind.value,
            "predicted_outcome": self.predicted_outcome,
            "proposal_id": self.proposal_id,
            "requested_operation": self.requested_operation,
            "required_grant_ids": list(self.required_grant_ids),
            "risk_notes": list(self.risk_notes),
            "schema_version": self.schema_version,
            "self_authorized": self.self_authorized,
            "surface_id": self.surface_id,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this proposal."""

        return _stable_sha256(self.canonical_payload())


@dataclass(frozen=True, slots=True)
class ExecutionBoundary:
    """Boundary that separates staged proposals from deployment authority."""

    boundary_id: str
    surface_id: str
    allowed_decision_statuses: tuple[BodyContractDecisionStatus, ...]
    prohibited_operations: tuple[str, ...]
    required_authority_refs: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    description: str
    schema_version: str = WAVE_SEVEN_EXECUTION_BOUNDARY_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate execution boundary fail-closed requirements."""

        object.__setattr__(
            self,
            "boundary_id",
            _require_non_empty(self.boundary_id, "boundary_id"),
        )
        object.__setattr__(
            self,
            "surface_id",
            _require_non_empty(self.surface_id, "surface_id"),
        )
        allowed_statuses = tuple(
            sorted(set(self.allowed_decision_statuses), key=lambda item: item.value)
        )
        object.__setattr__(self, "allowed_decision_statuses", allowed_statuses)
        object.__setattr__(
            self,
            "prohibited_operations",
            _normalize_unique_text_tuple(
                self.prohibited_operations, label="prohibited_operation"
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
            "evidence_ids",
            _normalize_unique_text_tuple(self.evidence_ids, label="evidence_id"),
        )
        object.__setattr__(
            self,
            "description",
            _require_non_empty(self.description, "description"),
        )
        object.__setattr__(
            self,
            "schema_version",
            _require_non_empty(self.schema_version, "schema_version"),
        )
        if not self.allowed_decision_statuses:
            raise ValueError("Execution boundaries require allowed decisions.")
        if not self.required_authority_refs:
            raise ValueError("Execution boundaries require authority refs.")
        if not self.evidence_ids:
            raise ValueError("Execution boundaries require evidence ids.")
        if BodyContractDecisionStatus.BLOCKED in self.allowed_decision_statuses:
            raise ValueError("Execution boundaries must not allow blocked decisions.")

    def prohibits(self, operation: str) -> bool:
        """Return whether the requested operation is prohibited."""

        return operation.strip() in self.prohibited_operations

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic execution-boundary payload."""

        return {
            "allowed_decision_statuses": [
                status.value for status in self.allowed_decision_statuses
            ],
            "boundary_id": self.boundary_id,
            "description": self.description,
            "evidence_ids": list(self.evidence_ids),
            "prohibited_operations": list(self.prohibited_operations),
            "required_authority_refs": list(self.required_authority_refs),
            "schema_version": self.schema_version,
            "surface_id": self.surface_id,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this boundary."""

        return _stable_sha256(self.canonical_payload())


@dataclass(frozen=True, slots=True)
class BodyContractDecision:
    """Decision for whether a proposed body interaction can proceed."""

    decision_id: str
    proposal: ActionProposal
    surface: BodySurface
    grants: tuple[CapabilityGrant, ...]
    boundary: ExecutionBoundary
    status: BodyContractDecisionStatus
    reasons: tuple[str, ...]
    required_human_authority_refs: tuple[str, ...]
    denied_operations: tuple[str, ...] = ()
    evidence_ids: tuple[str, ...] = ()
    schema_version: str = WAVE_SEVEN_BODY_CONTRACT_DECISION_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate body contract decision and fail closed on mismatches."""

        object.__setattr__(
            self,
            "decision_id",
            _require_non_empty(self.decision_id, "decision_id"),
        )
        object.__setattr__(
            self,
            "grants",
            tuple(sorted(self.grants, key=lambda grant: grant.grant_id)),
        )
        object.__setattr__(
            self,
            "reasons",
            _normalize_unique_text_tuple(self.reasons, label="reason"),
        )
        object.__setattr__(
            self,
            "required_human_authority_refs",
            _normalize_unique_text_tuple(
                self.required_human_authority_refs,
                label="required_human_authority_ref",
            ),
        )
        object.__setattr__(
            self,
            "denied_operations",
            _normalize_unique_text_tuple(
                self.denied_operations, label="denied_operation"
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
        if self.proposal.surface_id != self.surface.surface_id:
            raise ValueError("Proposal and surface ids must match.")
        if self.boundary.surface_id != self.surface.surface_id:
            raise ValueError("Boundary and surface ids must match.")
        _ensure_unique((grant.grant_id for grant in self.grants), label="grant_id")
        if not self.reasons:
            raise ValueError("Body contract decisions require reasons.")
        if not self.evidence_ids:
            raise ValueError("Body contract decisions require evidence ids.")
        if self.status is BodyContractDecisionStatus.BLOCKED:
            if not self.denied_operations:
                raise ValueError("Blocked body decisions require denied operations.")
        elif self.denied_operations:
            raise ValueError("Only blocked body decisions may deny operations.")
        if (
            self.status is not BodyContractDecisionStatus.BLOCKED
            and self.status not in self.boundary.allowed_decision_statuses
        ):
            raise ValueError("Decision status is outside the execution boundary.")
        if self.status is BodyContractDecisionStatus.ALLOWED_FOR_SIMULATION:
            if self.required_human_authority_refs:
                raise ValueError(
                    "Simulation-allowed decisions cannot require human authority."
                )
        elif not self.required_human_authority_refs:
            raise ValueError("Non-simulation decisions require human authority refs.")
        if self.status is not BodyContractDecisionStatus.BLOCKED:
            missing_grant_ids = tuple(
                grant_id
                for grant_id in self.proposal.required_grant_ids
                if grant_id not in {grant.grant_id for grant in self.grants}
            )
            if missing_grant_ids:
                missing = ", ".join(missing_grant_ids)
                raise ValueError(f"Decision missing required grants: {missing}")

    @property
    def evidence_bundle_ids(self) -> tuple[str, ...]:
        """Return all evidence ids bound to the body contract decision."""

        evidence: list[str] = list(self.evidence_ids)
        evidence.extend(self.proposal.evidence_ids)
        evidence.extend(self.boundary.evidence_ids)
        for grant in self.grants:
            evidence.extend(grant.evidence_ids)
        return _normalize_unique_text_tuple(evidence, label="evidence_id")

    @property
    def blocked(self) -> bool:
        """Return whether this body contract blocks the proposal."""

        return self.status is BodyContractDecisionStatus.BLOCKED

    @property
    def ready_for_review(self) -> bool:
        """Return whether this decision is ready for human review."""

        return self.status is BodyContractDecisionStatus.READY_FOR_HUMAN_REVIEW

    @property
    def allowed_for_simulation(self) -> bool:
        """Return whether this decision is only allowed for simulation."""

        return self.status is BodyContractDecisionStatus.ALLOWED_FOR_SIMULATION

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic body-contract decision payload."""

        return {
            "boundary_fingerprint": self.boundary.fingerprint(),
            "decision_id": self.decision_id,
            "denied_operations": list(self.denied_operations),
            "evidence_bundle_ids": list(self.evidence_bundle_ids),
            "evidence_ids": list(self.evidence_ids),
            "grant_fingerprints": [grant.fingerprint() for grant in self.grants],
            "proposal_fingerprint": self.proposal.fingerprint(),
            "reasons": list(self.reasons),
            "required_human_authority_refs": list(
                self.required_human_authority_refs
            ),
            "schema_version": self.schema_version,
            "status": self.status.value,
            "surface_fingerprint": self.surface.fingerprint(),
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this decision."""

        return _stable_sha256(self.canonical_payload())


def decide_body_contract(
    *,
    decision_id: str,
    proposal: ActionProposal,
    surface: BodySurface,
    grants: Iterable[CapabilityGrant],
    boundary: ExecutionBoundary,
    evidence_ids: Iterable[str],
) -> BodyContractDecision:
    """Evaluate a Wave 7 body contract proposal with fail-closed defaults."""

    grant_tuple = tuple(grants)
    reasons: list[str] = []
    required_authority: list[str] = []
    denied_operations: list[str] = []

    if proposal.surface_id != surface.surface_id:
        reasons.append("proposal-surface-mismatch")
        denied_operations.append(proposal.requested_operation)
    if boundary.surface_id != surface.surface_id:
        reasons.append("boundary-surface-mismatch")
        denied_operations.append(proposal.requested_operation)
    if surface.prohibited:
        reasons.append("surface-prohibited")
        required_authority.extend(boundary.required_authority_refs)
        denied_operations.append(proposal.requested_operation)
    if not surface.supports(proposal.requested_operation):
        reasons.append("surface-does-not-support-operation")
        denied_operations.append(proposal.requested_operation)
    if boundary.prohibits(proposal.requested_operation):
        reasons.append("boundary-prohibits-operation")
        denied_operations.append(proposal.requested_operation)

    grant_by_id = {grant.grant_id: grant for grant in grant_tuple}
    for grant_id in proposal.required_grant_ids:
        grant = grant_by_id.get(grant_id)
        if grant is None:
            reasons.append(f"missing-grant:{grant_id}")
            denied_operations.append(proposal.requested_operation)
            continue
        if grant.surface_id != proposal.surface_id:
            reasons.append(f"grant-surface-mismatch:{grant.grant_id}")
            denied_operations.append(proposal.requested_operation)
        if grant.operation != proposal.requested_operation:
            reasons.append(f"grant-operation-mismatch:{grant.grant_id}")
            denied_operations.append(proposal.requested_operation)
        if grant.blocks_use:
            reasons.append(f"grant-revoked:{grant.grant_id}")
            denied_operations.append(proposal.requested_operation)
        if grant.needs_review:
            reasons.append(f"grant-needs-review:{grant.grant_id}")
            required_authority.append(grant.authority_ref)
        if grant.status is CapabilityGrantStatus.RESTRICTED:
            reasons.append(f"grant-restricted:{grant.grant_id}")
            required_authority.append(grant.authority_ref)

    if denied_operations:
        status = BodyContractDecisionStatus.BLOCKED
        required_authority.extend(boundary.required_authority_refs)
        reasons.append("blocked-fail-closed")
    elif required_authority or surface.requires_human_review:
        status = BodyContractDecisionStatus.READY_FOR_HUMAN_REVIEW
        if surface.requires_human_review:
            required_authority.extend(boundary.required_authority_refs)
        reasons.append("human-review-required")
    elif all(grant.usable_without_review for grant in grant_tuple):
        status = BodyContractDecisionStatus.ALLOWED_FOR_SIMULATION
        reasons.append("allowed-for-simulation-only")
    else:
        status = BodyContractDecisionStatus.NEEDS_MORE_EVIDENCE
        required_authority.extend(boundary.required_authority_refs)
        reasons.append("capability-evidence-incomplete")

    return BodyContractDecision(
        decision_id=decision_id,
        proposal=proposal,
        surface=surface,
        grants=grant_tuple,
        boundary=boundary,
        status=status,
        reasons=tuple(reasons),
        required_human_authority_refs=tuple(required_authority),
        denied_operations=tuple(denied_operations),
        evidence_ids=tuple(evidence_ids),
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
