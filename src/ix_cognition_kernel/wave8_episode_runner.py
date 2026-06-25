"""Wave 8 bounded cognition episode runner.

This module introduces the first executable Wave 8 cognition loop. It connects
a bounded environment, a bounded model adapter, an action-draft boundary, and a
replay frame without allowing the model to become truth, authority, completion,
or evidence by itself.

Episode doctrine:

- an episode is bounded and replayable,
- prediction and action proposals precede measured outcome,
- model output must pass through an action-draft boundary,
- environment action must pass through environment assessment,
- measured result is required before learning claims can be promoted,
- blocked paths remain first-class evidence instead of being hidden.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from ix_cognition_kernel.wave8_environment_protocol import (
    BoundedEnvironmentSpec,
    EnvironmentActionResult,
    EnvironmentReplayFrame,
    EnvironmentTransitionStatus,
    build_environment_replay_frame,
)
from ix_cognition_kernel.wave8_environment_protocol import (
    EnvironmentObservation,
)
from ix_cognition_kernel.wave8_model_adapter import (
    BoundedModelOutput,
    DeterministicModelAdapter,
    ModelActionDraft,
    build_model_action_draft,
)

WAVE_EIGHT_EPISODE_STEP_SCHEMA_VERSION = "ix-cognition-kernel-wave8-episode-step-v1"
WAVE_EIGHT_EPISODE_RUN_SCHEMA_VERSION = "ix-cognition-kernel-wave8-episode-run-v1"


class EpisodeStepDecision(StrEnum):
    """Fail-closed decision for a bounded cognition episode step."""

    COMPLETED_REPLAYABLE = "completed-replayable"
    NEEDS_MEASURED_RESULT = "needs-measured-result"
    BLOCKED_MODEL_ACTION_DRAFT = "blocked-model-action-draft"
    BLOCKED_ENVIRONMENT_ACTION = "blocked-environment-action"


class EpisodeRunStatus(StrEnum):
    """Overall status for a bounded cognition episode run."""

    REPLAYABLE = "replayable"
    NEEDS_MEASURED_RESULT = "needs-measured-result"
    BLOCKED = "blocked"


@dataclass(frozen=True, slots=True)
class EpisodeStepTrace:
    """Trace for one bounded cognition step."""

    step_id: str
    step_index: int
    model_output: BoundedModelOutput
    action_draft: ModelActionDraft
    replay_frame: EnvironmentReplayFrame | None
    decision: EpisodeStepDecision
    notes: tuple[str, ...] = ()
    schema_version: str = WAVE_EIGHT_EPISODE_STEP_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate step trace consistency."""

        object.__setattr__(
            self,
            "step_id",
            _require_non_empty(self.step_id, "step_id"),
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
        if self.step_index < 0:
            raise ValueError("step_index must be greater than or equal to zero.")
        if self.decision is EpisodeStepDecision.BLOCKED_MODEL_ACTION_DRAFT:
            if self.replay_frame is not None:
                raise ValueError("Blocked model drafts must not include replay frames.")
        else:
            if self.replay_frame is None:
                raise ValueError("Non-draft-blocked steps require replay frames.")

    @property
    def replayable(self) -> bool:
        """Return whether this step can support later learning claims."""

        return self.decision is EpisodeStepDecision.COMPLETED_REPLAYABLE

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic step trace payload."""

        return {
            "action_draft_fingerprint": self.action_draft.fingerprint(),
            "decision": self.decision.value,
            "model_output_fingerprint": self.model_output.fingerprint(),
            "notes": list(self.notes),
            "replay_frame_fingerprint": (
                self.replay_frame.fingerprint() if self.replay_frame else ""
            ),
            "schema_version": self.schema_version,
            "step_id": self.step_id,
            "step_index": self.step_index,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this step trace."""

        return _stable_sha256(self.canonical_payload())


@dataclass(frozen=True, slots=True)
class BoundedEpisodeRun:
    """Replayable bounded cognition episode run."""

    run_id: str
    episode_id: str
    environment: BoundedEnvironmentSpec
    initial_observation: EnvironmentObservation
    steps: tuple[EpisodeStepTrace, ...]
    terminal: bool = False
    notes: tuple[str, ...] = ()
    schema_version: str = WAVE_EIGHT_EPISODE_RUN_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate episode run identity and trace continuity."""

        object.__setattr__(
            self,
            "run_id",
            _require_non_empty(self.run_id, "run_id"),
        )
        object.__setattr__(
            self,
            "episode_id",
            _require_non_empty(self.episode_id, "episode_id"),
        )
        object.__setattr__(
            self,
            "steps",
            tuple(self.steps),
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
        if not self.steps:
            raise ValueError("Bounded episode runs require at least one step.")
        _require_same_text(
            self.environment.environment_id,
            self.initial_observation.environment_id,
            "environment_id",
        )
        _require_same_text(
            self.episode_id,
            self.initial_observation.episode_id,
            "episode_id",
        )
        for expected_index, step in enumerate(self.steps):
            if step.step_index != expected_index:
                raise ValueError("Episode step indexes must be contiguous.")
            _require_same_text(
                self.episode_id,
                step.model_output.episode_id,
                "episode_id",
            )
            _require_same_text(
                self.environment.environment_id,
                step.model_output.environment_id,
                "environment_id",
            )
            if step.replay_frame is not None:
                _require_same_text(
                    self.environment.environment_id,
                    step.replay_frame.environment.environment_id,
                    "environment_id",
                )
                _require_same_text(
                    self.episode_id,
                    step.replay_frame.observation.episode_id,
                    "episode_id",
                )

    @property
    def status(self) -> EpisodeRunStatus:
        """Return fail-closed status for the episode run."""

        if any(
            step.decision
            in {
                EpisodeStepDecision.BLOCKED_MODEL_ACTION_DRAFT,
                EpisodeStepDecision.BLOCKED_ENVIRONMENT_ACTION,
            }
            for step in self.steps
        ):
            return EpisodeRunStatus.BLOCKED
        if any(
            step.decision is EpisodeStepDecision.NEEDS_MEASURED_RESULT
            for step in self.steps
        ):
            return EpisodeRunStatus.NEEDS_MEASURED_RESULT
        return EpisodeRunStatus.REPLAYABLE

    @property
    def replayable(self) -> bool:
        """Return whether this run can support later learning claims."""

        return self.status is EpisodeRunStatus.REPLAYABLE

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic episode run payload."""

        return {
            "environment_fingerprint": self.environment.fingerprint(),
            "episode_id": self.episode_id,
            "initial_observation_fingerprint": self.initial_observation.fingerprint(),
            "notes": list(self.notes),
            "run_id": self.run_id,
            "schema_version": self.schema_version,
            "status": self.status.value,
            "step_fingerprints": [step.fingerprint() for step in self.steps],
            "terminal": self.terminal,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this episode run."""

        return _stable_sha256(self.canonical_payload())


def run_single_step_episode(
    *,
    run_id: str,
    step_id: str,
    output_id: str,
    draft_id: str,
    action_id: str,
    frame_id: str,
    environment: BoundedEnvironmentSpec,
    observation: EnvironmentObservation,
    adapter: DeterministicModelAdapter,
    result: EnvironmentActionResult | None = None,
    notes: Iterable[str] = (),
) -> BoundedEpisodeRun:
    """Run one bounded cognition step through model, draft, and replay gates."""

    model_output = adapter.generate_output(
        output_id=output_id,
        environment=environment,
        observation=observation,
    )
    action_draft = build_model_action_draft(
        draft_id=draft_id,
        action_id=action_id,
        environment=environment,
        observation=observation,
        model_output=model_output,
    )
    replay_frame = None
    if action_draft.action_proposal is not None:
        replay_frame = build_environment_replay_frame(
            frame_id=frame_id,
            environment=environment,
            observation=observation,
            action=action_draft.action_proposal,
            result=result,
        )

    step = EpisodeStepTrace(
        step_id=step_id,
        step_index=0,
        model_output=model_output,
        action_draft=action_draft,
        replay_frame=replay_frame,
        decision=_step_decision(action_draft=action_draft, replay_frame=replay_frame),
    )
    return BoundedEpisodeRun(
        run_id=run_id,
        episode_id=observation.episode_id,
        environment=environment,
        initial_observation=observation,
        steps=(step,),
        terminal=bool(result and result.terminal),
        notes=tuple(notes),
    )


def _step_decision(
    *,
    action_draft: ModelActionDraft,
    replay_frame: EnvironmentReplayFrame | None,
) -> EpisodeStepDecision:
    if not action_draft.ready:
        return EpisodeStepDecision.BLOCKED_MODEL_ACTION_DRAFT
    if replay_frame is None:
        return EpisodeStepDecision.BLOCKED_ENVIRONMENT_ACTION
    if replay_frame.status is EnvironmentTransitionStatus.BLOCKED:
        return EpisodeStepDecision.BLOCKED_ENVIRONMENT_ACTION
    if replay_frame.status is EnvironmentTransitionStatus.NEEDS_MEASURED_RESULT:
        return EpisodeStepDecision.NEEDS_MEASURED_RESULT
    return EpisodeStepDecision.COMPLETED_REPLAYABLE


def _require_non_empty(value: str, label: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{label} must not be empty.")
    return normalized


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
