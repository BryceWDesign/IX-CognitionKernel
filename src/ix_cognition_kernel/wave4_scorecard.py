"""Wave 4 proto-candidate scorecard and fail-closed review gates.

An integrated proto-candidate bundle is not ready because it has the right
label. It is ready only when explicit gates prove task coverage, artifact
coverage, capability coverage, evidence binding, scenario continuity, BlackFox
receipt continuity, human authority, anti-overclaim boundaries, and no automatic
execution. This module turns those checks into deterministic, evidence-bound
scorecards.
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
from ix_cognition_kernel.wave4_proto_candidate import (
    WaveFourProtoCandidateStatus,
    WaveFourProtoCandidateTrialBundle,
)
from ix_cognition_kernel.wave4_trials import WaveFourTrialStatus

T = TypeVar("T")

WAVE_FOUR_SCORECARD_GATE_SCHEMA_VERSION = "ix-cognition-kernel-wave4-scorecard-gate-v1"
WAVE_FOUR_PROTO_SCORECARD_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave4-proto-candidate-scorecard-v1"
)


class WaveFourScorecardGateKind(StrEnum):
    """Gate kinds required for Wave 4 proto-candidate review."""

    PROTOCOL_STATUS = "protocol-status"
    TASK_COVERAGE = "task-coverage"
    ARTIFACT_COVERAGE = "artifact-coverage"
    CAPABILITY_COVERAGE = "capability-coverage"
    ARTIFACT_READINESS = "artifact-readiness"
    EVIDENCE_BINDING = "evidence-binding"
    SCENARIO_COVERAGE = "scenario-coverage"
    BLACKFOX_RECEIPT_COVERAGE = "blackfox-receipt-coverage"
    HUMAN_AUTHORITY_PRESERVED = "human-authority-preserved"
    ANTI_OVERCLAIM_BOUNDARY = "anti-overclaim-boundary"
    NO_AUTOMATIC_EXECUTION = "no-automatic-execution"


class WaveFourScorecardGateSeverity(StrEnum):
    """Failure severity for a scorecard gate."""

    EVIDENCE = "evidence"
    REPAIR = "repair"
    BLOCKING = "blocking"


class WaveFourScorecardStatus(StrEnum):
    """Fail-closed status for a Wave 4 proto-candidate scorecard."""

    READY_FOR_CONTROLLED_REVIEW = "ready-for-controlled-review"
    NEEDS_EVIDENCE = "needs-evidence"
    NEEDS_REPAIR = "needs-repair"
    BLOCKED = "blocked"


class WaveFourScorecardDecision(StrEnum):
    """Human-readable decision produced by a Wave 4 scorecard."""

    ALLOW_CONTROLLED_REVIEW = "allow-controlled-review"
    HOLD_FOR_EVIDENCE = "hold-for-evidence"
    HOLD_FOR_REPAIR = "hold-for-repair"
    BLOCK_REVIEW = "block-review"


REQUIRED_WAVE_FOUR_SCORECARD_GATE_KINDS: tuple[WaveFourScorecardGateKind, ...] = (
    WaveFourScorecardGateKind.PROTOCOL_STATUS,
    WaveFourScorecardGateKind.TASK_COVERAGE,
    WaveFourScorecardGateKind.ARTIFACT_COVERAGE,
    WaveFourScorecardGateKind.CAPABILITY_COVERAGE,
    WaveFourScorecardGateKind.ARTIFACT_READINESS,
    WaveFourScorecardGateKind.EVIDENCE_BINDING,
    WaveFourScorecardGateKind.SCENARIO_COVERAGE,
    WaveFourScorecardGateKind.BLACKFOX_RECEIPT_COVERAGE,
    WaveFourScorecardGateKind.HUMAN_AUTHORITY_PRESERVED,
    WaveFourScorecardGateKind.ANTI_OVERCLAIM_BOUNDARY,
    WaveFourScorecardGateKind.NO_AUTOMATIC_EXECUTION,
)


@dataclass(frozen=True, slots=True)
class WaveFourScorecardGate:
    """One fail-closed gate in a Wave 4 proto-candidate scorecard."""

    gate_id: str
    gate_kind: WaveFourScorecardGateKind
    severity: WaveFourScorecardGateSeverity
    passed: bool
    summary: str
    evidence_ids: tuple[str, ...] = ()
    failure_summary: str = ""
    source_system: WaveFourSourceSystem = WaveFourSourceSystem.IX_COGNITION_KERNEL
    schema_version: str = WAVE_FOUR_SCORECARD_GATE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate gate identity, evidence references, and pass/fail accounting."""

        object.__setattr__(self, "gate_id", _text(self.gate_id, "gate_id"))
        object.__setattr__(self, "summary", _text(self.summary, "summary"))
        object.__setattr__(
            self,
            "evidence_ids",
            _unique_text(self.evidence_ids, label="scorecard-gate evidence_id"),
        )
        object.__setattr__(self, "failure_summary", self.failure_summary.strip())
        object.__setattr__(
            self, "schema_version", _text(self.schema_version, "schema_version")
        )
        if self.passed and self.failure_summary:
            raise ValueError("Passed Wave 4 scorecard gates cannot carry failure text.")
        if not self.passed and not self.failure_summary:
            raise ValueError("Failed Wave 4 scorecard gates require failure text.")

    @property
    def gate_key(self) -> str:
        """Return deterministic uniqueness key."""

        return self.gate_id

    @property
    def readiness_gap(self) -> str:
        """Return fail-closed gap text when this gate failed."""

        if self.passed:
            return ""
        return f"{self.gate_id} failed: {self.failure_summary}"

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic gate payload."""

        return {
            "evidence_ids": list(self.evidence_ids),
            "failure_summary": self.failure_summary,
            "gate_id": self.gate_id,
            "gate_kind": self.gate_kind.value,
            "passed": self.passed,
            "readiness_gap": self.readiness_gap,
            "schema_version": self.schema_version,
            "severity": self.severity.value,
            "source_system": self.source_system.value,
            "summary": self.summary,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint."""

        return _stable_sha256(self.canonical_payload())


@dataclass(frozen=True, slots=True)
class WaveFourProtoCandidateScorecard:
    """Fail-closed scorecard for an integrated Wave 4 proto-candidate bundle."""

    scorecard_id: str
    proto_candidate_bundle: WaveFourProtoCandidateTrialBundle
    gates: tuple[WaveFourScorecardGate, ...]
    scenario_ids: tuple[str, ...]
    blackfox_receipt_ids: tuple[str, ...]
    reviewer_role_id: str = "wave4-scorecard-reviewer"
    generated_by_engine_id: str = "wave4-scorecard-engine"
    notes: tuple[str, ...] = ()
    blocked_reasons: tuple[str, ...] = ()
    required_gate_kinds: tuple[WaveFourScorecardGateKind, ...] = (
        REQUIRED_WAVE_FOUR_SCORECARD_GATE_KINDS
    )
    minimum_passing_score: float = 1.0
    permits_automatic_execution: bool = False
    claims_agi: bool = False
    independently_validated: bool = False
    schema_version: str = WAVE_FOUR_PROTO_SCORECARD_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate scorecard coverage, deterministic order, and boundaries."""

        object.__setattr__(
            self, "scorecard_id", _text(self.scorecard_id, "scorecard_id")
        )
        if not self.gates:
            raise ValueError("Wave 4 scorecards require gates.")
        gates = tuple(sorted(self.gates, key=lambda gate: gate.gate_key))
        _unique_items((gate.gate_id for gate in gates), "gate_id")
        object.__setattr__(self, "gates", gates)
        object.__setattr__(
            self, "scenario_ids", _unique_text(self.scenario_ids, label="scenario_id")
        )
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
            self, "notes", _unique_text(self.notes, label="scorecard note")
        )
        object.__setattr__(
            self,
            "blocked_reasons",
            _unique_text(self.blocked_reasons, label="blocked reason"),
        )
        object.__setattr__(
            self,
            "required_gate_kinds",
            _unique_items(self.required_gate_kinds, "required gate kind"),
        )
        if not 0.0 <= self.minimum_passing_score <= 1.0:
            raise ValueError("minimum_passing_score must be 0.0..1.0.")
        object.__setattr__(
            self, "schema_version", _text(self.schema_version, "schema_version")
        )
        if self.permits_automatic_execution:
            raise ValueError("Wave 4 scorecards cannot permit execution.")
        if self.claims_agi:
            raise ValueError("Wave 4 scorecards cannot claim AGI.")
        if self.independently_validated:
            raise ValueError("Wave 4 scorecards cannot claim independent validation.")

    @property
    def artifact_id(self) -> str:
        """Return shared Wave 4 artifact id for this scorecard."""

        return f"wave4-scorecard:{self.scorecard_id}"

    @property
    def gate_kinds_present(self) -> tuple[WaveFourScorecardGateKind, ...]:
        """Return scorecard gate kinds represented by gates."""

        return tuple(
            sorted({gate.gate_kind for gate in self.gates}, key=lambda item: item.value)
        )

    @property
    def missing_required_gate_kinds(self) -> tuple[WaveFourScorecardGateKind, ...]:
        """Return required gate kinds missing from this scorecard."""

        present = set(self.gate_kinds_present)
        return tuple(kind for kind in self.required_gate_kinds if kind not in present)

    @property
    def passed_gate_ids(self) -> tuple[str, ...]:
        """Return passed gate ids."""

        return tuple(gate.gate_id for gate in self.gates if gate.passed)

    @property
    def failed_gate_ids(self) -> tuple[str, ...]:
        """Return failed gate ids."""

        return tuple(gate.gate_id for gate in self.gates if not gate.passed)

    @property
    def failed_evidence_gate_ids(self) -> tuple[str, ...]:
        """Return failed gates that require more evidence."""

        return self._failed_gate_ids_by_severity(WaveFourScorecardGateSeverity.EVIDENCE)

    @property
    def failed_repair_gate_ids(self) -> tuple[str, ...]:
        """Return failed gates that require repair."""

        return self._failed_gate_ids_by_severity(WaveFourScorecardGateSeverity.REPAIR)

    @property
    def failed_blocking_gate_ids(self) -> tuple[str, ...]:
        """Return failed gates that block review."""

        return self._failed_gate_ids_by_severity(WaveFourScorecardGateSeverity.BLOCKING)

    @property
    def passing_score(self) -> float:
        """Return gate pass ratio rounded for deterministic export."""

        return round(len(self.passed_gate_ids) / len(self.gates), 6)

    @property
    def all_evidence_ids(self) -> tuple[str, ...]:
        """Return sorted evidence ids from gates and proto-candidate bundle."""

        evidence_ids = set(self.proto_candidate_bundle.all_evidence_ids)
        for gate in self.gates:
            evidence_ids.update(gate.evidence_ids)
        return tuple(sorted(evidence_ids))

    @property
    def readiness_gaps(self) -> tuple[str, ...]:
        """Return fail-closed gaps preventing controlled review."""

        gaps: list[str] = []
        if self.missing_required_gate_kinds:
            missing = ", ".join(kind.value for kind in self.missing_required_gate_kinds)
            gaps.append(f"missing scorecard gate coverage: {missing}")
        gaps.extend(gate.readiness_gap for gate in self.gates if gate.readiness_gap)
        if self.passing_score < self.minimum_passing_score:
            gaps.append(
                "scorecard pass ratio below minimum: "
                f"{self.passing_score:.3f}/{self.minimum_passing_score:.3f}"
            )
        if not self.scenario_ids:
            gaps.append(f"{self.scorecard_id} has no WorldTwin scenario ids")
        if not self.blackfox_receipt_ids:
            gaps.append(f"{self.scorecard_id} has no BlackFox receipt ids")
        return tuple(gaps)

    @property
    def blocking_gaps(self) -> tuple[str, ...]:
        """Return hard blocks for this scorecard."""

        gaps = [
            f"{self.scorecard_id} blocked: {reason}" for reason in self.blocked_reasons
        ]
        gaps.extend(
            f"blocking scorecard gate failed: {gate_id}"
            for gate_id in self.failed_blocking_gate_ids
        )
        gaps.extend(self.proto_candidate_bundle.blocking_gaps)
        return tuple(gaps)

    @property
    def status(self) -> WaveFourScorecardStatus:
        """Return fail-closed scorecard status."""

        if self.blocking_gaps:
            return WaveFourScorecardStatus.BLOCKED
        if (
            self.failed_repair_gate_ids
            or self.proto_candidate_bundle.status
            is WaveFourProtoCandidateStatus.NEEDS_REPAIR
        ):
            return WaveFourScorecardStatus.NEEDS_REPAIR
        if self.readiness_gaps:
            return WaveFourScorecardStatus.NEEDS_EVIDENCE
        return WaveFourScorecardStatus.READY_FOR_CONTROLLED_REVIEW

    @property
    def decision(self) -> WaveFourScorecardDecision:
        """Return human-readable scorecard decision."""

        if self.status is WaveFourScorecardStatus.BLOCKED:
            return WaveFourScorecardDecision.BLOCK_REVIEW
        if self.status is WaveFourScorecardStatus.NEEDS_REPAIR:
            return WaveFourScorecardDecision.HOLD_FOR_REPAIR
        if self.status is WaveFourScorecardStatus.NEEDS_EVIDENCE:
            return WaveFourScorecardDecision.HOLD_FOR_EVIDENCE
        return WaveFourScorecardDecision.ALLOW_CONTROLLED_REVIEW

    @property
    def ready_for_controlled_review(self) -> bool:
        """Return whether the scorecard allows controlled human review."""

        return self.status is WaveFourScorecardStatus.READY_FOR_CONTROLLED_REVIEW

    @property
    def human_authority_state(self) -> WaveFourAuthorityState:
        """Return human-authority state for the scorecard."""

        if self.status is WaveFourScorecardStatus.BLOCKED:
            return WaveFourAuthorityState.BLOCKED
        return WaveFourAuthorityState.HUMAN_REVIEW_REQUIRED

    @property
    def review_summary(self) -> str:
        """Return concise scorecard summary."""

        return (
            f"{self.scorecard_id}: {len(self.gates)} gates; "
            f"score {self.passing_score:.3f}; {self.status.value}; "
            "human review required; no AGI claim."
        )

    def gate_by_id(self, gate_id: str) -> WaveFourScorecardGate:
        """Return one scorecard gate by id."""

        for gate in self.gates:
            if gate.gate_id == gate_id:
                return gate
        raise ValueError(f"Unknown Wave 4 scorecard gate_id: {gate_id}")

    def to_artifact_ref(self) -> WaveFourArtifactRef:
        """Convert this scorecard into a shared Wave 4 readiness artifact."""

        if self.status is WaveFourScorecardStatus.READY_FOR_CONTROLLED_REVIEW:
            decision = WaveFourArtifactDecision.READY_FOR_CONTROLLED_REVIEW
        elif self.status is WaveFourScorecardStatus.BLOCKED:
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
            produced_by_agent_role_id=self.reviewer_role_id,
            evidence_ids=self.all_evidence_ids,
            decision=decision,
            authority_state=self.human_authority_state,
        )

    def evidence_links(self) -> tuple[WaveFourEvidenceLink, ...]:
        """Return evidence links for this scorecard artifact."""

        relation = WaveFourEvidenceRelation.TESTS
        if self.status is WaveFourScorecardStatus.BLOCKED:
            relation = WaveFourEvidenceRelation.BLOCKS
        return tuple(
            WaveFourEvidenceLink(
                evidence_id=evidence_id,
                artifact_id=self.artifact_id,
                relation=relation,
                summary=f"Evidence for Wave 4 scorecard {self.scorecard_id}.",
                source_system=WaveFourSourceSystem.LOCAL_TEST_SUITE,
            )
            for evidence_id in self.all_evidence_ids
        )

    def to_artifact_bundle(self) -> WaveFourArtifactBundle:
        """Convert this scorecard into a one-artifact Wave 4 bundle."""

        return WaveFourArtifactBundle(
            bundle_id=f"wave4-scorecard-bundle:{self.scorecard_id}",
            artifacts=(self.to_artifact_ref(),),
            evidence_links=self.evidence_links(),
            required_kinds=(WaveFourArtifactKind.READINESS_SNAPSHOT,),
            required_capability_areas=(WaveFourCapabilityArea.AUDIT_TRAIL,),
            notes=(self.review_summary, *self.notes),
        )

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic scorecard payload."""

        return {
            "all_evidence_ids": list(self.all_evidence_ids),
            "artifact_id": self.artifact_id,
            "blackfox_receipt_ids": list(self.blackfox_receipt_ids),
            "blocking_gaps": list(self.blocking_gaps),
            "blocked_reasons": list(self.blocked_reasons),
            "claims_agi": self.claims_agi,
            "decision": self.decision.value,
            "failed_blocking_gate_ids": list(self.failed_blocking_gate_ids),
            "failed_evidence_gate_ids": list(self.failed_evidence_gate_ids),
            "failed_gate_ids": list(self.failed_gate_ids),
            "failed_repair_gate_ids": list(self.failed_repair_gate_ids),
            "gate_kinds_present": [kind.value for kind in self.gate_kinds_present],
            "gates": [gate.canonical_payload() for gate in self.gates],
            "generated_by_engine_id": self.generated_by_engine_id,
            "human_authority_state": self.human_authority_state.value,
            "independently_validated": self.independently_validated,
            "minimum_passing_score": self.minimum_passing_score,
            "missing_required_gate_kinds": [
                kind.value for kind in self.missing_required_gate_kinds
            ],
            "notes": list(self.notes),
            "passed_gate_ids": list(self.passed_gate_ids),
            "passing_score": self.passing_score,
            "permits_automatic_execution": self.permits_automatic_execution,
            "proto_candidate_bundle_id": self.proto_candidate_bundle.bundle_id,
            "readiness_gaps": list(self.readiness_gaps),
            "required_gate_kinds": [kind.value for kind in self.required_gate_kinds],
            "review_summary": self.review_summary,
            "reviewer_role_id": self.reviewer_role_id,
            "scenario_ids": list(self.scenario_ids),
            "schema_version": self.schema_version,
            "scorecard_id": self.scorecard_id,
            "status": self.status.value,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint."""

        return _stable_sha256(self.canonical_payload())

    def _failed_gate_ids_by_severity(
        self, severity: WaveFourScorecardGateSeverity
    ) -> tuple[str, ...]:
        """Return failed gate ids matching a severity."""

        return tuple(
            gate.gate_id
            for gate in self.gates
            if not gate.passed and gate.severity is severity
        )


def build_wave_four_proto_candidate_scorecard(
    *,
    scorecard_id: str,
    proto_candidate_bundle: WaveFourProtoCandidateTrialBundle,
) -> WaveFourProtoCandidateScorecard:
    """Build the standard Wave 4 proto-candidate scorecard."""

    evidence_ids = proto_candidate_bundle.all_evidence_ids
    gates = (
        _gate(
            gate_id="gate:protocol-status",
            gate_kind=WaveFourScorecardGateKind.PROTOCOL_STATUS,
            severity=_protocol_status_severity(proto_candidate_bundle),
            passed=proto_candidate_bundle.trial_protocol.status
            is WaveFourTrialStatus.READY_FOR_CONTROLLED_REVIEW,
            summary="Controlled trial protocol is ready for review.",
            evidence_ids=evidence_ids,
            failure_summary="; ".join(
                proto_candidate_bundle.trial_protocol.readiness_gaps
            ),
        ),
        _gate(
            gate_id="gate:task-coverage",
            gate_kind=WaveFourScorecardGateKind.TASK_COVERAGE,
            severity=WaveFourScorecardGateSeverity.EVIDENCE,
            passed=not proto_candidate_bundle.missing_required_task_kinds,
            summary="All required Wave 4 controlled task kinds are present.",
            evidence_ids=evidence_ids,
            failure_summary=_missing_enum_summary(
                "missing task kinds",
                proto_candidate_bundle.missing_required_task_kinds,
            ),
        ),
        _gate(
            gate_id="gate:artifact-coverage",
            gate_kind=WaveFourScorecardGateKind.ARTIFACT_COVERAGE,
            severity=WaveFourScorecardGateSeverity.EVIDENCE,
            passed=not proto_candidate_bundle.missing_required_artifact_kinds,
            summary="All required Wave 4 artifact kinds are present.",
            evidence_ids=evidence_ids,
            failure_summary=_missing_enum_summary(
                "missing artifact kinds",
                proto_candidate_bundle.missing_required_artifact_kinds,
            ),
        ),
        _gate(
            gate_id="gate:capability-coverage",
            gate_kind=WaveFourScorecardGateKind.CAPABILITY_COVERAGE,
            severity=WaveFourScorecardGateSeverity.EVIDENCE,
            passed=not proto_candidate_bundle.missing_required_capability_areas,
            summary="All required Wave 4 capability areas are represented.",
            evidence_ids=evidence_ids,
            failure_summary=_missing_enum_summary(
                "missing capability areas",
                proto_candidate_bundle.missing_required_capability_areas,
            ),
        ),
        _gate(
            gate_id="gate:artifact-readiness",
            gate_kind=WaveFourScorecardGateKind.ARTIFACT_READINESS,
            severity=_artifact_readiness_severity(proto_candidate_bundle),
            passed=not proto_candidate_bundle.not_ready_artifact_ids,
            summary="All artifact refs are ready for controlled human review.",
            evidence_ids=evidence_ids,
            failure_summary=_missing_text_summary(
                "not-ready artifact ids",
                proto_candidate_bundle.not_ready_artifact_ids,
            ),
        ),
        _gate(
            gate_id="gate:evidence-binding",
            gate_kind=WaveFourScorecardGateKind.EVIDENCE_BINDING,
            severity=WaveFourScorecardGateSeverity.EVIDENCE,
            passed=_has_task_and_artifact_evidence(proto_candidate_bundle),
            summary="Tasks, artifacts, and evidence links remain evidence-bound.",
            evidence_ids=evidence_ids,
            failure_summary="one or more tasks or artifacts lacks evidence binding",
        ),
        _gate(
            gate_id="gate:scenario-coverage",
            gate_kind=WaveFourScorecardGateKind.SCENARIO_COVERAGE,
            severity=WaveFourScorecardGateSeverity.EVIDENCE,
            passed=_has_scenario_coverage(proto_candidate_bundle),
            summary="WorldTwin-style scenario coverage remains attached.",
            evidence_ids=evidence_ids,
            failure_summary="bundle or non-baseline tasks lack scenario ids",
        ),
        _gate(
            gate_id="gate:blackfox-receipt-coverage",
            gate_kind=WaveFourScorecardGateKind.BLACKFOX_RECEIPT_COVERAGE,
            severity=WaveFourScorecardGateSeverity.EVIDENCE,
            passed=_has_blackfox_receipt_coverage(proto_candidate_bundle),
            summary="BlackFox-style review receipts remain attached.",
            evidence_ids=evidence_ids,
            failure_summary="bundle or tasks lack BlackFox receipt ids",
        ),
        _gate(
            gate_id="gate:human-authority-preserved",
            gate_kind=WaveFourScorecardGateKind.HUMAN_AUTHORITY_PRESERVED,
            severity=WaveFourScorecardGateSeverity.BLOCKING,
            passed=_has_human_authority_preserved(proto_candidate_bundle),
            summary="Human authority remains required across bundle artifacts.",
            evidence_ids=evidence_ids,
            failure_summary="human authority is missing, blocked, or bypassed",
        ),
        _gate(
            gate_id="gate:anti-overclaim-boundary",
            gate_kind=WaveFourScorecardGateKind.ANTI_OVERCLAIM_BOUNDARY,
            severity=WaveFourScorecardGateSeverity.BLOCKING,
            passed=_has_no_agi_or_independent_validation_claim(proto_candidate_bundle),
            summary="Bundle does not claim AGI or independent validation.",
            evidence_ids=evidence_ids,
            failure_summary="AGI or independent-validation boundary was violated",
        ),
        _gate(
            gate_id="gate:no-automatic-execution",
            gate_kind=WaveFourScorecardGateKind.NO_AUTOMATIC_EXECUTION,
            severity=WaveFourScorecardGateSeverity.BLOCKING,
            passed=_has_no_automatic_execution(proto_candidate_bundle),
            summary="No task, artifact, or bundle allows automatic execution.",
            evidence_ids=evidence_ids,
            failure_summary="automatic execution authority was detected",
        ),
    )
    return WaveFourProtoCandidateScorecard(
        scorecard_id=scorecard_id,
        proto_candidate_bundle=proto_candidate_bundle,
        gates=gates,
        scenario_ids=proto_candidate_bundle.scenario_ids,
        blackfox_receipt_ids=proto_candidate_bundle.blackfox_receipt_ids,
    )


def _gate(
    *,
    gate_id: str,
    gate_kind: WaveFourScorecardGateKind,
    severity: WaveFourScorecardGateSeverity,
    passed: bool,
    summary: str,
    evidence_ids: tuple[str, ...],
    failure_summary: str,
) -> WaveFourScorecardGate:
    """Build a scorecard gate while adding failure text only when needed."""

    return WaveFourScorecardGate(
        gate_id=gate_id,
        gate_kind=gate_kind,
        severity=severity,
        passed=passed,
        summary=summary,
        evidence_ids=evidence_ids,
        failure_summary="" if passed else failure_summary,
    )


def _protocol_status_severity(
    bundle: WaveFourProtoCandidateTrialBundle,
) -> WaveFourScorecardGateSeverity:
    """Return protocol gate severity from current protocol state."""

    if bundle.trial_protocol.status is WaveFourTrialStatus.BLOCKED:
        return WaveFourScorecardGateSeverity.BLOCKING
    if bundle.trial_protocol.status is WaveFourTrialStatus.NEEDS_REPAIR:
        return WaveFourScorecardGateSeverity.REPAIR
    return WaveFourScorecardGateSeverity.EVIDENCE


def _artifact_readiness_severity(
    bundle: WaveFourProtoCandidateTrialBundle,
) -> WaveFourScorecardGateSeverity:
    """Return artifact-readiness severity from blocked artifacts."""

    if bundle.blocked_artifact_ids:
        return WaveFourScorecardGateSeverity.BLOCKING
    return WaveFourScorecardGateSeverity.EVIDENCE


def _has_task_and_artifact_evidence(bundle: WaveFourProtoCandidateTrialBundle) -> bool:
    """Return whether tasks, artifacts, and links retain evidence ids."""

    if not bundle.all_evidence_ids:
        return False
    return all(task.all_evidence_ids for task in bundle.controlled_tasks) and all(
        artifact.evidence_ids for artifact in bundle.artifact_refs
    )


def _has_scenario_coverage(bundle: WaveFourProtoCandidateTrialBundle) -> bool:
    """Return whether the bundle and scenario-requiring tasks have scenario ids."""

    if not bundle.scenario_ids:
        return False
    return all(
        task.scenario_ids or task.task_kind.value == "baseline-capability"
        for task in bundle.controlled_tasks
    )


def _has_blackfox_receipt_coverage(bundle: WaveFourProtoCandidateTrialBundle) -> bool:
    """Return whether the bundle and all controlled tasks carry receipts."""

    if not bundle.blackfox_receipt_ids:
        return False
    return all(task.blackfox_receipt_ids for task in bundle.controlled_tasks)


def _has_human_authority_preserved(
    bundle: WaveFourProtoCandidateTrialBundle,
) -> bool:
    """Return whether human authority remains visible and required."""

    return (
        bundle.human_authority_state is WaveFourAuthorityState.HUMAN_REVIEW_REQUIRED
        and all(artifact.requires_human_authority for artifact in bundle.artifact_refs)
        and all(
            artifact.authority_state
            in {
                WaveFourAuthorityState.HUMAN_REVIEW_REQUIRED,
                WaveFourAuthorityState.HUMAN_AUTHORITY_GRANTED,
            }
            for artifact in bundle.artifact_refs
        )
    )


def _has_no_agi_or_independent_validation_claim(
    bundle: WaveFourProtoCandidateTrialBundle,
) -> bool:
    """Return whether AGI and Wave 5 validation boundaries are preserved."""

    return (
        not bundle.claims_agi
        and not bundle.independently_validated
        and all(not artifact.claims_agi for artifact in bundle.artifact_refs)
        and all(
            not artifact.independently_validated for artifact in bundle.artifact_refs
        )
    )


def _has_no_automatic_execution(bundle: WaveFourProtoCandidateTrialBundle) -> bool:
    """Return whether no component grants automatic execution authority."""

    return (
        not bundle.permits_automatic_execution
        and all(
            not task.permits_automatic_execution for task in bundle.controlled_tasks
        )
        and all(
            not artifact.allowed_for_automatic_execution
            for artifact in bundle.artifact_refs
        )
    )


def _missing_enum_summary(label: str, values: Iterable[StrEnum]) -> str:
    """Return a missing-enum failure summary."""

    missing = tuple(value.value for value in values)
    if not missing:
        return ""
    return f"{label}: " + ", ".join(missing)


def _missing_text_summary(label: str, values: Iterable[str]) -> str:
    """Return a missing-text failure summary."""

    missing = tuple(values)
    if not missing:
        return ""
    return f"{label}: " + ", ".join(missing)


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
