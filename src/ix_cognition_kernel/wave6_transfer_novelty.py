"""Wave 6 transfer and novelty pressure records.

A Wave 6 measured cognition attempt cannot stop at memory correction. It must
pressure-test whether a corrected reasoning structure transfers to a different
context without hand-scripted rescue. This module captures that transfer proof in
small deterministic records and fails closed when novelty, negative controls, or
future-reasoning proof bindings are missing.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, TypeVar

T = TypeVar("T")
E = TypeVar("E", bound=StrEnum)

WAVE_SIX_TRANSFER_DOMAIN_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave6-transfer-domain-v1"
)
WAVE_SIX_TRANSFER_RECORD_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave6-transfer-novelty-record-v1"
)
WAVE_SIX_TRANSFER_LEDGER_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave6-transfer-novelty-ledger-v1"
)


class WaveSixTransferDecision(StrEnum):
    """Fail-closed decisions for transfer and novelty records."""

    ACCEPT_FOR_WAVE_SIX_REVIEW = "accept-for-wave-six-review"
    NEEDS_MORE_EVIDENCE = "needs-more-evidence"
    RECORD_ONLY = "record-only"
    BLOCK_CLAIM = "block-claim"


class WaveSixNoveltyPressureKind(StrEnum):
    """Kinds of novelty pressure used to resist benchmark theater."""

    DOMAIN_SHIFT = "domain-shift"
    HIDDEN_CONSTRAINT = "hidden-constraint"
    COUNTEREXAMPLE = "counterexample"
    NEGATIVE_CONTROL = "negative-control"
    PERTURBED_OBJECTIVE = "perturbed-objective"
    OUT_OF_DISTRIBUTION_ANALOGY = "out-of-distribution-analogy"


class WaveSixNegativeControlResult(StrEnum):
    """Negative-control outcomes for transfer review."""

    PASSED = "passed"
    FAILED = "failed"
    NOT_RUN = "not-run"


@dataclass(frozen=True, slots=True)
class WaveSixTransferDomain:
    """A bounded source or target domain used in a transfer probe."""

    domain_id: str
    name: str
    domain_family: str
    task_summary: str
    measurable_success_criteria: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    schema_version: str = WAVE_SIX_TRANSFER_DOMAIN_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Normalize domain fields and require measurable criteria."""

        object.__setattr__(
            self,
            "domain_id",
            _require_non_empty(self.domain_id, "domain_id"),
        )
        object.__setattr__(self, "name", _require_non_empty(self.name, "name"))
        object.__setattr__(
            self,
            "domain_family",
            _require_non_empty(self.domain_family, "domain_family"),
        )
        object.__setattr__(
            self,
            "task_summary",
            _require_non_empty(self.task_summary, "task_summary"),
        )
        object.__setattr__(
            self,
            "measurable_success_criteria",
            _normalize_unique_text_tuple(
                self.measurable_success_criteria,
                label="measurable_success_criterion",
            ),
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
        if not self.measurable_success_criteria:
            raise ValueError("Transfer domains require measurable success criteria.")
        if not self.evidence_ids:
            raise ValueError("Transfer domains require evidence ids.")

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic payload for hashing and review."""

        return {
            "domain_family": self.domain_family,
            "domain_id": self.domain_id,
            "evidence_ids": list(self.evidence_ids),
            "measurable_success_criteria": list(self.measurable_success_criteria),
            "name": self.name,
            "schema_version": self.schema_version,
            "task_summary": self.task_summary,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this domain."""

        return _stable_sha256(self.canonical_payload())


@dataclass(frozen=True, slots=True)
class WaveSixTransferNoveltyRecord:
    """Record that tests transfer of corrected reasoning under novelty."""

    record_id: str
    source_domain: WaveSixTransferDomain
    target_domain: WaveSixTransferDomain
    transferred_structure_id: str
    future_reasoning_proof_ids: tuple[str, ...]
    expected_transfer_behavior: str
    observed_target_behavior: str
    novelty_pressure_kinds: tuple[WaveSixNoveltyPressureKind, ...]
    negative_control_result: WaveSixNegativeControlResult
    negative_control_summary: str
    evidence_ids: tuple[str, ...]
    decision: WaveSixTransferDecision = WaveSixTransferDecision.NEEDS_MORE_EVIDENCE
    requires_human_review: bool = True
    allows_autonomous_execution: bool = False
    claims_agi: bool = False
    schema_version: str = WAVE_SIX_TRANSFER_RECORD_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate transfer claims without allowing novelty theater."""

        if not self.requires_human_review:
            raise ValueError("Transfer novelty records must require human review.")
        if self.allows_autonomous_execution:
            raise ValueError(
                "Transfer novelty records must not allow autonomous execution."
            )
        if self.claims_agi:
            raise ValueError("Transfer novelty records must not claim AGI.")
        object.__setattr__(
            self,
            "record_id",
            _require_non_empty(self.record_id, "record_id"),
        )
        object.__setattr__(
            self,
            "transferred_structure_id",
            _require_non_empty(
                self.transferred_structure_id,
                "transferred_structure_id",
            ),
        )
        object.__setattr__(
            self,
            "future_reasoning_proof_ids",
            _normalize_unique_text_tuple(
                self.future_reasoning_proof_ids,
                label="future_reasoning_proof_id",
            ),
        )
        object.__setattr__(
            self,
            "expected_transfer_behavior",
            _require_non_empty(
                self.expected_transfer_behavior,
                "expected_transfer_behavior",
            ),
        )
        object.__setattr__(
            self,
            "observed_target_behavior",
            _require_non_empty(
                self.observed_target_behavior,
                "observed_target_behavior",
            ),
        )
        object.__setattr__(
            self,
            "novelty_pressure_kinds",
            _normalize_unique_enum_tuple(
                self.novelty_pressure_kinds,
                label="novelty pressure kind",
            ),
        )
        object.__setattr__(
            self,
            "negative_control_summary",
            _require_non_empty(
                self.negative_control_summary,
                "negative_control_summary",
            ),
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
        if self.source_domain.domain_id == self.target_domain.domain_id:
            raise ValueError(
                "Transfer records require distinct source and target domains."
            )
        if self.source_domain.domain_family == self.target_domain.domain_family:
            raise ValueError("Transfer records require a cross-family domain shift.")
        if not self.future_reasoning_proof_ids:
            raise ValueError("Transfer records require future-reasoning proof ids.")
        if not self.novelty_pressure_kinds:
            raise ValueError("Transfer records require novelty pressure.")
        if (
            WaveSixNoveltyPressureKind.NEGATIVE_CONTROL
            not in self.novelty_pressure_kinds
        ):
            raise ValueError("Transfer records require negative-control pressure.")
        if not self.evidence_ids:
            raise ValueError("Transfer records require evidence ids.")

    @property
    def source_target_distinct(self) -> bool:
        """Return whether source and target domains are meaningfully distinct."""

        return (
            self.source_domain.domain_id != self.target_domain.domain_id
            and self.source_domain.domain_family != self.target_domain.domain_family
        )

    @property
    def negative_control_passed(self) -> bool:
        """Return whether the negative control passed."""

        return self.negative_control_result is WaveSixNegativeControlResult.PASSED

    @property
    def future_reasoning_bound(self) -> bool:
        """Return whether transfer is bound to prior future-reasoning proof."""

        return bool(self.future_reasoning_proof_ids)

    @property
    def novelty_pressure_bound(self) -> bool:
        """Return whether transfer faced explicit novelty pressure."""

        return bool(self.novelty_pressure_kinds)

    @property
    def evidence_bound(self) -> bool:
        """Return whether transfer, source, and target evidence are present."""

        return bool(
            self.evidence_ids
            and self.source_domain.evidence_ids
            and self.target_domain.evidence_ids
        )

    @property
    def accepted_for_review(self) -> bool:
        """Return whether the record is accepted for Wave 6 review."""

        return self.decision is WaveSixTransferDecision.ACCEPT_FOR_WAVE_SIX_REVIEW

    @property
    def blocks_claim(self) -> bool:
        """Return whether this transfer record blocks capability interpretation."""

        return self.decision is WaveSixTransferDecision.BLOCK_CLAIM

    @property
    def supports_transfer_claim(self) -> bool:
        """Return whether the record supports bounded transfer interpretation."""

        return (
            self.accepted_for_review
            and self.source_target_distinct
            and self.future_reasoning_bound
            and self.novelty_pressure_bound
            and self.negative_control_passed
            and self.evidence_bound
            and not self.blocks_claim
        )

    @property
    def combined_evidence_ids(self) -> tuple[str, ...]:
        """Return source, target, and transfer evidence without duplicates."""

        combined: list[str] = []
        seen: set[str] = set()
        for evidence_id in (
            *self.source_domain.evidence_ids,
            *self.target_domain.evidence_ids,
            *self.evidence_ids,
        ):
            if evidence_id not in seen:
                combined.append(evidence_id)
                seen.add(evidence_id)
        return tuple(combined)

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic payload for review and hashing."""

        return {
            "allows_autonomous_execution": self.allows_autonomous_execution,
            "claims_agi": self.claims_agi,
            "decision": self.decision.value,
            "evidence_ids": list(self.evidence_ids),
            "expected_transfer_behavior": self.expected_transfer_behavior,
            "future_reasoning_proof_ids": list(self.future_reasoning_proof_ids),
            "negative_control_result": self.negative_control_result.value,
            "negative_control_summary": self.negative_control_summary,
            "novelty_pressure_kinds": [
                pressure.value for pressure in self.novelty_pressure_kinds
            ],
            "observed_target_behavior": self.observed_target_behavior,
            "record_id": self.record_id,
            "requires_human_review": self.requires_human_review,
            "schema_version": self.schema_version,
            "source_domain_fingerprint": self.source_domain.fingerprint(),
            "target_domain_fingerprint": self.target_domain.fingerprint(),
            "transferred_structure_id": self.transferred_structure_id,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this transfer record."""

        return _stable_sha256(self.canonical_payload())


@dataclass(frozen=True, slots=True)
class WaveSixTransferNoveltyLedger:
    """Ledger of transfer and novelty records."""

    ledger_id: str
    records: tuple[WaveSixTransferNoveltyRecord, ...]
    required_supported_records: int = 1
    notes: tuple[str, ...] = ()
    schema_version: str = WAVE_SIX_TRANSFER_LEDGER_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate ledger identity, record uniqueness, and proof threshold."""

        object.__setattr__(
            self,
            "ledger_id",
            _require_non_empty(self.ledger_id, "ledger_id"),
        )
        if not self.records:
            raise ValueError("Transfer novelty ledgers require at least one record.")
        sorted_records = tuple(
            sorted(self.records, key=lambda record: record.record_id)
        )
        _unique_ids((record.record_id for record in sorted_records), label="record_id")
        object.__setattr__(self, "records", sorted_records)
        if self.required_supported_records < 1:
            raise ValueError("required_supported_records must be at least 1.")
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
        """Return transfer record ids in deterministic order."""

        return tuple(record.record_id for record in self.records)

    @property
    def supported_record_ids(self) -> tuple[str, ...]:
        """Return records supporting bounded transfer interpretation."""

        return tuple(
            record.record_id
            for record in self.records
            if record.supports_transfer_claim
        )

    @property
    def blocked_record_ids(self) -> tuple[str, ...]:
        """Return records that block capability interpretation."""

        return tuple(record.record_id for record in self.records if record.blocks_claim)

    @property
    def failed_negative_control_record_ids(self) -> tuple[str, ...]:
        """Return records whose negative controls did not pass."""

        return tuple(
            record.record_id
            for record in self.records
            if not record.negative_control_passed
        )

    @property
    def has_required_transfer_support(self) -> bool:
        """Return whether the ledger meets the transfer-support threshold."""

        return len(self.supported_record_ids) >= self.required_supported_records

    @property
    def ready_for_wave_six_review(self) -> bool:
        """Return whether transfer evidence can support Wave 6 review."""

        return self.has_required_transfer_support and not self.blocked_record_ids

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic ledger payload for hashing and review."""

        return {
            "blocked_record_ids": list(self.blocked_record_ids),
            "failed_negative_control_record_ids": list(
                self.failed_negative_control_record_ids
            ),
            "has_required_transfer_support": self.has_required_transfer_support,
            "ledger_id": self.ledger_id,
            "notes": list(self.notes),
            "ready_for_wave_six_review": self.ready_for_wave_six_review,
            "records": [record.canonical_payload() for record in self.records],
            "required_supported_records": self.required_supported_records,
            "schema_version": self.schema_version,
            "supported_record_ids": list(self.supported_record_ids),
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this transfer ledger."""

        return _stable_sha256(self.canonical_payload())


def build_wave_six_transfer_novelty_ledger(
    *,
    ledger_id: str,
    records: Iterable[WaveSixTransferNoveltyRecord],
    required_supported_records: int = 1,
    notes: Iterable[str] = (),
) -> WaveSixTransferNoveltyLedger:
    """Build a deterministic Wave 6 transfer and novelty ledger."""

    return WaveSixTransferNoveltyLedger(
        ledger_id=ledger_id,
        records=tuple(records),
        required_supported_records=required_supported_records,
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


def _normalize_unique_enum_tuple(
    values: Iterable[E], *, label: str
) -> tuple[E, ...]:
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
