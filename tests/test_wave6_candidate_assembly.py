from __future__ import annotations

from dataclasses import dataclass
from typing import Any, cast

import pytest

from ix_cognition_kernel.wave6_candidate_assembly import (
    WaveSixCandidateAssembly,
    WaveSixCandidateAssemblyBlocker,
    WaveSixCandidateAssemblyStatus,
    build_wave_six_candidate_assembly,
)
from ix_cognition_kernel.wave6_contracts import WaveSixSourceSystem
from ix_cognition_kernel.wave6_donor_evidence_intake import (
    WAVE_SIX_SUPPORTING_DONOR_SOURCE_SYSTEMS,
    WaveSixDonorEvidenceIntakeBundle,
    WaveSixDonorEvidenceReceipt,
    build_wave_six_donor_evidence_intake_bundle,
)
from ix_cognition_kernel.wave6_donor_profiles import (
    canonical_wave_six_donor_profile_for_source,
)
from ix_cognition_kernel.wave6_ix_handoff import (
    CANONICAL_IX_COGNITION_OBLIGATIONS,
    WaveSixIxHandoffPackage,
    load_ix_cognition_handoff,
)
from ix_cognition_kernel.wave6_ix_obligation_pressure import (
    WaveSixIxObligationPressureBundle,
    build_ix_obligation_pressure_bundle,
)


def _fingerprint(seed: int) -> str:
    return f"{seed:064x}"[-64:]


def _canonical_ix_payload() -> dict[str, Any]:
    obligations = []
    for index, definition in enumerate(CANONICAL_IX_COGNITION_OBLIGATIONS, start=1):
        obligations.append(
            {
                "canonical": True,
                "canonical_definition": definition.canonical_payload(),
                "evidence_required": list(definition.evidence_artifacts),
                "falsify_if": list(definition.falsification_conditions),
                "id": definition.obligation_id,
                "source": {
                    "column": 1,
                    "filename": "kernel_contract.ix",
                    "line": index,
                },
            }
        )
    return {
        "handoff_type": "ix.cognitionkernel.handoff",
        "packages": [
            {
                "attempt": "wave6_measured_cognition",
                "claim_boundaries": [
                    "measured system-level cognition only",
                    "not an AGI claim",
                    "human and independent review required",
                ],
                "execution_authority": "none",
                "human_approval_required": ["human authority required"],
                "human_authority_required": True,
                "non_goals": ["do not claim AGI", "do not self-certify"],
                "obligations": obligations,
                "purpose": ["test measured system-level cognition"],
                "runtime_semantics": "metadata_only_not_executed",
                "schema": "ix.cognition.contract.v1",
                "self_certification_allowed": False,
                "source": {
                    "column": 1,
                    "filename": "kernel_contract.ix",
                    "line": 1,
                },
                "target": "IX-CognitionKernel",
            }
        ],
        "runtime_semantics": "metadata_only_not_executed",
        "schema_version": "1.0",
    }


def _ix_package() -> WaveSixIxHandoffPackage:
    return load_ix_cognition_handoff(_canonical_ix_payload()).packages[0]


def _donor_receipts() -> tuple[WaveSixDonorEvidenceReceipt, ...]:
    receipts: list[WaveSixDonorEvidenceReceipt] = []
    seed = 100
    for source_system in WAVE_SIX_SUPPORTING_DONOR_SOURCE_SYSTEMS:
        profile = canonical_wave_six_donor_profile_for_source(source_system)
        assert profile is not None
        for artifact_kind in profile.supplied_artifact_kinds:
            seed += 1
            receipts.append(
                WaveSixDonorEvidenceReceipt(
                    receipt_id=f"{source_system.value}:{artifact_kind.value}",
                    source_system=source_system,
                    repo_name=profile.repo_name,
                    evidence_id=f"donor-evidence:{source_system.value}:{artifact_kind.value}",
                    artifact_kind=artifact_kind,
                    capability_area=profile.supplied_capability_areas[0],
                    loop_stages=(profile.supported_loop_stages[0],),
                    artifact_fingerprint=_fingerprint(seed),
                    summary=f"{profile.repo_name} supplies {artifact_kind.value}.",
                    produced_by_engine_id=f"{source_system.value}-evidence-engine",
                )
            )
    return tuple(receipts)


def _complete_donor_intake() -> WaveSixDonorEvidenceIntakeBundle:
    return build_wave_six_donor_evidence_intake_bundle(
        intake_id="complete-donor-intake",
        receipts=_donor_receipts(),
    )


@dataclass(frozen=True, slots=True)
class _ReadyPressureBundle:
    attempt: str
    source_package_fingerprint: str
    source_evidence_id: str
    contract_artifact_id: str
    evidence_gap_ids: tuple[str, ...] = ()
    falsification_probe_ids: tuple[str, ...] = ("probe:ready",)
    blocking_gap_ids: tuple[str, ...] = ()
    required_evidence_ids: tuple[str, ...] = ("ready-evidence",)

    def fingerprint(self) -> str:
        return _fingerprint(900)

    def canonical_payload(self) -> dict[str, Any]:
        return {
            "attempt": self.attempt,
            "blocking_gap_ids": list(self.blocking_gap_ids),
            "contract_artifact_id": self.contract_artifact_id,
            "evidence_gap_ids": list(self.evidence_gap_ids),
            "falsification_probe_ids": list(self.falsification_probe_ids),
            "required_evidence_ids": list(self.required_evidence_ids),
            "source_evidence_id": self.source_evidence_id,
            "source_package_fingerprint": self.source_package_fingerprint,
        }


def _ready_pressure_bundle(
    package: WaveSixIxHandoffPackage,
) -> WaveSixIxObligationPressureBundle:
    contract_artifact = package.to_contract_artifact()
    return cast(
        WaveSixIxObligationPressureBundle,
        _ReadyPressureBundle(
            attempt=package.attempt,
            source_package_fingerprint=package.fingerprint(),
            source_evidence_id=package.ix_evidence_id,
            contract_artifact_id=contract_artifact.artifact_id,
        ),
    )


def test_candidate_assembly_blocks_unresolved_ix_obligation_pressure() -> None:
    package = _ix_package()
    assembly = build_wave_six_candidate_assembly(
        assembly_id="candidate-assembly",
        ix_package=package,
        ix_pressure_bundle=build_ix_obligation_pressure_bundle(package),
        donor_intake_bundle=_complete_donor_intake(),
        notes=("Bounded assembly only.",),
    )

    assert (
        assembly.status
        is WaveSixCandidateAssemblyStatus.BLOCKED_BY_IX_OBLIGATION_PRESSURE
    )
    assert not assembly.ready_for_fail_closed_readiness_gate
    assert assembly.readiness_blockers == (
        WaveSixCandidateAssemblyBlocker.IX_OBLIGATION_GAPS_BLOCKING,
    )
    assert assembly.attempt == "wave6_measured_cognition"
    assert assembly.human_review_required
    assert assembly.metadata_only
    assert not assembly.claims_agi


def test_candidate_assembly_preserves_artifacts_and_evidence_ids() -> None:
    package = _ix_package()
    assembly = build_wave_six_candidate_assembly(
        assembly_id="candidate-assembly",
        ix_package=package,
        ix_pressure_bundle=build_ix_obligation_pressure_bundle(package),
        donor_intake_bundle=_complete_donor_intake(),
    )

    assert assembly.ix_contract_artifact.artifact_id == (
        "ix-handoff-artifact-wave6_measured_cognition"
    )
    assert assembly.artifact_ids[0] == assembly.ix_contract_artifact.artifact_id
    assert package.ix_evidence_id in assembly.evidence_ids
    assert len(assembly.donor_contract_artifacts) == len(_donor_receipts())
    assert len(assembly.fingerprint()) == 64
    assert assembly.fingerprint() == assembly.fingerprint()


def test_candidate_assembly_payload_is_deterministic_and_review_bounded() -> None:
    package = _ix_package()
    assembly = build_wave_six_candidate_assembly(
        assembly_id="candidate-assembly",
        ix_package=package,
        ix_pressure_bundle=build_ix_obligation_pressure_bundle(package),
        donor_intake_bundle=_complete_donor_intake(),
    )

    payload = assembly.canonical_payload()

    assert payload["schema_version"] == (
        "ix-cognition-kernel-wave6-candidate-assembly-v1"
    )
    assert payload["status"] == "blocked-by-ix-obligation-pressure"
    assert payload["ready_for_fail_closed_readiness_gate"] is False
    assert payload["claims_agi"] is False
    assert payload["allows_autonomous_execution"] is False
    assert payload["self_validated"] is False
    assert payload["ix_handoff_fingerprint"] == package.fingerprint()


def test_candidate_assembly_moves_to_donor_evidence_status_when_ix_ready() -> None:
    package = _ix_package()
    partial_intake = build_wave_six_donor_evidence_intake_bundle(
        intake_id="partial-donor-intake",
        receipts=(_donor_receipts()[0],),
    )
    assembly = build_wave_six_candidate_assembly(
        assembly_id="candidate-assembly",
        ix_package=package,
        ix_pressure_bundle=_ready_pressure_bundle(package),
        donor_intake_bundle=partial_intake,
    )

    assert assembly.status is WaveSixCandidateAssemblyStatus.NEEDS_DONOR_EVIDENCE
    assert assembly.readiness_blockers == (
        WaveSixCandidateAssemblyBlocker.DONOR_SOURCE_EVIDENCE_MISSING,
        WaveSixCandidateAssemblyBlocker.DONOR_ARTIFACT_EVIDENCE_MISSING,
    )


def test_candidate_assembly_can_enter_later_gate_when_inputs_are_ready() -> None:
    package = _ix_package()
    assembly = build_wave_six_candidate_assembly(
        assembly_id="candidate-assembly",
        ix_package=package,
        ix_pressure_bundle=_ready_pressure_bundle(package),
        donor_intake_bundle=_complete_donor_intake(),
    )

    assert (
        assembly.status
        is WaveSixCandidateAssemblyStatus.READY_FOR_FAIL_CLOSED_READINESS_GATE
    )
    assert assembly.ready_for_fail_closed_readiness_gate
    assert assembly.readiness_blockers == ()


def test_candidate_assembly_rejects_authority_and_overclaim_flags() -> None:
    package = _ix_package()

    with pytest.raises(ValueError, match="must not grant execution"):
        WaveSixCandidateAssembly(
            assembly_id="candidate-assembly",
            ix_package=package,
            ix_pressure_bundle=build_ix_obligation_pressure_bundle(package),
            donor_intake_bundle=_complete_donor_intake(),
            allows_autonomous_execution=True,
        )
    with pytest.raises(ValueError, match="must not claim AGI"):
        WaveSixCandidateAssembly(
            assembly_id="candidate-assembly",
            ix_package=package,
            ix_pressure_bundle=build_ix_obligation_pressure_bundle(package),
            donor_intake_bundle=_complete_donor_intake(),
            claims_agi=True,
        )
    with pytest.raises(ValueError, match="must not self-validate"):
        WaveSixCandidateAssembly(
            assembly_id="candidate-assembly",
            ix_package=package,
            ix_pressure_bundle=build_ix_obligation_pressure_bundle(package),
            donor_intake_bundle=_complete_donor_intake(),
            self_validated=True,
        )


def test_candidate_assembly_rejects_ix_pressure_linkage_mismatch() -> None:
    package = _ix_package()
    bad_pressure = cast(
        WaveSixIxObligationPressureBundle,
        _ReadyPressureBundle(
            attempt="wrong-attempt",
            source_package_fingerprint=package.fingerprint(),
            source_evidence_id=package.ix_evidence_id,
            contract_artifact_id=package.to_contract_artifact().artifact_id,
        ),
    )

    with pytest.raises(ValueError, match="ix-pressure-attempt-mismatch"):
        build_wave_six_candidate_assembly(
            assembly_id="candidate-assembly",
            ix_package=package,
            ix_pressure_bundle=bad_pressure,
            donor_intake_bundle=_complete_donor_intake(),
        )


def test_candidate_assembly_rejects_unknown_required_donor_source() -> None:
    with pytest.raises(ValueError, match="supporting donors"):
        build_wave_six_donor_evidence_intake_bundle(
            intake_id="bad-donor-intake",
            receipts=(_donor_receipts()[0],),
        ).__class__(
            intake_id="bad-donor-intake",
            receipts=(_donor_receipts()[0],),
            required_source_systems=(WaveSixSourceSystem.IX_MAIN,),
        )
