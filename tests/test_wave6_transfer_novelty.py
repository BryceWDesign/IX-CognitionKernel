import pytest

from ix_cognition_kernel.wave6_transfer_novelty import (
    WaveSixNegativeControlResult,
    WaveSixNoveltyPressureKind,
    WaveSixTransferDecision,
    WaveSixTransferDomain,
    WaveSixTransferNoveltyLedger,
    WaveSixTransferNoveltyRecord,
    build_wave_six_transfer_novelty_ledger,
)


def _domain(
    *,
    domain_id: str,
    name: str,
    domain_family: str,
    evidence_id: str,
) -> WaveSixTransferDomain:
    return WaveSixTransferDomain(
        domain_id=domain_id,
        name=name,
        domain_family=domain_family,
        task_summary="Measure whether corrected causal structure transfers.",
        measurable_success_criteria=(
            "Prediction is made before target outcome is observed.",
            "Corrected causal structure is applied without hand-scripted rescue.",
        ),
        evidence_ids=(evidence_id,),
    )


def _source_domain() -> WaveSixTransferDomain:
    return _domain(
        domain_id="source-software-repair",
        name="Software repair transfer source",
        domain_family="software",
        evidence_id="source-domain-evidence",
    )


def _target_domain() -> WaveSixTransferDomain:
    return _domain(
        domain_id="target-assurance-case",
        name="Assurance-case transfer target",
        domain_family="assurance",
        evidence_id="target-domain-evidence",
    )


def _record(
    *,
    record_id: str = "transfer-1",
    decision: WaveSixTransferDecision = (
        WaveSixTransferDecision.ACCEPT_FOR_WAVE_SIX_REVIEW
    ),
    negative_control_result: WaveSixNegativeControlResult = (
        WaveSixNegativeControlResult.PASSED
    ),
) -> WaveSixTransferNoveltyRecord:
    return WaveSixTransferNoveltyRecord(
        record_id=record_id,
        source_domain=_source_domain(),
        target_domain=_target_domain(),
        transferred_structure_id="corrected-causal-structure-1",
        future_reasoning_proof_ids=("future-proof-1",),
        expected_transfer_behavior=(
            "The target trial checks the corrected causal precondition first."
        ),
        observed_target_behavior=(
            "The target trial checked the corrected causal precondition first."
        ),
        novelty_pressure_kinds=(
            WaveSixNoveltyPressureKind.DOMAIN_SHIFT,
            WaveSixNoveltyPressureKind.NEGATIVE_CONTROL,
        ),
        negative_control_result=negative_control_result,
        negative_control_summary=(
            "A decoy target that lacks the causal precondition did not receive a "
            "false transfer pass."
        ),
        evidence_ids=("transfer-evidence-1",),
        decision=decision,
    )


def test_transfer_domain_requires_measurable_criteria_and_evidence() -> None:
    domain = _source_domain()

    assert domain.measurable_success_criteria
    assert domain.evidence_ids == ("source-domain-evidence",)
    assert domain.fingerprint() == domain.fingerprint()
    assert len(domain.fingerprint()) == 64


def test_transfer_novelty_record_supports_bounded_transfer_claim() -> None:
    record = _record()

    assert record.source_target_distinct
    assert record.negative_control_passed
    assert record.future_reasoning_bound
    assert record.novelty_pressure_bound
    assert record.evidence_bound
    assert record.accepted_for_review
    assert not record.blocks_claim
    assert record.supports_transfer_claim
    assert record.combined_evidence_ids == (
        "source-domain-evidence",
        "target-domain-evidence",
        "transfer-evidence-1",
    )
    assert record.fingerprint() == record.fingerprint()
    assert len(record.fingerprint()) == 64


def test_transfer_record_rejects_same_domain() -> None:
    domain = _source_domain()

    with pytest.raises(ValueError, match="distinct source and target"):
        WaveSixTransferNoveltyRecord(
            record_id="same-domain",
            source_domain=domain,
            target_domain=domain,
            transferred_structure_id="structure-1",
            future_reasoning_proof_ids=("future-proof-1",),
            expected_transfer_behavior="Apply corrected structure.",
            observed_target_behavior="Applied corrected structure.",
            novelty_pressure_kinds=(WaveSixNoveltyPressureKind.NEGATIVE_CONTROL,),
            negative_control_result=WaveSixNegativeControlResult.PASSED,
            negative_control_summary="Negative control passed.",
            evidence_ids=("evidence-same-domain",),
        )


def test_transfer_record_rejects_same_domain_family() -> None:
    with pytest.raises(ValueError, match="cross-family domain shift"):
        WaveSixTransferNoveltyRecord(
            record_id="same-family",
            source_domain=_source_domain(),
            target_domain=_domain(
                domain_id="target-software-review",
                name="Software review transfer target",
                domain_family="software",
                evidence_id="target-software-evidence",
            ),
            transferred_structure_id="structure-1",
            future_reasoning_proof_ids=("future-proof-1",),
            expected_transfer_behavior="Apply corrected structure.",
            observed_target_behavior="Applied corrected structure.",
            novelty_pressure_kinds=(WaveSixNoveltyPressureKind.NEGATIVE_CONTROL,),
            negative_control_result=WaveSixNegativeControlResult.PASSED,
            negative_control_summary="Negative control passed.",
            evidence_ids=("evidence-same-family",),
        )


def test_transfer_record_requires_future_reasoning_proof_ids() -> None:
    with pytest.raises(ValueError, match="future-reasoning proof ids"):
        WaveSixTransferNoveltyRecord(
            record_id="missing-future-proof",
            source_domain=_source_domain(),
            target_domain=_target_domain(),
            transferred_structure_id="structure-1",
            future_reasoning_proof_ids=(),
            expected_transfer_behavior="Apply corrected structure.",
            observed_target_behavior="Applied corrected structure.",
            novelty_pressure_kinds=(WaveSixNoveltyPressureKind.NEGATIVE_CONTROL,),
            negative_control_result=WaveSixNegativeControlResult.PASSED,
            negative_control_summary="Negative control passed.",
            evidence_ids=("evidence-missing-proof",),
        )


def test_transfer_record_requires_negative_control_pressure() -> None:
    with pytest.raises(ValueError, match="negative-control pressure"):
        WaveSixTransferNoveltyRecord(
            record_id="missing-negative-control",
            source_domain=_source_domain(),
            target_domain=_target_domain(),
            transferred_structure_id="structure-1",
            future_reasoning_proof_ids=("future-proof-1",),
            expected_transfer_behavior="Apply corrected structure.",
            observed_target_behavior="Applied corrected structure.",
            novelty_pressure_kinds=(WaveSixNoveltyPressureKind.DOMAIN_SHIFT,),
            negative_control_result=WaveSixNegativeControlResult.PASSED,
            negative_control_summary="Negative control passed.",
            evidence_ids=("evidence-missing-negative-control",),
        )


def test_transfer_record_rejects_agi_claim_and_autonomous_execution() -> None:
    with pytest.raises(ValueError, match="must not claim AGI"):
        WaveSixTransferNoveltyRecord(
            record_id="agi-claim",
            source_domain=_source_domain(),
            target_domain=_target_domain(),
            transferred_structure_id="structure-1",
            future_reasoning_proof_ids=("future-proof-1",),
            expected_transfer_behavior="Apply corrected structure.",
            observed_target_behavior="Applied corrected structure.",
            novelty_pressure_kinds=(WaveSixNoveltyPressureKind.NEGATIVE_CONTROL,),
            negative_control_result=WaveSixNegativeControlResult.PASSED,
            negative_control_summary="Negative control passed.",
            evidence_ids=("evidence-agi",),
            claims_agi=True,
        )

    with pytest.raises(ValueError, match="must not allow autonomous execution"):
        WaveSixTransferNoveltyRecord(
            record_id="autonomous-execution",
            source_domain=_source_domain(),
            target_domain=_target_domain(),
            transferred_structure_id="structure-1",
            future_reasoning_proof_ids=("future-proof-1",),
            expected_transfer_behavior="Apply corrected structure.",
            observed_target_behavior="Applied corrected structure.",
            novelty_pressure_kinds=(WaveSixNoveltyPressureKind.NEGATIVE_CONTROL,),
            negative_control_result=WaveSixNegativeControlResult.PASSED,
            negative_control_summary="Negative control passed.",
            evidence_ids=("evidence-auto",),
            allows_autonomous_execution=True,
        )


def test_transfer_novelty_ledger_accepts_supported_records() -> None:
    ledger = build_wave_six_transfer_novelty_ledger(
        ledger_id="transfer-ledger-1",
        records=(_record(record_id="transfer-b"), _record(record_id="transfer-a")),
        notes=("Cross-domain transfer is bounded and review-gated.",),
    )

    assert ledger.record_ids == ("transfer-a", "transfer-b")
    assert ledger.supported_record_ids == ("transfer-a", "transfer-b")
    assert ledger.blocked_record_ids == ()
    assert ledger.failed_negative_control_record_ids == ()
    assert ledger.has_required_transfer_support
    assert ledger.ready_for_wave_six_review
    assert ledger.fingerprint() == ledger.fingerprint()
    assert len(ledger.fingerprint()) == 64


def test_transfer_novelty_ledger_fails_without_negative_control_pass() -> None:
    ledger = WaveSixTransferNoveltyLedger(
        ledger_id="transfer-ledger-negative-control-fail",
        records=(
            _record(
                negative_control_result=WaveSixNegativeControlResult.FAILED,
            ),
        ),
    )

    assert ledger.failed_negative_control_record_ids == ("transfer-1",)
    assert ledger.supported_record_ids == ()
    assert not ledger.has_required_transfer_support
    assert not ledger.ready_for_wave_six_review


def test_transfer_novelty_ledger_blocks_on_blocking_record() -> None:
    ledger = WaveSixTransferNoveltyLedger(
        ledger_id="transfer-ledger-blocked",
        records=(_record(decision=WaveSixTransferDecision.BLOCK_CLAIM),),
    )

    assert ledger.blocked_record_ids == ("transfer-1",)
    assert not ledger.ready_for_wave_six_review


def test_transfer_novelty_ledger_rejects_duplicate_record_ids() -> None:
    record = _record()

    with pytest.raises(ValueError, match="Duplicate record_id"):
        WaveSixTransferNoveltyLedger(
            ledger_id="transfer-ledger-duplicate",
            records=(record, record),
        )
