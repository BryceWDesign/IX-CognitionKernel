import pytest

from ix_cognition_kernel.wave3_assurance import (
    REQUIRED_ASSURANCE_CLAIM_KINDS,
    AssuranceClaim,
    AssuranceClaimKind,
    AssuranceClaimStatus,
    AssuranceRecord,
    AssuranceRecordBundle,
    AssuranceRecordStatus,
    supported_assurance_claim,
)
from ix_cognition_kernel.wave3_contracts import (
    WaveThreeArtifactBundle,
    WaveThreeArtifactDecision,
    WaveThreeArtifactKind,
    WaveThreeArtifactRef,
    WaveThreeAuthorityState,
    WaveThreeEvidenceLink,
    WaveThreeEvidenceRelation,
    WaveThreeSourceSystem,
)

REQUIRED_ARTIFACT_IDS = {
    WaveThreeArtifactKind.ENGINE_COORDINATION: "engine-coordination:belief",
    WaveThreeArtifactKind.ROLE_ARTIFACT: "role-artifact:verifier",
    WaveThreeArtifactKind.TRIBUNAL_RECORD: "tribunal-record:tribunal-001",
    WaveThreeArtifactKind.REWARD_AUDIT: "reward-audit:reward-001",
    WaveThreeArtifactKind.CURRICULUM_TASK: "curriculum-task:task-001",
    WaveThreeArtifactKind.DISCOVERY_RECORD: "discovery-record:discovery-001",
    WaveThreeArtifactKind.MEMORY_QUARANTINE_DECISION: (
        "memory-quarantine-decision:memory-001"
    ),
    WaveThreeArtifactKind.SKILL_GENOME_UPDATE: "skill-genome-update:skill-001",
    WaveThreeArtifactKind.WORLDTWIN_SCENARIO: "worldtwin-scenario:scenario-001",
    WaveThreeArtifactKind.BLACKFOX_HANDOFF: "blackfox-handoff:handoff-001",
    WaveThreeArtifactKind.ASSURANCE_RECORD: "assurance-record:prior-001",
    WaveThreeArtifactKind.READINESS_SNAPSHOT: "readiness-snapshot:prior-001",
}


def artifact(kind: WaveThreeArtifactKind) -> WaveThreeArtifactRef:
    source = (
        WaveThreeSourceSystem.IX_BLACKFOX
        if kind is WaveThreeArtifactKind.BLACKFOX_HANDOFF
        else WaveThreeSourceSystem.IX_BLACKFOX_WORLDTWIN
        if kind is WaveThreeArtifactKind.WORLDTWIN_SCENARIO
        else WaveThreeSourceSystem.IX_COGNITION_KERNEL
    )
    return WaveThreeArtifactRef(
        artifact_id=REQUIRED_ARTIFACT_IDS[kind],
        kind=kind,
        source_system=source,
        summary=f"{kind.value} is represented for assurance review.",
        produced_by_engine_id="evaluator",
        produced_by_agent_role_id="verifier",
        evidence_ids=(f"evidence:{kind.value}",),
        decision=WaveThreeArtifactDecision.READY_FOR_HUMAN_REVIEW,
        authority_state=WaveThreeAuthorityState.HUMAN_REVIEW_REQUIRED,
    )


def artifact_bundle(
    kinds: tuple[WaveThreeArtifactKind, ...] = tuple(REQUIRED_ARTIFACT_IDS),
) -> WaveThreeArtifactBundle:
    artifacts = tuple(artifact(kind) for kind in kinds)
    return WaveThreeArtifactBundle(
        bundle_id="wave3-artifact-bundle-001",
        artifacts=artifacts,
        evidence_links=tuple(
            WaveThreeEvidenceLink(
                evidence_id=evidence_id,
                artifact_id=item.artifact_id,
                relation=WaveThreeEvidenceRelation.SUPPORTS,
                summary="Artifact evidence supports assurance review.",
                source_system=WaveThreeSourceSystem.LOCAL_TEST_SUITE,
            )
            for item in artifacts
            for evidence_id in item.evidence_ids
        ),
        required_kinds=kinds,
    )


def claim(
    claim_kind: AssuranceClaimKind,
    *,
    claim_id: str | None = None,
    supporting_artifact_ids: tuple[str, ...] = (
        "tribunal-record:tribunal-001",
        "blackfox-handoff:handoff-001",
    ),
) -> AssuranceClaim:
    return supported_assurance_claim(
        claim_id=claim_id or f"claim:{claim_kind.value}",
        claim_kind=claim_kind,
        statement=f"The substrate satisfies bounded {claim_kind.value} review.",
        supporting_artifact_ids=supporting_artifact_ids,
        evidence_ids=(f"evidence:claim:{claim_kind.value}",),
        limitations=(
            "This claim supports human review only; it is not certification.",
            "This claim does not prove AGI or production readiness.",
        ),
    )


def complete_claims() -> tuple[AssuranceClaim, ...]:
    return tuple(claim(kind) for kind in REQUIRED_ASSURANCE_CLAIM_KINDS)


def ready_record(assurance_id: str = "assurance-001") -> AssuranceRecord:
    return AssuranceRecord(
        assurance_id=assurance_id,
        artifact_bundles=(artifact_bundle(),),
        claims=complete_claims(),
        evidence_ids=(f"evidence:{assurance_id}",),
    )


def test_required_assurance_claim_kinds_are_locked() -> None:
    assert REQUIRED_ASSURANCE_CLAIM_KINDS == (
        AssuranceClaimKind.EVIDENCE_TRACEABILITY,
        AssuranceClaimKind.HUMAN_AUTHORITY_PRESERVED,
        AssuranceClaimKind.NO_AUTOMATIC_EXECUTION,
        AssuranceClaimKind.UNCERTAINTY_VISIBLE,
        AssuranceClaimKind.DONOR_BOUNDARY_COMPATIBLE,
        AssuranceClaimKind.NO_AGI_OVERCLAIM,
    )


def test_supported_assurance_claim_requires_artifacts_evidence_and_limits() -> None:
    with pytest.raises(ValueError, match="require artifact ids and evidence ids"):
        supported_assurance_claim(
            claim_id="claim:bad",
            claim_kind=AssuranceClaimKind.EVIDENCE_TRACEABILITY,
            statement="Invalid supported claim.",
            supporting_artifact_ids=(),
            evidence_ids=("evidence",),
            limitations=("not certification",),
        )
    with pytest.raises(ValueError, match="explicit limitations"):
        AssuranceClaim(
            claim_id="claim:bad",
            claim_kind=AssuranceClaimKind.EVIDENCE_TRACEABILITY,
            statement="Invalid claim without limitations.",
            supporting_artifact_ids=("artifact",),
            evidence_ids=("evidence",),
            limitations=(),
            confidence=0.5,
        )


def test_assurance_claim_confidence_is_bounded() -> None:
    with pytest.raises(ValueError, match="confidence must be between"):
        supported_assurance_claim(
            claim_id="claim:bad",
            claim_kind=AssuranceClaimKind.NO_AGI_OVERCLAIM,
            statement="Invalid confidence.",
            supporting_artifact_ids=("artifact",),
            evidence_ids=("evidence",),
            limitations=("not certification",),
            confidence=1.5,
        )


def test_blocked_claim_requires_blocking_reason() -> None:
    with pytest.raises(ValueError, match="Blocked assurance claims require"):
        AssuranceClaim(
            claim_id="claim:blocked",
            claim_kind=AssuranceClaimKind.NO_AUTOMATIC_EXECUTION,
            statement="Blocked claim without reason should fail closed.",
            supporting_artifact_ids=("artifact",),
            evidence_ids=("evidence",),
            limitations=("not certification",),
            confidence=0.7,
            status=AssuranceClaimStatus.BLOCKED,
        )


def test_ready_assurance_record_is_reviewable_not_certification_or_execution() -> None:
    record = ready_record()

    assert record.status is AssuranceRecordStatus.READY_FOR_HUMAN_REVIEW
    assert record.ready_for_human_review is True
    assert record.permits_automatic_execution is False
    assert record.certifies_agi is False
    assert record.human_authority_state is WaveThreeAuthorityState.HUMAN_REVIEW_REQUIRED
    assert record.missing_required_artifact_kinds == ()
    assert record.missing_required_claim_kinds == ()
    assert record.readiness_gaps == ()
    assert record.blocking_gaps == ()
    assert "AGI certification are not permitted" in record.review_summary


def test_assurance_record_rejects_claim_that_references_missing_artifact() -> None:
    with pytest.raises(ValueError, match="must reference bundled artifact ids"):
        AssuranceRecord(
            assurance_id="assurance-001",
            artifact_bundles=(artifact_bundle(),),
            claims=(
                claim(
                    AssuranceClaimKind.EVIDENCE_TRACEABILITY,
                    supporting_artifact_ids=("missing-artifact",),
                ),
            ),
            evidence_ids=("evidence:assurance",),
            required_claim_kinds=(AssuranceClaimKind.EVIDENCE_TRACEABILITY,),
        )


def test_assurance_record_reports_missing_artifact_and_claim_kinds() -> None:
    record = AssuranceRecord(
        assurance_id="assurance-001",
        artifact_bundles=(
            artifact_bundle(
                (
                    WaveThreeArtifactKind.TRIBUNAL_RECORD,
                    WaveThreeArtifactKind.BLACKFOX_HANDOFF,
                )
            ),
        ),
        claims=(claim(AssuranceClaimKind.EVIDENCE_TRACEABILITY),),
        evidence_ids=("evidence:assurance",),
    )

    assert record.status is AssuranceRecordStatus.NEEDS_EVIDENCE
    assert WaveThreeArtifactKind.ENGINE_COORDINATION in (
        record.missing_required_artifact_kinds
    )
    assert AssuranceClaimKind.NO_AGI_OVERCLAIM in record.missing_required_claim_kinds
    assert any(
        gap.startswith("missing required Wave 3 artifact kinds")
        for gap in record.readiness_gaps
    )
    assert any(
        gap.startswith("missing required assurance claim kinds")
        for gap in record.readiness_gaps
    )


def test_assurance_record_needs_repair_when_claim_is_unsupported() -> None:
    unsupported = AssuranceClaim(
        claim_id="claim:uncertainty-visible",
        claim_kind=AssuranceClaimKind.UNCERTAINTY_VISIBLE,
        statement="Uncertainty visibility needs more evidence.",
        supporting_artifact_ids=("tribunal-record:tribunal-001",),
        evidence_ids=(),
        limitations=("not certification",),
        confidence=0.5,
        status=AssuranceClaimStatus.NEEDS_EVIDENCE,
    )
    record = AssuranceRecord(
        assurance_id="assurance-001",
        artifact_bundles=(artifact_bundle(),),
        claims=(unsupported,),
        evidence_ids=("evidence:assurance",),
        required_claim_kinds=(AssuranceClaimKind.UNCERTAINTY_VISIBLE,),
    )

    assert record.status is AssuranceRecordStatus.NEEDS_REPAIR
    assert record.unsupported_claim_ids == ("claim:uncertainty-visible",)
    assert "unsupported assurance claims: claim:uncertainty-visible" in (
        record.readiness_gaps
    )


def test_assurance_record_blocks_when_claim_blocks() -> None:
    blocked = AssuranceClaim(
        claim_id="claim:no-automatic-execution",
        claim_kind=AssuranceClaimKind.NO_AUTOMATIC_EXECUTION,
        statement="Execution boundary is contradicted.",
        supporting_artifact_ids=("blackfox-handoff:handoff-001",),
        evidence_ids=("evidence:block",),
        limitations=("not certification",),
        confidence=0.2,
        status=AssuranceClaimStatus.BLOCKED,
        blocking_reasons=("A downstream artifact attempted automatic execution.",),
    )
    record = AssuranceRecord(
        assurance_id="assurance-001",
        artifact_bundles=(artifact_bundle(),),
        claims=(blocked,),
        evidence_ids=("evidence:assurance",),
        required_claim_kinds=(AssuranceClaimKind.NO_AUTOMATIC_EXECUTION,),
    )

    assert record.status is AssuranceRecordStatus.BLOCKED
    assert record.human_authority_state is WaveThreeAuthorityState.BLOCKED
    assert record.blocked_claim_ids == ("claim:no-automatic-execution",)
    assert "blocked assurance claims: claim:no-automatic-execution" in (
        record.blocking_gaps
    )


def test_assurance_record_blocks_when_bundled_artifact_blocks() -> None:
    blocked_artifact = WaveThreeArtifactRef(
        artifact_id="blackfox-handoff:handoff-blocked",
        kind=WaveThreeArtifactKind.BLACKFOX_HANDOFF,
        source_system=WaveThreeSourceSystem.IX_BLACKFOX,
        summary="Blocked handoff artifact.",
        produced_by_engine_id="blackfox-handoff",
        produced_by_agent_role_id="execution-liaison",
        evidence_ids=("evidence:blocked",),
        decision=WaveThreeArtifactDecision.BLOCKED,
        authority_state=WaveThreeAuthorityState.BLOCKED,
    )
    bundle = WaveThreeArtifactBundle(
        bundle_id="bundle-blocked",
        artifacts=(blocked_artifact,),
        evidence_links=(
            WaveThreeEvidenceLink(
                evidence_id="evidence:blocked",
                artifact_id="blackfox-handoff:handoff-blocked",
                relation=WaveThreeEvidenceRelation.BLOCKS,
                summary="Blocked artifact evidence.",
                source_system=WaveThreeSourceSystem.IX_BLACKFOX,
            ),
        ),
        required_kinds=(WaveThreeArtifactKind.BLACKFOX_HANDOFF,),
    )
    record = AssuranceRecord(
        assurance_id="assurance-001",
        artifact_bundles=(bundle,),
        claims=(
            claim(
                AssuranceClaimKind.NO_AUTOMATIC_EXECUTION,
                supporting_artifact_ids=("blackfox-handoff:handoff-blocked",),
            ),
        ),
        evidence_ids=("evidence:assurance",),
        required_claim_kinds=(AssuranceClaimKind.NO_AUTOMATIC_EXECUTION,),
        required_artifact_kinds=(WaveThreeArtifactKind.BLACKFOX_HANDOFF,),
    )

    assert record.status is AssuranceRecordStatus.BLOCKED
    assert record.blocked_artifact_ids == ("blackfox-handoff:handoff-blocked",)
    assert "blocked Wave 3 artifacts: blackfox-handoff:handoff-blocked" in (
        record.blocking_gaps
    )


def test_assurance_record_converts_to_shared_artifact_ref() -> None:
    artifact_ref = ready_record().to_artifact_ref()

    assert artifact_ref.artifact_id == "assurance-record:assurance-001"
    assert artifact_ref.kind is WaveThreeArtifactKind.ASSURANCE_RECORD
    assert artifact_ref.source_system is WaveThreeSourceSystem.IX_COGNITION_KERNEL
    assert artifact_ref.produced_by_engine_id == "evaluator"
    assert artifact_ref.produced_by_agent_role_id == "verifier"
    assert artifact_ref.allowed_for_automatic_execution is False
    assert artifact_ref.ready_for_human_review is True


def test_assurance_record_artifact_bundle_links_all_evidence() -> None:
    bundle = ready_record().to_artifact_bundle(artifact_bundle_id="assurance-artifacts")

    assert bundle.has_required_kind_coverage is True
    assert bundle.artifact_ids == ("assurance-record:assurance-001",)
    assert bundle.ready_for_human_review_artifact_ids == (
        "assurance-record:assurance-001",
    )
    assert (
        "evidence:assurance-001"
        in bundle.evidence_link_table["assurance-record:assurance-001"]
    )
    assert (
        "evidence:claim:no-agi-overclaim"
        in bundle.evidence_link_table["assurance-record:assurance-001"]
    )


def test_assurance_record_bundle_reports_ready_and_blocked_records() -> None:
    ready = ready_record("assurance-ready")
    blocked = AssuranceRecord(
        assurance_id="assurance-blocked",
        artifact_bundles=(artifact_bundle(),),
        claims=(
            AssuranceClaim(
                claim_id="claim:blocked",
                claim_kind=AssuranceClaimKind.NO_AUTOMATIC_EXECUTION,
                statement="Blocked claim.",
                supporting_artifact_ids=("blackfox-handoff:handoff-001",),
                evidence_ids=("evidence:blocked-claim",),
                limitations=("not certification",),
                confidence=0.1,
                status=AssuranceClaimStatus.BLOCKED,
                blocking_reasons=("Execution boundary is contradicted.",),
            ),
        ),
        evidence_ids=("evidence:assurance-blocked",),
        required_claim_kinds=(AssuranceClaimKind.NO_AUTOMATIC_EXECUTION,),
    )
    bundle = AssuranceRecordBundle(
        bundle_id="assurance-bundle-001",
        records=(blocked, ready),
    )

    assert bundle.assurance_ids == ("assurance-blocked", "assurance-ready")
    assert bundle.ready_assurance_ids == ("assurance-ready",)
    assert bundle.blocked_assurance_ids == ("assurance-blocked",)
    assert bundle.is_complete_for_human_review is False


def test_assurance_record_bundle_rejects_duplicate_records() -> None:
    record = ready_record()

    with pytest.raises(ValueError, match="Duplicate assurance_id"):
        AssuranceRecordBundle(
            bundle_id="assurance-bundle-001",
            records=(record, record),
        )


def test_assurance_fingerprints_are_deterministic() -> None:
    first = ready_record().fingerprint()
    second = ready_record().fingerprint()
    bundle_first = AssuranceRecordBundle(
        bundle_id="assurance-bundle-001",
        records=(ready_record(),),
    ).fingerprint()
    bundle_second = AssuranceRecordBundle(
        bundle_id="assurance-bundle-001",
        records=(ready_record(),),
    ).fingerprint()

    assert first == second
    assert len(first) == 64
    assert bundle_first == bundle_second
    assert len(bundle_first) == 64
