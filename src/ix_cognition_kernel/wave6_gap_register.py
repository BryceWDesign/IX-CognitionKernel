"""Wave 6 evidence-gap register.

Wave 6 review cannot hide missing evidence behind a large package. This module
records evidence gaps explicitly: what is open, what is resolved, what is
accepted only as bounded review risk, and what blocks interpretation. It is a
fail-closed register, not a promotion engine and not an AGI claim.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, TypeVar

E = TypeVar("E", bound=StrEnum)

WAVE_SIX_GAP_SCHEMA_VERSION = "ix-cognition-kernel-wave6-evidence-gap-v1"
WAVE_SIX_GAP_REGISTER_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave6-evidence-gap-register-v1"
)


class WaveSixGapKind(StrEnum):
    """Gap categories that must be checked before bounded Wave 6 review."""

    CI_VERIFICATION_GAP = "ci-verification-gap"
    REQUIRED_EVIDENCE_GAP = "required-evidence-gap"
    FINGERPRINT_REPRODUCTION_GAP = "fingerprint-reproduction-gap"
    TRANSFER_EVIDENCE_GAP = "transfer-evidence-gap"
    FALSIFICATION_EVIDENCE_GAP = "falsification-evidence-gap"
    HUMAN_REVIEW_GAP = "human-review-gap"
    INDEPENDENT_REVIEW_GAP = "independent-review-gap"
    CLAIM_BOUNDARY_GAP = "claim-boundary-gap"
    PUBLIC_WORDING_GAP = "public-wording-gap"


class WaveSixGapSeverity(StrEnum):
    """Severity for one Wave 6 evidence gap."""

    INFO = "info"
    MINOR = "minor"
    MAJOR = "major"
    CRITICAL = "critical"


class WaveSixGapState(StrEnum):
    """State for a Wave 6 evidence gap."""

    OPEN = "open"
    RESOLVED = "resolved"
    ACCEPTED_FOR_BOUNDED_REVIEW = "accepted-for-bounded-review"
    BLOCKING = "blocking"


class WaveSixGapDisposition(StrEnum):
    """Disposition for handling a Wave 6 evidence gap."""

    TRACK = "track"
    REQUIRE_EVIDENCE = "require-evidence"
    ACCEPT_BOUNDED_RISK = "accept-bounded-risk"
    BLOCK_WAVE_SIX_REVIEW = "block-wave-six-review"


class WaveSixGapRegisterDecision(StrEnum):
    """Fail-closed decision for the evidence-gap register."""

    READY_FOR_BOUNDED_REVIEW = "ready-for-bounded-review"
    HOLD_FOR_MORE_EVIDENCE = "hold-for-more-evidence"
    BLOCK_REVIEW = "block-review"


class WaveSixGapRegisterStatus(StrEnum):
    """Computed status for the evidence-gap register."""

    READY = "ready"
    NEEDS_MORE_EVIDENCE = "needs-more-evidence"
    BLOCKED = "blocked"


WAVE_SIX_REQUIRED_GAP_KINDS: tuple[WaveSixGapKind, ...] = (
    WaveSixGapKind.CI_VERIFICATION_GAP,
    WaveSixGapKind.REQUIRED_EVIDENCE_GAP,
    WaveSixGapKind.FINGERPRINT_REPRODUCTION_GAP,
    WaveSixGapKind.TRANSFER_EVIDENCE_GAP,
    WaveSixGapKind.FALSIFICATION_EVIDENCE_GAP,
    WaveSixGapKind.HUMAN_REVIEW_GAP,
    WaveSixGapKind.INDEPENDENT_REVIEW_GAP,
    WaveSixGapKind.CLAIM_BOUNDARY_GAP,
    WaveSixGapKind.PUBLIC_WORDING_GAP,
)


@dataclass(frozen=True, slots=True)
class WaveSixEvidenceGap:
    """One explicit evidence gap or resolved gap check."""

    gap_id: str
    kind: WaveSixGapKind
    severity: WaveSixGapSeverity
    state: WaveSixGapState
    disposition: WaveSixGapDisposition
    summary: str
    affected_artifact_ids: tuple[str, ...]
    required_evidence_ids: tuple[str, ...]
    mitigation_summary: str
    reviewer_question: str
    evidence_ids: tuple[str, ...] = ()
    requires_follow_up: bool = False
    blocks_review: bool = False
    claim_boundary_impact: bool = False
    schema_version: str = WAVE_SIX_GAP_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate evidence-gap semantics and fail-closed states."""

        object.__setattr__(self, "gap_id", _require_non_empty(self.gap_id, "gap_id"))
        object.__setattr__(self, "summary", _require_non_empty(self.summary, "summary"))
        object.__setattr__(
            self,
            "affected_artifact_ids",
            _normalize_unique_text_tuple(
                self.affected_artifact_ids,
                label="affected_artifact_id",
            ),
        )
        object.__setattr__(
            self,
            "required_evidence_ids",
            _normalize_unique_text_tuple(
                self.required_evidence_ids,
                label="required_evidence_id",
            ),
        )
        object.__setattr__(
            self,
            "mitigation_summary",
            _require_non_empty(self.mitigation_summary, "mitigation_summary"),
        )
        object.__setattr__(
            self,
            "reviewer_question",
            _require_non_empty(self.reviewer_question, "reviewer_question"),
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
        if not self.affected_artifact_ids:
            raise ValueError("Wave 6 evidence gaps require affected artifacts.")
        if not self.required_evidence_ids:
            raise ValueError("Wave 6 evidence gaps require required evidence ids.")
        if self.state is WaveSixGapState.RESOLVED and self.missing_evidence_ids:
            raise ValueError("Resolved evidence gaps require all required evidence.")
        if self.state is WaveSixGapState.BLOCKING:
            if not self.blocks_review:
                raise ValueError("Blocking evidence gaps must block review.")
            if self.disposition is not WaveSixGapDisposition.BLOCK_WAVE_SIX_REVIEW:
                raise ValueError("Blocking evidence gaps must use block disposition.")
        if (
            self.disposition is WaveSixGapDisposition.BLOCK_WAVE_SIX_REVIEW
            and not self.blocks_review
        ):
            raise ValueError("Block disposition must block review.")
        if self.severity is WaveSixGapSeverity.CRITICAL:
            if self.disposition is WaveSixGapDisposition.ACCEPT_BOUNDED_RISK:
                raise ValueError("Critical evidence gaps cannot be accepted as risk.")
            if self.state is WaveSixGapState.ACCEPTED_FOR_BOUNDED_REVIEW:
                raise ValueError("Critical evidence gaps cannot be accepted.")
        if self.state is WaveSixGapState.OPEN and not self.requires_follow_up:
            raise ValueError("Open evidence gaps require follow-up.")
        if self.requires_follow_up and self.state is WaveSixGapState.RESOLVED:
            raise ValueError("Resolved evidence gaps cannot require follow-up.")

    @property
    def missing_evidence_ids(self) -> tuple[str, ...]:
        """Return required evidence ids not present in the gap record."""

        present = set(self.evidence_ids)
        return tuple(
            evidence_id
            for evidence_id in self.required_evidence_ids
            if evidence_id not in present
        )

    @property
    def evidence_complete(self) -> bool:
        """Return whether all required evidence ids are present."""

        return not self.missing_evidence_ids

    @property
    def resolved(self) -> bool:
        """Return whether this gap is fully resolved."""

        return self.state is WaveSixGapState.RESOLVED and self.evidence_complete

    @property
    def accepted_for_bounded_review(self) -> bool:
        """Return whether this gap is accepted as bounded non-critical risk."""

        return (
            self.state is WaveSixGapState.ACCEPTED_FOR_BOUNDED_REVIEW
            and self.disposition is WaveSixGapDisposition.ACCEPT_BOUNDED_RISK
            and self.severity is not WaveSixGapSeverity.CRITICAL
        )

    @property
    def needs_more_evidence(self) -> bool:
        """Return whether this gap still needs evidence."""

        return (
            self.state is WaveSixGapState.OPEN
            or self.requires_follow_up
            or (
                bool(self.missing_evidence_ids) and not self.accepted_for_bounded_review
            )
        )

    @property
    def blocks_bounded_review(self) -> bool:
        """Return whether this gap blocks Wave 6 interpretation."""

        return (
            self.blocks_review
            or self.state is WaveSixGapState.BLOCKING
            or self.disposition is WaveSixGapDisposition.BLOCK_WAVE_SIX_REVIEW
        )

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic gap payload for hashing and review."""

        return {
            "affected_artifact_ids": list(self.affected_artifact_ids),
            "blocks_review": self.blocks_review,
            "claim_boundary_impact": self.claim_boundary_impact,
            "disposition": self.disposition.value,
            "evidence_complete": self.evidence_complete,
            "evidence_ids": list(self.evidence_ids),
            "gap_id": self.gap_id,
            "kind": self.kind.value,
            "missing_evidence_ids": list(self.missing_evidence_ids),
            "mitigation_summary": self.mitigation_summary,
            "required_evidence_ids": list(self.required_evidence_ids),
            "requires_follow_up": self.requires_follow_up,
            "reviewer_question": self.reviewer_question,
            "schema_version": self.schema_version,
            "severity": self.severity.value,
            "state": self.state.value,
            "summary": self.summary,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this gap."""

        return _stable_sha256(self.canonical_payload())


@dataclass(frozen=True, slots=True)
class WaveSixEvidenceGapRegister:
    """Fail-closed register of Wave 6 evidence gaps."""

    register_id: str
    gaps: tuple[WaveSixEvidenceGap, ...]
    decision: WaveSixGapRegisterDecision
    claim_boundary_statement: str
    generated_by_engine_id: str
    human_authority_id: str
    independent_reviewer_id: str
    required_gap_kinds: tuple[WaveSixGapKind, ...] = WAVE_SIX_REQUIRED_GAP_KINDS
    claims_agi: bool = False
    claims_production_ready: bool = False
    claims_certified: bool = False
    allows_autonomous_authority: bool = False
    notes: tuple[str, ...] = ()
    schema_version: str = WAVE_SIX_GAP_REGISTER_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate gap coverage, authority fields, and decision semantics."""

        object.__setattr__(
            self,
            "register_id",
            _require_non_empty(self.register_id, "register_id"),
        )
        if not self.gaps:
            raise ValueError("Wave 6 evidence-gap registers require gaps.")
        sorted_gaps = tuple(sorted(self.gaps, key=lambda gap: gap.gap_id))
        _require_unique_text((gap.gap_id for gap in sorted_gaps), label="gap_id")
        _require_unique_enum((gap.kind for gap in sorted_gaps), label="gap kind")
        object.__setattr__(self, "gaps", sorted_gaps)
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
            "required_gap_kinds",
            _normalize_unique_enum_tuple(
                self.required_gap_kinds,
                label="required gap kind",
            ),
        )
        object.__setattr__(
            self,
            "notes",
            _normalize_unique_text_tuple(self.notes, label="register note"),
        )
        object.__setattr__(
            self,
            "schema_version",
            _require_non_empty(self.schema_version, "schema_version"),
        )
        if self.decision is WaveSixGapRegisterDecision.READY_FOR_BOUNDED_REVIEW:
            if self.missing_gap_kinds:
                raise ValueError("Ready gap registers require every gap kind.")
            if self.follow_up_gap_ids:
                raise ValueError("Ready gap registers cannot need follow-up.")
            if self.blocking_gap_ids:
                raise ValueError("Ready gap registers cannot include blockers.")
            if self.overclaim_present:
                raise ValueError("Ready gap registers cannot contain overclaims.")
            if not self.claim_boundary_statement_valid:
                raise ValueError("Ready gap registers require valid claim boundary.")
        if (
            self.decision is WaveSixGapRegisterDecision.BLOCK_REVIEW
            and not self.blocking_gap_ids
            and not self.overclaim_present
        ):
            raise ValueError("Blocked gap registers require blocker or overclaim.")

    @property
    def gap_ids(self) -> tuple[str, ...]:
        """Return gap ids in deterministic order."""

        return tuple(gap.gap_id for gap in self.gaps)

    @property
    def present_gap_kinds(self) -> tuple[WaveSixGapKind, ...]:
        """Return required gap kinds represented by the register."""

        present = {gap.kind for gap in self.gaps}
        return tuple(kind for kind in self.required_gap_kinds if kind in present)

    @property
    def missing_gap_kinds(self) -> tuple[WaveSixGapKind, ...]:
        """Return required gap kinds missing from the register."""

        present = {gap.kind for gap in self.gaps}
        return tuple(kind for kind in self.required_gap_kinds if kind not in present)

    @property
    def resolved_gap_ids(self) -> tuple[str, ...]:
        """Return fully resolved gap ids."""

        return tuple(gap.gap_id for gap in self.gaps if gap.resolved)

    @property
    def accepted_risk_gap_ids(self) -> tuple[str, ...]:
        """Return non-critical gaps accepted for bounded review."""

        return tuple(gap.gap_id for gap in self.gaps if gap.accepted_for_bounded_review)

    @property
    def follow_up_gap_ids(self) -> tuple[str, ...]:
        """Return gap ids that still need evidence."""

        return tuple(gap.gap_id for gap in self.gaps if gap.needs_more_evidence)

    @property
    def blocking_gap_ids(self) -> tuple[str, ...]:
        """Return gap ids that block bounded review."""

        return tuple(gap.gap_id for gap in self.gaps if gap.blocks_bounded_review)

    @property
    def claim_boundary_gap_ids(self) -> tuple[str, ...]:
        """Return gap ids that affect the claim boundary."""

        return tuple(gap.gap_id for gap in self.gaps if gap.claim_boundary_impact)

    @property
    def overclaim_present(self) -> bool:
        """Return whether the register violates the claim boundary."""

        return (
            self.claims_agi
            or self.claims_production_ready
            or self.claims_certified
            or self.allows_autonomous_authority
        )

    @property
    def claim_boundary_statement_valid(self) -> bool:
        """Return whether the register preserves bounded review language."""

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
    def status(self) -> WaveSixGapRegisterStatus:
        """Return fail-closed evidence-gap register status."""

        if self.overclaim_present or self.blocking_gap_ids:
            return WaveSixGapRegisterStatus.BLOCKED
        if (
            self.missing_gap_kinds
            or self.follow_up_gap_ids
            or not self.claim_boundary_statement_valid
        ):
            return WaveSixGapRegisterStatus.NEEDS_MORE_EVIDENCE
        return WaveSixGapRegisterStatus.READY

    @property
    def ready_for_bounded_review(self) -> bool:
        """Return whether the gap register can support bounded review."""

        return self.status is WaveSixGapRegisterStatus.READY

    def gap_for_kind(self, kind: WaveSixGapKind) -> WaveSixEvidenceGap | None:
        """Return the gap record for a kind, if present."""

        for gap in self.gaps:
            if gap.kind is kind:
                return gap
        return None

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic register payload for hashing and review."""

        return {
            "accepted_risk_gap_ids": list(self.accepted_risk_gap_ids),
            "allows_autonomous_authority": self.allows_autonomous_authority,
            "blocking_gap_ids": list(self.blocking_gap_ids),
            "claim_boundary_gap_ids": list(self.claim_boundary_gap_ids),
            "claim_boundary_statement": self.claim_boundary_statement,
            "claim_boundary_statement_valid": self.claim_boundary_statement_valid,
            "claims_agi": self.claims_agi,
            "claims_certified": self.claims_certified,
            "claims_production_ready": self.claims_production_ready,
            "decision": self.decision.value,
            "follow_up_gap_ids": list(self.follow_up_gap_ids),
            "gap_ids": list(self.gap_ids),
            "gaps": [gap.canonical_payload() for gap in self.gaps],
            "generated_by_engine_id": self.generated_by_engine_id,
            "human_authority_id": self.human_authority_id,
            "independent_reviewer_id": self.independent_reviewer_id,
            "missing_gap_kinds": [kind.value for kind in self.missing_gap_kinds],
            "notes": list(self.notes),
            "present_gap_kinds": [kind.value for kind in self.present_gap_kinds],
            "register_id": self.register_id,
            "required_gap_kinds": [kind.value for kind in self.required_gap_kinds],
            "resolved_gap_ids": list(self.resolved_gap_ids),
            "schema_version": self.schema_version,
            "status": self.status.value,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this register."""

        return _stable_sha256(self.canonical_payload())


def build_wave_six_gap_register(
    *,
    register_id: str,
    gaps: Iterable[WaveSixEvidenceGap],
    decision: WaveSixGapRegisterDecision,
    claim_boundary_statement: str,
    generated_by_engine_id: str,
    human_authority_id: str,
    independent_reviewer_id: str,
    notes: Iterable[str] = (),
) -> WaveSixEvidenceGapRegister:
    """Build a deterministic Wave 6 evidence-gap register."""

    return WaveSixEvidenceGapRegister(
        register_id=register_id,
        gaps=tuple(gaps),
        decision=decision,
        claim_boundary_statement=claim_boundary_statement,
        generated_by_engine_id=generated_by_engine_id,
        human_authority_id=human_authority_id,
        independent_reviewer_id=independent_reviewer_id,
        notes=tuple(notes),
    )


def required_wave_six_gap_kinds() -> tuple[WaveSixGapKind, ...]:
    """Return required evidence-gap kinds for Wave 6 review."""

    return WAVE_SIX_REQUIRED_GAP_KINDS


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
