# IX-CognitionKernel

IX-CognitionKernel is a source-available governed causal cognition research kernel by Bryce Lovell.

The project explores how an AI-assisted cognition layer can represent beliefs, evidence, uncertainty, causal assumptions, plan state, evaluation records, memory quarantine, bounded agent roles, review gates, and human authority before any execution layer is trusted.

The core rule is simple:

**Model thinks. Cognition structures. Governance checks. Humans authorize. Evidence decides trust.**

## Current maturity state

**Wave 4 — Controlled proto-candidate review package**

This repository is not an AGI claim. It is not production-ready software. It is not independently validated. It is not certified. It does not grant autonomous execution authority.

Wave 4 adds a controlled review package for early proto-candidate behaviors under strict boundaries:

- cross-domain transfer probes
- failure-repair cycles
- uncertainty preservation traces
- long-horizon mission-state traces
- safe-refusal records
- reward-hacking audits
- adversarial robustness records
- reproducible audit trails
- scorecards
- human-review packets
- bounded maturity declarations
- human-review dockets
- completion receipts

All Wave 4 records are evidence-bound, deterministic where practical, review-only, and explicitly constrained against overclaiming.

## What this repo is trying to do

IX-CognitionKernel is an attempt to build a serious research substrate for governed cognition. The goal is not to wrap model output with marketing language. The goal is to make cognition state inspectable, testable, reviewable, and bounded.

The kernel is intended to help answer questions like:

- What does the system believe?
- What evidence supports that belief?
- What remains uncertain?
- What assumptions are stale, contradicted, unsafe, or unsupported?
- What causal model is being used?
- What plan is being proposed?
- What would count as failure?
- What evidence changed after an outcome?
- What memory is trusted, quarantined, or rejected?
- What human authority is required before action?
- What claims are not allowed?

## What this repo is not

IX-CognitionKernel is not:

- AGI
- a claimed AGI candidate
- an autonomous agent deployment framework
- a production AI safety system
- a certified assurance case
- a government, defense, or enterprise-approved system
- an independent-validation result
- a benchmark victory claim
- an execution engine that can approve its own actions

The repository may model higher maturity states, but it does not claim those states are achieved unless evidence supports them.

## Maturity ladder

The project uses a six-stage maturity ladder.

### Wave 0 — Repository Foundation

Repository structure, license posture, package layout, CI, strict lint/type/test setup, doctrine, cognitive BOM, engine registry, and bounded agent role registry.

### Wave 1 — Research Prototype

Structured code can represent beliefs, evidence, confidence, uncertainty states, causal assumptions, simple plan graphs, evaluation records, non-attached purpose rules, bounded agent roles, and maturity state.

### Wave 2 — Learnable Causal Cognition Core

The system updates beliefs and behavior from evidence; tracks contradictions and stale beliefs; compares predictions against observations; quarantines bad memory; and stores validated reusable skills.

### Wave 3 — Governed AGI-Emulation Substrate

The system coordinates cognition engines, bounded agents, tribunal-style critique, reward auditing, memory quarantine, skill updates, self-play/curriculum tasks, evaluator-driven discovery, BlackFox handoff packages, WorldTwin reasoning, and assurance-style evidence records.

### Wave 4 — Controlled Proto-Candidate Review Package

The system creates a bounded review package for proto-candidate behaviors under controlled tests. It includes transfer probes, failure-repair cycles, uncertainty preservation, mission-state continuity, safe refusal, reward/adversarial audits, reproducible receipts, scorecards, human-review dockets, and explicit no-AGI/no-production/no-independent-validation boundaries.

### Wave 5 — Credible AGI Candidate Under Independent Validation

This state would require external protocols, independent reviewers, reproducible evidence bundles, adversarial safety tests, long-horizon task tests, cross-domain transfer tests, memory integrity checks, safe-refusal proof, and preserved human authority.

This repository does not claim Wave 5.

### Wave 6 — AGI, only if overwhelming evidence justifies it

This state would require broad, durable, independently validated general intelligence, including novel skill acquisition, cross-domain transfer without custom retraining per task, causal understanding, long-horizon coherence, self-correction from evidence, stable mission identity, robust world modeling, safe uncertainty handling, transparent evidence trails, and independent repeatability.

This repository does not claim Wave 6.

## Core doctrine

IX-CognitionKernel uses the following doctrine:

- evidence over confidence
- uncertainty honesty over performance theater
- human authority over autonomous self-approval
- bounded review over hidden execution
- deterministic receipts over vibes
- memory quarantine over blind persistence
- contradiction handling over narrative smoothing
- reward-audit discipline over metric chasing
- safe refusal over unsafe compliance
- no maturity promotion without evidence

## Wave 4 architecture

Wave 4 is built around a controlled proto-candidate review package.

The major source modules include:

- `wave4_contracts.py`
- `wave4_trials.py`
- `wave4_transfer.py`
- `wave4_transfer_bundle.py`
- `wave4_failure_repair.py`
- `wave4_repair_suite.py`
- `wave4_mission_state.py`
- `wave4_safe_refusal.py`
- `wave4_adversarial_robustness.py`
- `wave4_audit_trail.py`
- `wave4_proto_candidate.py`
- `wave4_scorecard.py`
- `wave4_review_packet.py`
- `wave4_maturity_declaration.py`
- `wave4_review_docket.py`
- `wave4_completion_receipt.py`

These modules work together as a review pipeline:

1. Build controlled task evidence.
2. Convert task outputs into artifact references.
3. Bundle transfer, repair, mission-state, refusal, adversarial, reward, and audit evidence.
4. Score the proto-candidate package.
5. Build a human-review packet.
6. Build a bounded maturity declaration.
7. Build a review docket.
8. Build a completion receipt.
9. Preserve explicit no-execution, no-AGI, no-production, and no-independent-validation boundaries.

## Wave 4 evidence boundaries

Wave 4 records are designed to fail closed.

A record that lacks evidence should not pretend to be ready.

A record that detects repair issues should not pretend to be complete.

A record with blocked evidence should block progress.

A record may not grant execution authority.

A record may not claim AGI.

A record may not claim independent validation.

A record may not claim production readiness.

## Human authority

The repository preserves human authority as a first-class boundary.

Human review is not a decorative field. It is a control boundary. Wave 4 artifacts are review packages, not execution permission.

The intended posture is:

**AI-generated or AI-assisted cognition remains untrusted until evidence, policy, review, and human authorization say otherwise.**

## Relationship to IX-BlackFox

IX-CognitionKernel is the cognition and planning side of the larger IX research direction.

The intended separation is:

- IX-CognitionKernel structures cognition, evidence, uncertainty, plans, memory, and review packages.
- IX-BlackFox governs execution-facing code-change workflows with policy gates, receipts, CI evidence, and human review.
- IX-BlackFox-WorldTwin-style reasoning can provide scenario and consequence context before execution-facing handoff.

The boundary is intentional:

**Cognition does not equal permission.**

## Install for local development

This repository uses Python packaging with strict test, lint, and type-check discipline.

A typical local setup is:

```
python -m pip install -e ".[dev]"
```
Run checks

Run formatting/lint checks:
```
python -m ruff check .
```
Run type checks:
```
python -m mypy src tests
```
Run tests:
```
python -m pytest
```
Test philosophy

The test suite is not just checking happy-path object construction. The tests are intended to enforce the project doctrine:

missing evidence must surface as a gap
failed checks must carry failure text
passed checks must not carry failure text
duplicate ids are rejected
blocked records block progress
execution permission is rejected
AGI claims are rejected
independent-validation claims are rejected
production-readiness claims are rejected
deterministic fingerprints remain stable across input ordering
human-review state stays explicit
Source-available license posture

IX-CognitionKernel is source-available for evaluation and review under the repository license.

It should not be described as open source unless the license is changed to an OSI-approved open-source license.

Commercial, production, derivative operational, hosted-service, procurement, contractor, funded pilot, or government operational use requires the permission terms stated in the repository license.

Authorship

Created by Bryce Lovell.

Copyright © 2026 Bryce Lovell.

Status note

This repository is a research prototype. Any claim about readiness must be backed by tests, evidence records, independent review where applicable, and the actual repository state at the time of review.

No README statement should be interpreted as a claim of AGI, production readiness, certification, government affiliation, or independent validation.
