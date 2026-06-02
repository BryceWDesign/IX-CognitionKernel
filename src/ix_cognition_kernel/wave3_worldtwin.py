"""Wave 3 WorldTwin scenario reasoning records for IX-CognitionKernel.

The WorldTwin layer imports the donor-repo discipline into IX-CognitionKernel
without depending on donor package imports. It records bounded scenario questions,
explicit assumptions, expected outcomes, counterfactual branches, uncertainty
exposure, and human-review handoff readiness. A WorldTwin scenario record is a
review artifact only: it never claims complete reality and never authorizes
execution.
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
)

T = TypeVar("T")
E = TypeVar("E", bound=StrEnum)

WAVE_THREE_WORLDTWIN_BOUNDARY_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave3-worldtwin-boundary-v1"
)
WAVE_THREE_WORLDTWIN_ASSUMPTION_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave3-worldtwin-assumption-v1"
)
WAVE_THREE_WORLDTWIN_OUTCOME_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave3-worldtwin-outcome-v1"
)
WAVE_THREE_WORLDTWIN_COUNTERFACTUAL_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave3-worldtwin-counterfactual-v1"
)
WAVE_THREE_WORLDTWIN_SCENARIO_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave3-worldtwin-scenario-v1"
)
WAVE_THREE_WORLDTWIN_BUNDLE_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave3-worldtwin-bundle-v1"
)


class WorldTwinBoundaryKind(StrEnum):
    """Boundary kinds required for a bounded WorldTwin scenario."""

    TEMPORAL = "temporal"
    OPERATIONAL = "operational"
    POLICY = "policy"
    SAFETY = "safety"
    DATA = "data"
    HUMAN_REVIEW = "human-review"


class WorldTwinAssumptionStatus(StrEnum):
    """Lifecycle status for one scenario assumption."""

    ACTIVE = "active"
    DISPUTED = "disputed"
    EXPIRED = "expired"
    UNSUPPORTED = "unsupported"


class WorldTwinImpactLevel(StrEnum):
    """Impact level when an assumption is wrong."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class WorldTwinScenarioStatus(StrEnum):
    """Fail-closed status for a WorldTwin scenario record."""

    READY_FOR_HUMAN_REVIEW = "ready-for-human-review"
    NEEDS_EVIDENCE = "needs-evidence"
    NEEDS_REPAIR = "needs-repair"
    BLOCKED = "blocked"


REQUIRED_WORLDTWIN_BOUNDARY_KINDS: tuple[WorldTwinBoundaryKind, ...] = (
    WorldTwinBoundaryKind.OPERATIONAL,
    WorldTwinBoundaryKind.POLICY,
    WorldTwinBoundaryKind.SAFETY,
    WorldTwinBoundaryKind.DATA,
    WorldTwinBoundaryKind.HUMAN_REVIEW,
)

BLOCKING_ASSUMPTION_IMPACTS: frozenset[WorldTwinImpactLevel] = frozenset(
    {WorldTwinImpactLevel.HIGH, WorldTwinImpactLevel.CRITICAL}
)


@dataclass(frozen=True, slots=True)
class WorldTwinScenarioBoundary:
    """A named boundary limiting what the scenario may claim."""

    boundary_id: str
    kind: WorldTwinBoundaryKind
    description: str
    hard_boundary: bool = True
    schema_version: str = WAVE_THREE_WORLDTWIN_BOUNDARY_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate boundary identity and description."""

        object.__setattr__(self, "boundary_id", _text(self.boundary_id, "boundary_id"))
        object.__setattr__(
            self, "description", _text(self.description, "boundary description")
        )
        object.__setattr__(
            self, "schema_version", _text(self.schema_version, "schema_version")
        )

    @property
    def boundary_key(self) -> tuple[str, str]:
        """Return deterministic uniqueness key for this boundary."""

        return (self.boundary_id, self.kind.value)

    def canonical_payload(self) -> dict[str, Any]:
        """Return a deterministic payload for hashing and export."""

        return {
            "boundary_id": self.boundary_id,
            "description": self.description,
            "hard_boundary": self.hard_boundary,
            "kind": self.kind.value,
            "schema_version": self.schema_version,
        }


@dataclass(frozen=True, slots=True)
class WorldTwinAssumption:
    """An explicit assumption used by a scenario or counterfactual."""

    assumption_id: str
    statement: str
    status: WorldTwinAssumptionStatus
    confidence: float
    impact_if_wrong: WorldTwinImpactLevel
    evidence_ids: tuple[str, ...]
    required_evidence: tuple[str, ...]
    owner_role_id: str = "world-modeler"
    schema_version: str = WAVE_THREE_WORLDTWIN_ASSUMPTION_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate assumption text, confidence, and evidence fields."""

        object.__setattr__(
            self, "assumption_id", _text(self.assumption_id, "assumption_id")
        )
        object.__setattr__(
            self, "statement", _text(self.statement, "assumption statement")
        )
        confidence = float(self.confidence)
        if confidence < 0.0 or confidence > 1.0:
            raise ValueError("assumption confidence must be between 0.0 and 1.0")
        object.__setattr__(self, "confidence", confidence)
        object.__setattr__(
            self,
            "evidence_ids",
            _unique_text(self.evidence_ids, label="assumption evidence_id"),
        )
        object.__setattr__(
            self,
            "required_evidence",
            _unique_text(self.required_evidence, label="required evidence"),
        )
        object.__setattr__(
            self, "owner_role_id", _text(self.owner_role_id, "owner_role_id")
        )
        object.__setattr__(
            self, "schema_version", _text(self.schema_version, "schema_version")
        )
        if self.status is WorldTwinAssumptionStatus.ACTIVE and not self.evidence_ids:
            raise ValueError("Active WorldTwin assumptions require evidence ids.")
        if (
            self.status is WorldTwinAssumptionStatus.UNSUPPORTED
            and not self.required_evidence
        ):
            raise ValueError("Unsupported assumptions require required evidence notes.")

    @property
    def assumption_key(self) -> str:
        """Return deterministic uniqueness key for this assumption."""

        return self.assumption_id

    @property
    def blocks_progress(self) -> bool:
        """Return whether this assumption blocks scenario progress."""

        return (
            self.status
            in {
                WorldTwinAssumptionStatus.DISPUTED,
                WorldTwinAssumptionStatus.EXPIRED,
            }
            and self.impact_if_wrong in BLOCKING_ASSUMPTION_IMPACTS
        )

    @property
    def needs_evidence(self) -> bool:
        """Return whether this assumption needs more evidence."""

        return self.status is WorldTwinAssumptionStatus.UNSUPPORTED

    def canonical_payload(self) -> dict[str, Any]:
        """Return a deterministic payload for hashing and export."""

        return {
            "assumption_id": self.assumption_id,
            "confidence": self.confidence,
            "evidence_ids": list(self.evidence_ids),
            "impact_if_wrong": self.impact_if_wrong.value,
            "owner_role_id": self.owner_role_id,
            "required_evidence": list(self.required_evidence),
            "schema_version": self.schema_version,
            "statement": self.statement,
            "status": self.status.value,
        }


@dataclass(frozen=True, slots=True)
class WorldTwinExpectedOutcome:
    """A measurable expected outcome for a bounded scenario."""

    outcome_id: str
    description: str
    measurement_name: str
    expected_result: str
    uncertainty_notes: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    required: bool = True
    schema_version: str = WAVE_THREE_WORLDTWIN_OUTCOME_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate expected outcome measurement and evidence fields."""

        object.__setattr__(self, "outcome_id", _text(self.outcome_id, "outcome_id"))
        object.__setattr__(
            self, "description", _text(self.description, "outcome description")
        )
        object.__setattr__(
            self,
            "measurement_name",
            _text(self.measurement_name, "measurement_name"),
        )
        object.__setattr__(
            self, "expected_result", _text(self.expected_result, "expected_result")
        )
        object.__setattr__(
            self,
            "uncertainty_notes",
            _unique_text(self.uncertainty_notes, label="uncertainty note"),
        )
        if not self.uncertainty_notes:
            raise ValueError("Expected outcomes require uncertainty notes.")
        object.__setattr__(
            self,
            "evidence_ids",
            _unique_text(self.evidence_ids, label="outcome evidence_id"),
        )
        object.__setattr__(
            self, "schema_version", _text(self.schema_version, "schema_version")
        )

    @property
    def outcome_key(self) -> str:
        """Return deterministic uniqueness key for this outcome."""

        return self.outcome_id

    @property
    def needs_evidence(self) -> bool:
        """Return whether this outcome needs evidence before review."""

        return self.required and not self.evidence_ids

    def canonical_payload(self) -> dict[str, Any]:
        """Return a deterministic payload for hashing and export."""

        return {
            "description": self.description,
            "evidence_ids": list(self.evidence_ids),
            "expected_result": self.expected_result,
            "measurement_name": self.measurement_name,
            "outcome_id": self.outcome_id,
            "required": self.required,
            "schema_version": self.schema_version,
            "uncertainty_notes": list(self.uncertainty_notes),
        }


@dataclass(frozen=True, slots=True)
class WorldTwinCounterfactualBranch:
    """A bounded counterfactual branch tied to assumptions and outcomes."""

    branch_id: str
    changed_assumption_ids: tuple[str, ...]
    expected_outcome_ids: tuple[str, ...]
    rationale: str
    risk_notes: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    schema_version: str = WAVE_THREE_WORLDTWIN_COUNTERFACTUAL_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate counterfactual linkage and risk notes."""

        object.__setattr__(self, "branch_id", _text(self.branch_id, "branch_id"))
        object.__setattr__(
            self,
            "changed_assumption_ids",
            _unique_text(
                self.changed_assumption_ids,
                label="changed assumption_id",
            ),
        )
        if not self.changed_assumption_ids:
            raise ValueError("Counterfactual branches require changed assumptions.")
        object.__setattr__(
            self,
            "expected_outcome_ids",
            _unique_text(self.expected_outcome_ids, label="expected outcome_id"),
        )
        if not self.expected_outcome_ids:
            raise ValueError("Counterfactual branches require expected outcomes.")
        object.__setattr__(self, "rationale", _text(self.rationale, "rationale"))
        object.__setattr__(
            self, "risk_notes", _unique_text(self.risk_notes, label="risk note")
        )
        if not self.risk_notes:
            raise ValueError("Counterfactual branches require risk notes.")
        object.__setattr__(
            self,
            "evidence_ids",
            _unique_text(self.evidence_ids, label="counterfactual evidence_id"),
        )
        object.__setattr__(
            self, "schema_version", _text(self.schema_version, "schema_version")
        )

    @property
    def branch_key(self) -> str:
        """Return deterministic uniqueness key for this branch."""

        return self.branch_id

    @property
    def needs_evidence(self) -> bool:
        """Return whether this branch needs evidence before review."""

        return not self.evidence_ids

    def canonical_payload(self) -> dict[str, Any]:
        """Return a deterministic payload for hashing and export."""

        return {
            "branch_id": self.branch_id,
            "changed_assumption_ids": list(self.changed_assumption_ids),
            "evidence_ids": list(self.evidence_ids),
            "expected_outcome_ids": list(self.expected_outcome_ids),
            "rationale": self.rationale,
            "risk_notes": list(self.risk_notes),
            "schema_version": self.schema_version,
        }


@dataclass(frozen=True, slots=True)
class WorldTwinScenarioRecord:
    """Reviewable Wave 3 WorldTwin scenario reasoning record."""

    scenario_id: str
    title: str
    bounded_question: str
    system_under_test: str
    boundaries: tuple[WorldTwinScenarioBoundary, ...]
    assumptions: tuple[WorldTwinAssumption, ...]
    expected_outcomes: tuple[WorldTwinExpectedOutcome, ...]
    counterfactual_branches: tuple[WorldTwinCounterfactualBranch, ...]
    evidence_ids: tuple[str, ...]
    created_by_role_id: str = "world-modeler"
    source_repo_reference: str = "IX-BlackFox-WorldTwin"
    schema_version: str = WAVE_THREE_WORLDTWIN_SCENARIO_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate scenario scope, references, and review-only boundary."""

        object.__setattr__(self, "scenario_id", _text(self.scenario_id, "scenario_id"))
        object.__setattr__(self, "title", _text(self.title, "title"))
        object.__setattr__(
            self,
            "bounded_question",
            _text(self.bounded_question, "bounded_question"),
        )
        object.__setattr__(
            self,
            "system_under_test",
            _text(self.system_under_test, "system_under_test"),
        )
        boundaries = tuple(sorted(self.boundaries, key=lambda item: item.boundary_key))
        assumptions = tuple(
            sorted(self.assumptions, key=lambda item: item.assumption_key)
        )
        outcomes = tuple(
            sorted(self.expected_outcomes, key=lambda item: item.outcome_key)
        )
        branches = tuple(
            sorted(self.counterfactual_branches, key=lambda item: item.branch_key)
        )
        if not boundaries:
            raise ValueError("WorldTwin scenarios require boundaries.")
        if not assumptions:
            raise ValueError("WorldTwin scenarios require assumptions.")
        if not outcomes:
            raise ValueError("WorldTwin scenarios require expected outcomes.")
        if not branches:
            raise ValueError("WorldTwin scenarios require counterfactual branches.")
        _unique_values(
            (boundary.boundary_id for boundary in boundaries), label="boundary_id"
        )
        _unique_values(
            (boundary.kind for boundary in boundaries), label="boundary kind"
        )
        _unique_values(
            (assumption.assumption_id for assumption in assumptions),
            label="assumption_id",
        )
        _unique_values((outcome.outcome_id for outcome in outcomes), label="outcome_id")
        _unique_values((branch.branch_id for branch in branches), label="branch_id")
        object.__setattr__(self, "boundaries", boundaries)
        object.__setattr__(self, "assumptions", assumptions)
        object.__setattr__(self, "expected_outcomes", outcomes)
        object.__setattr__(self, "counterfactual_branches", branches)
        object.__setattr__(
            self,
            "evidence_ids",
            _unique_text(self.evidence_ids, label="scenario evidence_id"),
        )
        object.__setattr__(
            self,
            "created_by_role_id",
            _text(self.created_by_role_id, "created_by_role_id"),
        )
        object.__setattr__(
            self,
            "source_repo_reference",
            _text(self.source_repo_reference, "source_repo_reference"),
        )
        object.__setattr__(
            self, "schema_version", _text(self.schema_version, "schema_version")
        )
        _validate_counterfactual_references(
            branches=branches,
            assumptions=assumptions,
            outcomes=outcomes,
        )

    @property
    def artifact_id(self) -> str:
        """Return the shared Wave 3 artifact id for this scenario."""

        return f"worldtwin-scenario:{self.scenario_id}"

    @property
    def represented_boundary_kinds(self) -> tuple[WorldTwinBoundaryKind, ...]:
        """Return boundary kinds in required-order where possible."""

        present = {boundary.kind for boundary in self.boundaries}
        required_order = tuple(
            kind for kind in REQUIRED_WORLDTWIN_BOUNDARY_KINDS if kind in present
        )
        extra_order = tuple(
            sorted(
                (kind for kind in present if kind not in set(required_order)),
                key=lambda kind: kind.value,
            )
        )
        return required_order + extra_order

    @property
    def missing_required_boundary_kinds(self) -> tuple[WorldTwinBoundaryKind, ...]:
        """Return required WorldTwin boundary kinds not represented."""

        present = {boundary.kind for boundary in self.boundaries}
        return tuple(
            kind for kind in REQUIRED_WORLDTWIN_BOUNDARY_KINDS if kind not in present
        )

    @property
    def unsupported_assumption_ids(self) -> tuple[str, ...]:
        """Return assumptions needing more evidence."""

        return tuple(
            assumption.assumption_id
            for assumption in self.assumptions
            if assumption.needs_evidence
        )

    @property
    def blocking_assumption_ids(self) -> tuple[str, ...]:
        """Return assumptions that block scenario progress."""

        return tuple(
            assumption.assumption_id
            for assumption in self.assumptions
            if assumption.blocks_progress
        )

    @property
    def outcomes_needing_evidence_ids(self) -> tuple[str, ...]:
        """Return required expected outcomes missing evidence."""

        return tuple(
            outcome.outcome_id
            for outcome in self.expected_outcomes
            if outcome.needs_evidence
        )

    @property
    def branches_needing_evidence_ids(self) -> tuple[str, ...]:
        """Return counterfactual branches missing evidence."""

        return tuple(
            branch.branch_id
            for branch in self.counterfactual_branches
            if branch.needs_evidence
        )

    @property
    def assumption_evidence_ids(self) -> tuple[str, ...]:
        """Return sorted unique assumption evidence ids."""

        return tuple(
            sorted(
                evidence_id
                for assumption in self.assumptions
                for evidence_id in assumption.evidence_ids
            )
        )

    @property
    def outcome_evidence_ids(self) -> tuple[str, ...]:
        """Return sorted unique expected-outcome evidence ids."""

        return tuple(
            sorted(
                evidence_id
                for outcome in self.expected_outcomes
                for evidence_id in outcome.evidence_ids
            )
        )

    @property
    def branch_evidence_ids(self) -> tuple[str, ...]:
        """Return sorted unique counterfactual branch evidence ids."""

        return tuple(
            sorted(
                evidence_id
                for branch in self.counterfactual_branches
                for evidence_id in branch.evidence_ids
            )
        )

    @property
    def all_evidence_ids(self) -> tuple[str, ...]:
        """Return sorted unique scenario, assumption, outcome, and branch evidence."""

        return tuple(
            sorted(
                set(self.evidence_ids).union(
                    self.assumption_evidence_ids,
                    self.outcome_evidence_ids,
                    self.branch_evidence_ids,
                )
            )
        )

    @property
    def permits_automatic_execution(self) -> bool:
        """Return whether this scenario permits automatic execution."""

        return False

    @property
    def readiness_gaps(self) -> tuple[str, ...]:
        """Return non-blocking gaps that prevent human-review readiness."""

        gaps: list[str] = []
        if not self.evidence_ids:
            gaps.append(f"{self.scenario_id} has no top-level evidence ids")
        if self.missing_required_boundary_kinds:
            gaps.append(
                "missing WorldTwin boundary kinds: "
                + ", ".join(kind.value for kind in self.missing_required_boundary_kinds)
            )
        if self.unsupported_assumption_ids:
            gaps.append(
                "WorldTwin assumptions need evidence: "
                + ", ".join(self.unsupported_assumption_ids)
            )
        if self.outcomes_needing_evidence_ids:
            gaps.append(
                "WorldTwin expected outcomes need evidence: "
                + ", ".join(self.outcomes_needing_evidence_ids)
            )
        if self.branches_needing_evidence_ids:
            gaps.append(
                "WorldTwin counterfactual branches need evidence: "
                + ", ".join(self.branches_needing_evidence_ids)
            )
        return tuple(gaps)

    @property
    def blocking_gaps(self) -> tuple[str, ...]:
        """Return blocking gaps that stop scenario progress."""

        if not self.blocking_assumption_ids:
            return ()
        return (
            "WorldTwin assumptions block progress: "
            + ", ".join(self.blocking_assumption_ids),
        )

    @property
    def status(self) -> WorldTwinScenarioStatus:
        """Return the fail-closed WorldTwin scenario status."""

        if self.blocking_gaps:
            return WorldTwinScenarioStatus.BLOCKED
        if self.unsupported_assumption_ids or self.outcomes_needing_evidence_ids:
            return WorldTwinScenarioStatus.NEEDS_EVIDENCE
        if self.branches_needing_evidence_ids or self.missing_required_boundary_kinds:
            return WorldTwinScenarioStatus.NEEDS_REPAIR
        if self.readiness_gaps:
            return WorldTwinScenarioStatus.NEEDS_EVIDENCE
        return WorldTwinScenarioStatus.READY_FOR_HUMAN_REVIEW

    @property
    def ready_for_human_review(self) -> bool:
        """Return whether this scenario may enter human review."""

        return self.status is WorldTwinScenarioStatus.READY_FOR_HUMAN_REVIEW

    @property
    def human_authority_state(self) -> WaveThreeAuthorityState:
        """Return aggregate human-authority state for this scenario."""

        if self.status is WorldTwinScenarioStatus.BLOCKED:
            return WaveThreeAuthorityState.BLOCKED
        return WaveThreeAuthorityState.HUMAN_REVIEW_REQUIRED

    @property
    def review_summary(self) -> str:
        """Return a concise human-review summary."""

        return (
            f"{self.scenario_id}: {self.status.value}; "
            f"{len(self.assumptions)} assumptions, "
            f"{len(self.expected_outcomes)} expected outcomes, "
            f"{len(self.counterfactual_branches)} counterfactuals; "
            "automatic execution is not permitted."
        )

    def to_artifact_ref(self) -> WaveThreeArtifactRef:
        """Convert this scenario into a shared Wave 3 artifact reference."""

        if self.status is WorldTwinScenarioStatus.READY_FOR_HUMAN_REVIEW:
            decision = WaveThreeArtifactDecision.READY_FOR_HUMAN_REVIEW
            authority_state = WaveThreeAuthorityState.HUMAN_REVIEW_REQUIRED
        elif self.status is WorldTwinScenarioStatus.BLOCKED:
            decision = WaveThreeArtifactDecision.BLOCKED
            authority_state = WaveThreeAuthorityState.BLOCKED
        else:
            decision = WaveThreeArtifactDecision.NEEDS_EVIDENCE
            authority_state = WaveThreeAuthorityState.HUMAN_REVIEW_REQUIRED
        return WaveThreeArtifactRef(
            artifact_id=self.artifact_id,
            kind=WaveThreeArtifactKind.WORLDTWIN_SCENARIO,
            source_system=WaveThreeSourceSystem.IX_BLACKFOX_WORLDTWIN,
            summary=self.review_summary,
            produced_by_engine_id="causal-world-model",
            produced_by_agent_role_id=self.created_by_role_id,
            evidence_ids=self.all_evidence_ids,
            decision=decision,
            authority_state=authority_state,
        )

    def to_artifact_bundle(self, *, artifact_bundle_id: str) -> WaveThreeArtifactBundle:
        """Convert this scenario into a shared artifact bundle."""

        artifact = self.to_artifact_ref()
        return WaveThreeArtifactBundle(
            bundle_id=artifact_bundle_id,
            artifacts=(artifact,),
            evidence_links=tuple(
                WaveThreeEvidenceLink(
                    evidence_id=evidence_id,
                    artifact_id=artifact.artifact_id,
                    relation=WaveThreeEvidenceRelation.TESTS,
                    summary=(
                        "WorldTwin scenario evidence tests assumptions, expected "
                        "outcomes, counterfactual branches, and human-review bounds."
                    ),
                    source_system=WaveThreeSourceSystem.IX_BLACKFOX_WORLDTWIN,
                )
                for evidence_id in artifact.evidence_ids
            ),
            required_kinds=(WaveThreeArtifactKind.WORLDTWIN_SCENARIO,),
            notes=("WorldTwin scenarios are bounded review artifacts only.",),
        )

    def canonical_payload(self) -> dict[str, Any]:
        """Return a deterministic payload for hashing and export."""

        return {
            "all_evidence_ids": list(self.all_evidence_ids),
            "artifact_id": self.artifact_id,
            "assumptions": [item.canonical_payload() for item in self.assumptions],
            "bounded_question": self.bounded_question,
            "boundaries": [item.canonical_payload() for item in self.boundaries],
            "blocking_gaps": list(self.blocking_gaps),
            "counterfactual_branches": [
                item.canonical_payload() for item in self.counterfactual_branches
            ],
            "created_by_role_id": self.created_by_role_id,
            "evidence_ids": list(self.evidence_ids),
            "expected_outcomes": [
                item.canonical_payload() for item in self.expected_outcomes
            ],
            "human_authority_state": self.human_authority_state.value,
            "permits_automatic_execution": self.permits_automatic_execution,
            "readiness_gaps": list(self.readiness_gaps),
            "represented_boundary_kinds": [
                kind.value for kind in self.represented_boundary_kinds
            ],
            "review_summary": self.review_summary,
            "scenario_id": self.scenario_id,
            "schema_version": self.schema_version,
            "source_repo_reference": self.source_repo_reference,
            "status": self.status.value,
            "system_under_test": self.system_under_test,
            "title": self.title,
        }

    def fingerprint(self) -> str:
        """Return a deterministic SHA-256 fingerprint for this scenario."""

        return _stable_sha256(self.canonical_payload())


@dataclass(frozen=True, slots=True)
class WorldTwinScenarioBundle:
    """Deterministic bundle of WorldTwin scenario reasoning records."""

    bundle_id: str
    scenarios: tuple[WorldTwinScenarioRecord, ...]
    notes: tuple[str, ...] = ()
    schema_version: str = WAVE_THREE_WORLDTWIN_BUNDLE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate scenario uniqueness and bundle reviewability."""

        object.__setattr__(self, "bundle_id", _text(self.bundle_id, "bundle_id"))
        if not self.scenarios:
            raise ValueError(
                "WorldTwin scenario bundles require at least one scenario."
            )
        scenarios = tuple(sorted(self.scenarios, key=lambda item: item.scenario_id))
        _unique_values((item.scenario_id for item in scenarios), label="scenario_id")
        object.__setattr__(self, "scenarios", scenarios)
        object.__setattr__(
            self, "notes", _unique_text(self.notes, label="WorldTwin bundle note")
        )
        object.__setattr__(
            self, "schema_version", _text(self.schema_version, "schema_version")
        )

    @property
    def scenario_ids(self) -> tuple[str, ...]:
        """Return scenario ids in deterministic order."""

        return tuple(scenario.scenario_id for scenario in self.scenarios)

    @property
    def ready_scenario_ids(self) -> tuple[str, ...]:
        """Return scenario ids ready for human review."""

        return tuple(
            scenario.scenario_id
            for scenario in self.scenarios
            if scenario.ready_for_human_review
        )

    @property
    def blocked_scenario_ids(self) -> tuple[str, ...]:
        """Return blocked scenario ids."""

        return tuple(
            scenario.scenario_id
            for scenario in self.scenarios
            if scenario.status is WorldTwinScenarioStatus.BLOCKED
        )

    @property
    def readiness_gaps(self) -> tuple[str, ...]:
        """Return bundle-level and scenario-level gaps."""

        gaps: list[str] = []
        for scenario in self.scenarios:
            gaps.extend(scenario.readiness_gaps)
            gaps.extend(scenario.blocking_gaps)
        return tuple(gaps)

    @property
    def is_complete_for_human_review(self) -> bool:
        """Return whether every scenario is review-ready."""

        return not self.readiness_gaps and len(self.ready_scenario_ids) == len(
            self.scenarios
        )

    def scenario_by_id(self, scenario_id: str) -> WorldTwinScenarioRecord:
        """Return one WorldTwin scenario by id."""

        normalized = _text(scenario_id, "scenario_id")
        for scenario in self.scenarios:
            if scenario.scenario_id == normalized:
                return scenario
        raise ValueError(f"Unknown WorldTwin scenario_id: {scenario_id}")

    def to_artifact_bundle(self, *, artifact_bundle_id: str) -> WaveThreeArtifactBundle:
        """Convert WorldTwin scenarios into a shared artifact bundle."""

        artifacts = tuple(scenario.to_artifact_ref() for scenario in self.scenarios)
        return WaveThreeArtifactBundle(
            bundle_id=artifact_bundle_id,
            artifacts=artifacts,
            evidence_links=tuple(
                WaveThreeEvidenceLink(
                    evidence_id=evidence_id,
                    artifact_id=artifact.artifact_id,
                    relation=WaveThreeEvidenceRelation.TESTS,
                    summary=(
                        "WorldTwin bundle evidence preserves scenario, assumption, "
                        "counterfactual, and human-review boundaries."
                    ),
                    source_system=WaveThreeSourceSystem.IX_BLACKFOX_WORLDTWIN,
                )
                for artifact in artifacts
                for evidence_id in artifact.evidence_ids
            ),
            required_kinds=(WaveThreeArtifactKind.WORLDTWIN_SCENARIO,),
            notes=("WorldTwin bundles remain review-only scenario artifacts.",),
        )

    def canonical_payload(self) -> dict[str, Any]:
        """Return a deterministic payload for hashing and export."""

        return {
            "bundle_id": self.bundle_id,
            "notes": list(self.notes),
            "readiness_gaps": list(self.readiness_gaps),
            "scenarios": [scenario.canonical_payload() for scenario in self.scenarios],
            "schema_version": self.schema_version,
        }

    def fingerprint(self) -> str:
        """Return a deterministic SHA-256 fingerprint for this bundle."""

        return _stable_sha256(self.canonical_payload())


def _validate_counterfactual_references(
    *,
    branches: tuple[WorldTwinCounterfactualBranch, ...],
    assumptions: tuple[WorldTwinAssumption, ...],
    outcomes: tuple[WorldTwinExpectedOutcome, ...],
) -> None:
    """Reject counterfactual branches with missing assumptions or outcomes."""

    assumption_ids = {assumption.assumption_id for assumption in assumptions}
    outcome_ids = {outcome.outcome_id for outcome in outcomes}
    for branch in branches:
        for assumption_id in branch.changed_assumption_ids:
            if assumption_id not in assumption_ids:
                raise ValueError(
                    "Counterfactual branch references missing assumption: "
                    f"{assumption_id}"
                )
        for outcome_id in branch.expected_outcome_ids:
            if outcome_id not in outcome_ids:
                raise ValueError(
                    "Counterfactual branch references missing expected outcome: "
                    f"{outcome_id}"
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
