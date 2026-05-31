"""Ten-layer cognitive bill of materials for IX-CognitionKernel.

The cognitive BOM turns the 52 research and failure threads into architecture
layers. Each layer contributes a mechanism, a governance constraint, or a test
pressure that the cognition kernel must preserve instead of treating the threads
as loose inspiration.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class LayerKind(StrEnum):
    """Functional class for a cognitive BOM layer."""

    LEARNING_MECHANISM = "learning-mechanism"
    COMMUNICATION_MECHANISM = "communication-mechanism"
    WORLD_MODELING = "world-modeling"
    DISCOVERY_MECHANISM = "discovery-mechanism"
    MEMORY_MECHANISM = "memory-mechanism"
    SCIENTIFIC_LOOP = "scientific-loop"
    TOOL_USE = "tool-use"
    GOVERNANCE_MECHANISM = "governance-mechanism"
    FAILURE_THREAD = "failure-thread"
    IX_GOVERNANCE = "ix-governance"


@dataclass(frozen=True, slots=True)
class CognitiveLayer:
    """A locked layer in the IX-CognitionKernel cognitive BOM."""

    number: int
    name: str
    kind: LayerKind
    role: str
    required_kernel_pressure: str
    representative_threads: tuple[str, ...]

    @property
    def label(self) -> str:
        """Return the canonical layer label."""

        return f"Layer {self.number}: {self.name}"


COGNITIVE_BOM: tuple[CognitiveLayer, ...] = (
    CognitiveLayer(
        number=1,
        name="Self-play / open-ended curriculum",
        kind=LayerKind.LEARNING_MECHANISM,
        role=(
            "Generate staged challenges and adversarial practice loops so the "
            "kernel can improve through controlled task pressure instead of "
            "static prompting."
        ),
        required_kernel_pressure=(
            "Every curriculum task must produce measurable objectives, failure "
            "records, transfer checks, and stop conditions."
        ),
        representative_threads=(
            "AlphaZero",
            "POET",
            "OpenAI Five",
            "AlphaStar",
            "DeepNash",
        ),
    ),
    CognitiveLayer(
        number=2,
        name="Emergent communication / multi-agent protocol learning",
        kind=LayerKind.COMMUNICATION_MECHANISM,
        role=(
            "Study and constrain learned agent communication so compressed or "
            "non-obvious protocols remain logged, translated, and governable."
        ),
        required_kernel_pressure=(
            "No private protocol may influence action unless it is recorded, "
            "mapped to task outcomes, and rendered into human-readable evidence."
        ),
        representative_threads=(
            "Facebook FAIR negotiation agents",
            "DIAL/RIAL",
            "CommNet",
            "referential games",
            "LLM social convention studies",
        ),
    ),
    CognitiveLayer(
        number=3,
        name="World-model / imagination layer",
        kind=LayerKind.WORLD_MODELING,
        role=(
            "Represent possible futures, constraints, counterfactuals, and "
            "causal assumptions before any action leaves the cognition layer."
        ),
        required_kernel_pressure=(
            "Predictions must expose assumptions, uncertainty, and expected "
            "observable results before execution."
        ),
        representative_threads=(
            "MuZero",
            "Dreamer",
            "JEPA/world-model research",
            "Genie-style environment generation",
            "IX-BlackFox-WorldTwin",
        ),
    ),
    CognitiveLayer(
        number=4,
        name="Evaluator-driven discovery",
        kind=LayerKind.DISCOVERY_MECHANISM,
        role=(
            "Force generated ideas, plans, and candidate solutions through "
            "executable or inspectable evaluators instead of accepting fluency."
        ),
        required_kernel_pressure=(
            "Discovery claims require evaluator outputs, pass/fail criteria, and "
            "evidence records before they can update beliefs or skills."
        ),
        representative_threads=(
            "FunSearch",
            "AlphaEvolve",
            "AlphaTensor",
            "AlphaDev",
            "AlphaProof/AlphaGeometry",
        ),
    ),
    CognitiveLayer(
        number=5,
        name="Memory / reflection / skill accumulation",
        kind=LayerKind.MEMORY_MECHANISM,
        role=(
            "Preserve validated lessons, failure causes, reusable procedures, and "
            "long-horizon mission continuity without treating raw output as memory."
        ),
        required_kernel_pressure=(
            "Memory updates must pass quarantine, provenance, contradiction, and "
            "reuse-safety checks."
        ),
        representative_threads=(
            "Voyager",
            "Reflexion",
            "Generative Agents",
            "skill libraries",
            "memory quarantine doctrine",
        ),
    ),
    CognitiveLayer(
        number=6,
        name="Scientific-loop automation",
        kind=LayerKind.SCIENTIFIC_LOOP,
        role=(
            "Structure hypothesis, experiment design, measurement, analysis, and "
            "belief revision as a controlled loop."
        ),
        required_kernel_pressure=(
            "Scientific claims must include controls, measurement limits, negative "
            "results, uncertainty, and no-novelty-without-proof discipline."
        ),
        representative_threads=(
            "Robot Scientist Adam",
            "A-Lab",
            "ChemCrow",
            "The AI Scientist",
            "measurement-first IX science repos",
        ),
    ),
    CognitiveLayer(
        number=7,
        name="Tool-using agents / coding agents",
        kind=LayerKind.TOOL_USE,
        role=(
            "Allow models and agents to inspect, plan, edit, test, and interact "
            "with tools only through bounded authority and evidence-producing steps."
        ),
        required_kernel_pressure=(
            "Tool calls require purpose, permission, reversibility analysis, logs, "
            "and post-action evidence."
        ),
        representative_threads=(
            "ReAct",
            "SWE-agent",
            "AutoGPT-style systems",
            "coding-agent repair loops",
            "IX-BlackFox",
        ),
    ),
    CognitiveLayer(
        number=8,
        name="Multi-agent governance / specialist roles",
        kind=LayerKind.GOVERNANCE_MECHANISM,
        role=(
            "Use bounded agent roles to create critique, verification, routing, "
            "translation, and safety pressure without turning the system into a "
            "free-form agent swarm."
        ),
        required_kernel_pressure=(
            "Agents must produce structured artifacts and cannot gain authority "
            "from persuasion or volume of text."
        ),
        representative_threads=(
            "proposer/skeptic/verifier patterns",
            "specialist routing",
            "multi-agent tribunals",
            "CICERO-style strategy lessons",
            "IX-BlackFox-Cognition",
        ),
    ),
    CognitiveLayer(
        number=9,
        name="Failure/danger threads",
        kind=LayerKind.FAILURE_THREAD,
        role=(
            "Treat misalignment, deception, reward hacking, and evaluation gaming "
            "as required design inputs rather than afterthoughts."
        ),
        required_kernel_pressure=(
            "The kernel must detect objective mismatch, hidden uncertainty, "
            "deceptive incentives, benchmark gaming, and unsafe action pressure."
        ),
        representative_threads=(
            "specification gaming",
            "reward hacking",
            "alignment faking",
            "scheming evaluations",
            "deception and evaluation gaming",
        ),
    ),
    CognitiveLayer(
        number=10,
        name="IX governance stack",
        kind=LayerKind.IX_GOVERNANCE,
        role=(
            "Bind cognition to source-available IX governance patterns: human "
            "authority, receipts, assurance claims, world-model review, and "
            "least-authority action."
        ),
        required_kernel_pressure=(
            "No evidence-bound action package leaves the cognition layer without "
            "reviewable claims, uncertainty, authority boundaries, and handoff data."
        ),
        representative_threads=(
            "IX-BlackFox",
            "IX-BlackFox-Cognition",
            "IX-BlackFox-WorldTwin",
            "IX-Autonomy-Assurance-Case-Runtime",
            "IX-Decriel",
            "IX-Agent-Notary",
        ),
    ),
)


def layer_by_number(number: int) -> CognitiveLayer:
    """Return a cognitive BOM layer by number."""

    for layer in COGNITIVE_BOM:
        if layer.number == number:
            return layer
    raise ValueError(f"Unknown IX-CognitionKernel cognitive BOM layer: {number}")


def layer_names() -> tuple[str, ...]:
    """Return the locked cognitive BOM layer names in order."""

    return tuple(layer.name for layer in COGNITIVE_BOM)


def layers_by_kind(kind: LayerKind) -> tuple[CognitiveLayer, ...]:
    """Return all cognitive BOM layers matching a functional kind."""

    return tuple(layer for layer in COGNITIVE_BOM if layer.kind is kind)


def required_kernel_pressures() -> tuple[str, ...]:
    """Return the governance or test pressure imposed by every layer."""

    return tuple(layer.required_kernel_pressure for layer in COGNITIVE_BOM)
