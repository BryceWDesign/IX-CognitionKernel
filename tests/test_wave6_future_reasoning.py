import pytest

from ix_cognition_kernel.wave6_future_reasoning import (
    WaveSixFutureReasoningChangeProof,
    WaveSixFutureReasoningProofLedger,
    WaveSixReasoningChangeKind,
    WaveSixReasoningProofDecision,
    WaveSixReasoningSnapshot,
    build_wave_six_future_reasoning_proof_ledger,
)


def _snapshot(
    *,
    snapshot_id: str,
    reasoning_summary: str,
    active_assumption_ids: tuple[str, ...] = ("assumption-causal-1",),
    memory_ids: tuple[str, ...] = ("memory-1",),
    evidence_ids: tuple[str, ...] = ("snapshot-evidence-1",),
) -> WaveSixReasoningSnapshot:
    return WaveSixReasoningSnapshot(
        snapshot_id=snapshot_id,
        task_context="Cross-domain transfer trial after measured feedback.",
        reasoning_summary=reasoning_summary,
        active_assumption_ids=active_assumption_ids,
        memory_ids=memory_ids,
        evidence_ids=evidence_ids,
        created_by_stage="memory-update",
    )


def _before_snapshot() -> WaveSixReasoningSnapshot:
    return _snapshot(
        snapshot_id="before-1",
        reasoning_summary="The system prefers the original causal assumption.",
    )


def _after_snapshot() -> WaveSixReasoningSnapshot:
    return _snapshot(
        snapshot_id="after-1",
        reasoning_summary=(
            "The system now tests the corrected causal condition before using "
            "the original assumption."
        ),
        active_assumption_ids=("assumption-causal-1", "assumption-causal-2"),
        memory_ids=("memory-1", "memory-corrected-1"),
        evidence_ids=("snapshot-evidence-2",),
    )


def _proof(
    *,
    proof_id: str = "proof-1",
    decision: WaveSixReasoningProofDecision = (
        WaveSixReasoningProofDecision.ACCEPT_FOR_WAVE_SIX_REVIEW
    ),
) -> WaveSixFutureReasoningChangeProof:
    return WaveSixFutureReasoningChangeProof(
        proof_id=proof_id,
        before_snapshot=_before_snapshot(),
        after_snapshot=_after_snapshot(),
        reality_correction_record_ids=("correction-record-1",),
        changed_assumption_ids=("assumption-causal-1",),
        changed_memory_ids=("memory-corrected-1",),
        change_kind=WaveSixReasoningChangeKind.CAUSAL_ASSUMPTION_REWEIGHTED,
        expected_future_behavior=(
            "Future transfer trials test the corrected causal condition first."
        ),
        counterfactual_old_behavior=(
            "Future transfer trials would reuse the original assumption first."
        ),
        evidence_ids=("reasoning-change-evidence-1",),
        decision=decision,
    )


def test_reasoning_snapshot_is_evidence_bound_and_fingerprinted() -> None:
    snapshot = _before_snapshot()

    assert snapshot.active_assumption_ids == ("assumption-causal-1",)
    assert snapshot.memory_ids == ("memory-1",)
    assert snapshot.evidence_ids == ("snapshot-evidence-1",)
    assert snapshot.fingerprint() == snapshot.fingerprint()
    assert len(snapshot.fingerprint()) == 64


def test_future_reasoning_change_proof_requires_reality_correction() -> None:
    proof = _proof()

    assert proof.snapshot_fingerprints_differ
    assert proof.reality_correction_bound
    assert proof.behavior_change_bound
    assert proof.evidence_bound
    assert proof.accepted_for_review
    assert not proof.blocks_claim
    assert proof.proves_future_reasoning_changed
    assert proof.fingerprint() == proof.fingerprint()
    assert len(proof.fingerprint()) == 64


def test_future_reasoning_change_proof_rejects_identical_snapshots() -> None:
    snapshot = _before_snapshot()

    with pytest.raises(ValueError, match="different snapshots"):
        WaveSixFutureReasoningChangeProof(
            proof_id="identical-snapshots",
            before_snapshot=snapshot,
            after_snapshot=snapshot,
            reality_correction_record_ids=("correction-record-1",),
            changed_assumption_ids=("assumption-causal-1",),
            changed_memory_ids=("memory-1",),
            change_kind=WaveSixReasoningChangeKind.PREDICTION_RULE_REVISED,
            expected_future_behavior="Use the corrected prediction rule.",
            counterfactual_old_behavior="Use the old prediction rule.",
            evidence_ids=("evidence-identical",),
        )


def test_future_reasoning_change_proof_rejects_missing_correction_records() -> None:
    with pytest.raises(ValueError, match="reality correction records"):
        WaveSixFutureReasoningChangeProof(
            proof_id="missing-correction",
            before_snapshot=_before_snapshot(),
            after_snapshot=_after_snapshot(),
            reality_correction_record_ids=(),
            changed_assumption_ids=("assumption-causal-1",),
            changed_memory_ids=("memory-corrected-1",),
            change_kind=WaveSixReasoningChangeKind.PREDICTION_RULE_REVISED,
            expected_future_behavior="Use the corrected prediction rule.",
            counterfactual_old_behavior="Use the old prediction rule.",
            evidence_ids=("evidence-missing-correction",),
        )


def test_future_reasoning_change_proof_rejects_agi_claim() -> None:
    with pytest.raises(ValueError, match="must not claim AGI"):
        WaveSixFutureReasoningChangeProof(
            proof_id="agi-claim",
            before_snapshot=_before_snapshot(),
            after_snapshot=_after_snapshot(),
            reality_correction_record_ids=("correction-record-1",),
            changed_assumption_ids=("assumption-causal-1",),
            changed_memory_ids=("memory-corrected-1",),
            change_kind=WaveSixReasoningChangeKind.PREDICTION_RULE_REVISED,
            expected_future_behavior="Use the corrected prediction rule.",
            counterfactual_old_behavior="Use the old prediction rule.",
            evidence_ids=("evidence-agi-claim",),
            claims_agi=True,
        )


def test_future_reasoning_change_proof_rejects_autonomous_execution() -> None:
    with pytest.raises(ValueError, match="must not allow autonomous execution"):
        WaveSixFutureReasoningChangeProof(
            proof_id="autonomous-execution",
            before_snapshot=_before_snapshot(),
            after_snapshot=_after_snapshot(),
            reality_correction_record_ids=("correction-record-1",),
            changed_assumption_ids=("assumption-causal-1",),
            changed_memory_ids=("memory-corrected-1",),
            change_kind=WaveSixReasoningChangeKind.PREDICTION_RULE_REVISED,
            expected_future_behavior="Use the corrected prediction rule.",
            counterfactual_old_behavior="Use the old prediction rule.",
            evidence_ids=("evidence-autonomous-execution",),
            allows_autonomous_execution=True,
        )


def test_future_reasoning_change_ledger_accepts_proven_change() -> None:
    ledger = build_wave_six_future_reasoning_proof_ledger(
        ledger_id="future-ledger-1",
        proofs=(_proof(proof_id="proof-b"), _proof(proof_id="proof-a")),
        notes=("Measured reality changed future reasoning.",),
    )

    assert ledger.proof_ids == ("proof-a", "proof-b")
    assert ledger.accepted_proof_ids == ("proof-a", "proof-b")
    assert ledger.blocked_proof_ids == ()
    assert ledger.has_required_accepted_proofs
    assert ledger.ready_for_wave_six_review
    assert ledger.fingerprint() == ledger.fingerprint()
    assert len(ledger.fingerprint()) == 64


def test_future_reasoning_change_ledger_fails_without_accepted_proof() -> None:
    ledger = WaveSixFutureReasoningProofLedger(
        ledger_id="future-ledger-not-ready",
        proofs=(_proof(decision=WaveSixReasoningProofDecision.NEEDS_MORE_EVIDENCE),),
    )

    assert ledger.accepted_proof_ids == ()
    assert not ledger.has_required_accepted_proofs
    assert not ledger.ready_for_wave_six_review


def test_future_reasoning_change_ledger_blocks_on_blocking_proof() -> None:
    ledger = WaveSixFutureReasoningProofLedger(
        ledger_id="future-ledger-blocked",
        proofs=(_proof(decision=WaveSixReasoningProofDecision.BLOCK_CLAIM),),
    )

    assert ledger.blocked_proof_ids == ("proof-1",)
    assert not ledger.ready_for_wave_six_review


def test_future_reasoning_change_ledger_rejects_duplicate_proof_ids() -> None:
    proof = _proof()

    with pytest.raises(ValueError, match="Duplicate proof_id"):
        WaveSixFutureReasoningProofLedger(
            ledger_id="future-ledger-duplicate",
            proofs=(proof, proof),
        )
