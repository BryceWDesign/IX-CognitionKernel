"""Wave 5 external validation protocol manifests.

Wave 5 cannot be earned by internal assertions. This module models the
pre-registered protocol layer that outside reviewers and replication labs would
use before a credible AGI-candidate-under-independent-validation claim is even
reviewable. A protocol manifest is still record-only: it declares criteria,
falsification paths, forbidden shortcuts, evidence obligations, and reviewer
requirements without claiming AGI, certification, production readiness, or
autonomous authority.
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

WAVE_FIVE_PROTOCOL_CRITERION_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave5-protocol-criterion-v1"
)
WAVE_FIVE_ACCEPTANCE_GATE_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave5-acceptance-gate-v1"
)
WAVE_FIVE_EXTERNAL_PROTOCOL_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave5-external-protocol-v1"
)


class WaveFiveProtocolDomain(StrEnum):
    """External validation domains a Wave 5 protocol must cover."""

    EXTERNAL_REVIEW = "external-review"
    REPRODUCIBILITY = "reproducibility"
    ADVERSARIAL_SAFETY = "adversarial-safety"
    LONG_HORIZON = "long-horizon"
    CROSS_DOMAIN_TRANSFER = "cross-domain-transfer"
    MEMORY_INTEGRITY = "memory-integrity"
    SAFE_REFUSAL = "safe-refusal"
    HUMAN_AUTHORITY = "human-authority"
    ECOSYSTEM_TRACEABILITY = "ecosystem-traceability"
    WAVE_SIX_PRECONDITIONS = "wave-six-preconditions"


class WaveFiveProtocolCriterionKind(StrEnum):
    """Kinds of criteria that make a protocol falsifiable."""

    ACCEPTANCE = "acceptance"
    REJECTION = "rejection"
    MEASUREMENT = "measurement"
    NEGATIVE_CONTROL = "negative-control"
    FALSIFICATION = "falsification"


class WaveFiveAcceptanceGateKind(StrEnum):
    """Kinds of gates an external protocol must evaluate."""

    REQUIRED_EVIDENCE_PRESENT = "required-evidence-present"
    INDEPENDENT_REVIEWER_PRESENT = "independent-reviewer-present"
    REPRODUCTION_ATTEMPT_PRESENT = "reproduction-attempt-present"
    ADVERSARIAL_PRESSURE_PRESENT = "adversarial-pressure-present"
    HUMAN_AUTHORITY_PRESERVED = "human-authority-preserved"
    OVERCLAIM_BOUNDARY_PRESERVED = "overclaim-boundary-preserved"


class WaveFiveProtocolRegistrationState(StrEnum):
    """Registration state of an external validation protocol."""

    DRAFT_INTERNAL = "draft-internal"
    PREREGISTERED_EXTERNAL = "preregistered-external"
    UNDER_EXTERNAL_REVIEW = "under-external-review"
    ACCEPTED_FOR_EXECUTION = "accepted-for-execution"
    REJECTED = "rejected"


REQUIRED_WAVE_FIVE_PROTOCOL_DOMAINS: tuple[WaveFiveProtocolDomain, ...] = (
    WaveFiveProtocolDomain.EXTERNAL_REVIEW,
    WaveFiveProtocolDomain.REPRODUCIBILITY,
    WaveFiveProtocolDomain.ADVERSARIAL_SAFETY,
    WaveFiveProtocolDomain.LONG_HORIZON,
    WaveFiveProtocolDomain.CROSS_DOMAIN_TRANSFER,
    WaveFiveProtocolDomain.MEMORY_INTEGRITY,
    WaveFiveProtocolDomain.SAFE_REFUSAL,
    WaveFiveProtocolDomain.HUMAN_AUTHORITY,
    WaveFiveProtocolDomain.ECOSYSTEM_TRACEABILITY,
    WaveFiveProtocolDomain.WAVE_SIX_PRECONDITIONS,
)

REQUIRED_WAVE_FIVE_ACCEPTANCE_GATES: tuple[WaveFiveAcceptanceGateKind, ...] = (
    WaveFiveAcceptanceGateKind.REQUIRED_EVIDENCE_PRESENT,
    WaveFiveAcceptanceGateKind.INDEPENDENT_REVIEWER_PRESENT,
    WaveFiveAcceptanceGateKind.REPRODUCTION_ATTEMPT_PRESENT,
    WaveFiveAcceptanceGateKind.ADVERSARIAL_PRESSURE_PRESENT,
    WaveFiveAcceptanceGateKind.HUMAN_AUTHORITY_PRESERVED,
    WaveFiveAcceptanceGateKind.OVERCLAIM_BOUNDARY_PRESERVED,
)


@dataclass(frozen=True, slots=True)
class WaveFiveProtocolCriterion:
    """One falsifiable criterion inside a Wave 5 external protocol."""

    criterion_id: str
    criterion_kind: WaveFiveProtocolCriterionKind
    domain: WaveFiveProtocolDomain
    statement: str
    measurement_method: str
    pass_condition: str
    fail_condition: str
    required_evidence_ids: tuple[str, ...]
    schema_version: str = WAVE_FIVE_PROTOCOL_CRITERION_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate criterion identity and falsifiability."""

        object.__setattr__(
            self, "criterion_id", _text(self.criterion_id, "criterion_id")
        )
        object.__setattr__(self, "statement", _text(self.statement, "statement"))
        object.__setattr__(
            self,
            "measurement_method",
            _text(self.measurement_method, "measurement_method"),
        )
        object.__setattr__(
            self, "pass_condition", _text(self.pass_condition, "pass_condition")
        )
        object.__setattr__(
            self, "fail_condition", _text(self.fail_condition, "fail_condition")
        )
        if self.pass_condition == self.fail_condition:
            raise ValueError("Protocol pass_condition and fail_condition must differ.")
        object.__setattr__(
            self,
            "required_evidence_ids",
            _unique_text(self.required_evidence_ids, label="criterion evidence_id"),
        )
        if not self.required_evidence_ids:
            raise ValueError("Protocol criteria require evidence ids.")
        object.__setattr__(
            self, "schema_version", _text(self.schema_version, "schema_version")
        )

    @property
    def criterion_key(self) -> str:
        """Return deterministic uniqueness key."""

        return self.criterion_id

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic export payload."""

        return {
            "criterion_id": self.criterion_id,
            "criterion_kind": self.criterion_kind.value,
            "domain": self.domain.value,
            "fail_condition": self.fail_condition,
            "measurement_method": self.measurement_method,
            "pass_condition": self.pass_condition,
            "required_evidence_ids": list(self.required_evidence_ids),
            "schema_version": self.schema_version,
            "statement": self.statement,
        }


@dataclass(frozen=True, slots=True)
class WaveFiveAcceptanceGate:
    """One fail-closed gate in an external validation protocol."""

    gate_id: str
    gate_kind: WaveFiveAcceptanceGateKind
    description: str
    required_criterion_ids: tuple[str, ...]
    blocking: bool = True
    schema_version: str = WAVE_FIVE_ACCEPTANCE_GATE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate gate identity and criterion coverage."""

        object.__setattr__(self, "gate_id", _text(self.gate_id, "gate_id"))
        object.__setattr__(self, "description", _text(self.description, "description"))
        object.__setattr__(
            self,
            "required_criterion_ids",
            _unique_text(
                self.required_criterion_ids,
                label="gate required_criterion_id",
            ),
        )
        if not self.required_criterion_ids:
            raise ValueError("Acceptance gates require criterion ids.")
        object.__setattr__(
            self, "schema_version", _text(self.schema_version, "schema_version")
        )

    @property
    def gate_key(self) -> str:
        """Return deterministic uniqueness key."""

        return self.gate_id

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic export payload."""

        return {
            "blocking": self.blocking,
            "description": self.description,
            "gate_id": self.gate_id,
            "gate_kind": self.gate_kind.value,
            "required_criterion_ids": list(self.required_criterion_ids),
            "schema_version": self.schema_version,
        }


@dataclass(frozen=True, slots=True)
class WaveFiveExternalProtocolManifest:
    """Preregistered protocol manifest for independent Wave 5 validation."""

    protocol_id: str
    title: str
    owner: str
    registration_state: WaveFiveProtocolRegistrationState
    domains: tuple[WaveFiveProtocolDomain, ...]
    criteria: tuple[WaveFiveProtocolCriterion, ...]
    acceptance_gates: tuple[WaveFiveAcceptanceGate, ...]
    required_artifact_kinds: tuple[WaveFiveArtifactKind, ...]
    required_capability_areas: tuple[WaveFiveCapabilityArea, ...]
    forbidden_shortcuts: tuple[str, ...]
    external_reviewer_requirements: tuple[str, ...]
    reproduction_requirements: tuple[str, ...]
    claim_boundaries: tuple[WaveFiveClaimBoundary, ...] = (
        WAVE_FIVE_REQUIRED_CLAIM_BOUNDARIES
    )
    source_system: WaveFiveSourceSystem = (
        WaveFiveSourceSystem.EXTERNAL_VALIDATION_PROTOCOL
    )
    notes: tuple[str, ...] = ()
    schema_version: str = WAVE_FIVE_EXTERNAL_PROTOCOL_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate protocol coverage, falsifiability, and overclaim barriers."""

        object.__setattr__(self, "protocol_id", _text(self.protocol_id, "protocol_id"))
        object.__setattr__(self, "title", _text(self.title, "title"))
        object.__setattr__(self, "owner", _text(self.owner, "owner"))
        object.__setattr__(
            self,
            "domains",
            _unique_enum(self.domains, label="protocol domain"),
        )
        if not self.domains:
            raise ValueError("External protocol manifests require domains.")
        criteria = tuple(sorted(self.criteria, key=lambda item: item.criterion_key))
        gates = tuple(sorted(self.acceptance_gates, key=lambda item: item.gate_key))
        if not criteria:
            raise ValueError("External protocol manifests require criteria.")
        if not gates:
            raise ValueError("External protocol manifests require acceptance gates.")
        criterion_ids = _unique_values(
            (criterion.criterion_id for criterion in criteria), label="criterion_id"
        )
        _unique_values((gate.gate_id for gate in gates), label="gate_id")
        for gate in gates:
            for criterion_id in gate.required_criterion_ids:
                if criterion_id not in criterion_ids:
                    raise ValueError(
                        "Acceptance gates must reference manifest criteria: "
                        f"{criterion_id}"
                    )
        object.__setattr__(self, "criteria", criteria)
        object.__setattr__(self, "acceptance_gates", gates)
        object.__setattr__(
            self,
            "required_artifact_kinds",
            _unique_enum(self.required_artifact_kinds, label="artifact kind"),
        )
        object.__setattr__(
            self,
            "required_capability_areas",
            _unique_enum(
                self.required_capability_areas, label="capability area"
            ),
        )
        if not self.required_artifact_kinds:
            raise ValueError("External protocols require artifact kinds.")
        if not self.required_capability_areas:
            raise ValueError("External protocols require capability areas.")
        object.__setattr__(
            self,
            "forbidden_shortcuts",
            _unique_text(self.forbidden_shortcuts, label="forbidden shortcut"),
        )
        object.__setattr__(
            self,
            "external_reviewer_requirements",
            _unique_text(
                self.external_reviewer_requirements,
                label="external reviewer requirement",
            ),
        )
        object.__setattr__(
            self,
            "reproduction_requirements",
            _unique_text(
                self.reproduction_requirements, label="reproduction requirement"
            ),
        )
        if not self.forbidden_shortcuts:
            raise ValueError("External protocols require forbidden shortcuts.")
        if not self.external_reviewer_requirements:
            raise ValueError("External protocols require reviewer requirements.")
        if not self.reproduction_requirements:
            raise ValueError("External protocols require reproduction requirements.")
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
                "External protocol manifests must preserve claim boundary: "
                f"{missing_boundaries[0].value}"
            )
        object.__setattr__(
            self, "notes", _unique_text(self.notes, label="protocol note")
        )
        object.__setattr__(
            self, "schema_version", _text(self.schema_version, "schema_version")
        )
        if (
            self.registration_state
            is WaveFiveProtocolRegistrationState.DRAFT_INTERNAL
            and self.source_system
            is not WaveFiveSourceSystem.IX_COGNITION_KERNEL
        ):
            raise ValueError("Draft internal protocols must come from Kernel.")
        if self.is_externally_preregistered and self.source_system not in {
            WaveFiveSourceSystem.EXTERNAL_VALIDATION_PROTOCOL,
            WaveFiveSourceSystem.INDEPENDENT_REVIEWER,
            WaveFiveSourceSystem.INDEPENDENT_REPLICATION_LAB,
        }:
            raise ValueError(
                "Externally preregistered protocols require an external source system."
            )

    @property
    def is_externally_preregistered(self) -> bool:
        """Return whether the protocol is beyond internal drafting."""

        return self.registration_state in {
            WaveFiveProtocolRegistrationState.PREREGISTERED_EXTERNAL,
            WaveFiveProtocolRegistrationState.UNDER_EXTERNAL_REVIEW,
            WaveFiveProtocolRegistrationState.ACCEPTED_FOR_EXECUTION,
        }

    @property
    def criterion_ids(self) -> tuple[str, ...]:
        """Return criterion ids in deterministic order."""

        return tuple(criterion.criterion_id for criterion in self.criteria)

    @property
    def acceptance_gate_ids(self) -> tuple[str, ...]:
        """Return acceptance gate ids in deterministic order."""

        return tuple(gate.gate_id for gate in self.acceptance_gates)

    @property
    def missing_required_domains(self) -> tuple[WaveFiveProtocolDomain, ...]:
        """Return locked Wave 5 domains absent from this protocol."""

        return tuple(
            domain
            for domain in REQUIRED_WAVE_FIVE_PROTOCOL_DOMAINS
            if domain not in self.domains
        )

    @property
    def missing_required_acceptance_gates(
        self,
    ) -> tuple[WaveFiveAcceptanceGateKind, ...]:
        """Return required gate kinds absent from this protocol."""

        present = {gate.gate_kind for gate in self.acceptance_gates}
        return tuple(
            gate_kind
            for gate_kind in REQUIRED_WAVE_FIVE_ACCEPTANCE_GATES
            if gate_kind not in present
        )

    @property
    def has_required_domain_coverage(self) -> bool:
        """Return whether the protocol covers every locked Wave 5 domain."""

        return not self.missing_required_domains

    @property
    def has_required_gate_coverage(self) -> bool:
        """Return whether the protocol covers every locked Wave 5 gate kind."""

        return not self.missing_required_acceptance_gates

    @property
    def has_falsification_criteria(self) -> bool:
        """Return whether at least one criterion can falsify the protocol."""

        return any(
            criterion.criterion_kind is WaveFiveProtocolCriterionKind.FALSIFICATION
            for criterion in self.criteria
        )

    @property
    def has_negative_controls(self) -> bool:
        """Return whether the protocol includes negative controls."""

        return any(
            criterion.criterion_kind is WaveFiveProtocolCriterionKind.NEGATIVE_CONTROL
            for criterion in self.criteria
        )

    @property
    def ready_for_independent_execution(self) -> bool:
        """Return whether protocol can be executed by independent validators."""

        return (
            self.is_externally_preregistered
            and self.has_required_domain_coverage
            and self.has_required_gate_coverage
            and self.has_falsification_criteria
            and self.has_negative_controls
            and bool(self.external_reviewer_requirements)
            and bool(self.reproduction_requirements)
            and bool(self.forbidden_shortcuts)
        )

    @property
    def blocking_gates(self) -> tuple[str, ...]:
        """Return blocking gate ids."""

        return tuple(gate.gate_id for gate in self.acceptance_gates if gate.blocking)

    @property
    def evidence_ids(self) -> tuple[str, ...]:
        """Return unique evidence ids required by all criteria."""

        evidence_ids: list[str] = []
        seen: set[str] = set()
        for criterion in self.criteria:
            for evidence_id in criterion.required_evidence_ids:
                if evidence_id not in seen:
                    evidence_ids.append(evidence_id)
                    seen.add(evidence_id)
        return tuple(evidence_ids)

    def to_artifact_ref(self) -> WaveFiveArtifactRef:
        """Return this protocol manifest as a Wave 5 artifact reference."""

        decision = WaveFiveArtifactDecision.READY_FOR_INDEPENDENT_REVIEW
        validation_status = WaveFiveValidationStatus.UNDER_INDEPENDENT_REVIEW
        authority_state = WaveFiveAuthorityState.HUMAN_REVIEW_REQUIRED
        if self.registration_state is WaveFiveProtocolRegistrationState.REJECTED:
            decision = WaveFiveArtifactDecision.BLOCKED
            validation_status = WaveFiveValidationStatus.REJECTED
            authority_state = WaveFiveAuthorityState.BLOCKED
        elif not self.ready_for_independent_execution:
            decision = WaveFiveArtifactDecision.NEEDS_EXTERNAL_EVIDENCE
            validation_status = WaveFiveValidationStatus.MISSING_EXTERNAL_EVIDENCE
        return WaveFiveArtifactRef(
            artifact_id=self.protocol_id,
            kind=WaveFiveArtifactKind.EXTERNAL_PROTOCOL_MANIFEST,
            capability_area=WaveFiveCapabilityArea.EXTERNAL_PROTOCOLS,
            source_system=self.source_system,
            summary=self.title,
            produced_by_engine_id="wave5-external-protocol-engine",
            produced_by_agent_role_id="external-validation-registrar",
            evidence_ids=self.evidence_ids,
            decision=decision,
            authority_state=authority_state,
            validation_status=validation_status,
            claim_boundaries=self.claim_boundaries,
        )

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic export payload."""

        return {
            "acceptance_gates": [
                gate.canonical_payload() for gate in self.acceptance_gates
            ],
            "claim_boundaries": [boundary.value for boundary in self.claim_boundaries],
            "criteria": [criterion.canonical_payload() for criterion in self.criteria],
            "domains": [domain.value for domain in self.domains],
            "external_reviewer_requirements": list(
                self.external_reviewer_requirements
            ),
            "forbidden_shortcuts": list(self.forbidden_shortcuts),
            "notes": list(self.notes),
            "owner": self.owner,
            "protocol_id": self.protocol_id,
            "registration_state": self.registration_state.value,
            "reproduction_requirements": list(self.reproduction_requirements),
            "required_artifact_kinds": [
                kind.value for kind in self.required_artifact_kinds
            ],
            "required_capability_areas": [
                area.value for area in self.required_capability_areas
            ],
            "schema_version": self.schema_version,
            "source_system": self.source_system.value,
            "title": self.title,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this protocol."""

        return _stable_sha256(self.canonical_payload())


def required_wave_five_protocol_domains() -> tuple[WaveFiveProtocolDomain, ...]:
    """Return locked domains expected of a serious Wave 5 protocol."""

    return REQUIRED_WAVE_FIVE_PROTOCOL_DOMAINS


def required_wave_five_acceptance_gates() -> tuple[WaveFiveAcceptanceGateKind, ...]:
    """Return locked acceptance gates expected of Wave 5 protocols."""

    return REQUIRED_WAVE_FIVE_ACCEPTANCE_GATES


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
