import pytest

from ix_cognition_kernel.evaluation import (
    AcceptanceCriterion,
    EvaluationLedger,
    EvaluationRecord,
    EvaluationStatus,
)
from ix_cognition_kernel.wave3_contracts import (
    WaveThreeArtifactKind,
    WaveThreeAuthorityState,
)
from ix_cognition_kernel.wave3_discovery import (
    DiscoveryCandidate,
    DiscoveryCandidateKind,
    DiscoveryRecord,
    DiscoveryRecordBundle,
    DiscoveryRecordStatus,
    DiscoveryUpdateTarget,
)


def candidate(
    candidate_id: str = "candidate-001",
    *,
    candidate_kind: DiscoveryCandidateKind = DiscoveryCandidateKind.SKILL_CANDIDATE,
    proposed_update_targets: tuple[DiscoveryUpdateTarget, ...] = (
        DiscoveryUpdateTarget.SKILL_GENOME,
    ),
) -> DiscoveryCandidate:
    return DiscoveryCandidate(
        candidate_id=candidate_id,
        candidate_kind=candidate_kind,
        summary="A reusable evaluator-check pattern may improve future reviews.",
        source_artifact_ids=("tribunal-record:tribunal-001",),
        proposed_update_targets=proposed_update_targets,
        novelty_claim="The candidate combines failure visibility with reuse gating.",
        risk_notes=("Could become metric gaming if failed checks are hidden.",),
        evidence_ids=(f"candidate-evidence:{candidate_id}",),
    )


def criterion(satisfied: bool = True) -> AcceptanceCriterion:
    return AcceptanceCriterion(
        criterion_id="criterion-001",
        description="Candidate is backed by visible evidence and explicit risk notes.",
        required=True,
        satisfied=satisfied,
        evidence_ids=("criterion-evidence:001",) if satisfied else (),
        reason=None if satisfied else "Candidate lacks enough evidence.",
    )


def evaluation(
    evaluation_id: str = "evaluation-001",
    *,
    evaluated_artifact_id: str = "discovery-candidate:candidate-001",
    status: EvaluationStatus = EvaluationStatus.PASSED,
    evaluator_role_id: str = "verifier",
) -> EvaluationRecord:
    return EvaluationRecord(
        evaluation_id=evaluation_id,
        title="Evaluator review for discovery candidate.",
        evaluated_artifact_ids=(evaluated_artifact_id,),
        criteria=(criterion(satisfied=status is EvaluationStatus.PASSED),),
        status=status,
        evidence_ids=(f"evaluation-evidence:{evaluation_id}",)
        if status is EvaluationStatus.PASSED
        else (),
        reasons=()
        if status is EvaluationStatus.PASSED
        else ("Candidate cannot yet become review-ready.",),
        evaluator_role_id=evaluator_role_id,
    )


def ready_record(discovery_id: str = "discovery-001") -> DiscoveryRecord:
    item = candidate()
    return DiscoveryRecord(
        discovery_id=discovery_id,
        candidate=item,
        evaluation_ledger=EvaluationLedger(records=(evaluation(),)),
        required_evaluation_ids=("evaluation-001",),
        evidence_ids=(f"discovery-evidence:{discovery_id}",),
    )


def test_discovery_candidate_requires_source_targets_risk_and_matching_target() -> None:
    with pytest.raises(ValueError, match="require source artifact ids"):
        DiscoveryCandidate(
            candidate_id="candidate-001",
            candidate_kind=DiscoveryCandidateKind.HYPOTHESIS,
            summary="Invalid candidate.",
            source_artifact_ids=(),
            proposed_update_targets=(DiscoveryUpdateTarget.BELIEF_STATE,),
            novelty_claim="New hypothesis.",
            risk_notes=("Risk note.",),
            evidence_ids=("evidence",),
        )
    with pytest.raises(ValueError, match="require risk notes"):
        DiscoveryCandidate(
            candidate_id="candidate-001",
            candidate_kind=DiscoveryCandidateKind.HYPOTHESIS,
            summary="Invalid candidate.",
            source_artifact_ids=("artifact",),
            proposed_update_targets=(DiscoveryUpdateTarget.BELIEF_STATE,),
            novelty_claim="New hypothesis.",
            risk_notes=(),
            evidence_ids=("evidence",),
        )
    with pytest.raises(ValueError, match="requires matching update target"):
        candidate(
            candidate_kind=DiscoveryCandidateKind.HYPOTHESIS,
            proposed_update_targets=(DiscoveryUpdateTarget.PLAN_GRAPH,),
        )


@pytest.mark.parametrize(
    ("candidate_kind", "required_target"),
    [
        (DiscoveryCandidateKind.HYPOTHESIS, DiscoveryUpdateTarget.BELIEF_STATE),
        (DiscoveryCandidateKind.CAUSAL_EDGE, DiscoveryUpdateTarget.CAUSAL_MODEL),
        (DiscoveryCandidateKind.PLAN_REPAIR, DiscoveryUpdateTarget.PLAN_GRAPH),
        (
            DiscoveryCandidateKind.MEMORY_CANDIDATE,
            DiscoveryUpdateTarget.MEMORY_QUARANTINE,
        ),
        (DiscoveryCandidateKind.SKILL_CANDIDATE, DiscoveryUpdateTarget.SKILL_GENOME),
    ],
)
def test_discovery_candidate_kind_accepts_required_update_target(
    candidate_kind: DiscoveryCandidateKind, required_target: DiscoveryUpdateTarget
) -> None:
    item = candidate(
        candidate_kind=candidate_kind,
        proposed_update_targets=(required_target,),
    )

    assert item.candidate_kind is candidate_kind
    assert item.proposed_update_targets == (required_target,)


def test_discovery_candidate_must_be_generated_by_discovery_engine() -> None:
    with pytest.raises(ValueError, match="must be generated by"):
        DiscoveryCandidate(
            candidate_id="candidate-001",
            candidate_kind=DiscoveryCandidateKind.HYPOTHESIS,
            summary="Invalid generator.",
            source_artifact_ids=("artifact",),
            proposed_update_targets=(DiscoveryUpdateTarget.BELIEF_STATE,),
            novelty_claim="New hypothesis.",
            risk_notes=("Risk note.",),
            evidence_ids=("evidence",),
            generated_by_engine_id="planner",
        )


def test_ready_discovery_record_is_reviewable_not_state_mutating() -> None:
    record = ready_record()

    assert record.status is DiscoveryRecordStatus.READY_FOR_HUMAN_REVIEW
    assert record.ready_for_human_review is True
    assert record.may_request_belief_or_skill_update is True
    assert record.permits_automatic_state_update is False
    assert record.permits_automatic_execution is False
    assert record.human_authority_state is WaveThreeAuthorityState.HUMAN_REVIEW_REQUIRED
    assert record.readiness_gaps == ()
    assert record.blocking_gaps == ()
    assert "automatic state update is not permitted" in record.review_summary


def test_discovery_record_rejects_missing_or_mismatched_evaluator_record() -> None:
    with pytest.raises(ValueError, match="Unknown evaluation_id"):
        DiscoveryRecord(
            discovery_id="discovery-001",
            candidate=candidate(),
            evaluation_ledger=EvaluationLedger(records=(evaluation(),)),
            required_evaluation_ids=("missing-evaluation",),
            evidence_ids=("discovery-evidence",),
        )
    with pytest.raises(ValueError, match="must cover the discovery candidate"):
        DiscoveryRecord(
            discovery_id="discovery-001",
            candidate=candidate(),
            evaluation_ledger=EvaluationLedger(
                records=(evaluation(evaluated_artifact_id="other-artifact"),)
            ),
            required_evaluation_ids=("evaluation-001",),
            evidence_ids=("discovery-evidence",),
        )


def test_discovery_record_rejects_non_evaluator_role() -> None:
    with pytest.raises(ValueError, match="require evaluator roles"):
        DiscoveryRecord(
            discovery_id="discovery-001",
            candidate=candidate(),
            evaluation_ledger=EvaluationLedger(
                records=(evaluation(evaluator_role_id="planner"),)
            ),
            required_evaluation_ids=("evaluation-001",),
            evidence_ids=("discovery-evidence",),
        )


def test_discovery_record_needs_evaluation_without_passing_evidence() -> None:
    item = candidate()
    record = DiscoveryRecord(
        discovery_id="discovery-001",
        candidate=item,
        evaluation_ledger=EvaluationLedger(
            records=(
                evaluation(
                    evaluated_artifact_id=item.artifact_id,
                    status=EvaluationStatus.NEEDS_EVIDENCE,
                ),
            )
        ),
        required_evaluation_ids=("evaluation-001",),
        evidence_ids=("discovery-evidence",),
    )

    assert record.status is DiscoveryRecordStatus.NEEDS_EVALUATION
    assert record.ready_for_human_review is False
    assert record.may_request_belief_or_skill_update is False
    assert (
        "discovery evaluations need evidence: evaluation-001" in record.readiness_gaps
    )
    assert (
        "discovery cannot update belief or skill state without passing "
        "evaluator evidence"
    ) in record.readiness_gaps


def test_discovery_record_needs_repair_when_evaluation_fails() -> None:
    item = candidate()
    record = DiscoveryRecord(
        discovery_id="discovery-001",
        candidate=item,
        evaluation_ledger=EvaluationLedger(
            records=(
                evaluation(
                    evaluated_artifact_id=item.artifact_id,
                    status=EvaluationStatus.FAILED,
                ),
            )
        ),
        required_evaluation_ids=("evaluation-001",),
        evidence_ids=("discovery-evidence",),
    )

    assert record.status is DiscoveryRecordStatus.NEEDS_REPAIR
    assert "discovery evaluations failed: evaluation-001" in record.readiness_gaps


def test_discovery_record_blocks_when_evaluator_blocks() -> None:
    item = candidate()
    record = DiscoveryRecord(
        discovery_id="discovery-001",
        candidate=item,
        evaluation_ledger=EvaluationLedger(
            records=(
                evaluation(
                    evaluated_artifact_id=item.artifact_id,
                    status=EvaluationStatus.BLOCKED,
                ),
            )
        ),
        required_evaluation_ids=("evaluation-001",),
        evidence_ids=("discovery-evidence",),
        blocked_reasons=("Evaluator found unsafe update pressure.",),
    )

    assert record.status is DiscoveryRecordStatus.BLOCKED
    assert record.human_authority_state is WaveThreeAuthorityState.BLOCKED
    assert "discovery evaluations blocked: evaluation-001" in record.blocking_gaps
    assert "discovery-001 blocked: Evaluator found unsafe update pressure." in (
        record.blocking_gaps
    )


def test_discovery_record_rejects_block_reason_without_blocked_evaluation() -> None:
    with pytest.raises(ValueError, match="only with a blocked evaluation"):
        DiscoveryRecord(
            discovery_id="discovery-001",
            candidate=candidate(),
            evaluation_ledger=EvaluationLedger(records=(evaluation(),)),
            required_evaluation_ids=("evaluation-001",),
            evidence_ids=("discovery-evidence",),
            blocked_reasons=("Not allowed without blocked evaluation.",),
        )


def test_discovery_record_converts_to_shared_artifact_ref() -> None:
    artifact = ready_record().to_artifact_ref()

    assert artifact.artifact_id == "discovery-record:discovery-001"
    assert artifact.kind is WaveThreeArtifactKind.DISCOVERY_RECORD
    assert artifact.produced_by_engine_id == "evaluator-driven-discovery"
    assert artifact.produced_by_agent_role_id == "verifier"
    assert artifact.allowed_for_automatic_execution is False
    assert artifact.ready_for_human_review is True


def test_discovery_record_artifact_bundle_links_all_evidence() -> None:
    bundle = ready_record().to_artifact_bundle(artifact_bundle_id="discovery-artifacts")

    assert bundle.has_required_kind_coverage is True
    assert bundle.artifact_ids == ("discovery-record:discovery-001",)
    assert bundle.ready_for_human_review_artifact_ids == (
        "discovery-record:discovery-001",
    )
    assert bundle.evidence_link_table == {
        "discovery-record:discovery-001": (
            "candidate-evidence:candidate-001",
            "discovery-evidence:discovery-001",
            "evaluation-evidence:evaluation-001",
        ),
    }


def test_discovery_bundle_reports_readiness_and_blocks() -> None:
    ready = ready_record("discovery-ready")
    blocked_candidate = candidate("candidate-blocked")
    blocked = DiscoveryRecord(
        discovery_id="discovery-blocked",
        candidate=blocked_candidate,
        evaluation_ledger=EvaluationLedger(
            records=(
                evaluation(
                    evaluation_id="evaluation-blocked",
                    evaluated_artifact_id=blocked_candidate.artifact_id,
                    status=EvaluationStatus.BLOCKED,
                ),
            )
        ),
        required_evaluation_ids=("evaluation-blocked",),
        evidence_ids=("discovery-evidence:blocked",),
        blocked_reasons=("Blocked update target requires redesign.",),
    )
    bundle = DiscoveryRecordBundle(
        bundle_id="discovery-bundle-001",
        records=(blocked, ready),
    )

    assert bundle.record_ids == ("discovery-blocked", "discovery-ready")
    assert bundle.ready_record_ids == ("discovery-ready",)
    assert bundle.blocked_record_ids == ("discovery-blocked",)
    assert bundle.is_complete_for_human_review is False


def test_discovery_bundle_rejects_duplicate_records_and_candidates() -> None:
    item = ready_record()

    with pytest.raises(ValueError, match="Duplicate discovery_id"):
        DiscoveryRecordBundle(bundle_id="bundle", records=(item, item))

    duplicate_candidate = DiscoveryRecord(
        discovery_id="discovery-002",
        candidate=item.candidate,
        evaluation_ledger=item.evaluation_ledger,
        required_evaluation_ids=item.required_evaluation_ids,
        evidence_ids=("discovery-evidence:002",),
    )
    with pytest.raises(ValueError, match="Duplicate candidate_id"):
        DiscoveryRecordBundle(bundle_id="bundle", records=(item, duplicate_candidate))


def test_discovery_bundle_converts_to_shared_artifact_bundle() -> None:
    bundle = DiscoveryRecordBundle(
        bundle_id="discovery-bundle", records=(ready_record(),)
    )
    artifact_bundle = bundle.to_artifact_bundle(
        artifact_bundle_id="discovery-artifacts"
    )

    assert artifact_bundle.has_required_kind_coverage is True
    assert artifact_bundle.artifact_ids == ("discovery-record:discovery-001",)
    assert artifact_bundle.ready_for_human_review_artifact_ids == (
        "discovery-record:discovery-001",
    )


def test_discovery_fingerprints_are_deterministic() -> None:
    first = ready_record().fingerprint()
    second = ready_record().fingerprint()
    bundle_first = DiscoveryRecordBundle(
        bundle_id="discovery-bundle", records=(ready_record(),)
    ).fingerprint()
    bundle_second = DiscoveryRecordBundle(
        bundle_id="discovery-bundle", records=(ready_record(),)
    ).fingerprint()

    assert first == second
    assert len(first) == 64
    assert bundle_first == bundle_second
    assert len(bundle_first) == 64
