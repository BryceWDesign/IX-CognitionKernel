"""Wave 6 CI verification receipts.

Wave 6 review depends on honest verification state. This module records CI
commands as deterministic receipts: what command was expected, whether it passed,
what evidence anchors it, and whether missing or failed verification blocks the
bounded Wave 6 review claim. It does not execute CI and does not claim AGI.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, TypeVar

E = TypeVar("E", bound=StrEnum)

WAVE_SIX_CI_COMMAND_RECEIPT_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave6-ci-command-receipt-v1"
)
WAVE_SIX_CI_RECEIPT_LEDGER_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave6-ci-receipt-ledger-v1"
)


class WaveSixCICommandKind(StrEnum):
    """CI command kinds that may be required for Wave 6 review."""

    RUFF_CHECK = "ruff-check"
    MYPY = "mypy"
    PYTEST = "pytest"
    PY_COMPILE = "py-compile"
    PACKAGE_IMPORT = "package-import"
    SECURITY_SCAN = "security-scan"


class WaveSixCICommandStatus(StrEnum):
    """Observed status for one CI command."""

    PASSED = "passed"
    FAILED = "failed"
    NOT_RUN = "not-run"
    BLOCKED = "blocked"


class WaveSixCIReceiptDecision(StrEnum):
    """Fail-closed decision for a CI command receipt."""

    ACCEPT_FOR_REVIEW = "accept-for-review"
    NEEDS_MORE_EVIDENCE = "needs-more-evidence"
    BLOCK_REVIEW = "block-review"


class WaveSixCIReceiptLedgerDecision(StrEnum):
    """Final decision for the Wave 6 CI receipt ledger."""

    READY_FOR_BOUNDED_REVIEW = "ready-for-bounded-review"
    HOLD_FOR_MORE_EVIDENCE = "hold-for-more-evidence"
    BLOCK_REVIEW = "block-review"


class WaveSixCIReceiptLedgerStatus(StrEnum):
    """Computed status for the CI receipt ledger."""

    READY = "ready"
    NEEDS_MORE_EVIDENCE = "needs-more-evidence"
    BLOCKED = "blocked"


WAVE_SIX_REQUIRED_CI_COMMAND_KINDS: tuple[WaveSixCICommandKind, ...] = (
    WaveSixCICommandKind.RUFF_CHECK,
    WaveSixCICommandKind.MYPY,
    WaveSixCICommandKind.PYTEST,
)


@dataclass(frozen=True, slots=True)
class WaveSixCICommandReceipt:
    """One deterministic CI command receipt."""

    receipt_id: str
    command_kind: WaveSixCICommandKind
    command: str
    status: WaveSixCICommandStatus
    decision: WaveSixCIReceiptDecision
    summary: str
    evidence_ids: tuple[str, ...]
    output_fingerprint: str
    exit_code: int | None = None
    requires_follow_up: bool = False
    blocks_review: bool = False
    schema_version: str = WAVE_SIX_CI_COMMAND_RECEIPT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate CI command receipt semantics."""

        object.__setattr__(
            self,
            "receipt_id",
            _require_non_empty(self.receipt_id, "receipt_id"),
        )
        object.__setattr__(
            self,
            "command",
            _require_non_empty(self.command, "command"),
        )
        object.__setattr__(
            self,
            "summary",
            _require_non_empty(self.summary, "summary"),
        )
        object.__setattr__(
            self,
            "evidence_ids",
            _normalize_unique_text_tuple(self.evidence_ids, label="evidence_id"),
        )
        object.__setattr__(
            self,
            "output_fingerprint",
            _require_non_empty(self.output_fingerprint, "output_fingerprint"),
        )
        object.__setattr__(
            self,
            "schema_version",
            _require_non_empty(self.schema_version, "schema_version"),
        )
        if not self.evidence_ids:
            raise ValueError("CI command receipts require evidence ids.")
        if self.status is WaveSixCICommandStatus.PASSED:
            if self.exit_code not in (0, None):
                raise ValueError("Passed CI receipts require exit code 0 or unknown.")
            if self.decision is not WaveSixCIReceiptDecision.ACCEPT_FOR_REVIEW:
                raise ValueError("Passed CI receipts must be accepted for review.")
            if self.requires_follow_up:
                raise ValueError("Passed CI receipts cannot require follow-up.")
            if self.blocks_review:
                raise ValueError("Passed CI receipts cannot block review.")
        if self.status in {
            WaveSixCICommandStatus.FAILED,
            WaveSixCICommandStatus.BLOCKED,
        }:
            if self.decision is not WaveSixCIReceiptDecision.BLOCK_REVIEW:
                raise ValueError("Failed or blocked CI receipts must block review.")
            if not self.blocks_review:
                raise ValueError("Failed or blocked CI receipts must set blocker.")
        if self.status is WaveSixCICommandStatus.NOT_RUN:
            if self.decision is not WaveSixCIReceiptDecision.NEEDS_MORE_EVIDENCE:
                raise ValueError("Not-run CI receipts must need more evidence.")
            if not self.requires_follow_up:
                raise ValueError("Not-run CI receipts require follow-up.")

    @property
    def passed(self) -> bool:
        """Return whether this CI receipt passed."""

        return (
            self.status is WaveSixCICommandStatus.PASSED
            and self.decision is WaveSixCIReceiptDecision.ACCEPT_FOR_REVIEW
        )

    @property
    def needs_more_evidence(self) -> bool:
        """Return whether this CI receipt needs more evidence."""

        return (
            self.status is WaveSixCICommandStatus.NOT_RUN
            or self.decision is WaveSixCIReceiptDecision.NEEDS_MORE_EVIDENCE
            or self.requires_follow_up
        )

    @property
    def blocks_bounded_review(self) -> bool:
        """Return whether this CI receipt blocks bounded Wave 6 review."""

        return (
            self.blocks_review
            or self.status
            in {
                WaveSixCICommandStatus.FAILED,
                WaveSixCICommandStatus.BLOCKED,
            }
            or self.decision is WaveSixCIReceiptDecision.BLOCK_REVIEW
        )

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic receipt payload for hashing and review."""

        return {
            "blocks_review": self.blocks_review,
            "command": self.command,
            "command_kind": self.command_kind.value,
            "decision": self.decision.value,
            "evidence_ids": list(self.evidence_ids),
            "exit_code": self.exit_code,
            "output_fingerprint": self.output_fingerprint,
            "receipt_id": self.receipt_id,
            "requires_follow_up": self.requires_follow_up,
            "schema_version": self.schema_version,
            "status": self.status.value,
            "summary": self.summary,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this CI receipt."""

        return _stable_sha256(self.canonical_payload())


@dataclass(frozen=True, slots=True)
class WaveSixCIReceiptLedger:
    """Fail-closed ledger of Wave 6 CI verification receipts."""

    ledger_id: str
    receipts: tuple[WaveSixCICommandReceipt, ...]
    decision: WaveSixCIReceiptLedgerDecision
    claim_boundary_statement: str
    generated_by_engine_id: str
    human_authority_id: str
    independent_reviewer_id: str
    required_command_kinds: tuple[WaveSixCICommandKind, ...] = (
        WAVE_SIX_REQUIRED_CI_COMMAND_KINDS
    )
    claims_agi: bool = False
    claims_production_ready: bool = False
    claims_certified: bool = False
    allows_autonomous_authority: bool = False
    notes: tuple[str, ...] = ()
    schema_version: str = WAVE_SIX_CI_RECEIPT_LEDGER_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate CI receipt coverage, authority fields, and decision semantics."""

        object.__setattr__(
            self,
            "ledger_id",
            _require_non_empty(self.ledger_id, "ledger_id"),
        )
        if not self.receipts:
            raise ValueError("Wave 6 CI receipt ledgers require receipts.")
        sorted_receipts = tuple(
            sorted(self.receipts, key=lambda receipt: receipt.receipt_id)
        )
        _require_unique_text(
            (receipt.receipt_id for receipt in sorted_receipts),
            label="receipt_id",
        )
        _require_unique_enum(
            (receipt.command_kind for receipt in sorted_receipts),
            label="command kind",
        )
        object.__setattr__(self, "receipts", sorted_receipts)
        object.__setattr__(
            self,
            "claim_boundary_statement",
            _require_non_empty(
                self.claim_boundary_statement,
                "claim_boundary_statement",
            ),
        )
        object.__setattr__(
            self,
            "generated_by_engine_id",
            _require_non_empty(self.generated_by_engine_id, "generated_by_engine_id"),
        )
        object.__setattr__(
            self,
            "human_authority_id",
            _require_non_empty(self.human_authority_id, "human_authority_id"),
        )
        object.__setattr__(
            self,
            "independent_reviewer_id",
            _require_non_empty(
                self.independent_reviewer_id,
                "independent_reviewer_id",
            ),
        )
        object.__setattr__(
            self,
            "required_command_kinds",
            _normalize_unique_enum_tuple(
                self.required_command_kinds,
                label="required command kind",
            ),
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
        if self.decision is WaveSixCIReceiptLedgerDecision.READY_FOR_BOUNDED_REVIEW:
            if self.missing_command_kinds:
                raise ValueError("Ready CI ledgers require every command kind.")
            if self.follow_up_receipt_ids:
                raise ValueError("Ready CI ledgers cannot require follow-up.")
            if self.blocking_receipt_ids:
                raise ValueError("Ready CI ledgers cannot include blockers.")
            if self.overclaim_present:
                raise ValueError("Ready CI ledgers cannot contain overclaims.")
            if not self.claim_boundary_statement_valid:
                raise ValueError("Ready CI ledgers require valid claim boundary.")
        if (
            self.decision is WaveSixCIReceiptLedgerDecision.BLOCK_REVIEW
            and not self.blocking_receipt_ids
            and not self.overclaim_present
        ):
            raise ValueError("Blocked CI ledgers require blocker or overclaim.")

    @property
    def receipt_ids(self) -> tuple[str, ...]:
        """Return CI receipt ids in deterministic order."""

        return tuple(receipt.receipt_id for receipt in self.receipts)

    @property
    def present_command_kinds(self) -> tuple[WaveSixCICommandKind, ...]:
        """Return required CI command kinds represented by receipts."""

        present = {receipt.command_kind for receipt in self.receipts}
        return tuple(kind for kind in self.required_command_kinds if kind in present)

    @property
    def missing_command_kinds(self) -> tuple[WaveSixCICommandKind, ...]:
        """Return required CI command kinds missing from the ledger."""

        present = {receipt.command_kind for receipt in self.receipts}
        return tuple(
            kind for kind in self.required_command_kinds if kind not in present
        )

    @property
    def passed_receipt_ids(self) -> tuple[str, ...]:
        """Return receipt ids whose CI commands passed."""

        return tuple(receipt.receipt_id for receipt in self.receipts if receipt.passed)

    @property
    def follow_up_receipt_ids(self) -> tuple[str, ...]:
        """Return receipt ids that need more evidence."""

        return tuple(
            receipt.receipt_id
            for receipt in self.receipts
            if receipt.needs_more_evidence
        )

    @property
    def blocking_receipt_ids(self) -> tuple[str, ...]:
        """Return receipt ids that block bounded review."""

        return tuple(
            receipt.receipt_id
            for receipt in self.receipts
            if receipt.blocks_bounded_review
        )

    @property
    def overclaim_present(self) -> bool:
        """Return whether the CI ledger violates the claim boundary."""

        return (
            self.claims_agi
            or self.claims_production_ready
            or self.claims_certified
            or self.allows_autonomous_authority
        )

    @property
    def claim_boundary_statement_valid(self) -> bool:
        """Return whether the CI ledger preserves bounded review language."""

        normalized = self.claim_boundary_statement.casefold()
        required = (
            "measured system-level cognition",
            "bounded review",
            "not an agi",
            "human",
            "independent review",
        )
        return all(fragment in normalized for fragment in required)

    @property
    def status(self) -> WaveSixCIReceiptLedgerStatus:
        """Return fail-closed CI receipt ledger status."""

        if self.overclaim_present or self.blocking_receipt_ids:
            return WaveSixCIReceiptLedgerStatus.BLOCKED
        if (
            self.missing_command_kinds
            or self.follow_up_receipt_ids
            or not self.claim_boundary_statement_valid
        ):
            return WaveSixCIReceiptLedgerStatus.NEEDS_MORE_EVIDENCE
        return WaveSixCIReceiptLedgerStatus.READY

    @property
    def ready_for_bounded_review(self) -> bool:
        """Return whether the CI ledger can support bounded Wave 6 review."""

        return self.status is WaveSixCIReceiptLedgerStatus.READY

    def receipt_for_command_kind(
        self,
        command_kind: WaveSixCICommandKind,
    ) -> WaveSixCICommandReceipt | None:
        """Return the receipt for a command kind, if present."""

        for receipt in self.receipts:
            if receipt.command_kind is command_kind:
                return receipt
        return None

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic ledger payload for hashing and review."""

        return {
            "allows_autonomous_authority": self.allows_autonomous_authority,
            "blocking_receipt_ids": list(self.blocking_receipt_ids),
            "claim_boundary_statement": self.claim_boundary_statement,
            "claim_boundary_statement_valid": self.claim_boundary_statement_valid,
            "claims_agi": self.claims_agi,
            "claims_certified": self.claims_certified,
            "claims_production_ready": self.claims_production_ready,
            "decision": self.decision.value,
            "follow_up_receipt_ids": list(self.follow_up_receipt_ids),
            "generated_by_engine_id": self.generated_by_engine_id,
            "human_authority_id": self.human_authority_id,
            "independent_reviewer_id": self.independent_reviewer_id,
            "ledger_id": self.ledger_id,
            "missing_command_kinds": [
                kind.value for kind in self.missing_command_kinds
            ],
            "notes": list(self.notes),
            "passed_receipt_ids": list(self.passed_receipt_ids),
            "present_command_kinds": [
                kind.value for kind in self.present_command_kinds
            ],
            "receipt_ids": list(self.receipt_ids),
            "receipts": [receipt.canonical_payload() for receipt in self.receipts],
            "required_command_kinds": [
                kind.value for kind in self.required_command_kinds
            ],
            "schema_version": self.schema_version,
            "status": self.status.value,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this CI receipt ledger."""

        return _stable_sha256(self.canonical_payload())


def build_wave_six_ci_receipt_ledger(
    *,
    ledger_id: str,
    receipts: Iterable[WaveSixCICommandReceipt],
    decision: WaveSixCIReceiptLedgerDecision,
    claim_boundary_statement: str,
    generated_by_engine_id: str,
    human_authority_id: str,
    independent_reviewer_id: str,
    notes: Iterable[str] = (),
) -> WaveSixCIReceiptLedger:
    """Build a deterministic Wave 6 CI receipt ledger."""

    return WaveSixCIReceiptLedger(
        ledger_id=ledger_id,
        receipts=tuple(receipts),
        decision=decision,
        claim_boundary_statement=claim_boundary_statement,
        generated_by_engine_id=generated_by_engine_id,
        human_authority_id=human_authority_id,
        independent_reviewer_id=independent_reviewer_id,
        notes=tuple(notes),
    )


def required_wave_six_ci_command_kinds() -> tuple[WaveSixCICommandKind, ...]:
    """Return CI command kinds required for Wave 6 bounded review."""

    return WAVE_SIX_REQUIRED_CI_COMMAND_KINDS


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


def _require_unique_text(values: Iterable[str], *, label: str) -> None:
    """Reject duplicate text values."""

    seen: set[str] = set()
    for value in values:
        if value in seen:
            raise ValueError(f"Duplicate {label} detected: {value}")
        seen.add(value)


def _require_unique_enum(values: Iterable[E], *, label: str) -> None:
    """Reject duplicate enum values."""

    seen: set[E] = set()
    for value in values:
        if value in seen:
            raise ValueError(f"Duplicate {label} detected: {value.value}")
        seen.add(value)


def _stable_sha256(payload: Mapping[str, Any]) -> str:
    """Return deterministic SHA-256 over a canonical JSON payload."""

    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
