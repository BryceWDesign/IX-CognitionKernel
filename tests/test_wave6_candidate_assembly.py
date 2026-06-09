from typing import Any

import pytest

from ix_cognition_kernel.wave6_candidate_assembly import (
    WaveSixCandidateAssembly,
    WaveSixCandidateAssemblyBlocker,
    WaveSixCandidateAssemblyStatus,
    build_wave_six_candidate_assembly,
)
from ix_cognition_kernel.wave6_contracts import (
    WaveSixArtifactKind,
    WaveSixSourceSystem,
)
from ix_cognition_kernel.wave6_donor_evidence_intake import (
    WaveSixDonorEvidenceReceipt,
    build_wave_six_donor_evidence_intake_bundle,
    supporting_wave_six_donor_source_systems,
)
from ix_cognition_kernel.wave6_donor_profiles import (
    canonical_wave_six_donor_profile_for_source,
)
from ix_cognition_kernel.wave6_ix_handoff import (
    CANONICAL_IX_COGNITION_OBLIGATIONS,
    IX_COGNITION_CONTRACT_SCHEMA,
    IX_COGNITION_KERNEL_TARGET,
    IX_KERNEL_HANDOFF_TYPE,
    IX_KERNEL_HANDOFF_PAYLOAD_SCHEMA_VERSION,
    IX_METADATA_ONLY_RUNTIME_SEMANTICS,
    canonical_ix_cognition_obligation_ids,
    load_ix_cognition_handoff,
)
from ix_cognition_kernel.wave6_ix_obligation_pressure import (
    WaveSixIxObligationPressureBundle,
    build_ix_obligation_pressure_bundle,
)


def _source(line: int = 1) -> dict[str, Any]:
    return {
        "column": 5,
        "filename": "examples/cognitionkernel_wave6_contract.ix",
        "line": line,
    }


def _obligation_payload(index: int, obligation_id: str) -> dict[str, Any]:
    definition = next(
        definition
        for definition in CANONICAL_IX_COGNITION_OBLIGATIONS
        if definition.obligation_id == obligation_id
    )
    return {
        "canonical": True,
        "canonical_definition": definition.canonical_payload(),
        "evidence_required": [definition.evidence_artifacts[0]],
        "falsify_if": [definition.falsification_conditions[0]],
        "id": obligation_id,
        "source": _source(line=8 + (index * 5)),
    }


def _canonical_payload() -> dict[str, Any]:
    return {
        "handoff_type": IX_KERNEL_HANDOFF_TYPE,
        "packages": [
            {
                "attempt": "wave6_measured_cognition",
                "claim_boundaries": [
                    "Research candidate only, evaluation use only, not deployment",
                ],
                "execution_authority": "none",
                "human_approval_required": [
                    "Human review required before any advancement or public claim",
                ],
                "human_authority_required": True,
                "non_goals": [
                    "Do not claim AGI, certify AGI, or allow system self-approval",
                ],
                "obligations": [
                    _obligation_payload(index, obligation_id)
                    for index, obligation_id in enumerate(
                        canonical_ix_cognition_obligation_ids()
                    )
                ],
                "purpose": [
                    "Define a governed IX-CognitionKernel Wave 6 contract for "
                    "measured reality correction",
                ],
                "runtime_semantics": IX_METADATA_ONLY_RUNTIME_SEMANTICS,
                "schema": IX_COGNITION_CONTRACT_SCHEMA,
                "self_certification_allowed": False,
                "source": _source(line=6),
                "target": IX_COGNITION_KERNEL_TARGET,
            }
        ],
        "runtime_semantics": IX_METADATA_ONLY_RUNTIME_SEMANTICS,
        "schema_version": IX_KERNEL_HANDOFF_PAYLOAD_SCHEMA_VERSION,
    }


def _fingerprint(seed: int) -> str:
    return f"{seed:064x}"[-64:]


def _receipt_for(
    source_system: WaveSixSourceSystem,
    artifact_kind: WaveSixArtifactKind | None = None,
    *,
    seed: int = 1,
) -> WaveSixDonorEvidenceReceipt:
    profile = canonical_wave_six_donor_profile_for_source(source_system)
    assert profile is not None
    selected_artifact = artifact_kind or profile.supplied_artifact_kinds[0]
    return WaveSixDonorEvidenceReceipt(
        receipt_id=f"receipt-{source_system.value}-{selected_artifact.value}",
        source_system=source_system,
        repo_name=profile.repo_name,
        evidence_id=f"donor-evidence:{source_system.value}:{selected_artifact.value}",
        artifact_kind=selected_artifact,
        capability_area=profile.supplied_capability_areas[0],
        loop_stages=(profile.supported_loop_stages[0],),
        artifact_fingerprint=_fingerprint(seed),
        summary=f"Metadata-only evidence receipt for {profile.repo_name}.",
        produced_by_engine_id=f"{source_system.value}-evidence-exporter",
    )


def _full_receipts() -> tuple[WaveSixDonorEvidenceReceipt, ...]:
    receipts: list[WaveSixDonorEvidenceReceipt] = []
    seed = 1
    for source_system in supporting_wave_six_donor_source_systems():
        profile = canonical_wave_six_donor_profile_for_source(source_system)
        assert profile is not None
        for artifact_kind in profile.supplied_artifact_kinds:
            receipts.append(_receipt_for(source_system, artifact_kind, seed=seed))
            seed += 1
    return tuple(receipts)


def _candidate_assembly(receipts: tuple[WaveSixDonorEvidenceReceipt, ...]) -> (
    WaveSixCandidateAssembly
):
    package = load_ix_cognition_handoff(_canonical_payload()).packages[0]
    pressure_bundle = build_ix_obligation_pressure_bundle(package)
    donor_bundle = build_wave_six_donor_evidence_intake_bundle(
        intake_id="wave6-donor-intake",
        receipts=receipts,
    )
    return build_wave_six_candidate_assembly(
        assembly_id="wave6-bounded-candidate-assembly",
        ix_package=package,
        ix_pressure_bundle=pressure_bundle,
        donor_intake_bundle=donor_bundle,
        notes=("Candidate assembly only; unresolved IX obligations block review.",),
    )


def test_candidate_assembly_joins_ix_pressure_and_complete_donor_intake() -> None:
    assembly = _candidate_assembly(_full_receipts())

    assert assembly.attempt == "wave6_measured_cognition"
    assert assembly.ix_contract_artifact.artifact_id == (
        "ix-handoff-artifact-wave6_measured_cognition"
    )
    assert assembly.donor_intake_bundle.ready_for_candidate_assembly
    assert assembly.status is (
        WaveSixCandidateAssemblyStatus.BLOCKED_BY_IX_OBLIGATION_PRESSURE
    )
    assert not assembly.ready_for_fail_closed_readiness_gate
    assert assembly.readiness_blockers == (
        WaveSixCandidateAssemblyBlocker.IX_OBLIGATION_GAPS_BLOCKING,
    )
    assert len(assembly.ix_obligation_gap_ids) == len(
        canonical_ix_cognition_obligation_ids()
    )
    assert len(assembly.ix_falsification_probe_ids) == len(
        canonical_ix_cognition_obligation_ids()
    )
    assert assembly.evidence_ids[0] == (
        "ix-kernel-handoff:wave6_measured_cognition:kernel-handoff-json"
    )
    assert len(assembly.fingerprint()) == 64
    assert assembly.fingerprint() == assembly.fingerprint()


def test_candidate_assembly_reports_donor_gaps_but_keeps_ix_pressure_primary() -> None:
    assembly = _candidate_assembly(
        (_receipt_for(WaveSixSourceSystem.IX_FUNCTION, seed=101),)
    )

    assert assembly.status is (
        WaveSixCandidateAssemblyStatus.BLOCKED_BY_IX_OBLIGATION_PRESSURE
    )
    assert assembly.readiness_blockers == (
        WaveSixCandidateAssemblyBlocker.IX_OBLIGATION_GAPS_BLOCKING,
        WaveSixCandidateAssemblyBlocker.DONOR_SOURCE_EVIDENCE_MISSING,
        WaveSixCandidateAssemblyBlocker.DONOR_ARTIFACT_EVIDENCE_MISSING,
    )
    assert WaveSixSourceSystem.IX_BLACKFOX in (
        assembly.donor_intake_bundle.missing_source_systems
    )


def test_candidate_assembly_preserves_no_authority_and_no_agi_boundaries() -> None:
    assembly = _candidate_assembly(_full_receipts())

    assert assembly.human_review_required
    assert assembly.metadata_only
    assert not assembly.allows_autonomous_execution
    assert not assembly.claims_agi
    assert not assembly.claims_production_ready
    assert not assembly.claims_certified
    assert not assembly.self_validated
    assert all(not artifact.claims_agi for artifact in assembly.all_contract_artifacts)
    assert all(
        not artifact.allows_autonomous_execution
        for artifact in assembly.all_contract_artifacts
    )


def test_candidate_assembly_rejects_attempt_mismatch() -> None:
    package = load_ix_cognition_handoff(_canonical_payload()).packages[0]
    pressure_bundle = build_ix_obligation_pressure_bundle(package)
    tampered_pressure = WaveSixIxObligationPressureBundle(
        attempt="different_attempt",
        source_package_fingerprint=pressure_bundle.source_package_fingerprint,
        source_evidence_id=pressure_bundle.source_evidence_id,
        contract_artifact_id=pressure_bundle.contract_artifact_id,
        pressures=pressure_bundle.pressures,
    )
    donor_bundle = build_wave_six_donor_evidence_intake_bundle(
        intake_id="wave6-donor-intake",
        receipts=_full_receipts(),
    )

    with pytest.raises(ValueError, match="ix-pressure-attempt-mismatch"):
        build_wave_six_candidate_assembly(
            assembly_id="bad-assembly",
            ix_package=package,
            ix_pressure_bundle=tampered_pressure,
            donor_intake_bundle=donor_bundle,
        )


def test_candidate_assembly_rejects_fingerprint_mismatch() -> None:
    package = load_ix_cognition_handoff(_canonical_payload()).packages[0]
    pressure_bundle = build_ix_obligation_pressure_bundle(package)
    tampered_pressure = WaveSixIxObligationPressureBundle(
        attempt=pressure_bundle.attempt,
        source_package_fingerprint=f"{999:064x}"[-64:],
        source_evidence_id=pressure_bundle.source_evidence_id,
        contract_artifact_id=pressure_bundle.contract_artifact_id,
        pressures=pressure_bundle.pressures,
    )
    donor_bundle = build_wave_six_donor_evidence_intake_bundle(
        intake_id="wave6-donor-intake",
        receipts=_full_receipts(),
    )

    with pytest.raises(ValueError, match="ix-pressure-fingerprint-mismatch"):
        build_wave_six_candidate_assembly(
            assembly_id="bad-assembly",
            ix_package=package,
            ix_pressure_bundle=tampered_pressure,
            donor_intake_bundle=donor_bundle,
        )


def test_candidate_assembly_rejects_unsafe_claim_flags() -> None:
    package = load_ix_cognition_handoff(_canonical_payload()).packages[0]
    pressure_bundle = build_ix_obligation_pressure_bundle(package)
    donor_bundle = build_wave_six_donor_evidence_intake_bundle(
        intake_id="wave6-donor-intake",
        receipts=_full_receipts(),
    )

    with pytest.raises(ValueError, match="must not claim AGI"):
        WaveSixCandidateAssembly(
            assembly_id="unsafe-assembly",
            ix_package=package,
            ix_pressure_bundle=pressure_bundle,
            donor_intake_bundle=donor_bundle,
            claims_agi=True,
        )


def test_candidate_assembly_keeps_artifacts_and_evidence_deterministic() -> None:
    assembly = _candidate_assembly(_full_receipts())

    assert assembly.artifact_ids[0] == "ix-handoff-artifact-wave6_measured_cognition"
    assert assembly.artifact_ids == tuple(
        artifact.artifact_id for artifact in assembly.all_contract_artifacts
    )
    assert len(assembly.artifact_ids) == len(_full_receipts()) + 1
    assert all(probe.evidence_ids for probe in assembly.ix_falsification_probes)
    assert assembly.canonical_payload()["status"] == (
        "blocked-by-ix-obligation-pressure"
    )
