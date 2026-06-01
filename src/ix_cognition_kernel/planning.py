"""Simple plan graph records for IX-CognitionKernel Wave 1 preparation.

This module represents proposed plans as reviewable structure only. It does not
execute actions, authorize handoffs, or claim that a plan is safe. Wave 1 needs
plan nodes, dependencies, rollback metadata, evidence requirements, and stop
conditions to exist as typed records before later waves add richer evaluation and
handoff behavior.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from enum import StrEnum


class StopSeverity(StrEnum):
    """Severity of a stop condition attached to a plan node."""

    OBSERVE = "observe"
    CAUTION = "caution"
    BLOCKING = "blocking"
    KILL_SWITCH = "kill-switch"


class PlanNodeStatus(StrEnum):
    """Governed readiness status for a proposed plan node."""

    PROPOSED = "proposed"
    READY = "ready"
    BLOCKED = "blocked"
    COMPLETED = "completed"


@dataclass(frozen=True, slots=True)
class EvidenceRequirement:
    """Evidence required before a plan node can be considered ready."""

    requirement_id: str
    description: str
    required_evidence_ids: tuple[str, ...]
    satisfied_evidence_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        """Validate evidence requirement identity and description."""

        if not self.requirement_id.strip():
            raise ValueError(
                "Evidence requirements require a non-empty requirement_id."
            )
        if not self.description.strip():
            raise ValueError("Evidence requirements require a non-empty description.")
        _unique_ids(self.required_evidence_ids, label="required_evidence_id")
        _unique_ids(self.satisfied_evidence_ids, label="satisfied_evidence_id")

    @property
    def missing_evidence_ids(self) -> tuple[str, ...]:
        """Return required evidence ids that have not been satisfied."""

        satisfied = set(self.satisfied_evidence_ids)
        return tuple(
            evidence_id
            for evidence_id in self.required_evidence_ids
            if evidence_id not in satisfied
        )

    @property
    def is_satisfied(self) -> bool:
        """Return whether all required evidence ids have been satisfied."""

        return not self.missing_evidence_ids


@dataclass(frozen=True, slots=True)
class RollbackStep:
    """Rollback metadata for reversing or safely halting a plan node."""

    rollback_id: str
    description: str
    restores_node_ids: tuple[str, ...]
    requires_human_confirmation: bool

    def __post_init__(self) -> None:
        """Validate rollback identity and description."""

        if not self.rollback_id.strip():
            raise ValueError("Rollback steps require a non-empty rollback_id.")
        if not self.description.strip():
            raise ValueError("Rollback steps require a non-empty description.")


@dataclass(frozen=True, slots=True)
class StopCondition:
    """Condition that can pause or block a plan node before handoff."""

    condition_id: str
    description: str
    severity: StopSeverity
    triggered: bool
    evidence_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        """Validate stop-condition identity and description."""

        if not self.condition_id.strip():
            raise ValueError("Stop conditions require a non-empty condition_id.")
        if not self.description.strip():
            raise ValueError("Stop conditions require a non-empty description.")
        if self.triggered and not self.evidence_ids:
            raise ValueError("Triggered stop conditions require evidence ids.")

    @property
    def blocks_node(self) -> bool:
        """Return whether this condition blocks an attached node."""

        return self.triggered and self.severity in {
            StopSeverity.BLOCKING,
            StopSeverity.KILL_SWITCH,
        }


@dataclass(frozen=True, slots=True)
class PlanNode:
    """A proposed plan step with dependencies and governance metadata."""

    node_id: str
    title: str
    proposed_action: str
    depends_on: tuple[str, ...]
    belief_ids: tuple[str, ...]
    causal_assumption_ids: tuple[str, ...]
    evidence_requirement_ids: tuple[str, ...]
    rollback_step_ids: tuple[str, ...]
    stop_condition_ids: tuple[str, ...]
    reversible: bool
    human_authority_required: bool
    status: PlanNodeStatus = PlanNodeStatus.PROPOSED

    def __post_init__(self) -> None:
        """Validate plan-node identity, action text, and safety metadata."""

        if not self.node_id.strip():
            raise ValueError("Plan nodes require a non-empty node_id.")
        if not self.title.strip():
            raise ValueError("Plan nodes require a non-empty title.")
        if not self.proposed_action.strip():
            raise ValueError("Plan nodes require a non-empty proposed_action.")
        if self.node_id in self.depends_on:
            raise ValueError("Plan nodes cannot depend on themselves.")
        if self.reversible and not self.rollback_step_ids:
            raise ValueError("Reversible plan nodes require rollback_step_ids.")
        _unique_ids(self.depends_on, label="dependency node_id")
        _unique_ids(self.belief_ids, label="belief_id")
        _unique_ids(self.causal_assumption_ids, label="causal_assumption_id")
        _unique_ids(self.evidence_requirement_ids, label="evidence_requirement_id")
        _unique_ids(self.rollback_step_ids, label="rollback_step_id")
        _unique_ids(self.stop_condition_ids, label="stop_condition_id")

    @property
    def is_terminal_status(self) -> bool:
        """Return whether the node is in a terminal status."""

        return self.status in {PlanNodeStatus.BLOCKED, PlanNodeStatus.COMPLETED}


@dataclass(frozen=True, slots=True)
class SimplePlanGraph:
    """Wave 1 container for a bounded plan graph and its safety records."""

    graph_id: str
    objective: str
    nodes: tuple[PlanNode, ...]
    evidence_requirements: tuple[EvidenceRequirement, ...]
    rollback_steps: tuple[RollbackStep, ...]
    stop_conditions: tuple[StopCondition, ...]

    def __post_init__(self) -> None:
        """Validate graph identity, uniqueness, references, and cycles."""

        if not self.graph_id.strip():
            raise ValueError("Plan graphs require a non-empty graph_id.")
        if not self.objective.strip():
            raise ValueError("Plan graphs require a non-empty objective.")
        if not self.nodes:
            raise ValueError("Plan graphs require at least one plan node.")

        node_ids = _unique_ids((node.node_id for node in self.nodes), label="node_id")
        evidence_requirement_ids = _unique_ids(
            (requirement.requirement_id for requirement in self.evidence_requirements),
            label="evidence_requirement_id",
        )
        rollback_step_ids = _unique_ids(
            (rollback.rollback_id for rollback in self.rollback_steps),
            label="rollback_step_id",
        )
        stop_condition_ids = _unique_ids(
            (condition.condition_id for condition in self.stop_conditions),
            label="stop_condition_id",
        )

        for node in self.nodes:
            _validate_reference_subset(
                node.depends_on,
                node_ids,
                owner=node.node_id,
                label="dependency node_id",
            )
            _validate_reference_subset(
                node.evidence_requirement_ids,
                evidence_requirement_ids,
                owner=node.node_id,
                label="evidence_requirement_id",
            )
            _validate_reference_subset(
                node.rollback_step_ids,
                rollback_step_ids,
                owner=node.node_id,
                label="rollback_step_id",
            )
            _validate_reference_subset(
                node.stop_condition_ids,
                stop_condition_ids,
                owner=node.node_id,
                label="stop_condition_id",
            )
        _reject_dependency_cycles(self.nodes)

    @property
    def root_nodes(self) -> tuple[PlanNode, ...]:
        """Return nodes with no dependencies."""

        return tuple(node for node in self.nodes if not node.depends_on)

    @property
    def terminal_nodes(self) -> tuple[PlanNode, ...]:
        """Return nodes that no other node depends on."""

        depended_on = {
            dependency for node in self.nodes for dependency in node.depends_on
        }
        return tuple(node for node in self.nodes if node.node_id not in depended_on)

    @property
    def blocking_stop_conditions(self) -> tuple[StopCondition, ...]:
        """Return triggered stop conditions that block plan nodes."""

        return tuple(
            condition for condition in self.stop_conditions if condition.blocks_node
        )

    @property
    def unmet_evidence_requirements(self) -> tuple[EvidenceRequirement, ...]:
        """Return unsatisfied evidence requirements in the graph."""

        return tuple(
            requirement
            for requirement in self.evidence_requirements
            if not requirement.is_satisfied
        )

    @property
    def blocked_nodes(self) -> tuple[PlanNode, ...]:
        """Return nodes blocked by status or triggered blocking stop conditions."""

        blocking_condition_ids = {
            condition.condition_id for condition in self.blocking_stop_conditions
        }
        return tuple(
            node
            for node in self.nodes
            if node.status is PlanNodeStatus.BLOCKED
            or bool(blocking_condition_ids.intersection(node.stop_condition_ids))
        )

    def node_by_id(self, node_id: str) -> PlanNode:
        """Return a plan node by id."""

        for node in self.nodes:
            if node.node_id == node_id:
                return node
        raise ValueError(f"Unknown plan node_id: {node_id}")

    def ready_nodes(self, completed_node_ids: tuple[str, ...]) -> tuple[PlanNode, ...]:
        """Return nodes whose dependencies, evidence, and stops permit review."""

        completed = set(completed_node_ids)
        known_node_ids = {node.node_id for node in self.nodes}
        unknown_completed = completed.difference(known_node_ids)
        if unknown_completed:
            missing_completed = sorted(unknown_completed)[0]
            raise ValueError(
                f"Completed node id is not in plan graph: {missing_completed}"
            )

        blocked_node_ids = {node.node_id for node in self.blocked_nodes}
        unmet_requirement_ids = {
            requirement.requirement_id
            for requirement in self.unmet_evidence_requirements
        }
        ready: list[PlanNode] = []
        for node in self.nodes:
            if node.node_id in completed or node.node_id in blocked_node_ids:
                continue
            if node.status not in {PlanNodeStatus.PROPOSED, PlanNodeStatus.READY}:
                continue
            if not set(node.depends_on).issubset(completed):
                continue
            if unmet_requirement_ids.intersection(node.evidence_requirement_ids):
                continue
            ready.append(node)
        return tuple(ready)


def _unique_ids(values: Iterable[str], *, label: str) -> set[str]:
    """Return unique ids while rejecting duplicates."""

    seen: set[str] = set()
    for value in values:
        if value in seen:
            raise ValueError(f"Duplicate {label} detected: {value}")
        seen.add(value)
    return seen


def _validate_reference_subset(
    referenced_ids: tuple[str, ...],
    known_ids: set[str],
    *,
    owner: str,
    label: str,
) -> None:
    """Reject references that are not present inside a plan graph."""

    missing = tuple(
        reference_id for reference_id in referenced_ids if reference_id not in known_ids
    )
    if missing:
        raise ValueError(f"{owner} references unknown {label}: {missing[0]}")


def _reject_dependency_cycles(nodes: tuple[PlanNode, ...]) -> None:
    """Reject plan graphs with dependency cycles."""

    dependencies_by_node = {node.node_id: node.depends_on for node in nodes}
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node_id: str) -> None:
        if node_id in visited:
            return
        if node_id in visiting:
            raise ValueError(f"Plan graph contains a dependency cycle at {node_id}.")
        visiting.add(node_id)
        for dependency_id in dependencies_by_node[node_id]:
            visit(dependency_id)
        visiting.remove(node_id)
        visited.add(node_id)

    for node in nodes:
        visit(node.node_id)
