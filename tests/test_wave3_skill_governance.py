import pytest

from ix_cognition_kernel.agents import ArtifactKind
from ix_cognition_kernel.memory import (
    MemoryCandidate,
    MemoryCandidateKind,
    MemoryQuarantineLedger,
    MemoryValidationRecord,
    MemoryValidationStatus,
)
from ix_cognition_kernel.outcome import (
    OutcomeLearningLedger,
    OutcomeLearningRecord,
    OutcomeLearningStatus,
    OutcomePressure,
)
from ix_cognition_kernel.skills import (
    SkillCandidate,
    SkillCandidateKind,
    SkillReuseEvidenceRecord,
    SkillValidationLedger,
    SkillValidationRecord,
    SkillValidationStatus,
    evaluate_skill_candidates,
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
from ix_cognition_kernel.wave3_skill_governance import (
    DEFAULT_SKILL_GENOME_REVIEW_SCOPE,
    SKILL_GENOME_REVIEWER_ROLE_ID,
    SkillGenomeUpdateBundle,
    SkillGenomeUpdateRecord,
    SkillGenomeUpdateStatus,
)


def accepted_outcome(outcome_id: str = "outcome-001") -> OutcomeLearningRecord:
    return OutcomeLearningRecord(
        outcome_id=outcome_id,
        summary="Accepted outcome supports reusable skill validation.",
        status=OutcomeLearningStatus.ACCEPTED,
        pressure=OutcomePressure.CONFIRMED,
        belief_revision_ids=("revision-001",),
        causal_revision_ids=("causal-revision-001",),
        prediction_comparison_ids=("comparison-001",),
        evidence_ids=("ev-outcome-001",),
        learning_summary="Outcome evidence supports skill reuse review.",
        reasons=("Outcome learning was accepted with evidence.",),
    )


def outcome_ledger() -> OutcomeLearningLedger:
    return OutcomeLearningLedger(records=(accepted_outcome(),))


def accepted_memory(candidate_id: str = "memory-candidate-001") -> MemoryCandidate:
    return MemoryCandidate(
        candidate_id=candidate_id,
        kind=MemoryCandidateKind.PROCEDURE_HINT,
        content="A validated procedure hint can support a reusable skill.",
        provenance=("wave-2-memory-quarantine",),
        evidence_ids=("ev-memory-001",),
        source_outcome_ids=("outcome-001",),
        confidence=0.83,
        proposed_audit_index=0,
    )


def memory_ledger(
    *, status: MemoryValidationStatus = MemoryValidationStatus.ACCEPTED,
) -> MemoryQuarantineLedger:
    evidence_ids = (
        ("ev-memory-001",) if status is MemoryValidationStatus.ACCEPTED else ()
    )
    return MemoryQuarantineLedger(
        candidates=(accepted_memory(),),
        validations=(
            MemoryValidationRecord(
                validation_id="memory-validation-001",
                candidate_id="memory-candidate-001",
                status=status,
                evidence_ids=evidence_ids,
                outcome_ids=("outcome-001",)
                if status is MemoryValidationStatus.ACCEPTED
                else (),
                reviewer_role_id="memory-integrity-specialist",
                reasons=("Memory validation was reviewed for skill provenance.",),
            ),
        ),
    )


def skill_candidate(skill_id: str = "skill-001") -> SkillCandidate:
    return SkillCandidate(
        skill_id=skill_id,
        kind=SkillCandidateKind.EVALUATION_CHECK,
        name="Visible failure evidence check",
        procedure_steps=(
            "Inspect the review artifact for failed checks.",
            "Confirm failed checks remain visible in the evidence summary.",
        ),
        applicability_conditions=(
            "Use only when evaluating evidence visibility in governance records.",
        ),
        failure_modes=(
            "Fails if hidden failed checks can raise the review score.",
        ),
        source_memory_candidate_ids=("memory-candidate-001",),
        source_outcome_ids=("outcome-001",),
        confidence=0.86,
        provenance=("wave-2-skill-validation",),
        proposed_audit_index=1,
    )


def successful_reuse(skill_id: str = "skill-001") -> SkillReuseEvidenceRecord:
    return SkillReuseEvidenceRecord(
        reuse_id="reuse-001",
        skill_id=skill_id,
        outcome_id="outcome-001",
        evidence_ids=("reuse-evidence-001",),
        succeeded=True,
        audit_index=2,
        applicability_condition_ids=("condition-001",),
        failure_mode_ids=(),
        reasons=("The reusable check preserved failed evidence visibility.",),
    )


def failed_reuse(skill_id: str = "skill-001") -> SkillReuseEvidenceRecord:
    return SkillReuseEvidenceRecord(
        reuse_id="reuse-failed-001",
        skill_id=skill_id,
        outcome_id="outcome-001",
        evidence_ids=(),
        succeeded=False,
        audit_index=2,
        applicability_condition_ids=(),
        failure_mode_ids=("hidden-failed-check",),
        reasons=("The reusable check missed a hidden failed check.",),
    )


def validated_skill_ledger() -> SkillValidationLedger:
    return evaluate_skill_candidates(
        candidates=(skill_candidate(),),
        reuse_records=(successful_reuse(),),
        memory_ledger=memory_ledger(),
        outcome_ledger=outcome_ledger(),
        reviewer_role_id="learning-archivist",
    )


def needs_reuse_skill_ledger() -> SkillValidationLedger:
    return evaluate_skill_candidates(
        candidates=(skill_candidate(),),
        reuse_records=(),
        memory_ledger=memory_ledger(),
        outcome_ledger=outcome_ledger(),
        reviewer_role_id="learning-archivist",
    )


def rejected_skill_ledger() -> SkillValidationLedger:
    return evaluate_skill_candidates(
        candidates=(skill_candidate(),),
        reuse_records=(failed_reuse(),),
        memory_ledger=memory_ledger(),
        outcome_ledger=outcome_ledger(),
        reviewer_role_id="learning-archivist",
    )


def blocked_skill_ledger() -> SkillValidationLedger:
    return evaluate_skill_candidates(
        candidates=(skill_candidate(),),
        reuse_records=(successful_reuse(),),
        memory_ledger=memory_ledger(status=MemoryValidationStatus.REJECTED),
        outcome_ledger=outcome_ledger(),
        reviewer_role_id="learning-archivist",
    )


def role_bundle(
    required_role_ids: tuple[str, ...] = DEFAULT_SKILL_GENOME_REVIEW_SCOPE,
) -> RoleArtifactBundle:
    return RoleArtifactBundle(
        bundle_id="skill-role-bundle-001",
        records=tuple(
            complete_role_artifact_record(
                role_id, evidence_ids=(f"role-evidence:{role_id}",)
            )
            for role_id in required_role_ids
        ),
        required_role_ids=required_role_ids,
    )


def ready_update(update_id: str = "skill-update-001") -> SkillGenomeUpdateRecord:
    return SkillGenomeUpdateRecord(
        update_id=update_id,
        skill_ledger=validated_skill_ledger(),
        role_artifact_bundle=role_bundle(),
        evidence_ids=(f"update-evidence:{update_id}",),
        allowed_transfer_domains=("repo governance evidence checks",),
        reuse_limitations=("Requires fresh evidence review before every reuse.",),
    )


def test_skill_genome_review_scope_is_locked() -> None:
    assert SKILL_GENOME_REVIEWER_ROLE_ID == "learning-archivist"
    assert DEFAULT_SKILL_GENOME_REVIEW_SCOPE == (
        "learning-archivist",
        "verifier",
        "skeptic-red-team",
        "memory-integrity-specialist",
    )


def test_ready_skill_genome_update_is_reviewable_not_installed() -> None:
    update = ready_update()

    assert update.status is SkillGenomeUpdateStatus.READY_FOR_HUMAN_REVIEW
    assert update.ready_for_human_review is True
    assert update.may_request_skill_genome_update_review is True
    assert update.permits_automatic_skill_install is False
    assert update.permits_automatic_execution is False
    assert update.human_authority_state is WaveThreeAuthorityState.HUMAN_REVIEW_REQUIRED
    assert update.validated_skill_ids == ("skill-001",)
    assert update.readiness_gaps == ()
    assert update.blocking_gaps == ()
    assert "automatic skill install is not permitted" in update.review_summary


def test_skill_genome_update_requires_learning_archivist_scope() -> None:
    with pytest.raises(ValueError, match="require learning-archivist"):
        SkillGenomeUpdateRecord(
            update_id="skill-update-001",
            skill_ledger=validated_skill_ledger(),
            role_artifact_bundle=role_bundle(("verifier",)),
            required_role_ids=("verifier",),
            evidence_ids=("update-evidence",),
            allowed_transfer_domains=("repo governance",),
            reuse_limitations=("review before reuse",),
        )


def test_skill_genome_update_requires_learning_archivist_reviewer() -> None:
    with pytest.raises(ValueError, match="must be reviewed by learning-archivist"):
        SkillGenomeUpdateRecord(
            update_id="skill-update-001",
            skill_ledger=validated_skill_ledger(),
            role_artifact_bundle=role_bundle(),
            evidence_ids=("update-evidence",),
            allowed_transfer_domains=("repo governance",),
            reuse_limitations=("review before reuse",),
            reviewer_role_id="verifier",
        )


def test_skill_genome_update_rejects_validation_from_wrong_role() -> None:
    ledger = SkillValidationLedger(
        candidates=(skill_candidate(),),
        reuse_records=(successful_reuse(),),
        validations=(
            SkillValidationRecord(
                validation_id="skill-validation-001",
                skill_id="skill-001",
                status=SkillValidationStatus.VALIDATED,
                source_memory_candidate_ids=("memory-candidate-001",),
                source_outcome_ids=("outcome-001",),
                reuse_evidence_ids=("reuse-001",),
                reviewer_role_id="verifier",
                reasons=("Wrong reviewer role should fail closed.",),
            ),
        ),
    )

    with pytest.raises(ValueError, match="must be reviewed by learning-archivist"):
        SkillGenomeUpdateRecord(
            update_id="skill-update-001",
            skill_ledger=ledger,
            role_artifact_bundle=role_bundle(),
            evidence_ids=("update-evidence",),
            allowed_transfer_domains=("repo governance",),
            reuse_limitations=("review before reuse",),
        )


def test_skill_needing_reuse_evidence_cannot_request_genome_update() -> None:
    update = SkillGenomeUpdateRecord(
        update_id="skill-update-001",
        skill_ledger=needs_reuse_skill_ledger(),
        role_artifact_bundle=role_bundle(),
        evidence_ids=("update-evidence",),
        allowed_transfer_domains=("repo governance",),
        reuse_limitations=("review before reuse",),
    )

    assert update.status is SkillGenomeUpdateStatus.NEEDS_REUSE_EVIDENCE
    assert update.ready_for_human_review is False
    assert update.may_request_skill_genome_update_review is False
    assert update.needs_reuse_evidence_skill_ids == ("skill-001",)
    assert "skill candidates need reuse evidence: skill-001" in update.readiness_gaps


def test_rejected_and_blocked_skills_block_genome_update() -> None:
    rejected = SkillGenomeUpdateRecord(
        update_id="skill-update-rejected",
        skill_ledger=rejected_skill_ledger(),
        role_artifact_bundle=role_bundle(),
        evidence_ids=("update-evidence",),
        allowed_transfer_domains=("repo governance",),
        reuse_limitations=("review before reuse",),
    )
    blocked = SkillGenomeUpdateRecord(
        update_id="skill-update-blocked",
        skill_ledger=blocked_skill_ledger(),
        role_artifact_bundle=role_bundle(),
        evidence_ids=("update-evidence",),
        allowed_transfer_domains=("repo governance",),
        reuse_limitations=("review before reuse",),
    )

    assert rejected.status is SkillGenomeUpdateStatus.BLOCKED
    assert rejected.rejected_skill_ids == ("skill-001",)
    assert rejected.blocking_gaps == ("skill candidates rejected: skill-001",)
    assert blocked.status is SkillGenomeUpdateStatus.BLOCKED
    assert blocked.blocked_skill_ids == ("skill-001",)
    assert blocked.blocking_gaps == ("skill candidates blocked: skill-001",)


def test_validated_skill_requires_transfer_limits_and_reuse_limits() -> None:
    update = SkillGenomeUpdateRecord(
        update_id="skill-update-001",
        skill_ledger=validated_skill_ledger(),
        role_artifact_bundle=role_bundle(),
        evidence_ids=("update-evidence",),
        allowed_transfer_domains=(),
        reuse_limitations=(),
    )

    assert update.status is SkillGenomeUpdateStatus.NEEDS_EVIDENCE
    assert "validated skills require allowed transfer domains" in update.readiness_gaps
    assert "validated skills require explicit reuse limitations" in update.readiness_gaps


def test_incomplete_learning_archivist_role_blocks_update_review() -> None:
    incomplete_learning_role = RoleArtifactRecord(
        role_id="learning-archivist",
        produced_output_artifacts=(ArtifactKind.OUTCOME_DELTA,),
        consumed_input_artifacts=(ArtifactKind.WORLD_MODEL,),
        evidence_ids=("role-evidence:learning",),
        rationale="Missing evidence-check input keeps skill review incomplete.",
    )
    roles = (incomplete_learning_role,) + tuple(
        complete_role_artifact_record(
            role_id, evidence_ids=(f"role-evidence:{role_id}",)
        )
        for role_id in DEFAULT_SKILL_GENOME_REVIEW_SCOPE
        if role_id != "learning-archivist"
    )
    update = SkillGenomeUpdateRecord(
        update_id="skill-update-001",
        skill_ledger=validated_skill_ledger(),
        role_artifact_bundle=RoleArtifactBundle(
            bundle_id="skill-role-bundle-001",
            records=roles,
            required_role_ids=DEFAULT_SKILL_GENOME_REVIEW_SCOPE,
        ),
        evidence_ids=("update-evidence",),
        allowed_transfer_domains=("repo governance",),
        reuse_limitations=("review before reuse",),
    )

    assert update.status is SkillGenomeUpdateStatus.NEEDS_EVIDENCE
    assert "incomplete required skill-review roles: learning-archivist" in (
        update.readiness_gaps
    )
    assert "validated skills require complete learning-archivist role artifact" in (
        update.readiness_gaps
    )


def test_blocked_required_role_blocks_skill_genome_update() -> None:
    blocked_learning_role = RoleArtifactRecord(
        role_id="learning-archivist",
        produced_output_artifacts=(ArtifactKind.OUTCOME_DELTA,),
        consumed_input_artifacts=(ArtifactKind.WORLD_MODEL, ArtifactKind.EVIDENCE_CHECK),
        evidence_ids=("role-evidence:learning",),
        rationale="Learning role blocks because reuse evidence is contradictory.",
        status=RoleArtifactStatus.BLOCKED,
        authority=RoleArtifactAuthority.BLOCKED,
        paired_engine_ids=("outcome-learning", "skill-genome"),
        blocking_reasons=("Contradictory reuse evidence requires rejection.",),
    )
    roles = (blocked_learning_role,) + tuple(
        complete_role_artifact_record(
            role_id, evidence_ids=(f"role-evidence:{role_id}",)
        )
        for role_id in DEFAULT_SKILL_GENOME_REVIEW_SCOPE
        if role_id != "learning-archivist"
    )
    update = SkillGenomeUpdateRecord(
        update_id="skill-update-001",
        skill_ledger=validated_skill_ledger(),
        role_artifact_bundle=RoleArtifactBundle(
            bundle_id="skill-role-bundle-001",
            records=roles,
            required_role_ids=DEFAULT_SKILL_GENOME_REVIEW_SCOPE,
        ),
        evidence_ids=("update-evidence",),
        allowed_transfer_domains=("repo governance",),
        reuse_limitations=("review before reuse",),
    )

    assert update.status is SkillGenomeUpdateStatus.BLOCKED
    assert "blocked required skill-review roles: learning-archivist" in (
        update.blocking_gaps
    )


def test_skill_genome_update_converts_to_shared_artifact_ref() -> None:
    artifact = ready_update().to_artifact_ref()

    assert artifact.artifact_id == "skill-genome-update:skill-update-001"
    assert artifact.kind is WaveThreeArtifactKind.SKILL_GENOME_UPDATE
    assert artifact.produced_by_engine_id == "skill-genome"
    assert artifact.produced_by_agent_role_id == "learning-archivist"
    assert artifact.allowed_for_automatic_execution is False
    assert artifact.ready_for_human_review is True


def test_skill_genome_update_artifact_bundle_links_all_evidence() -> None:
    bundle = ready_update().to_artifact_bundle(
        artifact_bundle_id="skill-update-artifacts"
    )

    assert bundle.has_required_kind_coverage is True
    assert bundle.artifact_ids == ("skill-genome-update:skill-update-001",)
    assert bundle.ready_for_human_review_artifact_ids == (
        "skill-genome-update:skill-update-001",
    )
    assert bundle.evidence_link_table == {
        "skill-genome-update:skill-update-001": (
            "reuse-evidence-001",
            "update-evidence:skill-update-001",
        )
    }


def test_skill_genome_update_bundle_reports_ready_and_blocked_updates() -> None:
    ready = ready_update("skill-update-ready")
    blocked = SkillGenomeUpdateRecord(
        update_id="skill-update-blocked",
        skill_ledger=blocked_skill_ledger(),
        role_artifact_bundle=role_bundle(),
        evidence_ids=("update-evidence:blocked",),
        allowed_transfer_domains=("repo governance",),
        reuse_limitations=("review before reuse",),
    )
    bundle = SkillGenomeUpdateBundle(
        bundle_id="skill-update-bundle-001",
        updates=(blocked, ready),
    )

    assert bundle.update_ids == ("skill-update-blocked", "skill-update-ready")
    assert bundle.ready_update_ids == ("skill-update-ready",)
    assert bundle.blocked_update_ids == ("skill-update-blocked",)
    assert bundle.is_complete_for_human_review is False


def test_skill_genome_update_bundle_rejects_duplicate_updates() -> None:
    update = ready_update()

    with pytest.raises(ValueError, match="Duplicate update_id"):
        SkillGenomeUpdateBundle(
            bundle_id="skill-update-bundle-001",
            updates=(update, update),
        )


def test_skill_genome_update_fingerprints_are_deterministic() -> None:
    first = ready_update().fingerprint()
    second = ready_update().fingerprint()
    bundle_first = SkillGenomeUpdateBundle(
        bundle_id="skill-update-bundle-001",
        updates=(ready_update(),),
    ).fingerprint()
    bundle_second = SkillGenomeUpdateBundle(
        bundle_id="skill-update-bundle-001",
        updates=(ready_update(),),
    ).fingerprint()

    assert first == second
    assert len(first) == 64
    assert bundle_first == bundle_second
    assert len(bundle_first) == 64
