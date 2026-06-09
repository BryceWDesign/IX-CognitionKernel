from dataclasses import dataclass
from typing import Any

import pytest

from ix_cognition_kernel.wave6_blackfox_execution_handoff import (
    WaveSixBlackFoxExecutionHandoff,
    WaveSixBlackFoxHandoffBlocker,
    WaveSixBlackFoxHandoffDecision,
    WaveSixBlackFoxHandoffStatus,
    WaveSixBlackFoxVerificationCommand,
    build_wave_six_blackfox_execution_handoff,
)
from ix_cognition_kernel.wave6_candidate_assembly import (
    WaveSixCandidateAssembly,
    build_wave_six_candidate_assembly,
)
from ix_cognition_kernel.wave6_contracts import (
    WaveSixArtifactKind,
    WaveSixDecisionState,
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
class _ReadyGate:
    attempt: str = "ready_attempt"
    ready_for_bounded_review_inputs: bool = True
    blockers: tuple[Any, ...] = ()
    evidence_ids: tuple[str, ...] = ("evidence:ready",)
    ix_falsification_probe_ids: tuple[str, ...] = ("probe:ready",)
    human_authority_id: str = "human-reviewer-1"
    independent_reviewer_id: str = "independent-reviewer-1"
    donor_intake_bundle: _ReadyDonorIntake = _ReadyDonorIntake()

    def fingerprint(self) -> str:
        return _fingerprint(888)


def _commands() -> tuple[WaveSixBlackFoxVerificationCommand, ...]:
    return (
        WaveSixBlackFoxVerificationCommand(
            command_id="pytest",
            command="python -m pytest",
            purpose="Run the bounded Kernel test suite under BlackFox review.",
            expected_evidence_id="blackfox-ci:pytest",
        ),
        WaveSixBlackFoxVerificationCommand(
            command_id="ruff",
            command="python -m ruff check .",
            purpose="Run lint verification under BlackFox review.",
            expected_evidence_id="blackfox-ci:ruff",
        ),
    )


def _blackfox_receipt() -> WaveSixDonorEvidenceReceipt:
    return _receipt_for(
        WaveSixSourceSystem.IX_BLACKFOX,
        WaveSixArtifactKind.HUMAN_REVIEW_DOCKET,
        seed=202,
    )


def test_blackfox_handoff_holds_real_gate_with_open_ix_obligations() -> None:
    assembly = _candidate_assembly(_full_receipts())
    gate = build_wave_six_fail_closed_candidate_gate(
        gate_id="wave6-candidate-gate",
        candidate_assembly=assembly,
        claim_boundary_statement=CLAIM_BOUNDARY,
        human_authority_id="human-reviewer-1",
        independent_reviewer_id="independent-reviewer-1",
    )

    handoff = build_wave_six_blackfox_execution_handoff(
        handoff_id="wave6-blackfox-handoff",
        candidate_gate=gate,
        blackfox_receipt=_blackfox_receipt(),
        verification_commands=_commands(),
        policy_ids=("deny-network-egress", "require-human-approval"),
        purpose="Prepare BlackFox review metadata for bounded CI verification.",
    )

    assert handoff.status is WaveSixBlackFoxHandoffStatus.BLOCKED_BY_CANDIDATE_GATE
    assert handoff.decision is WaveSixBlackFoxHandoffDecision.HOLD_FOR_CANDIDATE_GATE
    assert not handoff.ready_for_blackfox_review_packet
    assert handoff.blockers == (
        WaveSixBlackFoxHandoffBlocker.CANDIDATE_GATE_NOT_READY,
        WaveSixBlackFoxHandoffBlocker.CANDIDATE_GATE_HAS_BLOCKERS,
    )
    assert not handoff.dispatch_allowed
    assert not handoff.network_egress_allowed
    assert handoff.workspace_isolation_required
    assert len(handoff.fingerprint()) == 64
    assert handoff.fingerprint() == handoff.fingerprint()


def test_blackfox_handoff_can_prepare_review_packet_for_ready_gate_only() -> None:
    handoff = build_wave_six_blackfox_execution_handoff(
        handoff_id="ready-blackfox-handoff",
        candidate_gate=_ReadyGate(),
        blackfox_receipt=_blackfox_receipt(),
        verification_commands=_commands(),
        policy_ids=("deny-network-egress", "require-human-approval"),
        purpose="Prepare metadata-only BlackFox review packet.",
    )

    assert handoff.status is (
        WaveSixBlackFoxHandoffStatus.READY_FOR_BLACKFOX_REVIEW_PACKET
    )
    assert handoff.decision is (
        WaveSixBlackFoxHandoffDecision.PREPARE_REVIEW_PACKET_ONLY
    )
    assert handoff.ready_for_blackfox_review_packet
    assert handoff.blockers == ()
    assert handoff.command_ids == ("pytest", "ruff")
    assert handoff.expected_command_evidence_ids == (
        "blackfox-ci:pytest",
        "blackfox-ci:ruff",
    )
    assert not handoff.dispatch_allowed


def test_blackfox_handoff_converts_to_non_executing_contract_artifact() -> None:
    handoff = build_wave_six_blackfox_execution_handoff(
        handoff_id="artifact-blackfox-handoff",
        candidate_gate=_ReadyGate(),
        blackfox_receipt=_blackfox_receipt(),
        verification_commands=_commands(),
        policy_ids=("deny-network-egress", "require-human-approval"),
        purpose="Prepare metadata-only BlackFox review packet.",
    )

    artifact = handoff.to_contract_artifact()

    assert artifact.artifact_id == "blackfox-handoff-artifact-artifact-blackfox-handoff"
    assert artifact.kind is WaveSixArtifactKind.HUMAN_REVIEW_DOCKET
    assert artifact.source_system is WaveSixSourceSystem.IX_BLACKFOX
    assert artifact.decision is WaveSixDecisionState.NEEDS_MORE_EVIDENCE
    assert artifact.evidence_ids[0] == _blackfox_receipt().evidence_id
    assert not artifact.allows_autonomous_execution
    assert not artifact.claims_agi
    assert not artifact.self_validated


def test_blackfox_handoff_rejects_non_blackfox_receipt() -> None:
    with pytest.raises(ValueError, match="IX-BlackFox receipt"):
        build_wave_six_blackfox_execution_handoff(
            handoff_id="bad-source-handoff",
            candidate_gate=_ReadyGate(),
            blackfox_receipt=_receipt_for(WaveSixSourceSystem.IX_FUNCTION, seed=303),
            verification_commands=_commands(),
            policy_ids=("deny-network-egress",),
            purpose="Invalid source should be rejected.",
        )


def test_blackfox_handoff_rejects_unsafe_command_syntax() -> None:
    with pytest.raises(ValueError, match="unsafe syntax"):
        WaveSixBlackFoxVerificationCommand(
            command_id="unsafe",
            command="python -m pytest && curl example.com",
            purpose="Unsafe shell chaining must be rejected.",
            expected_evidence_id="blackfox-ci:unsafe",
        )


def test_blackfox_handoff_rejects_authority_or_egress_flags() -> None:
    with pytest.raises(ValueError, match="must not dispatch execution"):
        WaveSixBlackFoxExecutionHandoff(
            handoff_id="dispatch-not-allowed",
            candidate_gate=_ReadyGate(),
            blackfox_receipt=_blackfox_receipt(),
            verification_commands=_commands(),
            policy_ids=("deny-network-egress",),
            purpose="Dispatch must be impossible from Kernel handoff.",
            dispatch_allowed=True,
        )
    with pytest.raises(ValueError, match="must deny network egress"):
        WaveSixBlackFoxExecutionHandoff(
            handoff_id="egress-not-allowed",
            candidate_gate=_ReadyGate(),
            blackfox_receipt=_blackfox_receipt(),
            verification_commands=_commands(),
            policy_ids=("deny-network-egress",),
            purpose="Network egress must stay denied.",
            network_egress_allowed=True,
        )
    with pytest.raises(ValueError, match="must not claim AGI"):
        WaveSixBlackFoxExecutionHandoff(
            handoff_id="agi-not-allowed",
            candidate_gate=_ReadyGate(),
            blackfox_receipt=_blackfox_receipt(),
            verification_commands=_commands(),
            policy_ids=("deny-network-egress",),
            purpose="AGI claims must stay blocked.",
            claims_agi=True,
        )


def test_blackfox_handoff_reports_missing_ready_gate_review_inputs() -> None:
    gate = _ReadyGate(
        ready_for_bounded_review_inputs=False,
        blockers=("human-authority-missing",),
        human_authority_id="",
        independent_reviewer_id="",
        ix_falsification_probe_ids=(),
    )

    handoff = build_wave_six_blackfox_execution_handoff(
        handoff_id="missing-review-inputs",
        candidate_gate=gate,
        blackfox_receipt=_blackfox_receipt(),
        verification_commands=_commands(),
        policy_ids=("deny-network-egress",),
        purpose="Show all missing review blockers.",
    )

    assert handoff.blockers == (
        WaveSixBlackFoxHandoffBlocker.CANDIDATE_GATE_NOT_READY,
        WaveSixBlackFoxHandoffBlocker.CANDIDATE_GATE_HAS_BLOCKERS,
        WaveSixBlackFoxHandoffBlocker.HUMAN_AUTHORITY_MISSING,
        WaveSixBlackFoxHandoffBlocker.INDEPENDENT_REVIEW_MISSING,
        WaveSixBlackFoxHandoffBlocker.FALSIFICATION_PRESSURE_MISSING,
    )
    assert handoff.status is WaveSixBlackFoxHandoffStatus.BLOCKED_BY_CANDIDATE_GATE


def test_blackfox_handoff_payload_preserves_no_execution_boundary() -> None:
    handoff = build_wave_six_blackfox_execution_handoff(
        handoff_id="payload-blackfox-handoff",
        candidate_gate=_ReadyGate(),
        blackfox_receipt=_blackfox_receipt(),
        verification_commands=_commands(),
        policy_ids=("deny-network-egress", "require-human-approval"),
        purpose="Prepare metadata-only BlackFox review packet.",
        notes=("Review packet only; no execution dispatch from Kernel.",),
    )

    payload = handoff.canonical_payload()

    assert payload["dispatch_allowed"] is False
    assert payload["network_egress_allowed"] is False
    assert payload["metadata_only"] is True
    assert payload["claims_agi"] is False
    assert payload["ready_for_blackfox_review_packet"] is True
    assert payload["decision"] == "prepare-review-packet-only"
