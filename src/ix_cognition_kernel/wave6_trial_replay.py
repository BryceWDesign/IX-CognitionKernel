"""Wave 6 trial replay ledger.

Wave 6 evidence must remain replayable after the first run. This module records
bounded trial replays, expected evidence, observed evidence, reviewer decisions,
and claim-blocking outcomes. It does not execute trials, grant autonomy, or claim
AGI. Its job is to make run outcomes auditable and repeatable.
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

WAVE_SIX_TRIAL_REPLAY_RECORD_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave6-trial-replay-record-v1"
)
WAVE_SIX_TRIAL_REPLAY_LEDGER_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave6-trial-replay-ledger-v1"
)


class WaveSixReplayStage(StrEnum):
    """Replay stages that map back to the Wave 6 master loop."""

    PREDICTION_REPLAY = "prediction-replay"
    TRIAL_REPLAY = "trial-replay"
    OUTCOME_REPLAY = "outcome-replay"
    DELTA_REPLAY = "delta-replay"
    MEMORY_UPDATE_REPLAY = "memory-update-replay"
    TRANSFER_REPLAY = "transfer-replay"
    FALSIFICATION_REPLAY = "falsification-replay"
    HUMAN_REVIEW_REPLAY = "human-review-replay"


class WaveSixReplayOutcome(StrEnum):
    """Observed outcome for a replayed trial stage."""

    MATCHED = "matched"
    DIVERGED = "diverged"
    INCONCLUSIVE = "inconclusive"
    BLOCKED_BY_SAFETY_GATE = "blocked-by-safety-gate"
    NOT_RUN = "not-run"


class WaveSixReplayDecision(StrEnum):
    """Fail-closed decision for a replay record."""

    ACCEPT_FOR_REVIEW = "accept-for-review"
    NEEDS_MORE_EVIDENCE = "needs-more-evidence"
    RECORD_ONLY = "record-only"
    BLOCK_CLAIM = "block-claim"


WAVE_SIX_REQUIRED_REPLAY_STAGES: tuple[WaveSixReplayStage, ...] = (
    WaveSixReplayStage.PREDICTION_REPLAY,
    WaveSixReplayStage.TRIAL_REPLAY,
    WaveSixReplayStage.OUTCOME_REPLAY,
    WaveSixReplayStage.DELTA_REPLAY,
    WaveSixReplayStage.MEMORY_UPDATE_REPLAY,
    WaveSixReplayStage.TRANSFER_REPLAY,
    WaveSixReplayStage.FALSIFICATION_REPLAY,
    WaveSixReplayStage.HUMAN_REVIEW_REPLAY,
)


@dataclass(frozen=True, slots=True)
class WaveSixTrialReplayRecord:
    """One replayable Wave 6 trial-stage record."""

    replay_id: str
    stage: WaveSixReplayStage
    original_artifact_id: str
    expected_fingerprint: str
    observed_fingerprint: str
    expected_evidence_ids: tuple[str, ...]
    observed_evidence_ids: tuple[str, ...]
    outcome: WaveSixReplayOutcome
    decision: WaveSixReplayDecision
    reviewer_notes: tuple[str, ...]
    divergence_summary: str = "no divergence recorded"
    requires_human_review: bool = True
    allows_autonomous_execution: bool = False
    claims_agi: bool = False
    schema_version: str = WAVE_SIX_TRIAL_REPLAY_RECORD_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate replay identity, evidence, and claim-blocking semantics."""

        if not self.requires_human_review:
            raise ValueError("Trial replay records must require human review.")
        if self.allows_autonomous_execution:
            raise ValueError("Trial replay records must not allow autonomous execution.")
        if self.claims_agi:
            raise ValueError("Trial replay records must not claim AGI.")
        object.__setattr__(
            self,
            "replay_id",
            _require_non_empty(self.replay_id, "replay_id"),
        )
        object.__setattr__(
            self,
            "original_artifact_id",
            _require_non_empty(self.original_artifact_id, "original_artifact_id"),
        )
        object.__setattr__(
            self,
            "expected_fingerprint",
            _require_non_empty(self.expected_fingerprint, "expected_fingerprint"),
        )
        object.__setattr__(
            self,
            "observed_fingerprint",
            _require_non_empty(self.observed_fingerprint, "observed_fingerprint"),
        )
        object.__setattr__(
            self,
            "expected_evidence_ids",
            _normalize_unique_text_tuple(
                self.expected_evidence_ids,
                label="expected_evidence_id",
            ),
        )
        object.__setattr__(
            self,
            "observed_evidence_ids",
            _normalize_unique_text_tuple(
                self.observed_evidence_ids,
                label="observed_evidence_id",
            ),
        )
        object.__setattr__(
            self,
            "reviewer_notes",
            _normalize_unique_text_tuple(self.reviewer_notes, label="reviewer_note"),
        )
        object.__setattr__(
            self,
            "divergence_summary",
            _require_non_empty(self.divergence_summary, "divergence_summary"),
        )
        object.__setattr__(
            self,
            "schema_version",
            _require_non_empty(self.schema_version, "schema_version"),
        )
        if not self.expected_evidence_ids:
            raise ValueError("Trial replay records require expected evidence ids.")
        if not self.observed_evidence_ids:
            raise ValueError("Trial replay records require observed evidence ids.")
        if not self.reviewer_notes:
            raise ValueError("Trial replay records require reviewer notes.")
        if self.outcome is WaveSixReplayOutcome.MATCHED:
            if self.expected_fingerprint != self.observed_fingerprint:
                raise ValueError("Matched replay requires identical fingerprints.")
            if self.decision is not WaveSixReplayDecision.ACCEPT_FOR_REVIEW:
                raise ValueError("Matched replay must be accepted for review.")
        if self.outcome in {
            WaveSixReplayOutcome.DIVERGED,
            WaveSixReplayOutcome.BLOCKED_BY_SAFETY_GATE,
        }:
            if self.decision is not WaveSixReplayDecision.BLOCK_CLAIM:
                raise ValueError("Diverged or safety-blocked replay must block claim.")

    @property
    def replay_matched(self) -> bool:
        """Return whether the replay matched the expected artifact."""

        return (
            self.outcome is WaveSixReplayOutcome.MATCHED
            and self.expected_fingerprint == self.observed_fingerprint
            and self.decision is WaveSixReplayDecision.ACCEPT_FOR_REVIEW
        )

    @property
    def needs_more_evidence(self) -> bool:
        """Return whether this replay still needs more evidence."""

        return self.decision is WaveSixReplayDecision.NEEDS_MORE_EVIDENCE

    @property
    def blocks_claim(self) -> bool:
        """Return whether this replay blocks Wave 6 interpretation."""

        return self.decision is WaveSixReplayDecision.BLOCK_CLAIM or self.outcome in {
            WaveSixReplayOutcome.DIVERGED,
            WaveSixReplayOutcome.BLOCKED_BY_SAFETY_GATE,
        }

    @property
    def combined_evidence_ids(self) -> tuple[str, ...]:
        """Return expected and observed evidence ids without duplicates."""

        combined: list[str] = []
        seen: set[str] = set()
        for evidence_id in (*self.expected_evidence_ids, *self.observed_evidence_ids):
            if evidence_id not in seen:
                combined.append(evidence_id)
                seen.add(evidence_id)
        return tuple(combined)

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic payload for hashing and review."""

        return {
            "allows_autonomous_execution": self.allows_autonomous_execution,
            "claims_agi": self.claims_agi,
            "decision": self.decision.value,
            "divergence_summary": self.divergence_summary,
            "expected_evidence_ids": list(self.expected_evidence_ids),
            "expected_fingerprint": self.expected_fingerprint,
            "observed_evidence_ids": list(self.observed_evidence_ids),
            "observed_fingerprint": self.observed_fingerprint,
            "original_artifact_id": self.original_artifact_id,
            "outcome": self.outcome.value,
            "replay_id": self.replay_id,
            "requires_human_review": self.requires_human_review,
            "reviewer_notes": list(self.reviewer_notes),
            "schema_version": self.schema_version,
            "stage": self.stage.value,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this replay record."""

        return _stable_sha256(self.canonical_payload())


@dataclass(frozen=True, slots=True)
class WaveSixTrialReplayLedger:
    """Ledger of replayed Wave 6 trial-stage records."""

    ledger_id: str
    records: tuple[WaveSixTrialReplayRecord, ...]
    required_stages: tuple[WaveSixReplayStage, ...] = WAVE_SIX_REQUIRED_REPLAY_STAGES
    require_all_stages_matched: bool = True
    claims_agi: bool = False
    notes: tuple[str, ...] = ()
    schema_version: str = WAVE_SIX_TRIAL_REPLAY_LEDGER_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate ledger identity, uniqueness, and no-AGI boundary."""

        if self.claims_agi:
            raise ValueError("Trial replay ledgers must not claim AGI.")
        object.__setattr__(
            self,
            "ledger_id",
            _require_non_empty(self.ledger_id, "ledger_id"),
        )
        if not self.records:
            raise ValueError("Trial replay ledgers require at least one record.")
        sorted_records = tuple(sorted(self.records, key=lambda record: record.replay_id))
        _unique_ids((record.replay_id for record in sorted_records), label="replay_id")
        _unique_ids((record.stage for record in sorted_records), label="replay stage")
        object.__setattr__(self, "records", sorted_records)
        object.__setattr__(
            self,
            "required_stages",
            _normalize_unique_enum_tuple(self.required_stages, label="required stage"),
        )
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
    def replay_ids(self) -> tuple[str, ...]:
        """Return replay ids in deterministic order."""

        return tuple(record.replay_id for record in self.records)

    @property
    def present_stages(self) -> tuple[WaveSixReplayStage, ...]:
        """Return required replay stages represented in the ledger."""

        present = {record.stage for record in self.records}
        return tuple(stage for stage in self.required_stages if stage in present)

    @property
    def missing_stages(self) -> tuple[WaveSixReplayStage, ...]:
        """Return required replay stages missing from the ledger."""

        present = {record.stage for record in self.records}
        return tuple(stage for stage in self.required_stages if stage not in present)

    @property
    def matched_replay_ids(self) -> tuple[str, ...]:
        """Return replay ids that matched and were accepted for review."""

        return tuple(record.replay_id for record in self.records if record.replay_matched)

    @property
    def blocking_replay_ids(self) -> tuple[str, ...]:
        """Return replay ids that block Wave 6 interpretation."""

        return tuple(record.replay_id for record in self.records if record.blocks_claim)

    @property
    def needs_more_evidence_replay_ids(self) -> tuple[str, ...]:
        """Return replay ids that still need more evidence."""

        return tuple(
            record.replay_id for record in self.records if record.needs_more_evidence
        )

    @property
    def matched_required_stages(self) -> tuple[WaveSixReplayStage, ...]:
        """Return required replay stages with accepted matched records."""

        matched = {record.stage for record in self.records if record.replay_matched}
        return tuple(stage for stage in self.required_stages if stage in matched)

    @property
    def missing_matched_required_stages(self) -> tuple[WaveSixReplayStage, ...]:
        """Return required stages that lack accepted matched replay records."""

        matched = set(self.matched_required_stages)
        return tuple(stage for stage in self.required_stages if stage not in matched)

    @property
    def ready_for_replay_review(self) -> bool:
        """Return whether the replay ledger can support Wave 6 review."""

        if self.missing_stages or self.blocking_replay_ids:
            return False
        if self.needs_more_evidence_replay_ids:
            return False
        if self.require_all_stages_matched and self.missing_matched_required_stages:
            return False
        return True

    def record_for_stage(
        self,
        stage: WaveSixReplayStage,
    ) -> WaveSixTrialReplayRecord | None:
        """Return the replay record for a stage, if present."""

        for record in self.records:
            if record.stage is stage:
                return record
        return None

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic ledger payload for hashing and review."""

        return {
            "blocking_replay_ids": list(self.blocking_replay_ids),
            "claims_agi": self.claims_agi,
            "ledger_id": self.ledger_id,
            "matched_replay_ids": list(self.matched_replay_ids),
            "matched_required_stages": [
                stage.value for stage in self.matched_required_stages
            ],
            "missing_matched_required_stages": [
                stage.value for stage in self.missing_matched_required_stages
            ],
            "missing_stages": [stage.value for stage in self.missing_stages],
            "needs_more_evidence_replay_ids": list(
                self.needs_more_evidence_replay_ids
            ),
            "notes": list(self.notes),
            "present_stages": [stage.value for stage in self.present_stages],
            "ready_for_replay_review": self.ready_for_replay_review,
            "records": [record.canonical_payload() for record in self.records],
            "require_all_stages_matched": self.require_all_stages_matched,
            "required_stages": [stage.value for stage in self.required_stages],
            "schema_version": self.schema_version,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this replay ledger."""

        return _stable_sha256(self.canonical_payload())


def build_wave_six_trial_replay_ledger(
    *,
    ledger_id: str,
    records: Iterable[WaveSixTrialReplayRecord],
    require_all_stages_matched: bool = True,
    notes: Iterable[str] = (),
) -> WaveSixTrialReplayLedger:
    """Build a deterministic Wave 6 trial replay ledger."""

    return WaveSixTrialReplayLedger(
        ledger_id=ledger_id,
        records=tuple(records),
        require_all_stages_matched=require_all_stages_matched,
        notes=tuple(notes),
    )


def required_wave_six_replay_stages() -> tuple[WaveSixReplayStage, ...]:
    """Return replay stages required for Wave 6 review."""

    return WAVE_SIX_REQUIRED_REPLAY_STAGES


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
