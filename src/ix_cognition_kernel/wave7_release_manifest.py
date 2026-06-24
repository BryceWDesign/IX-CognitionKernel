"""Wave 7 release manifest.

The release manifest binds the Wave 7 cognitive organism substrate into one
reviewable package. It collects architecture, identity, continuity, body
contract, capability, observation-action, experience, prediction lifecycle,
skill genome, goal pressure, runtime airlock, manipulation pressure,
self-revision, and organism scorecard evidence into a deterministic release
record.

The manifest is not a marketing claim. It is a replayable boundary object that
shows what exists, what was evaluated, what remains blocked, what needs human
review, and what must not be claimed.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from ix_cognition_kernel.wave7_organism_scorecard import (
    OrganismEvaluationSummary,
    OrganismScorecard,
)

WAVE_SEVEN_RELEASE_ARTIFACT_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave7-release-artifact-v1"
)
WAVE_SEVEN_RELEASE_GATE_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave7-release-gate-v1"
)
WAVE_SEVEN_RELEASE_MANIFEST_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave7-release-manifest-v1"
)
WAVE_SEVEN_RELEASE_REVIEW_PACKET_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave7-release-review-packet-v1"
)


class Wave7ReleaseArtifactKind(StrEnum):
    """Kinds of release artifacts expected in the Wave 7 manifest."""

    ARCHITECTURE_NOTE = "architecture-note"
    IDENTITY_MODEL = "identity-model"
    CONTINUITY_LEDGER = "continuity-ledger"
    BODY_CONTRACT = "body-contract"
    CAPABILITY_SURFACE = "capability-surface"
    OBSERVATION_ACTION_TRACE = "observation-action-trace"
    EXPERIENCE_COMPILER = "experience-compiler"
    PREDICTION_OUTCOME_LIFECYCLE = "prediction-outcome-lifecycle"
    SKILL_GENOME = "skill-genome"
    GOAL_PRESSURE = "goal-pressure"
    RUNTIME_AIRLOCK = "runtime-airlock"
    MANIPULATION_PRESSURE = "manipulation-pressure"
    SELF_REVISION = "self-revision"
    ORGANISM_SCORECARD = "organism-scorecard"
    RELEASE_MANIFEST = "release-manifest"


class Wave7ReleaseGateStatus(StrEnum):
    """Status for a Wave 7 release gate."""

    NOT_EVALUATED = "not-evaluated"
    SATISFIED = "satisfied"
    NEEDS_MORE_EVIDENCE = "needs-more-evidence"
    READY_FOR_HUMAN_REVIEW = "ready-for-human-review"
    BLOCKED = "blocked"


class Wave7ReleaseDecision(StrEnum):
    """Fail-closed Wave 7 release manifest decision."""

    RECORD_ONLY = "record-only"
    READY_FOR_HUMAN_REVIEW = "ready-for-human-review"
    NEEDS_MORE_EVIDENCE = "needs-more-evidence"
    BLOCKED = "blocked"


REQUIRED_WAVE7_ARTIFACT_KINDS: tuple[Wave7ReleaseArtifactKind, ...] = tuple(
    kind for kind in Wave7ReleaseArtifactKind
)


@dataclass(frozen=True, slots=True)
class Wave7ReleaseArtifact:
    """One evidence-bound artifact in the Wave 7 release manifest."""

    artifact_id: str
    kind: Wave7ReleaseArtifactKind
    path: str
    summary: str
    evidence_ids: tuple[str, ...]
    fingerprint_ref: str
    schema_version: str = WAVE_SEVEN_RELEASE_ARTIFACT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate release artifact metadata."""

        object.__setattr__(
            self,
            "artifact_id",
            _require_non_empty(self.artifact_id, "artifact_id"),
        )
        object.__setattr__(self, "path", _require_non_empty(self.path, "path"))
        object.__setattr__(
            self,
            "summary",
            _require_non_empty(self.summary, "summary"),
        )
        object.__setattr__(
            self,
            "evidence_ids",
            _normalize_unique_text_tuple(self.evidence_ids, label="evidence_id"),
        )
        object.__setattr__(
            self,
            "fingerprint_ref",
            _require_non_empty(self.fingerprint_ref, "fingerprint_ref"),
        )
        object.__setattr__(
            self,
            "schema_version",
            _require_non_empty(self.schema_version, "schema_version"),
        )
        if not self.evidence_ids:
            raise ValueError("Wave 7 release artifacts require evidence ids.")
        if len(self.fingerprint_ref) < 12:
            raise ValueError("Wave 7 release artifact fingerprint_ref is too short.")

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic release-artifact payload."""

        return {
            "artifact_id": self.artifact_id,
            "evidence_ids": list(self.evidence_ids),
            "fingerprint_ref": self.fingerprint_ref,
            "kind": self.kind.value,
            "path": self.path,
            "schema_version": self.schema_version,
            "summary": self.summary,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this artifact."""

        return _stable_sha256(self.canonical_payload())


@dataclass(frozen=True, slots=True)
class Wave7ReleaseGate:
    """Release gate that must be satisfied, reviewed, or blocked explicitly."""

    gate_id: str
    status: Wave7ReleaseGateStatus
    summary: str
    required_artifact_kinds: tuple[Wave7ReleaseArtifactKind, ...]
    evidence_ids: tuple[str, ...]
    authority_refs: tuple[str, ...]
    blocker_ids: tuple[str, ...] = ()
    schema_version: str = WAVE_SEVEN_RELEASE_GATE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate release gate status and authority boundary."""

        object.__setattr__(
            self,
            "gate_id",
            _require_non_empty(self.gate_id, "gate_id"),
        )
        object.__setattr__(
            self,
            "summary",
            _require_non_empty(self.summary, "summary"),
        )
        object.__setattr__(
            self,
            "required_artifact_kinds",
            tuple(
                sorted(
                    set(self.required_artifact_kinds),
                    key=lambda artifact_kind: artifact_kind.value,
                )
            ),
        )
        object.__setattr__(
            self,
            "evidence_ids",
            _normalize_unique_text_tuple(self.evidence_ids, label="evidence_id"),
        )
        object.__setattr__(
            self,
            "authority_refs",
            _normalize_unique_text_tuple(self.authority_refs, label="authority_ref"),
        )
        object.__setattr__(
            self,
            "blocker_ids",
            _normalize_unique_text_tuple(self.blocker_ids, label="blocker_id"),
        )
        object.__setattr__(
            self,
            "schema_version",
            _require_non_empty(self.schema_version, "schema_version"),
        )
        if not self.required_artifact_kinds:
            raise ValueError("Wave 7 release gates require artifact kinds.")
        if self.status is not Wave7ReleaseGateStatus.NOT_EVALUATED:
            if not self.evidence_ids:
                raise ValueError("Evaluated Wave 7 release gates require evidence.")
            if not self.authority_refs:
                raise ValueError("Evaluated Wave 7 release gates require authority.")
        if self.status is Wave7ReleaseGateStatus.BLOCKED and not self.blocker_ids:
            raise ValueError("Blocked Wave 7 release gates require blocker ids.")
        if self.status is not Wave7ReleaseGateStatus.BLOCKED and self.blocker_ids:
            raise ValueError("Only blocked Wave 7 release gates may list blockers.")

    @property
    def satisfied_or_reviewable(self) -> bool:
        """Return whether this gate is satisfied or ready for human review."""

        return self.status in {
            Wave7ReleaseGateStatus.SATISFIED,
            Wave7ReleaseGateStatus.READY_FOR_HUMAN_REVIEW,
        }

    @property
    def needs_more_evidence(self) -> bool:
        """Return whether this gate needs more evidence."""

        return self.status in {
            Wave7ReleaseGateStatus.NOT_EVALUATED,
            Wave7ReleaseGateStatus.NEEDS_MORE_EVIDENCE,
        }

    @property
    def blocks_release(self) -> bool:
        """Return whether this gate blocks the release manifest."""

        return self.status is Wave7ReleaseGateStatus.BLOCKED

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic release-gate payload."""

        return {
            "authority_refs": list(self.authority_refs),
            "blocker_ids": list(self.blocker_ids),
            "evidence_ids": list(self.evidence_ids),
            "gate_id": self.gate_id,
            "required_artifact_kinds": [
                artifact_kind.value
                for artifact_kind in self.required_artifact_kinds
            ],
            "schema_version": self.schema_version,
            "status": self.status.value,
            "summary": self.summary,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this gate."""

        return _stable_sha256(self.canonical_payload())


@dataclass(frozen=True, slots=True)
class Wave7ReleaseManifest:
    """Deterministic Wave 7 release manifest for human review."""

    manifest_id: str
    artifacts: tuple[Wave7ReleaseArtifact, ...]
    gates: tuple[Wave7ReleaseGate, ...]
    scorecard: OrganismScorecard
    evaluation_summary: OrganismEvaluationSummary
    decision: Wave7ReleaseDecision
    claim_boundary: str
    authority_refs: tuple[str, ...]
    notes: tuple[str, ...] = ()
    claims_agi: bool = False
    claims_autonomous_authority: bool = False
    schema_version: str = WAVE_SEVEN_RELEASE_MANIFEST_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate manifest completeness and fail-closed release decision."""

        if self.claims_agi:
            raise ValueError("Wave 7 release manifests must not claim AGI.")
        if self.claims_autonomous_authority:
            raise ValueError(
                "Wave 7 release manifests must not claim autonomous authority."
            )
        object.__setattr__(
            self,
            "manifest_id",
            _require_non_empty(self.manifest_id, "manifest_id"),
        )
        object.__setattr__(
            self,
            "artifacts",
            tuple(sorted(self.artifacts, key=lambda artifact: artifact.artifact_id)),
        )
        object.__setattr__(
            self,
            "gates",
            tuple(sorted(self.gates, key=lambda gate: gate.gate_id)),
        )
        object.__setattr__(
            self,
            "claim_boundary",
            _require_non_empty(self.claim_boundary, "claim_boundary"),
        )
        object.__setattr__(
            self,
            "authority_refs",
            _normalize_unique_text_tuple(self.authority_refs, label="authority_ref"),
        )
        object.__setattr__(
            self,
            "notes",
            _normalize_unique_text_tuple(self.notes, label="note"),
        )
        object.__setattr__(
            self,
            "schema_version",
            _require_non_empty(self.schema_version, "schema_version"),
        )
        if not self.artifacts:
            raise ValueError("Wave 7 release manifests require artifacts.")
        if not self.gates:
            raise ValueError("Wave 7 release manifests require gates.")
        if not self.authority_refs:
            raise ValueError("Wave 7 release manifests require authority refs.")
        _ensure_unique(
            (artifact.artifact_id for artifact in self.artifacts),
            label="artifact_id",
        )
        _ensure_unique((gate.gate_id for gate in self.gates), label="gate_id")
        missing = self.missing_artifact_kinds
        if missing:
            raise ValueError(
                "Wave 7 release manifest missing artifacts: "
                + ", ".join(missing)
            )
        if self.evaluation_summary.scorecard.scorecard_id != self.scorecard.scorecard_id:
            raise ValueError("Evaluation summary must reference scorecard.")
        lowered = self.claim_boundary.lower()
        if "agi" in lowered and "not" not in lowered:
            raise ValueError("Wave 7 release claim boundary must not assert AGI.")
        if self.decision is Wave7ReleaseDecision.READY_FOR_HUMAN_REVIEW:
            if self.blocking_gate_ids:
                raise ValueError("Review-ready Wave 7 release cannot have blockers.")
            if self.evidence_gap_gate_ids:
                raise ValueError(
                    "Review-ready Wave 7 release cannot have evidence gaps."
                )
            if not self.scorecard.ready_for_review:
                raise ValueError("Review-ready release requires review-ready scorecard.")
        if self.decision is Wave7ReleaseDecision.NEEDS_MORE_EVIDENCE:
            if not self.evidence_gap_gate_ids:
                raise ValueError("Needs-more-evidence release requires evidence gaps.")
        if self.decision is Wave7ReleaseDecision.BLOCKED:
            if not self.blocking_gate_ids:
                raise ValueError("Blocked Wave 7 release requires blocking gates.")

    @property
    def artifact_ids(self) -> tuple[str, ...]:
        """Return artifact ids in the release manifest."""

        return tuple(artifact.artifact_id for artifact in self.artifacts)

    @property
    def artifact_kinds(self) -> tuple[str, ...]:
        """Return artifact kinds in the release manifest."""

        return tuple(artifact.kind.value for artifact in self.artifacts)

    @property
    def missing_artifact_kinds(self) -> tuple[str, ...]:
        """Return required artifact kinds missing from this manifest."""

        present = {artifact.kind for artifact in self.artifacts}
        return tuple(
            artifact_kind.value
            for artifact_kind in REQUIRED_WAVE7_ARTIFACT_KINDS
            if artifact_kind not in present
        )

    @property
    def gate_ids(self) -> tuple[str, ...]:
        """Return release gate ids."""

        return tuple(gate.gate_id for gate in self.gates)

    @property
    def satisfied_gate_ids(self) -> tuple[str, ...]:
        """Return satisfied or reviewable gate ids."""

        return tuple(
            gate.gate_id for gate in self.gates if gate.satisfied_or_reviewable
        )

    @property
    def evidence_gap_gate_ids(self) -> tuple[str, ...]:
        """Return gates needing more evidence."""

        return tuple(gate.gate_id for gate in self.gates if gate.needs_more_evidence)

    @property
    def blocking_gate_ids(self) -> tuple[str, ...]:
        """Return gates blocking release."""

        return tuple(gate.gate_id for gate in self.gates if gate.blocks_release)

    @property
    def evidence_ids(self) -> tuple[str, ...]:
        """Return all evidence ids bound to this release manifest."""

        evidence: list[str] = list(self.scorecard.evidence_ids)
        evidence.extend(self.evaluation_summary.evidence_ids)
        for artifact in self.artifacts:
            evidence.extend(artifact.evidence_ids)
        for gate in self.gates:
            evidence.extend(gate.evidence_ids)
        return _normalize_unique_text_tuple(evidence, label="evidence_id")

    @property
    def ready_for_human_review(self) -> bool:
        """Return whether release manifest is ready for human review."""

        return (
            self.decision is Wave7ReleaseDecision.READY_FOR_HUMAN_REVIEW
            and self.scorecard.ready_for_review
            and not self.evidence_gap_gate_ids
            and not self.blocking_gate_ids
        )

    @property
    def blocks_claim(self) -> bool:
        """Return whether release manifest blocks stronger Wave 7 claims."""

        return (
            self.decision is Wave7ReleaseDecision.BLOCKED
            or bool(self.blocking_gate_ids)
            or self.scorecard.blocks_claim
        )

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic release-manifest payload."""

        return {
            "artifact_fingerprints": [
                artifact.fingerprint() for artifact in self.artifacts
            ],
            "artifact_ids": list(self.artifact_ids),
            "artifact_kinds": list(self.artifact_kinds),
            "authority_refs": list(self.authority_refs),
            "blocking_gate_ids": list(self.blocking_gate_ids),
            "claim_boundary": self.claim_boundary,
            "claims_agi": self.claims_agi,
            "claims_autonomous_authority": self.claims_autonomous_authority,
            "decision": self.decision.value,
            "evaluation_summary_fingerprint": self.evaluation_summary.fingerprint(),
            "evidence_gap_gate_ids": list(self.evidence_gap_gate_ids),
            "evidence_ids": list(self.evidence_ids),
            "gate_fingerprints": [gate.fingerprint() for gate in self.gates],
            "gate_ids": list(self.gate_ids),
            "manifest_id": self.manifest_id,
            "missing_artifact_kinds": list(self.missing_artifact_kinds),
            "notes": list(self.notes),
            "ready_for_human_review": self.ready_for_human_review,
            "satisfied_gate_ids": list(self.satisfied_gate_ids),
            "schema_version": self.schema_version,
            "scorecard_fingerprint": self.scorecard.fingerprint(),
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this manifest."""

        return _stable_sha256(self.canonical_payload())


@dataclass(frozen=True, slots=True)
class Wave7ReleaseReviewPacket:
    """Final review packet that wraps the Wave 7 release manifest."""

    packet_id: str
    manifest: Wave7ReleaseManifest
    reviewer_instructions: tuple[str, ...]
    evidence_export_ids: tuple[str, ...]
    schema_version: str = WAVE_SEVEN_RELEASE_REVIEW_PACKET_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate release review packet."""

        object.__setattr__(
            self,
            "packet_id",
            _require_non_empty(self.packet_id, "packet_id"),
        )
        object.__setattr__(
            self,
            "reviewer_instructions",
            _normalize_unique_text_tuple(
                self.reviewer_instructions, label="reviewer_instruction"
            ),
        )
        object.__setattr__(
            self,
            "evidence_export_ids",
            _normalize_unique_text_tuple(
                self.evidence_export_ids, label="evidence_export_id"
            ),
        )
        object.__setattr__(
            self,
            "schema_version",
            _require_non_empty(self.schema_version, "schema_version"),
        )
        if not self.reviewer_instructions:
            raise ValueError("Wave 7 release packets require reviewer instructions.")
        if not self.evidence_export_ids:
            raise ValueError("Wave 7 release packets require evidence export ids.")
        if not self.manifest.ready_for_human_review and not self.manifest.blocks_claim:
            raise ValueError(
                "Release packet requires review-ready or explicitly blocked manifest."
            )

    @property
    def evidence_ids(self) -> tuple[str, ...]:
        """Return all manifest evidence ids."""

        return self.manifest.evidence_ids

    @property
    def ready_for_human_review(self) -> bool:
        """Return whether packet is ready for human review."""

        return self.manifest.ready_for_human_review

    @property
    def blocks_claim(self) -> bool:
        """Return whether packet blocks stronger claims."""

        return self.manifest.blocks_claim

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic release-review-packet payload."""

        return {
            "blocks_claim": self.blocks_claim,
            "evidence_export_ids": list(self.evidence_export_ids),
            "evidence_ids": list(self.evidence_ids),
            "manifest_fingerprint": self.manifest.fingerprint(),
            "packet_id": self.packet_id,
            "ready_for_human_review": self.ready_for_human_review,
            "reviewer_instructions": list(self.reviewer_instructions),
            "schema_version": self.schema_version,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this packet."""

        return _stable_sha256(self.canonical_payload())


def build_wave7_release_artifacts(
    *,
    manifest_fingerprint_ref: str,
    scorecard_fingerprint_ref: str,
) -> tuple[Wave7ReleaseArtifact, ...]:
    """Build the canonical Wave 7 release artifact index."""

    artifact_specs = (
        (
            "artifact-architecture-note",
            Wave7ReleaseArtifactKind.ARCHITECTURE_NOTE,
            "docs/wave7_cognitive_organism_substrate.md",
            "Wave 7 cognitive organism substrate architecture note.",
            "wave7-architecture-evidence",
            "wave7-architecture-note",
        ),
        (
            "artifact-identity-model",
            Wave7ReleaseArtifactKind.IDENTITY_MODEL,
            "src/ix_cognition_kernel/wave7_cognitive_identity.py",
            "Persistent cognitive identity and continuity marker model.",
            "wave7-identity-evidence",
            "wave7-identity-model",
        ),
        (
            "artifact-continuity-ledger",
            Wave7ReleaseArtifactKind.CONTINUITY_LEDGER,
            "src/ix_cognition_kernel/wave7_continuity_ledger.py",
            "Continuity ledger for identity, revisions, and weaknesses.",
            "wave7-continuity-evidence",
            "wave7-continuity-ledger",
        ),
        (
            "artifact-body-contract",
            Wave7ReleaseArtifactKind.BODY_CONTRACT,
            "src/ix_cognition_kernel/wave7_body_contract.py",
            "Body contract that separates intent from permission.",
            "wave7-body-contract-evidence",
            "wave7-body-contract",
        ),
        (
            "artifact-capability-surface",
            Wave7ReleaseArtifactKind.CAPABILITY_SURFACE,
            "src/ix_cognition_kernel/wave7_capability_surface.py",
            "Capability surface and permission boundary memory.",
            "wave7-capability-surface-evidence",
            "wave7-capability-surface",
        ),
        (
            "artifact-observation-action-trace",
            Wave7ReleaseArtifactKind.OBSERVATION_ACTION_TRACE,
            "src/ix_cognition_kernel/wave7_observation_action_schema.py",
            "Observation-action trace schema and proposal readiness.",
            "wave7-observation-action-evidence",
            "wave7-observation-action-trace",
        ),
        (
            "artifact-experience-compiler",
            Wave7ReleaseArtifactKind.EXPERIENCE_COMPILER,
            "src/ix_cognition_kernel/wave7_experience_compiler.py",
            "Experience compiler from measured traces into reviewable learning.",
            "wave7-experience-evidence",
            "wave7-experience-compiler",
        ),
        (
            "artifact-prediction-outcome-lifecycle",
            Wave7ReleaseArtifactKind.PREDICTION_OUTCOME_LIFECYCLE,
            "src/ix_cognition_kernel/wave7_prediction_outcome_lifecycle.py",
            "Prediction-outcome-delta lifecycle and review report model.",
            "wave7-prediction-lifecycle-evidence",
            "wave7-prediction-outcome-lifecycle",
        ),
        (
            "artifact-skill-genome",
            Wave7ReleaseArtifactKind.SKILL_GENOME,
            "src/ix_cognition_kernel/wave7_skill_genome.py",
            "Skill genome and capability memory model.",
            "wave7-skill-genome-evidence",
            "wave7-skill-genome",
        ),
        (
            "artifact-goal-pressure",
            Wave7ReleaseArtifactKind.GOAL_PRESSURE,
            "src/ix_cognition_kernel/wave7_goal_pressure.py",
            "Goal pressure engine for bounded long-horizon direction.",
            "wave7-goal-pressure-evidence",
            "wave7-goal-pressure",
        ),
        (
            "artifact-runtime-airlock",
            Wave7ReleaseArtifactKind.RUNTIME_AIRLOCK,
            "src/ix_cognition_kernel/wave7_runtime_airlock.py",
            "Runtime airlock for simulation, review, evidence, and blocking.",
            "wave7-runtime-airlock-evidence",
            "wave7-runtime-airlock",
        ),
        (
            "artifact-manipulation-pressure",
            Wave7ReleaseArtifactKind.MANIPULATION_PRESSURE,
            "src/ix_cognition_kernel/wave7_manipulation_pressure.py",
            "Multi-turn manipulation pressure checks.",
            "wave7-manipulation-pressure-evidence",
            "wave7-manipulation-pressure",
        ),
        (
            "artifact-self-revision",
            Wave7ReleaseArtifactKind.SELF_REVISION,
            "src/ix_cognition_kernel/wave7_self_revision.py",
            "Self-revision proposal model with human authority boundary.",
            "wave7-self-revision-evidence",
            "wave7-self-revision",
        ),
        (
            "artifact-organism-scorecard",
            Wave7ReleaseArtifactKind.ORGANISM_SCORECARD,
            "src/ix_cognition_kernel/wave7_organism_scorecard.py",
            "Organism scorecard and evaluation summary.",
            "wave7-organism-scorecard-evidence",
            scorecard_fingerprint_ref,
        ),
        (
            "artifact-release-manifest",
            Wave7ReleaseArtifactKind.RELEASE_MANIFEST,
            "src/ix_cognition_kernel/wave7_release_manifest.py",
            "Wave 7 release manifest and review packet.",
            "wave7-release-manifest-evidence",
            manifest_fingerprint_ref,
        ),
    )

    return tuple(
        Wave7ReleaseArtifact(
            artifact_id=artifact_id,
            kind=kind,
            path=path,
            summary=summary,
            evidence_ids=(evidence_id,),
            fingerprint_ref=fingerprint_ref,
        )
        for artifact_id, kind, path, summary, evidence_id, fingerprint_ref
        in artifact_specs
    )


def build_wave7_release_gates(
    *,
    status: Wave7ReleaseGateStatus,
    authority_refs: Iterable[str],
) -> tuple[Wave7ReleaseGate, ...]:
    """Build canonical Wave 7 release gates."""

    authority_tuple = tuple(authority_refs)
    return (
        Wave7ReleaseGate(
            gate_id="gate-complete-artifact-coverage",
            status=status,
            summary="All Wave 7 artifact families are present.",
            required_artifact_kinds=REQUIRED_WAVE7_ARTIFACT_KINDS,
            evidence_ids=("wave7-artifact-coverage-evidence",),
            authority_refs=authority_tuple,
        ),
        Wave7ReleaseGate(
            gate_id="gate-human-authority-boundary",
            status=status,
            summary="No Wave 7 layer grants autonomous authority.",
            required_artifact_kinds=(
                Wave7ReleaseArtifactKind.BODY_CONTRACT,
                Wave7ReleaseArtifactKind.RUNTIME_AIRLOCK,
                Wave7ReleaseArtifactKind.SELF_REVISION,
            ),
            evidence_ids=("wave7-human-authority-boundary-evidence",),
            authority_refs=authority_tuple,
        ),
        Wave7ReleaseGate(
            gate_id="gate-evidence-and-replayability",
            status=status,
            summary="Wave 7 evidence, fingerprints, and review packets are replayable.",
            required_artifact_kinds=(
                Wave7ReleaseArtifactKind.CONTINUITY_LEDGER,
                Wave7ReleaseArtifactKind.EXPERIENCE_COMPILER,
                Wave7ReleaseArtifactKind.RELEASE_MANIFEST,
            ),
            evidence_ids=("wave7-replayability-evidence",),
            authority_refs=authority_tuple,
        ),
        Wave7ReleaseGate(
            gate_id="gate-organism-scorecard",
            status=status,
            summary="Wave 7 organism scorecard is available for human review.",
            required_artifact_kinds=(
                Wave7ReleaseArtifactKind.ORGANISM_SCORECARD,
            ),
            evidence_ids=("wave7-scorecard-gate-evidence",),
            authority_refs=authority_tuple,
        ),
    )


def infer_wave7_release_decision(
    *,
    gates: Iterable[Wave7ReleaseGate],
    scorecard: OrganismScorecard,
) -> Wave7ReleaseDecision:
    """Infer a fail-closed Wave 7 release decision."""

    gate_tuple = tuple(gates)
    if any(gate.blocks_release for gate in gate_tuple) or scorecard.blocks_claim:
        return Wave7ReleaseDecision.BLOCKED
    if any(gate.needs_more_evidence for gate in gate_tuple):
        return Wave7ReleaseDecision.NEEDS_MORE_EVIDENCE
    if scorecard.ready_for_review and all(
        gate.satisfied_or_reviewable for gate in gate_tuple
    ):
        return Wave7ReleaseDecision.READY_FOR_HUMAN_REVIEW
    return Wave7ReleaseDecision.RECORD_ONLY


def build_wave7_release_manifest(
    *,
    manifest_id: str,
    artifacts: Iterable[Wave7ReleaseArtifact],
    gates: Iterable[Wave7ReleaseGate],
    scorecard: OrganismScorecard,
    evaluation_summary: OrganismEvaluationSummary,
    claim_boundary: str,
    authority_refs: Iterable[str],
    notes: Iterable[str] = (),
) -> Wave7ReleaseManifest:
    """Build a deterministic Wave 7 release manifest."""

    gate_tuple = tuple(gates)
    return Wave7ReleaseManifest(
        manifest_id=manifest_id,
        artifacts=tuple(artifacts),
        gates=gate_tuple,
        scorecard=scorecard,
        evaluation_summary=evaluation_summary,
        decision=infer_wave7_release_decision(
            gates=gate_tuple,
            scorecard=scorecard,
        ),
        claim_boundary=claim_boundary,
        authority_refs=tuple(authority_refs),
        notes=tuple(notes),
    )


def build_wave7_release_review_packet(
    *,
    packet_id: str,
    manifest: Wave7ReleaseManifest,
    reviewer_instructions: Iterable[str],
    evidence_export_ids: Iterable[str],
) -> Wave7ReleaseReviewPacket:
    """Build a Wave 7 release review packet."""

    return Wave7ReleaseReviewPacket(
        packet_id=packet_id,
        manifest=manifest,
        reviewer_instructions=tuple(reviewer_instructions),
        evidence_export_ids=tuple(evidence_export_ids),
    )


def _require_non_empty(value: str, label: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{label} must not be empty.")
    return normalized


def _normalize_unique_text_tuple(
    values: Iterable[str], *, label: str
) -> tuple[str, ...]:
    normalized: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = _require_non_empty(value, label)
        if text in seen:
            raise ValueError(f"Duplicate {label}: {text}")
        seen.add(text)
        normalized.append(text)
    return tuple(sorted(normalized))


def _ensure_unique(values: Iterable[str], *, label: str) -> None:
    seen: set[str] = set()
    for value in values:
        if value in seen:
            raise ValueError(f"Duplicate {label}: {value}")
        seen.add(value)


def _stable_sha256(payload: Mapping[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return hashlib.sha256(encoded).hexdigest()
