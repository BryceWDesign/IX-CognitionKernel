"""Wave 7 observation and action proposal schema.

This module separates observation, intent, prediction, evidence requirements,
and proposal readiness. It strengthens the body-contract layer by making the
observation-to-action chain explicit and replayable before any runtime airlock
or human review decision is allowed to treat a proposal as mature.

The schema preserves these boundaries:

- observation is not ground truth,
- intent is not permission,
- prediction is not evidence,
- readiness is not authorization,
- action proposals cannot self-approve,
- missing evidence fails closed.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

WAVE_SEVEN_OBSERVATION_FRAME_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave7-observation-frame-v1"
)
WAVE_SEVEN_ACTION_INTENT_SCHEMA_VERSION = "ix-cognition-kernel-wave7-action-intent-v1"
WAVE_SEVEN_EVIDENCE_REQUIREMENT_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave7-evidence-requirement-v1"
)
WAVE_SEVEN_ACTION_PROPOSAL_ENVELOPE_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave7-action-proposal-envelope-v1"
)
WAVE_SEVEN_OBSERVED_OUTCOME_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave7-observed-outcome-v1"
)
WAVE_SEVEN_OBSERVATION_ACTION_TRACE_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave7-observation-action-trace-v1"
)


class ObservationReliability(StrEnum):
    """Reliability tier for bounded observations."""

    UNVERIFIED = "unverified"
    PARTIAL = "partial"
    MEASURED = "measured"
    CONTRADICTED = "contradicted"


class ActionIntentKind(StrEnum):
    """Kinds of action intent that may be proposed."""

    OBSERVE = "observe"
    SIMULATE = "simulate"
    STAGE_REVIEW_PACKET = "stage-review-packet"
    REQUEST_HUMAN_REVIEW = "request-human-review"
    NOOP = "noop"


class ProposalRisk(StrEnum):
    """Risk tier for a proposal envelope."""

    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


class EvidenceRequirementStatus(StrEnum):
    """Status for a proposal evidence requirement."""

    SATISFIED = "satisfied"
    MISSING = "missing"
    CONTRADICTED = "contradicted"
    REQUIRES_REVIEW = "requires-review"


class ProposalReadiness(StrEnum):
    """Fail-closed readiness state for an action proposal envelope."""

    DRAFT = "draft"
    READY_FOR_REVIEW = "ready-for-review"
    NEEDS_MORE_EVIDENCE = "needs-more-evidence"
    BLOCKED = "blocked"


class OutcomeAlignment(StrEnum):
    """Relationship between prediction and observed outcome."""

    MATCHED = "matched"
    PARTIAL = "partial"
    MISMATCHED = "mismatched"
    NOT_MEASURED = "not-measured"


@dataclass(frozen=True, slots=True)
class ObservationFrame:
    """Bounded observation frame used by Wave 7 proposal chains."""

    frame_id: str
    surface_id: str
    channel_id: str
    observed_state_ids: tuple[str, ...]
    observation_summary: str
    evidence_ids: tuple[str, ...]
    reliability: ObservationReliability = ObservationReliability.UNVERIFIED
    captured_after_action_id: str = ""
    claims_ground_truth: bool = False
    schema_version: str = WAVE_SEVEN_OBSERVATION_FRAME_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate an observation frame without claiming ground truth."""

        if self.claims_ground_truth:
            raise ValueError("Observation frames must not claim ground truth.")
        object.__setattr__(
            self,
            "frame_id",
            _require_non_empty(self.frame_id, "frame_id"),
        )
        object.__setattr__(
            self,
            "surface_id",
            _require_non_empty(self.surface_id, "surface_id"),
        )
        object.__setattr__(
            self,
            "channel_id",
            _require_non_empty(self.channel_id, "channel_id"),
        )
        object.__setattr__(
            self,
            "observed_state_ids",
            _normalize_unique_text_tuple(
                self.observed_state_ids, label="observed_state_id"
            ),
        )
        object.__setattr__(
            self,
            "observation_summary",
            _require_non_empty(self.observation_summary, "observation_summary"),
        )
        object.__setattr__(
            self,
            "evidence_ids",
            _normalize_unique_text_tuple(self.evidence_ids, label="evidence_id"),
        )
        object.__setattr__(
            self,
            "captured_after_action_id",
            _normalize_optional_text(self.captured_after_action_id),
        )
        object.__setattr__(
            self,
            "schema_version",
            _require_non_empty(self.schema_version, "schema_version"),
        )
        if not self.observed_state_ids:
            raise ValueError("Observation frames require observed state ids.")
        if not self.evidence_ids:
            raise ValueError("Observation frames require evidence ids.")
        if (
            self.reliability is ObservationReliability.MEASURED
            and not self.captured_after_action_id
        ):
            raise ValueError(
                "Measured observation frames require captured_after_action_id."
            )

    @property
    def measured(self) -> bool:
        """Return whether this observation is measured."""

        return self.reliability is ObservationReliability.MEASURED

    @property
    def blocks_claim(self) -> bool:
        """Return whether this observation blocks stronger claims."""

        return self.reliability in {
            ObservationReliability.UNVERIFIED,
            ObservationReliability.CONTRADICTED,
        }

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic observation payload."""

        return {
            "captured_after_action_id": self.captured_after_action_id,
            "channel_id": self.channel_id,
            "claims_ground_truth": self.claims_ground_truth,
            "evidence_ids": list(self.evidence_ids),
            "frame_id": self.frame_id,
            "observation_summary": self.observation_summary,
            "observed_state_ids": list(self.observed_state_ids),
            "reliability": self.reliability.value,
            "schema_version": self.schema_version,
            "surface_id": self.surface_id,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this observation."""

        return _stable_sha256(self.canonical_payload())


@dataclass(frozen=True, slots=True)
class ActionIntent:
    """Intent record that must not become permission by itself."""

    intent_id: str
    kind: ActionIntentKind
    surface_id: str
    requested_operation: str
    purpose: str
    expected_state_change: str
    evidence_ids: tuple[str, ...]
    originating_observation_ids: tuple[str, ...]
    self_authorized: bool = False
    claims_permission: bool = False
    schema_version: str = WAVE_SEVEN_ACTION_INTENT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate action intent without allowing self-authorization."""

        if self.self_authorized:
            raise ValueError("Action intents must not self-authorize.")
        if self.claims_permission:
            raise ValueError("Action intents must not claim permission.")
        object.__setattr__(
            self,
            "intent_id",
            _require_non_empty(self.intent_id, "intent_id"),
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
            "purpose",
            _require_non_empty(self.purpose, "purpose"),
        )
        object.__setattr__(
            self,
            "expected_state_change",
            _require_non_empty(self.expected_state_change, "expected_state_change"),
        )
        object.__setattr__(
            self,
            "evidence_ids",
            _normalize_unique_text_tuple(self.evidence_ids, label="evidence_id"),
        )
        object.__setattr__(
            self,
            "originating_observation_ids",
            _normalize_unique_text_tuple(
                self.originating_observation_ids,
                label="originating_observation_id",
            ),
        )
        object.__setattr__(
            self,
            "schema_version",
            _require_non_empty(self.schema_version, "schema_version"),
        )
        if not self.evidence_ids:
            raise ValueError("Action intents require evidence ids.")
        if (
            self.kind is not ActionIntentKind.NOOP
            and not self.originating_observation_ids
        ):
            raise ValueError("Non-noop action intents require observation ids.")

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic intent payload."""

        return {
            "claims_permission": self.claims_permission,
            "evidence_ids": list(self.evidence_ids),
            "expected_state_change": self.expected_state_change,
            "intent_id": self.intent_id,
            "kind": self.kind.value,
            "originating_observation_ids": list(self.originating_observation_ids),
            "purpose": self.purpose,
            "requested_operation": self.requested_operation,
            "schema_version": self.schema_version,
            "self_authorized": self.self_authorized,
            "surface_id": self.surface_id,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this intent."""

        return _stable_sha256(self.canonical_payload())


@dataclass(frozen=True, slots=True)
class ProposalEvidenceRequirement:
    """Evidence requirement that controls proposal readiness."""

    requirement_id: str
    description: str
    required_evidence_kinds: tuple[str, ...]
    satisfied_evidence_ids: tuple[str, ...]
    status: EvidenceRequirementStatus = EvidenceRequirementStatus.MISSING
    authority_refs: tuple[str, ...] = ()
    schema_version: str = WAVE_SEVEN_EVIDENCE_REQUIREMENT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate evidence requirement state."""

        object.__setattr__(
            self,
            "requirement_id",
            _require_non_empty(self.requirement_id, "requirement_id"),
        )
        object.__setattr__(
            self,
            "description",
            _require_non_empty(self.description, "description"),
        )
        object.__setattr__(
            self,
            "required_evidence_kinds",
            _normalize_unique_text_tuple(
                self.required_evidence_kinds, label="required_evidence_kind"
            ),
        )
        object.__setattr__(
            self,
            "satisfied_evidence_ids",
            _normalize_unique_text_tuple(
                self.satisfied_evidence_ids, label="satisfied_evidence_id"
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
        if not self.required_evidence_kinds:
            raise ValueError("Evidence requirements require evidence kinds.")
        if (
            self.status is EvidenceRequirementStatus.SATISFIED
            and not self.satisfied_evidence_ids
        ):
            raise ValueError("Satisfied requirements need evidence ids.")
        if (
            self.status is EvidenceRequirementStatus.REQUIRES_REVIEW
            and not self.authority_refs
        ):
            raise ValueError("Review-required evidence needs authority refs.")
        if (
            self.status
            in {
                EvidenceRequirementStatus.MISSING,
                EvidenceRequirementStatus.CONTRADICTED,
            }
            and self.satisfied_evidence_ids
        ):
            raise ValueError(
                "Missing or contradicted requirements cannot have satisfied ids."
            )

    @property
    def satisfied(self) -> bool:
        """Return whether this requirement is satisfied."""

        return self.status is EvidenceRequirementStatus.SATISFIED

    @property
    def needs_review(self) -> bool:
        """Return whether this requirement needs human review."""

        return self.status is EvidenceRequirementStatus.REQUIRES_REVIEW

    @property
    def blocks_readiness(self) -> bool:
        """Return whether this requirement blocks proposal readiness."""

        return self.status in {
            EvidenceRequirementStatus.MISSING,
            EvidenceRequirementStatus.CONTRADICTED,
        }

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic evidence-requirement payload."""

        return {
            "authority_refs": list(self.authority_refs),
            "description": self.description,
            "required_evidence_kinds": list(self.required_evidence_kinds),
            "requirement_id": self.requirement_id,
            "satisfied_evidence_ids": list(self.satisfied_evidence_ids),
            "schema_version": self.schema_version,
            "status": self.status.value,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this requirement."""

        return _stable_sha256(self.canonical_payload())


@dataclass(frozen=True, slots=True)
class ActionProposalEnvelope:
    """Proposal envelope connecting observations, intent, and evidence needs."""

    envelope_id: str
    intent: ActionIntent
    observations: tuple[ObservationFrame, ...]
    evidence_requirements: tuple[ProposalEvidenceRequirement, ...]
    risk: ProposalRisk
    predicted_outcome: str
    readiness: ProposalReadiness
    reviewer_notes: tuple[str, ...] = ()
    schema_version: str = WAVE_SEVEN_ACTION_PROPOSAL_ENVELOPE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate proposal envelope readiness with fail-closed semantics."""

        object.__setattr__(
            self,
            "envelope_id",
            _require_non_empty(self.envelope_id, "envelope_id"),
        )
        object.__setattr__(
            self,
            "observations",
            tuple(sorted(self.observations, key=lambda frame: frame.frame_id)),
        )
        object.__setattr__(
            self,
            "evidence_requirements",
            tuple(
                sorted(
                    self.evidence_requirements,
                    key=lambda requirement: requirement.requirement_id,
                )
            ),
        )
        object.__setattr__(
            self,
            "predicted_outcome",
            _require_non_empty(self.predicted_outcome, "predicted_outcome"),
        )
        object.__setattr__(
            self,
            "reviewer_notes",
            _normalize_unique_text_tuple(self.reviewer_notes, label="reviewer_note"),
        )
        object.__setattr__(
            self,
            "schema_version",
            _require_non_empty(self.schema_version, "schema_version"),
        )
        if not self.observations:
            raise ValueError("Action proposal envelopes require observations.")
        if not self.evidence_requirements:
            raise ValueError("Action proposal envelopes require evidence requirements.")
        _ensure_unique(
            (frame.frame_id for frame in self.observations), label="frame_id"
        )
        _ensure_unique(
            (requirement.requirement_id for requirement in self.evidence_requirements),
            label="requirement_id",
        )
        observation_ids = {frame.frame_id for frame in self.observations}
        missing_observations = tuple(
            observation_id
            for observation_id in self.intent.originating_observation_ids
            if observation_id not in observation_ids
        )
        if missing_observations:
            missing = ", ".join(missing_observations)
            raise ValueError(f"Envelope missing intent observations: {missing}")

        if self.readiness is ProposalReadiness.READY_FOR_REVIEW:
            if self.blocking_requirement_ids:
                raise ValueError("Ready envelopes cannot have blocking requirements.")
            if self.blocking_observation_ids:
                raise ValueError("Ready envelopes cannot have blocking observations.")
            if not self.required_authority_refs:
                raise ValueError("Ready envelopes require authority refs.")
        if self.readiness is ProposalReadiness.BLOCKED and not (
            self.blocking_requirement_ids or self.blocking_observation_ids
        ):
            raise ValueError("Blocked envelopes require blocking evidence.")

    @property
    def observation_ids(self) -> tuple[str, ...]:
        """Return observation frame ids in this envelope."""

        return tuple(frame.frame_id for frame in self.observations)

    @property
    def requirement_ids(self) -> tuple[str, ...]:
        """Return evidence requirement ids in this envelope."""

        return tuple(
            requirement.requirement_id for requirement in self.evidence_requirements
        )

    @property
    def blocking_observation_ids(self) -> tuple[str, ...]:
        """Return observation ids that block stronger claims."""

        return tuple(
            frame.frame_id for frame in self.observations if frame.blocks_claim
        )

    @property
    def blocking_requirement_ids(self) -> tuple[str, ...]:
        """Return evidence requirement ids that block readiness."""

        return tuple(
            requirement.requirement_id
            for requirement in self.evidence_requirements
            if requirement.blocks_readiness
        )

    @property
    def review_requirement_ids(self) -> tuple[str, ...]:
        """Return evidence requirement ids requiring human review."""

        return tuple(
            requirement.requirement_id
            for requirement in self.evidence_requirements
            if requirement.needs_review
        )

    @property
    def required_authority_refs(self) -> tuple[str, ...]:
        """Return authority refs required by review requirements."""

        authority_refs: list[str] = []
        for requirement in self.evidence_requirements:
            authority_refs.extend(requirement.authority_refs)
        return _dedupe_text_tuple(authority_refs, label="authority_ref")

    @property
    def evidence_ids(self) -> tuple[str, ...]:
        """Return all evidence ids in the proposal envelope."""

        evidence: list[str] = list(self.intent.evidence_ids)
        for frame in self.observations:
            evidence.extend(frame.evidence_ids)
        for requirement in self.evidence_requirements:
            evidence.extend(requirement.satisfied_evidence_ids)
        return _dedupe_text_tuple(evidence, label="evidence_id")

    @property
    def ready_for_review(self) -> bool:
        """Return whether this envelope is ready for human review."""

        return self.readiness is ProposalReadiness.READY_FOR_REVIEW

    @property
    def blocks_claim(self) -> bool:
        """Return whether this envelope blocks stronger proposal claims."""

        return self.readiness is ProposalReadiness.BLOCKED or bool(
            self.blocking_observation_ids or self.blocking_requirement_ids
        )

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic proposal-envelope payload."""

        return {
            "blocking_observation_ids": list(self.blocking_observation_ids),
            "blocking_requirement_ids": list(self.blocking_requirement_ids),
            "envelope_id": self.envelope_id,
            "evidence_ids": list(self.evidence_ids),
            "evidence_requirement_fingerprints": [
                requirement.fingerprint() for requirement in self.evidence_requirements
            ],
            "intent_fingerprint": self.intent.fingerprint(),
            "observation_fingerprints": [
                frame.fingerprint() for frame in self.observations
            ],
            "predicted_outcome": self.predicted_outcome,
            "readiness": self.readiness.value,
            "required_authority_refs": list(self.required_authority_refs),
            "review_requirement_ids": list(self.review_requirement_ids),
            "reviewer_notes": list(self.reviewer_notes),
            "risk": self.risk.value,
            "schema_version": self.schema_version,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this envelope."""

        return _stable_sha256(self.canonical_payload())


@dataclass(frozen=True, slots=True)
class ObservedOutcome:
    """Measured or unmeasured outcome attached to an action proposal envelope."""

    outcome_id: str
    envelope_id: str
    outcome_summary: str
    evidence_ids: tuple[str, ...]
    alignment: OutcomeAlignment
    measured_state_ids: tuple[str, ...] = ()
    lesson: str = ""
    schema_version: str = WAVE_SEVEN_OBSERVED_OUTCOME_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate outcome measurement discipline."""

        object.__setattr__(
            self,
            "outcome_id",
            _require_non_empty(self.outcome_id, "outcome_id"),
        )
        object.__setattr__(
            self,
            "envelope_id",
            _require_non_empty(self.envelope_id, "envelope_id"),
        )
        object.__setattr__(
            self,
            "outcome_summary",
            _require_non_empty(self.outcome_summary, "outcome_summary"),
        )
        object.__setattr__(
            self,
            "evidence_ids",
            _normalize_unique_text_tuple(self.evidence_ids, label="evidence_id"),
        )
        object.__setattr__(
            self,
            "measured_state_ids",
            _normalize_unique_text_tuple(
                self.measured_state_ids, label="measured_state_id"
            ),
        )
        object.__setattr__(
            self,
            "lesson",
            _normalize_optional_text(self.lesson),
        )
        object.__setattr__(
            self,
            "schema_version",
            _require_non_empty(self.schema_version, "schema_version"),
        )
        if not self.evidence_ids:
            raise ValueError("Observed outcomes require evidence ids.")
        if self.alignment is OutcomeAlignment.NOT_MEASURED:
            if self.measured_state_ids:
                raise ValueError("Unmeasured outcomes cannot have measured states.")
        elif not self.measured_state_ids:
            raise ValueError("Measured outcomes require measured state ids.")
        if (
            self.alignment
            in {
                OutcomeAlignment.PARTIAL,
                OutcomeAlignment.MISMATCHED,
            }
            and not self.lesson
        ):
            raise ValueError("Partial or mismatched outcomes require a lesson.")

    @property
    def measured(self) -> bool:
        """Return whether this outcome was measured."""

        return self.alignment is not OutcomeAlignment.NOT_MEASURED

    @property
    def changes_future_reasoning(self) -> bool:
        """Return whether outcome includes a future-reasoning lesson."""

        return bool(self.lesson)

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic observed-outcome payload."""

        return {
            "alignment": self.alignment.value,
            "envelope_id": self.envelope_id,
            "evidence_ids": list(self.evidence_ids),
            "lesson": self.lesson,
            "measured_state_ids": list(self.measured_state_ids),
            "outcome_id": self.outcome_id,
            "outcome_summary": self.outcome_summary,
            "schema_version": self.schema_version,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this outcome."""

        return _stable_sha256(self.canonical_payload())


@dataclass(frozen=True, slots=True)
class ObservationActionTrace:
    """Replayable chain from observation through proposal and outcome."""

    trace_id: str
    envelope: ActionProposalEnvelope
    outcome: ObservedOutcome | None = None
    notes: tuple[str, ...] = ()
    schema_version: str = WAVE_SEVEN_OBSERVATION_ACTION_TRACE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate observation-action trace linkage."""

        object.__setattr__(
            self,
            "trace_id",
            _require_non_empty(self.trace_id, "trace_id"),
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
        if self.outcome and self.outcome.envelope_id != self.envelope.envelope_id:
            raise ValueError("Trace outcome must reference the envelope id.")

    @property
    def evidence_ids(self) -> tuple[str, ...]:
        """Return all evidence ids bound to this trace."""

        evidence: list[str] = list(self.envelope.evidence_ids)
        if self.outcome:
            evidence.extend(self.outcome.evidence_ids)
        return _dedupe_text_tuple(evidence, label="evidence_id")

    @property
    def complete(self) -> bool:
        """Return whether trace has an outcome."""

        return self.outcome is not None

    @property
    def measured(self) -> bool:
        """Return whether trace has a measured outcome."""

        return bool(self.outcome and self.outcome.measured)

    @property
    def blocks_claim(self) -> bool:
        """Return whether trace blocks stronger readiness claims."""

        return self.envelope.blocks_claim or not self.measured

    @property
    def changes_future_reasoning(self) -> bool:
        """Return whether trace includes a future-reasoning lesson."""

        return bool(self.outcome and self.outcome.changes_future_reasoning)

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic trace payload."""

        return {
            "blocks_claim": self.blocks_claim,
            "changes_future_reasoning": self.changes_future_reasoning,
            "complete": self.complete,
            "envelope_fingerprint": self.envelope.fingerprint(),
            "evidence_ids": list(self.evidence_ids),
            "measured": self.measured,
            "notes": list(self.notes),
            "outcome_fingerprint": self.outcome.fingerprint() if self.outcome else "",
            "schema_version": self.schema_version,
            "trace_id": self.trace_id,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this trace."""

        return _stable_sha256(self.canonical_payload())


def assess_proposal_readiness(
    *,
    observations: Iterable[ObservationFrame],
    requirements: Iterable[ProposalEvidenceRequirement],
    risk: ProposalRisk,
) -> ProposalReadiness:
    """Assess action proposal readiness with fail-closed defaults."""

    observation_tuple = tuple(observations)
    requirement_tuple = tuple(requirements)
    if not observation_tuple or not requirement_tuple:
        return ProposalReadiness.NEEDS_MORE_EVIDENCE
    if any(
        frame.reliability is ObservationReliability.CONTRADICTED
        for frame in observation_tuple
    ):
        return ProposalReadiness.BLOCKED
    if any(
        requirement.status is EvidenceRequirementStatus.CONTRADICTED
        for requirement in requirement_tuple
    ):
        return ProposalReadiness.BLOCKED
    if any(requirement.blocks_readiness for requirement in requirement_tuple):
        return ProposalReadiness.NEEDS_MORE_EVIDENCE
    if any(
        frame.reliability is ObservationReliability.UNVERIFIED
        for frame in observation_tuple
    ):
        return ProposalReadiness.NEEDS_MORE_EVIDENCE
    if risk in {ProposalRisk.HIGH, ProposalRisk.CRITICAL}:
        return ProposalReadiness.READY_FOR_REVIEW
    if any(requirement.needs_review for requirement in requirement_tuple):
        return ProposalReadiness.READY_FOR_REVIEW
    return ProposalReadiness.READY_FOR_REVIEW


def build_observation_action_trace(
    *,
    trace_id: str,
    envelope: ActionProposalEnvelope,
    outcome: ObservedOutcome | None = None,
    notes: Iterable[str] = (),
) -> ObservationActionTrace:
    """Build a Wave 7 observation-action trace."""

    return ObservationActionTrace(
        trace_id=trace_id,
        envelope=envelope,
        outcome=outcome,
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
