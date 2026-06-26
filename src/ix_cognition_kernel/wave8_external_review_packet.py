"""Wave 8 external review packet.

This module adds the first external-review packaging surface for the Recursive
Reality-Corrected Learner. It does not certify intelligence. It packages replay
evidence, review questions, reviewer roles, claim boundaries, and fail-closed
findings so that a human or independent reviewer can inspect what happened.

External-review doctrine:

- internal replay is not independent validation,
- a review packet is not a certification,
- reviewer roles must be explicit,
- required artifacts must be present and replay-ready,
- questions must be tied to artifact kinds,
- claim boundaries must reject overclaiming language,
- the system cannot approve its own maturity claim.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from ix_cognition_kernel.wave8_replay_validator import (
    ReplayArtifactKind,
    ReplayValidationDecision,
    ReplayValidationReport,
)

WAVE_EIGHT_REVIEW_QUESTION_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave8-review-question-v1"
)
WAVE_EIGHT_EXTERNAL_REVIEW_PACKET_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave8-external-review-packet-v1"
)


class ExternalReviewerRole(StrEnum):
    """Required external review roles for Wave 8 evidence packets."""

    HUMAN_AUTHORITY = "human-authority"
    INDEPENDENT_REPLAYER = "independent-replayer"
    SAFETY_REVIEWER = "safety-reviewer"
    BASELINE_REVIEWER = "baseline-reviewer"
    TRANSFER_REVIEWER = "transfer-reviewer"


class ReviewQuestionScope(StrEnum):
    """Scope for an external review question."""

    EPISODE_REPLAY = "episode-replay"
    TRANSFER_GENERALIZATION = "transfer-generalization"
    SKILL_REUSE = "skill-reuse"
    WORLD_MODEL = "world-model"
    BASELINE_IMPROVEMENT = "baseline-improvement"
    CLAIM_BOUNDARY = "claim-boundary"


class ExternalReviewPacketDecision(StrEnum):
    """Fail-closed external review packet decision."""

    READY_FOR_EXTERNAL_REVIEW = "ready-for-external-review"
    NEEDS_REPLAY_VALIDATION = "needs-replay-validation"
    NEEDS_REQUIRED_ARTIFACTS = "needs-required-artifacts"
    NEEDS_REQUIRED_REVIEWERS = "needs-required-reviewers"
    NEEDS_REVIEW_QUESTIONS = "needs-review-questions"
    BLOCKED = "blocked"
    OVERCLAIM_BLOCKED = "overclaim-blocked"


@dataclass(frozen=True, slots=True)
class ExternalReviewQuestion:
    """Question an external reviewer must answer against replay artifacts."""

    question_id: str
    scope: ReviewQuestionScope
    prompt: str
    required_artifact_kinds: tuple[ReplayArtifactKind, ...]
    evidence_ids: tuple[str, ...]
    schema_version: str = WAVE_EIGHT_REVIEW_QUESTION_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate review-question scope and artifact bindings."""

        object.__setattr__(
            self,
            "question_id",
            _require_non_empty(self.question_id, "question_id"),
        )
        object.__setattr__(
            self,
            "prompt",
            _require_non_empty(self.prompt, "prompt"),
        )
        _reject_overclaiming_text(self.prompt, "prompt")
        object.__setattr__(
            self,
            "required_artifact_kinds",
            tuple(self.required_artifact_kinds),
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
        if not self.required_artifact_kinds:
            raise ValueError("External review questions require artifact kinds.")
        if not self.evidence_ids:
            raise ValueError("External review questions require evidence ids.")
        seen: set[ReplayArtifactKind] = set()
        for kind in self.required_artifact_kinds:
            if kind in seen:
                raise ValueError(f"Duplicate required artifact kind: {kind.value}")
            seen.add(kind)

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic review-question payload."""

        return {
            "evidence_ids": list(self.evidence_ids),
            "prompt": self.prompt,
            "question_id": self.question_id,
            "required_artifact_kinds": [
                kind.value for kind in self.required_artifact_kinds
            ],
            "schema_version": self.schema_version,
            "scope": self.scope.value,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this question."""

        return _stable_sha256(self.canonical_payload())


@dataclass(frozen=True, slots=True)
class ExternalReviewPacket:
    """Evidence-bound external review packet."""

    packet_id: str
    purpose: str
    claim_boundary: str
    replay_report: ReplayValidationReport
    reviewer_roles: tuple[ExternalReviewerRole, ...]
    questions: tuple[ExternalReviewQuestion, ...]
    decision: ExternalReviewPacketDecision
    findings: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    schema_version: str = WAVE_EIGHT_EXTERNAL_REVIEW_PACKET_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate review packet coverage, roles, and claim boundary."""

        object.__setattr__(
            self,
            "packet_id",
            _require_non_empty(self.packet_id, "packet_id"),
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
            "reviewer_roles",
            _normalize_unique_roles(self.reviewer_roles),
        )
        object.__setattr__(
            self,
            "questions",
            tuple(self.questions),
        )
        object.__setattr__(
            self,
            "findings",
            _dedupe_text_tuple(self.findings, label="finding"),
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
        if not self.evidence_ids:
            raise ValueError("External review packets require evidence ids.")
        seen_questions: set[str] = set()
        for question in self.questions:
            if question.question_id in seen_questions:
                raise ValueError(f"Duplicate question_id: {question.question_id}")
            seen_questions.add(question.question_id)
        if (
            self.decision is not ExternalReviewPacketDecision.READY_FOR_EXTERNAL_REVIEW
            and not self.findings
        ):
            raise ValueError("Non-ready external review packets require findings.")

    @property
    def ready(self) -> bool:
        """Return whether this packet is ready for external review."""

        return self.decision is ExternalReviewPacketDecision.READY_FOR_EXTERNAL_REVIEW

    @property
    def artifact_kinds_under_review(self) -> tuple[str, ...]:
        """Return artifact kinds referenced by review questions."""

        kinds = {
            kind.value
            for question in self.questions
            for kind in question.required_artifact_kinds
        }
        return tuple(sorted(kinds))

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic external review packet payload."""

        return {
            "artifact_kinds_under_review": list(self.artifact_kinds_under_review),
            "claim_boundary": self.claim_boundary,
            "decision": self.decision.value,
            "evidence_ids": list(self.evidence_ids),
            "findings": list(self.findings),
            "packet_id": self.packet_id,
            "purpose": self.purpose,
            "question_fingerprints": [
                question.fingerprint() for question in self.questions
            ],
            "replay_report_fingerprint": self.replay_report.fingerprint(),
            "reviewer_roles": [role.value for role in self.reviewer_roles],
            "schema_version": self.schema_version,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this packet."""

        return _stable_sha256(self.canonical_payload())


def default_wave8_review_questions(
    *, evidence_prefix: str = "wave8-review"
) -> tuple[ExternalReviewQuestion, ...]:
    """Return default review questions for Wave 8 external review."""

    prefix = _require_non_empty(evidence_prefix, "evidence_prefix")
    return (
        ExternalReviewQuestion(
            question_id="question-episode-replay",
            scope=ReviewQuestionScope.EPISODE_REPLAY,
            prompt=(
                "Can the bounded episode run be replayed from recorded "
                "environment, observation, action, and measured-result artifacts?"
            ),
            required_artifact_kinds=(ReplayArtifactKind.EPISODE_RUN,),
            evidence_ids=(f"{prefix}:episode-question",),
        ),
        ExternalReviewQuestion(
            question_id="question-transfer-generalization",
            scope=ReviewQuestionScope.TRANSFER_GENERALIZATION,
            prompt=(
                "Does the transfer report separate seed success from near, far, "
                "adversarial, and hidden-validation pressure?"
            ),
            required_artifact_kinds=(ReplayArtifactKind.TRANSFER_REPORT,),
            evidence_ids=(f"{prefix}:transfer-question",),
        ),
        ExternalReviewQuestion(
            question_id="question-skill-reuse",
            scope=ReviewQuestionScope.SKILL_REUSE,
            prompt=(
                "Was the reusable skill promoted only after replayable transfer "
                "evidence and preserved failure-mode review?"
            ),
            required_artifact_kinds=(ReplayArtifactKind.SKILL_VALIDATION,),
            evidence_ids=(f"{prefix}:skill-question",),
        ),
        ExternalReviewQuestion(
            question_id="question-world-model",
            scope=ReviewQuestionScope.WORLD_MODEL,
            prompt=(
                "Are durable world-model rules scoped, revisable, contradiction-aware, "
                "and tied to replay evidence?"
            ),
            required_artifact_kinds=(ReplayArtifactKind.WORLD_MODEL_SNAPSHOT,),
            evidence_ids=(f"{prefix}:world-question",),
        ),
        ExternalReviewQuestion(
            question_id="question-baseline-improvement",
            scope=ReviewQuestionScope.BASELINE_IMPROVEMENT,
            prompt=(
                "Does the candidate outperform the model-alone baseline on the same "
                "bounded tasks without hiding ties or regressions?"
            ),
            required_artifact_kinds=(ReplayArtifactKind.BASELINE_COMPARISON,),
            evidence_ids=(f"{prefix}:baseline-question",),
        ),
        ExternalReviewQuestion(
            question_id="question-claim-boundary",
            scope=ReviewQuestionScope.CLAIM_BOUNDARY,
            prompt=(
                "Does the packet preserve the boundary that this is a bounded "
                "recursive learning review artifact, not a certification?"
            ),
            required_artifact_kinds=(
                ReplayArtifactKind.EPISODE_RUN,
                ReplayArtifactKind.TRANSFER_REPORT,
                ReplayArtifactKind.BASELINE_COMPARISON,
            ),
            evidence_ids=(f"{prefix}:claim-boundary-question",),
        ),
    )


def build_external_review_packet(
    *,
    packet_id: str,
    purpose: str,
    claim_boundary: str,
    replay_report: ReplayValidationReport,
    reviewer_roles: Iterable[ExternalReviewerRole],
    questions: Iterable[ExternalReviewQuestion],
    evidence_ids: Iterable[str],
) -> ExternalReviewPacket:
    """Build an external review packet with a deterministic fail-closed decision."""

    role_tuple = tuple(reviewer_roles)
    question_tuple = tuple(questions)
    findings = _packet_findings(
        replay_report=replay_report,
        reviewer_roles=role_tuple,
        questions=question_tuple,
    )
    decision = _packet_decision(replay_report=replay_report, findings=findings)
    return ExternalReviewPacket(
        packet_id=packet_id,
        purpose=purpose,
        claim_boundary=claim_boundary,
        replay_report=replay_report,
        reviewer_roles=role_tuple,
        questions=question_tuple,
        decision=decision,
        findings=findings,
        evidence_ids=tuple(evidence_ids),
    )


def _packet_findings(
    *,
    replay_report: ReplayValidationReport,
    reviewer_roles: tuple[ExternalReviewerRole, ...],
    questions: tuple[ExternalReviewQuestion, ...],
) -> tuple[str, ...]:
    findings: list[str] = []
    if replay_report.decision is not ReplayValidationDecision.READY_FOR_REVIEW:
        findings.append(f"replay-report-not-ready:{replay_report.decision.value}")

    required_roles = {
        ExternalReviewerRole.HUMAN_AUTHORITY,
        ExternalReviewerRole.INDEPENDENT_REPLAYER,
        ExternalReviewerRole.SAFETY_REVIEWER,
        ExternalReviewerRole.BASELINE_REVIEWER,
        ExternalReviewerRole.TRANSFER_REVIEWER,
    }
    missing_roles = tuple(
        sorted(role.value for role in required_roles - set(reviewer_roles))
    )
    if missing_roles:
        findings.append(f"missing-reviewer-roles:{','.join(missing_roles)}")

    if not questions:
        findings.append("missing-review-questions")
    artifact_kinds = {artifact.kind for artifact in replay_report.artifacts}
    question_artifact_kinds = {
        kind for question in questions for kind in question.required_artifact_kinds
    }
    missing_question_artifacts = tuple(
        sorted(kind.value for kind in question_artifact_kinds - artifact_kinds)
    )
    if missing_question_artifacts:
        findings.append(
            f"question-artifacts-not-in-replay-report:"
            f"{','.join(missing_question_artifacts)}"
        )

    required_question_scopes = {
        ReviewQuestionScope.EPISODE_REPLAY,
        ReviewQuestionScope.TRANSFER_GENERALIZATION,
        ReviewQuestionScope.SKILL_REUSE,
        ReviewQuestionScope.WORLD_MODEL,
        ReviewQuestionScope.BASELINE_IMPROVEMENT,
        ReviewQuestionScope.CLAIM_BOUNDARY,
    }
    question_scopes = {question.scope for question in questions}
    missing_scopes = tuple(
        sorted(scope.value for scope in required_question_scopes - question_scopes)
    )
    if missing_scopes:
        findings.append(f"missing-review-question-scopes:{','.join(missing_scopes)}")

    return tuple(findings)


def _packet_decision(
    *,
    replay_report: ReplayValidationReport,
    findings: tuple[str, ...],
) -> ExternalReviewPacketDecision:
    if replay_report.decision is ReplayValidationDecision.OVERCLAIM_BLOCKED:
        return ExternalReviewPacketDecision.OVERCLAIM_BLOCKED
    if replay_report.decision is ReplayValidationDecision.BLOCKED:
        return ExternalReviewPacketDecision.BLOCKED
    if any(finding.startswith("replay-report-not-ready") for finding in findings):
        return ExternalReviewPacketDecision.NEEDS_REPLAY_VALIDATION
    if any(
        finding.startswith("question-artifacts-not-in-replay-report")
        for finding in findings
    ):
        return ExternalReviewPacketDecision.NEEDS_REQUIRED_ARTIFACTS
    if any(finding.startswith("missing-reviewer-roles") for finding in findings):
        return ExternalReviewPacketDecision.NEEDS_REQUIRED_REVIEWERS
    if any(finding.startswith("missing-review-question") for finding in findings):
        return ExternalReviewPacketDecision.NEEDS_REVIEW_QUESTIONS
    return ExternalReviewPacketDecision.READY_FOR_EXTERNAL_REVIEW


def _normalize_unique_roles(
    values: Iterable[ExternalReviewerRole],
) -> tuple[ExternalReviewerRole, ...]:
    normalized: list[ExternalReviewerRole] = []
    seen: set[ExternalReviewerRole] = set()
    for role in values:
        if role in seen:
            raise ValueError(f"Duplicate reviewer role: {role.value}")
        seen.add(role)
        normalized.append(role)
    if not normalized:
        raise ValueError("External review packets require reviewer roles.")
    return tuple(sorted(normalized, key=lambda role: role.value))


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
