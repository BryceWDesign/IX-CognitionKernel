"""Wave 6 bounded candidate assembly.

This module joins the first three Wave 6 integration layers into a single
reviewable candidate assembly surface:

* IX ``kernel-handoff.json`` ingestion.
* IX obligation evidence and falsification pressure.
* Supporting donor evidence intake receipts.

The assembly is deliberately fail-closed. It does not execute donor repos, does
not satisfy imported IX obligations by itself, does not advance maturity, and
does not claim AGI. It gives later readiness and assurance layers one stable
place to ask what was assembled, what is still missing, and what blocks review.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from ix_cognition_kernel.wave6_contracts import WaveSixContractArtifact
from ix_cognition_kernel.wave6_donor_evidence_intake import (
    WaveSixDonorEvidenceIntakeBundle,
    WaveSixDonorEvidenceIntakeStatus,
)
from ix_cognition_kernel.wave6_falsification import WaveSixFalsificationProbe
from ix_cognition_kernel.wave6_gap_register import WaveSixEvidenceGap
from ix_cognition_kernel.wave6_ix_handoff import WaveSixIxHandoffPackage
from ix_cognition_kernel.wave6_ix_obligation_pressure import (
    WaveSixIxObligationPressureBundle,
)

WAVE_SIX_CANDIDATE_ASSEMBLY_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave6-candidate-assembly-v1"
)
WAVE_SIX_CANDIDATE_ASSEMBLY_ENGINE_ID = "wave6-candidate-assembly-engine"


class WaveSixCandidateAssemblyStatus(StrEnum):
    """Fail-closed status for a bounded Wave 6 candidate assembly."""

    BLOCKED_BY_IX_OBLIGATION_PRESSURE = "blocked-by-ix-obligation-pressure"
    NEEDS_DONOR_EVIDENCE = "needs-donor-evidence"
    READY_FOR_FAIL_CLOSED_READINESS_GATE = "ready-for-fail-closed-readiness-gate"


class WaveSixCandidateAssemblyBlocker(StrEnum):
    """Named blockers emitted by a bounded candidate assembly."""

    IX_PRESSURE_ATTEMPT_MISMATCH = "ix-pressure-attempt-mismatch"
    IX_PRESSURE_FINGERPRINT_MISMATCH = "ix-pressure-fingerprint-mismatch"
    IX_PRESSURE_EVIDENCE_MISMATCH = "ix-pressure-evidence-mismatch"
    IX_PRESSURE_ARTIFACT_MISMATCH = "ix-pressure-artifact-mismatch"
    IX_OBLIGATION_GAPS_BLOCKING = "ix-obligation-gaps-blocking"
    DONOR_SOURCE_EVIDENCE_MISSING = "donor-source-evidence-missing"
    DONOR_ARTIFACT_EVIDENCE_MISSING = "donor-artifact-evidence-missing"


@dataclass(frozen=True, slots=True)
class WaveSixCandidateAssembly:
    """Bounded assembly of IX contract pressure and donor evidence receipts."""

    assembly_id: str
    ix_package: WaveSixIxHandoffPackage
    ix_pressure_bundle: WaveSixIxObligationPressureBundle
    donor_intake_bundle: WaveSixDonorEvidenceIntakeBundle
    generated_by_engine_id: str = WAVE_SIX_CANDIDATE_ASSEMBLY_ENGINE_ID
    human_review_required: bool = True
    metadata_only: bool = True
    allows_autonomous_execution: bool = False
    claims_agi: bool = False
    claims_production_ready: bool = False
    claims_certified: bool = False
    self_validated: bool = False
    notes: tuple[str, ...] = ()
    schema_version: str = WAVE_SIX_CANDIDATE_ASSEMBLY_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate assembly identity, provenance linkage, and claim boundaries."""

        object.__setattr__(
            self,
            "assembly_id",
            _require_non_empty(self.assembly_id, "assembly_id"),
        )
        object.__setattr__(
            self,
            "generated_by_engine_id",
            _require_non_empty(
                self.generated_by_engine_id,
                "generated_by_engine_id",
            ),
        )
        object.__setattr__(
            self,
            "notes",
            _normalize_unique_text_tuple(self.notes, label="assembly note"),
        )
        object.__setattr__(
            self,
            "schema_version",
            _require_non_empty(self.schema_version, "schema_version"),
        )
        if not self.human_review_required:
            raise ValueError("Wave 6 candidate assemblies require human review.")
        if not self.metadata_only:
            raise ValueError("Wave 6 candidate assemblies must be metadata-only.")
        if self.allows_autonomous_execution:
            raise ValueError("Wave 6 candidate assemblies must not grant execution.")
        if self.claims_agi:
            raise ValueError("Wave 6 candidate assemblies must not claim AGI.")
        if self.claims_production_ready:
            raise ValueError("Wave 6 candidate assemblies must not claim production.")
        if self.claims_certified:
            raise ValueError("Wave 6 candidate assemblies must not certify results.")
        if self.self_validated:
            raise ValueError("Wave 6 candidate assemblies must not self-validate.")
        if self.linkage_blockers:
            first_blocker = self.linkage_blockers[0]
            raise ValueError(f"Wave 6 candidate linkage failed: {first_blocker.value}")

    @property
    def attempt(self) -> str:
        """Return the IX attempt id represented by this candidate assembly."""

        return self.ix_package.attempt

    @property
    def ix_contract_artifact(self) -> WaveSixContractArtifact:
        """Return the imported IX contract artifact."""

        return self.ix_package.to_contract_artifact()

    @property
    def donor_contract_artifacts(self) -> tuple[WaveSixContractArtifact, ...]:
        """Return accepted donor evidence artifacts."""

        return self.donor_intake_bundle.contract_artifacts

    @property
    def all_contract_artifacts(self) -> tuple[WaveSixContractArtifact, ...]:
        """Return all currently assembled contract artifacts."""

        return (self.ix_contract_artifact, *self.donor_contract_artifacts)

    @property
    def artifact_ids(self) -> tuple[str, ...]:
        """Return assembled contract artifact ids in deterministic order."""

        return tuple(artifact.artifact_id for artifact in self.all_contract_artifacts)

    @property
    def evidence_ids(self) -> tuple[str, ...]:
        """Return unique evidence ids represented by the assembly."""

        return _unique_preserving_order(
            evidence_id
            for artifact in self.all_contract_artifacts
            for evidence_id in artifact.evidence_ids
        )

    @property
    def ix_obligation_gap_ids(self) -> tuple[str, ...]:
        """Return generated IX obligation evidence-gap ids."""

        return self.ix_pressure_bundle.evidence_gap_ids

    @property
    def ix_falsification_probe_ids(self) -> tuple[str, ...]:
        """Return generated IX falsification-probe ids."""

        return self.ix_pressure_bundle.falsification_probe_ids

    @property
    def ix_evidence_gaps(self) -> tuple[WaveSixEvidenceGap, ...]:
        """Return generated IX obligation evidence gaps."""

        return tuple(
            pressure.evidence_gap for pressure in self.ix_pressure_bundle.pressures
        )

    @property
    def ix_falsification_probes(self) -> tuple[WaveSixFalsificationProbe, ...]:
        """Return generated IX falsification probes."""

        return tuple(
            pressure.falsification_probe
            for pressure in self.ix_pressure_bundle.pressures
        )

    @property
    def linkage_blockers(self) -> tuple[WaveSixCandidateAssemblyBlocker, ...]:
        """Return structural linkage blockers between imported layers."""

        blockers: list[WaveSixCandidateAssemblyBlocker] = []
        contract_artifact = self.ix_package.to_contract_artifact()
        if self.ix_pressure_bundle.attempt != self.ix_package.attempt:
            blockers.append(
                WaveSixCandidateAssemblyBlocker.IX_PRESSURE_ATTEMPT_MISMATCH
            )
        if self.ix_pressure_bundle.source_package_fingerprint != (
            self.ix_package.fingerprint()
        ):
            blockers.append(
                WaveSixCandidateAssemblyBlocker.IX_PRESSURE_FINGERPRINT_MISMATCH
            )
        if self.ix_pressure_bundle.source_evidence_id != self.ix_package.ix_evidence_id:
            blockers.append(
                WaveSixCandidateAssemblyBlocker.IX_PRESSURE_EVIDENCE_MISMATCH
            )
        if self.ix_pressure_bundle.contract_artifact_id != (
            contract_artifact.artifact_id
        ):
            blockers.append(
                WaveSixCandidateAssemblyBlocker.IX_PRESSURE_ARTIFACT_MISMATCH
            )
        return tuple(blockers)

    @property
    def readiness_blockers(self) -> tuple[WaveSixCandidateAssemblyBlocker, ...]:
        """Return review blockers after structural linkage has been validated."""

        blockers: list[WaveSixCandidateAssemblyBlocker] = []
        if self.ix_pressure_bundle.blocking_gap_ids:
            blockers.append(WaveSixCandidateAssemblyBlocker.IX_OBLIGATION_GAPS_BLOCKING)
        if self.donor_intake_bundle.missing_source_systems:
            blockers.append(
                WaveSixCandidateAssemblyBlocker.DONOR_SOURCE_EVIDENCE_MISSING
            )
        if self.donor_intake_bundle.missing_required_artifact_keys:
            blockers.append(
                WaveSixCandidateAssemblyBlocker.DONOR_ARTIFACT_EVIDENCE_MISSING
            )
        return tuple(blockers)

    @property
    def status(self) -> WaveSixCandidateAssemblyStatus:
        """Return fail-closed assembly status."""

        if self.ix_pressure_bundle.blocking_gap_ids:
            return WaveSixCandidateAssemblyStatus.BLOCKED_BY_IX_OBLIGATION_PRESSURE
        if (
            self.donor_intake_bundle.status
            is WaveSixDonorEvidenceIntakeStatus.NEEDS_MORE_DONOR_EVIDENCE
        ):
            return WaveSixCandidateAssemblyStatus.NEEDS_DONOR_EVIDENCE
        return WaveSixCandidateAssemblyStatus.READY_FOR_FAIL_CLOSED_READINESS_GATE

    @property
    def ready_for_fail_closed_readiness_gate(self) -> bool:
        """Return whether this assembly can enter later readiness checks."""

        return (
            self.status
            is WaveSixCandidateAssemblyStatus.READY_FOR_FAIL_CLOSED_READINESS_GATE
        )

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic candidate assembly payload for review."""

        return {
            "all_contract_artifact_ids": list(self.artifact_ids),
            "allows_autonomous_execution": self.allows_autonomous_execution,
            "assembly_id": self.assembly_id,
            "attempt": self.attempt,
            "claims_agi": self.claims_agi,
            "claims_certified": self.claims_certified,
            "claims_production_ready": self.claims_production_ready,
            "donor_intake_fingerprint": self.donor_intake_bundle.fingerprint(),
            "evidence_ids": list(self.evidence_ids),
            "generated_by_engine_id": self.generated_by_engine_id,
            "human_review_required": self.human_review_required,
            "ix_contract_artifact_id": self.ix_contract_artifact.artifact_id,
            "ix_falsification_probe_ids": list(self.ix_falsification_probe_ids),
            "ix_handoff_fingerprint": self.ix_package.fingerprint(),
            "ix_obligation_gap_ids": list(self.ix_obligation_gap_ids),
            "ix_pressure_fingerprint": self.ix_pressure_bundle.fingerprint(),
            "metadata_only": self.metadata_only,
            "notes": list(self.notes),
            "readiness_blockers": [
                blocker.value for blocker in self.readiness_blockers
            ],
            "ready_for_fail_closed_readiness_gate": (
                self.ready_for_fail_closed_readiness_gate
            ),
            "schema_version": self.schema_version,
            "self_validated": self.self_validated,
            "status": self.status.value,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this assembly."""

        return _stable_sha256(self.canonical_payload())


def build_wave_six_candidate_assembly(
    *,
    assembly_id: str,
    ix_package: WaveSixIxHandoffPackage,
    ix_pressure_bundle: WaveSixIxObligationPressureBundle,
    donor_intake_bundle: WaveSixDonorEvidenceIntakeBundle,
    notes: Iterable[str] = (),
) -> WaveSixCandidateAssembly:
    """Build a bounded candidate assembly from imported Wave 6 layers."""

    return WaveSixCandidateAssembly(
        assembly_id=assembly_id,
        ix_package=ix_package,
        ix_pressure_bundle=ix_pressure_bundle,
        donor_intake_bundle=donor_intake_bundle,
        notes=tuple(notes),
    )


def _unique_preserving_order(values: Iterable[str]) -> tuple[str, ...]:
    """Return unique text values while preserving first-seen order."""

    seen: set[str] = set()
    unique: list[str] = []
    for value in values:
        if value not in seen:
            unique.append(value)
            seen.add(value)
    return tuple(unique)


def _normalize_unique_text_tuple(
    values: Iterable[str],
    *,
    label: str,
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


def _require_non_empty(value: str, label: str) -> str:
    """Return stripped text or raise when empty."""

    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{label} must not be empty.")
    return normalized


def _stable_sha256(payload: Mapping[str, Any]) -> str:
    """Return deterministic SHA-256 over a canonical JSON payload."""

    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
