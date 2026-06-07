"""Wave 6 readiness gate for measured system-level cognition.

This module deliberately stays small: it joins the Wave 6 contract bundle and
master-loop trace without creating a messy glue layer. The gate fails closed
until the loop is ordered, evidence-bound, contract-covered, donor-traceable,
falsification-aware, human-reviewable, and able to point to the core proof
signal: measured reality changed future reasoning.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from ix_cognition_kernel.wave6_contracts import (
    WaveSixArtifactKind,
    WaveSixContractBundle,
    WaveSixLoopStage,
    WaveSixSourceSystem,
)
from ix_cognition_kernel.wave6_master_loop import (
    WaveSixLoopReadiness,
    WaveSixMasterLoopTrace,
)

WAVE_SIX_READINESS_SCHEMA_VERSION = "ix-cognition-kernel-wave6-readiness-v1"


class WaveSixReadinessStatus(StrEnum):
    """Fail-closed Wave 6 readiness states."""

    BLOCKED = "blocked"
    NOT_READY = "not-ready"
    READY_FOR_MEASURED_COGNITION_REVIEW = "ready-for-measured-cognition-review"


class WaveSixReadinessBlocker(StrEnum):
    """Concrete reasons a Wave 6 package cannot advance."""

    MASTER_LOOP_NOT_REVIEW_READY = "master-loop-not-review-ready"
    CONTRACT_COVERAGE_INCOMPLETE = "contract-coverage-incomplete"
    DONOR_TRACEABILITY_INCOMPLETE = "donor-traceability-incomplete"
    REALITY_CORRECTED_REASONING_MISSING = "reality-corrected-reasoning-missing"
    FALSIFICATION_STAGE_MISSING = "falsification-stage-missing"
    FALSIFICATION_ARTIFACT_MISSING = "falsification-artifact-missing"
    HUMAN_REVIEW_STAGE_MISSING = "human-review-stage-missing"
    HUMAN_REVIEW_ARTIFACT_MISSING = "human-review-artifact-missing"
    BLOCKED_CONTRACT_ARTIFACT = "blocked-contract-artifact"


@dataclass(frozen=True, slots=True)
class WaveSixReadinessAssessment:
    """Assessment joining a clean master loop to Wave 6 contract coverage."""

    assessment_id: str
    trace: WaveSixMasterLoopTrace
    contract_bundle: WaveSixContractBundle
    require_all_donor_sources: bool = True
    reviewer_role: str = "human-reviewer"
    notes: tuple[str, ...] = ()
    schema_version: str = WAVE_SIX_READINESS_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Normalize identity and reviewer metadata."""

        object.__setattr__(
            self,
            "assessment_id",
            _require_non_empty(self.assessment_id, "assessment_id"),
        )
        object.__setattr__(
            self,
            "reviewer_role",
            _require_non_empty(self.reviewer_role, "reviewer_role"),
        )
        object.__setattr__(
            self,
            "notes",
            _normalize_unique_text_tuple(self.notes, label="assessment note"),
        )
        object.__setattr__(
            self,
            "schema_version",
            _require_non_empty(self.schema_version, "schema_version"),
        )

    @property
    def trace_readiness(self) -> WaveSixLoopReadiness:
        """Return the readiness state reported by the master-loop trace."""

        return self.trace.readiness

    @property
    def missing_contract_loop_stages(self) -> tuple[WaveSixLoopStage, ...]:
        """Return contract loop-stage gaps."""

        return self.contract_bundle.missing_loop_stages

    @property
    def missing_donor_source_systems(self) -> tuple[WaveSixSourceSystem, ...]:
        """Return donor source gaps when donor traceability is required."""

        if not self.require_all_donor_sources:
            return ()
        return self.contract_bundle.missing_donor_source_systems

    @property
    def reality_corrected_reasoning_step_ids(self) -> tuple[str, ...]:
        """Return proof steps where measured reality changed future reasoning."""

        return self.trace.reality_corrected_reasoning_step_ids

    @property
    def has_reality_corrected_reasoning_proof(self) -> bool:
        """Return whether the core Wave 6 proof target is represented."""

        return bool(self.reality_corrected_reasoning_step_ids)

    @property
    def has_falsification_stage(self) -> bool:
        """Return whether the master loop includes a falsification stage."""

        return self.trace.step_for_stage(WaveSixLoopStage.FALSIFICATION) is not None

    @property
    def has_human_review_stage(self) -> bool:
        """Return whether the master loop includes a human-review stage."""

        return self.trace.step_for_stage(WaveSixLoopStage.HUMAN_REVIEW) is not None

    @property
    def has_falsification_artifact(self) -> bool:
        """Return whether contract coverage includes a falsification artifact."""

        return WaveSixArtifactKind.FALSIFICATION_RECORD not in (
            self.contract_bundle.missing_artifact_kinds
        )

    @property
    def has_human_review_artifact(self) -> bool:
        """Return whether contract coverage includes a human-review artifact."""

        return WaveSixArtifactKind.HUMAN_REVIEW_DOCKET not in (
            self.contract_bundle.missing_artifact_kinds
        )

    @property
    def blockers(self) -> tuple[WaveSixReadinessBlocker, ...]:
        """Return deterministic blockers that prevent Wave 6 review."""

        blockers: list[WaveSixReadinessBlocker] = []
        if self.trace_readiness is not WaveSixLoopReadiness.READY_FOR_HUMAN_REVIEW:
            blockers.append(WaveSixReadinessBlocker.MASTER_LOOP_NOT_REVIEW_READY)
        if self.contract_bundle.blocked_artifact_ids:
            blockers.append(WaveSixReadinessBlocker.BLOCKED_CONTRACT_ARTIFACT)
        if not self.contract_bundle.has_required_contract_coverage:
            blockers.append(WaveSixReadinessBlocker.CONTRACT_COVERAGE_INCOMPLETE)
        if self.missing_donor_source_systems:
            blockers.append(WaveSixReadinessBlocker.DONOR_TRACEABILITY_INCOMPLETE)
        if not self.has_reality_corrected_reasoning_proof:
            blockers.append(
                WaveSixReadinessBlocker.REALITY_CORRECTED_REASONING_MISSING
            )
        if not self.has_falsification_stage:
            blockers.append(WaveSixReadinessBlocker.FALSIFICATION_STAGE_MISSING)
        if not self.has_falsification_artifact:
            blockers.append(WaveSixReadinessBlocker.FALSIFICATION_ARTIFACT_MISSING)
        if not self.has_human_review_stage:
            blockers.append(WaveSixReadinessBlocker.HUMAN_REVIEW_STAGE_MISSING)
        if not self.has_human_review_artifact:
            blockers.append(WaveSixReadinessBlocker.HUMAN_REVIEW_ARTIFACT_MISSING)
        return tuple(blockers)

    @property
    def status(self) -> WaveSixReadinessStatus:
        """Return fail-closed readiness status."""

        if (
            self.trace_readiness is WaveSixLoopReadiness.BLOCKED
            or self.contract_bundle.blocked_artifact_ids
        ):
            return WaveSixReadinessStatus.BLOCKED
        if self.blockers:
            return WaveSixReadinessStatus.NOT_READY
        return WaveSixReadinessStatus.READY_FOR_MEASURED_COGNITION_REVIEW

    @property
    def ready_for_measured_cognition_review(self) -> bool:
        """Return whether Wave 6 may enter measured-cognition review."""

        return (
            self.status
            is WaveSixReadinessStatus.READY_FOR_MEASURED_COGNITION_REVIEW
        )

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic payload for review and hashing."""

        return {
            "assessment_id": self.assessment_id,
            "blockers": [blocker.value for blocker in self.blockers],
            "contract_bundle_fingerprint": self.contract_bundle.fingerprint(),
            "missing_donor_source_systems": [
                source.value for source in self.missing_donor_source_systems
            ],
            "notes": list(self.notes),
            "reality_corrected_reasoning_step_ids": list(
                self.reality_corrected_reasoning_step_ids
            ),
            "require_all_donor_sources": self.require_all_donor_sources,
            "reviewer_role": self.reviewer_role,
            "schema_version": self.schema_version,
            "status": self.status.value,
            "trace_fingerprint": self.trace.fingerprint(),
            "trace_readiness": self.trace_readiness.value,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this assessment."""

        return _stable_sha256(self.canonical_payload())


def build_wave_six_readiness_assessment(
    *,
    assessment_id: str,
    trace: WaveSixMasterLoopTrace,
    contract_bundle: WaveSixContractBundle,
    require_all_donor_sources: bool = True,
    reviewer_role: str = "human-reviewer",
    notes: Iterable[str] = (),
) -> WaveSixReadinessAssessment:
    """Build a deterministic Wave 6 readiness assessment."""

    return WaveSixReadinessAssessment(
        assessment_id=assessment_id,
        trace=trace,
        contract_bundle=contract_bundle,
        require_all_donor_sources=require_all_donor_sources,
        reviewer_role=reviewer_role,
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


def _stable_sha256(payload: Mapping[str, Any]) -> str:
    """Return deterministic SHA-256 over a canonical JSON payload."""

    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
