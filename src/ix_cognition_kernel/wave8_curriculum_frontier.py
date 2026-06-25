"""Wave 8 curriculum-frontier pressure.

This module adds the first autonomous curriculum-selection surface for the
Recursive Reality-Corrected Learner. It does not allow the system to choose
tasks because they are impressive, convenient, or self-flattering. It ranks
bounded tasks by recoverable learning pressure, transfer gaps, hidden-validation
needs, and replay evidence.

Curriculum doctrine:

- task selection must be evidence-bound,
- too-easy tasks do not prove growth,
- impossible tasks do not create useful signal,
- recoverable failure is valuable,
- transfer gaps are higher value than seed replay,
- hidden validation must not be consumed casually,
- selection pressure is not authority to act.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from ix_cognition_kernel.wave8_task_suite import (
    TaskDifficulty,
    UnknownTaskInstance,
    UnknownTaskSuite,
)
from ix_cognition_kernel.wave8_transfer_challenge import (
    TransferBand,
    TransferTrialRecord,
    TransferTrialStatus,
)

WAVE_EIGHT_CURRICULUM_SIGNAL_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave8-curriculum-signal-v1"
)
WAVE_EIGHT_FRONTIER_ITEM_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave8-frontier-item-v1"
)
WAVE_EIGHT_FRONTIER_PLAN_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave8-frontier-plan-v1"
)


class CurriculumSignalKind(StrEnum):
    """Kinds of growth pressure a task may expose."""

    NEW_SEED = "new-seed"
    RECOVERABLE_FAILURE = "recoverable-failure"
    TRANSFER_GAP = "transfer-gap"
    FAR_TRANSFER_GAP = "far-transfer-gap"
    ADVERSARIAL_GAP = "adversarial-gap"
    HIDDEN_VALIDATION_GAP = "hidden-validation-gap"
    STALE_REPLAY = "stale-replay"
    TOO_EASY = "too-easy"
    TOO_HARD = "too-hard"
    BLOCKED_EVIDENCE = "blocked-evidence"


class FrontierPriority(StrEnum):
    """Selection priority for a curriculum frontier item."""

    SELECT_NOW = "select-now"
    SELECT_AFTER_REPLAY = "select-after-replay"
    HOLD_HIDDEN_VALIDATION = "hold-hidden-validation"
    DEFER_TOO_EASY = "defer-too-easy"
    DEFER_TOO_HARD = "defer-too-hard"
    BLOCKED = "blocked"


@dataclass(frozen=True, slots=True)
class CurriculumSignal:
    """Evidence-bound signal used to rank a task on the frontier."""

    signal_id: str
    task: UnknownTaskInstance
    kind: CurriculumSignalKind
    rationale: str
    evidence_ids: tuple[str, ...]
    score: int
    schema_version: str = WAVE_EIGHT_CURRICULUM_SIGNAL_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate curriculum signal evidence and score."""

        object.__setattr__(
            self,
            "signal_id",
            _require_non_empty(self.signal_id, "signal_id"),
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
        if not self.evidence_ids:
            raise ValueError("Curriculum signals require evidence ids.")
        if self.score < 0:
            raise ValueError("Curriculum signal score must be non-negative.")
        if self.kind is CurriculumSignalKind.BLOCKED_EVIDENCE and self.score != 0:
            raise ValueError("Blocked evidence signals must have zero score.")

    @property
    def blocks_selection(self) -> bool:
        """Return whether this signal blocks task selection."""

        return self.kind is CurriculumSignalKind.BLOCKED_EVIDENCE

    @property
    def holds_hidden_validation(self) -> bool:
        """Return whether this signal requires holding hidden validation."""

        return (
            self.kind is CurriculumSignalKind.HIDDEN_VALIDATION_GAP
            and self.task.is_hidden_validation
        )

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic signal payload."""

        return {
            "evidence_ids": list(self.evidence_ids),
            "kind": self.kind.value,
            "rationale": self.rationale,
            "schema_version": self.schema_version,
            "score": self.score,
            "signal_id": self.signal_id,
            "task_fingerprint": self.task.fingerprint(),
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this signal."""

        return _stable_sha256(self.canonical_payload())


@dataclass(frozen=True, slots=True)
class FrontierItem:
    """Ranked curriculum item for a bounded task."""

    item_id: str
    task: UnknownTaskInstance
    signals: tuple[CurriculumSignal, ...]
    priority: FrontierPriority
    schema_version: str = WAVE_EIGHT_FRONTIER_ITEM_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate frontier item consistency."""

        object.__setattr__(
            self,
            "item_id",
            _require_non_empty(self.item_id, "item_id"),
        )
        object.__setattr__(
            self,
            "signals",
            tuple(self.signals),
        )
        object.__setattr__(
            self,
            "schema_version",
            _require_non_empty(self.schema_version, "schema_version"),
        )
        if not self.signals:
            raise ValueError("Frontier items require at least one curriculum signal.")
        for signal in self.signals:
            if signal.task.task_id != self.task.task_id:
                raise ValueError("Frontier item signals must bind to the same task.")
        if self.priority is FrontierPriority.BLOCKED:
            if not any(signal.blocks_selection for signal in self.signals):
                raise ValueError("Blocked frontier items require a blocking signal.")
        if any(signal.blocks_selection for signal in self.signals):
            if self.priority is not FrontierPriority.BLOCKED:
                raise ValueError("Blocking signals require BLOCKED priority.")

    @property
    def score(self) -> int:
        """Return aggregate curriculum score."""

        return sum(signal.score for signal in self.signals)

    @property
    def selectable(self) -> bool:
        """Return whether this task can be selected for the next episode."""

        return self.priority in {
            FrontierPriority.SELECT_NOW,
            FrontierPriority.SELECT_AFTER_REPLAY,
        }

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic frontier item payload."""

        return {
            "item_id": self.item_id,
            "priority": self.priority.value,
            "schema_version": self.schema_version,
            "score": self.score,
            "signal_fingerprints": [signal.fingerprint() for signal in self.signals],
            "task_fingerprint": self.task.fingerprint(),
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this item."""

        return _stable_sha256(self.canonical_payload())


@dataclass(frozen=True, slots=True)
class CurriculumFrontierPlan:
    """Ranked task-selection plan for a Wave 8 task suite."""

    plan_id: str
    suite: UnknownTaskSuite
    items: tuple[FrontierItem, ...]
    selected_task_id: str | None
    findings: tuple[str, ...] = ()
    schema_version: str = WAVE_EIGHT_FRONTIER_PLAN_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate frontier plan coverage and selection."""

        object.__setattr__(
            self,
            "plan_id",
            _require_non_empty(self.plan_id, "plan_id"),
        )
        object.__setattr__(
            self,
            "items",
            tuple(self.items),
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
        if not self.items:
            raise ValueError("Curriculum frontier plans require items.")
        suite_task_ids = {task.task_id for task in self.suite.tasks}
        item_task_ids = {item.task.task_id for item in self.items}
        if suite_task_ids != item_task_ids:
            raise ValueError("Curriculum frontier plans must cover every suite task.")
        if self.selected_task_id is not None:
            if self.selected_task_id not in suite_task_ids:
                raise ValueError("Selected task id is not in the suite.")
            selected_items = [
                item for item in self.items if item.task.task_id == self.selected_task_id
            ]
            if not selected_items or not selected_items[0].selectable:
                raise ValueError("Selected task must be selectable.")

    @property
    def selected_item(self) -> FrontierItem | None:
        """Return the selected item, if any."""

        if self.selected_task_id is None:
            return None
        return next(
            item for item in self.items if item.task.task_id == self.selected_task_id
        )

    @property
    def has_selection(self) -> bool:
        """Return whether the plan selected a next task."""

        return self.selected_task_id is not None

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic frontier plan payload."""

        return {
            "findings": list(self.findings),
            "item_fingerprints": [item.fingerprint() for item in self.items],
            "plan_id": self.plan_id,
            "schema_version": self.schema_version,
            "selected_task_id": self.selected_task_id or "",
            "suite_fingerprint": self.suite.fingerprint(),
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this plan."""

        return _stable_sha256(self.canonical_payload())


def build_curriculum_frontier_plan(
    *,
    plan_id: str,
    suite: UnknownTaskSuite,
    completed_trials: Iterable[TransferTrialRecord] = (),
    hold_hidden_validation: bool = True,
) -> CurriculumFrontierPlan:
    """Build a deterministic curriculum frontier from task and trial evidence."""

    trial_by_task_id = {trial.task.task_id: trial for trial in completed_trials}
    items = tuple(
        _frontier_item_for_task(
            task=task,
            trial=trial_by_task_id.get(task.task_id),
            hold_hidden_validation=hold_hidden_validation,
        )
        for task in suite.tasks
    )
    ranked_items = tuple(
        sorted(
            items,
            key=lambda item: (
                _priority_rank(item.priority),
                -item.score,
                _difficulty_rank(item.task.difficulty),
                item.task.task_id,
            ),
        )
    )
    selected = next((item for item in ranked_items if item.selectable), None)
    findings: list[str] = []
    if selected is None:
        findings.append("no-selectable-frontier-item")
    if any(item.priority is FrontierPriority.HOLD_HIDDEN_VALIDATION for item in items):
        findings.append("hidden-validation-held")
    if any(item.priority is FrontierPriority.BLOCKED for item in items):
        findings.append("blocked-frontier-item-present")

    return CurriculumFrontierPlan(
        plan_id=plan_id,
        suite=suite,
        items=ranked_items,
        selected_task_id=selected.task.task_id if selected else None,
        findings=tuple(findings),
    )


def _frontier_item_for_task(
    *,
    task: UnknownTaskInstance,
    trial: TransferTrialRecord | None,
    hold_hidden_validation: bool,
) -> FrontierItem:
    signals = _signals_for_task(
        task=task,
        trial=trial,
        hold_hidden_validation=hold_hidden_validation,
    )
    priority = _priority_for_signals(signals)
    return FrontierItem(
        item_id=f"{task.task_id}:frontier-item",
        task=task,
        signals=signals,
        priority=priority,
    )


def _signals_for_task(
    *,
    task: UnknownTaskInstance,
    trial: TransferTrialRecord | None,
    hold_hidden_validation: bool,
) -> tuple[CurriculumSignal, ...]:
    if trial is None:
        return (_new_task_signal(task=task, hold_hidden_validation=hold_hidden_validation),)

    if trial.status is TransferTrialStatus.BLOCKED:
        return (
            CurriculumSignal(
                signal_id=f"{task.task_id}:blocked-evidence",
                task=task,
                kind=CurriculumSignalKind.BLOCKED_EVIDENCE,
                rationale="Prior trial is blocked and cannot support selection.",
                evidence_ids=(trial.fingerprint(),),
                score=0,
            ),
        )
    if trial.status is TransferTrialStatus.NEEDS_MEASURED_RESULT:
        return (
            CurriculumSignal(
                signal_id=f"{task.task_id}:stale-replay",
                task=task,
                kind=CurriculumSignalKind.STALE_REPLAY,
                rationale="Prior trial needs measured result before promotion.",
                evidence_ids=(trial.fingerprint(),),
                score=35,
            ),
        )
    if trial.status is TransferTrialStatus.REPLAYABLE_FAIL:
        return (
            CurriculumSignal(
                signal_id=f"{task.task_id}:recoverable-failure",
                task=task,
                kind=_gap_kind_for_task(task),
                rationale="Replayable failure exposes useful frontier pressure.",
                evidence_ids=(trial.fingerprint(),),
                score=_gap_score_for_task(task),
            ),
        )
    return (
        CurriculumSignal(
            signal_id=f"{task.task_id}:too-easy",
            task=task,
            kind=CurriculumSignalKind.TOO_EASY,
            rationale="Replayable pass already exists; prefer harder frontier pressure.",
            evidence_ids=(trial.fingerprint(),),
            score=5,
        ),
    )


def _new_task_signal(
    *, task: UnknownTaskInstance, hold_hidden_validation: bool
) -> CurriculumSignal:
    if task.is_hidden_validation and hold_hidden_validation:
        return CurriculumSignal(
            signal_id=f"{task.task_id}:hidden-validation-gap",
            task=task,
            kind=CurriculumSignalKind.HIDDEN_VALIDATION_GAP,
            rationale="Hidden validation is preserved until seed and transfer pressure exist.",
            evidence_ids=task.evidence_ids,
            score=60,
        )
    if task.difficulty is TaskDifficulty.SEED:
        return CurriculumSignal(
            signal_id=f"{task.task_id}:new-seed",
            task=task,
            kind=CurriculumSignalKind.NEW_SEED,
            rationale="Seed task has no prior trial and can establish baseline evidence.",
            evidence_ids=task.evidence_ids,
            score=40,
        )
    return CurriculumSignal(
        signal_id=f"{task.task_id}:new-transfer-gap",
        task=task,
        kind=_gap_kind_for_task(task),
        rationale="Transfer task has no prior trial and can pressure generalization.",
        evidence_ids=task.evidence_ids,
        score=_gap_score_for_task(task),
    )


def _gap_kind_for_task(task: UnknownTaskInstance) -> CurriculumSignalKind:
    if task.difficulty is TaskDifficulty.FAR_TRANSFER:
        return CurriculumSignalKind.FAR_TRANSFER_GAP
    if task.difficulty is TaskDifficulty.ADVERSARIAL:
        return CurriculumSignalKind.ADVERSARIAL_GAP
    if task.difficulty is TaskDifficulty.HIDDEN_VALIDATION:
        return CurriculumSignalKind.HIDDEN_VALIDATION_GAP
    return CurriculumSignalKind.TRANSFER_GAP


def _gap_score_for_task(task: UnknownTaskInstance) -> int:
    if task.difficulty is TaskDifficulty.HIDDEN_VALIDATION:
        return 90
    if task.difficulty is TaskDifficulty.ADVERSARIAL:
        return 85
    if task.difficulty is TaskDifficulty.FAR_TRANSFER:
        return 80
    if task.difficulty is TaskDifficulty.NEAR_TRANSFER:
        return 70
    return 50


def _priority_for_signals(signals: tuple[CurriculumSignal, ...]) -> FrontierPriority:
    if any(signal.blocks_selection for signal in signals):
        return FrontierPriority.BLOCKED
    if any(signal.holds_hidden_validation for signal in signals):
        return FrontierPriority.HOLD_HIDDEN_VALIDATION
    if any(signal.kind is CurriculumSignalKind.STALE_REPLAY for signal in signals):
        return FrontierPriority.SELECT_AFTER_REPLAY
    if any(signal.kind is CurriculumSignalKind.TOO_EASY for signal in signals):
        return FrontierPriority.DEFER_TOO_EASY
    if any(signal.kind is CurriculumSignalKind.TOO_HARD for signal in signals):
        return FrontierPriority.DEFER_TOO_HARD
    return FrontierPriority.SELECT_NOW


def _priority_rank(priority: FrontierPriority) -> int:
    ranks = {
        FrontierPriority.SELECT_NOW: 0,
        FrontierPriority.SELECT_AFTER_REPLAY: 1,
        FrontierPriority.HOLD_HIDDEN_VALIDATION: 2,
        FrontierPriority.DEFER_TOO_EASY: 3,
        FrontierPriority.DEFER_TOO_HARD: 4,
        FrontierPriority.BLOCKED: 5,
    }
    return ranks[priority]


def _difficulty_rank(difficulty: TaskDifficulty) -> int:
    ranks = {
        TaskDifficulty.HIDDEN_VALIDATION: 0,
        TaskDifficulty.ADVERSARIAL: 1,
        TaskDifficulty.FAR_TRANSFER: 2,
        TaskDifficulty.NEAR_TRANSFER: 3,
        TaskDifficulty.SEED: 4,
    }
    return ranks[difficulty]


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


def _stable_sha256(payload: Mapping[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
