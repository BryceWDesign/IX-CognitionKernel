import pytest

from ix_cognition_kernel.wave8_external_review_packet import (
    ExternalReviewerRole,
    ExternalReviewPacketDecision,
    build_external_review_packet,
    default_wave8_review_questions,
)
from ix_cognition_kernel.wave8_release_manifest import (
    ReleaseGateDecision,
    ReleaseGateKind,
    ReleaseGateRecord,
    Wave8ReleaseDecision,
    Wave8ReleaseManifest,
    build_wave8_release_manifest,
    default_wave8_release_gates,
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
        summary=f"{artifact_id} is available for release manifest review.",
    )


def _artifacts():
    return (
        _artifact("artifact-episode", ReplayArtifactKind.EPISODE_RUN, _SHA_A),
        _artifact("artifact-transfer", ReplayArtifactKind.TRANSFER_REPORT, _SHA_B),
        _artifact("artifact-skill", ReplayArtifactKind.SKILL_VALIDATION, _SHA_C),
        _artifact("artifact-world", ReplayArtifactKind.WORLD_MODEL_SNAPSHOT, _SHA_D),
        _artifact("artifact-baseline", ReplayArtifactKind.BASELINE_COMPARISON, _SHA_E),
    )


def _roles():
    return (
        ExternalReviewerRole.HUMAN_AUTHORITY,
        ExternalReviewerRole.INDEPENDENT_REPLAYER,
        ExternalReviewerRole.SAFETY_REVIEWER,
        ExternalReviewerRole.BASELINE_REVIEWER,
        ExternalReviewerRole.TRANSFER_REVIEWER,
    )


def _external_packet():
    replay_report = validate_replay_packet(
        report_id="replay-report-ready",
        purpose="Validate bounded Wave 8 replay packet for human review.",
        artifacts=_artifacts(),
    )
    return build_external_review_packet(
        packet_id="external-review-packet-1",
        purpose="Package bounded recursive learning evidence for external review.",
        claim_boundary="Bounded recursive learning evidence only; no certification.",
        replay_report=replay_report,
        reviewer_roles=_roles(),
        questions=default_wave8_review_questions(),
        evidence_ids=("packet-evidence-1",),
    )


def test_default_release_gates_pass_with_ready_packet_and_human_authority() -> None:
    packet = _external_packet()
    gates = default_wave8_release_gates(
        external_review_packet=packet,
        human_authority_evidence_ids=("human-review-evidence-1",),
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


def test_release_manifest_ready_with_complete_passed_gates() -> None:
    packet = _external_packet()
    gates = default_wave8_release_gates(
        external_review_packet=packet,
        human_authority_evidence_ids=("human-review-evidence-1",),
    )
    manifest = build_wave8_release_manifest(
        manifest_id="wave8-release-manifest-1",
        wave_name="Wave 8 Recursive Reality-Corrected Learner",
        purpose="Bind bounded recursive learning evidence for review handoff.",
        claim_boundary="Review handoff only; no certification.",
        external_review_packet=packet,
        gates=gates,
        evidence_ids=("manifest-evidence-1",),
    )

    assert manifest.ready
    assert manifest.decision is Wave8ReleaseDecision.READY_FOR_REVIEW_HANDOFF
    assert manifest.blocked_gate_count == 0
    assert manifest.warning_gate_count == 0
    assert manifest.findings == ()
    assert manifest.fingerprint() == manifest.fingerprint()
    assert len(manifest.fingerprint()) == 64


def test_release_manifest_blocks_missing_human_authority_evidence() -> None:
    packet = _external_packet()
    gates = default_wave8_release_gates(
        external_review_packet=packet,
        human_authority_evidence_ids=(),
    )
    manifest = build_wave8_release_manifest(
        manifest_id="wave8-release-manifest-blocked",
        wave_name="Wave 8 Recursive Reality-Corrected Learner",
        purpose="Bind bounded recursive learning evidence for review handoff.",
        claim_boundary="Review handoff only; no certification.",
        external_review_packet=packet,
        gates=gates,
        evidence_ids=("manifest-evidence-1",),
    )

    assert not manifest.ready
    assert manifest.decision is Wave8ReleaseDecision.BLOCKED
    assert manifest.blocked_gate_count == 1
    assert any(
        finding.startswith("blocked-release-gates") for finding in manifest.findings
    )


def test_release_manifest_reports_external_review_packet_not_ready() -> None:
    replay_report = validate_replay_packet(
        report_id="replay-report-missing",
        purpose="Validate incomplete replay packet.",
        artifacts=_artifacts()[:2],
    )
    packet = build_external_review_packet(
        packet_id="external-review-packet-not-ready",
        purpose="Package bounded recursive learning evidence for external review.",
        claim_boundary="Bounded recursive learning evidence only; no certification.",
        replay_report=replay_report,
        reviewer_roles=_roles(),
        questions=default_wave8_review_questions(),
        evidence_ids=("packet-evidence-1",),
    )
    gates = default_wave8_release_gates(
        external_review_packet=packet,
        human_authority_evidence_ids=("human-review-evidence-1",),
    )
    manifest = build_wave8_release_manifest(
        manifest_id="wave8-release-manifest-needs-review",
        wave_name="Wave 8 Recursive Reality-Corrected Learner",
        purpose="Bind bounded recursive learning evidence for review handoff.",
        claim_boundary="Review handoff only; no certification.",
        external_review_packet=packet,
        gates=gates,
        evidence_ids=("manifest-evidence-1",),
    )

    assert packet.decision is ExternalReviewPacketDecision.NEEDS_REPLAY_VALIDATION
    assert not manifest.ready
    assert manifest.decision is Wave8ReleaseDecision.BLOCKED
    assert manifest.blocked_gate_count == 2


def test_release_manifest_can_be_ready_with_warning_gate() -> None:
    packet = _external_packet()
    gates = list(
        default_wave8_release_gates(
            external_review_packet=packet,
            human_authority_evidence_ids=("human-review-evidence-1",),
        )
    )
    gates[-1] = ReleaseGateRecord(
        gate_id="gate-no-self-certification",
        kind=ReleaseGateKind.NO_SELF_CERTIFICATION,
        decision=ReleaseGateDecision.WARN,
        summary="No self-certification boundary is present but requires review note.",
        evidence_ids=("warning-evidence-1",),
        findings=("human-review-note-required",),
    )

    manifest = build_wave8_release_manifest(
        manifest_id="wave8-release-manifest-warning",
        wave_name="Wave 8 Recursive Reality-Corrected Learner",
        purpose="Bind bounded recursive learning evidence for review handoff.",
        claim_boundary="Review handoff only; no certification.",
        external_review_packet=packet,
        gates=tuple(gates),
        evidence_ids=("manifest-evidence-1",),
    )

    assert not manifest.ready
    assert manifest.decision is Wave8ReleaseDecision.READY_WITH_WARNINGS
    assert manifest.warning_gate_count == 1
    assert any(
        finding.startswith("warning-release-gates") for finding in manifest.findings
    )


def test_release_manifest_rejects_duplicate_gate_ids() -> None:
    packet = _external_packet()
    gate = ReleaseGateRecord(
        gate_id="duplicate-gate",
        kind=ReleaseGateKind.REPLAY_VALIDATION,
        decision=ReleaseGateDecision.PASS,
        summary="Replay validation gate.",
        evidence_ids=("gate-evidence-1",),
    )

    with pytest.raises(ValueError, match="Duplicate release gate id"):
        Wave8ReleaseManifest(
            manifest_id="manifest-duplicate",
            wave_name="Wave 8 Recursive Reality-Corrected Learner",
            purpose="Bind bounded recursive learning evidence for review handoff.",
            claim_boundary="Review handoff only; no certification.",
            external_review_packet=packet,
            gates=(gate, gate),
            decision=Wave8ReleaseDecision.NEEDS_GATE_EVIDENCE,
            findings=("duplicate-gate",),
            evidence_ids=("manifest-evidence-1",),
        )


def test_release_manifest_rejects_overclaiming_text() -> None:
    packet = _external_packet()
    gates = default_wave8_release_gates(
        external_review_packet=packet,
        human_authority_evidence_ids=("human-review-evidence-1",),
    )

    with pytest.raises(ValueError, match="blocked overclaiming"):
        build_wave8_release_manifest(
            manifest_id="manifest-overclaim",
            wave_name="Wave 8 Recursive Reality-Corrected Learner",
            purpose="This certifies AGI.",
            claim_boundary="Review handoff only; no certification.",
            external_review_packet=packet,
            gates=gates,
            evidence_ids=("manifest-evidence-1",),
        )
