"""Wave 4 release/closeout manifest records.

The release manifest is the final code-level Wave 4 closeout artifact before
README/public documentation. It records the completion receipt, source and test
component inventory, validation command results, evidence ids, scenario context,
and BlackFox receipt continuity. It remains a bounded engineering record: no
automatic execution, no automatic promotion, no AGI claim, no independent
validation claim, and no production-readiness claim.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Protocol, TypeVar

from ix_cognition_kernel.wave4_completion_receipt import (
    WaveFourCompletionReceiptStatus,
)
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

T = TypeVar("T")

WAVE_FOUR_RELEASE_COMPONENT_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave4-release-component-v1"
)
WAVE_FOUR_VALIDATION_COMMAND_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave4-validation-command-v1"
)
WAVE_FOUR_RELEASE_MANIFEST_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave4-release-manifest-v1"
)


class WaveFourReleaseComponentKind(StrEnum):
    """Component kinds required by a Wave 4 release manifest."""

    SOURCE_MODULE = "source-module"
    TEST_MODULE = "test-module"
    VALIDATION_COMMAND = "validation-command"
    COMPLETION_RECEIPT = "completion-receipt"
    REVIEW_DOCKET = "review-docket"
    README_PENDING = "readme-pending"


class WaveFourValidationCommandKind(StrEnum):
    """Validation command kinds tracked by the Wave 4 closeout manifest."""

    PYTEST = "pytest"
    RUFF = "ruff"
    MYPY = "mypy"
    PY_COMPILE = "py-compile"
    LINE_LENGTH_SCAN = "line-length-scan"


class WaveFourValidationResult(StrEnum):
    """Recorded validation result for one command."""

    PASSED = "passed"
    FAILED = "failed"
    NOT_RUN = "not-run"


class WaveFourReleaseManifestStatus(StrEnum):
    """Fail-closed status for a Wave 4 release manifest."""

    READY_FOR_CLOSEOUT = "ready-for-closeout"
    NEEDS_EVIDENCE = "needs-evidence"
    NEEDS_REPAIR = "needs-repair"
    BLOCKED = "blocked"


class WaveFourReleaseManifestDecision(StrEnum):
    """Bounded decision for the Wave 4 release manifest."""

    RECORD_CLOSEOUT = "record-closeout"
    HOLD_FOR_EVIDENCE = "hold-for-evidence"
    HOLD_FOR_REPAIR = "hold-for-repair"
    BLOCK_CLOSEOUT = "block-closeout"


REQUIRED_WAVE_FOUR_RELEASE_COMPONENT_KINDS: tuple[
    WaveFourReleaseComponentKind, ...
] = (
    WaveFourReleaseComponentKind.SOURCE_MODULE,
    WaveFourReleaseComponentKind.TEST_MODULE,
    WaveFourReleaseComponentKind.VALIDATION_COMMAND,
    WaveFourReleaseComponentKind.COMPLETION_RECEIPT,
    WaveFourReleaseComponentKind.REVIEW_DOCKET,
    WaveFourReleaseComponentKind.README_PENDING,
)

REQUIRED_WAVE_FOUR_VALIDATION_COMMAND_KINDS: tuple[
    WaveFourValidationCommandKind, ...
] = (
    WaveFourValidationCommandKind.PYTEST,
    WaveFourValidationCommandKind.RUFF,
    WaveFourValidationCommandKind.MYPY,
    WaveFourValidationCommandKind.PY_COMPILE,
    WaveFourValidationCommandKind.LINE_LENGTH_SCAN,
)

WAVE_FOUR_CLOSEOUT_SOURCE_PATHS: tuple[str, ...] = (
    "src/ix_cognition_kernel/wave4_contracts.py",
    "src/ix_cognition_kernel/wave4_trials.py",
    "src/ix_cognition_kernel/wave4_transfer.py",
    "src/ix_cognition_kernel/wave4_failure_repair.py",
    "src/ix_cognition_kernel/wave4_repair_suite.py",
    "src/ix_cognition_kernel/wave4_mission_state.py",
    "src/ix_cognition_kernel/wave4_uncertainty.py",
    "src/ix_cognition_kernel/wave4_safe_refusal.py",
    "src/ix_cognition_kernel/wave4_reward_audit.py",
    "src/ix_cognition_kernel/wave4_adversarial_robustness.py",
    "src/ix_cognition_kernel/wave4_audit_trail.py",
    "src/ix_cognition_kernel/wave4_proto_candidate.py",
    "src/ix_cognition_kernel/wave4_scorecard.py",
    "src/ix_cognition_kernel/wave4_review_packet.py",
    "src/ix_cognition_kernel/wave4_maturity_declaration.py",
    "src/ix_cognition_kernel/wave4_review_docket.py",
    "src/ix_cognition_kernel/wave4_completion_receipt.py",
    "src/ix_cognition_kernel/wave4_release_manifest.py",
)

WAVE_FOUR_CLOSEOUT_TEST_PATHS: tuple[str, ...] = (
    "tests/test_wave4_contracts.py",
    "tests/test_wave4_trials.py",
    "tests/test_wave4_transfer.py",
    "tests/test_wave4_failure_repair.py",
    "tests/test_wave4_repair_suite.py",
    "tests/test_wave4_mission_state.py",
    "tests/test_wave4_uncertainty.py",
    "tests/test_wave4_safe_refusal.py",
    "tests/test_wave4_reward_audit.py",
    "tests/test_wave4_adversarial_robustness.py",
    "tests/test_wave4_audit_trail.py",
    "tests/test_wave4_proto_candidate.py",
    "tests/test_wave4_scorecard.py",
    "tests/test_wave4_review_packet.py",
    "tests/test_wave4_maturity_declaration.py",
    "tests/test_wave4_review_docket.py",
    "tests/test_wave4_completion_receipt.py",
    "tests/test_wave4_release_manifest.py",
)


class WaveFourCompletionReceiptLike(Protocol):
    """Structural protocol for completion receipt fields used by the manifest."""

    receipt_id: str
    artifact_id: str
    status: WaveFourCompletionReceiptStatus
    receipt_digest: str
    all_evidence_ids: tuple[str, ...]
    readiness_gaps: tuple[str, ...]
    blocking_gaps: tuple[str, ...]
    permits_automatic_execution: bool
    permits_automatic_promotion: bool
    claims_agi: bool
    independently_validated: bool
    production_ready: bool


@dataclass(frozen=True, slots=True)
class WaveFourReleaseComponent:
    """One source, test, or closeout component in the Wave 4 manifest."""

    component_id: str
    component_kind: WaveFourReleaseComponentKind
    path: str
    summary: str
    evidence_ids: tuple[str, ...]
    required: bool = True
    schema_version: str = WAVE_FOUR_RELEASE_COMPONENT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate component identity, path, and evidence binding."""

        object.__setattr__(
            self,
            "component_id",
            _text(self.component_id, "component_id"),
        )
        object.__setattr__(self, "path", _text(self.path, "path"))
        object.__setattr__(self, "summary", _text(self.summary, "summary"))
        object.__setattr__(
            self,
            "evidence_ids",
            _unique_text(self.evidence_ids, label="component evidence_id"),
        )
        if self.required and not self.evidence_ids:
            raise ValueError("Required Wave 4 release components require evidence ids.")
        object.__setattr__(
            self,
            "schema_version",
            _text(self.schema_version, "schema_version"),
        )

    @property
    def component_key(self) -> str:
        """Return deterministic uniqueness key."""

        return self.component_id

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic component payload."""

        return {
            "component_id": self.component_id,
            "component_kind": self.component_kind.value,
            "evidence_ids": list(self.evidence_ids),
            "path": self.path,
            "required": self.required,
            "schema_version": self.schema_version,
            "summary": self.summary,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint."""

        return _stable_sha256(self.canonical_payload())


@dataclass(frozen=True, slots=True)
class WaveFourValidationCommandRecord:
    """One validation command and its recorded closeout result."""

    command_id: str
    command_kind: WaveFourValidationCommandKind
    command: str
    expected_gate: str
    result: WaveFourValidationResult
    evidence_ids: tuple[str, ...]
    failure_summary: str = ""
    schema_version: str = WAVE_FOUR_VALIDATION_COMMAND_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate command identity, evidence, and result accounting."""

        object.__setattr__(self, "command_id", _text(self.command_id, "command_id"))
        object.__setattr__(self, "command", _text(self.command, "command"))
        object.__setattr__(
            self,
            "expected_gate",
            _text(self.expected_gate, "expected_gate"),
        )
        object.__setattr__(
            self,
            "evidence_ids",
            _unique_text(self.evidence_ids, label="validation evidence_id"),
        )
        if not self.evidence_ids:
            raise ValueError("Wave 4 validation command records require evidence ids.")
        object.__setattr__(self, "failure_summary", self.failure_summary.strip())
        object.__setattr__(
            self,
            "schema_version",
            _text(self.schema_version, "schema_version"),
        )
        if self.result is WaveFourValidationResult.PASSED and self.failure_summary:
            raise ValueError("Passed Wave 4 validation commands cannot carry failure.")
        if self.result is WaveFourValidationResult.FAILED and not self.failure_summary:
            raise ValueError("Failed Wave 4 validation commands require failure text.")

    @property
    def command_key(self) -> str:
        """Return deterministic uniqueness key."""

        return self.command_id

    @property
    def readiness_gap(self) -> str:
        """Return fail-closed validation gap text."""

        if self.result is WaveFourValidationResult.PASSED:
            return ""
        if self.result is WaveFourValidationResult.NOT_RUN:
            return f"{self.command_id} was not run"
        return f"{self.command_id} failed: {self.failure_summary}"

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic validation command payload."""

        return {
            "command": self.command,
            "command_id": self.command_id,
            "command_kind": self.command_kind.value,
            "evidence_ids": list(self.evidence_ids),
            "expected_gate": self.expected_gate,
            "failure_summary": self.failure_summary,
            "readiness_gap": self.readiness_gap,
            "result": self.result.value,
            "schema_version": self.schema_version,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint."""

        return _stable_sha256(self.canonical_payload())


@dataclass(frozen=True, slots=True)
class WaveFourReleaseManifest:
    """Bounded Wave 4 closeout manifest for source, tests, and validation."""

    manifest_id: str
    completion_receipt: WaveFourCompletionReceiptLike
    components: tuple[WaveFourReleaseComponent, ...]
    validation_commands: tuple[WaveFourValidationCommandRecord, ...]
    scenario_ids: tuple[str, ...]
    blackfox_receipt_ids: tuple[str, ...]
    generated_by_engine_id: str = "wave4-release-manifest-engine"
    release_notes: tuple[str, ...] = ()
    blocked_reasons: tuple[str, ...] = ()
    required_component_kinds: tuple[WaveFourReleaseComponentKind, ...] = (
        REQUIRED_WAVE_FOUR_RELEASE_COMPONENT_KINDS
    )
    required_validation_command_kinds: tuple[WaveFourValidationCommandKind, ...] = (
        REQUIRED_WAVE_FOUR_VALIDATION_COMMAND_KINDS
    )
    permits_automatic_execution: bool = False
    permits_automatic_promotion: bool = False
    claims_agi: bool = False
    independently_validated: bool = False
    production_ready: bool = False
    schema_version: str = WAVE_FOUR_RELEASE_MANIFEST_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate closeout inventory, validation records, and boundaries."""

        object.__setattr__(self, "manifest_id", _text(self.manifest_id, "manifest_id"))
        if not self.components:
            raise ValueError("Wave 4 release manifests require components.")
        components = tuple(
            sorted(self.components, key=lambda item: item.component_key)
        )
        _unique_items((item.component_id for item in components), "component_id")
        object.__setattr__(self, "components", components)
        if not self.validation_commands:
            raise ValueError("Wave 4 release manifests require validation commands.")
        commands = tuple(
            sorted(self.validation_commands, key=lambda item: item.command_key)
        )
        _unique_items((item.command_id for item in commands), "command_id")
        object.__setattr__(self, "validation_commands", commands)
        object.__setattr__(
            self,
            "scenario_ids",
            _unique_text(self.scenario_ids, label="scenario_id"),
        )
        object.__setattr__(
            self,
            "blackfox_receipt_ids",
            _unique_text(self.blackfox_receipt_ids, label="blackfox receipt_id"),
        )
        object.__setattr__(
            self,
            "generated_by_engine_id",
            _text(self.generated_by_engine_id, "generated_by_engine_id"),
        )
        object.__setattr__(
            self,
            "release_notes",
            _unique_text(self.release_notes, label="release note"),
        )
        object.__setattr__(
            self,
            "blocked_reasons",
            _unique_text(self.blocked_reasons, label="blocked reason"),
        )
        object.__setattr__(
            self,
            "required_component_kinds",
            _unique_items(self.required_component_kinds, "required component kind"),
        )
        object.__setattr__(
            self,
            "required_validation_command_kinds",
            _unique_items(
                self.required_validation_command_kinds,
                "required validation command kind",
            ),
        )
        object.__setattr__(
            self,
            "schema_version",
            _text(self.schema_version, "schema_version"),
        )
        if self.permits_automatic_execution:
            raise ValueError("Wave 4 release manifests cannot permit execution.")
        if self.permits_automatic_promotion:
            raise ValueError("Wave 4 release manifests cannot permit promotion.")
        if self.claims_agi:
            raise ValueError("Wave 4 release manifests cannot claim AGI.")
        if self.independently_validated:
            raise ValueError(
                "Wave 4 release manifests cannot claim independent validation."
            )
        if self.production_ready:
            raise ValueError(
                "Wave 4 release manifests cannot claim production readiness."
            )

    @property
    def artifact_id(self) -> str:
        """Return shared Wave 4 artifact id for this manifest."""

        return f"wave4-release-manifest:{self.manifest_id}"

    @property
    def component_ids(self) -> tuple[str, ...]:
        """Return component ids in deterministic order."""

        return tuple(component.component_id for component in self.components)

    @property
    def command_ids(self) -> tuple[str, ...]:
        """Return validation command ids in deterministic order."""

        return tuple(command.command_id for command in self.validation_commands)

    @property
    def component_kinds_present(self) -> tuple[WaveFourReleaseComponentKind, ...]:
        """Return component kinds represented by this manifest."""

        return tuple(
            sorted(
                {component.component_kind for component in self.components},
                key=lambda item: item.value,
            )
        )

    @property
    def validation_command_kinds_present(
        self,
    ) -> tuple[WaveFourValidationCommandKind, ...]:
        """Return validation command kinds represented by this manifest."""

        return tuple(
            sorted(
                {command.command_kind for command in self.validation_commands},
                key=lambda item: item.value,
            )
        )

    @property
    def missing_required_component_kinds(
        self,
    ) -> tuple[WaveFourReleaseComponentKind, ...]:
        """Return required component kinds not represented."""

        present = set(self.component_kinds_present)
        return tuple(
            kind for kind in self.required_component_kinds if kind not in present
        )

    @property
    def missing_required_validation_command_kinds(
        self,
    ) -> tuple[WaveFourValidationCommandKind, ...]:
        """Return required validation command kinds not represented."""

        present = set(self.validation_command_kinds_present)
        return tuple(
            kind
            for kind in self.required_validation_command_kinds
            if kind not in present
        )

    @property
    def failed_command_ids(self) -> tuple[str, ...]:
        """Return validation commands that failed."""

        return tuple(
            command.command_id
            for command in self.validation_commands
            if command.result is WaveFourValidationResult.FAILED
        )

    @property
    def not_run_command_ids(self) -> tuple[str, ...]:
        """Return validation commands recorded as not run."""

        return tuple(
            command.command_id
            for command in self.validation_commands
            if command.result is WaveFourValidationResult.NOT_RUN
        )

    @property
    def all_evidence_ids(self) -> tuple[str, ...]:
        """Return sorted evidence ids from receipt, components, and commands."""

        evidence_ids = set(self.completion_receipt.all_evidence_ids)
        for component in self.components:
            evidence_ids.update(component.evidence_ids)
        for command in self.validation_commands:
            evidence_ids.update(command.evidence_ids)
        return tuple(sorted(evidence_ids))

    @property
    def release_digest(self) -> str:
        """Return deterministic release manifest digest."""

        return _stable_sha256(
            {
                "completion_receipt_digest": self.completion_receipt.receipt_digest,
                "components": [item.fingerprint() for item in self.components],
                "manifest_id": self.manifest_id,
                "validation": [
                    item.fingerprint() for item in self.validation_commands
                ],
            }
        )

    @property
    def readiness_gaps(self) -> tuple[str, ...]:
        """Return fail-closed gaps preventing closeout."""

        gaps: list[str] = []
        if self.completion_receipt.status is not (
            WaveFourCompletionReceiptStatus.READY_FOR_WAVE_FOUR_RECORD
        ):
            gaps.extend(self.completion_receipt.readiness_gaps)
        if self.missing_required_component_kinds:
            missing = ", ".join(
                kind.value for kind in self.missing_required_component_kinds
            )
            gaps.append(f"missing release component coverage: {missing}")
        if self.missing_required_validation_command_kinds:
            missing = ", ".join(
                kind.value for kind in self.missing_required_validation_command_kinds
            )
            gaps.append(f"missing validation command coverage: {missing}")
        for command in self.validation_commands:
            if command.readiness_gap:
                gaps.append(command.readiness_gap)
        if not self.scenario_ids:
            gaps.append(f"{self.manifest_id} has no WorldTwin scenario ids")
        if not self.blackfox_receipt_ids:
            gaps.append(f"{self.manifest_id} has no BlackFox receipt ids")
        return tuple(gaps)

    @property
    def blocking_gaps(self) -> tuple[str, ...]:
        """Return hard blocks for this release manifest."""

        gaps = [
            f"{self.manifest_id} blocked: {reason}"
            for reason in self.blocked_reasons
        ]
        gaps.extend(self.completion_receipt.blocking_gaps)
        return tuple(gaps)

    @property
    def status(self) -> WaveFourReleaseManifestStatus:
        """Return fail-closed closeout status."""

        if self.blocking_gaps:
            return WaveFourReleaseManifestStatus.BLOCKED
        if (
            self.failed_command_ids
            or self.completion_receipt.status
            is WaveFourCompletionReceiptStatus.NEEDS_REPAIR
        ):
            return WaveFourReleaseManifestStatus.NEEDS_REPAIR
        if self.readiness_gaps:
            return WaveFourReleaseManifestStatus.NEEDS_EVIDENCE
        return WaveFourReleaseManifestStatus.READY_FOR_CLOSEOUT

    @property
    def decision(self) -> WaveFourReleaseManifestDecision:
        """Return bounded release-manifest decision."""

        if self.status is WaveFourReleaseManifestStatus.BLOCKED:
            return WaveFourReleaseManifestDecision.BLOCK_CLOSEOUT
        if self.status is WaveFourReleaseManifestStatus.NEEDS_REPAIR:
            return WaveFourReleaseManifestDecision.HOLD_FOR_REPAIR
        if self.status is WaveFourReleaseManifestStatus.NEEDS_EVIDENCE:
            return WaveFourReleaseManifestDecision.HOLD_FOR_EVIDENCE
        return WaveFourReleaseManifestDecision.RECORD_CLOSEOUT

    @property
    def ready_for_closeout(self) -> bool:
        """Return whether this manifest can be recorded as Wave 4 closeout."""

        return self.status is WaveFourReleaseManifestStatus.READY_FOR_CLOSEOUT

    @property
    def human_authority_state(self) -> WaveFourAuthorityState:
        """Return human-authority state for this manifest."""

        if self.status is WaveFourReleaseManifestStatus.BLOCKED:
            return WaveFourAuthorityState.BLOCKED
        return WaveFourAuthorityState.HUMAN_REVIEW_REQUIRED

    @property
    def review_summary(self) -> str:
        """Return concise release-manifest summary."""

        return (
            f"{self.manifest_id}: {len(self.components)} components; "
            f"{len(self.validation_commands)} validation commands; "
            f"{self.status.value}; digest {self.release_digest[:12]}; "
            "README remains final documentation step; no AGI claim."
        )

    def to_artifact_ref(self) -> WaveFourArtifactRef:
        """Convert this manifest into a shared Wave 4 readiness artifact."""

        if self.status is WaveFourReleaseManifestStatus.READY_FOR_CLOSEOUT:
            decision = WaveFourArtifactDecision.READY_FOR_CONTROLLED_REVIEW
        elif self.status is WaveFourReleaseManifestStatus.BLOCKED:
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
            produced_by_agent_role_id="wave4-release-manifest-builder",
            evidence_ids=self.all_evidence_ids,
            decision=decision,
            authority_state=self.human_authority_state,
        )

    def evidence_links(self) -> tuple[WaveFourEvidenceLink, ...]:
        """Return evidence links for this manifest artifact."""

        relation = WaveFourEvidenceRelation.TESTS
        if self.status is WaveFourReleaseManifestStatus.BLOCKED:
            relation = WaveFourEvidenceRelation.BLOCKS
        return tuple(
            WaveFourEvidenceLink(
                evidence_id=evidence_id,
                artifact_id=self.artifact_id,
                relation=relation,
                summary=f"Evidence for Wave 4 release manifest {self.manifest_id}.",
                source_system=WaveFourSourceSystem.LOCAL_TEST_SUITE,
            )
            for evidence_id in self.all_evidence_ids
        )

    def to_artifact_bundle(self) -> WaveFourArtifactBundle:
        """Convert this manifest into a one-artifact Wave 4 bundle."""

        return WaveFourArtifactBundle(
            bundle_id=f"wave4-release-manifest-bundle:{self.manifest_id}",
            artifacts=(self.to_artifact_ref(),),
            evidence_links=self.evidence_links(),
            required_kinds=(WaveFourArtifactKind.READINESS_SNAPSHOT,),
            required_capability_areas=(WaveFourCapabilityArea.AUDIT_TRAIL,),
            notes=(self.review_summary, *self.release_notes),
        )

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic release-manifest payload."""

        return {
            "all_evidence_ids": list(self.all_evidence_ids),
            "artifact_id": self.artifact_id,
            "blackfox_receipt_ids": list(self.blackfox_receipt_ids),
            "blocking_gaps": list(self.blocking_gaps),
            "blocked_reasons": list(self.blocked_reasons),
            "command_ids": list(self.command_ids),
            "component_ids": list(self.component_ids),
            "component_kinds_present": [
                kind.value for kind in self.component_kinds_present
            ],
            "components": [item.canonical_payload() for item in self.components],
            "claims_agi": self.claims_agi,
            "completion_receipt_id": self.completion_receipt.receipt_id,
            "decision": self.decision.value,
            "failed_command_ids": list(self.failed_command_ids),
            "human_authority_state": self.human_authority_state.value,
            "independently_validated": self.independently_validated,
            "manifest_id": self.manifest_id,
            "missing_required_component_kinds": [
                kind.value for kind in self.missing_required_component_kinds
            ],
            "missing_required_validation_command_kinds": [
                kind.value
                for kind in self.missing_required_validation_command_kinds
            ],
            "not_run_command_ids": list(self.not_run_command_ids),
            "permits_automatic_execution": self.permits_automatic_execution,
            "permits_automatic_promotion": self.permits_automatic_promotion,
            "production_ready": self.production_ready,
            "readiness_gaps": list(self.readiness_gaps),
            "release_digest": self.release_digest,
            "release_notes": list(self.release_notes),
            "review_summary": self.review_summary,
            "scenario_ids": list(self.scenario_ids),
            "schema_version": self.schema_version,
            "status": self.status.value,
            "validation_command_kinds_present": [
                kind.value for kind in self.validation_command_kinds_present
            ],
            "validation_commands": [
                item.canonical_payload() for item in self.validation_commands
            ],
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint."""

        return _stable_sha256(self.canonical_payload())


def release_component(
    *,
    component_id: str,
    component_kind: WaveFourReleaseComponentKind,
    path: str,
    summary: str,
    evidence_id: str,
) -> WaveFourReleaseComponent:
    """Build one required Wave 4 release component."""

    return WaveFourReleaseComponent(
        component_id=component_id,
        component_kind=component_kind,
        path=path,
        summary=summary,
        evidence_ids=(evidence_id,),
    )


def passed_validation_command(
    *,
    command_id: str,
    command_kind: WaveFourValidationCommandKind,
    command: str,
    expected_gate: str,
    evidence_id: str,
) -> WaveFourValidationCommandRecord:
    """Build a passed validation command record."""

    return WaveFourValidationCommandRecord(
        command_id=command_id,
        command_kind=command_kind,
        command=command,
        expected_gate=expected_gate,
        result=WaveFourValidationResult.PASSED,
        evidence_ids=(evidence_id,),
    )


def build_wave_four_release_manifest(
    *,
    manifest_id: str,
    completion_receipt: WaveFourCompletionReceiptLike,
    validation_commands: tuple[WaveFourValidationCommandRecord, ...],
    scenario_ids: tuple[str, ...],
    blackfox_receipt_ids: tuple[str, ...],
) -> WaveFourReleaseManifest:
    """Build the standard Wave 4 closeout manifest."""

    components = (
        *(
            release_component(
                component_id=f"source:{path}",
                component_kind=WaveFourReleaseComponentKind.SOURCE_MODULE,
                path=path,
                summary="Wave 4 source module included in closeout inventory.",
                evidence_id=f"evidence:{path}",
            )
            for path in WAVE_FOUR_CLOSEOUT_SOURCE_PATHS
        ),
        *(
            release_component(
                component_id=f"test:{path}",
                component_kind=WaveFourReleaseComponentKind.TEST_MODULE,
                path=path,
                summary="Wave 4 test module included in closeout inventory.",
                evidence_id=f"evidence:{path}",
            )
            for path in WAVE_FOUR_CLOSEOUT_TEST_PATHS
        ),
        release_component(
            component_id="component:validation-commands",
            component_kind=WaveFourReleaseComponentKind.VALIDATION_COMMAND,
            path="validation:wave4-closeout",
            summary="Wave 4 closeout validation commands are recorded.",
            evidence_id="evidence:validation:wave4-closeout",
        ),
        release_component(
            component_id="component:completion-receipt",
            component_kind=WaveFourReleaseComponentKind.COMPLETION_RECEIPT,
            path=completion_receipt.artifact_id,
            summary="Wave 4 completion receipt is attached.",
            evidence_id="evidence:completion-receipt",
        ),
        release_component(
            component_id="component:review-docket",
            component_kind=WaveFourReleaseComponentKind.REVIEW_DOCKET,
            path="wave4-human-review-docket",
            summary="Wave 4 human-review docket is represented by receipt evidence.",
            evidence_id="evidence:review-docket",
        ),
        release_component(
            component_id="component:readme-pending",
            component_kind=WaveFourReleaseComponentKind.README_PENDING,
            path="README.md",
            summary="README remains the final documentation commit.",
            evidence_id="evidence:readme-pending",
        ),
    )
    return WaveFourReleaseManifest(
        manifest_id=manifest_id,
        completion_receipt=completion_receipt,
        components=components,
        validation_commands=validation_commands,
        scenario_ids=scenario_ids,
        blackfox_receipt_ids=blackfox_receipt_ids,
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

    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return hashlib.sha256(encoded).hexdigest()
