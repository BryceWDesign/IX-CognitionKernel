import pytest

from ix_cognition_kernel.wave6_maturity_gate import (
    WaveSixMaturityBlocker,
    WaveSixMaturityDecision,
    WaveSixMaturityDecisionRecord,
    WaveSixMaturityGate,
    WaveSixMaturityStatus,
    build_wave_six_maturity_gate,
)


class _EvidencePackage:
    def __init__(
        self,
        *,
        ready: bool = True,
        blockers: tuple[object, ...] = (),
        overclaim_present: bool = False,
        fingerprint: str = "evidence-package-fingerprint",
    ) -> None:
        self._ready = ready
        self._blockers = blockers
        self._overclaim_present = overclaim_present
        self._fingerprint = fingerprint

    @property
    def ready_for_external_review(self) -> bool:
        return self._ready

    @property
    def blockers(self) -> tuple[object, ...]:
        return self._blockers

    @property
    def overclaim_present(self) -> bool:
        return self._overclaim_present

    def fingerprint(self) -> str:
        return self._fingerprint


class _ReviewScorecard:
    def __init__(
        self,
        *,
        ready: bool = True,
        blocking_item_ids: tuple[str, ...] = (),
        follow_up_item_ids: tuple[str, ...] = (),
        overclaim_present: bool = False,
        fingerprint: str = "review-scorecard-fingerprint",
    ) -> None:
        self._ready = ready
        self._blocking_item_ids = blocking_item_ids
        self._follow_up_item_ids = follow_up_item_ids
        self._overclaim_present = overclaim_present
        self._fingerprint = fingerprint

    @property
    def ready_for_external_review(self) -> bool:
        return self._ready

    @property
    def blocking_item_ids(self) -> tuple[str, ...]:
        return self._blocking_item_ids

    @property
    def follow_up_item_ids(self) -> tuple[str, ...]:
        return self._follow_up_item_ids

    @property
    def overclaim_present(self) -> bool:
        return self._overclaim_present

    def fingerprint(self) -> str:
        return self._fingerprint


class _ExternalValidationGate:
    def __init__(
        self,
        *,
        ready: bool = True,
        blockers: tuple[object, ...] = (),
        overclaim_present: bool = False,
        fingerprint: str = "external-validation-fingerprint",
    ) -> None:
        self._ready = ready
        self._blockers = blockers
        self._overclaim_present = overclaim_present
        self._fingerprint = fingerprint

    @property
    def ready_for_external_validation_review(self) -> bool:
        return self._ready

    @property
    def blockers(self) -> tuple[object, ...]:
        return self._blockers

    @property
    def overclaim_present(self) -> bool:
        return self._overclaim_present

    def fingerprint(self) -> str:
        return self._fingerprint


def _boundary_statement() -> str:
    return (
        "This Wave-6 measured system-level cognition package is ready for "
        "bounded review under human authority and independent review. It is not "
        "an AGI claim."
    )


def _gate(
    *,
    evidence_package: _EvidencePackage | None = None,
    review_scorecard: _ReviewScorecard | None = None,
    external_validation_gate: _ExternalValidationGate | None = None,
    claim_boundary_statement: str | None = None,
    claims_agi: bool = False,
) -> WaveSixMaturityGate:
    return WaveSixMaturityGate(
        gate_id="maturity-gate-1",
        evidence_package=evidence_package or _EvidencePackage(),
        review_scorecard=review_scorecard or _ReviewScorecard(),
        external_validation_gate=external_validation_gate
        or _ExternalValidationGate(),
        claim_boundary_statement=claim_boundary_statement or _boundary_statement(),
        human_authority_id="human-authority-1",
        independent_reviewer_id="independent-reviewer-1",
        claims_agi=claims_agi,
        notes=("This is bounded review readiness, not AGI achieved.",),
    )


def test_maturity_gate_is_ready_when_all_inputs_are_ready_and_bounded() -> None:
    gate = build_wave_six_maturity_gate(
        gate_id="maturity-gate-ready",
        evidence_package=_EvidencePackage(),
        review_scorecard=_ReviewScorecard(),
        external_validation_gate=_ExternalValidationGate(),
        claim_boundary_statement=_boundary_statement(),
        human_authority_id="human-authority-1",
        independent_reviewer_id="independent-reviewer-1",
        notes=("All late-stage Wave 6 inputs are ready for bounded review.",),
    )

    assert gate.blockers == ()
    assert gate.status is WaveSixMaturityStatus.READY_FOR_BOUNDED_WAVE_SIX_REVIEW
    assert gate.decision is (
        WaveSixMaturityDecision.ENTER_BOUNDED_MEASURED_COGNITION_REVIEW
    )
    assert gate.ready_for_bounded_wave_six_review
    assert gate.claim_boundary_statement_valid
    assert not gate.overclaim_present
    assert gate.fingerprint() == gate.fingerprint()
    assert len(gate.fingerprint()) == 64


def test_maturity_gate_needs_evidence_when_package_is_not_ready() -> None:
    gate = _gate(evidence_package=_EvidencePackage(ready=False))

    assert gate.blockers == (WaveSixMaturityBlocker.EVIDENCE_PACKAGE_NOT_READY,)
    assert gate.status is WaveSixMaturityStatus.NEEDS_MORE_EVIDENCE
    assert gate.decision is WaveSixMaturityDecision.CONTINUE_EVIDENCE_COLLECTION
    assert not gate.ready_for_bounded_wave_six_review


def test_maturity_gate_blocks_when_package_has_blockers() -> None:
    gate = _gate(
        evidence_package=_EvidencePackage(
            ready=False,
            blockers=("missing-required-surface",),
        )
    )

    assert gate.evidence_package_blocked
    assert gate.blockers == (WaveSixMaturityBlocker.EVIDENCE_PACKAGE_BLOCKED,)
    assert gate.status is WaveSixMaturityStatus.BLOCKED
    assert gate.decision is WaveSixMaturityDecision.BLOCK_WAVE_SIX_INTERPRETATION


def test_maturity_gate_needs_evidence_when_scorecard_is_not_ready() -> None:
    gate = _gate(review_scorecard=_ReviewScorecard(ready=False))

    assert gate.blockers == (WaveSixMaturityBlocker.REVIEW_SCORECARD_NOT_READY,)
    assert gate.status is WaveSixMaturityStatus.NEEDS_MORE_EVIDENCE
    assert gate.decision is WaveSixMaturityDecision.CONTINUE_EVIDENCE_COLLECTION


def test_maturity_gate_blocks_when_scorecard_has_blocking_items() -> None:
    gate = _gate(
        review_scorecard=_ReviewScorecard(
            ready=False,
            blocking_item_ids=("scorecard-blocker-1",),
        )
    )

    assert gate.review_scorecard_blocked
    assert gate.blockers == (WaveSixMaturityBlocker.REVIEW_SCORECARD_BLOCKED,)
    assert gate.status is WaveSixMaturityStatus.BLOCKED
    assert gate.decision is WaveSixMaturityDecision.BLOCK_WAVE_SIX_INTERPRETATION


def test_maturity_gate_needs_evidence_when_external_validation_not_ready() -> None:
    gate = _gate(external_validation_gate=_ExternalValidationGate(ready=False))

    assert gate.blockers == (WaveSixMaturityBlocker.EXTERNAL_VALIDATION_NOT_READY,)
    assert gate.status is WaveSixMaturityStatus.NEEDS_MORE_EVIDENCE
    assert gate.decision is WaveSixMaturityDecision.CONTINUE_EVIDENCE_COLLECTION


def test_maturity_gate_blocks_when_external_validation_has_blockers() -> None:
    gate = _gate(
        external_validation_gate=_ExternalValidationGate(
            ready=False,
            blockers=("external-validation-blocker-1",),
        )
    )

    assert gate.external_validation_blocked
    assert gate.blockers == (WaveSixMaturityBlocker.EXTERNAL_VALIDATION_BLOCKED,)
    assert gate.status is WaveSixMaturityStatus.BLOCKED
    assert gate.decision is WaveSixMaturityDecision.BLOCK_WAVE_SIX_INTERPRETATION


def test_maturity_gate_blocks_on_overclaim_from_gate_or_inputs() -> None:
    direct_overclaim = _gate(claims_agi=True)

    assert direct_overclaim.overclaim_present
    assert WaveSixMaturityBlocker.OVERCLAIM_PRESENT in direct_overclaim.blockers
    assert direct_overclaim.status is WaveSixMaturityStatus.BLOCKED

    package_overclaim = _gate(
        evidence_package=_EvidencePackage(overclaim_present=True)
    )

    assert package_overclaim.overclaim_present
    assert WaveSixMaturityBlocker.OVERCLAIM_PRESENT in package_overclaim.blockers
    assert package_overclaim.status is WaveSixMaturityStatus.BLOCKED


def test_maturity_gate_blocks_on_invalid_claim_boundary_statement() -> None:
    gate = _gate(claim_boundary_statement="Wave 6 is done.")

    assert not gate.claim_boundary_statement_valid
    assert gate.blockers == (
        WaveSixMaturityBlocker.CLAIM_BOUNDARY_STATEMENT_INVALID,
    )
    assert gate.status is WaveSixMaturityStatus.BLOCKED
    assert gate.decision is WaveSixMaturityDecision.BLOCK_WAVE_SIX_INTERPRETATION


def test_maturity_gate_canonical_payload_indexes_input_fingerprints() -> None:
    gate = _gate(
        evidence_package=_EvidencePackage(fingerprint="package-fingerprint-1"),
        review_scorecard=_ReviewScorecard(fingerprint="scorecard-fingerprint-1"),
        external_validation_gate=_ExternalValidationGate(
            fingerprint="external-validation-fingerprint-1"
        ),
    )
    payload = gate.canonical_payload()

    assert payload["evidence_package_fingerprint"] == "package-fingerprint-1"
    assert payload["review_scorecard_fingerprint"] == "scorecard-fingerprint-1"
    assert (
        payload["external_validation_gate_fingerprint"]
        == "external-validation-fingerprint-1"
    )
    assert payload["status"] == "ready-for-bounded-wave-six-review"


def test_maturity_decision_record_wraps_ready_gate() -> None:
    gate = _gate()
    record = WaveSixMaturityDecisionRecord(
        record_id="maturity-decision-record-1",
        maturity_gate=gate,
        decision_rationale="All required gates are ready for bounded review.",
        reviewer_notes=("Human authority remains required.",),
    )

    assert record.ready_for_bounded_review
    assert not record.blocks_wave_six_interpretation
    assert record.fingerprint() == record.fingerprint()
    assert len(record.fingerprint()) == 64
    assert record.canonical_payload()["decision"] == (
        WaveSixMaturityDecision.ENTER_BOUNDED_MEASURED_COGNITION_REVIEW.value
    )


def test_maturity_decision_record_wraps_blocked_gate() -> None:
    gate = _gate(claim_boundary_statement="Wave 6 is done.")
    record = WaveSixMaturityDecisionRecord(
        record_id="maturity-decision-record-blocked",
        maturity_gate=gate,
        decision_rationale="Invalid boundary statement blocks interpretation.",
        reviewer_notes=("No AGI claim may be made.",),
    )

    assert not record.ready_for_bounded_review
    assert record.blocks_wave_six_interpretation


def test_maturity_gate_requires_non_empty_authority_and_review_metadata() -> None:
    with pytest.raises(ValueError, match="gate_id must not be empty"):
        WaveSixMaturityGate(
            gate_id=" ",
            evidence_package=_EvidencePackage(),
            review_scorecard=_ReviewScorecard(),
            external_validation_gate=_ExternalValidationGate(),
            claim_boundary_statement=_boundary_statement(),
            human_authority_id="human-authority-1",
            independent_reviewer_id="independent-reviewer-1",
        )

    with pytest.raises(ValueError, match="human_authority_id must not be empty"):
        WaveSixMaturityGate(
            gate_id="maturity-gate-invalid",
            evidence_package=_EvidencePackage(),
            review_scorecard=_ReviewScorecard(),
            external_validation_gate=_ExternalValidationGate(),
            claim_boundary_statement=_boundary_statement(),
            human_authority_id=" ",
            independent_reviewer_id="independent-reviewer-1",
        )


def test_maturity_decision_record_requires_reviewer_notes() -> None:
    with pytest.raises(ValueError, match="require reviewer notes"):
        WaveSixMaturityDecisionRecord(
            record_id="maturity-decision-record-no-notes",
            maturity_gate=_gate(),
            decision_rationale="Missing reviewer notes should fail.",
            reviewer_notes=(),
        )
