"""Wave 6 maturity gate.

This module is the fail-closed decision layer for the measured system-level
cognition attempt. It consumes the assembled evidence package, review scorecard,
and external validation gate as structural inputs. It never upgrades the package
to an AGI claim. The only positive outcome is readiness for bounded Wave 6
measured-cognition review under human and independent validation.
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

WAVE_SIX_MATURITY_GATE_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave6-maturity-gate-v1"
)
WAVE_SIX_MATURITY_DECISION_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave6-maturity-decision-v1"
)


class EvidencePackageLike(Protocol):
    """Structural protocol for the aggregated Wave 6 evidence package."""

    @property
    def ready_for_external_review(self) -> bool:
        """Return whether the evidence package is ready for external review."""

    @property
    def blockers(self) -> tuple[Any, ...]:
        """Return package blockers."""

    @property
    def overclaim_present(self) -> bool:
        """Return whether the package contains an overclaim."""

    def fingerprint(self) -> str:
        """Return deterministic package fingerprint."""


class ReviewScorecardLike(Protocol):
    """Structural protocol for the Wave 6 review scorecard."""

    @property
    def ready_for_external_review(self) -> bool:
        """Return whether the scorecard is ready for external review."""

    @property
    def blocking_item_ids(self) -> tuple[str, ...]:
        """Return scorecard items that block interpretation."""

    @property
    def follow_up_item_ids(self) -> tuple[str, ...]:
        """Return scorecard items requiring more evidence."""

    @property
    def overclaim_present(self) -> bool:
        """Return whether the scorecard contains an overclaim."""

    def fingerprint(self) -> str:
        """Return deterministic scorecard fingerprint."""


class ExternalValidationGateLike(Protocol):
    """Structural protocol for the Wave 6 external validation gate."""

    @property
    def ready_for_external_validation_review(self) -> bool:
        """Return whether external validation is ready for review."""

    @property
    def blockers(self) -> tuple[Any, ...]:
        """Return external validation blockers."""

    @property
    def overclaim_present(self) -> bool:
        """Return whether external validation contains an overclaim."""

    def fingerprint(self) -> str:
        """Return deterministic external validation fingerprint."""


class WaveSixMaturityBlocker(StrEnum):
    """Reasons a Wave 6 maturity gate cannot approve bounded review."""

    EVIDENCE_PACKAGE_NOT_READY = "evidence-package-not-ready"
    REVIEW_SCORECARD_NOT_READY = "review-scorecard-not-ready"
    EXTERNAL_VALIDATION_NOT_READY = "external-validation-not-ready"
    EVIDENCE_PACKAGE_BLOCKED = "evidence-package-blocked"
    REVIEW_SCORECARD_BLOCKED = "review-scorecard-blocked"
    EXTERNAL_VALIDATION_BLOCKED = "external-validation-blocked"
    OVERCLAIM_PRESENT = "overclaim-present"
    HUMAN_AUTHORITY_MISSING = "human-authority-missing"
    INDEPENDENT_REVIEW_MISSING = "independent-review-missing"
    CLAIM_BOUNDARY_STATEMENT_INVALID = "claim-boundary-statement-invalid"


class WaveSixMaturityStatus(StrEnum):
    """Fail-closed maturity status for Wave 6."""

    BLOCKED = "blocked"
    NEEDS_MORE_EVIDENCE = "needs-more-evidence"
    READY_FOR_BOUNDED_WAVE_SIX_REVIEW = "ready-for-bounded-wave-six-review"


class WaveSixMaturityDecision(StrEnum):
    """Human-readable final decision for Wave 6 maturity review."""

    BLOCK_WAVE_SIX_INTERPRETATION = "block-wave-six-interpretation"
    CONTINUE_EVIDENCE_COLLECTION = "continue-evidence-collection"
    ENTER_BOUNDED_MEASURED_COGNITION_REVIEW = (
        "enter-bounded-measured-cognition-review"
    )


@dataclass(frozen=True, slots=True)
class WaveSixMaturityGate:
    """Gate that decides whether Wave 6 may enter bounded external review."""

    gate_id: str
    evidence_package: EvidencePackageLike
    review_scorecard: ReviewScorecardLike
    external_validation_gate: ExternalValidationGateLike
    claim_boundary_statement: str
    human_authority_id: str
    independent_reviewer_id: str
    notes: tuple[str, ...] = ()
    claims_agi: bool = False
    claims_production_ready: bool = False
    claims_certified: bool = False
    allows_autonomous_authority: bool = False
    schema_version: str = WAVE_SIX_MATURITY_GATE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Normalize identity and review-boundary metadata."""

        object.__setattr__(self, "gate_id", _require_non_empty(self.gate_id, "gate_id"))
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
        """Return whether the gate or any input violates the claim boundary."""

        return (
            self.claims_agi
            or self.claims_production_ready
            or self.claims_certified
            or self.allows_autonomous_authority
            or self.evidence_package.overclaim_present
            or self.review_scorecard.overclaim_present
            or self.external_validation_gate.overclaim_present
        )

    @property
    def claim_boundary_statement_valid(self) -> bool:
        """Return whether the boundary statement blocks AGI and autonomy claims."""

        normalized = self.claim_boundary_statement.casefold()
        required_fragments = (
            "measured system-level cognition",
            "not an agi",
            "independent review",
            "human",
        )
        return all(fragment in normalized for fragment in required_fragments)

    @property
    def evidence_package_blocked(self) -> bool:
        """Return whether the evidence package has blocking evidence."""

        return self.evidence_package.overclaim_present or bool(
            self.evidence_package.blockers
            and not self.evidence_package.ready_for_external_review
        )

    @property
    def review_scorecard_blocked(self) -> bool:
        """Return whether the review scorecard has blocking items."""

        return self.review_scorecard.overclaim_present or bool(
            self.review_scorecard.blocking_item_ids
        )

    @property
    def external_validation_blocked(self) -> bool:
        """Return whether the external validation gate has blocking evidence."""

        return self.external_validation_gate.overclaim_present or bool(
            self.external_validation_gate.blockers
            and not self.external_validation_gate.ready_for_external_validation_review
        )

    @property
    def blockers(self) -> tuple[WaveSixMaturityBlocker, ...]:
        """Return deterministic blockers for the maturity gate."""

        blockers: list[WaveSixMaturityBlocker] = []
        if self.overclaim_present:
            blockers.append(WaveSixMaturityBlocker.OVERCLAIM_PRESENT)
        if not self.claim_boundary_statement_valid:
            blockers.append(WaveSixMaturityBlocker.CLAIM_BOUNDARY_STATEMENT_INVALID)
        if not self.human_authority_id:
            blockers.append(WaveSixMaturityBlocker.HUMAN_AUTHORITY_MISSING)
        if not self.independent_reviewer_id:
            blockers.append(WaveSixMaturityBlocker.INDEPENDENT_REVIEW_MISSING)
        if self.evidence_package_blocked:
            blockers.append(WaveSixMaturityBlocker.EVIDENCE_PACKAGE_BLOCKED)
        elif not self.evidence_package.ready_for_external_review:
            blockers.append(WaveSixMaturityBlocker.EVIDENCE_PACKAGE_NOT_READY)
        if self.review_scorecard_blocked:
            blockers.append(WaveSixMaturityBlocker.REVIEW_SCORECARD_BLOCKED)
        elif not self.review_scorecard.ready_for_external_review:
            blockers.append(WaveSixMaturityBlocker.REVIEW_SCORECARD_NOT_READY)
        if self.external_validation_blocked:
            blockers.append(WaveSixMaturityBlocker.EXTERNAL_VALIDATION_BLOCKED)
        elif not self.external_validation_gate.ready_for_external_validation_review:
            blockers.append(WaveSixMaturityBlocker.EXTERNAL_VALIDATION_NOT_READY)
        return tuple(blockers)

    @property
    def status(self) -> WaveSixMaturityStatus:
        """Return fail-closed maturity status."""

        blocking_conditions = {
            WaveSixMaturityBlocker.OVERCLAIM_PRESENT,
            WaveSixMaturityBlocker.CLAIM_BOUNDARY_STATEMENT_INVALID,
            WaveSixMaturityBlocker.EVIDENCE_PACKAGE_BLOCKED,
            WaveSixMaturityBlocker.REVIEW_SCORECARD_BLOCKED,
            WaveSixMaturityBlocker.EXTERNAL_VALIDATION_BLOCKED,
        }
        if any(blocker in blocking_conditions for blocker in self.blockers):
            return WaveSixMaturityStatus.BLOCKED
        if self.blockers:
            return WaveSixMaturityStatus.NEEDS_MORE_EVIDENCE
        return WaveSixMaturityStatus.READY_FOR_BOUNDED_WAVE_SIX_REVIEW

    @property
    def decision(self) -> WaveSixMaturityDecision:
        """Return the final bounded Wave 6 maturity decision."""

        if self.status is WaveSixMaturityStatus.BLOCKED:
            return WaveSixMaturityDecision.BLOCK_WAVE_SIX_INTERPRETATION
        if self.status is WaveSixMaturityStatus.NEEDS_MORE_EVIDENCE:
            return WaveSixMaturityDecision.CONTINUE_EVIDENCE_COLLECTION
        return WaveSixMaturityDecision.ENTER_BOUNDED_MEASURED_COGNITION_REVIEW

    @property
    def ready_for_bounded_wave_six_review(self) -> bool:
        """Return whether the system may enter bounded Wave 6 review."""

        return (
            self.status is WaveSixMaturityStatus.READY_FOR_BOUNDED_WAVE_SIX_REVIEW
        )

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic maturity-gate payload for hashing and review."""

        return {
            "allows_autonomous_authority": self.allows_autonomous_authority,
            "blockers": [blocker.value for blocker in self.blockers],
            "claim_boundary_statement": self.claim_boundary_statement,
            "claim_boundary_statement_valid": self.claim_boundary_statement_valid,
            "claims_agi": self.claims_agi,
            "claims_certified": self.claims_certified,
            "claims_production_ready": self.claims_production_ready,
            "decision": self.decision.value,
            "evidence_package_fingerprint": self.evidence_package.fingerprint(),
            "external_validation_gate_fingerprint": (
                self.external_validation_gate.fingerprint()
            ),
            "gate_id": self.gate_id,
            "human_authority_id": self.human_authority_id,
            "independent_reviewer_id": self.independent_reviewer_id,
            "notes": list(self.notes),
            "review_scorecard_fingerprint": self.review_scorecard.fingerprint(),
            "schema_version": self.schema_version,
            "status": self.status.value,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this maturity gate."""

        return _stable_sha256(self.canonical_payload())


@dataclass(frozen=True, slots=True)
class WaveSixMaturityDecisionRecord:
    """Reviewable record of the final Wave 6 maturity-gate decision."""

    record_id: str
    maturity_gate: WaveSixMaturityGate
    decision_rationale: str
    reviewer_notes: tuple[str, ...]
    schema_version: str = WAVE_SIX_MATURITY_DECISION_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate final decision metadata."""

        object.__setattr__(
            self,
            "record_id",
            _require_non_empty(self.record_id, "record_id"),
        )
        object.__setattr__(
            self,
            "decision_rationale",
            _require_non_empty(self.decision_rationale, "decision_rationale"),
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
        if not self.reviewer_notes:
            raise ValueError("Maturity decision records require reviewer notes.")

    @property
    def ready_for_bounded_review(self) -> bool:
        """Return whether the recorded decision enters bounded Wave 6 review."""

        return self.maturity_gate.ready_for_bounded_wave_six_review

    @property
    def blocks_wave_six_interpretation(self) -> bool:
        """Return whether the recorded decision blocks interpretation."""

        return (
            self.maturity_gate.decision
            is WaveSixMaturityDecision.BLOCK_WAVE_SIX_INTERPRETATION
        )

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic decision-record payload."""

        return {
            "decision": self.maturity_gate.decision.value,
            "decision_rationale": self.decision_rationale,
            "maturity_gate_fingerprint": self.maturity_gate.fingerprint(),
            "record_id": self.record_id,
            "reviewer_notes": list(self.reviewer_notes),
            "schema_version": self.schema_version,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this decision record."""

        return _stable_sha256(self.canonical_payload())


def build_wave_six_maturity_gate(
    *,
    gate_id: str,
    evidence_package: EvidencePackageLike,
    review_scorecard: ReviewScorecardLike,
    external_validation_gate: ExternalValidationGateLike,
    claim_boundary_statement: str,
    human_authority_id: str,
    independent_reviewer_id: str,
    notes: Iterable[str] = (),
) -> WaveSixMaturityGate:
    """Build a deterministic Wave 6 maturity gate."""

    return WaveSixMaturityGate(
        gate_id=gate_id,
        evidence_package=evidence_package,
        review_scorecard=review_scorecard,
        external_validation_gate=external_validation_gate,
        claim_boundary_statement=claim_boundary_statement,
        human_authority_id=human_authority_id,
        independent_reviewer_id=independent_reviewer_id,
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
