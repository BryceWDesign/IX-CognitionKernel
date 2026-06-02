import pytest

from ix_cognition_kernel.agents import ArtifactKind, agent_by_id, agent_ids
from ix_cognition_kernel.wave3_agent_artifacts import (
    RoleArtifactAuthority,
    RoleArtifactBundle,
    RoleArtifactRecord,
    RoleArtifactStatus,
    complete_role_artifact_record,
)
from ix_cognition_kernel.wave3_contracts import WaveThreeArtifactKind


def complete_record(role_id: str = "belief-curator") -> RoleArtifactRecord:
    return complete_role_artifact_record(role_id, evidence_ids=(f"evidence:{role_id}",))


def test_complete_role_artifact_uses_locked_agent_registry_contract() -> None:
    role = agent_by_id("belief-curator")
    record = complete_record("belief-curator")

    assert record.role_id == "belief-curator"
    assert record.consumed_input_artifacts == role.required_inputs
    assert record.produced_output_artifacts == role.required_outputs
    assert record.paired_engine_ids == role.paired_engines
    assert record.is_complete is True
    assert record.readiness_gaps == ()
    assert record.authority is RoleArtifactAuthority.MAY_BLOCK_WITH_EVIDENCE


def test_role_artifact_rejects_unknown_role_id() -> None:
    with pytest.raises(ValueError, match="Unknown IX-CognitionKernel agent role id"):
        complete_record("not-a-real-role")


def test_role_artifact_rejects_output_outside_role_registry_contract() -> None:
    with pytest.raises(ValueError, match="Unknown produced_output_artifact"):
        RoleArtifactRecord(
            role_id="belief-curator",
            produced_output_artifacts=(
                ArtifactKind.BELIEF_RECORD,
                ArtifactKind.PLAN_GRAPH,
            ),
            consumed_input_artifacts=(ArtifactKind.PROVENANCE_RECORD,),
            evidence_ids=("evidence:belief-curator",),
            rationale="Invalid output should be rejected.",
        )


def test_role_artifact_rejects_input_outside_role_registry_contract() -> None:
    with pytest.raises(ValueError, match="Unknown consumed_input_artifact"):
        RoleArtifactRecord(
            role_id="belief-curator",
            produced_output_artifacts=(ArtifactKind.BELIEF_RECORD,),
            consumed_input_artifacts=(
                ArtifactKind.PROVENANCE_RECORD,
                ArtifactKind.PLAN_GRAPH,
            ),
            evidence_ids=("evidence:belief-curator",),
            rationale="Invalid input should be rejected.",
        )


def test_role_artifact_rejects_paired_engine_outside_role_registry_contract() -> None:
    with pytest.raises(ValueError, match="Unknown paired_engine_id"):
        RoleArtifactRecord(
            role_id="belief-curator",
            produced_output_artifacts=(ArtifactKind.BELIEF_RECORD,),
            consumed_input_artifacts=(ArtifactKind.PROVENANCE_RECORD,),
            evidence_ids=("evidence:belief-curator",),
            rationale="Invalid paired engine should be rejected.",
            paired_engine_ids=("belief", "evaluator"),
        )


def test_ready_role_artifact_requires_full_coverage() -> None:
    with pytest.raises(ValueError, match="Ready-for-tribunal role artifacts require"):
        RoleArtifactRecord(
            role_id="belief-curator",
            produced_output_artifacts=(ArtifactKind.BELIEF_RECORD,),
            consumed_input_artifacts=(),
            evidence_ids=("evidence:belief-curator",),
            rationale="Missing provenance input blocks readiness.",
            status=RoleArtifactStatus.READY_FOR_TRIBUNAL,
            authority=RoleArtifactAuthority.MAY_BLOCK_WITH_EVIDENCE,
        )


def test_incomplete_role_artifact_reports_precise_readiness_gaps() -> None:
    record = RoleArtifactRecord(
        role_id="belief-curator",
        produced_output_artifacts=(),
        consumed_input_artifacts=(),
        evidence_ids=(),
        rationale="Evidence is missing, so the role cannot enter tribunal readiness.",
    )

    assert record.is_complete is False
    assert (
        "belief-curator missing required inputs: provenance-record"
        in record.readiness_gaps
    )
    assert (
        "belief-curator missing required outputs: belief-record"
        in record.readiness_gaps
    )
    assert "belief-curator has no evidence ids" in record.readiness_gaps


def test_blocked_role_artifact_requires_blocking_reason_and_blocked_authority() -> None:
    with pytest.raises(ValueError, match="Blocked role artifacts require"):
        RoleArtifactRecord(
            role_id="belief-curator",
            produced_output_artifacts=(ArtifactKind.BELIEF_RECORD,),
            consumed_input_artifacts=(ArtifactKind.PROVENANCE_RECORD,),
            evidence_ids=("evidence:belief-curator",),
            rationale="Blocked without a reason is not reviewable.",
            status=RoleArtifactStatus.BLOCKED,
            authority=RoleArtifactAuthority.BLOCKED,
        )

    with pytest.raises(ValueError, match="must carry blocked authority"):
        RoleArtifactRecord(
            role_id="belief-curator",
            produced_output_artifacts=(ArtifactKind.BELIEF_RECORD,),
            consumed_input_artifacts=(ArtifactKind.PROVENANCE_RECORD,),
            evidence_ids=("evidence:belief-curator",),
            rationale="Blocked authority mismatch should fail closed.",
            status=RoleArtifactStatus.BLOCKED,
            authority=RoleArtifactAuthority.REVIEW_ONLY,
            blocking_reasons=("Contradictory provenance requires review.",),
        )


def test_non_blocked_role_artifact_cannot_carry_blocking_reasons() -> None:
    with pytest.raises(ValueError, match="Only blocked role artifacts"):
        RoleArtifactRecord(
            role_id="belief-curator",
            produced_output_artifacts=(ArtifactKind.BELIEF_RECORD,),
            consumed_input_artifacts=(ArtifactKind.PROVENANCE_RECORD,),
            evidence_ids=("evidence:belief-curator",),
            rationale="Non-blocked artifact cannot carry blocked reason.",
            blocking_reasons=("not allowed",),
        )


def test_role_artifact_converts_to_shared_review_artifact_ref() -> None:
    artifact = complete_record("execution-liaison").to_artifact_ref()

    assert artifact.artifact_id == "role-artifact:execution-liaison"
    assert artifact.kind is WaveThreeArtifactKind.ROLE_ARTIFACT
    assert artifact.produced_by_engine_id == "multi-agent-tribunal"
    assert artifact.produced_by_agent_role_id == "execution-liaison"
    assert artifact.allowed_for_automatic_execution is False
    assert artifact.ready_for_human_review is True


def test_role_artifact_fingerprint_is_deterministic() -> None:
    first = complete_record("belief-curator").fingerprint()
    second = complete_record("belief-curator").fingerprint()

    assert first == second
    assert len(first) == 64


def test_role_artifact_bundle_reports_missing_required_roles() -> None:
    bundle = RoleArtifactBundle(
        bundle_id="role-bundle-001",
        records=(complete_record("belief-curator"),),
        required_role_ids=("belief-curator", "verifier"),
    )

    assert bundle.record_role_ids == ("belief-curator",)
    assert bundle.missing_required_role_ids == ("verifier",)
    assert bundle.is_complete_for_required_roles is False
    assert "missing required role artifacts: verifier" in bundle.readiness_gaps


def test_role_artifact_bundle_rejects_duplicate_records() -> None:
    with pytest.raises(ValueError, match="Duplicate role_id"):
        RoleArtifactBundle(
            bundle_id="role-bundle-001",
            records=(
                complete_record("belief-curator"),
                complete_record("belief-curator"),
            ),
        )


def test_role_artifact_bundle_rejects_non_required_role() -> None:
    with pytest.raises(ValueError, match="contains non-required role"):
        RoleArtifactBundle(
            bundle_id="role-bundle-001",
            records=(complete_record("belief-curator"),),
            required_role_ids=("verifier",),
        )


def test_complete_bundle_for_all_25_roles_has_no_readiness_gaps() -> None:
    records = tuple(complete_record(role_id) for role_id in agent_ids())
    bundle = RoleArtifactBundle(bundle_id="role-bundle-001", records=records)

    assert len(agent_ids()) == 25
    assert len(bundle.record_role_ids) == 25
    assert set(bundle.complete_role_ids) == set(agent_ids())
    assert bundle.missing_required_role_ids == ()
    assert bundle.incomplete_role_ids == ()
    assert bundle.blocked_role_ids == ()
    assert bundle.readiness_gaps == ()
    assert bundle.is_complete_for_required_roles is True


def test_role_artifact_bundle_converts_to_shared_artifact_bundle() -> None:
    bundle = RoleArtifactBundle(
        bundle_id="role-bundle-001",
        records=(complete_record("belief-curator"), complete_record("verifier")),
        required_role_ids=("belief-curator", "verifier"),
    )
    artifact_bundle = bundle.to_artifact_bundle(
        artifact_bundle_id="artifact-bundle-roles"
    )

    assert artifact_bundle.has_required_kind_coverage is True
    assert artifact_bundle.artifact_ids == (
        "role-artifact:belief-curator",
        "role-artifact:verifier",
    )
    assert artifact_bundle.ready_for_human_review_artifact_ids == (
        "role-artifact:belief-curator",
        "role-artifact:verifier",
    )
    assert artifact_bundle.evidence_link_table == {
        "role-artifact:belief-curator": ("evidence:belief-curator",),
        "role-artifact:verifier": ("evidence:verifier",),
    }


def test_role_artifact_bundle_fingerprint_is_deterministic_despite_input_order() -> (
    None
):
    first = RoleArtifactBundle(
        bundle_id="role-bundle-001",
        records=(complete_record("verifier"), complete_record("belief-curator")),
        required_role_ids=("belief-curator", "verifier"),
    )
    second = RoleArtifactBundle(
        bundle_id="role-bundle-001",
        records=(complete_record("belief-curator"), complete_record("verifier")),
        required_role_ids=("belief-curator", "verifier"),
    )

    assert first.fingerprint() == second.fingerprint()
    assert len(first.fingerprint()) == 64
