"""Wave 6 reality-correction records.

Measured system-level cognition is not proven by logging feedback. The proof
surface is narrower: measured reality must correct memory or reasoning in a way
that can change future reasoning. This module captures that proof target without
executing donor repos or claiming AGI.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, TypeVar

from ix_cognition_kernel.wave6_contracts import (
    WaveSixClaimBoundary,
    WaveSixDecisionState,
    WaveSixLoopStage,
    WaveSixSourceSystem,
    required_wave_six_claim_boundaries,
)
from ix_cognition_kernel.wave6_master_loop import WaveSixMasterLoopStep

T = TypeVar("T")
E = TypeVar("E", bound=StrEnum)

WAVE_SIX_REALITY_CORRECTION_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave6-reality-correction-v1"
)
WAVE_SIX_REALITY_CORRECTION_LEDGER_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave6-reality-correction-ledger-v1"
)


class WaveSixRealitySignalKind(StrEnum):
    """Kinds of measured-reality signals that may correct reasoning."""

    OBSERVED_OUTCOME = "observed-outcome"
    FAILED_PREDICTION = "failed-prediction"
    CONTRADICTED_ASSUMPTION = "contradicted-assumption"
    TRANSFER_FAILURE = "transfer-failure"
    NOVELTY_SURPRISE = "novelty-surprise"
    SAFETY_GATE_FEEDBACK = "safety-gate-feedback"


class WaveSixCorrectionDecision(StrEnum):
    """Correction decisions allowed after prediction-vs-outcome comparison."""

    RECORD_ONLY = "record-only"
    UPDATE_FUTURE_REASONING = "update-future-reasoning"
    QUARANTINE_MEMORY = "quarantine-memory"
    REQUIRE_RETRY = "require-retry"
    BLOCK_CLAIM = "block-claim"


@dataclass(frozen=True, slots=True)
class WaveSixRealityCorrectionRecord:
    """Evidence that measured reality corrected future reasoning."""

    record_id: str
    prediction_summary: str
    measured_outcome_summary: str
    reality_signal_kind: WaveSixRealitySignalKind
    prediction_evidence_ids: tuple[str, ...]
    outcome_evidence_ids: tuple[str, ...]
    prior_reasoning_fingerprint: str
    corrected_reasoning_summary: str
    affected_memory_ids: tuple[str, ...]
    correction_decision: WaveSixCorrectionDecision
    source_system: WaveSixSourceSystem = WaveSixSourceSystem.IX_COGNITION_KERNEL
    decision: WaveSixDecisionState = WaveSixDecisionState.NEEDS_MORE_EVIDENCE
    changes_future_reasoning: bool = False
    requires_human_review: bool = True
    allows_autonomous_execution: bool = False
    claims_agi: bool = False
    claim_boundaries: tuple[WaveSixClaimBoundary, ...] = (
        required_wave_six_claim_boundaries()
    )
    schema_version: str = WAVE_SIX_REALITY_CORRECTION_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate that correction claims are evidence-bound and fail closed."""

        if not self.requires_human_review:
            raise ValueError("Reality-correction records must require human review.")
        if self.allows_autonomous_execution:
            raise ValueError(
                "Reality-correction records must not allow autonomous execution."
            )
        if self.claims_agi:
            raise ValueError("Reality-correction records must not claim AGI.")
        object.__setattr__(
            self,
            "record_id",
            _require_non_empty(self.record_id, "record_id"),
        )
        object.__setattr__(
            self,
            "prediction_summary",
            _require_non_empty(self.prediction_summary, "prediction_summary"),
        )
        object.__setattr__(
            self,
            "measured_outcome_summary",
            _require_non_empty(
                self.measured_outcome_summary, "measured_outcome_summary"
            ),
        )
        object.__setattr__(
            self,
            "prediction_evidence_ids",
            _normalize_unique_text_tuple(
                self.prediction_evidence_ids, label="prediction_evidence_id"
            ),
        )
        object.__setattr__(
            self,
            "outcome_evidence_ids",
            _normalize_unique_text_tuple(
                self.outcome_evidence_ids, label="outcome_evidence_id"
            ),
        )
        object.__setattr__(
            self,
            "prior_reasoning_fingerprint",
            _require_non_empty(
                self.prior_reasoning_fingerprint,
                "prior_reasoning_fingerprint",
            ),
        )
        object.__setattr__(
            self,
            "corrected_reasoning_summary",
            _require_non_empty(
                self.corrected_reasoning_summary,
                "corrected_reasoning_summary",
            ),
        )
        object.__setattr__(
            self,
            "affected_memory_ids",
            _normalize_unique_text_tuple(
                self.affected_memory_ids, label="affected_memory_id"
            ),
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
        if not self.prediction_evidence_ids:
            raise ValueError("Reality-correction records require prediction evidence.")
        if not self.outcome_evidence_ids:
            raise ValueError("Reality-correction records require outcome evidence.")
        missing_boundaries = tuple(
            boundary
            for boundary in required_wave_six_claim_boundaries()
            if boundary not in self.claim_boundaries
        )
        if missing_boundaries:
            raise ValueError(
                "Reality-correction records must preserve required claim boundary: "
                f"{missing_boundaries[0].value}"
            )
        if self.changes_future_reasoning and not self.affected_memory_ids:
            raise ValueError(
                "Future reasoning change requires affected memory identifiers."
            )
        if (
            self.changes_future_reasoning
            and self.correction_decision is WaveSixCorrectionDecision.RECORD_ONLY
        ):
            raise ValueError(
                "Future reasoning change cannot use a record-only correction decision."
            )

    @property
    def evidence_bound(self) -> bool:
        """Return whether prediction and outcome evidence are both present."""

        return bool(self.prediction_evidence_ids and self.outcome_evidence_ids)

    @property
    def review_ready(self) -> bool:
        """Return whether this correction can enter Wave 6 review."""

        return self.decision in {
            WaveSixDecisionState.READY_FOR_WAVE_SIX_LOOP,
            WaveSixDecisionState.READY_FOR_INDEPENDENT_REVIEW,
        }

    @property
    def blocks_claim(self) -> bool:
        """Return whether this record blocks capability interpretation."""

        return (
            self.decision is WaveSixDecisionState.BLOCKED
            or self.correction_decision is WaveSixCorrectionDecision.BLOCK_CLAIM
        )

    @property
    def proves_reality_corrected_future_reasoning(self) -> bool:
        """Return whether the record satisfies the core Wave 6 proof target."""

        return (
            self.evidence_bound
            and self.changes_future_reasoning
            and bool(self.affected_memory_ids)
            and self.correction_decision
            in {
                WaveSixCorrectionDecision.UPDATE_FUTURE_REASONING,
                WaveSixCorrectionDecision.QUARANTINE_MEMORY,
            }
        )

    @property
    def combined_evidence_ids(self) -> tuple[str, ...]:
        """Return prediction and outcome evidence ids without duplicates."""

        combined: list[str] = []
        seen: set[str] = set()
        for evidence_id in (*self.prediction_evidence_ids, *self.outcome_evidence_ids):
            if evidence_id not in seen:
                combined.append(evidence_id)
                seen.add(evidence_id)
        return tuple(combined)

    def to_memory_update_step(self) -> WaveSixMasterLoopStep:
        """Convert the correction into a measured memory-update loop step."""

        return WaveSixMasterLoopStep(
            step_id=f"memory-update-{self.record_id}",
            stage=WaveSixLoopStage.MEMORY_UPDATE,
            summary=self.corrected_reasoning_summary,
            source_system=self.source_system,
            evidence_ids=self.combined_evidence_ids,
            decision=self.decision,
            measured_reality_signal=True,
            changes_future_reasoning=self.proves_reality_corrected_future_reasoning,
        )

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic payload for review and hashing."""

        return {
            "affected_memory_ids": list(self.affected_memory_ids),
            "allows_autonomous_execution": self.allows_autonomous_execution,
            "changes_future_reasoning": self.changes_future_reasoning,
            "claim_boundaries": [boundary.value for boundary in self.claim_boundaries],
            "claims_agi": self.claims_agi,
            "corrected_reasoning_summary": self.corrected_reasoning_summary,
            "correction_decision": self.correction_decision.value,
            "decision": self.decision.value,
            "measured_outcome_summary": self.measured_outcome_summary,
            "outcome_evidence_ids": list(self.outcome_evidence_ids),
            "prediction_evidence_ids": list(self.prediction_evidence_ids),
            "prediction_summary": self.prediction_summary,
            "prior_reasoning_fingerprint": self.prior_reasoning_fingerprint,
            "record_id": self.record_id,
            "requires_human_review": self.requires_human_review,
            "reality_signal_kind": self.reality_signal_kind.value,
            "schema_version": self.schema_version,
            "source_system": self.source_system.value,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this correction record."""

        return _stable_sha256(self.canonical_payload())


@dataclass(frozen=True, slots=True)
class WaveSixRealityCorrectionLedger:
    """Ledger of correction records used to judge Wave 6 evidence."""

    ledger_id: str
    records: tuple[WaveSixRealityCorrectionRecord, ...]
    required_proof_records: int = 1
    notes: tuple[str, ...] = ()
    schema_version: str = WAVE_SIX_REALITY_CORRECTION_LEDGER_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate ledger identity, record uniqueness, and proof threshold."""

        object.__setattr__(
            self,
            "ledger_id",
            _require_non_empty(self.ledger_id, "ledger_id"),
        )
        if not self.records:
            raise ValueError("Reality-correction ledgers require at least one record.")
        sorted_records = tuple(
            sorted(self.records, key=lambda record: record.record_id)
        )
        _unique_ids((record.record_id for record in sorted_records), label="record_id")
        object.__setattr__(self, "records", sorted_records)
        if self.required_proof_records < 1:
            raise ValueError("required_proof_records must be at least 1.")
        object.__setattr__(
            self,
            "notes",
            _normalize_unique_text_tuple(self.notes, label="ledger note"),
        )
        object.__setattr__(
            self,
            "schema_version",
            _require_non_empty(self.schema_version, "schema_version"),
        )

    @property
    def record_ids(self) -> tuple[str, ...]:
        """Return correction record ids in deterministic order."""

        return tuple(record.record_id for record in self.records)

    @property
    def blocking_record_ids(self) -> tuple[str, ...]:
        """Return record ids that block capability interpretation."""

        return tuple(record.record_id for record in self.records if record.blocks_claim)

    @property
    def review_ready_record_ids(self) -> tuple[str, ...]:
        """Return correction records ready for review."""

        return tuple(record.record_id for record in self.records if record.review_ready)

    @property
    def proof_record_ids(self) -> tuple[str, ...]:
        """Return records proving reality-corrected future reasoning."""

        return tuple(
            record.record_id
            for record in self.records
            if record.proves_reality_corrected_future_reasoning
        )

    @property
    def has_required_reality_correction_proof(self) -> bool:
        """Return whether the ledger meets the configured proof threshold."""

        return len(self.proof_record_ids) >= self.required_proof_records

    @property
    def ready_for_wave_six_memory_update(self) -> bool:
        """Return whether the ledger can support a Wave 6 memory update."""

        return (
            self.has_required_reality_correction_proof
            and not self.blocking_record_ids
        )

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic payload for review and hashing."""

        return {
            "blocking_record_ids": list(self.blocking_record_ids),
            "has_required_reality_correction_proof": (
                self.has_required_reality_correction_proof
            ),
            "ledger_id": self.ledger_id,
            "notes": list(self.notes),
            "proof_record_ids": list(self.proof_record_ids),
            "records": [record.canonical_payload() for record in self.records],
            "required_proof_records": self.required_proof_records,
            "schema_version": self.schema_version,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this correction ledger."""

        return _stable_sha256(self.canonical_payload())


def build_wave_six_reality_correction_ledger(
    *,
    ledger_id: str,
    records: Iterable[WaveSixRealityCorrectionRecord],
    required_proof_records: int = 1,
    notes: Iterable[str] = (),
) -> WaveSixRealityCorrectionLedger:
    """Build a deterministic Wave 6 reality-correction ledger."""

    return WaveSixRealityCorrectionLedger(
        ledger_id=ledger_id,
        records=tuple(records),
        required_proof_records=required_proof_records,
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
