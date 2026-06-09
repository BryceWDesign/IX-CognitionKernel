from __future__ import annotations

import pytest

from ix_cognition_kernel.wave6_contracts import (
    WaveSixArtifactKind,
    WaveSixCapabilityArea,
    WaveSixDecisionState,
    WaveSixLoopStage,
    WaveSixSourceSystem,
)
from ix_cognition_kernel.wave6_donor_evidence_intake import (
    WAVE_SIX_SUPPORTING_DONOR_SOURCE_SYSTEMS,
    WaveSixDonorEvidenceIntakeStatus,
    WaveSixDonorEvidenceReceipt,
    build_wave_six_donor_evidence_intake_bundle,
    supporting_wave_six_donor_source_systems,
)
from ix_cognition_kernel.wave6_donor_profiles import (
    canonical_wave_six_donor_profile_for_source,
)


def _fingerprint(seed: int) -> str:
    return f"{seed:064x}"[-64:]


def _receipt_for_source(
    source_system: WaveSixSourceSystem,
    *,
    seed: int = 1,
) -> WaveSixDonorEvidenceReceipt:
    profile = canonical_wave_six_donor_profile_for_source(source_system)
    assert profile is not None
    return WaveSixDonorEvidenceReceipt(
        receipt_id=f"receipt:{source_system.value}",
        source_system=source_system,
        repo_name=profile.repo_name,
        evidence_id=f"donor-evidence:{source_system.value}:primary",
        artifact_kind=profile.supplied_artifact_kinds[0],
        capability_area=profile.supplied_capability_areas[0],
        loop_stages=(profile.supported_loop_stages[0],),
        artifact_fingerprint=_fingerprint(seed),
        summary=f"{profile.repo_name} supplies bounded donor evidence.",
        produced_by_engine_id=f"{source_system.value}-evidence-engine",
        validation_notes=("metadata-only donor receipt",),
    )


def _all_required_receipts() -> tuple[WaveSixDonorEvidenceReceipt, ...]:
    receipts: list[WaveSixDonorEvidenceReceipt] = []
    seed = 10
    for source_system in WAVE_SIX_SUPPORTING_DONOR_SOURCE_SYSTEMS:
        profile = canonical_wave_six_donor_profile_for_source(source_system)
        assert profile is not None
        for artifact_kind in profile.supplied_artifact_kinds:
            seed += 1
            receipts.append(
                WaveSixDonorEvidenceReceipt(
                    receipt_id=f"receipt:{source_system.value}:{artifact_kind.value}",
                    source_system=source_system,
                    repo_name=profile.repo_name,
                    evidence_id=(
                        f"donor-evidence:{source_system.value}:"
                        f"{artifact_kind.value}"
                    ),
                    artifact_kind=artifact_kind,
                    capability_area=profile.supplied_capability_areas[0],
                    loop_stages=(profile.supported_loop_stages[0],),
                    artifact_fingerprint=_fingerprint(seed),
                    summary=(
                        f"{profile.repo_name} supplies {artifact_kind.value} "
                        "evidence."
                    ),
                    produced_by_engine_id=f"{source_system.value}-evidence-engine",
                )
            )
    return tuple(receipts)


def test_supporting_donor_sources_are_locked_to_expected_six() -> None:
    assert supporting_wave_six_donor_source_systems() == (
        WaveSixSourceSystem.IX_FUNCTION,
        WaveSixSourceSystem.IX_INTENT_REALITY_LOOP,
        WaveSixSourceSystem.IX_BLACKFOX,
        WaveSixSourceSystem.IX_BLACKFOX_COGNITION,
        WaveSixSourceSystem.IX_BLACKFOX_WORLDTWIN,
        WaveSixSourceSystem.IX_AUTONOMY_ASSURANCE_RUNTIME,
    )


def test_donor_evidence_receipt_accepts_metadata_only_supported_source() -> None:
    receipt = _receipt_for_source(WaveSixSourceSystem.IX_FUNCTION)

    assert receipt.profile.repo_name == "IX-Function"
    assert receipt.human_review_required
    assert receipt.metadata_only
    assert not receipt.claims_agi
    assert len(receipt.fingerprint()) == 64
    assert receipt.fingerprint() == receipt.fingerprint()
    assert receipt.canonical_payload()["profile_fingerprint"] == (
        receipt.profile.fingerprint()
    )


def test_donor_evidence_receipt_converts_to_contract_artifact() -> None:
    receipt = _receipt_for_source(WaveSixSourceSystem.IX_INTENT_REALITY_LOOP)
    artifact = receipt.to_contract_artifact()

    assert artifact.artifact_id == "donor-evidence-artifact-receipt:ix-irl"
    assert artifact.source_system is WaveSixSourceSystem.IX_INTENT_REALITY_LOOP
    assert artifact.evidence_ids == (receipt.evidence_id,)
    assert artifact.produced_by_engine_id == "wave6-donor-evidence-intake-engine"
    assert artifact.decision is WaveSixDecisionState.NEEDS_MORE_EVIDENCE


def test_donor_evidence_intake_bundle_reports_missing_coverage() -> None:
    receipt = _receipt_for_source(WaveSixSourceSystem.IX_FUNCTION)
    bundle = build_wave_six_donor_evidence_intake_bundle(
        intake_id="partial-donor-intake",
        receipts=(receipt,),
        notes=("partial intake should remain blocked",),
    )

    assert bundle.status is WaveSixDonorEvidenceIntakeStatus.NEEDS_MORE_DONOR_EVIDENCE
    assert not bundle.ready_for_candidate_assembly
    assert bundle.source_systems_present == (WaveSixSourceSystem.IX_FUNCTION,)
    assert WaveSixSourceSystem.IX_BLACKFOX in bundle.missing_source_systems
    assert bundle.missing_required_artifact_keys
    assert bundle.receipt_for_evidence_id(receipt.evidence_id) == receipt
    assert bundle.receipt_for_evidence_id("missing") is None


def test_donor_evidence_intake_bundle_ready_when_all_required_artifacts_present() -> None:
    bundle = build_wave_six_donor_evidence_intake_bundle(
        intake_id="complete-donor-intake",
        receipts=_all_required_receipts(),
    )

    assert bundle.status is WaveSixDonorEvidenceIntakeStatus.READY_FOR_CANDIDATE_ASSEMBLY
    assert bundle.ready_for_candidate_assembly
    assert bundle.missing_source_systems == ()
    assert bundle.missing_required_artifact_keys == ()
    assert len(bundle.contract_artifacts) == len(_all_required_receipts())
    assert bundle.fingerprint() == bundle.fingerprint()


def test_donor_evidence_intake_bundle_payload_is_deterministic() -> None:
    receipts = tuple(reversed(_all_required_receipts()))
    bundle = build_wave_six_donor_evidence_intake_bundle(
        intake_id="complete-donor-intake",
        receipts=receipts,
    )

    payload = bundle.canonical_payload()

    assert payload["schema_version"] == (
        "ix-cognition-kernel-wave6-donor-evidence-intake-bundle-v1"
    )
    assert payload["status"] == "ready-for-candidate-assembly"
    assert payload["receipt_count"] == len(_all_required_receipts())
    assert payload["receipt_count"] == len(bundle.receipt_ids)
    assert payload["receipt_count"] == len(bundle.evidence_ids)
    assert bundle.receipt_ids == tuple(sorted(bundle.receipt_ids))


def test_donor_evidence_receipt_rejects_wrong_repo_name() -> None:
    profile = canonical_wave_six_donor_profile_for_source(WaveSixSourceSystem.IX_FUNCTION)
    assert profile is not None

    with pytest.raises(ValueError, match="repo name"):
        WaveSixDonorEvidenceReceipt(
            receipt_id="bad-repo",
            source_system=WaveSixSourceSystem.IX_FUNCTION,
            repo_name="WrongRepo",
            evidence_id="donor-evidence:bad-repo",
            artifact_kind=profile.supplied_artifact_kinds[0],
            capability_area=profile.supplied_capability_areas[0],
            loop_stages=(profile.supported_loop_stages[0],),
            artifact_fingerprint=_fingerprint(99),
            summary="Wrong repo name.",
            produced_by_engine_id="engine",
        )


def test_donor_evidence_receipt_rejects_unsupported_source_or_artifact() -> None:
    with pytest.raises(ValueError, match="supporting donor sources"):
        WaveSixDonorEvidenceReceipt(
            receipt_id="ix-main-not-supported",
            source_system=WaveSixSourceSystem.IX_MAIN,
            repo_name="IX",
            evidence_id="donor-evidence:ix-main",
            artifact_kind=WaveSixArtifactKind.MASTER_LOOP_CONTRACT,
            capability_area=WaveSixCapabilityArea.MASTER_LOOP,
            loop_stages=(WaveSixLoopStage.INTENT,),
            artifact_fingerprint=_fingerprint(100),
            summary="IX main is handled by handoff ingestion, not donor intake.",
            produced_by_engine_id="engine",
        )

    with pytest.raises(ValueError, match="artifact kind"):
        WaveSixDonorEvidenceReceipt(
            receipt_id="unsupported-artifact",
            source_system=WaveSixSourceSystem.IX_FUNCTION,
            repo_name="IX-Function",
            evidence_id="donor-evidence:unsupported",
            artifact_kind=WaveSixArtifactKind.BLACKFOX_HANDOFF_RECEIPT,
            capability_area=WaveSixCapabilityArea.TRANSFER_GENERALIZATION,
            loop_stages=(WaveSixLoopStage.TRANSFER_CHECK,),
            artifact_fingerprint=_fingerprint(101),
            summary="Unsupported artifact for IX-Function.",
            produced_by_engine_id="engine",
        )


def test_donor_evidence_receipt_rejects_authority_and_overclaim_flags() -> None:
    with pytest.raises(ValueError, match="must not grant execution"):
        _receipt_for_source(
            WaveSixSourceSystem.IX_BLACKFOX,
            seed=200,
        ).__class__(
            receipt_id="bad-authority",
            source_system=WaveSixSourceSystem.IX_BLACKFOX,
            repo_name="IX-BlackFox",
            evidence_id="donor-evidence:bad-authority",
            artifact_kind=WaveSixArtifactKind.BLACKFOX_HANDOFF_RECEIPT,
            capability_area=WaveSixCapabilityArea.HUMAN_AUTHORITY_PRESERVATION,
            loop_stages=(WaveSixLoopStage.TRIAL,),
            artifact_fingerprint=_fingerprint(201),
            summary="Bad authority receipt.",
            produced_by_engine_id="engine",
            allows_autonomous_execution=True,
        )

    with pytest.raises(ValueError, match="must not claim AGI"):
        _receipt_for_source(
            WaveSixSourceSystem.IX_BLACKFOX_COGNITION,
            seed=300,
        ).__class__(
            receipt_id="bad-agi-claim",
            source_system=WaveSixSourceSystem.IX_BLACKFOX_COGNITION,
            repo_name="IX-BlackFox-Cognition",
            evidence_id="donor-evidence:bad-agi-claim",
            artifact_kind=WaveSixArtifactKind.COGNITION_REVIEW_RECORD,
            capability_area=WaveSixCapabilityArea.HUMAN_AUTHORITY_PRESERVATION,
            loop_stages=(WaveSixLoopStage.HUMAN_REVIEW,),
            artifact_fingerprint=_fingerprint(301),
            summary="Bad AGI claim receipt.",
            produced_by_engine_id="engine",
            claims_agi=True,
        )


def test_donor_evidence_intake_rejects_duplicate_receipts() -> None:
    receipt = _receipt_for_source(WaveSixSourceSystem.IX_FUNCTION)

    with pytest.raises(ValueError, match="Duplicate receipt_id"):
        build_wave_six_donor_evidence_intake_bundle(
            intake_id="duplicate-receipts",
            receipts=(receipt, receipt),
        )


def test_donor_evidence_intake_filters_receipts_by_source() -> None:
    receipt_a = _receipt_for_source(WaveSixSourceSystem.IX_FUNCTION, seed=1)
    receipt_b = _receipt_for_source(
        WaveSixSourceSystem.IX_INTENT_REALITY_LOOP,
        seed=2,
    )
    bundle = build_wave_six_donor_evidence_intake_bundle(
        intake_id="partial-donor-intake",
        receipts=(receipt_b, receipt_a),
    )

    assert bundle.receipts_for_source(WaveSixSourceSystem.IX_FUNCTION) == (receipt_a,)
    assert bundle.receipts_for_source(WaveSixSourceSystem.IX_BLACKFOX) == ()
