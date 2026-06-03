import pytest

from ix_cognition_kernel.wave4_audit_trail import (
    REQUIRED_WAVE_FOUR_REPLAY_CHECK_KINDS,
    WaveFourAuditEventKind,
    WaveFourAuditTrailEntry,
    WaveFourAuditTrailOutcome,
    WaveFourAuditTrailStatus,
    WaveFourReplayCheck,
    WaveFourReplayCheckKind,
    WaveFourReproducibleAuditTrail,
    audit_entry,
    passed_replay_check,
)
from ix_cognition_kernel.wave4_contracts import (
    WaveFourArtifactDecision,
    WaveFourArtifactKind,
    WaveFourArtifactRef,
    WaveFourAuthorityState,
    WaveFourCapabilityArea,
    WaveFourSourceSystem,
)
from ix_cognition_kernel.wave4_trials import (
    WaveFourTrialOutcome,
    WaveFourTrialStatus,
    WaveFourTrialTaskKind,
)


ARTIFACT_ID = "artifact:controlled-trial"


def artifact_ref() -> WaveFourArtifactRef:
    return WaveFourArtifactRef(
        artifact_id=ARTIFACT_ID,
        kind=WaveFourArtifactKind.CONTROLLED_TRIAL,
        capability_area=WaveFourCapabilityArea.CROSS_DOMAIN_TRANSFER,
        source_system=WaveFourSourceSystem.IX_COGNITION_KERNEL,
        summary="Controlled trial artifact under audit.",
        produced_by_engine_id="wave4-controlled-trial-engine",
        evidence_ids=("evidence:artifact",),
        decision=WaveFourArtifactDecision.READY_FOR_CONTROLLED_REVIEW,
        authority_state=WaveFourAuthorityState.HUMAN_REVIEW_REQUIRED,
    )


def chained_entries() -> tuple[WaveFourAuditTrailEntry, ...]:
    first = audit_entry(
        entry_id="entry:artifact-created",
        sequence_index=0,
        event_kind=WaveFourAuditEventKind.ARTIFACT_CREATED,
        artifact_id=ARTIFACT_ID,
        event_summary="Artifact was created with evidence attached.",
        payload={"artifact": ARTIFACT_ID, "state": "created"},
        evidence_id="evidence:entry-created",
        previous_digest="GENESIS",
    )
    second = audit_entry(
        entry_id="entry:evidence-linked",
        sequence_index=1,
        event_kind=WaveFourAuditEventKind.EVIDENCE_LINKED,
        artifact_id=ARTIFACT_ID,
        event_summary="Evidence links were replayed.",
        payload={"evidence_ids": ["evidence:artifact"]},
        evidence_id="evidence:entry-linked",
        previous_digest=first.digest,
    )
    third = audit_entry(
        entry_id="entry:human-authority",
        sequence_index=2,
        event_kind=WaveFourAuditEventKind.HUMAN_AUTHORITY_RECORDED,
        artifact_id=ARTIFACT_ID,
        event_summary="Human authority remained required.",
        payload={"authority": "human-review-required"},
        evidence_id="evidence:entry-authority",
        previous_digest=second.digest,
    )
    return (first, second, third)


def replay_checks(final_digest: str) -> tuple[WaveFourReplayCheck, ...]:
    return (
        passed_replay_check(
            check_id="check:digest-chain",
            check_kind=WaveFourReplayCheckKind.DIGEST_CHAIN_RECOMPUTED,
            expected_value=final_digest,
            observed_value=final_digest,
            evidence_id="evidence:check-digest-chain",
        ),
        passed_replay_check(
            check_id="check:artifact-payload",
            check_kind=WaveFourReplayCheckKind.ARTIFACT_PAYLOAD_REPLAYED,
            expected_value=ARTIFACT_ID,
            observed_value=ARTIFACT_ID,
            evidence_id="evidence:check-artifact-payload",
        ),
        passed_replay_check(
            check_id="check:evidence-links",
            check_kind=WaveFourReplayCheckKind.EVIDENCE_LINKS_REPLAYED,
            expected_value="evidence:artifact",
            observed_value="evidence:artifact",
            evidence_id="evidence:check-evidence-links",
        ),
        passed_replay_check(
            check_id="check:decision-state",
            check_kind=WaveFourReplayCheckKind.DECISION_STATE_REPLAYED,
            expected_value="ready-for-controlled-review",
            observed_value="ready-for-controlled-review",
            evidence_id="evidence:check-decision-state",
        ),
        passed_replay_check(
            check_id="check:human-authority",
            check_kind=WaveFourReplayCheckKind.HUMAN_AUTHORITY_REPLAYED,
            expected_value="human-review-required",
            observed_value="human-review-required",
            evidence_id="evidence:check-human-authority",
        ),
    )


def ready_trail() -> WaveFourReproducibleAuditTrail:
    entries = chained_entries()
    return WaveFourReproducibleAuditTrail(
        trail_id="audit-trail-001",
        entries=entries,
        replay_checks=replay_checks(entries[-1].digest),
        artifact_refs=(artifact_ref(),),
        scenario_ids=("worldtwin:audit-replay",),
        blackfox_receipt_ids=("blackfox:audit-replay-receipt",),
    )


def test_required_replay_check_kinds_are_locked() -> None:
    assert REQUIRED_WAVE_FOUR_REPLAY_CHECK_KINDS == (
        WaveFourReplayCheckKind.DIGEST_CHAIN_RECOMPUTED,
        WaveFourReplayCheckKind.ARTIFACT_PAYLOAD_REPLAYED,
        WaveFourReplayCheckKind.EVIDENCE_LINKS_REPLAYED,
        WaveFourReplayCheckKind.DECISION_STATE_REPLAYED,
        WaveFourReplayCheckKind.HUMAN_AUTHORITY_REPLAYED,
    )


def test_audit_entry_requires_payload_evidence_and_valid_sequence() -> None:
    with pytest.raises(ValueError, match="sequence_index must be >= 0"):
        audit_entry(
            entry_id="entry:invalid",
            sequence_index=-1,
            event_kind=WaveFourAuditEventKind.ARTIFACT_CREATED,
            artifact_id=ARTIFACT_ID,
            event_summary="Invalid negative sequence.",
            payload={"state": "invalid"},
            evidence_id="evidence:entry-invalid",
            previous_digest="GENESIS",
        )

    with pytest.raises(ValueError, match="require non-empty payloads"):
        audit_entry(
            entry_id="entry:invalid",
            sequence_index=0,
            event_kind=WaveFourAuditEventKind.ARTIFACT_CREATED,
            artifact_id=ARTIFACT_ID,
            event_summary="Invalid empty payload.",
            payload={},
            evidence_id="evidence:entry-invalid",
            previous_digest="GENESIS",
        )

    with pytest.raises(ValueError, match="must be JSON serializable"):
        WaveFourAuditTrailEntry(
            entry_id="entry:invalid",
            sequence_index=0,
            event_kind=WaveFourAuditEventKind.ARTIFACT_CREATED,
            artifact_id=ARTIFACT_ID,
            event_summary="Invalid non-serializable payload.",
            payload={"bad": {"set-is-not-json"}},
            evidence_ids=("evidence:entry-invalid",),
            previous_digest="GENESIS",
        )


def test_replay_check_requires_evidence_and_failure_text_when_failed() -> None:
    with pytest.raises(ValueError, match="replay checks require evidence ids"):
        WaveFourReplayCheck(
            check_id="check:invalid",
            check_kind=WaveFourReplayCheckKind.DIGEST_CHAIN_RECOMPUTED,
            expected_value="expected",
            observed_value="observed",
            evidence_ids=(),
            passed=True,
        )

    with pytest.raises(ValueError, match="Failed Wave 4 replay checks require"):
        WaveFourReplayCheck(
            check_id="check:invalid-fail",
            check_kind=WaveFourReplayCheckKind.DIGEST_CHAIN_RECOMPUTED,
            expected_value="expected",
            observed_value="observed",
            evidence_ids=("evidence:check-invalid-fail",),
            passed=False,
        )


def test_ready_audit_trail_confirms_replay_without_overclaim() -> None:
    trail = ready_trail()

    assert trail.status is WaveFourAuditTrailStatus.READY_FOR_CONTROLLED_REVIEW
    assert trail.outcome is WaveFourAuditTrailOutcome.REPLAY_CONFIRMED
    assert trail.ready_for_controlled_review is True
    assert trail.chain_gaps == ()
    assert trail.failed_replay_check_ids == ()
    assert trail.missing_required_replay_check_kinds == ()
    assert trail.readiness_gaps == ()
    assert trail.permits_automatic_execution is False
    assert trail.claims_agi is False
    assert trail.independently_validated is False
    assert "no AGI claim" in trail.review_summary


def test_trail_detects_digest_chain_tampering_as_repair_needed() -> None:
    entries = chained_entries()
    tampered = audit_entry(
        entry_id="entry:tampered",
        sequence_index=3,
        event_kind=WaveFourAuditEventKind.REPLAY_CHECK_RECORDED,
        artifact_id=ARTIFACT_ID,
        event_summary="Tampered entry uses wrong previous digest.",
        payload={"tampered": True},
        evidence_id="evidence:entry-tampered",
        previous_digest="not-the-previous-digest",
    )
    trail = WaveFourReproducibleAuditTrail(
        trail_id="audit-trail-tampered",
        entries=(*entries, tampered),
        replay_checks=replay_checks(tampered.digest),
        artifact_refs=(artifact_ref(),),
        scenario_ids=("worldtwin:audit-replay",),
        blackfox_receipt_ids=("blackfox:audit-replay-receipt",),
    )

    assert trail.status is WaveFourAuditTrailStatus.NEEDS_REPAIR
    assert trail.outcome is WaveFourAuditTrailOutcome.TAMPER_DETECTED
    assert len(trail.chain_gaps) == 1
    assert "previous digest mismatch" in trail.chain_gaps[0]


def test_trail_reports_missing_replay_coverage_and_receipts() -> None:
    entries = chained_entries()
    trail = WaveFourReproducibleAuditTrail(
        trail_id="audit-trail-gaps",
        entries=entries,
        replay_checks=(),
        artifact_refs=(artifact_ref(),),
        scenario_ids=(),
        blackfox_receipt_ids=(),
    )

    assert trail.status is WaveFourAuditTrailStatus.NEEDS_EVIDENCE
    assert trail.outcome is WaveFourAuditTrailOutcome.NEEDS_EVIDENCE
    assert "missing replay-check coverage" in trail.readiness_gaps[0]
    assert "audit-trail-gaps has no WorldTwin scenario ids" in trail.readiness_gaps
    assert "audit-trail-gaps has no BlackFox receipt ids" in trail.readiness_gaps


def test_failed_replay_check_detects_tamper_as_repair_needed() -> None:
    entries = chained_entries()
    failed_check = WaveFourReplayCheck(
        check_id="check:digest-failed",
        check_kind=WaveFourReplayCheckKind.DIGEST_CHAIN_RECOMPUTED,
        expected_value=entries[-1].digest,
        observed_value="different-digest",
        evidence_ids=("evidence:check-digest-failed",),
        passed=False,
        failure_summary="digest replay produced a different value",
    )
    trail = WaveFourReproducibleAuditTrail(
        trail_id="audit-trail-failed-check",
        entries=entries,
        replay_checks=(failed_check, *replay_checks(entries[-1].digest)[1:]),
        artifact_refs=(artifact_ref(),),
        scenario_ids=("worldtwin:audit-replay",),
        blackfox_receipt_ids=("blackfox:audit-replay-receipt",),
    )

    assert trail.status is WaveFourAuditTrailStatus.NEEDS_REPAIR
    assert trail.outcome is WaveFourAuditTrailOutcome.TAMPER_DETECTED
    assert trail.failed_replay_check_ids == ("check:digest-failed",)
    assert "digest replay produced" in trail.readiness_gaps[0]


def test_trail_rejects_unknown_artifact_references_and_duplicates() -> None:
    entries = chained_entries()
    with pytest.raises(ValueError, match="must reference artifact refs"):
        WaveFourReproducibleAuditTrail(
            trail_id="audit-trail-unknown-artifact",
            entries=entries,
            replay_checks=replay_checks(entries[-1].digest),
            artifact_refs=(),
            scenario_ids=("worldtwin:audit-replay",),
            blackfox_receipt_ids=("blackfox:audit-replay-receipt"),
        )

    with pytest.raises(ValueError, match="Duplicate entry_id"):
        WaveFourReproducibleAuditTrail(
            trail_id="audit-trail-duplicate",
            entries=(entries[0], entries[0]),
            replay_checks=(),
            artifact_refs=(artifact_ref(),),
            scenario_ids=("worldtwin:audit-replay",),
            blackfox_receipt_ids=("blackfox:audit-replay-receipt",),
        )


def test_blocked_audit_trail_cannot_carry_replay_results() -> None:
    entries = chained_entries()
    with pytest.raises(ValueError, match="cannot carry replay results"):
        WaveFourReproducibleAuditTrail(
            trail_id="audit-trail-blocked-invalid",
            entries=entries,
            replay_checks=replay_checks(entries[-1].digest),
            artifact_refs=(artifact_ref(),),
            scenario_ids=("worldtwin:audit-replay",),
            blackfox_receipt_ids=("blackfox:audit-replay-receipt",),
            blocked_reasons=("audit source evidence was contradicted",),
        )

    trail = WaveFourReproducibleAuditTrail(
        trail_id="audit-trail-blocked",
        entries=entries,
        replay_checks=(),
        artifact_refs=(artifact_ref(),),
        scenario_ids=("worldtwin:audit-replay",),
        blackfox_receipt_ids=("blackfox:audit-replay-receipt",),
        blocked_reasons=("audit source evidence was contradicted",),
    )

    assert trail.status is WaveFourAuditTrailStatus.BLOCKED
    assert trail.outcome is WaveFourAuditTrailOutcome.BLOCKED
    assert trail.blocking_gaps == (
        "audit-trail-blocked blocked: audit source evidence was contradicted",
    )


def test_trail_rejects_execution_agi_and_independent_validation() -> None:
    entries = chained_entries()
    with pytest.raises(ValueError, match="cannot permit execution"):
        WaveFourReproducibleAuditTrail(
            trail_id="invalid-execution",
            entries=entries,
            replay_checks=(),
            artifact_refs=(artifact_ref(),),
            scenario_ids=(),
            blackfox_receipt_ids=(),
            permits_automatic_execution=True,
        )

    with pytest.raises(ValueError, match="cannot claim AGI"):
        WaveFourReproducibleAuditTrail(
            trail_id="invalid-agi",
            entries=entries,
            replay_checks=(),
            artifact_refs=(artifact_ref(),),
            scenario_ids=(),
            blackfox_receipt_ids=(),
            claims_agi=True,
        )

    with pytest.raises(ValueError, match="cannot claim independent validation"):
        WaveFourReproducibleAuditTrail(
            trail_id="invalid-independent-validation",
            entries=entries,
            replay_checks=(),
            artifact_refs=(artifact_ref(),),
            scenario_ids=(),
            blackfox_receipt_ids=(),
            independently_validated=True,
        )


def test_audit_trail_converts_to_shared_artifact_and_bundle() -> None:
    trail = ready_trail()
    artifact = trail.to_artifact_ref()
    bundle = trail.to_artifact_bundle()

    assert artifact.kind is WaveFourArtifactKind.REPRODUCIBLE_AUDIT_TRAIL
    assert artifact.capability_area is WaveFourCapabilityArea.AUDIT_TRAIL
    assert artifact.ready_for_controlled_review is True
    assert artifact.allowed_for_automatic_execution is False
    assert artifact.claims_agi is False
    assert bundle.has_required_kind_coverage is True
    assert bundle.has_required_capability_coverage is True
    assert bundle.ready_for_controlled_review_artifact_ids == (artifact.artifact_id,)


def test_audit_trail_converts_to_controlled_replay_task() -> None:
    task = ready_trail().to_controlled_task()

    assert task.task_kind is WaveFourTrialTaskKind.BASELINE_CAPABILITY
    assert task.outcome is WaveFourTrialOutcome.PASSED
    assert task.status is WaveFourTrialStatus.READY_FOR_CONTROLLED_REVIEW
    assert task.ready_for_controlled_review is True
    assert task.scenario_ids == ("worldtwin:audit-replay",)
    assert task.blackfox_receipt_ids == ("blackfox:audit-replay-receipt",)
    assert len(task.measurements) == 5


def test_failed_audit_trail_converts_to_failed_trial_task() -> None:
    entries = chained_entries()
    failed_check = WaveFourReplayCheck(
        check_id="check:digest-failed",
        check_kind=WaveFourReplayCheckKind.DIGEST_CHAIN_RECOMPUTED,
        expected_value=entries[-1].digest,
        observed_value="different-digest",
        evidence_ids=("evidence:check-digest-failed",),
        passed=False,
        failure_summary="digest replay produced a different value",
    )
    trail = WaveFourReproducibleAuditTrail(
        trail_id="audit-trail-failed-check",
        entries=entries,
        replay_checks=(failed_check, *replay_checks(entries[-1].digest)[1:]),
        artifact_refs=(artifact_ref(),),
        scenario_ids=("worldtwin:audit-replay",),
        blackfox_receipt_ids=("blackfox:audit-replay-receipt",),
    )
    task = trail.to_controlled_task()

    assert task.outcome is WaveFourTrialOutcome.FAILED
    assert task.status is WaveFourTrialStatus.NEEDS_REPAIR
    assert task.failed_measurement_ids == ("audit-replay:check:digest-failed",)


def test_audit_trail_fingerprint_is_deterministic_despite_input_order() -> None:
    first = ready_trail()
    second = WaveFourReproducibleAuditTrail(
        trail_id="audit-trail-001",
        entries=tuple(reversed(first.entries)),
        replay_checks=tuple(reversed(first.replay_checks)),
        artifact_refs=(artifact_ref(),),
        scenario_ids=("worldtwin:audit-replay",),
        blackfox_receipt_ids=("blackfox:audit-replay-receipt",),
    )

    assert first.entry_ids == second.entry_ids
    assert first.fingerprint() == second.fingerprint()
    assert len(first.fingerprint()) == 64
