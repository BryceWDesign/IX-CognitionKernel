"""Wave 6 BlackFox execution-review handoff packaging.

IX-CognitionKernel should not execute trials directly. When a bounded Wave 6
package eventually needs controlled CI, sandboxed verification, or policy-gated
trial execution, the Kernel may prepare a BlackFox review packet. This module
keeps that boundary explicit: it packages metadata for BlackFox review, but it
never dispatches execution, grants autonomous authority, opens network egress,
claims AGI, or marks the candidate as ready by itself.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Protocol

from ix_cognition_kernel.wave6_contracts import (
    WaveSixArtifactKind,
    WaveSixCapabilityArea,
    WaveSixContractArtifact,
    WaveSixDecisionState,
    WaveSixLoopStage,
    WaveSixSourceSystem,
)
from ix_cognition_kernel.wave6_donor_evidence_intake import (
    WaveSixDonorEvidenceReceipt,
)

WAVE_SIX_BLACKFOX_HANDOFF_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave6-blackfox-execution-handoff-v1"
)
WAVE_SIX_BLACKFOX_COMMAND_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave6-blackfox-command-v1"
)
WAVE_SIX_BLACKFOX_HANDOFF_ENGINE_ID = "wave6-blackfox-handoff-engine"

_FORBIDDEN_COMMAND_FRAGMENTS: tuple[str, ...] = (
    "\n",
    "\r",
    ";",
    "&&",
    "||",
    "|",
    ">",
    "<",
    "`",
    "$(",
    "rm -rf",
    "del /",
    "format ",
    "shutdown",
    "curl ",
    "wget ",
    "scp ",
    "ssh ",
)


class BlackFoxGateLike(Protocol):
    """Structural gate surface needed by BlackFox handoff packaging."""

    @property
    def attempt(self) -> str:
        """Return the gated candidate attempt id."""

    @property
    def ready_for_bounded_review_inputs(self) -> bool:
        """Return whether the candidate gate allows review-input staging."""

    @property
    def blockers(self) -> tuple[Any, ...]:
        """Return candidate gate blockers."""

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic candidate gate payload when available."""

    @property
    def human_authority_id(self) -> str:
        """Return the human authority id recorded by the gate."""

    @property
    def independent_reviewer_id(self) -> str:
        """Return the independent reviewer id recorded by the gate."""

    def fingerprint(self) -> str:
        """Return deterministic candidate gate fingerprint."""


class WaveSixBlackFoxHandoffStatus(StrEnum):
    """Fail-closed status for a BlackFox execution-review handoff."""

    BLOCKED_BY_CANDIDATE_GATE = "blocked-by-candidate-gate"
    READY_FOR_BLACKFOX_REVIEW_PACKET = "ready-for-blackfox-review-packet"


class WaveSixBlackFoxHandoffDecision(StrEnum):
    """Decision emitted by the BlackFox handoff package."""

    HOLD_FOR_CANDIDATE_GATE = "hold-for-candidate-gate"
    PREPARE_REVIEW_PACKET_ONLY = "prepare-review-packet-only"


class WaveSixBlackFoxHandoffBlocker(StrEnum):
    """Reasons a BlackFox handoff cannot enter review-packet staging."""

    CANDIDATE_GATE_NOT_READY = "candidate-gate-not-ready"
    CANDIDATE_GATE_HAS_BLOCKERS = "candidate-gate-has-blockers"
    HUMAN_AUTHORITY_MISSING = "human-authority-missing"
    INDEPENDENT_REVIEW_MISSING = "independent-review-missing"
    FALSIFICATION_PRESSURE_MISSING = "falsification-pressure-missing"


@dataclass(frozen=True, slots=True)
class WaveSixBlackFoxVerificationCommand:
    """One verification command requested as metadata for BlackFox review."""

    command_id: str
    command: str
    purpose: str
    expected_evidence_id: str
    requires_human_approval: bool = True
    metadata_only: bool = True
    schema_version: str = WAVE_SIX_BLACKFOX_COMMAND_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate a command as bounded review metadata, not execution."""

        object.__setattr__(
            self,
            "command_id",
            _require_non_empty(self.command_id, "command_id"),
        )
        object.__setattr__(self, "command", _safe_command_text(self.command))
        object.__setattr__(
            self,
            "purpose",
            _require_non_empty(self.purpose, "purpose"),
        )
        object.__setattr__(
            self,
            "expected_evidence_id",
            _require_non_empty(
                self.expected_evidence_id,
                "expected_evidence_id",
            ),
        )
        object.__setattr__(
            self,
            "schema_version",
            _require_non_empty(self.schema_version, "schema_version"),
        )
        if not self.requires_human_approval:
            raise ValueError("BlackFox verification commands require human approval.")
        if not self.metadata_only:
            raise ValueError("BlackFox verification commands must be metadata-only.")

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic command payload for review and hashing."""

        return {
            "command": self.command,
            "command_id": self.command_id,
            "expected_evidence_id": self.expected_evidence_id,
            "metadata_only": self.metadata_only,
            "purpose": self.purpose,
            "requires_human_approval": self.requires_human_approval,
            "schema_version": self.schema_version,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this command."""

        return _stable_sha256(self.canonical_payload())


@dataclass(frozen=True, slots=True)
class WaveSixBlackFoxExecutionHandoff:
    """Metadata-only package for BlackFox-controlled execution review."""

    handoff_id: str
    candidate_gate: BlackFoxGateLike
    blackfox_receipt: WaveSixDonorEvidenceReceipt
    verification_commands: tuple[WaveSixBlackFoxVerificationCommand, ...]
    policy_ids: tuple[str, ...]
    purpose: str
    generated_by_engine_id: str = WAVE_SIX_BLACKFOX_HANDOFF_ENGINE_ID
    workspace_isolation_required: bool = True
    network_egress_allowed: bool = False
    destructive_actions_allowed: bool = False
    dispatch_allowed: bool = False
    metadata_only: bool = True
    requires_human_approval: bool = True
    allows_autonomous_execution: bool = False
    claims_agi: bool = False
    claims_production_ready: bool = False
    claims_certified: bool = False
    self_validated: bool = False
    notes: tuple[str, ...] = ()
    schema_version: str = WAVE_SIX_BLACKFOX_HANDOFF_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate BlackFox source identity and authority boundaries."""

        object.__setattr__(
            self,
            "handoff_id",
            _require_non_empty(self.handoff_id, "handoff_id"),
        )
        object.__setattr__(
            self,
            "verification_commands",
            _normalize_unique_commands(self.verification_commands),
        )
        object.__setattr__(
            self,
            "policy_ids",
            _normalize_unique_text_tuple(self.policy_ids, label="policy_id"),
        )
        object.__setattr__(
            self,
            "purpose",
            _require_non_empty(self.purpose, "purpose"),
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
            _normalize_unique_text_tuple(self.notes, label="handoff note"),
        )
        object.__setattr__(
            self,
            "schema_version",
            _require_non_empty(self.schema_version, "schema_version"),
        )
        if self.blackfox_receipt.source_system is not WaveSixSourceSystem.IX_BLACKFOX:
            raise ValueError("BlackFox handoff requires an IX-BlackFox receipt.")
        if not self.policy_ids:
            raise ValueError("BlackFox handoffs require at least one policy id.")
        if not self.workspace_isolation_required:
            raise ValueError("BlackFox handoffs require workspace isolation.")
        if self.network_egress_allowed:
            raise ValueError("BlackFox handoffs must deny network egress.")
        if self.destructive_actions_allowed:
            raise ValueError("BlackFox handoffs must not allow destructive actions.")
        if self.dispatch_allowed:
            raise ValueError("BlackFox handoffs must not dispatch execution.")
        if not self.metadata_only:
            raise ValueError("BlackFox handoffs must remain metadata-only.")
        if not self.requires_human_approval:
            raise ValueError("BlackFox handoffs require human approval.")
        if self.allows_autonomous_execution:
            raise ValueError("BlackFox handoffs must not allow autonomous execution.")
        if self.claims_agi:
            raise ValueError("BlackFox handoffs must not claim AGI.")
        if self.claims_production_ready:
            raise ValueError("BlackFox handoffs must not claim production readiness.")
        if self.claims_certified:
            raise ValueError("BlackFox handoffs must not claim certification.")
        if self.self_validated:
            raise ValueError("BlackFox handoffs must not self-validate.")

    @property
    def attempt(self) -> str:
        """Return the candidate attempt represented by this handoff."""

        return self.candidate_gate.attempt

    @property
    def command_ids(self) -> tuple[str, ...]:
        """Return verification command ids in deterministic order."""

        return tuple(command.command_id for command in self.verification_commands)

    @property
    def expected_command_evidence_ids(self) -> tuple[str, ...]:
        """Return expected evidence ids from requested verification commands."""

        return tuple(command.expected_evidence_id for command in self.verification_commands)

    @property
    def blockers(self) -> tuple[WaveSixBlackFoxHandoffBlocker, ...]:
        """Return blockers that prevent BlackFox review-packet staging."""

        blockers: list[WaveSixBlackFoxHandoffBlocker] = []
        if not self.candidate_gate.ready_for_bounded_review_inputs:
            blockers.append(WaveSixBlackFoxHandoffBlocker.CANDIDATE_GATE_NOT_READY)
        if self.candidate_gate.blockers:
            blockers.append(WaveSixBlackFoxHandoffBlocker.CANDIDATE_GATE_HAS_BLOCKERS)
        if not self.candidate_gate.human_authority_id.strip():
            blockers.append(WaveSixBlackFoxHandoffBlocker.HUMAN_AUTHORITY_MISSING)
        if not self.candidate_gate.independent_reviewer_id.strip():
            blockers.append(WaveSixBlackFoxHandoffBlocker.INDEPENDENT_REVIEW_MISSING)
        if not _gate_falsification_probe_ids(self.candidate_gate):
            blockers.append(WaveSixBlackFoxHandoffBlocker.FALSIFICATION_PRESSURE_MISSING)
        return tuple(blockers)

    @property
    def status(self) -> WaveSixBlackFoxHandoffStatus:
        """Return fail-closed BlackFox handoff status."""

        if self.blockers:
            return WaveSixBlackFoxHandoffStatus.BLOCKED_BY_CANDIDATE_GATE
        return WaveSixBlackFoxHandoffStatus.READY_FOR_BLACKFOX_REVIEW_PACKET

    @property
    def decision(self) -> WaveSixBlackFoxHandoffDecision:
        """Return BlackFox handoff decision."""

        if self.blockers:
            return WaveSixBlackFoxHandoffDecision.HOLD_FOR_CANDIDATE_GATE
        return WaveSixBlackFoxHandoffDecision.PREPARE_REVIEW_PACKET_ONLY

    @property
    def ready_for_blackfox_review_packet(self) -> bool:
        """Return whether this package may become a BlackFox review packet."""

        return (
            self.status
            is WaveSixBlackFoxHandoffStatus.READY_FOR_BLACKFOX_REVIEW_PACKET
        )

    @property
    def represented_evidence_ids(self) -> tuple[str, ...]:
        """Return evidence ids represented by the handoff package."""

        return _unique_preserving_order(
            (
                self.blackfox_receipt.evidence_id,
                *_gate_evidence_ids(self.candidate_gate),
                *self.expected_command_evidence_ids,
            )
        )

    def to_contract_artifact(self) -> WaveSixContractArtifact:
        """Convert this handoff into a bounded Wave 6 contract artifact."""

        return WaveSixContractArtifact(
            artifact_id=f"blackfox-handoff-artifact-{self.handoff_id}",
            kind=WaveSixArtifactKind.HUMAN_REVIEW_DOCKET,
            capability_area=WaveSixCapabilityArea.HUMAN_AUTHORITY_PRESERVATION,
            source_system=WaveSixSourceSystem.IX_BLACKFOX,
            summary=(
                "Metadata-only BlackFox execution-review handoff; dispatch is "
                "not allowed and human approval remains required."
            ),
            loop_stages=(
                WaveSixLoopStage.TRIAL,
                WaveSixLoopStage.FALSIFICATION,
                WaveSixLoopStage.HUMAN_REVIEW,
            ),
            evidence_ids=self.represented_evidence_ids,
            produced_by_engine_id=WAVE_SIX_BLACKFOX_HANDOFF_ENGINE_ID,
            decision=WaveSixDecisionState.NEEDS_MORE_EVIDENCE,
        )

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic BlackFox handoff payload for review."""

        return {
            "allows_autonomous_execution": self.allows_autonomous_execution,
            "attempt": self.attempt,
            "blackfox_receipt_fingerprint": self.blackfox_receipt.fingerprint(),
            "blockers": [blocker.value for blocker in self.blockers],
            "candidate_gate_fingerprint": self.candidate_gate.fingerprint(),
            "claims_agi": self.claims_agi,
            "claims_certified": self.claims_certified,
            "claims_production_ready": self.claims_production_ready,
            "command_ids": list(self.command_ids),
            "decision": self.decision.value,
            "destructive_actions_allowed": self.destructive_actions_allowed,
            "dispatch_allowed": self.dispatch_allowed,
            "expected_command_evidence_ids": list(self.expected_command_evidence_ids),
            "generated_by_engine_id": self.generated_by_engine_id,
            "handoff_id": self.handoff_id,
            "metadata_only": self.metadata_only,
            "network_egress_allowed": self.network_egress_allowed,
            "notes": list(self.notes),
            "policy_ids": list(self.policy_ids),
            "purpose": self.purpose,
            "ready_for_blackfox_review_packet": self.ready_for_blackfox_review_packet,
            "represented_evidence_ids": list(self.represented_evidence_ids),
            "requires_human_approval": self.requires_human_approval,
            "schema_version": self.schema_version,
            "self_validated": self.self_validated,
            "status": self.status.value,
            "verification_commands": [
                command.canonical_payload() for command in self.verification_commands
            ],
            "workspace_isolation_required": self.workspace_isolation_required,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this handoff."""

        return _stable_sha256(self.canonical_payload())


def _gate_payload(gate: BlackFoxGateLike) -> Mapping[str, Any]:
    """Return a candidate gate payload when the gate exposes one."""

    payload_method = getattr(gate, "canonical_payload", None)
    if callable(payload_method):
        payload = payload_method()
        if isinstance(payload, Mapping):
            return payload
    return {}


def _gate_evidence_ids(gate: BlackFoxGateLike) -> tuple[str, ...]:
    """Return evidence ids from a gate attribute or payload."""

    direct_values = getattr(gate, "evidence_ids", None)
    if isinstance(direct_values, tuple):
        return tuple(str(value) for value in direct_values)
    payload = _gate_payload(gate)
    values = payload.get("evidence_ids", ())
    if not isinstance(values, list | tuple):
        return ()
    return tuple(str(value) for value in values)


def _gate_falsification_probe_ids(gate: BlackFoxGateLike) -> tuple[str, ...]:
    """Return IX falsification-probe ids from a gate attribute or payload."""

    direct_values = getattr(gate, "ix_falsification_probe_ids", None)
    if isinstance(direct_values, tuple):
        return tuple(str(value) for value in direct_values)
    payload = _gate_payload(gate)
    values = payload.get("ix_falsification_probe_ids", ())
    if not isinstance(values, list | tuple):
        return ()
    return tuple(str(value) for value in values)


def build_wave_six_blackfox_execution_handoff(
    *,
    handoff_id: str,
    candidate_gate: BlackFoxGateLike,
    blackfox_receipt: WaveSixDonorEvidenceReceipt,
    verification_commands: Iterable[WaveSixBlackFoxVerificationCommand],
    policy_ids: Iterable[str],
    purpose: str,
    notes: Iterable[str] = (),
) -> WaveSixBlackFoxExecutionHandoff:
    """Build a metadata-only BlackFox execution-review handoff."""

    return WaveSixBlackFoxExecutionHandoff(
        handoff_id=handoff_id,
        candidate_gate=candidate_gate,
        blackfox_receipt=blackfox_receipt,
        verification_commands=tuple(verification_commands),
        policy_ids=tuple(policy_ids),
        purpose=purpose,
        notes=tuple(notes),
    )


def _safe_command_text(command: str) -> str:
    """Return a safe command string for metadata-only BlackFox review."""

    normalized = _require_non_empty(command, "command")
    normalized_casefold = normalized.casefold()
    for fragment in _FORBIDDEN_COMMAND_FRAGMENTS:
        if fragment in normalized_casefold:
            raise ValueError("BlackFox verification command contains unsafe syntax.")
    return normalized


def _normalize_unique_commands(
    commands: Iterable[WaveSixBlackFoxVerificationCommand],
) -> tuple[WaveSixBlackFoxVerificationCommand, ...]:
    """Return commands while rejecting duplicates and empty command sets."""

    normalized = tuple(commands)
    if not normalized:
        raise ValueError("BlackFox handoffs require verification commands.")
    command_ids = tuple(command.command_id for command in normalized)
    evidence_ids = tuple(command.expected_evidence_id for command in normalized)
    _require_unique(command_ids, label="command_id")
    _require_unique(evidence_ids, label="expected_evidence_id")
    return normalized


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


def _unique_preserving_order(values: Iterable[str]) -> tuple[str, ...]:
    """Return unique text values while preserving first-seen order."""

    seen: set[str] = set()
    unique: list[str] = []
    for value in values:
        if value not in seen:
            unique.append(value)
            seen.add(value)
    return tuple(unique)


def _require_unique(values: Iterable[str], *, label: str) -> None:
    """Reject duplicate text values."""

    seen: set[str] = set()
    for value in values:
        if value in seen:
            raise ValueError(f"Duplicate {label} detected: {value}")
        seen.add(value)


def _require_non_empty(value: str, label: str) -> str:
    """Return stripped text or raise when empty."""

    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{label} must not be empty.")
    return normalized


def _stable_sha256(payload: Mapping[str, Any]) -> str:
    """Return deterministic SHA-256 over a canonical JSON payload."""

    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return hashlib.sha256(encoded).hexdigest()
