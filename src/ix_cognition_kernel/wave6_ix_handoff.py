"""Wave 6 IX cognition handoff ingestion.

IX writes governed cognition contracts. IX-CognitionKernel must consume those
contracts as bounded evidence, not as executable authority. This module imports
IX-exported ``kernel-handoff.json`` payloads, validates the safety boundary, and
turns valid packages into Kernel-native Wave 6 contract artifacts.

The importer intentionally has no dependency on the IX package. IX exports JSON
contract evidence; the Kernel validates and records that evidence without
executing IX, executing donor repos, granting self-certification, or advancing an
AGI claim.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, cast

from ix_cognition_kernel.wave6_contracts import (
    WAVE_SIX_REQUIRED_LOOP_STAGES,
    WaveSixArtifactKind,
    WaveSixCapabilityArea,
    WaveSixContractArtifact,
    WaveSixDecisionState,
    WaveSixSourceSystem,
)

WAVE_SIX_IX_HANDOFF_SCHEMA_VERSION = "ix-cognition-kernel-wave6-ix-handoff-v1"
IX_KERNEL_HANDOFF_PAYLOAD_SCHEMA_VERSION = "1.0"
IX_KERNEL_HANDOFF_TYPE = "ix.cognitionkernel.handoff"
IX_COGNITION_CONTRACT_SCHEMA = "ix.cognition.contract.v1"
IX_COGNITION_KERNEL_TARGET = "IX-CognitionKernel"
IX_METADATA_ONLY_RUNTIME_SEMANTICS = "metadata_only_not_executed"
IX_NO_EXECUTION_AUTHORITY = "none"
WAVE_SIX_IX_HANDOFF_ENGINE_ID = "wave6-ix-handoff-ingestion-engine"


def _require_non_empty(value: str, label: str) -> str:
    """Return stripped text or raise when empty."""

    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{label} must not be empty.")
    return normalized


def _normalize_unique_text_tuple(
    values: Iterable[str],
    *,
    label: str,
) -> tuple[str, ...]:
    """Normalize text values while rejecting blanks and duplicates."""

    normalized: list[str] = []
    seen: set[str] = set()
    for value in values:
        stripped = _require_non_empty(value, label)
        if stripped in seen:
            raise ValueError(f"Duplicate {label} detected: {stripped}")
        normalized.append(stripped)
        seen.add(stripped)
    return tuple(normalized)


@dataclass(frozen=True, slots=True)
class WaveSixIxCanonicalObligationDefinition:
    """Kernel-side lock of one canonical IX cognition obligation definition."""

    obligation_id: str
    title: str
    purpose: str
    evidence_artifacts: tuple[str, ...]
    falsification_conditions: tuple[str, ...]

    def __post_init__(self) -> None:
        """Validate canonical obligation definition identity and requirements."""

        object.__setattr__(
            self,
            "obligation_id",
            _require_non_empty(self.obligation_id, "obligation_id"),
        )
        object.__setattr__(self, "title", _require_non_empty(self.title, "title"))
        object.__setattr__(
            self,
            "purpose",
            _require_non_empty(self.purpose, "purpose"),
        )
        object.__setattr__(
            self,
            "evidence_artifacts",
            _normalize_unique_text_tuple(
                self.evidence_artifacts,
                label="evidence_artifact",
            ),
        )
        object.__setattr__(
            self,
            "falsification_conditions",
            _normalize_unique_text_tuple(
                self.falsification_conditions,
                label="falsification_condition",
            ),
        )

    def canonical_payload(self) -> dict[str, Any]:
        """Return the IX-export-compatible canonical obligation payload."""

        return {
            "evidence_artifacts": list(self.evidence_artifacts),
            "falsification_conditions": list(self.falsification_conditions),
            "id": self.obligation_id,
            "purpose": self.purpose,
            "title": self.title,
        }


CANONICAL_IX_COGNITION_OBLIGATIONS: tuple[
    WaveSixIxCanonicalObligationDefinition,
    ...,
] = (
    WaveSixIxCanonicalObligationDefinition(
        obligation_id="purpose_discipline",
        title="Purpose discipline",
        purpose=(
            "Declare the measured reason the cognition attempt exists before it "
            "runs."
        ),
        evidence_artifacts=("attempt_purpose_record",),
        falsification_conditions=("purpose_missing", "purpose_changes_after_result"),
    ),
    WaveSixIxCanonicalObligationDefinition(
        obligation_id="claim_boundary_discipline",
        title="Claim-boundary discipline",
        purpose="Declare what the attempt may and may not claim from its evidence.",
        evidence_artifacts=("claim_boundary_record", "non_goal_record"),
        falsification_conditions=("claim_boundary_missing", "agi_claim_without_review"),
    ),
    WaveSixIxCanonicalObligationDefinition(
        obligation_id="human_authority",
        title="Human authority",
        purpose=(
            "Require human review for advancement or interpretation of "
            "candidate results."
        ),
        evidence_artifacts=("human_review_record",),
        falsification_conditions=("human_review_missing", "system_self_approved"),
    ),
    WaveSixIxCanonicalObligationDefinition(
        obligation_id="prediction_before_trial",
        title="Prediction before trial",
        purpose=(
            "Record a testable prediction before action, trial, or evaluation "
            "output is known."
        ),
        evidence_artifacts=("prediction_record",),
        falsification_conditions=(
            "prediction_missing",
            "prediction_recorded_after_outcome",
        ),
    ),
    WaveSixIxCanonicalObligationDefinition(
        obligation_id="measured_outcome_capture",
        title="Measured outcome capture",
        purpose=(
            "Record the observed result used to judge whether the attempt met "
            "reality."
        ),
        evidence_artifacts=("outcome_record",),
        falsification_conditions=("outcome_missing", "outcome_not_measured"),
    ),
    WaveSixIxCanonicalObligationDefinition(
        obligation_id="reality_delta_comparison",
        title="Reality-delta comparison",
        purpose="Compare prediction against measured outcome and record the delta.",
        evidence_artifacts=("delta_record", "prediction_outcome_comparison"),
        falsification_conditions=("delta_missing", "prediction_outcome_not_compared"),
    ),
    WaveSixIxCanonicalObligationDefinition(
        obligation_id="evidence_bound_memory_update",
        title="Evidence-bound memory update",
        purpose=(
            "Allow memory updates only when tied to measured evidence and "
            "reviewable rationale."
        ),
        evidence_artifacts=("memory_update_record", "memory_evidence_link"),
        falsification_conditions=(
            "memory_update_without_evidence",
            "memory_claim_not_traceable",
        ),
    ),
    WaveSixIxCanonicalObligationDefinition(
        obligation_id="future_reasoning_change",
        title="Future-reasoning change",
        purpose=(
            "Show that measured reality changed later reasoning rather than only "
            "being logged."
        ),
        evidence_artifacts=("before_after_reasoning_record",),
        falsification_conditions=("future_reasoning_unchanged", "change_is_cosmetic"),
    ),
    WaveSixIxCanonicalObligationDefinition(
        obligation_id="cross_domain_transfer_probe",
        title="Cross-domain transfer probe",
        purpose=(
            "Test whether learned structure transfers outside the source task or "
            "domain."
        ),
        evidence_artifacts=("transfer_probe_record", "source_target_domain_record"),
        falsification_conditions=("transfer_probe_missing", "transfer_failed"),
    ),
    WaveSixIxCanonicalObligationDefinition(
        obligation_id="novelty_generality_pressure",
        title="Novelty and generality pressure",
        purpose=(
            "Expose the attempt to non-identical tasks so success cannot be pure "
            "memorization."
        ),
        evidence_artifacts=("novelty_record", "generality_pressure_record"),
        falsification_conditions=("novelty_missing", "task_replay_only"),
    ),
    WaveSixIxCanonicalObligationDefinition(
        obligation_id="long_horizon_planning_trace",
        title="Long-horizon planning trace",
        purpose=(
            "Record multi-step planning state, progress, revisions, and stop "
            "conditions."
        ),
        evidence_artifacts=("plan_trace", "planning_revision_record"),
        falsification_conditions=(
            "plan_trace_missing",
            "plan_abandoned_without_record",
        ),
    ),
    WaveSixIxCanonicalObligationDefinition(
        obligation_id="uncertainty_assumption_exposure",
        title="Uncertainty and assumption exposure",
        purpose=(
            "Expose confidence, uncertainty, and assumptions instead of hiding "
            "unknowns."
        ),
        evidence_artifacts=("uncertainty_record", "assumption_ledger"),
        falsification_conditions=("uncertainty_hidden", "assumption_not_recorded"),
    ),
    WaveSixIxCanonicalObligationDefinition(
        obligation_id="contradiction_handling",
        title="Contradiction handling",
        purpose=(
            "Detect contradictions and route them to correction, quarantine, or "
            "review."
        ),
        evidence_artifacts=("contradiction_record", "resolution_record"),
        falsification_conditions=("contradiction_ignored", "conflict_used_as_truth"),
    ),
    WaveSixIxCanonicalObligationDefinition(
        obligation_id="shortcut_reward_hacking_detection",
        title="Shortcut and reward-hacking detection",
        purpose=(
            "Detect apparent success caused by metric gaming, shortcuts, or proxy "
            "exploitation."
        ),
        evidence_artifacts=("shortcut_audit_record", "reward_audit_record"),
        falsification_conditions=("reward_hacking_detected", "shortcut_not_audited"),
    ),
    WaveSixIxCanonicalObligationDefinition(
        obligation_id="safe_refusal_path",
        title="Safe refusal path",
        purpose=(
            "Permit refusal, deferment, or safe halt when obligations cannot be "
            "satisfied."
        ),
        evidence_artifacts=("refusal_record", "safe_halt_record"),
        falsification_conditions=("unsafe_continuation", "required_refusal_missing"),
    ),
    WaveSixIxCanonicalObligationDefinition(
        obligation_id="self_improvement_airlock",
        title="Self-improvement airlock",
        purpose=(
            "Separate proposed self-change from approval, execution, and "
            "promotion authority."
        ),
        evidence_artifacts=("self_change_proposal", "approval_separation_record"),
        falsification_conditions=(
            "self_change_self_approved",
            "unreviewed_self_modification",
        ),
    ),
    WaveSixIxCanonicalObligationDefinition(
        obligation_id="no_self_certification",
        title="No self-certification",
        purpose=(
            "Prevent the system or model from certifying its own AGI-candidate "
            "success."
        ),
        evidence_artifacts=("self_certification_guard_record",),
        falsification_conditions=(
            "system_self_certifies",
            "model_claims_final_authority",
        ),
    ),
    WaveSixIxCanonicalObligationDefinition(
        obligation_id="falsification_ledger",
        title="Falsification ledger",
        purpose=(
            "Record failure conditions and use them to block unsupported "
            "advancement claims."
        ),
        evidence_artifacts=("falsification_ledger",),
        falsification_conditions=(
            "falsification_record_missing",
            "failed_gate_ignored",
        ),
    ),
    WaveSixIxCanonicalObligationDefinition(
        obligation_id="independent_replay_review",
        title="Independent replay and review readiness",
        purpose=(
            "Produce enough evidence for independent replay, audit, or human "
            "review."
        ),
        evidence_artifacts=("replay_manifest", "review_packet"),
        falsification_conditions=("replay_not_possible", "review_packet_missing"),
    ),
    WaveSixIxCanonicalObligationDefinition(
        obligation_id="kernel_handoff_package",
        title="Kernel handoff package",
        purpose=(
            "Export a structured obligation package for IX-CognitionKernel to "
            "attempt."
        ),
        evidence_artifacts=("kernel_handoff_package",),
        falsification_conditions=("kernel_handoff_missing", "handoff_schema_invalid"),
    ),
)

CANONICAL_IX_COGNITION_OBLIGATION_IDS: tuple[str, ...] = tuple(
    definition.obligation_id for definition in CANONICAL_IX_COGNITION_OBLIGATIONS
)
CANONICAL_IX_COGNITION_OBLIGATION_MAP: Mapping[
    str,
    WaveSixIxCanonicalObligationDefinition,
] = {
    definition.obligation_id: definition for definition in CANONICAL_IX_COGNITION_OBLIGATIONS
}


class WaveSixIxHandoffValidationState(StrEnum):
    """Validation state for an imported IX handoff."""

    VALIDATED_CONTRACT_ONLY = "validated-contract-only"


@dataclass(frozen=True, slots=True)
class WaveSixIxSourceLocation:
    """Source location carried from the IX exported handoff payload."""

    filename: str
    line: int
    column: int

    def __post_init__(self) -> None:
        """Validate that source locations are concrete and positive."""

        object.__setattr__(
            self,
            "filename",
            _require_non_empty(self.filename, "source filename"),
        )
        if self.line < 1:
            raise ValueError("IX source line must be positive.")
        if self.column < 1:
            raise ValueError("IX source column must be positive.")

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic source-location payload."""

        return {
            "column": self.column,
            "filename": self.filename,
            "line": self.line,
        }


@dataclass(frozen=True, slots=True)
class WaveSixIxObligation:
    """One canonical obligation imported from an IX kernel handoff package."""

    obligation_id: str
    evidence_required: tuple[str, ...]
    falsify_if: tuple[str, ...]
    source: WaveSixIxSourceLocation
    canonical_definition: WaveSixIxCanonicalObligationDefinition
    canonical: bool = True
    schema_version: str = WAVE_SIX_IX_HANDOFF_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate obligation identity, canonical definition, and subsets."""

        object.__setattr__(
            self,
            "obligation_id",
            _require_non_empty(self.obligation_id, "obligation_id"),
        )
        object.__setattr__(
            self,
            "evidence_required",
            _normalize_unique_text_tuple(
                self.evidence_required,
                label="evidence_required",
            ),
        )
        object.__setattr__(
            self,
            "falsify_if",
            _normalize_unique_text_tuple(self.falsify_if, label="falsify_if"),
        )
        object.__setattr__(
            self,
            "schema_version",
            _require_non_empty(self.schema_version, "schema_version"),
        )
        if not self.canonical:
            raise ValueError("IX handoff obligations must be marked canonical.")
        if self.obligation_id != self.canonical_definition.obligation_id:
            raise ValueError("IX obligation id must match its canonical definition.")
        if not self.evidence_required:
            raise ValueError("IX obligations require at least one evidence item.")
        if not self.falsify_if:
            raise ValueError("IX obligations require at least one falsification gate.")
        _require_subset(
            self.evidence_required,
            self.canonical_definition.evidence_artifacts,
            item_label="evidence_required",
            owner_label=self.obligation_id,
        )
        _require_subset(
            self.falsify_if,
            self.canonical_definition.falsification_conditions,
            item_label="falsify_if",
            owner_label=self.obligation_id,
        )

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic imported-obligation payload."""

        return {
            "canonical": self.canonical,
            "canonical_definition": self.canonical_definition.canonical_payload(),
            "evidence_required": list(self.evidence_required),
            "falsify_if": list(self.falsify_if),
            "id": self.obligation_id,
            "schema_version": self.schema_version,
            "source": self.source.canonical_payload(),
        }


@dataclass(frozen=True, slots=True)
class WaveSixIxHandoffPackage:
    """Validated IX contract package targeted at IX-CognitionKernel."""

    attempt: str
    source: WaveSixIxSourceLocation
    purpose: tuple[str, ...]
    non_goals: tuple[str, ...]
    claim_boundaries: tuple[str, ...]
    human_approval_required: tuple[str, ...]
    obligations: tuple[WaveSixIxObligation, ...]
    target: str = IX_COGNITION_KERNEL_TARGET
    schema: str = IX_COGNITION_CONTRACT_SCHEMA
    runtime_semantics: str = IX_METADATA_ONLY_RUNTIME_SEMANTICS
    execution_authority: str = IX_NO_EXECUTION_AUTHORITY
    self_certification_allowed: bool = False
    human_authority_required: bool = True
    validation_state: WaveSixIxHandoffValidationState = (
        WaveSixIxHandoffValidationState.VALIDATED_CONTRACT_ONLY
    )
    schema_version: str = WAVE_SIX_IX_HANDOFF_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate package-level target, authority, and canonical obligations."""

        object.__setattr__(
            self,
            "attempt",
            _require_non_empty(self.attempt, "attempt"),
        )
        object.__setattr__(
            self,
            "target",
            _require_exact_text(
                self.target,
                IX_COGNITION_KERNEL_TARGET,
                "IX handoff target",
            ),
        )
        object.__setattr__(
            self,
            "schema",
            _require_exact_text(
                self.schema,
                IX_COGNITION_CONTRACT_SCHEMA,
                "IX cognition contract schema",
            ),
        )
        object.__setattr__(
            self,
            "runtime_semantics",
            _require_exact_text(
                self.runtime_semantics,
                IX_METADATA_ONLY_RUNTIME_SEMANTICS,
                "IX runtime semantics",
            ),
        )
        object.__setattr__(
            self,
            "execution_authority",
            _require_exact_text(
                self.execution_authority,
                IX_NO_EXECUTION_AUTHORITY,
                "IX handoff execution authority",
            ),
        )
        object.__setattr__(
            self,
            "purpose",
            _normalize_unique_text_tuple(self.purpose, label="purpose"),
        )
        object.__setattr__(
            self,
            "non_goals",
            _normalize_unique_text_tuple(self.non_goals, label="non_goal"),
        )
        object.__setattr__(
            self,
            "claim_boundaries",
            _normalize_unique_text_tuple(
                self.claim_boundaries,
                label="claim_boundary",
            ),
        )
        object.__setattr__(
            self,
            "human_approval_required",
            _normalize_unique_text_tuple(
                self.human_approval_required,
                label="human_approval_required",
            ),
        )
        object.__setattr__(
            self,
            "schema_version",
            _require_non_empty(self.schema_version, "schema_version"),
        )
        if self.self_certification_allowed:
            raise ValueError("IX handoff must not allow self-certification.")
        if not self.human_authority_required:
            raise ValueError("IX handoff must require human authority.")
        if not self.purpose:
            raise ValueError("IX handoff package requires purpose text.")
        if not self.non_goals:
            raise ValueError("IX handoff package requires non-goals.")
        if not self.claim_boundaries:
            raise ValueError("IX handoff package requires claim boundaries.")
        if not self.human_approval_required:
            raise ValueError("IX handoff package requires human approval records.")
        sorted_obligations = _sort_obligations_by_canonical_order(self.obligations)
        object.__setattr__(self, "obligations", sorted_obligations)
        _require_exact_obligation_ids(self.obligation_ids)

    @property
    def obligation_ids(self) -> tuple[str, ...]:
        """Return imported obligation ids in canonical IX cognition order."""

        return tuple(obligation.obligation_id for obligation in self.obligations)

    @property
    def required_evidence_ids(self) -> tuple[str, ...]:
        """Return declared downstream evidence ids in deterministic order."""

        return _unique_preserving_order(
            evidence_id
            for obligation in self.obligations
            for evidence_id in obligation.evidence_required
        )

    @property
    def falsification_gate_ids(self) -> tuple[str, ...]:
        """Return declared falsification gates in deterministic order."""

        return _unique_preserving_order(
            gate_id for obligation in self.obligations for gate_id in obligation.falsify_if
        )

    @property
    def ix_evidence_id(self) -> str:
        """Return the Kernel evidence id for this imported IX handoff package."""

        return f"ix-kernel-handoff:{self.attempt}:kernel-handoff-json"

    def to_contract_artifact(self) -> WaveSixContractArtifact:
        """Convert this IX package into a bounded Wave 6 contract artifact."""

        return WaveSixContractArtifact(
            artifact_id=f"ix-handoff-artifact-{self.attempt}",
            kind=WaveSixArtifactKind.MASTER_LOOP_CONTRACT,
            capability_area=WaveSixCapabilityArea.MASTER_LOOP,
            source_system=WaveSixSourceSystem.IX_MAIN,
            summary=(
                "IX cognition handoff package imported as metadata-only Wave 6 "
                "contract evidence; it grants no execution authority and makes "
                "no AGI claim."
            ),
            loop_stages=WAVE_SIX_REQUIRED_LOOP_STAGES,
            evidence_ids=(self.ix_evidence_id,),
            produced_by_engine_id=WAVE_SIX_IX_HANDOFF_ENGINE_ID,
            decision=WaveSixDecisionState.NEEDS_MORE_EVIDENCE,
        )

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic package payload for review and hashing."""

        return {
            "attempt": self.attempt,
            "claim_boundaries": list(self.claim_boundaries),
            "execution_authority": self.execution_authority,
            "falsification_gate_ids": list(self.falsification_gate_ids),
            "human_approval_required": list(self.human_approval_required),
            "human_authority_required": self.human_authority_required,
            "ix_evidence_id": self.ix_evidence_id,
            "non_goals": list(self.non_goals),
            "obligations": [
                obligation.canonical_payload() for obligation in self.obligations
            ],
            "purpose": list(self.purpose),
            "required_evidence_ids": list(self.required_evidence_ids),
            "runtime_semantics": self.runtime_semantics,
            "schema": self.schema,
            "schema_version": self.schema_version,
            "self_certification_allowed": self.self_certification_allowed,
            "source": self.source.canonical_payload(),
            "target": self.target,
            "validation_state": self.validation_state.value,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this package."""

        return _stable_sha256(self.canonical_payload())


@dataclass(frozen=True, slots=True)
class WaveSixIxHandoffBundle:
    """Validated IX ``kernel-handoff.json`` payload."""

    packages: tuple[WaveSixIxHandoffPackage, ...]
    handoff_type: str = IX_KERNEL_HANDOFF_TYPE
    runtime_semantics: str = IX_METADATA_ONLY_RUNTIME_SEMANTICS
    payload_schema_version: str = IX_KERNEL_HANDOFF_PAYLOAD_SCHEMA_VERSION
    schema_version: str = WAVE_SIX_IX_HANDOFF_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate bundle identity and deterministic package ordering."""

        object.__setattr__(
            self,
            "handoff_type",
            _require_exact_text(
                self.handoff_type,
                IX_KERNEL_HANDOFF_TYPE,
                "IX kernel handoff type",
            ),
        )
        object.__setattr__(
            self,
            "runtime_semantics",
            _require_exact_text(
                self.runtime_semantics,
                IX_METADATA_ONLY_RUNTIME_SEMANTICS,
                "IX runtime semantics",
            ),
        )
        object.__setattr__(
            self,
            "payload_schema_version",
            _require_exact_text(
                self.payload_schema_version,
                IX_KERNEL_HANDOFF_PAYLOAD_SCHEMA_VERSION,
                "IX handoff payload schema version",
            ),
        )
        object.__setattr__(
            self,
            "schema_version",
            _require_non_empty(self.schema_version, "schema_version"),
        )
        if not self.packages:
            raise ValueError("IX handoff bundle requires at least one package.")
        sorted_packages = tuple(sorted(self.packages, key=lambda package: package.attempt))
        _require_unique_text(
            (package.attempt for package in sorted_packages),
            label="attempt",
        )
        object.__setattr__(self, "packages", sorted_packages)

    @property
    def package_count(self) -> int:
        """Return the number of validated IX handoff packages."""

        return len(self.packages)

    @property
    def obligation_count(self) -> int:
        """Return the total imported obligation count."""

        return sum(len(package.obligations) for package in self.packages)

    @property
    def contract_artifacts(self) -> tuple[WaveSixContractArtifact, ...]:
        """Return Kernel-native artifacts produced by this IX handoff."""

        return tuple(package.to_contract_artifact() for package in self.packages)

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic bundle payload for review and hashing."""

        return {
            "handoff_type": self.handoff_type,
            "obligation_count": self.obligation_count,
            "packages": [package.canonical_payload() for package in self.packages],
            "package_count": self.package_count,
            "payload_schema_version": self.payload_schema_version,
            "runtime_semantics": self.runtime_semantics,
            "schema_version": self.schema_version,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for the imported bundle."""

        return _stable_sha256(self.canonical_payload())


def canonical_ix_cognition_obligation_ids() -> tuple[str, ...]:
    """Return canonical IX cognition obligation ids accepted by the importer."""

    return CANONICAL_IX_COGNITION_OBLIGATION_IDS


def load_ix_cognition_handoff(payload: Mapping[str, Any]) -> WaveSixIxHandoffBundle:
    """Load and validate an IX-exported ``kernel-handoff.json`` payload."""

    return WaveSixIxHandoffBundle(
        handoff_type=_text_value(payload, "handoff_type"),
        runtime_semantics=_text_value(payload, "runtime_semantics"),
        payload_schema_version=_text_value(payload, "schema_version"),
        packages=tuple(
            _load_handoff_package(package)
            for package in _mapping_sequence(payload, "packages")
        ),
    )


def _load_handoff_package(payload: Mapping[str, Any]) -> WaveSixIxHandoffPackage:
    """Load one package from an IX kernel handoff payload."""

    return WaveSixIxHandoffPackage(
        attempt=_text_value(payload, "attempt"),
        target=_text_value(payload, "target"),
        schema=_text_value(payload, "schema"),
        source=_load_source_location(_mapping_value(payload, "source")),
        runtime_semantics=_text_value(payload, "runtime_semantics"),
        execution_authority=_text_value(payload, "execution_authority"),
        self_certification_allowed=_bool_value(payload, "self_certification_allowed"),
        human_authority_required=_bool_value(payload, "human_authority_required"),
        purpose=_text_sequence(payload, "purpose"),
        non_goals=_text_sequence(payload, "non_goals"),
        claim_boundaries=_text_sequence(payload, "claim_boundaries"),
        human_approval_required=_text_sequence(payload, "human_approval_required"),
        obligations=tuple(
            _load_obligation(obligation)
            for obligation in _mapping_sequence(payload, "obligations")
        ),
    )


def _load_obligation(payload: Mapping[str, Any]) -> WaveSixIxObligation:
    """Load one canonical IX obligation from a handoff package."""

    obligation_id = _text_value(payload, "id")
    canonical_definition = _canonical_definition_for_payload(
        obligation_id,
        _mapping_value(payload, "canonical_definition"),
    )
    return WaveSixIxObligation(
        obligation_id=obligation_id,
        canonical=_bool_value(payload, "canonical"),
        evidence_required=_text_sequence(payload, "evidence_required"),
        falsify_if=_text_sequence(payload, "falsify_if"),
        source=_load_source_location(_mapping_value(payload, "source")),
        canonical_definition=canonical_definition,
    )


def _canonical_definition_for_payload(
    obligation_id: str,
    payload: Mapping[str, Any],
) -> WaveSixIxCanonicalObligationDefinition:
    """Return the locked canonical definition after verifying IX payload drift."""

    definition = CANONICAL_IX_COGNITION_OBLIGATION_MAP.get(obligation_id)
    if definition is None:
        raise ValueError(f"Unknown IX cognition obligation: {obligation_id}")
    if payload != definition.canonical_payload():
        raise ValueError(
            "IX canonical obligation definition drift detected for "
            f"{obligation_id}."
        )
    return definition


def _load_source_location(payload: Mapping[str, Any]) -> WaveSixIxSourceLocation:
    """Load a source location from an IX payload."""

    return WaveSixIxSourceLocation(
        filename=_text_value(payload, "filename"),
        line=_int_value(payload, "line"),
        column=_int_value(payload, "column"),
    )


def _sort_obligations_by_canonical_order(
    obligations: Iterable[WaveSixIxObligation],
) -> tuple[WaveSixIxObligation, ...]:
    """Return obligations sorted by the locked IX cognition obligation order."""

    by_id: dict[str, WaveSixIxObligation] = {}
    for obligation in obligations:
        if obligation.obligation_id in by_id:
            raise ValueError(
                f"Duplicate IX cognition obligation: {obligation.obligation_id}"
            )
        by_id[obligation.obligation_id] = obligation
    return tuple(
        by_id[obligation_id]
        for obligation_id in CANONICAL_IX_COGNITION_OBLIGATION_IDS
        if obligation_id in by_id
    )


def _require_exact_obligation_ids(obligation_ids: tuple[str, ...]) -> None:
    """Require exactly the locked canonical IX cognition obligation ids."""

    actual = set(obligation_ids)
    expected = set(CANONICAL_IX_COGNITION_OBLIGATION_IDS)
    missing = tuple(
        obligation_id
        for obligation_id in CANONICAL_IX_COGNITION_OBLIGATION_IDS
        if obligation_id not in actual
    )
    extra = tuple(sorted(actual - expected))
    if missing:
        raise ValueError(f"Missing IX cognition obligation: {missing[0]}")
    if extra:
        raise ValueError(f"Unknown IX cognition obligation: {extra[0]}")


def _require_subset(
    values: Iterable[str],
    allowed_values: Iterable[str],
    *,
    item_label: str,
    owner_label: str,
) -> None:
    """Require all declared values to come from a canonical value set."""

    allowed = set(allowed_values)
    for value in values:
        if value not in allowed:
            raise ValueError(
                f"{item_label} `{value}` is not canonical for {owner_label}."
            )


def _text_value(payload: Mapping[str, Any], key: str) -> str:
    """Read a required text field from a mapping."""

    value = payload.get(key)
    if not isinstance(value, str):
        raise ValueError(f"IX handoff field `{key}` must be text.")
    return _require_non_empty(value, key)


def _bool_value(payload: Mapping[str, Any], key: str) -> bool:
    """Read a required boolean field from a mapping."""

    value = payload.get(key)
    if not isinstance(value, bool):
        raise ValueError(f"IX handoff field `{key}` must be boolean.")
    return value


def _int_value(payload: Mapping[str, Any], key: str) -> int:
    """Read a required integer field from a mapping."""

    value = payload.get(key)
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(f"IX handoff field `{key}` must be an integer.")
    return value


def _mapping_value(payload: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    """Read a required mapping field from a mapping."""

    value = payload.get(key)
    if not isinstance(value, Mapping):
        raise ValueError(f"IX handoff field `{key}` must be an object.")
    return cast(Mapping[str, Any], value)


def _text_sequence(payload: Mapping[str, Any], key: str) -> tuple[str, ...]:
    """Read a required text sequence from a mapping."""

    values = _sequence_value(payload, key)
    text_values: list[str] = []
    for index, value in enumerate(values):
        if not isinstance(value, str):
            raise ValueError(f"IX handoff field `{key}[{index}]` must be text.")
        text_values.append(value)
    return _normalize_unique_text_tuple(text_values, label=key)


def _mapping_sequence(
    payload: Mapping[str, Any],
    key: str,
) -> tuple[Mapping[str, Any], ...]:
    """Read a required sequence of mappings from a mapping."""

    values = _sequence_value(payload, key)
    mappings: list[Mapping[str, Any]] = []
    for index, value in enumerate(values):
        if not isinstance(value, Mapping):
            raise ValueError(f"IX handoff field `{key}[{index}]` must be an object.")
        mappings.append(cast(Mapping[str, Any], value))
    return tuple(mappings)


def _sequence_value(payload: Mapping[str, Any], key: str) -> Sequence[Any]:
    """Read a required non-string sequence field from a mapping."""

    value = payload.get(key)
    if isinstance(value, str) or not isinstance(value, Sequence):
        raise ValueError(f"IX handoff field `{key}` must be a list.")
    return value


def _require_exact_text(value: str, expected: str, label: str) -> str:
    """Require exact text for a safety-critical IX field."""

    normalized = _require_non_empty(value, label)
    if normalized != expected:
        raise ValueError(f"{label} must be `{expected}`.")
    return normalized


def _unique_preserving_order(values: Iterable[str]) -> tuple[str, ...]:
    """Return unique text values while preserving first-seen order."""

    seen: set[str] = set()
    unique: list[str] = []
    for value in values:
        if value not in seen:
            unique.append(value)
            seen.add(value)
    return tuple(unique)


def _require_unique_text(values: Iterable[str], *, label: str) -> None:
    """Reject duplicate text values."""

    seen: set[str] = set()
    for value in values:
        if value in seen:
            raise ValueError(f"Duplicate {label} detected: {value}")
        seen.add(value)


def _stable_sha256(payload: Mapping[str, Any]) -> str:
    """Return deterministic SHA-256 over a canonical JSON payload."""

    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
    def _probe_id(contract_artifact_id: str, obligation: WaveSixIxObligation) -> str:
    """Return deterministic falsification-probe id for an IX obligation."""

    return f"ix-obligation-probe:{contract_artifact_id}:{obligation.obligation_id}"


def _sort_pressures_by_canonical_order(
    pressures: Iterable[WaveSixIxObligationPressure],
) -> tuple[WaveSixIxObligationPressure, ...]:
    """Return pressure records sorted by canonical IX obligation order."""

    by_id: dict[str, WaveSixIxObligationPressure] = {}
    for pressure in pressures:
        if pressure.obligation_id in by_id:
            raise ValueError(
                f"Duplicate IX obligation pressure: {pressure.obligation_id}"
            )
        by_id[pressure.obligation_id] = pressure
    return tuple(
        by_id[obligation_id]
        for obligation_id in canonical_ix_cognition_obligation_ids()
        if obligation_id in by_id
    )


def _require_exact_obligation_ids(obligation_ids: tuple[str, ...]) -> None:
    """Require pressure coverage for every canonical IX cognition obligation."""

    expected = set(canonical_ix_cognition_obligation_ids())
    actual = set(obligation_ids)
    missing = tuple(
        obligation_id
        for obligation_id in canonical_ix_cognition_obligation_ids()
        if obligation_id not in actual
    )
    extra = tuple(sorted(actual - expected))
    if missing:
        raise ValueError(f"Missing IX obligation pressure: {missing[0]}")
    if extra:
        raise ValueError(f"Unknown IX obligation pressure: {extra[0]}")


def _unique_preserving_order(values: Iterable[str]) -> tuple[str, ...]:
    """Return unique text values while preserving first-seen order."""

    seen: set[str] = set()
    unique: list[str] = []
    for value in values:
        if value not in seen:
            unique.append(value)
            seen.add(value)
    return tuple(unique)


def _require_non_empty(value: str, label: str) -> str:
    """Return stripped text or raise when empty."""

    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{label} must not be empty.")
    return normalized


def _require_sha256(value: str, label: str) -> str:
    """Require a deterministic SHA-256 fingerprint value."""

    normalized = _require_non_empty(value, label)
    if len(normalized) != 64:
        raise ValueError(f"{label} must be a SHA-256 fingerprint.")
    try:
        int(normalized, 16)
    except ValueError as exc:
        raise ValueError(f"{label} must be hexadecimal.") from exc
    return normalized


def _stable_sha256(payload: Mapping[str, Any]) -> str:
    """Return deterministic SHA-256 over a canonical JSON payload."""

    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
