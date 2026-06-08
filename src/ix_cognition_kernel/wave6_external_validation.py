"""Wave 6 external validation gate.

Independent challenge, replication, and replay evidence must converge before a
Wave 6 package can be treated as externally validation-ready. This module joins
those three review surfaces without executing them, granting authority, or
claiming AGI. It is intentionally small: each upstream ledger remains the source
of truth for its own evidence, while this gate records the combined verdict.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, TypeVar

from ix_cognition_kernel.wave6_challenge_suite import WaveSixChallengeSuite
from ix_cognition_kernel.wave6_replication_protocol import WaveSixReplicationProtocol
from ix_cognition_kernel.wave6_trial_replay import WaveSixTrialReplayLedger

T = TypeVar("T")
E = TypeVar("E", bound=StrEnum)

WAVE_SIX_EXTERNAL_VALIDATION_GATE_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave6-external-validation-gate-v1"
)
WAVE_SIX_EXTERNAL_VALIDATION_SUMMARY_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave6-external-validation-summary-v1"
)


class WaveSixExternalValidationSurface(StrEnum):
    """External validation surfaces that must converge."""

    INDEPENDENT_CHALLENGE_SUITE = "independent-challenge-suite"
    INDEPENDENT_REPLICATION_PROTOCOL = "independent-replication-protocol"
    TRIAL_REPLAY_LEDGER = "trial-replay-ledger"


class WaveSixExternalValidationBlocker(StrEnum):
    """Reasons the combined external validation gate cannot advance."""

    CHALLENGE_SUITE_NOT_READY = "challenge-suite-not-ready"
    REPLICATION_NOT_PASSED = "replication-not-passed"
    TRIAL_REPLAY_NOT_READY = "trial-replay-not-ready"
    CHALLENGE_CASE_BLOCKED = "challenge-case-blocked"
    REPLICATION_STEP_BLOCKED = "replication-step-blocked"
    TRIAL_REPLAY_BLOCKED = "trial-replay-blocked"
    OVERCLAIM_PRESENT = "overclaim-present"


class WaveSixExternalValidationStatus(StrEnum):
    """Fail-closed external validation status."""

    READY_FOR_EXTERNAL_VALIDATION_REVIEW = "ready-for-external-validation-review"
    NEEDS_MORE_EVIDENCE = "needs-more-evidence"
    BLOCKED = "blocked"


@dataclass(frozen=True, slots=True)
class WaveSixExternalValidationSummary:
    """Compact summary for one external validation surface."""

    summary_id: str
    surface: WaveSixExternalValidationSurface
    artifact_fingerprint: str
    ready: bool
    blocking_ids: tuple[str, ...]
    needs_more_evidence_ids: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    reviewer_question: str
    schema_version: str = WAVE_SIX_EXTERNAL_VALIDATION_SUMMARY_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Normalize summary fields and evidence references."""

        object.__setattr__(
            self,
            "summary_id",
            _require_non_empty(self.summary_id, "summary_id"),
        )
        object.__setattr__(
            self,
            "artifact_fingerprint",
            _require_non_empty(self.artifact_fingerprint, "artifact_fingerprint"),
        )
        object.__setattr__(
            self,
            "blocking_ids",
            _normalize_unique_text_tuple(self.blocking_ids, label="blocking_id"),
        )
        object.__setattr__(
            self,
            "needs_more_evidence_ids",
            _normalize_unique_text_tuple(
                self.needs_more_evidence_ids,
                label="needs_more_evidence_id",
            ),
        )
        object.__setattr__(
            self,
            "evidence_ids",
            _normalize_unique_text_tuple(self.evidence_ids, label="evidence_id"),
        )
        object.__setattr__(
            self,
            "reviewer_question",
            _require_non_empty(self.reviewer_question, "reviewer_question"),
        )
        object.__setattr__(
            self,
            "schema_version",
            _require_non_empty(self.schema_version, "schema_version"),
        )
        if not self.evidence_ids:
            raise ValueError("External validation summaries require evidence ids.")
        if self.ready and self.blocking_ids:
            raise ValueError("Ready validation summaries cannot include blockers.")
        if self.ready and self.needs_more_evidence_ids:
            raise ValueError("Ready validation summaries cannot need more evidence.")

    @property
    def blocked(self) -> bool:
        """Return whether this summary blocks external validation."""

        return bool(self.blocking_ids)

    @property
    def needs_more_evidence(self) -> bool:
        """Return whether this summary still needs more evidence."""

        return bool(self.needs_more_evidence_ids) or not self.ready

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic summary payload for hashing and review."""

        return {
            "artifact_fingerprint": self.artifact_fingerprint,
            "blocking_ids": list(self.blocking_ids),
            "evidence_ids": list(self.evidence_ids),
            "needs_more_evidence_ids": list(self.needs_more_evidence_ids),
            "ready": self.ready,
            "reviewer_question": self.reviewer_question,
            "schema_version": self.schema_version,
            "summary_id": self.summary_id,
            "surface": self.surface.value,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this summary."""

        return _stable_sha256(self.canonical_payload())


@dataclass(frozen=True, slots=True)
class WaveSixExternalValidationGate:
    """Combined external validation gate for Wave 6 evidence."""

    gate_id: str
    challenge_suite: WaveSixChallengeSuite
    replication_protocol: WaveSixReplicationProtocol
    trial_replay_ledger: WaveSixTrialReplayLedger
    validation_boundary_statement: str
    claims_agi: bool = False
    claims_production_ready: bool = False
    claims_certified: bool = False
    allows_autonomous_authority: bool = False
    notes: tuple[str, ...] = ()
    schema_version: str = WAVE_SIX_EXTERNAL_VALIDATION_GATE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate gate identity and hard claim boundaries."""

        object.__setattr__(self, "gate_id", _require_non_empty(self.gate_id, "gate_id"))
        object.__setattr__(
            self,
            "validation_boundary_statement",
            _require_non_empty(
                self.validation_boundary_statement,
                "validation_boundary_statement",
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
    def overclaim_present(self) -> bool:
        """Return whether this gate violates the claim boundary."""

        return (
            self.claims_agi
            or self.claims_production_ready
            or self.claims_certified
            or self.allows_autonomous_authority
        )

    @property
    def summaries(self) -> tuple[WaveSixExternalValidationSummary, ...]:
        """Return validation summaries for each external surface."""

        return (
            WaveSixExternalValidationSummary(
                summary_id="summary-independent-challenge-suite",
                surface=WaveSixExternalValidationSurface.INDEPENDENT_CHALLENGE_SUITE,
                artifact_fingerprint=self.challenge_suite.fingerprint(),
                ready=self.challenge_suite.ready_for_external_challenge_review,
                blocking_ids=self.challenge_suite.blocking_case_ids,
                needs_more_evidence_ids=(
                    self.challenge_suite.needs_more_evidence_case_ids
                    or tuple(
                        kind.value
                        for kind in self.challenge_suite.missing_passed_required_kinds
                    )
                ),
                evidence_ids=(f"challenge-suite:{self.challenge_suite.suite_id}",),
                reviewer_question=(
                    "Did independent challenge pressure include novelty, transfer, "
                    "negative controls, falsification, and human authority?"
                ),
            ),
            WaveSixExternalValidationSummary(
                summary_id="summary-independent-replication-protocol",
                surface=(
                    WaveSixExternalValidationSurface.INDEPENDENT_REPLICATION_PROTOCOL
                ),
                artifact_fingerprint=self.replication_protocol.fingerprint(),
                ready=self.replication_protocol.replication_passed,
                blocking_ids=self.replication_protocol.blocking_step_ids,
                needs_more_evidence_ids=(
                    self.replication_protocol.needs_evidence_step_ids
                    or tuple(
                        kind.value
                        for kind in self.replication_protocol.missing_step_kinds
                    )
                ),
                evidence_ids=(
                    f"replication-protocol:{self.replication_protocol.protocol_id}",
                ),
                reviewer_question=(
                    "Can an independent reviewer reproduce the package without "
                    "trusting the Kernel narrative?"
                ),
            ),
            WaveSixExternalValidationSummary(
                summary_id="summary-trial-replay-ledger",
                surface=WaveSixExternalValidationSurface.TRIAL_REPLAY_LEDGER,
                artifact_fingerprint=self.trial_replay_ledger.fingerprint(),
                ready=self.trial_replay_ledger.ready_for_replay_review,
                blocking_ids=self.trial_replay_ledger.blocking_replay_ids,
                needs_more_evidence_ids=(
                    self.trial_replay_ledger.needs_more_evidence_replay_ids
                    or tuple(
                        stage.value for stage in self.trial_replay_ledger.missing_stages
                    )
                    or tuple(
                        stage.value
                        for stage in (
                            self.trial_replay_ledger.missing_matched_required_stages
                        )
                    )
                ),
                evidence_ids=(
                    f"trial-replay-ledger:{self.trial_replay_ledger.ledger_id}",
                ),
                reviewer_question=(
                    "Do replay records match the expected artifacts without "
                    "divergence or safety-gate blocks?"
                ),
            ),
        )

    @property
    def blocking_summary_ids(self) -> tuple[str, ...]:
        """Return validation summaries that block interpretation."""

        return tuple(summary.summary_id for summary in self.summaries if summary.blocked)

    @property
    def needs_more_evidence_summary_ids(self) -> tuple[str, ...]:
        """Return validation summaries that still need evidence."""

        return tuple(
            summary.summary_id
            for summary in self.summaries
            if summary.needs_more_evidence and not summary.blocked
        )

    @property
    def blockers(self) -> tuple[WaveSixExternalValidationBlocker, ...]:
        """Return deterministic blockers for the external validation gate."""

        blockers: list[WaveSixExternalValidationBlocker] = []
        if self.overclaim_present:
            blockers.append(WaveSixExternalValidationBlocker.OVERCLAIM_PRESENT)
        if self.challenge_suite.blocking_case_ids:
            blockers.append(WaveSixExternalValidationBlocker.CHALLENGE_CASE_BLOCKED)
        if self.replication_protocol.blocking_step_ids:
            blockers.append(WaveSixExternalValidationBlocker.REPLICATION_STEP_BLOCKED)
        if self.trial_replay_ledger.blocking_replay_ids:
            blockers.append(WaveSixExternalValidationBlocker.TRIAL_REPLAY_BLOCKED)
        if not self.challenge_suite.ready_for_external_challenge_review:
            blockers.append(WaveSixExternalValidationBlocker.CHALLENGE_SUITE_NOT_READY)
        if not self.replication_protocol.replication_passed:
            blockers.append(WaveSixExternalValidationBlocker.REPLICATION_NOT_PASSED)
        if not self.trial_replay_ledger.ready_for_replay_review:
            blockers.append(WaveSixExternalValidationBlocker.TRIAL_REPLAY_NOT_READY)
        return tuple(blockers)

    @property
    def status(self) -> WaveSixExternalValidationStatus:
        """Return fail-closed external validation status."""

        if self.overclaim_present or self.blocking_summary_ids:
            return WaveSixExternalValidationStatus.BLOCKED
        if self.blockers or self.needs_more_evidence_summary_ids:
            return WaveSixExternalValidationStatus.NEEDS_MORE_EVIDENCE
        return WaveSixExternalValidationStatus.READY_FOR_EXTERNAL_VALIDATION_REVIEW

    @property
    def ready_for_external_validation_review(self) -> bool:
        """Return whether the gate is ready for external validation review."""

        return (
            self.status
            is WaveSixExternalValidationStatus.READY_FOR_EXTERNAL_VALIDATION_REVIEW
        )

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic gate payload for hashing and review."""

        return {
            "allows_autonomous_authority": self.allows_autonomous_authority,
            "blockers": [blocker.value for blocker in self.blockers],
            "blocking_summary_ids": list(self.blocking_summary_ids),
            "challenge_suite_fingerprint": self.challenge_suite.fingerprint(),
            "claims_agi": self.claims_agi,
            "claims_certified": self.claims_certified,
            "claims_production_ready": self.claims_production_ready,
            "gate_id": self.gate_id,
            "needs_more_evidence_summary_ids": list(
                self.needs_more_evidence_summary_ids
            ),
            "notes": list(self.notes),
            "replication_protocol_fingerprint": (
                self.replication_protocol.fingerprint()
            ),
            "schema_version": self.schema_version,
            "status": self.status.value,
            "summaries": [summary.canonical_payload() for summary in self.summaries],
            "trial_replay_ledger_fingerprint": self.trial_replay_ledger.fingerprint(),
            "validation_boundary_statement": self.validation_boundary_statement,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this validation gate."""

        return _stable_sha256(self.canonical_payload())


def build_wave_six_external_validation_gate(
    *,
    gate_id: str,
    challenge_suite: WaveSixChallengeSuite,
    replication_protocol: WaveSixReplicationProtocol,
    trial_replay_ledger: WaveSixTrialReplayLedger,
    validation_boundary_statement: str,
    notes: Iterable[str] = (),
) -> WaveSixExternalValidationGate:
    """Build a deterministic Wave 6 external validation gate."""

    return WaveSixExternalValidationGate(
        gate_id=gate_id,
        challenge_suite=challenge_suite,
        replication_protocol=replication_protocol,
        trial_replay_ledger=trial_replay_ledger,
        validation_boundary_statement=validation_boundary_statement,
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
