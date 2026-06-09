from __future__ import annotations

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
from ix_cognition_kernel.wave6_contracts import (
    WaveSixArtifactKind,
    WaveSixCapabilityArea,
    WaveSixLoopStage,
    WaveSixSourceSystem,
)
from ix_cognition_kernel.wave6_donor_evidence_intake import (
    WaveSixDonorEvidenceReceipt,
)


def _fingerprint(seed: int) -> str:
    return f"{seed:064x}"[-64:]


@dataclass(frozen=True, slots=True)
class _ReadyGate:
    attempt: str = "wave6_measured_cognition"
    ready_for_bounded_review_inputs: bool = True
    blockers: tuple[Any, ...] = ()
    human_authority_id: str = "human-authority-1"
    independent_reviewer_id: str = "independent-reviewer-1"
    evidence_ids: tuple[str, ...] = (
        "ix-kernel-handoff:wave6_measured_cognition:kernel-handoff-json",
        "donor-evidence:ix-blackfox:policy-ci-receipt",
    )
    ix_falsification_probe_ids: tuple[str, ...] = (
        "ix-obligation-probe:ix-handoff-artifact-wave6_measured_cognition:"
        "falsification_ledger",
    )

    def canonical_payload(self) -> dict[str, Any]:
        return {
            "attempt": self.attempt,
            "blockers": [str(blocker) for blocker in self.blockers],
            "evidence_ids": list(self.evidence_ids),
            "human_authority_id": self.human_authority_id,
            "independent_reviewer_id": self.independent_reviewer_id,
            "ix_falsification_probe_ids": list(self.ix_falsification_probe_ids),
            "ready_for_bounded_review_inputs": self.ready_for_bounded_review_inputs,
        }

    def fingerprint(self) -> str:
        return _fingerprint(77)


def _blackfox_receipt() -> WaveSixDonorEvidenceReceipt:
    return WaveSixDonorEvidenceReceipt(
        receipt_id="ix-blackfox-ci-policy",
        source_system=WaveSixSourceSystem.IX_BLACKFOX,
        repo_name="IX-BlackFox",
        evidence_id="donor-evidence:ix-blackfox:policy-ci-receipt",
        artifact_kind=WaveSixArtifactKind.BLACKFOX_HANDOFF_RECEIPT,
        capability_area=WaveSixCapabilityArea.HUMAN_AUTHORITY_PRESERVATION,
        loop_stages=(
            WaveSixLoopStage.TRIAL,
            WaveSixLoopStage.FALSIFICATION,
            WaveSixLoopStage.HUMAN_REVIEW,
        ),
        artifact_fingerprint=_fingerprint(88),
        summary="BlackFox policy, CI, sandbox, and receipt evidence.",
        produced_by_engine_id="ix-blackfox-policy-ci-engine",
    )


def _pytest_command() -> WaveSixBlackFoxVerificationCommand:
    return WaveSixBlackFoxVerificationCommand(
        command_id="pytest-q",
        command="python -m pytest -q",
        purpose="Run the bounded Kernel test suite under BlackFox review.",
        expected_evidence_id="blackfox-review:pytest-q",
    )


def _ruff_command() -> WaveSixBlackFoxVerificationCommand:
    return WaveSixBlackFoxVerificationCommand(
        command_id="ruff-check",
        command="python -m ruff check .",
        purpose="Run style and lint checks under BlackFox review.",
        expected_evidence_id="blackfox-review:ruff-check",
    )


def test_blackfox_handoff_prepares_review_packet_only_for_ready_gate() -> None:
    handoff = build_wave_six_blackfox_execution_handoff(
        handoff_id="blackfox-wave6-review",
        candidate_gate=_ReadyGate(),
        blackfox_receipt=_blackfox_receipt(),
        verification_commands=(_pytest_command(), _ruff_command()),
        policy_ids=("policy:no-network-egress", "policy:human-approval-required"),
        purpose="Prepare bounded verification metadata for BlackFox review.",
        notes=("Review packet only; no dispatch.",),
    )

    assert (
        handoff.status is WaveSixBlackFoxHandoffStatus.READY_FOR_BLACKFOX_REVIEW_PACKET
    )
    assert handoff.decision is WaveSixBlackFoxHandoffDecision.PREPARE_REVIEW_PACKET_ONLY
    assert handoff.ready_for_blackfox_review_packet
    assert handoff.blockers == ()
    assert not handoff.dispatch_allowed
    assert not handoff.network_egress_allowed
    assert handoff.workspace_isolation_required
    assert handoff.requires_human_approval
    assert handoff.metadata_only
    assert not handoff.claims_agi
    assert not handoff.allows_autonomous_execution
    assert len(handoff.fingerprint()) == 64
    assert handoff.fingerprint() == handoff.fingerprint()


def test_blackfox_handoff_payload_keeps_boundaries_and_evidence() -> None:
    handoff = build_wave_six_blackfox_execution_handoff(
        handoff_id="blackfox-wave6-review",
        candidate_gate=_ReadyGate(),
        blackfox_receipt=_blackfox_receipt(),
        verification_commands=(_pytest_command(), _ruff_command()),
        policy_ids=("policy:no-network-egress", "policy:human-approval-required"),
        purpose="Prepare bounded verification metadata for BlackFox review.",
    )

    payload = handoff.canonical_payload()

    assert payload["schema_version"] == (
        "ix-cognition-kernel-wave6-blackfox-execution-handoff-v1"
    )
    assert payload["decision"] == "prepare-review-packet-only"
    assert payload["status"] == "ready-for-blackfox-review-packet"
    assert payload["dispatch_allowed"] is False
    assert payload["network_egress_allowed"] is False
    assert payload["allows_autonomous_execution"] is False
    assert payload["claims_agi"] is False
    assert payload["candidate_gate_fingerprint"] == _fingerprint(77)
    assert payload["command_ids"] == ["pytest-q", "ruff-check"]
    assert payload["represented_evidence_ids"] == list(handoff.represented_evidence_ids)


def test_blackfox_handoff_contract_artifact_is_review_docket() -> None:
    handoff = build_wave_six_blackfox_execution_handoff(
        handoff_id="blackfox-wave6-review",
        candidate_gate=_ReadyGate(),
        blackfox_receipt=_blackfox_receipt(),
        verification_commands=(_pytest_command(),),
        policy_ids=("policy:no-network-egress",),
        purpose="Prepare bounded verification metadata for BlackFox review.",
    )

    artifact = handoff.to_contract_artifact()

    assert artifact.artifact_id == "blackfox-handoff-artifact-blackfox-wave6-review"
    assert artifact.kind is WaveSixArtifactKind.HUMAN_REVIEW_DOCKET
    assert artifact.source_system is WaveSixSourceSystem.IX_BLACKFOX
    assert artifact.decision.value == "needs-more-evidence"
    assert artifact.evidence_ids == handoff.represented_evidence_ids


def test_blackfox_handoff_blocks_when_candidate_gate_not_ready() -> None:
    gate = _ReadyGate(
        ready_for_bounded_review_inputs=False,
        blockers=("ix-obligation-pressure-unresolved",),
    )
    handoff = build_wave_six_blackfox_execution_handoff(
        handoff_id="blackfox-wave6-review",
        candidate_gate=gate,
        blackfox_receipt=_blackfox_receipt(),
        verification_commands=(_pytest_command(),),
        policy_ids=("policy:no-network-egress",),
        purpose="Prepare bounded verification metadata for BlackFox review.",
    )

    assert handoff.status is WaveSixBlackFoxHandoffStatus.BLOCKED_BY_CANDIDATE_GATE
    assert handoff.decision is WaveSixBlackFoxHandoffDecision.HOLD_FOR_CANDIDATE_GATE
    assert not handoff.ready_for_blackfox_review_packet
    assert handoff.blockers == (
        WaveSixBlackFoxHandoffBlocker.CANDIDATE_GATE_NOT_READY,
        WaveSixBlackFoxHandoffBlocker.CANDIDATE_GATE_HAS_BLOCKERS,
    )


def test_blackfox_handoff_blocks_missing_review_boundaries() -> None:
    gate = _ReadyGate(
        human_authority_id="",
        independent_reviewer_id="",
        ix_falsification_probe_ids=(),
    )
    handoff = build_wave_six_blackfox_execution_handoff(
        handoff_id="blackfox-wave6-review",
        candidate_gate=gate,
        blackfox_receipt=_blackfox_receipt(),
        verification_commands=(_pytest_command(),),
        policy_ids=("policy:no-network-egress",),
        purpose="Prepare bounded verification metadata for BlackFox review.",
    )

    assert handoff.blockers == (
        WaveSixBlackFoxHandoffBlocker.HUMAN_AUTHORITY_MISSING,
        WaveSixBlackFoxHandoffBlocker.INDEPENDENT_REVIEW_MISSING,
        WaveSixBlackFoxHandoffBlocker.FALSIFICATION_PRESSURE_MISSING,
    )


def test_blackfox_handoff_requires_blackfox_source_receipt() -> None:
    bad_receipt = WaveSixDonorEvidenceReceipt(
        receipt_id="ix-function-transfer",
        source_system=WaveSixSourceSystem.IX_FUNCTION,
        repo_name="IX-Function",
        evidence_id="donor-evidence:ix-function:transfer",
        artifact_kind=WaveSixArtifactKind.TRANSFER_NOVELTY_RECORD,
        capability_area=WaveSixCapabilityArea.TRANSFER_GENERALIZATION,
        loop_stages=(WaveSixLoopStage.TRANSFER_CHECK,),
        artifact_fingerprint=_fingerprint(99),
        summary="Transfer evidence.",
        produced_by_engine_id="ix-function-engine",
    )

    with pytest.raises(ValueError, match="requires an IX-BlackFox receipt"):
        build_wave_six_blackfox_execution_handoff(
            handoff_id="blackfox-wave6-review",
            candidate_gate=_ReadyGate(),
            blackfox_receipt=bad_receipt,
            verification_commands=(_pytest_command(),),
            policy_ids=("policy:no-network-egress",),
            purpose="Prepare bounded verification metadata for BlackFox review.",
        )


def test_blackfox_handoff_rejects_dispatch_or_overclaim_flags() -> None:
    with pytest.raises(ValueError, match="must not dispatch execution"):
        WaveSixBlackFoxExecutionHandoff(
            handoff_id="blackfox-wave6-review",
            candidate_gate=_ReadyGate(),
            blackfox_receipt=_blackfox_receipt(),
            verification_commands=(_pytest_command(),),
            policy_ids=("policy:no-network-egress",),
            purpose="Prepare bounded verification metadata.",
            dispatch_allowed=True,
        )
    with pytest.raises(ValueError, match="must not claim AGI"):
        WaveSixBlackFoxExecutionHandoff(
            handoff_id="blackfox-wave6-review",
            candidate_gate=_ReadyGate(),
            blackfox_receipt=_blackfox_receipt(),
            verification_commands=(_pytest_command(),),
            policy_ids=("policy:no-network-egress",),
            purpose="Prepare bounded verification metadata.",
            claims_agi=True,
        )


def test_blackfox_verification_command_rejects_unsafe_shell_syntax() -> None:
    with pytest.raises(ValueError, match="unsafe syntax"):
        WaveSixBlackFoxVerificationCommand(
            command_id="unsafe",
            command="python -m pytest -q && curl https://example.invalid",
            purpose="Unsafe chained command.",
            expected_evidence_id="blackfox-review:unsafe",
        )
