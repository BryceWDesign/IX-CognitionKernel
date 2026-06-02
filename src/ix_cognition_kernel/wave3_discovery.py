"""Wave 3 evaluator-driven discovery records for IX-CognitionKernel.

Wave 3 discovery may propose new hypotheses, causal edges, plan repairs, memory
candidates, or skill candidates, but it may not mutate belief state, memory, or
the skill genome by itself. Every discovery record is gated by evaluator evidence
and remains a human-review artifact only.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, TypeVar

from ix_cognition_kernel.evaluation import (
    EvaluationLedger,
    EvaluationRecord,
    EvaluationStatus,
)
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
E = TypeVar("E", bound=StrEnum)

WAVE_THREE_DISCOVERY_CANDIDATE_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave3-discovery-candidate-v1"
)
WAVE_THREE_DISCOVERY_RECORD_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave3-discovery-record-v1"
)
WAVE_THREE_DISCOVERY_BUNDLE_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave3-discovery-bundle-v1"
)

EVALUATOR_ROLE_IDS: frozenset[str] = frozenset(
    {
        "verifier",
        "skeptic-red-team",
        "learning-archivist",
        "memory-quarantine-officer",
    }
)


class DiscoveryCandidateKind(StrEnum):
    """Kinds of discovery candidates allowed in Wave 3."""

    HYPOTHESIS = "hypothesis"
    CAUSAL_EDGE = "causal-edge"
    PLAN_REPAIR = "plan-repair"
    MEMORY_CANDIDATE = "memory-candidate"
    SKILL_CANDIDATE = "skill-candidate"


class DiscoveryUpdateTarget(StrEnum):
    """State areas a discovery may request to update after review."""

    BELIEF_STATE = "belief-state"
    CAUSAL_MODEL = "causal-model"
    PLAN_GRAPH = "plan-graph"
    MEMORY_QUARANTINE = "memory-quarantine"
    SKILL_GENOME = "skill-genome"


class DiscoveryRecordStatus(StrEnum):
    """Fail-closed status for an evaluator-driven discovery record."""

    READY_FOR_HUMAN_REVIEW = "ready-for-human-review"
    NEEDS_EVALUATION = "needs-evaluation"
    NEEDS_REPAIR = "needs-repair"
    BLOCKED = "blocked"


_REQUIRED_TARGET_BY_KIND: Mapping[DiscoveryCandidateKind, DiscoveryUpdateTarget] = {
    DiscoveryCandidateKind.HYPOTHESIS: DiscoveryUpdateTarget.BELIEF_STATE,
    DiscoveryCandidateKind.CAUSAL_EDGE: DiscoveryUpdateTarget.CAUSAL_MODEL,
    DiscoveryCandidateKind.PLAN_REPAIR: DiscoveryUpdateTarget.PLAN_GRAPH,
    DiscoveryCandidateKind.MEMORY_CANDIDATE: DiscoveryUpdateTarget.MEMORY_QUARANTINE,
    DiscoveryCandidateKind.SKILL_CANDIDATE: DiscoveryUpdateTarget.SKILL_GENOME,
}


@dataclass(frozen=True, slots=True)
class DiscoveryCandidate:
    """A bounded discovery candidate before evaluator acceptance."""

    candidate_id: str
    candidate_kind: DiscoveryCandidateKind
    summary: str
    source_artifact_ids: tuple[str, ...]
    proposed_update_targets: tuple[DiscoveryUpdateTarget, ...]
    novelty_claim: str
    risk_notes: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    generated_by_engine_id: str = "evaluator-driven-discovery"
    schema_version: str = WAVE_THREE_DISCOVERY_CANDIDATE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate discovery candidate provenance, target, risk, and evidence."""

        object.__setattr__(
            self, "candidate_id", _text(self.candidate_id, "candidate_id")
        )
        object.__setattr__(self, "summary", _text(self.summary, "candidate summary"))
        object.__setattr__(
            self,
            "source_artifact_ids",
            _unique_text(self.source_artifact_ids, label="source artifact_id"),
        )
        if not self.source_artifact_ids:
            raise ValueError("Discovery candidates require source artifact ids.")
        object.__setattr__(
            self,
            "proposed_update_targets",
            _unique_enum(self.proposed_update_targets, label="proposed update target"),
        )
        if not self.proposed_update_targets:
            raise ValueError("Discovery candidates require proposed update targets.")
        object.__setattr__(
            self, "novelty_claim", _text(self.novelty_claim, "novelty_claim")
        )
        object.__setattr__(
            self, "risk_notes", _unique_text(self.risk_notes, label="risk note")
        )
        if not self.risk_notes:
            raise ValueError("Discovery candidates require risk notes.")
        object.__setattr__(
            self,
            "evidence_ids",
            _unique_text(self.evidence_ids, label="candidate evidence_id"),
        )
        object.__setattr__(
            self,
            "generated_by_engine_id",
            _text(self.generated_by_engine_id, "generated_by_engine_id"),
        )
        if self.generated_by_engine_id != "evaluator-driven-discovery":
            raise ValueError(
                "Discovery candidates must be generated by evaluator-driven-discovery."
            )
        object.__setattr__(
            self, "schema_version", _text(self.schema_version, "schema_version")
        )
        required_target = _REQUIRED_TARGET_BY_KIND[self.candidate_kind]
        if required_target not in self.proposed_update_targets:
            raise ValueError(
                "Discovery candidate kind requires matching update target: "
                f"{required_target.value}"
            )

    @property
    def artifact_id(self) -> str:
        """Return the shared Wave 3 artifact id for this candidate."""

        return f"discovery-candidate:{self.candidate_id}"

    @property
    def touches_belief_or_skill_state(self) -> bool:
        """Return whether this candidate targets belief or skill state."""

        return bool(
            {
                DiscoveryUpdateTarget.BELIEF_STATE,
                DiscoveryUpdateTarget.SKILL_GENOME,
            }.intersection(self.proposed_update_targets)
        )

    def canonical_payload(self) -> dict[str, Any]:
        """Return a deterministic payload for hashing and export."""

        return {
            "artifact_id": self.artifact_id,
            "candidate_id": self.candidate_id,
            "candidate_kind": self.candidate_kind.value,
            "evidence_ids": list(self.evidence_ids),
            "generated_by_engine_id": self.generated_by_engine_id,
            "novelty_claim": self.novelty_claim,
            "proposed_update_targets": [
                target.value for target in self.proposed_update_targets
            ],
            "risk_notes": list(self.risk_notes),
            "schema_version": self.schema_version,
            "source_artifact_ids": list(self.source_artifact_ids),
            "summary": self.summary,
            "touches_belief_or_skill_state": self.touches_belief_or_skill_state,
        }

    def fingerprint(self) -> str:
        """Return a deterministic SHA-256 fingerprint for this candidate."""

        return _stable_sha256(self.canonical_payload())


@dataclass(frozen=True, slots=True)
class DiscoveryRecord:
    """Evaluator-gated Wave 3 discovery record."""

    discovery_id: str
    candidate: DiscoveryCandidate
    evaluation_ledger: EvaluationLedger
    required_evaluation_ids: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    reviewer_role_id: str = "verifier"
    blocked_reasons: tuple[str, ...] = ()
    schema_version: str = WAVE_THREE_DISCOVERY_RECORD_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate evaluator evidence and fail-closed update gating."""

        object.__setattr__(
            self, "discovery_id", _text(self.discovery_id, "discovery_id")
        )
        object.__setattr__(
            self,
            "required_evaluation_ids",
            _unique_text(self.required_evaluation_ids, label="required evaluation_id"),
        )
        if not self.required_evaluation_ids:
            raise ValueError("Discovery records require evaluator evidence ids.")
        object.__setattr__(
            self,
            "evidence_ids",
            _unique_text(self.evidence_ids, label="discovery evidence_id"),
        )
        object.__setattr__(
            self, "reviewer_role_id", _text(self.reviewer_role_id, "reviewer_role_id")
        )
        if self.reviewer_role_id not in EVALUATOR_ROLE_IDS:
            raise ValueError("Discovery records require an evaluator reviewer role.")
        object.__setattr__(
            self,
            "blocked_reasons",
            _unique_text(self.blocked_reasons, label="blocked reason"),
        )
        object.__setattr__(
            self, "schema_version", _text(self.schema_version, "schema_version")
        )
        _validate_required_evaluations_exist(
            self.evaluation_ledger, self.required_evaluation_ids
        )
        _validate_evaluations(self.required_evaluations, self.candidate.artifact_id)
        if self.blocked_reasons and not self.blocked_evaluation_ids:
            raise ValueError(
                "Discovery records may carry blocked reasons only with a blocked "
                "evaluation."
            )

    @property
    def artifact_id(self) -> str:
        """Return the shared Wave 3 artifact id for this discovery record."""

        return f"discovery-record:{self.discovery_id}"

    @property
    def required_evaluations(self) -> tuple[EvaluationRecord, ...]:
        """Return required evaluation records in requested order."""

        return tuple(
            self.evaluation_ledger.record_by_id(evaluation_id)
            for evaluation_id in self.required_evaluation_ids
        )

    @property
    def evaluation_evidence_ids(self) -> tuple[str, ...]:
        """Return sorted unique evidence ids from required evaluations."""

        return tuple(
            sorted(
                evidence_id
                for evaluation in self.required_evaluations
                for evidence_id in evaluation.evidence_ids
            )
        )

    @property
    def all_evidence_ids(self) -> tuple[str, ...]:
        """Return sorted unique candidate, record, and evaluator evidence ids."""

        return tuple(
            sorted(
                set(self.candidate.evidence_ids).union(
                    self.evidence_ids, self.evaluation_evidence_ids
                )
            )
        )

    @property
    def passing_evaluation_ids(self) -> tuple[str, ...]:
        """Return required evaluator records that passed."""

        return tuple(
            evaluation.evaluation_id
            for evaluation in self.required_evaluations
            if evaluation.status is EvaluationStatus.PASSED
        )

    @property
    def failed_evaluation_ids(self) -> tuple[str, ...]:
        """Return required evaluator records that failed."""

        return tuple(
            evaluation.evaluation_id
            for evaluation in self.required_evaluations
            if evaluation.status is EvaluationStatus.FAILED
        )

    @property
    def blocked_evaluation_ids(self) -> tuple[str, ...]:
        """Return required evaluator records that are blocked."""

        return tuple(
            evaluation.evaluation_id
            for evaluation in self.required_evaluations
            if evaluation.status is EvaluationStatus.BLOCKED
        )

    @property
    def needs_evidence_evaluation_ids(self) -> tuple[str, ...]:
        """Return required evaluations that need evidence or have not run."""

        return tuple(
            evaluation.evaluation_id
            for evaluation in self.required_evaluations
            if evaluation.status
            in {EvaluationStatus.NEEDS_EVIDENCE, EvaluationStatus.NOT_RUN}
        )

    @property
    def has_required_evaluator_evidence(self) -> bool:
        """Return whether all required evaluations passed with evidence."""

        return bool(self.required_evaluations) and all(
            evaluation.is_passing and bool(evaluation.evidence_ids)
            for evaluation in self.required_evaluations
        )

    @property
    def may_request_belief_or_skill_update(self) -> bool:
        """Return whether this record may request later state-update review."""

        return (
            self.ready_for_human_review and self.candidate.touches_belief_or_skill_state
        )

    @property
    def permits_automatic_state_update(self) -> bool:
        """Return whether this record may directly update belief/skill state."""

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
            gaps.append(f"{self.discovery_id} has no top-level evidence ids")
        if self.needs_evidence_evaluation_ids:
            gaps.append(
                "discovery evaluations need evidence: "
                + ", ".join(self.needs_evidence_evaluation_ids)
            )
        if self.failed_evaluation_ids:
            gaps.append(
                "discovery evaluations failed: " + ", ".join(self.failed_evaluation_ids)
            )
        if not self.has_required_evaluator_evidence:
            gaps.append(
                "discovery cannot update belief or skill state without passing "
                "evaluator evidence"
            )
        return tuple(gaps)

    @property
    def blocking_gaps(self) -> tuple[str, ...]:
        """Return blocking gaps that stop discovery progress."""

        gaps: list[str] = []
        if self.blocked_evaluation_ids:
            gaps.append(
                "discovery evaluations blocked: "
                + ", ".join(self.blocked_evaluation_ids)
            )
        gaps.extend(
            f"{self.discovery_id} blocked: {reason}" for reason in self.blocked_reasons
        )
        return tuple(gaps)

    @property
    def status(self) -> DiscoveryRecordStatus:
        """Return the fail-closed discovery record status."""

        if self.blocking_gaps:
            return DiscoveryRecordStatus.BLOCKED
        if self.failed_evaluation_ids:
            return DiscoveryRecordStatus.NEEDS_REPAIR
        if self.readiness_gaps:
            return DiscoveryRecordStatus.NEEDS_EVALUATION
        return DiscoveryRecordStatus.READY_FOR_HUMAN_REVIEW

    @property
    def ready_for_human_review(self) -> bool:
        """Return whether this discovery record may enter human review."""

        return self.status is DiscoveryRecordStatus.READY_FOR_HUMAN_REVIEW

    @property
    def human_authority_state(self) -> WaveThreeAuthorityState:
        """Return aggregate human-authority state for this discovery record."""

        if self.status is DiscoveryRecordStatus.BLOCKED:
            return WaveThreeAuthorityState.BLOCKED
        return WaveThreeAuthorityState.HUMAN_REVIEW_REQUIRED

    @property
    def review_summary(self) -> str:
        """Return a concise human-review summary."""

        return (
            f"{self.discovery_id}: {self.status.value}; "
            f"candidate {self.candidate.candidate_id}; "
            f"{len(self.passing_evaluation_ids)}/{len(self.required_evaluation_ids)} "
            "evaluations passed; automatic state update is not permitted."
        )

    def to_artifact_ref(self) -> WaveThreeArtifactRef:
        """Convert this discovery record into a shared Wave 3 artifact reference."""

        if self.status is DiscoveryRecordStatus.READY_FOR_HUMAN_REVIEW:
            decision = WaveThreeArtifactDecision.READY_FOR_HUMAN_REVIEW
            authority_state = WaveThreeAuthorityState.HUMAN_REVIEW_REQUIRED
        elif self.status is DiscoveryRecordStatus.BLOCKED:
            decision = WaveThreeArtifactDecision.BLOCKED
            authority_state = WaveThreeAuthorityState.BLOCKED
        else:
            decision = WaveThreeArtifactDecision.NEEDS_EVIDENCE
            authority_state = WaveThreeAuthorityState.HUMAN_REVIEW_REQUIRED
        return WaveThreeArtifactRef(
            artifact_id=self.artifact_id,
            kind=WaveThreeArtifactKind.DISCOVERY_RECORD,
            source_system=WaveThreeSourceSystem.IX_COGNITION_KERNEL,
            summary=self.review_summary,
            produced_by_engine_id="evaluator-driven-discovery",
            produced_by_agent_role_id=self.reviewer_role_id,
            evidence_ids=self.all_evidence_ids,
            decision=decision,
            authority_state=authority_state,
        )

    def to_artifact_bundle(self, *, artifact_bundle_id: str) -> WaveThreeArtifactBundle:
        """Convert this discovery record into a shared Wave 3 artifact bundle."""

        artifact = self.to_artifact_ref()
        return WaveThreeArtifactBundle(
            bundle_id=artifact_bundle_id,
            artifacts=(artifact,),
            evidence_links=_evidence_links_for_artifacts((artifact,)),
            required_kinds=(WaveThreeArtifactKind.DISCOVERY_RECORD,),
            notes=("Discovery records request review; they do not mutate state.",),
        )

    def canonical_payload(self) -> dict[str, Any]:
        """Return a deterministic payload for hashing and export."""

        return {
            "all_evidence_ids": list(self.all_evidence_ids),
            "artifact_id": self.artifact_id,
            "blocked_reasons": list(self.blocked_reasons),
            "blocking_gaps": list(self.blocking_gaps),
            "candidate": self.candidate.canonical_payload(),
            "discovery_id": self.discovery_id,
            "human_authority_state": self.human_authority_state.value,
            "may_request_belief_or_skill_update": (
                self.may_request_belief_or_skill_update
            ),
            "permits_automatic_execution": self.permits_automatic_execution,
            "permits_automatic_state_update": self.permits_automatic_state_update,
            "readiness_gaps": list(self.readiness_gaps),
            "required_evaluation_ids": list(self.required_evaluation_ids),
            "review_summary": self.review_summary,
            "reviewer_role_id": self.reviewer_role_id,
            "schema_version": self.schema_version,
            "status": self.status.value,
        }

    def fingerprint(self) -> str:
        """Return a deterministic SHA-256 fingerprint for this discovery record."""

        return _stable_sha256(self.canonical_payload())


@dataclass(frozen=True, slots=True)
class DiscoveryRecordBundle:
    """Deterministic bundle of evaluator-driven discovery records."""

    bundle_id: str
    records: tuple[DiscoveryRecord, ...]
    notes: tuple[str, ...] = ()
    schema_version: str = WAVE_THREE_DISCOVERY_BUNDLE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate discovery record uniqueness and bundle reviewability."""

        object.__setattr__(self, "bundle_id", _text(self.bundle_id, "bundle_id"))
        if not self.records:
            raise ValueError("Discovery record bundles require at least one record.")
        records = tuple(sorted(self.records, key=lambda record: record.discovery_id))
        _unique_values(
            (record.discovery_id for record in records), label="discovery_id"
        )
        _unique_values(
            (record.candidate.candidate_id for record in records), label="candidate_id"
        )
        object.__setattr__(self, "records", records)
        object.__setattr__(
            self, "notes", _unique_text(self.notes, label="discovery bundle note")
        )
        object.__setattr__(
            self, "schema_version", _text(self.schema_version, "schema_version")
        )

    @property
    def record_ids(self) -> tuple[str, ...]:
        """Return discovery ids in deterministic order."""

        return tuple(record.discovery_id for record in self.records)

    @property
    def ready_record_ids(self) -> tuple[str, ...]:
        """Return records ready for human review."""

        return tuple(
            record.discovery_id
            for record in self.records
            if record.ready_for_human_review
        )

    @property
    def blocked_record_ids(self) -> tuple[str, ...]:
        """Return blocked discovery records."""

        return tuple(
            record.discovery_id
            for record in self.records
            if record.status is DiscoveryRecordStatus.BLOCKED
        )

    @property
    def readiness_gaps(self) -> tuple[str, ...]:
        """Return bundle-level and record-level readiness gaps."""

        gaps: list[str] = []
        for record in self.records:
            gaps.extend(record.readiness_gaps)
            gaps.extend(record.blocking_gaps)
        return tuple(gaps)

    @property
    def is_complete_for_human_review(self) -> bool:
        """Return whether every discovery record is review-ready."""

        return not self.readiness_gaps and len(self.ready_record_ids) == len(
            self.records
        )

    def record_by_id(self, discovery_id: str) -> DiscoveryRecord:
        """Return one discovery record by id."""

        normalized = _text(discovery_id, "discovery_id")
        for record in self.records:
            if record.discovery_id == normalized:
                return record
        raise ValueError(f"Unknown discovery_id: {discovery_id}")

    def to_artifact_bundle(self, *, artifact_bundle_id: str) -> WaveThreeArtifactBundle:
        """Convert discovery records into a shared Wave 3 artifact bundle."""

        artifacts = tuple(record.to_artifact_ref() for record in self.records)
        return WaveThreeArtifactBundle(
            bundle_id=artifact_bundle_id,
            artifacts=artifacts,
            evidence_links=_evidence_links_for_artifacts(artifacts),
            required_kinds=(WaveThreeArtifactKind.DISCOVERY_RECORD,),
            notes=(
                "Discovery bundle artifacts are review-only state-update requests.",
            ),
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


def _validate_required_evaluations_exist(
    evaluation_ledger: EvaluationLedger, required_evaluation_ids: tuple[str, ...]
) -> None:
    """Reject missing required evaluations early."""

    for evaluation_id in required_evaluation_ids:
        evaluation_ledger.record_by_id(evaluation_id)


def _validate_evaluations(
    evaluations: tuple[EvaluationRecord, ...], candidate_artifact_id: str
) -> None:
    """Reject evaluator records that do not cover the candidate or role boundary."""

    for evaluation in evaluations:
        if not evaluation.covers_artifact(candidate_artifact_id):
            raise ValueError(
                "Discovery evaluations must cover the discovery candidate artifact: "
                f"{evaluation.evaluation_id}"
            )
        if evaluation.evaluator_role_id not in EVALUATOR_ROLE_IDS:
            raise ValueError(
                "Discovery evaluations require evaluator roles: "
                f"{evaluation.evaluation_id}"
            )


def _evidence_links_for_artifacts(
    artifacts: tuple[WaveThreeArtifactRef, ...],
) -> tuple[WaveThreeEvidenceLink, ...]:
    """Create deterministic evidence links for discovery artifacts."""

    return tuple(
        WaveThreeEvidenceLink(
            evidence_id=evidence_id,
            artifact_id=artifact.artifact_id,
            relation=WaveThreeEvidenceRelation.TESTS,
            summary=(
                "Discovery evaluator evidence gates candidate update requests "
                "without automatic state mutation."
            ),
            source_system=WaveThreeSourceSystem.LOCAL_TEST_SUITE,
        )
        for artifact in artifacts
        for evidence_id in artifact.evidence_ids
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
