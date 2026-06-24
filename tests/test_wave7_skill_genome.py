import pytest

from ix_cognition_kernel.wave7_skill_genome import (
    SkillEvidence,
    SkillEvidenceKind,
    SkillFailure,
    SkillGene,
    SkillGenomeDecision,
    SkillRisk,
    SkillStatus,
    TransferAttempt,
    TransferResult,
    build_skill_genome,
    build_skill_genome_report,
)


def _evidence(
    *,
    evidence_id: str = "skill-evidence-1",
    confidence_delta: float = 0.2,
    measured: bool = True,
) -> SkillEvidence:
    return SkillEvidence(
        evidence_id=evidence_id,
        kind=SkillEvidenceKind.EXPERIENCE_RECORD,
        summary="Measured experience supports bounded simulation skill.",
        source_record_ids=("experience-1",) if measured else (),
        evidence_ids=("evidence-1",),
        confidence_delta=confidence_delta,
        measured=measured,
    )


def _failure(
    *,
    failure_id: str = "failure-1",
    unresolved: bool = True,
    corrective_action: str = "",
) -> SkillFailure:
    return SkillFailure(
        failure_id=failure_id,
        summary="Transfer failed when the target domain changed assumptions.",
        domain="novel transfer",
        affected_operations=("simulate-trial",),
        evidence_ids=("failure-evidence-1",),
        unresolved=unresolved,
        corrective_action=corrective_action,
    )


def _transfer(
    *,
    transfer_id: str = "transfer-1",
    result: TransferResult = TransferResult.PASSED,
    lesson: str = "",
) -> TransferAttempt:
    return TransferAttempt(
        transfer_id=transfer_id,
        source_domain="bounded simulation",
        target_domain="novel planning",
        task_family="transfer probe",
        result=result,
        source_skill_ids=("skill-sim-1",),
        evidence_ids=("transfer-evidence-1",),
        lesson=lesson,
    )


def _skill(
    *,
    status: SkillStatus = SkillStatus.DEMONSTRATED,
    risk: SkillRisk = SkillRisk.MODERATE,
    evidence: tuple[SkillEvidence, ...] = (),
    failures: tuple[SkillFailure, ...] = (),
    transfers: tuple[TransferAttempt, ...] = (),
    confidence: float = 0.7,
    stale_reason: str = "",
    revoked_reason: str = "",
) -> SkillGene:
    return SkillGene(
        skill_id="skill-sim-1",
        name="Bounded simulation skill",
        domain="bounded simulation",
        operations=("simulate-trial",),
        status=status,
        risk=risk,
        evidence=evidence or (_evidence(),),
        failures=failures,
        transfer_attempts=transfers,
        authority_refs=("human-authority-1",),
        confidence=confidence,
        stale_reason=stale_reason,
        revoked_reason=revoked_reason,
    )


def test_skill_evidence_is_measured_and_fingerprinted() -> None:
    evidence = _evidence()

    assert evidence.supports_skill
    assert not evidence.weakens_skill
    assert evidence.fingerprint() == evidence.fingerprint()
    assert len(evidence.fingerprint()) == 64

    with pytest.raises(ValueError, match="requires source record ids"):
        _evidence(measured=True, confidence_delta=0.1).__class__(
            evidence_id="bad-measured",
            kind=SkillEvidenceKind.EXPERIENCE_RECORD,
            summary="Bad measured evidence.",
            source_record_ids=(),
            evidence_ids=("evidence-1",),
            confidence_delta=0.1,
            measured=True,
        )


def test_unmeasured_skill_evidence_cannot_increase_confidence() -> None:
    with pytest.raises(ValueError, match="cannot increase confidence"):
        _evidence(measured=False, confidence_delta=0.1)

    weak = _evidence(measured=False, confidence_delta=-0.1)
    assert not weak.supports_skill
    assert weak.weakens_skill


def test_skill_failure_persists_until_corrected() -> None:
    unresolved = _failure()
    resolved = _failure(
        failure_id="failure-2",
        unresolved=False,
        corrective_action="Add transfer precondition check before reuse.",
    )

    assert unresolved.blocks_transfer_claim
    assert not resolved.blocks_transfer_claim
    assert resolved.corrective_action == (
        "Add transfer precondition check before reuse."
    )
    assert unresolved.fingerprint() == unresolved.fingerprint()

    with pytest.raises(ValueError, match="require corrective_action"):
        _failure(unresolved=False)


def test_transfer_attempt_tracks_generalization_separately() -> None:
    passed = _transfer()
    failed = _transfer(
        transfer_id="transfer-failed",
        result=TransferResult.FAILED,
        lesson="Future transfer must check target assumptions first.",
    )

    assert passed.passed
    assert not passed.blocks_generalization_claim
    assert failed.blocks_generalization_claim
    assert failed.changes_future_reasoning
    assert failed.fingerprint() == failed.fingerprint()

    with pytest.raises(ValueError, match="must have an attempted result"):
        _transfer(result=TransferResult.NOT_ATTEMPTED)

    with pytest.raises(ValueError, match="needs lesson"):
        _transfer(result=TransferResult.FAILED)


def test_skill_gene_distinguishes_skill_from_authorization() -> None:
    skill = _skill(transfers=(_transfer(),))

    assert skill.supports_operation("simulate-trial")
    assert skill.status is SkillStatus.DEMONSTRATED
    assert skill.transfer_demonstrated
    assert skill.passed_transfer_ids == ("transfer-1",)
    assert not skill.needs_more_evidence
    assert not skill.blocks_claim
    assert "evidence-1" in skill.evidence_ids
    assert "transfer-evidence-1" in skill.evidence_ids
    assert skill.fingerprint() == skill.fingerprint()
    assert len(skill.fingerprint()) == 64

    with pytest.raises(ValueError, match="must not claim authorization"):
        SkillGene(
            skill_id="skill-auth",
            name="Bad authorization skill",
            domain="bounded simulation",
            operations=("simulate-trial",),
            status=SkillStatus.DEMONSTRATED,
            risk=SkillRisk.LOW,
            evidence=(_evidence(),),
            failures=(),
            transfer_attempts=(),
            authority_refs=("human-authority-1",),
            confidence=0.7,
            claims_authorization=True,
        )


def test_unproven_and_revoked_skills_require_zero_confidence() -> None:
    unproven = _skill(
        status=SkillStatus.UNPROVEN,
        evidence=(),
        confidence=0.0,
    )
    revoked = _skill(
        status=SkillStatus.REVOKED,
        evidence=(),
        confidence=0.0,
        revoked_reason="Evidence was invalidated by review.",
    )

    assert unproven.needs_more_evidence
    assert revoked.blocks_claim

    with pytest.raises(ValueError, match="Unproven skills"):
        _skill(status=SkillStatus.UNPROVEN, evidence=(), confidence=0.1)

    with pytest.raises(ValueError, match="Revoked skills"):
        _skill(
            status=SkillStatus.REVOKED,
            evidence=(),
            confidence=0.1,
            revoked_reason="Bad confidence.",
        )


def test_stale_skill_requires_reason() -> None:
    stale = _skill(
        status=SkillStatus.STALE,
        confidence=0.3,
        stale_reason="Skill evidence predates the current body contract.",
    )

    assert stale.needs_more_evidence
    assert not stale.blocks_claim

    with pytest.raises(ValueError, match="Stale skills"):
        _skill(status=SkillStatus.STALE, confidence=0.3)


def test_skill_gene_preserves_unresolved_failures_and_blocked_transfers() -> None:
    skill = _skill(
        status=SkillStatus.CONSTRAINED,
        failures=(_failure(),),
        transfers=(
            _transfer(
                result=TransferResult.BLOCKED,
                lesson="Future reasoning must block this transfer path.",
            ),
        ),
        confidence=0.4,
    )

    assert skill.needs_review
    assert skill.blocks_claim
    assert skill.unresolved_failure_ids == ("failure-1",)
    assert skill.blocked_transfer_ids == ("transfer-1",)
    assert skill.changes_future_reasoning


def test_skill_genome_collects_skill_status_and_evidence() -> None:
    demonstrated = _skill(transfers=(_transfer(),))
    constrained = SkillGene(
        skill_id="skill-constrained-1",
        name="Constrained transfer skill",
        domain="novel transfer",
        operations=("transfer-probe",),
        status=SkillStatus.CONSTRAINED,
        risk=SkillRisk.HIGH,
        evidence=(
            _evidence(
                evidence_id="skill-evidence-2",
                confidence_delta=0.1,
            ),
        ),
        failures=(
            _failure(
                failure_id="failure-2",
                unresolved=False,
                corrective_action="Add novelty precondition check.",
            ),
        ),
        transfer_attempts=(
            _transfer(
                transfer_id="transfer-2",
                result=TransferResult.PARTIAL,
                lesson="Future transfer must check novelty first.",
            ),
        ),
        authority_refs=("human-authority-1",),
        confidence=0.45,
    )
    genome = build_skill_genome(
        genome_id="genome-1",
        skills=(demonstrated, constrained),
        doctrine_ids=("skill-is-not-authorization",),
        authority_refs=("human-authority-1",),
        notes=("Genome preserves capability memory.",),
    )

    assert genome.skill_ids == ("skill-constrained-1", "skill-sim-1")
    assert genome.demonstrated_skill_ids == ("skill-sim-1",)
    assert genome.constrained_skill_ids == ("skill-constrained-1",)
    assert genome.review_skill_ids == ("skill-constrained-1",)
    assert genome.transfer_demonstrated_skill_ids == ("skill-sim-1",)
    assert not genome.blocks_claim
    assert "evidence-1" in genome.evidence_ids
    assert "transfer-evidence-1" in genome.evidence_ids
    assert genome.fingerprint() == genome.fingerprint()
    assert len(genome.fingerprint()) == 64


def test_skill_genome_report_ready_for_review() -> None:
    genome = build_skill_genome(
        genome_id="genome-ready",
        skills=(_skill(transfers=(_transfer(),)),),
        doctrine_ids=("skill-is-not-authorization",),
        authority_refs=("human-authority-1",),
    )
    report = build_skill_genome_report(
        report_id="skill-report-1",
        genome=genome,
        decision=SkillGenomeDecision.READY_FOR_REVIEW,
        notes=("Skill genome is ready for review.",),
    )

    assert report.ready_for_review
    assert not report.blocks_claim
    assert "evidence-1" in report.evidence_ids
    assert report.fingerprint() == report.fingerprint()
    assert len(report.fingerprint()) == 64


def test_skill_genome_report_rejects_ready_state_with_blockers() -> None:
    genome = build_skill_genome(
        genome_id="genome-blocked",
        skills=(_skill(failures=(_failure(),)),),
        doctrine_ids=("skill-is-not-authorization",),
        authority_refs=("human-authority-1",),
    )

    with pytest.raises(ValueError, match="cannot have blockers"):
        build_skill_genome_report(
            report_id="skill-report-blocked",
            genome=genome,
            decision=SkillGenomeDecision.READY_FOR_REVIEW,
        )


def test_blocked_skill_genome_report_preserves_blockers() -> None:
    genome = build_skill_genome(
        genome_id="genome-blocked",
        skills=(_skill(failures=(_failure(),)),),
        doctrine_ids=("skill-is-not-authorization",),
        authority_refs=("human-authority-1",),
    )
    report = build_skill_genome_report(
        report_id="skill-report-blocked",
        genome=genome,
        decision=SkillGenomeDecision.BLOCKED,
        notes=("Unresolved failure remains visible.",),
    )

    assert report.blocks_claim
    assert not report.ready_for_review
    assert genome.blocking_skill_ids == ("skill-sim-1",)
