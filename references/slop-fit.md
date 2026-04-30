# SLOP Fit Analysis — Projection Protocol, Not Neural Runtime

**Date:** 2026-04-30  
**Question:** Does the SLOP spec in `~/dev/slop/spec` fit into `proj`'s research agenda around neural app runtimes and projection-based applications?

## Verdict

Yes — **SLOP fits strongly into this project, but as the projection/state protocol layer rather than as the neural app runtime itself.**

SLOP is best understood as:

> a semantic projection protocol for applications whose authoritative state is explicit.

It gives projection-based apps a concrete observation/action boundary: a live state tree, contextual affordances, salience metadata, snapshots, patches, and LLM context-injection conventions. That makes it excellent infrastructure for weak and hybrid projection experiments.

It does **not** satisfy the strong neural-runtime thesis by itself, because SLOP state lives in explicit trees, descriptors, JSON, app state, files, databases, or process memory — not in model internals such as activations, KV cache, recurrent state, or weights.

## Source Basis

This note is based on a local review of the SLOP spec, especially:

- `~/dev/slop/spec/core/overview.md` — semantic state tree, provider/consumer model, design principles.
- `~/dev/slop/spec/core/state-tree.md` — node schema, properties, children, affordances, canonical text rendering.
- `~/dev/slop/spec/core/messages.md` — subscribe/query/invoke, snapshots, patches, version/sequence semantics.
- `~/dev/slop/spec/core/affordances.md` — contextual actions attached to state nodes.
- `~/dev/slop/spec/core/attention.md` — salience, focus, urgency, changed metadata, compaction.
- `~/dev/slop/spec/core/transport.md` — discovery, local/web transports, security boundaries.
- `~/dev/slop/spec/integrations/llm-context.md` — ephemeral `<slop-state>` tail for fresh model-visible state.
- `~/dev/slop/spec/extensions/scaling.md` — view-scoped trees, summaries, windowing, lazy subtrees.
- `~/dev/slop/spec/extensions/async-actions.md` — progress/task nodes for long-running work.
- `~/dev/slop/spec/extensions/content-references.md` — on-demand large content references.
- `~/dev/slop/spec/integrations/mcp.md`, `web.md`, `desktop.md`, `adapters.md` — bridge/adoption paths.
- `~/dev/slop/spec/limitations.md` — explicit current gaps: sessions, auth metadata, backpressure, MCP extension, reconnection, tree composition.

## Mapping To `proj` Taxonomy

| `proj` category | Does SLOP fit? | Why |
|---|---:|---|
| **Weak projection** | Yes, excellent fit | SLOP can render current app state into an ephemeral model context tail. The model projects behavior from explicit, prompt-visible state rather than from pixels or hidden internals. |
| **Hybrid projection** | Yes, strongest practical fit | SLOP's tree and affordance model create a disciplined boundary between explicit state and model-driven mutation/projection. This is the best near-term engineering substrate. |
| **Strong projection / neural app runtime** | No, not directly | SLOP externalizes state as a semantic tree. Unless the authoritative state is model-internal, it is not a neural app runtime. |
| **Generative UI / agent UI** | Adjacent but cleaner | SLOP is not just generated UI; it defines observable semantic state plus contextual actions. It can feed generated UI layers, but is not limited to rendering. |
| **Codegen apps** | Mostly orthogonal | SLOP can expose a generated app's state, but generated source code remains the runtime. |
| **World-model runtime** | Possible observer layer | A future latent-state experiment could decode model internals into a SLOP tree for inspection, but SLOP would be instrumentation, not the world model. |

## Why SLOP Strengthens The Project

### 1. It makes “projection” concrete

The most useful SLOP principle for this repo is: **apps control the projection**.

A SLOP provider maps an underlying application state into a semantic tree:

```json
{
  "id": "msg-42",
  "type": "item",
  "properties": {
    "subject": "Launch plan",
    "unread": true
  },
  "affordances": [
    { "action": "reply" },
    { "action": "archive" }
  ],
  "meta": {
    "salience": 0.9
  }
}
```

That is exactly the kind of projected application surface this project needs to reason about. It avoids the vague version of projection where the model merely “imagines the app.”

### 2. It separates observation from action

SLOP's affordances are attached to the state nodes they affect. This is much stronger than giving the model a flat global tool list.

Instead of:

```text
Tools: reply_to_email(id, body), archive_email(id), delete_email(id), ...
```

The model sees:

```text
[item] msg-42: Launch plan (unread=true)  actions: {reply(body), archive, delete}
```

For projection-based apps, that matters: actions become part of the projected semantic state, not detached RPC calls.

### 3. It gives weak projection a rigorous implementation

The `llm-context.md` integration defines an ephemeral state tail:

```xml
<slop-state>
  ...current SLOP tree projection...
</slop-state>
```

Rules:

- render the current tree fresh on every model request;
- append it after the stable conversation prefix;
- do not persist previous state tails in conversation history;
- treat state-tail content as untrusted observation data;
- use salience, depth, windowing, and summaries to keep it small.

This gives Track A a disciplined alternative to transcript soup. It is still weak projection, because state is prompt-visible, but it is an honest and testable weak-projection architecture.

### 4. It gives hybrid projection a clean runtime loop

SLOP naturally supports this Track B loop:

```text
Explicit app state / db / event log
        │
        ▼
SLOP provider builds semantic state tree
        │
        ▼
SLOP consumer renders <slop-state> tail for the model
        │
        ▼
Model chooses contextual affordance
        │
        ▼
SLOP invoke
        │
        ▼
Provider validates, authorizes, mutates explicit state
        │
        ▼
Snapshot/patch stream updates the projected state
```

This is likely the best first serious prototype path for `proj`: useful, inspectable, replayable, and honest about explicit state.

### 5. It directly addresses scale and token budget

Projection apps become useless if the model has to read the entire app on every turn. SLOP has first-class mechanisms for this:

- `meta.summary` for collapsed subtrees;
- `meta.salience`, `focus`, `changed`, and `urgency` for attention;
- depth-limited subscriptions;
- `max_nodes` compaction;
- view-scoped trees;
- windowed collections;
- lazy subtrees;
- content references for large text/binary/streaming content.

Those mechanisms are highly relevant to `proj` because they define how a projected app can remain legible under finite context.

## Recommended Positioning In This Repo

Use this sentence as the canonical framing:

> SLOP is directly relevant to projection-based applications because it defines a semantic projection of application state for AI consumers: a live state tree with contextual affordances, salience, snapshots, patches, and LLM context-injection conventions. In this project's taxonomy, SLOP belongs primarily to weak and hybrid projection systems. It does not by itself constitute a neural app runtime, because the authoritative state remains explicit rather than residing in model internals. However, SLOP provides a practical substrate for building and evaluating projected apps, and can serve as an observer/interface layer for stronger latent-state experiments.

## Recommended Architecture Path

### Prototype 1 — Weak SLOP Projection App

Goal:

> Build a small app whose explicit semantic state is exposed through SLOP and injected into the LLM as an ephemeral `<slop-state>` tail.

Architecture:

```text
Toy app state
  ↓
SLOP provider
  ↓ snapshot/patches
SLOP consumer
  ↓ canonical text tree
LLM prompt tail
  ↓
LLM response or action choice
  ↓
SLOP invoke
  ↓
state mutation
```

What it proves:

- semantic observation beats screenshots;
- contextual affordances beat flat tool lists;
- ephemeral state tails beat stale transcript-state;
- projection can be live, inspectable, and testable.

What it does **not** prove:

- hidden-state persistence;
- model-internal app identity;
- strong neural runtime semantics.

### Prototype 2 — Hybrid Model-Mutated App

Goal:

> Let the model shape or mutate an explicit app state tree through constrained SLOP affordances, then re-project the result.

Example interaction:

```text
User: "Turn this into a lightweight CRM."

Model sees:
[root] app
  [collection] entities
  [view] current-screen
  actions: {create_entity(name), add_field(entity, field), create_view(type, entity)}

Model invokes:
create_entity({ name: "Contact" })
add_field({ entity: "Contact", field: "email" })
create_view({ type: "list", entity: "Contact" })
```

This is a strong Track B experiment because the model participates in app evolution, but every mutation remains explicit and auditable.

### Prototype 3 — Strong Latent-State Experiment With SLOP Observer

Goal:

> Test whether an open model can maintain small application state in internals, while a decoder/probe exposes the recovered state through SLOP for inspection.

Architecture:

```text
User events
  ↓
Open model inference loop
  ↓
KV/activation snapshot
  ↓
probe or decoder recovers candidate app state
  ↓
SLOP provider exposes recovered state tree
  ↓
evaluator/UI/agent observes and compares against oracle
```

In this design, SLOP is not the runtime. It is the observer/debug/projection layer wrapped around the neural-runtime experiment.

## Gaps And Caveats

### SLOP does not define model-side agency

SLOP defines state exposure and action invocation. It does not define:

- model planning;
- action selection;
- schema evolution;
- app synthesis;
- generated UI validation;
- how to distinguish model belief from app truth.

`proj` should own those layers.

### SLOP does not define app synthesis

SLOP can represent an app once there is a state tree and affordance set. It does not specify how a model invents new app schemas, workflows, node types, or affordances over time.

That is a promising Track B research contribution: model-guided app construction over an explicit SLOP state/action substrate.

### SLOP is present-tense by default

The ephemeral-tail pattern optimizes for fresh current state, not historical reasoning. If projected apps need temporal queries — “what changed since I asked?” — they need an explicit event log, semantic diff stream, pinned snapshots, or replay harness in addition to the current SLOP tree.

### SLOP's current limitations matter for productized projection apps

The SLOP limitations doc flags several practical gaps relevant to `proj`:

- no core multi-user primitive;
- no standardized authorization metadata;
- incomplete backpressure signaling;
- no formal MCP extension yet;
- no SDK-level reconnection handling;
- no formal multi-provider tree composition utility;
- no typed affordance result schema.

These do not block research prototypes, but they matter before claiming a production runtime.

### Stub affordance visibility is an agent workflow issue

Depth stubs intentionally drop `properties` and `affordances`. This keeps context small, but an agent may need a multi-step workflow:

```text
subscribe shallow → inspect summary → query deeper → discover affordances → invoke
```

Track A/B prototypes should test whether this interaction cost is acceptable.

## What Not To Overclaim

Do not say:

> SLOP proves the model is the app.

Say:

> SLOP provides a semantic projection protocol for explicit-state apps and a practical substrate for weak/hybrid projection experiments.

Do not say:

> A SLOP state tree is neural state.

Say:

> A SLOP state tree is an explicit projected view of app state; it can expose decoded neural state if a separate latent-state experiment provides one.

Do not say:

> SLOP replaces the strong projection problem.

Say:

> SLOP makes the explicit-state baseline strong enough that Track C has something rigorous to beat.

## Bottom Line

SLOP should be part of this project, but with a precise role:

```text
Projection-Based Applications
├── Weak projection
│   └── SLOP is a strong implementation substrate
├── Hybrid projection
│   └── SLOP is probably the best protocol boundary
└── Strong neural runtime
    └── SLOP can expose/debug projected state, but is not the runtime
```

The recommended next move is to use SLOP for the Track B hybrid harness while preserving Track C as the only experiment that can justify the phrase **“the model is the app.”**
