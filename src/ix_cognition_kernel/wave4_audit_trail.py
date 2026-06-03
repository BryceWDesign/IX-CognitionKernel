"""Wave 4 reproducible audit-trail records.

Wave 4 evidence must be replayable and tamper-evident. This module records
ordered audit entries, digest-chain validation, replay checks, artifact
coverage, and fail-closed review state. A valid trail is still record-only:
it does not authorize execution, claim AGI, or claim independent validation.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, TypeVar, cast

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

WAVE_FOUR_AUDIT_ENTRY_SCHEMA_VERSION = "ix-cognition-kernel-wave4-audit-entry-v1"
WAVE_FOUR_REPLAY_CHECK_SCHEMA_VERSION = "ix-cognition-kernel-wave4-replay-check-v1"
WAVE_FOUR_AUDIT_TRAIL_SCHEMA_VERSION = "ix-cognition-kernel-wave4-audit-trail-v1"


class WaveFourAuditEventKind(StrEnum):
    """Kinds of events that can appear in a reproducible Wave 4 trail."""

    ARTIFACT_CREATED = "artifact-created"
    EVIDENCE_LINKED = "evidence-linked"
    TRIAL_RECORDED = "trial-recorded"
    REVIEW_GATE_EVALUATED = "review-gate-evaluated"
    HUMAN_AUTHORITY_RECORDED = "human-authority-recorded"
    REPLAY_CHECK_RECORDED = "replay-check-recorded"


class WaveFourReplayCheckKind(StrEnum):
    """Replay checks required to treat an audit trail as reproducible."""

    DIGEST_CHAIN_RECOMPUTED = "digest-chain-recomputed"
    ARTIFACT_PAYLOAD_REPLAYED = "artifact-payload-replayed"
    EVIDENCE_LINKS_REPLAYED = "evidence-links-replayed"
    DECISION_STATE_REPLAYED = "decision-state-replayed"
    HUMAN_AUTHORITY_REPLAYED = "human-authority-replayed"


class WaveFourAuditTrailStatus(StrEnum):
    """Fail-closed review status for a Wave 4 audit trail."""

    READY_FOR_CONTROLLED_REVIEW = "ready-for-controlled-review"
    NEEDS_EVIDENCE = "needs-evidence"
    NEEDS_REPAIR = "needs-repair"
    BLOCKED = "blocked"


class WaveFourAuditTrailOutcome(StrEnum):
    """Measured outcome for replaying a Wave 4 audit trail."""

    REPLAY_CONFIRMED = "replay-confirmed"
    TAMPER_DETECTED = "tamper-detected"
    NEEDS_EVIDENCE = "needs-evidence"
    BLOCKED = "blocked"


REQUIRED_WAVE_FOUR_REPLAY_CHECK_KINDS: tuple[WaveFourReplayCheckKind, ...] = (
    WaveFourReplayCheckKind.DIGEST_CHAIN_RECOMPUTED,
    WaveFourReplayCheckKind.ARTIFACT_PAYLOAD_REPLAYED,
    WaveFourReplayCheckKind.EVIDENCE_LINKS_REPLAYED,
    WaveFourReplayCheckKind.DECISION_STATE_REPLAYED,
    WaveFourReplayCheckKind.HUMAN_AUTHORITY_REPLAYED,
)


@dataclass(frozen=True, slots=True)
class WaveFourAuditTrailEntry:
    """One deterministic entry in a Wave 4 audit digest chain."""

    entry_id: str
    sequence_index: int
    event_kind: WaveFourAuditEventKind
    artifact_id: str
    event_summary: str
    payload: Mapping[str, Any]
    evidence_ids: tuple[str, ...]
    previous_digest: str
    source_system: WaveFourSourceSystem = WaveFourSourceSystem.IX_COGNITION_KERNEL
    schema_version: str = WAVE_FOUR_AUDIT_ENTRY_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate entry identity, sequence, payload, and evidence binding."""

        object.__setattr__(self, "entry_id", _text(self.entry_id, "entry_id"))
        if self.sequence_index < 0:
            raise ValueError("Wave 4 audit entry sequence_index must be >= 0.")
        object.__setattr__(self, "artifact_id", _text(self.artifact_id, "artifact_id"))
        object.__setattr__(
            self, "event_summary", _text(self.event_summary, "event_summary")
        )
        normalized_payload = _normalize_mapping(self.payload, "payload")
        if not normalized_payload:
            raise ValueError("Wave 4 audit entries require non-empty payloads.")
        object.__setattr__(self, "payload", normalized_payload)
        object.__setattr__(
            self,
            "evidence_ids",
            _unique_text(self.evidence_ids, label="audit-entry evidence_id"),
        )
        if not self.evidence_ids:
            raise ValueError("Wave 4 audit entries require evidence ids.")
        object.__setattr__(
            self, "previous_digest", _text(self.previous_digest, "previous_digest")
        )
        object.__setattr__(
            self, "schema_version", _text(self.schema_version, "schema_version")
        )

    @property
    def entry_key(self) -> tuple[int, str]:
        """Return deterministic sort key."""

        return (self.sequence_index, self.entry_id)

    def payload_for_digest(self) -> dict[str, Any]:
        """Return entry payload included in the digest chain."""

        return {
            "artifact_id": self.artifact_id,
            "entry_id": self.entry_id,
            "event_kind": self.event_kind.value,
            "event_summary": self.event_summary,
            "evidence_ids": list(self.evidence_ids),
            "payload": dict(self.payload),
            "previous_digest": self.previous_digest,
            "schema_version": self.schema_version,
            "sequence_index": self.sequence_index,
            "source_system": self.source_system.value,
        }

    @property
    def digest(self) -> str:
        """Return deterministic SHA-256 digest for this entry."""

        return _stable_sha256(self.payload_for_digest())

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic export payload including digest."""

        return {**self.payload_for_digest(), "digest": self.digest}


@dataclass(frozen=True, slots=True)
class WaveFourReplayCheck:
    """One replay check against a digest-bound audit trail."""

    check_id: str
    check_kind: WaveFourReplayCheckKind
    expected_value: str
    observed_value: str
    evidence_ids: tuple[str, ...]
    passed: bool
    failure_summary: str = ""
    schema_version: str = WAVE_FOUR_REPLAY_CHECK_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate replay check evidence and pass/fail accounting."""

        object.__setattr__(self, "check_id", _text(self.check_id, "check_id"))
        object.__setattr__(
            self, "expected_value", _text(self.expected_value, "expected_value")
        )
        object.__setattr__(
            self, "observed_value", _text(self.observed_value, "observed_value")
        )
        object.__setattr__(
            self,
            "evidence_ids",
            _unique_text(self.evidence_ids, label="replay-check evidence_id"),
        )
        if not self.evidence_ids:
            raise ValueError("Wave 4 replay checks require evidence ids.")
        object.__setattr__(self, "failure_summary", self.failure_summary.strip())
        object.__setattr__(
            self, "schema_version", _text(self.schema_version, "schema_version")
        )
        if self.passed and self.failure_summary:
            raise ValueError("Passed Wave 4 replay checks cannot carry failure text.")
        if not self.passed and not self.failure_summary:
            raise ValueError("Failed Wave 4 replay checks require failure text.")

    @property
    def check_key(self) -> str:
        """Return deterministic uniqueness key."""

        return self.check_id

    @property
    def readiness_gap(self) -> str:
        """Return replay failure text when the check failed."""

        if self.passed:
            return ""
        return f"{self.check_id} replay failed: {self.failure_summary}"

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic replay-check payload."""

        return {
            "check_id": self.check_id,
            "check_kind": self.check_kind.value,
            "evidence_ids": list(self.evidence_ids),
            "expected_value": self.expected_value,
            "failure_summary": self.failure_summary,
            "observed_value": self.observed_value,
            "passed": self.passed,
            "readiness_gap": self.readiness_gap,
            "schema_version": self.schema_version,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint."""

        return _stable_sha256(self.canonical_payload())


@dataclass(frozen=True, slots=True)
class WaveFourReproducibleAuditTrail:
    """Digest-chained, replay-checked Wave 4 audit trail."""

    trail_id: str
    entries: tuple[WaveFourAuditTrailEntry, ...]
    replay_checks: tuple[WaveFourReplayCheck, ...]
    artifact_refs: tuple[WaveFourArtifactRef, ...]
    scenario_ids: tuple[str, ...]
    blackfox_receipt_ids: tuple[str, ...]
    required_replay_check_kinds: tuple[WaveFourReplayCheckKind, ...] = (
        REQUIRED_WAVE_FOUR_REPLAY_CHECK_KINDS
    )
    reviewer_role_id: str = "reproducible-audit-trail-reviewer"
    generated_by_engine_id: str = "wave4-reproducible-audit-trail-engine"
    blocked_reasons: tuple[str, ...] = ()
    permits_automatic_execution: bool = False
    claims_agi: bool = False
    independently_validated: bool = False
    schema_version: str = WAVE_FOUR_AUDIT_TRAIL_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate chain integrity, replay coverage, and hard boundaries."""

        object.__setattr__(self, "trail_id", _text(self.trail_id, "trail_id"))
        if not self.entries:
            raise ValueError("Wave 4 audit trails require entries.")
        entries = tuple(sorted(self.entries, key=lambda entry: entry.entry_key))
        _unique_items((entry.entry_id for entry in entries), "entry_id")
        _unique_items((entry.sequence_index for entry in entries), "sequence_index")
        object.__setattr__(self, "entries", entries)
        checks = tuple(sorted(self.replay_checks, key=lambda check: check.check_key))
        _unique_items((check.check_id for check in checks), "check_id")
        object.__setattr__(self, "replay_checks", checks)
        artifacts = tuple(sorted(self.artifact_refs, key=lambda item: item.artifact_id))
        artifact_ids = _unique_items(
            (artifact.artifact_id for artifact in artifacts), "artifact_id"
        )
        for entry in entries:
            if entry.artifact_id not in artifact_ids:
                raise ValueError(
                    "Wave 4 audit entries must reference artifact refs: "
                    f"{entry.artifact_id}"
                )
        object.__setattr__(self, "artifact_refs", artifacts)
        object.__setattr__(
            self, "scenario_ids", _unique_text(self.scenario_ids, label="scenario_id")
        )
        object.__setattr__(
            self,
            "blackfox_receipt_ids",
            _unique_text(self.blackfox_receipt_ids, label="blackfox receipt_id"),
        )
        object.__setattr__(
            self,
            "required_replay_check_kinds",
            _unique_items(self.required_replay_check_kinds, "required replay kind"),
        )
        if not self.required_replay_check_kinds:
            raise ValueError("Wave 4 audit trails require replay-check coverage.")
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
            raise ValueError("Wave 4 audit trails cannot permit execution.")
        if self.claims_agi:
            raise ValueError("Wave 4 audit trails cannot claim AGI.")
        if self.independently_validated:
            raise ValueError("Wave 4 audit trails cannot claim independent validation.")
        if self.blocked_reasons and self.replay_checks:
            raise ValueError("Blocked Wave 4 audit trails cannot carry replay results.")

    @property
    def artifact_id(self) -> str:
        """Return shared Wave 4 artifact id."""

        return f"wave4-reproducible-audit-trail:{self.trail_id}"

    @property
    def entry_ids(self) -> tuple[str, ...]:
        """Return entry ids in chain order."""

        return tuple(entry.entry_id for entry in self.entries)

    @property
    def artifact_ids(self) -> tuple[str, ...]:
        """Return artifact ids covered by this audit trail."""

        return tuple(artifact.artifact_id for artifact in self.artifact_refs)

    @property
    def final_digest(self) -> str:
        """Return final entry digest for the trail."""

        return self.entries[-1].digest

    @property
    def chain_gaps(self) -> tuple[str, ...]:
        """Return digest-chain continuity gaps."""

        gaps: list[str] = []
        expected_previous = "GENESIS"
        for entry in self.entries:
            if entry.previous_digest != expected_previous:
                gaps.append(
                    f"{entry.entry_id} previous digest mismatch: "
                    f"expected {expected_previous}, observed {entry.previous_digest}"
                )
            expected_previous = entry.digest
        return tuple(gaps)

    @property
    def failed_replay_check_ids(self) -> tuple[str, ...]:
        """Return replay checks that failed."""

        return tuple(check.check_id for check in self.replay_checks if not check.passed)

    @property
    def missing_required_replay_check_kinds(
        self,
    ) -> tuple[WaveFourReplayCheckKind, ...]:
        """Return required replay checks not represented in this trail."""

        present = {check.check_kind for check in self.replay_checks}
        return tuple(
            check_kind
            for check_kind in self.required_replay_check_kinds
            if check_kind not in present
        )

    @property
    def all_evidence_ids(self) -> tuple[str, ...]:
        """Return sorted evidence ids from entries, checks, and artifacts."""

        evidence_ids: set[str] = set()
        for entry in self.entries:
            evidence_ids.update(entry.evidence_ids)
        for check in self.replay_checks:
            evidence_ids.update(check.evidence_ids)
        for artifact in self.artifact_refs:
            evidence_ids.update(artifact.evidence_ids)
        return tuple(sorted(evidence_ids))

    @property
    def readiness_gaps(self) -> tuple[str, ...]:
        """Return fail-closed gaps preventing controlled review."""

        gaps: list[str] = []
        gaps.extend(self.chain_gaps)
        if self.missing_required_replay_check_kinds:
            missing = ", ".join(
                check_kind.value
                for check_kind in self.missing_required_replay_check_kinds
            )
            gaps.append(f"missing replay-check coverage: {missing}")
        for check in self.replay_checks:
            if check.readiness_gap:
                gaps.append(check.readiness_gap)
        if not self.scenario_ids:
            gaps.append(f"{self.trail_id} has no WorldTwin scenario ids")
        if not self.blackfox_receipt_ids:
            gaps.append(f"{self.trail_id} has no BlackFox receipt ids")
        return tuple(gaps)

    @property
    def blocking_gaps(self) -> tuple[str, ...]:
        """Return hard blocks for this audit trail."""

        return tuple(
            f"{self.trail_id} blocked: {reason}" for reason in self.blocked_reasons
        )

    @property
    def outcome(self) -> WaveFourAuditTrailOutcome:
        """Return measured fail-closed audit-trail outcome."""

        if self.blocked_reasons:
            return WaveFourAuditTrailOutcome.BLOCKED
        if self.chain_gaps or self.failed_replay_check_ids:
            return WaveFourAuditTrailOutcome.TAMPER_DETECTED
        if self.readiness_gaps:
            return WaveFourAuditTrailOutcome.NEEDS_EVIDENCE
        return WaveFourAuditTrailOutcome.REPLAY_CONFIRMED

    @property
    def status(self) -> WaveFourAuditTrailStatus:
        """Return fail-closed review status for this trail."""

        if self.blocked_reasons:
            return WaveFourAuditTrailStatus.BLOCKED
        if self.chain_gaps or self.failed_replay_check_ids:
            return WaveFourAuditTrailStatus.NEEDS_REPAIR
        if self.readiness_gaps:
            return WaveFourAuditTrailStatus.NEEDS_EVIDENCE
        return WaveFourAuditTrailStatus.READY_FOR_CONTROLLED_REVIEW

    @property
    def ready_for_controlled_review(self) -> bool:
        """Return whether this trail may enter controlled human review."""

        return self.status is WaveFourAuditTrailStatus.READY_FOR_CONTROLLED_REVIEW

    @property
    def human_authority_state(self) -> WaveFourAuthorityState:
        """Return human-authority state for this audit trail."""

        if self.status is WaveFourAuditTrailStatus.BLOCKED:
            return WaveFourAuthorityState.BLOCKED
        return WaveFourAuthorityState.HUMAN_REVIEW_REQUIRED

    @property
    def review_summary(self) -> str:
        """Return concise audit-trail summary."""

        return (
            f"{self.trail_id}: {len(self.entries)} digest-chain entries; "
            f"{len(self.replay_checks)} replay checks; {self.status.value}; "
            "human review required; no AGI claim."
        )

    def to_artifact_ref(self) -> WaveFourArtifactRef:
        """Convert this audit trail into a shared Wave 4 artifact reference."""

        if self.status is WaveFourAuditTrailStatus.READY_FOR_CONTROLLED_REVIEW:
            decision = WaveFourArtifactDecision.READY_FOR_CONTROLLED_REVIEW
        elif self.status is WaveFourAuditTrailStatus.BLOCKED:
            decision = WaveFourArtifactDecision.BLOCKED
        else:
            decision = WaveFourArtifactDecision.NEEDS_EVIDENCE
        return WaveFourArtifactRef(
            artifact_id=self.artifact_id,
            kind=WaveFourArtifactKind.REPRODUCIBLE_AUDIT_TRAIL,
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
        """Return shared evidence links for this audit-trail artifact."""

        return tuple(
            WaveFourEvidenceLink(
                evidence_id=evidence_id,
                artifact_id=self.artifact_id,
                relation=WaveFourEvidenceRelation.TESTS,
                summary=f"Evidence for Wave 4 audit trail {self.trail_id}.",
                source_system=WaveFourSourceSystem.LOCAL_TEST_SUITE,
            )
            for evidence_id in self.all_evidence_ids
        )

    def to_artifact_bundle(self) -> WaveFourArtifactBundle:
        """Convert this audit trail into a one-artifact Wave 4 bundle."""

        return WaveFourArtifactBundle(
            bundle_id=f"wave4-audit-trail-bundle:{self.trail_id}",
            artifacts=(self.to_artifact_ref(),),
            evidence_links=self.evidence_links(),
            required_kinds=(WaveFourArtifactKind.REPRODUCIBLE_AUDIT_TRAIL,),
            required_capability_areas=(WaveFourCapabilityArea.AUDIT_TRAIL,),
            notes=(self.review_summary,),
        )

    def to_controlled_task(self) -> WaveFourControlledTask:
        """Represent the audit trail as a controlled replay task."""

        measurements = tuple(
            WaveFourTrialMeasurement(
                measurement_id=f"audit-replay:{check.check_id}",
                metric_name="reproducible-audit-trail-replay",
                target=check.expected_value,
                observed=check.observed_value,
                passed=check.passed,
                evidence_ids=check.evidence_ids,
            )
            for check in self.replay_checks
        )
        if self.status is WaveFourAuditTrailStatus.READY_FOR_CONTROLLED_REVIEW:
            outcome = WaveFourTrialOutcome.PASSED
        elif self.status is WaveFourAuditTrailStatus.BLOCKED:
            outcome = WaveFourTrialOutcome.BLOCKED
        elif self.status is WaveFourAuditTrailStatus.NEEDS_REPAIR:
            outcome = WaveFourTrialOutcome.FAILED
        else:
            outcome = WaveFourTrialOutcome.NOT_RUN
        return WaveFourControlledTask(
            task_id=f"audit-trail:{self.trail_id}",
            task_kind=WaveFourTrialTaskKind.BASELINE_CAPABILITY,
            objective="Verify digest-chain reproducibility for Wave 4 evidence.",
            input_domain=self.trail_id,
            evaluation_prompt=(
                "Recompute the digest chain and replay artifact, evidence, "
                "decision, and human-authority state without changing results."
            ),
            success_criteria=(
                "digest chain recomputes without mismatch",
                "required replay checks pass",
                "artifact references and evidence ids remain visible",
                "no automatic execution and no AGI claim",
            ),
            stop_conditions=(
                "stop on digest mismatch",
                "stop on failed replay check",
                "stop on missing BlackFox review receipt",
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
        """Return deterministic audit-trail payload."""

        return {
            "all_evidence_ids": list(self.all_evidence_ids),
            "artifact_id": self.artifact_id,
            "artifact_ids": list(self.artifact_ids),
            "blackfox_receipt_ids": list(self.blackfox_receipt_ids),
            "blocking_gaps": list(self.blocking_gaps),
            "blocked_reasons": list(self.blocked_reasons),
            "chain_gaps": list(self.chain_gaps),
            "claims_agi": self.claims_agi,
            "entries": [entry.canonical_payload() for entry in self.entries],
            "entry_ids": list(self.entry_ids),
            "failed_replay_check_ids": list(self.failed_replay_check_ids),
            "final_digest": self.final_digest,
            "generated_by_engine_id": self.generated_by_engine_id,
            "human_authority_state": self.human_authority_state.value,
            "independently_validated": self.independently_validated,
            "missing_required_replay_check_kinds": [
                kind.value for kind in self.missing_required_replay_check_kinds
            ],
            "outcome": self.outcome.value,
            "permits_automatic_execution": self.permits_automatic_execution,
            "readiness_gaps": list(self.readiness_gaps),
            "replay_checks": [
                check.canonical_payload() for check in self.replay_checks
            ],
            "required_replay_check_kinds": [
                kind.value for kind in self.required_replay_check_kinds
            ],
            "review_summary": self.review_summary,
            "reviewer_role_id": self.reviewer_role_id,
            "scenario_ids": list(self.scenario_ids),
            "schema_version": self.schema_version,
            "status": self.status.value,
            "trail_id": self.trail_id,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint."""

        return _stable_sha256(self.canonical_payload())


def audit_entry(
    *,
    entry_id: str,
    sequence_index: int,
    event_kind: WaveFourAuditEventKind,
    artifact_id: str,
    event_summary: str,
    payload: Mapping[str, Any],
    evidence_id: str,
    previous_digest: str,
) -> WaveFourAuditTrailEntry:
    """Build one audit entry with a single evidence id."""

    return WaveFourAuditTrailEntry(
        entry_id=entry_id,
        sequence_index=sequence_index,
        event_kind=event_kind,
        artifact_id=artifact_id,
        event_summary=event_summary,
        payload=payload,
        evidence_ids=(evidence_id,),
        previous_digest=previous_digest,
    )


def passed_replay_check(
    *,
    check_id: str,
    check_kind: WaveFourReplayCheckKind,
    expected_value: str,
    observed_value: str,
    evidence_id: str,
) -> WaveFourReplayCheck:
    """Build a passing replay check with one evidence id."""

    return WaveFourReplayCheck(
        check_id=check_id,
        check_kind=check_kind,
        expected_value=expected_value,
        observed_value=observed_value,
        evidence_ids=(evidence_id,),
        passed=True,
    )


def _normalize_mapping(value: Mapping[str, Any], label: str) -> dict[str, Any]:
    """Return a canonical dict after proving JSON serializability."""

    try:
        encoded = json.dumps(value, sort_keys=True, separators=(",", ":"))
    except TypeError as exc:
        raise ValueError(f"{label} must be JSON serializable.") from exc
    return cast(dict[str, Any], json.loads(encoded))


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
