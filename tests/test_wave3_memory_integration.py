import pytest

from ix_cognition_kernel.agents import ArtifactKind
from ix_cognition_kernel.memory import (
    MemoryCandidate,
    MemoryCandidateKind,
    MemoryQuarantineLedger,
    MemoryValidationRecord,
    MemoryValidationStatus,
    evaluate_memory_quarantine,
)
from ix_cognition_kernel.outcome import (
    OutcomeLearningLedger,
    OutcomeLearningRecord,
    OutcomeLearningStatus,
    OutcomePressure,
)
from ix_cognition_kernel.wave3_agent_artifacts import (
    RoleArtifactAuthority,
    RoleArtifactBundle,
    RoleArtifactRecord,
    RoleArtifactStatus,
    complete_role_artifact_record,
)
from ix_cognition_kernel.wave3_contracts import (
    WaveThreeArtifactKind,
    WaveThreeAuthorityState,
)
from ix_cognition_kernel.wave3_memory_integration import (
    DEFAULT_MEMORY_ROLE_REVIEW_SCOPE,
    MEMORY_REVIEWER_ROLE_ID,
    MemoryRoleDecisionBundle,
    MemoryRoleDecisionRecord,
    MemoryRoleDecisionStatus,
)


def accepted_outcome(outcome_id: str = "outcome-001") -> OutcomeLearningRecord:
    return OutcomeLearningRecord(
        outcome_id=outcome_id,
        summary="Accepted outcome learning supports a memory candidate.",
        status=OutcomeLearningStatus.ACCEPTED,
        pressure=OutcomePressure.CONFIRMED,
        belief_revision_ids=("revision-001",),
        causal_revision_ids=("causal-revision-001",),
        prediction_comparison_ids=("comparison-001",),
        evidence_ids=("ev-outcome-001",),
        learning_summary="Outcome evidence linked belief and causal revisions.",
        reasons=("Outcome learning was accepted with evidence.",),
    )


def memory_candidate(
    candidate_id: str = "memory-candidate-001",
    *,
    confidence: float = 0.82,
    evidence_ids: tuple[str, ...] = ("ev-memory-001",),
    source_outcome_ids: tuple[str, ...] = ("outcome-001",),
    contradiction_ids: tuple[str, ...] = (),
    proposed_audit_index: int = 0,
) -> MemoryCandidate:
    return MemoryCandidate(
        candidate_id=candidate_id,
        kind=MemoryCandidateKind.OUTCOME_SUMMARY,
        content="A validated outcome can be reused as a bounded memory summary.",
        provenance=("wave-2-memory-quarantine",),
        evidence_ids=evidence_ids,
        source_outcome_ids=source_outcome_ids,
        confidence=confidence,
        proposed_audit_index=proposed_audit_index,
        contradiction_ids=contradiction_ids,
    )


def memory_ledger(
    *candidates: MemoryCandidate,
    current_audit_index: int = 1,
) -> MemoryQuarantineLedger:
    return evaluate_memory_quarantine(
        candidates=candidates or (memory_candidate(),),
        outcome_ledger=OutcomeLearningLedger(records=(accepted_outcome(),)),
        current_audit_index=current_audit_index,
    )


def role_bundle(
    required_role_ids: tuple[str, ...] = DEFAULT_MEMORY_ROLE_REVIEW_SCOPE,
) -> RoleArtifactBundle:
    return RoleArtifactBundle(
        bundle_id="memory-role-bundle-001",
        records=tuple(
            complete_role_artifact_record(
                role_id, evidence_ids=(f"role-evidence:{role_id}",)
            )
            for role_id in required_role_ids
        ),
        required_role_ids=required_role_ids,
    )


def ready_decision(
    decision_id: str = "memory-decision-001",
) -> MemoryRoleDecisionRecord:
    return MemoryRoleDecisionRecord(
        decision_id=decision_id,
        memory_ledger=memory_ledger(),
        role_artifact_bundle=role_bundle(),
        evidence_ids=(f"decision-evidence:{decision_id}",),
    )


def test_memory_role_review_scope_is_locked() -> None:
    assert MEMORY_REVIEWER_ROLE_ID == "memory-integrity-specialist"
    assert DEFAULT_MEMORY_ROLE_REVIEW_SCOPE == (
        "memory-integrity-specialist",
        "learning-archivist",
        "skeptic-red-team",
        "data-provenance-specialist",
    )


def test_ready_memory_role_decision_is_reviewable_not_persistent() -> None:
    decision = ready_decision()

    assert decision.status is MemoryRoleDecisionStatus.READY_FOR_HUMAN_REVIEW
    assert decision.ready_for_human_review is True
    assert decision.may_request_memory_persistence_review is True
    assert decision.permits_automatic_memory_write is False
    assert decision.permits_automatic_execution is False
    assert (
        decision.human_authority_state is WaveThreeAuthorityState.HUMAN_REVIEW_REQUIRED
    )
    assert decision.accepted_candidate_ids == ("memory-candidate-001",)
    assert decision.readiness_gaps == ()
    assert decision.blocking_gaps == ()
    assert "automatic memory writes are not permitted" in decision.review_summary


def test_memory_role_decision_requires_memory_integrity_specialist_scope() -> None:
    with pytest.raises(ValueError, match="require memory-integrity-specialist"):
        MemoryRoleDecisionRecord(
            decision_id="memory-decision-001",
            memory_ledger=memory_ledger(),
            role_artifact_bundle=role_bundle(("learning-archivist",)),
            required_role_ids=("learning-archivist",),
            evidence_ids=("decision-evidence",),
        )


def test_memory_role_decision_requires_memory_integrity_reviewer() -> None:
    with pytest.raises(ValueError, match="must be reviewed by"):
        MemoryRoleDecisionRecord(
            decision_id="memory-decision-001",
            memory_ledger=memory_ledger(),
            role_artifact_bundle=role_bundle(),
            evidence_ids=("decision-evidence",),
            reviewer_role_id="learning-archivist",
        )


def test_memory_role_decision_rejects_validation_from_wrong_role() -> None:
    ledger = MemoryQuarantineLedger(
        candidates=(memory_candidate(),),
        validations=(
            MemoryValidationRecord(
                validation_id="memory-validation-001",
                candidate_id="memory-candidate-001",
                status=MemoryValidationStatus.ACCEPTED,
                evidence_ids=("ev-memory-001",),
                outcome_ids=("outcome-001",),
                reviewer_role_id="learning-archivist",
                reasons=("Wrong reviewer role should fail closed.",),
            ),
        ),
    )

    with pytest.raises(ValueError, match="Memory validation records must be reviewed"):
        MemoryRoleDecisionRecord(
            decision_id="memory-decision-001",
            memory_ledger=ledger,
            role_artifact_bundle=role_bundle(),
            evidence_ids=("decision-evidence",),
        )


def test_quarantined_memory_needs_evidence_before_review() -> None:
    decision = MemoryRoleDecisionRecord(
        decision_id="memory-decision-001",
        memory_ledger=memory_ledger(memory_candidate(evidence_ids=())),
        role_artifact_bundle=role_bundle(),
        evidence_ids=("decision-evidence",),
    )

    assert decision.status is MemoryRoleDecisionStatus.NEEDS_EVIDENCE
    assert decision.ready_for_human_review is False
    assert decision.may_request_memory_persistence_review is False
    assert decision.quarantined_candidate_ids == ("memory-candidate-001",)
    assert (
        "memory candidates still quarantined: memory-candidate-001"
        in decision.readiness_gaps
    )


def test_rejected_memory_blocks_memory_role_decision() -> None:
    decision = MemoryRoleDecisionRecord(
        decision_id="memory-decision-001",
        memory_ledger=memory_ledger(
            memory_candidate(contradiction_ids=("contradiction-001",))
        ),
        role_artifact_bundle=role_bundle(),
        evidence_ids=("decision-evidence",),
    )

    assert decision.status is MemoryRoleDecisionStatus.BLOCKED
    assert decision.ready_for_human_review is False
    assert decision.human_authority_state is WaveThreeAuthorityState.BLOCKED
    assert decision.rejected_candidate_ids == ("memory-candidate-001",)
    assert decision.blocking_gaps == (
        "memory candidates rejected: memory-candidate-001",
    )


def test_expired_memory_blocks_memory_role_decision() -> None:
    decision = MemoryRoleDecisionRecord(
        decision_id="memory-decision-001",
        memory_ledger=memory_ledger(memory_candidate(), current_audit_index=6),
        role_artifact_bundle=role_bundle(),
        evidence_ids=("decision-evidence",),
    )

    assert decision.status is MemoryRoleDecisionStatus.BLOCKED
    assert decision.expired_candidate_ids == ("memory-candidate-001",)
    assert decision.blocking_gaps == (
        "memory candidates expired: memory-candidate-001",
    )


def test_incomplete_memory_integrity_role_blocks_persistence_review() -> None:
    incomplete_memory_role = RoleArtifactRecord(
        role_id="memory-integrity-specialist",
        produced_output_artifacts=(ArtifactKind.MEMORY_INTEGRITY_DECISION,),
        consumed_input_artifacts=(ArtifactKind.OUTCOME_DELTA,),
        evidence_ids=("role-evidence:memory",),
        rationale="Missing provenance input should keep memory review incomplete.",
    )
    roles = (incomplete_memory_role,) + tuple(
        complete_role_artifact_record(
            role_id, evidence_ids=(f"role-evidence:{role_id}",)
        )
        for role_id in DEFAULT_MEMORY_ROLE_REVIEW_SCOPE
        if role_id != "memory-integrity-specialist"
    )
    decision = MemoryRoleDecisionRecord(
        decision_id="memory-decision-001",
        memory_ledger=memory_ledger(),
        role_artifact_bundle=RoleArtifactBundle(
            bundle_id="memory-role-bundle-001",
            records=roles,
            required_role_ids=DEFAULT_MEMORY_ROLE_REVIEW_SCOPE,
        ),
        evidence_ids=("decision-evidence",),
    )

    assert decision.status is MemoryRoleDecisionStatus.NEEDS_EVIDENCE
    assert decision.may_request_memory_persistence_review is False
    assert "incomplete required memory-review roles: memory-integrity-specialist" in (
        decision.readiness_gaps
    )
    assert (
        "accepted memory requires complete memory-integrity-specialist role artifact"
        in decision.readiness_gaps
    )


def test_blocked_required_role_blocks_memory_role_decision() -> None:
    blocked_memory_role = RoleArtifactRecord(
        role_id="memory-integrity-specialist",
        produced_output_artifacts=(ArtifactKind.MEMORY_INTEGRITY_DECISION,),
        consumed_input_artifacts=(
            ArtifactKind.OUTCOME_DELTA,
            ArtifactKind.PROVENANCE_RECORD,
        ),
        evidence_ids=("role-evidence:memory",),
        rationale="Memory role blocks because provenance is contradictory.",
        status=RoleArtifactStatus.BLOCKED,
        authority=RoleArtifactAuthority.BLOCKED,
        paired_engine_ids=("memory-quarantine", "skill-genome"),
        blocking_reasons=("Contradictory provenance requires rejection.",),
    )
    roles = (blocked_memory_role,) + tuple(
        complete_role_artifact_record(
            role_id, evidence_ids=(f"role-evidence:{role_id}",)
        )
        for role_id in DEFAULT_MEMORY_ROLE_REVIEW_SCOPE
        if role_id != "memory-integrity-specialist"
    )
    decision = MemoryRoleDecisionRecord(
        decision_id="memory-decision-001",
        memory_ledger=memory_ledger(),
        role_artifact_bundle=RoleArtifactBundle(
            bundle_id="memory-role-bundle-001",
            records=roles,
            required_role_ids=DEFAULT_MEMORY_ROLE_REVIEW_SCOPE,
        ),
        evidence_ids=("decision-evidence",),
    )

    assert decision.status is MemoryRoleDecisionStatus.BLOCKED
    assert "blocked required memory-review roles: memory-integrity-specialist" in (
        decision.blocking_gaps
    )


def test_memory_role_decision_converts_to_shared_artifact_ref() -> None:
    artifact = ready_decision().to_artifact_ref()

    assert artifact.artifact_id == "memory-quarantine-decision:memory-decision-001"
    assert artifact.kind is WaveThreeArtifactKind.MEMORY_QUARANTINE_DECISION
    assert artifact.produced_by_engine_id == "memory-quarantine"
    assert artifact.produced_by_agent_role_id == "memory-integrity-specialist"
    assert artifact.allowed_for_automatic_execution is False
    assert artifact.ready_for_human_review is True


def test_memory_role_decision_artifact_bundle_links_all_evidence() -> None:
    bundle = ready_decision().to_artifact_bundle(
        artifact_bundle_id="memory-decision-artifacts"
    )

    assert bundle.has_required_kind_coverage is True
    assert bundle.artifact_ids == ("memory-quarantine-decision:memory-decision-001",)
    assert bundle.ready_for_human_review_artifact_ids == (
        "memory-quarantine-decision:memory-decision-001",
    )
    assert bundle.evidence_link_table == {
        "memory-quarantine-decision:memory-decision-001": (
            "decision-evidence:memory-decision-001",
            "ev-memory-001",
        )
    }


def test_memory_role_decision_bundle_reports_ready_and_blocked_decisions() -> None:
    ready = ready_decision("memory-decision-ready")
    blocked = MemoryRoleDecisionRecord(
        decision_id="memory-decision-blocked",
        memory_ledger=memory_ledger(
            memory_candidate(
                candidate_id="memory-candidate-blocked",
                contradiction_ids=("contradiction-001",),
            )
        ),
        role_artifact_bundle=role_bundle(),
        evidence_ids=("decision-evidence:blocked",),
    )
    bundle = MemoryRoleDecisionBundle(
        bundle_id="memory-decision-bundle-001",
        decisions=(blocked, ready),
    )

    assert bundle.decision_ids == ("memory-decision-blocked", "memory-decision-ready")
    assert bundle.ready_decision_ids == ("memory-decision-ready",)
    assert bundle.blocked_decision_ids == ("memory-decision-blocked",)
    assert bundle.is_complete_for_human_review is False


def test_memory_role_decision_bundle_rejects_duplicate_decisions() -> None:
    decision = ready_decision()

    with pytest.raises(ValueError, match="Duplicate decision_id"):
        MemoryRoleDecisionBundle(
            bundle_id="memory-decision-bundle-001",
            decisions=(decision, decision),
        )


def test_memory_role_decision_fingerprints_are_deterministic() -> None:
    first = ready_decision().fingerprint()
    second = ready_decision().fingerprint()
    bundle_first = MemoryRoleDecisionBundle(
        bundle_id="memory-decision-bundle-001",
        decisions=(ready_decision(),),
    ).fingerprint()
    bundle_second = MemoryRoleDecisionBundle(
        bundle_id="memory-decision-bundle-001",
        decisions=(ready_decision(),),
    ).fingerprint()

    assert first == second
    assert len(first) == 64
    assert bundle_first == bundle_second
    assert len(bundle_first) == 64
