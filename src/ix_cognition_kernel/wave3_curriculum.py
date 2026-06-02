"""Wave 3 self-play and curriculum task records for IX-CognitionKernel.

The self-play / curriculum engine generates staged challenges, adversarial tasks,
and transfer checks under bounded measurement. A curriculum record is not a free
license to self-improve. It is only reviewable evidence that a challenge was
scoped, measured, stopped safely, and kept inside human-review boundaries.
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

WAVE_THREE_CURRICULUM_TASK_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave3-curriculum-task-v1"
)
WAVE_THREE_CURRICULUM_MEASUREMENT_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave3-curriculum-measurement-v1"
)
WAVE_THREE_CURRICULUM_BUNDLE_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave3-curriculum-bundle-v1"
)


class CurriculumTaskKind(StrEnum):
    """Required Wave 3 curriculum challenge families."""

    STAGED_SELF_PLAY = "staged-self-play"
    ADVERSARIAL_CHALLENGE = "adversarial-challenge"
    TRANSFER_CHECK = "transfer-check"
    REGRESSION_REPLAY = "regression-replay"


class CurriculumOutcome(StrEnum):
    """Measured outcome for a curriculum task."""

    PASSED = "passed"
    FAILED = "failed"
    NOT_EVALUATED = "not-evaluated"
    BLOCKED = "blocked"


class CurriculumTaskStatus(StrEnum):
    """Fail-closed status for a curriculum task record."""

    READY_FOR_HUMAN_REVIEW = "ready-for-human-review"
    NEEDS_EVIDENCE = "needs-evidence"
    NEEDS_REPAIR = "needs-repair"
    BLOCKED = "blocked"


REQUIRED_CURRICULUM_TASK_KINDS: tuple[CurriculumTaskKind, ...] = (
    CurriculumTaskKind.STAGED_SELF_PLAY,
    CurriculumTaskKind.ADVERSARIAL_CHALLENGE,
    CurriculumTaskKind.TRANSFER_CHECK,
)


@dataclass(frozen=True, slots=True)
class CurriculumMeasurement:
    """One measurable check attached to a curriculum task."""

    measurement_id: str
    metric_name: str
    target: str
    observed: str
    passed: bool
    evidence_ids: tuple[str, ...]
    schema_version: str = WAVE_THREE_CURRICULUM_MEASUREMENT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate measurement identity and evidence binding."""

        object.__setattr__(
            self,
            "measurement_id",
            _require_non_empty(self.measurement_id, "measurement_id"),
        )
        object.__setattr__(
            self, "metric_name", _require_non_empty(self.metric_name, "metric_name")
        )
        object.__setattr__(self, "target", _require_non_empty(self.target, "target"))
        object.__setattr__(
            self, "observed", _require_non_empty(self.observed, "observed")
        )
        object.__setattr__(
            self,
            "evidence_ids",
            _normalize_unique_text_tuple(
                self.evidence_ids, label="measurement evidence_id"
            ),
        )
        object.__setattr__(
            self,
            "schema_version",
            _require_non_empty(self.schema_version, "schema_version"),
        )

    @property
    def measurement_key(self) -> str:
        """Return the deterministic uniqueness key for this measurement."""

        return self.measurement_id

    def canonical_payload(self) -> dict[str, Any]:
        """Return a deterministic payload for hashing and export."""

        return {
            "evidence_ids": list(self.evidence_ids),
            "measurement_id": self.measurement_id,
            "metric_name": self.metric_name,
            "observed": self.observed,
            "passed": self.passed,
            "schema_version": self.schema_version,
            "target": self.target,
        }

    def fingerprint(self) -> str:
        """Return a deterministic SHA-256 fingerprint for this measurement."""

        return _stable_sha256(self.canonical_payload())


@dataclass(frozen=True, slots=True)
class CurriculumTaskRecord:
    """Reviewable Wave 3 self-play/curriculum task record."""

    task_id: str
    task_kind: CurriculumTaskKind
    stage: int
    skill_under_test: str
    objective: str
    challenge_description: str
    success_criteria: tuple[str, ...]
    stop_conditions: tuple[str, ...]
    outcome: CurriculumOutcome
    evidence_ids: tuple[str, ...]
    measurements: tuple[CurriculumMeasurement, ...] = ()
    transfer_domains: tuple[str, ...] = ()
    adversarial_pressures: tuple[str, ...] = ()
    blocked_reasons: tuple[str, ...] = ()
    generated_by_engine_id: str = "self-play-curriculum"
    schema_version: str = WAVE_THREE_CURRICULUM_TASK_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate bounded challenge scope, measurement, and stop discipline."""

        object.__setattr__(self, "task_id", _require_non_empty(self.task_id, "task_id"))
        if self.stage < 1:
            raise ValueError("Curriculum task stage must be at least 1.")
        object.__setattr__(
            self,
            "skill_under_test",
            _require_non_empty(self.skill_under_test, "skill_under_test"),
        )
        object.__setattr__(
            self, "objective", _require_non_empty(self.objective, "objective")
        )
        object.__setattr__(
            self,
            "challenge_description",
            _require_non_empty(self.challenge_description, "challenge_description"),
        )
        object.__setattr__(
            self,
            "success_criteria",
            _normalize_unique_text_tuple(
                self.success_criteria, label="success criterion"
            ),
        )
        if not self.success_criteria:
            raise ValueError("Curriculum tasks require success criteria.")
        object.__setattr__(
            self,
            "stop_conditions",
            _normalize_unique_text_tuple(self.stop_conditions, label="stop condition"),
        )
        if not self.stop_conditions:
            raise ValueError("Curriculum tasks require stop conditions.")
        object.__setattr__(
            self,
            "evidence_ids",
            _normalize_unique_text_tuple(self.evidence_ids, label="task evidence_id"),
        )
        sorted_measurements = tuple(
            sorted(self.measurements, key=lambda item: item.measurement_key)
        )
        _unique_ids(
            (measurement.measurement_id for measurement in sorted_measurements),
            label="measurement_id",
        )
        object.__setattr__(self, "measurements", sorted_measurements)
        object.__setattr__(
            self,
            "transfer_domains",
            _normalize_unique_text_tuple(
                self.transfer_domains, label="transfer domain"
            ),
        )
        object.__setattr__(
            self,
            "adversarial_pressures",
            _normalize_unique_text_tuple(
                self.adversarial_pressures, label="adversarial pressure"
            ),
        )
        object.__setattr__(
            self,
            "blocked_reasons",
            _normalize_unique_text_tuple(self.blocked_reasons, label="blocked reason"),
        )
        object.__setattr__(
            self,
            "generated_by_engine_id",
            _require_non_empty(self.generated_by_engine_id, "generated_by_engine_id"),
        )
        if self.generated_by_engine_id != "self-play-curriculum":
            raise ValueError(
                "Curriculum task records must be generated by self-play-curriculum."
            )
        object.__setattr__(
            self,
            "schema_version",
            _require_non_empty(self.schema_version, "schema_version"),
        )
        if self.task_kind is CurriculumTaskKind.ADVERSARIAL_CHALLENGE and not (
            self.adversarial_pressures
        ):
            raise ValueError("Adversarial curriculum tasks require pressure labels.")
        if self.task_kind is CurriculumTaskKind.TRANSFER_CHECK and not (
            self.transfer_domains
        ):
            raise ValueError("Transfer curriculum tasks require transfer domains.")
        if self.outcome is CurriculumOutcome.BLOCKED and not self.blocked_reasons:
            raise ValueError("Blocked curriculum tasks require blocked reasons.")
        if self.blocked_reasons and self.outcome is not CurriculumOutcome.BLOCKED:
            raise ValueError("Only blocked curriculum tasks may carry blocked reasons.")

    @property
    def artifact_id(self) -> str:
        """Return the shared Wave 3 artifact id for this curriculum task."""

        return f"curriculum-task:{self.task_id}"

    @property
    def measurement_evidence_ids(self) -> tuple[str, ...]:
        """Return sorted unique evidence ids referenced by measurements."""

        return tuple(
            sorted(
                {
                    evidence_id
                    for measurement in self.measurements
                    for evidence_id in measurement.evidence_ids
                }
            )
        )

    @property
    def all_evidence_ids(self) -> tuple[str, ...]:
        """Return sorted unique task and measurement evidence ids."""

        return tuple(
            sorted(set(self.evidence_ids).union(self.measurement_evidence_ids))
        )

    @property
    def failed_measurement_ids(self) -> tuple[str, ...]:
        """Return measurement ids that failed acceptance."""

        return tuple(
            measurement.measurement_id
            for measurement in self.measurements
            if not measurement.passed
        )

    @property
    def readiness_gaps(self) -> tuple[str, ...]:
        """Return gaps that prevent human-review readiness."""

        gaps: list[str] = []
        if not self.evidence_ids:
            gaps.append(f"{self.task_id} has no top-level evidence ids")
        if not self.measurements:
            gaps.append(f"{self.task_id} has no curriculum measurements")
        if self.outcome is CurriculumOutcome.NOT_EVALUATED:
            gaps.append(f"{self.task_id} has not been evaluated")
        if self.outcome is CurriculumOutcome.FAILED:
            gaps.append(f"{self.task_id} failed curriculum outcome")
        if self.failed_measurement_ids:
            gaps.append(
                f"{self.task_id} failed measurements: "
                + ", ".join(self.failed_measurement_ids)
            )
        return tuple(gaps)

    @property
    def blocking_gaps(self) -> tuple[str, ...]:
        """Return evidence-bound blocks that stop curriculum progress."""

        if self.outcome is not CurriculumOutcome.BLOCKED:
            return ()
        return tuple(
            f"{self.task_id} blocked: {reason}" for reason in self.blocked_reasons
        )

    @property
    def status(self) -> CurriculumTaskStatus:
        """Return the fail-closed curriculum task status."""

        if self.blocking_gaps:
            return CurriculumTaskStatus.BLOCKED
        if self.failed_measurement_ids or self.outcome is CurriculumOutcome.FAILED:
            return CurriculumTaskStatus.NEEDS_REPAIR
        if self.readiness_gaps:
            return CurriculumTaskStatus.NEEDS_EVIDENCE
        return CurriculumTaskStatus.READY_FOR_HUMAN_REVIEW

    @property
    def ready_for_human_review(self) -> bool:
        """Return whether this task may enter human review."""

        return self.status is CurriculumTaskStatus.READY_FOR_HUMAN_REVIEW

    @property
    def permits_automatic_execution(self) -> bool:
        """Return whether this task permits automatic execution."""

        return False

    @property
    def human_authority_state(self) -> WaveThreeAuthorityState:
        """Return aggregate human-authority state for this curriculum task."""

        if self.status is CurriculumTaskStatus.BLOCKED:
            return WaveThreeAuthorityState.BLOCKED
        return WaveThreeAuthorityState.HUMAN_REVIEW_REQUIRED

    @property
    def review_summary(self) -> str:
        """Return a concise human-review summary."""

        return (
            f"{self.task_id}: {self.task_kind.value}; stage {self.stage}; "
            f"{self.status.value}; {len(self.measurements)} measurements; "
            "automatic execution is not permitted."
        )

    def to_artifact_ref(self) -> WaveThreeArtifactRef:
        """Convert this curriculum task into a shared Wave 3 artifact reference."""

        if self.status is CurriculumTaskStatus.READY_FOR_HUMAN_REVIEW:
            decision = WaveThreeArtifactDecision.READY_FOR_HUMAN_REVIEW
            authority_state = WaveThreeAuthorityState.HUMAN_REVIEW_REQUIRED
        elif self.status is CurriculumTaskStatus.BLOCKED:
            decision = WaveThreeArtifactDecision.BLOCKED
            authority_state = WaveThreeAuthorityState.BLOCKED
        else:
            decision = WaveThreeArtifactDecision.NEEDS_EVIDENCE
            authority_state = WaveThreeAuthorityState.HUMAN_REVIEW_REQUIRED
        return WaveThreeArtifactRef(
            artifact_id=self.artifact_id,
            kind=WaveThreeArtifactKind.CURRICULUM_TASK,
            source_system=WaveThreeSourceSystem.IX_COGNITION_KERNEL,
            summary=self.review_summary,
            produced_by_engine_id=self.generated_by_engine_id,
            produced_by_agent_role_id="curriculum-designer",
            evidence_ids=self.all_evidence_ids,
            decision=decision,
            authority_state=authority_state,
        )

    def canonical_payload(self) -> dict[str, Any]:
        """Return a deterministic payload for hashing and export."""

        return {
            "adversarial_pressures": list(self.adversarial_pressures),
            "all_evidence_ids": list(self.all_evidence_ids),
            "artifact_id": self.artifact_id,
            "blocked_reasons": list(self.blocked_reasons),
            "blocking_gaps": list(self.blocking_gaps),
            "challenge_description": self.challenge_description,
            "evidence_ids": list(self.evidence_ids),
            "failed_measurement_ids": list(self.failed_measurement_ids),
            "generated_by_engine_id": self.generated_by_engine_id,
            "human_authority_state": self.human_authority_state.value,
            "measurements": [
                measurement.canonical_payload() for measurement in self.measurements
            ],
            "objective": self.objective,
            "outcome": self.outcome.value,
            "permits_automatic_execution": self.permits_automatic_execution,
            "readiness_gaps": list(self.readiness_gaps),
            "review_summary": self.review_summary,
            "schema_version": self.schema_version,
            "skill_under_test": self.skill_under_test,
            "stage": self.stage,
            "stop_conditions": list(self.stop_conditions),
            "success_criteria": list(self.success_criteria),
            "task_id": self.task_id,
            "task_kind": self.task_kind.value,
            "transfer_domains": list(self.transfer_domains),
        }

    def fingerprint(self) -> str:
        """Return a deterministic SHA-256 fingerprint for this task."""

        return _stable_sha256(self.canonical_payload())


@dataclass(frozen=True, slots=True)
class CurriculumTaskBundle:
    """Deterministic bundle of Wave 3 curriculum tasks."""

    bundle_id: str
    tasks: tuple[CurriculumTaskRecord, ...]
    required_task_kinds: tuple[CurriculumTaskKind, ...] = REQUIRED_CURRICULUM_TASK_KINDS
    notes: tuple[str, ...] = ()
    schema_version: str = WAVE_THREE_CURRICULUM_BUNDLE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate task uniqueness, kind coverage, and bundle scope."""

        object.__setattr__(
            self, "bundle_id", _require_non_empty(self.bundle_id, "bundle_id")
        )
        if not self.tasks:
            raise ValueError("Curriculum task bundles require at least one task.")
        sorted_tasks = tuple(sorted(self.tasks, key=lambda task: task.task_id))
        _unique_ids((task.task_id for task in sorted_tasks), label="task_id")
        object.__setattr__(self, "tasks", sorted_tasks)
        object.__setattr__(
            self,
            "required_task_kinds",
            _normalize_unique_enum_tuple(
                self.required_task_kinds, label="required curriculum task kind"
            ),
        )
        if not self.required_task_kinds:
            raise ValueError("Curriculum task bundles require task-kind coverage.")
        object.__setattr__(
            self,
            "notes",
            _normalize_unique_text_tuple(self.notes, label="curriculum bundle note"),
        )
        object.__setattr__(
            self,
            "schema_version",
            _require_non_empty(self.schema_version, "schema_version"),
        )

    @property
    def task_ids(self) -> tuple[str, ...]:
        """Return task ids in deterministic order."""

        return tuple(task.task_id for task in self.tasks)

    @property
    def represented_task_kinds(self) -> tuple[CurriculumTaskKind, ...]:
        """Return represented task kinds in required-kind order when possible."""

        present = {task.task_kind for task in self.tasks}
        required_order = tuple(
            kind for kind in self.required_task_kinds if kind in present
        )
        extra_order = tuple(
            sorted(
                (kind for kind in present if kind not in set(required_order)),
                key=lambda kind: kind.value,
            )
        )
        return required_order + extra_order

    @property
    def missing_required_task_kinds(self) -> tuple[CurriculumTaskKind, ...]:
        """Return required curriculum task kinds missing from the bundle."""

        present = {task.task_kind for task in self.tasks}
        return tuple(kind for kind in self.required_task_kinds if kind not in present)

    @property
    def ready_task_ids(self) -> tuple[str, ...]:
        """Return task ids ready for human review."""

        return tuple(task.task_id for task in self.tasks if task.ready_for_human_review)

    @property
    def blocked_task_ids(self) -> tuple[str, ...]:
        """Return task ids blocked by evidence-bound conditions."""

        return tuple(
            task.task_id
            for task in self.tasks
            if task.status is CurriculumTaskStatus.BLOCKED
        )

    @property
    def readiness_gaps(self) -> tuple[str, ...]:
        """Return bundle-level and task-level readiness gaps."""

        gaps: list[str] = []
        if self.missing_required_task_kinds:
            gaps.append(
                "missing required curriculum task kinds: "
                + ", ".join(kind.value for kind in self.missing_required_task_kinds)
            )
        for task in self.tasks:
            gaps.extend(task.readiness_gaps)
            gaps.extend(task.blocking_gaps)
        return tuple(gaps)

    @property
    def is_complete_for_required_tasks(self) -> bool:
        """Return whether every required task kind is represented and reviewable."""

        return not self.readiness_gaps and len(self.ready_task_ids) == len(self.tasks)

    def task_by_id(self, task_id: str) -> CurriculumTaskRecord:
        """Return one curriculum task by id."""

        normalized = _require_non_empty(task_id, "task_id")
        for task in self.tasks:
            if task.task_id == normalized:
                return task
        raise ValueError(f"Unknown curriculum task id: {task_id}")

    def to_artifact_bundle(self, *, artifact_bundle_id: str) -> WaveThreeArtifactBundle:
        """Convert curriculum tasks into a shared Wave 3 artifact bundle."""

        artifacts = tuple(task.to_artifact_ref() for task in self.tasks)
        evidence_links = tuple(
            WaveThreeEvidenceLink(
                evidence_id=evidence_id,
                artifact_id=artifact.artifact_id,
                relation=WaveThreeEvidenceRelation.TESTS,
                summary=(
                    "Curriculum task evidence tests staged challenge, adversarial "
                    "pressure, transfer behavior, and stop-condition discipline."
                ),
                source_system=WaveThreeSourceSystem.LOCAL_TEST_SUITE,
            )
            for artifact in artifacts
            for evidence_id in artifact.evidence_ids
        )
        return WaveThreeArtifactBundle(
            bundle_id=artifact_bundle_id,
            artifacts=artifacts,
            evidence_links=evidence_links,
            required_kinds=(WaveThreeArtifactKind.CURRICULUM_TASK,),
            notes=("Curriculum tasks are measured review artifacts only.",),
        )

    def canonical_payload(self) -> dict[str, Any]:
        """Return a deterministic payload for hashing and export."""

        return {
            "bundle_id": self.bundle_id,
            "missing_required_task_kinds": [
                kind.value for kind in self.missing_required_task_kinds
            ],
            "notes": list(self.notes),
            "readiness_gaps": list(self.readiness_gaps),
            "represented_task_kinds": [
                kind.value for kind in self.represented_task_kinds
            ],
            "required_task_kinds": [kind.value for kind in self.required_task_kinds],
            "schema_version": self.schema_version,
            "tasks": [task.canonical_payload() for task in self.tasks],
        }

    def fingerprint(self) -> str:
        """Return a deterministic SHA-256 fingerprint for this bundle."""

        return _stable_sha256(self.canonical_payload())


def passing_curriculum_measurement(
    *,
    measurement_id: str,
    metric_name: str,
    target: str,
    observed: str,
    evidence_id: str,
) -> CurriculumMeasurement:
    """Create a passed curriculum measurement with one evidence id."""

    return CurriculumMeasurement(
        measurement_id=measurement_id,
        metric_name=metric_name,
        target=target,
        observed=observed,
        passed=True,
        evidence_ids=(evidence_id,),
    )


def measured_curriculum_task(
    *,
    task_id: str,
    task_kind: CurriculumTaskKind,
    stage: int,
    skill_under_test: str,
    objective: str,
    challenge_description: str,
    evidence_ids: tuple[str, ...],
    measurements: tuple[CurriculumMeasurement, ...],
    transfer_domains: tuple[str, ...] = (),
    adversarial_pressures: tuple[str, ...] = (),
) -> CurriculumTaskRecord:
    """Create a measured, passed curriculum task with default safety gates."""

    return CurriculumTaskRecord(
        task_id=task_id,
        task_kind=task_kind,
        stage=stage,
        skill_under_test=skill_under_test,
        objective=objective,
        challenge_description=challenge_description,
        success_criteria=(
            "Task result is measured against explicit acceptance criteria.",
            "Uncertainty and failure evidence remain visible in the record.",
        ),
        stop_conditions=(
            "Stop when the task attempts unreviewed execution authority.",
            "Stop when evidence is missing or contradicted.",
        ),
        outcome=CurriculumOutcome.PASSED,
        evidence_ids=evidence_ids,
        measurements=measurements,
        transfer_domains=transfer_domains,
        adversarial_pressures=adversarial_pressures,
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
