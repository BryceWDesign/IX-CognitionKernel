"""Wave 5 cross-domain transfer validation records.

Wave 5 must distinguish bounded cross-domain transfer from benchmark memory,
prompt-pattern copying, target-domain overfitting, or custom retraining per task.
This module records source capabilities, novel target domains, transfer
observations, negative controls, and external-review boundaries. The records are
strictly evidence artifacts: they do not claim AGI, production readiness,
certification, autonomous authority, or independent validation by self-review.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, TypeVar

from ix_cognition_kernel.wave5_contracts import (
    WAVE_FIVE_REQUIRED_CLAIM_BOUNDARIES,
    WaveFiveArtifactDecision,
    WaveFiveArtifactKind,
    WaveFiveArtifactRef,
    WaveFiveAuthorityState,
    WaveFiveCapabilityArea,
    WaveFiveClaimBoundary,
    WaveFiveSourceSystem,
    WaveFiveValidationStatus,
)

T = TypeVar("T")
E = TypeVar("E", bound=StrEnum)

WAVE_FIVE_TRANSFER_SOURCE_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave5-transfer-source-capability-v1"
)
WAVE_FIVE_TRANSFER_TARGET_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave5-transfer-target-domain-v1"
)
WAVE_FIVE_TRANSFER_OBSERVATION_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave5-transfer-observation-v1"
)
WAVE_FIVE_TRANSFER_NEGATIVE_CONTROL_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave5-transfer-negative-control-v1"
)
WAVE_FIVE_CROSS_DOMAIN_TRANSFER_RECORD_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave5-cross-domain-transfer-record-v1"
)


class WaveFiveTransferDomain(StrEnum):
    """Domains used to separate source capability from target transfer tests."""

    CAUSAL_REASONING = "causal-reasoning"
    EVIDENCE_AUDIT = "evidence-audit"
    MEMORY_GOVERNANCE = "memory-governance"
    SAFETY_REFUSAL = "safety-refusal"
    SOFTWARE_ENGINEERING = "software-engineering"
    SCENARIO_REASONING = "scenario-reasoning"
    HUMAN_AUTHORITY_GOVERNANCE = "human-authority-governance"
    ADVERSARIAL_ROBUSTNESS = "adversarial-robustness"


class WaveFiveTransferDimension(StrEnum):
    """Required dimensions for credible Wave 5 transfer evidence."""

    NOVEL_TARGET_DOMAIN = "novel-target-domain"
    INVARIANT_PRESERVATION = "invariant-preservation"
    NO_CUSTOM_RETRAINING = "no-custom-retraining"
    NEGATIVE_CONTROL_DETECTION = "negative-control-detection"
    UNCERTAINTY_PRESERVATION = "uncertainty-preservation"
    HUMAN_AUTHORITY_PRESERVATION = "human-authority-preservation"
    EVIDENCE_BINDING = "evidence-binding"
    FAILURE_RECOGNITION = "failure-recognition"


class WaveFiveTransferOutcome(StrEnum):
    """Observed outcome of a target-domain transfer attempt."""

    BOUNDED_TRANSFER_CONFIRMED = "bounded-transfer-confirmed"
    PARTIAL_TRANSFER_WITH_LIMITS = "partial-transfer-with-limits"
    TRANSFER_REJECTED_WITH_EVIDENCE = "transfer-rejected-with-evidence"
    ESCALATED_TO_HUMAN_REVIEW = "escalated-to-human-review"
    NEEDS_MORE_EVIDENCE = "needs-more-evidence"
    UNSUPPORTED_TRANSFER = "unsupported-transfer"
    AUTHORITY_BYPASS = "authority-bypass"


class WaveFiveTransferNegativeControlKind(StrEnum):
    """Invalid transfer behaviors that a Wave 5 record must catch."""

    BENCHMARK_MEMORIZATION = "benchmark-memorization"
    TARGET_DOMAIN_OVERFIT = "target-domain-overfit"
    UNSUPPORTED_ANALOGY = "unsupported-analogy"
    CUSTOM_RETRAINING_DEPENDENCY = "custom-retraining-dependency"
    HIDDEN_UNCERTAINTY = "hidden-uncertainty"
    AUTHORITY_ESCALATION = "authority-escalation"
    EVIDENCE_CHAIN_BREAK = "evidence-chain-break"


class WaveFiveTransferReviewState(StrEnum):
    """Review state of a Wave 5 cross-domain transfer record."""

    INTERNAL_REPLAY_READY = "internal-replay-ready"
    READY_FOR_EXTERNAL_TRANSFER_REVIEW = "ready-for-external-transfer-review"
    UNDER_EXTERNAL_TRANSFER_REVIEW = "under-external-transfer-review"
    EXTERNALLY_REVIEWED_WITH_BOUNDARIES = "externally-reviewed-with-boundaries"
    BLOCKED_BY_TRANSFER_FAILURE = "blocked-by-transfer-failure"


SAFE_WAVE_FIVE_TRANSFER_OUTCOMES: tuple[WaveFiveTransferOutcome, ...] = (
    WaveFiveTransferOutcome.BOUNDED_TRANSFER_CONFIRMED,
    WaveFiveTransferOutcome.PARTIAL_TRANSFER_WITH_LIMITS,
    WaveFiveTransferOutcome.TRANSFER_REJECTED_WITH_EVIDENCE,
    WaveFiveTransferOutcome.ESCALATED_TO_HUMAN_REVIEW,
)

REQUIRED_WAVE_FIVE_TRANSFER_DIMENSIONS: tuple[WaveFiveTransferDimension, ...] = (
    WaveFiveTransferDimension.NOVEL_TARGET_DOMAIN,
    WaveFiveTransferDimension.INVARIANT_PRESERVATION,
    WaveFiveTransferDimension.NO_CUSTOM_RETRAINING,
    WaveFiveTransferDimension.NEGATIVE_CONTROL_DETECTION,
    WaveFiveTransferDimension.UNCERTAINTY_PRESERVATION,
    WaveFiveTransferDimension.HUMAN_AUTHORITY_PRESERVATION,
    WaveFiveTransferDimension.EVIDENCE_BINDING,
    WaveFiveTransferDimension.FAILURE_RECOGNITION,
)

REQUIRED_WAVE_FIVE_NEGATIVE_CONTROLS: tuple[
    WaveFiveTransferNegativeControlKind, ...
] = (
    WaveFiveTransferNegativeControlKind.BENCHMARK_MEMORIZATION,
    WaveFiveTransferNegativeControlKind.TARGET_DOMAIN_OVERFIT,
    WaveFiveTransferNegativeControlKind.UNSUPPORTED_ANALOGY,
    WaveFiveTransferNegativeControlKind.CUSTOM_RETRAINING_DEPENDENCY,
    WaveFiveTransferNegativeControlKind.HIDDEN_UNCERTAINTY,
    WaveFiveTransferNegativeControlKind.AUTHORITY_ESCALATION,
    WaveFiveTransferNegativeControlKind.EVIDENCE_CHAIN_BREAK,
)

EXTERNAL_TRANSFER_REVIEW_SOURCE_SYSTEMS: tuple[WaveFiveSourceSystem, ...] = (
    WaveFiveSourceSystem.EXTERNAL_REVIEW,
    WaveFiveSourceSystem.INDEPENDENT_REVIEWER,
    WaveFiveSourceSystem.INDEPENDENT_REPLICATION_LAB,
)


@dataclass(frozen=True, slots=True)
class WaveFiveTransferSourceCapability:
    """Source-domain capability proposed for bounded transfer."""

    source_capability_id: str
    source_domain: WaveFiveTransferDomain
    capability_summary: str
    invariant_claims: tuple[str, ...]
    prohibited_assumptions: tuple[str, ...]
    protocol_ids: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    schema_version: str = WAVE_FIVE_TRANSFER_SOURCE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate source capability identity and invariant evidence."""

        object.__setattr__(
            self,
            "source_capability_id",
            _text(self.source_capability_id, "source_capability_id"),
        )
        object.__setattr__(
            self,
            "capability_summary",
            _text(self.capability_summary, "capability_summary"),
        )
        object.__setattr__(
            self,
            "invariant_claims",
            _unique_text(self.invariant_claims, label="invariant claim"),
        )
        object.__setattr__(
            self,
            "prohibited_assumptions",
            _unique_text(self.prohibited_assumptions, label="prohibited assumption"),
        )
        object.__setattr__(
            self, "protocol_ids", _unique_text(self.protocol_ids, label="protocol_id")
        )
        object.__setattr__(
            self, "evidence_ids", _unique_text(self.evidence_ids, label="evidence_id")
        )
        if not self.invariant_claims:
            raise ValueError("Transfer source capabilities require invariants.")
        if not self.prohibited_assumptions:
            raise ValueError(
                "Transfer source capabilities require prohibited assumptions."
            )
        if not self.protocol_ids:
            raise ValueError("Transfer source capabilities require protocol ids.")
        if not self.evidence_ids:
            raise ValueError("Transfer source capabilities require evidence ids.")
        object.__setattr__(
            self, "schema_version", _text(self.schema_version, "schema_version")
        )

    @property
    def source_key(self) -> str:
        """Return deterministic source capability key."""

        return self.source_capability_id

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic export payload."""

        return {
            "capability_summary": self.capability_summary,
            "evidence_ids": list(self.evidence_ids),
            "invariant_claims": list(self.invariant_claims),
            "prohibited_assumptions": list(self.prohibited_assumptions),
            "protocol_ids": list(self.protocol_ids),
            "schema_version": self.schema_version,
            "source_capability_id": self.source_capability_id,
            "source_domain": self.source_domain.value,
        }


@dataclass(frozen=True, slots=True)
class WaveFiveTransferTargetDomain:
    """Novel target domain used to test bounded transfer."""

    target_id: str
    source_capability_id: str
    target_domain: WaveFiveTransferDomain
    novelty_summary: str
    adaptation_constraints: tuple[str, ...]
    prohibited_shortcuts: tuple[str, ...]
    scenario_ids: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    used_custom_retraining: bool = False
    schema_version: str = WAVE_FIVE_TRANSFER_TARGET_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate target-domain novelty and shortcut controls."""

        object.__setattr__(self, "target_id", _text(self.target_id, "target_id"))
        object.__setattr__(
            self,
            "source_capability_id",
            _text(self.source_capability_id, "source_capability_id"),
        )
        object.__setattr__(
            self, "novelty_summary", _text(self.novelty_summary, "novelty_summary")
        )
        object.__setattr__(
            self,
            "adaptation_constraints",
            _unique_text(self.adaptation_constraints, label="adaptation constraint"),
        )
        object.__setattr__(
            self,
            "prohibited_shortcuts",
            _unique_text(self.prohibited_shortcuts, label="prohibited shortcut"),
        )
        object.__setattr__(
            self, "scenario_ids", _unique_text(self.scenario_ids, label="scenario_id")
        )
        object.__setattr__(
            self, "evidence_ids", _unique_text(self.evidence_ids, label="evidence_id")
        )
        if self.used_custom_retraining:
            raise ValueError("Wave 5 transfer targets cannot use custom retraining.")
        if not self.adaptation_constraints:
            raise ValueError("Transfer targets require adaptation constraints.")
        if not self.prohibited_shortcuts:
            raise ValueError("Transfer targets require prohibited shortcuts.")
        if not self.scenario_ids:
            raise ValueError("Transfer targets require scenario ids.")
        if not self.evidence_ids:
            raise ValueError("Transfer targets require evidence ids.")
        object.__setattr__(
            self, "schema_version", _text(self.schema_version, "schema_version")
        )

    @property
    def target_key(self) -> str:
        """Return deterministic target key."""

        return self.target_id

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic export payload."""

        return {
            "adaptation_constraints": list(self.adaptation_constraints),
            "evidence_ids": list(self.evidence_ids),
            "novelty_summary": self.novelty_summary,
            "prohibited_shortcuts": list(self.prohibited_shortcuts),
            "scenario_ids": list(self.scenario_ids),
            "schema_version": self.schema_version,
            "source_capability_id": self.source_capability_id,
            "target_domain": self.target_domain.value,
            "target_id": self.target_id,
            "used_custom_retraining": self.used_custom_retraining,
        }


@dataclass(frozen=True, slots=True)
class WaveFiveTransferObservation:
    """Observed behavior in one target-domain transfer test."""

    observation_id: str
    target_id: str
    outcome: WaveFiveTransferOutcome
    observed_behavior: str
    matched_invariants: tuple[str, ...]
    violated_invariants: tuple[str, ...]
    covered_dimensions: tuple[WaveFiveTransferDimension, ...]
    preserved_uncertainty: bool
    preserved_human_authority: bool
    evidence_bound: bool
    evidence_ids: tuple[str, ...]
    schema_version: str = WAVE_FIVE_TRANSFER_OBSERVATION_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate transfer observation and anti-overclaim controls."""

        object.__setattr__(
            self, "observation_id", _text(self.observation_id, "observation_id")
        )
        object.__setattr__(self, "target_id", _text(self.target_id, "target_id"))
        object.__setattr__(
            self,
            "observed_behavior",
            _text(self.observed_behavior, "observed_behavior"),
        )
        object.__setattr__(
            self,
            "matched_invariants",
            _unique_text(self.matched_invariants, label="matched invariant"),
        )
        object.__setattr__(
            self,
            "violated_invariants",
            _unique_text(self.violated_invariants, label="violated invariant"),
        )
        object.__setattr__(
            self,
            "covered_dimensions",
            _unique_enum(self.covered_dimensions, label="transfer dimension"),
        )
        object.__setattr__(
            self, "evidence_ids", _unique_text(self.evidence_ids, label="evidence_id")
        )
        if not self.covered_dimensions:
            raise ValueError("Transfer observations require covered dimensions.")
        if not self.evidence_ids:
            raise ValueError("Transfer observations require evidence ids.")
        if self.is_safe_outcome:
            if not self.evidence_bound:
                raise ValueError("Safe transfer outcomes must be evidence bound.")
            if not self.preserved_uncertainty:
                raise ValueError("Safe transfer outcomes must preserve uncertainty.")
            if not self.preserved_human_authority:
                raise ValueError("Safe transfer outcomes must preserve authority.")
        if self.outcome is WaveFiveTransferOutcome.BOUNDED_TRANSFER_CONFIRMED:
            if not self.matched_invariants:
                raise ValueError("Confirmed transfer requires matched invariants.")
            if self.violated_invariants:
                raise ValueError("Confirmed transfer cannot violate invariants.")
        object.__setattr__(
            self, "schema_version", _text(self.schema_version, "schema_version")
        )

    @property
    def observation_key(self) -> str:
        """Return deterministic observation key."""

        return self.observation_id

    @property
    def is_safe_outcome(self) -> bool:
        """Return whether the observed outcome is bounded and safe."""

        return self.outcome in SAFE_WAVE_FIVE_TRANSFER_OUTCOMES

    @property
    def blocks_wave_five_progress(self) -> bool:
        """Return whether this observation blocks transfer readiness."""

        return self.outcome in {
            WaveFiveTransferOutcome.NEEDS_MORE_EVIDENCE,
            WaveFiveTransferOutcome.UNSUPPORTED_TRANSFER,
            WaveFiveTransferOutcome.AUTHORITY_BYPASS,
        }

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic export payload."""

        return {
            "covered_dimensions": [
                dimension.value for dimension in self.covered_dimensions
            ],
            "evidence_bound": self.evidence_bound,
            "evidence_ids": list(self.evidence_ids),
            "matched_invariants": list(self.matched_invariants),
            "observation_id": self.observation_id,
            "observed_behavior": self.observed_behavior,
            "outcome": self.outcome.value,
            "preserved_human_authority": self.preserved_human_authority,
            "preserved_uncertainty": self.preserved_uncertainty,
            "schema_version": self.schema_version,
            "target_id": self.target_id,
            "violated_invariants": list(self.violated_invariants),
        }


@dataclass(frozen=True, slots=True)
class WaveFiveTransferNegativeControl:
    """Negative-control case for invalid cross-domain transfer behavior."""

    control_id: str
    target_id: str
    control_kind: WaveFiveTransferNegativeControlKind
    invalid_shortcut: str
    expected_detection: str
    detected: bool
    blocking: bool
    evidence_ids: tuple[str, ...]
    mitigation: str = ""
    schema_version: str = WAVE_FIVE_TRANSFER_NEGATIVE_CONTROL_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate negative-control detection and mitigation."""

        object.__setattr__(self, "control_id", _text(self.control_id, "control_id"))
        object.__setattr__(self, "target_id", _text(self.target_id, "target_id"))
        object.__setattr__(
            self, "invalid_shortcut", _text(self.invalid_shortcut, "invalid_shortcut")
        )
        object.__setattr__(
            self,
            "expected_detection",
            _text(self.expected_detection, "expected_detection"),
        )
        object.__setattr__(
            self, "evidence_ids", _unique_text(self.evidence_ids, label="evidence_id")
        )
        object.__setattr__(self, "mitigation", self.mitigation.strip())
        if not self.evidence_ids:
            raise ValueError("Transfer negative controls require evidence ids.")
        if self.detected and not self.mitigation:
            raise ValueError("Detected transfer negative controls require mitigation.")
        object.__setattr__(
            self, "schema_version", _text(self.schema_version, "schema_version")
        )

    @property
    def control_key(self) -> str:
        """Return deterministic negative-control key."""

        return self.control_id

    @property
    def resolved(self) -> bool:
        """Return whether the invalid shortcut was detected with mitigation."""

        return self.detected and bool(self.mitigation)

    @property
    def blocks_wave_five_progress(self) -> bool:
        """Return whether this negative control blocks transfer readiness."""

        return self.blocking and not self.resolved

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic export payload."""

        return {
            "blocking": self.blocking,
            "control_id": self.control_id,
            "control_kind": self.control_kind.value,
            "detected": self.detected,
            "evidence_ids": list(self.evidence_ids),
            "expected_detection": self.expected_detection,
            "invalid_shortcut": self.invalid_shortcut,
            "mitigation": self.mitigation,
            "resolved": self.resolved,
            "schema_version": self.schema_version,
            "target_id": self.target_id,
        }


@dataclass(frozen=True, slots=True)
class WaveFiveCrossDomainTransferRecord:
    """Wave 5 cross-domain transfer record for independent review."""

    record_id: str
    title: str
    source_system: WaveFiveSourceSystem
    review_state: WaveFiveTransferReviewState
    sources: tuple[WaveFiveTransferSourceCapability, ...]
    targets: tuple[WaveFiveTransferTargetDomain, ...]
    observations: tuple[WaveFiveTransferObservation, ...]
    negative_controls: tuple[WaveFiveTransferNegativeControl, ...]
    protocol_ids: tuple[str, ...]
    reviewer_ids: tuple[str, ...] = ()
    minimum_distinct_target_domains: int = 3
    claim_boundaries: tuple[WaveFiveClaimBoundary, ...] = (
        WAVE_FIVE_REQUIRED_CLAIM_BOUNDARIES
    )
    notes: tuple[str, ...] = ()
    schema_version: str = WAVE_FIVE_CROSS_DOMAIN_TRANSFER_RECORD_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate transfer coverage, references, and review boundaries."""

        object.__setattr__(self, "record_id", _text(self.record_id, "record_id"))
        object.__setattr__(self, "title", _text(self.title, "title"))
        if self.minimum_distinct_target_domains < 1:
            raise ValueError("Transfer records require at least one target domain.")
        sources = tuple(sorted(self.sources, key=lambda item: item.source_key))
        targets = tuple(sorted(self.targets, key=lambda item: item.target_key))
        observations = tuple(
            sorted(self.observations, key=lambda item: item.observation_key)
        )
        controls = tuple(
            sorted(self.negative_controls, key=lambda item: item.control_key)
        )
        if not sources:
            raise ValueError("Cross-domain transfer records require sources.")
        if not targets:
            raise ValueError("Cross-domain transfer records require targets.")
        if not observations:
            raise ValueError("Cross-domain transfer records require observations.")
        if not controls:
            raise ValueError("Cross-domain transfer records require negative controls.")
        source_ids = _unique_values(
            (item.source_capability_id for item in sources),
            label="source_capability_id",
        )
        target_ids = _unique_values(
            (item.target_id for item in targets), label="target_id"
        )
        _unique_values(
            (item.observation_id for item in observations),
            label="observation_id",
        )
        _unique_values((item.control_id for item in controls), label="control_id")
        self._validate_target_sources(source_ids, targets)
        self._validate_target_references(target_ids, observations, controls)
        object.__setattr__(self, "sources", sources)
        object.__setattr__(self, "targets", targets)
        object.__setattr__(self, "observations", observations)
        object.__setattr__(self, "negative_controls", controls)
        object.__setattr__(
            self, "protocol_ids", _unique_text(self.protocol_ids, label="protocol_id")
        )
        if not self.protocol_ids:
            raise ValueError("Cross-domain transfer records require protocol ids.")
        object.__setattr__(
            self, "reviewer_ids", _unique_text(self.reviewer_ids, label="reviewer_id")
        )
        object.__setattr__(
            self,
            "claim_boundaries",
            _unique_enum(self.claim_boundaries, label="claim boundary"),
        )
        missing_boundaries = tuple(
            boundary
            for boundary in WAVE_FIVE_REQUIRED_CLAIM_BOUNDARIES
            if boundary not in self.claim_boundaries
        )
        if missing_boundaries:
            raise ValueError(
                "Cross-domain transfer records must preserve claim boundary: "
                f"{missing_boundaries[0].value}"
            )
        object.__setattr__(
            self, "notes", _unique_text(self.notes, label="transfer record note")
        )
        object.__setattr__(
            self, "schema_version", _text(self.schema_version, "schema_version")
        )
        if self.externally_reviewed_with_boundaries:
            if self.source_system not in EXTERNAL_TRANSFER_REVIEW_SOURCE_SYSTEMS:
                raise ValueError(
                    "Externally reviewed transfer records require external source."
                )
            if not self.reviewer_ids:
                raise ValueError(
                    "Externally reviewed transfer records require reviewer ids."
                )
            if self.blocking_observation_ids or self.blocking_negative_control_ids:
                raise ValueError(
                    "Externally reviewed transfer records cannot contain blockers."
                )

    @property
    def distinct_source_domains(self) -> tuple[WaveFiveTransferDomain, ...]:
        """Return distinct source domains in source order."""

        domains: list[WaveFiveTransferDomain] = []
        seen: set[WaveFiveTransferDomain] = set()
        for source in self.sources:
            if source.source_domain not in seen:
                domains.append(source.source_domain)
                seen.add(source.source_domain)
        return tuple(domains)

    @property
    def distinct_target_domains(self) -> tuple[WaveFiveTransferDomain, ...]:
        """Return distinct target domains in target order."""

        domains: list[WaveFiveTransferDomain] = []
        seen: set[WaveFiveTransferDomain] = set()
        for target in self.targets:
            if target.target_domain not in seen:
                domains.append(target.target_domain)
                seen.add(target.target_domain)
        return tuple(domains)

    @property
    def target_ids(self) -> tuple[str, ...]:
        """Return target ids in deterministic order."""

        return tuple(target.target_id for target in self.targets)

    @property
    def covered_dimensions(self) -> tuple[WaveFiveTransferDimension, ...]:
        """Return transfer dimensions covered by observations."""

        dimensions: list[WaveFiveTransferDimension] = []
        seen: set[WaveFiveTransferDimension] = set()
        for observation in self.observations:
            for dimension in observation.covered_dimensions:
                if dimension not in seen:
                    dimensions.append(dimension)
                    seen.add(dimension)
        return tuple(dimensions)

    @property
    def missing_required_dimensions(self) -> tuple[WaveFiveTransferDimension, ...]:
        """Return required transfer dimensions not covered by observations."""

        covered = set(self.covered_dimensions)
        return tuple(
            dimension
            for dimension in REQUIRED_WAVE_FIVE_TRANSFER_DIMENSIONS
            if dimension not in covered
        )

    @property
    def covered_negative_control_kinds(
        self,
    ) -> tuple[WaveFiveTransferNegativeControlKind, ...]:
        """Return negative-control kinds represented in the record."""

        kinds: list[WaveFiveTransferNegativeControlKind] = []
        seen: set[WaveFiveTransferNegativeControlKind] = set()
        for control in self.negative_controls:
            if control.control_kind not in seen:
                kinds.append(control.control_kind)
                seen.add(control.control_kind)
        return tuple(kinds)

    @property
    def missing_required_negative_controls(
        self,
    ) -> tuple[WaveFiveTransferNegativeControlKind, ...]:
        """Return locked negative controls absent from the record."""

        covered = set(self.covered_negative_control_kinds)
        return tuple(
            kind for kind in REQUIRED_WAVE_FIVE_NEGATIVE_CONTROLS if kind not in covered
        )

    @property
    def blocking_observation_ids(self) -> tuple[str, ...]:
        """Return observations that block transfer readiness."""

        return tuple(
            observation.observation_id
            for observation in self.observations
            if observation.blocks_wave_five_progress
        )

    @property
    def blocking_negative_control_ids(self) -> tuple[str, ...]:
        """Return negative controls that block transfer readiness."""

        return tuple(
            control.control_id
            for control in self.negative_controls
            if control.blocks_wave_five_progress
        )

    @property
    def preserves_uncertainty(self) -> bool:
        """Return whether every observation preserves uncertainty."""

        return all(
            observation.preserved_uncertainty for observation in self.observations
        )

    @property
    def preserves_human_authority(self) -> bool:
        """Return whether every observation preserves human authority."""

        return all(
            observation.preserved_human_authority for observation in self.observations
        )

    @property
    def evidence_bound(self) -> bool:
        """Return whether every observation remains evidence-bound."""

        return all(observation.evidence_bound for observation in self.observations)

    @property
    def has_required_target_domain_coverage(self) -> bool:
        """Return whether enough distinct novel target domains are represented."""

        return len(self.distinct_target_domains) >= self.minimum_distinct_target_domains

    @property
    def has_required_dimension_coverage(self) -> bool:
        """Return whether all locked transfer dimensions are covered."""

        return not self.missing_required_dimensions

    @property
    def has_required_negative_control_coverage(self) -> bool:
        """Return whether every locked negative-control kind is represented."""

        return not self.missing_required_negative_controls

    @property
    def ready_for_external_transfer_review(self) -> bool:
        """Return whether the record can enter external transfer review."""

        return (
            self.review_state
            in {
                WaveFiveTransferReviewState.INTERNAL_REPLAY_READY,
                WaveFiveTransferReviewState.READY_FOR_EXTERNAL_TRANSFER_REVIEW,
                WaveFiveTransferReviewState.UNDER_EXTERNAL_TRANSFER_REVIEW,
            }
            and self.has_required_target_domain_coverage
            and self.has_required_dimension_coverage
            and self.has_required_negative_control_coverage
            and not self.blocking_observation_ids
            and not self.blocking_negative_control_ids
            and self.preserves_uncertainty
            and self.preserves_human_authority
            and self.evidence_bound
        )

    @property
    def externally_reviewed_with_boundaries(self) -> bool:
        """Return whether external transfer review accepted boundaries."""

        return (
            self.review_state
            is WaveFiveTransferReviewState.EXTERNALLY_REVIEWED_WITH_BOUNDARIES
        )

    @property
    def all_evidence_ids(self) -> tuple[str, ...]:
        """Return all evidence ids bound into the transfer record."""

        evidence_ids: list[str] = []
        seen: set[str] = set()
        for evidence_id in self._iter_evidence_ids():
            if evidence_id not in seen:
                evidence_ids.append(evidence_id)
                seen.add(evidence_id)
        return tuple(evidence_ids)

    def to_artifact_ref(self) -> WaveFiveArtifactRef:
        """Return this record as a Wave 5 cross-domain transfer artifact."""

        decision = WaveFiveArtifactDecision.NEEDS_EXTERNAL_EVIDENCE
        status = WaveFiveValidationStatus.MISSING_EXTERNAL_EVIDENCE
        authority = WaveFiveAuthorityState.HUMAN_REVIEW_REQUIRED
        if self.externally_reviewed_with_boundaries:
            decision = WaveFiveArtifactDecision.EXTERNALLY_REVIEWED
            status = WaveFiveValidationStatus.ACCEPTED_WITH_BOUNDARIES
        elif self.ready_for_external_transfer_review:
            decision = WaveFiveArtifactDecision.READY_FOR_INDEPENDENT_REVIEW
            status = WaveFiveValidationStatus.UNDER_INDEPENDENT_REVIEW
        elif self.blocking_observation_ids or self.blocking_negative_control_ids:
            decision = WaveFiveArtifactDecision.BLOCKED
            status = WaveFiveValidationStatus.REJECTED
            authority = WaveFiveAuthorityState.BLOCKED
        return WaveFiveArtifactRef(
            artifact_id=self.record_id,
            kind=WaveFiveArtifactKind.CROSS_DOMAIN_TRANSFER_RECORD,
            capability_area=WaveFiveCapabilityArea.CROSS_DOMAIN_TRANSFER,
            source_system=self.source_system,
            summary=self.title,
            produced_by_engine_id="wave5-cross-domain-transfer-engine",
            produced_by_agent_role_id="cross-domain-transfer-reviewer",
            evidence_ids=self.all_evidence_ids,
            decision=decision,
            authority_state=authority,
            validation_status=status,
            claim_boundaries=self.claim_boundaries,
        )

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic export payload."""

        return {
            "claim_boundaries": [boundary.value for boundary in self.claim_boundaries],
            "minimum_distinct_target_domains": self.minimum_distinct_target_domains,
            "negative_controls": [
                control.canonical_payload() for control in self.negative_controls
            ],
            "notes": list(self.notes),
            "observations": [
                observation.canonical_payload() for observation in self.observations
            ],
            "protocol_ids": list(self.protocol_ids),
            "record_id": self.record_id,
            "review_state": self.review_state.value,
            "reviewer_ids": list(self.reviewer_ids),
            "schema_version": self.schema_version,
            "source_system": self.source_system.value,
            "sources": [source.canonical_payload() for source in self.sources],
            "targets": [target.canonical_payload() for target in self.targets],
            "title": self.title,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this record."""

        return _stable_sha256(self.canonical_payload())

    def _iter_evidence_ids(self) -> Iterable[str]:
        """Yield evidence ids in deterministic transfer-record order."""

        for source in self.sources:
            yield from source.evidence_ids
        for target in self.targets:
            yield from target.evidence_ids
        for observation in self.observations:
            yield from observation.evidence_ids
        for control in self.negative_controls:
            yield from control.evidence_ids

    @staticmethod
    def _validate_target_sources(
        source_ids: set[str], targets: tuple[WaveFiveTransferTargetDomain, ...]
    ) -> None:
        """Validate that target domains reference bundled source capabilities."""

        for target in targets:
            if target.source_capability_id not in source_ids:
                raise ValueError(
                    "Transfer targets must reference bundled source capabilities: "
                    f"{target.source_capability_id}"
                )

    @staticmethod
    def _validate_target_references(
        target_ids: set[str],
        observations: tuple[WaveFiveTransferObservation, ...],
        controls: tuple[WaveFiveTransferNegativeControl, ...],
    ) -> None:
        """Validate observations and controls reference bundled targets."""

        for observation in observations:
            if observation.target_id not in target_ids:
                raise ValueError(
                    "Transfer observations must reference bundled targets: "
                    f"{observation.target_id}"
                )
        observed_target_ids = {observation.target_id for observation in observations}
        for target_id in target_ids:
            if target_id not in observed_target_ids:
                raise ValueError(f"Transfer targets require observations: {target_id}")
        for control in controls:
            if control.target_id not in target_ids:
                raise ValueError(
                    "Transfer negative controls must reference bundled targets: "
                    f"{control.target_id}"
                )


def required_wave_five_transfer_dimensions() -> tuple[WaveFiveTransferDimension, ...]:
    """Return locked dimensions required for Wave 5 transfer review."""

    return REQUIRED_WAVE_FIVE_TRANSFER_DIMENSIONS


def required_wave_five_transfer_negative_controls() -> tuple[
    WaveFiveTransferNegativeControlKind, ...
]:
    """Return locked negative controls required for Wave 5 transfer review."""

    return REQUIRED_WAVE_FIVE_NEGATIVE_CONTROLS


def safe_wave_five_transfer_outcomes() -> tuple[WaveFiveTransferOutcome, ...]:
    """Return transfer outcomes that preserve Wave 5 safety boundaries."""

    return SAFE_WAVE_FIVE_TRANSFER_OUTCOMES


def external_transfer_review_source_systems() -> tuple[WaveFiveSourceSystem, ...]:
    """Return source systems allowed to assert external transfer review."""

    return EXTERNAL_TRANSFER_REVIEW_SOURCE_SYSTEMS


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
        item = _text(value, label)
        if item in seen:
            raise ValueError(f"Duplicate {label} detected: {item}")
        normalized.append(item)
        seen.add(item)
    return tuple(normalized)


def _unique_enum(values: Iterable[E], *, label: str) -> tuple[E, ...]:
    """Return enum values while rejecting duplicates."""

    normalized: list[E] = []
    seen: set[E] = set()
    for value in values:
        if value in seen:
            raise ValueError(f"Duplicate {label} detected: {value.value}")
        normalized.append(value)
        seen.add(value)
    return tuple(normalized)


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
