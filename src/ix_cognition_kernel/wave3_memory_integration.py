"""Wave 3 governed memory-role integration for IX-CognitionKernel.

Wave 2 already quarantines proposed memory. Wave 3 adds the agent-role boundary:
accepted memory may become a reviewable update candidate only when the memory
quarantine ledger is clean, the Memory Integrity Specialist role artifact is
complete, supporting reviewer roles are represented, and the decision remains
human-review-only. This module never writes durable memory.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, TypeVar

from ix_cognition_kernel.memory import (
    MemoryQuarantineLedger,
    MemoryValidationRecord,
)
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

WAVE_THREE_MEMORY_ROLE_DECISION_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave3-memory-role-decision-v1"
)
WAVE_THREE_MEMORY_ROLE_BUNDLE_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave3-memory-role-bundle-v1"
)

MEMORY_REVIEWER_ROLE_ID = "memory-integrity-specialist"
DEFAULT_MEMORY_ROLE_REVIEW_SCOPE: tuple[str, ...] = (
    "memory-integrity-specialist",
    "learning-archivist",
    "skeptic-red-team",
    "data-provenance-specialist",
)


class MemoryRoleDecisionStatus(StrEnum):
    """Fail-closed status for a governed memory-role decision."""

    READY_FOR_HUMAN_REVIEW = "ready-for-human-review"
    NEEDS_EVIDENCE = "needs-evidence"
    BLOCKED = "blocked"


@dataclass(frozen=True, slots=True)
class MemoryRoleDecisionRecord:
    """Reviewable Wave 3 bridge between quarantine and bounded role artifacts."""

    decision_id: str
    memory_ledger: MemoryQuarantineLedger
    role_artifact_bundle: RoleArtifactBundle
    evidence_ids: tuple[str, ...]
    required_role_ids: tuple[str, ...] = DEFAULT_MEMORY_ROLE_REVIEW_SCOPE
    reviewer_role_id: str = MEMORY_REVIEWER_ROLE_ID
    schema_version: str = WAVE_THREE_MEMORY_ROLE_DECISION_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate memory, role coverage, evidence, and authority boundaries."""

        object.__setattr__(self, "decision_id", _text(self.decision_id, "decision_id"))
        object.__setattr__(
            self,
            "evidence_ids",
            _unique_text(self.evidence_ids, label="memory decision evidence_id"),
        )
        object.__setattr__(
            self,
            "required_role_ids",
            _unique_text(self.required_role_ids, label="required role_id"),
        )
        object.__setattr__(
            self, "reviewer_role_id", _text(self.reviewer_role_id, "reviewer_role_id")
        )
        if self.reviewer_role_id != MEMORY_REVIEWER_ROLE_ID:
            raise ValueError(
                "Wave 3 memory-role decisions must be reviewed by "
                "memory-integrity-specialist."
            )
        if MEMORY_REVIEWER_ROLE_ID not in self.required_role_ids:
            raise ValueError(
                "Wave 3 memory-role decisions require memory-integrity-specialist "
                "in required_role_ids."
            )
        object.__setattr__(
            self, "schema_version", _text(self.schema_version, "schema_version")
        )
        _validate_required_roles_are_in_bundle(
            required_role_ids=self.required_role_ids,
            role_artifact_bundle=self.role_artifact_bundle,
        )
        _validate_memory_validations_are_role_reviewed(self.memory_ledger.validations)

    @property
    def artifact_id(self) -> str:
        """Return the shared Wave 3 artifact id for this decision."""

        return f"memory-quarantine-decision:{self.decision_id}"

    @property
    def candidate_ids(self) -> tuple[str, ...]:
        """Return memory candidate ids in ledger order."""

        return tuple(
            candidate.candidate_id for candidate in self.memory_ledger.candidates
        )

    @property
    def accepted_candidate_ids(self) -> tuple[str, ...]:
        """Return accepted memory candidate ids."""

        return tuple(
            candidate.candidate_id
            for candidate in self.memory_ledger.accepted_candidates
        )

    @property
    def quarantined_candidate_ids(self) -> tuple[str, ...]:
        """Return quarantined memory candidate ids."""

        return tuple(
            candidate.candidate_id
            for candidate in self.memory_ledger.quarantined_candidates
        )

    @property
    def rejected_candidate_ids(self) -> tuple[str, ...]:
        """Return rejected memory candidate ids."""

        return tuple(
            candidate.candidate_id
            for candidate in self.memory_ledger.rejected_candidates
        )

    @property
    def expired_candidate_ids(self) -> tuple[str, ...]:
        """Return expired memory candidate ids."""

        return tuple(
            candidate.candidate_id
            for candidate in self.memory_ledger.expired_candidates
        )

    @property
    def validation_evidence_ids(self) -> tuple[str, ...]:
        """Return sorted unique evidence ids from memory validation records."""

        return tuple(
            sorted(
                evidence_id
                for validation in self.memory_ledger.validations
                for evidence_id in validation.evidence_ids
            )
        )

    @property
    def candidate_evidence_ids(self) -> tuple[str, ...]:
        """Return sorted unique evidence ids from memory candidates."""

        return tuple(
            sorted(
                evidence_id
                for candidate in self.memory_ledger.candidates
                for evidence_id in candidate.evidence_ids
            )
        )

    @property
    def all_evidence_ids(self) -> tuple[str, ...]:
        """Return sorted unique decision, candidate, and validation evidence ids."""

        return tuple(
            sorted(
                set(self.evidence_ids).union(
                    self.candidate_evidence_ids, self.validation_evidence_ids
                )
            )
        )

    @property
    def missing_required_role_ids(self) -> tuple[str, ...]:
        """Return required memory-review roles missing from the role bundle."""

        present = set(self.role_artifact_bundle.record_role_ids)
        return tuple(
            role_id for role_id in self.required_role_ids if role_id not in present
        )

    @property
    def incomplete_required_role_ids(self) -> tuple[str, ...]:
        """Return required roles represented but not complete."""

        complete = set(self.role_artifact_bundle.complete_role_ids)
        represented = set(self.role_artifact_bundle.record_role_ids)
        return tuple(
            role_id
            for role_id in self.required_role_ids
            if role_id in represented and role_id not in complete
        )

    @property
    def blocked_required_role_ids(self) -> tuple[str, ...]:
        """Return required roles whose role artifacts block progress."""

        blocked = set(self.role_artifact_bundle.blocked_role_ids)
        return tuple(
            role_id for role_id in self.required_role_ids if role_id in blocked
        )

    @property
    def permits_automatic_memory_write(self) -> bool:
        """Return whether this record can write durable memory automatically."""

        return False

    @property
    def permits_automatic_execution(self) -> bool:
        """Return whether this record permits automatic execution."""

        return False

    @property
    def readiness_gaps(self) -> tuple[str, ...]:
        """Return non-blocking gaps that prevent human-review readiness."""

        gaps: list[str] = []
        if not self.evidence_ids:
            gaps.append(f"{self.decision_id} has no top-level evidence ids")
        if not self.memory_ledger.candidates:
            gaps.append(f"{self.decision_id} has no memory candidates")
        if self.quarantined_candidate_ids:
            gaps.append(
                "memory candidates still quarantined: "
                + ", ".join(self.quarantined_candidate_ids)
            )
        if self.missing_required_role_ids:
            gaps.append(
                "missing required memory-review roles: "
                + ", ".join(self.missing_required_role_ids)
            )
        if self.incomplete_required_role_ids:
            gaps.append(
                "incomplete required memory-review roles: "
                + ", ".join(self.incomplete_required_role_ids)
            )
        if self.role_artifact_bundle.readiness_gaps:
            gaps.extend(
                f"role artifact gap: {gap}"
                for gap in self.role_artifact_bundle.readiness_gaps
                if _gap_mentions_required_scope(gap, self.required_role_ids)
            )
        if self.accepted_candidate_ids and not self._has_complete_memory_reviewer_role:
            gaps.append(
                "accepted memory requires complete memory-integrity-specialist "
                "role artifact"
            )
        return tuple(gaps)

    @property
    def blocking_gaps(self) -> tuple[str, ...]:
        """Return blocking gaps that stop memory-role progress."""

        gaps: list[str] = []
        if self.rejected_candidate_ids:
            gaps.append(
                "memory candidates rejected: " + ", ".join(self.rejected_candidate_ids)
            )
        if self.expired_candidate_ids:
            gaps.append(
                "memory candidates expired: " + ", ".join(self.expired_candidate_ids)
            )
        if self.blocked_required_role_ids:
            gaps.append(
                "blocked required memory-review roles: "
                + ", ".join(self.blocked_required_role_ids)
            )
        return tuple(gaps)

    @property
    def status(self) -> MemoryRoleDecisionStatus:
        """Return the fail-closed memory-role decision status."""

        if self.blocking_gaps:
            return MemoryRoleDecisionStatus.BLOCKED
        if self.readiness_gaps:
            return MemoryRoleDecisionStatus.NEEDS_EVIDENCE
        return MemoryRoleDecisionStatus.READY_FOR_HUMAN_REVIEW

    @property
    def ready_for_human_review(self) -> bool:
        """Return whether this memory decision may enter human review."""

        return self.status is MemoryRoleDecisionStatus.READY_FOR_HUMAN_REVIEW

    @property
    def may_request_memory_persistence_review(self) -> bool:
        """Return whether accepted memory may be presented for human review."""

        return bool(self.accepted_candidate_ids) and self.ready_for_human_review

    @property
    def human_authority_state(self) -> WaveThreeAuthorityState:
        """Return aggregate human-authority state for this memory decision."""

        if self.status is MemoryRoleDecisionStatus.BLOCKED:
            return WaveThreeAuthorityState.BLOCKED
        return WaveThreeAuthorityState.HUMAN_REVIEW_REQUIRED

    @property
    def review_summary(self) -> str:
        """Return a concise human-review summary."""

        return (
            f"{self.decision_id}: {self.status.value}; "
            f"{len(self.accepted_candidate_ids)} accepted, "
            f"{len(self.quarantined_candidate_ids)} quarantined, "
            f"{len(self.rejected_candidate_ids)} rejected, "
            f"{len(self.expired_candidate_ids)} expired; "
            "automatic memory writes are not permitted."
        )

    @property
    def _has_complete_memory_reviewer_role(self) -> bool:
        """Return whether memory-integrity-specialist is complete in the role bundle."""

        return MEMORY_REVIEWER_ROLE_ID in self.role_artifact_bundle.complete_role_ids

    def to_artifact_ref(self) -> WaveThreeArtifactRef:
        """Convert this decision into a shared Wave 3 artifact reference."""

        if self.status is MemoryRoleDecisionStatus.READY_FOR_HUMAN_REVIEW:
            decision = WaveThreeArtifactDecision.READY_FOR_HUMAN_REVIEW
            authority_state = WaveThreeAuthorityState.HUMAN_REVIEW_REQUIRED
        elif self.status is MemoryRoleDecisionStatus.BLOCKED:
            decision = WaveThreeArtifactDecision.BLOCKED
            authority_state = WaveThreeAuthorityState.BLOCKED
        else:
            decision = WaveThreeArtifactDecision.NEEDS_EVIDENCE
            authority_state = WaveThreeAuthorityState.HUMAN_REVIEW_REQUIRED
        return WaveThreeArtifactRef(
            artifact_id=self.artifact_id,
            kind=WaveThreeArtifactKind.MEMORY_QUARANTINE_DECISION,
            source_system=WaveThreeSourceSystem.IX_COGNITION_KERNEL,
            summary=self.review_summary,
            produced_by_engine_id="memory-quarantine",
            produced_by_agent_role_id=self.reviewer_role_id,
            evidence_ids=self.all_evidence_ids,
            decision=decision,
            authority_state=authority_state,
        )

    def to_artifact_bundle(self, *, artifact_bundle_id: str) -> WaveThreeArtifactBundle:
        """Convert this memory-role decision into a shared artifact bundle."""

        artifact = self.to_artifact_ref()
        return WaveThreeArtifactBundle(
            bundle_id=artifact_bundle_id,
            artifacts=(artifact,),
            evidence_links=tuple(
                WaveThreeEvidenceLink(
                    evidence_id=evidence_id,
                    artifact_id=artifact.artifact_id,
                    relation=WaveThreeEvidenceRelation.REVIEWS,
                    summary=(
                        "Memory quarantine and role-review evidence gate memory "
                        "persistence without automatic writes."
                    ),
                    source_system=WaveThreeSourceSystem.LOCAL_TEST_SUITE,
                )
                for evidence_id in artifact.evidence_ids
            ),
            required_kinds=(WaveThreeArtifactKind.MEMORY_QUARANTINE_DECISION,),
            notes=("Memory decisions request review; they do not persist memory.",),
        )

    def canonical_payload(self) -> dict[str, Any]:
        """Return a deterministic payload for hashing and export."""

        return {
            "accepted_candidate_ids": list(self.accepted_candidate_ids),
            "all_evidence_ids": list(self.all_evidence_ids),
            "artifact_id": self.artifact_id,
            "blocking_gaps": list(self.blocking_gaps),
            "candidate_ids": list(self.candidate_ids),
            "decision_id": self.decision_id,
            "expired_candidate_ids": list(self.expired_candidate_ids),
            "human_authority_state": self.human_authority_state.value,
            "may_request_memory_persistence_review": (
                self.may_request_memory_persistence_review
            ),
            "permits_automatic_execution": self.permits_automatic_execution,
            "permits_automatic_memory_write": self.permits_automatic_memory_write,
            "quarantined_candidate_ids": list(self.quarantined_candidate_ids),
            "readiness_gaps": list(self.readiness_gaps),
            "rejected_candidate_ids": list(self.rejected_candidate_ids),
            "required_role_ids": list(self.required_role_ids),
            "review_summary": self.review_summary,
            "reviewer_role_id": self.reviewer_role_id,
            "role_artifact_bundle_fingerprint": self.role_artifact_bundle.fingerprint(),
            "schema_version": self.schema_version,
            "status": self.status.value,
        }

    def fingerprint(self) -> str:
        """Return a deterministic SHA-256 fingerprint for this decision."""

        return _stable_sha256(self.canonical_payload())


@dataclass(frozen=True, slots=True)
class MemoryRoleDecisionBundle:
    """Deterministic bundle of governed memory-role decisions."""

    bundle_id: str
    decisions: tuple[MemoryRoleDecisionRecord, ...]
    notes: tuple[str, ...] = ()
    schema_version: str = WAVE_THREE_MEMORY_ROLE_BUNDLE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate decision uniqueness and bundle reviewability."""

        object.__setattr__(self, "bundle_id", _text(self.bundle_id, "bundle_id"))
        if not self.decisions:
            raise ValueError(
                "Memory-role decision bundles require at least one decision."
            )
        decisions = tuple(sorted(self.decisions, key=lambda item: item.decision_id))
        _unique_values(
            (decision.decision_id for decision in decisions), label="decision_id"
        )
        object.__setattr__(self, "decisions", decisions)
        object.__setattr__(
            self, "notes", _unique_text(self.notes, label="memory decision bundle note")
        )
        object.__setattr__(
            self, "schema_version", _text(self.schema_version, "schema_version")
        )

    @property
    def decision_ids(self) -> tuple[str, ...]:
        """Return decision ids in deterministic order."""

        return tuple(decision.decision_id for decision in self.decisions)

    @property
    def ready_decision_ids(self) -> tuple[str, ...]:
        """Return decision ids ready for human review."""

        return tuple(
            decision.decision_id
            for decision in self.decisions
            if decision.ready_for_human_review
        )

    @property
    def blocked_decision_ids(self) -> tuple[str, ...]:
        """Return blocked decision ids."""

        return tuple(
            decision.decision_id
            for decision in self.decisions
            if decision.status is MemoryRoleDecisionStatus.BLOCKED
        )

    @property
    def readiness_gaps(self) -> tuple[str, ...]:
        """Return bundle-level and decision-level gaps."""

        gaps: list[str] = []
        for decision in self.decisions:
            gaps.extend(decision.readiness_gaps)
            gaps.extend(decision.blocking_gaps)
        return tuple(gaps)

    @property
    def is_complete_for_human_review(self) -> bool:
        """Return whether every memory decision is review-ready."""

        return not self.readiness_gaps and len(self.ready_decision_ids) == len(
            self.decisions
        )

    def decision_by_id(self, decision_id: str) -> MemoryRoleDecisionRecord:
        """Return one memory-role decision by id."""

        normalized = _text(decision_id, "decision_id")
        for decision in self.decisions:
            if decision.decision_id == normalized:
                return decision
        raise ValueError(f"Unknown memory decision_id: {decision_id}")

    def to_artifact_bundle(self, *, artifact_bundle_id: str) -> WaveThreeArtifactBundle:
        """Convert memory-role decisions into a shared artifact bundle."""

        artifacts = tuple(decision.to_artifact_ref() for decision in self.decisions)
        return WaveThreeArtifactBundle(
            bundle_id=artifact_bundle_id,
            artifacts=artifacts,
            evidence_links=tuple(
                WaveThreeEvidenceLink(
                    evidence_id=evidence_id,
                    artifact_id=artifact.artifact_id,
                    relation=WaveThreeEvidenceRelation.REVIEWS,
                    summary=(
                        "Memory-role decision evidence preserves quarantine and "
                        "human-review boundaries."
                    ),
                    source_system=WaveThreeSourceSystem.LOCAL_TEST_SUITE,
                )
                for artifact in artifacts
                for evidence_id in artifact.evidence_ids
            ),
            required_kinds=(WaveThreeArtifactKind.MEMORY_QUARANTINE_DECISION,),
            notes=("Memory-role bundles remain review-only artifacts.",),
        )

    def canonical_payload(self) -> dict[str, Any]:
        """Return a deterministic payload for hashing and export."""

        return {
            "bundle_id": self.bundle_id,
            "decisions": [decision.canonical_payload() for decision in self.decisions],
            "notes": list(self.notes),
            "readiness_gaps": list(self.readiness_gaps),
            "schema_version": self.schema_version,
        }

    def fingerprint(self) -> str:
        """Return a deterministic SHA-256 fingerprint for this bundle."""

        return _stable_sha256(self.canonical_payload())


def _validate_required_roles_are_in_bundle(
    *, required_role_ids: tuple[str, ...], role_artifact_bundle: RoleArtifactBundle
) -> None:
    """Reject decisions whose role scope is not represented by the bundle."""

    represented = set(role_artifact_bundle.record_role_ids)
    missing = tuple(
        role_id for role_id in required_role_ids if role_id not in represented
    )
    if missing:
        raise ValueError(
            "Memory-role decisions require bundled role artifacts: "
            + ", ".join(missing)
        )


def _validate_memory_validations_are_role_reviewed(
    validations: tuple[MemoryValidationRecord, ...],
) -> None:
    """Reject validation records reviewed outside the memory integrity role."""

    for validation in validations:
        if validation.reviewer_role_id != MEMORY_REVIEWER_ROLE_ID:
            raise ValueError(
                "Memory validation records must be reviewed by "
                f"{MEMORY_REVIEWER_ROLE_ID}: {validation.validation_id}"
            )


def _gap_mentions_required_scope(gap: str, required_role_ids: tuple[str, ...]) -> bool:
    """Return whether a role bundle gap names the required memory-review scope."""

    return any(role_id in gap for role_id in required_role_ids)


def _text(value: str, label: str) -> str:
    """Return stripped text or raise when empty."""

    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{label} must not be empty.")
    return normalized


def _unique_text(values: Iterable[str], *, label: str) -> tuple[str, ...]:
    """Normalize text tuples while rejecting blanks and duplicates."""

    normalized = tuple(_text(value, label) for value in values)
    _unique_values(normalized, label=label)
    return normalized


def _unique_values(values: Iterable[T], *, label: str) -> set[T]:
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
