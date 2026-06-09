from dataclasses import dataclass
from typing import Any

from ix_cognition_kernel.wave6_candidate_assembly import (
    WaveSixCandidateAssembly,
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
from ix_cognition_kernel.wave6_fail_closed_candidate_gate import (
    WaveSixFailClosedCandidateGate,
    WaveSixFailClosedCandidateGateBlocker,
    WaveSixFailClosedCandidateGateDecision,
    WaveSixFailClosedCandidateGateStatus,
    build_wave_six_fail_closed_candidate_gate,
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
    build_ix_obligation_pressure_bundle,
)


CLAIM_BOUNDARY = (
    "This is measured system-level cognition evidence, not an AGI claim. "
    "Human authority and independent review are required, with no autonomous "
    "execution."
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
    )


@dataclass(frozen=True, slots=True)
class _ReadyDonorIntake:
    missing_source_systems: tuple[Any, ...] = ()
    missing_required_artifact_keys: tuple[str, ...] = ()

    def fingerprint(self) -> str:
        return _fingerprint(777)


@dataclass(frozen=True, slots=True)
class _ReadyAssembly:
    attempt: str = "ready_attempt"
    readiness_blockers: tuple[Any, ...] = ()
    ready_for_fail_closed_readiness_gate: bool = True
    evidence_ids: tuple[str, ...] = ("evidence:ready",)
    ix_obligation_gap_ids: tuple[str, ...] = ()
    ix_falsification_probe_ids: tuple[str, ...] = ("probe:ready",)
    donor_intake_bundle: _ReadyDonorIntake = _ReadyDonorIntake()
    human_review_required: bool = True
    metadata_only: bool = True
    allows_autonomous_execution: bool = False
    claims_agi: bool = False
    claims_production_ready: bool = False
    claims_certified: bool = False
    self_validated: bool = False

    def fingerprint(self) -> str:
        return _fingerprint(888)


def test_fail_closed_gate_blocks_real_assembly_with_open_ix_obligations() -> None:
    assembly = _candidate_assembly(_full_receipts())

    gate = build_wave_six_fail_closed_candidate_gate(
        gate_id="wave6-candidate-gate",
        candidate_assembly=assembly,
        claim_boundary_statement=CLAIM_BOUNDARY,
        human_authority_id="human-reviewer-1",
        independent_reviewer_id="independent-reviewer-1",
    )

    assert gate.status is WaveSixFailClosedCandidateGateStatus.NEEDS_MORE_EVIDENCE
    assert gate.decision is (
        WaveSixFailClosedCandidateGateDecision.CONTINUE_EVIDENCE_COLLECTION
    )
    assert not gate.ready_for_bounded_review_inputs
    assert gate.blockers == (
        WaveSixFailClosedCandidateGateBlocker.CANDIDATE_ASSEMBLY_NOT_READY,
        WaveSixFailClosedCandidateGateBlocker.IX_OBLIGATION_PRESSURE_UNRESOLVED,
    )
    assert len(gate.fingerprint()) == 64
    assert gate.fingerprint() == gate.fingerprint()


def test_fail_closed_gate_reports_donor_gaps_from_real_assembly() -> None:
    assembly = _candidate_assembly(
        (_receipt_for(WaveSixSourceSystem.IX_FUNCTION, seed=101),)
    )

    gate = build_wave_six_fail_closed_candidate_gate(
        gate_id="wave6-candidate-gate",
        candidate_assembly=assembly,
        claim_boundary_statement=CLAIM_BOUNDARY,
        human_authority_id="human-reviewer-1",
        independent_reviewer_id="independent-reviewer-1",
    )

    assert WaveSixFailClosedCandidateGateBlocker.DONOR_EVIDENCE_INCOMPLETE in (
        gate.blockers
    )
    assert gate.canonical_payload()["missing_donor_source_systems"]
    assert gate.canonical_payload()["missing_donor_artifact_keys"]


def test_fail_closed_gate_blocks_missing_human_and_independent_review() -> None:
    gate = build_wave_six_fail_closed_candidate_gate(
        gate_id="wave6-candidate-gate",
        candidate_assembly=_ReadyAssembly(),
        claim_boundary_statement=CLAIM_BOUNDARY,
        human_authority_id="",
        independent_reviewer_id="",
    )

    assert gate.status is WaveSixFailClosedCandidateGateStatus.BLOCKED
    assert gate.decision is (
        WaveSixFailClosedCandidateGateDecision.BLOCK_CANDIDATE_REVIEW
    )
    assert WaveSixFailClosedCandidateGateBlocker.HUMAN_AUTHORITY_MISSING in (
        gate.blockers
    )
    assert WaveSixFailClosedCandidateGateBlocker.INDEPENDENT_REVIEW_MISSING in (
        gate.blockers
    )


def test_fail_closed_gate_blocks_invalid_claim_boundary() -> None:
    gate = build_wave_six_fail_closed_candidate_gate(
        gate_id="wave6-candidate-gate",
        candidate_assembly=_ReadyAssembly(),
        claim_boundary_statement="Looks ready.",
        human_authority_id="human-reviewer-1",
        independent_reviewer_id="independent-reviewer-1",
    )

    assert gate.status is WaveSixFailClosedCandidateGateStatus.BLOCKED
    assert WaveSixFailClosedCandidateGateBlocker.CLAIM_BOUNDARY_INVALID in (
        gate.blockers
    )


def test_fail_closed_gate_blocks_overclaim_and_execution_authority() -> None:
    gate = WaveSixFailClosedCandidateGate(
        gate_id="wave6-candidate-gate",
        candidate_assembly=_ReadyAssembly(),
        claim_boundary_statement=CLAIM_BOUNDARY,
        human_authority_id="human-reviewer-1",
        independent_reviewer_id="independent-reviewer-1",
        claims_agi=True,
        allows_autonomous_authority=True,
    )

    assert gate.status is WaveSixFailClosedCandidateGateStatus.BLOCKED
    assert WaveSixFailClosedCandidateGateBlocker.OVERCLAIM_PRESENT in gate.blockers
    assert WaveSixFailClosedCandidateGateBlocker.EXECUTION_AUTHORITY_PRESENT in (
        gate.blockers
    )


def test_fail_closed_gate_blocks_empty_evidence_and_missing_falsification() -> None:
    empty_assembly = _ReadyAssembly(
        evidence_ids=(),
        ix_falsification_probe_ids=(),
    )
    gate = build_wave_six_fail_closed_candidate_gate(
        gate_id="wave6-candidate-gate",
        candidate_assembly=empty_assembly,
        claim_boundary_statement=CLAIM_BOUNDARY,
        human_authority_id="human-reviewer-1",
        independent_reviewer_id="independent-reviewer-1",
    )

    assert gate.status is WaveSixFailClosedCandidateGateStatus.NEEDS_MORE_EVIDENCE
    assert WaveSixFailClosedCandidateGateBlocker.EVIDENCE_PACKAGE_EMPTY in (
        gate.blockers
    )
    assert WaveSixFailClosedCandidateGateBlocker.FALSIFICATION_PRESSURE_MISSING in (
        gate.blockers
    )


def test_fail_closed_gate_allows_only_bounded_review_input_staging() -> None:
    gate = build_wave_six_fail_closed_candidate_gate(
        gate_id="wave6-candidate-gate",
        candidate_assembly=_ReadyAssembly(),
        claim_boundary_statement=CLAIM_BOUNDARY,
        human_authority_id="human-reviewer-1",
        independent_reviewer_id="independent-reviewer-1",
        notes=("Ready means review-input staging only, not AGI success.",),
    )

    assert gate.status is (
        WaveSixFailClosedCandidateGateStatus.READY_FOR_BOUNDED_REVIEW_INPUTS
    )
    assert gate.decision is (
        WaveSixFailClosedCandidateGateDecision.ENTER_BOUNDED_REVIEW_QUEUE
    )
    assert gate.ready_for_bounded_review_inputs
    assert gate.blockers == ()
    assert gate.canonical_payload()["claims_agi"] is False
    assert gate.canonical_payload()["ready_for_bounded_review_inputs"] is True
    assert gate.canonical_payload()["decision"] == "enter-bounded-review-queue"


def test_fail_closed_gate_payload_preserves_candidate_and_donor_fingerprints() -> None:
    assembly = _candidate_assembly(_full_receipts())
    gate = build_wave_six_fail_closed_candidate_gate(
        gate_id="wave6-candidate-gate",
        candidate_assembly=assembly,
        claim_boundary_statement=CLAIM_BOUNDARY,
        human_authority_id="human-reviewer-1",
        independent_reviewer_id="independent-reviewer-1",
    )

    payload = gate.canonical_payload()

    assert payload["assembly_fingerprint"] == assembly.fingerprint()
    assert payload["donor_intake_fingerprint"] == (
        assembly.donor_intake_bundle.fingerprint()
    )
    assert payload["attempt"] == "wave6_measured_cognition"
    assert payload["status"] == "needs-more-evidence"
