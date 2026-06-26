"""Wave 8 review query.

This module adds a deterministic review-query layer over the Wave 8 evidence
index. It does not certify intelligence. It lets reviewers ask bounded questions
against indexed artifacts while preserving claim boundaries, source
fingerprints, parent relationships, readiness status, and fail-closed behavior.

Review-query doctrine:

- queries are review aids, not proof,
- a query cannot override the evidence index,
- blocked indexes remain blocked,
- parent/child relationships remain visible,
- overclaiming query text fails closed,
- ready-only filters cannot hide blocked artifacts,
- no query may certify AGI or broad competence.
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

WAVE_EIGHT_REVIEW_QUERY_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave8-review-query-v1"
)
WAVE_EIGHT_REVIEW_QUERY_RESULT_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave8-review-query-result-v1"
)


class ReviewQueryMode(StrEnum):
    """Supported bounded review-query modes."""

    BY_KIND = "by-kind"
    BY_STATUS = "by-status"
    BY_TEXT = "by-text"
    BY_PARENT = "by-parent"
    READY_ONLY = "ready-only"
    BLOCKED_ONLY = "blocked-only"


class ReviewQueryDecision(StrEnum):
    """Fail-closed decision for a review query."""

    MATCHES_READY = "matches-ready"
    NO_MATCHES = "no-matches"
    BLOCKED_INDEX = "blocked-index"
    OVERCLAIM_BLOCKED = "overclaim-blocked"


@dataclass(frozen=True, slots=True)
class ReviewQueryRequest:
    """Bounded evidence-index query request."""

    query_id: str
    mode: ReviewQueryMode
    search_terms: tuple[str, ...]
    artifact_kinds: tuple[EvidenceArtifactKind, ...]
    statuses: tuple[EvidenceIndexEntryStatus, ...]
    parent_entry_ids: tuple[str, ...]
    require_ready_index: bool
    evidence_ids: tuple[str, ...]
    schema_version: str = WAVE_EIGHT_REVIEW_QUERY_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate query scope and evidence."""

        object.__setattr__(
            self,
            "query_id",
            _require_non_empty(self.query_id, "query_id"),
        )
        object.__setattr__(
            self,
            "search_terms",
            _normalize_unique_text_tuple(self.search_terms, label="search_term"),
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
            "parent_entry_ids",
            _dedupe_text_tuple(self.parent_entry_ids, label="parent_entry_id"),
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
        for term in self.search_terms:
            _reject_overclaiming_text(term, "search_term")
        if not self.evidence_ids:
            raise ValueError("Review query requests require evidence ids.")
        if self.mode is ReviewQueryMode.BY_KIND and not self.artifact_kinds:
            raise ValueError("BY_KIND queries require artifact kinds.")
        if self.mode is ReviewQueryMode.BY_STATUS and not self.statuses:
            raise ValueError("BY_STATUS queries require statuses.")
        if self.mode is ReviewQueryMode.BY_TEXT and not self.search_terms:
            raise ValueError("BY_TEXT queries require search terms.")
        if self.mode is ReviewQueryMode.BY_PARENT and not self.parent_entry_ids:
            raise ValueError("BY_PARENT queries require parent entry ids.")

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic review-query payload."""

        return {
            "artifact_kinds": [kind.value for kind in self.artifact_kinds],
            "evidence_ids": list(self.evidence_ids),
            "mode": self.mode.value,
            "parent_entry_ids": list(self.parent_entry_ids),
            "query_id": self.query_id,
            "require_ready_index": self.require_ready_index,
            "schema_version": self.schema_version,
            "search_terms": list(self.search_terms),
            "statuses": [status.value for status in self.statuses],
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this query."""

        return _stable_sha256(self.canonical_payload())


@dataclass(frozen=True, slots=True)
class ReviewQueryResult:
    """Deterministic result for a bounded evidence-index query."""

    result_id: str
    request: ReviewQueryRequest
    index_fingerprint: str
    matched_entries: tuple[EvidenceIndexEntry, ...]
    decision: ReviewQueryDecision
    findings: tuple[str, ...]
    schema_version: str = WAVE_EIGHT_REVIEW_QUERY_RESULT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate query-result payload."""

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
        if self.decision is not ReviewQueryDecision.MATCHES_READY:
            if not self.findings:
                raise ValueError("Non-ready review query results require findings.")
        if self.decision is ReviewQueryDecision.NO_MATCHES and self.matched_entries:
            raise ValueError("NO_MATCHES results cannot contain matched entries.")

    @property
    def ready(self) -> bool:
        """Return whether this query produced ready matches."""

        return self.decision is ReviewQueryDecision.MATCHES_READY

    @property
    def match_count(self) -> int:
        """Return count of matched entries."""

        return len(self.matched_entries)

    @property
    def matched_entry_ids(self) -> tuple[str, ...]:
        """Return matched entry ids in deterministic order."""

        return tuple(entry.entry_id for entry in self.matched_entries)

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
    search_terms: Iterable[str] = (),
    artifact_kinds: Iterable[EvidenceArtifactKind] = (),
    statuses: Iterable[EvidenceIndexEntryStatus] = (),
    parent_entry_ids: Iterable[str] = (),
    require_ready_index: bool = True,
    evidence_ids: Iterable[str],
) -> ReviewQueryRequest:
    """Build a bounded review query request."""

    return ReviewQueryRequest(
        query_id=query_id,
        mode=mode,
        search_terms=tuple(search_terms),
        artifact_kinds=tuple(artifact_kinds),
        statuses=tuple(statuses),
        parent_entry_ids=tuple(parent_entry_ids),
        require_ready_index=require_ready_index,
        evidence_ids=tuple(evidence_ids),
    )


def execute_review_query(
    *,
    result_id: str,
    index: Wave8EvidenceIndex,
    request: ReviewQueryRequest,
) -> ReviewQueryResult:
    """Execute a fail-closed review query against a Wave 8 evidence index."""

    findings: list[str] = []
    if (
        request.require_ready_index
        and index.decision is not EvidenceIndexDecision.READY_FOR_REVIEW_QUERY
    ):
        findings.append(f"index-not-ready:{index.decision.value}")
        return ReviewQueryResult(
            result_id=result_id,
            request=request,
            index_fingerprint=index.fingerprint(),
            matched_entries=(),
            decision=ReviewQueryDecision.BLOCKED_INDEX,
            findings=tuple(findings),
        )

    matched = _matched_entries(index=index, request=request)
    if not matched:
        findings.append("query-produced-no-matches")
        decision = ReviewQueryDecision.NO_MATCHES
    else:
        decision = ReviewQueryDecision.MATCHES_READY

    return ReviewQueryResult(
        result_id=result_id,
        request=request,
        index_fingerprint=index.fingerprint(),
        matched_entries=matched,
        decision=decision,
        findings=tuple(findings),
    )


def _matched_entries(
    *,
    index: Wave8EvidenceIndex,
    request: ReviewQueryRequest,
) -> tuple[EvidenceIndexEntry, ...]:
    entries = index.entries
    if request.mode is ReviewQueryMode.BY_KIND:
        kind_set = set(request.artifact_kinds)
        entries = tuple(entry for entry in entries if entry.kind in kind_set)
    elif request.mode is ReviewQueryMode.BY_STATUS:
        status_set = set(request.statuses)
        entries = tuple(entry for entry in entries if entry.status in status_set)
    elif request.mode is ReviewQueryMode.BY_TEXT:
        entries = tuple(
            entry for entry in entries if _entry_matches_terms(entry, request.search_terms)
        )
    elif request.mode is ReviewQueryMode.BY_PARENT:
        parent_ids = set(request.parent_entry_ids)
        entries = tuple(
            entry
            for entry in entries
            if parent_ids.intersection(entry.parent_entry_ids)
        )
    elif request.mode is ReviewQueryMode.READY_ONLY:
        entries = tuple(entry for entry in entries if entry.ready)
    elif request.mode is ReviewQueryMode.BLOCKED_ONLY:
        entries = tuple(entry for entry in entries if entry.blocked)

    return tuple(sorted(entries, key=lambda entry: entry.entry_id))


def _entry_matches_terms(
    entry: EvidenceIndexEntry,
    terms: tuple[str, ...],
) -> bool:
    haystack = " ".join(
        (
            entry.entry_id,
            entry.kind.value,
            entry.status.value,
            entry.title,
            entry.claim_boundary,
            " ".join(entry.findings),
            " ".join(entry.parent_entry_ids),
        )
    ).casefold()
    return all(term.casefold() in haystack for term in terms)


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
            raise ValueError(f"Duplicate evidence status: {value.value}")
        seen.add(value)
        normalized.append(value)
    return tuple(sorted(normalized, key=lambda value: value.value))


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
