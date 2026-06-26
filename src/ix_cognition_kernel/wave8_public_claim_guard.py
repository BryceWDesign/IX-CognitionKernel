"""Wave 8 public claim guard.

This module adds a deterministic public-claim guard for the Recursive
Reality-Corrected Learner. It does not write the README, certify intelligence,
or approve marketing language. It checks whether a proposed public statement is
bounded to the Wave 8 evidence chain, scorecard, evidence index, and
falsification matrix.

Public-claim doctrine:

- public claims must be narrower than internal evidence,
- readiness does not mean certification,
- review handoff does not mean deployment approval,
- bounded learning evidence does not mean AGI,
- falsification survival remains review-bound,
- blocked evidence must block public claims,
- claim text cannot override human authority.
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
from ix_cognition_kernel.wave8_falsification_matrix import (
    FalsificationMatrixDecision,
    Wave8FalsificationMatrix,
)
from ix_cognition_kernel.wave8_readiness_scorecard import (
    Wave8ReadinessDecision,
    Wave8ReadinessScorecard,
)

WAVE_EIGHT_PUBLIC_CLAIM_DRAFT_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave8-public-claim-draft-v1"
)
WAVE_EIGHT_PUBLIC_CLAIM_REVIEW_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave8-public-claim-review-v1"
)


class PublicClaimScope(StrEnum):
    """Allowed bounded public-claim scopes."""

    REVIEW_HANDOFF = "review-handoff"
    REPLAY_EVIDENCE = "replay-evidence"
    TRANSFER_EVIDENCE = "transfer-evidence"
    BASELINE_COMPARISON = "baseline-comparison"
    NEGATIVE_CONTROLS = "negative-controls"
    FALSIFICATION_MATRIX = "falsification-matrix"
    EVIDENCE_INDEX = "evidence-index"


class PublicClaimDecision(StrEnum):
    """Fail-closed public-claim review decision."""

    APPROVED_BOUNDED_REVIEW_CLAIM = "approved-bounded-review-claim"
    NEEDS_READY_EVIDENCE_INDEX = "needs-ready-evidence-index"
    NEEDS_READY_SCORECARD = "needs-ready-scorecard"
    NEEDS_FALSIFICATION_SURVIVAL = "needs-falsification-survival"
    NEEDS_SOURCE_ARTIFACTS = "needs-source-artifacts"
    BLOCKED_OVERCLAIM = "blocked-overclaim"


@dataclass(frozen=True, slots=True)
class PublicClaimDraft:
    """Proposed public claim bound to Wave 8 review evidence."""

    claim_id: str
    scope: PublicClaimScope
    text: str
    source_artifact_kinds: tuple[EvidenceArtifactKind, ...]
    evidence_ids: tuple[str, ...]
    schema_version: str = WAVE_EIGHT_PUBLIC_CLAIM_DRAFT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate proposed public-claim draft."""

        object.__setattr__(
            self,
            "claim_id",
            _require_non_empty(self.claim_id, "claim_id"),
        )
        object.__setattr__(
            self,
            "text",
            _require_non_empty(self.text, "text"),
        )
        object.__setattr__(
            self,
            "source_artifact_kinds",
            _normalize_unique_artifact_kinds(self.source_artifact_kinds),
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
        if not self.source_artifact_kinds:
            raise ValueError("Public claim drafts require source artifact kinds.")
        if not self.evidence_ids:
            raise ValueError("Public claim drafts require evidence ids.")

    @property
    def overclaims(self) -> bool:
        """Return whether the draft contains blocked overclaiming language."""

        return _contains_overclaiming_text(self.text)

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic public-claim draft payload."""

        return {
            "claim_id": self.claim_id,
            "evidence_ids": list(self.evidence_ids),
            "schema_version": self.schema_version,
            "scope": self.scope.value,
            "source_artifact_kinds": [
                kind.value for kind in self.source_artifact_kinds
            ],
            "text": self.text,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this claim draft."""

        return _stable_sha256(self.canonical_payload())


@dataclass(frozen=True, slots=True)
class PublicClaimReview:
    """Evidence-bound review result for a public claim draft."""

    review_id: str
    draft: PublicClaimDraft
    evidence_index_fingerprint: str
    readiness_scorecard_fingerprint: str
    falsification_matrix_fingerprint: str
    decision: PublicClaimDecision
    findings: tuple[str, ...]
    matched_entry_ids: tuple[str, ...]
    schema_version: str = WAVE_EIGHT_PUBLIC_CLAIM_REVIEW_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate public-claim review decision and bindings."""

        object.__setattr__(
            self,
            "review_id",
            _require_non_empty(self.review_id, "review_id"),
        )
        object.__setattr__(
            self,
            "evidence_index_fingerprint",
            _require_sha256(
                self.evidence_index_fingerprint,
                "evidence_index_fingerprint",
            ),
        )
        object.__setattr__(
            self,
            "readiness_scorecard_fingerprint",
            _require_sha256(
                self.readiness_scorecard_fingerprint,
                "readiness_scorecard_fingerprint",
            ),
        )
        object.__setattr__(
            self,
            "falsification_matrix_fingerprint",
            _require_sha256(
                self.falsification_matrix_fingerprint,
                "falsification_matrix_fingerprint",
            ),
        )
        object.__setattr__(
            self,
            "findings",
            _dedupe_text_tuple(self.findings, label="finding"),
        )
        object.__setattr__(
            self,
            "matched_entry_ids",
            _dedupe_text_tuple(self.matched_entry_ids, label="matched_entry_id"),
        )
        object.__setattr__(
            self,
            "schema_version",
            _require_non_empty(self.schema_version, "schema_version"),
        )
        if (
            self.decision is not PublicClaimDecision.APPROVED_BOUNDED_REVIEW_CLAIM
            and not self.findings
        ):
            raise ValueError("Non-approved public claim reviews require findings.")
        if (
            self.decision is PublicClaimDecision.APPROVED_BOUNDED_REVIEW_CLAIM
            and not self.matched_entry_ids
        ):
            raise ValueError("Approved public claim reviews require matched entries.")

    @property
    def approved(self) -> bool:
        """Return whether this claim is approved as bounded review language."""

        return self.decision is PublicClaimDecision.APPROVED_BOUNDED_REVIEW_CLAIM

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic public-claim review payload."""

        return {
            "decision": self.decision.value,
            "draft_fingerprint": self.draft.fingerprint(),
            "evidence_index_fingerprint": self.evidence_index_fingerprint,
            "falsification_matrix_fingerprint": self.falsification_matrix_fingerprint,
            "findings": list(self.findings),
            "matched_entry_ids": list(self.matched_entry_ids),
            "readiness_scorecard_fingerprint": self.readiness_scorecard_fingerprint,
            "review_id": self.review_id,
            "schema_version": self.schema_version,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this review."""

        return _stable_sha256(self.canonical_payload())


def build_public_claim_draft(
    *,
    claim_id: str,
    scope: PublicClaimScope,
    text: str,
    source_artifact_kinds: Iterable[EvidenceArtifactKind],
    evidence_ids: Iterable[str],
) -> PublicClaimDraft:
    """Build a proposed bounded public-claim draft."""

    return PublicClaimDraft(
        claim_id=claim_id,
        scope=scope,
        text=text,
        source_artifact_kinds=tuple(source_artifact_kinds),
        evidence_ids=tuple(evidence_ids),
    )


def review_public_claim(
    *,
    review_id: str,
    draft: PublicClaimDraft,
    evidence_index: Wave8EvidenceIndex,
    readiness_scorecard: Wave8ReadinessScorecard,
    falsification_matrix: Wave8FalsificationMatrix,
) -> PublicClaimReview:
    """Review a public claim draft against Wave 8 evidence gates."""

    matched_entry_ids = _matched_entry_ids(
        evidence_index=evidence_index,
        source_artifact_kinds=draft.source_artifact_kinds,
    )
    findings: list[str] = []
    if draft.overclaims:
        findings.append("public-claim-overclaims-scope")
    if evidence_index.decision is not EvidenceIndexDecision.READY_FOR_REVIEW_QUERY:
        findings.append(f"evidence-index-not-ready:{evidence_index.decision.value}")
    if (
        readiness_scorecard.decision
        is not Wave8ReadinessDecision.READY_FOR_REVIEW_HANDOFF
    ):
        findings.append(
            f"readiness-scorecard-not-ready:{readiness_scorecard.decision.value}"
        )
    if (
        falsification_matrix.decision
        is not FalsificationMatrixDecision.SURVIVED_BOUNDED_FALSIFICATION
    ):
        findings.append(
            f"falsification-matrix-not-survived:{falsification_matrix.decision.value}"
        )
    if not matched_entry_ids:
        findings.append("missing-source-artifact-kinds")

    decision = _public_claim_decision(findings)

    return PublicClaimReview(
        review_id=review_id,
        draft=draft,
        evidence_index_fingerprint=evidence_index.fingerprint(),
        readiness_scorecard_fingerprint=readiness_scorecard.fingerprint(),
        falsification_matrix_fingerprint=falsification_matrix.fingerprint(),
        decision=decision,
        findings=tuple(findings),
        matched_entry_ids=matched_entry_ids,
    )


def _matched_entry_ids(
    *,
    evidence_index: Wave8EvidenceIndex,
    source_artifact_kinds: tuple[EvidenceArtifactKind, ...],
) -> tuple[str, ...]:
    requested = set(source_artifact_kinds)
    return tuple(
        sorted(
            entry.entry_id for entry in evidence_index.entries if entry.kind in requested
        )
    )


def _public_claim_decision(findings: list[str]) -> PublicClaimDecision:
    if "public-claim-overclaims-scope" in findings:
        return PublicClaimDecision.BLOCKED_OVERCLAIM
    if any(finding.startswith("evidence-index-not-ready") for finding in findings):
        return PublicClaimDecision.NEEDS_READY_EVIDENCE_INDEX
    if any(finding.startswith("readiness-scorecard-not-ready") for finding in findings):
        return PublicClaimDecision.NEEDS_READY_SCORECARD
    if any(
        finding.startswith("falsification-matrix-not-survived") for finding in findings
    ):
        return PublicClaimDecision.NEEDS_FALSIFICATION_SURVIVAL
    if "missing-source-artifact-kinds" in findings:
        return PublicClaimDecision.NEEDS_SOURCE_ARTIFACTS
    return PublicClaimDecision.APPROVED_BOUNDED_REVIEW_CLAIM


def _normalize_unique_artifact_kinds(
    values: Iterable[EvidenceArtifactKind],
) -> tuple[EvidenceArtifactKind, ...]:
    normalized: list[EvidenceArtifactKind] = []
    seen: set[EvidenceArtifactKind] = set()
    for value in values:
        if value in seen:
            raise ValueError(f"Duplicate artifact kind: {value.value}")
        seen.add(value)
        normalized.append(value)
    return tuple(sorted(normalized, key=lambda value: value.value))


def _contains_overclaiming_text(value: str) -> bool:
    lowered = value.casefold()
    blocked_terms = (
        "agi",
        "artificial general intelligence",
        "certified intelligence",
        "certifies intelligence",
        "certifies artificial intelligence",
        "certifies artificial general intelligence",
        "general intelligence achieved",
        "human-level intelligence",
        "deployment approved",
        "autonomous authority",
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


def _normalize_unique_text_tuple(values: Iterable[str], *, label: str) -> tuple[str, ...]:
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
