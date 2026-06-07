"""Canonical Wave 6 master-loop blueprints.

The master loop must stay clean, simple, and testable. This module locks one
canonical blueprint per required Wave 6 loop stage, then builds an ordered
``WaveSixMasterLoopTrace`` without reaching into donor repo internals. Later
commits can attach stronger evidence to the same stable stages instead of
rewriting glue code.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any

from ix_cognition_kernel.wave6_contracts import (
    WaveSixDecisionState,
    WaveSixLoopStage,
    WaveSixSourceSystem,
)
from ix_cognition_kernel.wave6_master_loop import (
    WaveSixMasterLoopStep,
    WaveSixMasterLoopTrace,
    build_wave_six_master_loop_trace,
)

WAVE_SIX_LOOP_BLUEPRINT_SCHEMA_VERSION = "ix-cognition-kernel-wave6-loop-blueprint-v1"
WAVE_SIX_CANONICAL_TRACE_ID = "wave6-canonical-master-loop-trace"
WAVE_SIX_CANONICAL_OBJECTIVE = (
    "Measure whether the combined Wave 6 system changes future reasoning because "
    "measured reality corrected it."
)


@dataclass(frozen=True, slots=True)
class WaveSixLoopStepBlueprint:
    """Blueprint for one canonical master-loop step."""

    blueprint_id: str
    stage: WaveSixLoopStage
    source_system: WaveSixSourceSystem
    summary: str
    evidence_ids: tuple[str, ...]
    measured_reality_signal: bool = False
    changes_future_reasoning: bool = False
    decision: WaveSixDecisionState = WaveSixDecisionState.READY_FOR_WAVE_SIX_LOOP
    schema_version: str = WAVE_SIX_LOOP_BLUEPRINT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Normalize blueprint fields and prevent fake future-reasoning claims."""

        object.__setattr__(
            self,
            "blueprint_id",
            _require_non_empty(self.blueprint_id, "blueprint_id"),
        )
        object.__setattr__(
            self,
            "summary",
            _require_non_empty(self.summary, "summary"),
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
            raise ValueError("Loop step blueprints require evidence ids.")
        if self.changes_future_reasoning and not self.measured_reality_signal:
            raise ValueError(
                "Future reasoning change requires measured reality correction."
            )

    @property
    def step_id(self) -> str:
        """Return deterministic step id produced by this blueprint."""

        return f"step-{self.blueprint_id}"

    def to_step(self, *, prior_step_id: str | None) -> WaveSixMasterLoopStep:
        """Convert this blueprint into a concrete master-loop step."""

        return WaveSixMasterLoopStep(
            step_id=self.step_id,
            stage=self.stage,
            summary=self.summary,
            source_system=self.source_system,
            evidence_ids=self.evidence_ids,
            prior_step_id=prior_step_id,
            decision=self.decision,
            measured_reality_signal=self.measured_reality_signal,
            changes_future_reasoning=self.changes_future_reasoning,
        )

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic payload for hashing and review."""

        return {
            "blueprint_id": self.blueprint_id,
            "changes_future_reasoning": self.changes_future_reasoning,
            "decision": self.decision.value,
            "evidence_ids": list(self.evidence_ids),
            "measured_reality_signal": self.measured_reality_signal,
            "schema_version": self.schema_version,
            "source_system": self.source_system.value,
            "stage": self.stage.value,
            "step_id": self.step_id,
            "summary": self.summary,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this blueprint."""

        return _stable_sha256(self.canonical_payload())


def canonical_wave_six_loop_step_blueprints() -> tuple[WaveSixLoopStepBlueprint, ...]:
    """Return one locked blueprint per required Wave 6 master-loop stage."""

    return (
        WaveSixLoopStepBlueprint(
            blueprint_id="01-intent",
            stage=WaveSixLoopStage.INTENT,
            source_system=WaveSixSourceSystem.IX_MAIN,
            summary=(
                "Record the human-readable intent and bounded objective before "
                "any prediction, trial, or review action."
            ),
            evidence_ids=("wave6-loop:intent-contract",),
        ),
        WaveSixLoopStepBlueprint(
            blueprint_id="02-permission",
            stage=WaveSixLoopStage.PERMISSION,
            source_system=WaveSixSourceSystem.IX_AUTONOMY_ASSURANCE_RUNTIME,
            summary=(
                "Apply permission, hazard, and human-authority gates before the "
                "system may proceed to prediction or trial."
            ),
            evidence_ids=("wave6-loop:permission-gate",),
        ),
        WaveSixLoopStepBlueprint(
            blueprint_id="03-prediction",
            stage=WaveSixLoopStage.PREDICTION,
            source_system=WaveSixSourceSystem.IX_BLACKFOX_WORLDTWIN,
            summary=(
                "Create an evidence-bound prediction before outcome data is known."
            ),
            evidence_ids=("wave6-loop:prediction-before-outcome",),
        ),
        WaveSixLoopStepBlueprint(
            blueprint_id="04-trial",
            stage=WaveSixLoopStage.TRIAL,
            source_system=WaveSixSourceSystem.IX_BLACKFOX,
            summary=(
                "Run only a bounded, reviewable trial path with evidence capture "
                "and no autonomous authority."
            ),
            evidence_ids=("wave6-loop:bounded-trial",),
        ),
        WaveSixLoopStepBlueprint(
            blueprint_id="05-outcome",
            stage=WaveSixLoopStage.OUTCOME,
            source_system=WaveSixSourceSystem.IX_INTENT_REALITY_LOOP,
            summary="Record measured outcome evidence from the bounded trial.",
            evidence_ids=("wave6-loop:measured-outcome",),
            measured_reality_signal=True,
        ),
        WaveSixLoopStepBlueprint(
            blueprint_id="06-delta",
            stage=WaveSixLoopStage.DELTA,
            source_system=WaveSixSourceSystem.IX_BLACKFOX_WORLDTWIN,
            summary=(
                "Compare prediction against measured outcome and capture the "
                "reality delta."
            ),
            evidence_ids=("wave6-loop:prediction-outcome-delta",),
            measured_reality_signal=True,
        ),
        WaveSixLoopStepBlueprint(
            blueprint_id="07-memory-update",
            stage=WaveSixLoopStage.MEMORY_UPDATE,
            source_system=WaveSixSourceSystem.IX_COGNITION_KERNEL,
            summary=(
                "Update or quarantine memory so future reasoning changes only "
                "when measured reality justifies correction."
            ),
            evidence_ids=("wave6-loop:reality-corrected-memory-update",),
            measured_reality_signal=True,
            changes_future_reasoning=True,
        ),
        WaveSixLoopStepBlueprint(
            blueprint_id="08-transfer-check",
            stage=WaveSixLoopStage.TRANSFER_CHECK,
            source_system=WaveSixSourceSystem.IX_FUNCTION,
            summary=(
                "Pressure-test whether the corrected causal structure transfers "
                "to a different domain without hand-scripted rescue."
            ),
            evidence_ids=("wave6-loop:cross-domain-transfer-check",),
        ),
        WaveSixLoopStepBlueprint(
            blueprint_id="09-falsification",
            stage=WaveSixLoopStage.FALSIFICATION,
            source_system=WaveSixSourceSystem.IX_FUNCTION,
            summary=(
                "Apply falsification and negative-control pressure before any "
                "maturity or capability interpretation."
            ),
            evidence_ids=("wave6-loop:falsification-negative-control",),
        ),
        WaveSixLoopStepBlueprint(
            blueprint_id="10-human-review",
            stage=WaveSixLoopStage.HUMAN_REVIEW,
            source_system=WaveSixSourceSystem.HUMAN_REVIEW,
            summary=(
                "Present the full trace for human review with no AGI, production, "
                "certification, or autonomous-authority claim."
            ),
            evidence_ids=("wave6-loop:human-review-docket",),
        ),
    )


def build_canonical_wave_six_master_loop_trace() -> WaveSixMasterLoopTrace:
    """Build the canonical ordered Wave 6 master-loop trace."""

    steps: list[WaveSixMasterLoopStep] = []
    prior_step_id: str | None = None
    for blueprint in canonical_wave_six_loop_step_blueprints():
        step = blueprint.to_step(prior_step_id=prior_step_id)
        steps.append(step)
        prior_step_id = step.step_id
    return build_wave_six_master_loop_trace(
        trace_id=WAVE_SIX_CANONICAL_TRACE_ID,
        objective=WAVE_SIX_CANONICAL_OBJECTIVE,
        steps=steps,
        notes=(
            "Canonical Wave 6 trace for measured system-level cognition; this is "
            "not an AGI claim.",
        ),
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


def _stable_sha256(payload: Mapping[str, Any]) -> str:
    """Return deterministic SHA-256 over a canonical JSON payload."""

    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
