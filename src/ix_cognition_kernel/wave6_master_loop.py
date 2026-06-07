"""Clean Wave 6 master-loop trace model.

This module turns the Wave 6 claim boundary into a concrete loop trace that can
be tested without messy cross-repo glue. It does not execute actions, certify
intelligence, or claim AGI. It only records whether the required sequence exists
and whether every step is evidence-bound, review-gated, and ordered.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, TypeVar

from ix_cognition_kernel.wave6_contracts import (
    WAVE_SIX_REQUIRED_CLAIM_BOUNDARIES,
    WAVE_SIX_REQUIRED_LOOP_STAGES,
    WaveSixClaimBoundary,
    WaveSixDecisionState,
    WaveSixLoopStage,
    WaveSixSourceSystem,
)

T = TypeVar("T")
E = TypeVar("E", bound=StrEnum)

WAVE_SIX_MASTER_LOOP_STEP_SCHEMA_VERSION = "ix-cognition-kernel-wave6-loop-step-v1"
WAVE_SIX_MASTER_LOOP_TRACE_SCHEMA_VERSION = "ix-cognition-kernel-wave6-loop-trace-v1"


class WaveSixLoopReadiness(StrEnum):
    """Deterministic readiness states for the master cognition loop."""

    INCOMPLETE = "incomplete"
    ORDER_INVALID = "order-invalid"
    EVIDENCE_MISSING = "evidence-missing"
    BLOCKED = "blocked"
    READY_FOR_HUMAN_REVIEW = "ready-for-human-review"


@dataclass(frozen=True, slots=True)
class WaveSixMasterLoopStep:
    """One ordered stage in the Wave 6 measured cognition loop."""

    step_id: str
    stage: WaveSixLoopStage
    summary: str
    source_system: WaveSixSourceSystem
    evidence_ids: tuple[str, ...]
    prior_step_id: str | None = None
    decision: WaveSixDecisionState = WaveSixDecisionState.NEEDS_MORE_EVIDENCE
    measured_reality_signal: bool = False
    changes_future_reasoning: bool = False
    human_review_required: bool = True
    allows_autonomous_execution: bool = False
    claim_boundaries: tuple[WaveSixClaimBoundary, ...] = (
        WAVE_SIX_REQUIRED_CLAIM_BOUNDARIES
    )
    schema_version: str = WAVE_SIX_MASTER_LOOP_STEP_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate that the step is bounded, reviewable, and non-autonomous."""

        if not self.human_review_required:
            raise ValueError("Wave 6 loop steps must require human review.")
        if self.allows_autonomous_execution:
            raise ValueError("Wave 6 loop steps must not allow autonomous execution.")
        object.__setattr__(self, "step_id", _require_non_empty(self.step_id, "step_id"))
        object.__setattr__(self, "summary", _require_non_empty(self.summary, "summary"))
        if self.prior_step_id is not None:
            object.__setattr__(
                self,
                "prior_step_id",
                _require_non_empty(self.prior_step_id, "prior_step_id"),
            )
        object.__setattr__(
            self,
            "evidence_ids",
            _normalize_unique_text_tuple(self.evidence_ids, label="evidence_id"),
        )
        object.__setattr__(
            self,
            "claim_boundaries",
            _normalize_unique_enum_tuple(self.claim_boundaries, label="claim boundary"),
        )
        object.__setattr__(
            self,
            "schema_version",
            _require_non_empty(self.schema_version, "schema_version"),
        )
        missing_boundaries = tuple(
            boundary
            for boundary in WAVE_SIX_REQUIRED_CLAIM_BOUNDARIES
            if boundary not in self.claim_boundaries
        )
        if missing_boundaries:
            raise ValueError(
                "Wave 6 loop steps must preserve required claim boundary: "
                f"{missing_boundaries[0].value}"
            )
        if self.review_ready and not self.evidence_ids:
            raise ValueError("Review-ready Wave 6 loop steps require evidence ids.")
        if self.changes_future_reasoning and not self.measured_reality_signal:
            raise ValueError(
                "Future reasoning change requires a measured reality signal."
            )

    @property
    def evidence_bound(self) -> bool:
        """Return whether the step references evidence."""

        return bool(self.evidence_ids)

    @property
    def review_ready(self) -> bool:
        """Return whether this step can enter human review."""

        return self.decision in {
            WaveSixDecisionState.READY_FOR_WAVE_SIX_LOOP,
            WaveSixDecisionState.READY_FOR_INDEPENDENT_REVIEW,
        }

    @property
    def blocked(self) -> bool:
        """Return whether this step blocks the master loop."""

        return self.decision is WaveSixDecisionState.BLOCKED

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic payload for hashing and review."""

        return {
            "allows_autonomous_execution": self.allows_autonomous_execution,
            "changes_future_reasoning": self.changes_future_reasoning,
            "claim_boundaries": [boundary.value for boundary in self.claim_boundaries],
            "decision": self.decision.value,
            "evidence_ids": list(self.evidence_ids),
            "human_review_required": self.human_review_required,
            "measured_reality_signal": self.measured_reality_signal,
            "prior_step_id": self.prior_step_id,
            "schema_version": self.schema_version,
            "source_system": self.source_system.value,
            "stage": self.stage.value,
            "step_id": self.step_id,
            "summary": self.summary,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this loop step."""

        return _stable_sha256(self.canonical_payload())


@dataclass(frozen=True, slots=True)
class WaveSixMasterLoopTrace:
    """A clean, ordered, testable Wave 6 measured cognition trace."""

    trace_id: str
    objective: str
    steps: tuple[WaveSixMasterLoopStep, ...]
    required_stages: tuple[WaveSixLoopStage, ...] = WAVE_SIX_REQUIRED_LOOP_STAGES
    notes: tuple[str, ...] = ()
    schema_version: str = WAVE_SIX_MASTER_LOOP_TRACE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate identity, ordering inputs, and uniqueness."""

        object.__setattr__(
            self,
            "trace_id",
            _require_non_empty(self.trace_id, "trace_id"),
        )
        object.__setattr__(
            self,
            "objective",
            _require_non_empty(self.objective, "objective"),
        )
        if not self.steps:
            raise ValueError("Wave 6 master-loop traces require at least one step.")
        _unique_ids((step.step_id for step in self.steps), label="step_id")
        _unique_ids((step.stage for step in self.steps), label="loop stage")
        object.__setattr__(
            self,
            "required_stages",
            _normalize_unique_enum_tuple(
                self.required_stages, label="required loop stage"
            ),
        )
        object.__setattr__(
            self,
            "notes",
            _normalize_unique_text_tuple(self.notes, label="trace note"),
        )
        object.__setattr__(
            self,
            "schema_version",
            _require_non_empty(self.schema_version, "schema_version"),
        )

    @property
    def stage_sequence(self) -> tuple[WaveSixLoopStage, ...]:
        """Return the loop stages in recorded order."""

        return tuple(step.stage for step in self.steps)

    @property
    def step_ids(self) -> tuple[str, ...]:
        """Return step ids in recorded order."""

        return tuple(step.step_id for step in self.steps)

    @property
    def covered_stages(self) -> tuple[WaveSixLoopStage, ...]:
        """Return required stages covered by the trace."""

        present = set(self.stage_sequence)
        return tuple(stage for stage in self.required_stages if stage in present)

    @property
    def missing_stages(self) -> tuple[WaveSixLoopStage, ...]:
        """Return required stages missing from the trace."""

        present = set(self.stage_sequence)
        return tuple(stage for stage in self.required_stages if stage not in present)

    @property
    def out_of_order_stage_pairs(
        self,
    ) -> tuple[tuple[WaveSixLoopStage, WaveSixLoopStage], ...]:
        """Return adjacent stage pairs that violate required order."""

        required_index = {
            stage: index for index, stage in enumerate(self.required_stages)
        }
        invalid_pairs: list[tuple[WaveSixLoopStage, WaveSixLoopStage]] = []
        for previous, current in zip(
            self.stage_sequence, self.stage_sequence[1:], strict=False
        ):
            if required_index[current] <= required_index[previous]:
                invalid_pairs.append((previous, current))
        return tuple(invalid_pairs)

    @property
    def invalid_prior_links(self) -> tuple[str, ...]:
        """Return steps whose declared prior step does not match recorded order."""

        invalid: list[str] = []
        for index, step in enumerate(self.steps):
            expected_prior = None if index == 0 else self.steps[index - 1].step_id
            if step.prior_step_id != expected_prior:
                invalid.append(step.step_id)
        return tuple(invalid)

    @property
    def blocked_step_ids(self) -> tuple[str, ...]:
        """Return step ids that block the trace."""

        return tuple(step.step_id for step in self.steps if step.blocked)

    @property
    def evidence_missing_step_ids(self) -> tuple[str, ...]:
        """Return step ids that are not evidence-bound."""

        return tuple(step.step_id for step in self.steps if not step.evidence_bound)

    @property
    def has_complete_required_order(self) -> bool:
        """Return whether the trace exactly follows required stage order."""

        return self.stage_sequence == self.required_stages

    @property
    def reality_corrected_reasoning_step_ids(self) -> tuple[str, ...]:
        """Return steps proving measured reality changed future reasoning."""

        return tuple(
            step.step_id
            for step in self.steps
            if step.measured_reality_signal and step.changes_future_reasoning
        )

    @property
    def readiness(self) -> WaveSixLoopReadiness:
        """Return fail-closed readiness for the full master-loop trace."""

        if self.blocked_step_ids:
            return WaveSixLoopReadiness.BLOCKED
        if self.missing_stages:
            return WaveSixLoopReadiness.INCOMPLETE
        if self.out_of_order_stage_pairs or self.invalid_prior_links:
            return WaveSixLoopReadiness.ORDER_INVALID
        if self.evidence_missing_step_ids:
            return WaveSixLoopReadiness.EVIDENCE_MISSING
        return WaveSixLoopReadiness.READY_FOR_HUMAN_REVIEW

    @property
    def ready_for_human_review(self) -> bool:
        """Return whether the trace can enter Wave 6 human review."""

        return self.readiness is WaveSixLoopReadiness.READY_FOR_HUMAN_REVIEW

    def step_for_stage(self, stage: WaveSixLoopStage) -> WaveSixMasterLoopStep | None:
        """Return the step for a stage, if present."""

        for step in self.steps:
            if step.stage is stage:
                return step
        return None

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic payload for trace hashing and review."""

        return {
            "objective": self.objective,
            "notes": list(self.notes),
            "readiness": self.readiness.value,
            "required_stages": [stage.value for stage in self.required_stages],
            "schema_version": self.schema_version,
            "steps": [step.canonical_payload() for step in self.steps],
            "trace_id": self.trace_id,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this trace."""

        return _stable_sha256(self.canonical_payload())


def build_wave_six_master_loop_trace(
    *,
    trace_id: str,
    objective: str,
    steps: Iterable[WaveSixMasterLoopStep],
    notes: Iterable[str] = (),
) -> WaveSixMasterLoopTrace:
    """Build a Wave 6 trace while preserving caller-provided stage order."""

    return WaveSixMasterLoopTrace(
        trace_id=trace_id,
        objective=objective,
        steps=tuple(steps),
        notes=tuple(notes),
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
    """Normalize text values while rejecting blanks and duplicates."""

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
    """Return enum values as a tuple while rejecting duplicates."""

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
