"""Wave 8 integrated bounded trial.

This module wires the first Wave 8 surfaces into one deterministic integrated
trial. It is intentionally bounded: the output is not an AGI claim, not a
certification, and not autonomous authority. It is a replayable construction
showing that environment episodes, transfer pressure, skill synthesis, durable
world-model formation, baseline comparison, replay validation, external review,
and release-manifest gates can be bound together.

Integrated-trial doctrine:

- the trial is bounded and deterministic,
- every run is replayable before promotion,
- transfer evidence precedes skill reuse,
- world rules remain scoped and revisable,
- candidate improvement is compared against model-alone baseline,
- external review readiness is required before release handoff,
- human authority evidence is required before final readiness.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any

from ix_cognition_kernel.wave8_baseline_comparison import (
    BaselineComparisonReport,
    BaselineSystemKind,
    build_baseline_outcome_record,
    compare_baseline_pair,
    evaluate_baseline_comparison,
)
from ix_cognition_kernel.wave8_environment_protocol import EnvironmentActionResult
from ix_cognition_kernel.wave8_episode_runner import BoundedEpisodeRun, run_single_step_episode
from ix_cognition_kernel.wave8_external_review_packet import (
    ExternalReviewPacket,
    ExternalReviewerRole,
    build_external_review_packet,
    default_wave8_review_questions,
)
from ix_cognition_kernel.wave8_model_adapter import (
    DeterministicModelAdapter,
    DeterministicModelPolicy,
)
from ix_cognition_kernel.wave8_release_manifest import (
    Wave8ReleaseManifest,
    build_wave8_release_manifest,
    default_wave8_release_gates,
)
from ix_cognition_kernel.wave8_replay_validator import (
    ReplayValidationReport,
    artifact_from_baseline_report,
    artifact_from_episode_run,
    artifact_from_skill_validation,
    artifact_from_transfer_report,
    artifact_from_world_snapshot,
    validate_replay_packet,
)
from ix_cognition_kernel.wave8_skill_synthesis import (
    SkillLibraryEntry,
    SkillValidationRecord,
    create_skill_library_entry,
    synthesize_skill_candidate,
    validate_skill_candidate,
)
from ix_cognition_kernel.wave8_task_suite import (
    TaskDifficulty,
    TaskDisclosureLevel,
    TaskFamily,
    UnknownTaskInstance,
    UnknownTaskSuite,
    build_grid_transition_task,
    build_grid_transition_template,
    validate_unknown_task_suite,
)
from ix_cognition_kernel.wave8_transfer_challenge import (
    TransferChallengeReport,
    TransferTrialRecord,
    build_transfer_trial_record,
    evaluate_transfer_challenge,
)
from ix_cognition_kernel.wave8_world_model import (
    WorldModelSnapshot,
    build_world_model_snapshot,
    build_world_model_update,
    derive_world_rule_from_trials,
)

WAVE_EIGHT_INTEGRATED_TRIAL_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave8-integrated-trial-v1"
)


@dataclass(frozen=True, slots=True)
class IntegratedWave8TrialResult:
    """End-to-end deterministic Wave 8 bounded trial result."""

    trial_id: str
    suite: UnknownTaskSuite
    task_validation_fingerprint: str
    runs: tuple[BoundedEpisodeRun, ...]
    transfer_report: TransferChallengeReport
    skill_validation: SkillValidationRecord
    skill_entry: SkillLibraryEntry
    world_snapshot: WorldModelSnapshot
    baseline_report: BaselineComparisonReport
    replay_report: ReplayValidationReport
    external_review_packet: ExternalReviewPacket
    release_manifest: Wave8ReleaseManifest
    schema_version: str = WAVE_EIGHT_INTEGRATED_TRIAL_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate integrated trial coverage and readiness chain."""

        object.__setattr__(
            self,
            "trial_id",
            _require_non_empty(self.trial_id, "trial_id"),
        )
        object.__setattr__(
            self,
            "task_validation_fingerprint",
            _require_sha256(
                self.task_validation_fingerprint,
                "task_validation_fingerprint",
            ),
        )
        object.__setattr__(
            self,
            "runs",
            tuple(self.runs),
        )
        object.__setattr__(
            self,
            "schema_version",
            _require_non_empty(self.schema_version, "schema_version"),
        )
        if not self.runs:
            raise ValueError("Integrated Wave 8 trials require episode runs.")
        suite_task_ids = {task.task_id for task in self.suite.tasks}
        run_episode_ids = {run.episode_id for run in self.runs}
        suite_episode_ids = {task.initial_observation.episode_id for task in self.suite.tasks}
        if not suite_episode_ids.issubset(run_episode_ids):
            raise ValueError("Integrated Wave 8 trial runs must cover every suite task.")
        transfer_trial_task_ids = {
            trial.task.task_id for trial in self.transfer_report.trials
        }
        if transfer_trial_task_ids != suite_task_ids:
            raise ValueError("Transfer report must cover every suite task.")
        if not self.transfer_report.ready:
            raise ValueError("Integrated trial requires transfer-demonstrated report.")
        if not self.skill_validation.ready:
            raise ValueError("Integrated trial requires reusable skill validation.")
        if not self.skill_entry.reusable:
            raise ValueError("Integrated trial requires reusable skill entry.")
        if not self.world_snapshot.active_rules:
            raise ValueError("Integrated trial requires active world-model rules.")
        if not self.baseline_report.ready:
            raise ValueError("Integrated trial requires demonstrated baseline improvement.")
        if not self.replay_report.ready:
            raise ValueError("Integrated trial requires ready replay report.")
        if not self.external_review_packet.ready:
            raise ValueError("Integrated trial requires ready external review packet.")
        if not self.release_manifest.ready:
            raise ValueError("Integrated trial requires ready release manifest.")

    @property
    def ready(self) -> bool:
        """Return whether the integrated chain is ready for review handoff."""

        return (
            self.transfer_report.ready
            and self.skill_validation.ready
            and self.skill_entry.reusable
            and self.baseline_report.ready
            and self.replay_report.ready
            and self.external_review_packet.ready
            and self.release_manifest.ready
        )

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic integrated trial payload."""

        return {
            "baseline_report_fingerprint": self.baseline_report.fingerprint(),
            "external_review_packet_fingerprint": self.external_review_packet.fingerprint(),
            "release_manifest_fingerprint": self.release_manifest.fingerprint(),
            "replay_report_fingerprint": self.replay_report.fingerprint(),
            "run_fingerprints": [run.fingerprint() for run in self.runs],
            "schema_version": self.schema_version,
            "skill_entry_fingerprint": self.skill_entry.fingerprint(),
            "skill_validation_fingerprint": self.skill_validation.fingerprint(),
            "suite_fingerprint": self.suite.fingerprint(),
            "task_validation_fingerprint": self.task_validation_fingerprint,
            "transfer_report_fingerprint": self.transfer_report.fingerprint(),
            "trial_id": self.trial_id,
            "world_snapshot_fingerprint": self.world_snapshot.fingerprint(),
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this integrated trial."""

        return _stable_sha256(self.canonical_payload())


def build_integrated_wave8_trial(
    *,
    trial_id: str,
    human_authority_evidence_ids: Iterable[str],
) -> IntegratedWave8TrialResult:
    """Build a deterministic end-to-end Wave 8 bounded trial."""

    normalized_trial_id = _require_non_empty(trial_id, "trial_id")
    tasks = _build_tasks(normalized_trial_id)
    suite = UnknownTaskSuite(
        suite_id=f"{normalized_trial_id}:suite",
        purpose=(
            "Exercise bounded episode execution, transfer, skill synthesis, "
            "world-model formation, baseline comparison, replay, and review handoff."
        ),
        tasks=tasks,
        evidence_ids=(f"{normalized_trial_id}:suite-evidence",),
    )
    task_validation = validate_unknown_task_suite(
        report_id=f"{normalized_trial_id}:task-suite-validation",
        suite=suite,
    )
    if not task_validation.ready:
        raise ValueError("Integrated Wave 8 trial requires a ready task suite.")

    runs = tuple(_run_candidate_task(task=task) for task in suite.tasks)
    trials = tuple(
        build_transfer_trial_record(
            trial_id=f"{task.task_id}:transfer-trial",
            task=task,
            run=run,
            observed_feature_ids=task.expected_outcome_features,
            evidence_ids=(f"{task.task_id}:transfer-evidence",),
        )
        for task, run in zip(suite.tasks, runs, strict=True)
    )
    transfer_report = evaluate_transfer_challenge(
        report_id=f"{normalized_trial_id}:transfer-report",
        suite=suite,
        trials=trials,
    )
    skill_validation, skill_entry = _build_skill_chain(
        trial_id=normalized_trial_id,
        trials=trials,
        transfer_report=transfer_report,
    )
    world_snapshot = _build_world_snapshot(
        trial_id=normalized_trial_id,
        trials=trials,
    )
    baseline_report = _build_baseline_report(
        trial_id=normalized_trial_id,
        tasks=suite.tasks,
    )
    replay_report = _build_replay_report(
        trial_id=normalized_trial_id,
        representative_run=runs[0],
        transfer_report=transfer_report,
        skill_validation=skill_validation,
        world_snapshot=world_snapshot,
        baseline_report=baseline_report,
    )
    external_review_packet = _build_external_review_packet(
        trial_id=normalized_trial_id,
        replay_report=replay_report,
    )
    release_manifest = _build_release_manifest(
        trial_id=normalized_trial_id,
        external_review_packet=external_review_packet,
        human_authority_evidence_ids=tuple(human_authority_evidence_ids),
    )

    return IntegratedWave8TrialResult(
        trial_id=normalized_trial_id,
        suite=suite,
        task_validation_fingerprint=task_validation.fingerprint(),
        runs=runs,
        transfer_report=transfer_report,
        skill_validation=skill_validation,
        skill_entry=skill_entry,
        world_snapshot=world_snapshot,
        baseline_report=baseline_report,
        replay_report=replay_report,
        external_review_packet=external_review_packet,
        release_manifest=release_manifest,
    )


def _build_tasks(trial_id: str) -> tuple[UnknownTaskInstance, ...]:
    template = build_grid_transition_template(template_id=f"{trial_id}:grid-template")
    task_specs = (
        ("seed", TaskDifficulty.SEED, TaskDisclosureLevel.PARTIALLY_WITHHELD),
        ("near", TaskDifficulty.NEAR_TRANSFER, TaskDisclosureLevel.PARTIALLY_WITHHELD),
        ("far", TaskDifficulty.FAR_TRANSFER, TaskDisclosureLevel.PARTIALLY_WITHHELD),
        ("adversarial", TaskDifficulty.ADVERSARIAL, TaskDisclosureLevel.PARTIALLY_WITHHELD),
        ("hidden", TaskDifficulty.HIDDEN_VALIDATION, TaskDisclosureLevel.HIDDEN_GOAL),
    )
    return tuple(
        build_grid_transition_task(
            task_id=f"{trial_id}:task-{name}",
            template=template,
            episode_id=f"{trial_id}:episode-{name}",
            start_state_id=f"{trial_id}:state-{name}-0",
            empty_direction="east",
            expected_operation_id="move-east",
            difficulty=difficulty,
            disclosure_level=disclosure,
        )
        for name, difficulty, disclosure in task_specs
    )


def _adapter(*, adapter_id: str, operation_id: str) -> DeterministicModelAdapter:
    return DeterministicModelAdapter(
        adapter_id=adapter_id,
        policy=DeterministicModelPolicy(
            policy_id=f"{adapter_id}:policy",
            supported_environment_ids=("bounded-grid-transition",),
            operation_preferences=(operation_id,),
            rationale_template="Use {operation_id} from {state_id}.",
            expected_effect_template="{operation_id} should change the bounded state.",
            evidence_ids=(f"{adapter_id}:policy-evidence",),
            assumptions=("visible-state-is-current",),
            uncertainty_ids=("uncertainty-grid-transition",),
        ),
    )


def _result_for_task(
    *,
    task: UnknownTaskInstance,
    action_id: str,
    measured: bool = True,
) -> EnvironmentActionResult:
    return EnvironmentActionResult(
        result_id=f"{task.task_id}:result:{action_id}",
        action_id=action_id,
        environment_id=task.environment.environment_id,
        episode_id=task.initial_observation.episode_id,
        prior_state_id=task.initial_observation.state_id,
        resulting_state_id=f"{task.task_id}:state-result",
        outcome_summary="The bounded task produced a measured grid transition.",
        score_delta=1.0,
        evidence_ids=(f"{task.task_id}:result-evidence:{action_id}",),
        measured=measured,
        terminal=True,
    )


def _run_candidate_task(task: UnknownTaskInstance) -> BoundedEpisodeRun:
    action_id = f"{task.task_id}:candidate-action"
    return run_single_step_episode(
        run_id=f"{task.task_id}:candidate-run",
        step_id=f"{task.task_id}:candidate-step",
        output_id=f"{task.task_id}:candidate-output",
        draft_id=f"{task.task_id}:candidate-draft",
        action_id=action_id,
        frame_id=f"{task.task_id}:candidate-frame",
        environment=task.environment,
        observation=task.initial_observation,
        adapter=_adapter(adapter_id=f"{task.task_id}:candidate-adapter", operation_id="move-east"),
        result=_result_for_task(task=task, action_id=action_id),
    )


def _run_baseline_task(task: UnknownTaskInstance) -> BoundedEpisodeRun:
    action_id = f"{task.task_id}:baseline-action"
    return run_single_step_episode(
        run_id=f"{task.task_id}:baseline-run",
        step_id=f"{task.task_id}:baseline-step",
        output_id=f"{task.task_id}:baseline-output",
        draft_id=f"{task.task_id}:baseline-draft",
        action_id=action_id,
        frame_id=f"{task.task_id}:baseline-frame",
        environment=task.environment,
        observation=task.initial_observation,
        adapter=_adapter(adapter_id=f"{task.task_id}:baseline-adapter", operation_id="move-east"),
        result=_result_for_task(task=task, action_id=action_id),
    )


def _build_skill_chain(
    *,
    trial_id: str,
    trials: tuple[TransferTrialRecord, ...],
    transfer_report: TransferChallengeReport,
) -> tuple[SkillValidationRecord, SkillLibraryEntry]:
    candidate = synthesize_skill_candidate(
        skill_id=f"{trial_id}:skill-grid-transition",
        name="Bounded grid transition skill",
        purpose="Reuse measured grid-transition evidence under bounded constraints.",
        trials=trials,
        evidence_ids=(f"{trial_id}:skill-synthesis-evidence",),
    )
    validation = validate_skill_candidate(
        validation_id=f"{trial_id}:skill-validation",
        candidate=candidate,
        transfer_report=transfer_report,
    )
    entry = create_skill_library_entry(
        entry_id=f"{trial_id}:skill-entry",
        validation=validation,
        evidence_ids=(f"{trial_id}:skill-entry-evidence",),
    )
    return validation, entry


def _build_world_snapshot(
    *,
    trial_id: str,
    trials: tuple[TransferTrialRecord, ...],
) -> WorldModelSnapshot:
    rule = derive_world_rule_from_trials(
        rule_id=f"{trial_id}:world-rule-grid-transition",
        statement="Visible east-empty grid states support a bounded move-east transition.",
        family=TaskFamily.GRID_ABSTRACTION,
        trials=trials,
        evidence_ids=(f"{trial_id}:world-rule-evidence",),
    )
    update = build_world_model_update(
        update_id=f"{trial_id}:world-update",
        rule=rule,
        trials=trials,
    )
    return build_world_model_snapshot(
        snapshot_id=f"{trial_id}:world-snapshot",
        purpose="Store bounded grid transition rules for replay review.",
        updates=(update,),
        evidence_ids=(f"{trial_id}:world-snapshot-evidence",),
    )


def _build_baseline_report(
    *,
    trial_id: str,
    tasks: tuple[UnknownTaskInstance, ...],
) -> BaselineComparisonReport:
    comparison_tasks = tasks[1:3]
    pairs = []
    for index, task in enumerate(comparison_tasks, start=1):
        baseline = build_baseline_outcome_record(
            outcome_id=f"{trial_id}:baseline-outcome-{index}",
            system_kind=BaselineSystemKind.MODEL_ALONE,
            task=task,
            run=_run_baseline_task(task),
            observed_feature_ids=("model-alone-missed-expected-operation",),
            evidence_ids=(f"{trial_id}:baseline-outcome-evidence-{index}",),
        )
        candidate = build_baseline_outcome_record(
            outcome_id=f"{trial_id}:candidate-outcome-{index}",
            system_kind=BaselineSystemKind.COGNITION_KERNEL,
            task=task,
            run=_run_candidate_task(task),
            observed_feature_ids=task.expected_outcome_features,
            evidence_ids=(f"{trial_id}:candidate-outcome-evidence-{index}",),
        )
        pairs.append(
            compare_baseline_pair(
                pair_id=f"{trial_id}:baseline-pair-{index}",
                baseline=baseline,
                candidate=candidate,
            )
        )
    return evaluate_baseline_comparison(
        report_id=f"{trial_id}:baseline-report",
        purpose="Compare kernel-assisted outcomes against model-alone outcomes.",
        pairs=tuple(pairs),
    )


def _build_replay_report(
    *,
    trial_id: str,
    representative_run: BoundedEpisodeRun,
    transfer_report: TransferChallengeReport,
    skill_validation: SkillValidationRecord,
    world_snapshot: WorldModelSnapshot,
    baseline_report: BaselineComparisonReport,
) -> ReplayValidationReport:
    artifacts = (
        artifact_from_episode_run(
            artifact_id=f"{trial_id}:artifact-episode",
            run=representative_run,
            evidence_ids=(f"{trial_id}:artifact-episode-evidence",),
        ),
        artifact_from_transfer_report(
            artifact_id=f"{trial_id}:artifact-transfer",
            report=transfer_report,
            evidence_ids=(f"{trial_id}:artifact-transfer-evidence",),
        ),
        artifact_from_skill_validation(
            artifact_id=f"{trial_id}:artifact-skill",
            validation=skill_validation,
            evidence_ids=(f"{trial_id}:artifact-skill-evidence",),
        ),
        artifact_from_world_snapshot(
            artifact_id=f"{trial_id}:artifact-world",
            snapshot=world_snapshot,
            evidence_ids=(f"{trial_id}:artifact-world-evidence",),
        ),
        artifact_from_baseline_report(
            artifact_id=f"{trial_id}:artifact-baseline",
            report=baseline_report,
            evidence_ids=(f"{trial_id}:artifact-baseline-evidence",),
        ),
    )
    return validate_replay_packet(
        report_id=f"{trial_id}:replay-report",
        purpose="Validate bounded Wave 8 replay packet for human review.",
        artifacts=artifacts,
    )


def _build_external_review_packet(
    *,
    trial_id: str,
    replay_report: ReplayValidationReport,
) -> ExternalReviewPacket:
    return build_external_review_packet(
        packet_id=f"{trial_id}:external-review-packet",
        purpose="Package bounded recursive learning evidence for external review.",
        claim_boundary="Bounded recursive learning evidence only; no certification.",
        replay_report=replay_report,
        reviewer_roles=(
            ExternalReviewerRole.HUMAN_AUTHORITY,
            ExternalReviewerRole.INDEPENDENT_REPLAYER,
            ExternalReviewerRole.SAFETY_REVIEWER,
            ExternalReviewerRole.BASELINE_REVIEWER,
            ExternalReviewerRole.TRANSFER_REVIEWER,
        ),
        questions=default_wave8_review_questions(evidence_prefix=f"{trial_id}:review"),
        evidence_ids=(f"{trial_id}:external-review-evidence",),
    )


def _build_release_manifest(
    *,
    trial_id: str,
    external_review_packet: ExternalReviewPacket,
    human_authority_evidence_ids: tuple[str, ...],
) -> Wave8ReleaseManifest:
    gates = default_wave8_release_gates(
        external_review_packet=external_review_packet,
        human_authority_evidence_ids=human_authority_evidence_ids,
        evidence_prefix=f"{trial_id}:release",
    )
    return build_wave8_release_manifest(
        manifest_id=f"{trial_id}:release-manifest",
        wave_name="Wave 8 Recursive Reality-Corrected Learner",
        purpose="Bind bounded recursive learning evidence for review handoff.",
        claim_boundary="Review handoff only; no certification.",
        external_review_packet=external_review_packet,
        gates=gates,
        evidence_ids=(f"{trial_id}:release-manifest-evidence",),
    )


def _require_non_empty(value: str, label: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{label} must not be empty.")
    return normalized


def _require_sha256(value: str, label: str) -> str:
    normalized = _require_non_empty(value, label)
    if len(normalized) != 64:
        raise ValueError(f"{label} must be a SHA-256 hex digest.")
    try:
        int(normalized, 16)
    except ValueError as exc:
        raise ValueError(f"{label} must be a SHA-256 hex digest.") from exc
    return normalized


def _stable_sha256(payload: Mapping[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
