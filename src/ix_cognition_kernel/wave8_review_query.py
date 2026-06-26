"""Wave 8 review query.

This module adds deterministic review queries over the Wave 8 evidence index.
It does not certify intelligence. It lets reviewers ask bounded questions about
indexed artifacts, source kinds, readiness, blocked evidence, parent links, and
claim-boundary text without letting query text override the evidence chain.

Review-query doctrine:

- queries inspect evidence; they do not create evidence,
- blocked indexes fail closed unless explicitly allowed for blocked-only review,
- ready-only queries must not hide blocked entries in the source index,
- parent links must remain visible,
- overclaiming query terms are blocked,
- query results are bound to the exact evidence-index fingerprint,
- no query may certify AGI or deployment readiness.
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
    EvidenceIndexEntry,
    EvidenceIndexEntryStatus,
    Wave8EvidenceIndex,
)

WAVE_EIGHT_REVIEW_QUERY_REQUEST_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave8-review-query-request-v1"
)
WAVE_EIGHT_REVIEW_QUERY_RESULT_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave8-review-query-result-v1"
)


class ReviewQueryMode(StrEnum):
    """Supported bounded evidence-index query modes."""

    BY_KIND = "by-kind"
    BY_STATUS = "by-status"
    BY_TEXT = "by-text"
    BY_PARENT = "by-parent"
    READY_ONLY = "ready-only"
    BLOCKED_ONLY = "blocked-only"


class ReviewQueryDecision(StrEnum):
    """Fail-closed review-query decision."""

    MATCHES_READY = "matches-ready"
    NO_MATCHES = "no-matches"
    INDEX_NOT_READY = "index-not-ready"
    BLOCKED_OVERCLAIM = "blocked-overclaim"


@dataclass(frozen=True, slots=True)
class ReviewQueryRequest:
    """Bounded query request over a Wave 8 evidence index."""

    query_id: str
    mode: ReviewQueryMode
    artifact_kinds: tuple[EvidenceArtifactKind, ...] = ()
    statuses: tuple[EvidenceIndexEntryStatus, ...] = ()
    text_terms: tuple[str, ...] = ()
    parent_entry_ids: tuple[str, ...] = ()
    allow_blocked_index: bool = False
    evidence_ids: tuple[str, ...] = ()
    schema_version: str = WAVE_EIGHT_REVIEW_QUERY_REQUEST_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate bounded query request."""

        object.__setattr__(
            self,
            "query_id",
            _require_non_empty(self.query_id, "query_id"),
        )
        object.__setattr__(
            self,
            "artifact_kinds",
            _normalize_unique_artifact_kinds(self.artifact_kinds),
        )
        object.__setattr__(
            self,
            "statuses",
            _normalize_unique_statuses(self.statuses),
        )
        object.__setattr__(
            self,
            "text_terms",
            _normalize_unique_text_tuple(self.text_terms, label="text_term"),
        )
        object.__setattr__(
            self,
            "parent_entry_ids",
            _normalize_unique_text_tuple(
                self.parent_entry_ids,
                label="parent_entry_id",
            ),
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
        for term in self.text_terms:
            _reject_overclaiming_text(term, "text_term")
        if not self.evidence_ids:
            raise ValueError("Review query requests require evidence ids.")
        _validate_mode_fields(self)

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic query-request payload."""

        return {
            "allow_blocked_index": self.allow_blocked_index,
            "artifact_kinds": [kind.value for kind in self.artifact_kinds],
            "evidence_ids": list(self.evidence_ids),
            "mode": self.mode.value,
            "parent_entry_ids": list(self.parent_entry_ids),
            "query_id": self.query_id,
            "schema_version": self.schema_version,
            "statuses": [status.value for status in self.statuses],
            "text_terms": list(self.text_terms),
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this query request."""

        return _stable_sha256(self.canonical_payload())


@dataclass(frozen=True, slots=True)
class ReviewQueryResult:
    """Result of a bounded evidence-index query."""

    result_id: str
    request: ReviewQueryRequest
    index_fingerprint: str
    decision: ReviewQueryDecision
    matched_entries: tuple[EvidenceIndexEntry, ...]
    findings: tuple[str, ...]
    schema_version: str = WAVE_EIGHT_REVIEW_QUERY_RESULT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate query result bindings and fail-closed findings."""

        object.__setattr__(
            self,
            "result_id",
            _require_non_empty(self.result_id, "result_id"),
        )
        object.__setattr__(
            self,
            "index_fingerprint",
            _require_sha256(self.index_fingerprint, "index_fingerprint"),
        )
        object.__setattr__(
            self,
            "matched_entries",
            tuple(self.matched_entries),
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
        seen: set[str] = set()
        for entry in self.matched_entries:
            if entry.entry_id in seen:
                raise ValueError(f"Duplicate matched entry id: {entry.entry_id}")
            seen.add(entry.entry_id)
        if self.decision is ReviewQueryDecision.MATCHES_READY:
            if not self.matched_entries:
                raise ValueError("Ready review query results require matches.")
        elif not self.findings:
            raise ValueError("Non-ready review query results require findings.")

    @property
    def matched_entry_ids(self) -> tuple[str, ...]:
        """Return matched entry ids in deterministic order."""

        return tuple(entry.entry_id for entry in self.matched_entries)

    @property
    def ready(self) -> bool:
        """Return whether the query produced ready matches."""

        return self.decision is ReviewQueryDecision.MATCHES_READY

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic query-result payload."""

        return {
            "decision": self.decision.value,
            "findings": list(self.findings),
            "index_fingerprint": self.index_fingerprint,
            "matched_entry_fingerprints": [
                entry.fingerprint() for entry in self.matched_entries
            ],
            "request_fingerprint": self.request.fingerprint(),
            "result_id": self.result_id,
            "schema_version": self.schema_version,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this query result."""

        return _stable_sha256(self.canonical_payload())


def build_review_query_request(
    *,
    query_id: str,
    mode: ReviewQueryMode,
    artifact_kinds: Iterable[EvidenceArtifactKind] = (),
    statuses: Iterable[EvidenceIndexEntryStatus] = (),
    text_terms: Iterable[str] = (),
    parent_entry_ids: Iterable[str] = (),
    allow_blocked_index: bool = False,
    evidence_ids: Iterable[str],
) -> ReviewQueryRequest:
    """Build a deterministic bounded evidence-index query request."""

    return ReviewQueryRequest(
        query_id=query_id,
        mode=mode,
        artifact_kinds=tuple(artifact_kinds),
        statuses=tuple(statuses),
        text_terms=tuple(text_terms),
        parent_entry_ids=tuple(parent_entry_ids),
        allow_blocked_index=allow_blocked_index,
        evidence_ids=tuple(evidence_ids),
    )


def execute_review_query(
    *,
    result_id: str,
    index: Wave8EvidenceIndex,
    request: ReviewQueryRequest,
) -> ReviewQueryResult:
    """Execute a bounded review query against an evidence index."""

    if _request_overclaims(request):
        return ReviewQueryResult(
            result_id=result_id,
            request=request,
            index_fingerprint=index.fingerprint(),
            decision=ReviewQueryDecision.BLOCKED_OVERCLAIM,
            matched_entries=(),
            findings=("review-query-overclaims-scope",),
        )

    if (
        index.decision is not EvidenceIndexDecision.READY_FOR_REVIEW_QUERY
        and not request.allow_blocked_index
    ):
        return ReviewQueryResult(
            result_id=result_id,
            request=request,
            index_fingerprint=index.fingerprint(),
            decision=ReviewQueryDecision.INDEX_NOT_READY,
            matched_entries=(),
            findings=(f"evidence-index-not-ready:{index.decision.value}",),
        )

    matches = _matches_for_request(index=index, request=request)
    if not matches:
        return ReviewQueryResult(
            result_id=result_id,
            request=request,
            index_fingerprint=index.fingerprint(),
            decision=ReviewQueryDecision.NO_MATCHES,
            matched_entries=(),
            findings=("review-query-produced-no-matches",),
        )

    return ReviewQueryResult(
        result_id=result_id,
        request=request,
        index_fingerprint=index.fingerprint(),
        decision=ReviewQueryDecision.MATCHES_READY,
        matched_entries=matches,
        findings=(),
    )


def _matches_for_request(
    *,
    index: Wave8EvidenceIndex,
    request: ReviewQueryRequest,
) -> tuple[EvidenceIndexEntry, ...]:
    entries = index.entries
    if request.mode is ReviewQueryMode.BY_KIND:
        requested_kinds = set(request.artifact_kinds)
        entries = tuple(entry for entry in entries if entry.kind in requested_kinds)
    elif request.mode is ReviewQueryMode.BY_STATUS:
        requested_statuses = set(request.statuses)
        entries = tuple(entry for entry in entries if entry.status in requested_statuses)
    elif request.mode is ReviewQueryMode.BY_TEXT:
        entries = tuple(
            entry for entry in entries if _entry_matches_text_terms(entry, request)
        )
    elif request.mode is ReviewQueryMode.BY_PARENT:
        requested_parents = set(request.parent_entry_ids)
        entries = tuple(
            entry
            for entry in entries
            if requested_parents.intersection(entry.parent_entry_ids)
        )
    elif request.mode is ReviewQueryMode.READY_ONLY:
        entries = tuple(entry for entry in entries if entry.ready)
    elif request.mode is ReviewQueryMode.BLOCKED_ONLY:
        entries = tuple(entry for entry in entries if entry.blocked)

    return tuple(sorted(entries, key=lambda entry: entry.entry_id))


def _entry_matches_text_terms(
    entry: EvidenceIndexEntry,
    request: ReviewQueryRequest,
) -> bool:
    haystack = " ".join(
        (
            entry.entry_id,
            entry.kind.value,
            entry.title,
            entry.claim_boundary,
            " ".join(entry.evidence_ids),
            " ".join(entry.findings),
        )
    ).casefold()
    return all(term.casefold() in haystack for term in request.text_terms)


def _request_overclaims(request: ReviewQueryRequest) -> bool:
    return any(_contains_overclaiming_text(term) for term in request.text_terms)


def _validate_mode_fields(request: ReviewQueryRequest) -> None:
    if request.mode is ReviewQueryMode.BY_KIND and not request.artifact_kinds:
        raise ValueError("BY_KIND review queries require artifact kinds.")
    if request.mode is ReviewQueryMode.BY_STATUS and not request.statuses:
        raise ValueError("BY_STATUS review queries require statuses.")
    if request.mode is ReviewQueryMode.BY_TEXT and not request.text_terms:
        raise ValueError("BY_TEXT review queries require text terms.")
    if request.mode is ReviewQueryMode.BY_PARENT and not request.parent_entry_ids:
        raise ValueError("BY_PARENT review queries require parent entry ids.")


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


def _normalize_unique_statuses(
    values: Iterable[EvidenceIndexEntryStatus],
) -> tuple[EvidenceIndexEntryStatus, ...]:
    normalized: list[EvidenceIndexEntryStatus] = []
    seen: set[EvidenceIndexEntryStatus] = set()
    for value in values:
        if value in seen:
            raise ValueError(f"Duplicate status: {value.value}")
        seen.add(value)
        normalized.append(value)
    return tuple(sorted(normalized, key=lambda value: value.value))


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
