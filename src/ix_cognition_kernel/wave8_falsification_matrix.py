"""Wave 8 falsification matrix.

The falsification matrix is the Wave 8 hard-stop layer for recursive learning
evidence. It asks whether a release bundle would be falsified by blocked
negative controls, missing review artifacts, unsafe public claims, unreplayable
episodes, or failed readiness gates.

It does not certify intelligence. It records whether bounded recursive learning
evidence survived the explicit checks required before review handoff.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from ix_cognition_kernel.wave8_evidence_index import (
    EvidenceArtifactKind,
    EvidenceIndexDecision,
    Wave8EvidenceIndex,
)
from ix_cognition_kernel.wave8_external_review_packet import (
    ExternalReviewPacketDecision,
    ExternalReviewPacketRecord,
)
from ix_cognition_kernel.wave8_negative_controls import (
    NegativeControlKind,
    NegativeControlReport,
)
from ix_cognition_kernel.wave8_public_claim_guard import (
    PublicClaimAssessment,
    PublicClaimDecision,
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
    """Kinds of falsification checks applied before review handoff."""

    CLAIM_BOUNDARY = "claim-boundary"
    TRANSFER_SHORTCUT = "transfer-shortcut"
    BASELINE_REGRESSION = "baseline-regression"
    UNMEASURED_REPLAY = "unmeasured-replay"
    SELF_AUTHORITY = "self-authority"
    LIVE_ACTUATION = "live-actuation"
    REPLAY_VALIDATION = "replay-validation"
    EVIDENCE_INDEX = "evidence-index"
    PUBLIC_CLAIM = "public-claim"
    EXTERNAL_REVIEW = "external-review"
    READINESS_SCORE = "readiness-score"


class FalsificationCheckDecision(StrEnum):
    """Fail-closed decision for a falsification check."""

    SURVIVED = "survived"
    FALSIFIED = "falsified"
    NEEDS_EVIDENCE = "needs-evidence"


class FalsificationMatrixDecision(StrEnum):
    """Overall falsification matrix decision."""

    SURVIVED_FOR_REVIEW = "survived-for-review"
    FALSIFIED = "falsified"
    NEEDS_EVIDENCE = "needs-evidence"


@dataclass(frozen=True, slots=True)
class FalsificationCheckRecord:
    """One falsification check and the evidence that supports its decision."""

    check_id: str
    kind: FalsificationCheckKind
    hypothesis_under_test: str
    falsify_if: str
    observed_outcome: str
    decision: FalsificationCheckDecision
    evidence_ids: tuple[str, ...]
    linked_entry_ids: tuple[str, ...] = ()
    findings: tuple[str, ...] = ()
    schema_version: str = WAVE_EIGHT_FALSIFICATION_CHECK_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate falsification check consistency."""

        object.__setattr__(
            self,
            "check_id",
            _require_non_empty(self.check_id, "check_id"),
        )
        object.__setattr__(
            self,
            "hypothesis_under_test",
            _require_non_empty(
                self.hypothesis_under_test,
                "hypothesis_under_test",
            ),
        )
        object.__setattr__(
            self,
            "falsify_if",
            _require_non_empty(self.falsify_if, "falsify_if"),
        )
        object.__setattr__(
            self,
            "observed_outcome",
            _require_non_empty(self.observed_outcome, "observed_outcome"),
        )
        object.__setattr__(
            self,
            "evidence_ids",
            _normalize_unique_text_tuple(self.evidence_ids, label="evidence_id"),
        )
        object.__setattr__(
            self,
            "linked_entry_ids",
            _normalize_unique_text_tuple(
                self.linked_entry_ids,
                label="linked_entry_id",
            ),
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
            raise ValueError("Falsification checks require evidence ids.")
        if self.decision is not FalsificationCheckDecision.SURVIVED:
            if not self.findings:
                raise ValueError("Non-surviving falsification checks require findings.")

    @property
    def survived(self) -> bool:
        """Return whether this check survived falsification."""

        return self.decision is FalsificationCheckDecision.SURVIVED

    @property
    def blocking(self) -> bool:
        """Return whether this check blocks review handoff."""

        return self.decision is FalsificationCheckDecision.FALSIFIED

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic falsification-check payload."""

        return {
            "check_id": self.check_id,
            "decision": self.decision.value,
            "evidence_ids": list(self.evidence_ids),
            "falsify_if": self.falsify_if,
            "findings": list(self.findings),
            "hypothesis_under_test": self.hypothesis_under_test,
            "kind": self.kind.value,
            "linked_entry_ids": list(self.linked_entry_ids),
            "observed_outcome": self.observed_outcome,
            "schema_version": self.schema_version,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint."""

        return _stable_sha256(self.canonical_payload())


@dataclass(frozen=True, slots=True)
class FalsificationMatrix:
    """Review-handoff falsification matrix."""

    matrix_id: str
    claim_boundary: str
    checks: tuple[FalsificationCheckRecord, ...]
    evidence_ids: tuple[str, ...]
    findings: tuple[str, ...] = ()
    schema_version: str = WAVE_EIGHT_FALSIFICATION_MATRIX_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate matrix identity and required coverage."""

        object.__setattr__(
            self,
            "matrix_id",
            _require_non_empty(self.matrix_id, "matrix_id"),
        )
        object.__setattr__(
            self,
            "claim_boundary",
            _require_non_empty(self.claim_boundary, "claim_boundary"),
        )
        object.__setattr__(
            self,
            "checks",
            tuple(self.checks),
        )
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
        _reject_overclaiming_text(self.claim_boundary, "claim_boundary")
        if not self.checks:
            raise ValueError("Falsification matrices require checks.")
        if not self.evidence_ids:
            raise ValueError("Falsification matrices require evidence ids.")
        seen: set[str] = set()
        for check in self.checks:
            if check.check_id in seen:
                raise ValueError(f"Duplicate falsification check id: {check.check_id}")
            seen.add(check.check_id)
        missing = _missing_required_kinds(self.checks)
        if missing:
            raise ValueError(
                "Falsification matrices are missing check kinds: "
                f"{','.join(missing)}"
            )

    @property
    def decision(self) -> FalsificationMatrixDecision:
        """Return fail-closed overall matrix decision."""

        if any(check.decision is FalsificationCheckDecision.FALSIFIED for check in self.checks):
            return FalsificationMatrixDecision.FALSIFIED
        if any(
            check.decision is FalsificationCheckDecision.NEEDS_EVIDENCE
            for check in self.checks
        ):
            return FalsificationMatrixDecision.NEEDS_EVIDENCE
        return FalsificationMatrixDecision.SURVIVED_FOR_REVIEW

    @property
    def survived(self) -> bool:
        """Return whether the matrix survived for review handoff."""

        return self.decision is FalsificationMatrixDecision.SURVIVED_FOR_REVIEW

    @property
    def blocking_check_count(self) -> int:
        """Return number of falsified checks."""

        return sum(
            1
            for check in self.checks
            if check.decision is FalsificationCheckDecision.FALSIFIED
        )

    @property
    def needs_evidence_count(self) -> int:
        """Return number of checks that need more evidence."""

        return sum(
            1
            for check in self.checks
            if check.decision is FalsificationCheckDecision.NEEDS_EVIDENCE
        )

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic matrix payload."""

        return {
            "check_fingerprints": [check.fingerprint() for check in self.checks],
            "claim_boundary": self.claim_boundary,
            "decision": self.decision.value,
            "evidence_ids": list(self.evidence_ids),
            "findings": list(self.findings),
            "matrix_id": self.matrix_id,
            "schema_version": self.schema_version,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint."""

        return _stable_sha256(self.canonical_payload())


def build_falsification_matrix(
    *,
    matrix_id: str,
    claim_boundary: str,
    evidence_index: Wave8EvidenceIndex,
    negative_control_report: NegativeControlReport,
    replay_report: ReplayValidationReport,
    public_claim_assessment: PublicClaimAssessment,
    external_review_packet: ExternalReviewPacketRecord,
    readiness_scorecard: Wave8ReadinessScorecard,
    evidence_ids: Iterable[str],
    extra_checks: Iterable[FalsificationCheckRecord] = (),
    findings: Iterable[str] = (),
) -> FalsificationMatrix:
    """Build a falsification matrix from Wave 8 review artifacts."""

    checks = (
        _claim_boundary_check(evidence_index=evidence_index),
        _negative_control_check(
            check_id="check-transfer-shortcut",
            kind=FalsificationCheckKind.TRANSFER_SHORTCUT,
            control_kind=NegativeControlKind.ORIGINAL_TASK_ONLY_BLOCK,
            hypothesis="Original-task-only success cannot stand in for transfer.",
            falsify_if="Original-task-only success is promoted as transfer evidence.",
            negative_control_report=negative_control_report,
            linked_entry_ids=("entry-transfer-report",),
        ),
        _negative_control_check(
            check_id="check-baseline-regression",
            kind=FalsificationCheckKind.BASELINE_REGRESSION,
            control_kind=NegativeControlKind.BASELINE_REGRESSION_VISIBLE,
            hypothesis="Baseline regression remains visible when it occurs.",
            falsify_if="Regression is hidden or scored as improvement.",
            negative_control_report=negative_control_report,
            linked_entry_ids=("entry-baseline-report",),
        ),
        _negative_control_check(
            check_id="check-unmeasured-replay",
            kind=FalsificationCheckKind.UNMEASURED_REPLAY,
            control_kind=NegativeControlKind.UNMEASURED_RESULT_BLOCK,
            hypothesis="Unmeasured results cannot promote replay or learning evidence.",
            falsify_if=(
                "Unmeasured results are accepted as replayable learning evidence."
            ),
            negative_control_report=negative_control_report,
            linked_entry_ids=("entry-replay-report",),
        ),
        _negative_control_check(
            check_id="check-self-authority",
            kind=FalsificationCheckKind.SELF_AUTHORITY,
            control_kind=NegativeControlKind.SELF_AUTHORIZATION_BLOCK,
            hypothesis="Model output cannot authorize itself.",
            falsify_if="Self-authorization is accepted as approval.",
            negative_control_report=negative_control_report,
            linked_entry_ids=("entry-external-review-packet",),
        ),
        _negative_control_check(
            check_id="check-live-actuation",
            kind=FalsificationCheckKind.LIVE_ACTUATION,
            control_kind=NegativeControlKind.LIVE_ACTUATION_BLOCK,
            hypothesis="Live actuation stays outside bounded review evidence.",
            falsify_if="Live actuation is accepted inside bounded replay evidence.",
            negative_control_report=negative_control_report,
            linked_entry_ids=("entry-replay-report",),
        ),
        _replay_validation_check(replay_report=replay_report),
        _evidence_index_check(evidence_index=evidence_index),
        _public_claim_check(public_claim_assessment=public_claim_assessment),
        _external_review_check(external_review_packet=external_review_packet),
        _scorecard_check(
            check_id="check-readiness-scorecard",
            readiness_scorecard=readiness_scorecard,
            evidence_index=evidence_index,
        ),
        *tuple(extra_checks),
    )
    matrix_findings = tuple(findings) + _matrix_findings(checks)
    return FalsificationMatrix(
        matrix_id=matrix_id,
        claim_boundary=claim_boundary,
        checks=checks,
        evidence_ids=tuple(evidence_ids),
        findings=matrix_findings,
    )


def build_falsification_check(
    *,
    check_id: str,
    kind: FalsificationCheckKind,
    hypothesis_under_test: str,
    falsify_if: str,
    observed_outcome: str,
    decision: FalsificationCheckDecision,
    evidence_ids: Iterable[str],
    linked_entry_ids: Iterable[str] = (),
    findings: Iterable[str] = (),
) -> FalsificationCheckRecord:
    """Build a falsification check record."""

    return FalsificationCheckRecord(
        check_id=check_id,
        kind=kind,
        hypothesis_under_test=hypothesis_under_test,
        falsify_if=falsify_if,
        observed_outcome=observed_outcome,
        decision=decision,
        evidence_ids=tuple(evidence_ids),
        linked_entry_ids=tuple(linked_entry_ids),
        findings=tuple(findings),
    )


def _claim_boundary_check(
    *,
    evidence_index: Wave8EvidenceIndex,
) -> FalsificationCheckRecord:
    if evidence_index.claim_boundary:
        return FalsificationCheckRecord(
            check_id="check-claim-boundary",
            kind=FalsificationCheckKind.CLAIM_BOUNDARY,
            hypothesis_under_test=(
                "Public-facing claims remain bounded to review evidence."
            ),
            falsify_if="Claim boundary is missing or bypassed by indexed artifacts.",
            observed_outcome="Claim boundary is attached to index and scorecard evidence.",
            decision=FalsificationCheckDecision.SURVIVED,
            evidence_ids=(evidence_index.fingerprint(),),
            linked_entry_ids=("entry-readiness-scorecard",),
        )
    return FalsificationCheckRecord(
        check_id="check-claim-boundary",
        kind=FalsificationCheckKind.CLAIM_BOUNDARY,
        hypothesis_under_test="Review evidence must carry a claim boundary.",
        falsify_if="Evidence index has no bounded claim statement.",
        observed_outcome="Evidence index claim boundary is missing.",
        decision=FalsificationCheckDecision.FALSIFIED,
        evidence_ids=(evidence_index.fingerprint(),),
        findings=("claim-boundary-missing",),
    )


def _negative_control_check(
    *,
    check_id: str,
    kind: FalsificationCheckKind,
    control_kind: NegativeControlKind,
    hypothesis: str,
    falsify_if: str,
    negative_control_report: NegativeControlReport,
    linked_entry_ids: tuple[str, ...],
) -> FalsificationCheckRecord:
    control = negative_control_report.control_by_kind(control_kind)
    if control is None:
        return FalsificationCheckRecord(
            check_id=check_id,
            kind=kind,
            hypothesis_under_test=hypothesis,
            falsify_if=falsify_if,
            observed_outcome=f"Missing negative control: {control_kind.value}",
            decision=FalsificationCheckDecision.NEEDS_EVIDENCE,
            evidence_ids=(negative_control_report.fingerprint(),),
            linked_entry_ids=linked_entry_ids,
            findings=(f"missing-negative-control:{control_kind.value}",),
        )
    if control.passed:
        return FalsificationCheckRecord(
            check_id=check_id,
            kind=kind,
            hypothesis_under_test=hypothesis,
            falsify_if=falsify_if,
            observed_outcome=f"Negative control passed: {control_kind.value}",
            decision=FalsificationCheckDecision.SURVIVED,
            evidence_ids=(control.fingerprint(), negative_control_report.fingerprint()),
            linked_entry_ids=linked_entry_ids,
        )
    return FalsificationCheckRecord(
        check_id=check_id,
        kind=kind,
        hypothesis_under_test=hypothesis,
        falsify_if=falsify_if,
        observed_outcome=f"Negative control failed: {control_kind.value}",
        decision=FalsificationCheckDecision.FALSIFIED,
        evidence_ids=(control.fingerprint(), negative_control_report.fingerprint()),
        linked_entry_ids=linked_entry_ids,
        findings=(f"negative-control-failed:{control_kind.value}",),
    )


def _replay_validation_check(
    *,
    replay_report: ReplayValidationReport,
) -> FalsificationCheckRecord:
    if replay_report.decision is ReplayValidationDecision.READY_FOR_REVIEW:
        return FalsificationCheckRecord(
            check_id="check-replay-validation",
            kind=FalsificationCheckKind.REPLAY_VALIDATION,
            hypothesis_under_test=(
                "Replay evidence requires measured, replayable artifacts."
            ),
            falsify_if="Replay packet lacks ready replay validation.",
            observed_outcome="Replay validation is ready for review.",
            decision=FalsificationCheckDecision.SURVIVED,
            evidence_ids=(replay_report.fingerprint(),),
            linked_entry_ids=("entry-replay-report",),
        )
    return FalsificationCheckRecord(
        check_id="check-replay-validation",
        kind=FalsificationCheckKind.REPLAY_VALIDATION,
        hypothesis_under_test="Replay evidence requires measured, replayable artifacts.",
        falsify_if="Replay packet lacks ready replay validation.",
        observed_outcome=f"Replay validation decision: {replay_report.decision.value}",
        decision=FalsificationCheckDecision.FALSIFIED,
        evidence_ids=(replay_report.fingerprint(),),
        linked_entry_ids=("entry-replay-report",),
        findings=(f"replay-validation-not-ready:{replay_report.decision.value}",),
    )


def _evidence_index_check(
    *,
    evidence_index: Wave8EvidenceIndex,
) -> FalsificationCheckRecord:
    if evidence_index.decision is EvidenceIndexDecision.READY_FOR_REVIEW_QUERY:
        return FalsificationCheckRecord(
            check_id="check-evidence-index",
            kind=FalsificationCheckKind.EVIDENCE_INDEX,
            hypothesis_under_test="Evidence index exposes all required review artifacts.",
            falsify_if="Review evidence is missing or hidden from the index.",
            observed_outcome="Evidence index is ready for review query.",
            decision=FalsificationCheckDecision.SURVIVED,
            evidence_ids=(evidence_index.fingerprint(),),
            linked_entry_ids=(
                "entry-transfer-report",
                "entry-baseline-report",
                "entry-replay-report",
                "entry-readiness-scorecard",
                "entry-public-claim-assessment",
                "entry-external-review-packet",
                "entry-falsification-matrix",
            ),
        )
    return FalsificationCheckRecord(
        check_id="check-evidence-index",
        kind=FalsificationCheckKind.EVIDENCE_INDEX,
        hypothesis_under_test="Evidence index exposes all required review artifacts.",
        falsify_if="Review evidence is missing or hidden from the index.",
        observed_outcome=f"Evidence index decision: {evidence_index.decision.value}",
        decision=FalsificationCheckDecision.FALSIFIED,
        evidence_ids=(evidence_index.fingerprint(),),
        findings=(f"evidence-index-not-ready:{evidence_index.decision.value}",),
    )


def _public_claim_check(
    *,
    public_claim_assessment: PublicClaimAssessment,
) -> FalsificationCheckRecord:
    if public_claim_assessment.decision is PublicClaimDecision.ALLOWED_FOR_REVIEW:
        return FalsificationCheckRecord(
            check_id="check-public-claim",
            kind=FalsificationCheckKind.PUBLIC_CLAIM,
            hypothesis_under_test=(
                "Public claims stay bounded to review evidence only."
            ),
            falsify_if="Public claim overstates capability or certification.",
            observed_outcome="Public claim guard allowed bounded review statement.",
            decision=FalsificationCheckDecision.SURVIVED,
            evidence_ids=(public_claim_assessment.fingerprint(),),
            linked_entry_ids=("entry-public-claim-assessment",),
        )
    return FalsificationCheckRecord(
        check_id="check-public-claim",
        kind=FalsificationCheckKind.PUBLIC_CLAIM,
        hypothesis_under_test="Public claims stay bounded to review evidence only.",
        falsify_if="Public claim overstates capability or certification.",
        observed_outcome=f"Public claim decision: {public_claim_assessment.decision.value}",
        decision=FalsificationCheckDecision.FALSIFIED,
        evidence_ids=(public_claim_assessment.fingerprint(),),
        linked_entry_ids=("entry-public-claim-assessment",),
        findings=(f"public-claim-not-allowed:{public_claim_assessment.decision.value}",),
    )


def _external_review_check(
    *,
    external_review_packet: ExternalReviewPacketRecord,
) -> FalsificationCheckRecord:
    if external_review_packet.decision is ExternalReviewPacketDecision.READY_FOR_EXTERNAL_REVIEW:
        return FalsificationCheckRecord(
            check_id="check-external-review-packet",
            kind=FalsificationCheckKind.EXTERNAL_REVIEW,
            hypothesis_under_test="External review packet is explicit and bounded.",
            falsify_if="External review is missing, self-approved, or overclaiming.",
            observed_outcome="External review packet is ready.",
            decision=FalsificationCheckDecision.SURVIVED,
            evidence_ids=(external_review_packet.fingerprint(),),
            linked_entry_ids=("entry-external-review-packet",),
        )
    return FalsificationCheckRecord(
        check_id="check-external-review-packet",
        kind=FalsificationCheckKind.EXTERNAL_REVIEW,
        hypothesis_under_test="External review packet is explicit and bounded.",
        falsify_if="External review is missing, self-approved, or overclaiming.",
        observed_outcome=(
            f"External review decision: {external_review_packet.decision.value}"
        ),
        decision=FalsificationCheckDecision.FALSIFIED,
        evidence_ids=(external_review_packet.fingerprint(),),
        linked_entry_ids=("entry-external-review-packet",),
        findings=(
            f"external-review-packet-not-ready:{external_review_packet.decision.value}",
        ),
    )


def _scorecard_check(
    *,
    check_id: str,
    readiness_scorecard: Wave8ReadinessScorecard,
    evidence_index: Wave8EvidenceIndex,
) -> FalsificationCheckRecord:
    if readiness_scorecard.decision is Wave8ReadinessDecision.READY_FOR_REVIEW_HANDOFF:
        decision = FalsificationCheckDecision.SURVIVED
        findings: tuple[str, ...] = ()
        observed = "Readiness scorecard is review-handoff ready."
    else:
        decision = FalsificationCheckDecision.NEEDS_EVIDENCE
        findings = (f"scorecard-not-ready:{readiness_scorecard.decision.value}",)
        observed = "Readiness scorecard needs additional evidence."

    return FalsificationCheckRecord(
        check_id=check_id,
        kind=FalsificationCheckKind.READINESS_SCORE,
        hypothesis_under_test=(
            "Readiness scoring cannot override failed evidence gates."
        ),
        falsify_if="Scorecard reports readiness despite failed evidence gates.",
        observed_outcome=observed,
        decision=decision,
        evidence_ids=(readiness_scorecard.fingerprint(), evidence_index.fingerprint()),
        linked_entry_ids=("entry-readiness-scorecard",),
        findings=findings,
    )


def _matrix_findings(
    checks: Iterable[FalsificationCheckRecord],
) -> tuple[str, ...]:
    findings: list[str] = []
    for check in checks:
        if check.decision is FalsificationCheckDecision.FALSIFIED:
            findings.append(f"falsified:{check.kind.value}")
        elif check.decision is FalsificationCheckDecision.NEEDS_EVIDENCE:
            findings.append(f"needs-evidence:{check.kind.value}")
    return tuple(findings)


def _missing_required_kinds(
    checks: Iterable[FalsificationCheckRecord],
) -> tuple[str, ...]:
    present = {check.kind for check in checks}
    required = {
        FalsificationCheckKind.CLAIM_BOUNDARY,
        FalsificationCheckKind.TRANSFER_SHORTCUT,
        FalsificationCheckKind.BASELINE_REGRESSION,
        FalsificationCheckKind.UNMEASURED_REPLAY,
        FalsificationCheckKind.SELF_AUTHORITY,
        FalsificationCheckKind.LIVE_ACTUATION,
        FalsificationCheckKind.REPLAY_VALIDATION,
        FalsificationCheckKind.EVIDENCE_INDEX,
        FalsificationCheckKind.PUBLIC_CLAIM,
        FalsificationCheckKind.EXTERNAL_REVIEW,
        FalsificationCheckKind.READINESS_SCORE,
    }
    return tuple(sorted(kind.value for kind in required.difference(present)))


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
