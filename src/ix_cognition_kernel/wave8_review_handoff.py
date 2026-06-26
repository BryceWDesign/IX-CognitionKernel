"""Wave 8 review handoff.

This module adds a deterministic review-handoff binder for the Recursive
Reality-Corrected Learner. It does not certify intelligence, update public
documentation, or approve deployment. It binds the readiness scorecard, evidence
index, falsification matrix, review query result, and public-claim review into
one final handoff packet for human review.

Review-handoff doctrine:

- handoff is not certification,
- readiness must remain evidence-bound,
- query results must point back to the evidence index,
- falsification survival must remain review-bound,
- public claims must stay narrower than internal evidence,
- blocked gates cannot be hidden by a handoff packet,
- human reviewers remain the authority.
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
from ix_cognition_kernel.wave8_falsification_matrix import (
    FalsificationMatrixDecision,
    Wave8FalsificationMatrix,
)
from ix_cognition_kernel.wave8_public_claim_guard import (
    PublicClaimDecision,
    PublicClaimReview,
)
from ix_cognition_kernel.wave8_readiness_scorecard import (
    Wave8ReadinessDecision,
    Wave8ReadinessScorecard,
)
from ix_cognition_kernel.wave8_review_query import (
    ReviewQueryDecision,
    ReviewQueryResult,
)

WAVE_EIGHT_REVIEW_HANDOFF_SCHEMA_VERSION = "ix-cognition-kernel-wave8-review-handoff-v1"


class ReviewHandoffDecision(StrEnum):
    """Fail-closed Wave 8 review-handoff decision."""

    READY_FOR_HUMAN_REVIEW = "ready-for-human-review"
    NEEDS_READY_SCORECARD = "needs-ready-scorecard"
    NEEDS_READY_EVIDENCE_INDEX = "needs-ready-evidence-index"
    NEEDS_FALSIFICATION_SURVIVAL = "needs-falsification-survival"
    NEEDS_REVIEW_QUERY_MATCHES = "needs-review-query-matches"
    NEEDS_BOUNDED_PUBLIC_CLAIM = "needs-bounded-public-claim"
    BLOCKED_OVERCLAIM = "blocked-overclaim"


@dataclass(frozen=True, slots=True)
class Wave8ReviewHandoff:
    """Final deterministic Wave 8 review-handoff packet."""

    handoff_id: str
    purpose: str
    claim_boundary: str
    readiness_scorecard: Wave8ReadinessScorecard
    evidence_index: Wave8EvidenceIndex
    falsification_matrix: Wave8FalsificationMatrix
    review_query_result: ReviewQueryResult
    public_claim_review: PublicClaimReview
    reviewer_evidence_ids: tuple[str, ...]
    decision: ReviewHandoffDecision
    findings: tuple[str, ...]
    schema_version: str = WAVE_EIGHT_REVIEW_HANDOFF_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate review-handoff bindings and findings."""

        object.__setattr__(
            self,
            "handoff_id",
            _require_non_empty(self.handoff_id, "handoff_id"),
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
            "reviewer_evidence_ids",
            _normalize_unique_text_tuple(
                self.reviewer_evidence_ids,
                label="reviewer_evidence_id",
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
        if not self.reviewer_evidence_ids:
            raise ValueError("Wave 8 review handoffs require reviewer evidence ids.")
        _require_same_text(
            self.review_query_result.index_fingerprint,
            self.evidence_index.fingerprint(),
            "review_query_index_fingerprint",
        )
        _require_same_text(
            self.public_claim_review.evidence_index_fingerprint,
            self.evidence_index.fingerprint(),
            "public_claim_index_fingerprint",
        )
        _require_same_text(
            self.public_claim_review.readiness_scorecard_fingerprint,
            self.readiness_scorecard.fingerprint(),
            "public_claim_scorecard_fingerprint",
        )
        _require_same_text(
            self.public_claim_review.falsification_matrix_fingerprint,
            self.falsification_matrix.fingerprint(),
            "public_claim_falsification_fingerprint",
        )
        if (
            self.decision is not ReviewHandoffDecision.READY_FOR_HUMAN_REVIEW
            and not self.findings
        ):
            raise ValueError("Non-ready Wave 8 review handoffs require findings.")

    @property
    def ready(self) -> bool:
        """Return whether this handoff is ready for human review."""

        return self.decision is ReviewHandoffDecision.READY_FOR_HUMAN_REVIEW

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic review-handoff payload."""

        return {
            "claim_boundary": self.claim_boundary,
            "decision": self.decision.value,
            "evidence_index_fingerprint": self.evidence_index.fingerprint(),
            "falsification_matrix_fingerprint": self.falsification_matrix.fingerprint(),
            "findings": list(self.findings),
            "handoff_id": self.handoff_id,
            "public_claim_review_fingerprint": self.public_claim_review.fingerprint(),
            "purpose": self.purpose,
            "readiness_scorecard_fingerprint": self.readiness_scorecard.fingerprint(),
            "review_query_result_fingerprint": self.review_query_result.fingerprint(),
            "reviewer_evidence_ids": list(self.reviewer_evidence_ids),
            "schema_version": self.schema_version,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this handoff."""

        return _stable_sha256(self.canonical_payload())


def build_wave8_review_handoff(
    *,
    handoff_id: str,
    purpose: str,
    claim_boundary: str,
    readiness_scorecard: Wave8ReadinessScorecard,
    evidence_index: Wave8EvidenceIndex,
    falsification_matrix: Wave8FalsificationMatrix,
    review_query_result: ReviewQueryResult,
    public_claim_review: PublicClaimReview,
    reviewer_evidence_ids: Iterable[str],
) -> Wave8ReviewHandoff:
    """Build a deterministic Wave 8 review-handoff packet."""

    findings = _handoff_findings(
        readiness_scorecard=readiness_scorecard,
        evidence_index=evidence_index,
        falsification_matrix=falsification_matrix,
        review_query_result=review_query_result,
        public_claim_review=public_claim_review,
    )
    decision = _handoff_decision(findings=findings)
    return Wave8ReviewHandoff(
        handoff_id=handoff_id,
        purpose=purpose,
        claim_boundary=claim_boundary,
        readiness_scorecard=readiness_scorecard,
        evidence_index=evidence_index,
        falsification_matrix=falsification_matrix,
        review_query_result=review_query_result,
        public_claim_review=public_claim_review,
        reviewer_evidence_ids=tuple(reviewer_evidence_ids),
        decision=decision,
        findings=findings,
    )


def _handoff_findings(
    *,
    readiness_scorecard: Wave8ReadinessScorecard,
    evidence_index: Wave8EvidenceIndex,
    falsification_matrix: Wave8FalsificationMatrix,
    review_query_result: ReviewQueryResult,
    public_claim_review: PublicClaimReview,
) -> tuple[str, ...]:
    findings: list[str] = []
    if readiness_scorecard.decision is not (
        Wave8ReadinessDecision.READY_FOR_REVIEW_HANDOFF
    ):
        findings.append(
            f"readiness-scorecard-not-ready:{readiness_scorecard.decision.value}"
        )
    if evidence_index.decision is not EvidenceIndexDecision.READY_FOR_REVIEW_QUERY:
        findings.append(f"evidence-index-not-ready:{evidence_index.decision.value}")
    if falsification_matrix.decision is not (
        FalsificationMatrixDecision.SURVIVED_BOUNDED_FALSIFICATION
    ):
        findings.append(
            f"falsification-matrix-not-survived:{falsification_matrix.decision.value}"
        )
    if review_query_result.decision is not ReviewQueryDecision.MATCHES_READY:
        findings.append(f"review-query-not-ready:{review_query_result.decision.value}")
    if public_claim_review.decision is PublicClaimDecision.BLOCKED_OVERCLAIM:
        findings.append("public-claim-overclaim-blocked")
    elif public_claim_review.decision is not (
        PublicClaimDecision.APPROVED_BOUNDED_REVIEW_CLAIM
    ):
        findings.append(
            f"public-claim-not-approved:{public_claim_review.decision.value}"
        )
    return tuple(findings)


def _handoff_decision(
    *,
    findings: tuple[str, ...],
) -> ReviewHandoffDecision:
    if "public-claim-overclaim-blocked" in findings:
        return ReviewHandoffDecision.BLOCKED_OVERCLAIM
    if any(finding.startswith("readiness-scorecard-not-ready") for finding in findings):
        return ReviewHandoffDecision.NEEDS_READY_SCORECARD
    if any(finding.startswith("evidence-index-not-ready") for finding in findings):
        return ReviewHandoffDecision.NEEDS_READY_EVIDENCE_INDEX
    if any(
        finding.startswith("falsification-matrix-not-survived") for finding in findings
    ):
        return ReviewHandoffDecision.NEEDS_FALSIFICATION_SURVIVAL
    if any(finding.startswith("review-query-not-ready") for finding in findings):
        return ReviewHandoffDecision.NEEDS_REVIEW_QUERY_MATCHES
    if any(finding.startswith("public-claim-not-approved") for finding in findings):
        return ReviewHandoffDecision.NEEDS_BOUNDED_PUBLIC_CLAIM
    return ReviewHandoffDecision.READY_FOR_HUMAN_REVIEW


def _reject_overclaiming_text(value: str, label: str) -> None:
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
    if any(term in lowered for term in blocked_terms):
        raise ValueError(f"{label} contains blocked overclaiming language.")


def _require_same_text(left: str, right: str, label: str) -> None:
    if left != right:
        raise ValueError(f"Mismatched {label}: {left} != {right}")


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
