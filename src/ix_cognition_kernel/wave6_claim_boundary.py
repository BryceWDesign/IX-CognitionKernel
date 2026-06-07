"""Wave 6 claim-boundary declaration.

Wave 6 is a measured system-level cognition attempt, not an AGI claim. This
module makes that boundary a first-class, testable artifact. A declaration is
only review-ready when it preserves the allowed claim, blocks prohibited claims,
requires transfer/novelty/falsification/independent review evidence, and remains
under human authority.
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

WAVE_SIX_CLAIM_BOUNDARY_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave6-claim-boundary-v1"
)
WAVE_SIX_CLAIM_BOUNDARY_ASSESSMENT_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave6-claim-boundary-assessment-v1"
)


class WaveSixAllowedClaim(StrEnum):
    """Claims allowed for a bounded Wave 6 package."""

    MEASURED_SYSTEM_LEVEL_COGNITION_ATTEMPT = (
        "measured-system-level-cognition-attempt"
    )
    BOUNDED_WAVE_SIX_REVIEW_READY = "bounded-wave-six-review-ready"
    EVIDENCE_PACKAGE_ASSEMBLED = "evidence-package-assembled"
    EXTERNAL_REVIEW_CANDIDATE = "external-review-candidate"


class WaveSixProhibitedClaim(StrEnum):
    """Claims that must remain blocked unless future evidence changes the project."""

    AGI_ACHIEVED = "agi-achieved"
    PRODUCTION_READY = "production-ready"
    CERTIFIED_SAFE = "certified-safe"
    AUTONOMOUS_AUTHORITY_GRANTED = "autonomous-authority-granted"
    SELF_VALIDATED_INTELLIGENCE = "self-validated-intelligence"
    HUMAN_REVIEW_NOT_REQUIRED = "human-review-not-required"
    TRANSFER_PROVEN_UNIVERSALLY = "transfer-proven-universally"


class WaveSixClaimPrerequisite(StrEnum):
    """Evidence prerequisites before the allowed Wave 6 claim can be reviewed."""

    CLEAN_MASTER_LOOP = "clean-master-loop"
    REALITY_CORRECTED_REASONING = "reality-corrected-reasoning"
    FUTURE_REASONING_CHANGED = "future-reasoning-changed"
    CROSS_DOMAIN_TRANSFER_PRESSURE = "cross-domain-transfer-pressure"
    NOVELTY_PRESSURE = "novelty-pressure"
    NEGATIVE_CONTROL_PRESSURE = "negative-control-pressure"
    FALSIFICATION_SURVIVAL = "falsification-survival"
    HUMAN_REVIEW_APPROVAL = "human-review-approval"
    INDEPENDENT_REVIEW_PACKET = "independent-review-packet"


class WaveSixClaimBoundaryDecision(StrEnum):
    """Fail-closed decisions for claim-boundary declarations."""

    READY_FOR_BOUNDED_REVIEW = "ready-for-bounded-review"
    NEEDS_MORE_EVIDENCE = "needs-more-evidence"
    BLOCKED = "blocked"


WAVE_SIX_REQUIRED_ALLOWED_CLAIMS: tuple[WaveSixAllowedClaim, ...] = (
    WaveSixAllowedClaim.MEASURED_SYSTEM_LEVEL_COGNITION_ATTEMPT,
    WaveSixAllowedClaim.BOUNDED_WAVE_SIX_REVIEW_READY,
    WaveSixAllowedClaim.EVIDENCE_PACKAGE_ASSEMBLED,
    WaveSixAllowedClaim.EXTERNAL_REVIEW_CANDIDATE,
)

WAVE_SIX_REQUIRED_PROHIBITED_CLAIMS: tuple[WaveSixProhibitedClaim, ...] = (
    WaveSixProhibitedClaim.AGI_ACHIEVED,
    WaveSixProhibitedClaim.PRODUCTION_READY,
    WaveSixProhibitedClaim.CERTIFIED_SAFE,
    WaveSixProhibitedClaim.AUTONOMOUS_AUTHORITY_GRANTED,
    WaveSixProhibitedClaim.SELF_VALIDATED_INTELLIGENCE,
    WaveSixProhibitedClaim.HUMAN_REVIEW_NOT_REQUIRED,
    WaveSixProhibitedClaim.TRANSFER_PROVEN_UNIVERSALLY,
)

WAVE_SIX_REQUIRED_CLAIM_PREREQUISITES: tuple[WaveSixClaimPrerequisite, ...] = (
    WaveSixClaimPrerequisite.CLEAN_MASTER_LOOP,
    WaveSixClaimPrerequisite.REALITY_CORRECTED_REASONING,
    WaveSixClaimPrerequisite.FUTURE_REASONING_CHANGED,
    WaveSixClaimPrerequisite.CROSS_DOMAIN_TRANSFER_PRESSURE,
    WaveSixClaimPrerequisite.NOVELTY_PRESSURE,
    WaveSixClaimPrerequisite.NEGATIVE_CONTROL_PRESSURE,
    WaveSixClaimPrerequisite.FALSIFICATION_SURVIVAL,
    WaveSixClaimPrerequisite.HUMAN_REVIEW_APPROVAL,
    WaveSixClaimPrerequisite.INDEPENDENT_REVIEW_PACKET,
)


@dataclass(frozen=True, slots=True)
class WaveSixClaimBoundaryDeclaration:
    """Explicit declaration of what Wave 6 may and may not claim."""

    declaration_id: str
    boundary_statement: str
    allowed_claims: tuple[WaveSixAllowedClaim, ...]
    prohibited_claims: tuple[WaveSixProhibitedClaim, ...]
    satisfied_prerequisites: tuple[WaveSixClaimPrerequisite, ...]
    evidence_ids: tuple[str, ...]
    reviewer_questions: tuple[str, ...]
    decision: WaveSixClaimBoundaryDecision = (
        WaveSixClaimBoundaryDecision.NEEDS_MORE_EVIDENCE
    )
    human_authority_required: bool = True
    independent_review_required: bool = True
    claims_agi: bool = False
    claims_production_ready: bool = False
    claims_certified: bool = False
    allows_autonomous_authority: bool = False
    self_validated: bool = False
    schema_version: str = WAVE_SIX_CLAIM_BOUNDARY_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate the boundary declaration and block overclaims."""

        if not self.human_authority_required:
            raise ValueError("Claim-boundary declarations require human authority.")
        if not self.independent_review_required:
            raise ValueError("Claim-boundary declarations require independent review.")
        if self.claims_agi:
            raise ValueError("Claim-boundary declarations must not claim AGI.")
        if self.claims_production_ready:
            raise ValueError(
                "Claim-boundary declarations must not claim production readiness."
            )
        if self.claims_certified:
            raise ValueError(
                "Claim-boundary declarations must not claim certification."
            )
        if self.allows_autonomous_authority:
            raise ValueError(
                "Claim-boundary declarations must not allow autonomous authority."
            )
        if self.self_validated:
            raise ValueError(
                "Claim-boundary declarations must not claim self-validation."
            )
        object.__setattr__(
            self,
            "declaration_id",
            _require_non_empty(self.declaration_id, "declaration_id"),
        )
        object.__setattr__(
            self,
            "boundary_statement",
            _require_non_empty(self.boundary_statement, "boundary_statement"),
        )
        object.__setattr__(
            self,
            "allowed_claims",
            _normalize_unique_enum_tuple(self.allowed_claims, label="allowed claim"),
        )
        object.__setattr__(
            self,
            "prohibited_claims",
            _normalize_unique_enum_tuple(
                self.prohibited_claims, label="prohibited claim"
            ),
        )
        object.__setattr__(
            self,
            "satisfied_prerequisites",
            _normalize_unique_enum_tuple(
                self.satisfied_prerequisites,
                label="satisfied prerequisite",
            ),
        )
        object.__setattr__(
            self,
            "evidence_ids",
            _normalize_unique_text_tuple(self.evidence_ids, label="evidence_id"),
        )
        object.__setattr__(
            self,
            "reviewer_questions",
            _normalize_unique_text_tuple(
                self.reviewer_questions,
                label="reviewer_question",
            ),
        )
        object.__setattr__(
            self,
            "schema_version",
            _require_non_empty(self.schema_version, "schema_version"),
        )
        if not self.allowed_claims:
            raise ValueError("Claim-boundary declarations require allowed claims.")
        if not self.prohibited_claims:
            raise ValueError("Claim-boundary declarations require prohibited claims.")
        if not self.evidence_ids:
            raise ValueError("Claim-boundary declarations require evidence ids.")
        if not self.reviewer_questions:
            raise ValueError("Claim-boundary declarations require reviewer questions.")
        missing_allowed = tuple(
            claim
            for claim in WAVE_SIX_REQUIRED_ALLOWED_CLAIMS
            if claim not in self.allowed_claims
        )
        if missing_allowed:
            raise ValueError(
                "Claim-boundary declarations must include allowed claim: "
                f"{missing_allowed[0].value}"
            )
        missing_prohibited = tuple(
            claim
            for claim in WAVE_SIX_REQUIRED_PROHIBITED_CLAIMS
            if claim not in self.prohibited_claims
        )
        if missing_prohibited:
            raise ValueError(
                "Claim-boundary declarations must block prohibited claim: "
                f"{missing_prohibited[0].value}"
            )
        if (
            self.decision is WaveSixClaimBoundaryDecision.READY_FOR_BOUNDED_REVIEW
            and self.missing_prerequisites
        ):
            raise ValueError(
                "Ready claim-boundary declarations require all prerequisites."
            )
        if self.decision is WaveSixClaimBoundaryDecision.BLOCKED and not any(
            evidence_id.startswith("block-") for evidence_id in self.evidence_ids
        ):
            raise ValueError("Blocked declarations require blocking evidence.")

    @property
    def missing_prerequisites(self) -> tuple[WaveSixClaimPrerequisite, ...]:
        """Return required claim prerequisites not yet satisfied."""

        present = set(self.satisfied_prerequisites)
        return tuple(
            prerequisite
            for prerequisite in WAVE_SIX_REQUIRED_CLAIM_PREREQUISITES
            if prerequisite not in present
        )

    @property
    def ready_for_bounded_review(self) -> bool:
        """Return whether the declaration can enter bounded Wave 6 review."""

        return (
            self.decision is WaveSixClaimBoundaryDecision.READY_FOR_BOUNDED_REVIEW
            and not self.missing_prerequisites
        )

    @property
    def blocks_claim(self) -> bool:
        """Return whether the declaration blocks Wave 6 interpretation."""

        return self.decision is WaveSixClaimBoundaryDecision.BLOCKED

    @property
    def preserves_no_agi_boundary(self) -> bool:
        """Return whether the declaration explicitly blocks AGI overclaiming."""

        return (
            WaveSixProhibitedClaim.AGI_ACHIEVED in self.prohibited_claims
            and not self.claims_agi
        )

    @property
    def preserves_human_authority(self) -> bool:
        """Return whether human authority remains required."""

        return (
            self.human_authority_required
            and not self.allows_autonomous_authority
            and WaveSixProhibitedClaim.AUTONOMOUS_AUTHORITY_GRANTED
            in self.prohibited_claims
        )

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic payload for review and hashing."""

        return {
            "allowed_claims": [claim.value for claim in self.allowed_claims],
            "allows_autonomous_authority": self.allows_autonomous_authority,
            "boundary_statement": self.boundary_statement,
            "claims_agi": self.claims_agi,
            "claims_certified": self.claims_certified,
            "claims_production_ready": self.claims_production_ready,
            "declaration_id": self.declaration_id,
            "decision": self.decision.value,
            "evidence_ids": list(self.evidence_ids),
            "human_authority_required": self.human_authority_required,
            "independent_review_required": self.independent_review_required,
            "missing_prerequisites": [
                prerequisite.value for prerequisite in self.missing_prerequisites
            ],
            "prohibited_claims": [claim.value for claim in self.prohibited_claims],
            "reviewer_questions": list(self.reviewer_questions),
            "satisfied_prerequisites": [
                prerequisite.value for prerequisite in self.satisfied_prerequisites
            ],
            "schema_version": self.schema_version,
            "self_validated": self.self_validated,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this declaration."""

        return _stable_sha256(self.canonical_payload())


@dataclass(frozen=True, slots=True)
class WaveSixClaimBoundaryAssessment:
    """Assessment over one or more claim-boundary declarations."""

    assessment_id: str
    declarations: tuple[WaveSixClaimBoundaryDeclaration, ...]
    required_declarations: int = 1
    notes: tuple[str, ...] = ()
    schema_version: str = WAVE_SIX_CLAIM_BOUNDARY_ASSESSMENT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate declaration uniqueness and assessment threshold."""

        object.__setattr__(
            self,
            "assessment_id",
            _require_non_empty(self.assessment_id, "assessment_id"),
        )
        if not self.declarations:
            raise ValueError("Claim-boundary assessments require declarations.")
        sorted_declarations = tuple(
            sorted(
                self.declarations,
                key=lambda declaration: declaration.declaration_id,
            )
        )
        _unique_ids(
            (declaration.declaration_id for declaration in sorted_declarations),
            label="declaration_id",
        )
        object.__setattr__(self, "declarations", sorted_declarations)
        if self.required_declarations < 1:
            raise ValueError("required_declarations must be at least 1.")
        object.__setattr__(
            self,
            "notes",
            _normalize_unique_text_tuple(self.notes, label="assessment note"),
        )
        object.__setattr__(
            self,
            "schema_version",
            _require_non_empty(self.schema_version, "schema_version"),
        )

    @property
    def declaration_ids(self) -> tuple[str, ...]:
        """Return declaration ids in deterministic order."""

        return tuple(declaration.declaration_id for declaration in self.declarations)

    @property
    def ready_declaration_ids(self) -> tuple[str, ...]:
        """Return declarations ready for bounded Wave 6 review."""

        return tuple(
            declaration.declaration_id
            for declaration in self.declarations
            if declaration.ready_for_bounded_review
        )

    @property
    def blocked_declaration_ids(self) -> tuple[str, ...]:
        """Return declarations that block Wave 6 interpretation."""

        return tuple(
            declaration.declaration_id
            for declaration in self.declarations
            if declaration.blocks_claim
        )

    @property
    def declarations_missing_prerequisites(self) -> tuple[str, ...]:
        """Return declarations that still lack required prerequisites."""

        return tuple(
            declaration.declaration_id
            for declaration in self.declarations
            if declaration.missing_prerequisites
        )

    @property
    def has_required_ready_declarations(self) -> bool:
        """Return whether enough declarations are ready for bounded review."""

        return len(self.ready_declaration_ids) >= self.required_declarations

    @property
    def ready_for_wave_six_review(self) -> bool:
        """Return whether claim boundaries can support Wave 6 review."""

        return self.has_required_ready_declarations and not self.blocked_declaration_ids

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic assessment payload for hashing and review."""

        return {
            "assessment_id": self.assessment_id,
            "blocked_declaration_ids": list(self.blocked_declaration_ids),
            "declarations": [
                declaration.canonical_payload()
                for declaration in self.declarations
            ],
            "declarations_missing_prerequisites": list(
                self.declarations_missing_prerequisites
            ),
            "has_required_ready_declarations": self.has_required_ready_declarations,
            "notes": list(self.notes),
            "ready_declaration_ids": list(self.ready_declaration_ids),
            "ready_for_wave_six_review": self.ready_for_wave_six_review,
            "required_declarations": self.required_declarations,
            "schema_version": self.schema_version,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this assessment."""

        return _stable_sha256(self.canonical_payload())


def build_wave_six_claim_boundary_assessment(
    *,
    assessment_id: str,
    declarations: Iterable[WaveSixClaimBoundaryDeclaration],
    required_declarations: int = 1,
    notes: Iterable[str] = (),
) -> WaveSixClaimBoundaryAssessment:
    """Build a deterministic claim-boundary assessment."""

    return WaveSixClaimBoundaryAssessment(
        assessment_id=assessment_id,
        declarations=tuple(declarations),
        required_declarations=required_declarations,
        notes=tuple(notes),
    )


def required_wave_six_allowed_claims() -> tuple[WaveSixAllowedClaim, ...]:
    """Return allowed claims for bounded Wave 6 language."""

    return WAVE_SIX_REQUIRED_ALLOWED_CLAIMS


def required_wave_six_prohibited_claims() -> tuple[WaveSixProhibitedClaim, ...]:
    """Return claims that Wave 6 must explicitly block."""

    return WAVE_SIX_REQUIRED_PROHIBITED_CLAIMS


def required_wave_six_claim_prerequisites() -> tuple[WaveSixClaimPrerequisite, ...]:
    """Return prerequisites for bounded Wave 6 review language."""

    return WAVE_SIX_REQUIRED_CLAIM_PREREQUISITES


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
