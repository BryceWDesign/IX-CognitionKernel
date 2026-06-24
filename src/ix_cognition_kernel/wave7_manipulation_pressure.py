"""Wave 7 manipulation pressure checks.

Persistent cognitive systems must defend against manipulation across turns,
sessions, fragments, goals, body contracts, and runtime handoffs. This module
detects pressure patterns that try to launder intent, skip evidence, inflate
claims, bypass authority, or fragment unsafe behavior into smaller requests.

Wave 7 manipulation doctrine:

- fragmented intent must remain assembleable for review,
- authority laundering must be visible,
- claim inflation must be blocked,
- pressure to skip evidence must fail closed,
- cross-session risk must not be treated as isolated turns,
- manipulation detection is evidence-bound and replayable.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

WAVE_SEVEN_INTENT_FRAGMENT_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave7-cross-session-intent-fragment-v1"
)
WAVE_SEVEN_MANIPULATION_SIGNAL_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave7-manipulation-signal-v1"
)
WAVE_SEVEN_PRESSURE_PATTERN_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave7-pressure-pattern-v1"
)
WAVE_SEVEN_MANIPULATION_DECISION_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave7-manipulation-decision-v1"
)
WAVE_SEVEN_MANIPULATION_REPORT_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave7-manipulation-pressure-report-v1"
)


class IntentFragmentRisk(StrEnum):
    """Risk tags attached to a cross-session intent fragment."""

    AUTHORITY_LAUNDERING = "authority-laundering"
    CLAIM_INFLATION = "claim-inflation"
    EVIDENCE_SKIP = "evidence-skip"
    FRAGMENTED_INTENT = "fragmented-intent"
    SELF_APPROVAL = "self-approval"
    BODY_ESCALATION = "body-escalation"
    RUNTIME_ESCALATION = "runtime-escalation"


class ManipulationSignalKind(StrEnum):
    """Kinds of manipulation signals detected by Wave 7."""

    AUTHORITY_LAUNDERING = "authority-laundering"
    CLAIM_INFLATION = "claim-inflation"
    EVIDENCE_SKIP_PRESSURE = "evidence-skip-pressure"
    SELF_APPROVAL_PRESSURE = "self-approval-pressure"
    FRAGMENTED_INTENT_ASSEMBLY = "fragmented-intent-assembly"
    BODY_ESCALATION_PRESSURE = "body-escalation-pressure"
    RUNTIME_ESCALATION_PRESSURE = "runtime-escalation-pressure"


class ManipulationSeverity(StrEnum):
    """Severity of a manipulation signal or pattern."""

    INFO = "info"
    WATCH = "watch"
    REVIEW_REQUIRED = "review-required"
    BLOCKING = "blocking"


class PressurePatternKind(StrEnum):
    """Kinds of multi-turn or cross-session pressure patterns."""

    SINGLE_TURN = "single-turn"
    MULTI_TURN = "multi-turn"
    CROSS_SESSION = "cross-session"
    AUTHORITY_CHAIN = "authority-chain"
    CLAIM_ESCALATION_CHAIN = "claim-escalation-chain"
    EVIDENCE_BYPASS_CHAIN = "evidence-bypass-chain"


class ManipulationDecisionStatus(StrEnum):
    """Fail-closed decision for manipulation pressure."""

    CLEAR = "clear"
    WATCH = "watch"
    READY_FOR_HUMAN_REVIEW = "ready-for-human-review"
    BLOCKED = "blocked"


@dataclass(frozen=True, slots=True)
class CrossSessionIntentFragment:
    """Fragment of intent that may matter across turns or sessions."""

    fragment_id: str
    session_id: str
    turn_ids: tuple[str, ...]
    intent_summary: str
    normalized_intent_tags: tuple[str, ...]
    risk_tags: tuple[IntentFragmentRisk, ...]
    evidence_ids: tuple[str, ...]
    schema_version: str = WAVE_SEVEN_INTENT_FRAGMENT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate an intent fragment for replayable pressure review."""

        object.__setattr__(
            self,
            "fragment_id",
            _require_non_empty(self.fragment_id, "fragment_id"),
        )
        object.__setattr__(
            self,
            "session_id",
            _require_non_empty(self.session_id, "session_id"),
        )
        object.__setattr__(
            self,
            "turn_ids",
            _normalize_unique_text_tuple(self.turn_ids, label="turn_id"),
        )
        object.__setattr__(
            self,
            "intent_summary",
            _require_non_empty(self.intent_summary, "intent_summary"),
        )
        object.__setattr__(
            self,
            "normalized_intent_tags",
            _normalize_unique_text_tuple(
                self.normalized_intent_tags,
                label="normalized_intent_tag",
            ),
        )
        object.__setattr__(
            self,
            "risk_tags",
            tuple(sorted(set(self.risk_tags), key=lambda tag: tag.value)),
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
        if not self.turn_ids:
            raise ValueError("Intent fragments require turn ids.")
        if not self.normalized_intent_tags:
            raise ValueError("Intent fragments require normalized intent tags.")
        if not self.evidence_ids:
            raise ValueError("Intent fragments require evidence ids.")

    @property
    def risky(self) -> bool:
        """Return whether this fragment carries manipulation risk."""

        return bool(self.risk_tags)

    @property
    def risk_tag_values(self) -> tuple[str, ...]:
        """Return risk tag values."""

        return tuple(tag.value for tag in self.risk_tags)

    def carries(self, risk: IntentFragmentRisk) -> bool:
        """Return whether this fragment carries the given risk tag."""

        return risk in self.risk_tags

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic fragment payload."""

        return {
            "evidence_ids": list(self.evidence_ids),
            "fragment_id": self.fragment_id,
            "intent_summary": self.intent_summary,
            "normalized_intent_tags": list(self.normalized_intent_tags),
            "risk_tags": list(self.risk_tag_values),
            "schema_version": self.schema_version,
            "session_id": self.session_id,
            "turn_ids": list(self.turn_ids),
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this fragment."""

        return _stable_sha256(self.canonical_payload())


@dataclass(frozen=True, slots=True)
class ManipulationSignal:
    """Evidence-bound signal of manipulation pressure."""

    signal_id: str
    kind: ManipulationSignalKind
    severity: ManipulationSeverity
    summary: str
    evidence_ids: tuple[str, ...]
    fragment_ids: tuple[str, ...]
    requires_human_review: bool = False
    blocks_progress: bool = False
    schema_version: str = WAVE_SEVEN_MANIPULATION_SIGNAL_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate signal severity semantics."""

        object.__setattr__(
            self,
            "signal_id",
            _require_non_empty(self.signal_id, "signal_id"),
        )
        object.__setattr__(
            self,
            "summary",
            _require_non_empty(self.summary, "summary"),
        )
        object.__setattr__(
            self,
            "evidence_ids",
            _normalize_unique_text_tuple(self.evidence_ids, label="evidence_id"),
        )
        object.__setattr__(
            self,
            "fragment_ids",
            _normalize_unique_text_tuple(self.fragment_ids, label="fragment_id"),
        )
        object.__setattr__(
            self,
            "schema_version",
            _require_non_empty(self.schema_version, "schema_version"),
        )
        if not self.evidence_ids:
            raise ValueError("Manipulation signals require evidence ids.")
        if self.severity is ManipulationSeverity.BLOCKING and not self.blocks_progress:
            raise ValueError("Blocking manipulation signals must block progress.")
        if (
            self.severity is ManipulationSeverity.REVIEW_REQUIRED
            and not self.requires_human_review
        ):
            raise ValueError("Review-required signals must require human review.")
        if self.severity is ManipulationSeverity.INFO and (
            self.requires_human_review or self.blocks_progress
        ):
            raise ValueError("Info signals cannot require review or block.")

    @property
    def needs_review(self) -> bool:
        """Return whether this signal requires human review."""

        return self.requires_human_review

    @property
    def blocking(self) -> bool:
        """Return whether this signal blocks progress."""

        return self.blocks_progress

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic signal payload."""

        return {
            "blocks_progress": self.blocks_progress,
            "evidence_ids": list(self.evidence_ids),
            "fragment_ids": list(self.fragment_ids),
            "kind": self.kind.value,
            "requires_human_review": self.requires_human_review,
            "schema_version": self.schema_version,
            "severity": self.severity.value,
            "signal_id": self.signal_id,
            "summary": self.summary,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this signal."""

        return _stable_sha256(self.canonical_payload())


@dataclass(frozen=True, slots=True)
class PressurePattern:
    """Assembled manipulation pattern across fragments and signals."""

    pattern_id: str
    kind: PressurePatternKind
    severity: ManipulationSeverity
    summary: str
    fragment_ids: tuple[str, ...]
    signal_ids: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    requires_human_review: bool = False
    blocks_progress: bool = False
    schema_version: str = WAVE_SEVEN_PRESSURE_PATTERN_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate pressure pattern linkage and severity."""

        object.__setattr__(
            self,
            "pattern_id",
            _require_non_empty(self.pattern_id, "pattern_id"),
        )
        object.__setattr__(
            self,
            "summary",
            _require_non_empty(self.summary, "summary"),
        )
        object.__setattr__(
            self,
            "fragment_ids",
            _normalize_unique_text_tuple(self.fragment_ids, label="fragment_id"),
        )
        object.__setattr__(
            self,
            "signal_ids",
            _normalize_unique_text_tuple(self.signal_ids, label="signal_id"),
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
        if not self.fragment_ids:
            raise ValueError("Pressure patterns require fragment ids.")
        if not self.signal_ids:
            raise ValueError("Pressure patterns require signal ids.")
        if not self.evidence_ids:
            raise ValueError("Pressure patterns require evidence ids.")
        if self.severity is ManipulationSeverity.BLOCKING and not self.blocks_progress:
            raise ValueError("Blocking pressure patterns must block progress.")
        if (
            self.severity is ManipulationSeverity.REVIEW_REQUIRED
            and not self.requires_human_review
        ):
            raise ValueError("Review-required patterns must require human review.")
        if (
            self.kind is PressurePatternKind.CROSS_SESSION
            and len(self.fragment_ids) < 2
        ):
            raise ValueError("Cross-session patterns require multiple fragments.")

    @property
    def blocking(self) -> bool:
        """Return whether this pattern blocks progress."""

        return self.blocks_progress

    @property
    def needs_review(self) -> bool:
        """Return whether this pattern requires human review."""

        return self.requires_human_review

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic pressure-pattern payload."""

        return {
            "blocks_progress": self.blocks_progress,
            "evidence_ids": list(self.evidence_ids),
            "fragment_ids": list(self.fragment_ids),
            "kind": self.kind.value,
            "pattern_id": self.pattern_id,
            "requires_human_review": self.requires_human_review,
            "schema_version": self.schema_version,
            "severity": self.severity.value,
            "signal_ids": list(self.signal_ids),
            "summary": self.summary,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this pattern."""

        return _stable_sha256(self.canonical_payload())


@dataclass(frozen=True, slots=True)
class ManipulationDecision:
    """Decision produced from manipulation pressure analysis."""

    decision_id: str
    status: ManipulationDecisionStatus
    reason_ids: tuple[str, ...]
    required_authority_refs: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    schema_version: str = WAVE_SEVEN_MANIPULATION_DECISION_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate manipulation pressure decision."""

        object.__setattr__(
            self,
            "decision_id",
            _require_non_empty(self.decision_id, "decision_id"),
        )
        object.__setattr__(
            self,
            "reason_ids",
            _normalize_unique_text_tuple(self.reason_ids, label="reason_id"),
        )
        object.__setattr__(
            self,
            "required_authority_refs",
            _normalize_unique_text_tuple(
                self.required_authority_refs,
                label="required_authority_ref",
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
        if not self.reason_ids:
            raise ValueError("Manipulation decisions require reason ids.")
        if not self.evidence_ids:
            raise ValueError("Manipulation decisions require evidence ids.")
        if (
            self.status
            in {
                ManipulationDecisionStatus.READY_FOR_HUMAN_REVIEW,
                ManipulationDecisionStatus.BLOCKED,
            }
            and not self.required_authority_refs
        ):
            raise ValueError("Review or blocked decisions require authority refs.")
        if (
            self.status is ManipulationDecisionStatus.CLEAR
            and self.required_authority_refs
        ):
            raise ValueError("Clear decisions cannot require authority refs.")

    @property
    def blocked(self) -> bool:
        """Return whether this decision blocks progress."""

        return self.status is ManipulationDecisionStatus.BLOCKED

    @property
    def ready_for_review(self) -> bool:
        """Return whether this decision requires human review."""

        return self.status is ManipulationDecisionStatus.READY_FOR_HUMAN_REVIEW

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic manipulation-decision payload."""

        return {
            "decision_id": self.decision_id,
            "evidence_ids": list(self.evidence_ids),
            "reason_ids": list(self.reason_ids),
            "required_authority_refs": list(self.required_authority_refs),
            "schema_version": self.schema_version,
            "status": self.status.value,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this decision."""

        return _stable_sha256(self.canonical_payload())


@dataclass(frozen=True, slots=True)
class ManipulationPressureReport:
    """Replayable report for multi-turn manipulation pressure."""

    report_id: str
    fragments: tuple[CrossSessionIntentFragment, ...]
    signals: tuple[ManipulationSignal, ...]
    patterns: tuple[PressurePattern, ...]
    decision: ManipulationDecision
    notes: tuple[str, ...] = ()
    schema_version: str = WAVE_SEVEN_MANIPULATION_REPORT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate report linkage across fragments, signals, and patterns."""

        object.__setattr__(
            self,
            "report_id",
            _require_non_empty(self.report_id, "report_id"),
        )
        object.__setattr__(
            self,
            "fragments",
            tuple(sorted(self.fragments, key=lambda item: item.fragment_id)),
        )
        object.__setattr__(
            self,
            "signals",
            tuple(sorted(self.signals, key=lambda item: item.signal_id)),
        )
        object.__setattr__(
            self,
            "patterns",
            tuple(sorted(self.patterns, key=lambda item: item.pattern_id)),
        )
        object.__setattr__(
            self,
            "notes",
            _normalize_unique_text_tuple(self.notes, label="note"),
        )
        object.__setattr__(
            self,
            "schema_version",
            _require_non_empty(self.schema_version, "schema_version"),
        )
        if not self.fragments:
            raise ValueError("Manipulation pressure reports require fragments.")
        _ensure_unique(
            (fragment.fragment_id for fragment in self.fragments),
            label="fragment_id",
        )
        _ensure_unique((signal.signal_id for signal in self.signals), label="signal_id")
        _ensure_unique(
            (pattern.pattern_id for pattern in self.patterns),
            label="pattern_id",
        )
        fragment_ids = {fragment.fragment_id for fragment in self.fragments}
        signal_ids = {signal.signal_id for signal in self.signals}
        for signal in self.signals:
            missing = tuple(
                fragment_id
                for fragment_id in signal.fragment_ids
                if fragment_id not in fragment_ids
            )
            if missing:
                raise ValueError(
                    "Manipulation signal references missing fragments: "
                    + ", ".join(missing)
                )
        for pattern in self.patterns:
            missing_fragments = tuple(
                fragment_id
                for fragment_id in pattern.fragment_ids
                if fragment_id not in fragment_ids
            )
            missing_signals = tuple(
                signal_id
                for signal_id in pattern.signal_ids
                if signal_id not in signal_ids
            )
            if missing_fragments:
                raise ValueError(
                    "Pressure pattern references missing fragments: "
                    + ", ".join(missing_fragments)
                )
            if missing_signals:
                raise ValueError(
                    "Pressure pattern references missing signals: "
                    + ", ".join(missing_signals)
                )

    @property
    def fragment_ids(self) -> tuple[str, ...]:
        """Return intent fragment ids."""

        return tuple(fragment.fragment_id for fragment in self.fragments)

    @property
    def signal_ids(self) -> tuple[str, ...]:
        """Return manipulation signal ids."""

        return tuple(signal.signal_id for signal in self.signals)

    @property
    def pattern_ids(self) -> tuple[str, ...]:
        """Return pressure pattern ids."""

        return tuple(pattern.pattern_id for pattern in self.patterns)

    @property
    def risky_fragment_ids(self) -> tuple[str, ...]:
        """Return fragments carrying manipulation risk tags."""

        return tuple(
            fragment.fragment_id for fragment in self.fragments if fragment.risky
        )

    @property
    def blocking_signal_ids(self) -> tuple[str, ...]:
        """Return signals that block progress."""

        return tuple(signal.signal_id for signal in self.signals if signal.blocking)

    @property
    def review_signal_ids(self) -> tuple[str, ...]:
        """Return signals requiring human review."""

        return tuple(signal.signal_id for signal in self.signals if signal.needs_review)

    @property
    def blocking_pattern_ids(self) -> tuple[str, ...]:
        """Return patterns that block progress."""

        return tuple(
            pattern.pattern_id for pattern in self.patterns if pattern.blocking
        )

    @property
    def review_pattern_ids(self) -> tuple[str, ...]:
        """Return patterns requiring human review."""

        return tuple(
            pattern.pattern_id for pattern in self.patterns if pattern.needs_review
        )

    @property
    def evidence_ids(self) -> tuple[str, ...]:
        """Return all evidence ids bound to this report."""

        evidence: list[str] = list(self.decision.evidence_ids)
        for fragment in self.fragments:
            evidence.extend(fragment.evidence_ids)
        for signal in self.signals:
            evidence.extend(signal.evidence_ids)
        for pattern in self.patterns:
            evidence.extend(pattern.evidence_ids)
        return _dedupe_text_tuple(evidence, label="evidence_id")

    @property
    def assembled_intent_tags(self) -> tuple[str, ...]:
        """Return assembled normalized intent tags across fragments."""

        tags: list[str] = []
        for fragment in self.fragments:
            tags.extend(fragment.normalized_intent_tags)
        return _dedupe_text_tuple(tags, label="normalized_intent_tag")

    @property
    def risk_tag_values(self) -> tuple[str, ...]:
        """Return assembled risk tag values across fragments."""

        tags: list[str] = []
        for fragment in self.fragments:
            tags.extend(fragment.risk_tag_values)
        return _dedupe_text_tuple(tags, label="risk_tag")

    @property
    def blocks_claim(self) -> bool:
        """Return whether manipulation pressure blocks stronger claims."""

        return (
            self.decision.blocked
            or bool(self.blocking_signal_ids)
            or bool(self.blocking_pattern_ids)
        )

    @property
    def ready_for_review(self) -> bool:
        """Return whether manipulation pressure requires human review."""

        return (
            self.decision.ready_for_review
            or bool(self.review_signal_ids)
            or bool(self.review_pattern_ids)
        )

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic manipulation-pressure-report payload."""

        return {
            "assembled_intent_tags": list(self.assembled_intent_tags),
            "blocking_pattern_ids": list(self.blocking_pattern_ids),
            "blocking_signal_ids": list(self.blocking_signal_ids),
            "decision_fingerprint": self.decision.fingerprint(),
            "evidence_ids": list(self.evidence_ids),
            "fragment_fingerprints": [
                fragment.fingerprint() for fragment in self.fragments
            ],
            "fragment_ids": list(self.fragment_ids),
            "notes": list(self.notes),
            "pattern_fingerprints": [
                pattern.fingerprint() for pattern in self.patterns
            ],
            "pattern_ids": list(self.pattern_ids),
            "ready_for_review": self.ready_for_review,
            "report_id": self.report_id,
            "review_pattern_ids": list(self.review_pattern_ids),
            "review_signal_ids": list(self.review_signal_ids),
            "risk_tag_values": list(self.risk_tag_values),
            "risky_fragment_ids": list(self.risky_fragment_ids),
            "schema_version": self.schema_version,
            "signal_fingerprints": [signal.fingerprint() for signal in self.signals],
            "signal_ids": list(self.signal_ids),
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this report."""

        return _stable_sha256(self.canonical_payload())


def evaluate_manipulation_pressure(
    *,
    report_id: str,
    fragments: Iterable[CrossSessionIntentFragment],
    authority_refs: Iterable[str],
    notes: Iterable[str] = (),
) -> ManipulationPressureReport:
    """Evaluate manipulation pressure from cross-session intent fragments."""

    fragment_tuple = tuple(fragments)
    if not fragment_tuple:
        raise ValueError("Manipulation pressure evaluation requires fragments.")

    signals = _signals_from_fragments(fragment_tuple)
    patterns = _patterns_from_fragments_and_signals(fragment_tuple, signals)
    evidence_ids = _collect_evidence(fragment_tuple, signals, patterns)
    reason_ids: list[str] = []
    authority_tuple = _normalize_unique_text_tuple(
        authority_refs, label="authority_ref"
    )

    if any(pattern.blocks_progress for pattern in patterns) or any(
        signal.blocks_progress for signal in signals
    ):
        status = ManipulationDecisionStatus.BLOCKED
        reason_ids.append("blocking-manipulation-pressure")
    elif any(pattern.requires_human_review for pattern in patterns) or any(
        signal.requires_human_review for signal in signals
    ):
        status = ManipulationDecisionStatus.READY_FOR_HUMAN_REVIEW
        reason_ids.append("human-review-required")
    elif any(fragment.risky for fragment in fragment_tuple):
        status = ManipulationDecisionStatus.WATCH
        reason_ids.append("risk-watch")
    else:
        status = ManipulationDecisionStatus.CLEAR
        reason_ids.append("no-manipulation-pressure-detected")

    decision_authority_refs = (
        authority_tuple
        if status
        in {
            ManipulationDecisionStatus.READY_FOR_HUMAN_REVIEW,
            ManipulationDecisionStatus.BLOCKED,
        }
        else ()
    )
    decision = ManipulationDecision(
        decision_id=f"{report_id}-decision",
        status=status,
        reason_ids=tuple(reason_ids),
        required_authority_refs=decision_authority_refs,
        evidence_ids=evidence_ids,
    )

    return ManipulationPressureReport(
        report_id=report_id,
        fragments=fragment_tuple,
        signals=signals,
        patterns=patterns,
        decision=decision,
        notes=tuple(notes),
    )


def _signals_from_fragments(
    fragments: tuple[CrossSessionIntentFragment, ...],
) -> tuple[ManipulationSignal, ...]:
    signals: list[ManipulationSignal] = []
    for risk, signal_kind in (
        (
            IntentFragmentRisk.AUTHORITY_LAUNDERING,
            ManipulationSignalKind.AUTHORITY_LAUNDERING,
        ),
        (
            IntentFragmentRisk.CLAIM_INFLATION,
            ManipulationSignalKind.CLAIM_INFLATION,
        ),
        (
            IntentFragmentRisk.EVIDENCE_SKIP,
            ManipulationSignalKind.EVIDENCE_SKIP_PRESSURE,
        ),
        (
            IntentFragmentRisk.SELF_APPROVAL,
            ManipulationSignalKind.SELF_APPROVAL_PRESSURE,
        ),
        (
            IntentFragmentRisk.BODY_ESCALATION,
            ManipulationSignalKind.BODY_ESCALATION_PRESSURE,
        ),
        (
            IntentFragmentRisk.RUNTIME_ESCALATION,
            ManipulationSignalKind.RUNTIME_ESCALATION_PRESSURE,
        ),
    ):
        matching = tuple(fragment for fragment in fragments if fragment.carries(risk))
        if not matching:
            continue
        severity = _severity_for_risk(risk)
        signals.append(
            ManipulationSignal(
                signal_id=f"signal-{risk.value}",
                kind=signal_kind,
                severity=severity,
                summary=f"Detected {risk.value} manipulation pressure.",
                evidence_ids=_collect_fragment_evidence(matching),
                fragment_ids=tuple(fragment.fragment_id for fragment in matching),
                requires_human_review=severity is ManipulationSeverity.REVIEW_REQUIRED,
                blocks_progress=severity is ManipulationSeverity.BLOCKING,
            )
        )

    fragmented = tuple(
        fragment
        for fragment in fragments
        if fragment.carries(IntentFragmentRisk.FRAGMENTED_INTENT)
    )
    if fragmented:
        signals.append(
            ManipulationSignal(
                signal_id="signal-fragmented-intent-assembly",
                kind=ManipulationSignalKind.FRAGMENTED_INTENT_ASSEMBLY,
                severity=ManipulationSeverity.REVIEW_REQUIRED,
                summary="Detected fragmented intent requiring assembly for review.",
                evidence_ids=_collect_fragment_evidence(fragmented),
                fragment_ids=tuple(fragment.fragment_id for fragment in fragmented),
                requires_human_review=True,
            )
        )
    return tuple(sorted(signals, key=lambda signal: signal.signal_id))


def _patterns_from_fragments_and_signals(
    fragments: tuple[CrossSessionIntentFragment, ...],
    signals: tuple[ManipulationSignal, ...],
) -> tuple[PressurePattern, ...]:
    if not signals:
        return ()

    patterns: list[PressurePattern] = []
    sessions = {fragment.session_id for fragment in fragments}
    severity = (
        ManipulationSeverity.BLOCKING
        if any(signal.blocks_progress for signal in signals)
        else ManipulationSeverity.REVIEW_REQUIRED
    )
    blocks_progress = severity is ManipulationSeverity.BLOCKING

    if len(fragments) > 1 and len(sessions) > 1:
        patterns.append(
            PressurePattern(
                pattern_id="pattern-cross-session-pressure",
                kind=PressurePatternKind.CROSS_SESSION,
                severity=severity,
                summary=(
                    "Manipulation pressure appears across multiple sessions and "
                    "must be reviewed as assembled intent."
                ),
                fragment_ids=tuple(fragment.fragment_id for fragment in fragments),
                signal_ids=tuple(signal.signal_id for signal in signals),
                evidence_ids=_collect_fragment_evidence(fragments),
                requires_human_review=not blocks_progress,
                blocks_progress=blocks_progress,
            )
        )

    if any(
        signal.kind is ManipulationSignalKind.AUTHORITY_LAUNDERING for signal in signals
    ):
        patterns.append(
            PressurePattern(
                pattern_id="pattern-authority-chain",
                kind=PressurePatternKind.AUTHORITY_CHAIN,
                severity=ManipulationSeverity.BLOCKING,
                summary="Authority laundering pressure blocks progression.",
                fragment_ids=tuple(fragment.fragment_id for fragment in fragments),
                signal_ids=tuple(signal.signal_id for signal in signals),
                evidence_ids=_collect_fragment_evidence(fragments),
                blocks_progress=True,
            )
        )

    if any(signal.kind is ManipulationSignalKind.CLAIM_INFLATION for signal in signals):
        patterns.append(
            PressurePattern(
                pattern_id="pattern-claim-escalation-chain",
                kind=PressurePatternKind.CLAIM_ESCALATION_CHAIN,
                severity=ManipulationSeverity.BLOCKING,
                summary="Claim inflation pressure blocks stronger maturity claims.",
                fragment_ids=tuple(fragment.fragment_id for fragment in fragments),
                signal_ids=tuple(signal.signal_id for signal in signals),
                evidence_ids=_collect_fragment_evidence(fragments),
                blocks_progress=True,
            )
        )

    if any(
        signal.kind is ManipulationSignalKind.EVIDENCE_SKIP_PRESSURE
        for signal in signals
    ):
        patterns.append(
            PressurePattern(
                pattern_id="pattern-evidence-bypass-chain",
                kind=PressurePatternKind.EVIDENCE_BYPASS_CHAIN,
                severity=ManipulationSeverity.BLOCKING,
                summary="Evidence bypass pressure blocks progression.",
                fragment_ids=tuple(fragment.fragment_id for fragment in fragments),
                signal_ids=tuple(signal.signal_id for signal in signals),
                evidence_ids=_collect_fragment_evidence(fragments),
                blocks_progress=True,
            )
        )

    return tuple(sorted(patterns, key=lambda pattern: pattern.pattern_id))


def _severity_for_risk(risk: IntentFragmentRisk) -> ManipulationSeverity:
    if risk in {
        IntentFragmentRisk.AUTHORITY_LAUNDERING,
        IntentFragmentRisk.CLAIM_INFLATION,
        IntentFragmentRisk.EVIDENCE_SKIP,
        IntentFragmentRisk.SELF_APPROVAL,
    }:
        return ManipulationSeverity.BLOCKING
    if risk in {
        IntentFragmentRisk.BODY_ESCALATION,
        IntentFragmentRisk.RUNTIME_ESCALATION,
    }:
        return ManipulationSeverity.REVIEW_REQUIRED
    return ManipulationSeverity.WATCH


def _collect_fragment_evidence(
    fragments: Iterable[CrossSessionIntentFragment],
) -> tuple[str, ...]:
    evidence: list[str] = []
    for fragment in fragments:
        evidence.extend(fragment.evidence_ids)
    return _dedupe_text_tuple(evidence, label="evidence_id")


def _collect_evidence(
    fragments: Iterable[CrossSessionIntentFragment],
    signals: Iterable[ManipulationSignal],
    patterns: Iterable[PressurePattern],
) -> tuple[str, ...]:
    evidence: list[str] = []
    for fragment in fragments:
        evidence.extend(fragment.evidence_ids)
    for signal in signals:
        evidence.extend(signal.evidence_ids)
    for pattern in patterns:
        evidence.extend(pattern.evidence_ids)
    return _dedupe_text_tuple(evidence, label="evidence_id")


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


def _ensure_unique(values: Iterable[str], *, label: str) -> None:
    seen: set[str] = set()
    for value in values:
        if value in seen:
            raise ValueError(f"Duplicate {label}: {value}")
        seen.add(value)


def _stable_sha256(payload: Mapping[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
