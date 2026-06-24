import pytest

from ix_cognition_kernel.wave7_self_revision import (
    RevisionEvidenceGate,
    RevisionFindingSeverity,
    RevisionImpactAssessment,
    RevisionRisk,
    RevisionScope,
    RevisionTarget,
    RevisionTargetKind,
    SelfRevisionDecision,
    SelfRevisionDecisionStatus,
    SelfRevisionFinding,
    SelfRevisionProposal,
    build_self_revision_report,
    evaluate_self_revision,
)


def _target(*, immutable: bool = False) -> RevisionTarget:
    return RevisionTarget(
        target_id="target-1",
        kind=RevisionTargetKind.EVALUATOR_RULE,
        name="Evidence gate evaluator",
        current_behavior_summary="Requires measured evidence before review.",
        protected_invariants=("human-authority-final", "evidence-required"),
        evidence_ids=("target-evidence-1",),
        authority_refs=("human-authority-1",),
        immutable=immutable,
    )


def _impact(
    *,
    risk: RevisionRisk = RevisionRisk.HIGH,
    scope: RevisionScope = RevisionScope.REVIEW_PACKET,
    requires_sandbox: bool = True,
    affected_doctrine_ids: tuple[str, ...] = ("evidence-required",),
) -> RevisionImpactAssessment:
    return RevisionImpactAssessment(
        assessment_id="impact-1",
        target_id="target-1",
        risk=risk,
        scope=scope,
        expected_behavior_change="Require stronger evidence before readiness.",
        rollback_plan="Restore previous evaluator rule from receipt.",
        affected_doctrine_ids=affected_doctrine_ids,
        affected_capability_ids=("capability-review-1",),
        evidence_ids=("impact-evidence-1",),
        requires_sandbox=requires_sandbox,
    )


def _gate(
    *,
    supplied: tuple[str, ...] = ("proposal-evidence-1", "impact-evidence-1"),
) -> RevisionEvidenceGate:
    return RevisionEvidenceGate(
        gate_id="gate-1",
        proposal_id="proposal-1",
        required_evidence_ids=("proposal-evidence-1", "impact-evidence-1"),
        supplied_evidence_ids=supplied,
        authority_refs=("human-authority-1",),
    )


def _proposal(
    *,
    proposal_id: str = "proposal-1",
    target: RevisionTarget | None = None,
    impact: RevisionImpactAssessment | None = None,
    gate: RevisionEvidenceGate | None = None,
) -> SelfRevisionProposal:
    return SelfRevisionProposal(
        proposal_id=proposal_id,
        target=target or _target(),
        impact=impact or _impact(),
        evidence_gate=gate or _gate(),
        proposed_change_summary="Tighten readiness around measured outcomes.",
        rationale="A prior mismatch showed the evaluator was too permissive.",
        evidence_ids=("proposal-evidence-1",),
    )


def test_revision_target_preserves_invariants_and_fingerprint() -> None:
    target = _target()

    assert not target.blocks_revision
    assert target.protected_invariants == (
        "evidence-required",
        "human-authority-final",
    )
    assert target.fingerprint() == target.fingerprint()
    assert len(target.fingerprint()) == 64


def test_revision_target_requires_invariants() -> None:
    with pytest.raises(ValueError, match="protected invariants"):
        RevisionTarget(
            target_id="target-no-invariants",
            kind=RevisionTargetKind.EVALUATOR_RULE,
            name="Bad target",
            current_behavior_summary="Missing invariants.",
            protected_invariants=(),
            evidence_ids=("target-evidence-1",),
            authority_refs=("human-authority-1",),
        )


def test_high_risk_impact_requires_sandbox_and_doctrine_ids() -> None:
    impact = _impact()

    assert impact.elevated_review_required
    assert impact.fingerprint() == impact.fingerprint()
    assert len(impact.fingerprint()) == 64

    with pytest.raises(ValueError, match="require sandbox review"):
        _impact(requires_sandbox=False)

    with pytest.raises(ValueError, match="require doctrine impact"):
        _impact(affected_doctrine_ids=())


def test_impact_rejects_safe_without_review_claim() -> None:
    with pytest.raises(ValueError, match="must not claim safety"):
        RevisionImpactAssessment(
            assessment_id="impact-safe-claim",
            target_id="target-1",
            risk=RevisionRisk.MODERATE,
            scope=RevisionScope.REVIEW_PACKET,
            expected_behavior_change="Bad claim.",
            rollback_plan="Rollback.",
            affected_doctrine_ids=(),
            affected_capability_ids=(),
            evidence_ids=("impact-evidence-1",),
            claims_safe_without_review=True,
        )


def test_evidence_gate_reports_missing_evidence() -> None:
    gate = _gate(supplied=("proposal-evidence-1",))

    assert not gate.satisfied
    assert gate.missing_evidence_ids == ("impact-evidence-1",)
    assert gate.fingerprint() == gate.fingerprint()


def test_self_revision_proposal_rejects_self_authorization() -> None:
    with pytest.raises(ValueError, match="must not self-authorize"):
        SelfRevisionProposal(
            proposal_id="proposal-1",
            target=_target(),
            impact=_impact(),
            evidence_gate=_gate(),
            proposed_change_summary="Bad self authorization.",
            rationale="Bad rationale.",
            evidence_ids=("proposal-evidence-1",),
            self_authorized=True,
        )


def test_self_revision_proposal_rejects_review_bypass_and_authority_rewrite() -> None:
    with pytest.raises(ValueError, match="must not bypass review"):
        SelfRevisionProposal(
            proposal_id="proposal-1",
            target=_target(),
            impact=_impact(),
            evidence_gate=_gate(),
            proposed_change_summary="Bad review bypass.",
            rationale="Bad rationale.",
            evidence_ids=("proposal-evidence-1",),
            bypasses_review=True,
        )

    with pytest.raises(ValueError, match="must not modify authority model"):
        SelfRevisionProposal(
            proposal_id="proposal-1",
            target=_target(),
            impact=_impact(),
            evidence_gate=_gate(),
            proposed_change_summary="Bad authority rewrite.",
            rationale="Bad rationale.",
            evidence_ids=("proposal-evidence-1",),
            modifies_authority_model=True,
        )


def test_self_revision_proposal_ready_for_review_when_gate_satisfied() -> None:
    proposal = _proposal()

    assert proposal.ready_for_human_review
    assert not proposal.blocks_revision
    assert proposal.authority_refs == ("human-authority-1",)
    assert "proposal-evidence-1" in proposal.evidence_bundle_ids
    assert "target-evidence-1" in proposal.evidence_bundle_ids
    assert "impact-evidence-1" in proposal.evidence_bundle_ids
    assert proposal.fingerprint() == proposal.fingerprint()
    assert len(proposal.fingerprint()) == 64


def test_self_revision_finding_enforces_severity_semantics() -> None:
    finding = SelfRevisionFinding(
        finding_id="finding-review",
        severity=RevisionFindingSeverity.REVIEW_REQUIRED,
        summary="Human review required.",
        evidence_ids=("finding-evidence-1",),
        requires_human_review=True,
    )

    assert finding.requires_human_review
    assert not finding.blocks_revision
    assert finding.fingerprint() == finding.fingerprint()

    with pytest.raises(ValueError, match="must block revision"):
        SelfRevisionFinding(
            finding_id="finding-block-bad",
            severity=RevisionFindingSeverity.BLOCKING,
            summary="Bad blocking finding.",
            evidence_ids=("finding-evidence-1",),
        )


def test_evaluate_self_revision_needs_more_evidence() -> None:
    decision = evaluate_self_revision(
        decision_id="decision-missing-evidence",
        proposal=_proposal(gate=_gate(supplied=("proposal-evidence-1",))),
        supplied_evidence_ids=("proposal-evidence-1",),
    )

    assert decision.needs_more_evidence
    assert not decision.ready_for_review
    assert decision.missing_evidence_finding_ids == ("missing-revision-evidence",)
    assert "impact-evidence-1" in decision.evidence_bundle_ids


def test_evaluate_self_revision_routes_high_risk_to_human_review() -> None:
    decision = evaluate_self_revision(
        decision_id="decision-review",
        proposal=_proposal(),
        supplied_evidence_ids=("proposal-evidence-1", "impact-evidence-1"),
        notes=("Self-revision is reviewable but not approved.",),
    )

    assert decision.ready_for_review
    assert not decision.approved
    assert not decision.blocks_revision
    assert decision.review_finding_ids == ("elevated-review-required",)
    assert decision.required_authority_refs == ("human-authority-1",)
    assert decision.fingerprint() == decision.fingerprint()
    assert len(decision.fingerprint()) == 64


def test_evaluate_self_revision_blocks_immutable_target() -> None:
    decision = evaluate_self_revision(
        decision_id="decision-blocked",
        proposal=_proposal(target=_target(immutable=True)),
        supplied_evidence_ids=("proposal-evidence-1", "impact-evidence-1"),
    )

    assert decision.blocks_revision
    assert not decision.ready_for_review
    assert decision.blocking_finding_ids == ("immutable-target",)


def test_evaluate_self_revision_approves_only_with_human_review_ref() -> None:
    decision = evaluate_self_revision(
        decision_id="decision-approved",
        proposal=_proposal(),
        supplied_evidence_ids=("proposal-evidence-1", "impact-evidence-1"),
        satisfied_authority_refs=("human-authority-1",),
        human_review_ref="review-approval-1",
    )

    assert decision.approved
    assert not decision.ready_for_review
    assert decision.human_review_ref == "review-approval-1"


def test_decision_rejects_approval_without_human_review_ref() -> None:
    proposal = _proposal()

    with pytest.raises(ValueError, match="require human_review_ref"):
        SelfRevisionDecision(
            decision_id="decision-bad-approved",
            proposal=proposal,
            status=SelfRevisionDecisionStatus.APPROVED_BY_HUMAN_REVIEW,
            findings=(),
            required_authority_refs=("human-authority-1",),
            evidence_ids=("decision-evidence-1",),
        )


def test_decision_rejects_blocked_without_blocker() -> None:
    with pytest.raises(ValueError, match="require blockers"):
        SelfRevisionDecision(
            decision_id="decision-bad-blocked",
            proposal=_proposal(),
            status=SelfRevisionDecisionStatus.BLOCKED,
            findings=(),
            required_authority_refs=("human-authority-1",),
            evidence_ids=("decision-evidence-1",),
        )


def test_self_revision_report_preserves_decision_classes() -> None:
    proposal = _proposal()
    review = evaluate_self_revision(
        decision_id="decision-review",
        proposal=proposal,
        supplied_evidence_ids=("proposal-evidence-1", "impact-evidence-1"),
    )
    approved = evaluate_self_revision(
        decision_id="decision-approved",
        proposal=proposal,
        supplied_evidence_ids=("proposal-evidence-1", "impact-evidence-1"),
        satisfied_authority_refs=("human-authority-1",),
        human_review_ref="review-approval-1",
    )
    blocked_proposal = _proposal(
        proposal_id="proposal-blocked",
        target=_target(immutable=True),
        gate=RevisionEvidenceGate(
            gate_id="gate-blocked",
            proposal_id="proposal-blocked",
            required_evidence_ids=("proposal-evidence-1", "impact-evidence-1"),
            supplied_evidence_ids=("proposal-evidence-1", "impact-evidence-1"),
            authority_refs=("human-authority-1",),
        ),
    )
    blocked = evaluate_self_revision(
        decision_id="decision-blocked",
        proposal=blocked_proposal,
        supplied_evidence_ids=("proposal-evidence-1", "impact-evidence-1"),
    )
    report = build_self_revision_report(
        report_id="self-revision-report-1",
        proposals=(proposal, blocked_proposal),
        decisions=(review, approved, blocked),
        notes=("Self-revision decisions remain replayable.",),
    )

    assert report.proposal_ids == ("proposal-1", "proposal-blocked")
    assert report.decision_ids == (
        "decision-approved",
        "decision-blocked",
        "decision-review",
    )
    assert report.review_ready_decision_ids == ("decision-review",)
    assert report.approved_decision_ids == ("decision-approved",)
    assert report.blocked_decision_ids == ("decision-blocked",)
    assert report.blocks_claim
    assert "proposal-evidence-1" in report.evidence_ids
    assert report.fingerprint() == report.fingerprint()
    assert len(report.fingerprint()) == 64


def test_self_revision_report_rejects_decision_for_missing_proposal() -> None:
    proposal = _proposal()
    decision = evaluate_self_revision(
        decision_id="decision-review",
        proposal=proposal,
        supplied_evidence_ids=("proposal-evidence-1", "impact-evidence-1"),
    )
    other_proposal = SelfRevisionProposal(
        proposal_id="proposal-other",
        target=_target(),
        impact=_impact(),
        evidence_gate=RevisionEvidenceGate(
            gate_id="gate-other",
            proposal_id="proposal-other",
            required_evidence_ids=("proposal-evidence-1",),
            supplied_evidence_ids=("proposal-evidence-1",),
            authority_refs=("human-authority-1",),
        ),
        proposed_change_summary="Different proposal.",
        rationale="Different rationale.",
        evidence_ids=("proposal-other-evidence-1",),
    )

    with pytest.raises(ValueError, match="missing proposal"):
        build_self_revision_report(
            report_id="self-revision-report-bad",
            proposals=(other_proposal,),
            decisions=(decision,),
        )
