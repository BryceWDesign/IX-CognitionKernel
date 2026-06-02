import pytest
from test_wave3_substrate import ready_substrate

from ix_cognition_kernel.doctrine import ClaimBoundary, wave_by_number
from ix_cognition_kernel.wave3_contracts import (
    WaveThreeArtifactKind,
    WaveThreeAuthorityState,
)
from ix_cognition_kernel.wave3_readiness import (
    WAVE_THREE_REQUIRED_VALIDATION_ARTIFACT_IDS,
    WaveThreeReadinessSnapshot,
    WaveThreeReadinessStatus,
    wave_three_readiness_snapshot,
)
from ix_cognition_kernel.wave3_substrate import WaveThreeSubstrateResult


def ready_snapshot() -> WaveThreeReadinessSnapshot:
    return wave_three_readiness_snapshot(
        substrate_result=ready_substrate(),
        evidence_ids=("readiness-evidence:wave3",),
    )


def test_required_wave_three_validation_artifacts_are_locked() -> None:
    assert WAVE_THREE_REQUIRED_VALIDATION_ARTIFACT_IDS == (
        "engine-coordination-records",
        "25-agent-role-artifacts",
        "multi-agent-tribunal-flow",
        "reward-auditor-records",
        "self-play-curriculum-tasks",
        "evaluator-driven-discovery-records",
        "memory-quarantine-role-integration",
        "skill-genome-update-governance",
        "worldtwin-scenario-reasoning",
        "blackfox-handoff-packages",
        "assurance-style-evidence-records",
        "integrated-wave3-substrate-result",
        "adversarial-wave3-failure-scenarios",
    )


def test_ready_wave_three_snapshot_earns_wave_three_without_overclaim() -> None:
    snapshot = ready_snapshot()

    assert snapshot.project_name == "IX-CognitionKernel"
    assert snapshot.wave_label == "Wave 3 — Governed AGI-Emulation Substrate"
    assert snapshot.status is WaveThreeReadinessStatus.WAVE_THREE_READY
    assert snapshot.is_wave_three_ready is True
    assert snapshot.permits_automatic_execution is False
    assert snapshot.certifies_agi is False
    assert snapshot.permits_agi_claim is False
    assert (
        snapshot.human_authority_state is WaveThreeAuthorityState.HUMAN_REVIEW_REQUIRED
    )
    assert snapshot.readiness_gaps == ()
    assert snapshot.blocking_gaps == ()
    assert "automatic execution and AGI certification are not permitted" in (
        snapshot.review_summary
    )


def test_wave_three_snapshot_reports_substrate_artifact_and_evidence_counts() -> None:
    snapshot = ready_snapshot()

    assert snapshot.substrate_artifact_count > 0
    assert snapshot.substrate_evidence_count > 0
    assert WaveThreeArtifactKind.BLACKFOX_HANDOFF in (
        snapshot.represented_substrate_artifact_kinds
    )
    assert WaveThreeArtifactKind.WORLDTWIN_SCENARIO in (
        snapshot.represented_substrate_artifact_kinds
    )
    assert snapshot.missing_substrate_artifact_kinds == ()


def test_wave_three_snapshot_rejects_wrong_project_or_wave() -> None:
    substrate = ready_substrate()

    with pytest.raises(ValueError, match="IX-CognitionKernel"):
        WaveThreeReadinessSnapshot(
            project_name="WrongProject",
            maturity_wave=wave_by_number(3),
            substrate_result=substrate,
            validation_artifact_ids=WAVE_THREE_REQUIRED_VALIDATION_ARTIFACT_IDS,
            evidence_ids=("evidence",),
        )

    with pytest.raises(ValueError, match="target Wave 3"):
        WaveThreeReadinessSnapshot(
            project_name="IX-CognitionKernel",
            maturity_wave=wave_by_number(2),
            substrate_result=substrate,
            validation_artifact_ids=WAVE_THREE_REQUIRED_VALIDATION_ARTIFACT_IDS,
            evidence_ids=("evidence",),
        )


def test_wave_three_snapshot_requires_validation_artifact_coverage() -> None:
    with pytest.raises(ValueError, match="validation artifact coverage"):
        wave_three_readiness_snapshot(
            substrate_result=ready_substrate(),
            validation_artifact_ids=("engine-coordination-records",),
            evidence_ids=("evidence",),
        )


@pytest.mark.parametrize(
    "duplicate_id",
    [
        "engine-coordination-records",
        "integrated-wave3-substrate-result",
    ],
)
def test_wave_three_snapshot_rejects_duplicate_validation_artifacts(
    duplicate_id: str,
) -> None:
    with pytest.raises(ValueError, match="Duplicate validation_artifact_id"):
        wave_three_readiness_snapshot(
            substrate_result=ready_substrate(),
            validation_artifact_ids=(
                *WAVE_THREE_REQUIRED_VALIDATION_ARTIFACT_IDS,
                duplicate_id,
            ),
            evidence_ids=("evidence",),
        )


def test_wave_three_snapshot_needs_evidence_without_top_level_evidence() -> None:
    snapshot = wave_three_readiness_snapshot(
        substrate_result=ready_substrate(),
        evidence_ids=(),
    )

    assert snapshot.status is WaveThreeReadinessStatus.NEEDS_EVIDENCE
    assert snapshot.is_wave_three_ready is False
    assert "Wave 3 readiness snapshot has no top-level evidence ids" in (
        snapshot.readiness_gaps
    )


def test_wave_three_snapshot_needs_evidence_when_substrate_needs_evidence() -> None:
    source = ready_substrate()
    substrate = WaveThreeSubstrateResult(
        substrate_id="substrate-001",
        coordination_result=source.coordination_result,
        role_artifact_bundle=source.role_artifact_bundle,
        tribunal_record=source.tribunal_record,
        reward_audit=source.reward_audit,
        curriculum_bundle=source.curriculum_bundle,
        discovery_bundle=source.discovery_bundle,
        memory_decision_bundle=source.memory_decision_bundle,
        skill_update_bundle=source.skill_update_bundle,
        worldtwin_bundle=source.worldtwin_bundle,
        blackfox_handoff_bundle=source.blackfox_handoff_bundle,
        assurance_bundle=source.assurance_bundle,
        evidence_ids=(),
    )
    snapshot = wave_three_readiness_snapshot(
        substrate_result=substrate,
        evidence_ids=("readiness-evidence",),
    )

    assert snapshot.status is WaveThreeReadinessStatus.NEEDS_EVIDENCE
    assert snapshot.is_wave_three_ready is False
    assert "integrated Wave 3 substrate still needs evidence" in snapshot.readiness_gaps
    assert "substrate-001 has no top-level evidence ids" in snapshot.readiness_gaps


def test_wave_three_snapshot_artifact_ref_is_readiness_snapshot_kind() -> None:
    artifact = ready_snapshot().to_artifact_ref()

    assert artifact.artifact_id == "readiness-snapshot:wave-3"
    assert artifact.kind is WaveThreeArtifactKind.READINESS_SNAPSHOT
    assert artifact.produced_by_engine_id == "evaluator"
    assert artifact.produced_by_agent_role_id == "verifier"
    assert artifact.allowed_for_automatic_execution is False
    assert artifact.ready_for_human_review is True


def test_wave_three_snapshot_bundle_links_evidence() -> None:
    bundle = ready_snapshot().to_artifact_bundle(
        artifact_bundle_id="readiness-artifacts"
    )

    assert bundle.has_required_kind_coverage is True
    assert bundle.artifact_ids == ("readiness-snapshot:wave-3",)
    assert bundle.ready_for_human_review_artifact_ids == ("readiness-snapshot:wave-3",)
    assert (
        "readiness-evidence:wave3"
        in bundle.evidence_link_table["readiness-snapshot:wave-3"]
    )


def test_wave_three_snapshot_preserves_doctrine_claim_boundary() -> None:
    snapshot = ready_snapshot()

    assert snapshot.maturity_wave.claim_boundary is ClaimBoundary.EMULATION
    assert snapshot.maturity_wave.permitted_claim == (
        "Governed AGI-emulation substrate, not AGI."
    )
    assert snapshot.permits_agi_claim is False
    assert snapshot.certifies_agi is False


def test_wave_three_snapshot_fingerprint_is_deterministic() -> None:
    first = ready_snapshot().fingerprint()
    second = ready_snapshot().fingerprint()

    assert first == second
    assert len(first) == 64
