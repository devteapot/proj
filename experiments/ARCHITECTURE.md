# Architecture — Projection Runtime Experiments

This document reflects the audit finding: the original p0 design was a useful LLM/JSON app harness, but it did **not** prove the strong “model is the app” thesis. This version separates the prototype space into explicit tracks so the repo does not overclaim.

## Design Principle

Be precise about where application state lives.

| State surface | What it is | Does it prove strong projection? |
|---|---|---|
| Weights | Learned model parameters | Only if app behavior/state is trained into weights; usually static, not session state |
| Activations / recurrent state / KV cache | Inference-time hidden state | Candidate strong-projection state |
| Prompt-visible context / transcript | Explicit symbolic tokens supplied to the model | Weak projection, not hidden-state proof |
| JSON/db/files | Ordinary external state | Hybrid projection, not neural runtime proof |
| Generated HTML/JS/UI schema | Rendered or executable artifact | View layer or code layer, not app identity |

A prototype may use any of these, but it must label itself honestly.

## Core Terms

### Strong Projection

The model's internal state is the authoritative application state. The UI is a projection of that state. External artifacts may exist for display, logging, or safety, but they are not the canonical runtime.

Requirements:

1. State is represented in neural internals: activations, KV cache, recurrent memory, latent state, or trained weights.
2. State can be observed or decoded without relying only on generated self-reports.
3. State can be mutated through interaction.
4. State can be snapshotted, restored, perturbed, or probed.
5. Projection fidelity can be tested independently.

### Weak Projection

The model simulates an app over a transcript. Each interaction is fed back to the model, which emits the next UI. This is the Mirage/Websim pattern.

Useful for:

- testing malleable UX,
- measuring state drift,
- exploring “no app-specific code” interaction loops.

Not proof of:

- hidden-state persistence,
- durable identity,
- transactional semantics,
- real model-internal app state.

### Hybrid Projection

A conventional state substrate exists — JSON, database, files, event log — and the model mutates or renders it. This is practical and probably the fastest useful demo.

Useful for:

- building a working product surface,
- validating projection UX,
- creating test suites and invariant checks,
- later comparing against strong-projection experiments.

Not proof that:

- the model is the app.

## Prototype Tracks

## Track A — Weak Projection / Mirage-Style Loop

### Goal

Build the smallest code-less hallucinated app loop:

```text
Domain prompt + interaction history + user event
    -> model
    -> next UI projection
```

### Scope

- Input: domain description, user interactions, current transcript.
- Output: HTML/text/structured UI for the next screen.
- No app-specific business logic outside the model prompt.
- The host only captures interactions and displays the returned projection.

### Architecture

```text
User event
   │
   ▼
Interaction capture ──► Transcript builder ──► Model call ──► UI projection
                                                     │              │
                                                     ▼              ▼
                                               Raw response     Rendered view
```

### What It Tests

- How far a model can simulate a small app from interaction history.
- How quickly state drifts.
- Whether users tolerate per-interaction generation latency.
- Whether generated UI remains interactable over many turns.

### What It Does Not Test

- Hidden/KV state as the application.
- Durable persistence beyond transcript/context.
- Strong invariants.

### Minimum Evaluation

1. Run scripted app tasks: todo list, notes, tiny CRM.
2. Measure state loss over 50/100/200 interactions.
3. Inject adversarial user inputs that try to corrupt state.
4. Compare visible UI against a test oracle reconstructed from the transcript.
5. Track latency per interaction.

## Track B — Hybrid Projection Harness

### Goal

Build a useful, testable projection-style app runtime with explicit state. This is the pragmatic engineering baseline, not the strong thesis.

```text
User event
   │
   ▼
Explicit state manager ──► model-assisted transition ──► explicit state update
        │                                                        │
        └────────────────────► projection renderer ◄─────────────┘
                                      │
                                      ▼
                                   UI output
```

### State Model

State is explicit JSON or an event log. Example:

```json
{
  "session_id": "abc123",
  "domain": "notes",
  "records": [],
  "active_record_id": null,
  "history": [],
  "metadata": {
    "created_at": "...",
    "model_version": "..."
  }
}
```

This is **not** internal model state. It is external symbolic state.

### Components

#### 1. State Store

Owns the canonical JSON/event-log state.

Responsibilities:

- load/save sessions,
- validate schema,
- apply accepted mutations,
- keep audit history.

#### 2. Transition Proposer

Uses the model to propose a state delta from user input.

```json
{
  "intent": "create_note",
  "delta": [{ "op": "add", "path": "/records/-", "value": { "title": "Meeting" } }],
  "rationale": "User asked to create a note titled Meeting."
}
```

#### 3. Deterministic Validator

Checks deltas without trusting model self-evaluation.

Rules:

- schema validity,
- invariant preservation,
- authorization,
- no impossible transitions,
- no undeclared destructive changes.

#### 4. Projection Renderer

Can be model-assisted or deterministic, but must be evaluated against explicit state.

#### 5. Test Harness

Runs scripted interaction suites and compares final state/projection to expected outcomes.

### What It Tests

- Projection UX.
- Delta validation.
- Invariant design.
- Failure modes of model-suggested state transitions.
- Baselines for later strong-projection experiments.

### What It Does Not Test

- Whether hidden state can be the application.

## Track C — Strong Projection / Latent-State Experiment

### Goal

Test the actual thesis: can model internals act as the application state?

This requires an open model or runtime that exposes internals. Closed hosted APIs are insufficient because they do not expose activations/KV cache reliably enough for inspection, snapshotting, or perturbation.

### Candidate Experiment

Use a tiny domain with hard invariants, e.g. a counter, todo list, inventory ledger, or finite-state workflow.

```text
User event
   │
   ▼
Open model inference ──► hidden/KV state snapshot ──► probe/decoder ──► recovered app state
        │                         │                         │
        │                         └──── restore/perturb ◄────┘
        ▼
UI projection
```

### Requirements

1. **No authoritative external app state** during the main run.
2. Capture hidden states / KV cache after each interaction.
3. Train or define probes that recover app state from internals.
4. Snapshot and restore model-internal state if technically possible.
5. Perturb candidate state dimensions and observe projection changes.
6. Evaluate against an external oracle used only for testing, not runtime.

### Minimum Tests

#### State Recovery

Can a probe recover the app state from activations/KV better than chance and better than transcript-only baselines?

#### Persistence

Can the system resume from a saved internal state without replaying the full transcript?

#### Invariants

Can it preserve simple invariants?

Examples:

- item IDs are unique,
- completed count equals completed items,
- inventory cannot go negative,
- workflow cannot skip required approval states.

#### Counterfactual Intervention

If a latent feature corresponding to “active note” or “counter value” is changed, does the projected UI change accordingly?

#### Projection Fidelity

Does the UI projection reflect the decoded latent state, not just the latest textual self-report?

### What Success Would Mean

A successful Track C result would not prove a full neural app runtime, but it would establish a falsifiable foothold: model internals can carry small, queryable, mutable application state across interactions.

## Validation Principles

Avoid circular validation.

Bad:

```text
model generates state
model generates projection
model judges whether projection matches state
```

Better:

```text
runtime records user events
independent test oracle computes expected constraints
projection/state are checked by deterministic validators and/or separately trained probes
failures are logged as diffs
```

Validation layers should include:

- deterministic schema checks,
- invariant checks,
- replay tests,
- differential tests against a conventional reference app,
- adversarial input suites,
- probe-based latent-state recovery for Track C.

## Recommended Build Order

1. **Track A** — Clone the Mirage pattern locally to understand weak projection and UX drift.
2. **Track B** — Build the hybrid harness as the practical baseline and testbed.
3. **Track C** — Run small open-model latent-state experiments to test the strong claim.
4. Compare A/B/C on the same tiny domains and publish failure modes.

## Non-Goals For Now

- Production app framework.
- Multi-user support.
- Payments, auth, or sensitive data.
- Claims that context JSON proves hidden-state applications.
- Claims that generative UI protocols are already neural app runtimes.

## Relation to SLOP

SLOP should be used here as the **projection protocol for explicit-state experiments**, not as evidence that the app lives inside a model. The dedicated fit note is [`../references/slop-fit.md`](../references/slop-fit.md).

Potential mapping:

| SLOP concept | Track A — weak role | Track B — hybrid role | Track C — strong role |
|---|---|---|---|
| State tree | Prompt-visible current app surface in `<slop-state>` | Canonical semantic projection of explicit JSON/db/event state | Decoded/probed view of latent state for inspection only |
| Affordances | Contextual actions attached to visible projected state | Validated mutation boundary around explicit state | Diagnostic/control hooks around experiment harness |
| Snapshots/patches | Fresh current observation without stale transcript buildup | Replayable, testable state evolution | Compare decoded latent state over time |
| Salience/summaries/windowing | Keep weak projection within context budget | Scale explicit-state projected apps | Choose what latent diagnostics enter the observer tree |
| Content references | Avoid stuffing large prompt-visible content into the tail | On-demand document/log/file access | Attach probe artifacts, traces, and decoded snapshots |

### SLOP Track A pattern

```text
Toy app state -> SLOP provider -> canonical text tree -> ephemeral <slop-state> tail -> model -> invoke
```

This is a better weak-projection baseline than raw transcript replay because stale state tails are not persisted in conversation history.

### SLOP Track B pattern

```text
Explicit store -> SLOP tree -> model sees state + affordances -> invoke -> provider validates -> explicit mutation -> patches
```

This is the recommended first serious build: useful, inspectable, and honest that the state is symbolic.

### SLOP Track C pattern

```text
Open model internals -> probe/decoder -> SLOP tree -> evaluator/UI
```

Here SLOP is only the observer/projection layer. The strong claim still depends on showing that the authoritative state is recoverable from, mutable in, and restorable through model internals rather than copied into the SLOP tree.

## Open Questions

1. Can KV cache snapshots function as resumable app state, or are they too brittle?
2. Can latent probes recover structured business state reliably?
3. Is any strong-projection design debuggable enough to be useful?
4. Are symbolic stores fundamentally necessary for transactional apps?
5. What is the smallest non-toy domain where strong projection beats a hybrid?

## Bottom Line

The immediate architecture should be honest:

- Track A proves hallucinated UI loops are possible.
- Track B proves projection-style UX can be engineered safely with explicit state.
- Track C is the actual research bet.

Only Track C can justify the phrase **“the model is the app.”**
