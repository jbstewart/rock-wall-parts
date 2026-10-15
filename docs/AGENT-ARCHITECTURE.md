# Agent architecture for the code-CAD pipeline — assessment and decision

Decision record, 2026-09-14. Question asked: should this pipeline be rebuilt on a stateful agent framework — specifically LangGraph and/or Pydantic?

**Decision: adopt Pydantic for typed measurements. Do not adopt LangGraph for the CAD pipeline.** Rationale below, with the trigger conditions that would reverse either call.

## What was evaluated

**LangGraph** (1.2, May 2026) models an agent as a state machine: a state schema, nodes returning partial updates, edges, and a checkpointer (Postgres/SQLite) that persists state so runs survive crashes, support human-in-the-loop interrupts, and can rewind to a prior checkpoint. Its own documentation positions it as the low-level option and points simpler use cases elsewhere; the consistent industry read is that it earns its complexity when a workflow is genuinely a state machine with durability and audit requirements, and is a complexity tax otherwise.

**Pydantic** is two separable things. The plain library is data validation — typed models, field and cross-field validators, coercion. **PydanticAI** (v1) is the agent framework built on it: typed agents, dependency injection, output validators that re-prompt on validation failure, optional `pydantic-graph` for explicit state machines, and durable execution through third-party backends (Temporal, DBOS, Prefect, Restate) rather than built in.

**The Claude Agent SDK** and **Anthropic Managed Agents** are the other two ways to host an agent; Claude Code is already the first of these in practice, which is why no new harness is needed to have an agent driving this repo today.

## Why LangGraph is the wrong fit here

**The state is cheap to rebuild.** A full `truck_cupholder.py` run — 25 kernel checks, geometry, STEP/STL, coupons, build sheet — takes **6.2 seconds** (measured 2026-09-14). Durable checkpointing exists to protect expensive, long-running, non-reproducible state. Every design state in this repo is a deterministic function of files already in git, recoverable faster than a checkpointer round-trip. There is nothing here worth persisting that `git checkout` plus one script run does not restore.

**The latency is human and physical, not computational.** The real design loop is: generate → hand files to the printer owner → wait days → fit the part in the truck → measure with calipers. LangGraph's durable execution and interrupts are built for exactly this pause-for-a-human shape, but the pause is days long, mediated by people, and already spanned by Claude Code sessions plus the PPBO job page. A graph runtime would be orchestrating around a wait it cannot shorten.

**It would not have caught any defect this pipeline has actually produced.** Reviewing the full defect history of the first two jobs: measurement transcription errors, a bounding-box check too weak to catch a geometry gap, a misread drawing (figure-8 vs stadium), a build123d extrude-direction bug, an unchecked clip insertion path, a misleading output filename. Every one is a data-modeling failure or a missing-check failure. None is an orchestration failure. A state graph would have faithfully orchestrated its way into all of them.

## Why Pydantic is the right fit

The defect class this pipeline actually produces is bad numbers entering the parameter block and sitting there unchallenged. Today a measurement arrives as a bare float with a comment; nothing records where it came from, and nothing cross-checks it against the other numbers describing the same physical object.

A typed measurement carries its own provenance (`measured` / `drawing` / `derived` / `assumed` / `vendor`) and a date, and the model that holds a job's measurements carries **physical consistency relations** — statements about the real object, not about our design choices. A plate's underside must equal its top plus its thickness. A trim flange cannot be thicker than half the pocket it covers. An insert cannot be deeper than the recess it sits in. Cup diameters must increase from base to rim.

This was prototyped against the cup holder's real worksheet history (`projects/truck-cupholder/measurement_model_prototype.py`). Replaying the worksheet exactly as first filled in, the model caught all three transcription errors that took Rev A through Rev D to discover — the 1.32 flange thickness (a misplaced decimal on a different feature), the 1/16 plate underside (inconsistent with its own components), and the 2.0 tub depth (measured from a different datum) — in a single pass, before any geometry was generated.

It also surfaced a discrepancy still live in the current data; see the open item at the bottom of this file.

Secondary benefit: the BRIEF's measurement table becomes generated output rather than hand-maintained prose, which removes one of the two remaining manual sync burdens in the revision workflow.

## Adoption plan

1. Model measurements per job inside the project, as the prototype does. **Do not** move this to `lib/` until a second job adopts it — house rule is to generalize on the second use.
2. Keep `float(m)` working on the measurement type so existing call sites stay readable (`PLUG_R = float(m.hole_d) / 2 - 0.03`).
3. Consistency relations belong in the measurement model; design checks stay where they are, in `run_checks()`. The distinction matters: the measurement model asserts facts about the physical world, the generation checks assert that our design respects them.
4. Values marked `assumed` are reported at generation time, so a gating check never rests silently on a number nobody measured.

`pydantic>=2.13` added to `requirements.txt`.

## When to revisit

- **An LLM call inside the pipeline** (extracting measurements from a caliper photo, sweeping parameter variants) — reach for structured outputs. Anthropic's SDK parses directly into Pydantic models via `messages.parse()`, so the work above is already the groundwork. PydanticAI is the lighter wrapper if dependency injection and retry-on-validation are wanted; LangGraph would still be the wrong shape.
- **The business workflow, not the CAD.** Quote → deposit → questionnaire → site visit → release → superseded-attachment cleanup is multi-step, long-running, human-gated, and spans external systems. That is a genuine state machine and the one place in this shop where LangGraph's durability and interrupts would earn their keep. The tool layer already exists as the `platypus-business-ops` MCP server.
- **Scale.** If jobs reach the point where the same pipeline runs unattended across many parts — scheduled regeneration, drift detection against released files — revisit orchestration then. Two jobs driven interactively is not that.

## Open item raised by the prototype

The cup holder's hook-ledge depth does not reconcile. `LEDGE = 0.50` is what Rev D aimed the snap-hook ramp at, and what Rev G ships. But the component readings on the same worksheet — plate top at 11/32, plate thickness 1/8 — sum to 0.469, and the correction that produced 0.50 ("plate itself is 1/8, completely misread … it's 1/2\"") is ambiguous about whether the 1/2" was to the top of the plate or its underside.

The three readings imply materially different parts:

| If the true ledge is | Consequence for the Rev G hook |
|---|---|
| 0.469 (component readings) | 0.031 of slack — the part rattles, the Rev C complaint returns |
| 0.500 (as designed) | snug, as intended |
| 0.625 (1/2" was to plate *top*) | 0.125 of interference — the base may not seat at all |

Resolve with one caliper measurement in the truck: upholstery top straight down to the underside of the hard plastic plate. `SNUG_ADJUST` in `truck_cupholder.py` is the single knob that corrects it, and only the clips reprint. Until then, treat the Rev G snap fit as unverified against real data.
