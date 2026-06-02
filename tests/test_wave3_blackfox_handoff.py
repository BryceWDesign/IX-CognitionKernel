import pytest

from ix_cognition_kernel.wave3_blackfox_handoff import (
    REQUIRED_BLACKFOX_BOUNDARY_KINDS,
    REQUIRED_BLACKFOX_REVIEW_REQUIREMENT_KINDS,
    BlackFoxExecutionBoundary,
    BlackFoxHandoffBoundaryKind,
    BlackFoxHandoffBundle,
    BlackFoxHandoffPackage,
    BlackFoxHandoffStatus,
    BlackFoxReviewRequirement,
    BlackFoxReviewRequirementKind,
    BlackFoxRollbackReference,
)
from ix_cognition_kernel.wave3_contracts import (
    WaveThreeArtifactKind,
    WaveThreeAuthorityState,
    WaveThreeSourceSystem,
)


def boundary(kind: BlackFoxHandoffBoundaryKind) -> BlackFoxExecutionBoundary:
    return BlackFoxExecutionBoundary(
        boundary_id=f"boundary:{kind.value}",
        kind=kind,
        description=f"{kind.value} keeps the handoff inside BlackFox review bounds.",
        evidence_ids=(f"evidence:boundary:{kind.value}",),
    )


def required_boundaries() -> tuple[BlackFoxExecutionBoundary, ...]:
    return tuple(boundary(kind) for kind in REQUIRED_BLACKFOX_BOUNDARY_KINDS)


def requirement(
    kind: BlackFoxReviewRequirementKind,
    *,
    satisfied: bool = True,
) -> BlackFoxReviewRequirement:
    return BlackFoxReviewRequirement(
        requirement_id=f"requirement:{kind.value}",
        requirement_kind=kind,
        reviewer_role="human-reviewer",
        description=f"{kind.value} must be visible before BlackFox review.",
        evidence_ids=(f"evidence:requirement:{kind.value}",) if satisfied else (),
        satisfied=satisfied,
    )


def required_requirements() -> tuple[BlackFoxReviewRequirement, ...]:
    return tuple(
        requirement(kind) for kind in REQUIRED_BLACKFOX_REVIEW_REQUIREMENT_KINDS
    )


def rollback(validated: bool = True) -> BlackFoxRollbackReference:
    return BlackFoxRollbackReference(
        rollback_id="rollback:review-package",
        description="Rollback to the pre-handoff cognition package if review fails.",
        trigger_conditions=(
            "Stop if policy evidence is missing.",
            "Stop if human authority is absent.",
        ),
        evidence_ids=("evidence:rollback",) if validated else (),
        validated=validated,
    )


def ready_package(handoff_id: str = "handoff-001") -> BlackFoxHandoffPackage:
    return BlackFoxHandoffPackage(
        handoff_id=handoff_id,
        subject="IX-CognitionKernel Wave 3 review-only cognition handoff",
        cognition_artifact_ids=(
            "tribunal-record:tribunal-001",
            "worldtwin-scenario:scenario-001",
        ),
        evidence_bundle_ids=("wave3-artifact-bundle:substrate-001",),
        execution_boundaries=required_boundaries(),
        review_requirements=required_requirements(),
        rollback_references=(rollback(),),
        evidence_ids=(f"evidence:{handoff_id}",),
    )


def test_required_blackfox_boundary_and_review_kinds_are_locked() -> None:
    assert REQUIRED_BLACKFOX_BOUNDARY_KINDS == (
        BlackFoxHandoffBoundaryKind.POLICY_GATE,
        BlackFoxHandoffBoundaryKind.WORKSPACE_ISOLATION,
        BlackFoxHandoffBoundaryKind.EGRESS_CONTROL,
        BlackFoxHandoffBoundaryKind.TEST_ALLOWLIST,
        BlackFoxHandoffBoundaryKind.HUMAN_REVIEW,
        BlackFoxHandoffBoundaryKind.ROLLBACK,
    )
    assert REQUIRED_BLACKFOX_REVIEW_REQUIREMENT_KINDS == (
        BlackFoxReviewRequirementKind.HUMAN_APPROVAL,
        BlackFoxReviewRequirementKind.POLICY_REVIEW,
        BlackFoxReviewRequirementKind.EVIDENCE_REPLAY,
        BlackFoxReviewRequirementKind.ROLLBACK_REVIEW,
        BlackFoxReviewRequirementKind.NO_SELF_APPROVAL,
    )


def test_ready_blackfox_handoff_is_reviewable_not_executable() -> None:
    package = ready_package()

    assert package.status is BlackFoxHandoffStatus.READY_FOR_HUMAN_REVIEW
    assert package.ready_for_human_review is True
    assert package.permits_automatic_execution is False
    assert package.human_authority_state is WaveThreeAuthorityState.HUMAN_REVIEW_REQUIRED
    assert package.missing_required_boundary_kinds == ()
    assert package.missing_required_review_requirement_kinds == ()
    assert package.readiness_gaps == ()
    assert package.blocking_gaps == ()
    assert "automatic execution is not permitted" in package.review_summary


def test_blackfox_boundary_requires_evidence_when_enforced() -> None:
    with pytest.raises(ValueError, match="Enforced BlackFox boundaries require"):
        BlackFoxExecutionBoundary(
            boundary_id="boundary:policy",
            kind=BlackFoxHandoffBoundaryKind.POLICY_GATE,
            description="Policy gate must have evidence.",
            evidence_ids=(),
        )


def test_blackfox_review_requirement_forbids_model_or_system_self_approval() -> None:
    with pytest.raises(ValueError, match="forbid model/system self-approval"):
        BlackFoxReviewRequirement(
            requirement_id="requirement:no-self-approval",
            requirement_kind=BlackFoxReviewRequirementKind.NO_SELF_APPROVAL,
            reviewer_role="human-reviewer",
            description="Self approval must be forbidden.",
            evidence_ids=("evidence:self-approval",),
            forbids_model_or_system_self_approval=False,
        )


def test_satisfied_review_requirement_requires_evidence() -> None:
    with pytest.raises(ValueError, match="Satisfied BlackFox review requirements"):
        BlackFoxReviewRequirement(
            requirement_id="requirement:human-approval",
            requirement_kind=BlackFoxReviewRequirementKind.HUMAN_APPROVAL,
            reviewer_role="human-reviewer",
            description="Human approval requirement must have evidence.",
            evidence_ids=(),
            satisfied=True,
        )


def test_rollback_references_require_triggers_and_evidence_when_validated() -> None:
    with pytest.raises(ValueError, match="require trigger conditions"):
        BlackFoxRollbackReference(
            rollback_id="rollback:missing-trigger",
            description="Invalid rollback.",
            trigger_conditions=(),
            evidence_ids=("evidence:rollback",),
        )
    with pytest.raises(ValueError, match="Validated BlackFox rollback"):
        BlackFoxRollbackReference(
            rollback_id="rollback:missing-evidence",
            description="Invalid rollback.",
            trigger_conditions=("Stop on missing evidence.",),
            evidence_ids=(),
            validated=True,
        )


def test_handoff_rejects_automatic_execution_or_missing_human_authority() -> None:
    with pytest.raises(ValueError, match="must require human authority"):
        BlackFoxHandoffPackage(
            handoff_id="handoff-001",
            subject="Invalid handoff.",
            cognition_artifact_ids=("artifact",),
            evidence_bundle_ids=("bundle",),
            execution_boundaries=required_boundaries(),
            review_requirements=required_requirements(),
            rollback_references=(rollback(),),
            evidence_ids=("evidence",),
            requires_human_authority=False,
        )
    with pytest.raises(ValueError, match="must never allow automatic execution"):
        BlackFoxHandoffPackage(
            handoff_id="handoff-001",
            subject="Invalid handoff.",
            cognition_artifact_ids=("artifact",),
            evidence_bundle_ids=("bundle",),
            execution_boundaries=required_boundaries(),
            review_requirements=required_requirements(),
            rollback_references=(rollback(),),
            evidence_ids=("evidence",),
            allowed_for_automatic_execution=True,
        )


def test_handoff_rejects_wrong_engine_role_or_target_system() -> None:
    with pytest.raises(ValueError, match="produced by blackfox-handoff"):
        BlackFoxHandoffPackage(
            handoff_id="handoff-001",
            subject="Invalid handoff.",
            cognition_artifact_ids=("artifact",),
            evidence_bundle_ids=("bundle",),
            execution_boundaries=required_boundaries(),
            review_requirements=required_requirements(),
            rollback_references=(rollback(),),
            evidence_ids=("evidence",),
            produced_by_engine_id="planner",
        )
    with pytest.raises(ValueError, match="produced by execution-liaison"):
        BlackFoxHandoffPackage(
            handoff_id="handoff-001",
            subject="Invalid handoff.",
            cognition_artifact_ids=("artifact",),
            evidence_bundle_ids=("bundle",),
            execution_boundaries=required_boundaries(),
            review_requirements=required_requirements(),
            rollback_references=(rollback(),),
            evidence_ids=("evidence",),
            produced_by_agent_role_id="planner",
        )
    with pytest.raises(ValueError, match="target_system must be IX-BlackFox"):
        BlackFoxHandoffPackage(
            handoff_id="handoff-001",
            subject="Invalid handoff.",
            cognition_artifact_ids=("artifact",),
            evidence_bundle_ids=("bundle",),
            execution_boundaries=required_boundaries(),
            review_requirements=required_requirements(),
            rollback_references=(rollback(),),
            evidence_ids=("evidence",),
            target_system="OtherSystem",
        )


def test_handoff_reports_missing_boundary_and_review_requirement_kinds() -> None:
    package = BlackFoxHandoffPackage(
        handoff_id="handoff-001",
        subject="Incomplete BlackFox handoff.",
        cognition_artifact_ids=("artifact",),
        evidence_bundle_ids=("bundle",),
        execution_boundaries=tuple(
            boundary(kind)
            for kind in REQUIRED_BLACKFOX_BOUNDARY_KINDS
            if kind is not BlackFoxHandoffBoundaryKind.ROLLBACK
        ),
        review_requirements=tuple(
            requirement(kind)
            for kind in REQUIRED_BLACKFOX_REVIEW_REQUIREMENT_KINDS
            if kind is not BlackFoxReviewRequirementKind.ROLLBACK_REVIEW
        ),
        rollback_references=(rollback(),),
        evidence_ids=("evidence:handoff",),
    )

    assert package.status is BlackFoxHandoffStatus.NEEDS_EVIDENCE
    assert package.missing_required_boundary_kinds == (
        BlackFoxHandoffBoundaryKind.ROLLBACK,
    )
    assert package.missing_required_review_requirement_kinds == (
        BlackFoxReviewRequirementKind.ROLLBACK_REVIEW,
    )
    assert "missing BlackFox boundary kinds: rollback" in package.readiness_gaps
    assert "missing BlackFox review requirement kinds: rollback-review" in (
        package.readiness_gaps
    )


def test_unsatisfied_requirement_and_unvalidated_rollback_need_repair() -> None:
    package = BlackFoxHandoffPackage(
        handoff_id="handoff-001",
        subject="Repair-needed BlackFox handoff.",
        cognition_artifact_ids=("artifact",),
        evidence_bundle_ids=("bundle",),
        execution_boundaries=required_boundaries(),
        review_requirements=tuple(
            requirement(
                kind, satisfied=kind is not BlackFoxReviewRequirementKind.HUMAN_APPROVAL
            )
            for kind in REQUIRED_BLACKFOX_REVIEW_REQUIREMENT_KINDS
        ),
        rollback_references=(rollback(validated=False),),
        evidence_ids=("evidence:handoff",),
    )

    assert package.status is BlackFoxHandoffStatus.NEEDS_REPAIR
    assert package.unsatisfied_requirement_ids == ("requirement:human-approval",)
    assert package.unvalidated_rollback_ids == ("rollback:review-package",)
    assert "unsatisfied BlackFox review requirements: requirement:human-approval" in (
        package.readiness_gaps
    )
    assert "unvalidated BlackFox rollback references: rollback:review-package" in (
        package.readiness_gaps
    )


def test_unenforced_boundary_blocks_handoff() -> None:
    package = BlackFoxHandoffPackage(
        handoff_id="handoff-001",
        subject="Blocked BlackFox handoff.",
        cognition_artifact_ids=("artifact",),
        evidence_bundle_ids=("bundle",),
        execution_boundaries=(
            BlackFoxExecutionBoundary(
                boundary_id="boundary:policy-gate",
                kind=BlackFoxHandoffBoundaryKind.POLICY_GATE,
                description="Policy gate was documented but not enforced.",
                evidence_ids=(),
                enforced=False,
            ),
        )
        + tuple(
            boundary(kind)
            for kind in REQUIRED_BLACKFOX_BOUNDARY_KINDS
            if kind is not BlackFoxHandoffBoundaryKind.POLICY_GATE
        ),
        review_requirements=required_requirements(),
        rollback_references=(rollback(),),
        evidence_ids=("evidence:handoff",),
    )

    assert package.status is BlackFoxHandoffStatus.BLOCKED
    assert package.ready_for_human_review is False
    assert package.human_authority_state is WaveThreeAuthorityState.BLOCKED
    assert package.blocking_gaps == (
        "unenforced BlackFox execution boundaries: boundary:policy-gate",
    )


def test_blackfox_handoff_converts_to_shared_artifact_ref() -> None:
    artifact = ready_package().to_artifact_ref()

    assert artifact.artifact_id == "blackfox-handoff:handoff-001"
    assert artifact.kind is WaveThreeArtifactKind.BLACKFOX_HANDOFF
    assert artifact.source_system is WaveThreeSourceSystem.IX_BLACKFOX
    assert artifact.produced_by_engine_id == "blackfox-handoff"
    assert artifact.produced_by_agent_role_id == "execution-liaison"
    assert artifact.allowed_for_automatic_execution is False
    assert artifact.ready_for_human_review is True


def test_blackfox_handoff_artifact_bundle_links_all_evidence() -> None:
    bundle = ready_package().to_artifact_bundle(
        artifact_bundle_id="blackfox-handoff-artifacts"
    )

    assert bundle.has_required_kind_coverage is True
    assert bundle.artifact_ids == ("blackfox-handoff:handoff-001",)
    assert bundle.ready_for_human_review_artifact_ids == (
        "blackfox-handoff:handoff-001",
    )
    assert (
        "evidence:handoff-001"
        in bundle.evidence_link_table["blackfox-handoff:handoff-001"]
    )
    assert (
        "evidence:rollback"
        in bundle.evidence_link_table["blackfox-handoff:handoff-001"]
    )


def test_blackfox_handoff_bundle_reports_ready_and_blocked_packages() -> None:
    ready = ready_package("handoff-ready")
    blocked = BlackFoxHandoffPackage(
        handoff_id="handoff-blocked",
        subject="Blocked BlackFox handoff.",
        cognition_artifact_ids=("artifact",),
        evidence_bundle_ids=("bundle",),
        execution_boundaries=(
            BlackFoxExecutionBoundary(
                boundary_id="boundary:egress-control",
                kind=BlackFoxHandoffBoundaryKind.EGRESS_CONTROL,
                description="Egress boundary is not enforced.",
                evidence_ids=(),
                enforced=False,
            ),
        )
        + tuple(
            boundary(kind)
            for kind in REQUIRED_BLACKFOX_BOUNDARY_KINDS
            if kind is not BlackFoxHandoffBoundaryKind.EGRESS_CONTROL
        ),
        review_requirements=required_requirements(),
        rollback_references=(rollback(),),
        evidence_ids=("evidence:blocked",),
    )
    bundle = BlackFoxHandoffBundle(
        bundle_id="blackfox-handoff-bundle-001",
        packages=(blocked, ready),
    )

    assert bundle.handoff_ids == ("handoff-blocked", "handoff-ready")
    assert bundle.ready_handoff_ids == ("handoff-ready",)
    assert bundle.blocked_handoff_ids == ("handoff-blocked",)
    assert bundle.is_complete_for_human_review is False


def test_blackfox_handoff_bundle_rejects_duplicate_packages() -> None:
    package = ready_package()

    with pytest.raises(ValueError, match="Duplicate handoff_id"):
        BlackFoxHandoffBundle(
            bundle_id="blackfox-handoff-bundle-001",
            packages=(package, package),
        )


def test_blackfox_handoff_fingerprints_are_deterministic() -> None:
    first = ready_package().fingerprint()
    second = ready_package().fingerprint()
    bundle_first = BlackFoxHandoffBundle(
        bundle_id="blackfox-handoff-bundle-001",
        packages=(ready_package(),),
    ).fingerprint()
    bundle_second = BlackFoxHandoffBundle(
        bundle_id="blackfox-handoff-bundle-001",
        packages=(ready_package(),),
    ).fingerprint()

    assert first == second
    assert len(first) == 64
    assert bundle_first == bundle_second
    assert len(bundle_first) == 64
