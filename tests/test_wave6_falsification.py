import pytest

from ix_cognition_kernel.wave6_falsification import (
    WaveSixFalsificationDecision,
    WaveSixFalsificationLedger,
    WaveSixFalsificationOutcome,
    WaveSixFalsificationProbe,
    WaveSixFalsificationProbeKind,
    WaveSixFalsificationResult,
    build_wave_six_falsification_ledger,
)


def _probe(
    *,
    probe_id: str = "probe-1",
    probe_kind: WaveSixFalsificationProbeKind = (
        WaveSixFalsificationProbeKind.NEGATIVE_CONTROL
    ),
) -> WaveSixFalsificationProbe:
    return WaveSixFalsificationProbe(
        probe_id=probe_id,
        probe_kind=probe_kind,
        claim_under_test="Bounded future reasoning change survived review pressure.",
        falsification_question=(
            "Does the corrected reasoning falsely transfer when the causal "
            "precondition is absent?"
        ),
        expected_failure_mode=(
            "The system should withhold the transfer claim when the precondition "
            "is missing."
        ),
        method_summary="Run a negative-control target with the causal feature removed.",
        evidence_ids=(f"evidence-{probe_id}",),
    )


def _result(
    *,
    result_id: str = "result-1",
    probe: WaveSixFalsificationProbe | None = None,
    outcome: WaveSixFalsificationOutcome = WaveSixFalsificationOutcome.SURVIVED,
    decision: WaveSixFalsificationDecision = (
        WaveSixFalsificationDecision.ACCEPT_FOR_WAVE_SIX_REVIEW
    ),
    contradiction_evidence_ids: tuple[str, ...] = (),
) -> WaveSixFalsificationResult:
    return WaveSixFalsificationResult(
        result_id=result_id,
        probe=probe or _probe(),
        observed_result_summary=(
            "The system withheld the transfer claim for the negative-control case."
        ),
        outcome=outcome,
        decision=decision,
        evidence_ids=(f"evidence-{result_id}",),
        affected_claim_ids=("claim-transfer-survival",),
        contradiction_evidence_ids=contradiction_evidence_ids,
        reviewer_notes=("No AGI claim is made by this result.",),
    )


def test_falsification_probe_is_evidence_bound_and_fingerprinted() -> None:
    probe = _probe()

    assert probe.is_negative_control
    assert probe.evidence_ids == ("evidence-probe-1",)
    assert probe.fingerprint() == probe.fingerprint()
    assert len(probe.fingerprint()) == 64


def test_falsification_result_supports_bounded_claim_survival() -> None:
    result = _result()

    assert result.evidence_bound
    assert result.survived_probe
    assert result.accepted_for_review
    assert not result.blocks_claim
    assert result.supports_bounded_claim_survival
    assert result.combined_evidence_ids == (
        "evidence-probe-1",
        "evidence-result-1",
    )
    assert result.fingerprint() == result.fingerprint()
    assert len(result.fingerprint()) == 64


def test_falsified_result_requires_contradiction_evidence_and_blocks_claim() -> None:
    result = _result(
        outcome=WaveSixFalsificationOutcome.FALSIFIED,
        decision=WaveSixFalsificationDecision.BLOCK_CLAIM,
        contradiction_evidence_ids=("contradiction-1",),
    )

    assert result.blocks_claim
    assert not result.supports_bounded_claim_survival
    assert result.combined_evidence_ids == (
        "evidence-probe-1",
        "evidence-result-1",
        "contradiction-1",
    )


def test_falsified_result_rejects_missing_contradiction_evidence() -> None:
    with pytest.raises(ValueError, match="contradiction evidence"):
        _result(
            outcome=WaveSixFalsificationOutcome.FALSIFIED,
            decision=WaveSixFalsificationDecision.BLOCK_CLAIM,
        )


def test_falsified_result_must_block_claim() -> None:
    with pytest.raises(ValueError, match="must block the claim"):
        _result(
            outcome=WaveSixFalsificationOutcome.FALSIFIED,
            decision=WaveSixFalsificationDecision.NEEDS_MORE_EVIDENCE,
            contradiction_evidence_ids=("contradiction-1",),
        )


def test_safety_gate_blocked_result_must_block_claim() -> None:
    with pytest.raises(ValueError, match="Safety-gate-blocked"):
        _result(
            outcome=WaveSixFalsificationOutcome.BLOCKED_BY_SAFETY_GATE,
            decision=WaveSixFalsificationDecision.NEEDS_MORE_EVIDENCE,
        )


def test_falsification_probe_rejects_agi_claim_and_autonomous_execution() -> None:
    with pytest.raises(ValueError, match="must not claim AGI"):
        WaveSixFalsificationProbe(
            probe_id="agi-probe",
            probe_kind=WaveSixFalsificationProbeKind.CONTRADICTION_PROBE,
            claim_under_test="Invalid AGI claim.",
            falsification_question="Can this claim survive contradiction?",
            expected_failure_mode="The claim fails.",
            method_summary="Probe the invalid claim.",
            evidence_ids=("evidence-agi-probe",),
            claims_agi=True,
        )

    with pytest.raises(ValueError, match="must not allow autonomous execution"):
        WaveSixFalsificationProbe(
            probe_id="auto-probe",
            probe_kind=WaveSixFalsificationProbeKind.CONTRADICTION_PROBE,
            claim_under_test="Invalid autonomous claim.",
            falsification_question="Can this claim survive contradiction?",
            expected_failure_mode="The claim fails.",
            method_summary="Probe the invalid claim.",
            evidence_ids=("evidence-auto-probe",),
            allows_autonomous_execution=True,
        )


def test_falsification_ledger_accepts_survived_negative_control() -> None:
    ledger = build_wave_six_falsification_ledger(
        ledger_id="falsification-ledger-1",
        results=(_result(result_id="result-b"), _result(result_id="result-a")),
        notes=("Falsification must be allowed to block Wave 6 claims.",),
    )

    assert ledger.result_ids == ("result-a", "result-b")
    assert ledger.survived_result_ids == ("result-a", "result-b")
    assert ledger.negative_control_result_ids == ("result-a", "result-b")
    assert ledger.survived_negative_control_result_ids == (
        "result-a",
        "result-b",
    )
    assert ledger.blocking_result_ids == ()
    assert ledger.inconclusive_result_ids == ()
    assert ledger.has_required_negative_control
    assert ledger.has_required_survival
    assert ledger.ready_for_wave_six_review
    assert ledger.fingerprint() == ledger.fingerprint()
    assert len(ledger.fingerprint()) == 64


def test_falsification_ledger_fails_without_negative_control() -> None:
    ledger = WaveSixFalsificationLedger(
        ledger_id="falsification-ledger-no-negative-control",
        results=(
            _result(
                probe=_probe(
                    probe_id="contradiction-probe",
                    probe_kind=WaveSixFalsificationProbeKind.CONTRADICTION_PROBE,
                )
            ),
        ),
    )

    assert ledger.negative_control_result_ids == ()
    assert not ledger.has_required_negative_control
    assert not ledger.ready_for_wave_six_review


def test_falsification_ledger_blocks_on_falsified_result() -> None:
    ledger = WaveSixFalsificationLedger(
        ledger_id="falsification-ledger-blocked",
        results=(
            _result(
                outcome=WaveSixFalsificationOutcome.FALSIFIED,
                decision=WaveSixFalsificationDecision.BLOCK_CLAIM,
                contradiction_evidence_ids=("contradiction-1",),
            ),
        ),
    )

    assert ledger.blocking_result_ids == ("result-1",)
    assert not ledger.ready_for_wave_six_review


def test_falsification_ledger_tracks_inconclusive_results() -> None:
    ledger = WaveSixFalsificationLedger(
        ledger_id="falsification-ledger-inconclusive",
        results=(
            _result(
                outcome=WaveSixFalsificationOutcome.INCONCLUSIVE,
                decision=WaveSixFalsificationDecision.NEEDS_MORE_EVIDENCE,
            ),
        ),
        require_negative_control=False,
    )

    assert ledger.inconclusive_result_ids == ("result-1",)
    assert ledger.survived_result_ids == ()
    assert not ledger.ready_for_wave_six_review


def test_falsification_ledger_rejects_duplicate_result_ids() -> None:
    result = _result()

    with pytest.raises(ValueError, match="Duplicate result_id"):
        WaveSixFalsificationLedger(
            ledger_id="falsification-ledger-duplicate",
            results=(result, result),
        )
