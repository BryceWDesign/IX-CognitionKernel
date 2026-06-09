"""Wave 6 IX obligation evidence and falsification pressure.

Commit 1 made IX-CognitionKernel able to ingest IX's ``kernel-handoff.json``
as bounded contract evidence. This module takes the next step: every imported
IX obligation becomes explicit evidence pressure and falsification pressure.

The output is still metadata-only. It does not execute IX, execute donor repos,
advance maturity, certify the system, or claim AGI. It records what evidence is
missing and what questions must be allowed to falsify the interpretation.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, TypeVar

from ix_cognition_kernel.wave6_falsification import (
    WaveSixFalsificationProbe,
    WaveSixFalsificationProbeKind,
)
from ix_cognition_kernel.wave6_gap_register import (
    WaveSixEvidenceGap,
    WaveSixGapDisposition,
    WaveSixGapKind,
    WaveSixGapSeverity,
    WaveSixGapState,
)
from ix_cognition_kernel.wave6_ix_handoff import (
    WAVE_SIX_IX_HANDOFF_ENGINE_ID,
    WaveSixIxHandoffPackage,
    WaveSixIxObligation,
    canonical_ix_cognition_obligation_ids,
)

T = TypeVar("T")

WAVE_SIX_IX_OBLIGATION_PRESSURE_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave6-ix-obligation-pressure-v1"
)
WAVE_SIX_IX_OBLIGATION_PRESSURE_BUNDLE_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave6-ix-obligation-pressure-bundle-v1"
)
WAVE_SIX_IX_OBLIGATION_PRESSURE_ENGINE_ID = (
    "wave6-ix-obligation-pressure-engine"
)


class WaveSixIxObligationPressureDecision(StrEnum):
    """Fail-closed decision for imported IX obligation pressure."""

    NEEDS_MORE_EVIDENCE = "needs-more-evidence"
    BLOCKED_BY_MISSING_OBLIGATION_EVIDENCE = (
        "blocked-by-missing-obligation-evidence"
    )


class WaveSixIxObligationPressureStatus(StrEnum):
    """Computed status for imported IX obligation pressure."""

    OPEN = "open"
    BLOCKING = "blocking"


_CRITICAL_OBLIGATION_IDS: frozenset[str] = frozenset(
    {
        "claim_boundary_discipline",
        "human_authority",
        "no_self_certification",
        "falsification_ledger",
        "independent_replay_review",
        "kernel_handoff_package",
    }
)

_NEGATIVE_CONTROL_OBLIGATION_IDS: frozenset[str] = frozenset(
    {
        "purpose_discipline",
        "prediction_before_trial",
        "measured_outcome_capture",
        "reality_delta_comparison",
        "evidence_bound_memory_update",
        "long_horizon_planning_trace",
        "uncertainty_assumption_exposure",
    }
)

_REGRESSION_OBLIGATION_IDS: frozenset[str] = frozenset(
    {
        "future_reasoning_change",
        "independent_replay_review",
        "kernel_handoff_package",
    }
)

_SAFETY_GATE_OBLIGATION_IDS: frozenset[str] = frozenset(
    {
        "claim_boundary_discipline",
        "human_authority",
        "safe_refusal_path",
        "self_improvement_airlock",
        "no_self_certification",
        "falsification_ledger",
    }
)

_TRANSFER_OBLIGATION_IDS: frozenset[str] = frozenset(
    {"cross_domain_transfer_probe"}
)

_NOVELTY_OBLIGATION_IDS: frozenset[str] = frozenset(
    {"novelty_generality_pressure"}
)

_CONTRADICTION_OBLIGATION_IDS: frozenset[str] = frozenset(
    {
        "contradiction_handling",
        "shortcut_reward_hacking_detection",
    }
)


@dataclass(frozen=True, slots=True)
class WaveSixIxObligationPressure:
    """Evidence gap and falsification probe derived from one IX obligation."""

    obligation: WaveSixIxObligation
    affected_artifact_id: str
    evidence_gap: WaveSixEvidenceGap
    falsification_probe: WaveSixFalsificationProbe
    decision: WaveSixIxObligationPressureDecision = (
        WaveSixIxObligationPressureDecision.BLOCKED_BY_MISSING_OBLIGATION_EVIDENCE
    )
    schema_version: str = WAVE_SIX_IX_OBLIGATION_PRESSURE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate obligation pressure identity and fail-closed linkage."""

        object.__setattr__(
            self,
            "affected_artifact_id",
            _require_non_empty(self.affected_artifact_id, "affected_artifact_id"),
        )
        object.__setattr__(
            self,
            "schema_version",
            _require_non_empty(self.schema_version, "schema_version"),
        )
        expected_gap_id = _gap_id(self.affected_artifact_id, self.obligation)
        expected_probe_id = _probe_id(self.affected_artifact_id, self.obligation)
        if self.evidence_gap.gap_id != expected_gap_id:
            raise ValueError("IX obligation pressure gap id must be deterministic.")
        if self.falsification_probe.probe_id != expected_probe_id:
            raise ValueError("IX obligation pressure probe id must be deterministic.")
        if self.evidence_gap.required_evidence_ids != self.obligation.evidence_required:
            raise ValueError("IX obligation pressure evidence ids must match IX.")
        if self.evidence_gap.evidence_ids:
            raise ValueError("Imported IX obligation gaps start without evidence.")
        if self.evidence_gap.state is not WaveSixGapState.OPEN:
            raise ValueError("Imported IX obligation gaps must start open.")
        if self.evidence_gap.disposition is not WaveSixGapDisposition.REQUIRE_EVIDENCE:
            raise ValueError("Imported IX obligation gaps must require evidence.")
        if not self.evidence_gap.requires_follow_up:
            raise ValueError("Imported IX obligation gaps must require follow-up.")
        if not self.evidence_gap.blocks_review:
            raise ValueError("Imported IX obligation gaps must block review.")
        if self.falsification_probe.allows_autonomous_execution:
            raise ValueError(
                "IX obligation probes must not allow autonomous execution."
            )
        if self.falsification_probe.claims_agi:
            raise ValueError("IX obligation probes must not claim AGI.")
        if not self.falsification_probe.requires_human_review:
            raise ValueError("IX obligation probes must require human review.")

    @property
    def obligation_id(self) -> str:
        """Return the imported IX obligation id."""

        return self.obligation.obligation_id

    @property
    def required_evidence_ids(self) -> tuple[str, ...]:
        """Return evidence ids required to close this obligation gap."""

        return self.obligation.evidence_required

    @property
    def falsification_gate_ids(self) -> tuple[str, ...]:
        """Return IX falsification gates for this obligation."""

        return self.obligation.falsify_if

    @property
    def status(self) -> WaveSixIxObligationPressureStatus:
        """Return fail-closed status for this obligation pressure."""

        if self.evidence_gap.blocks_bounded_review:
            return WaveSixIxObligationPressureStatus.BLOCKING
        return WaveSixIxObligationPressureStatus.OPEN

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic obligation-pressure payload."""

        return {
            "affected_artifact_id": self.affected_artifact_id,
            "decision": self.decision.value,
            "evidence_gap": self.evidence_gap.canonical_payload(),
            "falsification_gate_ids": list(self.falsification_gate_ids),
            "falsification_probe": self.falsification_probe.canonical_payload(),
            "obligation": self.obligation.canonical_payload(),
            "obligation_id": self.obligation_id,
            "required_evidence_ids": list(self.required_evidence_ids),
            "schema_version": self.schema_version,
            "status": self.status.value,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this pressure record."""

        return _stable_sha256(self.canonical_payload())


@dataclass(frozen=True, slots=True)
class WaveSixIxObligationPressureBundle:
    """Evidence and falsification pressure derived from an IX handoff package."""

    attempt: str
    source_package_fingerprint: str
    source_evidence_id: str
    contract_artifact_id: str
    pressures: tuple[WaveSixIxObligationPressure, ...]
    generated_by_engine_id: str = WAVE_SIX_IX_OBLIGATION_PRESSURE_ENGINE_ID
    decision: WaveSixIxObligationPressureDecision = (
        WaveSixIxObligationPressureDecision.BLOCKED_BY_MISSING_OBLIGATION_EVIDENCE
    )
    schema_version: str = WAVE_SIX_IX_OBLIGATION_PRESSURE_BUNDLE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate complete canonical obligation pressure coverage."""

        object.__setattr__(self, "attempt", _require_non_empty(self.attempt, "attempt"))
        object.__setattr__(
            self,
            "source_package_fingerprint",
            _require_sha256(
                self.source_package_fingerprint,
                "source_package_fingerprint",
            ),
        )
        object.__setattr__(
            self,
            "source_evidence_id",
            _require_non_empty(self.source_evidence_id, "source_evidence_id"),
        )
        object.__setattr__(
            self,
            "contract_artifact_id",
            _require_non_empty(self.contract_artifact_id, "contract_artifact_id"),
        )
        object.__setattr__(
            self,
            "generated_by_engine_id",
            _require_non_empty(
                self.generated_by_engine_id,
                "generated_by_engine_id",
            ),
        )
        object.__setattr__(
            self,
            "schema_version",
            _require_non_empty(self.schema_version, "schema_version"),
        )
        if not self.pressures:
            raise ValueError("IX obligation pressure bundles require pressures.")
        sorted_pressures = _sort_pressures_by_canonical_order(self.pressures)
        object.__setattr__(self, "pressures", sorted_pressures)
        _require_exact_obligation_ids(self.obligation_ids)
        for pressure in self.pressures:
            if pressure.affected_artifact_id != self.contract_artifact_id:
                raise ValueError("IX obligation pressure artifact ids must match.")
        if self.generated_by_engine_id == WAVE_SIX_IX_HANDOFF_ENGINE_ID:
            raise ValueError("Pressure bundle must use its own engine id.")

    @property
    def obligation_ids(self) -> tuple[str, ...]:
        """Return obligation ids in canonical IX cognition order."""

        return tuple(pressure.obligation_id for pressure in self.pressures)

    @property
    def evidence_gap_ids(self) -> tuple[str, ...]:
        """Return generated evidence-gap ids in deterministic order."""

        return tuple(pressure.evidence_gap.gap_id for pressure in self.pressures)

    @property
    def falsification_probe_ids(self) -> tuple[str, ...]:
        """Return generated falsification-probe ids in deterministic order."""

        return tuple(
            pressure.falsification_probe.probe_id for pressure in self.pressures
        )

    @property
    def required_evidence_ids(self) -> tuple[str, ...]:
        """Return unique downstream evidence ids required by IX obligations."""

        return _unique_preserving_order(
            evidence_id
            for pressure in self.pressures
            for evidence_id in pressure.required_evidence_ids
        )

    @property
    def falsification_gate_ids(self) -> tuple[str, ...]:
        """Return unique IX falsification gates in deterministic order."""

        return _unique_preserving_order(
            gate_id
            for pressure in self.pressures
            for gate_id in pressure.falsification_gate_ids
        )

    @property
    def blocking_gap_ids(self) -> tuple[str, ...]:
        """Return generated gap ids that block bounded Wave 6 review."""

        return tuple(
            pressure.evidence_gap.gap_id
            for pressure in self.pressures
            if pressure.evidence_gap.blocks_bounded_review
        )

    @property
    def ready_for_bounded_review(self) -> bool:
        """Return whether imported IX obligations are evidence-satisfied."""

        return not self.blocking_gap_ids

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic bundle payload for review and hashing."""

        return {
            "attempt": self.attempt,
            "blocking_gap_ids": list(self.blocking_gap_ids),
            "contract_artifact_id": self.contract_artifact_id,
            "decision": self.decision.value,
            "evidence_gap_ids": list(self.evidence_gap_ids),
            "falsification_gate_ids": list(self.falsification_gate_ids),
            "falsification_probe_ids": list(self.falsification_probe_ids),
            "generated_by_engine_id": self.generated_by_engine_id,
            "obligation_ids": list(self.obligation_ids),
            "pressures": [pressure.canonical_payload() for pressure in self.pressures],
            "ready_for_bounded_review": self.ready_for_bounded_review,
            "required_evidence_ids": list(self.required_evidence_ids),
            "schema_version": self.schema_version,
            "source_evidence_id": self.source_evidence_id,
            "source_package_fingerprint": self.source_package_fingerprint,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this pressure bundle."""

        return _stable_sha256(self.canonical_payload())


def build_ix_obligation_pressure_bundle(
    package: WaveSixIxHandoffPackage,
) -> WaveSixIxObligationPressureBundle:
    """Build fail-closed evidence and falsification pressure from IX obligations."""

    contract_artifact = package.to_contract_artifact()
    pressures = tuple(
        _build_pressure(
            obligation=obligation,
            contract_artifact_id=contract_artifact.artifact_id,
            source_evidence_id=package.ix_evidence_id,
        )
        for obligation in package.obligations
    )
    return WaveSixIxObligationPressureBundle(
        attempt=package.attempt,
        source_package_fingerprint=package.fingerprint(),
        source_evidence_id=package.ix_evidence_id,
        contract_artifact_id=contract_artifact.artifact_id,
        pressures=pressures,
    )


def _build_pressure(
    *,
    obligation: WaveSixIxObligation,
    contract_artifact_id: str,
    source_evidence_id: str,
) -> WaveSixIxObligationPressure:
    """Build one pressure record from one canonical IX obligation."""

    return WaveSixIxObligationPressure(
        obligation=obligation,
        affected_artifact_id=contract_artifact_id,
        evidence_gap=_build_evidence_gap(
            obligation=obligation,
            contract_artifact_id=contract_artifact_id,
        ),
        falsification_probe=_build_falsification_probe(
            obligation=obligation,
            contract_artifact_id=contract_artifact_id,
            source_evidence_id=source_evidence_id,
        ),
    )


def _build_evidence_gap(
    *,
    obligation: WaveSixIxObligation,
    contract_artifact_id: str,
) -> WaveSixEvidenceGap:
    """Build an open evidence gap for one IX obligation."""

    return WaveSixEvidenceGap(
        gap_id=_gap_id(contract_artifact_id, obligation),
        kind=_gap_kind_for_obligation(obligation.obligation_id),
        severity=_severity_for_obligation(obligation.obligation_id),
        state=WaveSixGapState.OPEN,
        disposition=WaveSixGapDisposition.REQUIRE_EVIDENCE,
        summary=(
            f"IX obligation `{obligation.obligation_id}` is imported but not yet "
            "satisfied by Kernel or donor evidence."
        ),
        affected_artifact_ids=(contract_artifact_id, obligation.obligation_id),
        required_evidence_ids=obligation.evidence_required,
        mitigation_summary=(
            "Provide measured, replayable, human-reviewable evidence for this "
            "IX obligation before treating the Wave 6 package as review-ready."
        ),
        reviewer_question=(
            f"Does the evidence satisfy IX obligation `{obligation.obligation_id}` "
            "without granting execution authority or making an AGI claim?"
        ),
        requires_follow_up=True,
        blocks_review=True,
        claim_boundary_impact=obligation.obligation_id in _CRITICAL_OBLIGATION_IDS,
    )


def _build_falsification_probe(
    *,
    obligation: WaveSixIxObligation,
    contract_artifact_id: str,
    source_evidence_id: str,
) -> WaveSixFalsificationProbe:
    """Build a falsification probe for one IX obligation."""

    return WaveSixFalsificationProbe(
        probe_id=_probe_id(contract_artifact_id, obligation),
        probe_kind=_probe_kind_for_obligation(obligation.obligation_id),
        claim_under_test=(
            f"IX obligation `{obligation.obligation_id}` can be satisfied by "
            "bounded, measured, reviewable Wave 6 evidence."
        ),
        falsification_question=(
            "Would any declared IX falsification gate fire for obligation "
            f"`{obligation.obligation_id}`?"
        ),
        expected_failure_mode="; ".join(obligation.falsify_if),
        method_summary=(
            "Review the imported IX contract evidence and the downstream Kernel "
            "or donor evidence before accepting this obligation as satisfied."
        ),
        evidence_ids=(source_evidence_id,),
    )


def _gap_kind_for_obligation(obligation_id: str) -> WaveSixGapKind:
    """Map one IX obligation to the closest Kernel evidence-gap kind."""

    if obligation_id in {"human_authority", "safe_refusal_path"}:
        return WaveSixGapKind.HUMAN_REVIEW_GAP
    if obligation_id == "claim_boundary_discipline":
        return WaveSixGapKind.CLAIM_BOUNDARY_GAP
    if (
        obligation_id in _TRANSFER_OBLIGATION_IDS
        or obligation_id in _NOVELTY_OBLIGATION_IDS
    ):
        return WaveSixGapKind.TRANSFER_EVIDENCE_GAP
    if obligation_id == "falsification_ledger":
        return WaveSixGapKind.FALSIFICATION_EVIDENCE_GAP
    if obligation_id == "independent_replay_review":
        return WaveSixGapKind.INDEPENDENT_REVIEW_GAP
    return WaveSixGapKind.REQUIRED_EVIDENCE_GAP


def _severity_for_obligation(obligation_id: str) -> WaveSixGapSeverity:
    """Return fail-closed severity for one IX obligation."""

    if obligation_id in _CRITICAL_OBLIGATION_IDS:
        return WaveSixGapSeverity.CRITICAL
    return WaveSixGapSeverity.MAJOR


def _probe_kind_for_obligation(obligation_id: str) -> WaveSixFalsificationProbeKind:
    """Map one IX obligation to a falsification probe family."""

    if obligation_id in _TRANSFER_OBLIGATION_IDS:
        return WaveSixFalsificationProbeKind.TRANSFER_COUNTEREXAMPLE
    if obligation_id in _NOVELTY_OBLIGATION_IDS:
        return WaveSixFalsificationProbeKind.NOVELTY_REVERSAL
    if obligation_id in _CONTRADICTION_OBLIGATION_IDS:
        return WaveSixFalsificationProbeKind.CONTRADICTION_PROBE
    if obligation_id in _SAFETY_GATE_OBLIGATION_IDS:
        return WaveSixFalsificationProbeKind.SAFETY_GATE_PROBE
    if obligation_id in _REGRESSION_OBLIGATION_IDS:
        return WaveSixFalsificationProbeKind.REGRESSION_PROBE
    if obligation_id in _NEGATIVE_CONTROL_OBLIGATION_IDS:
        return WaveSixFalsificationProbeKind.NEGATIVE_CONTROL
    raise ValueError(f"Unmapped IX obligation for falsification: {obligation_id}")


def _gap_id(contract_artifact_id: str, obligation: WaveSixIxObligation) -> str:
    """Return deterministic evidence-gap id for an IX obligation."""

    return f"ix-obligation-gap:{contract_artifact_id}:{obligation.obligation_id}"


def _probe_id(contract_artifact_id: str, obligation: WaveSixIxObligation) -> str:
    """Return deterministic falsification-probe id for an IX obligation."""

    return f"ix-obligation-probe:{contract_artifact_id}:{obligation.obligation_id}"


def _sort_pressures_by_canonical_order(
    pressures: Iterable[WaveSixIxObligationPressure],
) -> tuple[WaveSixIxObligationPressure, ...]:
    """Return pressure records sorted by canonical IX obligation order."""

    by_id: dict[str, WaveSixIxObligationPressure] = {}
    for pressure in pressures:
        if pressure.obligation_id in by_id:
            raise ValueError(
                f"Duplicate IX obligation pressure: {pressure.obligation_id}"
            )
        by_id[pressure.obligation_id] = pressure
    return tuple(
        by_id[obligation_id]
        for obligation_id in canonical_ix_cognition_obligation_ids()
        if obligation_id in by_id
    )


def _require_exact_obligation_ids(obligation_ids: tuple[str, ...]) -> None:
    """Require pressure coverage for every canonical IX cognition obligation."""

    expected = set(canonical_ix_cognition_obligation_ids())
    actual = set(obligation_ids)
    missing = tuple(
        obligation_id
        for obligation_id in canonical_ix_cognition_obligation_ids()
        if obligation_id not in actual
    )
    extra = tuple(sorted(actual - expected))
    if missing:
        raise ValueError(f"Missing IX obligation pressure: {missing[0]}")
    if extra:
        raise ValueError(f"Unknown IX obligation pressure: {extra[0]}")


def _unique_preserving_order(values: Iterable[str]) -> tuple[str, ...]:
    """Return unique text values while preserving first-seen order."""

    seen: set[str] = set()
    unique: list[str] = []
    for value in values:
        if value not in seen:
            unique.append(value)
            seen.add(value)
    return tuple(unique)


def _require_non_empty(value: str, label: str) -> str:
    """Return stripped text or raise when empty."""

    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{label} must not be empty.")
    return normalized


def _require_sha256(value: str, label: str) -> str:
    """Require a deterministic SHA-256 fingerprint value."""

    normalized = _require_non_empty(value, label)
    if len(normalized) != 64:
        raise ValueError(f"{label} must be a SHA-256 fingerprint.")
    try:
        int(normalized, 16)
    except ValueError as exc:
        raise ValueError(f"{label} must be hexadecimal.") from exc
    return normalized


def _stable_sha256(payload: Mapping[str, Any]) -> str:
    """Return deterministic SHA-256 over a canonical JSON payload."""

    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return hashlib.sha256(encoded).hexdigest()
