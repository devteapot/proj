# References

This directory contains the research survey for `proj`: neural app runtimes and projection-based applications.

## Canonical Reference

Read these first:

- [`consolidated-research.md`](consolidated-research.md) — merged survey and thesis synthesis from the two model-assisted research runs.
- [`slop-fit.md`](slop-fit.md) — analysis of SLOP as a projection protocol for weak/hybrid projection apps, not a strong neural runtime.

Supporting audit file:

- [`source-status.md`](source-status.md) — source-confidence notes, broken/manual-check links, and recommended coverage additions.

## Audited Conclusion

No mature public system currently satisfies the strong definition of a projection-based application:

> the model's hidden/neural state is the authoritative application runtime, and the UI is only a projection of that state.

Existing work provides adjacent primitives, not the full architecture.

## Taxonomy After Audit

| Category | State authority | Relevance |
|---|---|---|
| **Strong projection** | Model internals: activations, recurrent state, KV cache, latents, weights | Research target; not mature today |
| **Weak projection** | Prompt-visible transcript/context | Closest demos: Mirage/Websim-style hallucinated apps |
| **Hybrid projection** | JSON/db/files/event logs plus model mutation/rendering | Practical engineering baseline; not proof of the thesis |
| **Generative UI / agent UI** | UI schemas, HTML, component trees, event protocols | Rendering/transport layer, not app identity |
| **World-model runtimes** | Learned visual/environment dynamics | Strong analogy; lacks business/app semantics |
| **Codegen apps** | Generated conventional source code | Opposite of projection; model exits runtime |

## Strongest Research Anchors

Direct or near-direct:

1. **Mirage / AmongAI** — closest weak-projection app demo.
2. **GameNGen, Oasis, Genie 3** — neural runtime/world-model analogues.
3. **Karpathy, Software 2.0 / LLM-as-kernel framing** — intellectual framing, but not a full app architecture.
4. **LaSynth / latent execution** — academic ancestor for programs in latent space.
5. **Transformers are Multi-State RNNs** — theoretical support for thinking about transformer state/KV cache as recurrent state.
6. **A2UI, AG-UI, MCP Apps, Thesys** — contrast cases: useful UI/protocol layers that externalize app state.

## What The Survey Should Not Overclaim

- Software 2.0 establishes weights as learned programs; it does **not** establish mutable inference-time app state.
- Mirage demonstrates a transcript-mediated hallucinated app loop; it does **not** prove hidden-state persistence.
- World models show networks can simulate environments; they do **not** solve app invariants, transactions, auth, or debugging.
- JSON-in-context prototypes are hybrid systems, not strong neural app runtimes.
- SLOP state trees are explicit semantic projections; they support weak/hybrid projection but do **not** make the model-internal state authoritative.
- Two research runs using near-identical prompts are useful triangulation, not independent empirical corroboration.

## Open Research Problems

- Persistent neural state with identity.
- Projection fidelity from latent state to UI.
- Independent validation without circular model self-grading.
- Debugging/probing/intervention on hidden state.
- Multi-user and transactional semantics.
- Latency for direct manipulation.

## Recommended Additions To Future Research

The current survey is good, but should eventually add deeper coverage of:

- MuZero, DreamerV2/V3, and model-based RL.
- Neural Turing Machines / Differentiable Neural Computers.
- Transformer memory/recurrent architectures: Transformer-XL, Memorizing Transformers, recurrent memory models, Mamba/RWKV-style stateful sequence models where relevant.
- UI agent benchmarks: OSWorld, WebArena, AndroidWorld, MiniWoB++, SeeAct, WebVoyager.
- Mechanistic interpretability: probing, sparse autoencoders, activation patching, causal tracing.
- Formal counter-thesis: databases, CRDTs, event sourcing, type systems, and why symbolic state remains hard to remove.

## Original Research Artifacts

The experiment files are preserved as source artifacts:

- `../experiments/codex-research-gpt55.md` — broader survey.
- `../experiments/codex-research-opus.md` — sharper critical synthesis and gap analysis.

Treat them as model-assisted research notes, not final authority. The canonical synthesis is `consolidated-research.md` plus the source audit in `source-status.md`.
