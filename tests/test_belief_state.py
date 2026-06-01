import pytest

from ix_cognition_kernel.state import (
    BeliefDisposition,
    BeliefRecord,
    BeliefState,
    ClaimRecord,
    EvidenceRecord,
    EvidenceStatus,
    UncertaintyStatus,
)


def verified_evidence() -> EvidenceRecord:
    return EvidenceRecord(
        evidence_id="ev-belief-001",
        summary="A passing state test supports the represented belief.",
        status=EvidenceStatus.VERIFIED,
        sources=("tests/test_belief_state.py",),
        supports_claim_ids=("claim-belief-001",),
    )


def active_claim() -> ClaimRecord:
    return ClaimRecord(
        claim_id="claim-belief-001",
        statement="IX-CognitionKernel can represent a first-class belief record.",
        confidence=0.91,
        uncertainty=UncertaintyStatus.KNOWN,
        evidence_ids=("ev-belief-001",),
    )


def active_belief() -> BeliefRecord:
    return BeliefRecord(
        belief_id="belief-001",
        claim=active_claim(),
        provenance=("manual-wave-1-design-review",),
        rationale="The claim is represented as structured state with evidence links.",
        disposition=BeliefDisposition.ACTIVE,
    )


def test_belief_record_exposes_claim_confidence_uncertainty_and_evidence() -> None:
    belief = active_belief()

    assert belief.claim_id == "claim-belief-001"
    assert belief.confidence == 0.91
    assert belief.uncertainty is UncertaintyStatus.KNOWN
    assert belief.evidence_ids == ("ev-belief-001",)
    assert belief.requires_evidence is False
    assert belief.is_blocked is False


def test_belief_record_requires_provenance() -> None:
    with pytest.raises(ValueError, match="provenance"):
        BeliefRecord(
            belief_id="belief-missing-provenance",
            claim=active_claim(),
            provenance=(),
            rationale="Missing provenance should be rejected.",
            disposition=BeliefDisposition.ACTIVE,
        )


def test_active_belief_cannot_hide_blocking_uncertainty() -> None:
    disputed_claim = ClaimRecord(
        claim_id="claim-disputed",
        statement="Disputed belief cannot be treated as active.",
        confidence=0.8,
        uncertainty=UncertaintyStatus.DISPUTED,
        evidence_ids=("ev-belief-001",),
    )

    with pytest.raises(ValueError, match="blocking uncertainty"):
        BeliefRecord(
            belief_id="belief-disputed",
            claim=disputed_claim,
            provenance=("red-team-review",),
            rationale="Disputed claims must be blocked or retired, not active.",
            disposition=BeliefDisposition.ACTIVE,
        )


def test_belief_state_rejects_duplicate_belief_ids() -> None:
    belief = active_belief()

    with pytest.raises(ValueError, match="Duplicate belief_id"):
        BeliefState(
            beliefs=(belief, belief),
            evidence=(verified_evidence(),),
        )


def test_belief_state_rejects_duplicate_claim_ids() -> None:
    first = active_belief()
    second = BeliefRecord(
        belief_id="belief-002",
        claim=active_claim(),
        provenance=("second-review",),
        rationale="The same claim cannot appear as a second durable belief.",
        disposition=BeliefDisposition.ACTIVE,
    )

    with pytest.raises(ValueError, match="Duplicate belief claim_id"):
        BeliefState(
            beliefs=(first, second),
            evidence=(verified_evidence(),),
        )


def test_belief_state_returns_actionable_claims_and_lookup() -> None:
    state = BeliefState(
        beliefs=(active_belief(),),
        evidence=(verified_evidence(),),
    )

    assert state.belief_by_id("belief-001").claim_id == "claim-belief-001"
    assert tuple(claim.claim_id for claim in state.actionable_claims) == (
        "claim-belief-001",
    )
    assert state.beliefs_requiring_evidence == ()
    assert state.blocked_beliefs == ()


def test_belief_state_lists_beliefs_requiring_evidence() -> None:
    claim = ClaimRecord(
        claim_id="claim-needs-evidence",
        statement="Unknown claims remain visible but not actionable.",
        confidence=0.4,
        uncertainty=UncertaintyStatus.UNKNOWN,
        evidence_ids=(),
    )
    belief = BeliefRecord(
        belief_id="belief-needs-evidence",
        claim=claim,
        provenance=("model-proposal",),
        rationale="The belief is tracked only so missing evidence stays visible.",
        disposition=BeliefDisposition.NEEDS_EVIDENCE,
    )
    state = BeliefState(beliefs=(belief,), evidence=())

    assert state.actionable_claims == ()
    assert state.beliefs_requiring_evidence == (belief,)


def test_belief_state_lists_blocked_beliefs() -> None:
    claim = ClaimRecord(
        claim_id="claim-unsafe",
        statement="Unsafe claims must remain blocked.",
        confidence=0.7,
        uncertainty=UncertaintyStatus.UNSAFE_TO_ACT,
        evidence_ids=(),
    )
    belief = BeliefRecord(
        belief_id="belief-unsafe",
        claim=claim,
        provenance=("hazard-review",),
        rationale="Unsafe-to-act uncertainty prevents actionability.",
        disposition=BeliefDisposition.BLOCKED,
    )
    state = BeliefState(beliefs=(belief,), evidence=())

    assert state.actionable_claims == ()
    assert state.blocked_beliefs == (belief,)


def test_unknown_belief_lookup_is_rejected() -> None:
    state = BeliefState(
        beliefs=(active_belief(),),
        evidence=(verified_evidence(),),
    )

    with pytest.raises(ValueError, match="Unknown belief_id"):
        state.belief_by_id("belief-missing")
