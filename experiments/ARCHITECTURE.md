# Architecture — Projection Runtime

## Design Principles

1. **The model is the app.** The neural network's weights + internal state hold the entire application. No code files define behavior.
2. **The UI is a projection.** The interface is generated in real-time from the model's current state, not from templates or code.
3. **State is first-class.** The application's state is a structured representation maintained by the model, not a side effect of code execution.
4. **Projection is verifiable.** Every rendering must be checkable for consistency with the internal state.

## Core Concepts

### Internal Application State (IAS)

The IAS is the structured representation of the application's state as maintained by the model. It's not the model's weights (those are the app's *knowledge*). The IAS is the app's *current condition* — what data it holds, what the user is doing, what context is active.

```json
{
  "session_id": "abc123",
  "app_state": {
    "domain": "notes",
    "documents": [...],
    "active_document": "doc-1",
    "user_preferences": {},
    "history": [...]
  },
  "metadata": {
    "created_at": "...",
    "last_modified": "...",
    "model_version": "..."
  }
}
```

The IAS is **not** stored in files. It's maintained in the model's context window (or external memory layer) and mutated through interactions. The model *owns* the state.

### Projection Protocol

The protocol for how the model communicates its state to the renderer. Unlike A2UI (which sends UI data) or Generative UI (which sends HTML), the projection protocol sends the **internal state** and lets the renderer choose how to display it.

```
Model → Projection Protocol → Renderer
(what the model knows)     (how to show it)
```

The renderer can output: text, HTML, JSON, voice, structured forms, whatever the client supports.

### Validation Layer

The validation layer checks that the projection matches the internal state. Two key checks:

1. **Faithfulness:** Does the rendered output correctly represent what the model knows? (Not hallucinating data, not omitting state)
2. **Consistency:** Is the internal state self-consistent? (No contradictions, no drift)

### The Projection Loop

```
1. User provides input (text, command, interaction)
2. Model processes input, updates IAS
3. Model generates projection of current IAS
4. Validation layer checks projection fidelity
5. Renderer displays projection to user
6. User interacts → repeat
```

## Minimal Prototype: p0

### Scope

Build the simplest possible proof that a model can maintain internal app state and project it through a renderable interface.

### What It Does

A CLI-based "app" where:
1. You define a domain (e.g., "a notes app", "a todo app", "a simple CRM")
2. The model initializes an IAS for that domain
3. You interact with the model using natural language
4. After each interaction, the model outputs a structured projection of its current IAS
5. You can inspect the projection to verify the model's internal state

### Components

#### 1. State Manager

Manages the IAS as structured data passed in the prompt context.

```python
class StateManager:
    def init(self, domain_spec):
        """Initialize IAS for a domain (e.g., notes, todos)"""
        ...

    def update(self, interaction):
        """Update IAS based on user interaction"""
        ...

    def get_state(self):
        """Get current structured state"""
        ...
```

#### 2. Projection Generator

Takes the IAS and generates a projection (text + structured format).

```python
class ProjectionGenerator:
    def generate(self, ias):
        """Generate human-readable + machine-verifiable projection"""
        return {
            "text": "rendered view for user",
            "structured": ias,
            "fingerprint": hash(ias)  # for validation
        }
```

#### 3. Validator

Checks that the projection matches the IAS.

```python
class Validator:
    def check(self, projection, ias):
        """Verify projection fidelity"""
        # Check that all state is represented
        # Check no extraneous data
        # Return pass/fail + diff
        ...
```

#### 4. CLI Runner

Ties it together:

```
$ proj run --domain notes

> Create a note titled "Meeting"
> [Model processes, updates IAS]
> Projection:
> ├── State: notes app
> ├── Active: "Meeting"
> ├── Content: ...
> └── Fingerprint: abc123
> ✓ Validation passed

> Update note content: "Discussed proj architecture"
> [Model processes, updates IAS]
> Projection:
> ├── State: notes app
> ├── Active: "Meeting"
> ├── Content: "Discussed proj architecture"
> └── Fingerprint: def456
> ✓ Validation passed
```

### Implementation

- **Language:** Python (accessible, good LLM API support)
- **Model:** Any LLM API (OpenAI, Anthropic, local via vLLM)
- **Output:** Structured JSON + formatted text
- **State:** Stored as JSON in context, persisted to disk between sessions

### What This Proves

1. **A model can hold app state in context** and mutate it through interaction
2. **The projection is a faithful rendering** of the internal state (verifiable)
3. **The model is the app** — no code files define behavior, only the model's knowledge and the projection protocol
4. **State persists across turns** — the model remembers what was created/modified

### What This Doesn't Do (Yet)

- No persistent storage (just context window + disk JSON)
- No real UI rendering (just structured text/JSON output)
- No weight-based state (the model's knowledge is generic, not app-specific)
- No multi-model support
- No validation against actual execution (just structural checks)

## Evolution Path

### Phase 1 (p0): CLI projection runner
- Verify the core concept works with any model
- Structured state + projection + validation in a loop

### Phase 2: Persistent sessions
- Store IAS to disk between runs
- Load/restore state on session start
- Version control for state (like git for app state)

### Phase 3: Renderer plugins
- Pluggable renderers: text, HTML, JSON, voice
- Same projection → different outputs based on renderer

### Phase 4: Model-specific apps
- Fine-tune models on specific app domains
- The model's weights become the app's "program"
- Faster inference, more coherent state

### Phase 5: Full runtime
- SLOP integration for orchestration
- Multi-model coordination
- Real UI rendering (web, mobile, voice)

## Connection to SLOP

This prototype can be built on top of SLOP:

- **Session provider** → State Manager (persistent state across interactions)
- **Runtime** → CLI Runner (the execution loop)
- **Orchestration** → Projection loop (coordinate state, projection, validation)
- **Protocol** → Projection Protocol (standardized state→UI translation)

The proj project is essentially SLOP applied to neural-native applications: the model is the app, the protocol is the projection layer, and the runtime manages the state machine.

## Risks and Open Questions

1. **State drift:** Over long interactions, the model's internal state may drift from its original state. How do we detect and correct this?
2. **Validation accuracy:** How reliably can we verify that a projection matches the internal state? The model generates both, so there's a circularity risk.
3. **State capacity:** The context window has limits. How do we scale beyond what fits in a single prompt?
4. **Determinism:** LLMs are probabilistic. Two identical interactions may produce different internal states. How do we ensure reproducibility?
5. **The "code" question:** If the model is the app and code is just a projection, how do we debug when the projection is wrong? Who fixes the model's understanding?

These are all active research questions — and opportunities.
