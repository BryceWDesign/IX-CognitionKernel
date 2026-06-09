"""Wave 6 fail-closed candidate readiness gate.

The bounded candidate assembly joins imported IX contract evidence, IX obligation
pressure, and supporting donor receipts. This gate is the next safety layer: it
checks whether that assembly may enter serious bounded Wave 6 review.

The gate does not satisfy open IX obligations, execute donor repositories, grant
authority, certify anything, or claim AGI. It fails closed when the assembly is
not ready, when donor evidence is incomplete, when IX obligation pressure is
unresolved, or when human and independent review boundaries are missing.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Protocol

WAVE_SIX_FAIL_CLOSED_CANDIDATE_GATE_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave6-fail-closed-candidate-gate-v1"
)
WAVE_SIX_FAIL_CLOSED_CANDIDATE_GATE_ENGINE_ID = (
    "wave6-fail-closed-candidate-gate-engine"
)


class DonorIntakeLike(Protocol):
    """Structural donor-intake surface required by the candidate gate."""

    @property
    def missing_source_systems(self) -> tuple[Any, ...]:
        """Return missing donor source systems."""

    @property
    def missing_required_artifact_keys(self) -> tuple[str, ...]:
        """Return missing donor source/artifact evidence keys."""

    def fingerprint(self) -> str:
        """Return deterministic donor-intake fingerprint."""


class CandidateAssemblyLike(Protocol):
    """Structural candidate assembly surface required by the gate."""

    @property
    def attempt(self) -> str:
        """Return the candidate attempt id."""

    @property
    def readiness_blockers(self) -> tuple[Any, ...]:
        """Return candidate assembly readiness blockers."""

    @property
    def ready_for_fail_closed_readiness_gate(self) -> bool:
        """Return whether the assembly believes it can enter readiness gates."""

    @property
    def evidence_ids(self) -> tuple[str, ...]:
        """Return assembled evidence ids."""

    @property
    def ix_obligation_gap_ids(self) -> tuple[str, ...]:
        """Return IX obligation evidence-gap ids."""

    @property
    def ix_falsification_probe_ids(self) -> tuple[str, ...]:
        """Return IX falsification-probe ids."""

    @property
    def donor_intake_bundle(self) -> DonorIntakeLike:
        """Return donor evidence intake bundle."""

    @property
    def human_review_required(self) -> bool:
        """Return whether human review is required."""

    @property
    def metadata_only(self) -> bool:
        """Return whether the assembly remains metadata-only."""

    @property
    def allows_autonomous_execution(self) -> bool:
        """Return whether the assembly grants autonomous execution."""

    @property
    def claims_agi(self) -> bool:
        """Return whether the assembly claims AGI."""

    @property
    def claims_production_ready(self) -> bool:
        """Return whether the assembly claims production readiness."""

    @property
    def claims_certified(self) -> bool:
        """Return whether the assembly claims certification."""

    @property
    def self_validated(self) -> bool:
        """Return whether the assembly self-validates."""

    def fingerprint(self) -> str:
        """Return deterministic candidate assembly fingerprint."""


class WaveSixFailClosedCandidateGateStatus(StrEnum):
    """Fail-closed status for candidate readiness gating."""

    BLOCKED = "blocked"
    NEEDS_MORE_EVIDENCE = "needs-more-evidence"
    READY_FOR_BOUNDED_REVIEW_INPUTS = "ready-for-bounded-review-inputs"


class WaveSixFailClosedCandidateGateDecision(StrEnum):
    """Decision emitted by the fail-closed candidate gate."""

    BLOCK_CANDIDATE_REVIEW = "block-candidate-review"
    CONTINUE_EVIDENCE_COLLECTION = "continue-evidence-collection"
    ENTER_BOUNDED_REVIEW_QUEUE = "enter-bounded-review-queue"


class WaveSixFailClosedCandidateGateBlocker(StrEnum):
    """Reasons the candidate gate cannot allow bounded review."""

    CANDIDATE_ASSEMBLY_NOT_READY = "candidate-assembly-not-ready"
    IX_OBLIGATION_PRESSURE_UNRESOLVED = "ix-obligation-pressure-unresolved"
    DONOR_EVIDENCE_INCOMPLETE = "donor-evidence-incomplete"
    HUMAN_AUTHORITY_MISSING = "human-authority-missing"
    INDEPENDENT_REVIEW_MISSING = "independent-review-missing"
    CLAIM_BOUNDARY_INVALID = "claim-boundary-invalid"
    EXECUTION_AUTHORITY_PRESENT = "execution-authority-present"
    OVERCLAIM_PRESENT = "overclaim-present"
    SELF_VALIDATION_PRESENT = "self-validation-present"
    EVIDENCE_PACKAGE_EMPTY = "evidence-package-empty"
    FALSIFICATION_PRESSURE_MISSING = "falsification-pressure-missing"


@dataclass(frozen=True, slots=True)
class WaveSixFailClosedCandidateGate:
    """Fail-closed gate for a bounded Wave 6 candidate assembly."""

    gate_id: str
    candidate_assembly: CandidateAssemblyLike
    claim_boundary_statement: str
    human_authority_id: str
    independent_reviewer_id: str
    generated_by_engine_id: str = WAVE_SIX_FAIL_CLOSED_CANDIDATE_GATE_ENGINE_ID
    notes: tuple[str, ...] = ()
    claims_agi: bool = False
    claims_production_ready: bool = False
    claims_certified: bool = False
    allows_autonomous_authority: bool = False
    self_validated: bool = False
    schema_version: str = WAVE_SIX_FAIL_CLOSED_CANDIDATE_GATE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Normalize gate metadata without hiding missing-review blockers."""

        object.__setattr__(self, "gate_id", _require_non_empty(self.gate_id, "gate_id"))
        object.__setattr__(
            self,
            "claim_boundary_statement",
            _normalize_text(self.claim_boundary_statement),
        )
        object.__setattr__(
            self,
            "human_authority_id",
            _normalize_text(self.human_authority_id),
        )
        object.__setattr__(
            self,
            "independent_reviewer_id",
            _normalize_text(self.independent_reviewer_id),
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
            _normalize_unique_text_tuple(self.notes, label="gate note"),
        )
        object.__setattr__(
            self,
            "schema_version",
            _require_non_empty(self.schema_version, "schema_version"),
        )

    @property
    def attempt(self) -> str:
        """Return the gated candidate attempt id."""

        return self.candidate_assembly.attempt

    @property
    def claim_boundary_statement_valid(self) -> bool:
        """Return whether the claim boundary blocks overclaiming."""

        normalized = self.claim_boundary_statement.casefold()
        required_fragments = (
            "measured system-level cognition",
            "not an agi",
            "human",
            "independent review",
            "no autonomous execution",
        )
        return all(fragment in normalized for fragment in required_fragments)

    @property
    def overclaim_present(self) -> bool:
        """Return whether the gate or assembly crosses claim boundaries."""

        return (
            self.claims_agi
            or self.claims_production_ready
            or self.claims_certified
            or self.candidate_assembly.claims_agi
            or self.candidate_assembly.claims_production_ready
            or self.candidate_assembly.claims_certified
        )

    @property
    def execution_authority_present(self) -> bool:
        """Return whether the gate or assembly grants execution authority."""

        return (
            self.allows_autonomous_authority
            or self.candidate_assembly.allows_autonomous_execution
            or not self.candidate_assembly.metadata_only
        )

    @property
    def self_validation_present(self) -> bool:
        """Return whether the gate or assembly attempts self-validation."""

        return self.self_validated or self.candidate_assembly.self_validated

    @property
    def human_authority_present(self) -> bool:
        """Return whether human review remains required and identified."""

        return bool(self.human_authority_id) and (
            self.candidate_assembly.human_review_required
        )

    @property
    def independent_review_present(self) -> bool:
        """Return whether an independent reviewer identity is present."""

        return bool(self.independent_reviewer_id)

    @property
    def donor_evidence_incomplete(self) -> bool:
        """Return whether donor evidence coverage remains incomplete."""

        donor_intake = self.candidate_assembly.donor_intake_bundle
        return bool(
            donor_intake.missing_source_systems
            or donor_intake.missing_required_artifact_keys
        )

    @property
    def ix_obligation_pressure_unresolved(self) -> bool:
        """Return whether IX obligation pressure is still blocking review."""

        blocker_values = _string_values(self.candidate_assembly.readiness_blockers)
        return (
            bool(self.candidate_assembly.ix_obligation_gap_ids)
            and "ix-obligation-gaps-blocking" in blocker_values
        )

    @property
    def evidence_package_empty(self) -> bool:
        """Return whether the assembly has no evidence ids."""

        return not self.candidate_assembly.evidence_ids

    @property
    def falsification_pressure_missing(self) -> bool:
        """Return whether no IX falsification pressure is represented."""

        return not self.candidate_assembly.ix_falsification_probe_ids

    @property
    def blockers(self) -> tuple[WaveSixFailClosedCandidateGateBlocker, ...]:
        """Return deterministic blockers that prevent bounded review."""

        blockers: list[WaveSixFailClosedCandidateGateBlocker] = []
        if self.overclaim_present:
            blockers.append(WaveSixFailClosedCandidateGateBlocker.OVERCLAIM_PRESENT)
        if self.execution_authority_present:
            blockers.append(
                WaveSixFailClosedCandidateGateBlocker.EXECUTION_AUTHORITY_PRESENT
            )
        if self.self_validation_present:
            blockers.append(WaveSixFailClosedCandidateGateBlocker.SELF_VALIDATION_PRESENT)
        if not self.human_authority_present:
            blockers.append(WaveSixFailClosedCandidateGateBlocker.HUMAN_AUTHORITY_MISSING)
        if not self.independent_review_present:
            blockers.append(
                WaveSixFailClosedCandidateGateBlocker.INDEPENDENT_REVIEW_MISSING
            )
        if not self.claim_boundary_statement_valid:
            blockers.append(WaveSixFailClosedCandidateGateBlocker.CLAIM_BOUNDARY_INVALID)
        if not self.candidate_assembly.ready_for_fail_closed_readiness_gate:
            blockers.append(
                WaveSixFailClosedCandidateGateBlocker.CANDIDATE_ASSEMBLY_NOT_READY
            )
        if self.ix_obligation_pressure_unresolved:
            blockers.append(
                WaveSixFailClosedCandidateGateBlocker.IX_OBLIGATION_PRESSURE_UNRESOLVED
            )
        if self.donor_evidence_incomplete:
            blockers.append(WaveSixFailClosedCandidateGateBlocker.DONOR_EVIDENCE_INCOMPLETE)
        if self.evidence_package_empty:
            blockers.append(WaveSixFailClosedCandidateGateBlocker.EVIDENCE_PACKAGE_EMPTY)
        if self.falsification_pressure_missing:
            blockers.append(
                WaveSixFailClosedCandidateGateBlocker.FALSIFICATION_PRESSURE_MISSING
            )
        return tuple(blockers)

    @property
    def status(self) -> WaveSixFailClosedCandidateGateStatus:
        """Return fail-closed candidate gate status."""

        hard_blockers = {
            WaveSixFailClosedCandidateGateBlocker.OVERCLAIM_PRESENT,
            WaveSixFailClosedCandidateGateBlocker.EXECUTION_AUTHORITY_PRESENT,
            WaveSixFailClosedCandidateGateBlocker.SELF_VALIDATION_PRESENT,
            WaveSixFailClosedCandidateGateBlocker.HUMAN_AUTHORITY_MISSING,
            WaveSixFailClosedCandidateGateBlocker.INDEPENDENT_REVIEW_MISSING,
            WaveSixFailClosedCandidateGateBlocker.CLAIM_BOUNDARY_INVALID,
        }
        if any(blocker in hard_blockers for blocker in self.blockers):
            return WaveSixFailClosedCandidateGateStatus.BLOCKED
        if self.blockers:
            return WaveSixFailClosedCandidateGateStatus.NEEDS_MORE_EVIDENCE
        return WaveSixFailClosedCandidateGateStatus.READY_FOR_BOUNDED_REVIEW_INPUTS

    @property
    def decision(self) -> WaveSixFailClosedCandidateGateDecision:
        """Return the review decision represented by this gate."""

        if self.status is WaveSixFailClosedCandidateGateStatus.BLOCKED:
            return WaveSixFailClosedCandidateGateDecision.BLOCK_CANDIDATE_REVIEW
        if self.status is WaveSixFailClosedCandidateGateStatus.NEEDS_MORE_EVIDENCE:
            return WaveSixFailClosedCandidateGateDecision.CONTINUE_EVIDENCE_COLLECTION
        return WaveSixFailClosedCandidateGateDecision.ENTER_BOUNDED_REVIEW_QUEUE

    @property
    def ready_for_bounded_review_inputs(self) -> bool:
        """Return whether the package may enter bounded review-input staging."""

        return (
            self.status
            is WaveSixFailClosedCandidateGateStatus.READY_FOR_BOUNDED_REVIEW_INPUTS
        )

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic fail-closed gate payload."""

        donor_intake = self.candidate_assembly.donor_intake_bundle
        return {
            "allows_autonomous_authority": self.allows_autonomous_authority,
            "assembly_fingerprint": self.candidate_assembly.fingerprint(),
            "attempt": self.attempt,
            "blockers": [blocker.value for blocker in self.blockers],
            "claim_boundary_statement": self.claim_boundary_statement,
            "claim_boundary_statement_valid": self.claim_boundary_statement_valid,
            "claims_agi": self.claims_agi,
            "claims_certified": self.claims_certified,
            "claims_production_ready": self.claims_production_ready,
            "decision": self.decision.value,
            "donor_intake_fingerprint": donor_intake.fingerprint(),
            "evidence_ids": list(self.candidate_assembly.evidence_ids),
            "generated_by_engine_id": self.generated_by_engine_id,
            "gate_id": self.gate_id,
            "human_authority_id": self.human_authority_id,
            "independent_reviewer_id": self.independent_reviewer_id,
            "ix_falsification_probe_ids": list(
                self.candidate_assembly.ix_falsification_probe_ids
            ),
            "ix_obligation_gap_ids": list(
                self.candidate_assembly.ix_obligation_gap_ids
            ),
            "missing_donor_artifact_keys": list(
                donor_intake.missing_required_artifact_keys
            ),
            "missing_donor_source_systems": [
                _string_value(source) for source in donor_intake.missing_source_systems
            ],
            "notes": list(self.notes),
            "ready_for_bounded_review_inputs": self.ready_for_bounded_review_inputs,
            "schema_version": self.schema_version,
            "self_validated": self.self_validated,
            "status": self.status.value,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this gate."""

        return _stable_sha256(self.canonical_payload())


def build_wave_six_fail_closed_candidate_gate(
    *,
    gate_id: str,
    candidate_assembly: CandidateAssemblyLike,
    claim_boundary_statement: str,
    human_authority_id: str,
    independent_reviewer_id: str,
    notes: Iterable[str] = (),
) -> WaveSixFailClosedCandidateGate:
    """Build a fail-closed gate for a bounded candidate assembly."""

    return WaveSixFailClosedCandidateGate(
        gate_id=gate_id,
        candidate_assembly=candidate_assembly,
        claim_boundary_statement=claim_boundary_statement,
        human_authority_id=human_authority_id,
        independent_reviewer_id=independent_reviewer_id,
        notes=tuple(notes),
    )


def _string_values(values: Iterable[Any]) -> frozenset[str]:
    """Return enum-like values as strings."""

    return frozenset(_string_value(value) for value in values)


def _string_value(value: Any) -> str:
    """Return the stable string value for enum-like objects."""

    raw_value = getattr(value, "value", value)
    return str(raw_value)


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


def _normalize_text(value: str) -> str:
    """Return stripped text while allowing empty review-boundary blockers."""

    return value.strip()


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
