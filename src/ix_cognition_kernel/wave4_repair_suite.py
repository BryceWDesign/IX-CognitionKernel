"""Wave 4 failure-repair suite records.

A single repair cycle is useful, but Wave 4 needs stronger evidence that the
system can repeatedly observe failure, apply bounded repairs, re-run the same
controlled task, and catch invalid repair behavior. This module aggregates
multiple cycles with negative controls and coverage checks while preserving the
IX-CognitionKernel boundary: the suite is review evidence only, never automatic
execution authority, never an AGI claim, and never independent validation.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, TypeVar

from ix_cognition_kernel.wave4_contracts import (
    WaveFourArtifactBundle,
    WaveFourArtifactKind,
    WaveFourCapabilityArea,
    WaveFourEvidenceLink,
    WaveFourEvidenceRelation,
    WaveFourSourceSystem,
)
from ix_cognition_kernel.wave4_failure_repair import (
    WaveFourFailureMode,
    WaveFourFailureRepairCycle,
    WaveFourRepairStatus,
)
from ix_cognition_kernel.wave4_trials import (
    WaveFourTrialProtocol,
    WaveFourTrialTaskKind,
)

T = TypeVar("T")

WAVE_FOUR_REPAIR_NEGATIVE_CONTROL_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave4-repair-negative-control-v1"
)
WAVE_FOUR_REPAIR_SUITE_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave4-repair-suite-v1"
)


class WaveFourRepairNegativeControlMode(StrEnum):
    """Invalid repair behaviors the suite must detect."""

    WEAKENED_EVIDENCE_GATE = "weakened-evidence-gate"
    SUPPRESSED_UNCERTAINTY = "suppressed-uncertainty"
    HIDDEN_INITIAL_FAILURE = "hidden-initial-failure"
    UNSAFE_AUTHORITY_GRANT = "unsafe-authority-grant"
    MISSING_ROLLBACK = "missing-rollback"
    SCORE_ONLY_OPTIMIZATION = "score-only-optimization"


@dataclass(frozen=True, slots=True)
class WaveFourRepairNegativeControl:
    """A negative control proving invalid repair behavior is caught."""

    control_id: str
    cycle_id: str
    mode: WaveFourRepairNegativeControlMode
    injected_invalid_behavior: str
    expected_detection: str
    evidence_ids: tuple[str, ...]
    detected: bool
    repair_guidance: str
    source_system: WaveFourSourceSystem = WaveFourSourceSystem.LOCAL_TEST_SUITE
    schema_version: str = WAVE_FOUR_REPAIR_NEGATIVE_CONTROL_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate negative-control identity, evidence, and guidance."""

        object.__setattr__(self, "control_id", _text(self.control_id, "control_id"))
        object.__setattr__(self, "cycle_id", _text(self.cycle_id, "cycle_id"))
        object.__setattr__(
            self,
            "injected_invalid_behavior",
            _text(self.injected_invalid_behavior, "injected_invalid_behavior"),
        )
        object.__setattr__(
            self,
            "expected_detection",
            _text(self.expected_detection, "expected_detection"),
        )
        object.__setattr__(
            self,
            "evidence_ids",
            _unique_text(self.evidence_ids, label="negative-control evidence_id"),
        )
        if not self.evidence_ids:
            raise ValueError("Wave 4 repair negative controls require evidence ids.")
        object.__setattr__(
            self,
            "repair_guidance",
            self.repair_guidance.strip(),
        )
        object.__setattr__(
            self, "schema_version", _text(self.schema_version, "schema_version")
        )
        if self.detected and not self.repair_guidance:
            raise ValueError(
                "Detected Wave 4 repair negative controls require repair guidance."
            )

    @property
    def control_key(self) -> str:
        """Return deterministic uniqueness key for this negative control."""

        return self.control_id

    @property
    def resolved(self) -> bool:
        """Return whether invalid behavior was detected and given guidance."""

        return self.detected and bool(self.repair_guidance)

    @property
    def readiness_gap(self) -> str:
        """Return the readiness gap represented by this control, if any."""

        if self.resolved:
            return ""
        if not self.detected:
            return f"{self.control_id} was not detected by repair review"
        return f"{self.control_id} lacks repair guidance"

    def canonical_payload(self) -> dict[str, Any]:
        """Return a deterministic payload for hashing and export."""

        return {
            "control_id": self.control_id,
            "cycle_id": self.cycle_id,
            "detected": self.detected,
            "evidence_ids": list(self.evidence_ids),
            "expected_detection": self.expected_detection,
            "injected_invalid_behavior": self.injected_invalid_behavior,
            "mode": self.mode.value,
            "readiness_gap": self.readiness_gap,
            "repair_guidance": self.repair_guidance,
            "resolved": self.resolved,
            "schema_version": self.schema_version,
            "source_system": self.source_system.value,
        }

    def fingerprint(self) -> str:
        """Return a deterministic SHA-256 fingerprint for this control."""

        return _stable_sha256(self.canonical_payload())


@dataclass(frozen=True, slots=True)
class WaveFourFailureRepairSuite:
    """Aggregate Wave 4 failure-repair cycles with negative controls."""

    suite_id: str
    cycles: tuple[WaveFourFailureRepairCycle, ...]
    negative_controls: tuple[WaveFourRepairNegativeControl, ...]
    required_failure_modes: tuple[WaveFourFailureMode, ...]
    min_ready_cycles: int = 1
    min_average_improvement_delta: float = 0.10
    reviewer_role_id: str = "failure-repair-suite-reviewer"
    generated_by_engine_id: str = "wave4-failure-repair-suite-engine"
    notes: tuple[str, ...] = ()
    permits_automatic_execution: bool = False
    claims_agi: bool = False
    independently_validated: bool = False
    schema_version: str = WAVE_FOUR_REPAIR_SUITE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate suite identity, references, and anti-overclaim boundaries."""

        object.__setattr__(self, "suite_id", _text(self.suite_id, "suite_id"))
        if not self.cycles:
            raise ValueError("Wave 4 repair suites require repair cycles.")
        sorted_cycles = tuple(sorted(self.cycles, key=lambda item: item.cycle_id))
        cycle_ids = _unique_items(
            (cycle.cycle_id for cycle in sorted_cycles), label="cycle_id"
        )
        object.__setattr__(self, "cycles", sorted_cycles)
        sorted_controls = tuple(
            sorted(self.negative_controls, key=lambda item: item.control_key)
        )
        _unique_items(
            (control.control_id for control in sorted_controls),
            label="negative control_id",
        )
        for control in sorted_controls:
            if control.cycle_id not in cycle_ids:
                raise ValueError(
                    "Wave 4 repair negative controls must reference bundled "
                    f"cycles: {control.cycle_id}"
                )
        object.__setattr__(self, "negative_controls", sorted_controls)
        object.__setattr__(
            self,
            "required_failure_modes",
            _unique_items(self.required_failure_modes, label="required failure mode"),
        )
        if not self.required_failure_modes:
            raise ValueError("Wave 4 repair suites require failure-mode coverage.")
        if self.min_ready_cycles < 1:
            raise ValueError("Wave 4 repair suites require a positive ready count.")
        if not 0.0 <= self.min_average_improvement_delta <= 1.0:
            raise ValueError("min_average_improvement_delta must be 0.0..1.0.")
        object.__setattr__(
            self, "reviewer_role_id", _text(self.reviewer_role_id, "reviewer_role_id")
        )
        object.__setattr__(
            self,
            "generated_by_engine_id",
            _text(self.generated_by_engine_id, "generated_by_engine_id"),
        )
        object.__setattr__(
            self, "notes", _unique_text(self.notes, label="repair-suite note")
        )
        object.__setattr__(
            self, "schema_version", _text(self.schema_version, "schema_version")
        )
        if self.permits_automatic_execution:
            raise ValueError("Wave 4 repair suites cannot permit execution.")
        if self.claims_agi:
            raise ValueError("Wave 4 repair suites cannot claim AGI.")
        if self.independently_validated:
            raise ValueError(
                "Wave 4 repair suites cannot claim independent validation."
            )

    @property
    def cycle_ids(self) -> tuple[str, ...]:
        """Return cycle ids in deterministic order."""

        return tuple(cycle.cycle_id for cycle in self.cycles)

    @property
    def ready_cycle_ids(self) -> tuple[str, ...]:
        """Return cycles ready for controlled review."""

        return tuple(
            cycle.cycle_id
            for cycle in self.cycles
            if cycle.status is WaveFourRepairStatus.READY_FOR_CONTROLLED_REVIEW
        )

    @property
    def evidence_gap_cycle_ids(self) -> tuple[str, ...]:
        """Return cycles that need more evidence."""

        return tuple(
            cycle.cycle_id
            for cycle in self.cycles
            if cycle.status is WaveFourRepairStatus.NEEDS_EVIDENCE
        )

    @property
    def repair_cycle_ids(self) -> tuple[str, ...]:
        """Return cycles that need additional repair."""

        return tuple(
            cycle.cycle_id
            for cycle in self.cycles
            if cycle.status is WaveFourRepairStatus.NEEDS_REPAIR
        )

    @property
    def blocked_cycle_ids(self) -> tuple[str, ...]:
        """Return cycles that block suite progress."""

        return tuple(
            cycle.cycle_id
            for cycle in self.cycles
            if cycle.status is WaveFourRepairStatus.BLOCKED
        )

    @property
    def covered_failure_modes(self) -> tuple[WaveFourFailureMode, ...]:
        """Return sorted failure modes covered by initial failed observations."""

        return tuple(
            sorted(
                {
                    mode
                    for cycle in self.cycles
                    for mode in cycle.initial_observation.failure_modes
                },
                key=lambda mode: mode.value,
            )
        )

    @property
    def missing_required_failure_modes(self) -> tuple[WaveFourFailureMode, ...]:
        """Return required failure modes not covered by repair cycles."""

        covered = set(self.covered_failure_modes)
        return tuple(
            mode for mode in self.required_failure_modes if mode not in covered
        )

    @property
    def average_improvement_delta(self) -> float:
        """Return average improvement delta across all cycles."""

        if not self.cycles:
            return 0.0
        return round(
            sum(cycle.improvement_delta for cycle in self.cycles) / len(self.cycles),
            6,
        )

    @property
    def scenario_ids(self) -> tuple[str, ...]:
        """Return sorted WorldTwin scenario ids represented by the suite."""

        return tuple(
            sorted({item for cycle in self.cycles for item in cycle.scenario_ids})
        )

    @property
    def blackfox_receipt_ids(self) -> tuple[str, ...]:
        """Return sorted BlackFox receipt ids represented by the suite."""

        return tuple(
            sorted(
                {
                    item
                    for cycle in self.cycles
                    for item in cycle.blackfox_receipt_ids
                }
            )
        )

    @property
    def all_evidence_ids(self) -> tuple[str, ...]:
        """Return sorted evidence ids from cycles and negative controls."""

        evidence_ids: set[str] = set()
        for cycle in self.cycles:
            evidence_ids.update(cycle.all_evidence_ids)
        for control in self.negative_controls:
            evidence_ids.update(control.evidence_ids)
        return tuple(sorted(evidence_ids))

    @property
    def resolved_negative_control_ids(self) -> tuple[str, ...]:
        """Return negative controls that were detected with guidance."""

        return tuple(
            control.control_id for control in self.negative_controls if control.resolved
        )

    @property
    def unresolved_negative_control_ids(self) -> tuple[str, ...]:
        """Return negative controls that still need repair."""

        return tuple(
            control.control_id
            for control in self.negative_controls
            if not control.resolved
        )

    @property
    def readiness_gaps(self) -> tuple[str, ...]:
        """Return fail-closed gaps preventing controlled review."""

        gaps: list[str] = []
        if len(self.ready_cycle_ids) < self.min_ready_cycles:
            gaps.append(
                "ready repair cycles below minimum: "
                f"{len(self.ready_cycle_ids)}/{self.min_ready_cycles}"
            )
        if self.missing_required_failure_modes:
            missing = ", ".join(
                mode.value for mode in self.missing_required_failure_modes
            )
            gaps.append(f"missing required failure modes: {missing}")
        if self.average_improvement_delta < self.min_average_improvement_delta:
            gaps.append(
                "average repair improvement below minimum: "
                f"{self.average_improvement_delta:.3f}/"
                f"{self.min_average_improvement_delta:.3f}"
            )
        for cycle in self.cycles:
            for gap in cycle.readiness_gaps:
                gaps.append(f"{cycle.cycle_id}: {gap}")
            for gap in cycle.blocking_gaps:
                gaps.append(gap)
        for control in self.negative_controls:
            if control.readiness_gap:
                gaps.append(control.readiness_gap)
        return tuple(gaps)

    @property
    def status(self) -> WaveFourRepairStatus:
        """Return aggregate fail-closed repair-suite status."""

        if self.blocked_cycle_ids:
            return WaveFourRepairStatus.BLOCKED
        if self.repair_cycle_ids or self.unresolved_negative_control_ids:
            return WaveFourRepairStatus.NEEDS_REPAIR
        if self.evidence_gap_cycle_ids or self.readiness_gaps:
            return WaveFourRepairStatus.NEEDS_EVIDENCE
        return WaveFourRepairStatus.READY_FOR_CONTROLLED_REVIEW

    @property
    def ready_for_controlled_review(self) -> bool:
        """Return whether the suite may enter controlled human review."""

        return self.status is WaveFourRepairStatus.READY_FOR_CONTROLLED_REVIEW

    @property
    def review_summary(self) -> str:
        """Return a concise repair-suite review summary."""

        return (
            f"{self.suite_id}: {len(self.cycles)} repair cycles; "
            f"{len(self.negative_controls)} negative controls; "
            f"avg delta {self.average_improvement_delta:.3f}; "
            f"{self.status.value}; human review required; no AGI claim."
        )

    def cycle_by_id(self, cycle_id: str) -> WaveFourFailureRepairCycle:
        """Return one cycle by id."""

        for cycle in self.cycles:
            if cycle.cycle_id == cycle_id:
                return cycle
        raise ValueError(f"Unknown Wave 4 repair cycle_id: {cycle_id}")

    def negative_controls_for_cycle(
        self, cycle_id: str
    ) -> tuple[WaveFourRepairNegativeControl, ...]:
        """Return negative controls attached to one cycle."""

        return tuple(
            control
            for control in self.negative_controls
            if control.cycle_id == cycle_id
        )

    def to_trial_protocol(self) -> WaveFourTrialProtocol:
        """Convert repair cycles into a controlled trial protocol."""

        return WaveFourTrialProtocol(
            protocol_id=f"failure-repair-suite:{self.suite_id}",
            tasks=tuple(cycle.to_controlled_task() for cycle in self.cycles),
            required_task_kinds=(WaveFourTrialTaskKind.FAILURE_REPAIR_PROBE,),
            notes=(self.review_summary, *self.notes),
        )

    def to_artifact_bundle(self) -> WaveFourArtifactBundle:
        """Convert repair cycles and controls into shared Wave 4 artifacts."""

        artifacts = tuple(cycle.to_artifact_ref() for cycle in self.cycles)
        evidence_links = tuple(
            link
            for cycle in self.cycles
            for link in self._evidence_links_for_cycle(cycle)
        )
        return WaveFourArtifactBundle(
            bundle_id=f"wave4-failure-repair-suite:{self.suite_id}",
            artifacts=artifacts,
            evidence_links=evidence_links,
            required_kinds=(WaveFourArtifactKind.FAILURE_REPAIR_CYCLE,),
            required_capability_areas=(
                WaveFourCapabilityArea.SELF_IMPROVEMENT_AFTER_FAILURE,
            ),
            notes=(self.review_summary, *self.notes),
        )

    def canonical_payload(self) -> dict[str, Any]:
        """Return a deterministic payload for hashing and export."""

        return {
            "all_evidence_ids": list(self.all_evidence_ids),
            "average_improvement_delta": self.average_improvement_delta,
            "blackfox_receipt_ids": list(self.blackfox_receipt_ids),
            "blocked_cycle_ids": list(self.blocked_cycle_ids),
            "claims_agi": self.claims_agi,
            "covered_failure_modes": [
                mode.value for mode in self.covered_failure_modes
            ],
            "cycles": [cycle.canonical_payload() for cycle in self.cycles],
            "evidence_gap_cycle_ids": list(self.evidence_gap_cycle_ids),
            "generated_by_engine_id": self.generated_by_engine_id,
            "independently_validated": self.independently_validated,
            "min_average_improvement_delta": self.min_average_improvement_delta,
            "min_ready_cycles": self.min_ready_cycles,
            "missing_required_failure_modes": [
                mode.value for mode in self.missing_required_failure_modes
            ],
            "negative_controls": [
                control.canonical_payload() for control in self.negative_controls
            ],
            "notes": list(self.notes),
            "permits_automatic_execution": self.permits_automatic_execution,
            "readiness_gaps": list(self.readiness_gaps),
            "ready_cycle_ids": list(self.ready_cycle_ids),
            "repair_cycle_ids": list(self.repair_cycle_ids),
            "required_failure_modes": [
                mode.value for mode in self.required_failure_modes
            ],
            "resolved_negative_control_ids": list(self.resolved_negative_control_ids),
            "review_summary": self.review_summary,
            "reviewer_role_id": self.reviewer_role_id,
            "scenario_ids": list(self.scenario_ids),
            "schema_version": self.schema_version,
            "status": self.status.value,
            "suite_id": self.suite_id,
            "unresolved_negative_control_ids": list(
                self.unresolved_negative_control_ids
            ),
        }

    def fingerprint(self) -> str:
        """Return a deterministic SHA-256 fingerprint for this suite."""

        return _stable_sha256(self.canonical_payload())

    def _evidence_links_for_cycle(
        self, cycle: WaveFourFailureRepairCycle
    ) -> tuple[WaveFourEvidenceLink, ...]:
        """Return evidence links for a cycle and attached negative controls."""

        links: list[WaveFourEvidenceLink] = list(cycle.evidence_links())
        for control in self.negative_controls_for_cycle(cycle.cycle_id):
            relation = WaveFourEvidenceRelation.TESTS
            if not control.resolved:
                relation = WaveFourEvidenceRelation.BLOCKS
            for evidence_id in control.evidence_ids:
                links.append(
                    WaveFourEvidenceLink(
                        evidence_id=evidence_id,
                        artifact_id=cycle.artifact_id,
                        relation=relation,
                        summary=(
                            "Negative-control evidence for Wave 4 repair "
                            f"control {control.control_id}."
                        ),
                        source_system=control.source_system,
                    )
                )
        return tuple(sorted(links, key=lambda link: link.link_key))


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
        stripped = _text(value, label)
        if stripped in seen:
            raise ValueError(f"Duplicate {label} detected: {stripped}")
        normalized.append(stripped)
        seen.add(stripped)
    return tuple(normalized)


def _unique_items(values: Iterable[T], *, label: str) -> tuple[T, ...]:
    """Return tuple of unique items while rejecting duplicates."""

    normalized: list[T] = []
    seen: set[T] = set()
    for value in values:
        if value in seen:
            raise ValueError(f"Duplicate {label} detected: {value}")
        normalized.append(value)
        seen.add(value)
    return tuple(normalized)


def _stable_sha256(payload: Mapping[str, Any]) -> str:
    """Return deterministic SHA-256 over a canonical JSON payload."""

    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
