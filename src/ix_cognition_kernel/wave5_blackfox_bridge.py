"""Wave 5 IX-BlackFox Wave 10 compatibility bridge records.

IX-CognitionKernel Wave 5 must be able to hand evidence-bound cognition outputs
into IX-BlackFox-style engineering governance without pretending that a handoff
is execution approval. This module records policy gates, sandbox/workspace
boundaries, receipt-chain coverage, CI verification, evidence bundles, rollback
visibility, and human authorization requirements compatible with the inspected
IX-BlackFox Wave 10 control-plane doctrine.

The bridge treats model output and cognition output as untrusted input. It may
make a handoff reviewable for BlackFox governance, but it never grants execution
authority, never self-approves, and never turns BlackFox compatibility into an
AGI, production, certification, or independent-validation claim.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, TypeVar

from ix_cognition_kernel.wave5_contracts import (
    WAVE_FIVE_REQUIRED_CLAIM_BOUNDARIES,
    WaveFiveArtifactDecision,
    WaveFiveArtifactKind,
    WaveFiveArtifactRef,
    WaveFiveAuthorityState,
    WaveFiveCapabilityArea,
    WaveFiveClaimBoundary,
    WaveFiveSourceSystem,
    WaveFiveValidationStatus,
)

T = TypeVar("T")
E = TypeVar("E", bound=StrEnum)

WAVE_FIVE_BLACKFOX_GATE_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave5-blackfox-gate-v1"
)
WAVE_FIVE_BLACKFOX_RECEIPT_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave5-blackfox-receipt-v1"
)
WAVE_FIVE_BLACKFOX_HANDOFF_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave5-blackfox-handoff-v1"
)


class WaveFiveBlackFoxGateKind(StrEnum):
    """IX-BlackFox governance gates required for Wave 5 handoff review."""

    MODEL_OUTPUT_UNTRUSTED = "model-output-untrusted"
    POLICY_GATE = "policy-gate"
    ISOLATED_WORKSPACE = "isolated-workspace"
    EGRESS_CONTROL = "egress-control"
    RECEIPT_CHAIN = "receipt-chain"
    CI_VERIFICATION = "ci-verification"
    EVIDENCE_BUNDLE = "evidence-bundle"
    HUMAN_AUTHORIZATION = "human-authorization"
    ROLLBACK_PATH = "rollback-path"
    NO_AUTONOMOUS_EXECUTION = "no-autonomous-execution"


class WaveFiveBlackFoxGateResult(StrEnum):
    """Observed result for a BlackFox compatibility gate."""

    PASSED = "passed"
    PASSED_WITH_LIMITS = "passed-with-limits"
    NEEDS_MORE_EVIDENCE = "needs-more-evidence"
    FAILED = "failed"


class WaveFiveBlackFoxReceiptKind(StrEnum):
    """Receipt classes expected by a BlackFox-style evidence chain."""

    PROPOSED_CHANGE = "proposed-change"
    POLICY_DECISION = "policy-decision"
    SANDBOX_WORKSPACE = "sandbox-workspace"
    EGRESS_DECISION = "egress-decision"
    TEST_RUN = "test-run"
    CI_VERIFICATION = "ci-verification"
    EVIDENCE_BUNDLE = "evidence-bundle"
    HUMAN_REVIEW = "human-review"
    ROLLBACK_RECORD = "rollback-record"


class WaveFiveBlackFoxAuthorityMode(StrEnum):
    """Authority mode attached to a BlackFox-compatible handoff."""

    REVIEW_ONLY = "review-only"
    HUMAN_APPROVAL_REQUIRED = "human-approval-required"
    HUMAN_APPROVED_REVIEW_ONLY = "human-approved-review-only"
    BLOCKED = "blocked"


class WaveFiveBlackFoxHandoffState(StrEnum):
    """Review state of a Kernel-to-BlackFox compatibility handoff."""

    INTERNAL_BRIDGE_READY = "internal-bridge-ready"
    READY_FOR_BLACKFOX_REVIEW = "ready-for-blackfox-review"
    UNDER_BLACKFOX_REVIEW = "under-blackfox-review"
    BLACKFOX_ACCEPTED_WITH_BOUNDARIES = "blackfox-accepted-with-boundaries"
    BLOCKED_BY_GOVERNANCE_GAP = "blocked-by-governance-gap"


REQUIRED_BLACKFOX_GATE_KINDS: tuple[WaveFiveBlackFoxGateKind, ...] = (
    WaveFiveBlackFoxGateKind.MODEL_OUTPUT_UNTRUSTED,
    WaveFiveBlackFoxGateKind.POLICY_GATE,
    WaveFiveBlackFoxGateKind.ISOLATED_WORKSPACE,
    WaveFiveBlackFoxGateKind.EGRESS_CONTROL,
    WaveFiveBlackFoxGateKind.RECEIPT_CHAIN,
    WaveFiveBlackFoxGateKind.CI_VERIFICATION,
    WaveFiveBlackFoxGateKind.EVIDENCE_BUNDLE,
    WaveFiveBlackFoxGateKind.HUMAN_AUTHORIZATION,
    WaveFiveBlackFoxGateKind.ROLLBACK_PATH,
    WaveFiveBlackFoxGateKind.NO_AUTONOMOUS_EXECUTION,
)

REQUIRED_BLACKFOX_RECEIPT_KINDS: tuple[WaveFiveBlackFoxReceiptKind, ...] = (
    WaveFiveBlackFoxReceiptKind.PROPOSED_CHANGE,
    WaveFiveBlackFoxReceiptKind.POLICY_DECISION,
    WaveFiveBlackFoxReceiptKind.SANDBOX_WORKSPACE,
    WaveFiveBlackFoxReceiptKind.EGRESS_DECISION,
    WaveFiveBlackFoxReceiptKind.TEST_RUN,
    WaveFiveBlackFoxReceiptKind.CI_VERIFICATION,
    WaveFiveBlackFoxReceiptKind.EVIDENCE_BUNDLE,
    WaveFiveBlackFoxReceiptKind.HUMAN_REVIEW,
    WaveFiveBlackFoxReceiptKind.ROLLBACK_RECORD,
)

SAFE_BLACKFOX_AUTHORITY_MODES: tuple[WaveFiveBlackFoxAuthorityMode, ...] = (
    WaveFiveBlackFoxAuthorityMode.REVIEW_ONLY,
    WaveFiveBlackFoxAuthorityMode.HUMAN_APPROVAL_REQUIRED,
    WaveFiveBlackFoxAuthorityMode.HUMAN_APPROVED_REVIEW_ONLY,
)

BLACKFOX_ACCEPTANCE_SOURCE_SYSTEMS: tuple[WaveFiveSourceSystem, ...] = (
    WaveFiveSourceSystem.IX_BLACKFOX,
    WaveFiveSourceSystem.HUMAN_REVIEW,
)


@dataclass(frozen=True, slots=True)
class WaveFiveBlackFoxGate:
    """One BlackFox-style governance gate for a Kernel handoff."""

    gate_id: str
    gate_kind: WaveFiveBlackFoxGateKind
    result: WaveFiveBlackFoxGateResult
    description: str
    evidence_ids: tuple[str, ...]
    blocking: bool = True
    schema_version: str = WAVE_FIVE_BLACKFOX_GATE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate gate identity and evidence binding."""

        object.__setattr__(self, "gate_id", _text(self.gate_id, "gate_id"))
        object.__setattr__(self, "description", _text(self.description, "description"))
        object.__setattr__(
            self, "evidence_ids", _unique_text(self.evidence_ids, label="evidence_id")
        )
        if not self.evidence_ids:
            raise ValueError("BlackFox gates require evidence ids.")
        object.__setattr__(
            self, "schema_version", _text(self.schema_version, "schema_version")
        )

    @property
    def gate_key(self) -> str:
        """Return deterministic gate key."""

        return self.gate_id

    @property
    def passed_with_boundaries(self) -> bool:
        """Return whether this gate passed while preserving limitations."""

        return self.result in {
            WaveFiveBlackFoxGateResult.PASSED,
            WaveFiveBlackFoxGateResult.PASSED_WITH_LIMITS,
        }

    @property
    def blocks_wave_five_progress(self) -> bool:
        """Return whether this gate blocks BlackFox compatibility."""

        return self.blocking and not self.passed_with_boundaries

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic export payload."""

        return {
            "blocking": self.blocking,
            "description": self.description,
            "evidence_ids": list(self.evidence_ids),
            "gate_id": self.gate_id,
            "gate_kind": self.gate_kind.value,
            "result": self.result.value,
            "schema_version": self.schema_version,
        }


@dataclass(frozen=True, slots=True)
class WaveFiveBlackFoxReceipt:
    """One receipt in a BlackFox-compatible evidence chain."""

    receipt_id: str
    receipt_kind: WaveFiveBlackFoxReceiptKind
    source_system: WaveFiveSourceSystem
    artifact_ids: tuple[str, ...]
    digest: str
    evidence_ids: tuple[str, ...]
    human_reviewer_id: str = ""
    authorizes_execution: bool = False
    self_approved: bool = False
    schema_version: str = WAVE_FIVE_BLACKFOX_RECEIPT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate receipt identity, digest, and no-authority boundaries."""

        object.__setattr__(self, "receipt_id", _text(self.receipt_id, "receipt_id"))
        object.__setattr__(
            self, "artifact_ids", _unique_text(self.artifact_ids, label="artifact_id")
        )
        object.__setattr__(self, "digest", _sha256(self.digest, "digest"))
        object.__setattr__(
            self, "evidence_ids", _unique_text(self.evidence_ids, label="evidence_id")
        )
        object.__setattr__(self, "human_reviewer_id", self.human_reviewer_id.strip())
        if not self.artifact_ids:
            raise ValueError("BlackFox receipts require artifact ids.")
        if not self.evidence_ids:
            raise ValueError("BlackFox receipts require evidence ids.")
        if self.authorizes_execution:
            raise ValueError("BlackFox bridge receipts cannot authorize execution.")
        if self.self_approved:
            raise ValueError("BlackFox bridge receipts cannot be self-approved.")
        if self.receipt_kind is WaveFiveBlackFoxReceiptKind.HUMAN_REVIEW:
            if not self.human_reviewer_id:
                raise ValueError("Human-review receipts require a human reviewer id.")
        object.__setattr__(
            self, "schema_version", _text(self.schema_version, "schema_version")
        )

    @property
    def receipt_key(self) -> str:
        """Return deterministic receipt key."""

        return self.receipt_id

    @property
    def has_human_review(self) -> bool:
        """Return whether this receipt carries human review evidence."""

        return (
            self.receipt_kind is WaveFiveBlackFoxReceiptKind.HUMAN_REVIEW
            and bool(self.human_reviewer_id)
        )

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic export payload."""

        return {
            "artifact_ids": list(self.artifact_ids),
            "authorizes_execution": self.authorizes_execution,
            "digest": self.digest,
            "evidence_ids": list(self.evidence_ids),
            "human_reviewer_id": self.human_reviewer_id,
            "receipt_id": self.receipt_id,
            "receipt_kind": self.receipt_kind.value,
            "schema_version": self.schema_version,
            "self_approved": self.self_approved,
            "source_system": self.source_system.value,
        }


@dataclass(frozen=True, slots=True)
class WaveFiveBlackFoxCompatibilityHandoff:
    """Kernel-to-BlackFox Wave 10 compatibility handoff record."""

    handoff_id: str
    title: str
    source_system: WaveFiveSourceSystem
    handoff_state: WaveFiveBlackFoxHandoffState
    authority_mode: WaveFiveBlackFoxAuthorityMode
    kernel_artifact_ids: tuple[str, ...]
    blackfox_control_refs: tuple[str, ...]
    gates: tuple[WaveFiveBlackFoxGate, ...]
    receipts: tuple[WaveFiveBlackFoxReceipt, ...]
    protocol_ids: tuple[str, ...]
    reviewer_ids: tuple[str, ...] = ()
    granted_execution_authority: bool = False
    claims_agi: bool = False
    claims_production_ready: bool = False
    claims_certified: bool = False
    claim_boundaries: tuple[WaveFiveClaimBoundary, ...] = (
        WAVE_FIVE_REQUIRED_CLAIM_BOUNDARIES
    )
    notes: tuple[str, ...] = ()
    schema_version: str = WAVE_FIVE_BLACKFOX_HANDOFF_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate BlackFox compatibility coverage and hard authority limits."""

        object.__setattr__(self, "handoff_id", _text(self.handoff_id, "handoff_id"))
        object.__setattr__(self, "title", _text(self.title, "title"))
        if self.granted_execution_authority:
            raise ValueError("BlackFox compatibility handoffs cannot grant execution.")
        if self.claims_agi:
            raise ValueError("BlackFox compatibility handoffs cannot claim AGI.")
        if self.claims_production_ready:
            raise ValueError(
                "BlackFox compatibility handoffs cannot claim production readiness."
            )
        if self.claims_certified:
            raise ValueError(
                "BlackFox compatibility handoffs cannot claim certification."
            )
        object.__setattr__(
            self,
            "kernel_artifact_ids",
            _unique_text(self.kernel_artifact_ids, label="kernel artifact_id"),
        )
        object.__setattr__(
            self,
            "blackfox_control_refs",
            _unique_text(self.blackfox_control_refs, label="BlackFox control ref"),
        )
        if not self.kernel_artifact_ids:
            raise ValueError("BlackFox handoffs require Kernel artifact ids.")
        if not self.blackfox_control_refs:
            raise ValueError("BlackFox handoffs require BlackFox control refs.")
        gates = tuple(sorted(self.gates, key=lambda item: item.gate_key))
        receipts = tuple(sorted(self.receipts, key=lambda item: item.receipt_key))
        if not gates:
            raise ValueError("BlackFox handoffs require gates.")
        if not receipts:
            raise ValueError("BlackFox handoffs require receipts.")
        _unique_values((item.gate_id for item in gates), label="gate_id")
        _unique_values((item.receipt_id for item in receipts), label="receipt_id")
        object.__setattr__(self, "gates", gates)
        object.__setattr__(self, "receipts", receipts)
        object.__setattr__(
            self, "protocol_ids", _unique_text(self.protocol_ids, label="protocol_id")
        )
        if not self.protocol_ids:
            raise ValueError("BlackFox handoffs require protocol ids.")
        object.__setattr__(
            self, "reviewer_ids", _unique_text(self.reviewer_ids, label="reviewer_id")
        )
        object.__setattr__(
            self,
            "claim_boundaries",
            _unique_enum(self.claim_boundaries, label="claim boundary"),
        )
        missing_boundaries = tuple(
            boundary
            for boundary in WAVE_FIVE_REQUIRED_CLAIM_BOUNDARIES
            if boundary not in self.claim_boundaries
        )
        if missing_boundaries:
            raise ValueError(
                "BlackFox handoffs must preserve claim boundary: "
                f"{missing_boundaries[0].value}"
            )
        object.__setattr__(self, "notes", _unique_text(self.notes, label="note"))
        object.__setattr__(
            self, "schema_version", _text(self.schema_version, "schema_version")
        )
        if self.authority_mode is WaveFiveBlackFoxAuthorityMode.BLOCKED:
            if not self.blocks_blackfox_compatibility:
                raise ValueError("Blocked authority mode requires a blocking gap.")
        if self.blackfox_accepted_with_boundaries:
            if self.source_system not in BLACKFOX_ACCEPTANCE_SOURCE_SYSTEMS:
                raise ValueError(
                    "BlackFox-accepted handoffs require BlackFox or human "
                    "review source."
                )
            if not self.reviewer_ids:
                raise ValueError("BlackFox-accepted handoffs require reviewer ids.")
            if self.blocks_blackfox_compatibility:
                raise ValueError(
                    "BlackFox-accepted handoffs cannot contain blocking gaps."
                )

    @property
    def covered_gate_kinds(self) -> tuple[WaveFiveBlackFoxGateKind, ...]:
        """Return BlackFox gate kinds represented by this handoff."""

        kinds: list[WaveFiveBlackFoxGateKind] = []
        seen: set[WaveFiveBlackFoxGateKind] = set()
        for gate in self.gates:
            if gate.gate_kind not in seen:
                kinds.append(gate.gate_kind)
                seen.add(gate.gate_kind)
        return tuple(kinds)

    @property
    def missing_required_gate_kinds(self) -> tuple[WaveFiveBlackFoxGateKind, ...]:
        """Return required BlackFox gates absent from this handoff."""

        covered = set(self.covered_gate_kinds)
        return tuple(
            kind for kind in REQUIRED_BLACKFOX_GATE_KINDS if kind not in covered
        )

    @property
    def covered_receipt_kinds(self) -> tuple[WaveFiveBlackFoxReceiptKind, ...]:
        """Return BlackFox receipt kinds represented by this handoff."""

        kinds: list[WaveFiveBlackFoxReceiptKind] = []
        seen: set[WaveFiveBlackFoxReceiptKind] = set()
        for receipt in self.receipts:
            if receipt.receipt_kind not in seen:
                kinds.append(receipt.receipt_kind)
                seen.add(receipt.receipt_kind)
        return tuple(kinds)

    @property
    def missing_required_receipt_kinds(
        self,
    ) -> tuple[WaveFiveBlackFoxReceiptKind, ...]:
        """Return required BlackFox receipt kinds absent from this handoff."""

        covered = set(self.covered_receipt_kinds)
        return tuple(
            kind for kind in REQUIRED_BLACKFOX_RECEIPT_KINDS if kind not in covered
        )

    @property
    def blocking_gate_ids(self) -> tuple[str, ...]:
        """Return BlackFox gates that block compatibility."""

        return tuple(
            gate.gate_id for gate in self.gates if gate.blocks_wave_five_progress
        )

    @property
    def has_human_review_receipt(self) -> bool:
        """Return whether a human-review receipt is present."""

        return any(receipt.has_human_review for receipt in self.receipts)

    @property
    def has_required_gate_coverage(self) -> bool:
        """Return whether every locked BlackFox gate is represented."""

        return not self.missing_required_gate_kinds

    @property
    def has_required_receipt_coverage(self) -> bool:
        """Return whether every locked BlackFox receipt is represented."""

        return not self.missing_required_receipt_kinds

    @property
    def preserves_blackfox_authority_boundary(self) -> bool:
        """Return whether the handoff preserves review-only BlackFox authority."""

        return (
            self.authority_mode in SAFE_BLACKFOX_AUTHORITY_MODES
            and not self.granted_execution_authority
            and not self.claims_agi
            and not self.claims_production_ready
            and not self.claims_certified
            and self.has_human_review_receipt
        )

    @property
    def blocks_blackfox_compatibility(self) -> bool:
        """Return whether any governance gap blocks BlackFox compatibility."""

        return bool(
            self.blocking_gate_ids
            or self.missing_required_gate_kinds
            or self.missing_required_receipt_kinds
        )

    @property
    def ready_for_blackfox_review(self) -> bool:
        """Return whether the handoff can enter BlackFox governance review."""

        return (
            self.handoff_state
            in {
                WaveFiveBlackFoxHandoffState.INTERNAL_BRIDGE_READY,
                WaveFiveBlackFoxHandoffState.READY_FOR_BLACKFOX_REVIEW,
                WaveFiveBlackFoxHandoffState.UNDER_BLACKFOX_REVIEW,
            }
            and self.has_required_gate_coverage
            and self.has_required_receipt_coverage
            and not self.blocking_gate_ids
            and self.preserves_blackfox_authority_boundary
        )

    @property
    def blackfox_accepted_with_boundaries(self) -> bool:
        """Return whether BlackFox or human review accepted the handoff."""

        return (
            self.handoff_state
            is WaveFiveBlackFoxHandoffState.BLACKFOX_ACCEPTED_WITH_BOUNDARIES
        )

    @property
    def all_evidence_ids(self) -> tuple[str, ...]:
        """Return all evidence ids bound into this handoff."""

        evidence_ids: list[str] = []
        seen: set[str] = set()
        for evidence_id in self._iter_evidence_ids():
            if evidence_id not in seen:
                evidence_ids.append(evidence_id)
                seen.add(evidence_id)
        return tuple(evidence_ids)

    def to_artifact_ref(self) -> WaveFiveArtifactRef:
        """Return this handoff as a Wave 5 ecosystem-traceability artifact."""

        decision = WaveFiveArtifactDecision.NEEDS_EXTERNAL_EVIDENCE
        status = WaveFiveValidationStatus.MISSING_EXTERNAL_EVIDENCE
        authority = WaveFiveAuthorityState.HUMAN_REVIEW_REQUIRED
        if self.blackfox_accepted_with_boundaries:
            decision = WaveFiveArtifactDecision.EXTERNALLY_REVIEWED
            status = WaveFiveValidationStatus.ACCEPTED_WITH_BOUNDARIES
        elif self.ready_for_blackfox_review:
            decision = WaveFiveArtifactDecision.READY_FOR_INDEPENDENT_REVIEW
            status = WaveFiveValidationStatus.UNDER_INDEPENDENT_REVIEW
        elif self.blocks_blackfox_compatibility:
            decision = WaveFiveArtifactDecision.BLOCKED
            status = WaveFiveValidationStatus.REJECTED
            authority = WaveFiveAuthorityState.BLOCKED
        return WaveFiveArtifactRef(
            artifact_id=self.handoff_id,
            kind=WaveFiveArtifactKind.ECOSYSTEM_TRACEABILITY_MAP,
            capability_area=WaveFiveCapabilityArea.ECOSYSTEM_TRACEABILITY,
            source_system=self.source_system,
            summary=self.title,
            produced_by_engine_id="wave5-blackfox-compatibility-bridge",
            produced_by_agent_role_id="blackfox-bridge-reviewer",
            evidence_ids=self.all_evidence_ids,
            decision=decision,
            authority_state=authority,
            validation_status=status,
            claim_boundaries=self.claim_boundaries,
        )

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic export payload."""

        return {
            "authority_mode": self.authority_mode.value,
            "blackfox_control_refs": list(self.blackfox_control_refs),
            "claim_boundaries": [boundary.value for boundary in self.claim_boundaries],
            "claims_agi": self.claims_agi,
            "claims_certified": self.claims_certified,
            "claims_production_ready": self.claims_production_ready,
            "gates": [gate.canonical_payload() for gate in self.gates],
            "granted_execution_authority": self.granted_execution_authority,
            "handoff_id": self.handoff_id,
            "handoff_state": self.handoff_state.value,
            "kernel_artifact_ids": list(self.kernel_artifact_ids),
            "notes": list(self.notes),
            "protocol_ids": list(self.protocol_ids),
            "receipts": [receipt.canonical_payload() for receipt in self.receipts],
            "reviewer_ids": list(self.reviewer_ids),
            "schema_version": self.schema_version,
            "source_system": self.source_system.value,
            "title": self.title,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this handoff."""

        return _stable_sha256(self.canonical_payload())

    def _iter_evidence_ids(self) -> Iterable[str]:
        """Yield evidence ids in deterministic handoff traversal order."""

        for gate in self.gates:
            yield from gate.evidence_ids
        for receipt in self.receipts:
            yield from receipt.evidence_ids


def required_blackfox_gate_kinds() -> tuple[WaveFiveBlackFoxGateKind, ...]:
    """Return locked BlackFox gates required for Wave 5 compatibility."""

    return REQUIRED_BLACKFOX_GATE_KINDS


def required_blackfox_receipt_kinds() -> tuple[WaveFiveBlackFoxReceiptKind, ...]:
    """Return locked BlackFox receipt kinds required for Wave 5 compatibility."""

    return REQUIRED_BLACKFOX_RECEIPT_KINDS


def safe_blackfox_authority_modes() -> tuple[WaveFiveBlackFoxAuthorityMode, ...]:
    """Return authority modes that preserve review-only BlackFox boundaries."""

    return SAFE_BLACKFOX_AUTHORITY_MODES


def blackfox_acceptance_source_systems() -> tuple[WaveFiveSourceSystem, ...]:
    """Return source systems that can assert bounded BlackFox acceptance."""

    return BLACKFOX_ACCEPTANCE_SOURCE_SYSTEMS


def _text(value: str, label: str) -> str:
    """Return stripped text or raise when empty."""

    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{label} must not be empty.")
    return normalized


def _unique_text(values: Iterable[str], *, label: str) -> tuple[str, ...]:
    """Normalize text values while rejecting blanks and duplicates."""

    normalized: list[str] = []
    seen: set[str] = set()
    for value in values:
        item = _text(value, label)
        if item in seen:
            raise ValueError(f"Duplicate {label} detected: {item}")
        normalized.append(item)
        seen.add(item)
    return tuple(normalized)


def _unique_enum(values: Iterable[E], *, label: str) -> tuple[E, ...]:
    """Return enum values while rejecting duplicates."""

    normalized: list[E] = []
    seen: set[E] = set()
    for value in values:
        if value in seen:
            raise ValueError(f"Duplicate {label} detected: {value.value}")
        normalized.append(value)
        seen.add(value)
    return tuple(normalized)


def _unique_values(values: Iterable[T], *, label: str) -> set[T]:
    """Return unique values while rejecting duplicates."""

    seen: set[T] = set()
    for value in values:
        if value in seen:
            raise ValueError(f"Duplicate {label} detected: {value}")
        seen.add(value)
    return seen


def _sha256(value: str, label: str) -> str:
    """Return a normalized SHA-256 digest or raise when malformed."""

    normalized = _text(value, label).lower()
    if len(normalized) != 64:
        raise ValueError(f"{label} must be a 64-character SHA-256 digest.")
    try:
        int(normalized, 16)
    except ValueError as exc:
        raise ValueError(f"{label} must be hexadecimal.") from exc
    return normalized


def _stable_sha256(payload: Mapping[str, Any]) -> str:
    """Return deterministic SHA-256 over a canonical JSON payload."""

    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return hashlib.sha256(encoded).hexdigest()
