"""Wave 4 cross-domain transfer bundles and negative-control cases.

Commit 3 added one controlled transfer evaluation. Wave 4 needs stronger proof:
multiple transfer evaluations, explicit target-domain coverage, negative controls,
BlackFox-style review receipts, WorldTwin scenario links, and fail-closed bundle
status. This module aggregates transfer evaluations without converting them into
execution authority, AGI claims, or independent-validation claims.
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
from ix_cognition_kernel.wave4_transfer import (
    WaveFourCrossDomainTransferEvaluation,
    WaveFourTransferStatus,
)
from ix_cognition_kernel.wave4_trials import (
    WaveFourTrialProtocol,
    WaveFourTrialTaskKind,
)

T = TypeVar("T")

WAVE_FOUR_TRANSFER_FAILURE_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave4-transfer-failure-case-v1"
)
WAVE_FOUR_TRANSFER_BUNDLE_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave4-transfer-bundle-v1"
)


class WaveFourTransferFailureMode(StrEnum):
    """Negative-control failure modes a transfer evaluator must catch."""

    HIDDEN_AUTHORITY_ESCALATION = "hidden-authority-escalation"
    MISSING_EVIDENCE_BINDING = "missing-evidence-binding"
    UNSUPPORTED_ANALOGY = "unsupported-analogy"
    INVARIANT_VIOLATION = "invariant-violation"
    AUTOMATIC_EXECUTION_PRESSURE = "automatic-execution-pressure"
    UNCERTAINTY_ERASURE = "uncertainty-erasure"


@dataclass(frozen=True, slots=True)
class WaveFourTransferFailureCase:
    """A negative-control case for cross-domain transfer evaluation.

    A detected failure case is evidence of evaluator discipline, not a pass for
    the failed behavior. The case is acceptable only when the unsafe or invalid
    transfer was detected and a repair recommendation was produced.
    """

    failure_case_id: str
    evaluation_id: str
    target_id: str
    failure_mode: WaveFourTransferFailureMode
    violated_invariant: str
    expected_detection_summary: str
    evidence_ids: tuple[str, ...]
    detected: bool
    repair_recommendation: str
    source_system: WaveFourSourceSystem = WaveFourSourceSystem.LOCAL_TEST_SUITE
    schema_version: str = WAVE_FOUR_TRANSFER_FAILURE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate failure-case identity and detection evidence."""

        object.__setattr__(
            self,
            "failure_case_id",
            _text(self.failure_case_id, "failure_case_id"),
        )
        object.__setattr__(self, "evaluation_id", _text(self.evaluation_id, "id"))
        object.__setattr__(self, "target_id", _text(self.target_id, "target_id"))
        object.__setattr__(
            self,
            "violated_invariant",
            _text(self.violated_invariant, "violated_invariant"),
        )
        object.__setattr__(
            self,
            "expected_detection_summary",
            _text(self.expected_detection_summary, "expected_detection_summary"),
        )
        object.__setattr__(
            self,
            "evidence_ids",
            _unique_text(self.evidence_ids, label="failure-case evidence_id"),
        )
        if not self.evidence_ids:
            raise ValueError("Wave 4 transfer failure cases require evidence ids.")
        object.__setattr__(
            self,
            "repair_recommendation",
            self.repair_recommendation.strip(),
        )
        object.__setattr__(
            self, "schema_version", _text(self.schema_version, "schema_version")
        )
        if self.detected and not self.repair_recommendation:
            raise ValueError(
                "Detected Wave 4 transfer failure cases require repair guidance."
            )

    @property
    def failure_key(self) -> str:
        """Return deterministic uniqueness key for this failure case."""

        return self.failure_case_id

    @property
    def resolved(self) -> bool:
        """Return whether the failure was caught and repair guidance exists."""

        return self.detected and bool(self.repair_recommendation)

    @property
    def readiness_gap(self) -> str:
        """Return the fail-closed gap represented by this case, if any."""

        if self.resolved:
            return ""
        if not self.detected:
            return f"{self.failure_case_id} was not detected by transfer review"
        return f"{self.failure_case_id} lacks repair guidance"

    def canonical_payload(self) -> dict[str, Any]:
        """Return a deterministic payload for hashing and export."""

        return {
            "detected": self.detected,
            "evaluation_id": self.evaluation_id,
            "evidence_ids": list(self.evidence_ids),
            "expected_detection_summary": self.expected_detection_summary,
            "failure_case_id": self.failure_case_id,
            "failure_mode": self.failure_mode.value,
            "readiness_gap": self.readiness_gap,
            "repair_recommendation": self.repair_recommendation,
            "resolved": self.resolved,
            "schema_version": self.schema_version,
            "source_system": self.source_system.value,
            "target_id": self.target_id,
            "violated_invariant": self.violated_invariant,
        }

    def fingerprint(self) -> str:
        """Return a deterministic SHA-256 fingerprint for this failure case."""

        return _stable_sha256(self.canonical_payload())


@dataclass(frozen=True, slots=True)
class WaveFourCrossDomainTransferBundle:
    """A deterministic bundle of transfer evaluations and negative controls."""

    bundle_id: str
    evaluations: tuple[WaveFourCrossDomainTransferEvaluation, ...]
    failure_cases: tuple[WaveFourTransferFailureCase, ...]
    required_source_domains: tuple[str, ...]
    required_target_domains: tuple[str, ...]
    min_ready_evaluations: int = 1
    reviewer_role_id: str = "cross-domain-transfer-bundle-reviewer"
    generated_by_engine_id: str = "wave4-cross-domain-transfer-bundle-engine"
    notes: tuple[str, ...] = ()
    permits_automatic_execution: bool = False
    claims_agi: bool = False
    independently_validated: bool = False
    schema_version: str = WAVE_FOUR_TRANSFER_BUNDLE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate bundle identity, coverage settings, and failure references."""

        object.__setattr__(self, "bundle_id", _text(self.bundle_id, "bundle_id"))
        if not self.evaluations:
            raise ValueError("Wave 4 transfer bundles require evaluations.")
        sorted_evaluations = tuple(
            sorted(self.evaluations, key=lambda item: item.evaluation_id)
        )
        evaluation_ids = _unique_items(
            (item.evaluation_id for item in sorted_evaluations),
            label="evaluation_id",
        )
        object.__setattr__(self, "evaluations", sorted_evaluations)
        sorted_failure_cases = tuple(
            sorted(self.failure_cases, key=lambda item: item.failure_key)
        )
        _unique_items(
            (item.failure_case_id for item in sorted_failure_cases),
            label="failure_case_id",
        )
        evaluation_targets = {
            item.evaluation_id: set(item.target_ids) for item in sorted_evaluations
        }
        for failure_case in sorted_failure_cases:
            if failure_case.evaluation_id not in evaluation_ids:
                raise ValueError(
                    "Wave 4 transfer failure cases must reference bundled "
                    f"evaluations: {failure_case.evaluation_id}"
                )
            known_targets = evaluation_targets[failure_case.evaluation_id]
            if failure_case.target_id not in known_targets:
                raise ValueError(
                    "Wave 4 transfer failure cases must reference target ids from "
                    f"their evaluation: {failure_case.target_id}"
                )
        object.__setattr__(self, "failure_cases", sorted_failure_cases)
        object.__setattr__(
            self,
            "required_source_domains",
            _unique_text(self.required_source_domains, label="required source domain"),
        )
        object.__setattr__(
            self,
            "required_target_domains",
            _unique_text(self.required_target_domains, label="required target domain"),
        )
        if self.min_ready_evaluations < 1:
            raise ValueError("Wave 4 transfer bundles require a positive ready count.")
        object.__setattr__(
            self, "reviewer_role_id", _text(self.reviewer_role_id, "reviewer_role_id")
        )
        object.__setattr__(
            self,
            "generated_by_engine_id",
            _text(self.generated_by_engine_id, "generated_by_engine_id"),
        )
        object.__setattr__(
            self, "notes", _unique_text(self.notes, label="transfer bundle note")
        )
        object.__setattr__(
            self, "schema_version", _text(self.schema_version, "schema_version")
        )
        if self.permits_automatic_execution:
            raise ValueError("Wave 4 transfer bundles cannot permit execution.")
        if self.claims_agi:
            raise ValueError("Wave 4 transfer bundles cannot claim AGI.")
        if self.independently_validated:
            raise ValueError(
                "Wave 4 transfer bundles cannot claim independent validation."
            )

    @property
    def evaluation_ids(self) -> tuple[str, ...]:
        """Return evaluation ids in deterministic order."""

        return tuple(item.evaluation_id for item in self.evaluations)

    @property
    def source_domains(self) -> tuple[str, ...]:
        """Return sorted source domains represented by bundled evaluations."""

        return tuple(
            sorted({item.source_rule.source_domain for item in self.evaluations})
        )

    @property
    def target_domains(self) -> tuple[str, ...]:
        """Return sorted target domains represented by bundled evaluations."""

        return tuple(
            sorted(
                {
                    target.target_domain
                    for evaluation in self.evaluations
                    for target in evaluation.targets
                }
            )
        )

    @property
    def scenario_ids(self) -> tuple[str, ...]:
        """Return sorted WorldTwin scenario ids represented by the bundle."""

        return tuple(
            sorted(
                {
                    scenario_id
                    for evaluation in self.evaluations
                    for scenario_id in evaluation.scenario_ids
                }
            )
        )

    @property
    def blackfox_receipt_ids(self) -> tuple[str, ...]:
        """Return sorted BlackFox receipt ids represented by the bundle."""

        return tuple(
            sorted(
                {
                    receipt_id
                    for evaluation in self.evaluations
                    for receipt_id in evaluation.blackfox_receipt_ids
                }
            )
        )

    @property
    def all_evidence_ids(self) -> tuple[str, ...]:
        """Return sorted evidence ids from evaluations and failure cases."""

        evidence_ids: set[str] = set()
        for evaluation in self.evaluations:
            evidence_ids.update(evaluation.all_evidence_ids)
        for failure_case in self.failure_cases:
            evidence_ids.update(failure_case.evidence_ids)
        return tuple(sorted(evidence_ids))

    @property
    def ready_evaluation_ids(self) -> tuple[str, ...]:
        """Return evaluations ready for controlled human review."""

        return tuple(
            item.evaluation_id
            for item in self.evaluations
            if item.status is WaveFourTransferStatus.READY_FOR_CONTROLLED_REVIEW
        )

    @property
    def evidence_gap_evaluation_ids(self) -> tuple[str, ...]:
        """Return evaluations that need more evidence before review."""

        return tuple(
            item.evaluation_id
            for item in self.evaluations
            if item.status is WaveFourTransferStatus.NEEDS_EVIDENCE
        )

    @property
    def repair_evaluation_ids(self) -> tuple[str, ...]:
        """Return evaluations that require repair before review."""

        return tuple(
            item.evaluation_id
            for item in self.evaluations
            if item.status is WaveFourTransferStatus.NEEDS_REPAIR
        )

    @property
    def blocked_evaluation_ids(self) -> tuple[str, ...]:
        """Return evaluations that block transfer-bundle progress."""

        return tuple(
            item.evaluation_id
            for item in self.evaluations
            if item.status is WaveFourTransferStatus.BLOCKED
        )

    @property
    def missing_required_source_domains(self) -> tuple[str, ...]:
        """Return required source domains not represented by evaluations."""

        present = set(self.source_domains)
        return tuple(
            item for item in self.required_source_domains if item not in present
        )

    @property
    def missing_required_target_domains(self) -> tuple[str, ...]:
        """Return required target domains not represented by evaluations."""

        present = set(self.target_domains)
        return tuple(
            item for item in self.required_target_domains if item not in present
        )

    @property
    def detected_failure_case_ids(self) -> tuple[str, ...]:
        """Return negative controls that were detected and given repair guidance."""

        return tuple(
            failure_case.failure_case_id
            for failure_case in self.failure_cases
            if failure_case.resolved
        )

    @property
    def unresolved_failure_case_ids(self) -> tuple[str, ...]:
        """Return negative controls that were not safely resolved."""

        return tuple(
            failure_case.failure_case_id
            for failure_case in self.failure_cases
            if not failure_case.resolved
        )

    @property
    def readiness_gaps(self) -> tuple[str, ...]:
        """Return fail-closed gaps preventing controlled review."""

        gaps: list[str] = []
        if len(self.ready_evaluation_ids) < self.min_ready_evaluations:
            gaps.append(
                "ready transfer evaluations below minimum: "
                f"{len(self.ready_evaluation_ids)}/{self.min_ready_evaluations}"
            )
        if self.missing_required_source_domains:
            missing_sources = ", ".join(self.missing_required_source_domains)
            gaps.append(f"missing required source domains: {missing_sources}")
        if self.missing_required_target_domains:
            missing_targets = ", ".join(self.missing_required_target_domains)
            gaps.append(f"missing required target domains: {missing_targets}")
        for evaluation in self.evaluations:
            for gap in evaluation.readiness_gaps:
                gaps.append(f"{evaluation.evaluation_id}: {gap}")
            for gap in evaluation.blocking_gaps:
                gaps.append(gap)
            if evaluation.failed_observation_ids:
                failed = ", ".join(evaluation.failed_observation_ids)
                gaps.append(
                    f"{evaluation.evaluation_id}: failed observations: {failed}"
                )
        for failure_case in self.failure_cases:
            if failure_case.readiness_gap:
                gaps.append(failure_case.readiness_gap)
        return tuple(gaps)

    @property
    def status(self) -> WaveFourTransferStatus:
        """Return aggregate fail-closed transfer-bundle status."""

        if self.blocked_evaluation_ids:
            return WaveFourTransferStatus.BLOCKED
        if self.repair_evaluation_ids or self.unresolved_failure_case_ids:
            return WaveFourTransferStatus.NEEDS_REPAIR
        if self.evidence_gap_evaluation_ids or self.readiness_gaps:
            return WaveFourTransferStatus.NEEDS_EVIDENCE
        return WaveFourTransferStatus.READY_FOR_CONTROLLED_REVIEW

    @property
    def ready_for_controlled_review(self) -> bool:
        """Return whether the bundle may enter controlled human review."""

        return self.status is WaveFourTransferStatus.READY_FOR_CONTROLLED_REVIEW

    @property
    def review_summary(self) -> str:
        """Return a concise transfer-bundle review summary."""

        return (
            f"{self.bundle_id}: {len(self.evaluations)} transfer evaluations; "
            f"{len(self.failure_cases)} negative controls; {self.status.value}; "
            "human review required; no AGI claim."
        )

    def failure_cases_for_evaluation(
        self, evaluation_id: str
    ) -> tuple[WaveFourTransferFailureCase, ...]:
        """Return failure cases attached to one evaluation."""

        return tuple(
            failure_case
            for failure_case in self.failure_cases
            if failure_case.evaluation_id == evaluation_id
        )

    def to_trial_protocol(self) -> WaveFourTrialProtocol:
        """Convert transfer evaluations into a controlled trial protocol."""

        return WaveFourTrialProtocol(
            protocol_id=f"transfer-bundle:{self.bundle_id}",
            tasks=tuple(
                evaluation.to_controlled_task() for evaluation in self.evaluations
            ),
            required_task_kinds=(WaveFourTrialTaskKind.CROSS_DOMAIN_TRANSFER_PROBE,),
            notes=(self.review_summary, *self.notes),
        )

    def to_artifact_bundle(self) -> WaveFourArtifactBundle:
        """Convert this bundle into shared Wave 4 transfer artifacts."""

        artifacts = tuple(
            self._artifact_ref_for_evaluation(evaluation)
            for evaluation in self.evaluations
        )
        evidence_links = tuple(
            link
            for evaluation in self.evaluations
            for link in self._evidence_links_for_evaluation(evaluation)
        )
        return WaveFourArtifactBundle(
            bundle_id=f"wave4-transfer-bundle:{self.bundle_id}",
            artifacts=artifacts,
            evidence_links=evidence_links,
            required_kinds=(WaveFourArtifactKind.TRANSFER_EVALUATION,),
            required_capability_areas=(WaveFourCapabilityArea.CROSS_DOMAIN_TRANSFER,),
            notes=(self.review_summary, *self.notes),
        )

    def canonical_payload(self) -> dict[str, Any]:
        """Return a deterministic payload for hashing and export."""

        return {
            "all_evidence_ids": list(self.all_evidence_ids),
            "blackfox_receipt_ids": list(self.blackfox_receipt_ids),
            "blocked_evaluation_ids": list(self.blocked_evaluation_ids),
            "bundle_id": self.bundle_id,
            "claims_agi": self.claims_agi,
            "detected_failure_case_ids": list(self.detected_failure_case_ids),
            "evaluations": [item.canonical_payload() for item in self.evaluations],
            "evidence_gap_evaluation_ids": list(self.evidence_gap_evaluation_ids),
            "failure_cases": [item.canonical_payload() for item in self.failure_cases],
            "generated_by_engine_id": self.generated_by_engine_id,
            "independently_validated": self.independently_validated,
            "min_ready_evaluations": self.min_ready_evaluations,
            "missing_required_source_domains": list(
                self.missing_required_source_domains
            ),
            "missing_required_target_domains": list(
                self.missing_required_target_domains
            ),
            "notes": list(self.notes),
            "permits_automatic_execution": self.permits_automatic_execution,
            "readiness_gaps": list(self.readiness_gaps),
            "ready_evaluation_ids": list(self.ready_evaluation_ids),
            "repair_evaluation_ids": list(self.repair_evaluation_ids),
            "required_source_domains": list(self.required_source_domains),
            "required_target_domains": list(self.required_target_domains),
            "review_summary": self.review_summary,
            "reviewer_role_id": self.reviewer_role_id,
            "scenario_ids": list(self.scenario_ids),
            "schema_version": self.schema_version,
            "source_domains": list(self.source_domains),
            "status": self.status.value,
            "target_domains": list(self.target_domains),
            "unresolved_failure_case_ids": list(self.unresolved_failure_case_ids),
        }

    def fingerprint(self) -> str:
        """Return a deterministic SHA-256 fingerprint for this bundle."""

        return _stable_sha256(self.canonical_payload())

    def _artifact_ref_for_evaluation(
        self, evaluation: WaveFourCrossDomainTransferEvaluation
    ) -> WaveFourArtifactRef:
        """Return an artifact reference enriched with failure-case evidence."""

        evidence_ids = tuple(
            sorted(
                set(evaluation.all_evidence_ids).union(
                    evidence_id
                    for failure_case in self.failure_cases_for_evaluation(
                        evaluation.evaluation_id
                    )
                    for evidence_id in failure_case.evidence_ids
                )
            )
        )
        if evaluation.status is WaveFourTransferStatus.READY_FOR_CONTROLLED_REVIEW:
            decision = WaveFourArtifactDecision.READY_FOR_CONTROLLED_REVIEW
        elif evaluation.status is WaveFourTransferStatus.BLOCKED:
            decision = WaveFourArtifactDecision.BLOCKED
        else:
            decision = WaveFourArtifactDecision.NEEDS_EVIDENCE
        authority_state = WaveFourAuthorityState.HUMAN_REVIEW_REQUIRED
        if evaluation.status is WaveFourTransferStatus.BLOCKED:
            authority_state = WaveFourAuthorityState.BLOCKED
        return WaveFourArtifactRef(
            artifact_id=evaluation.artifact_id,
            kind=WaveFourArtifactKind.TRANSFER_EVALUATION,
            capability_area=WaveFourCapabilityArea.CROSS_DOMAIN_TRANSFER,
            source_system=WaveFourSourceSystem.IX_COGNITION_KERNEL,
            summary=evaluation.review_summary,
            produced_by_engine_id=self.generated_by_engine_id,
            produced_by_agent_role_id=self.reviewer_role_id,
            evidence_ids=evidence_ids,
            decision=decision,
            authority_state=authority_state,
        )

    def _evidence_links_for_evaluation(
        self,
        evaluation: WaveFourCrossDomainTransferEvaluation,
    ) -> tuple[WaveFourEvidenceLink, ...]:
        """Return evidence links for evaluation and attached failure cases."""

        links: list[WaveFourEvidenceLink] = list(evaluation.evidence_links())
        for failure_case in self.failure_cases_for_evaluation(evaluation.evaluation_id):
            relation = WaveFourEvidenceRelation.TESTS
            if not failure_case.resolved:
                relation = WaveFourEvidenceRelation.BLOCKS
            for evidence_id in failure_case.evidence_ids:
                links.append(
                    WaveFourEvidenceLink(
                        evidence_id=evidence_id,
                        artifact_id=evaluation.artifact_id,
                        relation=relation,
                        summary=(
                            "Negative-control evidence for Wave 4 transfer "
                            f"failure case {failure_case.failure_case_id}."
                        ),
                        source_system=failure_case.source_system,
                    )
                )
        return tuple(sorted(links, key=lambda link: link.link_key))


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


def _unique_items(values: Iterable[T], *, label: str) -> set[T]:
    """Return unique items while rejecting duplicates."""

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
