# Track A - Weak SLOP Projection Prototype

This experiment demonstrates a small weak projection loop:

1. A tiny todo app owns explicit Python state.
2. That state is projected into a minimal SLOP-like semantic tree.
3. The tree is rendered as a canonical text tree in an ephemeral
   `<slop-state generated_at="...">...</slop-state>` prompt tail.
4. A model adapter chooses a contextual affordance.
5. The app applies the selected action and the next request gets a fresh tail.

This is **weak projection**, not strong projection. It does not store app
identity or state in hidden model state, KV cache, activations, weights, or any
other model-internal runtime. The authoritative app state is an ordinary Python
object, and the model-facing state is prompt-visible context.

## Files

- `slop_tree.py` - local compatibility tree facade and text rendering.
- `state_tree.py` - todo domain state and domain-to-SLOP projection.
- `slop_assembler.py` - SLOP Python SDK-backed tree assembler and canonical
  `<slop-state>` rendering.
- `prompt_builder.py` - stable-message prompt builder with fresh ephemeral
  state-tail injection.
- `action_router.py` - invocation data type and concrete todo dispatch.
- `model_adapter.py` - deterministic and OpenAI model adapters.
- `prototype.py` - CLI demo wiring the assembler, prompt builder, adapter, and
  router together.
- `test_prototype.py` - focused `unittest` coverage for prompt tails,
  affordances, and the demo state transition.
- `test_integration.py` - end-to-end state to tree to prompt to action to state
  update coverage.

## SLOP-Like Shape

Each projected node has:

- `id`
- `type`
- `properties`
- `children`
- `affordances`
- `meta`

Rendering is close to the SLOP text-tree style:

```text
[type] id: label (key=value) actions: {action(param: type)}
```

Example:

```text
[todo] todo-1: Draft Track A README (completed=false) actions: {complete_item(id: string)}
```

## Ephemeral Tail Rule

`EphemeralTailPromptBuilder` stores stable conversation messages separately from
state projection. Each `build_request(...)` call appends exactly one fresh
`<slop-state>` block after the stable prefix. Previous state tails are never
written into stored conversation history.

## Run

```bash
python3 experiments/track-a-weak-slop-projection/prototype.py
```

## Test

```bash
python3 -m unittest experiments/track-a-weak-slop-projection/test_prototype.py
python3 -m unittest experiments/track-a-weak-slop-projection/test_integration.py
```

## What This Tests

- Fresh prompt-visible semantic projection.
- Contextual affordances rendered next to relevant nodes.
- Stable conversation history that does not persist stale state tails.

## What This Does Not Test

- Hidden-state persistence.
- KV-cache or activation state as application state.
- Durable model-internal identity.
- True neural runtime semantics.

## Weak-Projection MVP Loop

This track now includes a minimal interactive loop and drift measurement layer:

- `interactive_loop.py` starts from a fresh `TodoApp`, prints the current
  `<slop-state>` tail, accepts free-form commands, tries `OpenAIAdapter` first,
  falls back to `DeterministicAdapter` when `OPENAI_API_KEY` is missing, applies
  the selected affordance, and accumulates turn, prompt-size, tail-size, and
  drift metrics.
- `drift_detector.py` compares deterministic snapshots before and after each
  turn. It classifies item changes as `expected`, `unexpected_add`,
  `unexpected_remove`, or `property_shift`, then reports drift counts,
  percentages, and per-item classifications.
- `demo_mirage.py` runs the same loop for ten canned turns and prints prompt
  tail growth plus aggregate drift rate.

Run the interactive loop:

```bash
python3 experiments/track-a-weak-slop-projection/interactive_loop.py
```

Run the scripted Mirage-style demo:

```bash
python3 experiments/track-a-weak-slop-projection/demo_mirage.py
```

Run the expanded tests:

```bash
python3 -m unittest discover experiments/track-a-weak-slop-projection
```
