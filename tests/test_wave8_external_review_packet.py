import pytest

from ix_cognition_kernel.wave8_external_review_packet import (
    ExternalReviewerRole,
    ExternalReviewPacketDecision,
    build_external_review_packet,
    default_wave8_review_questions,
)
from ix_cognition_kernel.wave8_replay_validator import (
    ReplayArtifactKind,
    ReplayArtifactRecord,
    ReplayArtifactStatus,
    validate_replay_packet,
)

_SHA_A = "a" * 64
_SHA_B = "b" * 64
_SHA_C = "c" * 64
_SHA_D = "d" * 64
_SHA_E = "e" * 64


def _artifact(
    artifact_id: str,
    kind: ReplayArtifactKind,
    source_fingerprint: str,
    status: ReplayArtifactStatus = ReplayArtifactStatus.REPLAYABLE,
) -> ReplayArtifactRecord:
    return ReplayArtifactRecord(
        artifact_id=artifact_id,
        kind=kind,
        source_fingerprint=source_fingerprint,
        status=status,
        evidence_ids=(f"{artifact_id}:evidence",),
        summary=f"{artifact_id} is available for bounded external review.",
    )


def _artifacts():
    return (
        _artifact("artifact-episode", ReplayArtifactKind.EPISODE_RUN, _SHA_A),
        _artifact("artifact-transfer", ReplayArtifactKind.TRANSFER_REPORT, _SHA_B),
        _artifact("artifact-skill", ReplayArtifactKind.SKILL_VALIDATION, _SHA_C),
        _artifact("artifact-world", ReplayArtifactKind.WORLD_MODEL_SNAPSHOT, _SHA_D),
        _artifact("artifact-baseline", ReplayArtifactKind.BASELINE_COMPARISON, _SHA_E),
    )


def _replay_report():
    return validate_replay_packet(
        report_id="replay-report-ready",
        purpose="Validate bounded Wave 8 replay packet for human review.",
        artifacts=_artifacts(),
    )


def _roles():
    return (
        ExternalReviewerRole.HUMAN_AUTHORITY,
        ExternalReviewerRole.INDEPENDENT_REPLAYER,
        ExternalReviewerRole.SAFETY_REVIEWER,
        ExternalReviewerRole.BASELINE_REVIEWER,
        ExternalReviewerRole.TRANSFER_REVIEWER,
    )


def test_external_review_packet_ready_with_replay_artifacts_roles_and_questions() -> (
    None
):
    packet = build_external_review_packet(
        packet_id="external-review-packet-1",
        purpose="Package bounded recursive learning evidence for external review.",
        claim_boundary="Bounded recursive learning evidence only; no certification.",
        replay_report=_replay_report(),
        reviewer_roles=_roles(),
        questions=default_wave8_review_questions(),
        evidence_ids=("packet-evidence-1",),
    )

    assert packet.ready
    assert packet.decision is ExternalReviewPacketDecision.READY_FOR_EXTERNAL_REVIEW
    assert packet.findings == ()
    assert "episode-run" in packet.artifact_kinds_under_review
    assert "baseline-comparison" in packet.artifact_kinds_under_review
    assert packet.fingerprint() == packet.fingerprint()
    assert len(packet.fingerprint()) == 64


def test_external_review_packet_requires_ready_replay_report() -> None:
    replay_report = validate_replay_packet(
        report_id="replay-report-missing",
        purpose="Validate incomplete replay packet.",
        artifacts=_artifacts()[:2],
    )
    packet = build_external_review_packet(
        packet_id="external-review-packet-missing-replay",
        purpose="Package bounded recursive learning evidence for external review.",
        claim_boundary="Bounded recursive learning evidence only; no certification.",
        replay_report=replay_report,
        reviewer_roles=_roles(),
        questions=default_wave8_review_questions(),
        evidence_ids=("packet-evidence-1",),
    )

    assert not packet.ready
    assert packet.decision is ExternalReviewPacketDecision.NEEDS_REPLAY_VALIDATION
    assert any(
        finding.startswith("replay-report-not-ready") for finding in packet.findings
    )


def test_external_review_packet_requires_all_reviewer_roles() -> None:
    packet = build_external_review_packet(
        packet_id="external-review-packet-missing-roles",
        purpose="Package bounded recursive learning evidence for external review.",
        claim_boundary="Bounded recursive learning evidence only; no certification.",
        replay_report=_replay_report(),
        reviewer_roles=(
            ExternalReviewerRole.HUMAN_AUTHORITY,
            ExternalReviewerRole.INDEPENDENT_REPLAYER,
        ),
        questions=default_wave8_review_questions(),
        evidence_ids=("packet-evidence-1",),
    )

    assert not packet.ready
    assert packet.decision is ExternalReviewPacketDecision.NEEDS_REQUIRED_REVIEWERS
    assert any(
        finding.startswith("missing-reviewer-roles") for finding in packet.findings
    )


def test_external_review_packet_requires_review_questions() -> None:
    packet = build_external_review_packet(
        packet_id="external-review-packet-missing-questions",
        purpose="Package bounded recursive learning evidence for external review.",
        claim_boundary="Bounded recursive learning evidence only; no certification.",
        replay_report=_replay_report(),
        reviewer_roles=_roles(),
        questions=(),
        evidence_ids=("packet-evidence-1",),
    )

    assert not packet.ready
    assert packet.decision is ExternalReviewPacketDecision.NEEDS_REVIEW_QUESTIONS
    assert "missing-review-questions" in packet.findings


def test_external_review_packet_rejects_duplicate_reviewer_roles() -> None:
    with pytest.raises(ValueError, match="Duplicate reviewer role"):
        build_external_review_packet(
            packet_id="external-review-packet-duplicate-role",
            purpose="Package bounded recursive learning evidence for external review.",
            claim_boundary=(
                "Bounded recursive learning evidence only; no certification."
            ),
            replay_report=_replay_report(),
            reviewer_roles=(
                ExternalReviewerRole.HUMAN_AUTHORITY,
                ExternalReviewerRole.HUMAN_AUTHORITY,
            ),
            questions=default_wave8_review_questions(),
            evidence_ids=("packet-evidence-1",),
        )


def test_external_review_packet_rejects_overclaiming_purpose_or_boundary() -> None:
    with pytest.raises(ValueError, match="blocked overclaiming"):
        build_external_review_packet(
            packet_id="external-review-packet-overclaim-purpose",
            purpose="This proves AGI.",
            claim_boundary=(
                "Bounded recursive learning evidence only; no certification."
            ),
            replay_report=_replay_report(),
            reviewer_roles=_roles(),
            questions=default_wave8_review_questions(),
            evidence_ids=("packet-evidence-1",),
        )

    with pytest.raises(ValueError, match="blocked overclaiming"):
        build_external_review_packet(
            packet_id="external-review-packet-overclaim-boundary",
            purpose="Package bounded recursive learning evidence for external review.",
            claim_boundary="This is an artificial general intelligence certification.",
            replay_report=_replay_report(),
            reviewer_roles=_roles(),
            questions=default_wave8_review_questions(),
            evidence_ids=("packet-evidence-1",),
        )
