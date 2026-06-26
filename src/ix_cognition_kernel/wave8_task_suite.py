"""Wave 8 unknown-task suite.

This module adds bounded unknown-task packaging for the Recursive
Reality-Corrected Learner. It does not claim that a task proves intelligence by
itself. It creates replayable task surfaces that an episode runner can use to
test whether future behavior improves under measured feedback.

Task-suite doctrine:

- known-task success is not transfer,
- hidden goals must remain bounded and replayable,
- every task must bind to a bounded environment,
- every task must provide measured initial observation evidence,
- withheld variants are required before generalization claims can be promoted,
- a suite is useful only when it contains pressure beyond original-task replay.
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
    EnvironmentKind,
    EnvironmentObservation,
)

WAVE_EIGHT_UNKNOWN_TASK_TEMPLATE_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave8-unknown-task-template-v1"
)
WAVE_EIGHT_UNKNOWN_TASK_INSTANCE_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave8-unknown-task-instance-v1"
)
WAVE_EIGHT_UNKNOWN_TASK_SUITE_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave8-unknown-task-suite-v1"
)
WAVE_EIGHT_UNKNOWN_TASK_VALIDATION_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave8-unknown-task-validation-v1"
)


class TaskFamily(StrEnum):
    """Task families that pressure different cognition surfaces."""

    GRID_ABSTRACTION = "grid-abstraction"
    CODE_REPAIR = "code-repair"
    CONTRADICTION_MEMORY = "contradiction-memory"
    PLANNING_WORLD = "planning-world"
    TOOL_USE_SIMULATION = "tool-use-simulation"


class TaskDisclosureLevel(StrEnum):
    """How much of the task objective is visible to the candidate."""

    FULLY_VISIBLE = "fully-visible"
    PARTIALLY_WITHHELD = "partially-withheld"
    HIDDEN_GOAL = "hidden-goal"


class TaskDifficulty(StrEnum):
    """Coarse difficulty tier for curriculum-frontier selection."""

    SEED = "seed"
    NEAR_TRANSFER = "near-transfer"
    FAR_TRANSFER = "far-transfer"
    ADVERSARIAL = "adversarial"
    HIDDEN_VALIDATION = "hidden-validation"


class TaskSuiteValidationDecision(StrEnum):
    """Validation decision for a Wave 8 unknown-task suite."""

    READY_FOR_EPISODES = "ready-for-episodes"
    NEEDS_TRANSFER_PRESSURE = "needs-transfer-pressure"
    NEEDS_HIDDEN_VALIDATION = "needs-hidden-validation"
    NEEDS_EVIDENCE = "needs-evidence"
    BLOCKED = "blocked"


@dataclass(frozen=True, slots=True)
class UnknownTaskTemplate:
    """Reusable template for creating bounded unknown-task instances."""

    template_id: str
    family: TaskFamily
    objective: str
    invariant_rules: tuple[str, ...]
    allowed_observation_channels: tuple[str, ...]
    allowed_action_space_ids: tuple[str, ...]
    scoring_rules: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    schema_version: str = WAVE_EIGHT_UNKNOWN_TASK_TEMPLATE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate the task template contract."""

        object.__setattr__(
            self,
            "template_id",
            _require_non_empty(self.template_id, "template_id"),
        )
        object.__setattr__(
            self,
            "objective",
            _require_non_empty(self.objective, "objective"),
        )
        object.__setattr__(
            self,
            "invariant_rules",
            _normalize_unique_text_tuple(self.invariant_rules, label="invariant_rule"),
        )
        object.__setattr__(
            self,
            "allowed_observation_channels",
            _normalize_unique_text_tuple(
                self.allowed_observation_channels,
                label="allowed_observation_channel",
            ),
        )
        object.__setattr__(
            self,
            "allowed_action_space_ids",
            _normalize_unique_text_tuple(
                self.allowed_action_space_ids,
                label="allowed_action_space_id",
            ),
        )
        object.__setattr__(
            self,
            "scoring_rules",
            _normalize_unique_text_tuple(self.scoring_rules, label="scoring_rule"),
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
        if not self.invariant_rules:
            raise ValueError("Unknown task templates require invariant rules.")
        if not self.allowed_observation_channels:
            raise ValueError(
                "Unknown task templates require allowed observation channels."
            )
        if not self.allowed_action_space_ids:
            raise ValueError("Unknown task templates require allowed action space ids.")
        if not self.scoring_rules:
            raise ValueError("Unknown task templates require scoring rules.")
        if not self.evidence_ids:
            raise ValueError("Unknown task templates require evidence ids.")

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic template payload."""

        return {
            "allowed_action_space_ids": list(self.allowed_action_space_ids),
            "allowed_observation_channels": list(self.allowed_observation_channels),
            "evidence_ids": list(self.evidence_ids),
            "family": self.family.value,
            "invariant_rules": list(self.invariant_rules),
            "objective": self.objective,
            "schema_version": self.schema_version,
            "scoring_rules": list(self.scoring_rules),
            "template_id": self.template_id,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this task template."""

        return _stable_sha256(self.canonical_payload())


@dataclass(frozen=True, slots=True)
class UnknownTaskInstance:
    """One bounded task instance connected to an environment and observation."""

    task_id: str
    template: UnknownTaskTemplate
    environment: BoundedEnvironmentSpec
    initial_observation: EnvironmentObservation
    expected_outcome_features: tuple[str, ...]
    withheld_features: tuple[str, ...]
    transfer_tags: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    disclosure_level: TaskDisclosureLevel = TaskDisclosureLevel.PARTIALLY_WITHHELD
    difficulty: TaskDifficulty = TaskDifficulty.SEED
    schema_version: str = WAVE_EIGHT_UNKNOWN_TASK_INSTANCE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate task instance binding and withheld-pressure evidence."""

        object.__setattr__(
            self,
            "task_id",
            _require_non_empty(self.task_id, "task_id"),
        )
        object.__setattr__(
            self,
            "expected_outcome_features",
            _normalize_unique_text_tuple(
                self.expected_outcome_features,
                label="expected_outcome_feature",
            ),
        )
        object.__setattr__(
            self,
            "withheld_features",
            _dedupe_text_tuple(self.withheld_features, label="withheld_feature"),
        )
        object.__setattr__(
            self,
            "transfer_tags",
            _normalize_unique_text_tuple(self.transfer_tags, label="transfer_tag"),
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
        _require_same_text(
            self.environment.environment_id,
            self.initial_observation.environment_id,
            "environment_id",
        )
        if self.initial_observation.channel_id not in (
            self.template.allowed_observation_channels
        ):
            raise ValueError("Initial observation channel is not allowed by template.")
        for action_space_id in self.environment.action_space_ids:
            if action_space_id not in self.template.allowed_action_space_ids:
                raise ValueError(
                    f"Environment action space is not allowed by template: "
                    f"{action_space_id}"
                )
        for scoring_rule in self.environment.scoring_rules:
            if scoring_rule not in self.template.scoring_rules:
                raise ValueError(
                    f"Environment scoring rule is not allowed by template: "
                    f"{scoring_rule}"
                )
        if not self.initial_observation.measured:
            raise ValueError("Unknown task instances require measured observations.")
        if not self.expected_outcome_features:
            raise ValueError(
                "Unknown task instances require expected outcome features."
            )
        if not self.transfer_tags:
            raise ValueError("Unknown task instances require transfer tags.")
        if not self.evidence_ids:
            raise ValueError("Unknown task instances require evidence ids.")
        if (
            self.disclosure_level is TaskDisclosureLevel.FULLY_VISIBLE
            and self.withheld_features
        ):
            raise ValueError("Fully visible tasks must not include withheld features.")
        if (
            self.disclosure_level is not TaskDisclosureLevel.FULLY_VISIBLE
            and not self.withheld_features
        ):
            raise ValueError("Withheld task variants require withheld features.")

    @property
    def is_transfer_pressure(self) -> bool:
        """Return whether the task pressures transfer beyond seed replay."""

        return self.difficulty in {
            TaskDifficulty.NEAR_TRANSFER,
            TaskDifficulty.FAR_TRANSFER,
            TaskDifficulty.ADVERSARIAL,
            TaskDifficulty.HIDDEN_VALIDATION,
        }

    @property
    def is_hidden_validation(self) -> bool:
        """Return whether the task is reserved for hidden validation."""

        return self.difficulty is TaskDifficulty.HIDDEN_VALIDATION or (
            self.disclosure_level is TaskDisclosureLevel.HIDDEN_GOAL
        )

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic task instance payload."""

        return {
            "difficulty": self.difficulty.value,
            "disclosure_level": self.disclosure_level.value,
            "environment_fingerprint": self.environment.fingerprint(),
            "evidence_ids": list(self.evidence_ids),
            "expected_outcome_features": list(self.expected_outcome_features),
            "initial_observation_fingerprint": self.initial_observation.fingerprint(),
            "schema_version": self.schema_version,
            "task_id": self.task_id,
            "template_fingerprint": self.template.fingerprint(),
            "transfer_tags": list(self.transfer_tags),
            "withheld_features": list(self.withheld_features),
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this task instance."""

        return _stable_sha256(self.canonical_payload())


@dataclass(frozen=True, slots=True)
class UnknownTaskSuite:
    """A bounded suite of tasks for Wave 8 episode trials."""

    suite_id: str
    purpose: str
    tasks: tuple[UnknownTaskInstance, ...]
    evidence_ids: tuple[str, ...]
    schema_version: str = WAVE_EIGHT_UNKNOWN_TASK_SUITE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate task suite shape and task identity uniqueness."""

        object.__setattr__(
            self,
            "suite_id",
            _require_non_empty(self.suite_id, "suite_id"),
        )
        object.__setattr__(
            self,
            "purpose",
            _require_non_empty(self.purpose, "purpose"),
        )
        object.__setattr__(
            self,
            "tasks",
            tuple(self.tasks),
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
        if not self.tasks:
            raise ValueError("Unknown task suites require at least one task.")
        if not self.evidence_ids:
            raise ValueError("Unknown task suites require evidence ids.")
        seen: set[str] = set()
        for task in self.tasks:
            if task.task_id in seen:
                raise ValueError(f"Duplicate task_id: {task.task_id}")
            seen.add(task.task_id)

    @property
    def task_count(self) -> int:
        """Return task count."""

        return len(self.tasks)

    @property
    def transfer_task_count(self) -> int:
        """Return count of transfer-pressure tasks."""

        return sum(1 for task in self.tasks if task.is_transfer_pressure)

    @property
    def hidden_validation_task_count(self) -> int:
        """Return count of hidden-validation tasks."""

        return sum(1 for task in self.tasks if task.is_hidden_validation)

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic suite payload."""

        return {
            "evidence_ids": list(self.evidence_ids),
            "purpose": self.purpose,
            "schema_version": self.schema_version,
            "suite_id": self.suite_id,
            "task_fingerprints": [task.fingerprint() for task in self.tasks],
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this task suite."""

        return _stable_sha256(self.canonical_payload())


@dataclass(frozen=True, slots=True)
class TaskSuiteValidationReport:
    """Validation report for an unknown-task suite."""

    report_id: str
    suite: UnknownTaskSuite
    decision: TaskSuiteValidationDecision
    findings: tuple[str, ...]
    schema_version: str = WAVE_EIGHT_UNKNOWN_TASK_VALIDATION_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate report payload."""

        object.__setattr__(
            self,
            "report_id",
            _require_non_empty(self.report_id, "report_id"),
        )
        object.__setattr__(
            self,
            "findings",
            _dedupe_text_tuple(self.findings, label="finding"),
        )
        object.__setattr__(
            self,
            "schema_version",
            _require_non_empty(self.schema_version, "schema_version"),
        )
        if (
            self.decision is not TaskSuiteValidationDecision.READY_FOR_EPISODES
            and not self.findings
        ):
            raise ValueError("Non-ready task suite reports require findings.")

    @property
    def ready(self) -> bool:
        """Return whether the suite can run bounded episodes."""

        return self.decision is TaskSuiteValidationDecision.READY_FOR_EPISODES

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic validation report payload."""

        return {
            "decision": self.decision.value,
            "findings": list(self.findings),
            "report_id": self.report_id,
            "schema_version": self.schema_version,
            "suite_fingerprint": self.suite.fingerprint(),
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this report."""

        return _stable_sha256(self.canonical_payload())


def build_grid_transition_template(*, template_id: str) -> UnknownTaskTemplate:
    """Build the first deterministic Wave 8 grid-transition template."""

    return UnknownTaskTemplate(
        template_id=template_id,
        family=TaskFamily.GRID_ABSTRACTION,
        objective="Infer bounded grid transitions from visible local features.",
        invariant_rules=(
            "agent-position-updates-only-after-bounded-action",
            "observation-is-visible-state-not-ground-truth",
            "measured-result-required-before-learning",
        ),
        allowed_observation_channels=("grid-visible-state",),
        allowed_action_space_ids=("inspect-cell", "move-east", "move-west"),
        scoring_rules=("penalize-unmeasured-claim", "reward-correct-transition"),
        evidence_ids=(f"{template_id}:template-evidence",),
    )


def build_grid_transition_task(
    *,
    task_id: str,
    template: UnknownTaskTemplate,
    episode_id: str,
    start_state_id: str,
    empty_direction: str,
    expected_operation_id: str,
    difficulty: TaskDifficulty,
    disclosure_level: TaskDisclosureLevel,
) -> UnknownTaskInstance:
    """Build a deterministic bounded grid-transition task instance."""

    normalized_empty_direction = _require_non_empty(empty_direction, "empty_direction")
    normalized_expected_operation_id = _require_non_empty(
        expected_operation_id,
        "expected_operation_id",
    )
    environment_id = f"{task_id}:environment"
    observation_id = f"{task_id}:observation"
    reset_evidence_id = f"{task_id}:reset-evidence"
    observation_evidence_id = f"{task_id}:observation-evidence"
    task_evidence_id = f"{task_id}:task-evidence"
    environment = BoundedEnvironmentSpec(
        environment_id=environment_id,
        kind=EnvironmentKind.GRID_ABSTRACTION,
        objective=template.objective,
        observation_channels=("grid-visible-state",),
        action_space_ids=template.allowed_action_space_ids,
        scoring_rules=template.scoring_rules,
        reset_evidence_ids=(reset_evidence_id,),
        hidden_goal=disclosure_level is TaskDisclosureLevel.HIDDEN_GOAL,
    )
    observation = EnvironmentObservation(
        observation_id=observation_id,
        environment_id=environment_id,
        episode_id=episode_id,
        state_id=start_state_id,
        channel_id="grid-visible-state",
        summary=f"The {normalized_empty_direction} cell is visibly empty.",
        visible_features=(
            f"{normalized_empty_direction}-cell-empty",
            f"state:{start_state_id}",
        ),
        evidence_ids=(observation_evidence_id,),
        measured=True,
    )
    withheld_features: tuple[str, ...] = ()
    if disclosure_level is not TaskDisclosureLevel.FULLY_VISIBLE:
        withheld_features = (
            f"expected-operation:{normalized_expected_operation_id}",
            f"empty-direction:{normalized_empty_direction}",
        )
    return UnknownTaskInstance(
        task_id=task_id,
        template=template,
        environment=environment,
        initial_observation=observation,
        expected_outcome_features=(
            f"operation:{normalized_expected_operation_id}",
            f"transition-from:{start_state_id}",
        ),
        withheld_features=withheld_features,
        transfer_tags=(
            f"difficulty:{difficulty.value}",
            f"family:{template.family.value}",
        ),
        evidence_ids=(task_evidence_id,),
        disclosure_level=disclosure_level,
        difficulty=difficulty,
    )


def validate_unknown_task_suite(
    *, report_id: str, suite: UnknownTaskSuite
) -> TaskSuiteValidationReport:
    """Validate whether a task suite is ready for bounded episode trials."""

    findings: list[str] = []
    if any(not task.initial_observation.evidence_ids for task in suite.tasks):
        findings.append("task-missing-observation-evidence")
    if suite.transfer_task_count == 0:
        findings.append("suite-missing-transfer-pressure")
    if suite.hidden_validation_task_count == 0:
        findings.append("suite-missing-hidden-validation")

    if "task-missing-observation-evidence" in findings:
        decision = TaskSuiteValidationDecision.NEEDS_EVIDENCE
    elif "suite-missing-transfer-pressure" in findings:
        decision = TaskSuiteValidationDecision.NEEDS_TRANSFER_PRESSURE
    elif "suite-missing-hidden-validation" in findings:
        decision = TaskSuiteValidationDecision.NEEDS_HIDDEN_VALIDATION
    else:
        decision = TaskSuiteValidationDecision.READY_FOR_EPISODES

    return TaskSuiteValidationReport(
        report_id=report_id,
        suite=suite,
        decision=decision,
        findings=tuple(findings),
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
