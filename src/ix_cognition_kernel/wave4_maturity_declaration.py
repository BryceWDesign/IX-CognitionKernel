"""Wave 4 bounded maturity-declaration records.

A Wave 4 declaration is not self-certification, AGI, independent validation, or
deployment permission. It is a bounded statement that the human-review packet is
ready to be reviewed as a controlled proto-candidate evidence package. This
module preserves that boundary with explicit fail-closed gates.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, TypeVar

from ix_cognition_kernel.wave4_contracts import (
    WaveFourArtifactBundle,
    WaveFourArtifactDecision,
    WaveFourArtifactKind,
    WaveFourArtifactRef,
    WaveFourAuthorityState,
    WaveFourCapabilityArea,
    WaveFourEvidenceLink,
    WaveFourEvidenceRelation,
    WaveFourSourceSystem,
)
from ix_cognition_kernel.wave4_review_packet import (
    WaveFourHumanReviewPacket,
    WaveFourHumanReviewPacketStatus,
)

T = TypeVar("T")

WAVE_FOUR_MATURITY_DECLARATION_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave4-maturity-declaration-v1"
)


class WaveFourMaturityDeclarationStatus(StrEnum):
    """Fail-closed status for a bounded Wave 4 declaration."""

    DECLARABLE_FOR_HUMAN_REVIEW = "declarable-for-human-review"
    NEEDS_EVIDENCE = "needs-evidence"
    NEEDS_REPAIR = "needs-repair"
    BLOCKED = "blocked"


class WaveFourMaturityDeclarationDecision(StrEnum):
    """Decision produced by a bounded maturity-declaration gate."""

    DECLARE_WAVE_FOUR_REVIEW_READY = "declare-wave-four-review-ready"
    HOLD_FOR_EVIDENCE = "hold-for-evidence"
    HOLD_FOR_REPAIR = "hold-for-repair"
    BLOCK_DECLARATION = "block-declaration"


class WaveFourMaturityBoundaryKind(StrEnum):
    """Boundary checks that prevent Wave 4 declaration overclaim."""

    REVIEW_PACKET_READY = "review-packet-ready"
    EVIDENCE_BOUND = "evidence-bound"
    HUMAN_REVIEW_REQUIRED = "human-review-required"
    NO_AUTOMATIC_EXECUTION = "no-automatic-execution"
    NO_AUTOMATIC_PROMOTION = "no-automatic-promotion"
    NO_AGI_CLAIM = "no-agi-claim"
    NO_INDEPENDENT_VALIDATION_CLAIM = "no-independent-validation-claim"
    NO_PRODUCTION_CLAIM = "no-production-claim"


REQUIRED_WAVE_FOUR_MATURITY_BOUNDARIES: tuple[WaveFourMaturityBoundaryKind, ...] = (
    WaveFourMaturityBoundaryKind.REVIEW_PACKET_READY,
    WaveFourMaturityBoundaryKind.EVIDENCE_BOUND,
    WaveFourMaturityBoundaryKind.HUMAN_REVIEW_REQUIRED,
    WaveFourMaturityBoundaryKind.NO_AUTOMATIC_EXECUTION,
    WaveFourMaturityBoundaryKind.NO_AUTOMATIC_PROMOTION,
    WaveFourMaturityBoundaryKind.NO_AGI_CLAIM,
    WaveFourMaturityBoundaryKind.NO_INDEPENDENT_VALIDATION_CLAIM,
    WaveFourMaturityBoundaryKind.NO_PRODUCTION_CLAIM,
)


@dataclass(frozen=True, slots=True)
class WaveFourMaturityBoundaryCheck:
    """One boundary check used by a Wave 4 maturity declaration."""

    check_id: str
    boundary_kind: WaveFourMaturityBoundaryKind
    passed: bool
    summary: str
    evidence_ids: tuple[str, ...] = ()
    failure_summary: str = ""
    source_system: WaveFourSourceSystem = WaveFourSourceSystem.IX_COGNITION_KERNEL

    def __post_init__(self) -> None:
        """Validate boundary identity and pass/fail accounting."""

        object.__setattr__(self, "check_id", _text(self.check_id, "check_id"))
        object.__setattr__(self, "summary", _text(self.summary, "summary"))
        object.__setattr__(
            self,
            "evidence_ids",
            _unique_text(self.evidence_ids, label="maturity boundary evidence_id"),
        )
        object.__setattr__(self, "failure_summary", self.failure_summary.strip())
        if self.passed and self.failure_summary:
            raise ValueError(
                "Passed Wave 4 maturity boundaries cannot carry failure text."
            )
        if not self.passed and not self.failure_summary:
            raise ValueError("Failed Wave 4 maturity boundaries require failure text.")

    @property
    def check_key(self) -> str:
        """Return deterministic uniqueness key."""

        return self.check_id

    @property
    def readiness_gap(self) -> str:
        """Return gap text when this boundary fails."""

        if self.passed:
            return ""
        return f"{self.check_id} failed: {self.failure_summary}"

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic boundary-check payload."""

        return {
            "boundary_kind": self.boundary_kind.value,
            "check_id": self.check_id,
            "evidence_ids": list(self.evidence_ids),
            "failure_summary": self.failure_summary,
            "passed": self.passed,
            "readiness_gap": self.readiness_gap,
            "source_system": self.source_system.value,
            "summary": self.summary,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint."""

        return _stable_sha256(self.canonical_payload())


@dataclass(frozen=True, slots=True)
class WaveFourMaturityDeclaration:
    """Bounded declaration that Wave 4 is ready for human review only."""

    declaration_id: str
    review_packet: WaveFourHumanReviewPacket
    boundary_checks: tuple[WaveFourMaturityBoundaryCheck, ...]
    declared_maturity_label: str = "Wave 4 proto-AGI candidate review package"
    generated_by_engine_id: str = "wave4-maturity-declaration-engine"
    reviewer_role_id: str = "wave4-maturity-declaration-reviewer"
    notes: tuple[str, ...] = ()
    blocked_reasons: tuple[str, ...] = ()
    required_boundary_kinds: tuple[WaveFourMaturityBoundaryKind, ...] = (
        REQUIRED_WAVE_FOUR_MATURITY_BOUNDARIES
    )
    permits_automatic_execution: bool = False
    permits_automatic_promotion: bool = False
    claims_agi: bool = False
    independently_validated: bool = False
    production_ready: bool = False
    schema_version: str = WAVE_FOUR_MATURITY_DECLARATION_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate declaration coverage and anti-overclaim boundaries."""

        object.__setattr__(
            self,
            "declaration_id",
            _text(self.declaration_id, "declaration_id"),
        )
        object.__setattr__(
            self,
            "declared_maturity_label",
            _text(self.declared_maturity_label, "declared_maturity_label"),
        )
        if not self.boundary_checks:
            raise ValueError("Wave 4 declarations require boundary checks.")
        checks = tuple(sorted(self.boundary_checks, key=lambda item: item.check_key))
        _unique_items((item.check_id for item in checks), "boundary check_id")
        object.__setattr__(self, "boundary_checks", checks)
        object.__setattr__(
            self,
            "generated_by_engine_id",
            _text(self.generated_by_engine_id, "generated_by_engine_id"),
        )
        object.__setattr__(
            self,
            "reviewer_role_id",
            _text(self.reviewer_role_id, "reviewer_role_id"),
        )
        object.__setattr__(
            self,
            "notes",
            _unique_text(self.notes, label="maturity declaration note"),
        )
        object.__setattr__(
            self,
            "blocked_reasons",
            _unique_text(self.blocked_reasons, label="blocked reason"),
        )
        object.__setattr__(
            self,
            "required_boundary_kinds",
            _unique_items(self.required_boundary_kinds, "required boundary kind"),
        )
        if not self.required_boundary_kinds:
            raise ValueError("Wave 4 declarations require boundary coverage.")
        object.__setattr__(
            self,
            "schema_version",
            _text(self.schema_version, "schema_version"),
        )
        if self.permits_automatic_execution:
            raise ValueError("Wave 4 declarations cannot permit execution.")
        if self.permits_automatic_promotion:
            raise ValueError("Wave 4 declarations cannot permit promotion.")
        if self.claims_agi:
            raise ValueError("Wave 4 declarations cannot claim AGI.")
        if self.independently_validated:
            raise ValueError("Wave 4 declarations cannot claim independent validation.")
        if self.production_ready:
            raise ValueError("Wave 4 declarations cannot claim production readiness.")

    @property
    def artifact_id(self) -> str:
        """Return shared Wave 4 artifact id for this declaration."""

        return f"wave4-maturity-declaration:{self.declaration_id}"

    @property
    def boundary_kinds_present(self) -> tuple[WaveFourMaturityBoundaryKind, ...]:
        """Return boundary kinds represented by checks."""

        return tuple(
            sorted(
                {check.boundary_kind for check in self.boundary_checks},
                key=lambda item: item.value,
            )
        )

    @property
    def missing_required_boundary_kinds(
        self,
    ) -> tuple[WaveFourMaturityBoundaryKind, ...]:
        """Return required boundary kinds missing from this declaration."""

        present = set(self.boundary_kinds_present)
        return tuple(
            kind for kind in self.required_boundary_kinds if kind not in present
        )

    @property
    def passed_boundary_ids(self) -> tuple[str, ...]:
        """Return passed boundary ids."""

        return tuple(check.check_id for check in self.boundary_checks if check.passed)

    @property
    def failed_boundary_ids(self) -> tuple[str, ...]:
        """Return failed boundary ids."""

        return tuple(
            check.check_id for check in self.boundary_checks if not check.passed
        )

    @property
    def all_evidence_ids(self) -> tuple[str, ...]:
        """Return sorted evidence ids from review packet and boundary checks."""

        evidence_ids = set(self.review_packet.all_evidence_ids)
        for check in self.boundary_checks:
            evidence_ids.update(check.evidence_ids)
        return tuple(sorted(evidence_ids))

    @property
    def readiness_gaps(self) -> tuple[str, ...]:
        """Return fail-closed gaps preventing declaration."""

        gaps: list[str] = []
        if self.missing_required_boundary_kinds:
            missing = ", ".join(
                kind.value for kind in self.missing_required_boundary_kinds
            )
            gaps.append(f"missing maturity boundary coverage: {missing}")
        if self.review_packet.status is not (
            WaveFourHumanReviewPacketStatus.READY_FOR_HUMAN_REVIEW
        ):
            gaps.extend(self.review_packet.readiness_gaps)
        gaps.extend(
            check.readiness_gap for check in self.boundary_checks if check.readiness_gap
        )
        if not self.review_packet.scenario_ids:
            gaps.append(f"{self.declaration_id} has no WorldTwin scenario ids")
        if not self.review_packet.blackfox_receipt_ids:
            gaps.append(f"{self.declaration_id} has no BlackFox receipt ids")
        return tuple(gaps)

    @property
    def blocking_gaps(self) -> tuple[str, ...]:
        """Return hard blocks for this maturity declaration."""

        gaps = [
            f"{self.declaration_id} blocked: {reason}"
            for reason in self.blocked_reasons
        ]
        gaps.extend(self.review_packet.blocking_gaps)
        return tuple(gaps)

    @property
    def status(self) -> WaveFourMaturityDeclarationStatus:
        """Return fail-closed declaration status."""

        if self.blocking_gaps:
            return WaveFourMaturityDeclarationStatus.BLOCKED
        if self.failed_boundary_ids:
            return WaveFourMaturityDeclarationStatus.NEEDS_REPAIR
        if self.readiness_gaps:
            return WaveFourMaturityDeclarationStatus.NEEDS_EVIDENCE
        return WaveFourMaturityDeclarationStatus.DECLARABLE_FOR_HUMAN_REVIEW

    @property
    def decision(self) -> WaveFourMaturityDeclarationDecision:
        """Return bounded maturity-declaration decision."""

        if self.status is WaveFourMaturityDeclarationStatus.BLOCKED:
            return WaveFourMaturityDeclarationDecision.BLOCK_DECLARATION
        if self.status is WaveFourMaturityDeclarationStatus.NEEDS_REPAIR:
            return WaveFourMaturityDeclarationDecision.HOLD_FOR_REPAIR
        if self.status is WaveFourMaturityDeclarationStatus.NEEDS_EVIDENCE:
            return WaveFourMaturityDeclarationDecision.HOLD_FOR_EVIDENCE
        return WaveFourMaturityDeclarationDecision.DECLARE_WAVE_FOUR_REVIEW_READY

    @property
    def declarable_for_human_review(self) -> bool:
        """Return whether the bounded Wave 4 declaration may be made."""

        return self.status is (
            WaveFourMaturityDeclarationStatus.DECLARABLE_FOR_HUMAN_REVIEW
        )

    @property
    def human_authority_state(self) -> WaveFourAuthorityState:
        """Return human-authority state for this declaration."""

        if self.status is WaveFourMaturityDeclarationStatus.BLOCKED:
            return WaveFourAuthorityState.BLOCKED
        return WaveFourAuthorityState.HUMAN_REVIEW_REQUIRED

    @property
    def review_summary(self) -> str:
        """Return concise maturity declaration summary."""

        return (
            f"{self.declaration_id}: {self.declared_maturity_label}; "
            f"{len(self.boundary_checks)} boundaries; {self.status.value}; "
            "human review only; no AGI claim."
        )

    def to_artifact_ref(self) -> WaveFourArtifactRef:
        """Convert declaration into a shared Wave 4 readiness artifact."""

        if self.status is (
            WaveFourMaturityDeclarationStatus.DECLARABLE_FOR_HUMAN_REVIEW
        ):
            decision = WaveFourArtifactDecision.READY_FOR_CONTROLLED_REVIEW
        elif self.status is WaveFourMaturityDeclarationStatus.BLOCKED:
            decision = WaveFourArtifactDecision.BLOCKED
        else:
            decision = WaveFourArtifactDecision.NEEDS_EVIDENCE
        return WaveFourArtifactRef(
            artifact_id=self.artifact_id,
            kind=WaveFourArtifactKind.READINESS_SNAPSHOT,
            capability_area=WaveFourCapabilityArea.AUDIT_TRAIL,
            source_system=WaveFourSourceSystem.IX_COGNITION_KERNEL,
            summary=self.review_summary,
            produced_by_engine_id=self.generated_by_engine_id,
            produced_by_agent_role_id=self.reviewer_role_id,
            evidence_ids=self.all_evidence_ids,
            decision=decision,
            authority_state=self.human_authority_state,
        )

    def evidence_links(self) -> tuple[WaveFourEvidenceLink, ...]:
        """Return evidence links for this declaration artifact."""

        relation = WaveFourEvidenceRelation.TESTS
        if self.status is WaveFourMaturityDeclarationStatus.BLOCKED:
            relation = WaveFourEvidenceRelation.BLOCKS
        return tuple(
            WaveFourEvidenceLink(
                evidence_id=evidence_id,
                artifact_id=self.artifact_id,
                relation=relation,
                summary=(
                    f"Evidence for bounded Wave 4 declaration {self.declaration_id}."
                ),
                source_system=WaveFourSourceSystem.LOCAL_TEST_SUITE,
            )
            for evidence_id in self.all_evidence_ids
        )

    def to_artifact_bundle(self) -> WaveFourArtifactBundle:
        """Convert this declaration into a one-artifact Wave 4 bundle."""

        return WaveFourArtifactBundle(
            bundle_id=f"wave4-maturity-declaration-bundle:{self.declaration_id}",
            artifacts=(self.to_artifact_ref(),),
            evidence_links=self.evidence_links(),
            required_kinds=(WaveFourArtifactKind.READINESS_SNAPSHOT,),
            required_capability_areas=(WaveFourCapabilityArea.AUDIT_TRAIL,),
            notes=(self.review_summary, *self.notes),
        )

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic declaration payload."""

        return {
            "all_evidence_ids": list(self.all_evidence_ids),
            "artifact_id": self.artifact_id,
            "blocking_gaps": list(self.blocking_gaps),
            "blocked_reasons": list(self.blocked_reasons),
            "boundary_checks": [
                check.canonical_payload() for check in self.boundary_checks
            ],
            "boundary_kinds_present": [
                kind.value for kind in self.boundary_kinds_present
            ],
            "claims_agi": self.claims_agi,
            "declarable_for_human_review": self.declarable_for_human_review,
            "declaration_id": self.declaration_id,
            "decision": self.decision.value,
            "declared_maturity_label": self.declared_maturity_label,
            "failed_boundary_ids": list(self.failed_boundary_ids),
            "generated_by_engine_id": self.generated_by_engine_id,
            "human_authority_state": self.human_authority_state.value,
            "independently_validated": self.independently_validated,
            "missing_required_boundary_kinds": [
                kind.value for kind in self.missing_required_boundary_kinds
            ],
            "notes": list(self.notes),
            "passed_boundary_ids": list(self.passed_boundary_ids),
            "permits_automatic_execution": self.permits_automatic_execution,
            "permits_automatic_promotion": self.permits_automatic_promotion,
            "production_ready": self.production_ready,
            "readiness_gaps": list(self.readiness_gaps),
            "required_boundary_kinds": [
                kind.value for kind in self.required_boundary_kinds
            ],
            "review_packet_id": self.review_packet.packet_id,
            "review_summary": self.review_summary,
            "reviewer_role_id": self.reviewer_role_id,
            "schema_version": self.schema_version,
            "status": self.status.value,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint."""

        return _stable_sha256(self.canonical_payload())


def build_wave_four_maturity_declaration(
    *,
    declaration_id: str,
    review_packet: WaveFourHumanReviewPacket,
) -> WaveFourMaturityDeclaration:
    """Build the standard bounded Wave 4 maturity declaration."""

    evidence_ids = review_packet.all_evidence_ids
    checks = (
        _check(
            check_id="boundary:review-packet-ready",
            boundary_kind=WaveFourMaturityBoundaryKind.REVIEW_PACKET_READY,
            passed=review_packet.status
            is WaveFourHumanReviewPacketStatus.READY_FOR_HUMAN_REVIEW,
            summary="Human-review packet is ready for review.",
            evidence_ids=evidence_ids,
            failure_summary="; ".join(
                (*review_packet.blocking_gaps, *review_packet.readiness_gaps)
            ),
        ),
        _check(
            check_id="boundary:evidence-bound",
            boundary_kind=WaveFourMaturityBoundaryKind.EVIDENCE_BOUND,
            passed=bool(review_packet.all_evidence_ids),
            summary="Declaration remains bound to packet evidence ids.",
            evidence_ids=evidence_ids,
            failure_summary="review packet has no evidence ids",
        ),
        _check(
            check_id="boundary:human-review-required",
            boundary_kind=WaveFourMaturityBoundaryKind.HUMAN_REVIEW_REQUIRED,
            passed=review_packet.human_authority_state
            is WaveFourAuthorityState.HUMAN_REVIEW_REQUIRED,
            summary="Human review remains required.",
            evidence_ids=evidence_ids,
            failure_summary="human review is not required",
        ),
        _check(
            check_id="boundary:no-automatic-execution",
            boundary_kind=WaveFourMaturityBoundaryKind.NO_AUTOMATIC_EXECUTION,
            passed=not review_packet.permits_automatic_execution,
            summary="Declaration grants no execution authority.",
            evidence_ids=evidence_ids,
            failure_summary="automatic execution was permitted",
        ),
        _check(
            check_id="boundary:no-automatic-promotion",
            boundary_kind=WaveFourMaturityBoundaryKind.NO_AUTOMATIC_PROMOTION,
            passed=not review_packet.permits_automatic_promotion,
            summary="Declaration grants no automatic maturity promotion.",
            evidence_ids=evidence_ids,
            failure_summary="automatic promotion was permitted",
        ),
        _check(
            check_id="boundary:no-agi-claim",
            boundary_kind=WaveFourMaturityBoundaryKind.NO_AGI_CLAIM,
            passed=not review_packet.claims_agi,
            summary="Declaration preserves the no-AGI-claim boundary.",
            evidence_ids=evidence_ids,
            failure_summary="AGI was claimed",
        ),
        _check(
            check_id="boundary:no-independent-validation-claim",
            boundary_kind=(
                WaveFourMaturityBoundaryKind.NO_INDEPENDENT_VALIDATION_CLAIM
            ),
            passed=not review_packet.independently_validated,
            summary="Declaration does not claim Wave 5 independent validation.",
            evidence_ids=evidence_ids,
            failure_summary="independent validation was claimed",
        ),
        _check(
            check_id="boundary:no-production-claim",
            boundary_kind=WaveFourMaturityBoundaryKind.NO_PRODUCTION_CLAIM,
            passed=True,
            summary="Declaration does not claim production readiness.",
            evidence_ids=evidence_ids,
            failure_summary="production readiness was claimed",
        ),
    )
    return WaveFourMaturityDeclaration(
        declaration_id=declaration_id,
        review_packet=review_packet,
        boundary_checks=checks,
    )


def _check(
    *,
    check_id: str,
    boundary_kind: WaveFourMaturityBoundaryKind,
    passed: bool,
    summary: str,
    evidence_ids: tuple[str, ...],
    failure_summary: str,
) -> WaveFourMaturityBoundaryCheck:
    """Build a boundary check while adding failure text only when needed."""

    return WaveFourMaturityBoundaryCheck(
        check_id=check_id,
        boundary_kind=boundary_kind,
        passed=passed,
        summary=summary,
        evidence_ids=evidence_ids,
        failure_summary="" if passed else failure_summary,
    )


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
        stripped = _text(value, label)
        if stripped in seen:
            raise ValueError(f"Duplicate {label} detected: {stripped}")
        normalized.append(stripped)
        seen.add(stripped)
    return tuple(normalized)


def _unique_items(values: Iterable[T], label: str) -> tuple[T, ...]:
    """Return tuple of unique items while rejecting duplicates."""

    normalized: list[T] = []
    seen: set[T] = set()
    for value in values:
        if value in seen:
            raise ValueError(f"Duplicate {label} detected: {value}")
        normalized.append(value)
        seen.add(value)
    return tuple(normalized)


def _stable_sha256(payload: Mapping[str, Any]) -> str:
    """Return deterministic SHA-256 over a canonical JSON payload."""

    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
