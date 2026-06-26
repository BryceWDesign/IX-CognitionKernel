"""Tests for Wave 8 release manifest."""

from __future__ import annotations

import pytest

from ix_cognition_kernel.wave8_external_review_packet import (
    ExternalReviewPacketDecision,
    build_external_review_packet,
    default_review_questions,
)
from ix_cognition_kernel.wave8_release_manifest import (
    ReleaseGateDecision,
    ReleaseGateKind,
    ReleaseGateRecord,
    Wave8ReleaseDecision,
    build_wave8_release_manifest,
    default_wave8_release_gates,
)
from ix_cognition_kernel.wave8_replay_validator import (
    ReplayArtifactKind,
    ReplayArtifactRecord,
    ReplayArtifactStatus,
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
        report_id="replay-report-release",
        purpose="Validate bounded replay evidence for release review.",
        artifacts=(
            _artifact("artifact-episode", ReplayArtifactKind.EPISODE_RUN),
            _artifact("artifact-transfer", ReplayArtifactKind.TRANSFER_REPORT),
            _artifact("artifact-skill", ReplayArtifactKind.SKILL_VALIDATION),
            _artifact("artifact-world", ReplayArtifactKind.WORLD_MODEL_SNAPSHOT),
            _artifact("artifact-baseline", ReplayArtifactKind.BASELINE_COMPARISON),
        ),
    )


def _ready_external_packet() -> object:
    return build_external_review_packet(
        packet_id="packet-release-ready",
        purpose="Provide bounded replay evidence to external reviewers.",
        claim_boundary="Review packet only; no certification.",
        replay_report=_ready_replay_report(),
        review_questions=default_review_questions(evidence_prefix="review-evidence"),
        evidence_ids=("packet-evidence-1",),
    )


def test_default_release_gates_pass_when_authority_and_packet_are_ready() -> None:
    gates = default_wave8_release_gates(
        external_review_packet=_ready_external_packet(),
        human_authority_evidence_ids=("human-authority-evidence-1",),
    )

    assert len(gates) == 7
    assert all(gate.decision is ReleaseGateDecision.PASS for gate in gates)
    assert {gate.kind for gate in gates} == {
        ReleaseGateKind.REPLAY_VALIDATION,
        ReleaseGateKind.EXTERNAL_REVIEW_PACKET,
        ReleaseGateKind.CLAIM_BOUNDARY,
        ReleaseGateKind.HUMAN_AUTHORITY,
        ReleaseGateKind.BASELINE_IMPROVEMENT,
        ReleaseGateKind.TRANSFER_EVIDENCE,
        ReleaseGateKind.NO_SELF_CERTIFICATION,
    }


def test_release_gates_block_missing_human_authority() -> None:
    gates = default_wave8_release_gates(
        external_review_packet=_ready_external_packet(),
        human_authority_evidence_ids=(),
    )

    human_gate = next(gate for gate in gates if gate.kind is ReleaseGateKind.HUMAN_AUTHORITY)
    assert human_gate.decision is ReleaseGateDecision.BLOCK
    assert "missing-human-authority-evidence" in human_gate.findings


def test_release_manifest_ready_when_all_gates_pass() -> None:
    packet = _ready_external_packet()
    manifest = build_wave8_release_manifest(
        manifest_id="manifest-ready",
        wave_name="Wave 8 Recursive Reality Corrected Learner",
        purpose="Bind bounded release evidence for review handoff.",
        claim_boundary="Review handoff only; no certification.",
        external_review_packet=packet,
        gates=default_wave8_release_gates(
            external_review_packet=packet,
            human_authority_evidence_ids=("human-authority-evidence-1",),
        ),
        evidence_ids=("manifest-evidence-1",),
    )

    assert manifest.decision is Wave8ReleaseDecision.READY_FOR_REVIEW_HANDOFF
    assert manifest.ready
    assert manifest.blocked_gate_count == 0
    assert len(manifest.fingerprint()) == 64


def test_release_manifest_blocks_when_gate_blocks() -> None:
    packet = _ready_external_packet()
    gates = default_wave8_release_gates(
        external_review_packet=packet,
        human_authority_evidence_ids=(),
    )
    manifest = build_wave8_release_manifest(
        manifest_id="manifest-blocked",
        wave_name="Wave 8 Recursive Reality Corrected Learner",
        purpose="Bind bounded release evidence for review handoff.",
        claim_boundary="Review handoff only; no certification.",
        external_review_packet=packet,
        gates=gates,
        evidence_ids=("manifest-evidence-1",),
    )

    assert manifest.decision is Wave8ReleaseDecision.BLOCKED
    assert manifest.blocked_gate_count == 1
    assert any(finding.startswith("blocked-release-gates") for finding in manifest.findings)


def test_release_manifest_warns_when_gate_warns() -> None:
    packet = _ready_external_packet()
    gates = (
        *default_wave8_release_gates(
            external_review_packet=packet,
            human_authority_evidence_ids=("human-authority-evidence-1",),
        )[:-1],
        ReleaseGateRecord(
            gate_id="gate-no-self-certification",
            kind=ReleaseGateKind.NO_SELF_CERTIFICATION,
            decision=ReleaseGateDecision.WARN,
            summary="No self-certification boundary needs reviewer confirmation.",
            evidence_ids=("warning-evidence-1",),
            findings=("reviewer-confirmation-needed",),
        ),
    )
    manifest = build_wave8_release_manifest(
        manifest_id="manifest-warning",
        wave_name="Wave 8 Recursive Reality Corrected Learner",
        purpose="Bind bounded release evidence for review handoff.",
        claim_boundary="Review handoff only; no certification.",
        external_review_packet=packet,
        gates=gates,
        evidence_ids=("manifest-evidence-1",),
    )

    assert manifest.decision is Wave8ReleaseDecision.READY_WITH_WARNINGS
    assert manifest.warning_gate_count == 1


def test_release_manifest_needs_review_packet_when_packet_not_ready() -> None:
    replay_report = validate_replay_packet(
        report_id="replay-report-not-ready",
        purpose="Validate bounded replay evidence for release review.",
        artifacts=(
            _artifact(
                "artifact-episode",
                ReplayArtifactKind.EPISODE_RUN,
                ReplayArtifactStatus.NEEDS_MEASURED_RESULT,
            ),
        ),
    )
    packet = build_external_review_packet(
        packet_id="packet-release-not-ready",
        purpose="Provide bounded replay evidence to external reviewers.",
        claim_boundary="Review packet only; no certification.",
        replay_report=replay_report,
        review_questions=default_review_questions(evidence_prefix="review-evidence"),
        evidence_ids=("packet-evidence-1",),
    )
    manifest = build_wave8_release_manifest(
        manifest_id="manifest-needs-packet",
        wave_name="Wave 8 Recursive Reality Corrected Learner",
        purpose="Bind bounded release evidence for review handoff.",
        claim_boundary="Review handoff only; no certification.",
        external_review_packet=packet,
        gates=default_wave8_release_gates(
            external_review_packet=packet,
            human_authority_evidence_ids=("human-authority-evidence-1",),
        ),
        evidence_ids=("manifest-evidence-1",),
    )

    assert packet.decision is ExternalReviewPacketDecision.NEEDS_REPLAY_VALIDATION
    assert manifest.decision is Wave8ReleaseDecision.BLOCKED


def test_release_manifest_rejects_overclaiming_wave_name() -> None:
    packet = _ready_external_packet()
    with pytest.raises(ValueError, match="blocked overclaiming"):
        build_wave8_release_manifest(
            manifest_id="manifest-overclaim",
            wave_name="AGI achieved",
            purpose="Bind bounded release evidence for review handoff.",
            claim_boundary="Review handoff only; no certification.",
            external_review_packet=packet,
            gates=default_wave8_release_gates(
                external_review_packet=packet,
                human_authority_evidence_ids=("human-authority-evidence-1",),
            ),
            evidence_ids=("manifest-evidence-1",),
        )
