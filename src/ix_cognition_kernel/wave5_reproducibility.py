"""Wave 5 reproducible evidence bundle records.

Wave 5 needs evidence that another reviewer can replay, inspect, dispute, or
reject. This module models deterministic evidence bundles: command records,
source/test/output digests, replay checks, environment notes, and reproduction
gaps. The records prepare independent replication without pretending an internal
clean test run is independent validation.
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

WAVE_FIVE_COMMAND_RECORD_SCHEMA_VERSION = "ix-cognition-kernel-wave5-command-record-v1"
WAVE_FIVE_DIGEST_RECORD_SCHEMA_VERSION = "ix-cognition-kernel-wave5-digest-record-v1"
WAVE_FIVE_REPLAY_CHECK_SCHEMA_VERSION = "ix-cognition-kernel-wave5-replay-check-v1"
WAVE_FIVE_REPRODUCTION_GAP_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave5-reproduction-gap-v1"
)
WAVE_FIVE_REPRODUCIBLE_BUNDLE_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave5-reproducible-bundle-v1"
)


class WaveFiveCommandOutcome(StrEnum):
    """Observed outcome of a replayable command."""

    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    NOT_RUN = "not-run"


class WaveFiveDigestKind(StrEnum):
    """Kinds of digests bound into a reproducible evidence bundle."""

    SOURCE_TREE = "source-tree"
    TEST_TREE = "test-tree"
    OUTPUT_ARTIFACT = "output-artifact"
    ENVIRONMENT_LOCK = "environment-lock"
    COMMAND_LOG = "command-log"


class WaveFiveHashAlgorithm(StrEnum):
    """Supported deterministic digest algorithms."""

    SHA256 = "sha256"


class WaveFiveReplayCheckKind(StrEnum):
    """Replay checks required before an evidence bundle is reviewable."""

    CLEAN_CHECKOUT = "clean-checkout"
    ENVIRONMENT_CAPTURE = "environment-capture"
    SOURCE_FINGERPRINT = "source-fingerprint"
    TEST_FINGERPRINT = "test-fingerprint"
    COMMAND_REPLAY = "command-replay"
    OUTPUT_DIGEST = "output-digest"
    FAILURE_CAPTURE = "failure-capture"


class WaveFiveReproductionGapSeverity(StrEnum):
    """Severity of gaps discovered during reproduction."""

    INFO = "info"
    WARNING = "warning"
    BLOCKING = "blocking"


class WaveFiveReproductionStatus(StrEnum):
    """Current status of the reproducible evidence bundle."""

    INTERNAL_REPLAY_READY = "internal-replay-ready"
    NEEDS_EXTERNAL_REPRODUCTION = "needs-external-reproduction"
    UNDER_EXTERNAL_REPRODUCTION = "under-external-reproduction"
    EXTERNALLY_REPRODUCED = "externally-reproduced"
    REPRODUCTION_FAILED = "reproduction-failed"
    STALE = "stale"


REQUIRED_WAVE_FIVE_REPLAY_CHECKS: tuple[WaveFiveReplayCheckKind, ...] = (
    WaveFiveReplayCheckKind.CLEAN_CHECKOUT,
    WaveFiveReplayCheckKind.ENVIRONMENT_CAPTURE,
    WaveFiveReplayCheckKind.SOURCE_FINGERPRINT,
    WaveFiveReplayCheckKind.TEST_FINGERPRINT,
    WaveFiveReplayCheckKind.COMMAND_REPLAY,
    WaveFiveReplayCheckKind.OUTPUT_DIGEST,
    WaveFiveReplayCheckKind.FAILURE_CAPTURE,
)

EXTERNAL_REPRODUCTION_SOURCE_SYSTEMS: tuple[WaveFiveSourceSystem, ...] = (
    WaveFiveSourceSystem.INDEPENDENT_REPLICATION_LAB,
    WaveFiveSourceSystem.EXTERNAL_REVIEW,
)


@dataclass(frozen=True, slots=True)
class WaveFiveCommandRecord:
    """One command that can be replayed by an external reviewer."""

    command_id: str
    command: tuple[str, ...]
    working_directory: str
    expected_exit_code: int
    observed_exit_code: int
    outcome: WaveFiveCommandOutcome
    stdout_digest: str
    stderr_digest: str
    evidence_ids: tuple[str, ...]
    schema_version: str = WAVE_FIVE_COMMAND_RECORD_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate command replay metadata."""

        object.__setattr__(self, "command_id", _text(self.command_id, "command_id"))
        object.__setattr__(
            self,
            "command",
            _unique_text(self.command, label="command argument", allow_duplicates=True),
        )
        if not self.command:
            raise ValueError("Command records require at least one command argument.")
        object.__setattr__(
            self,
            "working_directory",
            _text(self.working_directory, "working_directory"),
        )
        object.__setattr__(
            self,
            "stdout_digest",
            _sha256(self.stdout_digest, "stdout_digest"),
        )
        object.__setattr__(
            self,
            "stderr_digest",
            _sha256(self.stderr_digest, "stderr_digest"),
        )
        object.__setattr__(
            self, "evidence_ids", _unique_text(self.evidence_ids, label="evidence_id")
        )
        if not self.evidence_ids:
            raise ValueError("Command records require evidence ids.")
        if (
            self.outcome is WaveFiveCommandOutcome.PASSED
            and self.observed_exit_code != self.expected_exit_code
        ):
            raise ValueError("Passed commands must match the expected exit code.")
        if (
            self.outcome is WaveFiveCommandOutcome.FAILED
            and self.observed_exit_code == self.expected_exit_code
        ):
            raise ValueError("Failed commands must differ from the expected exit code.")
        object.__setattr__(
            self, "schema_version", _text(self.schema_version, "schema_version")
        )

    @property
    def command_key(self) -> str:
        """Return deterministic command key."""

        return self.command_id

    @property
    def passed(self) -> bool:
        """Return whether the command passed exactly as expected."""

        return (
            self.outcome is WaveFiveCommandOutcome.PASSED
            and self.observed_exit_code == self.expected_exit_code
        )

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic export payload."""

        return {
            "command": list(self.command),
            "command_id": self.command_id,
            "evidence_ids": list(self.evidence_ids),
            "expected_exit_code": self.expected_exit_code,
            "observed_exit_code": self.observed_exit_code,
            "outcome": self.outcome.value,
            "schema_version": self.schema_version,
            "stderr_digest": self.stderr_digest,
            "stdout_digest": self.stdout_digest,
            "working_directory": self.working_directory,
        }


@dataclass(frozen=True, slots=True)
class WaveFiveDigestRecord:
    """One deterministic digest bound to a reproducible bundle."""

    digest_id: str
    digest_kind: WaveFiveDigestKind
    path: str
    digest: str
    evidence_ids: tuple[str, ...]
    algorithm: WaveFiveHashAlgorithm = WaveFiveHashAlgorithm.SHA256
    schema_version: str = WAVE_FIVE_DIGEST_RECORD_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate digest metadata."""

        object.__setattr__(self, "digest_id", _text(self.digest_id, "digest_id"))
        object.__setattr__(self, "path", _text(self.path, "path"))
        object.__setattr__(self, "digest", _sha256(self.digest, "digest"))
        object.__setattr__(
            self, "evidence_ids", _unique_text(self.evidence_ids, label="evidence_id")
        )
        if not self.evidence_ids:
            raise ValueError("Digest records require evidence ids.")
        object.__setattr__(
            self, "schema_version", _text(self.schema_version, "schema_version")
        )

    @property
    def digest_key(self) -> str:
        """Return deterministic digest key."""

        return self.digest_id

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic export payload."""

        return {
            "algorithm": self.algorithm.value,
            "digest": self.digest,
            "digest_id": self.digest_id,
            "digest_kind": self.digest_kind.value,
            "evidence_ids": list(self.evidence_ids),
            "path": self.path,
            "schema_version": self.schema_version,
        }


@dataclass(frozen=True, slots=True)
class WaveFiveReplayCheck:
    """One replayability check inside a reproducible evidence bundle."""

    check_id: str
    check_kind: WaveFiveReplayCheckKind
    description: str
    passed: bool
    evidence_ids: tuple[str, ...]
    blocking: bool = True
    schema_version: str = WAVE_FIVE_REPLAY_CHECK_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate replay check identity and evidence binding."""

        object.__setattr__(self, "check_id", _text(self.check_id, "check_id"))
        object.__setattr__(self, "description", _text(self.description, "description"))
        object.__setattr__(
            self, "evidence_ids", _unique_text(self.evidence_ids, label="evidence_id")
        )
        if not self.evidence_ids:
            raise ValueError("Replay checks require evidence ids.")
        object.__setattr__(
            self, "schema_version", _text(self.schema_version, "schema_version")
        )

    @property
    def check_key(self) -> str:
        """Return deterministic replay-check key."""

        return self.check_id

    @property
    def blocks_reproduction(self) -> bool:
        """Return whether this check blocks reproduction."""

        return self.blocking and not self.passed

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic export payload."""

        return {
            "blocking": self.blocking,
            "check_id": self.check_id,
            "check_kind": self.check_kind.value,
            "description": self.description,
            "evidence_ids": list(self.evidence_ids),
            "passed": self.passed,
            "schema_version": self.schema_version,
        }


@dataclass(frozen=True, slots=True)
class WaveFiveReproductionGap:
    """One gap discovered while preparing or attempting reproduction."""

    gap_id: str
    severity: WaveFiveReproductionGapSeverity
    description: str
    mitigation: str
    evidence_ids: tuple[str, ...]
    schema_version: str = WAVE_FIVE_REPRODUCTION_GAP_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate reproduction-gap metadata."""

        object.__setattr__(self, "gap_id", _text(self.gap_id, "gap_id"))
        object.__setattr__(self, "description", _text(self.description, "description"))
        object.__setattr__(self, "mitigation", _text(self.mitigation, "mitigation"))
        object.__setattr__(
            self, "evidence_ids", _unique_text(self.evidence_ids, label="evidence_id")
        )
        if (
            self.severity is WaveFiveReproductionGapSeverity.BLOCKING
            and not self.evidence_ids
        ):
            raise ValueError("Blocking reproduction gaps require evidence ids.")
        object.__setattr__(
            self, "schema_version", _text(self.schema_version, "schema_version")
        )

    @property
    def gap_key(self) -> str:
        """Return deterministic gap key."""

        return self.gap_id

    @property
    def blocks_reproduction(self) -> bool:
        """Return whether this gap blocks external reproduction."""

        return self.severity is WaveFiveReproductionGapSeverity.BLOCKING

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic export payload."""

        return {
            "description": self.description,
            "evidence_ids": list(self.evidence_ids),
            "gap_id": self.gap_id,
            "mitigation": self.mitigation,
            "schema_version": self.schema_version,
            "severity": self.severity.value,
        }


@dataclass(frozen=True, slots=True)
class WaveFiveReproducibleEvidenceBundle:
    """Deterministic Wave 5 bundle for external reproduction."""

    bundle_id: str
    title: str
    source_system: WaveFiveSourceSystem
    reproduction_status: WaveFiveReproductionStatus
    protocol_ids: tuple[str, ...]
    command_records: tuple[WaveFiveCommandRecord, ...]
    digests: tuple[WaveFiveDigestRecord, ...]
    replay_checks: tuple[WaveFiveReplayCheck, ...]
    environment_notes: tuple[str, ...]
    reproduction_gaps: tuple[WaveFiveReproductionGap, ...] = ()
    claim_boundaries: tuple[WaveFiveClaimBoundary, ...] = (
        WAVE_FIVE_REQUIRED_CLAIM_BOUNDARIES
    )
    notes: tuple[str, ...] = ()
    schema_version: str = WAVE_FIVE_REPRODUCIBLE_BUNDLE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate reproducibility evidence and fail-closed blockers."""

        object.__setattr__(self, "bundle_id", _text(self.bundle_id, "bundle_id"))
        object.__setattr__(self, "title", _text(self.title, "title"))
        object.__setattr__(
            self, "protocol_ids", _unique_text(self.protocol_ids, label="protocol_id")
        )
        if not self.protocol_ids:
            raise ValueError("Reproducible bundles require protocol ids.")
        commands = tuple(
            sorted(self.command_records, key=lambda item: item.command_key)
        )
        digests = tuple(sorted(self.digests, key=lambda item: item.digest_key))
        checks = tuple(sorted(self.replay_checks, key=lambda item: item.check_key))
        gaps = tuple(sorted(self.reproduction_gaps, key=lambda item: item.gap_key))
        if not commands:
            raise ValueError("Reproducible bundles require command records.")
        if not digests:
            raise ValueError("Reproducible bundles require digest records.")
        if not checks:
            raise ValueError("Reproducible bundles require replay checks.")
        _unique_values((item.command_id for item in commands), label="command_id")
        _unique_values((item.digest_id for item in digests), label="digest_id")
        _unique_values((item.check_id for item in checks), label="check_id")
        _unique_values((item.gap_id for item in gaps), label="gap_id")
        object.__setattr__(self, "command_records", commands)
        object.__setattr__(self, "digests", digests)
        object.__setattr__(self, "replay_checks", checks)
        object.__setattr__(self, "reproduction_gaps", gaps)
        object.__setattr__(
            self,
            "environment_notes",
            _unique_text(self.environment_notes, label="environment note"),
        )
        if not self.environment_notes:
            raise ValueError("Reproducible bundles require environment notes.")
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
                "Reproducible bundles must preserve claim boundary: "
                f"{missing_boundaries[0].value}"
            )
        object.__setattr__(self, "notes", _unique_text(self.notes, label="note"))
        object.__setattr__(
            self, "schema_version", _text(self.schema_version, "schema_version")
        )
        if self.reproduction_status is WaveFiveReproductionStatus.EXTERNALLY_REPRODUCED:
            if self.source_system not in EXTERNAL_REPRODUCTION_SOURCE_SYSTEMS:
                raise ValueError(
                    "Externally reproduced bundles require an external source system."
                )
            if self.has_blocking_reproduction_gap or self.has_failed_blocking_check:
                raise ValueError(
                    "Externally reproduced bundles cannot include blocking failures."
                )
        if (
            self.reproduction_status is WaveFiveReproductionStatus.REPRODUCTION_FAILED
            and not (self.has_blocking_reproduction_gap or self.has_failed_command)
        ):
            raise ValueError(
                "Failed reproduction status requires a failed command or gap."
            )

    @property
    def command_ids(self) -> tuple[str, ...]:
        """Return command ids in deterministic bundle order."""

        return tuple(command.command_id for command in self.command_records)

    @property
    def digest_ids(self) -> tuple[str, ...]:
        """Return digest ids in deterministic bundle order."""

        return tuple(digest.digest_id for digest in self.digests)

    @property
    def replay_check_ids(self) -> tuple[str, ...]:
        """Return replay-check ids in deterministic bundle order."""

        return tuple(check.check_id for check in self.replay_checks)

    @property
    def missing_required_replay_checks(self) -> tuple[WaveFiveReplayCheckKind, ...]:
        """Return required replay checks absent from the bundle."""

        present = {check.check_kind for check in self.replay_checks}
        return tuple(
            kind for kind in REQUIRED_WAVE_FIVE_REPLAY_CHECKS if kind not in present
        )

    @property
    def has_required_digest_coverage(self) -> bool:
        """Return whether source, test, and output digests are present."""

        present = {digest.digest_kind for digest in self.digests}
        return {
            WaveFiveDigestKind.SOURCE_TREE,
            WaveFiveDigestKind.TEST_TREE,
            WaveFiveDigestKind.OUTPUT_ARTIFACT,
        }.issubset(present)

    @property
    def has_required_replay_check_coverage(self) -> bool:
        """Return whether all locked replay checks are represented."""

        return not self.missing_required_replay_checks

    @property
    def has_failed_command(self) -> bool:
        """Return whether any command failed."""

        return any(
            command.outcome is WaveFiveCommandOutcome.FAILED
            for command in self.command_records
        )

    @property
    def has_failed_blocking_check(self) -> bool:
        """Return whether any blocking replay check failed."""

        return any(check.blocks_reproduction for check in self.replay_checks)

    @property
    def has_blocking_reproduction_gap(self) -> bool:
        """Return whether any reproduction gap blocks external reproduction."""

        return any(gap.blocks_reproduction for gap in self.reproduction_gaps)

    @property
    def ready_for_external_reproduction(self) -> bool:
        """Return whether internal evidence is complete enough for reviewers."""

        return (
            self.reproduction_status
            in {
                WaveFiveReproductionStatus.INTERNAL_REPLAY_READY,
                WaveFiveReproductionStatus.NEEDS_EXTERNAL_REPRODUCTION,
                WaveFiveReproductionStatus.UNDER_EXTERNAL_REPRODUCTION,
            }
            and self.has_required_digest_coverage
            and self.has_required_replay_check_coverage
            and not self.has_failed_command
            and not self.has_failed_blocking_check
            and not self.has_blocking_reproduction_gap
        )

    @property
    def externally_reproduced_with_boundaries(self) -> bool:
        """Return whether external reproduction is present and bounded."""

        return (
            self.reproduction_status is WaveFiveReproductionStatus.EXTERNALLY_REPRODUCED
            and self.source_system in EXTERNAL_REPRODUCTION_SOURCE_SYSTEMS
            and not self.has_failed_blocking_check
            and not self.has_blocking_reproduction_gap
        )

    @property
    def all_evidence_ids(self) -> tuple[str, ...]:
        """Return all evidence ids bound into this bundle."""

        evidence_ids: list[str] = []
        seen: set[str] = set()
        for evidence_id in self._iter_evidence_ids():
            if evidence_id not in seen:
                evidence_ids.append(evidence_id)
                seen.add(evidence_id)
        return tuple(evidence_ids)

    def to_artifact_ref(self) -> WaveFiveArtifactRef:
        """Return this bundle as a Wave 5 artifact reference."""

        decision = WaveFiveArtifactDecision.NEEDS_EXTERNAL_EVIDENCE
        status = WaveFiveValidationStatus.MISSING_EXTERNAL_EVIDENCE
        authority = WaveFiveAuthorityState.HUMAN_REVIEW_REQUIRED
        if self.externally_reproduced_with_boundaries:
            decision = WaveFiveArtifactDecision.EXTERNALLY_REVIEWED
            status = WaveFiveValidationStatus.EXTERNALLY_REPRODUCED
        elif self.ready_for_external_reproduction:
            decision = WaveFiveArtifactDecision.READY_FOR_INDEPENDENT_REVIEW
            status = WaveFiveValidationStatus.UNDER_INDEPENDENT_REVIEW
        elif self.has_failed_command or self.has_failed_blocking_check:
            decision = WaveFiveArtifactDecision.BLOCKED
            status = WaveFiveValidationStatus.REJECTED
            authority = WaveFiveAuthorityState.BLOCKED
        elif self.has_blocking_reproduction_gap:
            decision = WaveFiveArtifactDecision.BLOCKED
            status = WaveFiveValidationStatus.DISPUTED
            authority = WaveFiveAuthorityState.BLOCKED
        return WaveFiveArtifactRef(
            artifact_id=self.bundle_id,
            kind=WaveFiveArtifactKind.REPRODUCIBLE_EVIDENCE_BUNDLE,
            capability_area=WaveFiveCapabilityArea.REPRODUCIBILITY,
            source_system=self.source_system,
            summary=self.title,
            produced_by_engine_id="wave5-reproducibility-engine",
            produced_by_agent_role_id="independent-reproduction-registrar",
            evidence_ids=self.all_evidence_ids,
            decision=decision,
            authority_state=authority,
            validation_status=status,
            claim_boundaries=self.claim_boundaries,
        )

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic export payload."""

        return {
            "bundle_id": self.bundle_id,
            "claim_boundaries": [boundary.value for boundary in self.claim_boundaries],
            "command_records": [
                command.canonical_payload() for command in self.command_records
            ],
            "digests": [digest.canonical_payload() for digest in self.digests],
            "environment_notes": list(self.environment_notes),
            "notes": list(self.notes),
            "protocol_ids": list(self.protocol_ids),
            "replay_checks": [
                check.canonical_payload() for check in self.replay_checks
            ],
            "reproduction_gaps": [
                gap.canonical_payload() for gap in self.reproduction_gaps
            ],
            "reproduction_status": self.reproduction_status.value,
            "schema_version": self.schema_version,
            "source_system": self.source_system.value,
            "title": self.title,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this bundle."""

        return _stable_sha256(self.canonical_payload())

    def _iter_evidence_ids(self) -> Iterable[str]:
        """Yield evidence ids in bundle traversal order."""

        for command in self.command_records:
            yield from command.evidence_ids
        for digest in self.digests:
            yield from digest.evidence_ids
        for check in self.replay_checks:
            yield from check.evidence_ids
        for gap in self.reproduction_gaps:
            yield from gap.evidence_ids


def required_wave_five_replay_checks() -> tuple[WaveFiveReplayCheckKind, ...]:
    """Return locked replay checks required of Wave 5 evidence bundles."""

    return REQUIRED_WAVE_FIVE_REPLAY_CHECKS


def external_reproduction_source_systems() -> tuple[WaveFiveSourceSystem, ...]:
    """Return source systems that can assert external reproduction."""

    return EXTERNAL_REPRODUCTION_SOURCE_SYSTEMS


def _text(value: str, label: str) -> str:
    """Return stripped text or raise when empty."""

    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{label} must not be empty.")
    return normalized


def _unique_text(
    values: Iterable[str], *, label: str, allow_duplicates: bool = False
) -> tuple[str, ...]:
    """Normalize text values while rejecting blanks and optional duplicates."""

    normalized: list[str] = []
    seen: set[str] = set()
    for value in values:
        item = _text(value, label)
        if not allow_duplicates and item in seen:
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


def _sha256(value: str, label: str) -> str:
    """Return a normalized SHA-256 digest or raise when malformed."""

    normalized = _text(value, label).lower()
    if len(normalized) != 64:
        raise ValueError(f"{label} must be a 64-character SHA-256 digest.")
    try:
        int(normalized, 16)
    except ValueError as exc:
        raise ValueError(f"{label} must be hexadecimal.") from exc
    return normalized


def _stable_sha256(payload: Mapping[str, Any]) -> str:
    """Return deterministic SHA-256 over a canonical JSON payload."""

    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
