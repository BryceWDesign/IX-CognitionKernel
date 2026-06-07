"""Wave 6 future-reasoning change proofs.

Wave 6 must prove more than feedback logging. This module records before/after
reasoning snapshots and requires a measured-reality correction reference before a
future-reasoning change can count. It stays deliberately decoupled from donor
runtime imports so the master loop remains clean, simple, and testable.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, TypeVar

T = TypeVar("T")

WAVE_SIX_REASONING_SNAPSHOT_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave6-reasoning-snapshot-v1"
)
WAVE_SIX_REASONING_CHANGE_PROOF_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave6-reasoning-change-proof-v1"
)
WAVE_SIX_REASONING_CHANGE_LEDGER_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave6-reasoning-change-ledger-v1"
)


class WaveSixReasoningChangeKind(StrEnum):
    """Kinds of future reasoning change allowed in Wave 6 evidence."""

    CAUSAL_ASSUMPTION_REWEIGHTED = "causal-assumption-reweighted"
    PREDICTION_RULE_REVISED = "prediction-rule-revised"
    MEMORY_QUARANTINED = "memory-quarantined"
    TRANSFER_RULE_REVISED = "transfer-rule-revised"
    REFUSAL_BOUNDARY_STRENGTHENED = "refusal-boundary-strengthened"


class WaveSixReasoningProofDecision(StrEnum):
    """Fail-closed decisions for future-reasoning change proofs."""

    RECORD_ONLY = "record-only"
    ACCEPT_FOR_WAVE_SIX_REVIEW = "accept-for-wave-six-review"
    NEEDS_MORE_EVIDENCE = "needs-more-evidence"
    BLOCK_CLAIM = "block-claim"


@dataclass(frozen=True, slots=True)
class WaveSixReasoningSnapshot:
    """A deterministic snapshot of reasoning before or after correction."""

    snapshot_id: str
    task_context: str
    reasoning_summary: str
    active_assumption_ids: tuple[str, ...]
    memory_ids: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    created_by_stage: str
    schema_version: str = WAVE_SIX_REASONING_SNAPSHOT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Normalize snapshot fields and reject empty review inputs."""

        object.__setattr__(
            self,
            "snapshot_id",
            _require_non_empty(self.snapshot_id, "snapshot_id"),
        )
        object.__setattr__(
            self,
            "task_context",
            _require_non_empty(self.task_context, "task_context"),
        )
        object.__setattr__(
            self,
            "reasoning_summary",
            _require_non_empty(self.reasoning_summary, "reasoning_summary"),
        )
        object.__setattr__(
            self,
            "active_assumption_ids",
            _normalize_unique_text_tuple(
                self.active_assumption_ids, label="active_assumption_id"
            ),
        )
        object.__setattr__(
            self,
            "memory_ids",
            _normalize_unique_text_tuple(self.memory_ids, label="memory_id"),
        )
        object.__setattr__(
            self,
            "evidence_ids",
            _normalize_unique_text_tuple(self.evidence_ids, label="evidence_id"),
        )
        object.__setattr__(
            self,
            "created_by_stage",
            _require_non_empty(self.created_by_stage, "created_by_stage"),
        )
        object.__setattr__(
            self,
            "schema_version",
            _require_non_empty(self.schema_version, "schema_version"),
        )
        if not self.active_assumption_ids:
            raise ValueError("Reasoning snapshots require active assumptions.")
        if not self.memory_ids:
            raise ValueError("Reasoning snapshots require memory identifiers.")
        if not self.evidence_ids:
            raise ValueError("Reasoning snapshots require evidence ids.")

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic snapshot payload for hashing."""

        return {
            "active_assumption_ids": list(self.active_assumption_ids),
            "created_by_stage": self.created_by_stage,
            "evidence_ids": list(self.evidence_ids),
            "memory_ids": list(self.memory_ids),
            "reasoning_summary": self.reasoning_summary,
            "schema_version": self.schema_version,
            "snapshot_id": self.snapshot_id,
            "task_context": self.task_context,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this snapshot."""

        return _stable_sha256(self.canonical_payload())


@dataclass(frozen=True, slots=True)
class WaveSixFutureReasoningChangeProof:
    """Proof that measured reality changed future reasoning."""

    proof_id: str
    before_snapshot: WaveSixReasoningSnapshot
    after_snapshot: WaveSixReasoningSnapshot
    reality_correction_record_ids: tuple[str, ...]
    changed_assumption_ids: tuple[str, ...]
    changed_memory_ids: tuple[str, ...]
    change_kind: WaveSixReasoningChangeKind
    expected_future_behavior: str
    counterfactual_old_behavior: str
    evidence_ids: tuple[str, ...]
    decision: WaveSixReasoningProofDecision = (
        WaveSixReasoningProofDecision.NEEDS_MORE_EVIDENCE
    )
    requires_human_review: bool = True
    allows_autonomous_execution: bool = False
    claims_agi: bool = False
    schema_version: str = WAVE_SIX_REASONING_CHANGE_PROOF_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate a future-reasoning change proof without overclaiming."""

        if not self.requires_human_review:
            raise ValueError("Reasoning-change proofs must require human review.")
        if self.allows_autonomous_execution:
            raise ValueError(
                "Reasoning-change proofs must not allow autonomous execution."
            )
        if self.claims_agi:
            raise ValueError("Reasoning-change proofs must not claim AGI.")
        object.__setattr__(
            self,
            "proof_id",
            _require_non_empty(self.proof_id, "proof_id"),
        )
        object.__setattr__(
            self,
            "reality_correction_record_ids",
            _normalize_unique_text_tuple(
                self.reality_correction_record_ids,
                label="reality_correction_record_id",
            ),
        )
        object.__setattr__(
            self,
            "changed_assumption_ids",
            _normalize_unique_text_tuple(
                self.changed_assumption_ids, label="changed_assumption_id"
            ),
        )
        object.__setattr__(
            self,
            "changed_memory_ids",
            _normalize_unique_text_tuple(
                self.changed_memory_ids, label="changed_memory_id"
            ),
        )
        object.__setattr__(
            self,
            "expected_future_behavior",
            _require_non_empty(
                self.expected_future_behavior,
                "expected_future_behavior",
            ),
        )
        object.__setattr__(
            self,
            "counterfactual_old_behavior",
            _require_non_empty(
                self.counterfactual_old_behavior,
                "counterfactual_old_behavior",
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
        if self.before_snapshot.fingerprint() == self.after_snapshot.fingerprint():
            raise ValueError("Reasoning-change proofs require different snapshots.")
        if not self.reality_correction_record_ids:
            raise ValueError(
                "Reasoning-change proofs require reality correction records."
            )
        if not self.changed_assumption_ids and not self.changed_memory_ids:
            raise ValueError(
                "Reasoning-change proofs require changed assumptions or memories."
            )
        if not self.evidence_ids:
            raise ValueError("Reasoning-change proofs require evidence ids.")
        if self.expected_future_behavior == self.counterfactual_old_behavior:
            raise ValueError(
                "Expected future behavior must differ from old behavior."
            )

    @property
    def snapshot_fingerprints_differ(self) -> bool:
        """Return whether before and after reasoning snapshots differ."""

        return self.before_snapshot.fingerprint() != self.after_snapshot.fingerprint()

    @property
    def reality_correction_bound(self) -> bool:
        """Return whether the proof references measured-reality correction."""

        return bool(self.reality_correction_record_ids)

    @property
    def behavior_change_bound(self) -> bool:
        """Return whether the proof names a concrete future behavior change."""

        return self.expected_future_behavior != self.counterfactual_old_behavior

    @property
    def evidence_bound(self) -> bool:
        """Return whether the proof has direct evidence and snapshot evidence."""

        return bool(
            self.evidence_ids
            and self.before_snapshot.evidence_ids
            and self.after_snapshot.evidence_ids
        )

    @property
    def blocks_claim(self) -> bool:
        """Return whether this proof blocks capability interpretation."""

        return self.decision is WaveSixReasoningProofDecision.BLOCK_CLAIM

    @property
    def accepted_for_review(self) -> bool:
        """Return whether this proof is accepted for Wave 6 review."""

        return self.decision is WaveSixReasoningProofDecision.ACCEPT_FOR_WAVE_SIX_REVIEW

    @property
    def proves_future_reasoning_changed(self) -> bool:
        """Return whether this proof meets the Wave 6 change criterion."""

        return (
            self.snapshot_fingerprints_differ
            and self.reality_correction_bound
            and self.behavior_change_bound
            and self.evidence_bound
            and not self.blocks_claim
            and bool(self.changed_assumption_ids or self.changed_memory_ids)
        )

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic proof payload for hashing and review."""

        return {
            "after_snapshot_fingerprint": self.after_snapshot.fingerprint(),
            "allows_autonomous_execution": self.allows_autonomous_execution,
            "before_snapshot_fingerprint": self.before_snapshot.fingerprint(),
            "change_kind": self.change_kind.value,
            "changed_assumption_ids": list(self.changed_assumption_ids),
            "changed_memory_ids": list(self.changed_memory_ids),
            "claims_agi": self.claims_agi,
            "counterfactual_old_behavior": self.counterfactual_old_behavior,
            "decision": self.decision.value,
            "evidence_ids": list(self.evidence_ids),
            "expected_future_behavior": self.expected_future_behavior,
            "proof_id": self.proof_id,
            "reality_correction_record_ids": list(
                self.reality_correction_record_ids
            ),
            "requires_human_review": self.requires_human_review,
            "schema_version": self.schema_version,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this proof."""

        return _stable_sha256(self.canonical_payload())


@dataclass(frozen=True, slots=True)
class WaveSixFutureReasoningProofLedger:
    """Ledger of future-reasoning change proofs."""

    ledger_id: str
    proofs: tuple[WaveSixFutureReasoningChangeProof, ...]
    required_accepted_proofs: int = 1
    notes: tuple[str, ...] = ()
    schema_version: str = WAVE_SIX_REASONING_CHANGE_LEDGER_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate ledger identity, proof uniqueness, and threshold."""

        object.__setattr__(
            self,
            "ledger_id",
            _require_non_empty(self.ledger_id, "ledger_id"),
        )
        if not self.proofs:
            raise ValueError("Future-reasoning ledgers require at least one proof.")
        sorted_proofs = tuple(sorted(self.proofs, key=lambda proof: proof.proof_id))
        _unique_ids((proof.proof_id for proof in sorted_proofs), label="proof_id")
        object.__setattr__(self, "proofs", sorted_proofs)
        if self.required_accepted_proofs < 1:
            raise ValueError("required_accepted_proofs must be at least 1.")
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
    def proof_ids(self) -> tuple[str, ...]:
        """Return proof ids in deterministic order."""

        return tuple(proof.proof_id for proof in self.proofs)

    @property
    def blocked_proof_ids(self) -> tuple[str, ...]:
        """Return proofs that block capability interpretation."""

        return tuple(proof.proof_id for proof in self.proofs if proof.blocks_claim)

    @property
    def accepted_proof_ids(self) -> tuple[str, ...]:
        """Return accepted proofs that demonstrate future-reasoning change."""

        return tuple(
            proof.proof_id
            for proof in self.proofs
            if proof.accepted_for_review and proof.proves_future_reasoning_changed
        )

    @property
    def has_required_accepted_proofs(self) -> bool:
        """Return whether the ledger meets the accepted-proof threshold."""

        return len(self.accepted_proof_ids) >= self.required_accepted_proofs

    @property
    def ready_for_wave_six_review(self) -> bool:
        """Return whether the ledger can support Wave 6 review."""

        return self.has_required_accepted_proofs and not self.blocked_proof_ids

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic ledger payload for hashing and review."""

        return {
            "accepted_proof_ids": list(self.accepted_proof_ids),
            "blocked_proof_ids": list(self.blocked_proof_ids),
            "has_required_accepted_proofs": self.has_required_accepted_proofs,
            "ledger_id": self.ledger_id,
            "notes": list(self.notes),
            "proofs": [proof.canonical_payload() for proof in self.proofs],
            "ready_for_wave_six_review": self.ready_for_wave_six_review,
            "required_accepted_proofs": self.required_accepted_proofs,
            "schema_version": self.schema_version,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this ledger."""

        return _stable_sha256(self.canonical_payload())


def build_wave_six_future_reasoning_proof_ledger(
    *,
    ledger_id: str,
    proofs: Iterable[WaveSixFutureReasoningChangeProof],
    required_accepted_proofs: int = 1,
    notes: Iterable[str] = (),
) -> WaveSixFutureReasoningProofLedger:
    """Build a deterministic future-reasoning proof ledger."""

    return WaveSixFutureReasoningProofLedger(
        ledger_id=ledger_id,
        proofs=tuple(proofs),
        required_accepted_proofs=required_accepted_proofs,
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
