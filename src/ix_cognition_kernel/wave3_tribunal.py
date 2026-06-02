"""Wave 3 multi-agent tribunal flow for IX-CognitionKernel.

The tribunal flow turns bounded role artifacts into a reviewable governance
record. It models proposal, critique, verification, translation, safety, and
handoff phases without granting execution authority or allowing persuasive
consensus to override evidence. A tribunal can become ready for human review only
when every required role artifact is represented, every required phase has
supporting evidence, and no role has issued an evidence-bound block.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, TypeVar

from ix_cognition_kernel.agents import agent_by_id
from ix_cognition_kernel.wave3_agent_artifacts import RoleArtifactBundle
from ix_cognition_kernel.wave3_contracts import (
    WaveThreeArtifactBundle,
    WaveThreeArtifactDecision,
    WaveThreeArtifactKind,
    WaveThreeArtifactRef,
    WaveThreeAuthorityState,
    WaveThreeEvidenceLink,
    WaveThreeEvidenceRelation,
    WaveThreeSourceSystem,
)

T = TypeVar("T")

WAVE_THREE_TRIBUNAL_SCHEMA_VERSION = "ix-cognition-kernel-wave3-tribunal-v1"
WAVE_THREE_TRIBUNAL_VOTE_SCHEMA_VERSION = "ix-cognition-kernel-wave3-tribunal-vote-v1"


class TribunalPhase(StrEnum):
    """Required review phase represented by tribunal votes."""

    PROPOSAL = "proposal"
    CRITIQUE = "critique"
    VERIFICATION = "verification"
    SAFETY = "safety"
    TRANSLATION = "translation"
    HANDOFF = "handoff"


class TribunalVotePosition(StrEnum):
    """Evidence-bound position taken by one bounded role."""

    SUPPORT = "support"
    CONCERN = "concern"
    BLOCK = "block"


class TribunalDecisionStatus(StrEnum):
    """Fail-closed status for a tribunal decision record."""

    READY_FOR_HUMAN_REVIEW = "ready-for-human-review"
    NEEDS_EVIDENCE = "needs-evidence"
    BLOCKED = "blocked"


REQUIRED_TRIBUNAL_PHASES: tuple[TribunalPhase, ...] = (
    TribunalPhase.PROPOSAL,
    TribunalPhase.CRITIQUE,
    TribunalPhase.VERIFICATION,
    TribunalPhase.SAFETY,
    TribunalPhase.TRANSLATION,
    TribunalPhase.HANDOFF,
)


@dataclass(frozen=True, slots=True)
class TribunalRoleVote:
    """One bounded role's evidence-bound vote in a tribunal phase."""

    role_id: str
    phase: TribunalPhase
    position: TribunalVotePosition
    artifact_ids: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    rationale: str
    concerns: tuple[str, ...] = ()
    schema_version: str = WAVE_THREE_TRIBUNAL_VOTE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate vote identity, evidence binding, and blocking discipline."""

        object.__setattr__(self, "role_id", _normalize_role_id(self.role_id))
        object.__setattr__(
            self,
            "artifact_ids",
            _normalize_unique_text_tuple(self.artifact_ids, label="vote artifact_id"),
        )
        object.__setattr__(
            self,
            "evidence_ids",
            _normalize_unique_text_tuple(self.evidence_ids, label="vote evidence_id"),
        )
        object.__setattr__(
            self, "rationale", _require_non_empty(self.rationale, "vote rationale")
        )
        object.__setattr__(
            self,
            "concerns",
            _normalize_unique_text_tuple(self.concerns, label="vote concern"),
        )
        object.__setattr__(
            self,
            "schema_version",
            _require_non_empty(self.schema_version, "schema_version"),
        )
        if self.position is TribunalVotePosition.BLOCK and not self.concerns:
            raise ValueError("Blocking tribunal votes require explicit concerns.")
        if self.position is TribunalVotePosition.CONCERN and not self.concerns:
            raise ValueError("Concern tribunal votes require explicit concerns.")

    @property
    def vote_key(self) -> tuple[str, str, str]:
        """Return the deterministic uniqueness key for this vote."""

        return (self.role_id, self.phase.value, self.position.value)

    @property
    def blocks_progress(self) -> bool:
        """Return whether this vote blocks tribunal progress."""

        return self.position is TribunalVotePosition.BLOCK

    @property
    def raises_dissent(self) -> bool:
        """Return whether this vote records dissent from simple support."""

        return self.position in {
            TribunalVotePosition.CONCERN,
            TribunalVotePosition.BLOCK,
        }

    def canonical_payload(self) -> dict[str, Any]:
        """Return a deterministic payload for hashing and export."""

        return {
            "artifact_ids": list(self.artifact_ids),
            "concerns": list(self.concerns),
            "evidence_ids": list(self.evidence_ids),
            "phase": self.phase.value,
            "position": self.position.value,
            "rationale": self.rationale,
            "role_id": self.role_id,
            "schema_version": self.schema_version,
        }

    def fingerprint(self) -> str:
        """Return a deterministic SHA-256 fingerprint for this vote."""

        return _stable_sha256(self.canonical_payload())


@dataclass(frozen=True, slots=True)
class TribunalDecisionRecord:
    """Reviewable Wave 3 tribunal decision assembled from bounded role votes."""

    tribunal_id: str
    role_artifact_bundle: RoleArtifactBundle
    votes: tuple[TribunalRoleVote, ...]
    required_role_ids: tuple[str, ...]
    required_phases: tuple[TribunalPhase, ...] = REQUIRED_TRIBUNAL_PHASES
    decision_summary: str = ""
    schema_version: str = WAVE_THREE_TRIBUNAL_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate role coverage, artifact linkage, and required review phases."""

        object.__setattr__(
            self, "tribunal_id", _require_non_empty(self.tribunal_id, "tribunal_id")
        )
        object.__setattr__(
            self,
            "required_role_ids",
            _normalize_required_role_ids(self.required_role_ids),
        )
        object.__setattr__(
            self,
            "required_phases",
            _normalize_unique_enum_tuple(self.required_phases, label="tribunal phase"),
        )
        if not self.required_phases:
            raise ValueError("Tribunal decisions require at least one review phase.")
        if not self.votes:
            raise ValueError("Tribunal decisions require at least one role vote.")
        sorted_votes = tuple(sorted(self.votes, key=lambda vote: vote.vote_key))
        _unique_ids((vote.vote_key for vote in sorted_votes), label="tribunal vote")
        object.__setattr__(self, "votes", sorted_votes)
        object.__setattr__(
            self,
            "decision_summary",
            self.decision_summary.strip() or self._default_decision_summary(),
        )
        object.__setattr__(
            self,
            "schema_version",
            _require_non_empty(self.schema_version, "schema_version"),
        )
        _validate_required_roles_within_bundle(
            required_role_ids=self.required_role_ids,
            role_artifact_bundle=self.role_artifact_bundle,
        )
        _validate_votes_reference_required_roles(
            votes=self.votes,
            required_role_ids=self.required_role_ids,
        )
        _validate_vote_artifacts_exist(
            votes=self.votes,
            role_artifact_bundle=self.role_artifact_bundle,
        )

    @property
    def status(self) -> TribunalDecisionStatus:
        """Return the fail-closed tribunal decision status."""

        if self.blocking_gaps:
            return TribunalDecisionStatus.BLOCKED
        if self.readiness_gaps:
            return TribunalDecisionStatus.NEEDS_EVIDENCE
        return TribunalDecisionStatus.READY_FOR_HUMAN_REVIEW

    @property
    def ready_for_human_review(self) -> bool:
        """Return whether the tribunal record may enter human review."""

        return self.status is TribunalDecisionStatus.READY_FOR_HUMAN_REVIEW

    @property
    def permits_automatic_execution(self) -> bool:
        """Return whether this tribunal permits automatic execution."""

        return False

    @property
    def human_authority_state(self) -> WaveThreeAuthorityState:
        """Return aggregate human-authority state for this tribunal."""

        if self.status is TribunalDecisionStatus.BLOCKED:
            return WaveThreeAuthorityState.BLOCKED
        return WaveThreeAuthorityState.HUMAN_REVIEW_REQUIRED

    @property
    def represented_phase_values(self) -> tuple[str, ...]:
        """Return represented review phases in required-phase order."""

        present = {vote.phase for vote in self.votes}
        return tuple(phase.value for phase in self.required_phases if phase in present)

    @property
    def missing_required_phases(self) -> tuple[TribunalPhase, ...]:
        """Return required review phases missing from votes."""

        present = {vote.phase for vote in self.votes}
        return tuple(phase for phase in self.required_phases if phase not in present)

    @property
    def missing_required_vote_role_ids(self) -> tuple[str, ...]:
        """Return required roles that did not cast any vote."""

        present = {vote.role_id for vote in self.votes}
        return tuple(
            role_id for role_id in self.required_role_ids if role_id not in present
        )

    @property
    def dissenting_role_ids(self) -> tuple[str, ...]:
        """Return role ids that raised concerns or blocks."""

        return tuple(vote.role_id for vote in self.votes if vote.raises_dissent)

    @property
    def blocking_role_ids(self) -> tuple[str, ...]:
        """Return role ids whose votes block tribunal progress."""

        return tuple(vote.role_id for vote in self.votes if vote.blocks_progress)

    @property
    def support_role_ids(self) -> tuple[str, ...]:
        """Return role ids whose votes support human-review readiness."""

        return tuple(
            vote.role_id
            for vote in self.votes
            if vote.position is TribunalVotePosition.SUPPORT
        )

    @property
    def readiness_gaps(self) -> tuple[str, ...]:
        """Return non-blocking gaps that prevent human-review readiness."""

        gaps: list[str] = []
        gaps.extend(self.role_artifact_bundle.readiness_gaps)
        if self.missing_required_vote_role_ids:
            gaps.append(
                "missing required role votes: "
                + ", ".join(self.missing_required_vote_role_ids)
            )
        if self.missing_required_phases:
            gaps.append(
                "missing required tribunal phases: "
                + ", ".join(phase.value for phase in self.missing_required_phases)
            )
        if not self.decision_summary.strip():
            gaps.append("tribunal decision summary is empty")
        return tuple(gaps)

    @property
    def blocking_gaps(self) -> tuple[str, ...]:
        """Return evidence-bound blocks that stop tribunal progress."""

        gaps: list[str] = []
        if self.role_artifact_bundle.blocked_role_ids:
            gaps.append(
                "blocked role artifacts: "
                + ", ".join(self.role_artifact_bundle.blocked_role_ids)
            )
        if self.blocking_role_ids:
            gaps.append("blocking role votes: " + ", ".join(self.blocking_role_ids))
        return tuple(gaps)

    @property
    def review_summary(self) -> str:
        """Return a concise human-review summary."""

        return (
            f"{self.tribunal_id}: {self.status.value}; "
            f"{len(self.support_role_ids)} support, "
            f"{len(self.dissenting_role_ids)} dissent, "
            f"{len(self.blocking_role_ids)} block; "
            "automatic execution is not permitted."
        )

    def to_artifact_ref(self) -> WaveThreeArtifactRef:
        """Convert this tribunal record into a shared Wave 3 artifact reference."""

        if self.status is TribunalDecisionStatus.READY_FOR_HUMAN_REVIEW:
            decision = WaveThreeArtifactDecision.READY_FOR_HUMAN_REVIEW
            authority_state = WaveThreeAuthorityState.HUMAN_REVIEW_REQUIRED
        elif self.status is TribunalDecisionStatus.BLOCKED:
            decision = WaveThreeArtifactDecision.BLOCKED
            authority_state = WaveThreeAuthorityState.BLOCKED
        else:
            decision = WaveThreeArtifactDecision.NEEDS_EVIDENCE
            authority_state = WaveThreeAuthorityState.HUMAN_REVIEW_REQUIRED
        return WaveThreeArtifactRef(
            artifact_id=f"tribunal-record:{self.tribunal_id}",
            kind=WaveThreeArtifactKind.TRIBUNAL_RECORD,
            source_system=WaveThreeSourceSystem.IX_COGNITION_KERNEL,
            summary=self.review_summary,
            produced_by_engine_id="multi-agent-tribunal",
            evidence_ids=self.evidence_ids,
            decision=decision,
            authority_state=authority_state,
        )

    @property
    def evidence_ids(self) -> tuple[str, ...]:
        """Return sorted unique evidence ids from all votes."""

        return tuple(
            sorted(
                {
                    evidence_id
                    for vote in self.votes
                    for evidence_id in vote.evidence_ids
                }
            )
        )

    def to_artifact_bundle(self, *, artifact_bundle_id: str) -> WaveThreeArtifactBundle:
        """Convert the tribunal decision into a shared artifact bundle."""

        artifact = self.to_artifact_ref()
        evidence_links = tuple(
            WaveThreeEvidenceLink(
                evidence_id=evidence_id,
                artifact_id=artifact.artifact_id,
                relation=WaveThreeEvidenceRelation.REVIEWS,
                summary="Tribunal vote evidence supports the Wave 3 tribunal record.",
                source_system=WaveThreeSourceSystem.LOCAL_TEST_SUITE,
            )
            for evidence_id in artifact.evidence_ids
        )
        return WaveThreeArtifactBundle(
            bundle_id=artifact_bundle_id,
            artifacts=(artifact,),
            evidence_links=evidence_links,
            required_kinds=(WaveThreeArtifactKind.TRIBUNAL_RECORD,),
            notes=("Tribunal records are review gates, not execution authority.",),
        )

    def canonical_payload(self) -> dict[str, Any]:
        """Return a deterministic payload for hashing and export."""

        return {
            "blocking_gaps": list(self.blocking_gaps),
            "decision_summary": self.decision_summary,
            "evidence_ids": list(self.evidence_ids),
            "human_authority_state": self.human_authority_state.value,
            "permits_automatic_execution": self.permits_automatic_execution,
            "readiness_gaps": list(self.readiness_gaps),
            "represented_phase_values": list(self.represented_phase_values),
            "required_phases": [phase.value for phase in self.required_phases],
            "required_role_ids": list(self.required_role_ids),
            "review_summary": self.review_summary,
            "role_artifact_bundle_fingerprint": self.role_artifact_bundle.fingerprint(),
            "schema_version": self.schema_version,
            "status": self.status.value,
            "tribunal_id": self.tribunal_id,
            "votes": [vote.canonical_payload() for vote in self.votes],
        }

    def fingerprint(self) -> str:
        """Return a deterministic SHA-256 fingerprint for this decision."""

        return _stable_sha256(self.canonical_payload())

    def _default_decision_summary(self) -> str:
        """Build a default summary before final status calculation."""

        return (
            f"Tribunal {self.tribunal_id} records bounded role review for "
            f"{len(self.votes)} votes; human review remains required."
        )


def tribunal_vote(
    *,
    role_id: str,
    phase: TribunalPhase,
    position: TribunalVotePosition = TribunalVotePosition.SUPPORT,
    evidence_ids: tuple[str, ...],
    rationale: str,
    concerns: tuple[str, ...] = (),
) -> TribunalRoleVote:
    """Create a vote linked to the role artifact id for one bounded role."""

    return TribunalRoleVote(
        role_id=role_id,
        phase=phase,
        position=position,
        artifact_ids=(f"role-artifact:{role_id}",),
        evidence_ids=evidence_ids,
        rationale=rationale,
        concerns=concerns,
    )


def _validate_required_roles_within_bundle(
    *, required_role_ids: tuple[str, ...], role_artifact_bundle: RoleArtifactBundle
) -> None:
    """Reject tribunal scope that is not represented by the role bundle."""

    bundle_roles = set(role_artifact_bundle.record_role_ids)
    for role_id in required_role_ids:
        if role_id not in bundle_roles:
            raise ValueError(
                "Tribunal required roles must be represented by role artifacts: "
                f"{role_id}"
            )


def _validate_votes_reference_required_roles(
    *, votes: tuple[TribunalRoleVote, ...], required_role_ids: tuple[str, ...]
) -> None:
    """Reject votes from roles outside tribunal scope."""

    required = set(required_role_ids)
    for vote in votes:
        if vote.role_id not in required:
            raise ValueError(
                f"Tribunal vote references non-required role: {vote.role_id}"
            )


def _validate_vote_artifacts_exist(
    *, votes: tuple[TribunalRoleVote, ...], role_artifact_bundle: RoleArtifactBundle
) -> None:
    """Reject votes that cite missing role-artifact ids."""

    artifact_ids = {record.artifact_id for record in role_artifact_bundle.records}
    for vote in votes:
        for artifact_id in vote.artifact_ids:
            if artifact_id not in artifact_ids:
                raise ValueError(
                    f"Tribunal vote references missing role artifact: {artifact_id}"
                )


def _normalize_role_id(role_id: str) -> str:
    """Normalize and validate a role id."""

    normalized = _require_non_empty(role_id, "role_id")
    agent_by_id(normalized)
    return normalized


def _normalize_required_role_ids(values: Iterable[str]) -> tuple[str, ...]:
    """Normalize required role ids without sorting away caller order."""

    normalized: list[str] = []
    seen: set[str] = set()
    for value in values:
        role_id = _normalize_role_id(value)
        if role_id in seen:
            raise ValueError(f"Duplicate required_role_id detected: {role_id}")
        normalized.append(role_id)
        seen.add(role_id)
    if not normalized:
        raise ValueError("Tribunal decisions require required role ids.")
    return tuple(normalized)


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


def _normalize_unique_enum_tuple(
    values: Iterable[TribunalPhase], *, label: str
) -> tuple[TribunalPhase, ...]:
    """Normalize enum values while rejecting duplicates."""

    normalized: list[TribunalPhase] = []
    seen: set[TribunalPhase] = set()
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


def _require_non_empty(value: str, label: str) -> str:
    """Return stripped text or raise when empty."""

    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{label} must not be empty.")
    return normalized


def _stable_sha256(payload: Mapping[str, Any]) -> str:
    """Return deterministic SHA-256 over a canonical JSON payload."""

    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
