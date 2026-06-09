from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ix_cognition_kernel.wave6_fail_closed_candidate_gate import (
    WaveSixFailClosedCandidateGateBlocker,
    WaveSixFailClosedCandidateGateDecision,
    WaveSixFailClosedCandidateGateStatus,
    build_wave_six_fail_closed_candidate_gate,
)


def _fingerprint(seed: int) -> str:
    return f"{seed:064x}"[-64:]


@dataclass(frozen=True, slots=True)
class _DonorIntake:
    missing_source_systems: tuple[Any, ...] = ()
    missing_required_artifact_keys: tuple[str, ...] = ()

    def fingerprint(self) -> str:
        return _fingerprint(101)


@dataclass(frozen=True, slots=True)
class _CandidateAssembly:
    attempt: str = "wave6_measured_cognition"
    readiness_blockers: tuple[Any, ...] = ()
    ready_for_fail_closed_readiness_gate: bool = True
    evidence_ids: tuple[str, ...] = (
        "ix-kernel-handoff:wave6_measured_cognition:kernel-handoff-json",
        "donor-evidence:ix-function:transfer-novelty-record",
    )
    ix_obligation_gap_ids: tuple[str, ...] = ()
    ix_falsification_probe_ids: tuple[str, ...] = (
        "ix-obligation-probe:ix-handoff-artifact-wave6_measured_cognition:"
        "falsification_ledger",
    )
    donor_intake_bundle: _DonorIntake = _DonorIntake()
    human_review_required: bool = True
    metadata_only: bool = True
    allows_autonomous_execution: bool = False
    claims_agi: bool = False
    claims_production_ready: bool = False
    claims_certified: bool = False
    self_validated: bool = False

    def fingerprint(self) -> str:
        return _fingerprint(202)


def _claim_boundary() -> str:
    return (
        "This is a measured system-level cognition review package, "
        "not an AGI claim, with human authority, independent review, "
        "and no autonomous execution."
    )


def test_fail_closed_candidate_gate_allows_only_bounded_review_inputs() -> None:
    gate = build_wave_six_fail_closed_candidate_gate(
        gate_id="wave6-candidate-gate",
        candidate_assembly=_CandidateAssembly(),
        claim_boundary_statement=_claim_boundary(),
        human_authority_id="human-reviewer-1",
        independent_reviewer_id="independent-reviewer-1",
        notes=("Gate may only stage bounded review inputs.",),
    )

    assert gate.status is (
        WaveSixFailClosedCandidateGateStatus.READY_FOR_BOUNDED_REVIEW_INPUTS
    )
    assert (
        gate.decision
        is WaveSixFailClosedCandidateGateDecision.ENTER_BOUNDED_REVIEW_QUEUE
    )
    assert gate.ready_for_bounded_review_inputs
    assert gate.blockers == ()
    assert gate.claim_boundary_statement_valid
    assert not gate.overclaim_present
    assert not gate.execution_authority_present
    assert not gate.self_validation_present
    assert gate.human_authority_present
    assert gate.independent_review_present
    assert len(gate.fingerprint()) == 64
    assert gate.fingerprint() == gate.fingerprint()


def test_fail_closed_candidate_gate_payload_is_deterministic() -> None:
    gate = build_wave_six_fail_closed_candidate_gate(
        gate_id="wave6-candidate-gate",
        candidate_assembly=_CandidateAssembly(),
        claim_boundary_statement=_claim_boundary(),
        human_authority_id="human-reviewer-1",
        independent_reviewer_id="independent-reviewer-1",
    )

    payload = gate.canonical_payload()

    assert payload["schema_version"] == (
        "ix-cognition-kernel-wave6-fail-closed-candidate-gate-v1"
    )
    assert payload["attempt"] == "wave6_measured_cognition"
    assert payload["status"] == "ready-for-bounded-review-inputs"
    assert payload["decision"] == "enter-bounded-review-queue"
    assert payload["assembly_fingerprint"] == _fingerprint(202)
    assert payload["donor_intake_fingerprint"] == _fingerprint(101)
    assert payload["ready_for_bounded_review_inputs"] is True
    assert payload["claim_boundary_statement_valid"] is True
    assert payload["evidence_ids"] == list(gate.candidate_assembly.evidence_ids)


def test_fail_closed_candidate_gate_blocks_missing_authority_and_claim_boundary() -> None:
    gate = build_wave_six_fail_closed_candidate_gate(
        gate_id="wave6-candidate-gate",
        candidate_assembly=_CandidateAssembly(),
        claim_boundary_statement="measured system-level cognition only",
        human_authority_id="",
        independent_reviewer_id="",
    )

    assert gate.status is WaveSixFailClosedCandidateGateStatus.BLOCKED
    assert gate.decision is WaveSixFailClosedCandidateGateDecision.BLOCK_CANDIDATE_REVIEW
    assert not gate.ready_for_bounded_review_inputs
    assert gate.blockers == (
        WaveSixFailClosedCandidateGateBlocker.HUMAN_AUTHORITY_MISSING,
        WaveSixFailClosedCandidateGateBlocker.INDEPENDENT_REVIEW_MISSING,
        WaveSixFailClosedCandidateGateBlocker.CLAIM_BOUNDARY_INVALID,
    )


def test_fail_closed_candidate_gate_blocks_overclaim_execution_and_self_validation() -> None:
    gate = build_wave_six_fail_closed_candidate_gate(
        gate_id="wave6-candidate-gate",
        candidate_assembly=_CandidateAssembly(
            allows_autonomous_execution=True,
            claims_agi=True,
            self_validated=True,
        ),
        claim_boundary_statement=_claim_boundary(),
        human_authority_id="human-reviewer-1",
        independent_reviewer_id="independent-reviewer-1",
    )

    assert gate.status is WaveSixFailClosedCandidateGateStatus.BLOCKED
    assert gate.blockers == (
        WaveSixFailClosedCandidateGateBlocker.OVERCLAIM_PRESENT,
        WaveSixFailClosedCandidateGateBlocker.EXECUTION_AUTHORITY_PRESENT,
        WaveSixFailClosedCandidateGateBlocker.SELF_VALIDATION_PRESENT,
    )


def test_fail_closed_candidate_gate_needs_evidence_for_ix_pressure() -> None:
    gate = build_wave_six_fail_closed_candidate_gate(
        gate_id="wave6-candidate-gate",
        candidate_assembly=_CandidateAssembly(
            readiness_blockers=("ix-obligation-gaps-blocking",),
            ready_for_fail_closed_readiness_gate=False,
            ix_obligation_gap_ids=("ix-obligation-gap:claim-boundary",),
        ),
        claim_boundary_statement=_claim_boundary(),
        human_authority_id="human-reviewer-1",
        independent_reviewer_id="independent-reviewer-1",
    )

    assert gate.status is WaveSixFailClosedCandidateGateStatus.NEEDS_MORE_EVIDENCE
    assert (
        gate.decision
        is WaveSixFailClosedCandidateGateDecision.CONTINUE_EVIDENCE_COLLECTION
    )
    assert gate.blockers == (
        WaveSixFailClosedCandidateGateBlocker.CANDIDATE_ASSEMBLY_NOT_READY,
        WaveSixFailClosedCandidateGateBlocker.IX_OBLIGATION_PRESSURE_UNRESOLVED,
    )


def test_fail_closed_candidate_gate_needs_evidence_for_donor_gaps() -> None:
    gate = build_wave_six_fail_closed_candidate_gate(
        gate_id="wave6-candidate-gate",
        candidate_assembly=_CandidateAssembly(
            readiness_blockers=("donor-evidence-incomplete",),
            ready_for_fail_closed_readiness_gate=False,
            donor_intake_bundle=_DonorIntake(
                missing_source_systems=("ix-blackfox",),
                missing_required_artifact_keys=("ix-blackfox:blackfox-receipt",),
            ),
        ),
        claim_boundary_statement=_claim_boundary(),
        human_authority_id="human-reviewer-1",
        independent_reviewer_id="independent-reviewer-1",
    )

    assert gate.status is WaveSixFailClosedCandidateGateStatus.NEEDS_MORE_EVIDENCE
    assert gate.blockers == (
        WaveSixFailClosedCandidateGateBlocker.CANDIDATE_ASSEMBLY_NOT_READY,
        WaveSixFailClosedCandidateGateBlocker.DONOR_EVIDENCE_INCOMPLETE,
    )


def test_fail_closed_candidate_gate_blocks_empty_evidence_and_missing_falsification() -> None:
    gate = build_wave_six_fail_closed_candidate_gate(
        gate_id="wave6-candidate-gate",
        candidate_assembly=_CandidateAssembly(
            evidence_ids=(),
            ix_falsification_probe_ids=(),
        ),
        claim_boundary_statement=_claim_boundary(),
        human_authority_id="human-reviewer-1",
        independent_reviewer_id="independent-reviewer-1",
    )

    assert gate.status is WaveSixFailClosedCandidateGateStatus.NEEDS_MORE_EVIDENCE
    assert gate.blockers == (
        WaveSixFailClosedCandidateGateBlocker.EVIDENCE_PACKAGE_EMPTY,
        WaveSixFailClosedCandidateGateBlocker.FALSIFICATION_PRESSURE_MISSING,
    )


def test_fail_closed_candidate_gate_blocks_when_human_review_not_required() -> None:
    gate = build_wave_six_fail_closed_candidate_gate(
        gate_id="wave6-candidate-gate",
        candidate_assembly=_CandidateAssembly(human_review_required=False),
        claim_boundary_statement=_claim_boundary(),
        human_authority_id="human-reviewer-1",
        independent_reviewer_id="independent-reviewer-1",
    )

    assert gate.status is WaveSixFailClosedCandidateGateStatus.BLOCKED
    assert gate.blockers == (
        WaveSixFailClosedCandidateGateBlocker.HUMAN_AUTHORITY_MISSING,
    )
