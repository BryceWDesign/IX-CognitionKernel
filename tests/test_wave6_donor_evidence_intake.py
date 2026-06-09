from ix_cognition_kernel.wave6_contracts import (
    WaveSixArtifactKind,
    WaveSixDecisionState,
    WaveSixLoopStage,
    WaveSixSourceSystem,
)
from ix_cognition_kernel.wave6_donor_evidence_intake import (
    WAVE_SIX_DONOR_EVIDENCE_INTAKE_ENGINE_ID,
    WaveSixDonorEvidenceIntakeStatus,
    WaveSixDonorEvidenceReceipt,
    build_wave_six_donor_evidence_intake_bundle,
    supporting_wave_six_donor_source_systems,
)
from ix_cognition_kernel.wave6_donor_profiles import (
    canonical_wave_six_donor_profile_for_source,
)

import pytest


def _fingerprint(seed: int) -> str:
    return f"{seed:064x}"[-64:]


def _receipt_for(
    source_system: WaveSixSourceSystem,
    artifact_kind: WaveSixArtifactKind | None = None,
    *,
    seed: int = 1,
    **overrides: object,
) -> WaveSixDonorEvidenceReceipt:
    profile = canonical_wave_six_donor_profile_for_source(source_system)
    assert profile is not None
    selected_artifact = artifact_kind or profile.supplied_artifact_kinds[0]
    payload = {
        "receipt_id": f"receipt-{source_system.value}-{selected_artifact.value}",
        "source_system": source_system,
        "repo_name": profile.repo_name,
        "evidence_id": (
            f"donor-evidence:{source_system.value}:{selected_artifact.value}"
        ),
        "artifact_kind": selected_artifact,
        "capability_area": profile.supplied_capability_areas[0],
        "loop_stages": (profile.supported_loop_stages[0],),
        "artifact_fingerprint": _fingerprint(seed),
        "summary": f"Metadata-only evidence receipt for {profile.repo_name}.",
        "produced_by_engine_id": f"{source_system.value}-evidence-exporter",
    }
    payload.update(overrides)
    return WaveSixDonorEvidenceReceipt(**payload)


def _full_receipts() -> tuple[WaveSixDonorEvidenceReceipt, ...]:
    receipts: list[WaveSixDonorEvidenceReceipt] = []
    seed = 1
    for source_system in supporting_wave_six_donor_source_systems():
        profile = canonical_wave_six_donor_profile_for_source(source_system)
        assert profile is not None
        for artifact_kind in profile.supplied_artifact_kinds:
            receipts.append(
                _receipt_for(source_system, artifact_kind, seed=seed)
            )
            seed += 1
    return tuple(receipts)


def test_donor_evidence_intake_accepts_complete_supporting_receipts() -> None:
    bundle = build_wave_six_donor_evidence_intake_bundle(
        intake_id="wave6-supporting-donor-intake",
        receipts=_full_receipts(),
        notes=("Metadata-only donor evidence intake for Wave 6 review.",),
    )

    assert bundle.source_systems_present == supporting_wave_six_donor_source_systems()
    assert bundle.missing_source_systems == ()
    assert bundle.missing_required_artifact_keys == ()
    assert bundle.status is (
        WaveSixDonorEvidenceIntakeStatus.READY_FOR_CANDIDATE_ASSEMBLY
    )
    assert bundle.ready_for_candidate_assembly
    assert len(bundle.contract_artifacts) == len(bundle.receipts)
    assert len(bundle.fingerprint()) == 64
    assert bundle.fingerprint() == bundle.fingerprint()


def test_donor_evidence_intake_reports_missing_supporting_sources() -> None:
    bundle = build_wave_six_donor_evidence_intake_bundle(
        intake_id="partial-donor-intake",
        receipts=(
            _receipt_for(
                WaveSixSourceSystem.IX_FUNCTION,
                seed=101,
            ),
        ),
    )

    assert bundle.status is WaveSixDonorEvidenceIntakeStatus.NEEDS_MORE_DONOR_EVIDENCE
    assert not bundle.ready_for_candidate_assembly
    assert bundle.source_systems_present == (WaveSixSourceSystem.IX_FUNCTION,)
    assert WaveSixSourceSystem.IX_BLACKFOX in bundle.missing_source_systems
    assert "ix-function:falsification-record" in bundle.missing_required_artifact_keys
    assert "ix-blackfox:human-review-docket" in bundle.missing_required_artifact_keys


def test_donor_evidence_receipt_converts_to_bounded_contract_artifact() -> None:
    receipt = _receipt_for(WaveSixSourceSystem.IX_BLACKFOX, seed=202)

    artifact = receipt.to_contract_artifact()

    assert artifact.artifact_id == f"donor-evidence-artifact-{receipt.receipt_id}"
    assert artifact.kind is receipt.artifact_kind
    assert artifact.source_system is WaveSixSourceSystem.IX_BLACKFOX
    assert artifact.loop_stages == receipt.loop_stages
    assert artifact.evidence_ids == (receipt.evidence_id,)
    assert artifact.produced_by_engine_id == WAVE_SIX_DONOR_EVIDENCE_INTAKE_ENGINE_ID
    assert artifact.decision is WaveSixDecisionState.NEEDS_MORE_EVIDENCE
    assert not artifact.allows_autonomous_execution
    assert not artifact.claims_agi
    assert not artifact.self_validated


def test_donor_evidence_intake_rejects_ix_main_as_supporting_donor() -> None:
    with pytest.raises(ValueError, match="supporting donor sources"):
        _receipt_for(WaveSixSourceSystem.IX_MAIN, seed=303)


def test_donor_evidence_intake_rejects_repo_name_mismatch() -> None:
    with pytest.raises(ValueError, match="repo name must match"):
        _receipt_for(
            WaveSixSourceSystem.IX_FUNCTION,
            repo_name="Wrong-Repo",
            seed=404,
        )


def test_donor_evidence_intake_rejects_unsupported_artifact_kind() -> None:
    with pytest.raises(ValueError, match="artifact kind is not supplied"):
        _receipt_for(
            WaveSixSourceSystem.IX_FUNCTION,
            WaveSixArtifactKind.HUMAN_REVIEW_DOCKET,
            seed=505,
        )


def test_donor_evidence_intake_rejects_unsupported_loop_stage() -> None:
    with pytest.raises(ValueError, match="loop stage is not supported"):
        _receipt_for(
            WaveSixSourceSystem.IX_FUNCTION,
            loop_stages=(WaveSixLoopStage.INTENT,),
            seed=606,
        )


def test_donor_evidence_intake_rejects_authority_and_overclaims() -> None:
    with pytest.raises(ValueError, match="must not grant execution"):
        _receipt_for(
            WaveSixSourceSystem.IX_BLACKFOX,
            allows_autonomous_execution=True,
            seed=707,
        )
    with pytest.raises(ValueError, match="must not claim AGI"):
        _receipt_for(
            WaveSixSourceSystem.IX_BLACKFOX_COGNITION,
            claims_agi=True,
            seed=708,
        )
    with pytest.raises(ValueError, match="must require human review"):
        _receipt_for(
            WaveSixSourceSystem.IX_BLACKFOX_WORLDTWIN,
            human_review_required=False,
            seed=709,
        )


def test_donor_evidence_intake_rejects_duplicate_evidence_ids() -> None:
    first = _receipt_for(WaveSixSourceSystem.IX_FUNCTION, seed=808)
    second = _receipt_for(
        WaveSixSourceSystem.IX_INTENT_REALITY_LOOP,
        evidence_id=first.evidence_id,
        seed=809,
    )

    with pytest.raises(ValueError, match="Duplicate evidence_id"):
        build_wave_six_donor_evidence_intake_bundle(
            intake_id="duplicate-evidence",
            receipts=(first, second),
        )


def test_donor_evidence_intake_can_lookup_receipts() -> None:
    bundle = build_wave_six_donor_evidence_intake_bundle(
        intake_id="lookup-intake",
        receipts=_full_receipts(),
    )

    receipt = bundle.receipt_for_evidence_id(
        "donor-evidence:ix-function:transfer-novelty-record"
    )

    assert receipt is not None
    assert receipt.source_system is WaveSixSourceSystem.IX_FUNCTION
    assert bundle.receipts_for_source(WaveSixSourceSystem.IX_BLACKFOX)
