from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest

from ix_cognition_kernel.wave6_assurance_case_bridge import (
    WaveSixAssuranceBridgeBlocker,
    WaveSixAssuranceBridgeDecision,
    WaveSixAssuranceBridgeStatus,
    WaveSixAssuranceCaseBridgeBundle,
    build_wave_six_assurance_case_bridge_bundle,
)


def _fingerprint(seed: int) -> str:
    return f"{seed:064x}"[-64:]


@dataclass(frozen=True, slots=True)
class _Gate:
    attempt: str = "wave6_measured_cognition"
    human_authority_id: str = "human-reviewer-1"
    independent_reviewer_id: str = "independent-reviewer-1"
    blockers: tuple[Any, ...] = ()
    ready_for_bounded_review_inputs: bool = True
    evidence_ids: tuple[str, ...] = (
        "ix-kernel-handoff:wave6_measured_cognition:kernel-handoff-json",
        "donor-evidence:ix-function:transfer-novelty-record",
    )

    def canonical_payload(self) -> dict[str, Any]:
        return {
            "attempt": self.attempt,
            "blockers": [str(blocker) for blocker in self.blockers],
            "evidence_ids": list(self.evidence_ids),
            "human_authority_id": self.human_authority_id,
            "independent_reviewer_id": self.independent_reviewer_id,
            "ready_for_bounded_review_inputs": self.ready_for_bounded_review_inputs,
        }

    def fingerprint(self) -> str:
        return _fingerprint(111)


@dataclass(frozen=True, slots=True)
class _BlackFoxHandoff:
    blockers: tuple[Any, ...] = ()
    ready_for_blackfox_review_packet: bool = True
    represented_evidence_ids: tuple[str, ...] = (
        "blackfox-ci:pytest",
        "blackfox-ci:ruff",
    )

    def canonical_payload(self) -> dict[str, Any]:
        return {
            "blockers": [str(blocker) for blocker in self.blockers],
            "ready_for_blackfox_review_packet": self.ready_for_blackfox_review_packet,
            "represented_evidence_ids": list(self.represented_evidence_ids),
        }

    def fingerprint(self) -> str:
        return _fingerprint(222)


def test_assurance_bridge_exports_draft_only_for_ready_gate_and_blackfox() -> None:
    bundle = build_wave_six_assurance_case_bridge_bundle(
        case_id="wave6-assurance-draft",
        candidate_gate=_Gate(),
        blackfox_handoff=_BlackFoxHandoff(),
        notes=("Draft assurance export only; not certification.",),
    )

    assert bundle.status is (
        WaveSixAssuranceBridgeStatus.READY_FOR_ASSURANCE_DRAFT_EXPORT
    )
    assert bundle.decision is WaveSixAssuranceBridgeDecision.EXPORT_ASSURANCE_DRAFT_ONLY
    assert bundle.ready_for_assurance_draft_export
    assert bundle.blockers == ()
    assert bundle.metadata_only
    assert bundle.human_review_required
    assert bundle.independent_review_required
    assert not bundle.allows_autonomous_execution
    assert not bundle.claims_agi
    assert not bundle.claims_certified
    assert len(bundle.fingerprint()) == 64
    assert bundle.fingerprint() == bundle.fingerprint()


def test_assurance_bridge_payload_targets_assurance_runtime_vocabulary() -> None:
    bundle = build_wave_six_assurance_case_bridge_bundle(
        case_id="wave6-assurance-draft",
        candidate_gate=_Gate(),
        blackfox_handoff=_BlackFoxHandoff(),
    )

    payload = bundle.canonical_payload()

    assert payload["target_runtime"] == "IX-Autonomy-Assurance-Case-Runtime"
    assert payload["schema_version"] == (
        "ix-cognition-kernel-wave6-assurance-case-bridge-v1"
    )
    assert payload["decision"] == "export-assurance-draft-only"
    assert payload["status"] == "ready-for-assurance-draft-export"
    assert payload["source_candidate_gate_fingerprint"] == _fingerprint(111)
    assert payload["blackfox_handoff_fingerprint"] == _fingerprint(222)
    assert payload["claims_agi"] is False
    assert payload["allows_autonomous_execution"] is False
    assert payload["claims_certified"] is False
    assert payload["self_validated"] is False


def test_assurance_bridge_exports_claims_hazards_controls_and_criteria() -> None:
    bundle = build_wave_six_assurance_case_bridge_bundle(
        case_id="wave6-assurance-draft",
        candidate_gate=_Gate(),
        blackfox_handoff=_BlackFoxHandoff(),
    )

    payload = bundle.canonical_payload()
    claim_ids = tuple(claim["claim_id"] for claim in payload["claims"])
    hazard_ids = tuple(hazard["hazard_id"] for hazard in payload["hazards"])
    control_ids = tuple(control["control_id"] for control in payload["controls"])
    criterion_ids = tuple(
        criterion["criterion_id"] for criterion in payload["verification_criteria"]
    )

    assert claim_ids == (
        "claim-boundary",
        "claim-human-authority",
        "claim-evidence-traceability",
        "claim-blackfox-control",
    )
    assert "hazard-overclaim" in hazard_ids
    assert "hazard-autonomous-execution" in hazard_ids
    assert "control-claim-boundary" in control_ids
    assert "control-no-execution-authority" in control_ids
    assert "criterion-no-agi-claim" in criterion_ids
    assert "criterion-blackfox-no-dispatch" in criterion_ids
    assert all(
        criterion["result"] == "not_run"
        for criterion in bundle.canonical_payload()["verification_criteria"]
    )


def test_assurance_bridge_keeps_gate_and_blackfox_evidence_traceable() -> None:
    bundle = build_wave_six_assurance_case_bridge_bundle(
        case_id="wave6-assurance-draft",
        candidate_gate=_Gate(),
        blackfox_handoff=_BlackFoxHandoff(),
    )

    assert bundle.evidence_ids == (
        "assurance:fingerprint:candidate-gate",
        "ix-kernel-handoff:wave6_measured_cognition:kernel-handoff-json",
        "donor-evidence:ix-function:transfer-novelty-record",
        "assurance:fingerprint:blackfox-handoff",
        "blackfox-ci:pytest",
        "blackfox-ci:ruff",
    )
    evidence = bundle.canonical_payload()["evidence"]

    assert evidence[0]["content_hash"] == _fingerprint(111)
    assert evidence[3]["content_hash"] == _fingerprint(222)
    assert bundle.canonical_payload()["evidence_ids"] == list(bundle.evidence_ids)


def test_assurance_bridge_blocks_candidate_gate_not_ready() -> None:
    bundle = build_wave_six_assurance_case_bridge_bundle(
        case_id="blocked-assurance-draft",
        candidate_gate=_Gate(
            blockers=("ix-obligation-pressure-unresolved",),
            ready_for_bounded_review_inputs=False,
        ),
        blackfox_handoff=_BlackFoxHandoff(),
    )

    assert bundle.status is WaveSixAssuranceBridgeStatus.BLOCKED_BY_CANDIDATE_GATE
    assert bundle.decision is WaveSixAssuranceBridgeDecision.HOLD_FOR_MORE_EVIDENCE
    assert not bundle.ready_for_assurance_draft_export
    assert bundle.blockers == (
        WaveSixAssuranceBridgeBlocker.CANDIDATE_GATE_NOT_READY,
        WaveSixAssuranceBridgeBlocker.CANDIDATE_GATE_HAS_BLOCKERS,
    )


def test_assurance_bridge_blocks_blackfox_handoff_not_ready_after_gate_ready() -> None:
    bundle = build_wave_six_assurance_case_bridge_bundle(
        case_id="blackfox-blocked-assurance-draft",
        candidate_gate=_Gate(),
        blackfox_handoff=_BlackFoxHandoff(
            blockers=("candidate-gate-not-ready",),
            ready_for_blackfox_review_packet=False,
        ),
    )

    assert bundle.status is WaveSixAssuranceBridgeStatus.BLOCKED_BY_BLACKFOX_HANDOFF
    assert bundle.decision is WaveSixAssuranceBridgeDecision.HOLD_FOR_MORE_EVIDENCE
    assert bundle.blockers == (
        WaveSixAssuranceBridgeBlocker.BLACKFOX_HANDOFF_NOT_READY,
        WaveSixAssuranceBridgeBlocker.BLACKFOX_HANDOFF_HAS_BLOCKERS,
    )


def test_assurance_bridge_blocks_missing_review_identities() -> None:
    bundle = build_wave_six_assurance_case_bridge_bundle(
        case_id="missing-reviewers-assurance-draft",
        candidate_gate=_Gate(
            human_authority_id="",
            independent_reviewer_id="",
        ),
        blackfox_handoff=_BlackFoxHandoff(),
    )

    assert bundle.status is WaveSixAssuranceBridgeStatus.BLOCKED_BY_CANDIDATE_GATE
    assert WaveSixAssuranceBridgeBlocker.HUMAN_AUTHORITY_MISSING in bundle.blockers
    assert WaveSixAssuranceBridgeBlocker.INDEPENDENT_REVIEW_MISSING in bundle.blockers


def test_assurance_bridge_rejects_overclaim_or_execution_flags() -> None:
    with pytest.raises(ValueError, match="must not claim AGI"):
        WaveSixAssuranceCaseBridgeBundle(
            case_id="unsafe-assurance-draft",
            candidate_gate=_Gate(),
            blackfox_handoff=_BlackFoxHandoff(),
            claims_agi=True,
        )
    with pytest.raises(ValueError, match="must not grant execution"):
        WaveSixAssuranceCaseBridgeBundle(
            case_id="unsafe-assurance-draft",
            candidate_gate=_Gate(),
            blackfox_handoff=_BlackFoxHandoff(),
            allows_autonomous_execution=True,
        )
    with pytest.raises(ValueError, match="must not certify results"):
        WaveSixAssuranceCaseBridgeBundle(
            case_id="unsafe-assurance-draft",
            candidate_gate=_Gate(),
            blackfox_handoff=_BlackFoxHandoff(),
            claims_certified=True,
        )
