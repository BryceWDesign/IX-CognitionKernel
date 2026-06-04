"""Wave 5 WorldTwin scenario and consequence bridge records.

Wave 5 needs scenario evidence that is useful without being magical. This module
records WorldTwin-style assumptions, consequence predictions, reality-delta
checks, falsification paths, and review controls. The bridge can make simulated
or scenario-derived evidence reviewable, but it never treats simulation as truth,
never grants execution authority, and never converts a scenario pass into AGI,
production, certification, or independent-validation proof.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, TypeVar

from ix_cognition_kernel.wave5_contracts import (
    WAVE_FIVE_REQUIRED_CLAIM_BOUNDARIES,
    WaveFiveArtifactDecision,
    WaveFiveArtifactKind,
    WaveFiveArtifactRef,
    WaveFiveAuthorityState,
    WaveFiveCapabilityArea,
    WaveFiveClaimBoundary,
    WaveFiveSourceSystem,
    WaveFiveValidationStatus,
)

T = TypeVar("T")
E = TypeVar("E", bound=StrEnum)

WAVE_FIVE_SCENARIO_ASSUMPTION_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave5-worldtwin-assumption-v1"
)
WAVE_FIVE_CONSEQUENCE_PREDICTION_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave5-worldtwin-prediction-v1"
)
WAVE_FIVE_REALITY_DELTA_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave5-worldtwin-reality-delta-v1"
)
WAVE_FIVE_WORLDTWIN_CONTROL_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave5-worldtwin-control-v1"
)
WAVE_FIVE_WORLDTWIN_BRIDGE_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave5-worldtwin-bridge-v1"
)


class WaveFiveScenarioAssumptionKind(StrEnum):
    """Assumption classes required for WorldTwin-style scenario review."""

    INITIAL_CONDITIONS = "initial-conditions"
    OPERATIONAL_CONSTRAINTS = "operational-constraints"
    UNCERTAINTY_BOUNDARY = "uncertainty-boundary"
    HUMAN_AUTHORITY_BOUNDARY = "human-authority-boundary"
    FAILURE_MODE = "failure-mode"
    ROLLBACK_PATH = "rollback-path"
    CLAIM_BOUNDARY = "claim-boundary"
    EXTERNAL_VALIDATION_LIMIT = "external-validation-limit"


class WaveFiveConsequenceKind(StrEnum):
    """Consequence classes the bridge must reason about before Wave 6."""

    SAFETY_CONSEQUENCE = "safety-consequence"
    AUTHORITY_CONSEQUENCE = "authority-consequence"
    LONG_HORIZON_CONSEQUENCE = "long-horizon-consequence"
    MEMORY_CONSEQUENCE = "memory-consequence"
    TRANSFER_CONSEQUENCE = "transfer-consequence"
    REFUSAL_CONSEQUENCE = "refusal-consequence"
    REPEATABILITY_CONSEQUENCE = "repeatability-consequence"
    WAVE_SIX_READINESS_CONSEQUENCE = "wave-six-readiness-consequence"


class WaveFivePredictionDisposition(StrEnum):
    """Disposition of one WorldTwin-style consequence prediction."""

    REVIEWABLE_WITH_BOUNDARIES = "reviewable-with-boundaries"
    REVIEWABLE_LIMITATION = "reviewable-limitation"
    FALSIFIED = "falsified"
    NEEDS_MORE_EVIDENCE = "needs-more-evidence"
    UNSAFE_TO_ACT = "unsafe-to-act"


class WaveFiveRealityDeltaKind(StrEnum):
    """Kinds of reality-delta checks that keep scenarios grounded."""

    ASSUMPTION_DRIFT = "assumption-drift"
    PREDICTION_MISMATCH = "prediction-mismatch"
    OBSERVED_FAILURE = "observed-failure"
    EXTERNAL_REVIEW_DELTA = "external-review-delta"
    HUMAN_AUTHORITY_DELTA = "human-authority-delta"
    WAVE_SIX_LIMITATION_DELTA = "wave-six-limitation-delta"


class WaveFiveRealityDeltaDisposition(StrEnum):
    """Disposition of one reality-delta check."""

    NO_BLOCKING_DELTA = "no-blocking-delta"
    LIMITATION_RECORDED = "limitation-recorded"
    FALSIFICATION_RECORDED = "falsification-recorded"
    NEEDS_MORE_EVIDENCE = "needs-more-evidence"
    BLOCKING_DELTA = "blocking-delta"


class WaveFiveWorldTwinControlKind(StrEnum):
    """Controls that stop scenario evidence from becoming overclaim theater."""

    ASSUMPTION_LEDGER_PRESENT = "assumption-ledger-present"
    PREDICTION_EVIDENCE_BOUND = "prediction-evidence-bound"
    FALSIFICATION_PATH_PRESENT = "falsification-path-present"
    REALITY_DELTA_RECORDED = "reality-delta-recorded"
    UNCERTAINTY_VISIBLE = "uncertainty-visible"
    HUMAN_AUTHORITY_PRESERVED = "human-authority-preserved"
    NO_SIMULATION_AS_PROOF = "no-simulation-as-proof"
    NO_EXECUTION_AUTHORITY = "no-execution-authority"
    WAVE_SIX_LIMITATION_VISIBLE = "wave-six-limitation-visible"


class WaveFiveWorldTwinControlResult(StrEnum):
    """Observed result of one WorldTwin bridge control."""

    PASSED = "passed"
    PASSED_WITH_LIMITS = "passed-with-limits"
    NEEDS_MORE_EVIDENCE = "needs-more-evidence"
    FAILED = "failed"


class WaveFiveWorldTwinBridgeState(StrEnum):
    """Review state of a WorldTwin scenario bridge."""

    INTERNAL_SCENARIO_READY = "internal-scenario-ready"
    READY_FOR_EXTERNAL_SCENARIO_REVIEW = "ready-for-external-scenario-review"
    UNDER_EXTERNAL_SCENARIO_REVIEW = "under-external-scenario-review"
    EXTERNALLY_REVIEWED_WITH_BOUNDARIES = "externally-reviewed-with-boundaries"
    BLOCKED_BY_SCENARIO_FAILURE = "blocked-by-scenario-failure"


SAFE_PREDICTION_DISPOSITIONS: tuple[WaveFivePredictionDisposition, ...] = (
    WaveFivePredictionDisposition.REVIEWABLE_WITH_BOUNDARIES,
    WaveFivePredictionDisposition.REVIEWABLE_LIMITATION,
)

BLOCKING_PREDICTION_DISPOSITIONS: tuple[WaveFivePredictionDisposition, ...] = (
    WaveFivePredictionDisposition.FALSIFIED,
    WaveFivePredictionDisposition.NEEDS_MORE_EVIDENCE,
    WaveFivePredictionDisposition.UNSAFE_TO_ACT,
)

REQUIRED_SCENARIO_ASSUMPTION_KINDS: tuple[
    WaveFiveScenarioAssumptionKind, ...
] = (
    WaveFiveScenarioAssumptionKind.INITIAL_CONDITIONS,
    WaveFiveScenarioAssumptionKind.OPERATIONAL_CONSTRAINTS,
    WaveFiveScenarioAssumptionKind.UNCERTAINTY_BOUNDARY,
    WaveFiveScenarioAssumptionKind.HUMAN_AUTHORITY_BOUNDARY,
    WaveFiveScenarioAssumptionKind.FAILURE_MODE,
    WaveFiveScenarioAssumptionKind.ROLLBACK_PATH,
    WaveFiveScenarioAssumptionKind.CLAIM_BOUNDARY,
    WaveFiveScenarioAssumptionKind.EXTERNAL_VALIDATION_LIMIT,
)

REQUIRED_CONSEQUENCE_KINDS: tuple[WaveFiveConsequenceKind, ...] = (
    WaveFiveConsequenceKind.SAFETY_CONSEQUENCE,
    WaveFiveConsequenceKind.AUTHORITY_CONSEQUENCE,
    WaveFiveConsequenceKind.LONG_HORIZON_CONSEQUENCE,
    WaveFiveConsequenceKind.MEMORY_CONSEQUENCE,
    WaveFiveConsequenceKind.TRANSFER_CONSEQUENCE,
    WaveFiveConsequenceKind.REFUSAL_CONSEQUENCE,
    WaveFiveConsequenceKind.REPEATABILITY_CONSEQUENCE,
    WaveFiveConsequenceKind.WAVE_SIX_READINESS_CONSEQUENCE,
)

REQUIRED_REALITY_DELTA_KINDS: tuple[WaveFiveRealityDeltaKind, ...] = (
    WaveFiveRealityDeltaKind.ASSUMPTION_DRIFT,
    WaveFiveRealityDeltaKind.PREDICTION_MISMATCH,
    WaveFiveRealityDeltaKind.OBSERVED_FAILURE,
    WaveFiveRealityDeltaKind.EXTERNAL_REVIEW_DELTA,
    WaveFiveRealityDeltaKind.HUMAN_AUTHORITY_DELTA,
    WaveFiveRealityDeltaKind.WAVE_SIX_LIMITATION_DELTA,
)

REQUIRED_WORLDTWIN_CONTROL_KINDS: tuple[WaveFiveWorldTwinControlKind, ...] = (
    WaveFiveWorldTwinControlKind.ASSUMPTION_LEDGER_PRESENT,
    WaveFiveWorldTwinControlKind.PREDICTION_EVIDENCE_BOUND,
    WaveFiveWorldTwinControlKind.FALSIFICATION_PATH_PRESENT,
    WaveFiveWorldTwinControlKind.REALITY_DELTA_RECORDED,
    WaveFiveWorldTwinControlKind.UNCERTAINTY_VISIBLE,
    WaveFiveWorldTwinControlKind.HUMAN_AUTHORITY_PRESERVED,
    WaveFiveWorldTwinControlKind.NO_SIMULATION_AS_PROOF,
    WaveFiveWorldTwinControlKind.NO_EXECUTION_AUTHORITY,
    WaveFiveWorldTwinControlKind.WAVE_SIX_LIMITATION_VISIBLE,
)

EXTERNAL_WORLDTWIN_REVIEW_SOURCE_SYSTEMS: tuple[WaveFiveSourceSystem, ...] = (
    WaveFiveSourceSystem.EXTERNAL_REVIEW,
    WaveFiveSourceSystem.INDEPENDENT_REVIEWER,
    WaveFiveSourceSystem.INDEPENDENT_REPLICATION_LAB,
)


@dataclass(frozen=True, slots=True)
class WaveFiveScenarioAssumption:
    """One evidence-bound assumption in a WorldTwin-style scenario."""

    assumption_id: str
    assumption_kind: WaveFiveScenarioAssumptionKind
    statement: str
    uncertainty_summary: str
    falsification_signal: str
    evidence_ids: tuple[str, ...]
    reviewer_visible: bool = True
    schema_version: str = WAVE_FIVE_SCENARIO_ASSUMPTION_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate assumption identity, falsifiability, and evidence."""

        object.__setattr__(
            self, "assumption_id", _text(self.assumption_id, "assumption_id")
        )
        object.__setattr__(self, "statement", _text(self.statement, "statement"))
        object.__setattr__(
            self,
            "uncertainty_summary",
            _text(self.uncertainty_summary, "uncertainty_summary"),
        )
        object.__setattr__(
            self,
            "falsification_signal",
            _text(self.falsification_signal, "falsification_signal"),
        )
        object.__setattr__(
            self, "evidence_ids", _unique_text(self.evidence_ids, label="evidence_id")
        )
        if not self.evidence_ids:
            raise ValueError("Scenario assumptions require evidence ids.")
        if not self.reviewer_visible:
            raise ValueError("Scenario assumptions must be reviewer visible.")
        object.__setattr__(
            self, "schema_version", _text(self.schema_version, "schema_version")
        )

    @property
    def assumption_key(self) -> str:
        """Return deterministic assumption key."""

        return self.assumption_id

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic export payload."""

        return {
            "assumption_id": self.assumption_id,
            "assumption_kind": self.assumption_kind.value,
            "evidence_ids": list(self.evidence_ids),
            "falsification_signal": self.falsification_signal,
            "reviewer_visible": self.reviewer_visible,
            "schema_version": self.schema_version,
            "statement": self.statement,
            "uncertainty_summary": self.uncertainty_summary,
        }


@dataclass(frozen=True, slots=True)
class WaveFiveConsequencePrediction:
    """One bounded consequence prediction derived from scenario assumptions."""

    prediction_id: str
    consequence_kind: WaveFiveConsequenceKind
    disposition: WaveFivePredictionDisposition
    predicted_consequence: str
    assumption_ids: tuple[str, ...]
    uncertainty_summary: str
    falsification_path: str
    evidence_ids: tuple[str, ...]
    preserves_human_authority: bool = True
    grants_execution_authority: bool = False
    claims_simulation_as_truth: bool = False
    schema_version: str = WAVE_FIVE_CONSEQUENCE_PREDICTION_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate prediction boundaries and evidence binding."""

        object.__setattr__(
            self, "prediction_id", _text(self.prediction_id, "prediction_id")
        )
        object.__setattr__(
            self,
            "predicted_consequence",
            _text(self.predicted_consequence, "predicted_consequence"),
        )
        object.__setattr__(
            self,
            "assumption_ids",
            _unique_text(self.assumption_ids, label="assumption_id"),
        )
        object.__setattr__(
            self,
            "uncertainty_summary",
            _text(self.uncertainty_summary, "uncertainty_summary"),
        )
        object.__setattr__(
            self, "falsification_path", _text(self.falsification_path, "path")
        )
        object.__setattr__(
            self, "evidence_ids", _unique_text(self.evidence_ids, label="evidence_id")
        )
        if not self.assumption_ids:
            raise ValueError("Consequence predictions require assumption ids.")
        if not self.evidence_ids:
            raise ValueError("Consequence predictions require evidence ids.")
        if self.grants_execution_authority:
            raise ValueError("WorldTwin predictions cannot grant execution authority.")
        if self.claims_simulation_as_truth:
            raise ValueError("WorldTwin predictions cannot treat simulation as truth.")
        if self.disposition in SAFE_PREDICTION_DISPOSITIONS:
            if not self.preserves_human_authority:
                raise ValueError("Safe predictions must preserve human authority.")
        object.__setattr__(
            self, "schema_version", _text(self.schema_version, "schema_version")
        )

    @property
    def prediction_key(self) -> str:
        """Return deterministic prediction key."""

        return self.prediction_id

    @property
    def blocks_wave_five_progress(self) -> bool:
        """Return whether this prediction blocks scenario readiness."""

        return self.disposition in BLOCKING_PREDICTION_DISPOSITIONS

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic export payload."""

        return {
            "assumption_ids": list(self.assumption_ids),
            "claims_simulation_as_truth": self.claims_simulation_as_truth,
            "consequence_kind": self.consequence_kind.value,
            "disposition": self.disposition.value,
            "evidence_ids": list(self.evidence_ids),
            "falsification_path": self.falsification_path,
            "grants_execution_authority": self.grants_execution_authority,
            "prediction_id": self.prediction_id,
            "predicted_consequence": self.predicted_consequence,
            "preserves_human_authority": self.preserves_human_authority,
            "schema_version": self.schema_version,
            "uncertainty_summary": self.uncertainty_summary,
        }


@dataclass(frozen=True, slots=True)
class WaveFiveRealityDeltaCheck:
    """Reality-delta check comparing scenario prediction to observed evidence."""

    delta_id: str
    prediction_id: str
    delta_kind: WaveFiveRealityDeltaKind
    disposition: WaveFiveRealityDeltaDisposition
    observation_summary: str
    required_response: str
    evidence_ids: tuple[str, ...]
    reviewer_visible: bool = True
    schema_version: str = WAVE_FIVE_REALITY_DELTA_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate reality-delta evidence and visibility."""

        object.__setattr__(self, "delta_id", _text(self.delta_id, "delta_id"))
        object.__setattr__(
            self, "prediction_id", _text(self.prediction_id, "prediction_id")
        )
        object.__setattr__(
            self,
            "observation_summary",
            _text(self.observation_summary, "observation_summary"),
        )
        object.__setattr__(
            self,
            "required_response",
            _text(self.required_response, "required_response"),
        )
        object.__setattr__(
            self, "evidence_ids", _unique_text(self.evidence_ids, label="evidence_id")
        )
        if not self.evidence_ids:
            raise ValueError("Reality-delta checks require evidence ids.")
        if not self.reviewer_visible:
            raise ValueError("Reality-delta checks must be reviewer visible.")
        object.__setattr__(
            self, "schema_version", _text(self.schema_version, "schema_version")
        )

    @property
    def delta_key(self) -> str:
        """Return deterministic delta key."""

        return self.delta_id

    @property
    def blocks_wave_five_progress(self) -> bool:
        """Return whether this delta blocks scenario readiness."""

        return self.disposition in {
            WaveFiveRealityDeltaDisposition.NEEDS_MORE_EVIDENCE,
            WaveFiveRealityDeltaDisposition.BLOCKING_DELTA,
        }

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic export payload."""

        return {
            "delta_id": self.delta_id,
            "delta_kind": self.delta_kind.value,
            "disposition": self.disposition.value,
            "evidence_ids": list(self.evidence_ids),
            "observation_summary": self.observation_summary,
            "prediction_id": self.prediction_id,
            "required_response": self.required_response,
            "reviewer_visible": self.reviewer_visible,
            "schema_version": self.schema_version,
        }


@dataclass(frozen=True, slots=True)
class WaveFiveWorldTwinControl:
    """Control proving the WorldTwin bridge stays bounded and falsifiable."""

    control_id: str
    control_kind: WaveFiveWorldTwinControlKind
    result: WaveFiveWorldTwinControlResult
    description: str
    evidence_ids: tuple[str, ...]
    blocking: bool = True
    schema_version: str = WAVE_FIVE_WORLDTWIN_CONTROL_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate control identity and evidence binding."""

        object.__setattr__(self, "control_id", _text(self.control_id, "control_id"))
        object.__setattr__(self, "description", _text(self.description, "description"))
        object.__setattr__(
            self, "evidence_ids", _unique_text(self.evidence_ids, label="evidence_id")
        )
        if not self.evidence_ids:
            raise ValueError("WorldTwin controls require evidence ids.")
        object.__setattr__(
            self, "schema_version", _text(self.schema_version, "schema_version")
        )

    @property
    def control_key(self) -> str:
        """Return deterministic control key."""

        return self.control_id

    @property
    def passed_with_boundaries(self) -> bool:
        """Return whether this control passed while preserving limitations."""

        return self.result in {
            WaveFiveWorldTwinControlResult.PASSED,
            WaveFiveWorldTwinControlResult.PASSED_WITH_LIMITS,
        }

    @property
    def blocks_wave_five_progress(self) -> bool:
        """Return whether this control blocks scenario readiness."""

        return self.blocking and not self.passed_with_boundaries

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic export payload."""

        return {
            "blocking": self.blocking,
            "control_id": self.control_id,
            "control_kind": self.control_kind.value,
            "description": self.description,
            "evidence_ids": list(self.evidence_ids),
            "result": self.result.value,
            "schema_version": self.schema_version,
        }


@dataclass(frozen=True, slots=True)
class WaveFiveWorldTwinScenarioBridge:
    """Wave 5 bridge from scenario reasoning to reviewable evidence."""

    bridge_id: str
    title: str
    source_system: WaveFiveSourceSystem
    bridge_state: WaveFiveWorldTwinBridgeState
    assumptions: tuple[WaveFiveScenarioAssumption, ...]
    predictions: tuple[WaveFiveConsequencePrediction, ...]
    reality_delta_checks: tuple[WaveFiveRealityDeltaCheck, ...]
    controls: tuple[WaveFiveWorldTwinControl, ...]
    protocol_ids: tuple[str, ...]
    reviewer_ids: tuple[str, ...] = ()
    claims_simulation_as_proof: bool = False
    grants_execution_authority: bool = False
    claims_agi: bool = False
    claim_boundaries: tuple[WaveFiveClaimBoundary, ...] = (
        WAVE_FIVE_REQUIRED_CLAIM_BOUNDARIES
    )
    notes: tuple[str, ...] = ()
    schema_version: str = WAVE_FIVE_WORLDTWIN_BRIDGE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate scenario coverage, deltas, controls, and review boundaries."""

        object.__setattr__(self, "bridge_id", _text(self.bridge_id, "bridge_id"))
        object.__setattr__(self, "title", _text(self.title, "title"))
        if self.claims_simulation_as_proof:
            raise ValueError("WorldTwin bridges cannot claim simulation as proof.")
        if self.grants_execution_authority:
            raise ValueError("WorldTwin bridges cannot grant execution authority.")
        if self.claims_agi:
            raise ValueError("WorldTwin bridges cannot claim AGI.")
        assumptions = tuple(
            sorted(self.assumptions, key=lambda item: item.assumption_key)
        )
        predictions = tuple(
            sorted(self.predictions, key=lambda item: item.prediction_key)
        )
        deltas = tuple(
            sorted(self.reality_delta_checks, key=lambda item: item.delta_key)
        )
        controls = tuple(sorted(self.controls, key=lambda item: item.control_key))
        if not assumptions:
            raise ValueError("WorldTwin bridges require assumptions.")
        if not predictions:
            raise ValueError("WorldTwin bridges require predictions.")
        if not deltas:
            raise ValueError("WorldTwin bridges require reality-delta checks.")
        if not controls:
            raise ValueError("WorldTwin bridges require controls.")
        assumption_ids = _unique_values(
            (item.assumption_id for item in assumptions), label="assumption_id"
        )
        prediction_ids = _unique_values(
            (item.prediction_id for item in predictions), label="prediction_id"
        )
        _unique_values((item.delta_id for item in deltas), label="delta_id")
        _unique_values((item.control_id for item in controls), label="control_id")
        self._validate_prediction_assumptions(assumption_ids, predictions)
        self._validate_delta_references(prediction_ids, deltas)
        object.__setattr__(self, "assumptions", assumptions)
        object.__setattr__(self, "predictions", predictions)
        object.__setattr__(self, "reality_delta_checks", deltas)
        object.__setattr__(self, "controls", controls)
        object.__setattr__(
            self, "protocol_ids", _unique_text(self.protocol_ids, label="protocol_id")
        )
        if not self.protocol_ids:
            raise ValueError("WorldTwin bridges require protocol ids.")
        object.__setattr__(
            self, "reviewer_ids", _unique_text(self.reviewer_ids, label="reviewer_id")
        )
        object.__setattr__(
            self,
            "claim_boundaries",
            _unique_enum(self.claim_boundaries, label="claim boundary"),
        )
        missing_boundaries = tuple(
            boundary
            for boundary in WAVE_FIVE_REQUIRED_CLAIM_BOUNDARIES
            if boundary not in self.claim_boundaries
        )
        if missing_boundaries:
            raise ValueError(
                "WorldTwin bridges must preserve claim boundary: "
                f"{missing_boundaries[0].value}"
            )
        object.__setattr__(self, "notes", _unique_text(self.notes, label="note"))
        object.__setattr__(
            self, "schema_version", _text(self.schema_version, "schema_version")
        )
        if self.externally_reviewed_with_boundaries:
            if self.source_system not in EXTERNAL_WORLDTWIN_REVIEW_SOURCE_SYSTEMS:
                raise ValueError(
                    "Externally reviewed WorldTwin bridges require external source."
                )
            if not self.reviewer_ids:
                raise ValueError(
                    "Externally reviewed WorldTwin bridges require reviewer ids."
                )
            if self.blocks_worldtwin_readiness:
                raise ValueError(
                    "Externally reviewed WorldTwin bridges cannot contain blockers."
                )

    @property
    def covered_assumption_kinds(self) -> tuple[WaveFiveScenarioAssumptionKind, ...]:
        """Return assumption kinds represented in this bridge."""

        kinds: list[WaveFiveScenarioAssumptionKind] = []
        seen: set[WaveFiveScenarioAssumptionKind] = set()
        for assumption in self.assumptions:
            if assumption.assumption_kind not in seen:
                kinds.append(assumption.assumption_kind)
                seen.add(assumption.assumption_kind)
        return tuple(kinds)

    @property
    def missing_required_assumption_kinds(
        self,
    ) -> tuple[WaveFiveScenarioAssumptionKind, ...]:
        """Return required assumption kinds absent from this bridge."""

        covered = set(self.covered_assumption_kinds)
        return tuple(
            kind for kind in REQUIRED_SCENARIO_ASSUMPTION_KINDS if kind not in covered
        )

    @property
    def covered_consequence_kinds(self) -> tuple[WaveFiveConsequenceKind, ...]:
        """Return consequence kinds represented in this bridge."""

        kinds: list[WaveFiveConsequenceKind] = []
        seen: set[WaveFiveConsequenceKind] = set()
        for prediction in self.predictions:
            if prediction.consequence_kind not in seen:
                kinds.append(prediction.consequence_kind)
                seen.add(prediction.consequence_kind)
        return tuple(kinds)

    @property
    def missing_required_consequence_kinds(self) -> tuple[WaveFiveConsequenceKind, ...]:
        """Return required consequence kinds absent from this bridge."""

        covered = set(self.covered_consequence_kinds)
        return tuple(kind for kind in REQUIRED_CONSEQUENCE_KINDS if kind not in covered)

    @property
    def covered_delta_kinds(self) -> tuple[WaveFiveRealityDeltaKind, ...]:
        """Return reality-delta kinds represented in this bridge."""

        kinds: list[WaveFiveRealityDeltaKind] = []
        seen: set[WaveFiveRealityDeltaKind] = set()
        for delta in self.reality_delta_checks:
            if delta.delta_kind not in seen:
                kinds.append(delta.delta_kind)
                seen.add(delta.delta_kind)
        return tuple(kinds)

    @property
    def missing_required_delta_kinds(self) -> tuple[WaveFiveRealityDeltaKind, ...]:
        """Return required reality-delta kinds absent from this bridge."""

        covered = set(self.covered_delta_kinds)
        return tuple(
            kind for kind in REQUIRED_REALITY_DELTA_KINDS if kind not in covered
        )

    @property
    def covered_control_kinds(self) -> tuple[WaveFiveWorldTwinControlKind, ...]:
        """Return WorldTwin control kinds represented in this bridge."""

        kinds: list[WaveFiveWorldTwinControlKind] = []
        seen: set[WaveFiveWorldTwinControlKind] = set()
        for control in self.controls:
            if control.control_kind not in seen:
                kinds.append(control.control_kind)
                seen.add(control.control_kind)
        return tuple(kinds)

    @property
    def missing_required_control_kinds(
        self,
    ) -> tuple[WaveFiveWorldTwinControlKind, ...]:
        """Return required WorldTwin controls absent from this bridge."""

        covered = set(self.covered_control_kinds)
        return tuple(
            kind for kind in REQUIRED_WORLDTWIN_CONTROL_KINDS if kind not in covered
        )

    @property
    def blocking_prediction_ids(self) -> tuple[str, ...]:
        """Return predictions that block scenario readiness."""

        return tuple(
            prediction.prediction_id
            for prediction in self.predictions
            if prediction.blocks_wave_five_progress
        )

    @property
    def blocking_delta_ids(self) -> tuple[str, ...]:
        """Return reality-delta checks that block scenario readiness."""

        return tuple(
            delta.delta_id
            for delta in self.reality_delta_checks
            if delta.blocks_wave_five_progress
        )

    @property
    def blocking_control_ids(self) -> tuple[str, ...]:
        """Return controls that block scenario readiness."""

        return tuple(
            control.control_id
            for control in self.controls
            if control.blocks_wave_five_progress
        )

    @property
    def has_required_assumption_coverage(self) -> bool:
        """Return whether every locked assumption kind is represented."""

        return not self.missing_required_assumption_kinds

    @property
    def has_required_consequence_coverage(self) -> bool:
        """Return whether every locked consequence kind is represented."""

        return not self.missing_required_consequence_kinds

    @property
    def has_required_delta_coverage(self) -> bool:
        """Return whether every locked reality-delta kind is represented."""

        return not self.missing_required_delta_kinds

    @property
    def has_required_control_coverage(self) -> bool:
        """Return whether every locked WorldTwin control kind is represented."""

        return not self.missing_required_control_kinds

    @property
    def preserves_human_authority(self) -> bool:
        """Return whether all predictions preserve human authority."""

        return all(
            prediction.preserves_human_authority for prediction in self.predictions
        )

    @property
    def blocks_worldtwin_readiness(self) -> bool:
        """Return whether any scenario component blocks readiness."""

        return bool(
            self.blocking_prediction_ids
            or self.blocking_delta_ids
            or self.blocking_control_ids
        )

    @property
    def ready_for_external_worldtwin_review(self) -> bool:
        """Return whether bridge can enter external scenario review."""

        return (
            self.bridge_state
            in {
                WaveFiveWorldTwinBridgeState.INTERNAL_SCENARIO_READY,
                WaveFiveWorldTwinBridgeState.READY_FOR_EXTERNAL_SCENARIO_REVIEW,
                WaveFiveWorldTwinBridgeState.UNDER_EXTERNAL_SCENARIO_REVIEW,
            }
            and self.has_required_assumption_coverage
            and self.has_required_consequence_coverage
            and self.has_required_delta_coverage
            and self.has_required_control_coverage
            and not self.blocks_worldtwin_readiness
            and self.preserves_human_authority
            and not self.claims_simulation_as_proof
            and not self.grants_execution_authority
            and not self.claims_agi
        )

    @property
    def externally_reviewed_with_boundaries(self) -> bool:
        """Return whether external scenario review accepted boundaries."""

        return (
            self.bridge_state
            is WaveFiveWorldTwinBridgeState.EXTERNALLY_REVIEWED_WITH_BOUNDARIES
        )

    @property
    def all_evidence_ids(self) -> tuple[str, ...]:
        """Return all evidence ids bound into this bridge."""

        evidence_ids: list[str] = []
        seen: set[str] = set()
        for evidence_id in self._iter_evidence_ids():
            if evidence_id not in seen:
                evidence_ids.append(evidence_id)
                seen.add(evidence_id)
        return tuple(evidence_ids)

    def to_artifact_ref(self) -> WaveFiveArtifactRef:
        """Return this bridge as a Wave 5 ecosystem traceability artifact."""

        decision = WaveFiveArtifactDecision.NEEDS_EXTERNAL_EVIDENCE
        status = WaveFiveValidationStatus.MISSING_EXTERNAL_EVIDENCE
        authority = WaveFiveAuthorityState.HUMAN_REVIEW_REQUIRED
        if self.externally_reviewed_with_boundaries:
            decision = WaveFiveArtifactDecision.EXTERNALLY_REVIEWED
            status = WaveFiveValidationStatus.ACCEPTED_WITH_BOUNDARIES
        elif self.ready_for_external_worldtwin_review:
            decision = WaveFiveArtifactDecision.READY_FOR_INDEPENDENT_REVIEW
            status = WaveFiveValidationStatus.UNDER_INDEPENDENT_REVIEW
        elif self.blocks_worldtwin_readiness:
            decision = WaveFiveArtifactDecision.BLOCKED
            status = WaveFiveValidationStatus.REJECTED
            authority = WaveFiveAuthorityState.BLOCKED
        return WaveFiveArtifactRef(
            artifact_id=self.bridge_id,
            kind=WaveFiveArtifactKind.ECOSYSTEM_TRACEABILITY_MAP,
            capability_area=WaveFiveCapabilityArea.ECOSYSTEM_TRACEABILITY,
            source_system=self.source_system,
            summary=self.title,
            produced_by_engine_id="wave5-worldtwin-scenario-bridge",
            produced_by_agent_role_id="worldtwin-scenario-reviewer",
            evidence_ids=self.all_evidence_ids,
            decision=decision,
            authority_state=authority,
            validation_status=status,
            claim_boundaries=self.claim_boundaries,
        )

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic export payload."""

        return {
            "assumptions": [item.canonical_payload() for item in self.assumptions],
            "bridge_id": self.bridge_id,
            "bridge_state": self.bridge_state.value,
            "claim_boundaries": [boundary.value for boundary in self.claim_boundaries],
            "claims_agi": self.claims_agi,
            "claims_simulation_as_proof": self.claims_simulation_as_proof,
            "controls": [item.canonical_payload() for item in self.controls],
            "grants_execution_authority": self.grants_execution_authority,
            "notes": list(self.notes),
            "predictions": [item.canonical_payload() for item in self.predictions],
            "protocol_ids": list(self.protocol_ids),
            "reality_delta_checks": [
                item.canonical_payload() for item in self.reality_delta_checks
            ],
            "reviewer_ids": list(self.reviewer_ids),
            "schema_version": self.schema_version,
            "source_system": self.source_system.value,
            "title": self.title,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this bridge."""

        return _stable_sha256(self.canonical_payload())

    def _iter_evidence_ids(self) -> Iterable[str]:
        """Yield evidence ids in deterministic bridge traversal order."""

        for assumption in self.assumptions:
            yield from assumption.evidence_ids
        for prediction in self.predictions:
            yield from prediction.evidence_ids
        for delta in self.reality_delta_checks:
            yield from delta.evidence_ids
        for control in self.controls:
            yield from control.evidence_ids

    @staticmethod
    def _validate_prediction_assumptions(
        assumption_ids: set[str],
        predictions: tuple[WaveFiveConsequencePrediction, ...],
    ) -> None:
        """Validate that predictions reference bundled assumptions."""

        for prediction in predictions:
            for assumption_id in prediction.assumption_ids:
                if assumption_id not in assumption_ids:
                    raise ValueError(
                        "WorldTwin predictions must reference bundled assumptions: "
                        f"{assumption_id}"
                    )

    @staticmethod
    def _validate_delta_references(
        prediction_ids: set[str],
        deltas: tuple[WaveFiveRealityDeltaCheck, ...],
    ) -> None:
        """Validate that reality-delta checks reference bundled predictions."""

        for delta in deltas:
            if delta.prediction_id not in prediction_ids:
                raise ValueError(
                    "Reality-delta checks must reference bundled predictions: "
                    f"{delta.prediction_id}"
                )


def required_scenario_assumption_kinds() -> tuple[
    WaveFiveScenarioAssumptionKind, ...
]:
    """Return locked assumption kinds required for WorldTwin review."""

    return REQUIRED_SCENARIO_ASSUMPTION_KINDS


def required_consequence_kinds() -> tuple[WaveFiveConsequenceKind, ...]:
    """Return locked consequence kinds required for WorldTwin review."""

    return REQUIRED_CONSEQUENCE_KINDS


def required_reality_delta_kinds() -> tuple[WaveFiveRealityDeltaKind, ...]:
    """Return locked reality-delta kinds required for WorldTwin review."""

    return REQUIRED_REALITY_DELTA_KINDS


def required_worldtwin_control_kinds() -> tuple[WaveFiveWorldTwinControlKind, ...]:
    """Return locked controls required for WorldTwin bridge review."""

    return REQUIRED_WORLDTWIN_CONTROL_KINDS


def safe_prediction_dispositions() -> tuple[WaveFivePredictionDisposition, ...]:
    """Return prediction dispositions that do not block review."""

    return SAFE_PREDICTION_DISPOSITIONS


def blocking_prediction_dispositions() -> tuple[WaveFivePredictionDisposition, ...]:
    """Return prediction dispositions that block scenario readiness."""

    return BLOCKING_PREDICTION_DISPOSITIONS


def external_worldtwin_review_source_systems() -> tuple[WaveFiveSourceSystem, ...]:
    """Return source systems allowed to assert external scenario review."""

    return EXTERNAL_WORLDTWIN_REVIEW_SOURCE_SYSTEMS


def _text(value: str, label: str) -> str:
    """Return stripped text or raise when empty."""

    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{label} must not be empty.")
    return normalized


def _unique_text(values: Iterable[str], *, label: str) -> tuple[str, ...]:
    """Normalize text values while rejecting blanks and duplicates."""

    normalized: list[str] = []
    seen: set[str] = set()
    for value in values:
        item = _text(value, label)
        if item in seen:
            raise ValueError(f"Duplicate {label} detected: {item}")
        normalized.append(item)
        seen.add(item)
    return tuple(normalized)


def _unique_enum(values: Iterable[E], *, label: str) -> tuple[E, ...]:
    """Return enum values while rejecting duplicates."""

    normalized: list[E] = []
    seen: set[E] = set()
    for value in values:
        if value in seen:
            raise ValueError(f"Duplicate {label} detected: {value.value}")
        normalized.append(value)
        seen.add(value)
    return tuple(normalized)


def _unique_values(values: Iterable[T], *, label: str) -> set[T]:
    """Return unique values while rejecting duplicates."""

    seen: set[T] = set()
    for value in values:
        if value in seen:
            raise ValueError(f"Duplicate {label} detected: {value}")
        seen.add(value)
    return seen


def _stable_sha256(payload: Mapping[str, Any]) -> str:
    """Return deterministic SHA-256 over a canonical JSON payload."""

    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return hashlib.sha256(encoded).hexdigest()
