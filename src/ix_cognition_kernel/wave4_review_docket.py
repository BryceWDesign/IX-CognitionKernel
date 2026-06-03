"""Wave 4 human-review docket records.

A bounded Wave 4 maturity declaration still needs a review docket before humans
can inspect it coherently. This module packages the declaration, review packet,
scorecard, evidence manifest, reviewer assignments, WorldTwin scenario context,
and BlackFox receipt continuity into a deterministic record. It remains
review-only: no automatic execution, no automatic promotion, no AGI claim, no
independent-validation claim, and no production-readiness claim.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Protocol, TypeVar

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
from ix_cognition_kernel.wave4_maturity_declaration import (
    WaveFourMaturityDeclarationDecision,
    WaveFourMaturityDeclarationStatus,
)

T = TypeVar("T")

WAVE_FOUR_DOCKET_ENTRY_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave4-review-docket-entry-v1"
)
WAVE_FOUR_REVIEWER_ASSIGNMENT_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave4-reviewer-assignment-v1"
)
WAVE_FOUR_HUMAN_REVIEW_DOCKET_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave4-human-review-docket-v1"
)


class WaveFourReviewDocketStatus(StrEnum):
    """Fail-closed status for a Wave 4 human-review docket."""

    READY_FOR_HUMAN_REVIEW = "ready-for-human-review"
    NEEDS_EVIDENCE = "needs-evidence"
    NEEDS_REPAIR = "needs-repair"
    BLOCKED = "blocked"


class WaveFourReviewDocketDecision(StrEnum):
    """Decision produced by a Wave 4 review docket."""

    SUBMIT_DOCKET_FOR_HUMAN_REVIEW = "submit-docket-for-human-review"
    HOLD_FOR_EVIDENCE = "hold-for-evidence"
    HOLD_FOR_REPAIR = "hold-for-repair"
    BLOCK_DOCKET = "block-docket"


class WaveFourReviewDocketEntryKind(StrEnum):
    """Kinds of entries in a human-review docket."""

    MATURITY_DECLARATION = "maturity-declaration"
    HUMAN_REVIEW_PACKET = "human-review-packet"
    SCORECARD = "scorecard"
    PROTO_CANDIDATE_BUNDLE = "proto-candidate-bundle"
    EVIDENCE_MANIFEST = "evidence-manifest"
    REVIEW_INSTRUCTIONS = "review-instructions"


class WaveFourReviewDecisionOption(StrEnum):
    """Allowed human-review outcomes exposed by the docket."""

    ACCEPT_FOR_WAVE_FOUR_RECORD = "accept-for-wave-four-record"
    REQUEST_MORE_EVIDENCE = "request-more-evidence"
    REQUEST_REPAIR = "request-repair"
    BLOCK_WAVE_FOUR_RECORD = "block-wave-four-record"


REQUIRED_WAVE_FOUR_DOCKET_ENTRY_KINDS: tuple[WaveFourReviewDocketEntryKind, ...] = (
    WaveFourReviewDocketEntryKind.MATURITY_DECLARATION,
    WaveFourReviewDocketEntryKind.HUMAN_REVIEW_PACKET,
    WaveFourReviewDocketEntryKind.SCORECARD,
    WaveFourReviewDocketEntryKind.PROTO_CANDIDATE_BUNDLE,
    WaveFourReviewDocketEntryKind.EVIDENCE_MANIFEST,
    WaveFourReviewDocketEntryKind.REVIEW_INSTRUCTIONS,
)

DEFAULT_WAVE_FOUR_REVIEW_DECISION_OPTIONS: tuple[WaveFourReviewDecisionOption, ...] = (
    WaveFourReviewDecisionOption.ACCEPT_FOR_WAVE_FOUR_RECORD,
    WaveFourReviewDecisionOption.REQUEST_MORE_EVIDENCE,
    WaveFourReviewDecisionOption.REQUEST_REPAIR,
    WaveFourReviewDecisionOption.BLOCK_WAVE_FOUR_RECORD,
)


class WaveFourScorecardLike(Protocol):
    """Structural protocol for the scorecard fields used by the docket."""

    scorecard_id: str


class WaveFourReviewPacketLike(Protocol):
    """Structural protocol for the review-packet fields used by the docket."""

    packet_id: str
    scorecard: WaveFourScorecardLike
    all_evidence_ids: tuple[str, ...]
    scenario_ids: tuple[str, ...]
    blackfox_receipt_ids: tuple[str, ...]
    required_reviewer_role_ids: tuple[str, ...]


class WaveFourMaturityDeclarationLike(Protocol):
    """Structural protocol for the declaration fields used by the docket."""

    declaration_id: str
    artifact_id: str
    status: WaveFourMaturityDeclarationStatus
    decision: WaveFourMaturityDeclarationDecision
    declarable_for_human_review: bool
    review_packet: WaveFourReviewPacketLike
    all_evidence_ids: tuple[str, ...]
    readiness_gaps: tuple[str, ...]
    blocking_gaps: tuple[str, ...]
    permits_automatic_execution: bool
    permits_automatic_promotion: bool
    claims_agi: bool
    independently_validated: bool
    production_ready: bool


@dataclass(frozen=True, slots=True)
class WaveFourReviewDocketEntry:
    """One deterministic entry in a Wave 4 human-review docket."""

    entry_id: str
    entry_kind: WaveFourReviewDocketEntryKind
    source_id: str
    summary: str
    payload: Mapping[str, Any]
    evidence_ids: tuple[str, ...]
    source_system: WaveFourSourceSystem = WaveFourSourceSystem.IX_COGNITION_KERNEL
    schema_version: str = WAVE_FOUR_DOCKET_ENTRY_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate entry identity, payload, and evidence binding."""

        object.__setattr__(self, "entry_id", _text(self.entry_id, "entry_id"))
        object.__setattr__(self, "source_id", _text(self.source_id, "source_id"))
        object.__setattr__(self, "summary", _text(self.summary, "summary"))
        normalized_payload = _normalize_mapping(self.payload, "payload")
        if not normalized_payload:
            raise ValueError("Wave 4 docket entries require non-empty payloads.")
        object.__setattr__(self, "payload", normalized_payload)
        object.__setattr__(
            self,
            "evidence_ids",
            _unique_text(self.evidence_ids, label="docket-entry evidence_id"),
        )
        if not self.evidence_ids:
            raise ValueError("Wave 4 docket entries require evidence ids.")
        object.__setattr__(
            self,
            "schema_version",
            _text(self.schema_version, "schema_version"),
        )

    @property
    def entry_key(self) -> str:
        """Return deterministic uniqueness key."""

        return self.entry_id

    @property
    def digest(self) -> str:
        """Return deterministic SHA-256 digest for this entry."""

        return _stable_sha256(self.payload_for_digest())

    def payload_for_digest(self) -> dict[str, Any]:
        """Return deterministic payload included in the entry digest."""

        return {
            "entry_id": self.entry_id,
            "entry_kind": self.entry_kind.value,
            "evidence_ids": list(self.evidence_ids),
            "payload": dict(self.payload),
            "schema_version": self.schema_version,
            "source_id": self.source_id,
            "source_system": self.source_system.value,
            "summary": self.summary,
        }

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic export payload including digest."""

        return {**self.payload_for_digest(), "digest": self.digest}

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint."""

        return self.digest


@dataclass(frozen=True, slots=True)
class WaveFourReviewerAssignment:
    """Reviewer role assignment for a bounded Wave 4 review docket."""

    assignment_id: str
    reviewer_role_id: str
    review_scope: str
    required_entry_ids: tuple[str, ...]
    decision_options: tuple[WaveFourReviewDecisionOption, ...]
    evidence_ids: tuple[str, ...]
    schema_version: str = WAVE_FOUR_REVIEWER_ASSIGNMENT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate reviewer assignment scope, entries, options, and evidence."""

        object.__setattr__(
            self,
            "assignment_id",
            _text(self.assignment_id, "assignment_id"),
        )
        object.__setattr__(
            self,
            "reviewer_role_id",
            _text(self.reviewer_role_id, "reviewer_role_id"),
        )
        object.__setattr__(
            self,
            "review_scope",
            _text(self.review_scope, "review_scope"),
        )
        object.__setattr__(
            self,
            "required_entry_ids",
            _unique_text(self.required_entry_ids, label="required entry_id"),
        )
        if not self.required_entry_ids:
            raise ValueError("Wave 4 reviewer assignments require entry ids.")
        object.__setattr__(
            self,
            "decision_options",
            _unique_items(self.decision_options, "decision option"),
        )
        if not self.decision_options:
            raise ValueError("Wave 4 reviewer assignments require decision options.")
        object.__setattr__(
            self,
            "evidence_ids",
            _unique_text(self.evidence_ids, label="reviewer-assignment evidence_id"),
        )
        if not self.evidence_ids:
            raise ValueError("Wave 4 reviewer assignments require evidence ids.")
        object.__setattr__(
            self,
            "schema_version",
            _text(self.schema_version, "schema_version"),
        )

    @property
    def assignment_key(self) -> str:
        """Return deterministic uniqueness key."""

        return self.assignment_id

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic reviewer-assignment payload."""

        return {
            "assignment_id": self.assignment_id,
            "decision_options": [option.value for option in self.decision_options],
            "evidence_ids": list(self.evidence_ids),
            "required_entry_ids": list(self.required_entry_ids),
            "review_scope": self.review_scope,
            "reviewer_role_id": self.reviewer_role_id,
            "schema_version": self.schema_version,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint."""

        return _stable_sha256(self.canonical_payload())


@dataclass(frozen=True, slots=True)
class WaveFourHumanReviewDocket:
    """Deterministic human-review docket for a bounded Wave 4 declaration."""

    docket_id: str
    maturity_declaration: WaveFourMaturityDeclarationLike
    entries: tuple[WaveFourReviewDocketEntry, ...]
    reviewer_assignments: tuple[WaveFourReviewerAssignment, ...]
    scenario_ids: tuple[str, ...]
    blackfox_receipt_ids: tuple[str, ...]
    generated_by_engine_id: str = "wave4-human-review-docket-engine"
    notes: tuple[str, ...] = ()
    blocked_reasons: tuple[str, ...] = ()
    required_entry_kinds: tuple[WaveFourReviewDocketEntryKind, ...] = (
        REQUIRED_WAVE_FOUR_DOCKET_ENTRY_KINDS
    )
    permits_automatic_execution: bool = False
    permits_automatic_promotion: bool = False
    claims_agi: bool = False
    independently_validated: bool = False
    production_ready: bool = False
    schema_version: str = WAVE_FOUR_HUMAN_REVIEW_DOCKET_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate docket references, reviewer coverage, and hard boundaries."""

        object.__setattr__(self, "docket_id", _text(self.docket_id, "docket_id"))
        if not self.entries:
            raise ValueError("Wave 4 review dockets require entries.")
        entries = tuple(sorted(self.entries, key=lambda item: item.entry_key))
        entry_ids = _unique_items((entry.entry_id for entry in entries), "entry_id")
        object.__setattr__(self, "entries", entries)
        assignments = tuple(
            sorted(
                self.reviewer_assignments,
                key=lambda item: item.assignment_key,
            )
        )
        _unique_items(
            (item.assignment_id for item in assignments),
            "assignment_id",
        )
        for assignment in assignments:
            for entry_id in assignment.required_entry_ids:
                if entry_id not in entry_ids:
                    raise ValueError(
                        "Wave 4 reviewer assignments must reference docket "
                        f"entries: {entry_id}"
                    )
        object.__setattr__(self, "reviewer_assignments", assignments)
        object.__setattr__(
            self,
            "scenario_ids",
            _unique_text(self.scenario_ids, label="scenario_id"),
        )
        object.__setattr__(
            self,
            "blackfox_receipt_ids",
            _unique_text(self.blackfox_receipt_ids, label="blackfox receipt_id"),
        )
        object.__setattr__(
            self,
            "generated_by_engine_id",
            _text(self.generated_by_engine_id, "generated_by_engine_id"),
        )
        object.__setattr__(
            self,
            "notes",
            _unique_text(self.notes, label="review-docket note"),
        )
        object.__setattr__(
            self,
            "blocked_reasons",
            _unique_text(self.blocked_reasons, label="blocked reason"),
        )
        object.__setattr__(
            self,
            "required_entry_kinds",
            _unique_items(self.required_entry_kinds, "required entry kind"),
        )
        if not self.required_entry_kinds:
            raise ValueError("Wave 4 review dockets require entry-kind coverage.")
        object.__setattr__(
            self,
            "schema_version",
            _text(self.schema_version, "schema_version"),
        )
        if self.permits_automatic_execution:
            raise ValueError("Wave 4 review dockets cannot permit execution.")
        if self.permits_automatic_promotion:
            raise ValueError("Wave 4 review dockets cannot permit promotion.")
        if self.claims_agi:
            raise ValueError("Wave 4 review dockets cannot claim AGI.")
        if self.independently_validated:
            raise ValueError(
                "Wave 4 review dockets cannot claim independent validation."
            )
        if self.production_ready:
            raise ValueError("Wave 4 review dockets cannot claim production readiness.")

    @property
    def artifact_id(self) -> str:
        """Return shared Wave 4 artifact id for this docket."""

        return f"wave4-human-review-docket:{self.docket_id}"

    @property
    def entry_ids(self) -> tuple[str, ...]:
        """Return docket entry ids in deterministic order."""

        return tuple(entry.entry_id for entry in self.entries)

    @property
    def entry_kinds_present(self) -> tuple[WaveFourReviewDocketEntryKind, ...]:
        """Return entry kinds represented by the docket."""

        return tuple(
            sorted(
                {entry.entry_kind for entry in self.entries},
                key=lambda item: item.value,
            )
        )

    @property
    def missing_required_entry_kinds(
        self,
    ) -> tuple[WaveFourReviewDocketEntryKind, ...]:
        """Return required entry kinds missing from the docket."""

        present = set(self.entry_kinds_present)
        return tuple(kind for kind in self.required_entry_kinds if kind not in present)

    @property
    def reviewer_role_ids(self) -> tuple[str, ...]:
        """Return reviewer role ids represented by assignments."""

        return tuple(
            sorted(
                {
                    assignment.reviewer_role_id
                    for assignment in self.reviewer_assignments
                }
            )
        )

    @property
    def missing_required_reviewer_role_ids(self) -> tuple[str, ...]:
        """Return review-packet roles not represented by assignments."""

        present = set(self.reviewer_role_ids)
        required = self.maturity_declaration.review_packet.required_reviewer_role_ids
        return tuple(role_id for role_id in required if role_id not in present)

    @property
    def entry_digest_by_id(self) -> dict[str, str]:
        """Return deterministic digest map for all docket entries."""

        return {entry.entry_id: entry.digest for entry in self.entries}

    @property
    def final_digest(self) -> str:
        """Return a deterministic digest for the full docket."""

        return _stable_sha256(
            {
                "docket_id": self.docket_id,
                "entries": self.entry_digest_by_id,
                "reviewer_assignments": [
                    assignment.fingerprint()
                    for assignment in self.reviewer_assignments
                ],
            }
        )

    @property
    def all_evidence_ids(self) -> tuple[str, ...]:
        """Return sorted evidence ids from declaration, entries, and assignments."""

        evidence_ids = set(self.maturity_declaration.all_evidence_ids)
        for entry in self.entries:
            evidence_ids.update(entry.evidence_ids)
        for assignment in self.reviewer_assignments:
            evidence_ids.update(assignment.evidence_ids)
        return tuple(sorted(evidence_ids))

    @property
    def missing_declaration_evidence_ids(self) -> tuple[str, ...]:
        """Return declaration evidence ids not represented in docket entries."""

        entry_evidence = {
            evidence_id for entry in self.entries for evidence_id in entry.evidence_ids
        }
        return tuple(
            evidence_id
            for evidence_id in self.maturity_declaration.all_evidence_ids
            if evidence_id not in entry_evidence
        )

    @property
    def readiness_gaps(self) -> tuple[str, ...]:
        """Return fail-closed gaps preventing docket submission."""

        gaps: list[str] = []
        if self.maturity_declaration.status is not (
            WaveFourMaturityDeclarationStatus.DECLARABLE_FOR_HUMAN_REVIEW
        ):
            gaps.extend(self.maturity_declaration.readiness_gaps)
        if self.missing_required_entry_kinds:
            missing = ", ".join(
                kind.value for kind in self.missing_required_entry_kinds
            )
            gaps.append(f"missing docket entry coverage: {missing}")
        if self.missing_required_reviewer_role_ids:
            missing_roles = ", ".join(self.missing_required_reviewer_role_ids)
            gaps.append(f"missing reviewer role coverage: {missing_roles}")
        if self.missing_declaration_evidence_ids:
            missing_evidence = ", ".join(self.missing_declaration_evidence_ids)
            gaps.append(f"missing declaration evidence in docket: {missing_evidence}")
        if not self.reviewer_assignments:
            gaps.append(f"{self.docket_id} has no reviewer assignments")
        if not self.scenario_ids:
            gaps.append(f"{self.docket_id} has no WorldTwin scenario ids")
        if not self.blackfox_receipt_ids:
            gaps.append(f"{self.docket_id} has no BlackFox receipt ids")
        return tuple(gaps)

    @property
    def blocking_gaps(self) -> tuple[str, ...]:
        """Return hard blocks for this review docket."""

        gaps = [
            f"{self.docket_id} blocked: {reason}"
            for reason in self.blocked_reasons
        ]
        gaps.extend(self.maturity_declaration.blocking_gaps)
        return tuple(gaps)

    @property
    def status(self) -> WaveFourReviewDocketStatus:
        """Return fail-closed docket status."""

        if self.blocking_gaps:
            return WaveFourReviewDocketStatus.BLOCKED
        if self.maturity_declaration.status is (
            WaveFourMaturityDeclarationStatus.NEEDS_REPAIR
        ):
            return WaveFourReviewDocketStatus.NEEDS_REPAIR
        if self.readiness_gaps:
            return WaveFourReviewDocketStatus.NEEDS_EVIDENCE
        return WaveFourReviewDocketStatus.READY_FOR_HUMAN_REVIEW

    @property
    def decision(self) -> WaveFourReviewDocketDecision:
        """Return bounded review-docket decision."""

        if self.status is WaveFourReviewDocketStatus.BLOCKED:
            return WaveFourReviewDocketDecision.BLOCK_DOCKET
        if self.status is WaveFourReviewDocketStatus.NEEDS_REPAIR:
            return WaveFourReviewDocketDecision.HOLD_FOR_REPAIR
        if self.status is WaveFourReviewDocketStatus.NEEDS_EVIDENCE:
            return WaveFourReviewDocketDecision.HOLD_FOR_EVIDENCE
        return WaveFourReviewDocketDecision.SUBMIT_DOCKET_FOR_HUMAN_REVIEW

    @property
    def ready_for_human_review(self) -> bool:
        """Return whether the docket may be submitted to human review."""

        return self.status is WaveFourReviewDocketStatus.READY_FOR_HUMAN_REVIEW

    @property
    def human_authority_state(self) -> WaveFourAuthorityState:
        """Return human-authority state for this review docket."""

        if self.status is WaveFourReviewDocketStatus.BLOCKED:
            return WaveFourAuthorityState.BLOCKED
        return WaveFourAuthorityState.HUMAN_REVIEW_REQUIRED

    @property
    def review_summary(self) -> str:
        """Return concise review-docket summary."""

        return (
            f"{self.docket_id}: {len(self.entries)} docket entries; "
            f"{len(self.reviewer_assignments)} reviewer assignments; "
            f"{self.status.value}; human review only; no AGI claim."
        )

    def to_artifact_ref(self) -> WaveFourArtifactRef:
        """Convert this docket into a shared Wave 4 readiness artifact."""

        if self.status is WaveFourReviewDocketStatus.READY_FOR_HUMAN_REVIEW:
            decision = WaveFourArtifactDecision.READY_FOR_CONTROLLED_REVIEW
        elif self.status is WaveFourReviewDocketStatus.BLOCKED:
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
            produced_by_agent_role_id="human-review-docket-builder",
            evidence_ids=self.all_evidence_ids,
            decision=decision,
            authority_state=self.human_authority_state,
        )

    def evidence_links(self) -> tuple[WaveFourEvidenceLink, ...]:
        """Return evidence links for this docket artifact."""

        relation = WaveFourEvidenceRelation.TESTS
        if self.status is WaveFourReviewDocketStatus.BLOCKED:
            relation = WaveFourEvidenceRelation.BLOCKS
        return tuple(
            WaveFourEvidenceLink(
                evidence_id=evidence_id,
                artifact_id=self.artifact_id,
                relation=relation,
                summary=f"Evidence for Wave 4 review docket {self.docket_id}.",
                source_system=WaveFourSourceSystem.LOCAL_TEST_SUITE,
            )
            for evidence_id in self.all_evidence_ids
        )

    def to_artifact_bundle(self) -> WaveFourArtifactBundle:
        """Convert this docket into a one-artifact Wave 4 bundle."""

        return WaveFourArtifactBundle(
            bundle_id=f"wave4-review-docket-bundle:{self.docket_id}",
            artifacts=(self.to_artifact_ref(),),
            evidence_links=self.evidence_links(),
            required_kinds=(WaveFourArtifactKind.READINESS_SNAPSHOT,),
            required_capability_areas=(WaveFourCapabilityArea.AUDIT_TRAIL,),
            notes=(self.review_summary, *self.notes),
        )

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic review-docket payload."""

        return {
            "all_evidence_ids": list(self.all_evidence_ids),
            "artifact_id": self.artifact_id,
            "blackfox_receipt_ids": list(self.blackfox_receipt_ids),
            "blocking_gaps": list(self.blocking_gaps),
            "blocked_reasons": list(self.blocked_reasons),
            "claims_agi": self.claims_agi,
            "decision": self.decision.value,
            "docket_id": self.docket_id,
            "entries": [entry.canonical_payload() for entry in self.entries],
            "entry_digest_by_id": self.entry_digest_by_id,
            "entry_ids": list(self.entry_ids),
            "entry_kinds_present": [kind.value for kind in self.entry_kinds_present],
            "final_digest": self.final_digest,
            "generated_by_engine_id": self.generated_by_engine_id,
            "human_authority_state": self.human_authority_state.value,
            "independently_validated": self.independently_validated,
            "maturity_declaration_id": self.maturity_declaration.declaration_id,
            "maturity_declaration_status": self.maturity_declaration.status.value,
            "missing_declaration_evidence_ids": list(
                self.missing_declaration_evidence_ids
            ),
            "missing_required_entry_kinds": [
                kind.value for kind in self.missing_required_entry_kinds
            ],
            "missing_required_reviewer_role_ids": list(
                self.missing_required_reviewer_role_ids
            ),
            "notes": list(self.notes),
            "permits_automatic_execution": self.permits_automatic_execution,
            "permits_automatic_promotion": self.permits_automatic_promotion,
            "production_ready": self.production_ready,
            "readiness_gaps": list(self.readiness_gaps),
            "required_entry_kinds": [kind.value for kind in self.required_entry_kinds],
            "review_summary": self.review_summary,
            "reviewer_assignments": [
                assignment.canonical_payload()
                for assignment in self.reviewer_assignments
            ],
            "reviewer_role_ids": list(self.reviewer_role_ids),
            "scenario_ids": list(self.scenario_ids),
            "schema_version": self.schema_version,
            "status": self.status.value,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint."""

        return _stable_sha256(self.canonical_payload())


def build_wave_four_human_review_docket(
    *,
    docket_id: str,
    maturity_declaration: WaveFourMaturityDeclarationLike,
) -> WaveFourHumanReviewDocket:
    """Build the standard Wave 4 human-review docket from a declaration."""

    packet = maturity_declaration.review_packet
    scorecard = packet.scorecard
    evidence_ids = maturity_declaration.all_evidence_ids
    entries = (
        _entry(
            entry_id="entry:maturity-declaration",
            entry_kind=WaveFourReviewDocketEntryKind.MATURITY_DECLARATION,
            source_id=maturity_declaration.declaration_id,
            summary="Bounded Wave 4 maturity declaration for human review.",
            payload={
                "declaration_id": maturity_declaration.declaration_id,
                "decision": maturity_declaration.decision.value,
                "status": maturity_declaration.status.value,
            },
            evidence_ids=evidence_ids,
        ),
        _entry(
            entry_id="entry:human-review-packet",
            entry_kind=WaveFourReviewDocketEntryKind.HUMAN_REVIEW_PACKET,
            source_id=packet.packet_id,
            summary="Human-review packet attached to the declaration.",
            payload={
                "packet_id": packet.packet_id,
                "reviewer_roles": list(packet.required_reviewer_role_ids),
            },
            evidence_ids=packet.all_evidence_ids,
        ),
        _entry(
            entry_id="entry:scorecard",
            entry_kind=WaveFourReviewDocketEntryKind.SCORECARD,
            source_id=scorecard.scorecard_id,
            summary="Wave 4 scorecard attached to the review packet.",
            payload={"scorecard_id": scorecard.scorecard_id},
            evidence_ids=evidence_ids,
        ),
        _entry(
            entry_id="entry:proto-candidate-bundle",
            entry_kind=WaveFourReviewDocketEntryKind.PROTO_CANDIDATE_BUNDLE,
            source_id=maturity_declaration.artifact_id,
            summary="Proto-candidate evidence package remains review-only.",
            payload={"artifact_id": maturity_declaration.artifact_id},
            evidence_ids=evidence_ids,
        ),
        _entry(
            entry_id="entry:evidence-manifest",
            entry_kind=WaveFourReviewDocketEntryKind.EVIDENCE_MANIFEST,
            source_id=f"evidence-manifest:{docket_id}",
            summary="Evidence ids covered by the docket.",
            payload={
                "evidence_count": len(evidence_ids),
                "evidence_ids": list(evidence_ids),
            },
            evidence_ids=evidence_ids,
        ),
        _entry(
            entry_id="entry:review-instructions",
            entry_kind=WaveFourReviewDocketEntryKind.REVIEW_INSTRUCTIONS,
            source_id=f"review-instructions:{docket_id}",
            summary=(
                "Reviewer decisions are bounded to accept, evidence, repair, "
                "or block."
            ),
            payload={
                "decision_options": [
                    option.value
                    for option in DEFAULT_WAVE_FOUR_REVIEW_DECISION_OPTIONS
                ],
                "no_agi_claim": True,
                "no_automatic_execution": True,
                "no_independent_validation_claim": True,
            },
            evidence_ids=evidence_ids,
        ),
    )
    entry_ids = tuple(entry.entry_id for entry in entries)
    assignments = tuple(
        WaveFourReviewerAssignment(
            assignment_id=f"assignment:{role_id}",
            reviewer_role_id=role_id,
            review_scope=f"Review Wave 4 docket evidence for {role_id}.",
            required_entry_ids=entry_ids,
            decision_options=DEFAULT_WAVE_FOUR_REVIEW_DECISION_OPTIONS,
            evidence_ids=evidence_ids,
        )
        for role_id in packet.required_reviewer_role_ids
    )
    return WaveFourHumanReviewDocket(
        docket_id=docket_id,
        maturity_declaration=maturity_declaration,
        entries=entries,
        reviewer_assignments=assignments,
        scenario_ids=packet.scenario_ids,
        blackfox_receipt_ids=packet.blackfox_receipt_ids,
    )


def _entry(
    *,
    entry_id: str,
    entry_kind: WaveFourReviewDocketEntryKind,
    source_id: str,
    summary: str,
    payload: Mapping[str, Any],
    evidence_ids: tuple[str, ...],
) -> WaveFourReviewDocketEntry:
    """Build a review-docket entry."""

    return WaveFourReviewDocketEntry(
        entry_id=entry_id,
        entry_kind=entry_kind,
        source_id=source_id,
        summary=summary,
        payload=payload,
        evidence_ids=evidence_ids,
    )


def _normalize_mapping(value: Mapping[str, Any], label: str) -> dict[str, Any]:
    """Return a canonical dict after proving JSON serializability."""

    try:
        encoded = json.dumps(value, sort_keys=True, separators=(",", ":"))
    except TypeError as exc:
        raise ValueError(f"{label} must be JSON serializable.") from exc
    return json.loads(encoded)


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

    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return hashlib.sha256(encoded).hexdigest()
