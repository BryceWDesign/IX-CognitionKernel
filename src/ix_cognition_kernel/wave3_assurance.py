"""Wave 3 assurance-style evidence records for IX-CognitionKernel.

Wave 3 cannot be treated as earned merely because many artifacts exist. The
assurance layer binds artifact bundles to bounded, reviewable claims: evidence
traceability, preserved human authority, no automatic execution, visible
uncertainty, donor-boundary compatibility, and explicit anti-AGI-overclaim
limits. These records are not certification, production approval, or execution
authority.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, TypeVar

from ix_cognition_kernel.wave3_contracts import (
    WaveThreeArtifactBundle,
    WaveThreeArtifactDecision,
    WaveThreeArtifactKind,
    WaveThreeArtifactRef,
    WaveThreeAuthorityState,
    WaveThreeEvidenceLink,
    WaveThreeEvidenceRelation,
    WaveThreeSourceSystem,
    required_wave_three_artifact_kinds,
)

T = TypeVar("T")
E = TypeVar("E", bound=StrEnum)

WAVE_THREE_ASSURANCE_CLAIM_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave3-assurance-claim-v1"
)
WAVE_THREE_ASSURANCE_RECORD_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave3-assurance-record-v1"
)
WAVE_THREE_ASSURANCE_BUNDLE_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave3-assurance-bundle-v1"
)


class AssuranceClaimKind(StrEnum):
    """Bounded claim families required for Wave 3 assurance review."""

    EVIDENCE_TRACEABILITY = "evidence-traceability"
    HUMAN_AUTHORITY_PRESERVED = "human-authority-preserved"
    NO_AUTOMATIC_EXECUTION = "no-automatic-execution"
    UNCERTAINTY_VISIBLE = "uncertainty-visible"
    DONOR_BOUNDARY_COMPATIBLE = "donor-boundary-compatible"
    NO_AGI_OVERCLAIM = "no-agi-overclaim"


class AssuranceClaimStatus(StrEnum):
    """Fail-closed status for one assurance claim."""

    SUPPORTED = "supported"
    NEEDS_EVIDENCE = "needs-evidence"
    DISPUTED = "disputed"
    BLOCKED = "blocked"


class AssuranceRecordStatus(StrEnum):
    """Fail-closed status for an assurance record."""

    READY_FOR_HUMAN_REVIEW = "ready-for-human-review"
    NEEDS_EVIDENCE = "needs-evidence"
    NEEDS_REPAIR = "needs-repair"
    BLOCKED = "blocked"


REQUIRED_ASSURANCE_CLAIM_KINDS: tuple[AssuranceClaimKind, ...] = (
    AssuranceClaimKind.EVIDENCE_TRACEABILITY,
    AssuranceClaimKind.HUMAN_AUTHORITY_PRESERVED,
    AssuranceClaimKind.NO_AUTOMATIC_EXECUTION,
    AssuranceClaimKind.UNCERTAINTY_VISIBLE,
    AssuranceClaimKind.DONOR_BOUNDARY_COMPATIBLE,
    AssuranceClaimKind.NO_AGI_OVERCLAIM,
)


@dataclass(frozen=True, slots=True)
class AssuranceClaim:
    """One bounded, evidence-backed claim about the Wave 3 substrate."""

    claim_id: str
    claim_kind: AssuranceClaimKind
    statement: str
    supporting_artifact_ids: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    limitations: tuple[str, ...]
    confidence: float
    status: AssuranceClaimStatus = AssuranceClaimStatus.NEEDS_EVIDENCE
    reviewer_role_id: str = "verifier"
    blocking_reasons: tuple[str, ...] = ()
    schema_version: str = WAVE_THREE_ASSURANCE_CLAIM_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate claim evidence, limits, confidence, and blocked state."""

        object.__setattr__(self, "claim_id", _text(self.claim_id, "claim_id"))
        object.__setattr__(self, "statement", _text(self.statement, "claim statement"))
        object.__setattr__(
            self,
            "supporting_artifact_ids",
            _unique_text(
                self.supporting_artifact_ids,
                label="supporting artifact_id",
            ),
        )
        object.__setattr__(
            self,
            "evidence_ids",
            _unique_text(self.evidence_ids, label="assurance claim evidence_id"),
        )
        object.__setattr__(
            self,
            "limitations",
            _unique_text(self.limitations, label="assurance limitation"),
        )
        if not self.limitations:
            raise ValueError("Assurance claims require explicit limitations.")
        confidence = float(self.confidence)
        if confidence < 0.0 or confidence > 1.0:
            raise ValueError("assurance claim confidence must be between 0.0 and 1.0")
        object.__setattr__(self, "confidence", confidence)
        object.__setattr__(
            self, "reviewer_role_id", _text(self.reviewer_role_id, "reviewer_role_id")
        )
        object.__setattr__(
            self,
            "blocking_reasons",
            _unique_text(self.blocking_reasons, label="claim blocking reason"),
        )
        object.__setattr__(
            self, "schema_version", _text(self.schema_version, "schema_version")
        )
        if self.status is AssuranceClaimStatus.SUPPORTED and (
            not self.supporting_artifact_ids or not self.evidence_ids
        ):
            raise ValueError(
                "Supported assurance claims require artifact ids and evidence ids."
            )
        if self.status is AssuranceClaimStatus.BLOCKED and not self.blocking_reasons:
            raise ValueError("Blocked assurance claims require blocking reasons.")
        if self.status is not AssuranceClaimStatus.BLOCKED and self.blocking_reasons:
            raise ValueError(
                "Only blocked assurance claims may carry blocking reasons."
            )

    @property
    def claim_key(self) -> tuple[str, str]:
        """Return deterministic uniqueness key for this assurance claim."""

        return (self.claim_id, self.claim_kind.value)

    @property
    def ready_for_human_review(self) -> bool:
        """Return whether this claim can support an assurance record."""

        return self.status is AssuranceClaimStatus.SUPPORTED

    @property
    def blocks_progress(self) -> bool:
        """Return whether this claim blocks assurance progress."""

        return self.status is AssuranceClaimStatus.BLOCKED

    @property
    def readiness_gaps(self) -> tuple[str, ...]:
        """Return non-blocking gaps for this claim."""

        gaps: list[str] = []
        if not self.supporting_artifact_ids:
            gaps.append(f"{self.claim_id} has no supporting artifact ids")
        if not self.evidence_ids:
            gaps.append(f"{self.claim_id} has no evidence ids")
        if self.status is AssuranceClaimStatus.NEEDS_EVIDENCE:
            gaps.append(f"{self.claim_id} needs evidence")
        if self.status is AssuranceClaimStatus.DISPUTED:
            gaps.append(f"{self.claim_id} is disputed and needs repair")
        return tuple(gaps)

    @property
    def blocking_gaps(self) -> tuple[str, ...]:
        """Return blocking gaps for this claim."""

        if not self.blocks_progress:
            return ()
        return tuple(
            f"{self.claim_id} blocked: {reason}" for reason in self.blocking_reasons
        )

    def canonical_payload(self) -> dict[str, Any]:
        """Return a deterministic payload for hashing and export."""

        return {
            "blocking_gaps": list(self.blocking_gaps),
            "blocking_reasons": list(self.blocking_reasons),
            "claim_id": self.claim_id,
            "claim_kind": self.claim_kind.value,
            "confidence": self.confidence,
            "evidence_ids": list(self.evidence_ids),
            "limitations": list(self.limitations),
            "readiness_gaps": list(self.readiness_gaps),
            "reviewer_role_id": self.reviewer_role_id,
            "schema_version": self.schema_version,
            "statement": self.statement,
            "status": self.status.value,
            "supporting_artifact_ids": list(self.supporting_artifact_ids),
        }

    def fingerprint(self) -> str:
        """Return a deterministic SHA-256 fingerprint for this claim."""

        return _stable_sha256(self.canonical_payload())


@dataclass(frozen=True, slots=True)
class AssuranceRecord:
    """Reviewable Wave 3 assurance record over artifact bundles and claims."""

    assurance_id: str
    artifact_bundles: tuple[WaveThreeArtifactBundle, ...]
    claims: tuple[AssuranceClaim, ...]
    evidence_ids: tuple[str, ...]
    required_claim_kinds: tuple[AssuranceClaimKind, ...] = (
        REQUIRED_ASSURANCE_CLAIM_KINDS
    )
    required_artifact_kinds: tuple[WaveThreeArtifactKind, ...] = (
        required_wave_three_artifact_kinds()
    )
    reviewer_role_id: str = "verifier"
    schema_version: str = WAVE_THREE_ASSURANCE_RECORD_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate artifact coverage, claims, evidence, and overclaim bounds."""

        object.__setattr__(
            self, "assurance_id", _text(self.assurance_id, "assurance_id")
        )
        if not self.artifact_bundles:
            raise ValueError("Assurance records require artifact bundles.")
        sorted_bundles = tuple(
            sorted(self.artifact_bundles, key=lambda bundle: bundle.bundle_id)
        )
        _unique_values(
            (bundle.bundle_id for bundle in sorted_bundles), label="artifact bundle_id"
        )
        object.__setattr__(self, "artifact_bundles", sorted_bundles)
        if not self.claims:
            raise ValueError("Assurance records require assurance claims.")
        sorted_claims = tuple(sorted(self.claims, key=lambda claim: claim.claim_key))
        _unique_values((claim.claim_id for claim in sorted_claims), label="claim_id")
        _unique_values(
            (claim.claim_kind for claim in sorted_claims), label="assurance claim kind"
        )
        object.__setattr__(self, "claims", sorted_claims)
        object.__setattr__(
            self,
            "evidence_ids",
            _unique_text(self.evidence_ids, label="assurance record evidence_id"),
        )
        object.__setattr__(
            self,
            "required_claim_kinds",
            _unique_enum(self.required_claim_kinds, label="required claim kind"),
        )
        object.__setattr__(
            self,
            "required_artifact_kinds",
            _unique_enum(self.required_artifact_kinds, label="required artifact kind"),
        )
        object.__setattr__(
            self, "reviewer_role_id", _text(self.reviewer_role_id, "reviewer_role_id")
        )
        object.__setattr__(
            self, "schema_version", _text(self.schema_version, "schema_version")
        )
        _validate_claim_artifacts_exist(
            claims=sorted_claims,
            artifact_ids=set(self.artifact_ids),
        )

    @property
    def artifact_id(self) -> str:
        """Return the shared Wave 3 artifact id for this assurance record."""

        return f"assurance-record:{self.assurance_id}"

    @property
    def artifacts(self) -> tuple[WaveThreeArtifactRef, ...]:
        """Return all artifact refs from all bundled artifact bundles."""

        return tuple(
            artifact
            for bundle in self.artifact_bundles
            for artifact in bundle.artifacts
        )

    @property
    def artifact_ids(self) -> tuple[str, ...]:
        """Return artifact ids represented by all bundles."""

        return tuple(sorted(artifact.artifact_id for artifact in self.artifacts))

    @property
    def represented_artifact_kinds(self) -> tuple[WaveThreeArtifactKind, ...]:
        """Return represented artifact kinds in required-kind order."""

        present = {artifact.kind for artifact in self.artifacts}
        required_order = tuple(
            kind for kind in self.required_artifact_kinds if kind in present
        )
        extra_order = tuple(
            sorted(
                (kind for kind in present if kind not in set(required_order)),
                key=lambda kind: kind.value,
            )
        )
        return required_order + extra_order

    @property
    def missing_required_artifact_kinds(self) -> tuple[WaveThreeArtifactKind, ...]:
        """Return required Wave 3 artifact kinds missing from assurance evidence."""

        present = {artifact.kind for artifact in self.artifacts}
        return tuple(
            kind for kind in self.required_artifact_kinds if kind not in present
        )

    @property
    def missing_required_claim_kinds(self) -> tuple[AssuranceClaimKind, ...]:
        """Return required assurance claim kinds not represented."""

        present = {claim.claim_kind for claim in self.claims}
        return tuple(kind for kind in self.required_claim_kinds if kind not in present)

    @property
    def unsupported_claim_ids(self) -> tuple[str, ...]:
        """Return claim ids that are not supported."""

        return tuple(
            claim.claim_id for claim in self.claims if not claim.ready_for_human_review
        )

    @property
    def blocked_claim_ids(self) -> tuple[str, ...]:
        """Return claim ids that block assurance progress."""

        return tuple(claim.claim_id for claim in self.claims if claim.blocks_progress)

    @property
    def blocked_artifact_ids(self) -> tuple[str, ...]:
        """Return artifact ids that block assurance progress."""

        return tuple(
            artifact.artifact_id
            for artifact in self.artifacts
            if artifact.blocks_progress
        )

    @property
    def executable_artifact_ids(self) -> tuple[str, ...]:
        """Return artifact ids that incorrectly attempt automatic execution."""

        return tuple(
            artifact.artifact_id
            for artifact in self.artifacts
            if artifact.allowed_for_automatic_execution
        )

    @property
    def claim_evidence_ids(self) -> tuple[str, ...]:
        """Return sorted unique evidence ids from claims."""

        return tuple(
            sorted(
                evidence_id
                for claim in self.claims
                for evidence_id in claim.evidence_ids
            )
        )

    @property
    def artifact_evidence_ids(self) -> tuple[str, ...]:
        """Return sorted unique evidence ids from artifacts."""

        return tuple(
            sorted(
                evidence_id
                for artifact in self.artifacts
                for evidence_id in artifact.evidence_ids
            )
        )

    @property
    def all_evidence_ids(self) -> tuple[str, ...]:
        """Return sorted unique assurance, claim, and artifact evidence ids."""

        return tuple(
            sorted(
                set(self.evidence_ids).union(
                    self.claim_evidence_ids,
                    self.artifact_evidence_ids,
                )
            )
        )

    @property
    def permits_automatic_execution(self) -> bool:
        """Return whether this assurance record permits automatic execution."""

        return False

    @property
    def certifies_agi(self) -> bool:
        """Return whether this record certifies AGI.

        This is intentionally always false. Wave 3 is governed AGI-emulation
        substrate work, not an AGI claim.
        """

        return False

    @property
    def readiness_gaps(self) -> tuple[str, ...]:
        """Return non-blocking gaps that prevent human-review readiness."""

        gaps: list[str] = []
        if not self.evidence_ids:
            gaps.append(f"{self.assurance_id} has no top-level evidence ids")
        if self.missing_required_artifact_kinds:
            gaps.append(
                "missing required Wave 3 artifact kinds: "
                + ", ".join(kind.value for kind in self.missing_required_artifact_kinds)
            )
        if self.missing_required_claim_kinds:
            gaps.append(
                "missing required assurance claim kinds: "
                + ", ".join(kind.value for kind in self.missing_required_claim_kinds)
            )
        if self.unsupported_claim_ids:
            gaps.append(
                "unsupported assurance claims: " + ", ".join(self.unsupported_claim_ids)
            )
        for claim in self.claims:
            gaps.extend(claim.readiness_gaps)
        return tuple(gaps)

    @property
    def blocking_gaps(self) -> tuple[str, ...]:
        """Return blocking gaps that stop assurance progress."""

        gaps: list[str] = []
        if self.blocked_artifact_ids:
            gaps.append(
                "blocked Wave 3 artifacts: " + ", ".join(self.blocked_artifact_ids)
            )
        if self.executable_artifact_ids:
            gaps.append(
                "artifacts attempted automatic execution: "
                + ", ".join(self.executable_artifact_ids)
            )
        if self.blocked_claim_ids:
            gaps.append(
                "blocked assurance claims: " + ", ".join(self.blocked_claim_ids)
            )
        for claim in self.claims:
            gaps.extend(claim.blocking_gaps)
        return tuple(gaps)

    @property
    def status(self) -> AssuranceRecordStatus:
        """Return the fail-closed assurance record status."""

        if self.blocking_gaps:
            return AssuranceRecordStatus.BLOCKED
        if self.unsupported_claim_ids:
            return AssuranceRecordStatus.NEEDS_REPAIR
        if self.readiness_gaps:
            return AssuranceRecordStatus.NEEDS_EVIDENCE
        return AssuranceRecordStatus.READY_FOR_HUMAN_REVIEW

    @property
    def ready_for_human_review(self) -> bool:
        """Return whether this assurance record may enter human review."""

        return self.status is AssuranceRecordStatus.READY_FOR_HUMAN_REVIEW

    @property
    def human_authority_state(self) -> WaveThreeAuthorityState:
        """Return aggregate human-authority state for this assurance record."""

        if self.status is AssuranceRecordStatus.BLOCKED:
            return WaveThreeAuthorityState.BLOCKED
        return WaveThreeAuthorityState.HUMAN_REVIEW_REQUIRED

    @property
    def review_summary(self) -> str:
        """Return a concise human-review summary."""

        return (
            f"{self.assurance_id}: {self.status.value}; "
            f"{len(self.claims)} claims, {len(self.artifacts)} artifacts, "
            f"{len(self.missing_required_artifact_kinds)} missing artifact kinds; "
            "automatic execution and AGI certification are not permitted."
        )

    def to_artifact_ref(self) -> WaveThreeArtifactRef:
        """Convert this assurance record into a shared Wave 3 artifact reference."""

        if self.status is AssuranceRecordStatus.READY_FOR_HUMAN_REVIEW:
            decision = WaveThreeArtifactDecision.READY_FOR_HUMAN_REVIEW
            authority_state = WaveThreeAuthorityState.HUMAN_REVIEW_REQUIRED
        elif self.status is AssuranceRecordStatus.BLOCKED:
            decision = WaveThreeArtifactDecision.BLOCKED
            authority_state = WaveThreeAuthorityState.BLOCKED
        else:
            decision = WaveThreeArtifactDecision.NEEDS_EVIDENCE
            authority_state = WaveThreeAuthorityState.HUMAN_REVIEW_REQUIRED
        return WaveThreeArtifactRef(
            artifact_id=self.artifact_id,
            kind=WaveThreeArtifactKind.ASSURANCE_RECORD,
            source_system=WaveThreeSourceSystem.IX_COGNITION_KERNEL,
            summary=self.review_summary,
            produced_by_engine_id="evaluator",
            produced_by_agent_role_id=self.reviewer_role_id,
            evidence_ids=self.all_evidence_ids,
            decision=decision,
            authority_state=authority_state,
        )

    def to_artifact_bundle(self, *, artifact_bundle_id: str) -> WaveThreeArtifactBundle:
        """Convert this assurance record into a shared artifact bundle."""

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
                        "Assurance evidence links bounded claims to Wave 3 artifacts "
                        "without certification, AGI claims, or execution authority."
                    ),
                    source_system=WaveThreeSourceSystem.LOCAL_TEST_SUITE,
                )
                for evidence_id in artifact.evidence_ids
            ),
            required_kinds=(WaveThreeArtifactKind.ASSURANCE_RECORD,),
            notes=(
                "Assurance records are bounded human-review artifacts, not "
                "certification or deployment approval.",
            ),
        )

    def canonical_payload(self) -> dict[str, Any]:
        """Return a deterministic payload for hashing and export."""

        return {
            "all_evidence_ids": list(self.all_evidence_ids),
            "artifact_bundle_fingerprints": [
                bundle.fingerprint() for bundle in self.artifact_bundles
            ],
            "artifact_id": self.artifact_id,
            "artifact_ids": list(self.artifact_ids),
            "assurance_id": self.assurance_id,
            "blocking_gaps": list(self.blocking_gaps),
            "certifies_agi": self.certifies_agi,
            "claims": [claim.canonical_payload() for claim in self.claims],
            "human_authority_state": self.human_authority_state.value,
            "missing_required_artifact_kinds": [
                kind.value for kind in self.missing_required_artifact_kinds
            ],
            "missing_required_claim_kinds": [
                kind.value for kind in self.missing_required_claim_kinds
            ],
            "permits_automatic_execution": self.permits_automatic_execution,
            "readiness_gaps": list(self.readiness_gaps),
            "review_summary": self.review_summary,
            "reviewer_role_id": self.reviewer_role_id,
            "schema_version": self.schema_version,
            "status": self.status.value,
        }

    def fingerprint(self) -> str:
        """Return a deterministic SHA-256 fingerprint for this record."""

        return _stable_sha256(self.canonical_payload())


@dataclass(frozen=True, slots=True)
class AssuranceRecordBundle:
    """Deterministic bundle of Wave 3 assurance records."""

    bundle_id: str
    records: tuple[AssuranceRecord, ...]
    notes: tuple[str, ...] = ()
    schema_version: str = WAVE_THREE_ASSURANCE_BUNDLE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate assurance record uniqueness and bundle reviewability."""

        object.__setattr__(self, "bundle_id", _text(self.bundle_id, "bundle_id"))
        if not self.records:
            raise ValueError("Assurance record bundles require at least one record.")
        records = tuple(sorted(self.records, key=lambda record: record.assurance_id))
        _unique_values(
            (record.assurance_id for record in records), label="assurance_id"
        )
        object.__setattr__(self, "records", records)
        object.__setattr__(
            self, "notes", _unique_text(self.notes, label="assurance bundle note")
        )
        object.__setattr__(
            self, "schema_version", _text(self.schema_version, "schema_version")
        )

    @property
    def assurance_ids(self) -> tuple[str, ...]:
        """Return assurance ids in deterministic order."""

        return tuple(record.assurance_id for record in self.records)

    @property
    def ready_assurance_ids(self) -> tuple[str, ...]:
        """Return assurance record ids ready for human review."""

        return tuple(
            record.assurance_id
            for record in self.records
            if record.ready_for_human_review
        )

    @property
    def blocked_assurance_ids(self) -> tuple[str, ...]:
        """Return blocked assurance record ids."""

        return tuple(
            record.assurance_id
            for record in self.records
            if record.status is AssuranceRecordStatus.BLOCKED
        )

    @property
    def readiness_gaps(self) -> tuple[str, ...]:
        """Return bundle-level and record-level gaps."""

        gaps: list[str] = []
        for record in self.records:
            gaps.extend(record.readiness_gaps)
            gaps.extend(record.blocking_gaps)
        return tuple(gaps)

    @property
    def is_complete_for_human_review(self) -> bool:
        """Return whether every assurance record is review-ready."""

        return not self.readiness_gaps and len(self.ready_assurance_ids) == len(
            self.records
        )

    def record_by_id(self, assurance_id: str) -> AssuranceRecord:
        """Return one assurance record by id."""

        normalized = _text(assurance_id, "assurance_id")
        for record in self.records:
            if record.assurance_id == normalized:
                return record
        raise ValueError(f"Unknown assurance_id: {assurance_id}")

    def to_artifact_bundle(self, *, artifact_bundle_id: str) -> WaveThreeArtifactBundle:
        """Convert assurance records into a shared artifact bundle."""

        artifacts = tuple(record.to_artifact_ref() for record in self.records)
        return WaveThreeArtifactBundle(
            bundle_id=artifact_bundle_id,
            artifacts=artifacts,
            evidence_links=tuple(
                WaveThreeEvidenceLink(
                    evidence_id=evidence_id,
                    artifact_id=artifact.artifact_id,
                    relation=WaveThreeEvidenceRelation.REVIEWS,
                    summary=(
                        "Assurance bundle evidence preserves traceability, "
                        "human authority, and anti-overclaim boundaries."
                    ),
                    source_system=WaveThreeSourceSystem.LOCAL_TEST_SUITE,
                )
                for artifact in artifacts
                for evidence_id in artifact.evidence_ids
            ),
            required_kinds=(WaveThreeArtifactKind.ASSURANCE_RECORD,),
            notes=("Assurance bundles remain bounded review artifacts.",),
        )

    def canonical_payload(self) -> dict[str, Any]:
        """Return a deterministic payload for hashing and export."""

        return {
            "bundle_id": self.bundle_id,
            "notes": list(self.notes),
            "readiness_gaps": list(self.readiness_gaps),
            "records": [record.canonical_payload() for record in self.records],
            "schema_version": self.schema_version,
        }

    def fingerprint(self) -> str:
        """Return a deterministic SHA-256 fingerprint for this bundle."""

        return _stable_sha256(self.canonical_payload())


def supported_assurance_claim(
    *,
    claim_id: str,
    claim_kind: AssuranceClaimKind,
    statement: str,
    supporting_artifact_ids: tuple[str, ...],
    evidence_ids: tuple[str, ...],
    limitations: tuple[str, ...],
    confidence: float = 0.9,
) -> AssuranceClaim:
    """Create a supported assurance claim with explicit limitations."""

    return AssuranceClaim(
        claim_id=claim_id,
        claim_kind=claim_kind,
        statement=statement,
        supporting_artifact_ids=supporting_artifact_ids,
        evidence_ids=evidence_ids,
        limitations=limitations,
        confidence=confidence,
        status=AssuranceClaimStatus.SUPPORTED,
    )


def _validate_claim_artifacts_exist(
    *, claims: tuple[AssuranceClaim, ...], artifact_ids: set[str]
) -> None:
    """Reject assurance claims that cite artifacts absent from the record."""

    for claim in claims:
        for artifact_id in claim.supporting_artifact_ids:
            if artifact_id not in artifact_ids:
                raise ValueError(
                    "Assurance claims must reference bundled artifact ids: "
                    f"{claim.claim_id}:{artifact_id}"
                )


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


def _unique_enum(values: Iterable[E], *, label: str) -> tuple[E, ...]:
    """Normalize enum tuples while rejecting duplicates."""

    normalized = tuple(values)
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
