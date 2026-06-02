"""Wave 3 governed skill-genome update records for IX-CognitionKernel.

Wave 2 validates reusable skill candidates. Wave 3 adds governance around the
skill genome itself: a validated skill may request human review only when the
skill ledger is clean, reuse evidence remains linked, transfer limits are
explicit, the Learning Archivist role artifact is complete, and the update stays
review-only. This module never installs skills, mutates the genome, or grants
execution authority.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, TypeVar

from ix_cognition_kernel.skills import (
    SkillReuseEvidenceRecord,
    SkillValidationLedger,
    SkillValidationRecord,
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

WAVE_THREE_SKILL_GENOME_UPDATE_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave3-skill-genome-update-v1"
)
WAVE_THREE_SKILL_GENOME_BUNDLE_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave3-skill-genome-bundle-v1"
)

SKILL_GENOME_REVIEWER_ROLE_ID = "learning-archivist"
DEFAULT_SKILL_GENOME_REVIEW_SCOPE: tuple[str, ...] = (
    "learning-archivist",
    "verifier",
    "skeptic-red-team",
    "memory-integrity-specialist",
)


class SkillGenomeUpdateStatus(StrEnum):
    """Fail-closed status for a governed skill-genome update record."""

    READY_FOR_HUMAN_REVIEW = "ready-for-human-review"
    NEEDS_EVIDENCE = "needs-evidence"
    NEEDS_REUSE_EVIDENCE = "needs-reuse-evidence"
    BLOCKED = "blocked"


@dataclass(frozen=True, slots=True)
class SkillGenomeUpdateRecord:
    """Reviewable Wave 3 bridge between skill validation and genome update."""

    update_id: str
    skill_ledger: SkillValidationLedger
    role_artifact_bundle: RoleArtifactBundle
    evidence_ids: tuple[str, ...]
    allowed_transfer_domains: tuple[str, ...]
    reuse_limitations: tuple[str, ...]
    required_role_ids: tuple[str, ...] = DEFAULT_SKILL_GENOME_REVIEW_SCOPE
    reviewer_role_id: str = SKILL_GENOME_REVIEWER_ROLE_ID
    schema_version: str = WAVE_THREE_SKILL_GENOME_UPDATE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate skill-ledger, role, transfer, and review-only boundaries."""

        object.__setattr__(self, "update_id", _text(self.update_id, "update_id"))
        object.__setattr__(
            self,
            "evidence_ids",
            _unique_text(self.evidence_ids, label="skill update evidence_id"),
        )
        object.__setattr__(
            self,
            "allowed_transfer_domains",
            _unique_text(
                self.allowed_transfer_domains,
                label="allowed transfer domain",
            ),
        )
        object.__setattr__(
            self,
            "reuse_limitations",
            _unique_text(self.reuse_limitations, label="reuse limitation"),
        )
        object.__setattr__(
            self,
            "required_role_ids",
            _unique_text(self.required_role_ids, label="required role_id"),
        )
        object.__setattr__(
            self, "reviewer_role_id", _text(self.reviewer_role_id, "reviewer_role_id")
        )
        if self.reviewer_role_id != SKILL_GENOME_REVIEWER_ROLE_ID:
            raise ValueError(
                "Wave 3 skill-genome updates must be reviewed by learning-archivist."
            )
        if SKILL_GENOME_REVIEWER_ROLE_ID not in self.required_role_ids:
            raise ValueError(
                "Wave 3 skill-genome updates require learning-archivist in "
                "required_role_ids."
            )
        object.__setattr__(
            self, "schema_version", _text(self.schema_version, "schema_version")
        )
        _validate_required_roles_are_in_bundle(
            required_role_ids=self.required_role_ids,
            role_artifact_bundle=self.role_artifact_bundle,
        )
        _validate_skill_validations_are_learning_archivist_reviewed(
            self.skill_ledger.validations
        )

    @property
    def artifact_id(self) -> str:
        """Return the shared Wave 3 artifact id for this update."""

        return f"skill-genome-update:{self.update_id}"

    @property
    def candidate_skill_ids(self) -> tuple[str, ...]:
        """Return skill ids represented by the skill ledger."""

        return tuple(candidate.skill_id for candidate in self.skill_ledger.candidates)

    @property
    def validated_skill_ids(self) -> tuple[str, ...]:
        """Return skill ids validated for possible genome update review."""

        return tuple(
            candidate.skill_id for candidate in self.skill_ledger.validated_candidates
        )

    @property
    def needs_reuse_evidence_skill_ids(self) -> tuple[str, ...]:
        """Return skill ids that still need successful reuse evidence."""

        return tuple(
            candidate.skill_id
            for candidate in self.skill_ledger.candidates_needing_reuse_evidence
        )

    @property
    def rejected_skill_ids(self) -> tuple[str, ...]:
        """Return rejected skill ids."""

        return tuple(
            candidate.skill_id for candidate in self.skill_ledger.rejected_candidates
        )

    @property
    def blocked_skill_ids(self) -> tuple[str, ...]:
        """Return blocked skill ids."""

        return tuple(
            candidate.skill_id for candidate in self.skill_ledger.blocked_candidates
        )

    @property
    def reuse_evidence_ids(self) -> tuple[str, ...]:
        """Return sorted unique evidence ids from skill reuse evidence records."""

        return tuple(
            sorted(
                evidence_id
                for reuse in self.skill_ledger.reuse_records
                for evidence_id in reuse.evidence_ids
            )
        )

    @property
    def validation_reuse_record_ids(self) -> tuple[str, ...]:
        """Return reuse record ids cited by validated skill records."""

        return tuple(
            sorted(
                reuse_id
                for validation in self.skill_ledger.validations
                for reuse_id in validation.reuse_evidence_ids
            )
        )

    @property
    def all_evidence_ids(self) -> tuple[str, ...]:
        """Return sorted unique top-level and reuse evidence ids."""

        return tuple(sorted(set(self.evidence_ids).union(self.reuse_evidence_ids)))

    @property
    def missing_required_role_ids(self) -> tuple[str, ...]:
        """Return required skill-review roles missing from the role bundle."""

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
    def permits_automatic_skill_install(self) -> bool:
        """Return whether this record can install a skill automatically."""

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
            gaps.append(f"{self.update_id} has no top-level evidence ids")
        if not self.skill_ledger.candidates:
            gaps.append(f"{self.update_id} has no skill candidates")
        if self.needs_reuse_evidence_skill_ids:
            gaps.append(
                "skill candidates need reuse evidence: "
                + ", ".join(self.needs_reuse_evidence_skill_ids)
            )
        if self.missing_required_role_ids:
            gaps.append(
                "missing required skill-review roles: "
                + ", ".join(self.missing_required_role_ids)
            )
        if self.incomplete_required_role_ids:
            gaps.append(
                "incomplete required skill-review roles: "
                + ", ".join(self.incomplete_required_role_ids)
            )
        if self.role_artifact_bundle.readiness_gaps:
            gaps.extend(
                f"role artifact gap: {gap}"
                for gap in self.role_artifact_bundle.readiness_gaps
                if _gap_mentions_required_scope(gap, self.required_role_ids)
            )
        if self.validated_skill_ids and not self._has_complete_skill_reviewer_role:
            gaps.append(
                "validated skills require complete learning-archivist role artifact"
            )
        if self.validated_skill_ids and not self.allowed_transfer_domains:
            gaps.append("validated skills require allowed transfer domains")
        if self.validated_skill_ids and not self.reuse_limitations:
            gaps.append("validated skills require explicit reuse limitations")
        if self.validated_skill_ids and not self.reuse_evidence_ids:
            gaps.append("validated skills require linked reuse evidence ids")
        return tuple(gaps)

    @property
    def blocking_gaps(self) -> tuple[str, ...]:
        """Return blocking gaps that stop skill-genome progress."""

        gaps: list[str] = []
        if self.rejected_skill_ids:
            gaps.append(
                "skill candidates rejected: " + ", ".join(self.rejected_skill_ids)
            )
        if self.blocked_skill_ids:
            gaps.append(
                "skill candidates blocked: " + ", ".join(self.blocked_skill_ids)
            )
        if self.blocked_required_role_ids:
            gaps.append(
                "blocked required skill-review roles: "
                + ", ".join(self.blocked_required_role_ids)
            )
        return tuple(gaps)

    @property
    def status(self) -> SkillGenomeUpdateStatus:
        """Return the fail-closed skill-genome update status."""

        if self.blocking_gaps:
            return SkillGenomeUpdateStatus.BLOCKED
        if self.needs_reuse_evidence_skill_ids:
            return SkillGenomeUpdateStatus.NEEDS_REUSE_EVIDENCE
        if self.readiness_gaps:
            return SkillGenomeUpdateStatus.NEEDS_EVIDENCE
        return SkillGenomeUpdateStatus.READY_FOR_HUMAN_REVIEW

    @property
    def ready_for_human_review(self) -> bool:
        """Return whether this update record may enter human review."""

        return self.status is SkillGenomeUpdateStatus.READY_FOR_HUMAN_REVIEW

    @property
    def may_request_skill_genome_update_review(self) -> bool:
        """Return whether validated skills may be presented for human review."""

        return bool(self.validated_skill_ids) and self.ready_for_human_review

    @property
    def human_authority_state(self) -> WaveThreeAuthorityState:
        """Return aggregate human-authority state for this skill update."""

        if self.status is SkillGenomeUpdateStatus.BLOCKED:
            return WaveThreeAuthorityState.BLOCKED
        return WaveThreeAuthorityState.HUMAN_REVIEW_REQUIRED

    @property
    def review_summary(self) -> str:
        """Return a concise human-review summary."""

        return (
            f"{self.update_id}: {self.status.value}; "
            f"{len(self.validated_skill_ids)} validated, "
            f"{len(self.needs_reuse_evidence_skill_ids)} need reuse evidence, "
            f"{len(self.rejected_skill_ids)} rejected, "
            f"{len(self.blocked_skill_ids)} blocked; "
            "automatic skill install is not permitted."
        )

    @property
    def _has_complete_skill_reviewer_role(self) -> bool:
        """Return whether learning-archivist is complete in the role bundle."""

        return SKILL_GENOME_REVIEWER_ROLE_ID in self.role_artifact_bundle.complete_role_ids

    def reuse_records_for_validated_skills(self) -> tuple[SkillReuseEvidenceRecord, ...]:
        """Return reuse evidence records cited by validated skill validations."""

        validated_reuse_ids = set(self.validation_reuse_record_ids)
        return tuple(
            reuse
            for reuse in self.skill_ledger.reuse_records
            if reuse.reuse_id in validated_reuse_ids
        )

    def validation_for_skill(self, skill_id: str) -> SkillValidationRecord:
        """Return the skill validation record for a skill id."""

        return self.skill_ledger.validation_for_skill(skill_id)

    def to_artifact_ref(self) -> WaveThreeArtifactRef:
        """Convert this update into a shared Wave 3 artifact reference."""

        if self.status is SkillGenomeUpdateStatus.READY_FOR_HUMAN_REVIEW:
            decision = WaveThreeArtifactDecision.READY_FOR_HUMAN_REVIEW
            authority_state = WaveThreeAuthorityState.HUMAN_REVIEW_REQUIRED
        elif self.status is SkillGenomeUpdateStatus.BLOCKED:
            decision = WaveThreeArtifactDecision.BLOCKED
            authority_state = WaveThreeAuthorityState.BLOCKED
        else:
            decision = WaveThreeArtifactDecision.NEEDS_EVIDENCE
            authority_state = WaveThreeAuthorityState.HUMAN_REVIEW_REQUIRED
        return WaveThreeArtifactRef(
            artifact_id=self.artifact_id,
            kind=WaveThreeArtifactKind.SKILL_GENOME_UPDATE,
            source_system=WaveThreeSourceSystem.IX_COGNITION_KERNEL,
            summary=self.review_summary,
            produced_by_engine_id="skill-genome",
            produced_by_agent_role_id=self.reviewer_role_id,
            evidence_ids=self.all_evidence_ids,
            decision=decision,
            authority_state=authority_state,
        )

    def to_artifact_bundle(self, *, artifact_bundle_id: str) -> WaveThreeArtifactBundle:
        """Convert this skill update into a shared artifact bundle."""

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
                        "Skill validation and role-review evidence gate reusable "
                        "skill updates without automatic installation."
                    ),
                    source_system=WaveThreeSourceSystem.LOCAL_TEST_SUITE,
                )
                for evidence_id in artifact.evidence_ids
            ),
            required_kinds=(WaveThreeArtifactKind.SKILL_GENOME_UPDATE,),
            notes=("Skill-genome updates request review; they do not install skills.",),
        )

    def canonical_payload(self) -> dict[str, Any]:
        """Return a deterministic payload for hashing and export."""

        return {
            "allowed_transfer_domains": list(self.allowed_transfer_domains),
            "all_evidence_ids": list(self.all_evidence_ids),
            "artifact_id": self.artifact_id,
            "blocked_skill_ids": list(self.blocked_skill_ids),
            "blocking_gaps": list(self.blocking_gaps),
            "candidate_skill_ids": list(self.candidate_skill_ids),
            "human_authority_state": self.human_authority_state.value,
            "may_request_skill_genome_update_review": (
                self.may_request_skill_genome_update_review
            ),
            "needs_reuse_evidence_skill_ids": list(self.needs_reuse_evidence_skill_ids),
            "permits_automatic_execution": self.permits_automatic_execution,
            "permits_automatic_skill_install": self.permits_automatic_skill_install,
            "readiness_gaps": list(self.readiness_gaps),
            "rejected_skill_ids": list(self.rejected_skill_ids),
            "required_role_ids": list(self.required_role_ids),
            "reuse_limitations": list(self.reuse_limitations),
            "review_summary": self.review_summary,
            "reviewer_role_id": self.reviewer_role_id,
            "role_artifact_bundle_fingerprint": self.role_artifact_bundle.fingerprint(),
            "schema_version": self.schema_version,
            "status": self.status.value,
            "update_id": self.update_id,
            "validated_skill_ids": list(self.validated_skill_ids),
            "validation_reuse_record_ids": list(self.validation_reuse_record_ids),
        }

    def fingerprint(self) -> str:
        """Return a deterministic SHA-256 fingerprint for this update."""

        return _stable_sha256(self.canonical_payload())


@dataclass(frozen=True, slots=True)
class SkillGenomeUpdateBundle:
    """Deterministic bundle of governed skill-genome update records."""

    bundle_id: str
    updates: tuple[SkillGenomeUpdateRecord, ...]
    notes: tuple[str, ...] = ()
    schema_version: str = WAVE_THREE_SKILL_GENOME_BUNDLE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate update uniqueness and bundle reviewability."""

        object.__setattr__(self, "bundle_id", _text(self.bundle_id, "bundle_id"))
        if not self.updates:
            raise ValueError("Skill-genome update bundles require at least one update.")
        updates = tuple(sorted(self.updates, key=lambda item: item.update_id))
        _unique_values((update.update_id for update in updates), label="update_id")
        object.__setattr__(self, "updates", updates)
        object.__setattr__(
            self, "notes", _unique_text(self.notes, label="skill update bundle note")
        )
        object.__setattr__(
            self, "schema_version", _text(self.schema_version, "schema_version")
        )

    @property
    def update_ids(self) -> tuple[str, ...]:
        """Return update ids in deterministic order."""

        return tuple(update.update_id for update in self.updates)

    @property
    def ready_update_ids(self) -> tuple[str, ...]:
        """Return update ids ready for human review."""

        return tuple(
            update.update_id for update in self.updates if update.ready_for_human_review
        )

    @property
    def blocked_update_ids(self) -> tuple[str, ...]:
        """Return blocked update ids."""

        return tuple(
            update.update_id
            for update in self.updates
            if update.status is SkillGenomeUpdateStatus.BLOCKED
        )

    @property
    def readiness_gaps(self) -> tuple[str, ...]:
        """Return bundle-level and update-level gaps."""

        gaps: list[str] = []
        for update in self.updates:
            gaps.extend(update.readiness_gaps)
            gaps.extend(update.blocking_gaps)
        return tuple(gaps)

    @property
    def is_complete_for_human_review(self) -> bool:
        """Return whether every skill update is review-ready."""

        return not self.readiness_gaps and len(self.ready_update_ids) == len(
            self.updates
        )

    def update_by_id(self, update_id: str) -> SkillGenomeUpdateRecord:
        """Return one skill-genome update by id."""

        normalized = _text(update_id, "update_id")
        for update in self.updates:
            if update.update_id == normalized:
                return update
        raise ValueError(f"Unknown skill genome update_id: {update_id}")

    def to_artifact_bundle(self, *, artifact_bundle_id: str) -> WaveThreeArtifactBundle:
        """Convert skill-genome updates into a shared artifact bundle."""

        artifacts = tuple(update.to_artifact_ref() for update in self.updates)
        return WaveThreeArtifactBundle(
            bundle_id=artifact_bundle_id,
            artifacts=artifacts,
            evidence_links=tuple(
                WaveThreeEvidenceLink(
                    evidence_id=evidence_id,
                    artifact_id=artifact.artifact_id,
                    relation=WaveThreeEvidenceRelation.REVIEWS,
                    summary=(
                        "Skill-genome update evidence preserves validation, reuse, "
                        "transfer, and human-review boundaries."
                    ),
                    source_system=WaveThreeSourceSystem.LOCAL_TEST_SUITE,
                )
                for artifact in artifacts
                for evidence_id in artifact.evidence_ids
            ),
            required_kinds=(WaveThreeArtifactKind.SKILL_GENOME_UPDATE,),
            notes=("Skill-genome bundles remain review-only artifacts.",),
        )

    def canonical_payload(self) -> dict[str, Any]:
        """Return a deterministic payload for hashing and export."""

        return {
            "bundle_id": self.bundle_id,
            "notes": list(self.notes),
            "readiness_gaps": list(self.readiness_gaps),
            "schema_version": self.schema_version,
            "updates": [update.canonical_payload() for update in self.updates],
        }

    def fingerprint(self) -> str:
        """Return a deterministic SHA-256 fingerprint for this bundle."""

        return _stable_sha256(self.canonical_payload())


def _validate_required_roles_are_in_bundle(
    *, required_role_ids: tuple[str, ...], role_artifact_bundle: RoleArtifactBundle
) -> None:
    """Reject updates whose role scope is not represented by the bundle."""

    represented = set(role_artifact_bundle.record_role_ids)
    missing = tuple(
        role_id for role_id in required_role_ids if role_id not in represented
    )
    if missing:
        raise ValueError(
            "Skill-genome updates require bundled role artifacts: " + ", ".join(missing)
        )


def _validate_skill_validations_are_learning_archivist_reviewed(
    validations: tuple[SkillValidationRecord, ...],
) -> None:
    """Reject validation records reviewed outside the learning archivist role."""

    for validation in validations:
        if validation.reviewer_role_id != SKILL_GENOME_REVIEWER_ROLE_ID:
            raise ValueError(
                "Skill validation records must be reviewed by "
                f"{SKILL_GENOME_REVIEWER_ROLE_ID}: {validation.validation_id}"
            )


def _gap_mentions_required_scope(gap: str, required_role_ids: tuple[str, ...]) -> bool:
    """Return whether a role bundle gap names the required skill-review scope."""

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
