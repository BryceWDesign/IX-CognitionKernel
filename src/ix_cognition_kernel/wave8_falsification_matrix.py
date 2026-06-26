"""Wave 8 falsification matrix.

This module adds a deterministic falsification matrix for Wave 8. It does not
certify intelligence. It records whether the review packet survives explicit
negative controls, replay validation, evidence-index readiness, public-claim
guardrails, and readiness-score evidence.

Falsification doctrine:

- survival means "ready for review," not "true forever,"
- blocked negative controls falsify the review handoff,
- missing evidence keeps the matrix out of ready state,
- public claims cannot override evidence,
- the matrix cannot self-certify AGI or deployment readiness,
- every check remains replayable through source fingerprints.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from ix_cognition_kernel.wave8_evidence_index import (
    EvidenceIndexDecision,
    Wave8EvidenceIndex,
)
from ix_cognition_kernel.wave8_external_review_packet import (
    ExternalReviewPacket,
    ExternalReviewPacketDecision,
)
from ix_cognition_kernel.wave8_negative_controls import (
    NegativeControlDecision,
    NegativeControlReport,
)
from ix_cognition_kernel.wave8_public_claim_guard import (
    PublicClaimDecision,
    PublicClaimReview,
)
from ix_cognition_kernel.wave8_readiness_scorecard import (
    Wave8ReadinessDecision,
    Wave8ReadinessScorecard,
)
from ix_cognition_kernel.wave8_replay_validator import (
    ReplayValidationDecision,
    ReplayValidationReport,
)

WAVE_EIGHT_FALSIFICATION_CHECK_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave8-falsification-check-v1"
)
WAVE_EIGHT_FALSIFICATION_MATRIX_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave8-falsification-matrix-v1"
)


class FalsificationCheckKind(StrEnum):
    """Falsification checks required for Wave 8 review handoff."""

    NEGATIVE_CONTROLS = "negative-controls"
    REPLAY_VALIDATION = "replay-validation"
    EVIDENCE_INDEX = "evidence-index"
    PUBLIC_CLAIM_GUARD = "public-claim-guard"
    EXTERNAL_REVIEW_PACKET = "external-review-packet"
    READINESS_SCORECARD = "readiness-scorecard"
    CLAIM_BOUNDARY = "claim-boundary"
    HUMAN_AUTHORITY = "human-authority"


class FalsificationCheckDecision(StrEnum):
    """Decision for one falsification check."""

    SURVIVED = "survived"
    NEEDS_EVIDENCE = "needs-evidence"
    FALSIFIED = "falsified"
    OVERCLAIM_BLOCKED = "overclaim-blocked"


class FalsificationMatrixDecision(StrEnum):
    """Overall falsification-matrix decision."""

    SURVIVED_BOUNDED_FALSIFICATION = "survived-bounded-falsification"
    NEEDS_EVIDENCE = "needs-evidence"
    FALSIFIED = "falsified"
    OVERCLAIM_BLOCKED = "overclaim-blocked"


@dataclass(frozen=True, slots=True)
class FalsificationCheckRecord:
    """One deterministic falsification check."""

    check_id: str
    kind: FalsificationCheckKind
    decision: FalsificationCheckDecision
    source_fingerprints: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    summary: str
    findings: tuple[str, ...] = ()
    schema_version: str = WAVE_EIGHT_FALSIFICATION_CHECK_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate falsification check payload."""

        object.__setattr__(
            self,
            "check_id",
            _require_non_empty(self.check_id, "check_id"),
        )
        object.__setattr__(
            self,
            "source_fingerprints",
            _normalize_unique_sha256_tuple(
                self.source_fingerprints,
                label="source_fingerprint",
            ),
        )
        object.__setattr__(
            self,
            "evidence_ids",
            _normalize_unique_text_tuple(self.evidence_ids, label="evidence_id"),
        )
        object.__setattr__(
            self,
            "summary",
            _require_non_empty(self.summary, "summary"),
        )
        _reject_overclaiming_text(self.summary, "summary")
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
        if not self.source_fingerprints:
            raise ValueError("Falsification checks require source fingerprints.")
        if not self.evidence_ids:
            raise ValueError("Falsification checks require evidence ids.")
        if (
            self.decision is not FalsificationCheckDecision.SURVIVED
            and not self.findings
        ):
            raise ValueError("Non-surviving falsification checks require findings.")

    @property
    def survived(self) -> bool:
        """Return whether this check survived falsification."""

        return self.decision is FalsificationCheckDecision.SURVIVED

    @property
    def blocking(self) -> bool:
        """Return whether this check blocks review handoff."""

        return self.decision in {
            FalsificationCheckDecision.FALSIFIED,
            FalsificationCheckDecision.OVERCLAIM_BLOCKED,
        }

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic falsification-check payload."""

        return {
            "check_id": self.check_id,
            "decision": self.decision.value,
            "evidence_ids": list(self.evidence_ids),
            "findings": list(self.findings),
            "kind": self.kind.value,
            "schema_version": self.schema_version,
            "source_fingerprints": list(self.source_fingerprints),
            "summary": self.summary,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this check."""

        return _stable_sha256(self.canonical_payload())


@dataclass(frozen=True, slots=True)
class Wave8FalsificationMatrix:
    """Deterministic Wave 8 falsification matrix."""

    matrix_id: str
    purpose: str
    claim_boundary: str
    checks: tuple[FalsificationCheckRecord, ...]
    decision: FalsificationMatrixDecision
    findings: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    schema_version: str = WAVE_EIGHT_FALSIFICATION_MATRIX_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate matrix coverage and decision consistency."""

        object.__setattr__(
            self,
            "matrix_id",
            _require_non_empty(self.matrix_id, "matrix_id"),
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
        _reject_overclaiming_text(self.purpose, "purpose")
        _reject_overclaiming_text(self.claim_boundary, "claim_boundary")
        object.__setattr__(
            self,
            "checks",
            tuple(self.checks),
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
        if not self.checks:
            raise ValueError("Falsification matrices require checks.")
        if not self.evidence_ids:
            raise ValueError("Falsification matrices require evidence ids.")
        seen_check_ids: set[str] = set()
        for check in self.checks:
            if check.check_id in seen_check_ids:
                raise ValueError(f"Duplicate falsification check id: {check.check_id}")
            seen_check_ids.add(check.check_id)
        missing_kinds = _missing_required_check_kinds(self.checks)
        if missing_kinds:
            raise ValueError(
                "Falsification matrices are missing check kinds: "
                f"{','.join(missing_kinds)}"
            )
        if (
            self.decision
            is not FalsificationMatrixDecision.SURVIVED_BOUNDED_FALSIFICATION
            and not self.findings
        ):
            raise ValueError("Non-surviving falsification matrices require findings.")

    @property
    def survived(self) -> bool:
        """Return whether the matrix survived bounded falsification."""

        return (
            self.decision
            is FalsificationMatrixDecision.SURVIVED_BOUNDED_FALSIFICATION
        )

    @property
    def blocking_check_count(self) -> int:
        """Return count of blocking checks."""

        return sum(1 for check in self.checks if check.blocking)

    @property
    def needs_evidence_count(self) -> int:
        """Return count of checks that need more evidence."""

        return sum(
            1
            for check in self.checks
            if check.decision is FalsificationCheckDecision.NEEDS_EVIDENCE
        )

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic falsification-matrix payload."""

        return {
            "check_fingerprints": [check.fingerprint() for check in self.checks],
            "claim_boundary": self.claim_boundary,
            "decision": self.decision.value,
            "evidence_ids": list(self.evidence_ids),
            "findings": list(self.findings),
            "matrix_id": self.matrix_id,
            "purpose": self.purpose,
            "schema_version": self.schema_version,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this matrix."""

        return _stable_sha256(self.canonical_payload())


def check_negative_controls(
    *,
    check_id: str,
    report: NegativeControlReport,
    evidence_ids: Iterable[str],
) -> FalsificationCheckRecord:
    """Build a falsification check for negative controls."""

    if report.decision is NegativeControlDecision.PASSED:
        decision = FalsificationCheckDecision.SURVIVED
        findings: tuple[str, ...] = ()
        summary = "Negative controls passed and blocked shortcuts remain visible."
    elif report.decision is NegativeControlDecision.NEEDS_CONTROLS:
        decision = FalsificationCheckDecision.NEEDS_EVIDENCE
        findings = (f"negative-controls-not-ready:{report.decision.value}",)
        summary = "Negative controls need additional evidence."
    else:
        decision = FalsificationCheckDecision.FALSIFIED
        findings = (f"negative-controls-falsified:{report.decision.value}",)
        summary = "Negative controls falsified review readiness."

    return FalsificationCheckRecord(
        check_id=check_id,
        kind=FalsificationCheckKind.NEGATIVE_CONTROLS,
        decision=decision,
        source_fingerprints=(report.fingerprint(),),
        evidence_ids=tuple(evidence_ids),
        summary=summary,
        findings=findings,
    )


def check_replay_validation(
    *,
    check_id: str,
    report: ReplayValidationReport,
    evidence_ids: Iterable[str],
) -> FalsificationCheckRecord:
    """Build a falsification check for replay validation."""

    if report.decision is ReplayValidationDecision.READY_FOR_REVIEW:
        decision = FalsificationCheckDecision.SURVIVED
        findings: tuple[str, ...] = ()
        summary = "Replay validation survived required artifact checks."
    elif report.decision is ReplayValidationDecision.OVERCLAIM_BLOCKED:
        decision = FalsificationCheckDecision.OVERCLAIM_BLOCKED
        findings = (f"replay-validation-overclaim:{report.decision.value}",)
        summary = "Replay validation blocked overclaiming evidence."
    elif report.decision is ReplayValidationDecision.NEEDS_REQUIRED_ARTIFACTS:
        decision = FalsificationCheckDecision.NEEDS_EVIDENCE
        findings = (f"replay-validation-needs-evidence:{report.decision.value}",)
        summary = "Replay validation needs required artifacts."
    elif report.decision is ReplayValidationDecision.NEEDS_MEASURED_RESULT:
        decision = FalsificationCheckDecision.NEEDS_EVIDENCE
        findings = (f"replay-validation-needs-evidence:{report.decision.value}",)
        summary = "Replay validation needs measured results."
    else:
        decision = FalsificationCheckDecision.FALSIFIED
        findings = (f"replay-validation-falsified:{report.decision.value}",)
        summary = "Replay validation falsified review readiness."

    return FalsificationCheckRecord(
        check_id=check_id,
        kind=FalsificationCheckKind.REPLAY_VALIDATION,
        decision=decision,
        source_fingerprints=(report.fingerprint(),),
        evidence_ids=tuple(evidence_ids),
        summary=summary,
        findings=findings,
    )


def check_evidence_index(
    *,
    check_id: str,
    index: Wave8EvidenceIndex,
    evidence_ids: Iterable[str],
) -> FalsificationCheckRecord:
    """Build a falsification check for evidence-index readiness."""

    if index.decision is EvidenceIndexDecision.READY_FOR_REVIEW_QUERY:
        decision = FalsificationCheckDecision.SURVIVED
        findings: tuple[str, ...] = ()
        summary = "Evidence index is ready for bounded review query."
    elif index.decision is EvidenceIndexDecision.NEEDS_REQUIRED_ARTIFACTS:
        decision = FalsificationCheckDecision.NEEDS_EVIDENCE
        findings = (f"evidence-index-needs-evidence:{index.decision.value}",)
        summary = "Evidence index needs required artifacts."
    else:
        decision = FalsificationCheckDecision.FALSIFIED
        findings = (f"evidence-index-falsified:{index.decision.value}",)
        summary = "Evidence index falsified review readiness."

    return FalsificationCheckRecord(
        check_id=check_id,
        kind=FalsificationCheckKind.EVIDENCE_INDEX,
        decision=decision,
        source_fingerprints=(index.fingerprint(),),
        evidence_ids=tuple(evidence_ids),
        summary=summary,
        findings=findings,
    )


def check_public_claim_guard(
    *,
    check_id: str,
    review: PublicClaimReview,
    evidence_ids: Iterable[str],
) -> FalsificationCheckRecord:
    """Build a falsification check for public-claim guard results."""

    if review.decision is PublicClaimDecision.APPROVED_BOUNDED_REVIEW_CLAIM:
        decision = FalsificationCheckDecision.SURVIVED
        findings: tuple[str, ...] = ()
        summary = "Public claim guard approved only bounded review language."
    elif review.decision is PublicClaimDecision.BLOCKED_OVERCLAIM:
        decision = FalsificationCheckDecision.OVERCLAIM_BLOCKED
        findings = (f"public-claim-overclaim:{review.decision.value}",)
        summary = "Public claim guard blocked overclaiming language."
    else:
        decision = FalsificationCheckDecision.NEEDS_EVIDENCE
        findings = (f"public-claim-not-ready:{review.decision.value}",)
        summary = "Public claim guard needs ready bounded source evidence."

    return FalsificationCheckRecord(
        check_id=check_id,
        kind=FalsificationCheckKind.PUBLIC_CLAIM_GUARD,
        decision=decision,
        source_fingerprints=(review.fingerprint(),),
        evidence_ids=tuple(evidence_ids),
        summary=summary,
        findings=findings,
    )


def check_external_review_packet(
    *,
    check_id: str,
    packet: ExternalReviewPacket,
    evidence_ids: Iterable[str],
) -> FalsificationCheckRecord:
    """Build a falsification check for external review packet readiness."""

    if packet.decision is ExternalReviewPacketDecision.READY_FOR_EXTERNAL_REVIEW:
        decision = FalsificationCheckDecision.SURVIVED
        findings: tuple[str, ...] = ()
        summary = "External review packet is ready for bounded external review."
    elif packet.decision is ExternalReviewPacketDecision.OVERCLAIM_BLOCKED:
        decision = FalsificationCheckDecision.OVERCLAIM_BLOCKED
        findings = (f"external-review-overclaim:{packet.decision.value}",)
        summary = "External review packet blocked overclaiming language."
    else:
        decision = FalsificationCheckDecision.NEEDS_EVIDENCE
        findings = (f"external-review-not-ready:{packet.decision.value}",)
        summary = "External review packet needs additional evidence."

    return FalsificationCheckRecord(
        check_id=check_id,
        kind=FalsificationCheckKind.EXTERNAL_REVIEW_PACKET,
        decision=decision,
        source_fingerprints=(packet.fingerprint(),),
        evidence_ids=tuple(evidence_ids),
        summary=summary,
        findings=findings,
    )


def check_readiness_scorecard(
    *,
    check_id: str,
    scorecard: Wave8ReadinessScorecard,
    evidence_ids: Iterable[str],
) -> FalsificationCheckRecord:
    """Build a falsification check for readiness-score evidence."""

    if scorecard.decision is Wave8ReadinessDecision.READY_FOR_REVIEW_HANDOFF:
        decision = FalsificationCheckDecision.SURVIVED
        findings: tuple[str, ...] = ()
        summary = "Readiness scorecard is ready for review handoff."
    elif scorecard.decision is Wave8ReadinessDecision.OVERCLAIM_BLOCKED:
        decision = FalsificationCheckDecision.OVERCLAIM_BLOCKED
        findings = (f"scorecard-overclaim:{scorecard.decision.value}",)
        summary = "Readiness scorecard blocked overclaiming language."
    else:
        decision = FalsificationCheckDecision.NEEDS_EVIDENCE
        findings = (f"scorecard-not-ready:{scorecard.decision.value}",)
        summary = "Readiness scorecard needs additional evidence."

    return FalsificationCheckRecord(
        check_id=check_id,
        kind=FalsificationCheckKind.READINESS_SCORECARD,
        decision=decision,
        source_fingerprints=(scorecard.fingerprint(),),
        evidence_ids=tuple(evidence_ids),
        summary=summary,
        findings=findings,
    )


def check_claim_boundary(
    *,
    check_id: str,
    claim_boundary: str,
    source_fingerprints: Iterable[str],
    evidence_ids: Iterable[str],
) -> FalsificationCheckRecord:
    """Build a falsification check for claim-boundary language."""

    boundary = _require_non_empty(claim_boundary, "claim_boundary")
    source_tuple = tuple(source_fingerprints)
    if _contains_overclaiming_text(boundary):
        return FalsificationCheckRecord(
            check_id=check_id,
            kind=FalsificationCheckKind.CLAIM_BOUNDARY,
            decision=FalsificationCheckDecision.OVERCLAIM_BLOCKED,
            source_fingerprints=source_tuple,
            evidence_ids=tuple(evidence_ids),
            summary="Claim boundary blocked overclaiming language.",
            findings=("claim-boundary-overclaims-scope",),
        )

    return FalsificationCheckRecord(
        check_id=check_id,
        kind=FalsificationCheckKind.CLAIM_BOUNDARY,
        decision=FalsificationCheckDecision.SURVIVED,
        source_fingerprints=source_tuple,
        evidence_ids=tuple(evidence_ids),
        summary="Claim boundary preserves bounded review-only scope.",
    )


def check_human_authority(
    *,
    check_id: str,
    human_authority_recorded: bool,
    source_fingerprints: Iterable[str],
    evidence_ids: Iterable[str],
) -> FalsificationCheckRecord:
    """Build a falsification check for human authority."""

    if human_authority_recorded:
        return FalsificationCheckRecord(
            check_id=check_id,
            kind=FalsificationCheckKind.HUMAN_AUTHORITY,
            decision=FalsificationCheckDecision.SURVIVED,
            source_fingerprints=tuple(source_fingerprints),
            evidence_ids=tuple(evidence_ids),
            summary="Human authority remains outside model self-approval.",
        )

    return FalsificationCheckRecord(
        check_id=check_id,
        kind=FalsificationCheckKind.HUMAN_AUTHORITY,
        decision=FalsificationCheckDecision.NEEDS_EVIDENCE,
        source_fingerprints=tuple(source_fingerprints),
        evidence_ids=tuple(evidence_ids),
        summary="Human authority evidence is missing.",
        findings=("missing-human-authority-evidence",),
    )


def build_wave8_falsification_matrix(
    *,
    matrix_id: str,
    purpose: str,
    claim_boundary: str,
    checks: Iterable[FalsificationCheckRecord],
    evidence_ids: Iterable[str],
) -> Wave8FalsificationMatrix:
    """Build a Wave 8 falsification matrix from explicit checks."""

    check_tuple = tuple(checks)
    findings = _matrix_findings(check_tuple)
    decision = _matrix_decision(check_tuple, findings)

    return Wave8FalsificationMatrix(
        matrix_id=matrix_id,
        purpose=purpose,
        claim_boundary=claim_boundary,
        checks=check_tuple,
        decision=decision,
        findings=findings,
        evidence_ids=tuple(evidence_ids),
    )


def _matrix_findings(checks: tuple[FalsificationCheckRecord, ...]) -> tuple[str, ...]:
    findings: list[str] = []
    missing_kinds = _missing_required_check_kinds(checks)
    if missing_kinds:
        findings.append(f"missing-falsification-checks:{','.join(missing_kinds)}")

    overclaiming_checks = tuple(
        check.check_id
        for check in checks
        if check.decision is FalsificationCheckDecision.OVERCLAIM_BLOCKED
    )
    falsified_checks = tuple(
        check.check_id
        for check in checks
        if check.decision is FalsificationCheckDecision.FALSIFIED
    )
    needs_evidence_checks = tuple(
        check.check_id
        for check in checks
        if check.decision is FalsificationCheckDecision.NEEDS_EVIDENCE
    )

    if overclaiming_checks:
        findings.append(
            f"overclaim-blocked-checks:{','.join(sorted(overclaiming_checks))}"
        )
    if falsified_checks:
        findings.append(f"falsified-checks:{','.join(sorted(falsified_checks))}")
    if needs_evidence_checks:
        findings.append(
            f"needs-evidence-checks:{','.join(sorted(needs_evidence_checks))}"
        )
    return tuple(findings)


def _matrix_decision(
    checks: tuple[FalsificationCheckRecord, ...],
    findings: tuple[str, ...],
) -> FalsificationMatrixDecision:
    if any(check.decision is FalsificationCheckDecision.OVERCLAIM_BLOCKED for check in checks):
        return FalsificationMatrixDecision.OVERCLAIM_BLOCKED
    if any(check.decision is FalsificationCheckDecision.FALSIFIED for check in checks):
        return FalsificationMatrixDecision.FALSIFIED
    if any(finding.startswith("missing-falsification-checks") for finding in findings):
        return FalsificationMatrixDecision.NEEDS_EVIDENCE
    if any(
        check.decision is FalsificationCheckDecision.NEEDS_EVIDENCE
        for check in checks
    ):
        return FalsificationMatrixDecision.NEEDS_EVIDENCE
    return FalsificationMatrixDecision.SURVIVED_BOUNDED_FALSIFICATION


def _missing_required_check_kinds(
    checks: Iterable[FalsificationCheckRecord],
) -> tuple[str, ...]:
    required = {
        FalsificationCheckKind.NEGATIVE_CONTROLS,
        FalsificationCheckKind.REPLAY_VALIDATION,
        FalsificationCheckKind.EVIDENCE_INDEX,
        FalsificationCheckKind.PUBLIC_CLAIM_GUARD,
        FalsificationCheckKind.EXTERNAL_REVIEW_PACKET,
        FalsificationCheckKind.READINESS_SCORECARD,
        FalsificationCheckKind.CLAIM_BOUNDARY,
        FalsificationCheckKind.HUMAN_AUTHORITY,
    }
    present = {check.kind for check in checks}
    return tuple(sorted(kind.value for kind in required - present))


def _reject_overclaiming_text(value: str, label: str) -> None:
    if _contains_overclaiming_text(value):
        raise ValueError(f"{label} contains blocked overclaiming language.")


def _contains_overclaiming_text(value: str) -> bool:
    lowered = value.casefold()
    blocked_terms = (
        "agi",
        "artificial general intelligence",
        "certified intelligence",
        "certifies intelligence",
        "certifies artificial general intelligence",
        "deployment approved",
        "general intelligence achieved",
        "human-level intelligence",
        "superintelligence",
        "universal intelligence",
    )
    return any(term in lowered for term in blocked_terms)


def _require_non_empty(value: str, label: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{label} must not be empty.")
    return normalized


def _require_sha256(value: str, label: str) -> str:
    normalized = _require_non_empty(value, label)
    if len(normalized) != 64:
        raise ValueError(f"{label} must be a SHA-256 hex digest.")
    try:
        int(normalized, 16)
    except ValueError as exc:
        raise ValueError(f"{label} must be a SHA-256 hex digest.") from exc
    return normalized


def _normalize_unique_sha256_tuple(
    values: Iterable[str], *, label: str
) -> tuple[str, ...]:
    normalized: list[str] = []
    seen: set[str] = set()
    for value in values:
        digest = _require_sha256(value, label)
        if digest in seen:
            raise ValueError(f"Duplicate {label}: {digest}")
        seen.add(digest)
        normalized.append(digest)
    return tuple(sorted(normalized))


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
