import pytest

from ix_cognition_kernel.evaluation import (
    AcceptanceCriterion,
    EvaluationLedger,
    EvaluationRecord,
    EvaluationStatus,
)


def satisfied_criterion() -> AcceptanceCriterion:
    return AcceptanceCriterion(
        criterion_id="criterion-001",
        description="The artifact is represented as structured, reviewable state.",
        required=True,
        satisfied=True,
        evidence_ids=("ev-eval-001",),
    )


def optional_unsatisfied_criterion() -> AcceptanceCriterion:
    return AcceptanceCriterion(
        criterion_id="criterion-optional",
        description="Optional future integration is not required for Wave 1.",
        required=False,
        satisfied=False,
        evidence_ids=(),
        reason="The optional criterion is intentionally deferred.",
    )


def passing_record() -> EvaluationRecord:
    return EvaluationRecord(
        evaluation_id="eval-001",
        title="Wave 1 artifact representation review",
        evaluated_artifact_ids=("belief-state", "plan-graph"),
        criteria=(satisfied_criterion(), optional_unsatisfied_criterion()),
        status=EvaluationStatus.PASSED,
        evidence_ids=("ev-eval-001",),
        reasons=("All required criteria are satisfied with evidence.",),
        evaluator_role_id="quality-evaluator",
    )


def test_acceptance_criterion_rejects_unsatisfied_required_without_reason() -> None:
    with pytest.raises(ValueError, match="require a reason"):
        AcceptanceCriterion(
            criterion_id="criterion-no-reason",
            description="Required criteria need a reason when unsatisfied.",
            required=True,
            satisfied=False,
            evidence_ids=(),
        )


def test_satisfied_acceptance_criterion_requires_evidence_ids() -> None:
    with pytest.raises(ValueError, match="require evidence ids"):
        AcceptanceCriterion(
            criterion_id="criterion-no-evidence",
            description="Satisfied criteria need evidence.",
            required=True,
            satisfied=True,
            evidence_ids=(),
        )


def test_acceptance_criterion_reports_when_it_blocks_pass() -> None:
    criterion = AcceptanceCriterion(
        criterion_id="criterion-blocking",
        description="Required criterion is not yet satisfied.",
        required=True,
        satisfied=False,
        evidence_ids=(),
        reason="The required evidence is missing.",
    )

    assert criterion.blocks_pass is True


def test_passing_evaluation_record_exposes_status_and_artifact_coverage() -> None:
    record = passing_record()

    assert record.is_passing is True
    assert record.blocks_progress is False
    assert record.unsatisfied_required_criteria == ()
    assert record.covers_artifact("belief-state") is True
    assert record.covers_artifact("missing-artifact") is False


def test_passing_evaluation_requires_evidence_ids() -> None:
    with pytest.raises(ValueError, match="Passed evaluations require evidence ids"):
        EvaluationRecord(
            evaluation_id="eval-no-evidence",
            title="Invalid passing review",
            evaluated_artifact_ids=("artifact-001",),
            criteria=(satisfied_criterion(),),
            status=EvaluationStatus.PASSED,
            evidence_ids=(),
            reasons=("This should fail because there is no evidence.",),
            evaluator_role_id="quality-evaluator",
        )


def test_passing_evaluation_rejects_unsatisfied_required_criteria() -> None:
    unsatisfied_required = AcceptanceCriterion(
        criterion_id="criterion-unsatisfied",
        description="This required criterion is not satisfied.",
        required=True,
        satisfied=False,
        evidence_ids=(),
        reason="Required evidence is missing.",
    )

    with pytest.raises(ValueError, match="unsatisfied required criteria"):
        EvaluationRecord(
            evaluation_id="eval-invalid-pass",
            title="Invalid passing review",
            evaluated_artifact_ids=("artifact-001",),
            criteria=(unsatisfied_required,),
            status=EvaluationStatus.PASSED,
            evidence_ids=("ev-eval-001",),
            reasons=("This should fail because a required criterion is unmet.",),
            evaluator_role_id="quality-evaluator",
        )


def test_failed_blocked_and_needs_evidence_evaluations_require_reasons() -> None:
    for status in (
        EvaluationStatus.FAILED,
        EvaluationStatus.BLOCKED,
        EvaluationStatus.NEEDS_EVIDENCE,
    ):
        with pytest.raises(ValueError, match="require reasons"):
            EvaluationRecord(
                evaluation_id=f"eval-{status.value}",
                title="Invalid non-passing review",
                evaluated_artifact_ids=("artifact-001",),
                criteria=(satisfied_criterion(),),
                status=status,
                evidence_ids=("ev-eval-001",),
                reasons=(),
                evaluator_role_id="quality-evaluator",
            )


def test_not_run_evaluation_cannot_contain_evidence_or_reasons() -> None:
    with pytest.raises(ValueError, match="not-run evaluations"):
        EvaluationRecord(
            evaluation_id="eval-not-run-invalid",
            title="Invalid not-run review",
            evaluated_artifact_ids=("artifact-001",),
            criteria=(satisfied_criterion(),),
            status=EvaluationStatus.NOT_RUN,
            evidence_ids=("ev-eval-001",),
            reasons=("Not-run records cannot already have reasons.",),
            evaluator_role_id="quality-evaluator",
        )


def test_evaluation_ledger_returns_passing_and_artifact_records() -> None:
    record = passing_record()
    ledger = EvaluationLedger(records=(record,))

    assert ledger.record_by_id("eval-001") == record
    assert ledger.passing_records == (record,)
    assert ledger.blocking_records == ()
    assert ledger.records_for_artifact("plan-graph") == (record,)
    assert ledger.artifact_is_passing("belief-state") is True
    assert ledger.artifact_is_passing("missing-artifact") is False


def test_evaluation_ledger_returns_blocking_and_needs_evidence_records() -> None:
    needs_evidence = EvaluationRecord(
        evaluation_id="eval-needs-evidence",
        title="Evidence gap review",
        evaluated_artifact_ids=("causal-model",),
        criteria=(
            AcceptanceCriterion(
                criterion_id="criterion-missing-evidence",
                description="The artifact needs additional evidence.",
                required=True,
                satisfied=False,
                evidence_ids=(),
                reason="The evidence record has not been provided.",
            ),
        ),
        status=EvaluationStatus.NEEDS_EVIDENCE,
        evidence_ids=(),
        reasons=("The causal model cannot pass without evidence.",),
        evaluator_role_id="quality-evaluator",
    )
    ledger = EvaluationLedger(records=(needs_evidence,))

    assert ledger.passing_records == ()
    assert ledger.blocking_records == (needs_evidence,)
    assert ledger.needs_evidence_records == (needs_evidence,)
    assert ledger.artifact_is_passing("causal-model") is False


def test_evaluation_ledger_rejects_duplicate_evaluation_ids() -> None:
    record = passing_record()

    with pytest.raises(ValueError, match="Duplicate evaluation_id"):
        EvaluationLedger(records=(record, record))


def test_unknown_evaluation_record_lookup_is_rejected() -> None:
    with pytest.raises(ValueError, match="Unknown evaluation_id"):
        EvaluationLedger(records=(passing_record(),)).record_by_id("eval-missing")
