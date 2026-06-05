import pytest

from ix_cognition_kernel.wave5_contracts import (
    WaveFiveArtifactDecision,
    WaveFiveAuthorityState,
    WaveFiveSourceSystem,
    WaveFiveValidationStatus,
)
from ix_cognition_kernel.wave5_external_review_packet import (
    WaveFiveExternalReviewPacket,
    WaveFiveReviewPacketSection,
    WaveFiveReviewPacketSectionKind,
    WaveFiveReviewPacketState,
    WaveFiveReviewQuestion,
    WaveFiveReviewQuestionKind,
    WaveFiveReviewResponse,
    WaveFiveReviewResponseDisposition,
    blocking_review_response_dispositions,
    external_review_packet_source_systems,
    required_review_packet_section_kinds,
    required_review_question_kinds,
    safe_review_response_dispositions,
)


def _review_sections() -> tuple[WaveFiveReviewPacketSection, ...]:
    return tuple(
        WaveFiveReviewPacketSection(
            section_id=f"section-{section_kind.value}",
            section_kind=section_kind,
            title=f"Section {section_kind.value}",
            summary=f"Review section for {section_kind.value}",
            artifact_ids=(f"artifact-{section_kind.value}",),
            evidence_ids=(f"evidence-{section_kind.value}",),
            required_reviewer_actions=(f"review-{section_kind.value}",),
        )
        for section_kind in required_review_packet_section_kinds()
    )


def _review_questions() -> tuple[WaveFiveReviewQuestion, ...]:
    return tuple(
        WaveFiveReviewQuestion(
            question_id=f"question-{question_kind.value}",
            question_kind=question_kind,
            question=f"Can reviewers assess {question_kind.value}?",
            expected_evidence_ids=(f"question-evidence-{question_kind.value}",),
        )
        for question_kind in required_review_question_kinds()
    )


def _review_responses(
    disposition: WaveFiveReviewResponseDisposition = (
        WaveFiveReviewResponseDisposition.ACCEPTED_WITH_BOUNDARIES
    ),
) -> tuple[WaveFiveReviewResponse, ...]:
    return tuple(
        WaveFiveReviewResponse(
            response_id=f"response-{question_kind.value}",
            question_id=f"question-{question_kind.value}",
            reviewer_id="reviewer-1",
            disposition=disposition,
            rationale=f"Reviewer response for {question_kind.value}",
            evidence_ids=(f"response-evidence-{question_kind.value}",),
            reviewer_source_system=WaveFiveSourceSystem.INDEPENDENT_REVIEWER,
            limitations=(
                (f"limited-{question_kind.value}",)
                if disposition
                is WaveFiveReviewResponseDisposition.ACCEPTED_WITH_LIMITATIONS
                else ()
            ),
        )
        for question_kind in required_review_question_kinds()
    )


def _review_packet(
    *,
    packet_state: WaveFiveReviewPacketState = (
        WaveFiveReviewPacketState.READY_FOR_EXTERNAL_REVIEW
    ),
    source_system: WaveFiveSourceSystem = WaveFiveSourceSystem.IX_COGNITION_KERNEL,
    sections: tuple[WaveFiveReviewPacketSection, ...] | None = None,
    questions: tuple[WaveFiveReviewQuestion, ...] | None = None,
    responses: tuple[WaveFiveReviewResponse, ...] | None = None,
    reviewer_ids: tuple[str, ...] = (),
) -> WaveFiveExternalReviewPacket:
    return WaveFiveExternalReviewPacket(
        packet_id="review-packet-1",
        title="Wave 5 external review packet",
        source_system=source_system,
        packet_state=packet_state,
        sections=sections or _review_sections(),
        questions=questions or _review_questions(),
        responses=responses if responses is not None else _review_responses(),
        reviewer_instructions=("Review the packet without granting maturity.",),
        gap_summaries=("No unresolved packet gaps.",),
        reviewer_ids=reviewer_ids,
    )


def test_required_review_packet_sets_are_locked() -> None:
    assert len(required_review_packet_section_kinds()) >= 10
    assert len(required_review_question_kinds()) >= 6
    assert (
        WaveFiveReviewResponseDisposition.ACCEPTED_WITH_BOUNDARIES
        in safe_review_response_dispositions()
    )
    assert (
        WaveFiveReviewResponseDisposition.REJECTED
        in blocking_review_response_dispositions()
    )
    assert (
        WaveFiveSourceSystem.INDEPENDENT_REVIEWER
        in external_review_packet_source_systems()
    )


def test_review_packet_ready_when_sections_questions_and_responses_are_complete() -> (
    None
):
    packet = _review_packet()

    assert packet.has_required_section_coverage
    assert packet.has_required_question_coverage
    assert packet.ready_for_external_review
    assert not packet.blocks_packet_readiness
    assert packet.blocking_response_ids == ()
    assert packet.unanswered_blocking_question_ids == ()

    artifact_ref = packet.to_artifact_ref()
    assert (
        artifact_ref.decision is WaveFiveArtifactDecision.READY_FOR_INDEPENDENT_REVIEW
    )
    assert artifact_ref.authority_state is WaveFiveAuthorityState.HUMAN_REVIEW_REQUIRED
    assert (
        artifact_ref.validation_status
        is WaveFiveValidationStatus.UNDER_INDEPENDENT_REVIEW
    )
    assert artifact_ref.evidence_ids == packet.all_evidence_ids


def test_review_packet_blocks_missing_required_section() -> None:
    sections = tuple(
        section
        for section in _review_sections()
        if section.section_kind is not WaveFiveReviewPacketSectionKind.CLAIM_LIMITS
    )

    packet = _review_packet(sections=sections)

    assert packet.missing_required_section_kinds == (
        WaveFiveReviewPacketSectionKind.CLAIM_LIMITS,
    )
    assert packet.blocks_packet_readiness
    assert not packet.ready_for_external_review


def test_review_packet_blocks_missing_required_question_kind() -> None:
    questions = tuple(
        question
        for question in _review_questions()
        if question.question_kind is not WaveFiveReviewQuestionKind.OVERCLAIM
    )
    responses = tuple(
        response
        for response in _review_responses()
        if response.question_id != "question-overclaim"
    )

    packet = _review_packet(questions=questions, responses=responses)

    assert packet.missing_required_question_kinds == (
        WaveFiveReviewQuestionKind.OVERCLAIM,
    )
    assert packet.blocks_packet_readiness
    assert not packet.ready_for_external_review


def test_review_packet_blocks_unanswered_blocking_questions() -> None:
    packet = _review_packet(responses=())

    assert packet.unanswered_blocking_question_ids
    assert packet.blocks_packet_readiness
    assert not packet.ready_for_external_review


def test_review_packet_blocks_disputed_responses() -> None:
    packet = _review_packet(
        responses=_review_responses(
            disposition=WaveFiveReviewResponseDisposition.DISPUTED
        )
    )

    assert packet.blocking_response_ids
    assert packet.blocks_packet_readiness
    assert not packet.ready_for_external_review


def test_review_packet_rejects_forbidden_claims() -> None:
    with pytest.raises(ValueError, match="cannot claim AGI"):
        WaveFiveExternalReviewPacket(
            packet_id="invalid-review-packet",
            title="Invalid packet",
            source_system=WaveFiveSourceSystem.IX_COGNITION_KERNEL,
            packet_state=WaveFiveReviewPacketState.INTERNAL_PACKET_READY,
            sections=_review_sections(),
            questions=_review_questions(),
            responses=_review_responses(),
            reviewer_instructions=("Review only.",),
            gap_summaries=("No gaps.",),
            claims_agi=True,
        )


def test_externally_reviewed_packet_requires_external_source() -> None:
    with pytest.raises(ValueError, match="external review source"):
        _review_packet(
            packet_state=WaveFiveReviewPacketState.EXTERNALLY_REVIEWED_WITH_BOUNDARIES,
            source_system=WaveFiveSourceSystem.IX_COGNITION_KERNEL,
            reviewer_ids=("reviewer-1",),
        )


def test_externally_reviewed_packet_exports_reviewed_artifact() -> None:
    packet = _review_packet(
        packet_state=WaveFiveReviewPacketState.EXTERNALLY_REVIEWED_WITH_BOUNDARIES,
        source_system=WaveFiveSourceSystem.EXTERNAL_REVIEW,
        reviewer_ids=("reviewer-1",),
    )

    assert packet.externally_reviewed_with_boundaries
    artifact_ref = packet.to_artifact_ref()
    assert artifact_ref.decision is WaveFiveArtifactDecision.EXTERNALLY_REVIEWED
    assert (
        artifact_ref.validation_status
        is WaveFiveValidationStatus.ACCEPTED_WITH_BOUNDARIES
    )
