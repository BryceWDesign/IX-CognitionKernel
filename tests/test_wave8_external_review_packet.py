"""Tests for Wave 8 external review packet."""

from __future__ import annotations

import pytest

from ix_cognition_kernel.wave8_external_review_packet import (
    ExternalReviewPacketDecision,
    ReviewerRole,
    build_external_review_packet,
    default_review_questions,
)
from ix_cognition_kernel.wave8_replay_validator import (
    ReplayArtifactKind,
    ReplayArtifactRecord,
    ReplayArtifactStatus,
    ReplayValidationDecision,
    validate_replay_packet,
)


def _artifact(
    artifact_id: str,
    kind: ReplayArtifactKind,
    status: ReplayArtifactStatus = ReplayArtifactStatus.REPLAYABLE,
) -> ReplayArtifactRecord:
    return ReplayArtifactRecord(
        artifact_id=artifact_id,
        kind=kind,
        source_fingerprint="a" * 64,
        status=status,
        evidence_ids=(f"evidence-{artifact_id}",),
        summary=f"{kind.value} is bounded review evidence.",
    )


def _ready_replay_report() -> object:
    return validate_replay_packet(
        report_id="replay-report-review",
        purpose="Validate bounded replay evidence for review.",
        artifacts=(
            _artifact("artifact-episode", ReplayArtifactKind.EPISODE_RUN),
            _artifact("artifact-transfer", ReplayArtifactKind.TRANSFER_REPORT),
            _artifact("artifact-skill", ReplayArtifactKind.SKILL_VALIDATION),
            _artifact("artifact-world", ReplayArtifactKind.WORLD_MODEL_SNAPSHOT),
            _artifact("artifact-baseline", ReplayArtifactKind.BASELINE_COMPARISON),
        ),
    )


def test_default_review_questions_cover_core_roles() -> None:
    questions = default_review_questions(evidence_prefix="review-evidence")

    roles = {question.reviewer_role for question in questions}
    assert ReviewerRole.EXTERNAL_RESEARCHER in roles
    assert ReviewerRole.SAFETY_REVIEWER in roles
    assert ReviewerRole.HUMAN_AUTHORITY in roles
    assert all(len(question.fingerprint()) == 64 for question in questions)


def test_external_review_packet_ready_when_replay_and_questions_are_ready() -> None:
    packet = build_external_review_packet(
        packet_id="packet-ready",
        purpose="Provide bounded replay evidence to external reviewers.",
        claim_boundary="Review packet only; no certification.",
        replay_report=_ready_replay_report(),
        review_questions=default_review_questions(evidence_prefix="review-evidence"),
        evidence_ids=("packet-evidence-1",),
    )

    assert packet.decision is ExternalReviewPacketDecision.READY_FOR_EXTERNAL_REVIEW
    assert packet.ready
    assert packet.question_count == 4


def test_external_review_packet_needs_replay_when_report_is_not_ready() -> None:
    report = validate_replay_packet(
        report_id="replay-report-not-ready",
        purpose="Validate bounded replay evidence for review.",
        artifacts=(
            _artifact(
                "artifact-episode",
                ReplayArtifactKind.EPISODE_RUN,
                ReplayArtifactStatus.NEEDS_MEASURED_RESULT,
            ),
        ),
    )
    packet = build_external_review_packet(
        packet_id="packet-not-ready",
        purpose="Provide bounded replay evidence to external reviewers.",
        claim_boundary="Review packet only; no certification.",
        replay_report=report,
        review_questions=default_review_questions(evidence_prefix="review-evidence"),
        evidence_ids=("packet-evidence-1",),
    )

    assert packet.decision is ExternalReviewPacketDecision.NEEDS_REPLAY_VALIDATION
    assert "replay-report-not-ready" in packet.findings[0]


def test_external_review_packet_needs_questions() -> None:
    packet = build_external_review_packet(
        packet_id="packet-no-questions",
        purpose="Provide bounded replay evidence to external reviewers.",
        claim_boundary="Review packet only; no certification.",
        replay_report=_ready_replay_report(),
        review_questions=(),
        evidence_ids=("packet-evidence-1",),
    )

    assert packet.decision is ExternalReviewPacketDecision.NEEDS_REVIEW_QUESTIONS
    assert "missing-review-questions" in packet.findings


def test_external_review_packet_blocks_overclaiming_claim_boundary() -> None:
    with pytest.raises(ValueError, match="blocked overclaiming"):
        build_external_review_packet(
            packet_id="packet-overclaim",
            purpose="Provide bounded replay evidence to external reviewers.",
            claim_boundary="Certifies AGI.",
            replay_report=_ready_replay_report(),
            review_questions=default_review_questions(evidence_prefix="review-evidence"),
            evidence_ids=("packet-evidence-1",),
        )


def test_external_review_packet_blocks_when_review_question_overclaims() -> None:
    from ix_cognition_kernel.wave8_external_review_packet import ExternalReviewQuestion

    with pytest.raises(ValueError, match="blocked overclaiming"):
        ExternalReviewQuestion(
            question_id="question-overclaim",
            reviewer_role=ReviewerRole.EXTERNAL_RESEARCHER,
            prompt="Does this certify AGI?",
            required_artifact_kinds=(ReplayArtifactKind.EPISODE_RUN,),
            evidence_ids=("question-evidence-1",),
        )


def test_external_review_packet_fingerprint_is_deterministic() -> None:
    packet = build_external_review_packet(
        packet_id="packet-stable",
        purpose="Provide bounded replay evidence to external reviewers.",
        claim_boundary="Review packet only; no certification.",
        replay_report=_ready_replay_report(),
        review_questions=default_review_questions(evidence_prefix="review-evidence"),
        evidence_ids=("packet-evidence-1",),
    )
    same = build_external_review_packet(
        packet_id="packet-stable",
        purpose="Provide bounded replay evidence to external reviewers.",
        claim_boundary="Review packet only; no certification.",
        replay_report=_ready_replay_report(),
        review_questions=default_review_questions(evidence_prefix="review-evidence"),
        evidence_ids=("packet-evidence-1",),
    )

    assert packet.fingerprint() == same.fingerprint()
    assert packet.replay_report.decision is ReplayValidationDecision.READY_FOR_REVIEW
