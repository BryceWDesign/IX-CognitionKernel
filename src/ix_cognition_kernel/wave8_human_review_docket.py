"""Wave 8 human review docket.

This module adds a deterministic human-review docket for the Recursive
Reality-Corrected Learner. It does not certify intelligence, approve deployment,
or update public documentation. It turns a ready review handoff into reviewer
work items that preserve claim boundaries, source bindings, and fail-closed
handoff status.

Human-review docket doctrine:

- humans remain the authority,
- docket readiness is not certification,
- a blocked handoff blocks the docket,
- reviewer items must bind back to evidence,
- public claims stay narrower than internal evidence,
- unanswered review work cannot be hidden,
- no docket may declare AGI or deployment approval.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from ix_cognition_kernel.wave8_review_handoff import (
    ReviewHandoffDecision,
    Wave8ReviewHandoff,
)

WAVE_EIGHT_HUMAN_REVIEW_ITEM_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave8-human-review-item-v1"
)
WAVE_EIGHT_HUMAN_REVIEW_DOCKET_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave8-human-review-docket-v1"
)


class HumanReviewRole(StrEnum):
    """Required Wave 8 human-review roles."""

    HUMAN_AUTHORITY = "human-authority"
    INDEPENDENT_REPLAYER = "independent-replayer"
    SAFETY_REVIEWER = "safety-reviewer"
    TRANSFER_REVIEWER = "transfer-reviewer"
    BASELINE_REVIEWER = "baseline-reviewer"
    CLAIM_BOUNDARY_REVIEWER = "claim-boundary-reviewer"


class HumanReviewItemDecision(StrEnum):
    """Decision for one review item."""

    READY_FOR_REVIEW = "ready-for-review"
    NEEDS_EVIDENCE = "needs-evidence"
    BLOCKED_BY_HANDOFF = "blocked-by-handoff"


class HumanReviewDocketDecision(StrEnum):
    """Overall human-review docket decision."""

    READY_FOR_HUMAN_REVIEW = "ready-for-human-review"
    NEEDS_EVIDENCE = "needs-evidence"
    BLOCKED_BY_HANDOFF = "blocked-by-handoff"
    OVERCLAIM_BLOCKED = "overclaim-blocked"


@dataclass(frozen=True, slots=True)
class HumanReviewItem:
    """One reviewer work item bound to Wave 8 evidence."""

    item_id: str
    role: HumanReviewRole
    question: str
    decision: HumanReviewItemDecision
    source_entry_ids: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    findings: tuple[str, ...] = ()
    schema_version: str = WAVE_EIGHT_HUMAN_REVIEW_ITEM_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate reviewer item bindings."""

        object.__setattr__(
            self,
            "item_id",
            _require_non_empty(self.item_id, "item_id"),
        )
        object.__setattr__(
            self,
            "question",
            _require_non_empty(self.question, "question"),
        )
        _reject_overclaiming_text(self.question, "question")
        object.__setattr__(
            self,
            "source_entry_ids",
            _normalize_unique_text_tuple(
                self.source_entry_ids,
                label="source_entry_id",
            ),
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
        if not self.source_entry_ids:
            raise ValueError("Human review items require source entry ids.")
        if not self.evidence_ids:
            raise ValueError("Human review items require evidence ids.")
        if (
            self.decision is not HumanReviewItemDecision.READY_FOR_REVIEW
            and not self.findings
        ):
            raise ValueError("Non-ready human review items require findings.")

    @property
    def ready(self) -> bool:
        """Return whether this item is ready for human review."""

        return self.decision is HumanReviewItemDecision.READY_FOR_REVIEW

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic human-review item payload."""

        return {
            "decision": self.decision.value,
            "evidence_ids": list(self.evidence_ids),
            "findings": list(self.findings),
            "item_id": self.item_id,
            "question": self.question,
            "role": self.role.value,
            "schema_version": self.schema_version,
            "source_entry_ids": list(self.source_entry_ids),
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this item."""

        return _stable_sha256(self.canonical_payload())


@dataclass(frozen=True, slots=True)
class Wave8HumanReviewDocket:
    """Deterministic Wave 8 human-review docket."""

    docket_id: str
    purpose: str
    claim_boundary: str
    handoff_fingerprint: str
    items: tuple[HumanReviewItem, ...]
    decision: HumanReviewDocketDecision
    findings: tuple[str, ...]
    schema_version: str = WAVE_EIGHT_HUMAN_REVIEW_DOCKET_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate docket coverage and fail-closed decision."""

        object.__setattr__(
            self,
            "docket_id",
            _require_non_empty(self.docket_id, "docket_id"),
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
        object.__setattr__(
            self,
            "handoff_fingerprint",
            _require_sha256(self.handoff_fingerprint, "handoff_fingerprint"),
        )
        _reject_overclaiming_text(self.purpose, "purpose")
        _reject_overclaiming_text(self.claim_boundary, "claim_boundary")
        object.__setattr__(
            self,
            "items",
            tuple(self.items),
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
        if not self.items:
            raise ValueError("Wave 8 human review dockets require items.")
        seen_ids: set[str] = set()
        for item in self.items:
            if item.item_id in seen_ids:
                raise ValueError(f"Duplicate human review item id: {item.item_id}")
            seen_ids.add(item.item_id)
        missing = _missing_required_roles(self.items)
        if missing:
            raise ValueError(
                f"Wave 8 human review dockets are missing roles: {','.join(missing)}"
            )
        if (
            self.decision is not HumanReviewDocketDecision.READY_FOR_HUMAN_REVIEW
            and not self.findings
        ):
            raise ValueError("Non-ready human review dockets require findings.")

    @property
    def ready(self) -> bool:
        """Return whether the docket is ready for human review."""

        return self.decision is HumanReviewDocketDecision.READY_FOR_HUMAN_REVIEW

    @property
    def ready_item_count(self) -> int:
        """Return count of ready review items."""

        return sum(1 for item in self.items if item.ready)

    @property
    def blocked_item_count(self) -> int:
        """Return count of blocked review items."""

        return sum(
            1
            for item in self.items
            if item.decision is HumanReviewItemDecision.BLOCKED_BY_HANDOFF
        )

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic human-review docket payload."""

        return {
            "claim_boundary": self.claim_boundary,
            "decision": self.decision.value,
            "docket_id": self.docket_id,
            "findings": list(self.findings),
            "handoff_fingerprint": self.handoff_fingerprint,
            "item_fingerprints": [item.fingerprint() for item in self.items],
            "purpose": self.purpose,
            "schema_version": self.schema_version,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this docket."""

        return _stable_sha256(self.canonical_payload())


def default_human_review_items(
    *,
    handoff: Wave8ReviewHandoff,
    evidence_prefix: str = "wave8-human-review",
) -> tuple[HumanReviewItem, ...]:
    """Build default reviewer work items from a Wave 8 handoff."""

    prefix = _require_non_empty(evidence_prefix, "evidence_prefix")
    ready = handoff.ready
    decision = (
        HumanReviewItemDecision.READY_FOR_REVIEW
        if ready
        else HumanReviewItemDecision.BLOCKED_BY_HANDOFF
    )
    findings = () if ready else (f"handoff-not-ready:{handoff.decision.value}",)
    specs = (
        (
            "authority",
            HumanReviewRole.HUMAN_AUTHORITY,
            "Does the handoff preserve human authority over all readiness claims?",
            ("entry-release-manifest", "entry-readiness-scorecard"),
        ),
        (
            "replay",
            HumanReviewRole.INDEPENDENT_REPLAYER,
            "Can the replay evidence be independently inspected and reproduced?",
            ("entry-replay-report", "entry-task-suite"),
        ),
        (
            "safety",
            HumanReviewRole.SAFETY_REVIEWER,
            "Do negative controls and fail-closed gates block unsafe claims?",
            ("entry-negative-control-report", "entry-readiness-scorecard"),
        ),
        (
            "transfer",
            HumanReviewRole.TRANSFER_REVIEWER,
            "Does transfer evidence exceed original-task-only performance?",
            ("entry-transfer-report", "entry-skill-validation"),
        ),
        (
            "baseline",
            HumanReviewRole.BASELINE_REVIEWER,
            "Does the candidate improve against model-alone baseline evidence?",
            ("entry-baseline-report",),
        ),
        (
            "claim-boundary",
            HumanReviewRole.CLAIM_BOUNDARY_REVIEWER,
            "Is the public claim narrower than the indexed evidence?",
            ("entry-readiness-scorecard", "entry-negative-control-report"),
        ),
    )
    return tuple(
        HumanReviewItem(
            item_id=f"{prefix}:{slug}",
            role=role,
            question=question,
            decision=decision,
            source_entry_ids=source_entry_ids,
            evidence_ids=(handoff.fingerprint(), f"{prefix}:{slug}:evidence"),
            findings=findings,
        )
        for slug, role, question, source_entry_ids in specs
    )


def build_wave8_human_review_docket(
    *,
    docket_id: str,
    purpose: str,
    claim_boundary: str,
    handoff: Wave8ReviewHandoff,
    items: Iterable[HumanReviewItem],
) -> Wave8HumanReviewDocket:
    """Build a deterministic Wave 8 human-review docket."""

    item_tuple = tuple(items)
    findings = _docket_findings(handoff=handoff, items=item_tuple)
    decision = _docket_decision(handoff=handoff, findings=findings)
    return Wave8HumanReviewDocket(
        docket_id=docket_id,
        purpose=purpose,
        claim_boundary=claim_boundary,
        handoff_fingerprint=handoff.fingerprint(),
        items=item_tuple,
        decision=decision,
        findings=findings,
    )


def _docket_findings(
    *,
    handoff: Wave8ReviewHandoff,
    items: tuple[HumanReviewItem, ...],
) -> tuple[str, ...]:
    findings: list[str] = []
    if handoff.decision is ReviewHandoffDecision.BLOCKED_OVERCLAIM:
        findings.append("handoff-overclaim-blocked")
    elif handoff.decision is not ReviewHandoffDecision.READY_FOR_HUMAN_REVIEW:
        findings.append(f"handoff-not-ready:{handoff.decision.value}")

    non_ready_ids = tuple(sorted(item.item_id for item in items if not item.ready))
    if non_ready_ids:
        findings.append(f"non-ready-human-review-items:{','.join(non_ready_ids)}")
    return tuple(findings)


def _docket_decision(
    *,
    handoff: Wave8ReviewHandoff,
    findings: tuple[str, ...],
) -> HumanReviewDocketDecision:
    if "handoff-overclaim-blocked" in findings:
        return HumanReviewDocketDecision.OVERCLAIM_BLOCKED
    if any(finding.startswith("handoff-not-ready") for finding in findings):
        return HumanReviewDocketDecision.BLOCKED_BY_HANDOFF
    if any(finding.startswith("non-ready-human-review-items") for finding in findings):
        return HumanReviewDocketDecision.NEEDS_EVIDENCE
    if handoff.decision is not ReviewHandoffDecision.READY_FOR_HUMAN_REVIEW:
        return HumanReviewDocketDecision.BLOCKED_BY_HANDOFF
    return HumanReviewDocketDecision.READY_FOR_HUMAN_REVIEW


def _missing_required_roles(items: Iterable[HumanReviewItem]) -> tuple[str, ...]:
    required = {
        HumanReviewRole.HUMAN_AUTHORITY,
        HumanReviewRole.INDEPENDENT_REPLAYER,
        HumanReviewRole.SAFETY_REVIEWER,
        HumanReviewRole.TRANSFER_REVIEWER,
        HumanReviewRole.BASELINE_REVIEWER,
        HumanReviewRole.CLAIM_BOUNDARY_REVIEWER,
    }
    present = {item.role for item in items}
    return tuple(sorted(role.value for role in required - present))


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
