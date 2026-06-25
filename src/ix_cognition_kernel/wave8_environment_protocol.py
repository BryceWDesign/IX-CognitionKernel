"""Wave 8 bounded environment protocol.

This module introduces the first Wave 8 surface for the Recursive
Reality-Corrected Learner: bounded environments. It does not run cognition
by itself; it defines the replayable substrate that an episode runner can use
without treating model output as truth, permission, completion, or evidence.

Environment doctrine:

- an environment is a bounded test surface, not the real world,
- an observation is not ground truth,
- an action proposal is not permission,
- a transition must preserve measured evidence,
- live actuation fails closed,
- replayability is required before learning claims can be promoted.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

WAVE_EIGHT_ENVIRONMENT_SPEC_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave8-environment-spec-v1"
)
WAVE_EIGHT_ENVIRONMENT_OBSERVATION_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave8-environment-observation-v1"
)
WAVE_EIGHT_ENVIRONMENT_ACTION_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave8-environment-action-v1"
)
WAVE_EIGHT_ENVIRONMENT_RESULT_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave8-environment-result-v1"
)
WAVE_EIGHT_ENVIRONMENT_REPLAY_FRAME_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave8-environment-replay-frame-v1"
)


class EnvironmentKind(StrEnum):
    """Kinds of bounded environments Wave 8 can reason against."""

    GRID_ABSTRACTION = "grid-abstraction"
    CODE_REPAIR = "code-repair"
    CONTRADICTION_MEMORY = "contradiction-memory"
    PLANNING_WORLD = "planning-world"
    TOOL_USE_SIMULATION = "tool-use-simulation"


class EnvironmentBoundary(StrEnum):
    """Execution boundary for a proposed environment action."""

    OBSERVATION_ONLY = "observation-only"
    SIMULATION_ONLY = "simulation-only"
    REPLAY_ONLY = "replay-only"
    REVIEW_PACKET_ONLY = "review-packet-only"
    LIVE_ACTUATION = "live-actuation"


class EnvironmentActionDecision(StrEnum):
    """Fail-closed decision for an environment action proposal."""

    READY_FOR_BOUNDED_RUN = "ready-for-bounded-run"
    NEEDS_MORE_EVIDENCE = "needs-more-evidence"
    OUT_OF_SCOPE = "out-of-scope"
    BLOCKED_LIVE_ACTUATION = "blocked-live-actuation"
    BLOCKED_SELF_AUTHORITY = "blocked-self-authority"


class EnvironmentTransitionStatus(StrEnum):
    """Replay status for an environment transition."""

    REPLAYABLE = "replayable"
    NEEDS_MEASURED_RESULT = "needs-measured-result"
    BLOCKED = "blocked"


@dataclass(frozen=True, slots=True)
class BoundedEnvironmentSpec:
    """Replayable definition of a bounded task environment."""

    environment_id: str
    kind: EnvironmentKind
    objective: str
    observation_channels: tuple[str, ...]
    action_space_ids: tuple[str, ...]
    scoring_rules: tuple[str, ...]
    reset_evidence_ids: tuple[str, ...]
    permits_live_actuation: bool = False
    hidden_goal: bool = False
    schema_version: str = WAVE_EIGHT_ENVIRONMENT_SPEC_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate the environment boundary."""

        object.__setattr__(
            self,
            "environment_id",
            _require_non_empty(self.environment_id, "environment_id"),
        )
        object.__setattr__(
            self,
            "objective",
            _require_non_empty(self.objective, "objective"),
        )
        object.__setattr__(
            self,
            "observation_channels",
            _normalize_unique_text_tuple(
                self.observation_channels, label="observation_channel"
            ),
        )
        object.__setattr__(
            self,
            "action_space_ids",
            _normalize_unique_text_tuple(self.action_space_ids, label="action_space_id"),
        )
        object.__setattr__(
            self,
            "scoring_rules",
            _normalize_unique_text_tuple(self.scoring_rules, label="scoring_rule"),
        )
        object.__setattr__(
            self,
            "reset_evidence_ids",
            _normalize_unique_text_tuple(
                self.reset_evidence_ids, label="reset_evidence_id"
            ),
        )
        object.__setattr__(
            self,
            "schema_version",
            _require_non_empty(self.schema_version, "schema_version"),
        )
        if not self.observation_channels:
            raise ValueError("Bounded environments require observation channels.")
        if not self.action_space_ids:
            raise ValueError("Bounded environments require action space ids.")
        if not self.scoring_rules:
            raise ValueError("Bounded environments require scoring rules.")
        if not self.reset_evidence_ids:
            raise ValueError("Bounded environments require reset evidence ids.")
        if self.permits_live_actuation:
            raise ValueError("Wave 8 bounded environments must not permit live actuation.")

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic environment payload."""

        return {
            "action_space_ids": list(self.action_space_ids),
            "environment_id": self.environment_id,
            "hidden_goal": self.hidden_goal,
            "kind": self.kind.value,
            "objective": self.objective,
            "observation_channels": list(self.observation_channels),
            "permits_live_actuation": self.permits_live_actuation,
            "reset_evidence_ids": list(self.reset_evidence_ids),
            "schema_version": self.schema_version,
            "scoring_rules": list(self.scoring_rules),
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this environment."""

        return _stable_sha256(self.canonical_payload())


@dataclass(frozen=True, slots=True)
class EnvironmentObservation:
    """Measured or bounded observation from an environment episode."""

    observation_id: str
    environment_id: str
    episode_id: str
    state_id: str
    channel_id: str
    summary: str
    visible_features: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    step_index: int = 0
    measured: bool = False
    claims_ground_truth: bool = False
    schema_version: str = WAVE_EIGHT_ENVIRONMENT_OBSERVATION_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate observation evidence and ground-truth boundary."""

        if self.claims_ground_truth:
            raise ValueError("Environment observations must not claim ground truth.")
        object.__setattr__(
            self,
            "observation_id",
            _require_non_empty(self.observation_id, "observation_id"),
        )
        object.__setattr__(
            self,
            "environment_id",
            _require_non_empty(self.environment_id, "environment_id"),
        )
        object.__setattr__(
            self,
            "episode_id",
            _require_non_empty(self.episode_id, "episode_id"),
        )
        object.__setattr__(
            self,
            "state_id",
            _require_non_empty(self.state_id, "state_id"),
        )
        object.__setattr__(
            self,
            "channel_id",
            _require_non_empty(self.channel_id, "channel_id"),
        )
        object.__setattr__(
            self,
            "summary",
            _require_non_empty(self.summary, "summary"),
        )
        object.__setattr__(
            self,
            "visible_features",
            _normalize_unique_text_tuple(self.visible_features, label="visible_feature"),
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
        if self.step_index < 0:
            raise ValueError("step_index must be greater than or equal to zero.")
        if not self.visible_features:
            raise ValueError("Environment observations require visible features.")
        if not self.evidence_ids:
            raise ValueError("Environment observations require evidence ids.")

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic observation payload."""

        return {
            "channel_id": self.channel_id,
            "claims_ground_truth": self.claims_ground_truth,
            "environment_id": self.environment_id,
            "episode_id": self.episode_id,
            "evidence_ids": list(self.evidence_ids),
            "measured": self.measured,
            "observation_id": self.observation_id,
            "schema_version": self.schema_version,
            "state_id": self.state_id,
            "step_index": self.step_index,
            "summary": self.summary,
            "visible_features": list(self.visible_features),
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this observation."""

        return _stable_sha256(self.canonical_payload())


@dataclass(frozen=True, slots=True)
class EnvironmentActionProposal:
    """Action proposal for a bounded environment transition."""

    action_id: str
    environment_id: str
    episode_id: str
    actor_id: str
    operation_id: str
    rationale: str
    expected_effect: str
    precondition_state_ids: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    boundary: EnvironmentBoundary = EnvironmentBoundary.SIMULATION_ONLY
    self_authorized: bool = False
    claims_completion: bool = False
    schema_version: str = WAVE_EIGHT_ENVIRONMENT_ACTION_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate proposal without granting permission or completion."""

        if self.self_authorized:
            raise ValueError("Environment action proposals must not self-authorize.")
        if self.claims_completion:
            raise ValueError("Environment action proposals must not claim completion.")
        object.__setattr__(
            self,
            "action_id",
            _require_non_empty(self.action_id, "action_id"),
        )
        object.__setattr__(
            self,
            "environment_id",
            _require_non_empty(self.environment_id, "environment_id"),
        )
        object.__setattr__(
            self,
            "episode_id",
            _require_non_empty(self.episode_id, "episode_id"),
        )
        object.__setattr__(
            self,
            "actor_id",
            _require_non_empty(self.actor_id, "actor_id"),
        )
        object.__setattr__(
            self,
            "operation_id",
            _require_non_empty(self.operation_id, "operation_id"),
        )
        object.__setattr__(
            self,
            "rationale",
            _require_non_empty(self.rationale, "rationale"),
        )
        object.__setattr__(
            self,
            "expected_effect",
            _require_non_empty(self.expected_effect, "expected_effect"),
        )
        object.__setattr__(
            self,
            "precondition_state_ids",
            _normalize_unique_text_tuple(
                self.precondition_state_ids, label="precondition_state_id"
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
        if not self.precondition_state_ids:
            raise ValueError("Environment actions require precondition state ids.")
        if not self.evidence_ids:
            raise ValueError("Environment actions require evidence ids.")

    @property
    def requests_live_actuation(self) -> bool:
        """Return whether this proposal attempts live actuation."""

        return self.boundary is EnvironmentBoundary.LIVE_ACTUATION

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic action proposal payload."""

        return {
            "action_id": self.action_id,
            "actor_id": self.actor_id,
            "boundary": self.boundary.value,
            "claims_completion": self.claims_completion,
            "environment_id": self.environment_id,
            "episode_id": self.episode_id,
            "evidence_ids": list(self.evidence_ids),
            "expected_effect": self.expected_effect,
            "operation_id": self.operation_id,
            "precondition_state_ids": list(self.precondition_state_ids),
            "rationale": self.rationale,
            "schema_version": self.schema_version,
            "self_authorized": self.self_authorized,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this action proposal."""

        return _stable_sha256(self.canonical_payload())


@dataclass(frozen=True, slots=True)
class EnvironmentActionResult:
    """Measured result from applying a bounded environment action."""

    result_id: str
    action_id: str
    environment_id: str
    episode_id: str
    prior_state_id: str
    resulting_state_id: str
    outcome_summary: str
    score_delta: float
    evidence_ids: tuple[str, ...]
    terminal: bool = False
    measured: bool = False
    schema_version: str = WAVE_EIGHT_ENVIRONMENT_RESULT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate measured result evidence."""

        object.__setattr__(
            self,
            "result_id",
            _require_non_empty(self.result_id, "result_id"),
        )
        object.__setattr__(
            self,
            "action_id",
            _require_non_empty(self.action_id, "action_id"),
        )
        object.__setattr__(
            self,
            "environment_id",
            _require_non_empty(self.environment_id, "environment_id"),
        )
        object.__setattr__(
            self,
            "episode_id",
            _require_non_empty(self.episode_id, "episode_id"),
        )
        object.__setattr__(
            self,
            "prior_state_id",
            _require_non_empty(self.prior_state_id, "prior_state_id"),
        )
        object.__setattr__(
            self,
            "resulting_state_id",
            _require_non_empty(self.resulting_state_id, "resulting_state_id"),
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
            "schema_version",
            _require_non_empty(self.schema_version, "schema_version"),
        )
        if not self.evidence_ids:
            raise ValueError("Environment action results require evidence ids.")

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic result payload."""

        return {
            "action_id": self.action_id,
            "environment_id": self.environment_id,
            "episode_id": self.episode_id,
            "evidence_ids": list(self.evidence_ids),
            "measured": self.measured,
            "outcome_summary": self.outcome_summary,
            "prior_state_id": self.prior_state_id,
            "result_id": self.result_id,
            "resulting_state_id": self.resulting_state_id,
            "schema_version": self.schema_version,
            "score_delta": self.score_delta,
            "terminal": self.terminal,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this result."""

        return _stable_sha256(self.canonical_payload())


@dataclass(frozen=True, slots=True)
class EnvironmentReplayFrame:
    """Replayable environment transition frame."""

    frame_id: str
    environment: BoundedEnvironmentSpec
    observation: EnvironmentObservation
    action: EnvironmentActionProposal
    result: EnvironmentActionResult | None
    decision: EnvironmentActionDecision
    notes: tuple[str, ...] = ()
    schema_version: str = WAVE_EIGHT_ENVIRONMENT_REPLAY_FRAME_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate replay frame consistency."""

        object.__setattr__(
            self,
            "frame_id",
            _require_non_empty(self.frame_id, "frame_id"),
        )
        object.__setattr__(
            self,
            "notes",
            _dedupe_text_tuple(self.notes, label="note"),
        )
        object.__setattr__(
            self,
            "schema_version",
            _require_non_empty(self.schema_version, "schema_version"),
        )
        _require_same_text(
            self.environment.environment_id,
            self.observation.environment_id,
            "environment_id",
        )
        _require_same_text(
            self.environment.environment_id,
            self.action.environment_id,
            "environment_id",
        )
        _require_same_text(
            self.observation.episode_id,
            self.action.episode_id,
            "episode_id",
        )
        if self.result is not None:
            _require_same_text(
                self.environment.environment_id,
                self.result.environment_id,
                "environment_id",
            )
            _require_same_text(
                self.action.action_id,
                self.result.action_id,
                "action_id",
            )
            _require_same_text(
                self.action.episode_id,
                self.result.episode_id,
                "episode_id",
            )
            _require_same_text(
                self.observation.state_id,
                self.result.prior_state_id,
                "prior_state_id",
            )

    @property
    def status(self) -> EnvironmentTransitionStatus:
        """Return fail-closed replay status for this transition."""

        if self.decision not in {EnvironmentActionDecision.READY_FOR_BOUNDED_RUN}:
            return EnvironmentTransitionStatus.BLOCKED
        if self.result is None or not self.result.measured:
            return EnvironmentTransitionStatus.NEEDS_MEASURED_RESULT
        return EnvironmentTransitionStatus.REPLAYABLE

    @property
    def replayable(self) -> bool:
        """Return whether the frame can support later learning claims."""

        return self.status is EnvironmentTransitionStatus.REPLAYABLE

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic replay frame payload."""

        return {
            "action_fingerprint": self.action.fingerprint(),
            "decision": self.decision.value,
            "environment_fingerprint": self.environment.fingerprint(),
            "frame_id": self.frame_id,
            "notes": list(self.notes),
            "observation_fingerprint": self.observation.fingerprint(),
            "result_fingerprint": self.result.fingerprint() if self.result else "",
            "schema_version": self.schema_version,
            "status": self.status.value,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this replay frame."""

        return _stable_sha256(self.canonical_payload())


def assess_environment_action(
    *,
    environment: BoundedEnvironmentSpec,
    observation: EnvironmentObservation,
    action: EnvironmentActionProposal,
) -> EnvironmentActionDecision:
    """Assess whether an action may run inside a bounded environment."""

    if action.self_authorized:
        return EnvironmentActionDecision.BLOCKED_SELF_AUTHORITY
    if action.requests_live_actuation or environment.permits_live_actuation:
        return EnvironmentActionDecision.BLOCKED_LIVE_ACTUATION
    if environment.environment_id != observation.environment_id:
        return EnvironmentActionDecision.OUT_OF_SCOPE
    if environment.environment_id != action.environment_id:
        return EnvironmentActionDecision.OUT_OF_SCOPE
    if observation.episode_id != action.episode_id:
        return EnvironmentActionDecision.OUT_OF_SCOPE
    if observation.channel_id not in environment.observation_channels:
        return EnvironmentActionDecision.OUT_OF_SCOPE
    if action.operation_id not in environment.action_space_ids:
        return EnvironmentActionDecision.OUT_OF_SCOPE
    if observation.state_id not in action.precondition_state_ids:
        return EnvironmentActionDecision.NEEDS_MORE_EVIDENCE
    if not observation.measured:
        return EnvironmentActionDecision.NEEDS_MORE_EVIDENCE
    return EnvironmentActionDecision.READY_FOR_BOUNDED_RUN


def build_environment_replay_frame(
    *,
    frame_id: str,
    environment: BoundedEnvironmentSpec,
    observation: EnvironmentObservation,
    action: EnvironmentActionProposal,
    result: EnvironmentActionResult | None = None,
    notes: Iterable[str] = (),
) -> EnvironmentReplayFrame:
    """Build a replay frame with a deterministic action decision."""

    decision = assess_environment_action(
        environment=environment,
        observation=observation,
        action=action,
    )
    return EnvironmentReplayFrame(
        frame_id=frame_id,
        environment=environment,
        observation=observation,
        action=action,
        result=result,
        decision=decision,
        notes=tuple(notes),
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


def _require_same_text(left: str, right: str, label: str) -> None:
    if left != right:
        raise ValueError(f"Mismatched {label}: {left} != {right}")


def _stable_sha256(payload: Mapping[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
