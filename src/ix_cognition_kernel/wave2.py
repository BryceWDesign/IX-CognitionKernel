"""Wave 2 readiness snapshot for IX-CognitionKernel.

Wave 2 is only earned when the repository can demonstrate evidence-driven
belief updates, belief history, prediction comparison, causal revision, outcome
learning, memory quarantine, validated skills, and integrated cycle readiness.
This module does not execute actions, persist memory, or claim AGI. It records
whether the Wave 2 learning artifacts back the maturity claim.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from ix_cognition_kernel.cycle import LearnableCognitionCycleResult
from ix_cognition_kernel.doctrine import (
    WaveDefinition,
    allows_agi_claim,
    wave_by_number,
)
from ix_cognition_kernel.outcome import OutcomeLearningStatus

WAVE_TWO_REQUIRED_VALIDATION_ARTIFACT_IDS: tuple[str, ...] = (
    "evidence-event-ledger",
    "belief-update-engine",
    "contradiction-detection",
    "staleness-supersession-handling",
    "belief-history",
    "causal-predictions",
    "prediction-observation-comparison",
    "causal-revision-engine",
    "outcome-learning-records",
    "memory-quarantine-engine",
    "validated-skill-records",
    "integrated-learnable-cognition-cycle",
    "adversarial-failure-scenarios",
)


@dataclass(frozen=True, slots=True)
class WaveTwoReadinessSnapshot:
    """Fail-closed readiness snapshot for the Wave 2 maturity claim."""

    project_name: str
    maturity_wave: WaveDefinition
    learning_cycles: tuple[LearnableCognitionCycleResult, ...]
    validation_artifact_ids: tuple[str, ...]
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        """Validate Wave 2 snapshot identity and minimum evidence structure."""

        if self.project_name != "IX-CognitionKernel":
            raise ValueError("Wave 2 snapshots must use IX-CognitionKernel.")
        if self.maturity_wave.number != 2:
            raise ValueError("Wave 2 readiness snapshots must target Wave 2.")
        if not self.learning_cycles:
            raise ValueError("Wave 2 readiness snapshots require learning cycles.")
        _unique_ids(self.validation_artifact_ids, label="validation_artifact_id")
        missing = tuple(
            artifact_id
            for artifact_id in WAVE_TWO_REQUIRED_VALIDATION_ARTIFACT_IDS
            if artifact_id not in self.validation_artifact_ids
        )
        if missing:
            raise ValueError(
                "Wave 2 readiness snapshots require validation artifact coverage: "
                f"{missing[0]}"
            )

    @property
    def wave_label(self) -> str:
        """Return the Wave 2 maturity label."""

        return self.maturity_wave.label

    @property
    def belief_revision_count(self) -> int:
        """Return the number of belief revisions across learning cycles."""

        return sum(
            len(cycle.belief_history.all_revisions) for cycle in self.learning_cycles
        )

    @property
    def causal_revision_count(self) -> int:
        """Return the number of causal revisions across learning cycles."""

        return sum(
            len(cycle.causal_revision_result.revisions)
            for cycle in self.learning_cycles
        )

    @property
    def prediction_comparison_count(self) -> int:
        """Return prediction comparison count across learning cycles."""

        return sum(
            len(cycle.prediction_comparison_ledger.comparisons)
            for cycle in self.learning_cycles
        )

    @property
    def accepted_outcome_count(self) -> int:
        """Return accepted outcome-learning record count."""

        return sum(
            1
            for cycle in self.learning_cycles
            if cycle.outcome_record.status is OutcomeLearningStatus.ACCEPTED
        )

    @property
    def accepted_memory_count(self) -> int:
        """Return accepted memory candidate count across cycles."""

        return sum(
            len(cycle.memory_ledger.accepted_candidates)
            for cycle in self.learning_cycles
        )

    @property
    def validated_skill_count(self) -> int:
        """Return validated skill candidate count across cycles."""

        return sum(
            len(cycle.skill_ledger.validated_candidates)
            for cycle in self.learning_cycles
        )

    @property
    def permits_agi_claim(self) -> bool:
        """Return whether this Wave 2 snapshot permits an AGI claim."""

        return allows_agi_claim(
            self.maturity_wave.number,
            overwhelming_evidence=False,
        )

    @property
    def readiness_gaps(self) -> tuple[str, ...]:
        """Return fail-closed gaps preventing Wave 2 readiness."""

        gaps: list[str] = []
        incomplete_cycles = tuple(
            cycle
            for cycle in self.learning_cycles
            if not cycle.is_complete_learning_cycle
        )
        if incomplete_cycles:
            gaps.append("learning-cycles contain incomplete readiness results")
        if self.belief_revision_count == 0:
            gaps.append("belief-history has no evidence-driven revisions")
        if self.prediction_comparison_count == 0:
            gaps.append("prediction-comparison-ledger has no comparisons")
        if self.causal_revision_count == 0:
            gaps.append("causal-revision-result has no revisions")
        if self.accepted_outcome_count == 0:
            gaps.append("outcome-learning has no accepted records")
        if self.accepted_memory_count == 0:
            gaps.append("memory-quarantine has no accepted candidates")
        if self.validated_skill_count == 0:
            gaps.append("skill-validation has no validated skills")
        if self.permits_agi_claim:
            gaps.append("maturity-state improperly permits AGI claim")
        return tuple(gaps)

    @property
    def is_wave_two_ready(self) -> bool:
        """Return whether the snapshot earns the Wave 2 maturity claim."""

        return not self.readiness_gaps


def wave_two_readiness_snapshot(
    *,
    learning_cycles: tuple[LearnableCognitionCycleResult, ...],
    validation_artifact_ids: tuple[
        str, ...
    ] = WAVE_TWO_REQUIRED_VALIDATION_ARTIFACT_IDS,
    notes: tuple[str, ...] = (),
) -> WaveTwoReadinessSnapshot:
    """Create a Wave 2 readiness snapshot from integrated learning cycles."""

    return WaveTwoReadinessSnapshot(
        project_name="IX-CognitionKernel",
        maturity_wave=wave_by_number(2),
        learning_cycles=learning_cycles,
        validation_artifact_ids=validation_artifact_ids,
        notes=notes,
    )


def _unique_ids(values: Iterable[str], *, label: str) -> set[str]:
    """Return unique ids while rejecting duplicates and blank values."""

    seen: set[str] = set()
    for value in values:
        if not value.strip():
            raise ValueError(f"{label} values cannot be empty.")
        if value in seen:
            raise ValueError(f"Duplicate {label} detected: {value}")
        seen.add(value)
    return seen
