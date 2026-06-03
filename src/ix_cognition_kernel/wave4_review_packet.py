"""Wave 4 human-review packet records.

Wave 4 does not promote itself. A ready scorecard can only become a reviewable
human-review packet that preserves evidence, gates, reviewer roles, BlackFox
receipts, WorldTwin scenarios, and anti-overclaim boundaries. This module makes
that handoff explicit without granting automatic execution, claiming AGI, or
claiming independent validation.
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
from ix_cognition_kernel.wave4_scorecard import (
    WaveFourProtoCandidateScorecard,
    WaveFourScorecardGateSeverity,
    WaveFourScorecardStatus,
)

T = TypeVar("T")

WAVE_FOUR_REVIEW_REQUIREMENT_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave4-review-requirement-v1"
)
WAVE_FOUR_HUMAN_REVIEW_PACKET_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave4-human-review-packet-v1"
)


class WaveFourReviewRequirementKind(StrEnum):
    """Requirement kinds for handing Wave 4 evidence to humans."""

    SCORECARD_READY = "scorecard-ready"
    EVIDENCE_TRACEABLE = "evidence-traceable"
    SCENARIO_CONTEXT_ATTACHED = "scenario-context-attached"
    BLACKFOX_RECEIPTS_ATTACHED = "blackfox-receipts-attached"
    HUMAN_AUTHORITY_PRESERVED = "human-authority-preserved"
    REVIEWER_ROLES_ASSIGNED = "reviewer-roles-assigned"
    NO_AUTOMATIC_PROMOTION = "no-automatic-promotion"
    NO_AUTOMATIC_EXECUTION = "no-automatic-execution"
    NO_AGI_CLAIM = "no-agi-claim"
    NO_INDEPENDENT_VALIDATION_CLAIM = "no-independent-validation-claim"


class WaveFourHumanReviewPacketStatus(StrEnum):
    """Fail-closed status for a Wave 4 human-review packet."""

    READY_FOR_HUMAN_REVIEW = "ready-for-human-review"
    NEEDS_EVIDENCE = "needs-evidence"
    NEEDS_REPAIR = "needs-repair"
    BLOCKED = "blocked"


class WaveFourHumanReviewDecision(StrEnum):
    """Decision produced by a Wave 4 human-review packet gate."""

    SUBMIT_FOR_HUMAN_REVIEW = "submit-for-human-review"
    HOLD_FOR_EVIDENCE = "hold-for-evidence"
    HOLD_FOR_REPAIR = "hold-for-repair"
    BLOCK_REVIEW = "block-review"


REQUIRED_WAVE_FOUR_REVIEW_REQUIREMENT_KINDS: tuple[
    WaveFourReviewRequirementKind, ...
] = (
    WaveFourReviewRequirementKind.SCORECARD_READY,
    WaveFourReviewRequirementKind.EVIDENCE_TRACEABLE,
    WaveFourReviewRequirementKind.SCENARIO_CONTEXT_ATTACHED,
    WaveFourReviewRequirementKind.BLACKFOX_RECEIPTS_ATTACHED,
    WaveFourReviewRequirementKind.HUMAN_AUTHORITY_PRESERVED,
    WaveFourReviewRequirementKind.REVIEWER_ROLES_ASSIGNED,
    WaveFourReviewRequirementKind.NO_AUTOMATIC_PROMOTION,
    WaveFourReviewRequirementKind.NO_AUTOMATIC_EXECUTION,
    WaveFourReviewRequirementKind.NO_AGI_CLAIM,
    WaveFourReviewRequirementKind.NO_INDEPENDENT_VALIDATION_CLAIM,
)


@dataclass(frozen=True, slots=True)
class WaveFourReviewRequirement:
    """One human-review packet requirement evaluated fail-closed."""

    requirement_id: str
    requirement_kind: WaveFourReviewRequirementKind
    severity: WaveFourScorecardGateSeverity
    passed: bool
    summary: str
    evidence_ids: tuple[str, ...] = ()
    failure_summary: str = ""
    source_system: WaveFourSourceSystem = WaveFourSourceSystem.IX_COGNITION_KERNEL
    schema_version: str = WAVE_FOUR_REVIEW_REQUIREMENT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate requirement identity and pass/fail accounting."""

        object.__setattr__(
            self,
            "requirement_id",
            _text(self.requirement_id, "requirement_id"),
        )
        object.__setattr__(self, "summary", _text(self.summary, "summary"))
        object.__setattr__(
            self,
            "evidence_ids",
            _unique_text(
                self.evidence_ids,
                label="review requirement evidence_id",
            ),
        )
        object.__setattr__(self, "failure_summary", self.failure_summary.strip())
        object.__setattr__(
            self,
            "schema_version",
            _text(self.schema_version, "schema_version"),
        )
        if self.passed and self.failure_summary:
            raise ValueError(
                "Passed Wave 4 review requirements cannot carry failure text."
            )
        if not self.passed and not self.failure_summary:
            raise ValueError("Failed Wave 4 review requirements require failure text.")

    @property
    def requirement_key(self) -> str:
        """Return deterministic uniqueness key."""

        return self.requirement_id

    @property
    def readiness_gap(self) -> str:
        """Return fail-closed gap text when this requirement failed."""

        if self.passed:
            return ""
        return f"{self.requirement_id} failed: {self.failure_summary}"

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic requirement payload."""

        return {
            "evidence_ids": list(self.evidence_ids),
            "failure_summary": self.failure_summary,
            "passed": self.passed,
            "readiness_gap": self.readiness_gap,
            "requirement_id": self.requirement_id,
            "requirement_kind": self.requirement_kind.value,
            "schema_version": self.schema_version,
            "severity": self.severity.value,
            "source_system": self.source_system.value,
            "summary": self.summary,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint."""

        return _stable_sha256(self.canonical_payload())


@dataclass(frozen=True, slots=True)
class WaveFourHumanReviewPacket:
    """Reviewable Wave 4 packet handed to humans after scorecard gating."""

    packet_id: str
    scorecard: WaveFourProtoCandidateScorecard
    requirements: tuple[WaveFourReviewRequirement, ...]
    required_reviewer_role_ids: tuple[str, ...]
    scenario_ids: tuple[str, ...]
    blackfox_receipt_ids: tuple[str, ...]
    generated_by_engine_id: str = "wave4-human-review-packet-engine"
    notes: tuple[str, ...] = ()
    blocked_reasons: tuple[str, ...] = ()
    required_requirement_kinds: tuple[WaveFourReviewRequirementKind, ...] = (
        REQUIRED_WAVE_FOUR_REVIEW_REQUIREMENT_KINDS
    )
    permits_automatic_execution: bool = False
    permits_automatic_promotion: bool = False
    claims_agi: bool = False
    independently_validated: bool = False
    schema_version: str = WAVE_FOUR_HUMAN_REVIEW_PACKET_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate packet references, coverage, and anti-overclaim boundaries."""

        object.__setattr__(self, "packet_id", _text(self.packet_id, "packet_id"))
        if not self.requirements:
            raise ValueError("Wave 4 human-review packets require requirements.")
        requirements = tuple(
            sorted(self.requirements, key=lambda item: item.requirement_key)
        )
        _unique_items(
            (item.requirement_id for item in requirements),
            "requirement_id",
        )
        object.__setattr__(self, "requirements", requirements)
        object.__setattr__(
            self,
            "required_reviewer_role_ids",
            _unique_text(
                self.required_reviewer_role_ids,
                label="required reviewer role_id",
            ),
        )
        object.__setattr__(
            self,
            "scenario_ids",
            _unique_text(self.scenario_ids, label="scenario_id"),
        )
        object.__setattr__(
            self,
            "blackfox_receipt_ids",
            _unique_text(
                self.blackfox_receipt_ids,
                label="blackfox receipt_id",
            ),
        )
        object.__setattr__(
            self,
            "generated_by_engine_id",
            _text(self.generated_by_engine_id, "generated_by_engine_id"),
        )
        object.__setattr__(
            self,
            "notes",
            _unique_text(self.notes, label="review-packet note"),
        )
        object.__setattr__(
            self,
            "blocked_reasons",
            _unique_text(self.blocked_reasons, label="blocked reason"),
        )
        object.__setattr__(
            self,
            "required_requirement_kinds",
            _unique_items(
                self.required_requirement_kinds,
                "required requirement kind",
            ),
        )
        if not self.required_requirement_kinds:
            raise ValueError(
                "Wave 4 human-review packets require requirement coverage."
            )
        object.__setattr__(
            self,
            "schema_version",
            _text(self.schema_version, "schema_version"),
        )
        if self.permits_automatic_execution:
            raise ValueError("Wave 4 review packets cannot permit execution.")
        if self.permits_automatic_promotion:
            raise ValueError("Wave 4 review packets cannot permit promotion.")
        if self.claims_agi:
            raise ValueError("Wave 4 review packets cannot claim AGI.")
        if self.independently_validated:
            raise ValueError(
                "Wave 4 review packets cannot claim independent validation."
            )

    @property
    def artifact_id(self) -> str:
        """Return shared Wave 4 artifact id for this review packet."""

        return f"wave4-human-review-packet:{self.packet_id}"

    @property
    def requirement_kinds_present(self) -> tuple[WaveFourReviewRequirementKind, ...]:
        """Return requirement kinds represented by the packet."""

        return tuple(
            sorted(
                {item.requirement_kind for item in self.requirements},
                key=lambda item: item.value,
            )
        )

    @property
    def missing_required_requirement_kinds(
        self,
    ) -> tuple[WaveFourReviewRequirementKind, ...]:
        """Return required requirement kinds missing from this packet."""

        present = set(self.requirement_kinds_present)
        return tuple(
            kind for kind in self.required_requirement_kinds if kind not in present
        )

    @property
    def passed_requirement_ids(self) -> tuple[str, ...]:
        """Return passed requirement ids."""

        return tuple(item.requirement_id for item in self.requirements if item.passed)

    @property
    def failed_requirement_ids(self) -> tuple[str, ...]:
        """Return failed requirement ids."""

        return tuple(
            item.requirement_id for item in self.requirements if not item.passed
        )

    @property
    def failed_evidence_requirement_ids(self) -> tuple[str, ...]:
        """Return failed requirements that need more evidence."""

        return self._failed_requirement_ids_by_severity(
            WaveFourScorecardGateSeverity.EVIDENCE
        )

    @property
    def failed_repair_requirement_ids(self) -> tuple[str, ...]:
        """Return failed requirements that need repair."""

        return self._failed_requirement_ids_by_severity(
            WaveFourScorecardGateSeverity.REPAIR
        )

    @property
    def failed_blocking_requirement_ids(self) -> tuple[str, ...]:
        """Return failed requirements that block review."""

        return self._failed_requirement_ids_by_severity(
            WaveFourScorecardGateSeverity.BLOCKING
        )

    @property
    def all_evidence_ids(self) -> tuple[str, ...]:
        """Return sorted evidence ids from the scorecard and packet."""

        evidence_ids = set(self.scorecard.all_evidence_ids)
        for requirement in self.requirements:
            evidence_ids.update(requirement.evidence_ids)
        return tuple(sorted(evidence_ids))

    @property
    def readiness_gaps(self) -> tuple[str, ...]:
        """Return fail-closed gaps preventing human-review submission."""

        gaps: list[str] = []
        if self.missing_required_requirement_kinds:
            missing = ", ".join(
                kind.value for kind in self.missing_required_requirement_kinds
            )
            gaps.append(f"missing review-packet requirement coverage: {missing}")
        if self.scorecard.status is not (
            WaveFourScorecardStatus.READY_FOR_CONTROLLED_REVIEW
        ):
            gaps.extend(self.scorecard.readiness_gaps)
        gaps.extend(
            requirement.readiness_gap
            for requirement in self.requirements
            if requirement.readiness_gap
        )
        if not self.required_reviewer_role_ids:
            gaps.append(f"{self.packet_id} has no required reviewer roles")
        if not self.scenario_ids:
            gaps.append(f"{self.packet_id} has no WorldTwin scenario ids")
        if not self.blackfox_receipt_ids:
            gaps.append(f"{self.packet_id} has no BlackFox receipt ids")
        return tuple(gaps)

    @property
    def blocking_gaps(self) -> tuple[str, ...]:
        """Return hard blocks for this human-review packet."""

        gaps = [
            f"{self.packet_id} blocked: {reason}" for reason in self.blocked_reasons
        ]
        gaps.extend(
            f"blocking review requirement failed: {requirement_id}"
            for requirement_id in self.failed_blocking_requirement_ids
        )
        gaps.extend(self.scorecard.blocking_gaps)
        return tuple(gaps)

    @property
    def status(self) -> WaveFourHumanReviewPacketStatus:
        """Return fail-closed status for the human-review packet."""

        if self.blocking_gaps:
            return WaveFourHumanReviewPacketStatus.BLOCKED
        if self.failed_repair_requirement_ids or self.scorecard.status is (
            WaveFourScorecardStatus.NEEDS_REPAIR
        ):
            return WaveFourHumanReviewPacketStatus.NEEDS_REPAIR
        if self.readiness_gaps:
            return WaveFourHumanReviewPacketStatus.NEEDS_EVIDENCE
        return WaveFourHumanReviewPacketStatus.READY_FOR_HUMAN_REVIEW

    @property
    def decision(self) -> WaveFourHumanReviewDecision:
        """Return human-review packet decision."""

        if self.status is WaveFourHumanReviewPacketStatus.BLOCKED:
            return WaveFourHumanReviewDecision.BLOCK_REVIEW
        if self.status is WaveFourHumanReviewPacketStatus.NEEDS_REPAIR:
            return WaveFourHumanReviewDecision.HOLD_FOR_REPAIR
        if self.status is WaveFourHumanReviewPacketStatus.NEEDS_EVIDENCE:
            return WaveFourHumanReviewDecision.HOLD_FOR_EVIDENCE
        return WaveFourHumanReviewDecision.SUBMIT_FOR_HUMAN_REVIEW

    @property
    def ready_for_human_review(self) -> bool:
        """Return whether the packet may be submitted to human review."""

        return self.status is WaveFourHumanReviewPacketStatus.READY_FOR_HUMAN_REVIEW

    @property
    def human_authority_state(self) -> WaveFourAuthorityState:
        """Return human-authority state for this review packet."""

        if self.status is WaveFourHumanReviewPacketStatus.BLOCKED:
            return WaveFourAuthorityState.BLOCKED
        return WaveFourAuthorityState.HUMAN_REVIEW_REQUIRED

    @property
    def review_summary(self) -> str:
        """Return concise human-review packet summary."""

        return (
            f"{self.packet_id}: {len(self.requirements)} review requirements; "
            f"{len(self.required_reviewer_role_ids)} reviewer roles; "
            f"{self.status.value}; no automatic promotion; no AGI claim."
        )

    def to_artifact_ref(self) -> WaveFourArtifactRef:
        """Convert this packet into a shared Wave 4 readiness artifact."""

        if self.status is WaveFourHumanReviewPacketStatus.READY_FOR_HUMAN_REVIEW:
            decision = WaveFourArtifactDecision.READY_FOR_CONTROLLED_REVIEW
        elif self.status is WaveFourHumanReviewPacketStatus.BLOCKED:
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
            produced_by_agent_role_id="human-review-packet-builder",
            evidence_ids=self.all_evidence_ids,
            decision=decision,
            authority_state=self.human_authority_state,
        )

    def evidence_links(self) -> tuple[WaveFourEvidenceLink, ...]:
        """Return evidence links for this review packet artifact."""

        relation = WaveFourEvidenceRelation.TESTS
        if self.status is WaveFourHumanReviewPacketStatus.BLOCKED:
            relation = WaveFourEvidenceRelation.BLOCKS
        return tuple(
            WaveFourEvidenceLink(
                evidence_id=evidence_id,
                artifact_id=self.artifact_id,
                relation=relation,
                summary=f"Evidence for Wave 4 review packet {self.packet_id}.",
                source_system=WaveFourSourceSystem.LOCAL_TEST_SUITE,
            )
            for evidence_id in self.all_evidence_ids
        )

    def to_artifact_bundle(self) -> WaveFourArtifactBundle:
        """Convert this packet into a one-artifact Wave 4 bundle."""

        return WaveFourArtifactBundle(
            bundle_id=f"wave4-human-review-packet-bundle:{self.packet_id}",
            artifacts=(self.to_artifact_ref(),),
            evidence_links=self.evidence_links(),
            required_kinds=(WaveFourArtifactKind.READINESS_SNAPSHOT,),
            required_capability_areas=(WaveFourCapabilityArea.AUDIT_TRAIL,),
            notes=(self.review_summary, *self.notes),
        )

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic review-packet payload."""

        return {
            "all_evidence_ids": list(self.all_evidence_ids),
            "artifact_id": self.artifact_id,
            "blackfox_receipt_ids": list(self.blackfox_receipt_ids),
            "blocking_gaps": list(self.blocking_gaps),
            "blocked_reasons": list(self.blocked_reasons),
            "claims_agi": self.claims_agi,
            "decision": self.decision.value,
            "failed_blocking_requirement_ids": list(
                self.failed_blocking_requirement_ids
            ),
            "failed_evidence_requirement_ids": list(
                self.failed_evidence_requirement_ids
            ),
            "failed_repair_requirement_ids": list(self.failed_repair_requirement_ids),
            "failed_requirement_ids": list(self.failed_requirement_ids),
            "generated_by_engine_id": self.generated_by_engine_id,
            "human_authority_state": self.human_authority_state.value,
            "independently_validated": self.independently_validated,
            "missing_required_requirement_kinds": [
                kind.value for kind in self.missing_required_requirement_kinds
            ],
            "notes": list(self.notes),
            "packet_id": self.packet_id,
            "passed_requirement_ids": list(self.passed_requirement_ids),
            "permits_automatic_execution": self.permits_automatic_execution,
            "permits_automatic_promotion": self.permits_automatic_promotion,
            "readiness_gaps": list(self.readiness_gaps),
            "required_requirement_kinds": [
                kind.value for kind in self.required_requirement_kinds
            ],
            "required_reviewer_role_ids": list(self.required_reviewer_role_ids),
            "requirements": [item.canonical_payload() for item in self.requirements],
            "review_summary": self.review_summary,
            "scenario_ids": list(self.scenario_ids),
            "schema_version": self.schema_version,
            "scorecard_decision": self.scorecard.decision.value,
            "scorecard_id": self.scorecard.scorecard_id,
            "scorecard_status": self.scorecard.status.value,
            "status": self.status.value,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint."""

        return _stable_sha256(self.canonical_payload())

    def _failed_requirement_ids_by_severity(
        self,
        severity: WaveFourScorecardGateSeverity,
    ) -> tuple[str, ...]:
        """Return failed requirement ids matching severity."""

        return tuple(
            item.requirement_id
            for item in self.requirements
            if not item.passed and item.severity is severity
        )


def build_wave_four_human_review_packet(
    *,
    packet_id: str,
    scorecard: WaveFourProtoCandidateScorecard,
    required_reviewer_role_ids: tuple[str, ...] = (
        "proto-candidate-technical-reviewer",
        "safety-boundary-reviewer",
        "evidence-chain-reviewer",
    ),
) -> WaveFourHumanReviewPacket:
    """Build the standard Wave 4 human-review packet from a scorecard."""

    evidence_ids = scorecard.all_evidence_ids
    requirements = (
        _requirement(
            requirement_id="requirement:scorecard-ready",
            requirement_kind=WaveFourReviewRequirementKind.SCORECARD_READY,
            severity=_scorecard_status_severity(scorecard),
            passed=scorecard.status
            is WaveFourScorecardStatus.READY_FOR_CONTROLLED_REVIEW,
            summary="Wave 4 scorecard allows controlled review.",
            evidence_ids=evidence_ids,
            failure_summary="; ".join(
                (*scorecard.blocking_gaps, *scorecard.readiness_gaps)
            ),
        ),
        _requirement(
            requirement_id="requirement:evidence-traceable",
            requirement_kind=WaveFourReviewRequirementKind.EVIDENCE_TRACEABLE,
            severity=WaveFourScorecardGateSeverity.EVIDENCE,
            passed=bool(scorecard.all_evidence_ids),
            summary="Scorecard and proto-candidate evidence ids remain traceable.",
            evidence_ids=evidence_ids,
            failure_summary="scorecard has no traceable evidence ids",
        ),
        _requirement(
            requirement_id="requirement:scenario-context-attached",
            requirement_kind=(WaveFourReviewRequirementKind.SCENARIO_CONTEXT_ATTACHED),
            severity=WaveFourScorecardGateSeverity.EVIDENCE,
            passed=bool(scorecard.scenario_ids),
            summary="WorldTwin-style scenario context remains attached.",
            evidence_ids=evidence_ids,
            failure_summary="scorecard has no scenario ids",
        ),
        _requirement(
            requirement_id="requirement:blackfox-receipts-attached",
            requirement_kind=(WaveFourReviewRequirementKind.BLACKFOX_RECEIPTS_ATTACHED),
            severity=WaveFourScorecardGateSeverity.EVIDENCE,
            passed=bool(scorecard.blackfox_receipt_ids),
            summary="BlackFox-style review receipts remain attached.",
            evidence_ids=evidence_ids,
            failure_summary="scorecard has no BlackFox receipt ids",
        ),
        _requirement(
            requirement_id="requirement:human-authority-preserved",
            requirement_kind=(WaveFourReviewRequirementKind.HUMAN_AUTHORITY_PRESERVED),
            severity=WaveFourScorecardGateSeverity.BLOCKING,
            passed=scorecard.human_authority_state
            is WaveFourAuthorityState.HUMAN_REVIEW_REQUIRED,
            summary="Human authority remains required before any action.",
            evidence_ids=evidence_ids,
            failure_summary="human authority is not preserved as review-required",
        ),
        _requirement(
            requirement_id="requirement:reviewer-roles-assigned",
            requirement_kind=WaveFourReviewRequirementKind.REVIEWER_ROLES_ASSIGNED,
            severity=WaveFourScorecardGateSeverity.EVIDENCE,
            passed=bool(required_reviewer_role_ids),
            summary="Required reviewer roles are declared for packet review.",
            evidence_ids=evidence_ids,
            failure_summary="no reviewer roles were assigned",
        ),
        _requirement(
            requirement_id="requirement:no-automatic-promotion",
            requirement_kind=WaveFourReviewRequirementKind.NO_AUTOMATIC_PROMOTION,
            severity=WaveFourScorecardGateSeverity.BLOCKING,
            passed=True,
            summary="Packet can only be submitted to human review, not promoted.",
            evidence_ids=evidence_ids,
            failure_summary="automatic promotion was enabled",
        ),
        _requirement(
            requirement_id="requirement:no-automatic-execution",
            requirement_kind=WaveFourReviewRequirementKind.NO_AUTOMATIC_EXECUTION,
            severity=WaveFourScorecardGateSeverity.BLOCKING,
            passed=not scorecard.permits_automatic_execution,
            summary="Scorecard and packet do not grant execution authority.",
            evidence_ids=evidence_ids,
            failure_summary="automatic execution authority was detected",
        ),
        _requirement(
            requirement_id="requirement:no-agi-claim",
            requirement_kind=WaveFourReviewRequirementKind.NO_AGI_CLAIM,
            severity=WaveFourScorecardGateSeverity.BLOCKING,
            passed=not scorecard.claims_agi,
            summary="Packet preserves the no-AGI-claim boundary.",
            evidence_ids=evidence_ids,
            failure_summary="AGI claim boundary was violated",
        ),
        _requirement(
            requirement_id="requirement:no-independent-validation-claim",
            requirement_kind=(
                WaveFourReviewRequirementKind.NO_INDEPENDENT_VALIDATION_CLAIM
            ),
            severity=WaveFourScorecardGateSeverity.BLOCKING,
            passed=not scorecard.independently_validated,
            summary="Packet does not claim Wave 5 independent validation.",
            evidence_ids=evidence_ids,
            failure_summary="independent-validation boundary was violated",
        ),
    )
    return WaveFourHumanReviewPacket(
        packet_id=packet_id,
        scorecard=scorecard,
        requirements=requirements,
        required_reviewer_role_ids=required_reviewer_role_ids,
        scenario_ids=scorecard.scenario_ids,
        blackfox_receipt_ids=scorecard.blackfox_receipt_ids,
    )


def _requirement(
    *,
    requirement_id: str,
    requirement_kind: WaveFourReviewRequirementKind,
    severity: WaveFourScorecardGateSeverity,
    passed: bool,
    summary: str,
    evidence_ids: tuple[str, ...],
    failure_summary: str,
) -> WaveFourReviewRequirement:
    """Build a requirement while adding failure text only when needed."""

    return WaveFourReviewRequirement(
        requirement_id=requirement_id,
        requirement_kind=requirement_kind,
        severity=severity,
        passed=passed,
        summary=summary,
        evidence_ids=evidence_ids,
        failure_summary="" if passed else failure_summary,
    )


def _scorecard_status_severity(
    scorecard: WaveFourProtoCandidateScorecard,
) -> WaveFourScorecardGateSeverity:
    """Return review-packet severity from scorecard status."""

    if scorecard.status is WaveFourScorecardStatus.BLOCKED:
        return WaveFourScorecardGateSeverity.BLOCKING
    if scorecard.status is WaveFourScorecardStatus.NEEDS_REPAIR:
        return WaveFourScorecardGateSeverity.REPAIR
    return WaveFourScorecardGateSeverity.EVIDENCE


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
