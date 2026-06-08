"""Wave 6 falsification pressure ledger.

Wave 6 evidence must be allowed to fail. This module records explicit probes,
negative controls, observed results, and claim-blocking outcomes so measured
system-level cognition cannot promote itself by ignoring contradiction evidence.
It remains a deterministic review layer and does not execute donor repos.
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

WAVE_SIX_FALSIFICATION_PROBE_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave6-falsification-probe-v1"
)
WAVE_SIX_FALSIFICATION_RESULT_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave6-falsification-result-v1"
)
WAVE_SIX_FALSIFICATION_LEDGER_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave6-falsification-ledger-v1"
)


class WaveSixFalsificationProbeKind(StrEnum):
    """Kinds of probes used to try to break a Wave 6 interpretation."""

    NEGATIVE_CONTROL = "negative-control"
    CONTRADICTION_PROBE = "contradiction-probe"
    TRANSFER_COUNTEREXAMPLE = "transfer-counterexample"
    NOVELTY_REVERSAL = "novelty-reversal"
    SAFETY_GATE_PROBE = "safety-gate-probe"
    REGRESSION_PROBE = "regression-probe"


class WaveSixFalsificationOutcome(StrEnum):
    """Observed outcomes from falsification probes."""

    SURVIVED = "survived"
    FALSIFIED = "falsified"
    INCONCLUSIVE = "inconclusive"
    BLOCKED_BY_SAFETY_GATE = "blocked-by-safety-gate"


class WaveSixFalsificationDecision(StrEnum):
    """Fail-closed decisions for falsification results."""

    ACCEPT_FOR_WAVE_SIX_REVIEW = "accept-for-wave-six-review"
    NEEDS_MORE_EVIDENCE = "needs-more-evidence"
    RECORD_ONLY = "record-only"
    BLOCK_CLAIM = "block-claim"


@dataclass(frozen=True, slots=True)
class WaveSixFalsificationProbe:
    """A deterministic probe that attempts to falsify a bounded claim."""

    probe_id: str
    probe_kind: WaveSixFalsificationProbeKind
    claim_under_test: str
    falsification_question: str
    expected_failure_mode: str
    method_summary: str
    evidence_ids: tuple[str, ...]
    requires_human_review: bool = True
    allows_autonomous_execution: bool = False
    claims_agi: bool = False
    schema_version: str = WAVE_SIX_FALSIFICATION_PROBE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate that the probe is evidence-bound and non-autonomous."""

        if not self.requires_human_review:
            raise ValueError("Falsification probes must require human review.")
        if self.allows_autonomous_execution:
            raise ValueError(
                "Falsification probes must not allow autonomous execution."
            )
        if self.claims_agi:
            raise ValueError("Falsification probes must not claim AGI.")
        object.__setattr__(
            self,
            "probe_id",
            _require_non_empty(self.probe_id, "probe_id"),
        )
        object.__setattr__(
            self,
            "claim_under_test",
            _require_non_empty(self.claim_under_test, "claim_under_test"),
        )
        object.__setattr__(
            self,
            "falsification_question",
            _require_non_empty(
                self.falsification_question,
                "falsification_question",
            ),
        )
        object.__setattr__(
            self,
            "expected_failure_mode",
            _require_non_empty(
                self.expected_failure_mode,
                "expected_failure_mode",
            ),
        )
        object.__setattr__(
            self,
            "method_summary",
            _require_non_empty(self.method_summary, "method_summary"),
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
            raise ValueError("Falsification probes require evidence ids.")

    @property
    def is_negative_control(self) -> bool:
        """Return whether this probe is a negative control."""

        return self.probe_kind is WaveSixFalsificationProbeKind.NEGATIVE_CONTROL

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic payload for review and hashing."""

        return {
            "allows_autonomous_execution": self.allows_autonomous_execution,
            "claim_under_test": self.claim_under_test,
            "claims_agi": self.claims_agi,
            "evidence_ids": list(self.evidence_ids),
            "expected_failure_mode": self.expected_failure_mode,
            "falsification_question": self.falsification_question,
            "method_summary": self.method_summary,
            "probe_id": self.probe_id,
            "probe_kind": self.probe_kind.value,
            "requires_human_review": self.requires_human_review,
            "schema_version": self.schema_version,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this probe."""

        return _stable_sha256(self.canonical_payload())


@dataclass(frozen=True, slots=True)
class WaveSixFalsificationResult:
    """Observed result for one falsification probe."""

    result_id: str
    probe: WaveSixFalsificationProbe
    observed_result_summary: str
    outcome: WaveSixFalsificationOutcome
    decision: WaveSixFalsificationDecision
    evidence_ids: tuple[str, ...]
    affected_claim_ids: tuple[str, ...]
    contradiction_evidence_ids: tuple[str, ...] = ()
    reviewer_notes: tuple[str, ...] = ()
    requires_human_review: bool = True
    allows_autonomous_execution: bool = False
    claims_agi: bool = False
    schema_version: str = WAVE_SIX_FALSIFICATION_RESULT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate observed result and fail-closed claim handling."""

        if not self.requires_human_review:
            raise ValueError("Falsification results must require human review.")
        if self.allows_autonomous_execution:
            raise ValueError(
                "Falsification results must not allow autonomous execution."
            )
        if self.claims_agi:
            raise ValueError("Falsification results must not claim AGI.")
        object.__setattr__(
            self,
            "result_id",
            _require_non_empty(self.result_id, "result_id"),
        )
        object.__setattr__(
            self,
            "observed_result_summary",
            _require_non_empty(
                self.observed_result_summary,
                "observed_result_summary",
            ),
        )
        object.__setattr__(
            self,
            "evidence_ids",
            _normalize_unique_text_tuple(self.evidence_ids, label="evidence_id"),
        )
        object.__setattr__(
            self,
            "affected_claim_ids",
            _normalize_unique_text_tuple(
                self.affected_claim_ids,
                label="affected_claim_id",
            ),
        )
        object.__setattr__(
            self,
            "contradiction_evidence_ids",
            _normalize_unique_text_tuple(
                self.contradiction_evidence_ids,
                label="contradiction_evidence_id",
            ),
        )
        object.__setattr__(
            self,
            "reviewer_notes",
            _normalize_unique_text_tuple(self.reviewer_notes, label="reviewer_note"),
        )
        object.__setattr__(
            self,
            "schema_version",
            _require_non_empty(self.schema_version, "schema_version"),
        )
        if not self.evidence_ids:
            raise ValueError("Falsification results require evidence ids.")
        if not self.affected_claim_ids:
            raise ValueError("Falsification results require affected claim ids.")
        if self.outcome is WaveSixFalsificationOutcome.FALSIFIED:
            if not self.contradiction_evidence_ids:
                raise ValueError("Falsified results require contradiction evidence.")
            if self.decision is not WaveSixFalsificationDecision.BLOCK_CLAIM:
                raise ValueError("Falsified results must block the claim.")
        if (
            self.outcome is WaveSixFalsificationOutcome.BLOCKED_BY_SAFETY_GATE
            and self.decision is not WaveSixFalsificationDecision.BLOCK_CLAIM
        ):
            raise ValueError("Safety-gate-blocked results must block the claim.")

    @property
    def evidence_bound(self) -> bool:
        """Return whether probe and result evidence are both present."""

        return bool(self.probe.evidence_ids and self.evidence_ids)

    @property
    def survived_probe(self) -> bool:
        """Return whether the claim survived this probe."""

        return self.outcome is WaveSixFalsificationOutcome.SURVIVED

    @property
    def inconclusive(self) -> bool:
        """Return whether this result is inconclusive."""

        return self.outcome is WaveSixFalsificationOutcome.INCONCLUSIVE

    @property
    def blocks_claim(self) -> bool:
        """Return whether this result blocks capability interpretation."""

        return (
            self.decision is WaveSixFalsificationDecision.BLOCK_CLAIM
            or self.outcome
            in {
                WaveSixFalsificationOutcome.FALSIFIED,
                WaveSixFalsificationOutcome.BLOCKED_BY_SAFETY_GATE,
            }
        )

    @property
    def accepted_for_review(self) -> bool:
        """Return whether this result can support Wave 6 review."""

        return self.decision is WaveSixFalsificationDecision.ACCEPT_FOR_WAVE_SIX_REVIEW

    @property
    def supports_bounded_claim_survival(self) -> bool:
        """Return whether this result supports bounded claim survival."""

        return (
            self.survived_probe
            and self.accepted_for_review
            and self.evidence_bound
            and not self.blocks_claim
        )

    @property
    def combined_evidence_ids(self) -> tuple[str, ...]:
        """Return probe, result, and contradiction evidence without duplicates."""

        combined: list[str] = []
        seen: set[str] = set()
        for evidence_id in (
            *self.probe.evidence_ids,
            *self.evidence_ids,
            *self.contradiction_evidence_ids,
        ):
            if evidence_id not in seen:
                combined.append(evidence_id)
                seen.add(evidence_id)
        return tuple(combined)

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic payload for review and hashing."""

        return {
            "affected_claim_ids": list(self.affected_claim_ids),
            "allows_autonomous_execution": self.allows_autonomous_execution,
            "claims_agi": self.claims_agi,
            "contradiction_evidence_ids": list(self.contradiction_evidence_ids),
            "decision": self.decision.value,
            "evidence_ids": list(self.evidence_ids),
            "observed_result_summary": self.observed_result_summary,
            "outcome": self.outcome.value,
            "probe_fingerprint": self.probe.fingerprint(),
            "requires_human_review": self.requires_human_review,
            "result_id": self.result_id,
            "reviewer_notes": list(self.reviewer_notes),
            "schema_version": self.schema_version,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this result."""

        return _stable_sha256(self.canonical_payload())


@dataclass(frozen=True, slots=True)
class WaveSixFalsificationLedger:
    """Ledger of falsification results for Wave 6 review."""

    ledger_id: str
    results: tuple[WaveSixFalsificationResult, ...]
    required_survived_results: int = 1
    require_negative_control: bool = True
    notes: tuple[str, ...] = ()
    schema_version: str = WAVE_SIX_FALSIFICATION_LEDGER_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate ledger identity, result uniqueness, and thresholds."""

        object.__setattr__(
            self,
            "ledger_id",
            _require_non_empty(self.ledger_id, "ledger_id"),
        )
        if not self.results:
            raise ValueError("Falsification ledgers require at least one result.")
        sorted_results = tuple(
            sorted(self.results, key=lambda result: result.result_id)
        )
        _unique_ids((result.result_id for result in sorted_results), label="result_id")
        object.__setattr__(self, "results", sorted_results)
        if self.required_survived_results < 1:
            raise ValueError("required_survived_results must be at least 1.")
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
    def result_ids(self) -> tuple[str, ...]:
        """Return result ids in deterministic order."""

        return tuple(result.result_id for result in self.results)

    @property
    def survived_result_ids(self) -> tuple[str, ...]:
        """Return results that survived falsification pressure."""

        return tuple(
            result.result_id
            for result in self.results
            if result.supports_bounded_claim_survival
        )

    @property
    def blocking_result_ids(self) -> tuple[str, ...]:
        """Return results that block capability interpretation."""

        return tuple(result.result_id for result in self.results if result.blocks_claim)

    @property
    def inconclusive_result_ids(self) -> tuple[str, ...]:
        """Return inconclusive result ids."""

        return tuple(result.result_id for result in self.results if result.inconclusive)

    @property
    def negative_control_result_ids(self) -> tuple[str, ...]:
        """Return result ids produced from negative-control probes."""

        return tuple(
            result.result_id
            for result in self.results
            if result.probe.is_negative_control
        )

    @property
    def survived_negative_control_result_ids(self) -> tuple[str, ...]:
        """Return negative-control results that survived and were accepted."""

        return tuple(
            result.result_id
            for result in self.results
            if result.probe.is_negative_control
            and result.supports_bounded_claim_survival
        )

    @property
    def has_required_negative_control(self) -> bool:
        """Return whether required negative-control pressure is satisfied."""

        if not self.require_negative_control:
            return True
        return bool(self.survived_negative_control_result_ids)

    @property
    def has_required_survival(self) -> bool:
        """Return whether enough probes survived for bounded review."""

        return len(self.survived_result_ids) >= self.required_survived_results

    @property
    def ready_for_wave_six_review(self) -> bool:
        """Return whether falsification evidence can support Wave 6 review."""

        return (
            self.has_required_survival
            and self.has_required_negative_control
            and not self.blocking_result_ids
        )

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic ledger payload for hashing and review."""

        return {
            "blocking_result_ids": list(self.blocking_result_ids),
            "has_required_negative_control": self.has_required_negative_control,
            "has_required_survival": self.has_required_survival,
            "inconclusive_result_ids": list(self.inconclusive_result_ids),
            "ledger_id": self.ledger_id,
            "negative_control_result_ids": list(self.negative_control_result_ids),
            "notes": list(self.notes),
            "ready_for_wave_six_review": self.ready_for_wave_six_review,
            "require_negative_control": self.require_negative_control,
            "required_survived_results": self.required_survived_results,
            "results": [result.canonical_payload() for result in self.results],
            "schema_version": self.schema_version,
            "survived_negative_control_result_ids": list(
                self.survived_negative_control_result_ids
            ),
            "survived_result_ids": list(self.survived_result_ids),
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this ledger."""

        return _stable_sha256(self.canonical_payload())


def build_wave_six_falsification_ledger(
    *,
    ledger_id: str,
    results: Iterable[WaveSixFalsificationResult],
    required_survived_results: int = 1,
    require_negative_control: bool = True,
    notes: Iterable[str] = (),
) -> WaveSixFalsificationLedger:
    """Build a deterministic Wave 6 falsification ledger."""

    return WaveSixFalsificationLedger(
        ledger_id=ledger_id,
        results=tuple(results),
        required_survived_results=required_survived_results,
        require_negative_control=require_negative_control,
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
