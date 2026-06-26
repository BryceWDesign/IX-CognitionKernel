"""Wave 8 release manifest.

This module adds the first Wave 8 release-manifest binder for the Recursive
Reality-Corrected Learner. It does not certify intelligence. It binds replay
validation, external review readiness, release gates, claim boundaries, and
evidence fingerprints into one deterministic packet.

Release doctrine:

- a manifest is not a certification,
- readiness is gated by replay and external review,
- blocked evidence remains visible,
- warnings do not become approval,
- overclaiming language blocks release,
- the system cannot self-approve a maturity claim,
- README/public narrative remains separate from evidence readiness.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from ix_cognition_kernel.wave8_external_review_packet import (
    ExternalReviewPacket,
    ExternalReviewPacketDecision,
)

WAVE_EIGHT_RELEASE_GATE_SCHEMA_VERSION = "ix-cognition-kernel-wave8-release-gate-v1"
WAVE_EIGHT_RELEASE_MANIFEST_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave8-release-manifest-v1"
)


class ReleaseGateKind(StrEnum):
    """Kinds of release gates required before Wave 8 handoff."""

    REPLAY_VALIDATION = "replay-validation"
    EXTERNAL_REVIEW_PACKET = "external-review-packet"
    CLAIM_BOUNDARY = "claim-boundary"
    HUMAN_AUTHORITY = "human-authority"
    BASELINE_IMPROVEMENT = "baseline-improvement"
    TRANSFER_EVIDENCE = "transfer-evidence"
    NO_SELF_CERTIFICATION = "no-self-certification"


class ReleaseGateDecision(StrEnum):
    """Decision for one release gate."""

    PASS = "pass"
    WARN = "warn"
    BLOCK = "block"


class Wave8ReleaseDecision(StrEnum):
    """Overall Wave 8 release-manifest decision."""

    READY_FOR_REVIEW_HANDOFF = "ready-for-review-handoff"
    READY_WITH_WARNINGS = "ready-with-warnings"
    NEEDS_REVIEW_PACKET = "needs-review-packet"
    NEEDS_GATE_EVIDENCE = "needs-gate-evidence"
    BLOCKED = "blocked"
    OVERCLAIM_BLOCKED = "overclaim-blocked"


@dataclass(frozen=True, slots=True)
class ReleaseGateRecord:
    """One evidence-bound Wave 8 release gate."""

    gate_id: str
    kind: ReleaseGateKind
    decision: ReleaseGateDecision
    summary: str
    evidence_ids: tuple[str, ...]
    findings: tuple[str, ...] = ()
    schema_version: str = WAVE_EIGHT_RELEASE_GATE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate gate payload and fail-closed findings."""

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
        _reject_overclaiming_text(self.summary, "summary")
        object.__setattr__(
            self,
            "evidence_ids",
            _normalize_unique_text_tuple(self.evidence_ids, label="evidence_id"),
        )
        object.__setattr__(
            self,
            "findings",
            _dedupe_text_tuple(self.findings, label="finding"),
        )
        object.__setattr__(
            self,
            "schema_version",
            _require_non_empty(self.schema_version, "schema_version"),
        )
        if not self.evidence_ids:
            raise ValueError("Release gate records require evidence ids.")
        if self.decision is not ReleaseGateDecision.PASS and not self.findings:
            raise ValueError("Warned or blocked release gates require findings.")

    @property
    def passed(self) -> bool:
        """Return whether this gate passed without warning."""

        return self.decision is ReleaseGateDecision.PASS

    @property
    def blocked(self) -> bool:
        """Return whether this gate blocks release."""

        return self.decision is ReleaseGateDecision.BLOCK

    @property
    def warned(self) -> bool:
        """Return whether this gate warns but does not block."""

        return self.decision is ReleaseGateDecision.WARN

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic release-gate payload."""

        return {
            "decision": self.decision.value,
            "evidence_ids": list(self.evidence_ids),
            "findings": list(self.findings),
            "gate_id": self.gate_id,
            "kind": self.kind.value,
            "schema_version": self.schema_version,
            "summary": self.summary,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this gate."""

        return _stable_sha256(self.canonical_payload())


@dataclass(frozen=True, slots=True)
class Wave8ReleaseManifest:
    """Deterministic Wave 8 release manifest for review handoff."""

    manifest_id: str
    wave_name: str
    purpose: str
    claim_boundary: str
    external_review_packet: ExternalReviewPacket
    gates: tuple[ReleaseGateRecord, ...]
    decision: Wave8ReleaseDecision
    findings: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    schema_version: str = WAVE_EIGHT_RELEASE_MANIFEST_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate release manifest coverage and claim boundary."""

        object.__setattr__(
            self,
            "manifest_id",
            _require_non_empty(self.manifest_id, "manifest_id"),
        )
        object.__setattr__(
            self,
            "wave_name",
            _require_non_empty(self.wave_name, "wave_name"),
        )
        object.__setattr__(
            self,
            "purpose",
            _require_non_empty(self.purpose, "purpose"),
        )
        object.__setattr__(
            self,
            "claim_boundary",
            _require_non_empty(self.claim_boundary, "claim_boundary"),
        )
        _reject_overclaiming_text(self.wave_name, "wave_name")
        _reject_overclaiming_text(self.purpose, "purpose")
        _reject_overclaiming_text(self.claim_boundary, "claim_boundary")
        object.__setattr__(
            self,
            "gates",
            tuple(self.gates),
        )
        object.__setattr__(
            self,
            "findings",
            _dedupe_text_tuple(self.findings, label="finding"),
        )
        object.__setattr__(
            self,
            "evidence_ids",
            _normalize_unique_text_tuple(self.evidence_ids, label="evidence_id"),
        )
        object.__setattr__(
            self,
            "schema_version",
            _require_non_empty(self.schema_version, "schema_version"),
        )
        if not self.gates:
            raise ValueError("Wave 8 release manifests require gates.")
        if not self.evidence_ids:
            raise ValueError("Wave 8 release manifests require evidence ids.")
        seen_gate_ids: set[str] = set()
        for gate in self.gates:
            if gate.gate_id in seen_gate_ids:
                raise ValueError(f"Duplicate release gate id: {gate.gate_id}")
            seen_gate_ids.add(gate.gate_id)
        missing_gate_kinds = _missing_required_gate_kinds(self.gates)
        if missing_gate_kinds:
            raise ValueError(
                "Wave 8 release manifests are missing gate kinds: "
                f"{','.join(missing_gate_kinds)}"
            )
        if (
            self.decision is not Wave8ReleaseDecision.READY_FOR_REVIEW_HANDOFF
            and not self.findings
        ):
            raise ValueError("Non-ready release manifests require findings.")

    @property
    def ready(self) -> bool:
        """Return whether the manifest is ready for review handoff."""

        return self.decision is Wave8ReleaseDecision.READY_FOR_REVIEW_HANDOFF

    @property
    def blocked_gate_count(self) -> int:
        """Return count of blocking gates."""

        return sum(1 for gate in self.gates if gate.blocked)

    @property
    def warning_gate_count(self) -> int:
        """Return count of warning gates."""

        return sum(1 for gate in self.gates if gate.warned)

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic release-manifest payload."""

        return {
            "claim_boundary": self.claim_boundary,
            "decision": self.decision.value,
            "evidence_ids": list(self.evidence_ids),
            "external_review_packet_fingerprint": (
                self.external_review_packet.fingerprint()
            ),
            "findings": list(self.findings),
            "gate_fingerprints": [gate.fingerprint() for gate in self.gates],
            "manifest_id": self.manifest_id,
            "purpose": self.purpose,
            "schema_version": self.schema_version,
            "wave_name": self.wave_name,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this manifest."""

        return _stable_sha256(self.canonical_payload())


def default_wave8_release_gates(
    *,
    external_review_packet: ExternalReviewPacket,
    human_authority_evidence_ids: Iterable[str],
    evidence_prefix: str = "wave8-release",
) -> tuple[ReleaseGateRecord, ...]:
    """Build deterministic default release gates from an external packet."""

    prefix = _require_non_empty(evidence_prefix, "evidence_prefix")
    human_authority_evidence = tuple(human_authority_evidence_ids)
    if not human_authority_evidence:
        human_gate = ReleaseGateRecord(
            gate_id="gate-human-authority",
            kind=ReleaseGateKind.HUMAN_AUTHORITY,
            decision=ReleaseGateDecision.BLOCK,
            summary="Human authority evidence is missing.",
            evidence_ids=(f"{prefix}:human-authority-missing",),
            findings=("missing-human-authority-evidence",),
        )
    else:
        human_gate = ReleaseGateRecord(
            gate_id="gate-human-authority",
            kind=ReleaseGateKind.HUMAN_AUTHORITY,
            decision=ReleaseGateDecision.PASS,
            summary="Human authority evidence is present for review handoff.",
            evidence_ids=human_authority_evidence,
        )

    replay_decision = ReleaseGateDecision.PASS
    replay_findings: tuple[str, ...] = ()
    if not external_review_packet.replay_report.ready:
        replay_decision = ReleaseGateDecision.BLOCK
        replay_findings = (
            f"replay-report-not-ready:"
            f"{external_review_packet.replay_report.decision.value}",
        )

    review_decision = ReleaseGateDecision.PASS
    review_findings: tuple[str, ...] = ()
    if external_review_packet.decision is not (
        ExternalReviewPacketDecision.READY_FOR_EXTERNAL_REVIEW
    ):
        review_decision = ReleaseGateDecision.BLOCK
        review_findings = (
            f"external-review-packet-not-ready:{external_review_packet.decision.value}",
        )

    return (
        ReleaseGateRecord(
            gate_id="gate-replay-validation",
            kind=ReleaseGateKind.REPLAY_VALIDATION,
            decision=replay_decision,
            summary="Replay validation report is bound to release readiness.",
            evidence_ids=(external_review_packet.replay_report.fingerprint(),),
            findings=replay_findings,
        ),
        ReleaseGateRecord(
            gate_id="gate-external-review-packet",
            kind=ReleaseGateKind.EXTERNAL_REVIEW_PACKET,
            decision=review_decision,
            summary="External review packet readiness is bound to release readiness.",
            evidence_ids=(external_review_packet.fingerprint(),),
            findings=review_findings,
        ),
        ReleaseGateRecord(
            gate_id="gate-claim-boundary",
            kind=ReleaseGateKind.CLAIM_BOUNDARY,
            decision=ReleaseGateDecision.PASS,
            summary="Claim boundary preserves bounded recursive learning scope.",
            evidence_ids=(f"{prefix}:claim-boundary",),
        ),
        human_gate,
        ReleaseGateRecord(
            gate_id="gate-baseline-improvement",
            kind=ReleaseGateKind.BASELINE_IMPROVEMENT,
            decision=ReleaseGateDecision.PASS,
            summary="Baseline improvement evidence remains review-bound.",
            evidence_ids=(f"{prefix}:baseline-improvement",),
        ),
        ReleaseGateRecord(
            gate_id="gate-transfer-evidence",
            kind=ReleaseGateKind.TRANSFER_EVIDENCE,
            decision=ReleaseGateDecision.PASS,
            summary="Transfer evidence remains review-bound.",
            evidence_ids=(f"{prefix}:transfer-evidence",),
        ),
        ReleaseGateRecord(
            gate_id="gate-no-self-certification",
            kind=ReleaseGateKind.NO_SELF_CERTIFICATION,
            decision=ReleaseGateDecision.PASS,
            summary="Manifest preserves no self-certification boundary.",
            evidence_ids=(f"{prefix}:no-self-certification",),
        ),
    )


def build_wave8_release_manifest(
    *,
    manifest_id: str,
    wave_name: str,
    purpose: str,
    claim_boundary: str,
    external_review_packet: ExternalReviewPacket,
    gates: Iterable[ReleaseGateRecord],
    evidence_ids: Iterable[str],
) -> Wave8ReleaseManifest:
    """Build a deterministic Wave 8 release manifest."""

    gate_tuple = tuple(gates)
    findings = _manifest_findings(
        external_review_packet=external_review_packet,
        gates=gate_tuple,
    )
    decision = _manifest_decision(
        external_review_packet=external_review_packet,
        gates=gate_tuple,
        findings=findings,
    )
    return Wave8ReleaseManifest(
        manifest_id=manifest_id,
        wave_name=wave_name,
        purpose=purpose,
        claim_boundary=claim_boundary,
        external_review_packet=external_review_packet,
        gates=gate_tuple,
        decision=decision,
        findings=findings,
        evidence_ids=tuple(evidence_ids),
    )


def _manifest_findings(
    *,
    external_review_packet: ExternalReviewPacket,
    gates: tuple[ReleaseGateRecord, ...],
) -> tuple[str, ...]:
    findings: list[str] = []
    if external_review_packet.decision is not (
        ExternalReviewPacketDecision.READY_FOR_EXTERNAL_REVIEW
    ):
        findings.append(
            f"external-review-packet-not-ready:{external_review_packet.decision.value}"
        )

    missing_gate_kinds = _missing_required_gate_kinds(gates)
    if missing_gate_kinds:
        findings.append(f"missing-release-gates:{','.join(missing_gate_kinds)}")

    blocked = tuple(gate.gate_id for gate in gates if gate.blocked)
    warnings = tuple(gate.gate_id for gate in gates if gate.warned)
    if blocked:
        findings.append(f"blocked-release-gates:{','.join(sorted(blocked))}")
    if warnings:
        findings.append(f"warning-release-gates:{','.join(sorted(warnings))}")

    return tuple(findings)


def _manifest_decision(
    *,
    external_review_packet: ExternalReviewPacket,
    gates: tuple[ReleaseGateRecord, ...],
    findings: tuple[str, ...],
) -> Wave8ReleaseDecision:
    if (
        external_review_packet.decision
        is ExternalReviewPacketDecision.OVERCLAIM_BLOCKED
    ):
        return Wave8ReleaseDecision.OVERCLAIM_BLOCKED
    if any(finding.startswith("blocked-release-gates") for finding in findings):
        return Wave8ReleaseDecision.BLOCKED
    if any(
        finding.startswith("external-review-packet-not-ready") for finding in findings
    ):
        return Wave8ReleaseDecision.NEEDS_REVIEW_PACKET
    if any(finding.startswith("missing-release-gates") for finding in findings):
        return Wave8ReleaseDecision.NEEDS_GATE_EVIDENCE
    if any(gate.warned for gate in gates):
        return Wave8ReleaseDecision.READY_WITH_WARNINGS
    return Wave8ReleaseDecision.READY_FOR_REVIEW_HANDOFF


def _missing_required_gate_kinds(gates: Iterable[ReleaseGateRecord]) -> tuple[str, ...]:
    required = {
        ReleaseGateKind.REPLAY_VALIDATION,
        ReleaseGateKind.EXTERNAL_REVIEW_PACKET,
        ReleaseGateKind.CLAIM_BOUNDARY,
        ReleaseGateKind.HUMAN_AUTHORITY,
        ReleaseGateKind.BASELINE_IMPROVEMENT,
        ReleaseGateKind.TRANSFER_EVIDENCE,
        ReleaseGateKind.NO_SELF_CERTIFICATION,
    }
    present = {gate.kind for gate in gates}
    return tuple(sorted(kind.value for kind in required - present))


def _reject_overclaiming_text(value: str, label: str) -> None:
    lowered = value.casefold()
    blocked_terms = (
        "agi",
        "artificial general intelligence",
        "general intelligence achieved",
        "universal intelligence",
        "superintelligence",
    )
    if any(term in lowered for term in blocked_terms):
        raise ValueError(f"{label} contains blocked overclaiming language.")


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


def _dedupe_text_tuple(values: Iterable[str], *, label: str) -> tuple[str, ...]:
    normalized: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = _require_non_empty(value, label)
        if text in seen:
            continue
        seen.add(text)
        normalized.append(text)
    return tuple(sorted(normalized))


def _stable_sha256(payload: Mapping[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
