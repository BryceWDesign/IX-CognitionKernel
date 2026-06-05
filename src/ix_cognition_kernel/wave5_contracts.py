"""Shared Wave 5 independent-validation contracts for IX-CognitionKernel.

Wave 5 is the credible AGI-candidate-under-independent-validation layer. These
contracts define the evidence vocabulary used by later Wave 5 modules before any
maturity declaration is allowed. They do not make an AGI claim, do not treat
self-review as independent validation, and do not grant execution authority.

The module intentionally creates the bridge Wave 6 will depend on: external
protocols, independent reviewer evidence, reproducible bundles, adversarial
safety records, long-horizon and cross-domain validation, memory/refusal proofs,
human-authority preservation, ecosystem traceability, and an explicit Wave 6
precondition boundary.
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

WAVE_FIVE_ARTIFACT_SCHEMA_VERSION = "ix-cognition-kernel-wave5-artifact-v1"
WAVE_FIVE_BUNDLE_SCHEMA_VERSION = "ix-cognition-kernel-wave5-bundle-v1"


class WaveFiveCapabilityArea(StrEnum):
    """Independent-validation areas required before Wave 5 is credible."""

    EXTERNAL_PROTOCOLS = "external-protocols"
    INDEPENDENT_REVIEW = "independent-review"
    REPRODUCIBILITY = "reproducibility"
    ADVERSARIAL_SAFETY = "adversarial-safety"
    LONG_HORIZON_VALIDATION = "long-horizon-validation"
    CROSS_DOMAIN_TRANSFER = "cross-domain-transfer"
    BENCHMARK_GAMING_RESISTANCE = "benchmark-gaming-resistance"
    MEMORY_INTEGRITY = "memory-integrity"
    SAFE_REFUSAL = "safe-refusal"
    HUMAN_AUTHORITY_PRESERVATION = "human-authority-preservation"
    ECOSYSTEM_TRACEABILITY = "ecosystem-traceability"
    WAVE_SIX_READINESS_BOUNDARY = "wave-six-readiness-boundary"


class WaveFiveArtifactKind(StrEnum):
    """Required Wave 5 artifact classes."""

    EXTERNAL_PROTOCOL_MANIFEST = "external-protocol-manifest"
    REVIEWER_ATTESTATION = "reviewer-attestation"
    REPRODUCIBLE_EVIDENCE_BUNDLE = "reproducible-evidence-bundle"
    ADVERSARIAL_SAFETY_RECORD = "adversarial-safety-record"
    LONG_HORIZON_TASK_RECORD = "long-horizon-task-record"
    CROSS_DOMAIN_TRANSFER_RECORD = "cross-domain-transfer-record"
    BENCHMARK_CONTAMINATION_AUDIT = "benchmark-contamination-audit"
    MEMORY_INTEGRITY_PROOF = "memory-integrity-proof"
    SAFE_REFUSAL_PROOF = "safe-refusal-proof"
    HUMAN_AUTHORITY_PROOF = "human-authority-proof"
    REPEATABILITY_LEDGER = "repeatability-ledger"
    ECOSYSTEM_TRACEABILITY_MAP = "ecosystem-traceability-map"
    WAVE_SIX_PRECONDITION_LEDGER = "wave-six-precondition-ledger"
    INDEPENDENT_VALIDATION_DOSSIER = "independent-validation-dossier"
    FAIL_CLOSED_SCORECARD = "fail-closed-scorecard"
    REVIEW_BOARD_DOCKET = "review-board-docket"
    MATURITY_DECLARATION = "maturity-declaration"
    RELEASE_MANIFEST = "release-manifest"


class WaveFiveSourceSystem(StrEnum):
    """Source systems allowed to contribute Wave 5 evidence references."""

    IX_COGNITION_KERNEL = "ix-cognition-kernel"
    IX_BLACKFOX = "ix-blackfox"
    IX_BLACKFOX_COGNITION = "ix-blackfox-cognition"
    IX_BLACKFOX_WORLDTWIN = "ix-blackfox-worldtwin"
    HUMAN_REVIEW = "human-review"
    LOCAL_TEST_SUITE = "local-test-suite"
    EXTERNAL_REVIEW = "external-review"
    EXTERNAL_VALIDATION_PROTOCOL = "external-validation-protocol"
    INDEPENDENT_REVIEWER = "independent-reviewer"
    INDEPENDENT_REPLICATION_LAB = "independent-replication-lab"
    ADVERSARIAL_TESTER = "adversarial-tester"


class WaveFiveArtifactDecision(StrEnum):
    """Fail-closed decision state for one Wave 5 artifact."""

    RECORD_ONLY = "record-only"
    NEEDS_EXTERNAL_EVIDENCE = "needs-external-evidence"
    READY_FOR_INDEPENDENT_REVIEW = "ready-for-independent-review"
    EXTERNALLY_REVIEWED = "externally-reviewed"
    BLOCKED = "blocked"


class WaveFiveAuthorityState(StrEnum):
    """Human-authority state carried by Wave 5 artifacts."""

    RECORD_ONLY = "record-only"
    HUMAN_REVIEW_REQUIRED = "human-review-required"
    HUMAN_AUTHORITY_GRANTED = "human-authority-granted"
    BLOCKED = "blocked"


class WaveFiveValidationStatus(StrEnum):
    """Independent-validation state without pretending internal review is enough."""

    NOT_SUBMITTED = "not-submitted"
    MISSING_EXTERNAL_EVIDENCE = "missing-external-evidence"
    UNDER_INDEPENDENT_REVIEW = "under-independent-review"
    EXTERNALLY_REPRODUCED = "externally-reproduced"
    ACCEPTED_WITH_BOUNDARIES = "accepted-with-boundaries"
    DISPUTED = "disputed"
    REJECTED = "rejected"


class WaveFiveEvidenceRelation(StrEnum):
    """How evidence relates to a Wave 5 independent-validation artifact."""

    SUPPORTS = "supports"
    CONTRADICTS = "contradicts"
    TESTS = "tests"
    DERIVES_FROM = "derives-from"
    REVIEWS = "reviews"
    REPRODUCES = "reproduces"
    DISPUTES = "disputes"
    BLOCKS = "blocks"


class WaveFiveClaimBoundary(StrEnum):
    """Claims Wave 5 artifacts must preserve before Wave 6 evidence exists."""

    NO_AGI_CLAIM = "no-agi-claim"
    NO_PRODUCTION_CLAIM = "no-production-claim"
    NO_CERTIFICATION_CLAIM = "no-certification-claim"
    NO_AUTONOMOUS_AUTHORITY = "no-autonomous-authority"
    NO_SELF_VALIDATION = "no-self-validation"
    INDEPENDENT_EVIDENCE_REQUIRED = "independent-evidence-required"


WAVE_FIVE_REQUIRED_CAPABILITY_AREAS: tuple[WaveFiveCapabilityArea, ...] = (
    WaveFiveCapabilityArea.EXTERNAL_PROTOCOLS,
    WaveFiveCapabilityArea.INDEPENDENT_REVIEW,
    WaveFiveCapabilityArea.REPRODUCIBILITY,
    WaveFiveCapabilityArea.ADVERSARIAL_SAFETY,
    WaveFiveCapabilityArea.LONG_HORIZON_VALIDATION,
    WaveFiveCapabilityArea.CROSS_DOMAIN_TRANSFER,
    WaveFiveCapabilityArea.BENCHMARK_GAMING_RESISTANCE,
    WaveFiveCapabilityArea.MEMORY_INTEGRITY,
    WaveFiveCapabilityArea.SAFE_REFUSAL,
    WaveFiveCapabilityArea.HUMAN_AUTHORITY_PRESERVATION,
    WaveFiveCapabilityArea.ECOSYSTEM_TRACEABILITY,
    WaveFiveCapabilityArea.WAVE_SIX_READINESS_BOUNDARY,
)

WAVE_FIVE_REQUIRED_ARTIFACT_KINDS: tuple[WaveFiveArtifactKind, ...] = (
    WaveFiveArtifactKind.EXTERNAL_PROTOCOL_MANIFEST,
    WaveFiveArtifactKind.REVIEWER_ATTESTATION,
    WaveFiveArtifactKind.REPRODUCIBLE_EVIDENCE_BUNDLE,
    WaveFiveArtifactKind.ADVERSARIAL_SAFETY_RECORD,
    WaveFiveArtifactKind.LONG_HORIZON_TASK_RECORD,
    WaveFiveArtifactKind.CROSS_DOMAIN_TRANSFER_RECORD,
    WaveFiveArtifactKind.BENCHMARK_CONTAMINATION_AUDIT,
    WaveFiveArtifactKind.MEMORY_INTEGRITY_PROOF,
    WaveFiveArtifactKind.SAFE_REFUSAL_PROOF,
    WaveFiveArtifactKind.HUMAN_AUTHORITY_PROOF,
    WaveFiveArtifactKind.REPEATABILITY_LEDGER,
    WaveFiveArtifactKind.ECOSYSTEM_TRACEABILITY_MAP,
    WaveFiveArtifactKind.WAVE_SIX_PRECONDITION_LEDGER,
    WaveFiveArtifactKind.INDEPENDENT_VALIDATION_DOSSIER,
    WaveFiveArtifactKind.FAIL_CLOSED_SCORECARD,
    WaveFiveArtifactKind.REVIEW_BOARD_DOCKET,
    WaveFiveArtifactKind.MATURITY_DECLARATION,
    WaveFiveArtifactKind.RELEASE_MANIFEST,
)

WAVE_FIVE_REQUIRED_CLAIM_BOUNDARIES: tuple[WaveFiveClaimBoundary, ...] = (
    WaveFiveClaimBoundary.NO_AGI_CLAIM,
    WaveFiveClaimBoundary.NO_PRODUCTION_CLAIM,
    WaveFiveClaimBoundary.NO_CERTIFICATION_CLAIM,
    WaveFiveClaimBoundary.NO_AUTONOMOUS_AUTHORITY,
    WaveFiveClaimBoundary.NO_SELF_VALIDATION,
    WaveFiveClaimBoundary.INDEPENDENT_EVIDENCE_REQUIRED,
)

WAVE_FIVE_EXTERNAL_EVIDENCE_SOURCE_SYSTEMS: tuple[WaveFiveSourceSystem, ...] = (
    WaveFiveSourceSystem.EXTERNAL_REVIEW,
    WaveFiveSourceSystem.EXTERNAL_VALIDATION_PROTOCOL,
    WaveFiveSourceSystem.INDEPENDENT_REVIEWER,
    WaveFiveSourceSystem.INDEPENDENT_REPLICATION_LAB,
    WaveFiveSourceSystem.ADVERSARIAL_TESTER,
)

WAVE_FIVE_EXTERNAL_VALIDATION_STATUSES: tuple[WaveFiveValidationStatus, ...] = (
    WaveFiveValidationStatus.EXTERNALLY_REPRODUCED,
    WaveFiveValidationStatus.ACCEPTED_WITH_BOUNDARIES,
)


@dataclass(frozen=True, slots=True)
class WaveFiveEvidenceLink:
    """A typed evidence reference bound to one Wave 5 artifact."""

    evidence_id: str
    artifact_id: str
    relation: WaveFiveEvidenceRelation
    summary: str
    source_system: WaveFiveSourceSystem

    def __post_init__(self) -> None:
        """Validate evidence-link identity and reviewability."""

        object.__setattr__(
            self,
            "evidence_id",
            _require_non_empty(self.evidence_id, "evidence_id"),
        )
        object.__setattr__(
            self,
            "artifact_id",
            _require_non_empty(self.artifact_id, "artifact_id"),
        )
        object.__setattr__(
            self,
            "summary",
            _require_non_empty(self.summary, "evidence link summary"),
        )

    @property
    def link_key(self) -> tuple[str, str, str]:
        """Return the unique key for this evidence-artifact relation."""

        return (self.evidence_id, self.artifact_id, self.relation.value)

    @property
    def is_external_validation_evidence(self) -> bool:
        """Return whether this link comes from an external validation source."""

        return self.source_system in WAVE_FIVE_EXTERNAL_EVIDENCE_SOURCE_SYSTEMS

    def canonical_payload(self) -> dict[str, str]:
        """Return a deterministic payload for evidence-link hashing."""

        return {
            "artifact_id": self.artifact_id,
            "evidence_id": self.evidence_id,
            "relation": self.relation.value,
            "source_system": self.source_system.value,
            "summary": self.summary,
        }


@dataclass(frozen=True, slots=True)
class WaveFiveArtifactRef:
    """A reviewable, non-executable Wave 5 validation artifact reference."""

    artifact_id: str
    kind: WaveFiveArtifactKind
    capability_area: WaveFiveCapabilityArea
    source_system: WaveFiveSourceSystem
    summary: str
    produced_by_engine_id: str
    evidence_ids: tuple[str, ...]
    produced_by_agent_role_id: str = ""
    decision: WaveFiveArtifactDecision = (
        WaveFiveArtifactDecision.NEEDS_EXTERNAL_EVIDENCE
    )
    authority_state: WaveFiveAuthorityState = (
        WaveFiveAuthorityState.HUMAN_REVIEW_REQUIRED
    )
    validation_status: WaveFiveValidationStatus = (
        WaveFiveValidationStatus.MISSING_EXTERNAL_EVIDENCE
    )
    claim_boundaries: tuple[WaveFiveClaimBoundary, ...] = (
        WAVE_FIVE_REQUIRED_CLAIM_BOUNDARIES
    )
    requires_human_authority: bool = True
    allowed_for_automatic_execution: bool = False
    claims_agi: bool = False
    claims_production_ready: bool = False
    claims_certified: bool = False
    self_validated: bool = False
    schema_version: str = WAVE_FIVE_ARTIFACT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate identity, evidence binding, and claim boundaries."""

        if not self.requires_human_authority:
            raise ValueError("Wave 5 artifacts must require human authority awareness.")
        if self.allowed_for_automatic_execution:
            raise ValueError("Wave 5 artifacts must never allow automatic execution.")
        if self.claims_agi:
            raise ValueError("Wave 5 artifacts must not claim AGI.")
        if self.claims_production_ready:
            raise ValueError("Wave 5 artifacts must not claim production readiness.")
        if self.claims_certified:
            raise ValueError("Wave 5 artifacts must not claim certification.")
        if self.self_validated:
            raise ValueError("Wave 5 artifacts must not claim self-validation.")
        object.__setattr__(
            self,
            "artifact_id",
            _require_non_empty(self.artifact_id, "artifact_id"),
        )
        object.__setattr__(
            self,
            "summary",
            _require_non_empty(self.summary, "artifact summary"),
        )
        object.__setattr__(
            self,
            "produced_by_engine_id",
            _require_non_empty(self.produced_by_engine_id, "produced_by_engine_id"),
        )
        object.__setattr__(
            self,
            "produced_by_agent_role_id",
            self.produced_by_agent_role_id.strip(),
        )
        object.__setattr__(
            self,
            "evidence_ids",
            _normalize_unique_text_tuple(
                self.evidence_ids, label="artifact evidence_id"
            ),
        )
        object.__setattr__(
            self,
            "claim_boundaries",
            _normalize_unique_enum_tuple(self.claim_boundaries, label="claim boundary"),
        )
        object.__setattr__(
            self,
            "schema_version",
            _require_non_empty(self.schema_version, "artifact schema_version"),
        )
        if (
            self.decision
            in {
                WaveFiveArtifactDecision.READY_FOR_INDEPENDENT_REVIEW,
                WaveFiveArtifactDecision.EXTERNALLY_REVIEWED,
            }
            and not self.evidence_ids
        ):
            raise ValueError("Reviewable Wave 5 artifacts require evidence ids.")
        if (
            self.decision is WaveFiveArtifactDecision.BLOCKED
            and self.authority_state is WaveFiveAuthorityState.HUMAN_AUTHORITY_GRANTED
        ):
            raise ValueError("Blocked Wave 5 artifacts cannot carry granted authority.")
        missing_boundaries = tuple(
            boundary
            for boundary in WAVE_FIVE_REQUIRED_CLAIM_BOUNDARIES
            if boundary not in self.claim_boundaries
        )
        if missing_boundaries:
            raise ValueError(
                "Wave 5 artifacts must preserve required claim boundary: "
                f"{missing_boundaries[0].value}"
            )

    @property
    def evidence_bound(self) -> bool:
        """Return whether the artifact has at least one evidence id."""

        return bool(self.evidence_ids)

    @property
    def ready_for_independent_review(self) -> bool:
        """Return whether this artifact may enter independent review."""

        return (
            self.decision is WaveFiveArtifactDecision.READY_FOR_INDEPENDENT_REVIEW
            and self.evidence_bound
            and self.authority_state
            in {
                WaveFiveAuthorityState.HUMAN_REVIEW_REQUIRED,
                WaveFiveAuthorityState.HUMAN_AUTHORITY_GRANTED,
            }
            and not self.claims_agi
            and not self.claims_production_ready
            and not self.claims_certified
            and not self.self_validated
            and not self.allowed_for_automatic_execution
        )

    @property
    def needs_external_evidence(self) -> bool:
        """Return whether this artifact is still missing external evidence."""

        return self.validation_status in {
            WaveFiveValidationStatus.NOT_SUBMITTED,
            WaveFiveValidationStatus.MISSING_EXTERNAL_EVIDENCE,
            WaveFiveValidationStatus.UNDER_INDEPENDENT_REVIEW,
        }

    @property
    def externally_validated_with_boundaries(self) -> bool:
        """Return whether the artifact has an external validation status."""

        return self.validation_status in WAVE_FIVE_EXTERNAL_VALIDATION_STATUSES

    @property
    def blocks_progress(self) -> bool:
        """Return whether this artifact blocks later Wave 5 readiness."""

        return (
            self.decision is WaveFiveArtifactDecision.BLOCKED
            or self.authority_state is WaveFiveAuthorityState.BLOCKED
            or self.validation_status
            in {WaveFiveValidationStatus.DISPUTED, WaveFiveValidationStatus.REJECTED}
        )

    def canonical_payload(self) -> dict[str, Any]:
        """Return a deterministic payload for artifact hashing."""

        return {
            "allowed_for_automatic_execution": self.allowed_for_automatic_execution,
            "artifact_id": self.artifact_id,
            "authority_state": self.authority_state.value,
            "capability_area": self.capability_area.value,
            "claim_boundaries": [boundary.value for boundary in self.claim_boundaries],
            "claims_agi": self.claims_agi,
            "claims_certified": self.claims_certified,
            "claims_production_ready": self.claims_production_ready,
            "decision": self.decision.value,
            "evidence_ids": list(self.evidence_ids),
            "kind": self.kind.value,
            "produced_by_agent_role_id": self.produced_by_agent_role_id,
            "produced_by_engine_id": self.produced_by_engine_id,
            "requires_human_authority": self.requires_human_authority,
            "schema_version": self.schema_version,
            "self_validated": self.self_validated,
            "source_system": self.source_system.value,
            "summary": self.summary,
            "validation_status": self.validation_status.value,
        }

    def fingerprint(self) -> str:
        """Return a deterministic SHA-256 fingerprint for this artifact."""

        return _stable_sha256(self.canonical_payload())


@dataclass(frozen=True, slots=True)
class WaveFiveArtifactBundle:
    """A deterministic bundle of Wave 5 artifacts and evidence links."""

    bundle_id: str
    artifacts: tuple[WaveFiveArtifactRef, ...]
    evidence_links: tuple[WaveFiveEvidenceLink, ...]
    required_kinds: tuple[WaveFiveArtifactKind, ...] = ()
    required_capability_areas: tuple[WaveFiveCapabilityArea, ...] = ()
    required_claim_boundaries: tuple[WaveFiveClaimBoundary, ...] = ()
    notes: tuple[str, ...] = ()
    schema_version: str = WAVE_FIVE_BUNDLE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate bundle uniqueness, references, and external evidence gates."""

        object.__setattr__(
            self,
            "bundle_id",
            _require_non_empty(self.bundle_id, "bundle_id"),
        )
        if not self.artifacts:
            raise ValueError("Wave 5 artifact bundles require at least one artifact.")
        sorted_artifacts = tuple(
            sorted(self.artifacts, key=lambda artifact: artifact.artifact_id)
        )
        sorted_links = tuple(
            sorted(self.evidence_links, key=lambda link: link.link_key)
        )
        artifact_ids = _unique_ids(
            (artifact.artifact_id for artifact in sorted_artifacts),
            label="artifact_id",
        )
        _unique_ids((link.link_key for link in sorted_links), label="evidence link")
        for link in sorted_links:
            if link.artifact_id not in artifact_ids:
                raise ValueError(
                    "Wave 5 evidence links must reference bundled artifacts: "
                    f"{link.artifact_id}"
                )
        linked_evidence_ids_by_artifact = _linked_evidence_ids_by_artifact(sorted_links)
        external_evidence_ids_by_artifact = _external_evidence_ids_by_artifact(
            sorted_links
        )
        for artifact in sorted_artifacts:
            linked_ids = linked_evidence_ids_by_artifact.get(
                artifact.artifact_id, set()
            )
            missing_links = tuple(
                evidence_id
                for evidence_id in artifact.evidence_ids
                if evidence_id not in linked_ids
            )
            if missing_links:
                raise ValueError(
                    "Wave 5 artifact evidence ids require matching evidence links: "
                    f"{artifact.artifact_id}:{missing_links[0]}"
                )
            external_ids = external_evidence_ids_by_artifact.get(
                artifact.artifact_id, set()
            )
            if artifact.externally_validated_with_boundaries and not external_ids:
                raise ValueError(
                    "Externally validated Wave 5 artifacts require external "
                    f"evidence links: {artifact.artifact_id}"
                )
            if (
                artifact.decision is WaveFiveArtifactDecision.EXTERNALLY_REVIEWED
                and not external_ids
            ):
                raise ValueError(
                    "Externally reviewed Wave 5 artifacts require external "
                    f"evidence links: {artifact.artifact_id}"
                )
        object.__setattr__(self, "artifacts", sorted_artifacts)
        object.__setattr__(self, "evidence_links", sorted_links)
        object.__setattr__(
            self,
            "required_kinds",
            _normalize_unique_enum_tuple(self.required_kinds, label="required kind"),
        )
        object.__setattr__(
            self,
            "required_capability_areas",
            _normalize_unique_enum_tuple(
                self.required_capability_areas, label="required capability area"
            ),
        )
        object.__setattr__(
            self,
            "required_claim_boundaries",
            _normalize_unique_enum_tuple(
                self.required_claim_boundaries, label="required claim boundary"
            ),
        )
        object.__setattr__(
            self,
            "notes",
            _normalize_unique_text_tuple(self.notes, label="bundle note"),
        )
        object.__setattr__(
            self,
            "schema_version",
            _require_non_empty(self.schema_version, "bundle schema_version"),
        )

    @property
    def artifact_ids(self) -> tuple[str, ...]:
        """Return artifact ids in deterministic bundle order."""

        return tuple(artifact.artifact_id for artifact in self.artifacts)

    @property
    def blocked_artifact_ids(self) -> tuple[str, ...]:
        """Return artifact ids that block progress."""

        return tuple(
            artifact.artifact_id
            for artifact in self.artifacts
            if artifact.blocks_progress
        )

    @property
    def ready_for_independent_review_artifact_ids(self) -> tuple[str, ...]:
        """Return artifact ids that may enter independent review."""

        return tuple(
            artifact.artifact_id
            for artifact in self.artifacts
            if artifact.ready_for_independent_review
        )

    @property
    def externally_validated_artifact_ids(self) -> tuple[str, ...]:
        """Return artifact ids with bounded external validation status."""

        return tuple(
            artifact.artifact_id
            for artifact in self.artifacts
            if artifact.externally_validated_with_boundaries
        )

    @property
    def missing_external_evidence_artifact_ids(self) -> tuple[str, ...]:
        """Return artifact ids still needing external validation evidence."""

        return tuple(
            artifact.artifact_id
            for artifact in self.artifacts
            if artifact.needs_external_evidence
        )

    @property
    def missing_required_kinds(self) -> tuple[WaveFiveArtifactKind, ...]:
        """Return required artifact kinds not represented in this bundle."""

        present = {artifact.kind for artifact in self.artifacts}
        return tuple(kind for kind in self.required_kinds if kind not in present)

    @property
    def missing_required_capability_areas(self) -> tuple[WaveFiveCapabilityArea, ...]:
        """Return required capability areas not represented in this bundle."""

        present = {artifact.capability_area for artifact in self.artifacts}
        return tuple(
            area for area in self.required_capability_areas if area not in present
        )

    @property
    def missing_required_claim_boundaries(self) -> tuple[WaveFiveClaimBoundary, ...]:
        """Return required claim boundaries not preserved by every artifact."""

        missing: list[WaveFiveClaimBoundary] = []
        for boundary in self.required_claim_boundaries:
            boundary_missing = any(
                boundary not in artifact.claim_boundaries for artifact in self.artifacts
            )
            if boundary_missing:
                missing.append(boundary)
        return tuple(missing)

    @property
    def has_required_kind_coverage(self) -> bool:
        """Return whether every requested artifact kind is represented."""

        return not self.missing_required_kinds

    @property
    def has_required_capability_coverage(self) -> bool:
        """Return whether every requested capability area is represented."""

        return not self.missing_required_capability_areas

    @property
    def has_required_claim_boundary_coverage(self) -> bool:
        """Return whether every artifact preserves requested claim boundaries."""

        return not self.missing_required_claim_boundaries

    @property
    def evidence_link_table(self) -> Mapping[str, tuple[str, ...]]:
        """Return artifact ids mapped to sorted linked evidence ids."""

        linked = _linked_evidence_ids_by_artifact(self.evidence_links)
        return {
            artifact_id: tuple(sorted(evidence_ids))
            for artifact_id, evidence_ids in sorted(linked.items())
        }

    @property
    def external_evidence_link_table(self) -> Mapping[str, tuple[str, ...]]:
        """Return artifact ids mapped to sorted external evidence ids."""

        linked = _external_evidence_ids_by_artifact(self.evidence_links)
        return {
            artifact_id: tuple(sorted(evidence_ids))
            for artifact_id, evidence_ids in sorted(linked.items())
        }

    def artifact_by_id(self, artifact_id: str) -> WaveFiveArtifactRef:
        """Return one artifact by id."""

        for artifact in self.artifacts:
            if artifact.artifact_id == artifact_id:
                return artifact
        raise ValueError(f"Unknown Wave 5 artifact_id: {artifact_id}")

    def artifact_ids_by_kind(self, kind: WaveFiveArtifactKind) -> tuple[str, ...]:
        """Return artifact ids matching a required Wave 5 kind."""

        return tuple(
            artifact.artifact_id for artifact in self.artifacts if artifact.kind is kind
        )

    def artifact_ids_by_capability_area(
        self, capability_area: WaveFiveCapabilityArea
    ) -> tuple[str, ...]:
        """Return artifact ids matching a required Wave 5 capability area."""

        return tuple(
            artifact.artifact_id
            for artifact in self.artifacts
            if artifact.capability_area is capability_area
        )

    def canonical_payload(self) -> dict[str, Any]:
        """Return a deterministic payload for bundle hashing."""

        return {
            "artifacts": [artifact.canonical_payload() for artifact in self.artifacts],
            "bundle_id": self.bundle_id,
            "evidence_links": [
                link.canonical_payload() for link in self.evidence_links
            ],
            "notes": list(self.notes),
            "required_capability_areas": [
                area.value for area in self.required_capability_areas
            ],
            "required_claim_boundaries": [
                boundary.value for boundary in self.required_claim_boundaries
            ],
            "required_kinds": [kind.value for kind in self.required_kinds],
            "schema_version": self.schema_version,
        }

    def fingerprint(self) -> str:
        """Return a deterministic SHA-256 fingerprint for this bundle."""

        return _stable_sha256(self.canonical_payload())


def required_wave_five_artifact_kinds() -> tuple[WaveFiveArtifactKind, ...]:
    """Return the locked required artifact kinds for Wave 5 readiness."""

    return WAVE_FIVE_REQUIRED_ARTIFACT_KINDS


def required_wave_five_capability_areas() -> tuple[WaveFiveCapabilityArea, ...]:
    """Return the locked required validation areas for Wave 5 readiness."""

    return WAVE_FIVE_REQUIRED_CAPABILITY_AREAS


def required_wave_five_claim_boundaries() -> tuple[WaveFiveClaimBoundary, ...]:
    """Return the locked claim boundaries that prevent Wave 5 overclaiming."""

    return WAVE_FIVE_REQUIRED_CLAIM_BOUNDARIES


def external_wave_five_source_systems() -> tuple[WaveFiveSourceSystem, ...]:
    """Return source systems that count as external validation evidence."""

    return WAVE_FIVE_EXTERNAL_EVIDENCE_SOURCE_SYSTEMS


def _require_non_empty(value: str, label: str) -> str:
    """Return stripped text or raise when empty."""

    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{label} must not be empty.")
    return normalized


def _normalize_unique_text_tuple(
    values: Iterable[str], *, label: str
) -> tuple[str, ...]:
    """Normalize text tuples while rejecting blanks and duplicates."""

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
    """Return a tuple of enum values while rejecting duplicates."""

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


def _linked_evidence_ids_by_artifact(
    evidence_links: Iterable[WaveFiveEvidenceLink],
) -> dict[str, set[str]]:
    """Group evidence ids by linked artifact id."""

    grouped: dict[str, set[str]] = {}
    for link in evidence_links:
        grouped.setdefault(link.artifact_id, set()).add(link.evidence_id)
    return grouped


def _external_evidence_ids_by_artifact(
    evidence_links: Iterable[WaveFiveEvidenceLink],
) -> dict[str, set[str]]:
    """Group external validation evidence ids by linked artifact id."""

    grouped: dict[str, set[str]] = {}
    for link in evidence_links:
        if link.is_external_validation_evidence:
            grouped.setdefault(link.artifact_id, set()).add(link.evidence_id)
    return grouped


def _stable_sha256(payload: Mapping[str, Any]) -> str:
    """Return deterministic SHA-256 over a canonical JSON payload."""

    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
