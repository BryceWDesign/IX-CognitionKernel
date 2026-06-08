"""Wave 6 independent challenge suite.

Wave 6 needs more than an internal evidence package. It needs challenge cases
that can embarrass the system: novel targets, hidden constraints, negative
controls, transfer requirements, measurable success criteria, and explicit block
paths. This module models those challenge cases without executing them so the
suite remains deterministic, reviewable, and independent-evaluator friendly.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, TypeVar

T = TypeVar("T")
E = TypeVar("E", bound=StrEnum)

WAVE_SIX_CHALLENGE_CASE_SCHEMA_VERSION = "ix-cognition-kernel-wave6-challenge-case-v1"
WAVE_SIX_CHALLENGE_SUITE_SCHEMA_VERSION = "ix-cognition-kernel-wave6-challenge-suite-v1"


class WaveSixChallengeKind(StrEnum):
    """Kinds of independent challenges required for Wave 6."""

    REALITY_CORRECTION = "reality-correction"
    FUTURE_REASONING_CHANGE = "future-reasoning-change"
    CROSS_DOMAIN_TRANSFER = "cross-domain-transfer"
    NOVELTY_GENERALIZATION = "novelty-generalization"
    NEGATIVE_CONTROL = "negative-control"
    FALSIFICATION = "falsification"
    HUMAN_AUTHORITY_BOUNDARY = "human-authority-boundary"


class WaveSixChallengeOutcome(StrEnum):
    """Observed or planned outcome state for a challenge case."""

    NOT_RUN = "not-run"
    PASSED = "passed"
    FAILED = "failed"
    INCONCLUSIVE = "inconclusive"
    BLOCKED_BY_SAFETY_GATE = "blocked-by-safety-gate"


class WaveSixChallengeDecision(StrEnum):
    """Fail-closed challenge decision."""

    ACCEPT_FOR_REVIEW = "accept-for-review"
    NEEDS_MORE_EVIDENCE = "needs-more-evidence"
    RECORD_ONLY = "record-only"
    BLOCK_CLAIM = "block-claim"


WAVE_SIX_REQUIRED_CHALLENGE_KINDS: tuple[WaveSixChallengeKind, ...] = (
    WaveSixChallengeKind.REALITY_CORRECTION,
    WaveSixChallengeKind.FUTURE_REASONING_CHANGE,
    WaveSixChallengeKind.CROSS_DOMAIN_TRANSFER,
    WaveSixChallengeKind.NOVELTY_GENERALIZATION,
    WaveSixChallengeKind.NEGATIVE_CONTROL,
    WaveSixChallengeKind.FALSIFICATION,
    WaveSixChallengeKind.HUMAN_AUTHORITY_BOUNDARY,
)


@dataclass(frozen=True, slots=True)
class WaveSixChallengeCase:
    """One independent challenge case for the Wave 6 package."""

    case_id: str
    kind: WaveSixChallengeKind
    title: str
    challenge_prompt: str
    hidden_constraint_summary: str
    measurable_success_criteria: tuple[str, ...]
    expected_failure_modes: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    outcome: WaveSixChallengeOutcome = WaveSixChallengeOutcome.NOT_RUN
    decision: WaveSixChallengeDecision = WaveSixChallengeDecision.NEEDS_MORE_EVIDENCE
    requires_human_review: bool = True
    allows_autonomous_execution: bool = False
    claims_agi: bool = False
    schema_version: str = WAVE_SIX_CHALLENGE_CASE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate challenge case boundaries and evidence fields."""

        if not self.requires_human_review:
            raise ValueError("Wave 6 challenge cases must require human review.")
        if self.allows_autonomous_execution:
            raise ValueError(
                "Wave 6 challenge cases must not allow autonomous execution."
            )
        if self.claims_agi:
            raise ValueError("Wave 6 challenge cases must not claim AGI.")
        object.__setattr__(
            self,
            "case_id",
            _require_non_empty(self.case_id, "case_id"),
        )
        object.__setattr__(self, "title", _require_non_empty(self.title, "title"))
        object.__setattr__(
            self,
            "challenge_prompt",
            _require_non_empty(self.challenge_prompt, "challenge_prompt"),
        )
        object.__setattr__(
            self,
            "hidden_constraint_summary",
            _require_non_empty(
                self.hidden_constraint_summary,
                "hidden_constraint_summary",
            ),
        )
        object.__setattr__(
            self,
            "measurable_success_criteria",
            _normalize_unique_text_tuple(
                self.measurable_success_criteria,
                label="measurable_success_criterion",
            ),
        )
        object.__setattr__(
            self,
            "expected_failure_modes",
            _normalize_unique_text_tuple(
                self.expected_failure_modes,
                label="expected_failure_mode",
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
        if not self.measurable_success_criteria:
            raise ValueError("Wave 6 challenge cases require success criteria.")
        if not self.expected_failure_modes:
            raise ValueError("Wave 6 challenge cases require failure modes.")
        if not self.evidence_ids:
            raise ValueError("Wave 6 challenge cases require evidence ids.")
        if (
            self.outcome is WaveSixChallengeOutcome.FAILED
            and self.decision is not WaveSixChallengeDecision.BLOCK_CLAIM
        ):
            raise ValueError("Failed Wave 6 challenge cases must block the claim.")
        if (
            self.outcome is WaveSixChallengeOutcome.BLOCKED_BY_SAFETY_GATE
            and self.decision is not WaveSixChallengeDecision.BLOCK_CLAIM
        ):
            raise ValueError("Safety-gated challenge cases must block the claim.")
        if (
            self.outcome is WaveSixChallengeOutcome.PASSED
            and self.decision is not WaveSixChallengeDecision.ACCEPT_FOR_REVIEW
        ):
            raise ValueError("Passed challenge cases must be accepted for review.")

    @property
    def passed(self) -> bool:
        """Return whether this challenge case passed and can support review."""

        return (
            self.outcome is WaveSixChallengeOutcome.PASSED
            and self.decision is WaveSixChallengeDecision.ACCEPT_FOR_REVIEW
        )

    @property
    def blocks_claim(self) -> bool:
        """Return whether this challenge case blocks Wave 6 interpretation."""

        return (
            self.decision is WaveSixChallengeDecision.BLOCK_CLAIM
            or self.outcome
            in {
                WaveSixChallengeOutcome.FAILED,
                WaveSixChallengeOutcome.BLOCKED_BY_SAFETY_GATE,
            }
        )

    @property
    def needs_more_evidence(self) -> bool:
        """Return whether the challenge case still needs evidence."""

        return self.decision is WaveSixChallengeDecision.NEEDS_MORE_EVIDENCE

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic payload for hashing and review."""

        return {
            "allows_autonomous_execution": self.allows_autonomous_execution,
            "case_id": self.case_id,
            "challenge_prompt": self.challenge_prompt,
            "claims_agi": self.claims_agi,
            "decision": self.decision.value,
            "evidence_ids": list(self.evidence_ids),
            "expected_failure_modes": list(self.expected_failure_modes),
            "hidden_constraint_summary": self.hidden_constraint_summary,
            "kind": self.kind.value,
            "measurable_success_criteria": list(self.measurable_success_criteria),
            "outcome": self.outcome.value,
            "requires_human_review": self.requires_human_review,
            "schema_version": self.schema_version,
            "title": self.title,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this challenge case."""

        return _stable_sha256(self.canonical_payload())


@dataclass(frozen=True, slots=True)
class WaveSixChallengeSuite:
    """Independent challenge suite for Wave 6 external review."""

    suite_id: str
    cases: tuple[WaveSixChallengeCase, ...]
    required_kinds: tuple[WaveSixChallengeKind, ...] = WAVE_SIX_REQUIRED_CHALLENGE_KINDS
    require_all_kinds_passed: bool = True
    claims_agi: bool = False
    notes: tuple[str, ...] = ()
    schema_version: str = WAVE_SIX_CHALLENGE_SUITE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate suite identity, uniqueness, and claim boundary."""

        if self.claims_agi:
            raise ValueError("Wave 6 challenge suites must not claim AGI.")
        object.__setattr__(
            self,
            "suite_id",
            _require_non_empty(self.suite_id, "suite_id"),
        )
        if not self.cases:
            raise ValueError("Wave 6 challenge suites require at least one case.")
        sorted_cases = tuple(sorted(self.cases, key=lambda case: case.case_id))
        _unique_ids((case.case_id for case in sorted_cases), label="case_id")
        object.__setattr__(self, "cases", sorted_cases)
        object.__setattr__(
            self,
            "required_kinds",
            _normalize_unique_enum_tuple(self.required_kinds, label="required kind"),
        )
        object.__setattr__(
            self,
            "notes",
            _normalize_unique_text_tuple(self.notes, label="suite note"),
        )
        object.__setattr__(
            self,
            "schema_version",
            _require_non_empty(self.schema_version, "schema_version"),
        )

    @property
    def case_ids(self) -> tuple[str, ...]:
        """Return challenge case ids in deterministic order."""

        return tuple(case.case_id for case in self.cases)

    @property
    def present_kinds(self) -> tuple[WaveSixChallengeKind, ...]:
        """Return required challenge kinds represented in the suite."""

        present = {case.kind for case in self.cases}
        return tuple(kind for kind in self.required_kinds if kind in present)

    @property
    def missing_kinds(self) -> tuple[WaveSixChallengeKind, ...]:
        """Return required challenge kinds missing from the suite."""

        present = {case.kind for case in self.cases}
        return tuple(kind for kind in self.required_kinds if kind not in present)

    @property
    def passed_case_ids(self) -> tuple[str, ...]:
        """Return case ids that passed and were accepted for review."""

        return tuple(case.case_id for case in self.cases if case.passed)

    @property
    def blocking_case_ids(self) -> tuple[str, ...]:
        """Return case ids that block Wave 6 interpretation."""

        return tuple(case.case_id for case in self.cases if case.blocks_claim)

    @property
    def needs_more_evidence_case_ids(self) -> tuple[str, ...]:
        """Return case ids that still need evidence."""

        return tuple(case.case_id for case in self.cases if case.needs_more_evidence)

    @property
    def passed_required_kinds(self) -> tuple[WaveSixChallengeKind, ...]:
        """Return required kinds with at least one passed case."""

        passed = {case.kind for case in self.cases if case.passed}
        return tuple(kind for kind in self.required_kinds if kind in passed)

    @property
    def missing_passed_required_kinds(self) -> tuple[WaveSixChallengeKind, ...]:
        """Return required kinds without a passed case."""

        passed = set(self.passed_required_kinds)
        return tuple(kind for kind in self.required_kinds if kind not in passed)

    @property
    def ready_for_external_challenge_review(self) -> bool:
        """Return whether the suite can support external challenge review."""

        if self.missing_kinds or self.blocking_case_ids:
            return False
        if self.needs_more_evidence_case_ids:
            return False
        return not (
            self.require_all_kinds_passed and self.missing_passed_required_kinds
        )

    def case_for_kind(
        self,
        kind: WaveSixChallengeKind,
    ) -> WaveSixChallengeCase | None:
        """Return the first challenge case for a kind, if present."""

        for case in self.cases:
            if case.kind is kind:
                return case
        return None

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic suite payload for hashing and review."""

        return {
            "blocking_case_ids": list(self.blocking_case_ids),
            "case_ids": list(self.case_ids),
            "cases": [case.canonical_payload() for case in self.cases],
            "claims_agi": self.claims_agi,
            "missing_kinds": [kind.value for kind in self.missing_kinds],
            "missing_passed_required_kinds": [
                kind.value for kind in self.missing_passed_required_kinds
            ],
            "needs_more_evidence_case_ids": list(self.needs_more_evidence_case_ids),
            "notes": list(self.notes),
            "passed_case_ids": list(self.passed_case_ids),
            "present_kinds": [kind.value for kind in self.present_kinds],
            "ready_for_external_challenge_review": (
                self.ready_for_external_challenge_review
            ),
            "require_all_kinds_passed": self.require_all_kinds_passed,
            "required_kinds": [kind.value for kind in self.required_kinds],
            "schema_version": self.schema_version,
            "suite_id": self.suite_id,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this challenge suite."""

        return _stable_sha256(self.canonical_payload())


def build_wave_six_challenge_suite(
    *,
    suite_id: str,
    cases: Iterable[WaveSixChallengeCase],
    require_all_kinds_passed: bool = True,
    notes: Iterable[str] = (),
) -> WaveSixChallengeSuite:
    """Build a deterministic Wave 6 challenge suite."""

    return WaveSixChallengeSuite(
        suite_id=suite_id,
        cases=tuple(cases),
        require_all_kinds_passed=require_all_kinds_passed,
        notes=tuple(notes),
    )


def required_wave_six_challenge_kinds() -> tuple[WaveSixChallengeKind, ...]:
    """Return required challenge kinds for Wave 6 external pressure."""

    return WAVE_SIX_REQUIRED_CHALLENGE_KINDS


def _require_non_empty(value: str, label: str) -> str:
    """Return stripped text or raise when empty."""

    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{label} must not be empty.")
    return normalized


def _normalize_unique_text_tuple(
    values: Iterable[str], *, label: str
) -> tuple[str, ...]:
    """Normalize text values while rejecting blanks and duplicates."""

    normalized: list[str] = []
    seen: set[str] = set()
    for value in values:
        stripped = _require_non_empty(value, label)
        if stripped in seen:
            raise ValueError(f"Duplicate {label} detected: {stripped}")
        normalized.append(stripped)
        seen.add(stripped)
    return tuple(normalized)


def _normalize_unique_enum_tuple(values: Iterable[E], *, label: str) -> tuple[E, ...]:
    """Return enum values as a tuple while rejecting duplicates."""

    normalized: list[E] = []
    seen: set[E] = set()
    for value in values:
        if value in seen:
            raise ValueError(f"Duplicate {label} detected: {value.value}")
        normalized.append(value)
        seen.add(value)
    return tuple(normalized)


def _unique_ids(values: Iterable[T], *, label: str) -> set[T]:
    """Return unique values while rejecting duplicates."""

    seen: set[T] = set()
    for value in values:
        if value in seen:
            raise ValueError(f"Duplicate {label} detected: {value}")
        seen.add(value)
    return seen


def _stable_sha256(payload: Mapping[str, Any]) -> str:
    """Return deterministic SHA-256 over a canonical JSON payload."""

    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
