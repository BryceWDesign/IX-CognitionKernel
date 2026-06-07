"""Wave 6 independent replication protocol.

Measured system-level cognition evidence is not strong unless another reviewer can
replay the package without trusting the original system's narrative. This module
models deterministic replication steps, expected artifacts, pass/fail criteria,
and reviewer decisions. It does not execute the protocol and does not claim AGI.
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

WAVE_SIX_REPLICATION_STEP_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave6-replication-step-v1"
)
WAVE_SIX_REPLICATION_PROTOCOL_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave6-replication-protocol-v1"
)


class WaveSixReplicationStepKind(StrEnum):
    """Kinds of replication steps needed for Wave 6 review."""

    ENVIRONMENT_CHECK = "environment-check"
    ARTIFACT_FINGERPRINT_REPLAY = "artifact-fingerprint-replay"
    MASTER_LOOP_REPLAY = "master-loop-replay"
    REALITY_CORRECTION_REPLAY = "reality-correction-replay"
    FUTURE_REASONING_REPLAY = "future-reasoning-replay"
    TRANSFER_NOVELTY_REPLAY = "transfer-novelty-replay"
    FALSIFICATION_REPLAY = "falsification-replay"
    HUMAN_REVIEW_REPLAY = "human-review-replay"
    CLAIM_BOUNDARY_REPLAY = "claim-boundary-replay"


class WaveSixReplicationStepStatus(StrEnum):
    """Status for one replication step."""

    NOT_RUN = "not-run"
    PASSED = "passed"
    FAILED = "failed"
    INCONCLUSIVE = "inconclusive"
    BLOCKED = "blocked"


class WaveSixReplicationDecision(StrEnum):
    """Fail-closed protocol decision."""

    READY_FOR_REPLICATION = "ready-for-replication"
    REPLICATION_PASSED = "replication-passed"
    NEEDS_MORE_EVIDENCE = "needs-more-evidence"
    BLOCK_CLAIM = "block-claim"


WAVE_SIX_REQUIRED_REPLICATION_STEP_KINDS: tuple[WaveSixReplicationStepKind, ...] = (
    WaveSixReplicationStepKind.ENVIRONMENT_CHECK,
    WaveSixReplicationStepKind.ARTIFACT_FINGERPRINT_REPLAY,
    WaveSixReplicationStepKind.MASTER_LOOP_REPLAY,
    WaveSixReplicationStepKind.REALITY_CORRECTION_REPLAY,
    WaveSixReplicationStepKind.FUTURE_REASONING_REPLAY,
    WaveSixReplicationStepKind.TRANSFER_NOVELTY_REPLAY,
    WaveSixReplicationStepKind.FALSIFICATION_REPLAY,
    WaveSixReplicationStepKind.HUMAN_REVIEW_REPLAY,
    WaveSixReplicationStepKind.CLAIM_BOUNDARY_REPLAY,
)


@dataclass(frozen=True, slots=True)
class WaveSixReplicationStep:
    """One deterministic step in an independent replication protocol."""

    step_id: str
    kind: WaveSixReplicationStepKind
    instruction: str
    expected_artifact_ids: tuple[str, ...]
    expected_fingerprints: tuple[str, ...]
    pass_criteria: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    status: WaveSixReplicationStepStatus = WaveSixReplicationStepStatus.NOT_RUN
    reviewer_notes: tuple[str, ...] = ()
    blocks_claim: bool = False
    requires_human_review: bool = True
    allows_autonomous_execution: bool = False
    claims_agi: bool = False
    schema_version: str = WAVE_SIX_REPLICATION_STEP_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Normalize fields and enforce non-AGI, non-autonomous boundaries."""

        if not self.requires_human_review:
            raise ValueError("Replication steps must require human review.")
        if self.allows_autonomous_execution:
            raise ValueError("Replication steps must not allow autonomous execution.")
        if self.claims_agi:
            raise ValueError("Replication steps must not claim AGI.")
        object.__setattr__(self, "step_id", _require_non_empty(self.step_id, "step_id"))
        object.__setattr__(
            self,
            "instruction",
            _require_non_empty(self.instruction, "instruction"),
        )
        object.__setattr__(
            self,
            "expected_artifact_ids",
            _normalize_unique_text_tuple(
                self.expected_artifact_ids,
                label="expected_artifact_id",
            ),
        )
        object.__setattr__(
            self,
            "expected_fingerprints",
            _normalize_unique_text_tuple(
                self.expected_fingerprints,
                label="expected_fingerprint",
            ),
        )
        object.__setattr__(
            self,
            "pass_criteria",
            _normalize_unique_text_tuple(self.pass_criteria, label="pass_criterion"),
        )
        object.__setattr__(
            self,
            "evidence_ids",
            _normalize_unique_text_tuple(self.evidence_ids, label="evidence_id"),
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
        if not self.expected_artifact_ids:
            raise ValueError("Replication steps require expected artifact ids.")
        if not self.expected_fingerprints:
            raise ValueError("Replication steps require expected fingerprints.")
        if not self.pass_criteria:
            raise ValueError("Replication steps require pass criteria.")
        if not self.evidence_ids:
            raise ValueError("Replication steps require evidence ids.")
        if self.status in {
            WaveSixReplicationStepStatus.FAILED,
            WaveSixReplicationStepStatus.BLOCKED,
        } and not self.blocks_claim:
            raise ValueError(
                "Failed or blocked replication steps must block the claim."
            )
        if self.status is WaveSixReplicationStepStatus.PASSED and self.blocks_claim:
            raise ValueError("Passed replication steps cannot block the claim.")

    @property
    def passed(self) -> bool:
        """Return whether this step passed replication."""

        return self.status is WaveSixReplicationStepStatus.PASSED

    @property
    def needs_evidence(self) -> bool:
        """Return whether this step still needs more evidence."""

        return self.status in {
            WaveSixReplicationStepStatus.NOT_RUN,
            WaveSixReplicationStepStatus.INCONCLUSIVE,
        }

    @property
    def blocks_replication(self) -> bool:
        """Return whether this step blocks the replicated claim."""

        return self.blocks_claim or self.status in {
            WaveSixReplicationStepStatus.FAILED,
            WaveSixReplicationStepStatus.BLOCKED,
        }

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic payload for hashing and review."""

        return {
            "allows_autonomous_execution": self.allows_autonomous_execution,
            "blocks_claim": self.blocks_claim,
            "claims_agi": self.claims_agi,
            "evidence_ids": list(self.evidence_ids),
            "expected_artifact_ids": list(self.expected_artifact_ids),
            "expected_fingerprints": list(self.expected_fingerprints),
            "instruction": self.instruction,
            "kind": self.kind.value,
            "pass_criteria": list(self.pass_criteria),
            "requires_human_review": self.requires_human_review,
            "reviewer_notes": list(self.reviewer_notes),
            "schema_version": self.schema_version,
            "status": self.status.value,
            "step_id": self.step_id,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this replication step."""

        return _stable_sha256(self.canonical_payload())


@dataclass(frozen=True, slots=True)
class WaveSixReplicationProtocol:
    """Independent replication protocol for a Wave 6 evidence package."""

    protocol_id: str
    package_fingerprint: str
    steps: tuple[WaveSixReplicationStep, ...]
    decision: WaveSixReplicationDecision
    replication_boundary_statement: str
    required_step_kinds: tuple[WaveSixReplicationStepKind, ...] = (
        WAVE_SIX_REQUIRED_REPLICATION_STEP_KINDS
    )
    claims_agi: bool = False
    claims_production_ready: bool = False
    claims_certified: bool = False
    allows_autonomous_authority: bool = False
    notes: tuple[str, ...] = ()
    schema_version: str = WAVE_SIX_REPLICATION_PROTOCOL_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate protocol coverage, status, and claim boundary."""

        if self.claims_agi:
            raise ValueError("Replication protocols must not claim AGI.")
        if self.claims_production_ready:
            raise ValueError(
                "Replication protocols must not claim production readiness."
            )
        if self.claims_certified:
            raise ValueError("Replication protocols must not claim certification.")
        if self.allows_autonomous_authority:
            raise ValueError(
                "Replication protocols must not allow autonomous authority."
            )
        object.__setattr__(
            self,
            "protocol_id",
            _require_non_empty(self.protocol_id, "protocol_id"),
        )
        object.__setattr__(
            self,
            "package_fingerprint",
            _require_non_empty(self.package_fingerprint, "package_fingerprint"),
        )
        if not self.steps:
            raise ValueError("Replication protocols require at least one step.")
        sorted_steps = tuple(sorted(self.steps, key=lambda step: step.step_id))
        _unique_ids((step.step_id for step in sorted_steps), label="step_id")
        _unique_ids((step.kind for step in sorted_steps), label="step kind")
        object.__setattr__(self, "steps", sorted_steps)
        object.__setattr__(
            self,
            "replication_boundary_statement",
            _require_non_empty(
                self.replication_boundary_statement,
                "replication_boundary_statement",
            ),
        )
        object.__setattr__(
            self,
            "required_step_kinds",
            _normalize_unique_enum_tuple(
                self.required_step_kinds,
                label="required step kind",
            ),
        )
        object.__setattr__(
            self,
            "notes",
            _normalize_unique_text_tuple(self.notes, label="protocol note"),
        )
        object.__setattr__(
            self,
            "schema_version",
            _require_non_empty(self.schema_version, "schema_version"),
        )
        if self.decision is WaveSixReplicationDecision.REPLICATION_PASSED:
            if self.missing_step_kinds:
                raise ValueError("Passed replication requires every step kind.")
            if self.blocking_step_ids:
                raise ValueError("Passed replication cannot include blocking steps.")
            if self.needs_evidence_step_ids:
                raise ValueError("Passed replication cannot need more evidence.")
        if (
            self.decision is WaveSixReplicationDecision.BLOCK_CLAIM
            and not self.blocking_step_ids
        ):
            raise ValueError("Blocked replication requires a blocking step.")

    @property
    def step_ids(self) -> tuple[str, ...]:
        """Return replication step ids in deterministic order."""

        return tuple(step.step_id for step in self.steps)

    @property
    def present_step_kinds(self) -> tuple[WaveSixReplicationStepKind, ...]:
        """Return required step kinds represented by the protocol."""

        present = {step.kind for step in self.steps}
        return tuple(kind for kind in self.required_step_kinds if kind in present)

    @property
    def missing_step_kinds(self) -> tuple[WaveSixReplicationStepKind, ...]:
        """Return required step kinds missing from the protocol."""

        present = {step.kind for step in self.steps}
        return tuple(kind for kind in self.required_step_kinds if kind not in present)

    @property
    def passed_step_ids(self) -> tuple[str, ...]:
        """Return step ids that passed replication."""

        return tuple(step.step_id for step in self.steps if step.passed)

    @property
    def needs_evidence_step_ids(self) -> tuple[str, ...]:
        """Return step ids that need more evidence."""

        return tuple(step.step_id for step in self.steps if step.needs_evidence)

    @property
    def blocking_step_ids(self) -> tuple[str, ...]:
        """Return step ids that block the replicated claim."""

        return tuple(step.step_id for step in self.steps if step.blocks_replication)

    @property
    def ready_to_run(self) -> bool:
        """Return whether the protocol is assembled and ready to run."""

        return (
            self.decision is WaveSixReplicationDecision.READY_FOR_REPLICATION
            and not self.missing_step_kinds
            and not self.blocking_step_ids
        )

    @property
    def replication_passed(self) -> bool:
        """Return whether independent replication passed."""

        return (
            self.decision is WaveSixReplicationDecision.REPLICATION_PASSED
            and not self.missing_step_kinds
            and not self.blocking_step_ids
            and not self.needs_evidence_step_ids
        )

    @property
    def blocks_claim(self) -> bool:
        """Return whether the protocol blocks the replicated claim."""

        return (
            self.decision is WaveSixReplicationDecision.BLOCK_CLAIM
            or bool(self.blocking_step_ids)
        )

    def step_for_kind(
        self,
        kind: WaveSixReplicationStepKind,
    ) -> WaveSixReplicationStep | None:
        """Return the replication step for a kind, if present."""

        for step in self.steps:
            if step.kind is kind:
                return step
        return None

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic protocol payload for hashing and review."""

        return {
            "allows_autonomous_authority": self.allows_autonomous_authority,
            "blocking_step_ids": list(self.blocking_step_ids),
            "claims_agi": self.claims_agi,
            "claims_certified": self.claims_certified,
            "claims_production_ready": self.claims_production_ready,
            "decision": self.decision.value,
            "missing_step_kinds": [kind.value for kind in self.missing_step_kinds],
            "needs_evidence_step_ids": list(self.needs_evidence_step_ids),
            "notes": list(self.notes),
            "package_fingerprint": self.package_fingerprint,
            "passed_step_ids": list(self.passed_step_ids),
            "present_step_kinds": [kind.value for kind in self.present_step_kinds],
            "protocol_id": self.protocol_id,
            "replication_boundary_statement": self.replication_boundary_statement,
            "required_step_kinds": [kind.value for kind in self.required_step_kinds],
            "schema_version": self.schema_version,
            "steps": [step.canonical_payload() for step in self.steps],
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this protocol."""

        return _stable_sha256(self.canonical_payload())


def build_wave_six_replication_protocol(
    *,
    protocol_id: str,
    package_fingerprint: str,
    steps: Iterable[WaveSixReplicationStep],
    decision: WaveSixReplicationDecision,
    replication_boundary_statement: str,
    notes: Iterable[str] = (),
) -> WaveSixReplicationProtocol:
    """Build a deterministic Wave 6 replication protocol."""

    return WaveSixReplicationProtocol(
        protocol_id=protocol_id,
        package_fingerprint=package_fingerprint,
        steps=tuple(steps),
        decision=decision,
        replication_boundary_statement=replication_boundary_statement,
        notes=tuple(notes),
    )


def required_wave_six_replication_step_kinds() -> tuple[
    WaveSixReplicationStepKind, ...
]:
    """Return required replication step kinds for Wave 6 review."""

    return WAVE_SIX_REQUIRED_REPLICATION_STEP_KINDS


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
