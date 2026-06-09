"""Wave 6 assurance-case bridge export.

IX-Autonomy-Assurance-Case-Runtime should receive reviewable claim, hazard,
control, criterion, and evidence metadata from IX-CognitionKernel. The Kernel
must not certify the result, import the assurance runtime as a dependency, or
turn bounded review evidence into an AGI claim.

This bridge exports a deterministic assurance-style draft payload from a
fail-closed candidate gate and an optional BlackFox execution-review handoff. It
is metadata-only: unresolved blockers remain visible, verification criteria
start as not-run, and no autonomous execution authority is created.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Protocol

WAVE_SIX_ASSURANCE_BRIDGE_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave6-assurance-case-bridge-v1"
)
WAVE_SIX_ASSURANCE_BRIDGE_ENGINE_ID = "wave6-assurance-case-bridge-engine"
WAVE_SIX_ASSURANCE_TARGET_RUNTIME = "IX-Autonomy-Assurance-Case-Runtime"


class AssuranceGateLike(Protocol):
    """Structural candidate-gate surface used by the assurance bridge."""

    @property
    def attempt(self) -> str:
        """Return the gated candidate attempt id."""

    @property
    def human_authority_id(self) -> str:
        """Return the human authority id carried by the gate."""

    @property
    def independent_reviewer_id(self) -> str:
        """Return the independent reviewer id carried by the gate."""

    @property
    def blockers(self) -> tuple[Any, ...]:
        """Return fail-closed gate blockers."""

    @property
    def ready_for_bounded_review_inputs(self) -> bool:
        """Return whether bounded review-input staging is allowed."""

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic gate payload."""

    def fingerprint(self) -> str:
        """Return deterministic gate fingerprint."""


class BlackFoxHandoffLike(Protocol):
    """Structural BlackFox handoff surface used by the assurance bridge."""

    @property
    def blockers(self) -> tuple[Any, ...]:
        """Return BlackFox handoff blockers."""

    @property
    def ready_for_blackfox_review_packet(self) -> bool:
        """Return whether BlackFox review-packet staging is allowed."""

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic BlackFox handoff payload."""

    def fingerprint(self) -> str:
        """Return deterministic BlackFox handoff fingerprint."""


class WaveSixAssuranceBridgeStatus(StrEnum):
    """Status for an assurance-case bridge export."""

    BLOCKED_BY_CANDIDATE_GATE = "blocked-by-candidate-gate"
    BLOCKED_BY_BLACKFOX_HANDOFF = "blocked-by-blackfox-handoff"
    READY_FOR_ASSURANCE_DRAFT_EXPORT = "ready-for-assurance-draft-export"


class WaveSixAssuranceBridgeDecision(StrEnum):
    """Decision emitted by an assurance-case bridge export."""

    HOLD_FOR_MORE_EVIDENCE = "hold-for-more-evidence"
    EXPORT_ASSURANCE_DRAFT_ONLY = "export-assurance-draft-only"


class WaveSixAssuranceBridgeBlocker(StrEnum):
    """Reasons an assurance draft export is still blocked."""

    CANDIDATE_GATE_NOT_READY = "candidate-gate-not-ready"
    CANDIDATE_GATE_HAS_BLOCKERS = "candidate-gate-has-blockers"
    BLACKFOX_HANDOFF_NOT_READY = "blackfox-handoff-not-ready"
    BLACKFOX_HANDOFF_HAS_BLOCKERS = "blackfox-handoff-has-blockers"
    HUMAN_AUTHORITY_MISSING = "human-authority-missing"
    INDEPENDENT_REVIEW_MISSING = "independent-review-missing"
    EVIDENCE_PACKAGE_EMPTY = "evidence-package-empty"


@dataclass(frozen=True, slots=True)
class WaveSixAssuranceCaseBridgeBundle:
    """Metadata-only assurance draft export from Wave 6 review surfaces."""

    case_id: str
    candidate_gate: AssuranceGateLike
    blackfox_handoff: BlackFoxHandoffLike | None = None
    generated_by_engine_id: str = WAVE_SIX_ASSURANCE_BRIDGE_ENGINE_ID
    metadata_only: bool = True
    human_review_required: bool = True
    independent_review_required: bool = True
    allows_autonomous_execution: bool = False
    claims_agi: bool = False
    claims_production_ready: bool = False
    claims_certified: bool = False
    self_validated: bool = False
    notes: tuple[str, ...] = ()
    schema_version: str = WAVE_SIX_ASSURANCE_BRIDGE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate assurance export safety boundaries."""

        object.__setattr__(self, "case_id", _require_non_empty(self.case_id, "case_id"))
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
            "notes",
            _normalize_unique_text_tuple(self.notes, label="bridge note"),
        )
        object.__setattr__(
            self,
            "schema_version",
            _require_non_empty(self.schema_version, "schema_version"),
        )
        if not self.metadata_only:
            raise ValueError("Assurance bridge exports must be metadata-only.")
        if not self.human_review_required:
            raise ValueError("Assurance bridge exports require human review.")
        if not self.independent_review_required:
            raise ValueError("Assurance bridge exports require independent review.")
        if self.allows_autonomous_execution:
            raise ValueError("Assurance bridge exports must not grant execution.")
        if self.claims_agi:
            raise ValueError("Assurance bridge exports must not claim AGI.")
        if self.claims_production_ready:
            raise ValueError("Assurance bridge exports must not claim production.")
        if self.claims_certified:
            raise ValueError("Assurance bridge exports must not certify results.")
        if self.self_validated:
            raise ValueError("Assurance bridge exports must not self-validate.")

    @property
    def attempt(self) -> str:
        """Return the candidate attempt id represented by this export."""

        return _require_non_empty(self.candidate_gate.attempt, "attempt")

    @property
    def gate_payload(self) -> Mapping[str, Any]:
        """Return the canonical candidate-gate payload."""

        return self.candidate_gate.canonical_payload()

    @property
    def blackfox_payload(self) -> Mapping[str, Any]:
        """Return the canonical BlackFox handoff payload when present."""

        if self.blackfox_handoff is None:
            return {}
        return self.blackfox_handoff.canonical_payload()

    @property
    def gate_evidence_ids(self) -> tuple[str, ...]:
        """Return evidence ids represented by the candidate gate."""

        return _payload_text_sequence(self.gate_payload, "evidence_ids")

    @property
    def blackfox_evidence_ids(self) -> tuple[str, ...]:
        """Return evidence ids represented by the BlackFox handoff."""

        if self.blackfox_handoff is None:
            return ()
        return _payload_text_sequence(self.blackfox_payload, "represented_evidence_ids")

    @property
    def evidence_ids(self) -> tuple[str, ...]:
        """Return unique evidence ids represented by the assurance export."""

        blackfox_fingerprint_ids = (
            ("assurance:fingerprint:blackfox-handoff",)
            if self.blackfox_handoff is not None
            else ()
        )
        return _unique_preserving_order(
            (
                "assurance:fingerprint:candidate-gate",
                *self.gate_evidence_ids,
                *blackfox_fingerprint_ids,
                *self.blackfox_evidence_ids,
            )
        )

    @property
    def blockers(self) -> tuple[WaveSixAssuranceBridgeBlocker, ...]:
        """Return fail-closed blockers for assurance export readiness."""

        blockers: list[WaveSixAssuranceBridgeBlocker] = []
        if not self.candidate_gate.ready_for_bounded_review_inputs:
            blockers.append(WaveSixAssuranceBridgeBlocker.CANDIDATE_GATE_NOT_READY)
        if self.candidate_gate.blockers:
            blockers.append(WaveSixAssuranceBridgeBlocker.CANDIDATE_GATE_HAS_BLOCKERS)
        if self.blackfox_handoff is not None:
            if not self.blackfox_handoff.ready_for_blackfox_review_packet:
                blockers.append(
                    WaveSixAssuranceBridgeBlocker.BLACKFOX_HANDOFF_NOT_READY
                )
            if self.blackfox_handoff.blockers:
                blockers.append(
                    WaveSixAssuranceBridgeBlocker.BLACKFOX_HANDOFF_HAS_BLOCKERS
                )
        if not self.candidate_gate.human_authority_id.strip():
            blockers.append(WaveSixAssuranceBridgeBlocker.HUMAN_AUTHORITY_MISSING)
        if not self.candidate_gate.independent_reviewer_id.strip():
            blockers.append(WaveSixAssuranceBridgeBlocker.INDEPENDENT_REVIEW_MISSING)
        if not self.evidence_ids:
            blockers.append(WaveSixAssuranceBridgeBlocker.EVIDENCE_PACKAGE_EMPTY)
        return tuple(blockers)

    @property
    def status(self) -> WaveSixAssuranceBridgeStatus:
        """Return fail-closed assurance bridge status."""

        if (
            WaveSixAssuranceBridgeBlocker.CANDIDATE_GATE_NOT_READY in self.blockers
            or WaveSixAssuranceBridgeBlocker.CANDIDATE_GATE_HAS_BLOCKERS
            in self.blockers
            or WaveSixAssuranceBridgeBlocker.HUMAN_AUTHORITY_MISSING in self.blockers
            or WaveSixAssuranceBridgeBlocker.INDEPENDENT_REVIEW_MISSING in self.blockers
        ):
            return WaveSixAssuranceBridgeStatus.BLOCKED_BY_CANDIDATE_GATE
        if (
            WaveSixAssuranceBridgeBlocker.BLACKFOX_HANDOFF_NOT_READY in self.blockers
            or WaveSixAssuranceBridgeBlocker.BLACKFOX_HANDOFF_HAS_BLOCKERS
            in self.blockers
        ):
            return WaveSixAssuranceBridgeStatus.BLOCKED_BY_BLACKFOX_HANDOFF
        return WaveSixAssuranceBridgeStatus.READY_FOR_ASSURANCE_DRAFT_EXPORT

    @property
    def decision(self) -> WaveSixAssuranceBridgeDecision:
        """Return assurance bridge decision."""

        if self.status is WaveSixAssuranceBridgeStatus.READY_FOR_ASSURANCE_DRAFT_EXPORT:
            return WaveSixAssuranceBridgeDecision.EXPORT_ASSURANCE_DRAFT_ONLY
        return WaveSixAssuranceBridgeDecision.HOLD_FOR_MORE_EVIDENCE

    @property
    def ready_for_assurance_draft_export(self) -> bool:
        """Return whether this payload may be exported as a draft only."""

        return (
            self.status
            is WaveSixAssuranceBridgeStatus.READY_FOR_ASSURANCE_DRAFT_EXPORT
        )

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic assurance-case bridge payload."""

        return {
            "allows_autonomous_execution": self.allows_autonomous_execution,
            "attempt": self.attempt,
            "blackfox_handoff_fingerprint": self._blackfox_fingerprint_or_none(),
            "blockers": [blocker.value for blocker in self.blockers],
            "case_id": self.case_id,
            "claims": self._claim_payloads(),
            "claims_agi": self.claims_agi,
            "claims_certified": self.claims_certified,
            "claims_production_ready": self.claims_production_ready,
            "controls": self._control_payloads(),
            "decision": self.decision.value,
            "evidence": self._evidence_payloads(),
            "evidence_ids": list(self.evidence_ids),
            "generated_by_engine_id": self.generated_by_engine_id,
            "hazards": self._hazard_payloads(),
            "human_review_required": self.human_review_required,
            "independent_review_required": self.independent_review_required,
            "metadata_only": self.metadata_only,
            "notes": list(self.notes),
            "ready_for_assurance_draft_export": self.ready_for_assurance_draft_export,
            "schema_version": self.schema_version,
            "self_validated": self.self_validated,
            "source_candidate_gate_fingerprint": self.candidate_gate.fingerprint(),
            "status": self.status.value,
            "target_runtime": WAVE_SIX_ASSURANCE_TARGET_RUNTIME,
            "verification_criteria": self._verification_criterion_payloads(),
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this bridge bundle."""

        return _stable_sha256(self.canonical_payload())

    def _claim_payloads(self) -> list[dict[str, Any]]:
        """Return assurance-runtime-aligned draft claims."""

        return [
            _claim(
                "claim-boundary",
                "Bounded measured system-level cognition evidence, not AGI.",
                "Gate and bridge boundaries prevent AGI or certification claims.",
                ("assurance:fingerprint:candidate-gate",),
                ("criterion-no-agi-claim",),
            ),
            _claim(
                "claim-human-authority",
                "Human authority and independent review remain required.",
                "The gate carries human and independent reviewer identities.",
                ("assurance:fingerprint:candidate-gate",),
                ("criterion-human-authority",),
            ),
            _claim(
                "claim-evidence-traceability",
                "The package exposes traceable evidence identifiers.",
                "Evidence ids are exported for downstream review, not accepted.",
                self.evidence_ids,
                ("criterion-evidence-traceability",),
            ),
            _claim(
                "claim-blackfox-control",
                "Execution-facing review remains BlackFox-controlled.",
                "BlackFox metadata can be reviewed without Kernel dispatch.",
                self._blackfox_claim_evidence_ids(),
                ("criterion-blackfox-no-dispatch",),
            ),
        ]

    def _hazard_payloads(self) -> list[dict[str, Any]]:
        """Return assurance-runtime-aligned hazards."""

        return [
            _hazard(
                "hazard-overclaim",
                "AGI or certification overclaim",
                "Review artifacts could be misread as proof of AGI.",
                "critical",
                ("control-claim-boundary",),
                ("assurance:fingerprint:candidate-gate",),
            ),
            _hazard(
                "hazard-autonomous-execution",
                "Unauthorized autonomous execution",
                "Evidence packaging could be mistaken for action authority.",
                "catastrophic",
                ("control-no-execution-authority",),
                ("assurance:fingerprint:candidate-gate",),
            ),
            _hazard(
                "hazard-self-validation",
                "System self-validation",
                "The system could be treated as certifying itself.",
                "critical",
                ("control-human-independent-review",),
                ("assurance:fingerprint:candidate-gate",),
            ),
            _hazard(
                "hazard-evidence-gap",
                "Evidence gap hidden by packaging",
                "Missing evidence could be hidden by clean packaging.",
                "major",
                ("control-evidence-traceability",),
                self.evidence_ids,
            ),
        ]

    def _control_payloads(self) -> list[dict[str, Any]]:
        """Return assurance-runtime-aligned controls."""

        return [
            _control(
                "control-claim-boundary",
                "Claim-boundary guardrail",
                "Preserve not-AGI and not-certified boundaries.",
                ("hazard-overclaim",),
                ("assurance:fingerprint:candidate-gate",),
            ),
            _control(
                "control-no-execution-authority",
                "No execution authority",
                "Keep Kernel exports metadata-only and non-dispatching.",
                ("hazard-autonomous-execution",),
                ("assurance:fingerprint:candidate-gate",),
            ),
            _control(
                "control-human-independent-review",
                "Human and independent review",
                "Require named human and independent review surfaces.",
                ("hazard-self-validation",),
                ("assurance:fingerprint:candidate-gate",),
            ),
            _control(
                "control-evidence-traceability",
                "Evidence traceability",
                "Expose evidence ids and fingerprints without accepting them.",
                ("hazard-evidence-gap",),
                self.evidence_ids,
            ),
        ]

    def _verification_criterion_payloads(self) -> list[dict[str, Any]]:
        """Return assurance-runtime-aligned not-run verification criteria."""

        return [
            _criterion(
                "criterion-no-agi-claim",
                "Confirm no exported claim asserts AGI or certification.",
                "human-assurance-review",
                "No AGI, production, or certification claim present.",
                ("assurance:fingerprint:candidate-gate",),
            ),
            _criterion(
                "criterion-human-authority",
                "Confirm human and independent review are identified.",
                "human-assurance-review",
                "Both review identities are present and non-empty.",
                ("assurance:fingerprint:candidate-gate",),
            ),
            _criterion(
                "criterion-evidence-traceability",
                "Confirm evidence ids and fingerprints are traceable.",
                "evidence-bundle-review",
                "Evidence ids resolve in downstream review package.",
                self.evidence_ids,
            ),
            _criterion(
                "criterion-blackfox-no-dispatch",
                "Confirm any BlackFox handoff remains non-dispatching.",
                "policy-gate-review",
                "BlackFox review packet does not dispatch execution.",
                self._blackfox_claim_evidence_ids(),
            ),
        ]

    def _evidence_payloads(self) -> list[dict[str, Any]]:
        """Return assurance-runtime-aligned evidence records."""

        records = [
            _evidence(
                "assurance:fingerprint:candidate-gate",
                "Candidate gate fingerprint from IX-CognitionKernel.",
                "IX-CognitionKernel",
                ("claim-boundary", "claim-human-authority"),
                content_hash=self.candidate_gate.fingerprint(),
            )
        ]
        records.extend(
            _evidence(
                evidence_id,
                "Evidence id represented by candidate-gate payload.",
                "IX-CognitionKernel",
                ("claim-evidence-traceability",),
            )
            for evidence_id in self.gate_evidence_ids
        )
        if self.blackfox_handoff is not None:
            records.append(
                _evidence(
                    "assurance:fingerprint:blackfox-handoff",
                    "BlackFox handoff fingerprint from IX-CognitionKernel.",
                    "IX-CognitionKernel",
                    ("claim-blackfox-control",),
                    content_hash=self.blackfox_handoff.fingerprint(),
                )
            )
            records.extend(
                _evidence(
                    evidence_id,
                    "Evidence id represented by BlackFox handoff payload.",
                    "IX-CognitionKernel",
                    ("claim-blackfox-control",),
                )
                for evidence_id in self.blackfox_evidence_ids
            )
        return records

    def _blackfox_fingerprint_or_none(self) -> str | None:
        """Return BlackFox handoff fingerprint when present."""

        if self.blackfox_handoff is None:
            return None
        return self.blackfox_handoff.fingerprint()

    def _blackfox_claim_evidence_ids(self) -> tuple[str, ...]:
        """Return evidence ids for BlackFox-control claims and criteria."""

        if self.blackfox_handoff is None:
            return ("assurance:fingerprint:candidate-gate",)
        return _unique_preserving_order(
            (
                "assurance:fingerprint:blackfox-handoff",
                *self.blackfox_evidence_ids,
            )
        )


def build_wave_six_assurance_case_bridge_bundle(
    *,
    case_id: str,
    candidate_gate: AssuranceGateLike,
    blackfox_handoff: BlackFoxHandoffLike | None = None,
    notes: Iterable[str] = (),
) -> WaveSixAssuranceCaseBridgeBundle:
    """Build a metadata-only assurance-case bridge export bundle."""

    return WaveSixAssuranceCaseBridgeBundle(
        case_id=case_id,
        candidate_gate=candidate_gate,
        blackfox_handoff=blackfox_handoff,
        notes=tuple(notes),
    )


def _claim(
    claim_id: str,
    statement: str,
    argument: str,
    evidence_ids: tuple[str, ...],
    criterion_ids: tuple[str, ...],
) -> dict[str, Any]:
    """Build one assurance-runtime-aligned claim payload."""

    return {
        "argument": _require_non_empty(argument, "argument"),
        "claim_id": _require_non_empty(claim_id, "claim_id"),
        "evidence_ids": list(
            _normalize_unique_text_tuple(evidence_ids, label="evidence_id")
        ),
        "statement": _require_non_empty(statement, "statement"),
        "verification_criterion_ids": list(
            _normalize_unique_text_tuple(criterion_ids, label="criterion_id")
        ),
        "verification_result": "not_run",
    }


def _hazard(
    hazard_id: str,
    title: str,
    description: str,
    severity: str,
    control_ids: tuple[str, ...],
    evidence_ids: tuple[str, ...],
) -> dict[str, Any]:
    """Build one assurance-runtime-aligned hazard payload."""

    return {
        "control_ids": list(
            _normalize_unique_text_tuple(control_ids, label="control_id")
        ),
        "description": _require_non_empty(description, "description"),
        "evidence_ids": list(
            _normalize_unique_text_tuple(evidence_ids, label="evidence_id")
        ),
        "hazard_id": _require_non_empty(hazard_id, "hazard_id"),
        "severity": _require_non_empty(severity, "severity"),
        "title": _require_non_empty(title, "title"),
    }


def _control(
    control_id: str,
    name: str,
    description: str,
    hazard_ids: tuple[str, ...],
    evidence_ids: tuple[str, ...],
) -> dict[str, Any]:
    """Build one assurance-runtime-aligned control payload."""

    return {
        "control_id": _require_non_empty(control_id, "control_id"),
        "description": _require_non_empty(description, "description"),
        "evidence_ids": list(
            _normalize_unique_text_tuple(evidence_ids, label="evidence_id")
        ),
        "mitigates_hazard_ids": list(
            _normalize_unique_text_tuple(hazard_ids, label="hazard_id")
        ),
        "name": _require_non_empty(name, "name"),
    }


def _criterion(
    criterion_id: str,
    statement: str,
    method: str,
    expected_result: str,
    evidence_ids: tuple[str, ...],
) -> dict[str, Any]:
    """Build one assurance-runtime-aligned verification criterion payload."""

    return {
        "criterion_id": _require_non_empty(criterion_id, "criterion_id"),
        "evidence_ids": list(
            _normalize_unique_text_tuple(evidence_ids, label="evidence_id")
        ),
        "expected_result": _require_non_empty(expected_result, "expected_result"),
        "result": "not_run",
        "statement": _require_non_empty(statement, "statement"),
        "verification_method": _require_non_empty(method, "verification_method"),
    }


def _evidence(
    evidence_id: str,
    description: str,
    source: str,
    supports: tuple[str, ...],
    *,
    content_hash: str | None = None,
) -> dict[str, Any]:
    """Build one assurance-runtime-aligned evidence-link payload."""

    if content_hash is not None:
        content_hash = _require_sha256(content_hash, "content_hash")
    return {
        "content_hash": content_hash,
        "description": _require_non_empty(description, "description"),
        "evidence_id": _require_non_empty(evidence_id, "evidence_id"),
        "source": _require_non_empty(source, "source"),
        "status": "provided",
        "supports": list(_normalize_unique_text_tuple(supports, label="supports")),
    }


def _payload_text_sequence(payload: Mapping[str, Any], key: str) -> tuple[str, ...]:
    """Read a payload list/tuple of text values as a deterministic tuple."""

    values = payload.get(key, ())
    if isinstance(values, str) or not isinstance(values, Sequence):
        raise ValueError(f"Payload field `{key}` must be a sequence of text values.")
    text_values: list[str] = []
    for index, value in enumerate(values):
        if not isinstance(value, str):
            raise ValueError(f"Payload field `{key}[{index}]` must be text.")
        text_values.append(value)
    return _normalize_unique_text_tuple(text_values, label=key)


def _unique_preserving_order(values: Iterable[str]) -> tuple[str, ...]:
    """Return unique text values while preserving first-seen order."""

    seen: set[str] = set()
    unique: list[str] = []
    for value in values:
        normalized = _require_non_empty(value, "value")
        if normalized not in seen:
            unique.append(normalized)
            seen.add(normalized)
    return tuple(unique)


def _normalize_unique_text_tuple(
    values: Iterable[str],
    *,
    label: str,
) -> tuple[str, ...]:
    """Normalize text values while rejecting blanks and duplicates."""

    normalized: list[str] = []
    seen: set[str] = set()
    for value in values:
        stripped = _require_non_empty(value, label)
        if stripped in seen:
            raise ValueError(f"Duplicate {label} detected: {stripped}")
        normalized.append(stripped)
        seen.add(stripped)
    return tuple(normalized)


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
