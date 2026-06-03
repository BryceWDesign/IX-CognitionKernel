"""Wave 4 cross-domain transfer evaluation records.

Wave 4 must show controlled transfer behavior before any proto-candidate claim
is credible. This module records a source-domain rule, bounded target-domain
applications, observed transfer behavior, and fail-closed review state. The
records are evidence artifacts only: they do not authorize execution, do not
claim AGI, and do not claim independent validation.
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
from ix_cognition_kernel.wave4_trials import (
    WaveFourControlledTask,
    WaveFourTrialMeasurement,
    WaveFourTrialOutcome,
    WaveFourTrialTaskKind,
)

T = TypeVar("T")

WAVE_FOUR_TRANSFER_RULE_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave4-transfer-rule-v1"
)
WAVE_FOUR_TRANSFER_TARGET_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave4-transfer-target-v1"
)
WAVE_FOUR_TRANSFER_OBSERVATION_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave4-transfer-observation-v1"
)
WAVE_FOUR_TRANSFER_EVALUATION_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave4-transfer-evaluation-v1"
)


class WaveFourTransferOutcome(StrEnum):
    """Measured outcome for a cross-domain transfer evaluation."""

    TRANSFER_CONFIRMED = "transfer-confirmed"
    PARTIAL_TRANSFER = "partial-transfer"
    TRANSFER_FAILED = "transfer-failed"
    BLOCKED = "blocked"


class WaveFourTransferStatus(StrEnum):
    """Fail-closed review status for transfer evaluation records."""

    READY_FOR_CONTROLLED_REVIEW = "ready-for-controlled-review"
    NEEDS_EVIDENCE = "needs-evidence"
    NEEDS_REPAIR = "needs-repair"
    BLOCKED = "blocked"


@dataclass(frozen=True, slots=True)
class WaveFourTransferRule:
    """A source-domain rule proposed for bounded cross-domain transfer."""

    rule_id: str
    source_domain: str
    rule_summary: str
    invariant_conditions: tuple[str, ...]
    supporting_evidence_ids: tuple[str, ...]
    prohibited_assumptions: tuple[str, ...] = ()
    schema_version: str = WAVE_FOUR_TRANSFER_RULE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate source rule identity and evidence support."""

        object.__setattr__(self, "rule_id", _text(self.rule_id, "rule_id"))
        object.__setattr__(
            self, "source_domain", _text(self.source_domain, "source_domain")
        )
        object.__setattr__(
            self, "rule_summary", _text(self.rule_summary, "rule_summary")
        )
        object.__setattr__(
            self,
            "invariant_conditions",
            _unique_text(self.invariant_conditions, label="invariant condition"),
        )
        if not self.invariant_conditions:
            raise ValueError("Wave 4 transfer rules require invariant conditions.")
        object.__setattr__(
            self,
            "supporting_evidence_ids",
            _unique_text(
                self.supporting_evidence_ids, label="rule supporting evidence_id"
            ),
        )
        if not self.supporting_evidence_ids:
            raise ValueError("Wave 4 transfer rules require supporting evidence ids.")
        object.__setattr__(
            self,
            "prohibited_assumptions",
            _unique_text(
                self.prohibited_assumptions, label="prohibited assumption"
            ),
        )
        object.__setattr__(
            self, "schema_version", _text(self.schema_version, "schema_version")
        )

    @property
    def rule_key(self) -> str:
        """Return deterministic uniqueness key for this transfer rule."""

        return self.rule_id

    def canonical_payload(self) -> dict[str, Any]:
        """Return a deterministic payload for hashing and export."""

        return {
            "invariant_conditions": list(self.invariant_conditions),
            "prohibited_assumptions": list(self.prohibited_assumptions),
            "rule_id": self.rule_id,
            "rule_summary": self.rule_summary,
            "schema_version": self.schema_version,
            "source_domain": self.source_domain,
            "supporting_evidence_ids": list(self.supporting_evidence_ids),
        }

    def fingerprint(self) -> str:
        """Return a deterministic SHA-256 fingerprint for this rule."""

        return _stable_sha256(self.canonical_payload())


@dataclass(frozen=True, slots=True)
class WaveFourTransferTarget:
    """A bounded target domain where the source rule is tested."""

    target_id: str
    target_domain: str
    adaptation_summary: str
    expected_behavior: str
    scenario_ids: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    risk_notes: tuple[str, ...] = ()
    schema_version: str = WAVE_FOUR_TRANSFER_TARGET_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate target identity, scenario links, and evidence support."""

        object.__setattr__(self, "target_id", _text(self.target_id, "target_id"))
        object.__setattr__(
            self, "target_domain", _text(self.target_domain, "target_domain")
        )
        object.__setattr__(
            self,
            "adaptation_summary",
            _text(self.adaptation_summary, "adaptation_summary"),
        )
        object.__setattr__(
            self,
            "expected_behavior",
            _text(self.expected_behavior, "expected_behavior"),
        )
        object.__setattr__(
            self, "scenario_ids", _unique_text(self.scenario_ids, label="scenario_id")
        )
        if not self.scenario_ids:
            raise ValueError("Wave 4 transfer targets require scenario ids.")
        object.__setattr__(
            self,
            "evidence_ids",
            _unique_text(self.evidence_ids, label="target evidence_id"),
        )
        if not self.evidence_ids:
            raise ValueError("Wave 4 transfer targets require evidence ids.")
        object.__setattr__(
            self, "risk_notes", _unique_text(self.risk_notes, label="risk note")
        )
        object.__setattr__(
            self, "schema_version", _text(self.schema_version, "schema_version")
        )

    @property
    def target_key(self) -> str:
        """Return deterministic uniqueness key for this transfer target."""

        return self.target_id

    def canonical_payload(self) -> dict[str, Any]:
        """Return a deterministic payload for hashing and export."""

        return {
            "adaptation_summary": self.adaptation_summary,
            "evidence_ids": list(self.evidence_ids),
            "expected_behavior": self.expected_behavior,
            "risk_notes": list(self.risk_notes),
            "scenario_ids": list(self.scenario_ids),
            "schema_version": self.schema_version,
            "target_domain": self.target_domain,
            "target_id": self.target_id,
        }

    def fingerprint(self) -> str:
        """Return a deterministic SHA-256 fingerprint for this target."""

        return _stable_sha256(self.canonical_payload())


@dataclass(frozen=True, slots=True)
class WaveFourTransferObservation:
    """Measured transfer behavior observed in one target domain."""

    observation_id: str
    target_id: str
    observed_behavior: str
    matched_invariant_conditions: tuple[str, ...]
    violated_invariant_conditions: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    passed: bool
    schema_version: str = WAVE_FOUR_TRANSFER_OBSERVATION_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate transfer observation evidence and invariant accounting."""

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
            "matched_invariant_conditions",
            _unique_text(
                self.matched_invariant_conditions,
                label="matched invariant condition",
            ),
        )
        object.__setattr__(
            self,
            "violated_invariant_conditions",
            _unique_text(
                self.violated_invariant_conditions,
                label="violated invariant condition",
            ),
        )
        object.__setattr__(
            self,
            "evidence_ids",
            _unique_text(self.evidence_ids, label="observation evidence_id"),
        )
        if not self.evidence_ids:
            raise ValueError("Wave 4 transfer observations require evidence ids.")
        object.__setattr__(
            self, "schema_version", _text(self.schema_version, "schema_version")
        )
        if self.passed and self.violated_invariant_conditions:
            raise ValueError(
                "Passed Wave 4 transfer observations cannot violate invariants."
            )
        if not self.passed and not self.violated_invariant_conditions:
            raise ValueError(
                "Failed Wave 4 transfer observations require violated invariants."
            )

    @property
    def observation_key(self) -> str:
        """Return deterministic uniqueness key for this transfer observation."""

        return self.observation_id

    def canonical_payload(self) -> dict[str, Any]:
        """Return a deterministic payload for hashing and export."""

        return {
            "evidence_ids": list(self.evidence_ids),
            "matched_invariant_conditions": list(self.matched_invariant_conditions),
            "observation_id": self.observation_id,
            "observed_behavior": self.observed_behavior,
            "passed": self.passed,
            "schema_version": self.schema_version,
            "target_id": self.target_id,
            "violated_invariant_conditions": list(
                self.violated_invariant_conditions
            ),
        }

    def fingerprint(self) -> str:
        """Return a deterministic SHA-256 fingerprint for this observation."""

        return _stable_sha256(self.canonical_payload())


@dataclass(frozen=True, slots=True)
class WaveFourCrossDomainTransferEvaluation:
    """A controlled Wave 4 evaluation of cross-domain rule transfer."""

    evaluation_id: str
    source_rule: WaveFourTransferRule
    targets: tuple[WaveFourTransferTarget, ...]
    observations: tuple[WaveFourTransferObservation, ...]
    blackfox_receipt_ids: tuple[str, ...]
    reviewer_role_id: str = "cross-domain-transfer-evaluator"
    generated_by_engine_id: str = "wave4-cross-domain-transfer-engine"
    blocked_reasons: tuple[str, ...] = ()
    permits_automatic_execution: bool = False
    claims_agi: bool = False
    independently_validated: bool = False
    schema_version: str = WAVE_FOUR_TRANSFER_EVALUATION_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate evaluation coverage, safety boundaries, and uniqueness."""

        object.__setattr__(
            self, "evaluation_id", _text(self.evaluation_id, "evaluation_id")
        )
        if not self.targets:
            raise ValueError("Wave 4 transfer evaluations require targets.")
        sorted_targets = tuple(sorted(self.targets, key=lambda item: item.target_key))
        target_ids = _unique_items(
            (target.target_id for target in sorted_targets), label="target_id"
        )
        object.__setattr__(self, "targets", sorted_targets)
        sorted_observations = tuple(
            sorted(self.observations, key=lambda item: item.observation_key)
        )
        _unique_items(
            (item.observation_id for item in sorted_observations),
            label="observation_id",
        )
        for observation in sorted_observations:
            if observation.target_id not in target_ids:
                raise ValueError(
                    "Wave 4 transfer observations must reference evaluation targets: "
                    f"{observation.target_id}"
                )
        object.__setattr__(self, "observations", sorted_observations)
        object.__setattr__(
            self,
            "blackfox_receipt_ids",
            _unique_text(self.blackfox_receipt_ids, label="blackfox receipt_id"),
        )
        object.__setattr__(
            self, "reviewer_role_id", _text(self.reviewer_role_id, "reviewer_role_id")
        )
        object.__setattr__(
            self,
            "generated_by_engine_id",
            _text(self.generated_by_engine_id, "generated_by_engine_id"),
        )
        object.__setattr__(
            self,
            "blocked_reasons",
            _unique_text(self.blocked_reasons, label="blocked reason"),
        )
        object.__setattr__(
            self, "schema_version", _text(self.schema_version, "schema_version")
        )
        if self.permits_automatic_execution:
            raise ValueError("Wave 4 transfer evaluations cannot permit execution.")
        if self.claims_agi:
            raise ValueError("Wave 4 transfer evaluations cannot claim AGI.")
        if self.independently_validated:
            raise ValueError(
                "Wave 4 transfer evaluations cannot claim independent validation."
            )
        if self.blocked_reasons and self.observations:
            raise ValueError(
                "Blocked Wave 4 transfer evaluations cannot carry results."
            )

    @property
    def artifact_id(self) -> str:
        """Return the shared Wave 4 artifact id for this evaluation."""

        return f"wave4-transfer-evaluation:{self.evaluation_id}"

    @property
    def target_ids(self) -> tuple[str, ...]:
        """Return target ids in deterministic order."""

        return tuple(target.target_id for target in self.targets)

    @property
    def observed_target_ids(self) -> tuple[str, ...]:
        """Return target ids that have at least one observation."""

        return tuple(sorted({item.target_id for item in self.observations}))

    @property
    def missing_observation_target_ids(self) -> tuple[str, ...]:
        """Return target ids without observation evidence."""

        observed = set(self.observed_target_ids)
        return tuple(
            target_id for target_id in self.target_ids if target_id not in observed
        )

    @property
    def failed_observation_ids(self) -> tuple[str, ...]:
        """Return observation ids that failed transfer acceptance."""

        return tuple(
            observation.observation_id
            for observation in self.observations
            if not observation.passed
        )

    @property
    def all_evidence_ids(self) -> tuple[str, ...]:
        """Return sorted evidence ids from source, targets, and observations."""

        evidence_ids = set(self.source_rule.supporting_evidence_ids)
        for target in self.targets:
            evidence_ids.update(target.evidence_ids)
        for observation in self.observations:
            evidence_ids.update(observation.evidence_ids)
        return tuple(sorted(evidence_ids))

    @property
    def scenario_ids(self) -> tuple[str, ...]:
        """Return sorted WorldTwin scenario ids used by transfer targets."""

        return tuple(
            sorted({item for target in self.targets for item in target.scenario_ids})
        )

    @property
    def readiness_gaps(self) -> tuple[str, ...]:
        """Return gaps that prevent controlled transfer review."""

        gaps: list[str] = []
        if self.missing_observation_target_ids:
            missing = ", ".join(self.missing_observation_target_ids)
            gaps.append(f"missing transfer observations for targets: {missing}")
        if not self.blackfox_receipt_ids:
            gaps.append("missing BlackFox receipt ids for transfer review")
        if not self.all_evidence_ids:
            gaps.append("missing evidence ids for transfer evaluation")
        return tuple(gaps)

    @property
    def blocking_gaps(self) -> tuple[str, ...]:
        """Return hard blocks for this transfer evaluation."""

        return tuple(
            f"{self.evaluation_id} blocked: {reason}"
            for reason in self.blocked_reasons
        )

    @property
    def outcome(self) -> WaveFourTransferOutcome:
        """Return the measured fail-closed transfer outcome."""

        if self.blocked_reasons:
            return WaveFourTransferOutcome.BLOCKED
        if self.failed_observation_ids and self.observed_target_ids:
            return WaveFourTransferOutcome.PARTIAL_TRANSFER
        if self.failed_observation_ids:
            return WaveFourTransferOutcome.TRANSFER_FAILED
        if self.readiness_gaps:
            return WaveFourTransferOutcome.TRANSFER_FAILED
        return WaveFourTransferOutcome.TRANSFER_CONFIRMED

    @property
    def status(self) -> WaveFourTransferStatus:
        """Return aggregate fail-closed transfer review status."""

        if self.blocked_reasons:
            return WaveFourTransferStatus.BLOCKED
        if self.failed_observation_ids:
            return WaveFourTransferStatus.NEEDS_REPAIR
        if self.readiness_gaps:
            return WaveFourTransferStatus.NEEDS_EVIDENCE
        return WaveFourTransferStatus.READY_FOR_CONTROLLED_REVIEW

    @property
    def ready_for_controlled_review(self) -> bool:
        """Return whether this evaluation may enter controlled review."""

        return self.status is WaveFourTransferStatus.READY_FOR_CONTROLLED_REVIEW

    @property
    def human_authority_state(self) -> WaveFourAuthorityState:
        """Return human-authority state for this evaluation."""

        if self.status is WaveFourTransferStatus.BLOCKED:
            return WaveFourAuthorityState.BLOCKED
        return WaveFourAuthorityState.HUMAN_REVIEW_REQUIRED

    @property
    def review_summary(self) -> str:
        """Return a concise transfer review summary."""

        return (
            f"{self.evaluation_id}: {self.source_rule.source_domain} -> "
            f"{len(self.targets)} targets; {self.status.value}; "
            f"{len(self.failed_observation_ids)} failed observations; "
            "human review required; no AGI claim."
        )

    def to_artifact_ref(self) -> WaveFourArtifactRef:
        """Convert the evaluation into a shared Wave 4 artifact reference."""

        if self.status is WaveFourTransferStatus.READY_FOR_CONTROLLED_REVIEW:
            decision = WaveFourArtifactDecision.READY_FOR_CONTROLLED_REVIEW
        elif self.status is WaveFourTransferStatus.BLOCKED:
            decision = WaveFourArtifactDecision.BLOCKED
        else:
            decision = WaveFourArtifactDecision.NEEDS_EVIDENCE
        return WaveFourArtifactRef(
            artifact_id=self.artifact_id,
            kind=WaveFourArtifactKind.TRANSFER_EVALUATION,
            capability_area=WaveFourCapabilityArea.CROSS_DOMAIN_TRANSFER,
            source_system=WaveFourSourceSystem.IX_COGNITION_KERNEL,
            summary=self.review_summary,
            produced_by_engine_id=self.generated_by_engine_id,
            produced_by_agent_role_id=self.reviewer_role_id,
            evidence_ids=self.all_evidence_ids,
            decision=decision,
            authority_state=self.human_authority_state,
        )

    def evidence_links(self) -> tuple[WaveFourEvidenceLink, ...]:
        """Return shared evidence links for this transfer artifact."""

        return tuple(
            WaveFourEvidenceLink(
                evidence_id=evidence_id,
                artifact_id=self.artifact_id,
                relation=WaveFourEvidenceRelation.TESTS,
                summary=(
                    "Evidence for Wave 4 transfer evaluation "
                    f"{self.evaluation_id}."
                ),
                source_system=WaveFourSourceSystem.LOCAL_TEST_SUITE,
            )
            for evidence_id in self.all_evidence_ids
        )

    def to_artifact_bundle(self) -> WaveFourArtifactBundle:
        """Convert this evaluation into a one-artifact Wave 4 bundle."""

        return WaveFourArtifactBundle(
            bundle_id=f"wave4-transfer-bundle:{self.evaluation_id}",
            artifacts=(self.to_artifact_ref(),),
            evidence_links=self.evidence_links(),
            required_kinds=(WaveFourArtifactKind.TRANSFER_EVALUATION,),
            required_capability_areas=(WaveFourCapabilityArea.CROSS_DOMAIN_TRANSFER,),
            notes=(self.review_summary,),
        )

    def to_controlled_task(self) -> WaveFourControlledTask:
        """Represent the transfer evaluation as a controlled trial task."""

        measurements = tuple(
            WaveFourTrialMeasurement(
                measurement_id=f"transfer-observation:{observation.observation_id}",
                metric_name="cross-domain-transfer-invariant-preservation",
                target="all invariant conditions preserved in target domain",
                observed=observation.observed_behavior,
                passed=observation.passed,
                evidence_ids=observation.evidence_ids,
            )
            for observation in self.observations
        )
        if self.status is WaveFourTransferStatus.READY_FOR_CONTROLLED_REVIEW:
            outcome = WaveFourTrialOutcome.PASSED
        elif self.status is WaveFourTransferStatus.BLOCKED:
            outcome = WaveFourTrialOutcome.BLOCKED
        elif self.status is WaveFourTransferStatus.NEEDS_REPAIR:
            outcome = WaveFourTrialOutcome.FAILED
        else:
            outcome = WaveFourTrialOutcome.NOT_RUN
        return WaveFourControlledTask(
            task_id=f"transfer:{self.evaluation_id}",
            task_kind=WaveFourTrialTaskKind.CROSS_DOMAIN_TRANSFER_PROBE,
            objective=self.source_rule.rule_summary,
            input_domain=self.source_rule.source_domain,
            evaluation_prompt="Evaluate whether the source rule transfers without "
            "hiding uncertainty, violating boundaries, or authorizing execution.",
            success_criteria=(
                "target observations preserve source-rule invariants",
                "WorldTwin scenarios and BlackFox receipts remain linked",
                "no automatic execution and no AGI claim",
            ),
            stop_conditions=(
                "stop on violated invariant",
                "stop on missing observation evidence",
                "stop on missing human-review receipt",
            ),
            safety_boundaries=(
                "record only",
                "human review required",
                "no AGI claim",
            ),
            outcome=outcome,
            evidence_ids=self.all_evidence_ids,
            measurements=measurements,
            scenario_ids=self.scenario_ids,
            blackfox_receipt_ids=self.blackfox_receipt_ids,
            blocked_reasons=self.blocked_reasons,
        )

    def canonical_payload(self) -> dict[str, Any]:
        """Return a deterministic payload for hashing and export."""

        return {
            "all_evidence_ids": list(self.all_evidence_ids),
            "artifact_id": self.artifact_id,
            "blackfox_receipt_ids": list(self.blackfox_receipt_ids),
            "blocking_gaps": list(self.blocking_gaps),
            "blocked_reasons": list(self.blocked_reasons),
            "claims_agi": self.claims_agi,
            "failed_observation_ids": list(self.failed_observation_ids),
            "generated_by_engine_id": self.generated_by_engine_id,
            "human_authority_state": self.human_authority_state.value,
            "independently_validated": self.independently_validated,
            "missing_observation_target_ids": list(self.missing_observation_target_ids),
            "observations": [item.canonical_payload() for item in self.observations],
            "outcome": self.outcome.value,
            "permits_automatic_execution": self.permits_automatic_execution,
            "readiness_gaps": list(self.readiness_gaps),
            "review_summary": self.review_summary,
            "reviewer_role_id": self.reviewer_role_id,
            "schema_version": self.schema_version,
            "scenario_ids": list(self.scenario_ids),
            "source_rule": self.source_rule.canonical_payload(),
            "status": self.status.value,
            "target_ids": list(self.target_ids),
            "targets": [target.canonical_payload() for target in self.targets],
        }

    def fingerprint(self) -> str:
        """Return a deterministic SHA-256 fingerprint for this evaluation."""

        return _stable_sha256(self.canonical_payload())


def passing_transfer_observation(
    *,
    observation_id: str,
    target_id: str,
    observed_behavior: str,
    matched_invariant_conditions: tuple[str, ...],
    evidence_id: str,
) -> WaveFourTransferObservation:
    """Build a passing transfer observation with one evidence id."""

    return WaveFourTransferObservation(
        observation_id=observation_id,
        target_id=target_id,
        observed_behavior=observed_behavior,
        matched_invariant_conditions=matched_invariant_conditions,
        violated_invariant_conditions=(),
        evidence_ids=(evidence_id,),
        passed=True,
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
