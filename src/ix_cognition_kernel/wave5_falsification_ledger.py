"""Wave 5 falsification and kill-criteria ledger records.

Wave 5 must be falsifiable before it can responsibly bridge into Wave 6 design
work. This module records challenges, kill criteria, observed results, and
reviewer-visible blocking verdicts. A falsification ledger can make evidence
reviewable only when failed challenges are retained, kill criteria are explicit,
and blocking results prevent promotion rather than being hidden as limitations.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, TypeVar

from ix_cognition_kernel.wave5_contracts import (
    WAVE_FIVE_REQUIRED_CLAIM_BOUNDARIES,
    WaveFiveArtifactDecision,
    WaveFiveArtifactKind,
    WaveFiveArtifactRef,
    WaveFiveAuthorityState,
    WaveFiveCapabilityArea,
    WaveFiveClaimBoundary,
    WaveFiveSourceSystem,
    WaveFiveValidationStatus,
)

T = TypeVar("T")
E = TypeVar("E", bound=StrEnum)

WAVE_FIVE_FALSIFICATION_CHALLENGE_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave5-falsification-challenge-v1"
)
WAVE_FIVE_KILL_CRITERION_SCHEMA_VERSION = "ix-cognition-kernel-wave5-kill-criterion-v1"
WAVE_FIVE_FALSIFICATION_RESULT_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave5-falsification-result-v1"
)
WAVE_FIVE_FALSIFICATION_LEDGER_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave5-falsification-ledger-v1"
)


class WaveFiveFalsificationTargetKind(StrEnum):
    """Evidence targets that must be open to falsification before Wave 6."""

    EVIDENCE_CHAIN = "evidence-chain"
    CROSS_DOMAIN_TRANSFER = "cross-domain-transfer"
    LONG_HORIZON_STATE = "long-horizon-state"
    SAFE_REFUSAL = "safe-refusal"
    MEMORY_INTEGRITY = "memory-integrity"
    BENCHMARK_GAMING = "benchmark-gaming"
    HUMAN_AUTHORITY = "human-authority"
    REPEATABILITY = "repeatability"
    WORLDTWIN_SCENARIO = "worldtwin-scenario"
    BLACKFOX_HANDOFF = "blackfox-handoff"
    WAVE_SIX_READINESS = "wave-six-readiness"


class WaveFiveFalsificationChallengeStatus(StrEnum):
    """Status of one falsification challenge."""

    READY = "ready"
    READY_WITH_LIMITS = "ready-with-limits"
    NEEDS_MORE_EVIDENCE = "needs-more-evidence"
    BLOCKED = "blocked"


class WaveFiveKillCriterionKind(StrEnum):
    """Kill criteria that must block readiness when triggered."""

    EVIDENCE_CHAIN_BREAK = "evidence-chain-break"
    TRANSFER_FAILURE = "transfer-failure"
    LONG_HORIZON_COHERENCE_FAILURE = "long-horizon-coherence-failure"
    UNSAFE_COMPLIANCE = "unsafe-compliance"
    MEMORY_POISONING_OR_STALENESS = "memory-poisoning-or-staleness"
    BENCHMARK_CONTAMINATION = "benchmark-contamination"
    AUTHORITY_BYPASS = "authority-bypass"
    REPRODUCTION_FAILURE = "reproduction-failure"
    SCENARIO_FALSIFIED = "scenario-falsified"
    GOVERNANCE_HANDOFF_GAP = "governance-handoff-gap"
    WAVE_SIX_OVERCLAIM = "wave-six-overclaim"


class WaveFiveKillCriterionDisposition(StrEnum):
    """Disposition of one kill criterion."""

    NOT_TRIGGERED = "not-triggered"
    TRIGGERED_AND_BLOCKING = "triggered-and-blocking"
    TRIGGERED_BUT_RESOLVED = "triggered-but-resolved"
    NEEDS_MORE_EVIDENCE = "needs-more-evidence"
    DISPUTED = "disputed"


class WaveFiveFalsificationVerdict(StrEnum):
    """Observed verdict for one falsification result."""

    SURVIVED_CHALLENGE = "survived-challenge"
    SURVIVED_WITH_LIMITS = "survived-with-limits"
    FALSIFIED = "falsified"
    DISPUTED = "disputed"
    NEEDS_MORE_EVIDENCE = "needs-more-evidence"
    BLOCKED_BY_KILL_CRITERION = "blocked-by-kill-criterion"


class WaveFiveFalsificationLedgerState(StrEnum):
    """Review state of the Wave 5 falsification ledger."""

    INTERNAL_LEDGER_READY = "internal-ledger-ready"
    READY_FOR_EXTERNAL_FALSIFICATION_REVIEW = "ready-for-external-falsification-review"
    UNDER_EXTERNAL_FALSIFICATION_REVIEW = "under-external-falsification-review"
    EXTERNALLY_REVIEWED_WITH_BOUNDARIES = "externally-reviewed-with-boundaries"
    BLOCKED_BY_FALSIFICATION = "blocked-by-falsification"


SAFE_FALSIFICATION_VERDICTS: tuple[WaveFiveFalsificationVerdict, ...] = (
    WaveFiveFalsificationVerdict.SURVIVED_CHALLENGE,
    WaveFiveFalsificationVerdict.SURVIVED_WITH_LIMITS,
)

BLOCKING_FALSIFICATION_VERDICTS: tuple[WaveFiveFalsificationVerdict, ...] = (
    WaveFiveFalsificationVerdict.FALSIFIED,
    WaveFiveFalsificationVerdict.DISPUTED,
    WaveFiveFalsificationVerdict.NEEDS_MORE_EVIDENCE,
    WaveFiveFalsificationVerdict.BLOCKED_BY_KILL_CRITERION,
)

REQUIRED_FALSIFICATION_TARGETS: tuple[WaveFiveFalsificationTargetKind, ...] = (
    WaveFiveFalsificationTargetKind.EVIDENCE_CHAIN,
    WaveFiveFalsificationTargetKind.CROSS_DOMAIN_TRANSFER,
    WaveFiveFalsificationTargetKind.LONG_HORIZON_STATE,
    WaveFiveFalsificationTargetKind.SAFE_REFUSAL,
    WaveFiveFalsificationTargetKind.MEMORY_INTEGRITY,
    WaveFiveFalsificationTargetKind.BENCHMARK_GAMING,
    WaveFiveFalsificationTargetKind.HUMAN_AUTHORITY,
    WaveFiveFalsificationTargetKind.REPEATABILITY,
    WaveFiveFalsificationTargetKind.WORLDTWIN_SCENARIO,
    WaveFiveFalsificationTargetKind.BLACKFOX_HANDOFF,
    WaveFiveFalsificationTargetKind.WAVE_SIX_READINESS,
)

REQUIRED_KILL_CRITERIA: tuple[WaveFiveKillCriterionKind, ...] = (
    WaveFiveKillCriterionKind.EVIDENCE_CHAIN_BREAK,
    WaveFiveKillCriterionKind.TRANSFER_FAILURE,
    WaveFiveKillCriterionKind.LONG_HORIZON_COHERENCE_FAILURE,
    WaveFiveKillCriterionKind.UNSAFE_COMPLIANCE,
    WaveFiveKillCriterionKind.MEMORY_POISONING_OR_STALENESS,
    WaveFiveKillCriterionKind.BENCHMARK_CONTAMINATION,
    WaveFiveKillCriterionKind.AUTHORITY_BYPASS,
    WaveFiveKillCriterionKind.REPRODUCTION_FAILURE,
    WaveFiveKillCriterionKind.SCENARIO_FALSIFIED,
    WaveFiveKillCriterionKind.GOVERNANCE_HANDOFF_GAP,
    WaveFiveKillCriterionKind.WAVE_SIX_OVERCLAIM,
)

EXTERNAL_FALSIFICATION_REVIEW_SOURCE_SYSTEMS: tuple[WaveFiveSourceSystem, ...] = (
    WaveFiveSourceSystem.EXTERNAL_REVIEW,
    WaveFiveSourceSystem.INDEPENDENT_REVIEWER,
    WaveFiveSourceSystem.ADVERSARIAL_TESTER,
)


@dataclass(frozen=True, slots=True)
class WaveFiveFalsificationChallenge:
    """One falsification challenge reviewers can run against Wave 5 evidence."""

    challenge_id: str
    target_kind: WaveFiveFalsificationTargetKind
    status: WaveFiveFalsificationChallengeStatus
    challenge_question: str
    expected_failure_signal: str
    artifact_ids: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    reviewer_visible: bool = True
    schema_version: str = WAVE_FIVE_FALSIFICATION_CHALLENGE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate challenge evidence and reviewer visibility."""

        object.__setattr__(
            self, "challenge_id", _text(self.challenge_id, "challenge_id")
        )
        object.__setattr__(
            self,
            "challenge_question",
            _text(self.challenge_question, "challenge_question"),
        )
        object.__setattr__(
            self,
            "expected_failure_signal",
            _text(self.expected_failure_signal, "expected_failure_signal"),
        )
        object.__setattr__(
            self, "artifact_ids", _unique_text(self.artifact_ids, label="artifact_id")
        )
        object.__setattr__(
            self, "evidence_ids", _unique_text(self.evidence_ids, label="evidence_id")
        )
        if not self.artifact_ids:
            raise ValueError("Falsification challenges require artifact ids.")
        if not self.evidence_ids:
            raise ValueError("Falsification challenges require evidence ids.")
        if not self.reviewer_visible:
            raise ValueError("Falsification challenges must be reviewer visible.")
        object.__setattr__(
            self, "schema_version", _text(self.schema_version, "schema_version")
        )

    @property
    def challenge_key(self) -> str:
        """Return deterministic challenge key."""

        return self.challenge_id

    @property
    def ready_for_review(self) -> bool:
        """Return whether this challenge can be sent to reviewers."""

        return self.status in {
            WaveFiveFalsificationChallengeStatus.READY,
            WaveFiveFalsificationChallengeStatus.READY_WITH_LIMITS,
        }

    @property
    def blocks_ledger_readiness(self) -> bool:
        """Return whether this challenge blocks ledger readiness."""

        return not self.ready_for_review

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic export payload."""

        return {
            "artifact_ids": list(self.artifact_ids),
            "challenge_id": self.challenge_id,
            "challenge_question": self.challenge_question,
            "evidence_ids": list(self.evidence_ids),
            "expected_failure_signal": self.expected_failure_signal,
            "ready_for_review": self.ready_for_review,
            "reviewer_visible": self.reviewer_visible,
            "schema_version": self.schema_version,
            "status": self.status.value,
            "target_kind": self.target_kind.value,
        }


@dataclass(frozen=True, slots=True)
class WaveFiveKillCriterion:
    """One explicit condition that must block Wave 6 readiness if triggered."""

    criterion_id: str
    criterion_kind: WaveFiveKillCriterionKind
    disposition: WaveFiveKillCriterionDisposition
    description: str
    blocking_response: str
    evidence_ids: tuple[str, ...]
    resolved_by_evidence_ids: tuple[str, ...] = ()
    reviewer_visible: bool = True
    schema_version: str = WAVE_FIVE_KILL_CRITERION_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate kill-criterion visibility and evidence handling."""

        object.__setattr__(
            self, "criterion_id", _text(self.criterion_id, "criterion_id")
        )
        object.__setattr__(self, "description", _text(self.description, "description"))
        object.__setattr__(
            self,
            "blocking_response",
            _text(self.blocking_response, "blocking_response"),
        )
        object.__setattr__(
            self, "evidence_ids", _unique_text(self.evidence_ids, label="evidence_id")
        )
        object.__setattr__(
            self,
            "resolved_by_evidence_ids",
            _unique_text(
                self.resolved_by_evidence_ids,
                label="resolved evidence_id",
            ),
        )
        if not self.evidence_ids:
            raise ValueError("Kill criteria require evidence ids.")
        if not self.reviewer_visible:
            raise ValueError("Kill criteria must be reviewer visible.")
        if (
            self.disposition is WaveFiveKillCriterionDisposition.TRIGGERED_BUT_RESOLVED
            and not self.resolved_by_evidence_ids
        ):
            raise ValueError("Resolved kill criteria require resolution evidence.")
        object.__setattr__(
            self, "schema_version", _text(self.schema_version, "schema_version")
        )

    @property
    def criterion_key(self) -> str:
        """Return deterministic criterion key."""

        return self.criterion_id

    @property
    def blocks_wave_six_entry(self) -> bool:
        """Return whether this criterion blocks Wave 6 design review."""

        return self.disposition in {
            WaveFiveKillCriterionDisposition.TRIGGERED_AND_BLOCKING,
            WaveFiveKillCriterionDisposition.NEEDS_MORE_EVIDENCE,
            WaveFiveKillCriterionDisposition.DISPUTED,
        }

    @property
    def all_evidence_ids(self) -> tuple[str, ...]:
        """Return primary and resolution evidence ids."""

        return _dedupe_text((*self.evidence_ids, *self.resolved_by_evidence_ids))

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic export payload."""

        return {
            "all_evidence_ids": list(self.all_evidence_ids),
            "blocking_response": self.blocking_response,
            "criterion_id": self.criterion_id,
            "criterion_kind": self.criterion_kind.value,
            "description": self.description,
            "disposition": self.disposition.value,
            "evidence_ids": list(self.evidence_ids),
            "resolved_by_evidence_ids": list(self.resolved_by_evidence_ids),
            "reviewer_visible": self.reviewer_visible,
            "schema_version": self.schema_version,
        }


@dataclass(frozen=True, slots=True)
class WaveFiveFalsificationResult:
    """Observed result for a falsification challenge."""

    result_id: str
    challenge_id: str
    verdict: WaveFiveFalsificationVerdict
    observed_result: str
    evidence_ids: tuple[str, ...]
    triggered_criterion_ids: tuple[str, ...] = ()
    reviewer_ids: tuple[str, ...] = ()
    retained_failure_output: bool = True
    schema_version: str = WAVE_FIVE_FALSIFICATION_RESULT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate result evidence and failure-output retention."""

        object.__setattr__(self, "result_id", _text(self.result_id, "result_id"))
        object.__setattr__(
            self, "challenge_id", _text(self.challenge_id, "challenge_id")
        )
        object.__setattr__(
            self, "observed_result", _text(self.observed_result, "observed_result")
        )
        object.__setattr__(
            self, "evidence_ids", _unique_text(self.evidence_ids, label="evidence_id")
        )
        object.__setattr__(
            self,
            "triggered_criterion_ids",
            _unique_text(
                self.triggered_criterion_ids,
                label="triggered criterion_id",
            ),
        )
        object.__setattr__(
            self, "reviewer_ids", _unique_text(self.reviewer_ids, label="reviewer_id")
        )
        if not self.evidence_ids:
            raise ValueError("Falsification results require evidence ids.")
        if (
            self.verdict in BLOCKING_FALSIFICATION_VERDICTS
            and not self.retained_failure_output
        ):
            raise ValueError("Blocking falsification outputs must be retained.")
        if (
            self.verdict is WaveFiveFalsificationVerdict.BLOCKED_BY_KILL_CRITERION
            and not self.triggered_criterion_ids
        ):
            raise ValueError("Kill-criterion verdicts require criterion ids.")
        object.__setattr__(
            self, "schema_version", _text(self.schema_version, "schema_version")
        )

    @property
    def result_key(self) -> str:
        """Return deterministic result key."""

        return self.result_id

    @property
    def blocks_wave_six_entry(self) -> bool:
        """Return whether this result blocks Wave 6 design review."""

        return self.verdict in BLOCKING_FALSIFICATION_VERDICTS

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic export payload."""

        return {
            "challenge_id": self.challenge_id,
            "evidence_ids": list(self.evidence_ids),
            "observed_result": self.observed_result,
            "result_id": self.result_id,
            "retained_failure_output": self.retained_failure_output,
            "reviewer_ids": list(self.reviewer_ids),
            "schema_version": self.schema_version,
            "triggered_criterion_ids": list(self.triggered_criterion_ids),
            "verdict": self.verdict.value,
        }


@dataclass(frozen=True, slots=True)
class WaveFiveFalsificationLedger:
    """Wave 5 ledger for falsification challenges and kill criteria."""

    ledger_id: str
    title: str
    source_system: WaveFiveSourceSystem
    ledger_state: WaveFiveFalsificationLedgerState
    challenges: tuple[WaveFiveFalsificationChallenge, ...]
    kill_criteria: tuple[WaveFiveKillCriterion, ...]
    results: tuple[WaveFiveFalsificationResult, ...]
    protocol_ids: tuple[str, ...]
    reviewer_ids: tuple[str, ...] = ()
    attempted_wave_six_promotion: bool = False
    claims_agi: bool = False
    grants_execution_authority: bool = False
    claim_boundaries: tuple[WaveFiveClaimBoundary, ...] = (
        WAVE_FIVE_REQUIRED_CLAIM_BOUNDARIES
    )
    notes: tuple[str, ...] = ()
    schema_version: str = WAVE_FIVE_FALSIFICATION_LEDGER_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate falsification coverage, references, and claim boundaries."""

        object.__setattr__(self, "ledger_id", _text(self.ledger_id, "ledger_id"))
        object.__setattr__(self, "title", _text(self.title, "title"))
        if self.attempted_wave_six_promotion:
            raise ValueError("Falsification ledgers cannot promote to Wave 6.")
        if self.claims_agi:
            raise ValueError("Falsification ledgers cannot claim AGI.")
        if self.grants_execution_authority:
            raise ValueError("Falsification ledgers cannot grant execution authority.")
        challenges = tuple(sorted(self.challenges, key=lambda item: item.challenge_key))
        criteria = tuple(
            sorted(self.kill_criteria, key=lambda item: item.criterion_key)
        )
        results = tuple(sorted(self.results, key=lambda item: item.result_key))
        if not challenges:
            raise ValueError("Falsification ledgers require challenges.")
        if not criteria:
            raise ValueError("Falsification ledgers require kill criteria.")
        if not results:
            raise ValueError("Falsification ledgers require results.")
        challenge_ids = _unique_values(
            (item.challenge_id for item in challenges), label="challenge_id"
        )
        criterion_ids = _unique_values(
            (item.criterion_id for item in criteria), label="criterion_id"
        )
        _unique_values((item.result_id for item in results), label="result_id")
        self._validate_result_references(challenge_ids, criterion_ids, results)
        object.__setattr__(self, "challenges", challenges)
        object.__setattr__(self, "kill_criteria", criteria)
        object.__setattr__(self, "results", results)
        object.__setattr__(
            self, "protocol_ids", _unique_text(self.protocol_ids, label="protocol_id")
        )
        if not self.protocol_ids:
            raise ValueError("Falsification ledgers require protocol ids.")
        object.__setattr__(
            self, "reviewer_ids", _unique_text(self.reviewer_ids, label="reviewer_id")
        )
        object.__setattr__(
            self,
            "claim_boundaries",
            _unique_enum(self.claim_boundaries, label="claim boundary"),
        )
        missing = tuple(
            boundary
            for boundary in WAVE_FIVE_REQUIRED_CLAIM_BOUNDARIES
            if boundary not in self.claim_boundaries
        )
        if missing:
            raise ValueError(
                "Falsification ledgers must preserve claim boundary: "
                f"{missing[0].value}"
            )
        object.__setattr__(self, "notes", _unique_text(self.notes, label="note"))
        object.__setattr__(
            self, "schema_version", _text(self.schema_version, "schema_version")
        )
        if self.externally_reviewed_with_boundaries:
            if self.source_system not in EXTERNAL_FALSIFICATION_REVIEW_SOURCE_SYSTEMS:
                raise ValueError(
                    "Externally reviewed falsification ledgers require external source."
                )
            if not self.reviewer_ids:
                raise ValueError(
                    "Externally reviewed falsification ledgers require reviewers."
                )
            if self.blocks_falsification_readiness:
                raise ValueError(
                    "Externally reviewed falsification ledgers cannot contain blockers."
                )

    @property
    def covered_targets(self) -> tuple[WaveFiveFalsificationTargetKind, ...]:
        """Return falsification targets represented by challenges."""

        return tuple(challenge.target_kind for challenge in self.challenges)

    @property
    def missing_required_targets(self) -> tuple[WaveFiveFalsificationTargetKind, ...]:
        """Return required falsification targets absent from this ledger."""

        covered = set(self.covered_targets)
        return tuple(
            target for target in REQUIRED_FALSIFICATION_TARGETS if target not in covered
        )

    @property
    def covered_criterion_kinds(self) -> tuple[WaveFiveKillCriterionKind, ...]:
        """Return kill-criterion kinds represented in this ledger."""

        return tuple(criterion.criterion_kind for criterion in self.kill_criteria)

    @property
    def missing_required_criteria(self) -> tuple[WaveFiveKillCriterionKind, ...]:
        """Return required kill criteria absent from this ledger."""

        covered = set(self.covered_criterion_kinds)
        return tuple(
            criterion
            for criterion in REQUIRED_KILL_CRITERIA
            if criterion not in covered
        )

    @property
    def blocking_challenge_ids(self) -> tuple[str, ...]:
        """Return challenges that are not ready for falsification review."""

        return tuple(
            challenge.challenge_id
            for challenge in self.challenges
            if challenge.blocks_ledger_readiness
        )

    @property
    def blocking_criterion_ids(self) -> tuple[str, ...]:
        """Return kill criteria that block Wave 6 entry."""

        return tuple(
            criterion.criterion_id
            for criterion in self.kill_criteria
            if criterion.blocks_wave_six_entry
        )

    @property
    def blocking_result_ids(self) -> tuple[str, ...]:
        """Return falsification results that block Wave 6 entry."""

        return tuple(
            result.result_id for result in self.results if result.blocks_wave_six_entry
        )

    @property
    def has_required_target_coverage(self) -> bool:
        """Return whether every locked falsification target is covered."""

        return not self.missing_required_targets

    @property
    def has_required_criterion_coverage(self) -> bool:
        """Return whether every locked kill criterion is covered."""

        return not self.missing_required_criteria

    @property
    def makes_no_forbidden_claims(self) -> bool:
        """Return whether ledger avoids forbidden promotion claims."""

        return not any(
            (
                self.attempted_wave_six_promotion,
                self.claims_agi,
                self.grants_execution_authority,
            )
        )

    @property
    def blocks_falsification_readiness(self) -> bool:
        """Return whether any falsification condition blocks readiness."""

        return bool(
            self.missing_required_targets
            or self.missing_required_criteria
            or self.blocking_challenge_ids
            or self.blocking_criterion_ids
            or self.blocking_result_ids
            or not self.makes_no_forbidden_claims
        )

    @property
    def ready_for_external_falsification_review(self) -> bool:
        """Return whether ledger can enter external falsification review."""

        return (
            self.ledger_state
            in {
                WaveFiveFalsificationLedgerState.INTERNAL_LEDGER_READY,
                (
                    WaveFiveFalsificationLedgerState.READY_FOR_EXTERNAL_FALSIFICATION_REVIEW
                ),
                WaveFiveFalsificationLedgerState.UNDER_EXTERNAL_FALSIFICATION_REVIEW,
            }
            and self.has_required_target_coverage
            and self.has_required_criterion_coverage
            and not self.blocking_challenge_ids
            and not self.blocking_criterion_ids
            and not self.blocking_result_ids
            and self.makes_no_forbidden_claims
        )

    @property
    def externally_reviewed_with_boundaries(self) -> bool:
        """Return whether external falsification review accepted boundaries."""

        return (
            self.ledger_state
            is WaveFiveFalsificationLedgerState.EXTERNALLY_REVIEWED_WITH_BOUNDARIES
        )

    @property
    def all_evidence_ids(self) -> tuple[str, ...]:
        """Return all evidence ids bound into this ledger."""

        evidence_ids: list[str] = []
        seen: set[str] = set()
        for evidence_id in self._iter_evidence_ids():
            if evidence_id not in seen:
                evidence_ids.append(evidence_id)
                seen.add(evidence_id)
        return tuple(evidence_ids)

    def to_artifact_ref(self) -> WaveFiveArtifactRef:
        """Return this ledger as a Wave 5 traceability artifact."""

        decision = WaveFiveArtifactDecision.NEEDS_EXTERNAL_EVIDENCE
        status = WaveFiveValidationStatus.MISSING_EXTERNAL_EVIDENCE
        authority = WaveFiveAuthorityState.HUMAN_REVIEW_REQUIRED
        if self.externally_reviewed_with_boundaries:
            decision = WaveFiveArtifactDecision.EXTERNALLY_REVIEWED
            status = WaveFiveValidationStatus.ACCEPTED_WITH_BOUNDARIES
        elif self.ready_for_external_falsification_review:
            decision = WaveFiveArtifactDecision.READY_FOR_INDEPENDENT_REVIEW
            status = WaveFiveValidationStatus.UNDER_INDEPENDENT_REVIEW
        elif self.blocks_falsification_readiness:
            decision = WaveFiveArtifactDecision.BLOCKED
            status = WaveFiveValidationStatus.REJECTED
            authority = WaveFiveAuthorityState.BLOCKED
        return WaveFiveArtifactRef(
            artifact_id=self.ledger_id,
            kind=WaveFiveArtifactKind.ECOSYSTEM_TRACEABILITY_MAP,
            capability_area=WaveFiveCapabilityArea.ECOSYSTEM_TRACEABILITY,
            source_system=self.source_system,
            summary=self.title,
            produced_by_engine_id="wave5-falsification-ledger-engine",
            produced_by_agent_role_id="falsification-reviewer",
            evidence_ids=self.all_evidence_ids,
            decision=decision,
            authority_state=authority,
            validation_status=status,
            claim_boundaries=self.claim_boundaries,
        )

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic export payload."""

        return {
            "attempted_wave_six_promotion": self.attempted_wave_six_promotion,
            "challenges": [item.canonical_payload() for item in self.challenges],
            "claim_boundaries": [boundary.value for boundary in self.claim_boundaries],
            "claims_agi": self.claims_agi,
            "grants_execution_authority": self.grants_execution_authority,
            "kill_criteria": [item.canonical_payload() for item in self.kill_criteria],
            "ledger_id": self.ledger_id,
            "ledger_state": self.ledger_state.value,
            "notes": list(self.notes),
            "protocol_ids": list(self.protocol_ids),
            "results": [item.canonical_payload() for item in self.results],
            "reviewer_ids": list(self.reviewer_ids),
            "schema_version": self.schema_version,
            "source_system": self.source_system.value,
            "title": self.title,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this ledger."""

        return _stable_sha256(self.canonical_payload())

    def _iter_evidence_ids(self) -> Iterable[str]:
        """Yield evidence ids in deterministic ledger traversal order."""

        for challenge in self.challenges:
            yield from challenge.evidence_ids
        for criterion in self.kill_criteria:
            yield from criterion.all_evidence_ids
        for result in self.results:
            yield from result.evidence_ids

    @staticmethod
    def _validate_result_references(
        challenge_ids: set[str],
        criterion_ids: set[str],
        results: tuple[WaveFiveFalsificationResult, ...],
    ) -> None:
        """Validate result references to bundled challenges and criteria."""

        for result in results:
            if result.challenge_id not in challenge_ids:
                raise ValueError(
                    "Falsification results must reference bundled challenges: "
                    f"{result.challenge_id}"
                )
            for criterion_id in result.triggered_criterion_ids:
                if criterion_id not in criterion_ids:
                    raise ValueError(
                        "Falsification results must reference bundled criteria: "
                        f"{criterion_id}"
                    )


def required_falsification_targets() -> tuple[WaveFiveFalsificationTargetKind, ...]:
    """Return locked falsification targets required for Wave 5 review."""

    return REQUIRED_FALSIFICATION_TARGETS


def required_kill_criteria() -> tuple[WaveFiveKillCriterionKind, ...]:
    """Return locked kill criteria required for Wave 5 review."""

    return REQUIRED_KILL_CRITERIA


def safe_falsification_verdicts() -> tuple[WaveFiveFalsificationVerdict, ...]:
    """Return verdicts that do not block Wave 6 design review."""

    return SAFE_FALSIFICATION_VERDICTS


def blocking_falsification_verdicts() -> tuple[WaveFiveFalsificationVerdict, ...]:
    """Return verdicts that block Wave 6 design review."""

    return BLOCKING_FALSIFICATION_VERDICTS


def external_falsification_review_source_systems() -> tuple[WaveFiveSourceSystem, ...]:
    """Return source systems allowed to assert external falsification review."""

    return EXTERNAL_FALSIFICATION_REVIEW_SOURCE_SYSTEMS


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
        item = _text(value, label)
        if item in seen:
            raise ValueError(f"Duplicate {label} detected: {item}")
        normalized.append(item)
        seen.add(item)
    return tuple(normalized)


def _unique_enum(values: Iterable[E], *, label: str) -> tuple[E, ...]:
    """Return enum values while rejecting duplicates."""

    normalized: list[E] = []
    seen: set[E] = set()
    for value in values:
        if value in seen:
            raise ValueError(f"Duplicate {label} detected: {value.value}")
        normalized.append(value)
        seen.add(value)
    return tuple(normalized)


def _unique_values(values: Iterable[T], *, label: str) -> set[T]:
    """Return unique values while rejecting duplicates."""

    seen: set[T] = set()
    for value in values:
        if value in seen:
            raise ValueError(f"Duplicate {label} detected: {value}")
        seen.add(value)
    return seen


def _dedupe_text(values: Iterable[str]) -> tuple[str, ...]:
    """Return de-duplicated text values in input order."""

    deduped: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value not in seen:
            deduped.append(value)
            seen.add(value)
    return tuple(deduped)


def _stable_sha256(payload: Mapping[str, Any]) -> str:
    """Return deterministic SHA-256 over a canonical JSON payload."""

    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
