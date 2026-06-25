"""Wave 8 bounded model adapter.

The Wave 8 episode runner must be able to use a model without pretending the
model is truth, authority, completion, or evidence. This module defines the
model-facing boundary for the Recursive Reality-Corrected Learner.

Adapter doctrine:

- a model output is a draft, not a decision,
- a selected operation is a proposal, not permission,
- confidence is not evidence,
- the adapter must be deterministic under the same inputs,
- unsupported environments and operations fail closed,
- action proposals remain bounded to environment protocol surfaces.
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
    EnvironmentActionProposal,
    EnvironmentBoundary,
    EnvironmentObservation,
)

WAVE_EIGHT_MODEL_OUTPUT_SCHEMA_VERSION = "ix-cognition-kernel-wave8-model-output-v1"
WAVE_EIGHT_MODEL_ACTION_DRAFT_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave8-model-action-draft-v1"
)
WAVE_EIGHT_DETERMINISTIC_MODEL_POLICY_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave8-deterministic-model-policy-v1"
)


class ModelOutputConfidence(StrEnum):
    """Evidence-aware confidence tier for bounded model output."""

    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"


class ModelActionDraftDecision(StrEnum):
    """Fail-closed decision for converting model output to an action proposal."""

    READY_FOR_ACTION_PROPOSAL = "ready-for-action-proposal"
    NEEDS_OBSERVATION_EVIDENCE = "needs-observation-evidence"
    UNSUPPORTED_OPERATION = "unsupported-operation"
    OUT_OF_SCOPE = "out-of-scope"
    BLOCKED_AUTHORITY_CLAIM = "blocked-authority-claim"
    BLOCKED_TRUTH_CLAIM = "blocked-truth-claim"
    BLOCKED_COMPLETION_CLAIM = "blocked-completion-claim"


@dataclass(frozen=True, slots=True)
class BoundedModelOutput:
    """Draft output from a model adapter before permission or action."""

    output_id: str
    adapter_id: str
    environment_id: str
    episode_id: str
    observation_id: str
    selected_operation_id: str
    rationale: str
    expected_effect: str
    assumptions: tuple[str, ...]
    uncertainty_ids: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    confidence: ModelOutputConfidence = ModelOutputConfidence.LOW
    claims_truth: bool = False
    claims_authority: bool = False
    claims_completion: bool = False
    schema_version: str = WAVE_EIGHT_MODEL_OUTPUT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate model output boundaries."""

        if self.claims_truth:
            raise ValueError("Bounded model output must not claim truth.")
        if self.claims_authority:
            raise ValueError("Bounded model output must not claim authority.")
        if self.claims_completion:
            raise ValueError("Bounded model output must not claim completion.")
        object.__setattr__(
            self,
            "output_id",
            _require_non_empty(self.output_id, "output_id"),
        )
        object.__setattr__(
            self,
            "adapter_id",
            _require_non_empty(self.adapter_id, "adapter_id"),
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
            "observation_id",
            _require_non_empty(self.observation_id, "observation_id"),
        )
        object.__setattr__(
            self,
            "selected_operation_id",
            _require_non_empty(self.selected_operation_id, "selected_operation_id"),
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
            "assumptions",
            _normalize_unique_text_tuple(self.assumptions, label="assumption"),
        )
        object.__setattr__(
            self,
            "uncertainty_ids",
            _normalize_unique_text_tuple(self.uncertainty_ids, label="uncertainty_id"),
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
        if not self.assumptions:
            raise ValueError("Bounded model output requires assumptions.")
        if not self.uncertainty_ids:
            raise ValueError("Bounded model output requires uncertainty ids.")
        if not self.evidence_ids:
            raise ValueError("Bounded model output requires evidence ids.")

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic model output payload."""

        return {
            "adapter_id": self.adapter_id,
            "assumptions": list(self.assumptions),
            "claims_authority": self.claims_authority,
            "claims_completion": self.claims_completion,
            "claims_truth": self.claims_truth,
            "confidence": self.confidence.value,
            "environment_id": self.environment_id,
            "episode_id": self.episode_id,
            "evidence_ids": list(self.evidence_ids),
            "expected_effect": self.expected_effect,
            "observation_id": self.observation_id,
            "output_id": self.output_id,
            "rationale": self.rationale,
            "schema_version": self.schema_version,
            "selected_operation_id": self.selected_operation_id,
            "uncertainty_ids": list(self.uncertainty_ids),
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this output."""

        return _stable_sha256(self.canonical_payload())


@dataclass(frozen=True, slots=True)
class ModelActionDraft:
    """Action proposal draft derived from bounded model output."""

    draft_id: str
    model_output: BoundedModelOutput
    decision: ModelActionDraftDecision
    action_proposal: EnvironmentActionProposal | None = None
    notes: tuple[str, ...] = ()
    schema_version: str = WAVE_EIGHT_MODEL_ACTION_DRAFT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate draft consistency."""

        object.__setattr__(
            self,
            "draft_id",
            _require_non_empty(self.draft_id, "draft_id"),
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
        if self.decision is ModelActionDraftDecision.READY_FOR_ACTION_PROPOSAL:
            if self.action_proposal is None:
                raise ValueError("Ready model action drafts require an action proposal.")
            _require_same_text(
                self.model_output.environment_id,
                self.action_proposal.environment_id,
                "environment_id",
            )
            _require_same_text(
                self.model_output.episode_id,
                self.action_proposal.episode_id,
                "episode_id",
            )
            _require_same_text(
                self.model_output.adapter_id,
                self.action_proposal.actor_id,
                "adapter_id",
            )
            _require_same_text(
                self.model_output.selected_operation_id,
                self.action_proposal.operation_id,
                "operation_id",
            )
        elif self.action_proposal is not None:
            raise ValueError("Blocked model action drafts must not include proposals.")

    @property
    def ready(self) -> bool:
        """Return whether the draft can enter environment action assessment."""

        return self.decision is ModelActionDraftDecision.READY_FOR_ACTION_PROPOSAL

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic action draft payload."""

        return {
            "action_proposal_fingerprint": (
                self.action_proposal.fingerprint() if self.action_proposal else ""
            ),
            "decision": self.decision.value,
            "draft_id": self.draft_id,
            "model_output_fingerprint": self.model_output.fingerprint(),
            "notes": list(self.notes),
            "schema_version": self.schema_version,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this action draft."""

        return _stable_sha256(self.canonical_payload())


@dataclass(frozen=True, slots=True)
class DeterministicModelPolicy:
    """Deterministic policy fixture for model-adapter tests and baselines."""

    policy_id: str
    supported_environment_ids: tuple[str, ...]
    operation_preferences: tuple[str, ...]
    rationale_template: str
    expected_effect_template: str
    evidence_ids: tuple[str, ...]
    assumptions: tuple[str, ...]
    uncertainty_ids: tuple[str, ...]
    schema_version: str = WAVE_EIGHT_DETERMINISTIC_MODEL_POLICY_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate deterministic model policy."""

        object.__setattr__(
            self,
            "policy_id",
            _require_non_empty(self.policy_id, "policy_id"),
        )
        object.__setattr__(
            self,
            "supported_environment_ids",
            _normalize_unique_text_tuple(
                self.supported_environment_ids, label="supported_environment_id"
            ),
        )
        object.__setattr__(
            self,
            "operation_preferences",
            _normalize_unique_text_tuple(
                self.operation_preferences, label="operation_preference"
            ),
        )
        object.__setattr__(
            self,
            "rationale_template",
            _require_non_empty(self.rationale_template, "rationale_template"),
        )
        object.__setattr__(
            self,
            "expected_effect_template",
            _require_non_empty(
                self.expected_effect_template, "expected_effect_template"
            ),
        )
        object.__setattr__(
            self,
            "evidence_ids",
            _normalize_unique_text_tuple(self.evidence_ids, label="evidence_id"),
        )
        object.__setattr__(
            self,
            "assumptions",
            _normalize_unique_text_tuple(self.assumptions, label="assumption"),
        )
        object.__setattr__(
            self,
            "uncertainty_ids",
            _normalize_unique_text_tuple(self.uncertainty_ids, label="uncertainty_id"),
        )
        object.__setattr__(
            self,
            "schema_version",
            _require_non_empty(self.schema_version, "schema_version"),
        )
        if not self.supported_environment_ids:
            raise ValueError("Model policies require supported environment ids.")
        if not self.operation_preferences:
            raise ValueError("Model policies require operation preferences.")
        if not self.evidence_ids:
            raise ValueError("Model policies require evidence ids.")
        if not self.assumptions:
            raise ValueError("Model policies require assumptions.")
        if not self.uncertainty_ids:
            raise ValueError("Model policies require uncertainty ids.")

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic model policy payload."""

        return {
            "assumptions": list(self.assumptions),
            "evidence_ids": list(self.evidence_ids),
            "expected_effect_template": self.expected_effect_template,
            "operation_preferences": list(self.operation_preferences),
            "policy_id": self.policy_id,
            "rationale_template": self.rationale_template,
            "schema_version": self.schema_version,
            "supported_environment_ids": list(self.supported_environment_ids),
            "uncertainty_ids": list(self.uncertainty_ids),
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this policy."""

        return _stable_sha256(self.canonical_payload())


@dataclass(frozen=True, slots=True)
class DeterministicModelAdapter:
    """Deterministic model adapter for bounded Wave 8 episode trials."""

    adapter_id: str
    policy: DeterministicModelPolicy

    def __post_init__(self) -> None:
        """Validate adapter identity."""

        object.__setattr__(
            self,
            "adapter_id",
            _require_non_empty(self.adapter_id, "adapter_id"),
        )

    def generate_output(
        self,
        *,
        output_id: str,
        environment: BoundedEnvironmentSpec,
        observation: EnvironmentObservation,
    ) -> BoundedModelOutput:
        """Generate deterministic bounded output from environment and observation."""

        selected_operation = self._select_operation(environment=environment)
        rationale = self.policy.rationale_template.format(
            environment_id=environment.environment_id,
            observation_id=observation.observation_id,
            operation_id=selected_operation,
            state_id=observation.state_id,
        )
        expected_effect = self.policy.expected_effect_template.format(
            environment_id=environment.environment_id,
            observation_id=observation.observation_id,
            operation_id=selected_operation,
            state_id=observation.state_id,
        )
        return BoundedModelOutput(
            output_id=output_id,
            adapter_id=self.adapter_id,
            environment_id=environment.environment_id,
            episode_id=observation.episode_id,
            observation_id=observation.observation_id,
            selected_operation_id=selected_operation,
            rationale=rationale,
            expected_effect=expected_effect,
            assumptions=self.policy.assumptions,
            uncertainty_ids=self.policy.uncertainty_ids,
            evidence_ids=self.policy.evidence_ids,
        )

    def _select_operation(self, *, environment: BoundedEnvironmentSpec) -> str:
        for operation_id in self.policy.operation_preferences:
            if operation_id in environment.action_space_ids:
                return operation_id
        return self.policy.operation_preferences[0]


def evaluate_model_output(
    *,
    environment: BoundedEnvironmentSpec,
    observation: EnvironmentObservation,
    model_output: BoundedModelOutput,
) -> ModelActionDraftDecision:
    """Evaluate whether bounded model output may become an action proposal."""

    if model_output.claims_authority:
        return ModelActionDraftDecision.BLOCKED_AUTHORITY_CLAIM
    if model_output.claims_truth:
        return ModelActionDraftDecision.BLOCKED_TRUTH_CLAIM
    if model_output.claims_completion:
        return ModelActionDraftDecision.BLOCKED_COMPLETION_CLAIM
    if environment.environment_id != observation.environment_id:
        return ModelActionDraftDecision.OUT_OF_SCOPE
    if environment.environment_id != model_output.environment_id:
        return ModelActionDraftDecision.OUT_OF_SCOPE
    if observation.episode_id != model_output.episode_id:
        return ModelActionDraftDecision.OUT_OF_SCOPE
    if observation.observation_id != model_output.observation_id:
        return ModelActionDraftDecision.OUT_OF_SCOPE
    if observation.channel_id not in environment.observation_channels:
        return ModelActionDraftDecision.OUT_OF_SCOPE
    if model_output.selected_operation_id not in environment.action_space_ids:
        return ModelActionDraftDecision.UNSUPPORTED_OPERATION
    if not observation.measured:
        return ModelActionDraftDecision.NEEDS_OBSERVATION_EVIDENCE
    return ModelActionDraftDecision.READY_FOR_ACTION_PROPOSAL


def build_model_action_draft(
    *,
    draft_id: str,
    action_id: str,
    environment: BoundedEnvironmentSpec,
    observation: EnvironmentObservation,
    model_output: BoundedModelOutput,
    notes: Iterable[str] = (),
) -> ModelActionDraft:
    """Convert bounded model output into an environment action draft."""

    decision = evaluate_model_output(
        environment=environment,
        observation=observation,
        model_output=model_output,
    )
    action_proposal = None
    if decision is ModelActionDraftDecision.READY_FOR_ACTION_PROPOSAL:
        action_proposal = EnvironmentActionProposal(
            action_id=action_id,
            environment_id=model_output.environment_id,
            episode_id=model_output.episode_id,
            actor_id=model_output.adapter_id,
            operation_id=model_output.selected_operation_id,
            rationale=model_output.rationale,
            expected_effect=model_output.expected_effect,
            precondition_state_ids=(observation.state_id,),
            evidence_ids=(model_output.fingerprint(), *model_output.evidence_ids),
            boundary=EnvironmentBoundary.SIMULATION_ONLY,
        )
    return ModelActionDraft(
        draft_id=draft_id,
        model_output=model_output,
        decision=decision,
        action_proposal=action_proposal,
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
