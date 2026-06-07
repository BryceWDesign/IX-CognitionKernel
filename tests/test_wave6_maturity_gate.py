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
        blockers: tuple[str, ...] = (),
        overclaim_present: bool = False,
    ) -> None:
        self._ready = ready
        self._blockers = blockers
        self._overclaim_present = overclaim_present

    @property
    def ready_for_external_review(self) -> bool:
        return self._ready

    @property
    def blockers(self) -> tuple[str, ...]:
        return self._blockers

    @property
    def overclaim_present(self) -> bool:
        return self._overclaim_present

    def fingerprint(self) -> str:
        return "evidence-package-fingerprint"


class _ReviewScorecard:
    def __init__(
        self,
        *,
        ready: bool = True,
        blocking_item_ids: tuple[str, ...] = (),
        follow_up_item_ids: tuple[str, ...] = (),
        overclaim_present: bool = False,
    ) -> None:
        self._ready = ready
        self._blocking_item_ids = blocking_item_ids
        self._follow_up_item_ids = follow_up_item_ids
        self._overclaim_present = overclaim_present

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
        return "review-scorecard-fingerprint"


class _ExternalValidationGate:
    def __init__(
        self,
        *,
        ready: bool = True,
        blockers: tuple[str, ...] = (),
        overclaim_present: bool = False,
    ) -> None:
        self._ready = ready
        self._blockers = blockers
        self._overclaim_present = overclaim_present

    @property
    def ready_for_external_validation_review(self) -> bool:
        return self._ready

    @property
    def blockers(self) -> tuple[str, ...]:
        return self._blockers

    @property
    def overclaim_present(self) -> bool:
        return self._overclaim_present

    def fingerprint(self) -> str:
        return "external-validation-fingerprint"


def _boundary_statement() -> str:
    return (
        "This is a Wave-6 measured system-level cognition attempt under human "
        "authority and independent review. It is not an AGI claim."
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
        external_validation_gate=external_validation_gate or _ExternalValidationGate(),
        claim_boundary_statement=claim_boundary_statement or _boundary_statement(),
        human_authority_id="human-authority-1",
        independent_reviewer_id="independent-reviewer-1",
        claims_agi=claims_agi,
        notes=("Ready means bounded review, not AGI achieved.",),
    )


def test_maturity_gate_enters_bounded_review_when_every_surface_is_ready() -> None:
    gate = build_wave_six_maturity_gate(
        gate_id="maturity-gate-ready",
        evidence_package=_EvidencePackage(),
        review_scorecard=_ReviewScorecard(),
        external_validation_gate=_ExternalValidationGate(),
        claim_boundary_statement=_boundary_statement(),
        human_authority_id="human-authority-1",
        independent_reviewer_id="independent-reviewer-1",
        notes=("External reviewers still decide whether evidence survives.",),
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


def test_maturity_gate_needs_more_evidence_when_package_is_not_ready() -> None:
    gate = _gate(evidence_package=_EvidencePackage(ready=False))

    assert gate.blockers == (WaveSixMaturityBlocker.EVIDENCE_PACKAGE_NOT_READY,)
    assert gate.status is WaveSixMaturityStatus.NEEDS_MORE_EVIDENCE
    assert gate.decision is WaveSixMaturityDecision.CONTINUE_EVIDENCE_COLLECTION
    assert not gate.ready_for_bounded_wave_six_review


def test_maturity_gate_blocks_when_package_reports_blockers() -> None:
    gate = _gate(
        evidence_package=_EvidencePackage(
            ready=False,
            blockers=("claim-blocked",),
        )
    )

    assert WaveSixMaturityBlocker.EVIDENCE_PACKAGE_BLOCKED in gate.blockers
    assert gate.status is WaveSixMaturityStatus.BLOCKED
    assert gate.decision is WaveSixMaturityDecision.BLOCK_WAVE_SIX_INTERPRETATION


def test_maturity_gate_blocks_on_scorecard_blocking_item() -> None:
    gate = _gate(
        review_scorecard=_ReviewScorecard(
            ready=False,
            blocking_item_ids=("item-falsification-survival",),
        )
    )

    assert WaveSixMaturityBlocker.REVIEW_SCORECARD_BLOCKED in gate.blockers
    assert gate.status is WaveSixMaturityStatus.BLOCKED


def test_maturity_gate_needs_more_evidence_on_scorecard_follow_up() -> None:
    gate = _gate(
        review_scorecard=_ReviewScorecard(
            ready=False,
            follow_up_item_ids=("item-cross-domain-transfer",),
        )
    )

    assert WaveSixMaturityBlocker.REVIEW_SCORECARD_NOT_READY in gate.blockers
    assert gate.status is WaveSixMaturityStatus.NEEDS_MORE_EVIDENCE


def test_maturity_gate_blocks_on_external_validation_blocker() -> None:
    gate = _gate(
        external_validation_gate=_ExternalValidationGate(
            ready=False,
            blockers=("replication-step-blocked",),
        )
    )

    assert WaveSixMaturityBlocker.EXTERNAL_VALIDATION_BLOCKED in gate.blockers
    assert gate.status is WaveSixMaturityStatus.BLOCKED


def test_maturity_gate_needs_more_evidence_when_external_validation_not_ready() -> None:
    gate = _gate(external_validation_gate=_ExternalValidationGate(ready=False))

    assert WaveSixMaturityBlocker.EXTERNAL_VALIDATION_NOT_READY in gate.blockers
    assert gate.status is WaveSixMaturityStatus.NEEDS_MORE_EVIDENCE


def test_maturity_gate_blocks_on_overclaim_from_any_surface() -> None:
    assert _gate(claims_agi=True).status is WaveSixMaturityStatus.BLOCKED
    assert _gate(evidence_package=_EvidencePackage(overclaim_present=True)).status is (
        WaveSixMaturityStatus.BLOCKED
    )
    assert _gate(review_scorecard=_ReviewScorecard(overclaim_present=True)).status is (
        WaveSixMaturityStatus.BLOCKED
    )
    assert _gate(
        external_validation_gate=_ExternalValidationGate(overclaim_present=True)
    ).status is WaveSixMaturityStatus.BLOCKED


def test_maturity_gate_blocks_invalid_claim_boundary_statement() -> None:
    gate = _gate(claim_boundary_statement="Wave 6 is ready.")

    assert WaveSixMaturityBlocker.CLAIM_BOUNDARY_STATEMENT_INVALID in gate.blockers
    assert gate.status is WaveSixMaturityStatus.BLOCKED
    assert not gate.claim_boundary_statement_valid


def test_maturity_gate_rejects_empty_identity_fields() -> None:
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
            gate_id="maturity-gate",
            evidence_package=_EvidencePackage(),
            review_scorecard=_ReviewScorecard(),
            external_validation_gate=_ExternalValidationGate(),
            claim_boundary_statement=_boundary_statement(),
            human_authority_id=" ",
            independent_reviewer_id="independent-reviewer-1",
        )


def test_maturity_decision_record_captures_final_gate_decision() -> None:
    record = WaveSixMaturityDecisionRecord(
        record_id="decision-record-1",
        maturity_gate=_gate(),
        decision_rationale=(
            "All required evidence surfaces are ready for bounded Wave 6 review."
        ),
        reviewer_notes=("This remains a review decision, not an AGI claim.",),
    )

    assert record.ready_for_bounded_review
    assert not record.blocks_wave_six_interpretation
    assert record.fingerprint() == record.fingerprint()
    assert len(record.fingerprint()) == 64


def test_maturity_decision_record_requires_reviewer_notes() -> None:
    with pytest.raises(ValueError, match="require reviewer notes"):
        WaveSixMaturityDecisionRecord(
            record_id="decision-record-no-notes",
            maturity_gate=_gate(),
            decision_rationale="Missing reviewer notes is invalid.",
            reviewer_notes=(),
        )
