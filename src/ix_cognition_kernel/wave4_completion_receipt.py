"""Wave 4 completion receipt records.

A Wave 4 completion receipt records that the controlled proto-candidate review
package is ready to be stored as a human-review record. It is not deployment
approval, production readiness, independent validation, automatic promotion, or
an AGI claim. The receipt exists to close the evidence chain with deterministic
checks, a digest, and explicit human-authority boundaries.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Protocol, TypeVar

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
from ix_cognition_kernel.wave4_review_docket import WaveFourReviewDocketStatus

T = TypeVar("T")

WAVE_FOUR_RECORD_CHECK_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave4-record-check-v1"
)
WAVE_FOUR_COMPLETION_RECEIPT_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave4-completion-receipt-v1"
)


class WaveFourRecordCheckKind(StrEnum):
    """Checks required before recording the Wave 4 review package."""

    DOCKET_READY = "docket-ready"
    DOCKET_DIGEST_PRESENT = "docket-digest-present"
    EVIDENCE_PRESENT = "evidence-present"
    REVIEWERS_PRESENT = "reviewers-present"
    SCENARIOS_PRESENT = "scenarios-present"
    BLACKFOX_RECEIPTS_PRESENT = "blackfox-receipts-present"
    HUMAN_AUTHORITY_REQUIRED = "human-authority-required"
    NO_AUTOMATIC_EXECUTION = "no-automatic-execution"
    NO_AUTOMATIC_PROMOTION = "no-automatic-promotion"
    NO_AGI_CLAIM = "no-agi-claim"
    NO_INDEPENDENT_VALIDATION_CLAIM = "no-independent-validation-claim"
    NO_PRODUCTION_CLAIM = "no-production-claim"


class WaveFourRecordCheckSeverity(StrEnum):
    """Severity classes for Wave 4 completion receipt checks."""

    EVIDENCE = "evidence"
    REPAIR = "repair"
    BLOCKING = "blocking"


class WaveFourCompletionReceiptStatus(StrEnum):
    """Fail-closed status for a Wave 4 completion receipt."""

    READY_FOR_WAVE_FOUR_RECORD = "ready-for-wave-four-record"
    NEEDS_EVIDENCE = "needs-evidence"
    NEEDS_REPAIR = "needs-repair"
    BLOCKED = "blocked"


class WaveFourCompletionReceiptDecision(StrEnum):
    """Decision produced by a completion receipt gate."""

    RECORD_WAVE_FOUR_REVIEW_PACKAGE = "record-wave-four-review-package"
    HOLD_FOR_EVIDENCE = "hold-for-evidence"
    HOLD_FOR_REPAIR = "hold-for-repair"
    BLOCK_RECORD = "block-record"


REQUIRED_WAVE_FOUR_RECORD_CHECK_KINDS: tuple[WaveFourRecordCheckKind, ...] = (
    WaveFourRecordCheckKind.DOCKET_READY,
    WaveFourRecordCheckKind.DOCKET_DIGEST_PRESENT,
    WaveFourRecordCheckKind.EVIDENCE_PRESENT,
    WaveFourRecordCheckKind.REVIEWERS_PRESENT,
    WaveFourRecordCheckKind.SCENARIOS_PRESENT,
    WaveFourRecordCheckKind.BLACKFOX_RECEIPTS_PRESENT,
    WaveFourRecordCheckKind.HUMAN_AUTHORITY_REQUIRED,
    WaveFourRecordCheckKind.NO_AUTOMATIC_EXECUTION,
    WaveFourRecordCheckKind.NO_AUTOMATIC_PROMOTION,
    WaveFourRecordCheckKind.NO_AGI_CLAIM,
    WaveFourRecordCheckKind.NO_INDEPENDENT_VALIDATION_CLAIM,
    WaveFourRecordCheckKind.NO_PRODUCTION_CLAIM,
)


class WaveFourReviewDocketLike(Protocol):
    """Read-only structural protocol for completion-receipt docket fields."""

    @property
    def docket_id(self) -> str:
        """Return the docket id."""

    @property
    def status(self) -> WaveFourReviewDocketStatus:
        """Return the docket status."""

    @property
    def human_authority_state(self) -> WaveFourAuthorityState:
        """Return the docket human-authority state."""

    @property
    def final_digest(self) -> str:
        """Return the docket digest."""

    @property
    def all_evidence_ids(self) -> tuple[str, ...]:
        """Return evidence ids visible to the docket."""

    @property
    def scenario_ids(self) -> tuple[str, ...]:
        """Return WorldTwin scenario ids."""

    @property
    def blackfox_receipt_ids(self) -> tuple[str, ...]:
        """Return BlackFox receipt ids."""

    @property
    def reviewer_assignments(self) -> tuple[Any, ...]:
        """Return reviewer assignments."""

    @property
    def readiness_gaps(self) -> tuple[str, ...]:
        """Return docket readiness gaps."""

    @property
    def blocking_gaps(self) -> tuple[str, ...]:
        """Return docket blocking gaps."""

    @property
    def permits_automatic_execution(self) -> bool:
        """Return whether the docket permits execution."""

    @property
    def permits_automatic_promotion(self) -> bool:
        """Return whether the docket permits promotion."""

    @property
    def claims_agi(self) -> bool:
        """Return whether the docket claims AGI."""

    @property
    def independently_validated(self) -> bool:
        """Return whether the docket claims independent validation."""

    @property
    def production_ready(self) -> bool:
        """Return whether the docket claims production readiness."""


@dataclass(frozen=True, slots=True)
class WaveFourRecordCheck:
    """One deterministic check for a Wave 4 completion receipt."""

    check_id: str
    check_kind: WaveFourRecordCheckKind
    severity: WaveFourRecordCheckSeverity
    passed: bool
    summary: str
    evidence_ids: tuple[str, ...] = ()
    failure_summary: str = ""
    source_system: WaveFourSourceSystem = WaveFourSourceSystem.IX_COGNITION_KERNEL
    schema_version: str = WAVE_FOUR_RECORD_CHECK_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate check identity and pass/fail accounting."""

        object.__setattr__(self, "check_id", _text(self.check_id, "check_id"))
        object.__setattr__(self, "summary", _text(self.summary, "summary"))
        object.__setattr__(
            self,
            "evidence_ids",
            _unique_text(self.evidence_ids, label="completion-check evidence_id"),
        )
        object.__setattr__(self, "failure_summary", self.failure_summary.strip())
        object.__setattr__(
            self,
            "schema_version",
            _text(self.schema_version, "schema_version"),
        )
        if self.passed and self.failure_summary:
            raise ValueError(
                "Passed Wave 4 completion receipt checks cannot carry failure text."
            )
        if not self.passed and not self.failure_summary:
            raise ValueError(
                "Failed Wave 4 completion receipt checks require failure text."
            )

    @property
    def check_key(self) -> str:
        """Return deterministic uniqueness key."""

        return self.check_id

    @property
    def readiness_gap(self) -> str:
        """Return fail-closed gap text when this check failed."""

        if self.passed:
            return ""
        return f"{self.check_id} failed: {self.failure_summary}"

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic check payload."""

        return {
            "check_id": self.check_id,
            "check_kind": self.check_kind.value,
            "evidence_ids": list(self.evidence_ids),
            "failure_summary": self.failure_summary,
            "passed": self.passed,
            "readiness_gap": self.readiness_gap,
            "schema_version": self.schema_version,
            "severity": self.severity.value,
            "source_system": self.source_system.value,
            "summary": self.summary,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint."""

        return _stable_sha256(self.canonical_payload())


@dataclass(frozen=True, slots=True)
class WaveFourCompletionReceipt:
    """Deterministic completion receipt for a bounded Wave 4 review record."""

    receipt_id: str
    review_docket: WaveFourReviewDocketLike
    record_checks: tuple[WaveFourRecordCheck, ...]
    generated_by_engine_id: str = "wave4-completion-receipt-engine"
    reviewer_role_id: str = "wave4-completion-record-reviewer"
    notes: tuple[str, ...] = ()
    blocked_reasons: tuple[str, ...] = ()
    required_check_kinds: tuple[WaveFourRecordCheckKind, ...] = (
        REQUIRED_WAVE_FOUR_RECORD_CHECK_KINDS
    )
    permits_automatic_execution: bool = False
    permits_automatic_promotion: bool = False
    claims_agi: bool = False
    independently_validated: bool = False
    production_ready: bool = False
    schema_version: str = WAVE_FOUR_COMPLETION_RECEIPT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate receipt coverage, docket binding, and hard boundaries."""

        object.__setattr__(self, "receipt_id", _text(self.receipt_id, "receipt_id"))
        if not self.record_checks:
            raise ValueError("Wave 4 completion receipts require record checks.")
        checks = tuple(sorted(self.record_checks, key=lambda item: item.check_key))
        _unique_items((item.check_id for item in checks), "record check_id")
        object.__setattr__(self, "record_checks", checks)
        object.__setattr__(
            self,
            "generated_by_engine_id",
            _text(self.generated_by_engine_id, "generated_by_engine_id"),
        )
        object.__setattr__(
            self,
            "reviewer_role_id",
            _text(self.reviewer_role_id, "reviewer_role_id"),
        )
        object.__setattr__(
            self,
            "notes",
            _unique_text(self.notes, label="completion receipt note"),
        )
        object.__setattr__(
            self,
            "blocked_reasons",
            _unique_text(self.blocked_reasons, label="blocked reason"),
        )
        object.__setattr__(
            self,
            "required_check_kinds",
            _unique_items(self.required_check_kinds, "required record check kind"),
        )
        if not self.required_check_kinds:
            raise ValueError("Wave 4 completion receipts require check coverage.")
        object.__setattr__(
            self,
            "schema_version",
            _text(self.schema_version, "schema_version"),
        )
        if self.permits_automatic_execution:
            raise ValueError("Wave 4 completion receipts cannot permit execution.")
        if self.permits_automatic_promotion:
            raise ValueError("Wave 4 completion receipts cannot permit promotion.")
        if self.claims_agi:
            raise ValueError("Wave 4 completion receipts cannot claim AGI.")
        if self.independently_validated:
            raise ValueError(
                "Wave 4 completion receipts cannot claim independent validation."
            )
        if self.production_ready:
            raise ValueError(
                "Wave 4 completion receipts cannot claim production readiness."
            )

    @property
    def artifact_id(self) -> str:
        """Return shared Wave 4 artifact id for this receipt."""

        return f"wave4-completion-receipt:{self.receipt_id}"

    @property
    def check_kinds_present(self) -> tuple[WaveFourRecordCheckKind, ...]:
        """Return check kinds represented by the receipt."""

        return tuple(
            sorted(
                {check.check_kind for check in self.record_checks},
                key=lambda item: item.value,
            )
        )

    @property
    def missing_required_check_kinds(self) -> tuple[WaveFourRecordCheckKind, ...]:
        """Return required check kinds missing from this receipt."""

        present = set(self.check_kinds_present)
        return tuple(kind for kind in self.required_check_kinds if kind not in present)

    @property
    def passed_check_ids(self) -> tuple[str, ...]:
        """Return passed check ids."""

        return tuple(check.check_id for check in self.record_checks if check.passed)

    @property
    def failed_check_ids(self) -> tuple[str, ...]:
        """Return failed check ids."""

        return tuple(check.check_id for check in self.record_checks if not check.passed)

    @property
    def failed_evidence_check_ids(self) -> tuple[str, ...]:
        """Return failed evidence-severity check ids."""

        return self._failed_check_ids_by_severity(WaveFourRecordCheckSeverity.EVIDENCE)

    @property
    def failed_repair_check_ids(self) -> tuple[str, ...]:
        """Return failed repair-severity check ids."""

        return self._failed_check_ids_by_severity(WaveFourRecordCheckSeverity.REPAIR)

    @property
    def failed_blocking_check_ids(self) -> tuple[str, ...]:
        """Return failed blocking-severity check ids."""

        return self._failed_check_ids_by_severity(WaveFourRecordCheckSeverity.BLOCKING)

    @property
    def all_evidence_ids(self) -> tuple[str, ...]:
        """Return sorted evidence ids from docket and receipt checks."""

        evidence_ids = set(self.review_docket.all_evidence_ids)
        for check in self.record_checks:
            evidence_ids.update(check.evidence_ids)
        return tuple(sorted(evidence_ids))

    @property
    def receipt_digest(self) -> str:
        """Return deterministic digest of the receipt record."""

        return _stable_sha256(
            {
                "docket_digest": self.review_docket.final_digest,
                "receipt_id": self.receipt_id,
                "record_check_fingerprints": [
                    check.fingerprint() for check in self.record_checks
                ],
                "schema_version": self.schema_version,
            }
        )

    @property
    def readiness_gaps(self) -> tuple[str, ...]:
        """Return fail-closed gaps preventing Wave 4 record completion."""

        gaps: list[str] = []
        if self.missing_required_check_kinds:
            missing = ", ".join(kind.value for kind in self.missing_required_check_kinds)
            gaps.append(f"missing completion receipt check coverage: {missing}")
        if self.review_docket.status is not WaveFourReviewDocketStatus.READY_FOR_HUMAN_REVIEW:
            gaps.extend(self.review_docket.readiness_gaps)
        gaps.extend(check.readiness_gap for check in self.record_checks if check.readiness_gap)
        return tuple(gaps)

    @property
    def blocking_gaps(self) -> tuple[str, ...]:
        """Return hard blocks for this completion receipt."""

        gaps = [
            f"{self.receipt_id} blocked: {reason}" for reason in self.blocked_reasons
        ]
        gaps.extend(
            f"blocking completion receipt check failed: {check_id}"
            for check_id in self.failed_blocking_check_ids
        )
        gaps.extend(self.review_docket.blocking_gaps)
        return tuple(gaps)

    @property
    def status(self) -> WaveFourCompletionReceiptStatus:
        """Return fail-closed completion receipt status."""

        if self.blocking_gaps:
            return WaveFourCompletionReceiptStatus.BLOCKED
        if self.failed_repair_check_ids or self.review_docket.status is (
            WaveFourReviewDocketStatus.NEEDS_REPAIR
        ):
            return WaveFourCompletionReceiptStatus.NEEDS_REPAIR
        if self.readiness_gaps:
            return WaveFourCompletionReceiptStatus.NEEDS_EVIDENCE
        return WaveFourCompletionReceiptStatus.READY_FOR_WAVE_FOUR_RECORD

    @property
    def decision(self) -> WaveFourCompletionReceiptDecision:
        """Return completion receipt decision."""

        if self.status is WaveFourCompletionReceiptStatus.BLOCKED:
            return WaveFourCompletionReceiptDecision.BLOCK_RECORD
        if self.status is WaveFourCompletionReceiptStatus.NEEDS_REPAIR:
            return WaveFourCompletionReceiptDecision.HOLD_FOR_REPAIR
        if self.status is WaveFourCompletionReceiptStatus.NEEDS_EVIDENCE:
            return WaveFourCompletionReceiptDecision.HOLD_FOR_EVIDENCE
        return WaveFourCompletionReceiptDecision.RECORD_WAVE_FOUR_REVIEW_PACKAGE

    @property
    def ready_for_wave_four_record(self) -> bool:
        """Return whether this receipt may be recorded as the Wave 4 package."""

        return self.status is WaveFourCompletionReceiptStatus.READY_FOR_WAVE_FOUR_RECORD

    @property
    def human_authority_state(self) -> WaveFourAuthorityState:
        """Return human-authority state for this receipt."""

        if self.status is WaveFourCompletionReceiptStatus.BLOCKED:
            return WaveFourAuthorityState.BLOCKED
        return WaveFourAuthorityState.HUMAN_REVIEW_REQUIRED

    @property
    def review_summary(self) -> str:
        """Return concise completion receipt summary."""

        return (
            f"{self.receipt_id}: {len(self.record_checks)} record checks; "
            f"{self.status.value}; human review record only; no AGI claim."
        )

    def to_artifact_ref(self) -> WaveFourArtifactRef:
        """Convert receipt into a shared Wave 4 readiness artifact."""

        if self.status is WaveFourCompletionReceiptStatus.READY_FOR_WAVE_FOUR_RECORD:
            decision = WaveFourArtifactDecision.READY_FOR_CONTROLLED_REVIEW
        elif self.status is WaveFourCompletionReceiptStatus.BLOCKED:
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
            produced_by_agent_role_id=self.reviewer_role_id,
            evidence_ids=self.all_evidence_ids,
            decision=decision,
            authority_state=self.human_authority_state,
        )

    def evidence_links(self) -> tuple[WaveFourEvidenceLink, ...]:
        """Return evidence links for this receipt artifact."""

        relation = WaveFourEvidenceRelation.TESTS
        if self.status is WaveFourCompletionReceiptStatus.BLOCKED:
            relation = WaveFourEvidenceRelation.BLOCKS
        return tuple(
            WaveFourEvidenceLink(
                evidence_id=evidence_id,
                artifact_id=self.artifact_id,
                relation=relation,
                summary=f"Evidence for Wave 4 completion receipt {self.receipt_id}.",
                source_system=WaveFourSourceSystem.LOCAL_TEST_SUITE,
            )
            for evidence_id in self.all_evidence_ids
        )

    def to_artifact_bundle(self) -> WaveFourArtifactBundle:
        """Convert this receipt into a one-artifact Wave 4 bundle."""

        return WaveFourArtifactBundle(
            bundle_id=f"wave4-completion-receipt-bundle:{self.receipt_id}",
            artifacts=(self.to_artifact_ref(),),
            evidence_links=self.evidence_links(),
            required_kinds=(WaveFourArtifactKind.READINESS_SNAPSHOT,),
            required_capability_areas=(WaveFourCapabilityArea.AUDIT_TRAIL,),
            notes=(self.review_summary, *self.notes),
        )

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic completion-receipt payload."""

        return {
            "all_evidence_ids": list(self.all_evidence_ids),
            "artifact_id": self.artifact_id,
            "blocking_gaps": list(self.blocking_gaps),
            "blocked_reasons": list(self.blocked_reasons),
            "claims_agi": self.claims_agi,
            "decision": self.decision.value,
            "docket_id": self.review_docket.docket_id,
            "docket_status": self.review_docket.status.value,
            "failed_blocking_check_ids": list(self.failed_blocking_check_ids),
            "failed_check_ids": list(self.failed_check_ids),
            "failed_evidence_check_ids": list(self.failed_evidence_check_ids),
            "failed_repair_check_ids": list(self.failed_repair_check_ids),
            "generated_by_engine_id": self.generated_by_engine_id,
            "human_authority_state": self.human_authority_state.value,
            "independently_validated": self.independently_validated,
            "missing_required_check_kinds": [
                kind.value for kind in self.missing_required_check_kinds
            ],
            "notes": list(self.notes),
            "passed_check_ids": list(self.passed_check_ids),
            "permits_automatic_execution": self.permits_automatic_execution,
            "permits_automatic_promotion": self.permits_automatic_promotion,
            "production_ready": self.production_ready,
            "readiness_gaps": list(self.readiness_gaps),
            "ready_for_wave_four_record": self.ready_for_wave_four_record,
            "receipt_digest": self.receipt_digest,
            "receipt_id": self.receipt_id,
            "record_checks": [
                check.canonical_payload() for check in self.record_checks
            ],
            "required_check_kinds": [
                kind.value for kind in self.required_check_kinds
            ],
            "review_summary": self.review_summary,
            "reviewer_role_id": self.reviewer_role_id,
            "schema_version": self.schema_version,
            "status": self.status.value,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint."""

        return _stable_sha256(self.canonical_payload())

    def _failed_check_ids_by_severity(
        self,
        severity: WaveFourRecordCheckSeverity,
    ) -> tuple[str, ...]:
        """Return failed check ids matching severity."""

        return tuple(
            check.check_id
            for check in self.record_checks
            if not check.passed and check.severity is severity
        )


def build_wave_four_completion_receipt(
    *,
    receipt_id: str,
    review_docket: WaveFourReviewDocketLike,
) -> WaveFourCompletionReceipt:
    """Build the standard Wave 4 completion receipt from a review docket."""

    evidence_ids = review_docket.all_evidence_ids
    checks = (
        _check(
            check_id="check:docket-ready",
            check_kind=WaveFourRecordCheckKind.DOCKET_READY,
            severity=_docket_status_severity(review_docket.status),
            passed=review_docket.status
            is WaveFourReviewDocketStatus.READY_FOR_HUMAN_REVIEW,
            summary="Review docket is ready for human-review record.",
            evidence_ids=evidence_ids,
            failure_summary="; ".join(
                (*review_docket.blocking_gaps, *review_docket.readiness_gaps)
            ),
        ),
        _check(
            check_id="check:docket-digest-present",
            check_kind=WaveFourRecordCheckKind.DOCKET_DIGEST_PRESENT,
            severity=WaveFourRecordCheckSeverity.EVIDENCE,
            passed=_looks_like_sha256(review_docket.final_digest),
            summary="Review docket final digest is present and well-formed.",
            evidence_ids=evidence_ids,
            failure_summary="docket digest is missing or malformed",
        ),
        _check(
            check_id="check:evidence-present",
            check_kind=WaveFourRecordCheckKind.EVIDENCE_PRESENT,
            severity=WaveFourRecordCheckSeverity.EVIDENCE,
            passed=bool(review_docket.all_evidence_ids),
            summary="Review docket evidence ids are present.",
            evidence_ids=evidence_ids,
            failure_summary="review docket has no evidence ids",
        ),
        _check(
            check_id="check:reviewers-present",
            check_kind=WaveFourRecordCheckKind.REVIEWERS_PRESENT,
            severity=WaveFourRecordCheckSeverity.EVIDENCE,
            passed=bool(review_docket.reviewer_assignments),
            summary="Reviewer assignments are present.",
            evidence_ids=evidence_ids,
            failure_summary="review docket has no reviewer assignments",
        ),
        _check(
            check_id="check:scenarios-present",
            check_kind=WaveFourRecordCheckKind.SCENARIOS_PRESENT,
            severity=WaveFourRecordCheckSeverity.EVIDENCE,
            passed=bool(review_docket.scenario_ids),
            summary="WorldTwin scenario ids are present.",
            evidence_ids=evidence_ids,
            failure_summary="review docket has no WorldTwin scenario ids",
        ),
        _check(
            check_id="check:blackfox-receipts-present",
            check_kind=WaveFourRecordCheckKind.BLACKFOX_RECEIPTS_PRESENT,
            severity=WaveFourRecordCheckSeverity.EVIDENCE,
            passed=bool(review_docket.blackfox_receipt_ids),
            summary="BlackFox receipt ids are present.",
            evidence_ids=evidence_ids,
            failure_summary="review docket has no BlackFox receipt ids",
        ),
        _check(
            check_id="check:human-authority-required",
            check_kind=WaveFourRecordCheckKind.HUMAN_AUTHORITY_REQUIRED,
            severity=WaveFourRecordCheckSeverity.BLOCKING,
            passed=review_docket.human_authority_state
            is WaveFourAuthorityState.HUMAN_REVIEW_REQUIRED,
            summary="Human authority remains required.",
            evidence_ids=evidence_ids,
            failure_summary="human authority is not review-required",
        ),
        _check(
            check_id="check:no-automatic-execution",
            check_kind=WaveFourRecordCheckKind.NO_AUTOMATIC_EXECUTION,
            severity=WaveFourRecordCheckSeverity.BLOCKING,
            passed=not review_docket.permits_automatic_execution,
            summary="Completion receipt grants no execution authority.",
            evidence_ids=evidence_ids,
            failure_summary="automatic execution was permitted",
        ),
        _check(
            check_id="check:no-automatic-promotion",
            check_kind=WaveFourRecordCheckKind.NO_AUTOMATIC_PROMOTION,
            severity=WaveFourRecordCheckSeverity.BLOCKING,
            passed=not review_docket.permits_automatic_promotion,
            summary="Completion receipt grants no automatic promotion.",
            evidence_ids=evidence_ids,
            failure_summary="automatic promotion was permitted",
        ),
        _check(
            check_id="check:no-agi-claim",
            check_kind=WaveFourRecordCheckKind.NO_AGI_CLAIM,
            severity=WaveFourRecordCheckSeverity.BLOCKING,
            passed=not review_docket.claims_agi,
            summary="Completion receipt preserves the no-AGI-claim boundary.",
            evidence_ids=evidence_ids,
            failure_summary="AGI was claimed",
        ),
        _check(
            check_id="check:no-independent-validation-claim",
            check_kind=WaveFourRecordCheckKind.NO_INDEPENDENT_VALIDATION_CLAIM,
            severity=WaveFourRecordCheckSeverity.BLOCKING,
            passed=not review_docket.independently_validated,
            summary="Completion receipt does not claim independent validation.",
            evidence_ids=evidence_ids,
            failure_summary="independent validation was claimed",
        ),
        _check(
            check_id="check:no-production-claim",
            check_kind=WaveFourRecordCheckKind.NO_PRODUCTION_CLAIM,
            severity=WaveFourRecordCheckSeverity.BLOCKING,
            passed=not review_docket.production_ready,
            summary="Completion receipt does not claim production readiness.",
            evidence_ids=evidence_ids,
            failure_summary="production readiness was claimed",
        ),
    )
    return WaveFourCompletionReceipt(
        receipt_id=receipt_id,
        review_docket=review_docket,
        record_checks=checks,
    )


def _check(
    *,
    check_id: str,
    check_kind: WaveFourRecordCheckKind,
    severity: WaveFourRecordCheckSeverity,
    passed: bool,
    summary: str,
    evidence_ids: tuple[str, ...],
    failure_summary: str,
) -> WaveFourRecordCheck:
    """Build a record check while adding failure text only when needed."""

    return WaveFourRecordCheck(
        check_id=check_id,
        check_kind=check_kind,
        severity=severity,
        passed=passed,
        summary=summary,
        evidence_ids=evidence_ids,
        failure_summary="" if passed else failure_summary,
    )


def _docket_status_severity(
    status: WaveFourReviewDocketStatus,
) -> WaveFourRecordCheckSeverity:
    """Return completion-check severity from docket status."""

    if status is WaveFourReviewDocketStatus.BLOCKED:
        return WaveFourRecordCheckSeverity.BLOCKING
    if status is WaveFourReviewDocketStatus.NEEDS_REPAIR:
        return WaveFourRecordCheckSeverity.REPAIR
    return WaveFourRecordCheckSeverity.EVIDENCE


def _looks_like_sha256(value: str) -> bool:
    """Return whether text is a lowercase or uppercase SHA-256 hex digest."""

    if len(value) != 64:
        return False
    try:
        int(value, 16)
    except ValueError:
        return False
    return True


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
