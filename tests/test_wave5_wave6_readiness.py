import pytest

from ix_cognition_kernel.wave5_contracts import (
    WaveFiveArtifactDecision,
    WaveFiveAuthorityState,
    WaveFiveSourceSystem,
    WaveFiveValidationStatus,
)
from ix_cognition_kernel.wave5_wave6_readiness import (
    WaveFiveWaveSixBlockerKind,
    WaveFiveWaveSixBlockerSeverity,
    WaveFiveWaveSixPreconditionKind,
    WaveFiveWaveSixPreconditionRecord,
    WaveFiveWaveSixPreconditionStatus,
    WaveFiveWaveSixReadinessBlocker,
    WaveFiveWaveSixReadinessGate,
    WaveFiveWaveSixReadinessState,
    blocking_wave_six_precondition_statuses,
    external_wave_six_review_source_systems,
    required_wave_six_preconditions,
    safe_wave_six_precondition_statuses,
)


def _preconditions(
    status: WaveFiveWaveSixPreconditionStatus = (
        WaveFiveWaveSixPreconditionStatus.SATISFIED
    ),
) -> tuple[WaveFiveWaveSixPreconditionRecord, ...]:
    return tuple(
        WaveFiveWaveSixPreconditionRecord(
            precondition_id=f"precondition-{precondition_kind.value}",
            precondition_kind=precondition_kind,
            status=status,
            artifact_ids=(f"artifact-{precondition_kind.value}",),
            evidence_ids=(f"evidence-{precondition_kind.value}",),
            summary=f"Wave 6 precondition for {precondition_kind.value}",
            limitations=(
                (f"limited-{precondition_kind.value}",)
                if status is WaveFiveWaveSixPreconditionStatus.SATISFIED_WITH_LIMITS
                else ()
            ),
            blocker_ids=(
                (f"blocker-{precondition_kind.value}",)
                if status in blocking_wave_six_precondition_statuses()
                else ()
            ),
        )
        for precondition_kind in required_wave_six_preconditions()
    )


def _readiness_gate(
    *,
    readiness_state: WaveFiveWaveSixReadinessState = (
        WaveFiveWaveSixReadinessState.READY_FOR_EXTERNAL_WAVE_SIX_REVIEW
    ),
    source_system: WaveFiveSourceSystem = WaveFiveSourceSystem.IX_COGNITION_KERNEL,
    preconditions: tuple[WaveFiveWaveSixPreconditionRecord, ...] | None = None,
    blockers: tuple[WaveFiveWaveSixReadinessBlocker, ...] = (),
    reviewer_ids: tuple[str, ...] = (),
) -> WaveFiveWaveSixReadinessGate:
    return WaveFiveWaveSixReadinessGate(
        gate_id="wave-six-readiness-gate-1",
        title="Wave 5 to Wave 6 readiness gate",
        source_system=source_system,
        readiness_state=readiness_state,
        preconditions=preconditions or _preconditions(),
        blockers=blockers,
        protocol_ids=("protocol-1",),
        reviewer_ids=reviewer_ids,
    )


def test_required_wave_six_readiness_sets_are_locked() -> None:
    assert len(required_wave_six_preconditions()) >= 10
    assert (
        WaveFiveWaveSixPreconditionKind.EXTERNAL_PROTOCOLS_PREREGISTERED
        in required_wave_six_preconditions()
    )
    assert (
        WaveFiveWaveSixPreconditionStatus.SATISFIED
        in safe_wave_six_precondition_statuses()
    )
    assert (
        WaveFiveWaveSixPreconditionStatus.MISSING
        in blocking_wave_six_precondition_statuses()
    )
    assert (
        WaveFiveSourceSystem.INDEPENDENT_REPLICATION_LAB
        in external_wave_six_review_source_systems()
    )


def test_wave_six_readiness_gate_ready_when_preconditions_are_satisfied() -> None:
    gate = _readiness_gate()

    assert gate.has_required_precondition_coverage
    assert gate.ready_for_external_wave_six_review
    assert not gate.blocks_wave_six_readiness
    assert gate.blocking_precondition_ids == ()
    assert gate.unresolved_blocker_ids == ()
    assert gate.makes_no_forbidden_claims

    artifact_ref = gate.to_artifact_ref()
    assert (
        artifact_ref.decision is WaveFiveArtifactDecision.READY_FOR_INDEPENDENT_REVIEW
    )
    assert artifact_ref.authority_state is WaveFiveAuthorityState.HUMAN_REVIEW_REQUIRED
    assert (
        artifact_ref.validation_status
        is WaveFiveValidationStatus.UNDER_INDEPENDENT_REVIEW
    )
    assert artifact_ref.evidence_ids == gate.all_evidence_ids


def test_wave_six_readiness_gate_reports_missing_precondition() -> None:
    missing_kind = required_wave_six_preconditions()[0]
    preconditions = tuple(
        precondition
        for precondition in _preconditions()
        if precondition.precondition_kind is not missing_kind
    )

    gate = _readiness_gate(preconditions=preconditions)

    assert gate.missing_required_precondition_kinds == (missing_kind,)
    assert gate.blocks_wave_six_readiness
    assert not gate.ready_for_external_wave_six_review


def test_wave_six_readiness_gate_blocks_blocking_precondition() -> None:
    gate = _readiness_gate(
        preconditions=_preconditions(status=WaveFiveWaveSixPreconditionStatus.BLOCKED)
    )

    assert gate.blocking_precondition_ids
    assert gate.blocks_wave_six_readiness
    assert not gate.ready_for_external_wave_six_review

    artifact_ref = gate.to_artifact_ref()
    assert artifact_ref.decision is WaveFiveArtifactDecision.BLOCKED
    assert artifact_ref.authority_state is WaveFiveAuthorityState.BLOCKED
    assert artifact_ref.validation_status is WaveFiveValidationStatus.REJECTED


def test_wave_six_readiness_gate_blocks_unresolved_blocker() -> None:
    blocker = WaveFiveWaveSixReadinessBlocker(
        blocker_id="blocker-1",
        blocker_kind=WaveFiveWaveSixBlockerKind.UNRESOLVED_FALSIFICATION,
        severity=WaveFiveWaveSixBlockerSeverity.BLOCKING,
        precondition_kind=required_wave_six_preconditions()[0],
        description="A falsification blocker remains unresolved.",
        mitigation="Resolve the falsification issue before Wave 6 submission.",
        evidence_ids=("blocker-evidence-1",),
    )

    gate = _readiness_gate(blockers=(blocker,))

    assert gate.unresolved_blocker_ids == ("blocker-1",)
    assert gate.blocks_wave_six_readiness
    assert not gate.ready_for_external_wave_six_review


def test_wave_six_precondition_requires_blocker_ids_for_blocking_status() -> None:
    with pytest.raises(ValueError, match="require blocker ids"):
        WaveFiveWaveSixPreconditionRecord(
            precondition_id="precondition-blocked",
            precondition_kind=WaveFiveWaveSixPreconditionKind.EXTERNAL_REVIEW_GAP
            if hasattr(WaveFiveWaveSixPreconditionKind, "EXTERNAL_REVIEW_GAP")
            else WaveFiveWaveSixPreconditionKind.EXTERNAL_PROTOCOLS_PREREGISTERED,
            status=WaveFiveWaveSixPreconditionStatus.BLOCKED,
            artifact_ids=("artifact-1",),
            evidence_ids=("evidence-1",),
            summary="Blocked precondition without blocker ids.",
        )


def test_wave_six_readiness_gate_rejects_forbidden_claims() -> None:
    with pytest.raises(ValueError, match="cannot claim AGI"):
        WaveFiveWaveSixReadinessGate(
            gate_id="invalid-wave-six-gate",
            title="Invalid Wave 6 gate",
            source_system=WaveFiveSourceSystem.IX_COGNITION_KERNEL,
            readiness_state=WaveFiveWaveSixReadinessState.INTERNAL_GATE_READY,
            preconditions=_preconditions(),
            blockers=(),
            protocol_ids=("protocol-1",),
            claims_agi=True,
        )


def test_externally_reviewed_wave_six_gate_requires_external_source() -> None:
    with pytest.raises(ValueError, match="external source"):
        _readiness_gate(
            readiness_state=(
                WaveFiveWaveSixReadinessState.EXTERNALLY_REVIEWED_WITH_BOUNDARIES
            ),
            source_system=WaveFiveSourceSystem.IX_COGNITION_KERNEL,
            reviewer_ids=("reviewer-1",),
        )


def test_externally_reviewed_wave_six_gate_exports_reviewed_artifact() -> None:
    gate = _readiness_gate(
        readiness_state=WaveFiveWaveSixReadinessState.EXTERNALLY_REVIEWED_WITH_BOUNDARIES,
        source_system=WaveFiveSourceSystem.EXTERNAL_REVIEW,
        reviewer_ids=("reviewer-1",),
    )

    assert gate.externally_reviewed_with_boundaries
    artifact_ref = gate.to_artifact_ref()
    assert artifact_ref.decision is WaveFiveArtifactDecision.EXTERNALLY_REVIEWED
    assert (
        artifact_ref.validation_status
        is WaveFiveValidationStatus.ACCEPTED_WITH_BOUNDARIES
    )
