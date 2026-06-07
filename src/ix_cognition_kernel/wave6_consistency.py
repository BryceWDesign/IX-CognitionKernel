"""Wave 6 package consistency checks.

By this point Wave 6 has several review artifacts: audit manifest, release
manifest, review summary, maturity decision, and external validation records.
Those artifacts must not drift apart. This module records deterministic
cross-artifact consistency checks without importing or executing the upstream
objects. It is a small review layer that blocks overclaims, missing fingerprints,
or mismatched authority and boundary statements.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Protocol, TypeVar

T = TypeVar("T")
E = TypeVar("E", bound=StrEnum)

WAVE_SIX_CONSISTENCY_CHECK_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave6-consistency-check-v1"
)
WAVE_SIX_CONSISTENCY_REPORT_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave6-consistency-report-v1"
)


class FingerprintedArtifactLike(Protocol):
    """Structural protocol for a review artifact with a fingerprint."""

    def fingerprint(self) -> str:
        """Return deterministic artifact fingerprint."""


class WaveSixConsistencyCheckKind(StrEnum):
    """Kinds of cross-artifact consistency checks for Wave 6."""

    CLAIM_BOUNDARY_ALIGNMENT = "claim-boundary-alignment"
    HUMAN_AUTHORITY_ALIGNMENT = "human-authority-alignment"
    INDEPENDENT_REVIEW_ALIGNMENT = "independent-review-alignment"
    RELEASE_SUMMARY_LINK = "release-summary-link"
    AUDIT_RELEASE_LINK = "audit-release-link"
    MATURITY_DECISION_LINK = "maturity-decision-link"
    EXTERNAL_VALIDATION_LINK = "external-validation-link"
    REQUIRED_FINGERPRINT_PRESENT = "required-fingerprint-present"
    NO_OVERCLAIM_PRESENT = "no-overclaim-present"


class WaveSixConsistencyFinding(StrEnum):
    """Finding for one cross-artifact consistency check."""

    PASSED = "passed"
    NEEDS_MORE_EVIDENCE = "needs-more-evidence"
    BLOCKS_REVIEW = "blocks-review"


class WaveSixConsistencyDecision(StrEnum):
    """Fail-closed decision for a consistency report."""

    ACCEPT_FOR_BOUNDED_REVIEW = "accept-for-bounded-review"
    HOLD_FOR_MORE_EVIDENCE = "hold-for-more-evidence"
    BLOCK_REVIEW = "block-review"


class WaveSixConsistencyStatus(StrEnum):
    """Overall status for a Wave 6 consistency report."""

    READY = "ready"
    NEEDS_MORE_EVIDENCE = "needs-more-evidence"
    BLOCKED = "blocked"


WAVE_SIX_REQUIRED_CONSISTENCY_CHECKS: tuple[WaveSixConsistencyCheckKind, ...] = (
    WaveSixConsistencyCheckKind.CLAIM_BOUNDARY_ALIGNMENT,
    WaveSixConsistencyCheckKind.HUMAN_AUTHORITY_ALIGNMENT,
    WaveSixConsistencyCheckKind.INDEPENDENT_REVIEW_ALIGNMENT,
    WaveSixConsistencyCheckKind.RELEASE_SUMMARY_LINK,
    WaveSixConsistencyCheckKind.AUDIT_RELEASE_LINK,
    WaveSixConsistencyCheckKind.MATURITY_DECISION_LINK,
    WaveSixConsistencyCheckKind.EXTERNAL_VALIDATION_LINK,
    WaveSixConsistencyCheckKind.REQUIRED_FINGERPRINT_PRESENT,
    WaveSixConsistencyCheckKind.NO_OVERCLAIM_PRESENT,
)


@dataclass(frozen=True, slots=True)
class WaveSixConsistencyCheck:
    """One deterministic cross-artifact consistency check."""

    check_id: str
    kind: WaveSixConsistencyCheckKind
    summary: str
    expected_value: str
    observed_value: str
    evidence_ids: tuple[str, ...]
    finding: WaveSixConsistencyFinding = WaveSixConsistencyFinding.PASSED
    reviewer_question: str = "Does this cross-artifact check remain consistent?"
    requires_follow_up: bool = False
    blocks_review: bool = False
    schema_version: str = WAVE_SIX_CONSISTENCY_CHECK_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate identity, evidence binding, and finding semantics."""

        object.__setattr__(
            self,
            "check_id",
            _require_non_empty(self.check_id, "check_id"),
        )
        object.__setattr__(self, "summary", _require_non_empty(self.summary, "summary"))
        object.__setattr__(
            self,
            "expected_value",
            _require_non_empty(self.expected_value, "expected_value"),
        )
        object.__setattr__(
            self,
            "observed_value",
            _require_non_empty(self.observed_value, "observed_value"),
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
            raise ValueError("Wave 6 consistency checks require evidence ids.")
        if self.finding is WaveSixConsistencyFinding.PASSED:
            if self.requires_follow_up:
                raise ValueError("Passed consistency checks cannot require follow-up.")
            if self.blocks_review:
                raise ValueError("Passed consistency checks cannot block review.")
        if (
            self.finding is WaveSixConsistencyFinding.NEEDS_MORE_EVIDENCE
            and not self.requires_follow_up
        ):
            raise ValueError(
                "Needs-more-evidence consistency checks require follow-up."
            )
        if (
            self.finding is WaveSixConsistencyFinding.BLOCKS_REVIEW
            and not self.blocks_review
        ):
            raise ValueError("Blocking consistency checks must block review.")
        if self.expected_value != self.observed_value:
            if self.finding is WaveSixConsistencyFinding.PASSED:
                raise ValueError("Mismatched consistency checks cannot pass.")

    @property
    def passed(self) -> bool:
        """Return whether this consistency check passed."""

        return self.finding is WaveSixConsistencyFinding.PASSED

    @property
    def needs_more_evidence(self) -> bool:
        """Return whether this consistency check needs more evidence."""

        return self.finding is WaveSixConsistencyFinding.NEEDS_MORE_EVIDENCE

    @property
    def blocks_bounded_review(self) -> bool:
        """Return whether this check blocks bounded review."""

        return (
            self.blocks_review
            or self.finding is WaveSixConsistencyFinding.BLOCKS_REVIEW
        )

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic check payload for hashing and review."""

        return {
            "blocks_review": self.blocks_review,
            "check_id": self.check_id,
            "evidence_ids": list(self.evidence_ids),
            "expected_value": self.expected_value,
            "finding": self.finding.value,
            "kind": self.kind.value,
            "observed_value": self.observed_value,
            "requires_follow_up": self.requires_follow_up,
            "reviewer_question": self.reviewer_question,
            "schema_version": self.schema_version,
            "summary": self.summary,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this check."""

        return _stable_sha256(self.canonical_payload())


@dataclass(frozen=True, slots=True)
class WaveSixConsistencyReport:
    """Cross-artifact consistency report for a bounded Wave 6 package."""

    report_id: str
    checks: tuple[WaveSixConsistencyCheck, ...]
    decision: WaveSixConsistencyDecision
    claim_boundary_statement: str
    generated_by_engine_id: str
    human_authority_id: str
    independent_reviewer_id: str
    required_checks: tuple[WaveSixConsistencyCheckKind, ...] = (
        WAVE_SIX_REQUIRED_CONSISTENCY_CHECKS
    )
    claims_agi: bool = False
    claims_production_ready: bool = False
    claims_certified: bool = False
    allows_autonomous_authority: bool = False
    notes: tuple[str, ...] = ()
    schema_version: str = WAVE_SIX_CONSISTENCY_REPORT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate report coverage, authority fields, and claim boundary."""

        object.__setattr__(
            self,
            "report_id",
            _require_non_empty(self.report_id, "report_id"),
        )
        if not self.checks:
            raise ValueError("Wave 6 consistency reports require checks.")
        sorted_checks = tuple(sorted(self.checks, key=lambda check: check.check_id))
        _require_unique_text(
            (check.check_id for check in sorted_checks),
            label="check_id",
        )
        _require_unique_enum(
            (check.kind for check in sorted_checks),
            label="check kind",
        )
        object.__setattr__(self, "checks", sorted_checks)
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
            "required_checks",
            _normalize_unique_enum_tuple(
                self.required_checks,
                label="required check",
            ),
        )
        object.__setattr__(
            self,
            "notes",
            _normalize_unique_text_tuple(self.notes, label="report note"),
        )
        object.__setattr__(
            self,
            "schema_version",
            _require_non_empty(self.schema_version, "schema_version"),
        )
        if self.decision is WaveSixConsistencyDecision.ACCEPT_FOR_BOUNDED_REVIEW:
            if self.missing_check_kinds:
                raise ValueError("Accepted consistency reports require every check.")
            if self.follow_up_check_ids:
                raise ValueError("Accepted consistency reports cannot need follow-up.")
            if self.blocking_check_ids:
                raise ValueError(
                    "Accepted consistency reports cannot include blockers."
                )
            if self.overclaim_present:
                raise ValueError("Accepted consistency reports cannot overclaim.")
            if not self.claim_boundary_statement_valid:
                raise ValueError("Accepted reports require a valid claim boundary.")
        if self.decision is WaveSixConsistencyDecision.BLOCK_REVIEW:
            if not self.blocking_check_ids and not self.overclaim_present:
                raise ValueError(
                    "Blocked consistency reports require blocker or overclaim."
                )

    @property
    def check_ids(self) -> tuple[str, ...]:
        """Return consistency check ids in deterministic order."""

        return tuple(check.check_id for check in self.checks)

    @property
    def present_check_kinds(self) -> tuple[WaveSixConsistencyCheckKind, ...]:
        """Return required consistency checks represented by the report."""

        present = {check.kind for check in self.checks}
        return tuple(kind for kind in self.required_checks if kind in present)

    @property
    def missing_check_kinds(self) -> tuple[WaveSixConsistencyCheckKind, ...]:
        """Return required consistency checks missing from the report."""

        present = {check.kind for check in self.checks}
        return tuple(kind for kind in self.required_checks if kind not in present)

    @property
    def passed_check_ids(self) -> tuple[str, ...]:
        """Return passed consistency check ids."""

        return tuple(check.check_id for check in self.checks if check.passed)

    @property
    def follow_up_check_ids(self) -> tuple[str, ...]:
        """Return checks that need more evidence."""

        return tuple(
            check.check_id for check in self.checks if check.needs_more_evidence
        )

    @property
    def blocking_check_ids(self) -> tuple[str, ...]:
        """Return checks that block bounded review."""

        return tuple(
            check.check_id for check in self.checks if check.blocks_bounded_review
        )

    @property
    def overclaim_present(self) -> bool:
        """Return whether the report violates the claim boundary."""

        return (
            self.claims_agi
            or self.claims_production_ready
            or self.claims_certified
            or self.allows_autonomous_authority
        )

    @property
    def claim_boundary_statement_valid(self) -> bool:
        """Return whether the report preserves bounded review only."""

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
    def status(self) -> WaveSixConsistencyStatus:
        """Return fail-closed report status."""

        if self.overclaim_present or self.blocking_check_ids:
            return WaveSixConsistencyStatus.BLOCKED
        if (
            self.missing_check_kinds
            or self.follow_up_check_ids
            or not self.claim_boundary_statement_valid
        ):
            return WaveSixConsistencyStatus.NEEDS_MORE_EVIDENCE
        return WaveSixConsistencyStatus.READY

    @property
    def ready_for_bounded_review(self) -> bool:
        """Return whether the consistency report can support bounded review."""

        return self.status is WaveSixConsistencyStatus.READY

    def check_for_kind(
        self,
        kind: WaveSixConsistencyCheckKind,
    ) -> WaveSixConsistencyCheck | None:
        """Return the consistency check for a kind, if present."""

        for check in self.checks:
            if check.kind is kind:
                return check
        return None

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic report payload for hashing and review."""

        return {
            "allows_autonomous_authority": self.allows_autonomous_authority,
            "blocking_check_ids": list(self.blocking_check_ids),
            "check_ids": list(self.check_ids),
            "checks": [check.canonical_payload() for check in self.checks],
            "claim_boundary_statement": self.claim_boundary_statement,
            "claim_boundary_statement_valid": self.claim_boundary_statement_valid,
            "claims_agi": self.claims_agi,
            "claims_certified": self.claims_certified,
            "claims_production_ready": self.claims_production_ready,
            "decision": self.decision.value,
            "follow_up_check_ids": list(self.follow_up_check_ids),
            "generated_by_engine_id": self.generated_by_engine_id,
            "human_authority_id": self.human_authority_id,
            "independent_reviewer_id": self.independent_reviewer_id,
            "missing_check_kinds": [kind.value for kind in self.missing_check_kinds],
            "notes": list(self.notes),
            "passed_check_ids": list(self.passed_check_ids),
            "present_check_kinds": [kind.value for kind in self.present_check_kinds],
            "report_id": self.report_id,
            "required_checks": [kind.value for kind in self.required_checks],
            "schema_version": self.schema_version,
            "status": self.status.value,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this consistency report."""

        return _stable_sha256(self.canonical_payload())


def build_wave_six_consistency_report(
    *,
    report_id: str,
    checks: Iterable[WaveSixConsistencyCheck],
    decision: WaveSixConsistencyDecision,
    claim_boundary_statement: str,
    generated_by_engine_id: str,
    human_authority_id: str,
    independent_reviewer_id: str,
    notes: Iterable[str] = (),
) -> WaveSixConsistencyReport:
    """Build a deterministic Wave 6 consistency report."""

    return WaveSixConsistencyReport(
        report_id=report_id,
        checks=tuple(checks),
        decision=decision,
        claim_boundary_statement=claim_boundary_statement,
        generated_by_engine_id=generated_by_engine_id,
        human_authority_id=human_authority_id,
        independent_reviewer_id=independent_reviewer_id,
        notes=tuple(notes),
    )


def build_fingerprint_presence_check(
    *,
    check_id: str,
    artifact_id: str,
    artifact: FingerprintedArtifactLike,
    evidence_ids: Iterable[str],
) -> WaveSixConsistencyCheck:
    """Build a check proving that an artifact exposes a stable fingerprint."""

    fingerprint = artifact.fingerprint()
    finding = WaveSixConsistencyFinding.PASSED
    requires_follow_up = False
    if not fingerprint.strip():
        finding = WaveSixConsistencyFinding.NEEDS_MORE_EVIDENCE
        requires_follow_up = True
    return WaveSixConsistencyCheck(
        check_id=check_id,
        kind=WaveSixConsistencyCheckKind.REQUIRED_FINGERPRINT_PRESENT,
        summary=f"{artifact_id} exposes a deterministic fingerprint.",
        expected_value="fingerprint-present",
        observed_value="fingerprint-present" if fingerprint.strip() else "missing",
        evidence_ids=tuple(evidence_ids),
        finding=finding,
        requires_follow_up=requires_follow_up,
        reviewer_question="Can the reviewer recompute the referenced fingerprint?",
    )


def required_wave_six_consistency_checks() -> tuple[WaveSixConsistencyCheckKind, ...]:
    """Return required consistency check kinds for Wave 6 review."""

    return WAVE_SIX_REQUIRED_CONSISTENCY_CHECKS


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
